"""
Admin Schemas - Pydantic models for admin endpoints
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class UserStats(BaseModel):
    total_users: int
    active_users: int
    students: int                   # active + verified
    students_total: Optional[int] = None       # all with role=student
    students_unverified: Optional[int] = None  # role=student and !is_verified
    instructors: int
    companies: Optional[int] = 0
    spocs: Optional[int] = 0
    new_users_count: int  # Generic field for period-filtered new users

class CourseStats(BaseModel):
    total_courses: int
    published_courses: int
    draft_courses: int
    avg_rating: float
    recent_courses: List[Dict[str, Any]] = []

class EnrollmentStats(BaseModel):
    total_enrollments: int
    completed_enrollments: int
    completion_rate: float
    new_enrollments_count: int  # Generic field for period-filtered new enrollments
    recent_enrollments: List[Dict[str, Any]] = []

class RevenueStats(BaseModel):
    total_revenue: float
    monthly_revenue: float = 0  # Current calendar month to date (IST)
    monthly_revenue_label: str = ""  # e.g. "July 2026" — the month above
    avg_course_price: float
    revenue_period: float  # Generic field for period-filtered revenue

class AdminStatsResponse(BaseModel):
    user_stats: UserStats
    course_stats: CourseStats
    enrollment_stats: EnrollmentStats
    revenue_stats: RevenueStats

class UserManagementResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: str
    role: str
    status: str
    is_verified: Optional[bool] = None
    joined_date: datetime
    last_login: Optional[datetime]
    total_courses: int
    profile_complete: bool
    # Issue 5: surface phone in the admin user list/details so admins don't
    # have to open each row to find contact info.
    phone: Optional[str] = ""

class CourseManagementResponse(BaseModel):
    id: int
    title: str
    instructor_name: str
    status: str
    price: float
    enrolled_students: int
    rating: float
    # Total times any lesson video in this course has been viewed
    # (Issue 1: video view count per course). Defaults to 0 for legacy rows.
    video_view_count: int = 0
    # Course banner image (the same asset the public course cards use). Empty
    # string when the course has no thumbnail so the UI can fall back.
    banner_url: str = ""
    # Optional: seeded/imported rows can have NULL timestamps; a strict
    # (non-optional) datetime here makes Pydantic 500 the whole list response.
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class RevenueStatsResponse(BaseModel):
    period: str
    total_revenue: float
    total_transactions: int
    avg_transaction_value: float
    top_courses: List[Dict[str, Any]]

class SystemHealthResponse(BaseModel):
    database_status: str
    total_users: int
    total_courses: int
    recent_activity_24h: Dict[str, int]
    server_time: datetime
    uptime: str

class UpdateUserRoleRequest(BaseModel):
    role: str

# Blog Management Schemas

class BlogManagementResponse(BaseModel):
    """Response model for admin blog list endpoint"""
    id: int
    title: str
    slug: str
    status: str
    category: Optional[str] = None
    author_name: str
    view_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class BlogUpdateRequest(BaseModel):
    """Request model for updating a blog post"""
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None  # DRAFT, PUBLISHED


class BlogStatusUpdateRequest(BaseModel):
    """Request model for updating blog post status"""
    status: str  # DRAFT, PUBLISHED


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations"""
    blog_ids: List[int]