"""
Instructor Review Router - Private feedback from students to instructors
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.instructor_review import InstructorReview
from app.services.auth_service import AuthService
from app.schemas.instructor_review import (
    InstructorReviewCreate,
    InstructorReviewResponse,
    InstructorResponseCreate
)

router = APIRouter()


@router.post("/", response_model=InstructorReviewResponse)
async def create_instructor_review(
    review_data: InstructorReviewCreate,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a private review for an instructor (student only)
    """
    # Check if user is enrolled in the course
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == review_data.course_id,
        Enrollment.user_id == current_user.id
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in this course to review the instructor"
        )

    # Get course and instructor
    course = db.query(Course).filter(Course.id == review_data.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    instructor = db.query(User).filter(User.id == course.post_author).first()
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found"
        )

    # Check if student has already reviewed this instructor for this course
    existing_review = db.query(InstructorReview).filter(
        InstructorReview.course_id == review_data.course_id,
        InstructorReview.student_id == current_user.id
    ).first()

    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted a review for this instructor"
        )

    # Create new review
    new_review = InstructorReview(
        course_id=review_data.course_id,
        instructor_id=instructor.id,
        student_id=current_user.id,
        rating=review_data.rating,
        review_title=review_data.review_title or "",
        review_content=review_data.review_content,
        is_private=True,
        is_read=False
    )

    db.add(new_review)
    db.commit()
    db.refresh(new_review)

    return {
        "id": new_review.id,
        "course_id": new_review.course_id,
        "course_title": course.post_title,
        "instructor_id": instructor.id,
        "instructor_name": instructor.display_name,
        "student_id": current_user.id,
        "student_name": current_user.display_name,
        "rating": new_review.rating,
        "review_title": new_review.review_title,
        "review_content": new_review.review_content,
        "is_read": new_review.is_read,
        "instructor_response": new_review.instructor_response,
        "response_date": new_review.response_date,
        "created_at": new_review.created_at,
        "updated_at": new_review.updated_at
    }


@router.get("/my-reviews", response_model=List[InstructorReviewResponse])
async def get_my_reviews(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all reviews submitted by the current student
    """
    reviews = db.query(InstructorReview).filter(
        InstructorReview.student_id == current_user.id
    ).order_by(InstructorReview.created_at.desc()).all()

    result = []
    for review in reviews:
        course = db.query(Course).filter(Course.id == review.course_id).first()
        instructor = db.query(User).filter(User.id == review.instructor_id).first()

        if course and instructor:
            result.append({
                "id": review.id,
                "course_id": review.course_id,
                "course_title": course.post_title,
                "instructor_id": instructor.id,
                "instructor_name": instructor.display_name,
                "student_id": current_user.id,
                "student_name": current_user.display_name,
                "rating": review.rating,
                "review_title": review.review_title,
                "review_content": review.review_content,
                "is_read": review.is_read,
                "instructor_response": review.instructor_response,
                "response_date": review.response_date,
                "created_at": review.created_at,
                "updated_at": review.updated_at
            })

    return result


@router.get("/instructor/received", response_model=List[InstructorReviewResponse])
async def get_instructor_reviews(
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db)
):
    """
    Get all reviews received by the current instructor
    """
    reviews = db.query(InstructorReview).filter(
        InstructorReview.instructor_id == current_user.id
    ).order_by(InstructorReview.created_at.desc()).all()

    result = []
    for review in reviews:
        course = db.query(Course).filter(Course.id == review.course_id).first()
        student = db.query(User).filter(User.id == review.student_id).first()

        if course and student:
            # Mark as read when instructor views it
            if not review.is_read:
                review.is_read = True
                db.commit()

            result.append({
                "id": review.id,
                "course_id": review.course_id,
                "course_title": course.post_title,
                "instructor_id": current_user.id,
                "instructor_name": current_user.display_name,
                "student_id": student.id,
                "student_name": student.display_name,
                "rating": review.rating,
                "review_title": review.review_title,
                "review_content": review.review_content,
                "is_read": review.is_read,
                "instructor_response": review.instructor_response,
                "response_date": review.response_date,
                "created_at": review.created_at,
                "updated_at": review.updated_at
            })

    return result


@router.post("/{review_id}/respond")
async def respond_to_review(
    review_id: int,
    response_data: InstructorResponseCreate,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db)
):
    """
    Instructor responds to a review
    """
    review = db.query(InstructorReview).filter(
        InstructorReview.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Check if the review is for the current instructor
    if review.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only respond to reviews addressed to you"
        )

    # Update the response
    review.instructor_response = response_data.response
    review.response_date = datetime.utcnow()
    review.is_read = True

    db.commit()
    db.refresh(review)

    return {
        "message": "Response submitted successfully",
        "review_id": review.id,
        "response": review.instructor_response,
        "response_date": review.response_date
    }


@router.get("/{review_id}", response_model=InstructorReviewResponse)
async def get_review(
    review_id: int,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific review (student can view their own, instructor can view reviews for them)
    """
    review = db.query(InstructorReview).filter(
        InstructorReview.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Check permissions
    if review.student_id != current_user.id and review.instructor_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this review"
        )

    course = db.query(Course).filter(Course.id == review.course_id).first()
    instructor = db.query(User).filter(User.id == review.instructor_id).first()
    student = db.query(User).filter(User.id == review.student_id).first()

    if not course or not instructor or not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Related data not found"
        )

    return {
        "id": review.id,
        "course_id": review.course_id,
        "course_title": course.post_title,
        "instructor_id": instructor.id,
        "instructor_name": instructor.display_name,
        "student_id": student.id,
        "student_name": student.display_name,
        "rating": review.rating,
        "review_title": review.review_title,
        "review_content": review.review_content,
        "is_read": review.is_read,
        "instructor_response": review.instructor_response,
        "response_date": review.response_date,
        "created_at": review.created_at,
        "updated_at": review.updated_at
    }


@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a review (student can delete their own reviews)
    """
    review = db.query(InstructorReview).filter(
        InstructorReview.id == review_id
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )

    # Only the student who created it or admin can delete
    if review.student_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews"
        )

    db.delete(review)
    db.commit()

    return {"message": "Review deleted successfully"}
