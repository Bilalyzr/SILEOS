"""
Checkout Router - SashaInfinity LMS API
Handles checkout operations for courses
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.services.auth_service import AuthService

router = APIRouter()

@router.get("/course-info")
async def get_course_checkout_info(
    course_id: int = Query(..., description="Course ID"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user)
):
    """
    Get checkout information for a course
    Returns course details needed for checkout page (price, is_enrolled, etc.)
    """
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check if user is enrolled
    is_enrolled = False
    if current_user:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == current_user.id
        ).first()
        is_enrolled = enrollment is not None and enrollment.enrollment_status not in ['cancelled', 'suspended']

    return {
        "course_id": course.id,
        "title": course.post_title,
        "thumbnail": course.course_thumbnail,
        "price": float(course.course_price) if course.course_price else 0,
        # align with pricing.is_on_sale() after merge
        "sale_price": float(course.course_sale_price) if course.course_sale_price and 0 < course.course_sale_price < (course.course_price or 0) else None,
        "is_free": course.course_price == 0,
        "level": course.course_level,
        "duration": course.course_duration,
        "is_enrolled": is_enrolled,
        "instructor": {
            "id": course.instructor.id if course.instructor else None,
            "name": course.instructor.display_name if course.instructor else "Unknown"
        } if course.instructor else None
    }
