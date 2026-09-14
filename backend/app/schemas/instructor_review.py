"""
Instructor Review Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InstructorReviewCreate(BaseModel):
    """Schema for creating a new instructor review"""
    course_id: int = Field(..., description="ID of the course")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    review_title: Optional[str] = Field(None, max_length=255, description="Review title")
    review_content: str = Field(..., min_length=10, description="Review content (min 10 characters)")


class InstructorReviewResponse(BaseModel):
    """Schema for instructor review response"""
    id: int
    course_id: int
    course_title: str
    instructor_id: int
    instructor_name: str
    student_id: int
    student_name: str
    rating: int
    review_title: Optional[str]
    review_content: str
    is_read: bool
    instructor_response: Optional[str]
    response_date: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class InstructorResponseCreate(BaseModel):
    """Schema for instructor responding to a review"""
    response: str = Field(..., min_length=10, description="Instructor's response (min 10 characters)")
