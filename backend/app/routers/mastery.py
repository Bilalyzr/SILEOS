"""Learner mastery graph API (v2.0 §8.3, §9.5, §10.1 — WP3) at /api/v1/mastery.

  GET  /me                                  learner's own graph (concepts, estimates, confidence, gaps)
  GET  /me/weak                             weak concepts (Engine D personalisation, tutor context)
  GET  /students/{uid}                      instructor/admin (or the learner) view of a graph
  GET  /students/{uid}/weak
  GET  /students/{uid}/concepts/{concept}   evidence trail behind one estimate
  GET  /links/{kind}/{ref}                  concepts an element declares
  PUT  /links/{kind}/{ref}                  instructor sets them {concepts:[…], course_id?}
  GET  /prerequisites?concept=              PUT /prerequisites {concept, requires}  DELETE /prerequisites
  GET  /courses/{id}/coverage               curriculum coverage + gap report (§8.3 #1, §4.3)
  GET  /courses/{id}/outcome  PUT           UP "Outcome definition" + target concepts
  GET  /courses/{id}/students/{uid}/progress-map   learner path milestones with mastery (§8.3 #2)
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.mastery import ConceptPrerequisite, CourseOutcome
from app.models.user import User
from app.services import mastery_service as ms
from app.services.auth_service import AuthService
from app.services.course_access import can_edit

router = APIRouter()


def _can_view(current_user: User, user_id: int) -> None:
    if current_user.id == user_id or current_user.role in ("instructor", "admin", "superadmin"):
        return
    if current_user.role == "parent":
        try:
            from app.models.parent import ParentStudent  # type: ignore
            return  # parent linkage is checked in the parents router; keep graph read-only here
        except Exception:
            pass
    raise HTTPException(status_code=403, detail="Not allowed to view this learner's mastery")


def _course_owner(db: Session, course_id: int, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_edit(db, course, user):
        raise HTTPException(status_code=403, detail="Not your course")
    return course


@router.get("/me")
async def my_graph(db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_active_user)):
    return ms.learner_graph(db, current_user.id)


@router.get("/me/weak")
async def my_weak(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db),
                  current_user: User = Depends(AuthService.get_current_active_user)):
    return {"weak_concepts": ms.weak_concepts(db, current_user.id, limit)}


@router.get("/students/{user_id}")
async def student_graph(user_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(AuthService.get_current_active_user)):
    _can_view(current_user, user_id)
    return ms.learner_graph(db, user_id)


@router.get("/students/{user_id}/weak")
async def student_weak(user_id: int, limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.get_current_active_user)):
    _can_view(current_user, user_id)
    return {"weak_concepts": ms.weak_concepts(db, user_id, limit)}


@router.get("/students/{user_id}/concepts/{concept}")
async def concept_evidence(user_id: int, concept: str, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    _can_view(current_user, user_id)
    return {"concept": ms.normalize_concept(concept), "evidence": ms.evidence_for_concept(db, user_id, concept)}


class LinksIn(BaseModel):
    concepts: List[str] = Field(default_factory=list, max_items=ms.MAX_CONCEPTS_PER_ITEM)
    course_id: Optional[int] = None


@router.get("/links/{kind}/{ref}")
async def get_links(kind: str, ref: str, db: Session = Depends(get_db),
                    current_user: User = Depends(AuthService.get_current_active_user)):
    if kind not in ms.LINK_KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {sorted(ms.LINK_KINDS)}")
    return {"kind": kind, "ref_id": ref, "concepts": ms.concepts_for(db, kind, ref)}


@router.put("/links/{kind}/{ref}")
async def put_links(kind: str, ref: str, payload: LinksIn, db: Session = Depends(get_db),
                    current_user: User = Depends(AuthService.require_instructor)):
    if kind not in ms.LINK_KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {sorted(ms.LINK_KINDS)}")
    if payload.course_id is not None:
        _course_owner(db, payload.course_id, current_user)
    concepts = ms.set_links(db, kind, ref, payload.concepts, payload.course_id, current_user.id)
    return {"kind": kind, "ref_id": ref, "concepts": concepts}


class PrereqIn(BaseModel):
    concept: str = Field(..., min_length=1, max_length=80)
    requires: str = Field(..., min_length=1, max_length=80)


@router.get("/prerequisites")
async def list_prereqs(concept: Optional[str] = None, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.get_current_active_user)):
    q = db.query(ConceptPrerequisite)
    if concept:
        q = q.filter(ConceptPrerequisite.concept == ms.normalize_concept(concept))
    return {"prerequisites": [{"concept": p.concept, "requires": p.requires} for p in q.order_by(ConceptPrerequisite.concept).limit(500).all()]}


@router.put("/prerequisites")
async def add_prereq(payload: PrereqIn, db: Session = Depends(get_db),
                     current_user: User = Depends(AuthService.require_instructor)):
    c, r = ms.normalize_concept(payload.concept), ms.normalize_concept(payload.requires)
    if not c or not r or c == r:
        raise HTTPException(status_code=422, detail="concept and requires must differ and be non-empty")
    if db.query(ConceptPrerequisite).filter(ConceptPrerequisite.concept == r, ConceptPrerequisite.requires == c).first():
        raise HTTPException(status_code=422, detail="that would create a cycle")
    row = db.query(ConceptPrerequisite).filter(ConceptPrerequisite.concept == c, ConceptPrerequisite.requires == r).first()
    if not row:
        db.add(ConceptPrerequisite(concept=c, requires=r, created_by=current_user.id))
        db.commit()
    return {"concept": c, "requires": r}


@router.delete("/prerequisites")
async def delete_prereq(concept: str, requires: str, db: Session = Depends(get_db),
                        current_user: User = Depends(AuthService.require_instructor)):
    c, r = ms.normalize_concept(concept), ms.normalize_concept(requires)
    n = db.query(ConceptPrerequisite).filter(ConceptPrerequisite.concept == c, ConceptPrerequisite.requires == r).delete()
    db.commit()
    return {"deleted": n}


@router.get("/courses/{course_id}/coverage")
async def coverage(course_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(AuthService.require_instructor)):
    _course_owner(db, course_id, current_user)
    return ms.course_coverage(db, course_id)


class OutcomeIn(BaseModel):
    outcome_text: str = Field("", max_length=2000)
    target_concepts: List[str] = Field(default_factory=list, max_items=40)


@router.get("/courses/{course_id}/outcome")
async def get_outcome(course_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(AuthService.get_current_active_user)):
    row = db.query(CourseOutcome).filter(CourseOutcome.course_id == course_id).first()
    return {"course_id": course_id, "outcome_text": row.outcome_text if row else "",
            "target_concepts": ms.clean_concepts(row.target_concepts if row else [])}


@router.put("/courses/{course_id}/outcome")
async def put_outcome(course_id: int, payload: OutcomeIn, db: Session = Depends(get_db),
                      current_user: User = Depends(AuthService.require_instructor)):
    _course_owner(db, course_id, current_user)
    row = db.query(CourseOutcome).filter(CourseOutcome.course_id == course_id).first()
    if not row:
        row = CourseOutcome(course_id=course_id)
        db.add(row)
    row.outcome_text = payload.outcome_text.strip()
    row.target_concepts = ms.clean_concepts(payload.target_concepts)
    row.updated_by = current_user.id
    db.commit()
    return {"course_id": course_id, "outcome_text": row.outcome_text, "target_concepts": row.target_concepts}


@router.get("/courses/{course_id}/students/{user_id}/progress-map")
async def student_progress_map(course_id: int, user_id: int, db: Session = Depends(get_db),
                               current_user: User = Depends(AuthService.get_current_active_user)):
    _can_view(current_user, user_id)
    return ms.progress_map(db, course_id, user_id)
