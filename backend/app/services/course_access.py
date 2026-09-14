"""Who may edit a course (roadmap R6). ONE rule for every router:
owner, admin/superadmin, or a course collaborator (co-instructor).
"""
from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

ADMIN_ROLES = ("admin", "superadmin")


def is_collaborator(db: Session, course_id: int, user_id: int) -> bool:
    from app.models.course_ops import CourseCollaborator
    return (db.query(CourseCollaborator.id)
            .filter(CourseCollaborator.course_id == course_id, CourseCollaborator.user_id == user_id).first()) is not None


def can_edit(db: Session, course, user) -> bool:
    if course is None or user is None:
        return False
    if getattr(user, "role", None) in ADMIN_ROLES:
        return True
    if course.post_author == user.id:
        return True
    return is_collaborator(db, course.id, user.id)


def collaborated_course_ids(db: Session, user_id: int) -> List[int]:
    from app.models.course_ops import CourseCollaborator
    return [cid for (cid,) in db.query(CourseCollaborator.course_id).filter(CourseCollaborator.user_id == user_id).all()]
