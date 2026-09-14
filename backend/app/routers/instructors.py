"""
Instructors Router - SashaInfinity LMS API
Handles instructor endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.course import Course
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
def get_instructors(db: Session = Depends(get_db)):
    """Get all instructors"""
    # Get users with instructor role
    instructors = db.query(User).filter(
        User.role.in_(["instructor", "admin", "superadmin"])
    ).order_by(User.display_name).all()

    result = []
    for instructor in instructors:
        # Count published courses for this instructor
        course_count = db.query(func.count(Course.id)).filter(
            Course.post_author == instructor.id,
            Course.post_status.in_(["publish", "published"])
        ).scalar()

        if course_count > 0:  # Only include instructors with published courses
            result.append({
                "id": instructor.id,
                "name": instructor.display_name or instructor.user_login,
                "avatar": instructor.profile.profile_photo if instructor.profile else None,
                "bio": instructor.profile.description if instructor.profile else None,
                "course_count": course_count,
            })

    return result
