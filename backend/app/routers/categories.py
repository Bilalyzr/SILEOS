"""
Categories Router - SashaInfinity LMS API
Handles course category endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.course import Course, CourseCategory, CourseTag
from app.models.user import User
from app.services.course_service import CourseService

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
def get_categories(db: Session = Depends(get_db)):
    """Get all course categories"""
    categories = db.query(CourseCategory).order_by(CourseCategory.term_order, CourseCategory.name).all()
    result = []
    for cat in categories:
        result.append({
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "parent_id": cat.parent_id,
        })
    return result


@router.get("/{category_id}/courses")
def get_courses_by_category(
    category_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get courses by category"""
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get courses for this category
    query = db.query(Course).filter(
        Course.post_status == "published",
        Course.categories.any(CourseCategory.id == category_id)
    )

    total = query.count()
    courses = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "courses": [CourseService.serialize_course(c, db) for c in courses],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/tags", response_model=List[Dict[str, Any]])
def get_tags(db: Session = Depends(get_db)):
    """Get all course tags"""
    tags = db.query(CourseTag).order_by(CourseTag.name).all()
    result = []
    for tag in tags:
        result.append({
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
        })
    return result


@router.get("/instructors", response_model=List[Dict[str, Any]])
def get_instructors(db: Session = Depends(get_db)):
    """Get all instructors"""
    from sqlalchemy import func
    
    # Get users with instructor role
    instructors = db.query(User).filter(
        User.role.in_(["instructor", "admin", "superadmin"])
    ).order_by(User.display_name).all()
    
    result = []
    for instructor in instructors:
        # Count published courses for this instructor
        course_count = db.query(func.count(Course.id)).filter(
            Course.post_author == instructor.id,
            Course.post_status == "published"
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
