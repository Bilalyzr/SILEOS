"""
Candidate schemas — SS2. Pydantic v2.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CandidateProfileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_visible: bool = False
    resume_url: Optional[str] = ""
    bio: Optional[str] = ""
    skills: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    availability_date: Optional[date] = None
    linkedin_url: Optional[str] = ""
    github_url: Optional[str] = ""
    portfolio_url: Optional[str] = ""


class CandidateProfileUpdate(BaseModel):
    """Partial update — every field optional."""
    model_config = ConfigDict(from_attributes=True)

    resume_url: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[List[str]] = None
    preferred_roles: Optional[List[str]] = None
    availability_date: Optional[date] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    is_visible: Optional[bool] = None


class VisibilityToggle(BaseModel):
    is_visible: bool


class CandidateEligibilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    source: str
    eligible: bool
    reason: Optional[str] = ""
    decided_at: Optional[datetime] = None
    cohort_id: Optional[int] = None


class CandidateProfileOut(CandidateProfileBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completeness: int = 0
    eligibility: Optional[CandidateEligibilityOut] = None


class CandidateSummary(BaseModel):
    """Compact view returned in /browse."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    display_name: str
    bio: Optional[str] = ""
    skills: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    availability_date: Optional[date] = None
    linkedin_url: Optional[str] = ""
    github_url: Optional[str] = ""
    portfolio_url: Optional[str] = ""
    eligibility_source: Optional[str] = None


class CandidateBrowseResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CandidateSummary]


class CandidateDetailResponse(CandidateSummary):
    resume_url: Optional[str] = ""
    # Email/phone are NOT exposed on the detail view — they are only
    # revealed after an accepted CompanyInterest (SS3).
