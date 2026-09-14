"""
Candidate router — SS2 (mounted at /api/v1/candidates).
Owned by SS2 implementer.

Endpoints:
  GET  /me                     — own profile (self)
  PUT  /me                     — upsert own profile
  POST /me/visibility          — toggle is_visible
  GET  /browse                 — company-only, approved Company required
  GET  /{user_id}              — company-only detail (approved Company required)
"""
from __future__ import annotations

from typing import List, Optional, Tuple
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.models.user import User
from app.models.candidate import CandidateProfile, CandidateEligibility
from app.schemas.candidate import (
    CandidateProfileOut,
    CandidateProfileUpdate,
    CandidateEligibilityOut,
    VisibilityToggle,
    CandidateSummary,
    CandidateBrowseResponse,
    CandidateDetailResponse,
)
from app.services.auth_service import AuthService


router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _completeness(p: CandidateProfile) -> int:
    """Return a rough 0-100% completeness score. LinkedIn is required."""
    checks = [
        bool(p.resume_url),
        bool(p.bio and len(p.bio.strip()) >= 40),
        bool(p.skills and len(p.skills) >= 3),
        bool(p.preferred_roles and len(p.preferred_roles) >= 1),
        p.availability_date is not None,
        bool(p.linkedin_url),  # LinkedIn specifically required
    ]
    return int(round(100 * sum(1 for c in checks if c) / len(checks)))


def _get_or_create_profile(db: Session, user_id: int) -> CandidateProfile:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    if profile:
        return profile
    profile = CandidateProfile(user_id=user_id, is_visible=False, skills=[], preferred_roles=[])
    try:
        db.add(profile)
        db.commit()
        db.refresh(profile)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {e}")
    return profile


def _eligibility_for(db: Session, user_id: int) -> Optional[CandidateEligibility]:
    return (
        db.query(CandidateEligibility)
        .filter(CandidateEligibility.user_id == user_id)
        .first()
    )


def _serialize_profile(p: CandidateProfile, elig: Optional[CandidateEligibility]) -> CandidateProfileOut:
    data = CandidateProfileOut.model_validate(p, from_attributes=True).model_dump()
    data["completeness"] = _completeness(p)
    if elig is not None:
        data["eligibility"] = CandidateEligibilityOut.model_validate(elig, from_attributes=True).model_dump()
    return CandidateProfileOut(**data)


def _require_approved_company(current_user: User, db: Session) -> None:
    """
    Company role is already asserted by require_company. Additionally verify
    the caller's Company record has is_approved=True. SS3 owns models.company;
    if the module isn't importable yet (branch ordering), fall back to 503.
    """
    try:
        from app.models.company import Company  # type: ignore
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Company marketplace not available yet",
        )

    company = db.query(Company).filter(Company.owner_user_id == current_user.id).first()
    if not company or not getattr(company, "is_approved", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your company account is not approved yet",
        )


# ---------------------------------------------------------------------------
# Self endpoints
# ---------------------------------------------------------------------------

@router.get("/me", response_model=CandidateProfileOut)
def get_my_profile(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, current_user.id)
    elig = _eligibility_for(db, current_user.id)
    return _serialize_profile(profile, elig)


@router.put("/me", response_model=CandidateProfileOut)
def update_my_profile(
    payload: CandidateProfileUpdate,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, current_user.id)

    data = payload.model_dump(exclude_unset=True)

    # Validation: LinkedIn URL is required if user wants to be visible
    new_is_visible = data.get("is_visible", profile.is_visible)
    new_linkedin = data.get("linkedin_url", profile.linkedin_url)

    if new_is_visible and not new_linkedin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn URL is required to make your profile visible to companies"
        )

    # Validation: All three links must be unique (if provided)
    links = {
        "linkedin": data.get("linkedin_url", profile.linkedin_url) or "",
        "github": data.get("github_url", profile.github_url) or "",
        "portfolio": data.get("portfolio_url", profile.portfolio_url) or "",
    }
    non_empty_links = {k: v for k, v in links.items() if v.strip()}

    if len(non_empty_links) != len(set(non_empty_links.values())):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn, GitHub, and Portfolio URLs must be unique"
        )

    try:
        for key, value in data.items():
            setattr(profile, key, value)
        db.commit()
        db.refresh(profile)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {e}")

    return _serialize_profile(profile, _eligibility_for(db, current_user.id))


@router.post("/me/visibility", response_model=CandidateProfileOut)
def toggle_my_visibility(
    payload: VisibilityToggle,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, current_user.id)
    try:
        profile.is_visible = bool(payload.is_visible)
        db.commit()
        db.refresh(profile)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update visibility: {e}")
    return _serialize_profile(profile, _eligibility_for(db, current_user.id))


# ---------------------------------------------------------------------------
# Company-facing endpoints
# ---------------------------------------------------------------------------

@router.get("/browse", response_model=CandidateBrowseResponse)
def browse_candidates(
    skills: Optional[str] = Query(None, description="Comma-separated skills to match (any)"),
    roles: Optional[str] = Query(None, description="Comma-separated preferred roles to match (any)"),
    availability_before: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(AuthService.require_company),
    db: Session = Depends(get_db),
):
    _require_approved_company(current_user, db)

    q = (
        db.query(CandidateProfile, CandidateEligibility, User)
        .join(CandidateEligibility, CandidateEligibility.user_id == CandidateProfile.user_id)
        .join(User, User.id == CandidateProfile.user_id)
        .filter(CandidateProfile.is_visible.is_(True))
        .filter(CandidateEligibility.eligible.is_(True))
        .filter(User.is_active.is_(True))
    )

    if availability_before is not None:
        q = q.filter(
            and_(
                CandidateProfile.availability_date.isnot(None),
                CandidateProfile.availability_date <= availability_before,
            )
        )

    rows: List[Tuple[CandidateProfile, CandidateEligibility, User]] = q.all()

    # JSON-column filtering in Python (DB-agnostic; dataset is small).
    def _norm_list(v: Optional[str]) -> List[str]:
        return [s.strip().lower() for s in (v or "").split(",") if s.strip()]

    want_skills = _norm_list(skills)
    want_roles = _norm_list(roles)

    def matches(profile: CandidateProfile) -> bool:
        if want_skills:
            have = {str(x).lower() for x in (profile.skills or [])}
            if not any(s in have for s in want_skills):
                return False
        if want_roles:
            have = {str(x).lower() for x in (profile.preferred_roles or [])}
            if not any(r in have for r in want_roles):
                return False
        return True

    filtered = [r for r in rows if matches(r[0])]
    total = len(filtered)
    start = (page - 1) * page_size
    page_rows = filtered[start : start + page_size]

    items = [
        CandidateSummary(
            user_id=u.id,
            display_name=u.display_name,
            bio=p.bio or "",
            skills=list(p.skills or []),
            preferred_roles=list(p.preferred_roles or []),
            availability_date=p.availability_date,
            linkedin_url=p.linkedin_url or "",
            github_url=p.github_url or "",
            portfolio_url=p.portfolio_url or "",
            eligibility_source=e.source if e else None,
        )
        for (p, e, u) in page_rows
    ]

    return CandidateBrowseResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/{user_id}", response_model=CandidateDetailResponse)
def get_candidate_detail(
    user_id: int,
    current_user: User = Depends(AuthService.require_company),
    db: Session = Depends(get_db),
):
    _require_approved_company(current_user, db)

    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    user = db.query(User).filter(User.id == user_id).first()
    elig = _eligibility_for(db, user_id)

    if not profile or not user or not profile.is_visible or not (elig and elig.eligible):
        raise HTTPException(status_code=404, detail="Candidate not available")

    return CandidateDetailResponse(
        user_id=user.id,
        display_name=user.display_name,
        bio=profile.bio or "",
        skills=list(profile.skills or []),
        preferred_roles=list(profile.preferred_roles or []),
        availability_date=profile.availability_date,
        linkedin_url=profile.linkedin_url or "",
        github_url=profile.github_url or "",
        portfolio_url=profile.portfolio_url or "",
        eligibility_source=elig.source if elig else None,
        resume_url=profile.resume_url or "",
    )
