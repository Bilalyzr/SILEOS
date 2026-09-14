"""Conversion funnel API (roadmap R1) at /api/v1/funnel.

  POST /events                       {kind, course_id, session_id, meta?} — optional auth (visitors count)
  GET  /courses/{id}/summary?days=   owner/admin
  GET  /overview?days=               instructor: own courses; admin: all
  GET  /me/continue                  learner: continue where you left off
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.user import User
from app.services import funnel_service as svc
from app.services.auth_service import AuthService

router = APIRouter()
ADMIN_ROLES = ("admin", "superadmin")


class EventIn(BaseModel):
    kind: str
    course_id: int
    session_id: str = Field(min_length=8, max_length=64)
    meta: Optional[Dict[str, Any]] = None


@router.post("/events", status_code=201)
async def post_event(body: EventIn, db: Session = Depends(get_db),
                     current_user: Optional[User] = Depends(AuthService.get_optional_current_user)):
    if body.kind not in svc.KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {list(svc.KINDS)}")
    if not db.query(Course.id).filter(Course.id == body.course_id).first():
        raise HTTPException(status_code=404, detail="Course not found")
    meta = {k: v for k, v in (body.meta or {}).items() if isinstance(k, str) and isinstance(v, (str, int, float, bool))}
    ev = svc.record(db, body.kind, body.course_id, body.session_id, user_id=current_user.id if current_user else None, meta=meta)
    return {"id": ev.id, "kind": ev.kind}


@router.get("/courses/{course_id}/summary")
async def course_summary(course_id: int, days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db),
                         current_user: User = Depends(AuthService.get_current_active_user)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.post_author != current_user.id and current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not your course")
    return svc.summary(db, course_id, days)


@router.get("/overview")
async def funnel_overview(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db),
                          current_user: User = Depends(AuthService.require_instructor)):
    admin = current_user.role in ADMIN_ROLES
    return {"days": days, "courses": svc.overview(db, days, instructor_id=None if admin else current_user.id)}


@router.get("/me/continue")
async def my_continue(db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_active_user)):
    return {"items": svc.continue_learning(db, current_user.id)}


@router.get("/instructor/earnings")
async def instructor_earnings(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db),
                              current_user: User = Depends(AuthService.require_instructor)):
    admin = current_user.role in ADMIN_ROLES
    return svc.earnings(db, days, instructor_id=None if admin else current_user.id)


@router.get("/instructor/report.pdf")
async def instructor_report_pdf(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db),
                                current_user: User = Depends(AuthService.require_instructor)):
    from fastapi.responses import Response
    admin = current_user.role in ADMIN_ROLES
    pdf = svc.report_pdf(db, days, current_user.display_name or "Instructor", None if admin else current_user.id)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="instructor-report-{days}d.pdf"'})
