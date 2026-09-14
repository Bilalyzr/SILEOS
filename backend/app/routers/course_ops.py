"""Instructor growth tools (roadmap R6) at /api/v1/course-ops.

  POST /courses/{id}/clone {title?}            deep copy → my draft
  POST /courses/{id}/template {is_template}    owner/admin: publish as a start template
  GET  /templates                              any instructor: templates to start from
  POST /templates/{id}/use {title?}            clone a template into my drafts
  POST /courses/{id}/quizzes/import-csv        multipart file + title → new quiz (all-or-nothing)
  GET  /csv-help                               column spec
  GET/POST/DELETE /courses/{id}/collaborators  owner/admin manage co-instructors
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.course_ops import CourseCollaborator
from app.models.user import User
from app.services import course_ops_service as svc
from app.services.auth_service import AuthService
from app.services.course_access import ADMIN_ROLES, can_edit

router = APIRouter()


def _course(db: Session, course_id: int) -> Course:
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return c


def _owner_only(course: Course, user: User) -> None:
    if course.post_author != user.id and user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only the course owner can do this")


def _course_out(c: Course) -> dict:
    return {"id": c.id, "title": c.post_title, "status": c.post_status, "course_type": c.course_type or "",
            "is_template": bool(getattr(c, "is_template", False)), "owner_id": c.post_author}


class CloneIn(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


@router.post("/courses/{course_id}/clone", status_code=201)
async def clone_course(course_id: int, body: CloneIn, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.require_instructor)):
    source = _course(db, course_id)
    if not can_edit(db, source, current_user) and not getattr(source, "is_template", False):
        raise HTTPException(status_code=403, detail="You can clone your own courses or templates")
    new, lessons, quizzes, assignments = svc.clone_course(db, source, current_user.id, body.title)
    return {**_course_out(new), "copied": {"lessons": lessons, "quizzes": quizzes, "assignments": assignments}}


class TemplateIn(BaseModel):
    is_template: bool


@router.post("/courses/{course_id}/template")
async def set_template(course_id: int, body: TemplateIn, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.require_instructor)):
    course = _course(db, course_id)
    _owner_only(course, current_user)
    course.is_template = body.is_template
    db.commit()
    return _course_out(course)


@router.get("/templates")
async def list_templates(db: Session = Depends(get_db), current_user: User = Depends(AuthService.require_instructor)):
    rows = db.query(Course).filter(Course.is_template.is_(True)).order_by(Course.post_title.asc()).limit(100).all()
    from app.models.course import Lesson
    out = []
    for c in rows:
        out.append({**_course_out(c), "lessons": db.query(Lesson).filter(Lesson.post_parent == c.id).count(),
                    "excerpt": (c.post_excerpt or "")[:200]})
    return {"templates": out}


@router.post("/templates/{course_id}/use", status_code=201)
async def use_template(course_id: int, body: CloneIn, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.require_instructor)):
    source = _course(db, course_id)
    if not getattr(source, "is_template", False):
        raise HTTPException(status_code=404, detail="Template not found")
    new, lessons, quizzes, assignments = svc.clone_course(db, source, current_user.id, body.title or source.post_title, from_template=True)
    return {**_course_out(new), "copied": {"lessons": lessons, "quizzes": quizzes, "assignments": assignments}}


@router.get("/csv-help")
async def csv_help(current_user: User = Depends(AuthService.require_instructor)):
    return {"help": svc.CSV_HELP, "types": sorted(svc.CSV_TYPES),
            "example": "question,type,option_a,option_b,option_c,option_d,correct,marks,explanation\n"
                       "What is 2+2?,multiple_choice,3,4,5,6,B,1,Basic addition\n"
                       "Water boils at 100 C at sea level,true_false,,,,,TRUE,1,\n"
                       "The powerhouse of the cell is the ____,fill_in_blanks,,,,,mitochondria,2,"}


@router.post("/courses/{course_id}/quizzes/import-csv", status_code=201)
async def import_quiz_csv(course_id: int, file: UploadFile = File(...), title: str = Form(""),
                          passing_grade: int = Form(50), db: Session = Depends(get_db),
                          current_user: User = Depends(AuthService.require_instructor)):
    course = _course(db, course_id)
    if not can_edit(db, course, current_user):
        raise HTTPException(status_code=403, detail="Not your course")
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV larger than 2MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    rows, errors = svc.parse_quiz_csv(text)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors[:50], "help": svc.CSV_HELP})
    quiz = svc.create_quiz_from_rows(db, course_id, current_user.id, title.strip() or f"Imported quiz ({len(rows)} questions)", rows,
                                     passing_grade=max(0, min(100, passing_grade)))
    return {"quiz_id": quiz.id, "title": quiz.post_title, "questions": len(rows)}


class CollaboratorIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)


@router.get("/courses/{course_id}/collaborators")
async def list_collaborators(course_id: int, db: Session = Depends(get_db),
                             current_user: User = Depends(AuthService.require_instructor)):
    course = _course(db, course_id)
    if not can_edit(db, course, current_user):
        raise HTTPException(status_code=403, detail="Not your course")
    return {"owner_id": course.post_author, "collaborators": svc.list_collaborators(db, course_id)}


@router.post("/courses/{course_id}/collaborators", status_code=201)
async def add_collaborator(course_id: int, body: CollaboratorIn, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.require_instructor)):
    course = _course(db, course_id)
    _owner_only(course, current_user)
    try:
        row, created = svc.add_collaborator(db, course, body.email, current_user.id)
    except (LookupError, ValueError) as exc:
        # 422, not 404: main.py's global 404 handler rewrites every 404 detail to
        # "Endpoint not found", which would hide the real message from the owner.
        raise HTTPException(status_code=422, detail=str(exc))
    if created:
        try:
            from app.services.notification_service import create_notification
            create_notification(db, user_id=row.user_id, type="course_collaborator", title=f"You are now a co-instructor of {course.post_title}",
                                message="You can edit the curriculum, quizzes, assignments and live classes.", link=f"/instructor/courses/{course.id}/edit",
                                related_id=course.id)
        except Exception:
            pass
    return {"created": created, "collaborators": svc.list_collaborators(db, course_id)}


@router.delete("/courses/{course_id}/collaborators/{user_id}")
async def remove_collaborator(course_id: int, user_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(AuthService.require_instructor)):
    course = _course(db, course_id)
    _owner_only(course, current_user)
    row = db.query(CourseCollaborator).filter(CourseCollaborator.course_id == course_id, CourseCollaborator.user_id == user_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not a collaborator")
    db.delete(row)
    db.commit()
    return {"removed": user_id, "collaborators": svc.list_collaborators(db, course_id)}
