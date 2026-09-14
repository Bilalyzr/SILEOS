"""Learning-signals engine API (2026-09-06) at /api/v1/signals.

  POST /events                              batch of behaviour signals (learner)
  GET  /me/profile?course_id=               learner struggle profile
  GET  /students/{uid}/profile?course_id=   course editor / admin
  GET  /lessons/{id}/heatmap[?user_id=]     course editor (all learners) / learner (own)
  GET|POST|DELETE /lessons/{id}/markers     concept markers on the timeline (course editor)
  POST /adaptive/{course_id}/build          personalised practice set (learner)
  GET  /adaptive/{session_id}               questions (no answer keys)
  POST /adaptive/{session_id}/submit        server-side grading → mastery evidence
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.learning_signals import AdaptiveSession, LessonConceptMarker
from app.models.user import User
from app.services import learning_signals_service as svc
from app.services.auth_service import AuthService
from app.services.course_access import ADMIN_ROLES, can_edit

router = APIRouter()


class EventIn(BaseModel):
    kind: str
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    quiz_id: Optional[int] = None
    question_id: Optional[int] = None
    position_s: Optional[float] = None
    value: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None


class EventsIn(BaseModel):
    events: List[EventIn] = Field(min_length=1, max_length=svc.MAX_BATCH)


@router.post("/events", status_code=201)
async def post_events(body: EventsIn, db: Session = Depends(get_db),
                      current_user: User = Depends(AuthService.get_current_active_user)):
    n = svc.ingest(db, current_user.id, [e.model_dump() for e in body.events])
    return {"recorded": n}


@router.get("/me/profile")
async def my_profile(course_id: Optional[int] = None, db: Session = Depends(get_db),
                     current_user: User = Depends(AuthService.get_current_active_user)):
    return svc.learner_profile(db, current_user.id, course_id)


def _course_editor(db: Session, course_id: int, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_edit(db, course, user):
        raise HTTPException(status_code=403, detail="Not your course")
    return course


@router.get("/students/{user_id}/profile")
async def student_profile(user_id: int, course_id: int = Query(...), db: Session = Depends(get_db),
                          current_user: User = Depends(AuthService.get_current_active_user)):
    if user_id != current_user.id:
        _course_editor(db, course_id, current_user)
    return svc.learner_profile(db, user_id, course_id)


def _lesson(db: Session, lesson_id: int) -> Lesson:
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.get("/lessons/{lesson_id}/heatmap")
async def lesson_heatmap(lesson_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db),
                         current_user: User = Depends(AuthService.get_current_active_user)):
    lesson = _lesson(db, lesson_id)
    course = db.query(Course).filter(Course.id == lesson.post_parent).first()
    if can_edit(db, course, current_user):
        return svc.lesson_heatmap(db, lesson_id, user_id)
    return svc.lesson_heatmap(db, lesson_id, current_user.id)   # learners only ever see their own


class MarkerIn(BaseModel):
    time_s: int = Field(ge=0, le=86400)
    concept: str = Field(min_length=1, max_length=80)


@router.get("/lessons/{lesson_id}/markers")
async def list_markers(lesson_id: int, db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_active_user)):
    _lesson(db, lesson_id)
    return {"markers": [{"id": m.id, "time_s": m.time_s, "concept": m.concept} for m in svc.markers_for(db, lesson_id)]}


@router.post("/lessons/{lesson_id}/markers", status_code=201)
async def add_marker(lesson_id: int, body: MarkerIn, db: Session = Depends(get_db),
                     current_user: User = Depends(AuthService.require_instructor)):
    from app.services.mastery_service import normalize_concept, set_links, concepts_for
    lesson = _lesson(db, lesson_id)
    _course_editor(db, lesson.post_parent, current_user)
    concept = normalize_concept(body.concept)
    m = LessonConceptMarker(lesson_id=lesson_id, time_s=body.time_s, concept=concept, created_by=current_user.id)
    db.add(m)
    db.commit()
    # the lesson now teaches this concept too (mastery graph teaching link)
    try:
        existing = concepts_for(db, "lesson", lesson_id)
        if concept not in existing:
            set_links(db, "lesson", lesson_id, existing + [concept], course_id=lesson.post_parent)
            db.commit()
    except Exception:
        db.rollback()
    return {"markers": [{"id": x.id, "time_s": x.time_s, "concept": x.concept} for x in svc.markers_for(db, lesson_id)]}


@router.delete("/lessons/{lesson_id}/markers/{marker_id}")
async def delete_marker(lesson_id: int, marker_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(AuthService.require_instructor)):
    lesson = _lesson(db, lesson_id)
    _course_editor(db, lesson.post_parent, current_user)
    m = db.query(LessonConceptMarker).filter(LessonConceptMarker.id == marker_id, LessonConceptMarker.lesson_id == lesson_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Marker not found")
    db.delete(m)
    db.commit()
    return {"markers": [{"id": x.id, "time_s": x.time_s, "concept": x.concept} for x in svc.markers_for(db, lesson_id)]}


def _enrolled_or_editor(db: Session, course_id: int, user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if can_edit(db, course, user):
        return course
    if not db.query(Enrollment.id).filter(Enrollment.user_id == user.id, Enrollment.course_id == course_id,
                                          Enrollment.enrollment_status.in_(["enrolled", "completed"])).first():
        raise HTTPException(status_code=403, detail="Enrol in the course first")
    return course


@router.post("/adaptive/{course_id}/build", status_code=201)
async def build_adaptive(course_id: int, count: int = Query(8, ge=3, le=30), focus: Optional[List[str]] = Query(None), db: Session = Depends(get_db),
                         current_user: User = Depends(AuthService.get_current_active_user)):
    _enrolled_or_editor(db, course_id, current_user)
    sess = svc.build_adaptive(db, current_user.id, course_id, count, focus_concepts=focus)
    if not sess.question_ids:
        raise HTTPException(status_code=422, detail="This course has no questions to practise with yet")
    return {"session_id": sess.id, "plan": sess.plan, "questions": svc.adaptive_questions(db, sess)}


@router.get("/adaptive/{session_id}")
async def get_adaptive(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_active_user)):
    sess = db.query(AdaptiveSession).filter(AdaptiveSession.id == session_id).first()
    if not sess or sess.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": sess.id, "plan": sess.plan, "questions": svc.adaptive_questions(db, sess),
            "submitted": sess.submitted_at is not None, "score": sess.score, "max_score": sess.max_score}


class AdaptiveAnswers(BaseModel):
    answers: Dict[str, Any]


@router.post("/adaptive/{session_id}/submit")
async def submit_adaptive(session_id: int, body: AdaptiveAnswers, db: Session = Depends(get_db),
                          current_user: User = Depends(AuthService.get_current_active_user)):
    sess = db.query(AdaptiveSession).filter(AdaptiveSession.id == session_id).first()
    if not sess or sess.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if sess.submitted_at is not None:
        raise HTTPException(status_code=409, detail="Already submitted")
    return svc.grade_adaptive(db, sess, body.answers)



@router.get("/courses/{course_id}/hotspots")
async def course_hotspots(course_id: int, days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db),
                          current_user: User = Depends(AuthService.get_current_active_user)):
    _course_editor(db, course_id, current_user)
    return svc.course_hotspots(db, course_id, days)


@router.get("/courses/{course_id}/sasha-insights")
async def sasha_course_insights(
    course_id: int,
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Course-bounded instructor monitor for Sasha learning signals.

    General chats and AI replies are never stored in this signal table or
    returned here.
    """
    _course_editor(db, course_id, current_user)
    from app.services.tutor_insights_service import course_insights
    return course_insights(db, course_id, days)
