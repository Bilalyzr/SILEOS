"""
Wishlist Router - SashaInfinity LMS API
Handles wishlist operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import WishlistItem
from app.services.auth_service import AuthService
from app.services.course_service import CourseService

router = APIRouter()

@router.get("/")
async def get_wishlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Get current user's wishlist
    """
    wishlist_items = db.query(WishlistItem).options(
        joinedload(WishlistItem.course).joinedload(Course.instructor).joinedload(User.profile)
    ).filter(
        WishlistItem.user_id == current_user.id
    ).all()

    courses = []
    for item in wishlist_items:
        if item.course:
            course_data = CourseService.format_course_response(item.course, False, None)
            course_data['wishlist_item_id'] = item.id
            courses.append(course_data)

    return {
        "courses": courses,
        "total": len(courses)
    }

@router.post("/")
async def add_to_wishlist(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Add a course to wishlist. Body: {"course_id": <int>}.
    """
    try:
        course_id = int(payload.get("course_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="course_id is required")

    # Check if course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check if already in wishlist
    existing = db.query(WishlistItem).filter(
        WishlistItem.user_id == current_user.id,
        WishlistItem.course_id == course_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course already in wishlist"
        )

    # Add to wishlist
    wishlist_item = WishlistItem(
        user_id=current_user.id,
        course_id=course_id
    )

    db.add(wishlist_item)
    db.commit()
    db.refresh(wishlist_item)

    return {
        "message": "Course added to wishlist",
        "wishlist_item_id": wishlist_item.id
    }

@router.delete("/{course_id}")
async def remove_from_wishlist(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Remove a course from wishlist
    """
    wishlist_item = db.query(WishlistItem).filter(
        WishlistItem.user_id == current_user.id,
        WishlistItem.course_id == course_id
    ).first()

    if not wishlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found in wishlist"
        )

    db.delete(wishlist_item)
    db.commit()

    return {
        "message": "Course removed from wishlist"
    }

@router.delete("/item/{wishlist_item_id}")
async def remove_wishlist_item(
    wishlist_item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Remove a wishlist item by its ID
    """
    wishlist_item = db.query(WishlistItem).filter(
        WishlistItem.id == wishlist_item_id,
        WishlistItem.user_id == current_user.id
    ).first()

    if not wishlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist item not found"
        )

    db.delete(wishlist_item)
    db.commit()

    return {
        "message": "Wishlist item removed successfully"
    }
