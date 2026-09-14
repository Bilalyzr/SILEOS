"""
User Schemas - Pydantic models for user endpoints
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Dict, List, Optional, Any
from datetime import datetime

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    designation: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    profile_photo: Optional[str] = None
    cover_photo: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None

    @validator('phone')
    def validate_phone(cls, v):
        if v and len(v) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return v

class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: str
    role: str
    status: str
    first_name: str
    last_name: str
    phone: str
    description: str
    designation: str
    address: str
    city: str
    state: str
    country: str
    postal_code: str
    profile_photo: str
    cover_photo: str
    facebook: str
    twitter: str
    linkedin: str
    website: str
    joined_date: datetime

class InstructorApplicationRequest(BaseModel):
    bio: str
    expertise: List[str]
    experience: str
    education: List[Dict[str, str]]
    certifications: List[Dict[str, str]]
    social_links: Optional[Dict[str, str]] = None

    @validator('bio')
    def validate_bio(cls, v):
        if len(v) < 100:
            raise ValueError('Bio must be at least 100 characters')
        return v

    @validator('expertise')
    def validate_expertise(cls, v):
        if len(v) < 1:
            raise ValueError('At least one area of expertise is required')
        return v

class InstructorProfileResponse(BaseModel):
    id: int
    user_id: int
    bio: str
    expertise: List[str]
    experience: str
    education: List[Dict[str, str]]
    certifications: List[Dict[str, str]]
    social_links: Dict[str, str]
    status: str
    rating: Optional[float]
    total_students: int
    total_courses: int
    created_at: datetime

class UserStatsResponse(BaseModel):
    role: str
    # Student stats
    enrolled_courses: Optional[int] = None
    completed_courses: Optional[int] = None
    in_progress_courses: Optional[int] = None
    certificates_earned: Optional[int] = None
    total_learning_time: Optional[int] = None
    # Instructor stats
    total_courses: Optional[int] = None
    published_courses: Optional[int] = None
    draft_courses: Optional[int] = None
    total_students: Optional[int] = None
    total_revenue: Optional[float] = None
    # Admin stats
    total_users: Optional[int] = None
    total_enrollments: Optional[int] = None
    active_users: Optional[int] = None