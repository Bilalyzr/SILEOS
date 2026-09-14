"""
Lesson read endpoints for mobile clients.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.course import LessonResponse
from app.services.auth_service import AuthService
from app.services.course_service import CourseService

router = APIRouter()
PUBLISHED_STATUSES = ["publish", "published", "PUBLISH", "PUBLISHED"]


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user),
):
    """
    Get a lesson by id.

    Public users can read preview lessons on published courses. Enrolled
    students, course owners, and admins can read full lesson content.
    """
    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.course))
        .filter(Lesson.id == lesson_id)
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    course = lesson.course or db.query(Course).filter(Course.id == lesson.post_parent).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    if course.post_status not in PUBLISHED_STATUSES:
        is_owner_or_admin = bool(
            current_user
            and (current_user.role == "admin" or current_user.id == course.post_author)
        )
        if not is_owner_or_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Course not available",
            )

    has_full_access = bool(lesson.lesson_preview)
    if current_user:
        has_full_access = has_full_access or current_user.role == "admin" or current_user.id == course.post_author
        if not has_full_access:
            enrollment = (
                db.query(Enrollment)
                .filter(
                    Enrollment.course_id == course.id,
                    Enrollment.user_id == current_user.id,
                )
                .first()
            )
            has_full_access = bool(
                enrollment
                and enrollment.enrollment_status not in ("cancelled", "suspended")
            )

    if not has_full_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in this course to view this lesson",
        )

    return CourseService.format_lesson_response(lesson)
