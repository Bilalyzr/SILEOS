"""Studio faces API (v2.0 §4 — WP6) at /api/v1/studio.

  GET  /courses/{id}/settings            parent-view + rewards + opening face (owner/admin)
  PUT  /courses/{id}/settings            partial update {parent_view?, rewards?, face_dismissed?}
  GET  /courses/{id}/schedule            SP term view: weeks of live classes + counts
  POST /courses/{id}/schedule/clone-week {from_week_start, to_week_start} → new class ids
  GET  /courses/{id}/rewards/me          learner: course points, custom badges + progress
  GET  /courses/{id}/parent-view         guardian/learner: what guardians can see (read-only)
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.user import User
from app.services import studio_service as studio
from app.services.auth_service import AuthService
from app.services.course_access import can_edit

router = APIRouter()


def _course_owner(db: Session, course_id: int, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_edit(db, course, user):
        raise HTTPException(status_code=403, detail="Not your course")
    return course


class SettingsIn(BaseModel):
    parent_view: Optional[Dict[str, Any]] = None
    rewards: Optional[Dict[str, Any]] = None
    face_dismissed: Optional[bool] = None


class CloneWeekIn(BaseModel):
    from_week_start: date
    to_week_start: date


@router.get("/courses/{course_id}/settings")
async def get_settings(course_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.get_current_active_user)):
    _course_owner(db, course_id, current_user)
    return studio.get_settings(db, course_id)


@router.put("/courses/{course_id}/settings")
async def put_settings(course_id: int, body: SettingsIn, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.get_current_active_user)):
    _course_owner(db, course_id, current_user)
    try:
        return studio.put_settings(db, course_id, current_user.id, parent_view=body.parent_view,
                                   rewards=body.rewards, face_dismissed=body.face_dismissed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/courses/{course_id}/schedule")
async def schedule(course_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(AuthService.get_current_active_user)):
    _course_owner(db, course_id, current_user)
    return studio.term_schedule(db, course_id)


@router.post("/courses/{course_id}/schedule/clone-week")
async def clone_week(course_id: int, body: CloneWeekIn, db: Session = Depends(get_db),
                     current_user: User = Depends(AuthService.get_current_active_user)):
    course = _course_owner(db, course_id, current_user)
    try:
        ids = studio.clone_week(db, course_id, course.post_author, body.from_week_start, body.to_week_start)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"created": ids, "schedule": studio.term_schedule(db, course_id)}


@router.get("/courses/{course_id}/rewards/me")
async def my_rewards(course_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(AuthService.get_current_active_user)):
    if not db.query(Course.id).filter(Course.id == course_id).first():
        raise HTTPException(status_code=404, detail="Course not found")
    return studio.my_course_rewards(db, current_user.id, course_id)


@router.get("/courses/{course_id}/parent-view")
async def parent_view(course_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(AuthService.get_current_active_user)):
    if not db.query(Course.id).filter(Course.id == course_id).first():
        raise HTTPException(status_code=404, detail="Course not found")
    return {"course_id": course_id, "parent_view": studio.parent_view(db, course_id)}
