"""
Pydantic v2 schemas for SS3 company module.
"""
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Company signup / setup ----------

class CompanySignupRequest(BaseModel):
    """Self-serve signup — creates User(role='company') + Company(is_approved=False)."""
    name: str = Field(..., min_length=2, max_length=200)
    contact_email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    contact_phone: Optional[str] = Field(default="", max_length=30)
    website: Optional[str] = Field(default="", max_length=255)
    industry: Optional[str] = Field(default="", max_length=100)
    team_size: Optional[str] = Field(default="", max_length=50)
    description: Optional[str] = Field(default="", max_length=5000)


class CompanyAdminInviteRequest(BaseModel):
    """Admin pre-creates and pre-approves; company finishes via emailed setup link."""
    name: str = Field(..., min_length=2, max_length=200)
    contact_email: EmailStr
    contact_phone: Optional[str] = Field(default="", max_length=30)
    website: Optional[str] = Field(default="", max_length=255)
    industry: Optional[str] = Field(default="", max_length=100)
    team_size: Optional[str] = Field(default="", max_length=50)
    description: Optional[str] = Field(default="", max_length=5000)


class CompanyCompleteSetupRequest(BaseModel):
    token: str = Field(..., min_length=10)
    password: str = Field(..., min_length=8, max_length=128)


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=30)
    website: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    team_size: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=5000)
    logo_url: Optional[str] = Field(None, max_length=500)


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: int
    name: str
    slug: str
    website: str = ""
    industry: str = ""
    team_size: str = ""
    description: str = ""
    logo_url: str = ""
    contact_email: str
    contact_phone: str = ""
    is_approved: bool
    approval_source: str
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanyRejectRequest(BaseModel):
    reason: Optional[str] = Field(default="", max_length=2000)


# ---------- Interest flow ----------

class InterestCreateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class InterestCompanyView(BaseModel):
    """Row surfaced to the *company* (includes candidate contact once accepted)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_user_id: int
    candidate_name: Optional[str] = None
    status: str
    company_message: str = ""
    responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # revealed only when status == 'accepted'
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None


class InterestCandidateView(BaseModel):
    """Row surfaced to the *candidate* (student's internship inbox)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    company_name: Optional[str] = None
    company_logo_url: Optional[str] = None
    company_industry: Optional[str] = None
    company_website: Optional[str] = None
    status: str
    company_message: str = ""
    responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ---------- Candidate browse (SS3 reads SS2) ----------

class CandidateBrowseItem(BaseModel):
    """Thin candidate card shown in the company dashboard browse list."""
    user_id: int
    display_name: str
    headline: Optional[str] = None
    skills: List[str] = []
    preferred_roles: List[str] = []
    availability_date: Optional[date] = None
    resume_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class CandidateBrowseResponse(BaseModel):
    items: List[CandidateBrowseItem]
    total: int
    page: int
    page_size: int
