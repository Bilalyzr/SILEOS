"""Pydantic schemas for company dashboard v2."""
from datetime import datetime, date as DateType
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ---------- Managers ----------

class ManagerInviteRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)


class ManagerResponse(BaseModel):
    id: int
    user_id: int
    email: EmailStr
    name: str
    accepted_at: Optional[datetime] = None
    invited_at: datetime
    setup_token: Optional[str] = None

    class Config:
        from_attributes = True


class ManagerCompleteSetupRequest(BaseModel):
    token: str
    password: str = Field(min_length=6, max_length=200)


# ---------- Overview ----------

class OverviewResponse(BaseModel):
    active_interns: int
    active_internships: int
    week_attendance_pct: float
    pending_work_log_reviews: int
    today_present: int
    today_absent: int
    today_late: int
    today_excused: int
    today_not_marked: int
    activity: List[dict]


# ---------- Students ----------

class StudentListItem(BaseModel):
    user_id: int
    voucher_id: int
    name: str
    email: EmailStr
    internship_id: int
    internship_title: str
    progress_pct: float
    attendance_pct: float
    reporting_manager_user_id: Optional[int] = None
    reporting_manager_name: Optional[str] = None
    cert_status: str
    notes: str = ""
    internship_status: str = "active"
    # Candidate profile links
    resume_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    items: List[StudentListItem]
    total: int


class StudentPatchRequest(BaseModel):
    reporting_manager_user_id: Optional[int] = None
    notes: Optional[str] = None
    internship_status: Optional[str] = None


# ---------- Internships ----------

class CompanyInternshipItem(BaseModel):
    id: int
    title: str
    slug: str
    cover_image: Optional[str] = ""
    student_count: int
    avg_progress_pct: float
    spoc_name: Optional[str] = None

    class Config:
        from_attributes = True


class CompanyInternshipListResponse(BaseModel):
    items: List[CompanyInternshipItem]


# ---------- Attendance ----------

class AttendanceEntry(BaseModel):
    id: Optional[int] = None
    student_user_id: int
    internship_id: int
    date: DateType
    status: str
    hours_worked: float
    notes: str = ""


class AttendanceGridResponse(BaseModel):
    students: List[dict]
    dates: List[DateType]


class AttendanceUpsertRequest(BaseModel):
    entries: List[AttendanceEntry]


# ---------- Work Logs ----------

class WorkLogItem(BaseModel):
    id: int
    student_user_id: int
    student_name: str
    internship_id: int
    internship_title: str
    log_date: DateType
    content: str
    attachment_url: str = ""
    review_status: str
    reviewed_by_name: Optional[str] = None
    reviewer_comment: str = ""

    class Config:
        from_attributes = True


class WorkLogListResponse(BaseModel):
    items: List[WorkLogItem]
    total: int


class WorkLogReviewRequest(BaseModel):
    status: str  # approved|flagged
    comment: str = ""


# ---------- Announcements ----------

class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str
    internship_id: Optional[int] = None


class AnnouncementItem(BaseModel):
    id: int
    title: str
    body: str
    internship_id: Optional[int] = None
    internship_title: Optional[str] = None
    created_at: datetime
    created_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class AnnouncementListResponse(BaseModel):
    items: List[AnnouncementItem]


# ---------- Performance Reviews ----------

class PerformanceReviewCreateRequest(BaseModel):
    student_user_id: int
    internship_id: int
    rating: int = Field(ge=1, le=5)
    feedback: str = ""
    hire_recommendation: str = Field(default="maybe")  # yes|maybe|no


class PerformanceReviewItem(BaseModel):
    id: int
    company_id: int
    student_user_id: int
    student_name: str
    internship_id: int
    internship_title: str
    rating: int
    feedback: str
    hire_recommendation: str
    submitted_at: datetime

    class Config:
        from_attributes = True


# ---------- Internship Requests ----------

class InternshipRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    start_date: DateType
    end_date: DateType
    intern_count: int = Field(ge=1, default=1)
    description: str = ""


class InternshipRequestItem(BaseModel):
    id: int
    company_id: int
    company_name: str
    requested_by: int
    requester_name: str
    title: str
    start_date: DateType
    end_date: DateType
    intern_count: int
    description: str
    status: str
    rejection_reason: str = ""
    approved_internship_id: Optional[int] = None
    reviewed_by: Optional[int] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InternshipRequestListResponse(BaseModel):
    items: List[InternshipRequestItem]


class ApproveInternshipRequestRequest(BaseModel):
    spoc_user_id: int
    price: int = Field(ge=0)
    slug: Optional[str] = None


class RejectInternshipRequestRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)
