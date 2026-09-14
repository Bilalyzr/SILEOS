"""Instructor growth tools (roadmap R6): co-instructors.

A collaborator can edit a course exactly like its owner (curriculum,
quizzes, assignments, studio settings, live classes, gradebook) — the single
rule lives in services/course_access.can_edit(). Ownership (post_author),
revenue and deletion stay with the owner.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class CourseCollaborator(Base):
    __tablename__ = "course_collaborators"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_course_collaborator"),)

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="co_instructor")
    added_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
