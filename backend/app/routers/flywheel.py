"""Flywheel + extras (v2.0 §10 — WP8) at /api/v1/flywheel.

  GET  /courses/{id}/next-agenda?class_id=&polish=   next-class proposal (derived; LLM prose optional)
  GET  /courses/{id}/insight-cards                   3D path evidence × question outcomes (derived)
  POST /teach-back  GET /teach-back?concept=&course_id=   peer explanations
  POST /teach-back/{id}/rate {helpful}               one vote per learner, changeable
  POST /teach-back/{id}/hide                         instructor/admin moderation
  GET  /digilocker/status                            adapter configured?
  POST /certificates/{issued_id}/digilocker          push (honest 503 without credentials)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.flywheel import TeachBack, TeachBackRating
from app.models.user import User
from app.services import flywheel_service as svc
from app.services.auth_service import AuthService

router = APIRouter()
ADMIN_ROLES = ("admin", "superadmin")


def _course(db: Session, course_id: int) -> Course:
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return c


def _owner(db: Session, course_id: int, user: User) -> Course:
    c = _course(db, course_id)
    if c.post_author != user.id and user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not your course")
    return c


def _enrolled_or_owner(db: Session, course_id: int, user: User) -> None:
    c = _course(db, course_id)
    if c.post_author == user.id or user.role in ADMIN_ROLES:
        return
    if not db.query(Enrollment.id).filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id,
                                          Enrollment.enrollment_status.in_(["enrolled", "completed"])).first():
        raise HTTPException(status_code=403, detail="Enrol in the course first")


@router.get("/courses/{course_id}/next-agenda")
async def next_agenda(course_id: int, class_id: Optional[int] = None, polish: bool = False,
                      db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_active_user)):
    _owner(db, course_id, current_user)
    return svc.next_class_agenda(db, course_id, class_id=class_id, polish=polish, actor_id=current_user.id)


@router.get("/courses/{course_id}/insight-cards")
async def insight_cards(course_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(AuthService.get_current_active_user)):
    _owner(db, course_id, current_user)
    return {"course_id": course_id, "cards": svc.insight_cards(db, course_id)}


class TeachBackIn(BaseModel):
    concept: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=svc.TEACH_BACK_MAX)
    course_id: Optional[int] = None


@router.post("/teach-back", status_code=201)
async def write_teach_back(body: TeachBackIn, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    if body.course_id:
        _enrolled_or_owner(db, body.course_id, current_user)
    try:
        tb = svc.write_teach_back(db, current_user.id, body.concept, body.text, body.course_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return svc.teach_back_dict(tb, author=current_user.display_name)


@router.get("/teach-back")
async def list_teach_backs(concept: Optional[str] = Query(default=None), course_id: Optional[int] = None,
                           mine: bool = False, limit: int = Query(20, ge=1, le=100),
                           db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_active_user)):
    from app.services.mastery_service import normalize_concept
    q = db.query(TeachBack)
    if mine:
        q = q.filter(TeachBack.user_id == current_user.id)
    else:
        q = q.filter(TeachBack.status == "visible")
    if concept:
        q = q.filter(TeachBack.concept == normalize_concept(concept))
    if course_id:
        q = q.filter(TeachBack.course_id == course_id)
    rows = q.order_by((TeachBack.helpful_count - TeachBack.not_helpful_count).desc(), TeachBack.id.desc()).limit(limit).all()
    votes = {r.teach_back_id: r.helpful for r in db.query(TeachBackRating)
             .filter(TeachBackRating.rater_id == current_user.id, TeachBackRating.teach_back_id.in_([t.id for t in rows] or [0])).all()}
    names = {u.id: u.display_name for u in db.query(User).filter(User.id.in_({t.user_id for t in rows} or {0})).all()}
    return {"teach_backs": [svc.teach_back_dict(t, my_vote=votes.get(t.id), author=names.get(t.user_id)) for t in rows]}


class RateIn(BaseModel):
    helpful: bool


@router.post("/teach-back/{tb_id}/rate")
async def rate(tb_id: int, body: RateIn, db: Session = Depends(get_db),
               current_user: User = Depends(AuthService.get_current_active_user)):
    try:
        tb, changed = svc.rate_teach_back(db, tb_id, current_user.id, body.helpful)
    except LookupError:
        raise HTTPException(status_code=404, detail="Teach-back not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {**svc.teach_back_dict(tb, my_vote=body.helpful), "changed": changed}


@router.post("/teach-back/{tb_id}/hide")
async def hide(tb_id: int, db: Session = Depends(get_db), current_user: User = Depends(AuthService.require_instructor)):
    tb = db.query(TeachBack).filter(TeachBack.id == tb_id).first()
    if not tb:
        raise HTTPException(status_code=404, detail="Teach-back not found")
    if current_user.role not in ADMIN_ROLES:
        if not tb.course_id or _course(db, tb.course_id).post_author != current_user.id:
            raise HTTPException(status_code=403, detail="Only the course owner can hide this")
    tb.status = "hidden"
    db.commit()
    return svc.teach_back_dict(tb)


@router.get("/digilocker/status")
async def digilocker_status(current_user: User = Depends(AuthService.get_current_active_user)):
    return {"configured": svc.digilocker_configured(),
            "needs": [] if svc.digilocker_configured() else ["DIGILOCKER_CLIENT_ID", "DIGILOCKER_CLIENT_SECRET"],
            "note": "Issuer onboarding with NeGD (DigiLocker) and APAAR/ABC-ID mapping are owner-owned inputs."}


@router.post("/certificates/{issued_id}/digilocker")
async def push_to_digilocker(issued_id: int, db: Session = Depends(get_db),
                             current_user: User = Depends(AuthService.get_current_active_user)):
    from app.models.certificate import IssuedCertificate
    issued = db.query(IssuedCertificate).filter(IssuedCertificate.id == issued_id).first()
    if not issued:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if issued.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not your certificate")
    payload = svc.digilocker_payload(issued)
    if not svc.digilocker_configured():
        raise HTTPException(status_code=503, detail="DigiLocker push is not configured: set DIGILOCKER_CLIENT_ID and "
                                                    "DIGILOCKER_CLIENT_SECRET (issuer credentials from NeGD). Nothing is faked.")
    # Credentials present but the issuer API integration is owner-verified on a
    # real sandbox — return the descriptor so the owner can complete the push.
    return {"status": "prepared", "document": payload}
