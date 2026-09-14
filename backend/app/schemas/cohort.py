"""Pydantic v2 schemas for SS1 — cohorts module."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- College ----------

class CollegeBase(BaseModel):
    name: str
    slug: Optional[str] = None
    city: Optional[str] = ""
    state: Optional[str] = ""
    contact_name: Optional[str] = ""
    contact_email: Optional[str] = ""


class CollegeCreate(CollegeBase):
    pass


class CollegeUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None


class CollegeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    city: str
    state: str
    contact_name: str
    contact_email: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ---------- ReferralCode ----------

class ReferralCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cohort_id: int
    code: str
    max_uses: int
    used_count: int
    expires_at: Optional[datetime] = None
    created_at: datetime


# ---------- Cohort ----------

class CohortBase(BaseModel):
    college_id: int
    course_id: int
    spoc_user_id: int
    name: str
    slug: Optional[str] = None
    max_students: int = 0
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None
    is_active: bool = True


class CohortCreate(CohortBase):
    referral_max_uses: int = Field(default=100, ge=1)
    referral_expires_at: Optional[datetime] = None


class CohortUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    college_id: Optional[int] = None
    course_id: Optional[int] = None
    spoc_user_id: Optional[int] = None
    max_students: Optional[int] = None
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None
    is_active: Optional[bool] = None
    # Per-cohort seat price override (e.g. college-negotiated pricing).
    # Explicit null clears the override back to the course's normal price;
    # omitting the field leaves it untouched (handler uses exclude_unset).
    seat_price: Optional[float] = Field(default=None, gt=0)


class CohortOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # college_id / course_id are nullable in the DB model (internship-spawned
    # cohorts have no college or course). A previous non-Optional schema
    # caused /admin/cohorts to 500 on Pydantic validation when any such
    # cohort existed.
    college_id: Optional[int] = None
    course_id: Optional[int] = None
    spoc_user_id: int
    name: str
    slug: str
    max_students: int
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None
    is_active: bool
    seat_price: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    referral_code: Optional[ReferralCodeOut] = None


# ---------- Roster / task stats ----------

class RosterRow(BaseModel):
    user_id: int
    display_name: str
    email: str
    joined_at: datetime
    active_today: bool  # activity-derived from LessonProgress / QuizAttempt


class TaskStatsRow(BaseModel):
    user_id: int
    display_name: str
    completed_lessons: int
    quiz_attempts: int
    assignment_submissions: int


# ---------- Sessions / attendance ----------

SessionType = Literal["lecture", "lab", "evaluation", "other"]
AttendanceStatus = Literal["present", "absent", "late", "excused"]


class SessionBase(BaseModel):
    scheduled_at: datetime
    duration_minutes: int = 60
    topic: str = ""
    session_type: SessionType = "lecture"


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    topic: Optional[str] = None
    session_type: Optional[SessionType] = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cohort_id: int
    scheduled_at: datetime
    duration_minutes: int
    topic: str
    session_type: str
    created_by: Optional[int] = None
    created_at: datetime


class AttendanceEntry(BaseModel):
    user_id: int
    status: AttendanceStatus
    notes: Optional[str] = ""


class BulkAttendanceRequest(BaseModel):
    entries: List[AttendanceEntry]


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    user_id: int
    status: str
    notes: str
    marked_by: Optional[int] = None
    marked_at: Optional[datetime] = None


# ---------- Eligibility toggle (SS2 handoff) ----------

class EligibilityToggleRequest(BaseModel):
    eligible: bool
    reason: Optional[str] = ""


class EligibilityToggleOut(BaseModel):
    user_id: int
    eligible: bool
    source: str
    cohort_id: Optional[int] = None
    decided_by: Optional[int] = None
    reason: str = ""
