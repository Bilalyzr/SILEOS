"""Public-preview asset gate (2026-09-05).

A lesson the instructor marked `lesson_preview` can be opened by anyone from
the course page. Its media therefore has to be reachable WITHOUT a login —
but only that media, and only while the course is published. This helper is
the single rule the asset endpoints (3D model file, virtual-lab detail,
game play payload) consult when there is no authenticated user.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

PUBLISHED_STATUSES = ("publish", "published", "active")


def allows_anonymous(db: Session, field: str, value: Any) -> bool:
    """True when at least one lesson with `<field> == value` is a public
    preview inside a published course."""
    from app.models.course import Course, Lesson
    if value in (None, ""):
        return False
    col = getattr(Lesson, field, None)
    if col is None:
        return False
    return (db.query(Lesson.id).join(Course, Course.id == Lesson.post_parent)
            .filter(col == value, Lesson.lesson_preview.is_(True), Course.post_status.in_(PUBLISHED_STATUSES))
            .first()) is not None


def require_anonymous_preview(db: Session, field: str, value: Any, what: str = "This content") -> None:
    if not allows_anonymous(db, field, value):
        raise HTTPException(status_code=401, detail=f"{what} needs a login — only public-preview lessons are open to visitors")
