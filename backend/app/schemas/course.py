"""
Course Schemas - Pydantic models for course endpoints
"""

from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import math

from app.core.course_types import normalize_course_type
from app.core.course_links import validate_course_slug


def _validated_course_type(cls, v):
    """Normalize to the canonical lowercase type; None/blank stays None.

    Blank means "not chosen yet" (create applies the default, update leaves
    the row unchanged). Anything outside the three types becomes a 422.
    """
    return normalize_course_type(v)

class CourseBase(BaseModel):
    title: str
    description: str
    content: Optional[str] = ""
    excerpt: Optional[str] = ""
    thumbnail: Optional[str] = ""
    intro_video: Optional[str] = ""
    price: float = 0
    sale_price: Optional[float] = None
    level: str = "beginner"
    category: str
    duration: Optional[int] = 0
    language: Optional[str] = "English"
    requirements: Optional[List[str]] = []
    benefits: Optional[List[str]] = []
    faq: Optional[List[Dict[str, str]]] = []
    num_offline_workshops: Optional[int] = 0
    num_hours: Optional[int] = 0
    institution: Optional[str] = ""

    @validator('level')
    def validate_level(cls, v):
        allowed_levels = ['beginner', 'intermediate', 'advanced', 'expert']
        if v not in allowed_levels:
            raise ValueError(f'Level must be one of: {allowed_levels}')
        return v

    @validator('price', 'sale_price')
    def validate_price(cls, v):
        if v is not None and (not math.isfinite(v) or v < 0):
            raise ValueError('Price must be finite and non-negative')
        return v

class CourseCreate(CourseBase):
    slug: Optional[str] = None
    _slug_check = validator('slug', allow_reuse=True)(validate_course_slug)
    instructor_id: Optional[int] = None  # Admin only
    certificate_id: Optional[int] = None  # instructor-chosen certificate template
    status: Optional[str] = None  # publish/draft/pending/private (falls back by role)
    target_audience: Optional[str] = None
    course_type: Optional[str] = None

    _course_type_check = validator('course_type', allow_reuse=True)(_validated_course_type)

class CourseUpdate(BaseModel):
    slug: Optional[str] = None
    _slug_check = validator('slug', allow_reuse=True)(validate_course_slug)
    sections_meta: Optional[str] = None  # JSON sections structure
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    thumbnail: Optional[str] = None
    intro_video: Optional[str] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None

    @validator('price', 'sale_price')
    def validate_price(cls, v):
        if v is not None and (not math.isfinite(v) or v < 0):
            raise ValueError('Price must be finite and non-negative')
        return v
    level: Optional[str] = None
    category: Optional[str] = None
    duration: Optional[int] = None
    language: Optional[str] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    faq: Optional[List[Dict[str, str]]] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    # The edit-course form sends these two; without them Pydantic silently drops
    # the values and the fields never persist (target audience / course type).
    target_audience: Optional[str] = None
    course_type: Optional[str] = None
    num_offline_workshops: Optional[int] = None
    num_hours: Optional[int] = None
    institution: Optional[str] = None
    certificate_id: Optional[int] = None  # instructor-chosen certificate template

    _course_type_check = validator('course_type', allow_reuse=True)(_validated_course_type)

class InstructorInfo(BaseModel):
    id: int
    name: str
    avatar: Optional[str] = None

class CourseStats(BaseModel):
    lessons: int
    quizzes: int
    duration: int
    students: int
    video_views: Optional[int] = 0

class CourseListResponse(BaseModel):
    id: int
    slug: Optional[str] = None
    title: str
    description: str
    featured_image: str
    price: float
    sale_price: Optional[float] = None
    level: str
    category: str
    course_type: str = ""
    instructor: InstructorInfo
    stats: CourseStats
    rating: float
    is_enrolled: bool = False
    num_offline_workshops: Optional[int] = 0
    num_hours: Optional[int] = 0
    institution: Optional[str] = ""
    created_at: datetime
    updated_at: datetime

class PaginatedCoursesResponse(BaseModel):
    courses: List[CourseListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class LessonInfo(BaseModel):
    attachment_url: Optional[str] = None
    id: int
    title: str
    content: Optional[str] = ""
    duration: Optional[int]
    video_duration: Optional[int] = 0
    video_url: Optional[str] = ""
    is_preview: bool
    is_locked: bool = False   # public-preview lock (2026-09-05): media stripped when True
    is_public_preview: Optional[bool] = None
    order: int
    course_id: int
    lesson_video: Optional[str] = ""
    lesson_content: Optional[str] = ""
    lesson_title: Optional[str] = ""
    youtube_url: Optional[str] = ""
    created_at: Optional[datetime] = None
    post_date: Optional[datetime] = None
    lesson_content_type: Optional[str] = "video"
    h5p_content_id: Optional[int] = None
    # Opaque H5PContent.public_id resolved server-side from h5p_content_id
    # (plan Task 5) — the only content handle the H5P frontend/API accept
    # (app/routers/h5p.py routes by public_id, never the integer PK). None
    # for video lessons or when h5p_content_id doesn't resolve.
    h5p_public_id: Optional[str] = None
    # Learning-games support (plan Task 6, spec §3). "game"-typed lessons
    # reference a published Game the caller owns via game_id; game_title is
    # resolved server-side (mirrors h5p_public_id) for display without a
    # second round trip.
    game_id: Optional[int] = None
    geogebra_applet_id: Optional[int] = None
    three_d_model_id: Optional[int] = None
    virtual_lab_sim: Optional[str] = None
    game_title: Optional[str] = None

class QuizInfo(BaseModel):
    id: int
    title: str
    questions_count: int
    time_limit: Optional[int]
    created_at: datetime

class AssignmentInfo(BaseModel):
    id: int
    title: str
    description: Optional[str]
    total_points: int
    created_at: datetime

class CourseResponse(BaseModel):
    id: int
    slug: Optional[str] = None
    title: str
    description: str
    content: str
    excerpt: str
    thumbnail: str
    intro_video: str
    price: float
    sale_price: Optional[float] = None
    level: str
    category: str
    course_type: str = ""
    duration: int
    language: str
    requirements: List[str]
    benefits: List[str]
    faq: List[Dict[str, str]]
    instructor: InstructorInfo
    lessons: List[LessonInfo]
    quizzes: List[QuizInfo]
    assignments: List[AssignmentInfo]
    stats: CourseStats
    rating: float
    is_enrolled: bool
    enrollment_date: Optional[datetime]
    progress: Optional[float]
    status: str
    sections_meta: Optional[str] = None
    num_offline_workshops: Optional[int] = 0
    num_hours: Optional[int] = 0
    institution: Optional[str] = ""
    certificate_id: Optional[int] = None  # instructor-chosen certificate template
    created_at: datetime
    updated_at: datetime

# Lesson Schemas

LESSON_CONTENT_TYPES = {"video", "h5p", "game", "geogebra", "three_d", "virtual_lab"}


class LessonBase(BaseModel):
    title: str
    content: Optional[str] = ""
    video_url: Optional[str] = ""
    video_duration: Optional[int] = 0
    is_preview: bool = False
    youtube_url: Optional[str] = ""
    # H5P interactive-content support (plan Task 4, spec B5/B7). "video"
    # (default) keeps existing behaviour; "h5p" requires h5p_content_id to
    # reference a `ready` H5PContent row the caller owns (enforced in the
    # courses.py router, which needs a DB lookup this schema layer can't
    # do — this validator only constrains the literal string value).
    lesson_content_type: Optional[str] = "video"
    h5p_content_id: Optional[int] = None
    game_id: Optional[int] = None
    geogebra_applet_id: Optional[int] = None
    three_d_model_id: Optional[int] = None
    virtual_lab_sim: Optional[str] = None

    @validator("lesson_content_type")
    def _validate_content_type(cls, v):
        if v is not None and v not in LESSON_CONTENT_TYPES:
            raise ValueError(f"lesson_content_type must be one of {sorted(LESSON_CONTENT_TYPES)}")
        return v

class LessonCreate(LessonBase):
    pass

class LessonUpdate(BaseModel):
    menu_order: Optional[int] = None
    attachment_url: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    youtube_url: Optional[str] = None
    video_duration: Optional[int] = None
    is_preview: Optional[bool] = None
    order: Optional[int] = None
    lesson_content_type: Optional[str] = None
    h5p_content_id: Optional[int] = None
    game_id: Optional[int] = None
    geogebra_applet_id: Optional[int] = None
    three_d_model_id: Optional[int] = None
    virtual_lab_sim: Optional[str] = None

    @validator("lesson_content_type")
    def _validate_content_type(cls, v):
        if v is not None and v not in LESSON_CONTENT_TYPES:
            raise ValueError(f"lesson_content_type must be one of {sorted(LESSON_CONTENT_TYPES)}")
        return v

class LessonResponse(BaseModel):
    id: int
    title: str
    content: str
    video_url: str
    video_duration: Optional[int]
    is_preview: bool
    is_locked: bool = False   # public-preview lock (2026-09-05): media stripped when True
    is_public_preview: Optional[bool] = None
    order: int
    course_id: int
    created_at: datetime
    updated_at: datetime
    youtube_url: Optional[str] = ""
    lesson_content_type: Optional[str] = "video"
    h5p_content_id: Optional[int] = None
    game_id: Optional[int] = None
    geogebra_applet_id: Optional[int] = None
    three_d_model_id: Optional[int] = None
    virtual_lab_sim: Optional[str] = None

# Enrollment Schemas

class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    student_id: int
    status: str
    enrolled_at: datetime
    progress: float

class CourseProgressResponse(BaseModel):
    course_id: int
    student_id: int
    total_lessons: int
    completed_lessons: int
    total_quizzes: int
    completed_quizzes: int
    overall_progress: float
    last_accessed: Optional[datetime]
    completion_date: Optional[datetime]
    certificate_earned: bool
    total_assignments: int = 0
    completed_assignments: int = 0
    completed_lesson_ids: List[int] = []
    passed_quiz_ids: List[int] = []
    completed_assignment_ids: List[int] = []
    enrolled: bool = True
