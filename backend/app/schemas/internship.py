"""
Internship Module Schemas
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class InternshipModeEnum(str, Enum):
    online = "online"
    offline = "offline"
    hybrid = "hybrid"


class InternshipStatusEnum(str, Enum):
    draft = "draft"
    published = "published"
    closed = "closed"
    completed = "completed"


class ApplicationStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    withdrawn = "withdrawn"


class AttendanceStatusEnum(str, Enum):
    present = "present"
    absent = "absent"
    half_day = "half_day"
    leave = "leave"


class TaskStatusEnum(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    submitted = "submitted"
    completed = "completed"
    revision_required = "revision_required"


class TaskPriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ============================================================
# INSTITUTION SCHEMAS
# ============================================================
class InstitutionBase(BaseModel):
    name: str
    logo: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    verified: Optional[bool] = None
    is_active: Optional[bool] = None


class InstitutionResponse(InstitutionBase):
    id: int
    verified: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# SPOC SCHEMAS
# ============================================================
class SpocBase(BaseModel):
    name: str
    designation: Optional[str] = None
    email: str
    phone: Optional[str] = None
    department: Optional[str] = None
    is_primary: bool = False


class SpocCreate(SpocBase):
    institution_id: int


class SpocUpdate(BaseModel):
    name: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class SpocResponse(SpocBase):
    id: int
    institution_id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# INTERNSHIP SCHEMAS
# ============================================================
class InternshipBase(BaseModel):
    title: str
    topic: Optional[str] = None
    description: Optional[str] = None
    featured_image: Optional[str] = None
    mode: InternshipModeEnum = InternshipModeEnum.online
    location: Optional[str] = None
    duration_weeks: int = 4
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    application_deadline: Optional[date] = None
    is_paid: bool = False
    amount: float = 0.0
    max_students: int = 30
    institution_id: Optional[int] = None
    spoc_id: Optional[int] = None
    requirements: Optional[str] = None
    skills_required: Optional[str] = None
    benefits: Optional[str] = None


class InternshipCreate(InternshipBase):
    pass


class InternshipUpdate(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    description: Optional[str] = None
    featured_image: Optional[str] = None
    mode: Optional[InternshipModeEnum] = None
    location: Optional[str] = None
    duration_weeks: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    application_deadline: Optional[date] = None
    is_paid: Optional[bool] = None
    amount: Optional[float] = None
    max_students: Optional[int] = None
    institution_id: Optional[int] = None
    spoc_id: Optional[int] = None
    status: Optional[InternshipStatusEnum] = None
    requirements: Optional[str] = None
    skills_required: Optional[str] = None
    benefits: Optional[str] = None


class InternshipResponse(InternshipBase):
    id: int
    slug: str
    status: InternshipStatusEnum
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    institution: Optional[InstitutionResponse] = None
    spoc: Optional[SpocResponse] = None
    application_count: Optional[int] = 0
    enrollment_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


# ============================================================
# APPLICATION SCHEMAS
# ============================================================
class ApplicationCreate(BaseModel):
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    internship_id: int
    student_id: int
    cover_letter: Optional[str]
    resume_url: Optional[str]
    status: ApplicationStatusEnum
    application_date: datetime
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    internship_title: Optional[str] = None
    
    class Config:
        from_attributes = True


class ApplicationReview(BaseModel):
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None


# ============================================================
# ENROLLMENT SCHEMAS
# ============================================================
class EnrollmentResponse(BaseModel):
    id: int
    internship_id: int
    student_id: int
    enrolled_date: datetime
    completion_date: Optional[datetime]
    status: str
    progress_percentage: float
    total_attendance_days: int
    tasks_completed: int
    tasks_total: int
    student_name: Optional[str] = None
    internship_title: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============================================================
# ATTENDANCE SCHEMAS
# ============================================================
class AttendanceCheckIn(BaseModel):
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: int
    enrollment_id: int
    date: date
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    status: AttendanceStatusEnum
    notes: Optional[str]
    verified_by_spoc: bool
    
    class Config:
        from_attributes = True


# ============================================================
# TASK SCHEMAS
# ============================================================
class TaskCreate(BaseModel):
    internship_id: int
    enrollment_id: Optional[int] = None
    assigned_to: Optional[int] = None
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: TaskPriorityEnum = TaskPriorityEnum.medium


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[TaskPriorityEnum] = None
    status: Optional[TaskStatusEnum] = None
    submission_url: Optional[str] = None
    submission_notes: Optional[str] = None
    spoc_feedback: Optional[str] = None
    grade: Optional[float] = None


class TaskResponse(BaseModel):
    id: int
    internship_id: int
    enrollment_id: Optional[int]
    assigned_to: Optional[int]
    title: str
    description: Optional[str]
    deadline: Optional[datetime]
    priority: TaskPriorityEnum
    status: TaskStatusEnum
    submission_url: Optional[str]
    submission_notes: Optional[str]
    submitted_at: Optional[datetime]
    spoc_feedback: Optional[str]
    grade: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# STATS SCHEMAS
# ============================================================
class InternshipStats(BaseModel):
    total: int
    published: int
    drafts: int
    closed: int
    completed: int
    total_applications: int
    total_enrollments: int
    total_institutions: int
