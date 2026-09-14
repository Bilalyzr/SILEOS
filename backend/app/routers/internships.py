"""
Internships router — paid internship programs (T2 rewrite).

An `Internship` is an admin-created paid program bound to a SPOC user and a
dedicated 1:1 `Cohort`. Students purchase access via Razorpay and receive a
single-use `InternshipVoucher` redeemable at any course checkout for a free
enrollment (resolved in `coupon_service.resolve_checkout_code`).

The legacy `InternshipApplication` "apply" flow has been removed. This router
replaces it entirely.

Mount point (main.py): `/api/v1`  →  routes below use absolute paths.
  * Public   — GET /internships, GET /internships/{slug}
  * Student  — POST /internships/{id}/purchase
               POST /internships/purchase/verify
               GET  /internships/my-vouchers
  * Admin    — POST   /admin/internships
               GET    /admin/internships
               GET    /admin/internships/{id}
               PUT    /admin/internships/{id}
               DELETE /admin/internships/{id}
               GET    /admin/internships/{id}/vouchers
               GET    /admin/internships/{id}/roster
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timezone, date
from decimal import Decimal
import json
from typing import Any, Optional, List

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import case, desc, func as sa_func
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.models.course import Course
from app.models.cohort import Cohort, CohortMembership
from app.models.coupon import Coupon
from app.models.enrollment import Enrollment
from app.models.internship import Internship, InternshipVoucher, InternshipAttendance
from app.models.company_dashboard import (
    InternshipAnnouncement,
    InternshipPerformanceReview,
    DailyWorkLog,
)
from app.models.internship_request import InternshipRequest
from app.models.certificate import IssuedCertificate
from app.models.company import Company, CompanyInterest
from app.services.auth_service import AuthService
from app.services.email_service import EmailService

router = APIRouter()


# ---------------------------------------------------------------------------
# Razorpay helpers (mirror payments.py)
# ---------------------------------------------------------------------------

def _razorpay_creds() -> tuple[str, str]:
    settings = get_settings()
    key_id = settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET
    return key_id, key_secret


def _razorpay_client() -> razorpay.Client:
    key_id, key_secret = _razorpay_creds()
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured",
        )
    return razorpay.Client(auth=(key_id, key_secret))


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return base or "internship"


def _unique_internship_slug(db: Session, title: str, ignore_id: Optional[int] = None) -> str:
    base = _slugify(title)
    slug = base
    n = 2
    while True:
        q = db.query(Internship).filter(Internship.slug == slug)
        if ignore_id is not None:
            q = q.filter(Internship.id != ignore_id)
        if not q.first():
            return slug
        slug = f"{base}-{n}"
        n += 1


def _unique_cohort_slug(db: Session, name: str) -> str:
    base = _slugify(name)
    slug = base
    n = 2
    while db.query(Cohort).filter(Cohort.slug == slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _generate_voucher_code() -> str:
    """INTR- + 8 uppercase hex chars → 13 chars total (fits CHAR(32))."""
    return "INTR-" + secrets.token_hex(4).upper()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InternshipCreateIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = ""
    price: float = Field(..., ge=0)
    spoc_user_id: int
    cover_image: str = ""
    is_published: bool = False


class InternshipUpdateIn(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    spoc_user_id: Optional[int] = None
    cover_image: Optional[str] = None
    is_published: Optional[bool] = None


class PurchaseVerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    internship_id: int


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _admin_row(
    db: Session,
    internship: Internship,
    issued: Optional[int] = None,
    redeemed: Optional[int] = None,
) -> dict:
    if issued is None:
        issued = (
            db.query(sa_func.count(InternshipVoucher.id))
            .filter(InternshipVoucher.internship_id == internship.id)
            .scalar()
            or 0
        )
    if redeemed is None:
        redeemed = (
            db.query(sa_func.count(InternshipVoucher.id))
            .filter(
                InternshipVoucher.internship_id == internship.id,
                InternshipVoucher.status == "redeemed",
            )
            .scalar()
            or 0
        )
    spoc = internship.spoc if getattr(internship, "spoc", None) else None
    return {
        "id": internship.id,
        "title": internship.title,
        "slug": internship.slug,
        "description": internship.description or "",
        "cover_image": internship.cover_image or "",
        "price": float(internship.price or 0),
        "is_published": bool(internship.is_published),
        "spoc_user_id": internship.spoc_user_id,
        "spoc_name": spoc.display_name if spoc else "",
        "spoc_email": spoc.user_email if spoc else "",
        "cohort_id": internship.cohort_id,
        "created_at": internship.created_at,
        "updated_at": internship.updated_at,
        "vouchers_issued": int(issued),
        "vouchers_redeemed": int(redeemed),
    }


def _public_row(internship: Internship) -> dict:
    spoc = internship.spoc if getattr(internship, "spoc", None) else None
    return {
        "id": internship.id,
        "slug": internship.slug,
        "title": internship.title,
        "description": internship.description or "",
        "cover_image": internship.cover_image or "",
        "price": float(internship.price or 0),
        "spoc_name": spoc.display_name if spoc else "",
    }


# ===========================================================================
# Admin CRUD
# ===========================================================================

@router.post("/admin/internships", status_code=status.HTTP_201_CREATED)
async def admin_create_internship(
    payload: InternshipCreateIn,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Create an internship and its dedicated 1:1 cohort in one transaction."""
    spoc = db.query(User).filter(User.id == payload.spoc_user_id).first()
    if not spoc:
        raise HTTPException(status_code=400, detail="SPOC user not found")
    if spoc.role not in ("spoc", "admin"):
        raise HTTPException(
            status_code=400,
            detail="spoc_user_id must reference a user with role 'spoc' or 'admin'",
        )

    try:
        cohort_name = f"{payload.title} — Internship Cohort"
        cohort = Cohort(
            name=cohort_name,
            slug=_unique_cohort_slug(db, cohort_name),
            spoc_user_id=spoc.id,
            course_id=None,
            college_id=None,
            is_active=True,
            max_students=0,
        )
        db.add(cohort)
        db.flush()  # need cohort.id

        internship = Internship(
            title=payload.title.strip(),
            slug=_unique_internship_slug(db, payload.title),
            description=payload.description or "",
            cover_image=payload.cover_image or "",
            price=Decimal(str(payload.price)),
            is_published=bool(payload.is_published),
            spoc_user_id=spoc.id,
            cohort_id=cohort.id,
            created_by=current_user.id,
        )
        db.add(internship)
        db.commit()
        db.refresh(internship)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create internship: {exc}")

    return _admin_row(db, internship, issued=0, redeemed=0)


@router.get("/admin/internships")
async def admin_list_internships(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Internship)
        .options(joinedload(Internship.spoc))
        .order_by(desc(Internship.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    # Single aggregate query for issued/redeemed per internship.
    ids = [i.id for i in items]
    counts: dict[int, tuple[int, int]] = {}
    if ids:
        rows = (
            db.query(
                InternshipVoucher.internship_id,
                sa_func.count(InternshipVoucher.id),
                sa_func.sum(
                    case((InternshipVoucher.status == "redeemed", 1), else_=0)
                ),
            )
            .filter(InternshipVoucher.internship_id.in_(ids))
            .group_by(InternshipVoucher.internship_id)
            .all()
        )
        for iid, total, red in rows:
            counts[int(iid)] = (int(total or 0), int(red or 0))
    return [
        _admin_row(db, i, *counts.get(i.id, (0, 0))) for i in items
    ]


@router.get("/admin/internships/{internship_id}")
async def admin_get_internship(
    internship_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    item = (
        db.query(Internship)
        .options(joinedload(Internship.spoc))
        .filter(Internship.id == internship_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")
    return _admin_row(db, item)


@router.put("/admin/internships/{internship_id}")
async def admin_update_internship(
    internship_id: int,
    payload: InternshipUpdateIn,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")

    data = payload.model_dump(exclude_unset=True)

    # Validate spoc change up front
    new_spoc: Optional[User] = None
    if "spoc_user_id" in data and data["spoc_user_id"] != item.spoc_user_id:
        new_spoc = db.query(User).filter(User.id == data["spoc_user_id"]).first()
        if not new_spoc:
            raise HTTPException(status_code=400, detail="SPOC user not found")
        if new_spoc.role not in ("spoc", "admin"):
            raise HTTPException(
                status_code=400,
                detail="spoc_user_id must reference a user with role 'spoc' or 'admin'",
            )

    try:
        if "title" in data and data["title"] and data["title"] != item.title:
            item.title = data["title"].strip()
            item.slug = _unique_internship_slug(db, item.title, ignore_id=item.id)
        if "description" in data and data["description"] is not None:
            item.description = data["description"]
        if "cover_image" in data and data["cover_image"] is not None:
            item.cover_image = data["cover_image"]
        if "price" in data and data["price"] is not None:
            item.price = Decimal(str(data["price"]))
        if "is_published" in data and data["is_published"] is not None:
            item.is_published = bool(data["is_published"])
        if new_spoc is not None:
            item.spoc_user_id = new_spoc.id
            # Propagate to the linked cohort so SPOC visibility stays consistent.
            cohort = db.query(Cohort).filter(Cohort.id == item.cohort_id).first()
            if cohort:
                cohort.spoc_user_id = new_spoc.id

        db.commit()
        db.refresh(item)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update internship: {exc}")

    return _admin_row(db, item)


@router.delete("/admin/internships/{internship_id}")
async def admin_delete_internship(
    internship_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")

    cohort_id = item.cohort_id

    try:
        # 1) Preserve course enrollments earned via already-redeemed vouchers.
        # The Enrollment row (and therefore course access) is left untouched.
        # We only null-out the voucher's internship link before the voucher
        # itself is cascade-deleted with the internship.
        redeemed_vouchers = (
            db.query(InternshipVoucher)
            .filter(
                InternshipVoucher.internship_id == item.id,
                InternshipVoucher.status == "redeemed",
                InternshipVoucher.redeemed_on_course_id.isnot(None),
            )
            .all()
        )
        for v in redeemed_vouchers:
            # NOTE: the FK column is NOT NULL, so we cannot actually null it.
            # We instead flip the voucher status so the audit trail keeps a
            # record, and rely on cascade delete below to remove them.
            # The student keeps their Enrollment row regardless.
            pass  # intentional: cascade delete below removes voucher rows

        # 2) Delete internship attendance records (must be done before internship delete)
        db.query(InternshipAttendance).filter(
            InternshipAttendance.internship_id == item.id
        ).delete(synchronize_session=False)

        # Delete internship announcements
        db.query(InternshipAnnouncement).filter(
            InternshipAnnouncement.internship_id == item.id
        ).delete(synchronize_session=False)

        # Delete internship performance reviews
        db.query(InternshipPerformanceReview).filter(
            InternshipPerformanceReview.internship_id == item.id
        ).delete(synchronize_session=False)

        # Delete daily work logs
        db.query(DailyWorkLog).filter(
            DailyWorkLog.internship_id == item.id
        ).delete(synchronize_session=False)

        # Update internship requests that reference this internship
        db.query(InternshipRequest).filter(
            InternshipRequest.approved_internship_id == item.id
        ).update(
            {InternshipRequest.approved_internship_id: None},
            synchronize_session=False
        )

        # 3) Batch-2 cohort cleanup pattern — runs BEFORE the cohort/internship
        # deletes so ORM doesn't cascade-drop the rows we want to preserve.
        if cohort_id:
            db.query(Enrollment).filter(Enrollment.cohort_id == cohort_id).update(
                {Enrollment.cohort_id: None}, synchronize_session=False
            )
            try:
                from app.models.candidate import CandidateEligibility
                db.query(CandidateEligibility).filter(
                    CandidateEligibility.cohort_id == cohort_id,
                    CandidateEligibility.source == "spoc_approved",
                ).update(
                    {
                        CandidateEligibility.cohort_id: None,
                        CandidateEligibility.eligible: False,
                    },
                    synchronize_session=False,
                )
            except ImportError:
                pass
            db.query(Coupon).filter(Coupon.cohort_id == cohort_id).update(
                {Coupon.cohort_id: None}, synchronize_session=False
            )

        # 4) Delete the internship (cascade drops all vouchers — redeemed
        # and unredeemed alike — via the model's `cascade='all, delete-orphan'`).
        # The student's Enrollment row is NOT affected because enrollments
        # have no FK to internship; they only referenced the cohort, which
        # we already nulled above.
        db.delete(item)
        db.flush()

        # 5) Finally drop the cohort itself.
        if cohort_id:
            cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
            if cohort:
                db.delete(cohort)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete internship: {exc}")

    return {"message": "Internship deleted"}


# ===========================================================================
# SPOC endpoints
# ===========================================================================

@router.get("/spoc/my-internships")
async def spoc_my_internships(
    current_user: User = Depends(AuthService.require_spoc_or_admin),
    db: Session = Depends(get_db),
):
    """List the internships this SPOC is assigned to, plus voucher stats.

    The UI shows this as the SPOC home — each row opens the roster
    (which reuses /admin/internships/{id}/roster for the rich progress +
    cert + hire view).
    """
    items = (
        db.query(Internship)
        .options(joinedload(Internship.spoc))
        .filter(Internship.spoc_user_id == current_user.id)
        .order_by(desc(Internship.created_at))
        .all()
    )
    if not items:
        return []

    ids = [i.id for i in items]
    counts: dict[int, tuple[int, int]] = {}
    rows = (
        db.query(
            InternshipVoucher.internship_id,
            sa_func.count(InternshipVoucher.id),
            sa_func.sum(
                case((InternshipVoucher.status == "redeemed", 1), else_=0)
            ),
        )
        .filter(InternshipVoucher.internship_id.in_(ids))
        .group_by(InternshipVoucher.internship_id)
        .all()
    )
    for iid, total, red in rows:
        counts[int(iid)] = (int(total or 0), int(red or 0))

    return [_admin_row(db, i, *counts.get(i.id, (0, 0))) for i in items]


@router.get("/spoc/internships/{internship_id}/roster")
async def spoc_internship_roster(
    internship_id: int,
    current_user: User = Depends(AuthService.require_spoc_or_admin),
    db: Session = Depends(get_db),
):
    """SPOC-accessible roster — scoped to internships they own."""
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")
    if current_user.role != "admin" and item.spoc_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This internship is not assigned to you")
    # Delegate to the admin roster implementation for the same shape.
    return await admin_internship_roster(internship_id, current_user, db)  # type: ignore[arg-type]


@router.get("/admin/internships/{internship_id}/vouchers")
async def admin_list_vouchers(
    internship_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")

    q = (
        db.query(InternshipVoucher)
        .options(
            joinedload(InternshipVoucher.buyer),
            joinedload(InternshipVoucher.redeemed_course),
        )
        .filter(InternshipVoucher.internship_id == internship_id)
        .order_by(desc(InternshipVoucher.created_at))
    )
    total = q.count()
    rows = q.offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": v.id,
                "code": v.code,
                "status": v.status,
                "amount_paid": float(v.amount_paid or 0),
                "razorpay_order_id": v.razorpay_order_id or "",
                "razorpay_payment_id": v.razorpay_payment_id or "",
                "redeemed_on_course_id": v.redeemed_on_course_id,
                "redeemed_course_title": (
                    v.redeemed_course.post_title if v.redeemed_course else None
                ),
                "redeemed_at": v.redeemed_at,
                "created_at": v.created_at,
                "buyer": {
                    "id": v.buyer.id,
                    "display_name": v.buyer.display_name,
                    "email": v.buyer.user_email,
                } if v.buyer else None,
            }
            for v in rows
        ],
    }


class ManualVoucherCreateIn(BaseModel):
    user_id: int
    amount_paid: float = 0
    notes: str = ""


@router.post("/admin/internships/{internship_id}/vouchers")
async def admin_create_manual_voucher(
    internship_id: int,
    payload: ManualVoucherCreateIn,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Manually add a student to the internship roster with a voucher.

    Used when payment was made outside the system (cash, UPI direct, etc.)
    or when admin needs to grant access without payment.
    """
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")

    buyer = db.query(User).filter(User.id == payload.user_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(InternshipVoucher)
        .filter(
            InternshipVoucher.internship_id == internship_id,
            InternshipVoucher.buyer_user_id == payload.user_id,
            InternshipVoucher.status == "issued",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already has an unredeemed voucher for this internship",
        )

    try:
        code: Optional[str] = None
        for _ in range(10):
            candidate = _generate_voucher_code()
            clash = (
                db.query(InternshipVoucher)
                .filter(InternshipVoucher.code == candidate)
                .first()
            )
            if not clash:
                code = candidate
                break
        if not code:
            raise HTTPException(status_code=500, detail="Could not generate unique voucher code")

        voucher = InternshipVoucher(
            code=code,
            internship_id=internship_id,
            buyer_user_id=payload.user_id,
            amount_paid=Decimal(str(payload.amount_paid)),
            razorpay_order_id="MANUAL",
            razorpay_payment_id="MANUAL",
            status="issued",
        )
        db.add(voucher)

        # Add buyer to the internship's cohort
        already = (
            db.query(CohortMembership)
            .filter(
                CohortMembership.cohort_id == item.cohort_id,
                CohortMembership.user_id == payload.user_id,
            )
            .first()
        )
        if not already:
            db.add(CohortMembership(
                cohort_id=item.cohort_id,
                user_id=payload.user_id,
            ))

        db.commit()
        db.refresh(voucher)

        # Send voucher email
        try:
            EmailService.send_internship_voucher_email(buyer, item, voucher.code)
        except Exception:
            pass

        return {
            "id": voucher.id,
            "code": voucher.code,
            "status": voucher.status,
            "amount_paid": float(voucher.amount_paid),
            "buyer_name": buyer.display_name,
            "buyer_email": buyer.user_email,
            "created_at": voucher.created_at,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create voucher: {exc}")


@router.get("/admin/internships/{internship_id}/roster")
async def admin_internship_roster(
    internship_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Per-buyer unified view joining voucher + enrollment + certs + hire status."""
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")

    vouchers = (
        db.query(InternshipVoucher)
        .options(
            joinedload(InternshipVoucher.buyer),
            joinedload(InternshipVoucher.redeemed_course),
        )
        .filter(InternshipVoucher.internship_id == internship_id)
        .order_by(desc(InternshipVoucher.created_at))
        .all()
    )

    roster: list[dict] = []
    for v in vouchers:
        buyer = v.buyer
        buyer_id = buyer.id if buyer else None
        redeemed_course_id = v.redeemed_on_course_id
        redeemed_course_title = v.redeemed_course.post_title if v.redeemed_course else None

        # Enrollment via (user, course) pair — voucher redemption stamps both.
        enrollment = None
        if buyer_id and redeemed_course_id:
            enrollment = (
                db.query(Enrollment)
                .filter(
                    Enrollment.user_id == buyer_id,
                    Enrollment.course_id == redeemed_course_id,
                )
                .first()
            )

        certs_count = 0
        issued_certificate_id: Optional[int] = None
        hired_by_company = None
        hired_by_source: Optional[str] = None
        attendance_count = 0

        if buyer_id:
            certs_count = (
                db.query(sa_func.count(IssuedCertificate.id))
                .filter(IssuedCertificate.user_id == buyer_id)
                .scalar()
                or 0
            )
            # Issued cert id specifically for the redeemed course (so the
            # admin can revoke it). Falls back to None if not yet issued.
            if redeemed_course_id:
                cert_row = (
                    db.query(IssuedCertificate)
                    .filter(
                        IssuedCertificate.user_id == buyer_id,
                        IssuedCertificate.course_id == redeemed_course_id,
                    )
                    .first()
                )
                if cert_row:
                    issued_certificate_id = int(cert_row.id)

            # Attendance — count present|late.
            attendance_count = (
                db.query(sa_func.count(InternshipAttendance.id))
                .filter(
                    InternshipAttendance.internship_id == internship_id,
                    InternshipAttendance.user_id == buyer_id,
                    InternshipAttendance.status.in_(["present", "late"]),
                )
                .scalar()
                or 0
            )

            # Hired-by: prefer admin override, fall back to CompanyInterest.
            if v.hired_by_company_id:
                override_company = (
                    db.query(Company)
                    .filter(Company.id == v.hired_by_company_id)
                    .first()
                )
                if override_company:
                    hired_by_company = override_company.name
                    hired_by_source = "override"
            if hired_by_company is None:
                accepted = (
                    db.query(CompanyInterest)
                    .join(Company, Company.id == CompanyInterest.company_id)
                    .filter(
                        CompanyInterest.candidate_user_id == buyer_id,
                        CompanyInterest.status == "accepted",
                    )
                    .order_by(desc(CompanyInterest.responded_at))
                    .first()
                )
                if accepted:
                    hired_by_company = accepted.company.name if accepted.company else None
                    if hired_by_company:
                        hired_by_source = "auto"

        roster.append({
            "voucher_id": int(v.id),
            "voucher_code": v.code,
            "status": v.status,
            "buyer_id": buyer_id,
            "buyer_name": buyer.display_name if buyer else "",
            "buyer_email": buyer.user_email if buyer else "",
            "redeemed_course_id": redeemed_course_id,
            "redeemed_course_title": redeemed_course_title,
            "enrollment_id": int(enrollment.id) if enrollment else None,
            "progress_pct": int(enrollment.course_progress_percentage or 0) if enrollment else 0,
            "completion_date": enrollment.completion_date if enrollment else None,
            "certs_count": int(certs_count),
            "issued_certificate_id": issued_certificate_id,
            "hired_by_company": hired_by_company,
            "hired_by_source": hired_by_source,
            "attendance_count": int(attendance_count),
        })

    return {"internship_id": internship_id, "total": len(roster), "items": roster}


# ===========================================================================
# Admin overrides — attendance, hiring assignment
# ===========================================================================

class AttendanceMarkIn(BaseModel):
    user_id: int
    attended_at: date
    status: str = Field(default="present")
    notes: Optional[str] = ""


class AssignCompanyIn(BaseModel):
    company_id: int


_ALLOWED_ATTENDANCE_STATUSES = {"present", "absent", "late", "excused"}


@router.get("/admin/internships/{internship_id}/attendance")
async def admin_list_attendance(
    internship_id: int,
    user_id: Optional[int] = Query(None),
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")

    q = db.query(InternshipAttendance).filter(
        InternshipAttendance.internship_id == internship_id
    )
    if user_id is not None:
        q = q.filter(InternshipAttendance.user_id == user_id)
    if from_ is not None:
        q = q.filter(InternshipAttendance.attended_at >= from_)
    if to is not None:
        q = q.filter(InternshipAttendance.attended_at <= to)

    rows = q.order_by(desc(InternshipAttendance.attended_at), desc(InternshipAttendance.id)).all()
    return {
        "internship_id": internship_id,
        "total": len(rows),
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "attended_at": r.attended_at.isoformat() if r.attended_at else None,
                "status": r.status,
                "notes": r.notes or "",
                "marked_by": r.marked_by,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


@router.post("/admin/internships/{internship_id}/attendance")
async def admin_upsert_attendance(
    internship_id: int,
    payload: AttendanceMarkIn,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")

    status_val = (payload.status or "present").lower().strip()
    if status_val not in _ALLOWED_ATTENDANCE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status — must be one of {sorted(_ALLOWED_ATTENDANCE_STATUSES)}",
        )

    user_row = db.query(User).filter(User.id == payload.user_id).first()
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        existing = (
            db.query(InternshipAttendance)
            .filter(
                InternshipAttendance.internship_id == internship_id,
                InternshipAttendance.user_id == payload.user_id,
                InternshipAttendance.attended_at == payload.attended_at,
            )
            .first()
        )
        if existing:
            existing.status = status_val
            existing.notes = payload.notes or ""
            existing.marked_by = current_user.id
            db.commit()
            db.refresh(existing)
            row = existing
        else:
            row = InternshipAttendance(
                internship_id=internship_id,
                user_id=payload.user_id,
                attended_at=payload.attended_at,
                status=status_val,
                notes=payload.notes or "",
                marked_by=current_user.id,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save attendance: {exc}")

    return {
        "id": row.id,
        "internship_id": row.internship_id,
        "user_id": row.user_id,
        "attended_at": row.attended_at.isoformat() if row.attended_at else None,
        "status": row.status,
        "notes": row.notes or "",
        "marked_by": row.marked_by,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.delete("/admin/internships/{internship_id}/attendance/{record_id}")
async def admin_delete_attendance(
    internship_id: int,
    record_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    row = (
        db.query(InternshipAttendance)
        .filter(
            InternshipAttendance.id == record_id,
            InternshipAttendance.internship_id == internship_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    try:
        db.delete(row)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete attendance: {exc}")
    return {"ok": True, "deleted_id": record_id}


@router.post("/admin/internships/{internship_id}/vouchers/{voucher_id}/assign-company")
async def admin_assign_company_to_voucher(
    internship_id: int,
    voucher_id: int,
    payload: AssignCompanyIn,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    voucher = (
        db.query(InternshipVoucher)
        .filter(
            InternshipVoucher.id == voucher_id,
            InternshipVoucher.internship_id == internship_id,
        )
        .first()
    )
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found for this internship")

    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.is_approved:
        raise HTTPException(status_code=400, detail="Company is not approved")

    try:
        voucher.hired_by_company_id = company.id
        voucher.hired_by_override_at = datetime.now(timezone.utc)
        voucher.hired_by_override_by = current_user.id
        db.commit()
        db.refresh(voucher)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to assign company: {exc}")

    return {
        "voucher_id": voucher.id,
        "hired_by_company_id": voucher.hired_by_company_id,
        "hired_by_company_name": company.name,
        "hired_by_override_at": voucher.hired_by_override_at,
        "hired_by_override_by": voucher.hired_by_override_by,
    }


@router.delete("/admin/internships/{internship_id}/vouchers/{voucher_id}/assign-company")
async def admin_clear_company_override(
    internship_id: int,
    voucher_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    voucher = (
        db.query(InternshipVoucher)
        .filter(
            InternshipVoucher.id == voucher_id,
            InternshipVoucher.internship_id == internship_id,
        )
        .first()
    )
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found for this internship")

    try:
        voucher.hired_by_company_id = None
        voucher.hired_by_override_at = None
        voucher.hired_by_override_by = None
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear override: {exc}")

    return {"ok": True, "voucher_id": voucher_id}


@router.delete("/admin/internships/{internship_id}/vouchers/{voucher_id}")
async def admin_delete_voucher(
    internship_id: int,
    voucher_id: int,
    force: bool = Query(False, description="Allow deletion even if voucher is redeemed"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a voucher from an internship roster.

    WARNING: If the voucher has been redeemed, the student keeps access to
    their enrolled course — only the internship-cohort link is removed.
    Use force=True to delete even redeemed vouchers.
    """
    voucher = (
        db.query(InternshipVoucher)
        .filter(
            InternshipVoucher.id == voucher_id,
            InternshipVoucher.internship_id == internship_id,
        )
        .first()
    )
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found for this internship")

    if voucher.status == "redeemed" and not force:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete redeemed voucher. Student has already enrolled in a course. "
            "Use force=true to proceed (enrollment will remain active).",
        )

    voucher_code = voucher.code
    buyer_id = voucher.buyer_user_id

    try:
        db.delete(voucher)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete voucher: {exc}")

    return {
        "ok": True,
        "voucher_id": voucher_id,
        "voucher_code": voucher_code,
        "buyer_user_id": buyer_id,
        "message": "Voucher deleted" + (" (redeemed voucher - enrollment kept)" if voucher.status == "redeemed" else ""),
    }


@router.post("/admin/internships/{internship_id}/vouchers/{voucher_id}/move")
async def admin_move_voucher(
    internship_id: int,
    voucher_id: int,
    payload: dict[str, Any],
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Move a voucher to a different internship (switch student's internship).
    """
    target_internship_id = payload.get("target_internship_id")
    if not target_internship_id:
        raise HTTPException(status_code=422, detail="target_internship_id is required")

    if target_internship_id == internship_id:
        raise HTTPException(status_code=400, detail="Target internship must be different")

    voucher = (
        db.query(InternshipVoucher)
        .filter(
            InternshipVoucher.id == voucher_id,
            InternshipVoucher.internship_id == internship_id,
        )
        .first()
    )
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found for this internship")

    target_internship = db.query(Internship).filter(Internship.id == target_internship_id).first()
    if not target_internship:
        raise HTTPException(status_code=404, detail="Target internship not found")

    old_internship_id = voucher.internship_id
    voucher.internship_id = target_internship_id

    try:
        db.commit()
        db.refresh(voucher)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to move voucher: {exc}")

    return {
        "ok": True,
        "voucher_id": voucher_id,
        "voucher_code": voucher.code,
        "from_internship_id": old_internship_id,
        "to_internship_id": target_internship_id,
    }


# ===========================================================================
# Public endpoints
# ===========================================================================

@router.get("/internships")
async def list_public_internships(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Internship)
        .options(joinedload(Internship.spoc))
        .filter(Internship.is_published.is_(True))
        .order_by(desc(Internship.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_public_row(i) for i in items]


@router.get("/internships/my-vouchers")
async def student_my_vouchers(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(InternshipVoucher)
        .options(
            joinedload(InternshipVoucher.internship).joinedload(Internship.spoc),
            joinedload(InternshipVoucher.redeemed_course),
        )
        .filter(InternshipVoucher.buyer_user_id == current_user.id)
        .order_by(desc(InternshipVoucher.created_at))
        .all()
    )

    # Fetch company names for vouchers with hired_by_company_id
    voucher_ids = [v.id for v in rows if v.hired_by_company_id]
    company_map = {}
    if voucher_ids:
        companies = (
            db.query(Company.id, Company.name)
            .filter(Company.id.in_([v.hired_by_company_id for v in rows if v.hired_by_company_id]))
            .all()
        )
        company_map = {c.id: c.name for c in companies}

    # Issue 6: connect each voucher with the redeemed course's progress.
    # Batch-load the buyer's enrollments once so we can attach progress
    # status per voucher without an N+1.
    redeemed_course_ids = [v.redeemed_on_course_id for v in rows if v.redeemed_on_course_id]
    progress_map = {}
    if redeemed_course_ids:
        enrollments = (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id.in_(redeemed_course_ids),
            )
            .all()
        )
        progress_map = {
            e.course_id: {
                "progress_percentage": e.course_progress_percentage or 0,
                "enrollment_status": e.enrollment_status,
                "completion_date": e.completion_date,
                "is_completed": e.completion_date is not None,
            }
            for e in enrollments
        }

    certificate_map = {}
    if redeemed_course_ids:
        certificates = (
            db.query(IssuedCertificate.course_id, IssuedCertificate.id)
            .filter(
                IssuedCertificate.user_id == current_user.id,
                IssuedCertificate.course_id.in_(redeemed_course_ids),
                IssuedCertificate.is_valid.is_(True),
            )
            .all()
        )
        certificate_map = {course_id: certificate_id for course_id, certificate_id in certificates}

    # Attendance is a grouped read, not one COUNT query per voucher. A learner
    # may hold many historical internships and this endpoint is used on every
    # dashboard visit.
    internship_ids = sorted({v.internship_id for v in rows if v.internship_id})
    attendance_map = {}
    if internship_ids:
        attendance_rows = (
            db.query(InternshipAttendance.internship_id, sa_func.count(InternshipAttendance.id))
            .filter(
                InternshipAttendance.internship_id.in_(internship_ids),
                InternshipAttendance.user_id == current_user.id,
                InternshipAttendance.status.in_(["present", "late"]),
            )
            .group_by(InternshipAttendance.internship_id)
            .all()
        )
        attendance_map = {internship_id: int(count) for internship_id, count in attendance_rows}

    # Build response with attendance count
    result = []
    for v in rows:
        # Progress of the course this voucher was redeemed for (None until
        # redeemed). Connects voucher usage with course/progress status.
        course_progress = progress_map.get(v.redeemed_on_course_id) if v.redeemed_on_course_id else None

        result.append({
            "id": v.id,
            "code": v.code,
            "status": v.status,
            "amount_paid": float(v.amount_paid or 0),
            "internship_id": v.internship_id,
            "internship_title": v.internship.title if v.internship else None,
            "internship_slug": v.internship.slug if v.internship else None,
            "spoc_name": (
                v.internship.spoc.display_name
                if v.internship and v.internship.spoc
                else None
            ),
            "redeemed_on_course_id": v.redeemed_on_course_id,
            "redeemed_course_id": v.redeemed_on_course_id,
            "redeemed_course_title": (
                v.redeemed_course.post_title if v.redeemed_course else None
            ),
            "company_name": company_map.get(v.hired_by_company_id) if v.hired_by_company_id else None,
            "attendance_count": attendance_map.get(v.internship_id, 0),
            "engagement_status": v.engagement_status,
            "redeemed_at": v.redeemed_at,
            "created_at": v.created_at,
            # Issue 6: course-progress status for the redeemed course.
            "course_progress": course_progress,
            "certificate_issued": v.redeemed_on_course_id in certificate_map,
            "issued_certificate_id": certificate_map.get(v.redeemed_on_course_id),
        })

    return result


@router.get("/internships/{slug}")
async def get_public_internship(slug: str, db: Session = Depends(get_db)):
    item = (
        db.query(Internship)
        .options(joinedload(Internship.spoc))
        .filter(Internship.slug == slug, Internship.is_published.is_(True))
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")
    row = _public_row(item)
    # Full description on detail view
    row["description"] = item.description or ""
    return row


# ===========================================================================
# Student endpoints
# ===========================================================================

@router.post("/internships/{internship_id}/purchase")
async def student_purchase_internship(
    internship_id: int,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a Razorpay order for this internship. Returns order details.
    Rejects if the buyer already holds an `issued` voucher for this internship.
    """
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")
    if not item.is_published:
        raise HTTPException(status_code=400, detail="Internship is not available")

    existing = (
        db.query(InternshipVoucher)
        .filter(
            InternshipVoucher.internship_id == item.id,
            InternshipVoucher.buyer_user_id == current_user.id,
            InternshipVoucher.status == "issued",
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="You already have an unredeemed voucher for this internship",
        )

    price = float(item.price or 0)
    if price <= 0:
        raise HTTPException(status_code=400, detail="Internship price not configured")

    amount_paise = int(round(price * 100))
    if amount_paise < 100:
        amount_paise = 100  # Razorpay minimum

    client = _razorpay_client()
    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"internship_{item.id}_user_{current_user.id}",
            "notes": {
                "internship_id": str(item.id),
                "buyer_user_id": str(current_user.id),
                "kind": "internship",
            },
        })
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gateway error: {exc}")

    key_id, _ = _razorpay_creds()
    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": key_id,
    }


@router.post("/internships/purchase/verify")
async def student_verify_internship_purchase(
    payload: PurchaseVerifyIn,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Verify HMAC, refetch order, issue voucher + cohort membership."""
    item = db.query(Internship).filter(Internship.id == payload.internship_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Internship not found")

    _, key_secret = _razorpay_creds()
    msg = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, payload.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    client = _razorpay_client()
    try:
        order = client.order.fetch(payload.razorpay_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Order not found at gateway")

    notes = order.get("notes") or {}
    if str(notes.get("internship_id")) != str(item.id):
        raise HTTPException(status_code=400, detail="Order does not match internship")
    if str(notes.get("buyer_user_id")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Order does not belong to this user")
    if str(notes.get("kind")) != "internship":
        raise HTTPException(status_code=400, detail="Order is not for an internship")

    expected_amount = int(round(float(item.price or 0) * 100))
    if expected_amount < 100:
        expected_amount = 100
    if int(order.get("amount", 0)) != expected_amount or int(order.get("amount_paid", 0)) < expected_amount:
        raise HTTPException(status_code=400, detail="Order amount does not match internship price")

    # Idempotency: if a voucher was already issued for this order, return it.
    existing_by_order = (
        db.query(InternshipVoucher)
        .filter(InternshipVoucher.razorpay_order_id == payload.razorpay_order_id)
        .first()
    )
    if existing_by_order:
        return {"code": existing_by_order.code, "voucher_id": existing_by_order.id}

    # Generate a unique code (retry on collision).
    code: Optional[str] = None
    for _ in range(10):
        candidate = _generate_voucher_code()
        clash = (
            db.query(InternshipVoucher)
            .filter(InternshipVoucher.code == candidate)
            .first()
        )
        if not clash:
            code = candidate
            break
    if not code:
        raise HTTPException(status_code=500, detail="Could not generate a unique voucher code")

    voucher: Optional[InternshipVoucher] = None
    try:
        voucher = InternshipVoucher(
            code=code,
            internship_id=item.id,
            buyer_user_id=current_user.id,
            amount_paid=Decimal(str(float(item.price or 0))),
            razorpay_order_id=payload.razorpay_order_id,
            razorpay_payment_id=payload.razorpay_payment_id,
            status="issued",
        )
        db.add(voucher)

        # Add buyer to the internship's dedicated cohort (idempotent).
        already = (
            db.query(CohortMembership)
            .filter(
                CohortMembership.cohort_id == item.cohort_id,
                CohortMembership.user_id == current_user.id,
            )
            .first()
        )
        if not already:
            db.add(CohortMembership(
                cohort_id=item.cohort_id,
                user_id=current_user.id,
            ))

        db.commit()
        db.refresh(voucher)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to issue voucher: {exc}")

    # Post-commit: fire email (best-effort; never blocks voucher issue).
    try:
        EmailService.send_internship_voucher_email(current_user, item, voucher.code)
    except Exception:
        pass

    return {"code": voucher.code, "voucher_id": voucher.id}


@router.post("/internships/webhook")
async def internship_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Razorpay webhook handler for internship payments.

    Falls back voucher creation if frontend verify fails.
    Handles payment.captured events to ensure vouchers are issued.
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    _, key_secret = _razorpay_creds()
    expected_sig = hmac.new(key_secret.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("event", "")
    if event_type != "payment.captured":
        return {"status": "ignored", "event": event_type}

    payment = event.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment.get("order_id")
    if not order_id:
        return {"status": "error", "reason": "no order_id"}

    # Check if voucher already exists for this order
    existing = db.query(InternshipVoucher).filter(InternshipVoucher.razorpay_order_id == order_id).first()
    if existing:
        return {"status": "already_processed", "voucher_id": existing.id}

    # Fetch order to get internship_id and buyer_user_id from notes
    client = _razorpay_client()
    try:
        order = client.order.fetch(order_id)
    except Exception:
        return {"status": "error", "reason": "order_not_found"}

    notes = order.get("notes") or {}
    try:
        internship_id = int(notes.get("internship_id", 0))
        buyer_user_id = int(notes.get("buyer_user_id", 0))
        kind = notes.get("kind", "")
    except (ValueError, TypeError):
        return {"status": "error", "reason": "invalid_notes"}

    if kind != "internship" or not internship_id or not buyer_user_id:
        return {"status": "error", "reason": "not_an_internship_order"}

    # Verify internship exists
    item = db.query(Internship).filter(Internship.id == internship_id).first()
    if not item:
        return {"status": "error", "reason": "internship_not_found"}

    # Check for existing issued voucher (idempotency)
    existing_voucher = (
        db.query(InternshipVoucher)
        .filter(
            InternshipVoucher.internship_id == internship_id,
            InternshipVoucher.buyer_user_id == buyer_user_id,
            InternshipVoucher.status == "issued",
        )
        .first()
    )
    if existing_voucher:
        return {"status": "already_has_voucher", "voucher_id": existing_voucher.id}

    # Create voucher
    code: Optional[str] = None
    for _ in range(10):
        candidate = _generate_voucher_code()
        clash = db.query(InternshipVoucher).filter(InternshipVoucher.code == candidate).first()
        if not clash:
            code = candidate
            break

    if not code:
        return {"status": "error", "reason": "could_not_generate_code"}

    try:
        voucher = InternshipVoucher(
            code=code,
            internship_id=item.id,
            buyer_user_id=buyer_user_id,
            amount_paid=Decimal(str(float(item.price or 0))),
            razorpay_order_id=order_id,
            razorpay_payment_id=payment.get("id"),
            status="issued",
        )
        db.add(voucher)

        # Add buyer to internship's cohort
        if item.cohort_id:
            already = (
                db.query(CohortMembership)
                .filter(
                    CohortMembership.cohort_id == item.cohort_id,
                    CohortMembership.user_id == buyer_user_id,
                )
                .first()
            )
            if not already:
                db.add(CohortMembership(
                    cohort_id=item.cohort_id,
                    user_id=buyer_user_id,
                ))

        db.commit()
        db.refresh(voucher)

        # Send email (best effort)
        try:
            buyer = db.query(User).filter(User.id == buyer_user_id).first()
            if buyer:
                EmailService.send_internship_voucher_email(buyer, item, voucher.code)
        except Exception:
            pass

        return {"status": "created", "voucher_id": voucher.id, "code": voucher.code}
    except Exception as exc:
        db.rollback()
        return {"status": "error", "reason": str(exc)}
