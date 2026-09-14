"""
Companies router — SS3 (mounted at /api/v1/companies).

Covers:
  - Company self-serve signup + admin invite/pre-approve flow
  - Admin approval queue (list / approve / reject)
  - Company profile /me, /me update
  - Candidate browse + express-interest flow
  - Candidate-side internship inbox (accept / decline)
  - Company-side withdraw

SS2 integration is done with a deferred import (try/except ImportError ->
503) so this router loads cleanly even if SS2 lands later.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import JWTError, jwt
from sqlalchemy import String, and_, cast, or_, func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    ALGORITHM,
    create_access_token,
    get_password_hash,
)
from app.models.company import Company, CompanyInterest
from app.models.user import User, UserProfile
from app.schemas.company import (
    CandidateBrowseItem,
    CandidateBrowseResponse,
    CompanyAdminInviteRequest,
    CompanyCompleteSetupRequest,
    CompanyRejectRequest,
    CompanyResponse,
    CompanySignupRequest,
    CompanyUpdate,
    InterestCandidateView,
    InterestCompanyView,
    InterestCreateRequest,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService


router = APIRouter()
settings = get_settings()


# ---------------- helpers ----------------


def _slugify(name: str) -> str:
    base = "".join(c.lower() if c.isalnum() else "-" for c in name.strip())
    base = "-".join(filter(None, base.split("-")))
    return base or "company"


def _unique_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    candidate = base
    n = 2
    while db.query(Company).filter(Company.slug == candidate).first() is not None:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def _get_my_company(db: Session, user: User) -> Company:
    """Return the company for the authenticated user (owner or manager)."""
    # Owner path
    company = db.query(Company).filter(Company.owner_user_id == user.id).first()
    if company:
        return company
    # Manager path
    from app.models.company_dashboard import CompanyManager

    link = db.query(CompanyManager).filter(CompanyManager.user_id == user.id).first()
    if link:
        company = db.query(Company).filter(Company.id == link.company_id).first()
        if company:
            return company
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="No company profile for this user"
    )


def _require_approved_company(db: Session, user: User) -> Company:
    company = _get_my_company(db, user)
    if not company.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company not approved yet",
        )
    return company


def _mint_company_setup_token(email: str, company_id: int) -> str:
    """Create a fresh 48h company_setup JWT for the given contact."""
    return create_access_token(
        {"sub": email, "type": "company_setup", "cid": company_id},
        expires_delta=timedelta(hours=48),
    )


def _verify_setup_token(token: str) -> str:
    """Decode a company_setup token; return the email (sub). Raise 400 on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired setup token")
    if payload.get("type") != "company_setup":
        raise HTTPException(status_code=400, detail="Wrong token type")
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Malformed token")
    return email


# ---------------- Signup / Setup ----------------


@router.post("/signup", response_model=CompanyResponse, status_code=201)
def company_signup(
    body: CompanySignupRequest,
    db: Session = Depends(get_db),
):
    """
    Self-serve company signup.
    Creates User(role='company') + Company(is_approved=False, approval_source='self_serve').
    Admin must then approve via the approval queue.
    """
    # Idempotency: reject if email already used
    existing = db.query(User).filter(User.user_email == body.contact_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        login = body.contact_email.split("@")[0][:50]
        # guarantee uniqueness of user_login
        base_login = login or "company"
        n = 2
        while db.query(User).filter(User.user_login == login).first() is not None:
            login = f"{base_login}{n}"[:60]
            n += 1

        user = User(
            user_login=login,
            user_pass=get_password_hash(body.password),
            user_nicename=login,
            user_email=body.contact_email,
            display_name=body.name,
            role="company",
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        db.flush()

        company = Company(
            owner_user_id=user.id,
            name=body.name,
            slug=_unique_slug(db, body.name),
            website=body.website or "",
            industry=body.industry or "",
            team_size=body.team_size or "",
            description=body.description or "",
            contact_email=body.contact_email,
            contact_phone=body.contact_phone or "",
            is_approved=False,
            approval_source="self_serve",
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        return company
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {e}")


@router.post("/admin/invite", response_model=CompanyResponse, status_code=201)
def admin_invite_company(
    body: CompanyAdminInviteRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    """
    Admin pre-creates a Company (pre-approved) and emails the contact a
    setup link. A placeholder User is created with a random unusable password
    — the company chooses their real password via /complete-setup.
    """
    existing_user = db.query(User).filter(User.user_email == body.contact_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        import secrets as _secrets

        placeholder_pw = get_password_hash(_secrets.token_urlsafe(32))

        login = body.contact_email.split("@")[0][:50] or "company"
        base_login = login
        n = 2
        while db.query(User).filter(User.user_login == login).first() is not None:
            login = f"{base_login}{n}"[:60]
            n += 1

        user = User(
            user_login=login,
            user_pass=placeholder_pw,
            user_nicename=login,
            user_email=body.contact_email,
            display_name=body.name,
            role="company",
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        db.flush()

        company = Company(
            owner_user_id=user.id,
            name=body.name,
            slug=_unique_slug(db, body.name),
            website=body.website or "",
            industry=body.industry or "",
            team_size=body.team_size or "",
            description=body.description or "",
            contact_email=body.contact_email,
            contact_phone=body.contact_phone or "",
            is_approved=True,  # pre-approved
            approval_source="admin_invite",
            approved_by=admin.id,
            approved_at=datetime.now(timezone.utc),
        )
        db.add(company)
        db.commit()
        db.refresh(company)

        # 48h setup token
        setup_token = _mint_company_setup_token(body.contact_email, company.id)
        try:
            EmailService.send_company_setup_link_email(body.contact_email, setup_token)
        except Exception:
            # email failure must not roll back the created records
            pass

        return company
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Admin invite failed: {e}")


@router.post("/admin/bulk-invite")
def admin_bulk_invite_companies(
    body: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    """
    Bulk admin invite. Body: {entries: [{name, email}, ...], send_setup_email?: bool}.

    B7 (2026-09-04): the whole batch is now ONE transaction — every entry is
    validated (shape, email format, not-already-a-user, no duplicate email
    within the batch itself) BEFORE any row is written. If any entry fails
    validation, nothing is written at all and the response is 400 with the
    full per-row breakdown (so the caller can fix and retry the exact
    failing rows). Only once every entry validates do we create the User +
    Company rows and commit once. Setup-token minting / emailing happens
    after that single commit succeeds and is best-effort per the existing
    pattern elsewhere in this file (a mail failure must not roll back
    already-committed records) — those results are informational, not
    validation failures.
    """
    import secrets as _secrets
    import re as _re

    entries = body.get("entries") or []
    send_setup_email = body.get("send_setup_email", True)
    if not isinstance(entries, list):
        raise HTTPException(status_code=400, detail="entries must be a list")

    email_re = _re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    # ---- Phase 1: validate every entry, write nothing yet ----
    validated = []  # [{name, email}] for entries that passed all checks
    failures = []  # [{name, email, status, message}] for entries that didn't
    seen_emails_in_batch = set()

    for raw in entries:
        name = ""
        email = ""
        if not isinstance(raw, dict):
            failures.append(
                {
                    "name": name,
                    "email": email,
                    "status": "error",
                    "message": "entry must be an object with name + email",
                }
            )
            continue

        name = (raw.get("name") or "").strip()
        email = (raw.get("email") or "").strip().lower()

        if not name or len(name) < 2:
            failures.append(
                {
                    "name": name,
                    "email": email,
                    "status": "error",
                    "message": "Invalid company name",
                }
            )
            continue
        if not email or not email_re.match(email):
            failures.append(
                {
                    "name": name,
                    "email": email,
                    "status": "error",
                    "message": "Invalid email",
                }
            )
            continue
        if email in seen_emails_in_batch:
            failures.append(
                {
                    "name": name,
                    "email": email,
                    "status": "error",
                    "message": "Duplicate email within this batch",
                }
            )
            continue
        if db.query(User).filter(User.user_email == email).first():
            failures.append(
                {
                    "name": name,
                    "email": email,
                    "status": "error",
                    "message": "A user with that email already exists",
                }
            )
            continue

        seen_emails_in_batch.add(email)
        validated.append({"name": name, "email": email})

    if failures:
        # No partial writes — reject the whole batch and list every
        # failing row so the caller can fix and resubmit.
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Bulk invite rejected — fix the listed rows and resubmit. No rows were created.",
                "total": len(entries),
                "failed": len(failures),
                "results": failures,
            },
        )

    # ---- Phase 2: everything validated — write all rows, one commit ----
    created = []  # [{name, email, company}]
    try:
        for entry in validated:
            name = entry["name"]
            email = entry["email"]

            placeholder_pw = get_password_hash(_secrets.token_urlsafe(32))
            login = email.split("@")[0][:50] or "company"
            base_login = login
            n = 2
            while db.query(User).filter(User.user_login == login).first() is not None:
                login = f"{base_login}{n}"[:60]
                n += 1

            user = User(
                user_login=login,
                user_pass=placeholder_pw,
                user_nicename=login,
                user_email=email,
                display_name=name,
                role="company",
                is_active=True,
                is_verified=False,
            )
            db.add(user)
            db.flush()

            company = Company(
                owner_user_id=user.id,
                name=name,
                slug=_unique_slug(db, name),
                website="",
                industry="",
                team_size="",
                description="",
                contact_email=email,
                contact_phone="",
                is_approved=True,
                approval_source="admin_invite",
                approved_by=admin.id,
                approved_at=datetime.now(timezone.utc),
            )
            db.add(company)
            db.flush()

            created.append({"name": name, "email": email, "company": company})

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=f"Bulk invite failed — no rows were created: {e}"
        )

    for row in created:
        db.refresh(row["company"])

    # ---- Phase 3: setup tokens + optional emails (best-effort, post-commit) ----
    results = []
    for row in created:
        name, email, company = row["name"], row["email"], row["company"]
        mail_note = ""
        try:
            setup_token = _mint_company_setup_token(email, company.id)
            if send_setup_email:
                try:
                    EmailService.send_company_setup_link_email(email, setup_token)
                    mail_note = "Setup email sent"
                except Exception as me:
                    mail_note = f"Setup email failed: {me}"
            else:
                mail_note = "Setup email skipped"
        except Exception as te:
            mail_note = f"Token generation failed: {te}"

        results.append(
            {
                "name": name,
                "email": email,
                "status": "invited",
                "message": mail_note,
                "company_id": company.id,
            }
        )

    return {
        "total": len(entries),
        "invited": len(results),
        "skipped": 0,
        "errors": 0,
        "results": results,
    }


@router.post("/complete-setup", response_model=CompanyResponse)
def complete_setup(body: CompanyCompleteSetupRequest, db: Session = Depends(get_db)):
    """Admin-invited company finishes setup: accepts setup token + new password."""
    email = _verify_setup_token(body.token)
    user = db.query(User).filter(User.user_email == email).first()
    if not user or user.role != "company":
        raise HTTPException(status_code=404, detail="Company user not found")

    company = db.query(Company).filter(Company.owner_user_id == user.id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        user.user_pass = get_password_hash(body.password)
        user.is_verified = True
        db.commit()
        db.refresh(company)
        return company
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Setup failed: {e}")


# ---------------- Admin approval queue ----------------


@router.get("/admin/pending", response_model=List[CompanyResponse])
def admin_list_pending(
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    q = (
        db.query(Company)
        .filter(Company.is_approved.is_(False))
        .filter(Company.rejected_at.is_(None))
        .order_by(Company.created_at.desc())
    )
    return q.all()


@router.get("/admin/all")
def admin_list_all(
    status: str = Query(
        "all", description="all | invited | pending | active | rejected"
    ),
    search: Optional[str] = Query(
        None, description="Substring across name/contact_email/slug"
    ),
    limit: int = Query(200, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    """
    Unified admin listing of companies across all lifecycle states.

    Derived status per row:
      - rejected: rejected_at IS NOT NULL
      - invited : approval_source='admin_invite' AND is_approved=True AND owner.is_verified=False
      - pending : is_approved=False AND rejected_at IS NULL
      - active  : is_approved=True AND (approval_source!='admin_invite' OR owner.is_verified=True)
    """
    if status not in ("all", "invited", "pending", "active", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status filter")

    # Base query — eager-load owner to avoid N+1 on the per-row status computation.
    q = db.query(Company).options(joinedload(Company.owner))

    if search:
        like = f"%{search.strip().lower()}%"
        q = q.filter(
            or_(
                sa_func.lower(Company.name).like(like),
                sa_func.lower(Company.contact_email).like(like),
                sa_func.lower(Company.slug).like(like),
            )
        )

    # Apply status filter at the SQL level where possible (the 'active' vs
    # 'invited' split depends on owner.is_verified, so those two need a join
    # to the users table).
    if status == "rejected":
        q = q.filter(Company.rejected_at.isnot(None))
    elif status == "pending":
        q = q.filter(
            Company.is_approved.is_(False),
            Company.rejected_at.is_(None),
        )
    elif status == "invited":
        q = q.join(User, User.id == Company.owner_user_id).filter(
            Company.approval_source == "admin_invite",
            Company.is_approved.is_(True),
            Company.rejected_at.is_(None),
            User.is_verified.is_(False),
        )
    elif status == "active":
        q = q.join(User, User.id == Company.owner_user_id).filter(
            Company.is_approved.is_(True),
            Company.rejected_at.is_(None),
            or_(
                Company.approval_source != "admin_invite",
                User.is_verified.is_(True),
            ),
        )
    # 'all' → no extra filter

    total = q.count()
    companies = q.order_by(Company.created_at.desc()).offset(skip).limit(limit).all()

    # interests_sent in one subquery (avoid N+1).
    company_ids = [c.id for c in companies]
    interests_map: dict = {}
    if company_ids:
        rows = (
            db.query(
                CompanyInterest.company_id,
                sa_func.count(CompanyInterest.id).label("cnt"),
            )
            .filter(CompanyInterest.company_id.in_(company_ids))
            .group_by(CompanyInterest.company_id)
            .all()
        )
        interests_map = {cid: cnt for cid, cnt in rows}

    def _derive_status(c: Company) -> str:
        if c.rejected_at is not None:
            return "rejected"
        owner_verified = bool(c.owner and c.owner.is_verified)
        if c.approval_source == "admin_invite" and c.is_approved and not owner_verified:
            return "invited"
        if not c.is_approved:
            return "pending"
        return "active"

    out = []
    for c in companies:
        owner_obj = c.owner
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "contact_email": c.contact_email,
                "contact_phone": c.contact_phone or "",
                "website": c.website or "",
                "industry": c.industry or "",
                "team_size": c.team_size or "",
                "description": c.description or "",
                "logo_url": c.logo_url or "",
                "approval_source": c.approval_source,
                "is_approved": bool(c.is_approved),
                "approved_at": c.approved_at,
                "rejected_at": c.rejected_at,
                "rejection_reason": c.rejection_reason or "",
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "status": _derive_status(c),
                "owner": {
                    "id": owner_obj.id if owner_obj else None,
                    "display_name": owner_obj.display_name if owner_obj else None,
                    "is_verified": bool(owner_obj.is_verified) if owner_obj else False,
                    "last_login": owner_obj.last_login if owner_obj else None,
                },
                "interests_sent": int(interests_map.get(c.id, 0)),
            }
        )

    return {"total": total, "limit": limit, "skip": skip, "items": out}


@router.post("/admin/{company_id}/resend-invite")
def admin_resend_invite(
    company_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    """
    Resend the admin-invite setup email for a company whose contact hasn't
    completed setup yet. Mints a fresh 48h company_setup token.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.approval_source != "admin_invite":
        raise HTTPException(
            status_code=400,
            detail="Only admin-invite companies can be re-invited",
        )
    owner = db.query(User).filter(User.id == company.owner_user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Company owner not found")
    if owner.is_verified:
        raise HTTPException(status_code=400, detail="Company already set up")

    try:
        setup_token = _mint_company_setup_token(owner.user_email, company.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token mint failed: {e}")

    try:
        EmailService.send_company_setup_link_email(owner.user_email, setup_token)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send setup email: {e}",
        )

    return {"ok": True, "sent_to": owner.user_email}


@router.patch("/admin/{company_id}/approve", response_model=CompanyResponse)
def admin_approve_company(
    company_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        was_rejected = company.rejected_at is not None
        company.is_approved = True
        company.approved_by = admin.id
        company.approved_at = datetime.now(timezone.utc)
        company.rejected_at = None
        company.rejection_reason = ""
        # If this is a previously-rejected company being un-rejected, flip
        # the owner's login back on so they can access the portal again.
        if was_rejected:
            owner = db.query(User).filter(User.id == company.owner_user_id).first()
            if owner and not owner.is_active:
                owner.is_active = True
        db.commit()
        db.refresh(company)
        try:
            EmailService.send_company_approved_email(company)
        except Exception:
            pass
        return company
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Approve failed: {e}")


@router.patch("/admin/{company_id}/reject", response_model=CompanyResponse)
def admin_reject_company(
    company_id: int,
    body: CompanyRejectRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        company.is_approved = False
        company.rejected_at = datetime.now(timezone.utc)
        company.rejection_reason = body.reason or ""
        # Disable the owner's login so a rejected company can't access an
        # empty dashboard. Re-enabled on approve.
        owner = db.query(User).filter(User.id == company.owner_user_id).first()
        if owner:
            owner.is_active = False
        db.commit()
        db.refresh(company)
        return company
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Reject failed: {e}")


# ---------------- Company self-service profile ----------------


@router.get("/me", response_model=CompanyResponse)
def get_my_company(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    return _get_my_company(db, user)


@router.put("/me", response_model=CompanyResponse)
def update_my_company(
    body: CompanyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company),
):
    company = _get_my_company(db, user)
    try:
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(company, k, v)
        db.commit()
        db.refresh(company)
        return company
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {e}")


# ---------------- Candidate browse (reads SS2) ----------------


@router.get("/candidates/browse", response_model=CandidateBrowseResponse)
def browse_candidates(
    skills: Optional[str] = Query(None, description="comma-separated skill keywords"),
    roles: Optional[str] = Query(None, description="comma-separated preferred roles"),
    availability_before: Optional[str] = Query(
        None, description="ISO date — return candidates available on/before this date"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company),
):
    """
    Company-only candidate browse. Joins CandidateProfile (SS2) with
    CandidateEligibility (SS2). SS2 models are deferred-imported so this
    router still loads before SS2 lands — returns 503 if SS2 missing.
    """
    _require_approved_company(db, user)

    try:
        from app.models.candidate import (
            CandidateProfile,
            CandidateEligibility,
        )  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Candidate module (SS2) not yet available on this deployment.",
        )

    try:
        q = (
            db.query(CandidateProfile, User)
            .join(
                CandidateEligibility,
                CandidateEligibility.user_id == CandidateProfile.user_id,
            )
            .join(User, User.id == CandidateProfile.user_id)
            .filter(CandidateProfile.is_visible.is_(True))
            .filter(CandidateEligibility.eligible.is_(True))
            .filter(User.is_active.is_(True))
        )

        if skills:
            for term in [s.strip() for s in skills.split(",") if s.strip()]:
                q = q.filter(
                    sa_func.lower(cast(CandidateProfile.skills, String)).like(
                        f"%{term.lower()}%"
                    )
                )

        if roles:
            for term in [s.strip() for s in roles.split(",") if s.strip()]:
                q = q.filter(
                    sa_func.lower(cast(CandidateProfile.preferred_roles, String)).like(
                        f"%{term.lower()}%"
                    )
                )

        if availability_before:
            try:
                before_dt = datetime.fromisoformat(availability_before).date()
                q = q.filter(
                    or_(
                        CandidateProfile.availability_date.is_(None),
                        CandidateProfile.availability_date <= before_dt,
                    )
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="availability_before must be ISO date"
                )

        total = q.count()
        rows = (
            q.order_by(CandidateProfile.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items: List[CandidateBrowseItem] = []
        for profile, u in rows:
            skills_list = profile.skills if isinstance(profile.skills, list) else []
            roles_list = (
                profile.preferred_roles
                if isinstance(profile.preferred_roles, list)
                else []
            )
            items.append(
                CandidateBrowseItem(
                    user_id=u.id,
                    display_name=u.display_name or u.user_login,
                    headline=(getattr(profile, "bio", "") or "")[:160] or None,
                    skills=skills_list,
                    preferred_roles=roles_list,
                    availability_date=getattr(profile, "availability_date", None),
                    resume_url=getattr(profile, "resume_url", None),
                    linkedin_url=getattr(profile, "linkedin_url", None),
                    github_url=getattr(profile, "github_url", None),
                    portfolio_url=getattr(profile, "portfolio_url", None),
                )
            )

        return CandidateBrowseResponse(
            items=items, total=total, page=page, page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Browse failed: {e}")


# ---------------- Express interest ----------------


@router.post(
    "/candidates/{candidate_user_id}/interest", response_model=InterestCompanyView
)
def express_interest(
    candidate_user_id: int,
    body: InterestCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company),
):
    company = _require_approved_company(db, user)

    candidate = db.query(User).filter(User.id == candidate_user_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Block duplicate ACTIVE (interested/accepted) interest; allow re-opening after
    # a declined/withdrawn previous one by reusing the same row.
    existing = (
        db.query(CompanyInterest)
        .filter(CompanyInterest.company_id == company.id)
        .filter(CompanyInterest.candidate_user_id == candidate_user_id)
        .first()
    )
    try:
        if existing:
            if existing.status in ("interested", "accepted"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Active interest already exists (status={existing.status})",
                )
            # re-open declined/withdrawn
            existing.status = "interested"
            existing.company_message = body.message
            existing.responded_at = None
            db.commit()
            db.refresh(existing)
            interest = existing
        else:
            interest = CompanyInterest(
                company_id=company.id,
                candidate_user_id=candidate_user_id,
                status="interested",
                company_message=body.message,
            )
            db.add(interest)
            try:
                db.commit()
                db.refresh(interest)
            except IntegrityError:
                # Concurrent request already created the row; re-fetch and reuse.
                db.rollback()
                existing_race = (
                    db.query(CompanyInterest)
                    .filter(CompanyInterest.company_id == company.id)
                    .filter(CompanyInterest.candidate_user_id == candidate_user_id)
                    .first()
                )
                if not existing_race:
                    raise HTTPException(
                        status_code=500,
                        detail="Interest row collision but could not recover",
                    )
                interest = existing_race
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Interest failed: {e}")

    try:
        EmailService.send_candidate_interest_email(candidate, company, body.message)
    except Exception:
        pass

    return _to_company_view(interest, candidate)


def _to_company_view(interest: CompanyInterest, candidate: User) -> InterestCompanyView:
    reveal = interest.status == "accepted"
    phone = ""
    if reveal:
        # Resilient lookup — candidate may have no profile row (CandidateProfile
        # doesn't store phone; UserProfile does). Never crash on None chains.
        phone = getattr(getattr(candidate, "profile", None), "phone", "") or ""
    return InterestCompanyView(
        id=interest.id,
        candidate_user_id=interest.candidate_user_id,
        candidate_name=candidate.display_name if candidate else None,
        status=interest.status,
        company_message=interest.company_message or "",
        responded_at=interest.responded_at,
        created_at=interest.created_at,
        candidate_email=candidate.user_email if reveal else None,
        candidate_phone=phone if reveal else None,
    )


@router.get("/me/interests", response_model=List[InterestCompanyView])
def my_company_pipeline(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company),
):
    company = _get_my_company(db, user)
    rows = (
        db.query(CompanyInterest, User)
        .join(User, User.id == CompanyInterest.candidate_user_id)
        .filter(CompanyInterest.company_id == company.id)
        .order_by(CompanyInterest.created_at.desc())
        .all()
    )
    return [_to_company_view(interest, candidate) for interest, candidate in rows]


@router.get("/me/candidate-inbox", response_model=List[InterestCandidateView])
def my_candidate_inbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Any authenticated user sees interests addressed to them."""
    rows = (
        db.query(CompanyInterest, Company)
        .join(Company, Company.id == CompanyInterest.company_id)
        .filter(CompanyInterest.candidate_user_id == current_user.id)
        .order_by(CompanyInterest.created_at.desc())
        .all()
    )
    out: List[InterestCandidateView] = []
    for interest, company in rows:
        out.append(
            InterestCandidateView(
                id=interest.id,
                company_id=company.id,
                company_name=company.name,
                company_logo_url=company.logo_url or None,
                company_industry=company.industry or None,
                company_website=company.website or None,
                status=interest.status,
                company_message=interest.company_message or "",
                responded_at=interest.responded_at,
                created_at=interest.created_at,
            )
        )
    return out


def _get_interest_for_candidate(
    db: Session, interest_id: int, user: User
) -> CompanyInterest:
    interest = (
        db.query(CompanyInterest).filter(CompanyInterest.id == interest_id).first()
    )
    if not interest:
        raise HTTPException(status_code=404, detail="Interest not found")
    if interest.candidate_user_id != user.id:
        raise HTTPException(
            status_code=403, detail="This interest is not addressed to you"
        )
    return interest


@router.post("/interests/{interest_id}/accept", response_model=InterestCandidateView)
def accept_interest(
    interest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    interest = _get_interest_for_candidate(db, interest_id, current_user)
    if interest.status not in ("interested", "declined"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot accept an interest in status={interest.status}",
        )
    try:
        interest.status = "accepted"
        interest.responded_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(interest)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Accept failed: {e}")

    # notify the company that candidate accepted
    try:
        company = db.query(Company).filter(Company.id == interest.company_id).first()
        if company:
            EmailService.send_interest_accepted_email(company, current_user)
    except Exception:
        pass

    company = db.query(Company).filter(Company.id == interest.company_id).first()
    return InterestCandidateView(
        id=interest.id,
        company_id=company.id if company else interest.company_id,
        company_name=company.name if company else None,
        company_logo_url=(company.logo_url or None) if company else None,
        company_industry=(company.industry or None) if company else None,
        company_website=(company.website or None) if company else None,
        status=interest.status,
        company_message=interest.company_message or "",
        responded_at=interest.responded_at,
        created_at=interest.created_at,
    )


@router.post("/interests/{interest_id}/decline", response_model=InterestCandidateView)
def decline_interest(
    interest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    interest = _get_interest_for_candidate(db, interest_id, current_user)
    if interest.status not in ("interested",):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot decline an interest in status={interest.status}",
        )
    try:
        interest.status = "declined"
        interest.responded_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(interest)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Decline failed: {e}")

    company = db.query(Company).filter(Company.id == interest.company_id).first()
    return InterestCandidateView(
        id=interest.id,
        company_id=company.id if company else interest.company_id,
        company_name=company.name if company else None,
        company_logo_url=(company.logo_url or None) if company else None,
        company_industry=(company.industry or None) if company else None,
        company_website=(company.website or None) if company else None,
        status=interest.status,
        company_message=interest.company_message or "",
        responded_at=interest.responded_at,
        created_at=interest.created_at,
    )


@router.post("/interests/{interest_id}/withdraw", response_model=InterestCompanyView)
def withdraw_interest(
    interest_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company),
):
    company = _get_my_company(db, user)
    interest = (
        db.query(CompanyInterest).filter(CompanyInterest.id == interest_id).first()
    )
    if not interest:
        raise HTTPException(status_code=404, detail="Interest not found")
    if interest.company_id != company.id:
        raise HTTPException(status_code=403, detail="Not your interest row")
    if interest.status not in ("interested",):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot withdraw an interest in status={interest.status}",
        )
    try:
        interest.status = "withdrawn"
        interest.responded_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(interest)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Withdraw failed: {e}")

    candidate = db.query(User).filter(User.id == interest.candidate_user_id).first()
    return _to_company_view(interest, candidate)
