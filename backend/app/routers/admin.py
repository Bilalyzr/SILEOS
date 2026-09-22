"""
Admin Router - SashaInfinity LMS API
Handles admin operations, user management, and system analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
import logging
import os
import re

from app.core.database import get_db
from app.models.user import User, UserProfile, InstructorProfile, AdminImpersonationLog
from app.models.course import Course, Lesson, CourseCategory, CourseTag, CourseCategoryRelation, CourseTagRelation, CourseReview
from app.models.enrollment import Enrollment, LessonProgress
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer, QuizAttempt
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.payment import Payment, Order, PaymentStatus, OrderStatus, OrderItem
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.models.certificate import Certificate, IssuedCertificate
from app.models.internship_request import InternshipRequest
from app.models.internship import InternshipVoucher
from app.models.company import Company
from app.models.cohort import Cohort
from app.models.blog import BlogPost
from app.models.membership import Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus
from app.models.bundle import Bundle, BundleCourse
from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, InvoiceStatus,
)
from app.schemas.company_dashboard import (
    InternshipRequestItem, InternshipRequestListResponse,
    ApproveInternshipRequestRequest, RejectInternshipRequestRequest,
)
from app.schemas.membership import AdminMembershipOut, AdminPlanOut, PlanCreate, PlanUpdate
from app.schemas.bundle import AdminBundleOut, BundleCreate, BundleUpdate
from app.schemas.company_invoice import (
    InvoiceCreate, InvoiceUpdate, InvoiceOut, InvoiceItemOut, MarkPaidRequest,
)
from app.routers.bundles import _bundle_out
from app.services import invoice_service
from app.services import refund_service
from app.services.invoice_pdf import ensure_invoice_pdf, render_invoice_pdf
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.course_service import CourseService
from app.routers import memberships
from app.schemas.admin import (
    AdminStatsResponse,
    UserManagementResponse,
    CourseManagementResponse,
    RevenueStatsResponse,
    SystemHealthResponse,
    UpdateUserRoleRequest,
    BlogManagementResponse,
    BlogUpdateRequest,
    BlogStatusUpdateRequest,
    BulkDeleteRequest
)

router = APIRouter()

# Initialize logger for this module
logger = logging.getLogger(__name__)

@router.get("/payment-health")
async def payment_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Payment pipeline observability: what needs a human."""
    def _event_row(ev):
        return {
            "event_id": ev.event_id,
            "event_type": ev.event_type,
            "attempts": ev.attempts,
            "last_error": ev.last_error,
            "received_at": ev.received_at.isoformat() if ev.received_at else None,
        }

    failed = (db.query(WebhookEvent)
              .filter(WebhookEvent.status == WebhookEventStatus.FAILED)
              .order_by(WebhookEvent.received_at.desc()).limit(50).all())
    skipped = (db.query(WebhookEvent)
               .filter(WebhookEvent.status == WebhookEventStatus.SKIPPED)
               .order_by(WebhookEvent.received_at.desc()).limit(50).all())

    refunded = (
        db.query(Payment)
        .join(Enrollment, Enrollment.order_id == Payment.order_id)
        .filter(
            Payment.payment_status == PaymentStatus.REFUNDED,
            Enrollment.enrollment_status == "enrolled",
        )
        .limit(50).all()
    )

    # Admin-initiated refunds whose gateway call failed: money did NOT move and
    # access is still intact, so these need an operator to retry (or write off)
    # — a different queue from `refunded_with_active_enrollment`, which is about
    # externally-refunded payments whose access still needs a human decision.
    failed_refunds = (
        db.query(Payment)
        .filter(Payment.refund_status == "failed")
        .order_by(Payment.refund_requested_at.desc())
        .limit(50).all()
    )

    # Refunds still 'requested' long after they were issued: the process
    # crashed between the gateway call and the local commit, so the gateway may
    # already hold a refund we never recorded. Retrying the refund endpoint
    # adopts it rather than issuing a second — but somebody has to look.
    stuck_cutoff = datetime.now(timezone.utc) - refund_service.STALE_REQUESTED_AFTER
    stuck_refunds = (
        db.query(Payment)
        .filter(
            Payment.refund_status == "requested",
            Payment.refund_requested_at.isnot(None),
            Payment.refund_requested_at < stuck_cutoff,
        )
        .order_by(Payment.refund_requested_at.desc())
        .limit(50).all()
    )

    def _minutes_pending(p):
        if not p.refund_requested_at:
            return None
        requested = p.refund_requested_at
        if requested.tzinfo is None:            # SQLite hands back naive UTC
            requested = requested.replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - requested).total_seconds() // 60)
    by_status = {}
    for st in MembershipStatus:
        by_status[st.value] = db.query(Membership).filter(
            Membership.status == st).count()
    memberships_section = {
        "by_status": by_status,
        "in_grace": by_status.get("grace", 0),
    }

    return {
        "failed_events": {"count": len(failed), "items": [_event_row(e) for e in failed]},
        "skipped_events": {"count": len(skipped), "items": [_event_row(e) for e in skipped]},
        "refunded_with_active_enrollment": {
            "count": len(refunded),
            "items": [
                {
                    "gateway_payment_id": p.gateway_payment_id,
                    "order_id": p.order_id,
                    "amount": float(p.amount or 0),
                    "user_id": p.user_id,
                }
                for p in refunded
            ],
        },
        "refunds": {
            # Gateway said no: money did NOT move, access is intact, an
            # operator should retry (the endpoint's retry adopts any refund the
            # gateway turns out to hold).
            "failed": {
                "count": len(failed_refunds),
                "items": [
                    {
                        "order_id": p.order_id,
                        "payment_id": p.id,
                        "gateway_payment_id": p.gateway_payment_id,
                        "amount": float(p.amount or 0),
                        "requested_by": p.refund_requested_by,
                        "requested_at": p.refund_requested_at.isoformat() if p.refund_requested_at else None,
                        "error": p.refund_error or "",
                    }
                    for p in failed_refunds
                ],
            },
            # Claimed but never resolved: the outcome at the gateway is
            # UNKNOWN. Highest-priority queue — money may have moved.
            "stuck": {
                "count": len(stuck_refunds),
                "items": [
                    {
                        "order_id": p.order_id,
                        "payment_id": p.id,
                        "gateway_payment_id": p.gateway_payment_id,
                        "amount": float(p.amount or 0),
                        "requested_by": p.refund_requested_by,
                        "requested_at": p.refund_requested_at.isoformat() if p.refund_requested_at else None,
                        "minutes_pending": _minutes_pending(p),
                    }
                    for p in stuck_refunds
                ],
            },
        },
        "memberships": memberships_section,
    }

@router.post("/memberships/plans", response_model=AdminPlanOut)
async def create_membership_plan(
    request: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    # Validate course ids BEFORE any gateway call — a stale id used to hit the
    # FK on commit and surface as a bare "Internal server error".
    if not request.all_access:
        missing = [
            cid
            for cid in dict.fromkeys(request.course_ids)
            if not db.query(Course.id).filter(Course.id == cid).first()
        ]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"course_ids not found: {missing}",
            )

    # A free plan needs no gateway object; and an unconfigured/unreachable
    # gateway must produce a clean 503, not a raw razorpay error -> 500.
    razorpay_plan_id = None
    if request.price and request.price > 0:
        try:
            client = memberships._rzp_client()
            rzp_plan = client.plan.create({
                "period": request.period,
                "interval": request.interval,
                "item": {
                    "name": request.name,
                    "amount": int(round(request.price * 100)),
                    "currency": "INR",
                },
            })
            razorpay_plan_id = str(rzp_plan["id"])
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Razorpay plan creation failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="Payment gateway rejected the plan. Check the Razorpay keys and try again.",
            )

    plan = MembershipPlan(
        name=request.name, description=request.description,
        all_access=request.all_access, period=request.period,
        interval=request.interval, price=request.price,
        grace_days=request.grace_days,
        razorpay_plan_id=razorpay_plan_id,
    )
    db.add(plan)
    db.flush()
    if not request.all_access:
        for cid in dict.fromkeys(request.course_ids):
            db.add(MembershipPlanCourse(plan_id=plan.id, course_id=cid))
    db.commit()
    db.refresh(plan)
    return _admin_plan_out(db, plan)


@router.get("/memberships/plans", response_model=list[AdminPlanOut])
async def list_membership_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    return [_admin_plan_out(db, p) for p in db.query(MembershipPlan)
            .order_by(MembershipPlan.created_at.desc()).all()]


@router.patch("/memberships/plans/{plan_id}", response_model=AdminPlanOut)
async def update_membership_plan(
    plan_id: int,
    request: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if request.description is not None:
        plan.description = request.description
    if request.is_active is not None:
        plan.is_active = request.is_active
    if request.course_ids is not None and not plan.all_access:
        db.query(MembershipPlanCourse).filter(
            MembershipPlanCourse.plan_id == plan.id).delete()
        for cid in request.course_ids:
            db.add(MembershipPlanCourse(plan_id=plan.id, course_id=cid))
    db.commit()
    db.refresh(plan)
    return _admin_plan_out(db, plan)


@router.get("/memberships", response_model=list[AdminMembershipOut])
async def list_memberships(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    rows = (db.query(Membership, MembershipPlan, User)
            .join(MembershipPlan, MembershipPlan.id == Membership.plan_id)
            .join(User, User.id == Membership.user_id)
            .order_by(Membership.created_at.desc()).limit(200).all())
    return [AdminMembershipOut(
        id=m.id, user_id=u.id, user_email=u.user_email or "",
        plan_name=p.name, status=m.status.value,
        current_period_end=m.current_period_end,
    ) for m, p, u in rows]


class AdminCancelMembershipRequest(BaseModel):
    immediate: bool = False
    # Logged only — Membership has no reason column and the spec adds none.
    reason: str = Field(min_length=1, max_length=500)


@router.post("/memberships/{membership_id}/cancel")
async def admin_cancel_membership(
    membership_id: int,
    request: AdminCancelMembershipRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Admin cancel-subscription (spec §2, R1). immediate=false keeps access
    until period end; immediate=true cancels at the gateway now and suspends
    the materialized membership enrollments (never rows carrying an order_id).
    502 on gateway failure with nothing changed locally; re-running either mode
    on an already-cancelled membership is an idempotent 200 with no gateway
    call."""
    m = db.query(Membership).filter(Membership.id == membership_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")
    memberships.cancel_membership_subscription(
        db, m, immediate=request.immediate, actor_id=current_user.id)
    db.commit()
    db.refresh(m)
    # `reason` is audit context only: never a column, never any user PII.
    logger.info("admin cancel membership_id=%s user_id=%s immediate=%s actor_id=%s reason=%r",
                m.id, m.user_id, request.immediate, current_user.id, request.reason)
    return {
        "success": True,
        "membership_id": m.id,
        "status": m.status.value,
        "cancel_at_period_end": m.cancel_at_period_end,
    }


def _admin_plan_out(db, plan) -> AdminPlanOut:
    from app.services.membership_access import covered_course_ids
    ids = covered_course_ids(db, plan)
    return AdminPlanOut(
        id=plan.id, name=plan.name, description=plan.description or "",
        all_access=plan.all_access, period=plan.period, interval=plan.interval,
        price=float(plan.price), covered_courses=len(ids),
        grace_days=plan.grace_days, razorpay_plan_id=plan.razorpay_plan_id,
        is_active=plan.is_active,
        course_ids=[] if plan.all_access else sorted(ids))


def _admin_bundle_out(db: Session, bundle: Bundle) -> AdminBundleOut:
    out = _bundle_out(db, bundle)
    sales_count = db.query(Order).filter(Order.bundle_id == bundle.id).count()
    return AdminBundleOut(
        **out.model_dump(),
        is_active=bundle.is_active,
        sales_count=sales_count,
    )


def _validate_paid_course_ids(db: Session, course_ids: list[int]) -> list[int]:
    """Dedupe (order-preserving) and confirm every id is a real, publishable
    course. Requiring course_price_type == "paid" made every id fail on
    catalogs whose courses carry the default 'free' price type — the admin
    picker lists all courses, so the whole feature was unusable. Paid-only
    bundling is a pricing decision, not an integrity constraint.
    BundleCourse has no unique constraint on (bundle_id, course_id), so this
    is the only guard against duplicate rows / bogus ids reaching the table."""
    deduped = list(dict.fromkeys(course_ids))
    missing = [
        cid
        for cid in deduped
        if not db.query(Course.id).filter(Course.id == cid).first()
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"course_ids not found: {missing}",
        )
    return deduped


@router.post("/bundles", response_model=AdminBundleOut)
async def create_bundle(
    request: BundleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    course_ids = _validate_paid_course_ids(db, request.course_ids)
    # Cheap pre-check for the common case (admin double-submit / slug reuse)
    # so the friendly 409 doesn't depend on the DB round-trip below. The
    # unique constraint on Bundle.slug is the race-safe net for a concurrent
    # create with the same slug landing between this check and the insert.
    if db.query(Bundle).filter(Bundle.slug == request.slug).first():
        raise HTTPException(
            status_code=409,
            detail="A bundle with this slug already exists",
        )
    bundle = Bundle(
        name=request.name,
        slug=request.slug,
        description=request.description,
        bundle_price=request.bundle_price,
    )
    db.add(bundle)
    db.flush()
    for cid in course_ids:
        db.add(BundleCourse(bundle_id=bundle.id, course_id=cid))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A bundle with this slug already exists",
        )
    db.refresh(bundle)
    return _admin_bundle_out(db, bundle)


@router.get("/bundles", response_model=list[AdminBundleOut])
async def list_bundles_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    bundles = db.query(Bundle).order_by(Bundle.created_at.desc()).all()
    return [_admin_bundle_out(db, b) for b in bundles]


@router.patch("/bundles/{bundle_id}", response_model=AdminBundleOut)
async def update_bundle(
    bundle_id: int,
    request: BundleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if request.name is not None:
        bundle.name = request.name
    if request.description is not None:
        bundle.description = request.description
    if request.bundle_price is not None:
        bundle.bundle_price = request.bundle_price
    if request.is_active is not None:
        bundle.is_active = request.is_active
    if request.course_ids is not None:
        course_ids = _validate_paid_course_ids(db, request.course_ids)
        db.query(BundleCourse).filter(BundleCourse.bundle_id == bundle.id).delete()
        for cid in course_ids:
            db.add(BundleCourse(bundle_id=bundle.id, course_id=cid))
    db.commit()
    db.refresh(bundle)
    return _admin_bundle_out(db, bundle)


# ──────────────────────────────────────────────────────────────────────────
# Company invoices
# ──────────────────────────────────────────────────────────────────────────

def _invoice_out(db: Session, invoice: CompanyInvoice) -> InvoiceOut:
    company = db.query(Company).filter(Company.id == invoice.company_id).first()
    items = db.query(CompanyInvoiceItem).filter(
        CompanyInvoiceItem.invoice_id == invoice.id).order_by(CompanyInvoiceItem.id).all()
    return InvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        company_id=invoice.company_id,
        company_name=company.name if company else f"Company #{invoice.company_id} (record removed)",
        status=invoice.status.value,
        subtotal=float(invoice.subtotal or 0),
        cgst=float(invoice.cgst or 0),
        sgst=float(invoice.sgst or 0),
        igst=float(invoice.igst or 0),
        total=float(invoice.total or 0),
        tax_note=invoice.tax_note or "",
        due_date=invoice.due_date,
        issued_at=invoice.issued_at,
        paid_at=invoice.paid_at,
        paid_via=invoice.paid_via or "",
        payment_reference=invoice.payment_reference or "",
        notes=invoice.notes or "",
        items=[
            InvoiceItemOut(
                id=it.id, description=it.description,
                course_id=it.course_id, bundle_id=it.bundle_id,
                quantity=it.quantity, unit_price=float(it.unit_price),
                line_total=float(it.line_total),
            )
            for it in items
        ],
    )


def _get_invoice_or_404(db: Session, invoice_id: int) -> CompanyInvoice:
    invoice = db.query(CompanyInvoice).filter(CompanyInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/company-invoices", response_model=InvoiceOut)
async def create_company_invoice(
    request: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    company = db.query(Company).filter(Company.id == request.company_id).first()
    if not company or not company.is_approved:
        raise HTTPException(
            status_code=400,
            detail="Company must exist and be approved to invoice",
        )
    subtotal = sum(item.quantity * item.unit_price for item in request.items)
    invoice = CompanyInvoice(
        company_id=company.id,
        status=InvoiceStatus.DRAFT,
        subtotal=subtotal,
        total=subtotal,
        due_date=request.due_date,
        notes=request.notes or "",
    )
    db.add(invoice)
    db.flush()
    for item in request.items:
        db.add(CompanyInvoiceItem(
            invoice_id=invoice.id,
            description=item.description,
            course_id=item.course_id,
            bundle_id=item.bundle_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.quantity * item.unit_price,
        ))
    db.commit()
    db.refresh(invoice)
    return _invoice_out(db, invoice)


@router.get("/company-invoices", response_model=list[InvoiceOut])
async def list_company_invoices(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    q = db.query(CompanyInvoice)
    if status_filter:
        try:
            q = q.filter(CompanyInvoice.status == InvoiceStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
    invoices = q.order_by(CompanyInvoice.created_at.desc()).all()
    return [_invoice_out(db, inv) for inv in invoices]


@router.get("/company-invoices/{invoice_id}", response_model=InvoiceOut)
async def get_company_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    invoice = _get_invoice_or_404(db, invoice_id)
    return _invoice_out(db, invoice)


@router.patch("/company-invoices/{invoice_id}", response_model=InvoiceOut)
async def update_company_invoice(
    invoice_id: int,
    request: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Only draft invoices can be updated")
    if request.due_date is not None:
        invoice.due_date = request.due_date
    if request.notes is not None:
        invoice.notes = request.notes
    if request.items is not None:
        db.query(CompanyInvoiceItem).filter(
            CompanyInvoiceItem.invoice_id == invoice.id).delete()
        subtotal = 0.0
        for item in request.items:
            line_total = item.quantity * item.unit_price
            subtotal += line_total
            db.add(CompanyInvoiceItem(
                invoice_id=invoice.id,
                description=item.description,
                course_id=item.course_id,
                bundle_id=item.bundle_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_total,
            ))
        invoice.subtotal = subtotal
        invoice.total = subtotal
    db.commit()
    db.refresh(invoice)
    return _invoice_out(db, invoice)


@router.post("/company-invoices/{invoice_id}/issue", response_model=InvoiceOut)
async def issue_company_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Only draft invoices can be issued")
    try:
        invoice_service.issue_invoice(db, invoice, pdf_renderer=lambda inv: render_invoice_pdf(db, inv))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    db.refresh(invoice)
    return _invoice_out(db, invoice)


@router.post("/company-invoices/{invoice_id}/cancel", response_model=InvoiceOut)
async def cancel_company_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.ISSUED:
        raise HTTPException(
            status_code=409,
            detail="Only issued, unpaid invoices can be cancelled",
        )
    invoice.status = InvoiceStatus.CANCELLED
    db.commit()
    db.refresh(invoice)
    return _invoice_out(db, invoice)


@router.post("/company-invoices/{invoice_id}/mark-paid", response_model=InvoiceOut)
async def mark_company_invoice_paid(
    invoice_id: int,
    request: MarkPaidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    # Guard concurrent double-settlement: reload with a row lock on postgres
    # (SQLite has no cross-connection concurrency in tests, so the lock is a
    # no-op there and the sequential 409 path is what tests exercise).
    q = db.query(CompanyInvoice).filter(CompanyInvoice.id == invoice_id)
    if db.bind.dialect.name == "postgresql":
        q = q.with_for_update()
    invoice = q.first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != InvoiceStatus.ISSUED:
        raise HTTPException(status_code=409, detail="Only issued invoices can be marked paid")
    ok = invoice_service.settle_invoice(
        db, invoice, via="bank_transfer", reference=request.reference,
    )
    if not ok:
        db.rollback()
        raise HTTPException(status_code=409, detail="Invoice could not be settled")
    db.commit()
    db.refresh(invoice)
    return _invoice_out(db, invoice)


@router.get("/company-invoices/{invoice_id}/pdf")
async def get_company_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    invoice = _get_invoice_or_404(db, invoice_id)
    # Re-render on demand if the file went missing (lost bind mount / recreated
    # volume) — see ensure_invoice_pdf.
    path = ensure_invoice_pdf(db, invoice)
    if not path:
        raise HTTPException(status_code=404, detail="Invoice PDF not available")
    db.commit()
    filename = os.path.basename(path)
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive admin statistics with optional time period filter.
    Period affects the 'new_*_count' fields and revenue_period calculation.
    """
    # Validate period parameter
    valid_periods = {"7d", "30d", "90d", "1y"}
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period '{period}'. Must be one of: {', '.join(sorted(valid_periods))}"
        )
    from app.models.payment import Payment, PaymentStatus
    # User statistics. The raw student count includes unverified and
    # inactive/suspended accounts (e.g. legacy WP-imported rows), which
    # makes the dashboard number look inflated. Break it out so the UI
    # can show the meaningful "active & verified" number as primary and
    # keep the raw total as a secondary hint.
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.user_status == 1).count()  # 1 = active
    students = db.query(User).filter(
        User.role == "student",
        User.user_status == 1,
        User.is_verified.is_(True),
    ).count()
    students_total = db.query(User).filter(User.role == "student").count()
    students_unverified = db.query(User).filter(
        User.role == "student",
        User.is_verified.is_(False),
    ).count()
    instructors = db.query(User).filter(User.role == "instructor").count()
    companies = db.query(User).filter(User.role == "company").count()
    spocs = db.query(User).filter(User.role == "spoc").count()

    # Course statistics
    total_courses = db.query(Course).count()
    # Support both uppercase and lowercase status values
    published_courses = db.query(Course).filter(Course.post_status.in_(["publish", "PUBLISH", "published", "PUBLISHED"])).count()
    draft_courses = db.query(Course).filter(Course.post_status.in_(["draft", "DRAFT"])).count()

    # Enrollment statistics
    total_enrollments = db.query(Enrollment).count()
    completed_enrollments = db.query(Enrollment).filter(
        Enrollment.completion_date.isnot(None)
    ).count()

    # Revenue statistics (course payments + internship vouchers)
    course_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_status == PaymentStatus.COMPLETED
    ).scalar() or 0

    internship_revenue = db.query(func.sum(InternshipVoucher.amount_paid)).scalar() or 0

    total_revenue = course_revenue + internship_revenue

    # Revenue booked in the CURRENT CALENDAR MONTH (month-to-date), independent
    # of the `period` selector above. Month boundaries are computed in IST — the
    # platform's market timezone — to match /admin/revenue-timeseries, so
    # "this month" means what an Indian admin expects rather than a UTC month.
    IST = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(timezone.utc).astimezone(IST)
    month_start_utc = now_ist.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    ).astimezone(timezone.utc)

    monthly_course_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_status == PaymentStatus.COMPLETED,
        Payment.created_at >= month_start_utc,
    ).scalar() or 0
    monthly_internship_revenue = db.query(func.sum(InternshipVoucher.amount_paid)).filter(
        InternshipVoucher.created_at >= month_start_utc,
    ).scalar() or 0
    monthly_revenue = monthly_course_revenue + monthly_internship_revenue

    # Parse period and calculate date range for filtering
    period_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = period_map.get(period, 30)
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # New users/enrollments within the selected period
    new_users_count = db.query(User).filter(
        User.user_registered >= cutoff_date
    ).count()
    new_enrollments_count = db.query(Enrollment).filter(
        Enrollment.enrollment_date >= cutoff_date
    ).count()

    # Recent courses (top by enrollment count)
    # Use a simpler query that gets courses with enrollment counts
    recent_courses_query = db.query(
        Course.id,
        Course.post_title,
        Course.average_rating,
        Course.post_status,
        func.count(Enrollment.id).label('students')
    ).outerjoin(
        Enrollment, Course.id == Enrollment.course_id
    ).group_by(
        Course.id
    ).order_by(
        func.count(Enrollment.id).desc()
    ).limit(5).all()

    recent_courses = []
    for course in recent_courses_query:
        # Get revenue for this course separately via Payment
        from app.models.payment import OrderItem
        revenue = db.query(func.sum(Payment.amount)).join(
            Order, Payment.order_id == Order.id
        ).join(
            OrderItem, Order.id == OrderItem.order_id
        ).filter(
            OrderItem.course_id == course.id,
            Payment.payment_status == PaymentStatus.COMPLETED
        ).scalar() or 0

        recent_courses.append({
            "id": course.id,
            "title": course.post_title,
            "students": course.students,
            "revenue": f"₹{revenue/1000:.1f}L" if revenue >= 1000 else f"₹{revenue}",
            "rating": float(course.average_rating) if course.average_rating else 0,
            "status": "published" if course.post_status and course.post_status.lower() in ["publish", "published"] else "draft"
        })

    # Recent enrollments (last 5)
    recent_enrollments_query = db.query(Enrollment).options(
        joinedload(Enrollment.student),
        joinedload(Enrollment.course)
    ).order_by(
        Enrollment.enrollment_date.desc()
    ).limit(5).all()

    recent_enrollments = []
    for enr in recent_enrollments_query:
        # Get student name from profile, falling back to the account's
        # display_name / login (the User model has no `username` field).
        fallback_name = enr.student.display_name or enr.student.user_login or enr.student.user_email
        if enr.student.profile:
            first = enr.student.profile.first_name or ""
            last = enr.student.profile.last_name or ""
            student_name = f"{first} {last}".strip() or fallback_name
        else:
            student_name = fallback_name
        course_title = enr.course.post_title if enr.course else "Unknown Course"
        # Format date relative to now - handle both naive and aware datetimes
        enr_date = enr.enrollment_date
        if enr_date.tzinfo is not None:
            enr_date = enr_date.replace(tzinfo=None)
        days_ago = (datetime.utcnow() - enr_date).days
        if days_ago == 0:
            date_str = "today"
        elif days_ago == 1:
            date_str = "yesterday"
        elif days_ago < 7:
            date_str = f"{days_ago} days ago"
        elif days_ago < 30:
            weeks = days_ago // 7
            date_str = f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            date_str = enr.enrollment_date.strftime("%b %d")

        recent_enrollments.append({
            "student": student_name,
            "course": course_title,
            "date": date_str,
            "status": "active" if not enr.completion_date else "completed"
        })

    return {
        "user_stats": {
            "total_users": total_users,
            "active_users": active_users,
            "students": students,                      # active + verified only
            "students_total": students_total,          # everyone with role=student
            "students_unverified": students_unverified,
            "instructors": instructors,
            "companies": companies,
            "spocs": spocs,
            "new_users_count": new_users_count
        },
        "course_stats": {
            "total_courses": total_courses,
            "published_courses": published_courses,
            "draft_courses": draft_courses,
            "avg_rating": db.query(func.avg(Course.average_rating)).scalar() or 0,
            "recent_courses": recent_courses
        },
        "enrollment_stats": {
            "total_enrollments": total_enrollments,
            "completed_enrollments": completed_enrollments,
            "completion_rate": (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0,
            "new_enrollments_count": new_enrollments_count,
            "recent_enrollments": recent_enrollments
        },
        "revenue_stats": {
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "monthly_revenue_label": now_ist.strftime("%B %Y"),
            "course_revenue": course_revenue,
            "internship_revenue": internship_revenue,
            "avg_course_price": db.query(func.avg(Course.course_price)).scalar() or 0,
            "revenue_period": (
                db.query(func.sum(Payment.amount)).filter(
                    Payment.payment_status == PaymentStatus.COMPLETED,
                    Payment.created_at >= cutoff_date
                ).scalar() or 0
            ) + (
                db.query(func.sum(InternshipVoucher.amount_paid)).filter(
                    InternshipVoucher.created_at >= cutoff_date
                ).scalar() or 0
            )
        }
    }

@router.get("/revenue-timeseries")
async def get_revenue_timeseries(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Daily revenue for the admin Revenue chart, allocated by source.

    Course revenue = COMPLETED orders (Order.total_amount), bucketed by the
    ORDER DATE (Order.date_created). Internship revenue = internship voucher
    payments (InternshipVoucher.amount_paid), bucketed by purchase date. Each
    point carries the per-source breakdown (`courses`, `internships`) plus their
    sum (`revenue`) so the area chart can stack the respective allocations.
    Days inside the window with no income are emitted as 0 so the chart is
    continuous (no gaps, no missing dates).

    Read-only — no schema/migration. Buckets are computed in Python against
    IST (the platform's market timezone) so the day boundaries match what an
    Indian admin expects, independent of the database's session timezone.
    """
    valid_periods = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period '{period}'. Must be one of: {', '.join(sorted(valid_periods))}",
        )
    days = valid_periods[period]

    IST = timezone(timedelta(hours=5, minutes=30))
    now_utc = datetime.now(timezone.utc)
    # Pull from a day earlier than the window start to absorb the UTC→IST
    # shift, so a payment near the boundary lands in the right bucket.
    start_utc = now_utc - timedelta(days=days + 1)

    def to_ist_date(dt):
        """Normalize a stored timestamp (tz-aware or naive-UTC) to an IST date."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).date()

    course_buckets: Dict[Any, float] = {}
    intern_buckets: Dict[Any, float] = {}

    # Course/product revenue — COMPLETED orders only, allocated to the day the
    # order was placed (Order.date_created). total_amount is the gross order value.
    order_rows = db.query(Order.total_amount, Order.date_created).filter(
        Order.order_status == OrderStatus.COMPLETED,
        Order.date_created >= start_utc,
    ).all()
    for total_amount, date_created in order_rows:
        d = to_ist_date(date_created)
        if d is not None:
            course_buckets[d] = course_buckets.get(d, 0.0) + float(total_amount or 0)

    # Internship voucher revenue, allocated to the purchase date (created_at).
    voucher_rows = db.query(
        InternshipVoucher.amount_paid, InternshipVoucher.created_at
    ).filter(
        InternshipVoucher.created_at >= start_utc,
    ).all()
    for amount_paid, created_at in voucher_rows:
        d = to_ist_date(created_at)
        if d is not None:
            intern_buckets[d] = intern_buckets.get(d, 0.0) + float(amount_paid or 0)

    # Build a continuous day-by-day series ending today (IST), filling zeros.
    today_ist = now_utc.astimezone(IST).date()
    start_ist = today_ist - timedelta(days=days - 1)

    points = []
    total = 0.0
    cursor = start_ist
    while cursor <= today_ist:
        courses = round(course_buckets.get(cursor, 0.0), 2)
        internships = round(intern_buckets.get(cursor, 0.0), 2)
        revenue = round(courses + internships, 2)
        total += revenue
        points.append({
            "date": cursor.isoformat(),          # YYYY-MM-DD
            "label": cursor.strftime("%d %b"),   # e.g. "26 Jun"
            "revenue": revenue,                   # total = courses + internships
            "courses": courses,                   # COMPLETED orders that day
            "internships": internships,           # internship vouchers that day
        })
        cursor += timedelta(days=1)

    return {
        "period": period,
        "currency": "INR",
        "total": round(total, 2),
        "points": points,
    }


@router.get("/users", response_model=List[UserManagementResponse])
async def get_users_for_management(
    response: Response,
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, le=2000),
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get users for admin management with filtering. Returns newest-first
    so recently-registered students are visible by default. Total row
    count (post-filter) is exposed in the `X-Total-Count` response header
    so the frontend can render a proper counter / paginator.
    """
    query = db.query(User).options(
        joinedload(User.profile),
        joinedload(User.enrollments),
        joinedload(User.courses)
    )

    # Apply filters
    if role:
        query = query.filter(User.role == role)

    if status:
        # Convert status string to integer (active=1, inactive=0, suspended=2)
        status_map = {"active": 1, "inactive": 0, "suspended": 2}
        if status in status_map:
            query = query.filter(User.user_status == status_map[status])

    if search:
        query = query.filter(
            User.user_login.contains(search) |
            User.user_email.contains(search) |
            User.display_name.contains(search)
        )

    # Total after filters, for the header. Cheap: single COUNT(*).
    total = query.with_entities(sa_func.count(User.id)).scalar() or 0
    response.headers["X-Total-Count"] = str(total)

    users = (
        query.order_by(User.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Map user_status integer to status string
    def get_status_string(status_int):
        status_map = {0: "inactive", 1: "active", 2: "suspended"}
        return status_map.get(status_int, "inactive")

    return [
        {
            "id": user.id,
            "username": user.user_login,
            "email": user.user_email,
            "display_name": user.display_name,
            "role": user.role,
            "status": get_status_string(user.user_status),
            "is_verified": bool(user.is_verified),
            "joined_date": user.user_registered,
            "last_login": user.last_login,
            "total_courses": len(user.enrollments) if user.role == "student" else len(user.courses),
            "profile_complete": bool(user.profile and user.profile.first_name and user.profile.last_name),
            "phone": (user.profile.phone if user.profile and user.profile.phone else "")
        }
        for user in users
    ]

@router.get("/students")
async def get_students_for_voucher(
    current_user: User = Depends(AuthService.require_admin),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get students who can be added to internship rosters via manual voucher.
    Returns active students with email and display_name for dropdown.
    """
    query = db.query(User).filter(User.role == "student", User.user_status == 1)

    if search:
        query = query.filter(
            User.user_email.contains(search) | User.display_name.contains(search)
        )

    students = query.order_by(User.user_email).limit(500).all()

    return [
        {
            "id": s.id,
            "email": s.user_email,
            "display_name": s.display_name or s.user_email.split("@")[0]
        }
        for s in students
    ]

@router.get("/users/{user_id}", response_model=dict)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed profile for a specific user by ID.
    Used by admins viewing profiles of other users (e.g., SPOCs).
    """
    from app.models.user import UserProfile

    user = db.query(User).options(joinedload(User.profile)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = user.profile

    return {
        "id": user.id,
        "first_name": profile.first_name if profile else "",
        "last_name": profile.last_name if profile else "",
        "email": user.user_email,
        "phone": profile.phone if profile and profile.phone else "",
        "description": profile.description if profile and profile.description else "",
        "designation": profile.designation if profile and profile.designation else "",
        "address": profile.address if profile and profile.address else "",
        "city": profile.city if profile and profile.city else "",
        "state": profile.state if profile and profile.state else "",
        "country": profile.country if profile and profile.country else "",
        "postal_code": profile.postal_code if profile and profile.postal_code else "",
        "profile_photo": profile.profile_photo if profile and profile.profile_photo else "",
        "cover_photo": profile.cover_photo if profile and profile.cover_photo else "",
        "facebook": profile.facebook if profile and profile.facebook else "",
        "twitter": profile.twitter if profile and profile.twitter else "",
        "linkedin": profile.linkedin if profile and profile.linkedin else "",
        "website": profile.website if profile and profile.website else "",
    }

@router.get("/users/{user_id}/stats")
async def get_user_stats(
    user_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Get stats for a SPOC user.
    Returns: my_internships, vouchers_redeemed, pending_interns
    """
    from app.models.internship import Internship, InternshipVoucher

    # Count internships where this user is the SPOC
    my_internships = db.query(Internship).filter(Internship.spoc_user_id == user_id).count()

    # Get internship IDs for this SPOC
    internship_ids = [i[0] for i in db.query(Internship.id).filter(Internship.spoc_user_id == user_id).all()]

    # Count vouchers for this SPOC's internships
    vouchers_redeemed = 0
    pending_interns = 0

    if internship_ids:
        vouchers_redeemed = db.query(InternshipVoucher).filter(
            InternshipVoucher.internship_id.in_(internship_ids),
            InternshipVoucher.status == 'redeemed'
        ).count()

        pending_interns = db.query(InternshipVoucher).filter(
            InternshipVoucher.internship_id.in_(internship_ids),
            InternshipVoucher.status == 'issued'
        ).count()

    result = {
        "my_internships": my_internships,
        "vouchers_redeemed": vouchers_redeemed,
        "pending_interns": pending_interns
    }
    logging.info(f"[SPOC_STATS] user_id={user_id}, result={result}")
    return result

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    new_status: Optional[str] = None,
    status_param: Optional[str] = Query(default=None, alias="status"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user status (activate/deactivate). Accepts either
    `?new_status=...` or `?status=...`.
    """
    new_status = new_status or status_param

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status query parameter is required"
        )

    if new_status not in ["active", "inactive", "suspended"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status"
        )

    # Convert status string to integer
    status_map = {"active": 1, "inactive": 0, "suspended": 2}
    user.user_status = status_map[new_status]

    # `user_status` is display/reporting state only — nothing enforces it.
    # Access is gated on the separate `is_active` boolean
    # (AuthService.get_current_active_user), so writing user_status alone left
    # a user flipped to Inactive in the admin panel still able to log in and
    # use the site. Keep the two in sync, the same way the SPOC edit endpoint
    # already does.
    user.is_active = new_status == "active"

    db.commit()

    return {
        "message": f"User status updated to {new_status}",
        "user_id": user.id,
        "status": new_status,
        "is_active": user.is_active,
    }

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_data: UpdateUserRoleRequest,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user role (e.g., promote student to instructor)
    """
    role = role_data.role

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if role not in ["student", "instructor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )

    old_role = user.role
    user.role = role

    # If promoting to instructor, approve their application if exists
    if role == "instructor":
        instructor_profile = db.query(InstructorProfile).filter(
            InstructorProfile.user_id == user_id
        ).first()
        if instructor_profile:
            instructor_profile.is_approved = True

    db.commit()

    logger.info(f"Admin {current_user.id} changed user {user_id} role from {old_role} to {role}")

    return {"message": f"User role updated to {role}", "old_role": old_role, "new_role": role}


@router.get("/spocs")
async def list_spocs(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Return all users with role='spoc' for the admin cohort-creation dropdown."""
    rows = db.query(User).filter(User.role == "spoc").order_by(User.id.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.user_email,
            "display_name": u.display_name,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at,
        }
        for u in rows
    ]


@router.post("/spocs", status_code=201)
async def create_spoc(
    payload: dict,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin creates a SPOC account directly. Body: {email, password, display_name, phone?}.
    SPOC is created verified + active so they can log in immediately.
    """
    from app.core.security import get_password_hash

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    display_name = (payload.get("display_name") or "").strip()
    phone = payload.get("phone") or ""

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name required")

    if db.query(User).filter(User.user_email == email).first():
        raise HTTPException(status_code=400, detail="A user with that email already exists")

    login = email.split("@")[0][:50] or "spoc"
    base_login = login
    n = 2
    while db.query(User).filter(User.user_login == login).first() is not None:
        login = f"{base_login}{n}"[:60]
        n += 1

    try:
        user = User(
            user_login=login,
            user_pass=get_password_hash(password),
            user_nicename=login,
            user_email=email,
            display_name=display_name,
            role="spoc",
            is_active=True,
            is_verified=True,
            user_status=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {
            "id": user.id,
            "email": user.user_email,
            "display_name": user.display_name,
            "role": user.role,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create SPOC: {e}")


@router.put("/spocs/{user_id}")
async def update_spoc(
    user_id: int,
    payload: dict,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin edits a SPOC's display_name / email / phone / is_active.
    Only these mutable fields are accepted.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SPOC not found")
    if user.role != "spoc":
        raise HTTPException(status_code=400, detail="User is not a SPOC")

    try:
        if "display_name" in payload:
            dn = (payload.get("display_name") or "").strip()
            if not dn:
                raise HTTPException(status_code=400, detail="Display name cannot be empty")
            user.display_name = dn

        if "email" in payload:
            new_email = (payload.get("email") or "").strip().lower()
            if not new_email or "@" not in new_email:
                raise HTTPException(status_code=400, detail="Valid email required")
            if new_email != user.user_email:
                conflict = db.query(User).filter(
                    User.user_email == new_email, User.id != user_id
                ).first()
                if conflict:
                    raise HTTPException(status_code=400, detail="Email already in use")
                user.user_email = new_email

        if "is_active" in payload:
            user.is_active = bool(payload.get("is_active"))
            # mirror to user_status for consistency with listing filters
            user.user_status = 1 if user.is_active else 0

        if "phone" in payload:
            phone_val = (payload.get("phone") or "").strip()
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if profile is None:
                profile = UserProfile(user_id=user_id, phone=phone_val)
                db.add(profile)
            else:
                profile.phone = phone_val

        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update SPOC: {e}")

    return {
        "id": user.id,
        "email": user.user_email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
    }


@router.delete("/spocs/{user_id}")
async def delete_spoc(
    user_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Delete a SPOC. Rejects with 400 if the SPOC is still assigned to any
    Internship or Cohort — lists the blockers so the admin can reassign.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="SPOC not found")
    if user.role != "spoc":
        raise HTTPException(status_code=400, detail="User is not a SPOC")

    try:
        from app.models.internship import Internship
        from app.models.cohort import Cohort

        internships = db.query(Internship).filter(
            Internship.spoc_user_id == user_id
        ).all()
        cohorts = db.query(Cohort).filter(Cohort.spoc_user_id == user_id).all()

        if internships or cohorts:
            blockers = []
            for i in internships:
                blockers.append(f"Internship: {i.title}")
            for c in cohorts:
                blockers.append(f"Cohort: {c.name}")
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cannot delete — SPOC is still assigned to: "
                    + "; ".join(blockers)
                ),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conflict check failed: {e}")

    try:
        # SPOC users have no enrollments / vouchers / courses. Drop profile + user.
        db.query(UserProfile).filter(UserProfile.user_id == user_id).delete(
            synchronize_session=False
        )
        db.delete(user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete SPOC: {e}")

    return {"message": f"SPOC {user.display_name} deleted"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a user and all their related data
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # If instructor, delete all their courses and related content
    if user.role == "instructor":
        # Get all courses by this instructor
        courses = db.query(Course).filter(Course.post_author == user_id).all()
        course_ids = [c.id for c in courses]

        if course_ids:
            # Delete certificates issued for these courses
            db.query(IssuedCertificate).filter(
                IssuedCertificate.course_id.in_(course_ids)
            ).delete(synchronize_session=False)

            # Delete quiz attempts for these courses
            db.query(QuizAttempt).filter(
                QuizAttempt.course_id.in_(course_ids)
            ).delete(synchronize_session=False)

            # Delete quiz question answers
            quizzes = db.query(Quiz).filter(Quiz.post_parent.in_(course_ids)).all()
            quiz_ids = [q.id for q in quizzes]
            if quiz_ids:
                questions = db.query(QuizQuestion).filter(
                    QuizQuestion.quiz_id.in_(quiz_ids)
                ).all()
                question_ids = [q.question_id for q in questions]
                if question_ids:
                    db.query(QuizQuestionAnswer).filter(
                        QuizQuestionAnswer.belongs_question_id.in_(question_ids)
                    ).delete(synchronize_session=False)
                    db.query(QuizQuestion).filter(
                        QuizQuestion.quiz_id.in_(quiz_ids)
                    ).delete(synchronize_session=False)
                db.query(Quiz).filter(Quiz.post_parent.in_(course_ids)).delete(synchronize_session=False)

            # Delete assignments and submissions
            assignments = db.query(Assignment).filter(
                Assignment.course_id.in_(course_ids)
            ).all()
            assignment_ids = [a.id for a in assignments]
            if assignment_ids:
                db.query(AssignmentSubmission).filter(
                    AssignmentSubmission.assignment_id.in_(assignment_ids)
                ).delete(synchronize_session=False)
                db.query(Assignment).filter(
                    Assignment.course_id.in_(course_ids)
                ).delete(synchronize_session=False)

            # Delete lesson progress for these courses
            db.query(LessonProgress).filter(
                LessonProgress.course_id.in_(course_ids)
            ).delete(synchronize_session=False)

            # Delete enrollments in these courses
            db.query(Enrollment).filter(
                Enrollment.course_id.in_(course_ids)
            ).delete(synchronize_session=False)

            # Delete payments and order items related to these courses
            db.query(OrderItem).filter(
                OrderItem.course_id.in_(course_ids)
            ).delete(synchronize_session=False)

            # Delete lessons
            db.query(Lesson).filter(
                Lesson.post_parent.in_(course_ids)
            ).delete(synchronize_session=False)

            # Delete courses
            db.query(Course).filter(
                Course.post_author == user_id
            ).delete(synchronize_session=False)

        # Delete instructor earnings
        from app.models.payment import Earning
        db.query(Earning).filter(Earning.user_id == user_id).delete(synchronize_session=False)

        # Delete instructor withdrawals
        from app.models.payment import Withdrawal
        db.query(Withdrawal).filter(Withdrawal.user_id == user_id).delete(synchronize_session=False)

    # Delete user-specific data (for all users including students)

    # Delete lesson progress for this user
    db.query(LessonProgress).filter(LessonProgress.user_id == user_id).delete(synchronize_session=False)

    # Delete quiz attempts for this user
    db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).delete(synchronize_session=False)

    # Delete assignment submissions for this user
    db.query(AssignmentSubmission).filter(AssignmentSubmission.user_id == user_id).delete(synchronize_session=False)

    # Delete certificates issued to this user
    db.query(IssuedCertificate).filter(IssuedCertificate.user_id == user_id).delete(synchronize_session=False)

    # Delete enrollments for this user
    db.query(Enrollment).filter(Enrollment.user_id == user_id).delete(synchronize_session=False)

    # Delete orders and order items for this user
    orders = db.query(Order).filter(Order.user_id == user_id).all()
    for order in orders:
        # Delete order items first
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete(synchronize_session=False)
    db.query(Order).filter(Order.user_id == user_id).delete(synchronize_session=False)

    # Delete wishlist items for this user
    from app.models.enrollment import WishlistItem
    db.query(WishlistItem).filter(WishlistItem.user_id == user_id).delete(synchronize_session=False)

    # Delete course reviews by this user
    db.query(CourseReview).filter(CourseReview.user_id == user_id).delete(synchronize_session=False)

    # Delete blog posts by this user
    from app.models.blog import BlogPost
    db.query(BlogPost).filter(BlogPost.author_id == user_id).delete(synchronize_session=False)

    # Delete coupon usage records for this user (coupons they used)
    from app.models.coupon import Coupon, CouponUsage
    db.query(CouponUsage).filter(CouponUsage.user_id == user_id).delete(synchronize_session=False)
    # Delete coupons created by this user (if admin/instructor)
    db.query(Coupon).filter(Coupon.created_by == user_id).delete(synchronize_session=False)

    # Delete candidate profile if exists
    try:
        from app.models.candidate import CandidateProfile, CandidateEligibility
        db.query(CandidateEligibility).filter(CandidateEligibility.user_id == user_id).delete(synchronize_session=False)
        db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).delete(synchronize_session=False)
    except ImportError:
        pass

    # Delete internship-related records for this user
    try:
        from app.models.internship import InternshipVoucher, InternshipAttendance
        db.query(InternshipVoucher).filter(InternshipVoucher.buyer_user_id == user_id).delete(synchronize_session=False)
        db.query(InternshipAttendance).filter(InternshipAttendance.user_id == user_id).delete(synchronize_session=False)
    except ImportError:
        pass

    # Delete cohort membership if exists
    try:
        from app.models.cohort import CohortMembership
        db.query(CohortMembership).filter(CohortMembership.user_id == user_id).delete(synchronize_session=False)
    except ImportError:
        pass

    # Delete page views for this user if table exists
    try:
        from app.models.page_view import PageView
        db.query(PageView).filter(PageView.user_id == user_id).delete(synchronize_session=False)
    except ImportError:
        pass

    # Delete admin impersonation logs for this user (as admin or target)
    db.query(AdminImpersonationLog).filter(
        (AdminImpersonationLog.admin_user_id == user_id) |
        (AdminImpersonationLog.target_user_id == user_id)
    ).delete(synchronize_session=False)

    # Delete instructor profile if exists
    db.query(InstructorProfile).filter(InstructorProfile.user_id == user_id).delete(synchronize_session=False)

    # Delete user profile
    db.query(UserProfile).filter(UserProfile.user_id == user_id).delete(synchronize_session=False)

    # Delete user roles
    from app.models.user import UserRole
    db.query(UserRole).filter(UserRole.user_id == user_id).delete(synchronize_session=False)

    # Delete user
    db.delete(user)
    db.commit()

    return {"message": f"User {user.display_name} and all associated data have been deleted successfully"}


@router.post("/users/{user_id}/password-reset-link")
async def generate_user_password_reset_link(
    user_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate a ONE-TIME password reset link for a user and return it once.

    Reuses the exact single-use reset-token mechanism from
    `auth.forgot_password`/`auth.reset_password` (a JWT with a jti marker
    persisted on `user_activation_key`, cleared on first use) rather than
    inventing a parallel one. The admin never sees or sets the user's actual
    password — only this one-time link, which the admin must hand to the
    user out of band (email/chat). There is no `must_change_password` flag
    on the User model in this codebase, so that part of the standard
    "forced change on next login" pattern is intentionally not implemented
    here; the link itself already forces a password CHANGE (old password
    stops working the moment it's used) which meets the spirit of the
    requirement without a schema migration.
    """
    import secrets
    from app.core.security import create_access_token
    from app.routers.auth import _RESET_KEY_PREFIX

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    reset_jti = secrets.token_urlsafe(24)
    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "password_reset", "jti": reset_jti},
        expires_delta=timedelta(hours=1)
    )
    user.user_activation_key = f"{_RESET_KEY_PREFIX}{reset_jti}"
    db.commit()

    from app.core.config import get_settings
    settings = get_settings()
    frontend_url = (settings.FRONTEND_URL or "").rstrip("/")
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"

    logger.info(
        "Admin %s generated a one-time password reset link for user_id=%s",
        current_user.id, user.id,
    )

    return {
        "message": "One-time password reset link generated. Share it with the user — it will not be shown again.",
        "user_id": user.id,
        "reset_link": reset_link,
        "expires_in_hours": 1,
    }


@router.get("/courses", response_model=List[CourseManagementResponse])
async def get_courses_for_management(
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    status: Optional[str] = None,
    instructor_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get courses for admin management
    """
    query = db.query(Course).options(joinedload(Course.instructor).joinedload(User.profile))

    if status:
        query = query.filter(Course.post_status == status)

    if instructor_id:
        query = query.filter(Course.post_author == instructor_id)

    courses = query.offset(skip).limit(limit).all()

    return [
        {
            "id": course.id,
            "title": course.post_title,
            "instructor_name": course.instructor.display_name if course.instructor else "Unknown",
            "status": course.post_status,
            "price": float(course.course_price) if course.course_price else 0.0,
            "enrolled_students": course.total_enrollments or 0,
            "rating": float(course.average_rating) if course.average_rating else 0.0,
            "video_view_count": course.video_view_count or 0,
            "banner_url": course.course_thumbnail or "",
            "created_at": course.created_at,
            "updated_at": course.updated_at
        }
        for course in courses
    ]

@router.put("/courses/{course_id}/status")
async def update_course_status(
    course_id: int,
    course_status: str,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Update course status (publish/draft/pending/private)
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Accept course status conventions: publish, draft, pending, private, archive
    if course_status not in ["draft", "publish", "pending", "private", "archive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course status. Must be: draft, publish, pending, private, or archive"
        )

    course.post_status = course_status
    db.commit()

    return {"message": f"Course status updated to {course_status}"}

@router.get("/instructor-applications")
async def get_instructor_applications(
    current_user: User = Depends(AuthService.require_admin),
    status: Optional[str] = Query("pending"),
    db: Session = Depends(get_db)
):
    """
    Get instructor applications (pending = not approved and not blocked)
    """
    query = db.query(InstructorProfile).options(
        joinedload(InstructorProfile.user)
    )

    if status == "pending":
        query = query.filter(
            InstructorProfile.is_approved == False,
            InstructorProfile.is_blocked == False
        )
    elif status == "approved":
        query = query.filter(InstructorProfile.is_approved == True)
    elif status == "rejected":
        query = query.filter(InstructorProfile.is_blocked == True)

    applications = query.all()

    return [
        {
            "id": app.id,
            "user_id": app.user_id,
            "username": app.user.user_login,
            "email": app.user.user_email,
            "display_name": app.user.display_name,
            "bio": app.instructor_bio or "",
            "designation": app.instructor_designation or "",
            "is_approved": app.is_approved,
            "is_blocked": app.is_blocked,
            "applied_at": app.created_at
        }
        for app in applications
    ]

@router.put("/instructor-applications/{application_id}")
async def process_instructor_application(
    application_id: int,
    action: str = Query(..., description="approve or reject"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve or reject instructor application
    """
    application = db.query(InstructorProfile).filter(
        InstructorProfile.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    if action not in ["approve", "reject"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'approve' or 'reject'"
        )

    if action == "approve":
        application.is_approved = True
        application.is_blocked = False
        print(f"✓ Approved instructor application ID {application_id} for user ID {application.user_id}")
    else:
        application.is_approved = False
        application.is_blocked = True
        print(f"✗ Rejected instructor application ID {application_id} for user ID {application.user_id}")

    db.commit()

    return {"message": f"Application {action}d successfully"}

@router.get("/revenue")
async def get_revenue_analytics(
    current_user: User = Depends(AuthService.require_admin),
    period: str = Query("30d"),  # 7d, 30d, 90d, 1y, all
    db: Session = Depends(get_db)
):
    """
    Get revenue analytics - includes course payments AND internship vouchers.
    """
    # Calculate date range
    if period == "7d":
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        start_date = datetime.utcnow() - timedelta(days=30)
    elif period == "90d":
        start_date = datetime.utcnow() - timedelta(days=90)
    elif period == "1y":
        start_date = datetime.utcnow() - timedelta(days=365)
    elif period == "all":
        start_date = datetime.min.replace(tzinfo=timezone.utc)
    else:
        start_date = datetime.utcnow() - timedelta(days=30)

    # Get course payments revenue
    payments = db.query(Payment).filter(
        Payment.payment_status == PaymentStatus.COMPLETED,
        Payment.created_at >= start_date
    ).all()

    # Cast Decimal -> float so it can be added to the float internship revenue
    # below without raising a Decimal/float TypeError.
    course_revenue = float(sum([p.amount for p in payments]))
    course_transactions = len(payments)

    # Get internship voucher revenue (all issued vouchers)
    from app.models.internship import InternshipVoucher, Internship
    vouchers = db.query(InternshipVoucher).filter(
        InternshipVoucher.created_at >= start_date
    ).all()

    internship_revenue = sum([float(v.amount_paid) for v in vouchers])
    internship_transactions = len(vouchers)

    # Combine
    total_revenue = course_revenue + internship_revenue
    total_transactions = course_transactions + internship_transactions

    # Revenue by course. A Payment has no direct course_id — it belongs to an
    # Order, whose order_items carry the purchased course(s). Each payment's
    # gross amount is split across the course(s) it bought (weighted by line-item
    # value) so the per-course revenue reconciles with total_revenue, and a
    # payment counts as one transaction per distinct course (not per line item).
    # Payments whose order has no resolvable course fall into "Uncategorized" so
    # nothing silently drops out of the breakdown.
    course_breakdown = {}
    for payment in payments:
        pay_amount = float(payment.amount or 0)
        order = payment.order
        items = list(order.order_items) if order else []

        titles: dict = {}
        weights: dict = {}
        for item in items:
            # An ebook line has course_id NULL and ebook_id set (migration
            # 0005 relaxed course_id). Keying it on None would collapse every
            # ebook sale into one row labelled "Course #None"; key it on the
            # ebook instead so the breakdown names the product that was sold.
            ebook_id = getattr(item, "ebook_id", None)
            if item.course_id is None and ebook_id is not None:
                key = f"ebook:{ebook_id}"
                titles.setdefault(
                    key, item.order_item_name or f"Ebook #{ebook_id}")
            else:
                key = item.course_id
                titles.setdefault(
                    key,
                    item.course.post_title if item.course
                    else (item.order_item_name or f"Course #{key}"),
                )
            weights[key] = weights.get(key, 0.0) + float(item.total or 0)

        if weights:
            total_weight = sum(weights.values())
            for course_id, weight in weights.items():
                share = (weight / total_weight) if total_weight > 0 else (1.0 / len(weights))
                entry = course_breakdown.setdefault(
                    course_id,
                    {"course_title": titles[course_id], "revenue": 0.0, "transactions": 0},
                )
                entry["revenue"] += pay_amount * share
                entry["transactions"] += 1
        else:
            entry = course_breakdown.setdefault(
                "uncategorized",
                {"course_title": "Uncategorized", "revenue": 0.0, "transactions": 0},
            )
            entry["revenue"] += pay_amount
            entry["transactions"] += 1

    # Add internships as a "course" category
    if internship_revenue > 0:
        course_breakdown["internships"] = {
            "course_title": "Internship Programs",
            "revenue": internship_revenue,
            "transactions": internship_transactions
        }

    # Top by revenue
    top_courses = sorted(
        course_breakdown.values(),
        key=lambda x: x["revenue"],
        reverse=True
    )[:10]

    return {
        "period": period,
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "avg_transaction_value": total_revenue / total_transactions if total_transactions > 0 else 0,
        "course_revenue": course_revenue,
        "internship_revenue": internship_revenue,
        "top_courses": top_courses
    }

@router.get("/system-health")
async def get_system_health(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Get system health metrics
    """
    # Database health
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    # Recent activity
    recent_users = db.query(User).filter(
        User.user_registered >= datetime.utcnow() - timedelta(hours=24)
    ).count()

    recent_enrollments = db.query(Enrollment).filter(
        Enrollment.enrollment_date >= datetime.utcnow() - timedelta(hours=24)
    ).count()

    recent_payments = db.query(Payment).filter(
        Payment.created_at >= datetime.utcnow() - timedelta(hours=24),
        Payment.payment_status == PaymentStatus.COMPLETED
    ).count()

    return {
        "database_status": db_status,
        "total_users": db.query(User).count(),
        "total_courses": db.query(Course).count(),
        "recent_activity_24h": {
            "new_users": recent_users,
            "new_enrollments": recent_enrollments,
            "completed_payments": recent_payments
        },
        "server_time": datetime.utcnow(),
        "uptime": "healthy"  # This would typically come from system metrics
    }

class AdminGrantEnrollmentIn(BaseModel):
    user_id: int
    course_id: int


@router.post("/enrollments")
async def admin_grant_enrollment(
    payload: AdminGrantEnrollmentIn,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin manually grants a course enrollment (comp seat, support gesture,
    etc.) with no order behind it. Uses the shared
    `fulfillment_service.grant_purchased_course` rescue helper — the same
    "enroll or rescue a suspended row" semantics as every other fulfillment
    path — with `source="admin"` and `order_id=None`. Returns 409 if the
    user is already actively enrolled (not a rescue case).
    """
    from app.services.fulfillment_service import grant_purchased_course

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    existing = db.query(Enrollment).filter(
        Enrollment.user_id == payload.user_id,
        Enrollment.course_id == payload.course_id,
    ).first()
    if existing is not None and existing.enrollment_status == "enrolled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already enrolled in this course",
        )

    try:
        changed = grant_purchased_course(
            db, user_id=payload.user_id, course_id=payload.course_id,
            order_id=None, source="admin",
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant enrollment: {exc}",
        )

    logger.info(
        "Admin %s granted enrollment for user_id=%s course_id=%s (changed=%s)",
        current_user.id, payload.user_id, payload.course_id, changed,
    )

    return {
        "message": "Enrollment granted",
        "user_id": payload.user_id,
        "course_id": payload.course_id,
        "newly_granted": changed,
    }


@router.get("/enrollments")
async def get_enrollments(
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status: Optional[str] = None,
    course_id: Optional[int] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get all enrollments with filtering options
    """
    query = db.query(Enrollment).options(
        joinedload(Enrollment.student),
        joinedload(Enrollment.course)
    )

    if status:
        query = query.filter(Enrollment.enrollment_status == status)

    if course_id:
        query = query.filter(Enrollment.course_id == course_id)

    if student_id:
        query = query.filter(Enrollment.user_id == student_id)

    enrollments = query.order_by(desc(Enrollment.enrollment_date)).offset(skip).limit(limit).all()

    return [
        {
            "id": enrollment.id,
            "student_name": enrollment.student.display_name,
            "student_email": enrollment.student.user_email,
            "course_title": enrollment.course.post_title,
            "course_id": enrollment.course_id,
            "enrollment_date": enrollment.enrollment_date,
            "status": enrollment.enrollment_status,
            "progress": enrollment.course_progress_percentage,
            "completed_lessons": enrollment.completed_lessons,
            "total_lessons": enrollment.total_lessons,
            "completion_date": enrollment.completion_date
        }
        for enrollment in enrollments
    ]

@router.put("/enrollments/{enrollment_id}/status")
async def update_enrollment_status(
    enrollment_id: int,
    new_status: Optional[str] = None,
    status_param: Optional[str] = Query(default=None, alias="status"),
    reason: Optional[str] = None,
    notify_student: bool = True,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Update enrollment status with enhanced options for admin management.
    Accepts either `?new_status=...` (canonical) or `?status=...` (legacy,
    kept for the admin UI that was written before the rename).
    """
    from app.services.email_service import EmailService

    # Accept both query-param names. The status module import is not
    # shadowed here because we never bind the parameter to the name
    # `status` directly — FastAPI maps the `status` query to status_param.
    new_status = new_status or status_param

    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found"
        )

    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status query parameter is required"
        )

    if new_status not in ["enrolled", "completed", "cancelled", "suspended"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be: enrolled, completed, cancelled, or suspended"
        )

    old_status = enrollment.enrollment_status
    enrollment.enrollment_status = new_status

    # Set completion date if status is completed (tz-aware to match column type)
    if new_status == "completed" and not enrollment.completion_date:
        enrollment.completion_date = datetime.now(timezone.utc)
        # Recalculate progress to sync counters when marking as completed
        CourseService.calculate_course_progress(db, enrollment)
        # The recalc can REVERT the "completed" override above: when the
        # student hasn't actually finished all course content, its
        # regression branch resets the status back to "enrolled" (and
        # clears completion_date). Re-read the row so the notification and
        # the response below report the FINAL status, not the requested
        # one — never claim completion that was just rolled back.
        db.refresh(enrollment)
        new_status = enrollment.enrollment_status

    # Handle status change notifications
    if notify_student and old_status != new_status:
        try:
            # Prepare notification details
            notification_data = {
                'student_name': enrollment.student.display_name,
                'student_email': enrollment.student.user_email,
                'course_title': enrollment.course.post_title,
                'course_id': enrollment.course_id,
                'old_status': old_status,
                'new_status': new_status,
                'changed_by': current_user.display_name,
                'reason': reason or 'Administrative action'
            }

            # Send appropriate notification based on status change
            if new_status == "cancelled":
                EmailService.send_enrollment_termination_notice(
                    student_email=enrollment.student.user_email,
                    student_name=enrollment.student.display_name,
                    course_title=enrollment.course.post_title,
                    reason=f"Cancelled by administrator: {reason or 'Administrative action'}"
                )
            elif new_status == "suspended":
                EmailService.send_enrollment_suspension_notice(
                    student_email=enrollment.student.user_email,
                    student_name=enrollment.student.display_name,
                    course_title=enrollment.course.post_title,
                    reason=f"Suspended by administrator: {reason or 'Administrative action'}"
                )
            elif new_status == "completed":
                EmailService.send_enrollment_completion_notification(
                    student_email=enrollment.student.user_email,
                    student_name=enrollment.student.display_name,
                    course_title=enrollment.course.post_title,
                    course_id=enrollment.course_id,
                    completed_by=current_user.display_name,
                    reason=f"Marked as completed by administrator: {reason or 'Administrative action'}"
                )

            logger.info(f"✅ Sent enrollment status change notification to {enrollment.student.user_email}")

        except Exception as e:
            logger.error(f"❌ Failed to send enrollment notification: {e}")
            # Don't raise the error - continue with the status update

    db.commit()

    return {
        "message": f"Enrollment status updated from {old_status} to {new_status}",
        "enrollment_id": enrollment_id,
        "student_name": enrollment.student.display_name,
        "course_title": enrollment.course.post_title,
        "notification_sent": notify_student and old_status != new_status
    }

@router.put("/enrollments/bulk-update")
async def bulk_update_enrollment_status(
    enrollment_ids: List[int],
    new_status: Optional[str] = None,
    status_param: Optional[str] = Query(default=None, alias="status"),
    reason: Optional[str] = None,
    notify_students: bool = True,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Bulk update enrollment status for multiple enrollments. Accepts either
    `?new_status=...` or `?status=...`.

    A `completed` force-override runs the progress recalc per enrollment, so
    a below-100% student is reverted to `enrolled` before any completion is
    reported or mailed — the same post-recalc semantics as the single
    PUT /enrollments/{id}/status endpoint.
    """
    from app.services.email_service import EmailService

    new_status = new_status or status_param
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status query parameter is required"
        )

    # Get all enrollments
    enrollments = db.query(Enrollment).filter(
        Enrollment.id.in_(enrollment_ids)
    ).all()

    if not enrollments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No enrollments found with provided IDs"
        )

    # Validate status
    if new_status not in ["enrolled", "completed", "cancelled", "suspended"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be: enrolled, completed, cancelled, or suspended"
        )

    updated_count = 0
    notification_count = 0

    for enrollment in enrollments:
        old_status = enrollment.enrollment_status
        enrollment.enrollment_status = new_status

        # Set completion date if status is completed (tz-aware column),
        # then recalculate progress — mirroring the single
        # update_enrollment_status endpoint. The recalc can REVERT the
        # "completed" override above: when the student hasn't actually
        # finished all course content, its regression branch resets the
        # status back to "enrolled" (and clears completion_date).
        if new_status == "completed" and not enrollment.completion_date:
            enrollment.completion_date = datetime.now(timezone.utc)
            CourseService.calculate_course_progress(db, enrollment)
            # Re-read the row so notifications and counts below report the
            # FINAL status, not the requested one — never claim (or mail
            # about) a completion that was just rolled back.
            db.refresh(enrollment)

        # Post-recalc status for THIS row: equal to new_status unless the
        # recalc reverted a below-100% force-complete.
        effective_status = enrollment.enrollment_status

        updated_count += 1

        # Send notification if requested and status changed (notifications
        # branch on the effective status, so a reverted force-complete
        # fires nothing at all).
        if notify_students and old_status != effective_status:
            try:
                if effective_status == "cancelled":
                    EmailService.send_enrollment_termination_notice(
                        student_email=enrollment.student.user_email,
                        student_name=enrollment.student.display_name,
                        course_title=enrollment.course.post_title,
                        reason=f"Bulk cancelled by administrator: {reason or 'Administrative action'}"
                    )
                elif effective_status == "suspended":
                    EmailService.send_enrollment_suspension_notice(
                        student_email=enrollment.student.user_email,
                        student_name=enrollment.student.display_name,
                        course_title=enrollment.course.post_title,
                        reason=f"Bulk suspended by administrator: {reason or 'Administrative action'}"
                    )
                elif effective_status == "completed":
                    EmailService.send_enrollment_completion_notification(
                        student_email=enrollment.student.user_email,
                        student_name=enrollment.student.display_name,
                        course_title=enrollment.course.post_title,
                        course_id=enrollment.course_id,
                        completed_by=current_user.display_name,
                        reason=f"Bulk marked as completed by administrator: {reason or 'Administrative action'}"
                    )
                notification_count += 1
                logger.info(f"✅ Sent bulk notification to {enrollment.student.user_email}")

            except Exception as e:
                logger.error(f"❌ Failed to send bulk notification to {enrollment.student.user_email}: {e}")

    db.commit()

    return {
        "message": f"Bulk update completed: {updated_count} enrollments updated",
        "status_changed_to": new_status,
        "enrollments_updated": updated_count,
        "notifications_sent": notification_count,
        "total_notifications_requested": len(enrollments) if notify_students else 0,
        "changed_by": current_user.display_name,
        "reason": reason
    }

@router.delete("/courses/{course_id}/with-enrollments")
async def delete_course_with_enrollments(
    course_id: int,
    send_notifications: bool = True,
    refund_enrolled_students: bool = False,
    reason: Optional[str] = None,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a course and all its associated enrollments with proper notifications
    """
    from app.services.email_service import EmailService

    # Get course details
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Get all enrollments for this course
    enrollments = db.query(Enrollment).filter(
        Enrollment.course_id == course_id
    ).all()

    # Prepare notification data
    notifications = []
    for enrollment in enrollments:
        notifications.append({
            'student_email': enrollment.student.user_email,
            'student_name': enrollment.student.display_name,
            'course_title': course.post_title,
            'course_id': course_id,
            'deleted_by': current_user.display_name,
            'reason': reason or 'Course removed by administrator'
        })

    # Delete all related data (similar to existing user deletion logic but for course)
    try:
        # Delete certificates
        db.query(IssuedCertificate).filter(
            IssuedCertificate.course_id == course_id
        ).delete(synchronize_session=False)

        # Delete quiz attempts
        db.query(QuizAttempt).filter(
            QuizAttempt.course_id == course_id
        ).delete(synchronize_session=False)

        # Delete quiz content
        quizzes = db.query(Quiz).filter(Quiz.post_parent == course_id).all()
        quiz_ids = [q.id for q in quizzes]
        if quiz_ids:
            questions = db.query(QuizQuestion).filter(
                QuizQuestion.quiz_id.in_(quiz_ids)
            ).all()
            question_ids = [q.question_id for q in questions]
            if question_ids:
                db.query(QuizQuestionAnswer).filter(
                    QuizQuestionAnswer.belongs_question_id.in_(question_ids)
                ).delete(synchronize_session=False)
                db.query(QuizQuestion).filter(
                    QuizQuestion.quiz_id.in_(quiz_ids)
                ).delete(synchronize_session=False)
            db.query(Quiz).filter(Quiz.post_parent == course_id).delete(synchronize_session=False)

        # Delete assignments and submissions
        assignments = db.query(Assignment).filter(
            Assignment.course_id == course_id
        ).all()
        assignment_ids = [a.id for a in assignments]
        if assignment_ids:
            db.query(AssignmentSubmission).filter(
                AssignmentSubmission.assignment_id.in_(assignment_ids)
            ).delete(synchronize_session=False)
            db.query(Assignment).filter(
                Assignment.course_id == course_id
            ).delete(synchronize_session=False)

        # Delete lesson progress
        db.query(LessonProgress).filter(
            LessonProgress.course_id == course_id
        ).delete(synchronize_session=False)

        # Delete enrollments
        enrollment_ids = [e.id for e in enrollments]
        db.query(Enrollment).filter(
            Enrollment.course_id == course_id
        ).delete(synchronize_session=False)

        # Delete payments and order items related to this course
        db.query(OrderItem).filter(
            OrderItem.course_id == course_id
        ).delete(synchronize_session=False)

        # Delete lessons
        db.query(Lesson).filter(
            Lesson.post_parent == course_id
        ).delete(synchronize_session=False)

        # Delete the course
        db.delete(course)
        db.commit()

        # Send notifications if requested
        if send_notifications and notifications:
            try:
                result = EmailService.send_bulk_course_deletion_notifications(notifications)
                logger.info(f"✅ Sent {result['sent']} deletion notifications, {result['failed']} failed")
            except Exception as e:
                logger.error(f"❌ Failed to send bulk deletion notifications: {e}")

        return {
            "message": f"Course '{course.post_title}' and all related data have been deleted successfully",
            "course_id": course_id,
            "course_title": course.post_title,
            "enrollments_affected": len(enrollments),
            "notifications_sent": len(notifications) if send_notifications else 0,
            "refund_requested": refund_enrolled_students,
            "deleted_by": current_user.display_name,
            "reason": reason or "Course removed by administrator"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to delete course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}"
        )

@router.get("/pending-submissions")
async def pending_submissions(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """All assignment submissions awaiting review, for the admin approvals queue."""
    from app.models.assignment import SubmissionStatus
    subs = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.status == SubmissionStatus.SUBMITTED
    ).all()
    out = []
    for s in subs:
        a = db.query(Assignment).filter(Assignment.id == s.assignment_id).first()
        c = db.query(Course).filter(Course.id == a.course_id).first() if a else None
        enr = None
        if c:
            enr = db.query(Enrollment).filter(
                Enrollment.user_id == s.user_id,
                Enrollment.course_id == c.id,
                Enrollment.completion_date.isnot(None),
            ).first()
        out.append({
            "submission_id": s.id,
            "student_name": s.student.display_name if s.student else "Unknown",
            "course_title": c.post_title if c else "Unknown",
            "assignment_title": a.title if a else "Unknown",
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "blocks_certificate": enr is not None,
        })
    return {"submissions": out}


# Categories & Tags Management

class TaxonomyPayload(BaseModel):
    """Request body for creating/updating a course category or tag.

    Declared as a Pydantic model so FastAPI reads `name`/`description` from the
    JSON request body (which the admin UI sends), rather than treating them as
    query parameters.
    """
    name: str = Field(..., min_length=1)
    description: str = ""


@router.get("/categories")
async def get_categories(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Get all course categories"""
    categories = db.query(CourseCategory).all()
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "course_count": len(cat.courses),
            "created_at": cat.created_at
        }
        for cat in categories
    ]

@router.post("/categories")
async def create_category(
    payload: TaxonomyPayload,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Create a new category"""
    name = payload.name
    description = payload.description
    # Generate slug from name
    slug = name.lower().replace(' ', '-').replace('_', '-')

    # Check if slug already exists
    existing = db.query(CourseCategory).filter(CourseCategory.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )

    category = CourseCategory(
        name=name,
        slug=slug,
        description=description
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description
    }

@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    payload: TaxonomyPayload,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Update a category"""
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    category.name = payload.name
    category.slug = payload.name.lower().replace(' ', '-').replace('_', '-')
    category.description = payload.description
    db.commit()

    return {"message": "Category updated successfully"}

@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Delete a category"""
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    db.delete(category)
    db.commit()

    return {"message": "Category deleted successfully"}

# Tags Management

@router.get("/tags")
async def get_tags(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Get all course tags"""
    tags = db.query(CourseTag).all()
    return [
        {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
            "course_count": len(tag.courses),
            "created_at": tag.created_at
        }
        for tag in tags
    ]

@router.post("/tags")
async def create_tag(
    payload: TaxonomyPayload,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Create a new tag"""
    name = payload.name
    description = payload.description
    # Generate slug from name
    slug = name.lower().replace(' ', '-').replace('_', '-')

    # Check if slug already exists
    existing = db.query(CourseTag).filter(CourseTag.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists"
        )

    tag = CourseTag(
        name=name,
        slug=slug,
        description=description
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)

    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "description": tag.description
    }

@router.put("/tags/{tag_id}")
async def update_tag(
    tag_id: int,
    payload: TaxonomyPayload,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Update a tag"""
    tag = db.query(CourseTag).filter(CourseTag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    tag.name = payload.name
    tag.slug = payload.name.lower().replace(' ', '-').replace('_', '-')
    tag.description = payload.description
    db.commit()

    return {"message": "Tag updated successfully"}

@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Delete a tag"""
    tag = db.query(CourseTag).filter(CourseTag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    db.delete(tag)
    db.commit()

    return {"message": "Tag deleted successfully"}

# Course-Category Associations

@router.post("/courses/{course_id}/categories")
async def add_course_category(
    course_id: int,
    category_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Associate a category with a course"""
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Verify category exists
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check if association already exists
    existing = db.query(CourseCategoryRelation).filter(
        CourseCategoryRelation.course_id == course_id,
        CourseCategoryRelation.category_id == category_id
    ).first()

    if existing:
        return {"message": "Category already associated with course"}

    # Create association
    association = CourseCategoryRelation(course_id=course_id, category_id=category_id)
    db.add(association)
    db.commit()

    return {"message": "Category associated with course successfully"}

@router.delete("/courses/{course_id}/categories/{category_id}")
async def remove_course_category(
    course_id: int,
    category_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Remove a category association from a course"""
    association = db.query(CourseCategoryRelation).filter(
        CourseCategoryRelation.course_id == course_id,
        CourseCategoryRelation.category_id == category_id
    ).first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Association not found"
        )

    db.delete(association)
    db.commit()

    return {"message": "Category removed from course successfully"}

@router.get("/courses/{course_id}/categories")
async def get_course_categories(
    course_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Get all categories associated with a course"""
    associations = db.query(CourseCategoryRelation).filter(
        CourseCategoryRelation.course_id == course_id
    ).all()

    categories = []
    for assoc in associations:
        category = db.query(CourseCategory).filter(CourseCategory.id == assoc.category_id).first()
        if category:
            categories.append({
                "id": category.id,
                "name": category.name,
                "slug": category.slug
            })

    return categories

# Course-Tag Associations

@router.post("/courses/{course_id}/tags")
async def add_course_tag(
    course_id: int,
    tag_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Associate a tag with a course"""
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Verify tag exists
    tag = db.query(CourseTag).filter(CourseTag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )

    # Check if association already exists
    existing = db.query(CourseTagRelation).filter(
        CourseTagRelation.course_id == course_id,
        CourseTagRelation.tag_id == tag_id
    ).first()

    if existing:
        return {"message": "Tag already associated with course"}

    # Create association
    association = CourseTagRelation(course_id=course_id, tag_id=tag_id)
    db.add(association)
    db.commit()

    return {"message": "Tag associated with course successfully"}

@router.delete("/courses/{course_id}/tags/{tag_id}")
async def remove_course_tag(
    course_id: int,
    tag_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Remove a tag association from a course"""
    association = db.query(CourseTagRelation).filter(
        CourseTagRelation.course_id == course_id,
        CourseTagRelation.tag_id == tag_id
    ).first()

    if not association:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Association not found"
        )

    db.delete(association)
    db.commit()

    return {"message": "Tag removed from course successfully"}

@router.get("/courses/{course_id}/tags")
async def get_course_tags(
    course_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Get all tags associated with a course"""
    associations = db.query(CourseTagRelation).filter(
        CourseTagRelation.course_id == course_id
    ).all()

    tags = []
    for assoc in associations:
        tag = db.query(CourseTag).filter(CourseTag.id == assoc.tag_id).first()
        if tag:
            tags.append({
                "id": tag.id,
                "name": tag.name,
                "slug": tag.slug
            })

    return tags

# Certificates Management

@router.get("/certificates")
async def get_issued_certificates(
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Get all issued certificates with verification data"""
    from app.models.certificate import IssuedCertificate

    # Get issued certificates with student and course data
    certificates = db.query(IssuedCertificate).options(
        joinedload(IssuedCertificate.student),
        joinedload(IssuedCertificate.course)
    ).order_by(desc(IssuedCertificate.created_at)).offset(skip).limit(limit).all()

    return [
        {
            "id": cert.id,
            "student_name": cert.student.display_name if cert.student else "N/A",
            "student_email": cert.student.user_email if cert.student else "N/A",
            "course_title": cert.course.post_title if cert.course else "N/A",
            "course_id": cert.course_id,
            "certificate_id": cert.secure_certificate_id or f"CERT-{cert.id}",
            "secure_certificate_id": cert.secure_certificate_id,
            "certificate_hash": cert.certificate_hash,
            "issue_date": cert.created_at,
            "completion_date": cert.completion_date,
            "grade": float(cert.course_completion_percentage) if cert.course_completion_percentage else 100
        }
        for cert in certificates
    ]

# Orders Management

@router.get("/orders")
async def get_orders(
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all orders with course details including video"""
    from app.models.course import Course

    query = db.query(Order).options(
        joinedload(Order.user),
        joinedload(Order.order_items)
    )

    if status:
        query = query.filter(Order.order_status == status)

    orders = query.order_by(desc(Order.created_at)).offset(skip).limit(limit).all()

    # Single query to fetch all course details at once
    course_ids = set()
    for order in orders:
        if order.order_items:
            first_item = order.order_items[0] if order.order_items else None
            if first_item and first_item.course_id:
                course_ids.add(first_item.course_id)

    # Fetch all courses in one query
    courses_map = {}
    if course_ids:
        courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
        courses_map = {c.id: c for c in courses}

    # Coupon code per order. There is no coupon column on Order — the link is
    # CouponUsage.order_id -> Coupon.code — so resolve it in one query rather
    # than per row. Without this the admin table could show a discounted total
    # with no indication of why it differed from the list price.
    from app.models.coupon import Coupon, CouponUsage

    order_ids = [o.id for o in orders]
    coupon_map: dict[int, str] = {}
    payment_map: dict[int, Payment] = {}
    if order_ids:
        for usage_order_id, coupon_code in (
            db.query(CouponUsage.order_id, Coupon.code)
            .join(Coupon, Coupon.id == CouponUsage.coupon_id)
            .filter(CouponUsage.order_id.in_(order_ids))
            .all()
        ):
            coupon_map[usage_order_id] = coupon_code

        # Gateway reference and refund state live on Payment, not Order. An
        # order can carry several Payment rows (a retried checkout, an earlier
        # partially-handled attempt); ordering by id makes the row we display
        # deterministic instead of whatever the query happened to yield first,
        # and REFUNDED-first means the refund columns below describe the
        # payment that actually carries the refund rather than a stale sibling.
        for payment in (
            db.query(Payment)
            .filter(Payment.order_id.in_(order_ids))
            .order_by(Payment.id.desc())
            .all()
        ):
            existing = payment_map.get(payment.order_id)
            if existing is None or (
                existing.refund_status is None and payment.refund_status is not None
            ):
                payment_map[payment.order_id] = payment

    result = []
    for order in orders:
        # Get first order item to find course
        first_item = order.order_items[0] if order.order_items else None
        course_id = first_item.course_id if first_item else None

        # Get course from pre-fetched map
        course = courses_map.get(course_id) if course_id else None

        result.append({
            "id": order.id,
            "order_key": order.order_key,
            "user_name": order.user.display_name if order.user else "N/A",
            "user_email": order.user.user_email if order.user else "N/A",
            "course_title": ", ".join([item.order_item_name for item in order.order_items]) if order.order_items else "N/A",
            "course_id": course_id,
            "course_intro_video": getattr(course, 'course_intro_video', None) if course else None,
            "course_thumbnail": getattr(course, 'course_thumbnail', None) if course else None,
            # `amount` stays the amount actually captured, so existing callers
            # keep working; the breakdown below is what was missing.
            "amount": float(order.total_amount or 0),
            "subtotal_amount": float(order.subtotal_amount or 0),   # list price, pre-discount
            "discount_amount": float(order.discount_amount or 0),
            "total_amount": float(order.total_amount or 0),         # what the customer paid
            "currency": order.currency or "INR",
            "coupon_code": coupon_map.get(order.id),
            "transaction_id": order.transaction_id or None,
            "gateway_payment_id": getattr(payment_map.get(order.id), "gateway_payment_id", None) or None,
            "gateway_order_id": getattr(payment_map.get(order.id), "gateway_order_id", None) or None,
            # Refund state lives on Payment (the refund endpoint's intent row).
            # `status` below already carries REFUNDED for a completed refund;
            # these four explain WHY, WHO and WHETHER it is still in flight.
            "refund_status": getattr(payment_map.get(order.id), "refund_status", None),
            "refund_reason": getattr(payment_map.get(order.id), "refund_reason", None),
            "gateway_refund_id": getattr(payment_map.get(order.id), "gateway_refund_id", None),
            "refund_processed_at": getattr(payment_map.get(order.id), "refund_processed_at", None),
            "status": order.order_status.value if hasattr(order.order_status, 'value') else str(order.order_status),
            "payment_method": order.payment_method or "N/A",
            "created_at": order.created_at,
            "updated_at": order.updated_at
        })

    return result


class AdminRefundRequest(BaseModel):
    # Same >=10-char rule as schemas/payment.RefundRequest (which also
    # requires a payment_id — here the order id comes from the path).
    # NOTE: there is deliberately no amount field. Refunds are FULL-amount and
    # the figure is read from the Payment row, never from the request (R2).
    reason: str = Field(min_length=10, max_length=1000)


@router.post("/orders/{order_id}/refund")
def refund_order_endpoint(
    order_id: int,
    request: AdminRefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Full-amount, admin-initiated refund (spec §1, R2).

    Declared as a plain `def` ON PURPOSE: refund_service's default gateway
    adapter drives the legacy `async def PaymentService.process_refund` with
    asyncio.run, which needs a thread WITHOUT a running event loop — FastAPI
    runs sync endpoints in its threadpool, async ones on the loop. Making this
    `async def` would break every real refund. tests/test_refunds.py asserts it.
    """
    try:
        return refund_service.refund_order(
            db, order_id, reason=request.reason, actor_id=current_user.id,
        )
    except refund_service.RefundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/internship-vouchers")
async def get_internship_vouchers(
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all internship vouchers (internship payments)"""
    from app.models.internship import Internship
    from app.models.user import User as UserModel
    from app.models.enrollment import Enrollment

    query = db.query(InternshipVoucher).options(
        joinedload(InternshipVoucher.buyer),
        joinedload(InternshipVoucher.internship),
        joinedload(InternshipVoucher.redeemed_course),
    )

    if status:
        query = query.filter(InternshipVoucher.status == status)

    vouchers = query.order_by(desc(InternshipVoucher.created_at)).offset(skip).limit(limit).all()

    # Issue 6: batch-load enrollments for the redeemed courses so each
    # voucher row can carry the buyer's course-progress status.
    redeemed_pairs = [
        (v.buyer_user_id, v.redeemed_on_course_id)
        for v in vouchers
        if v.redeemed_on_course_id
    ]
    progress_map = {}
    if redeemed_pairs:
        buyer_ids = list({pid for pid, _ in redeemed_pairs})
        course_ids = list({cid for _, cid in redeemed_pairs})
        enrollments = (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id.in_(buyer_ids),
                Enrollment.course_id.in_(course_ids),
            )
            .all()
        )
        progress_map = {
            (e.user_id, e.course_id): {
                "progress_percentage": e.course_progress_percentage or 0,
                "enrollment_status": e.enrollment_status,
                "is_completed": e.completion_date is not None,
                "completion_date": e.completion_date,
            }
            for e in enrollments
        }

    return [
        {
            "id": voucher.id,
            "order_key": voucher.code,
            "user_name": voucher.buyer.display_name if voucher.buyer else "N/A",
            "user_email": voucher.buyer.user_email if voucher.buyer else "N/A",
            "course_title": voucher.internship.title if voucher.internship else "N/A",
            "redeemed_on_course_id": voucher.redeemed_on_course_id,
            "redeemed_course_title": (
                voucher.redeemed_course.post_title if voucher.redeemed_course else None
            ),
            # Issue 6: progress of the course this voucher was redeemed for.
            "course_progress": progress_map.get((voucher.buyer_user_id, voucher.redeemed_on_course_id)),
            "amount": float(voucher.amount_paid),
            "status": voucher.status,
            "payment_method": "Razorpay" if voucher.razorpay_payment_id else "N/A",
            "created_at": voucher.created_at,
            "updated_at": voucher.created_at,
            "type": "internship"
        }
        for voucher in vouchers
    ]

@router.post("/instructors/create")
async def create_instructor_account(
    data: dict,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Create a new instructor account directly from admin panel"""
    from app.models.user import InstructorProfile
    import bcrypt

    email = data.get("email", "").strip().lower()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name", username)
    bio = data.get("bio", "")

    if not email or not username or not password:
        raise HTTPException(status_code=400, detail="Email, username and password are required")

    if db.query(User).filter(User.user_email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if db.query(User).filter(User.user_login == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(
        user_login=username, user_nicename=username, user_email=email, user_pass=hashed,
        display_name=display_name, role="instructor",
        user_status=1, is_verified=True,
        user_registered=datetime.utcnow()
    )
    db.add(user)
    db.flush()

    # NOTE: InstructorProfile (models/user.py:104-132) only has instructor_bio /
    # instructor_designation / is_approved / is_blocked / earning_* columns —
    # expertise/experience/education have no backing columns and are
    # intentionally dropped (not persisted).
    profile = InstructorProfile(
        user_id=user.id, instructor_bio=bio, is_approved=True,
    )
    db.add(profile)
    db.commit()
    return {"message": "Instructor created successfully", "user_id": user.id, "email": email}


@router.post("/courses/create")
async def admin_create_course(
    data: dict,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Create a course and assign to an instructor"""
    title = data.get("title", "").strip()
    instructor_id = data.get("instructor_id")
    category = data.get("category", "General")
    description = data.get("description", "")
    price = float(data.get("price", 0))
    certificate_template_id = data.get("certificate_template_id")

    if not title or not instructor_id:
        raise HTTPException(status_code=400, detail="Title and instructor_id are required")

    from sqlalchemy import or_
    instructor = db.query(User).filter(User.id == instructor_id, or_(User.role == "instructor", User.role == "admin")).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor/Admin not found")

    from app.models.course import Course
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    existing = db.query(Course).filter(Course.post_name == slug).first()
    if existing:
        slug = f"{slug}-{instructor_id}"

    course = Course(
        post_title=title, post_author=instructor_id,
        post_content=description, post_status="publish",
        post_name=slug, post_type="course",
        course_price=price, course_category=category,
        certificate_template=str(certificate_template_id) if certificate_template_id else ""
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"message": "Course created successfully", "course_id": course.id, "title": title}


@router.get("/certificate-render-check")
async def certificate_render_check(
    current_user: User = Depends(AuthService.require_admin),
):
    """Diagnose why certificate PDFs fall back to the plain ReportLab design.

    The renderer is deliberately fault-tolerant: any failure inside headless
    Chrome is caught and the legacy ReportLab certificate is served instead.
    That keeps downloads working but means a broken Chrome shows up as "the
    PDF looks wrong", never as an error. This endpoint exercises the same path
    and reports what actually happens, so the cause is visible without having
    to read container logs.
    """
    import os
    import shutil
    import subprocess

    from app.services.certificate_service import CertificateService

    def _version(binary: str) -> Optional[str]:
        path = shutil.which(binary)
        if not path:
            return None
        try:
            out = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=10
            )
            return (out.stdout or out.stderr).strip() or None
        except Exception as exc:
            return f"present but failed to run: {exc}"

    report: Dict[str, Any] = {
        "chrome": _version("google-chrome-stable") or _version("google-chrome"),
        "chromedriver_pinned_path": CertificateService._CHROMEDRIVER_PATH,
        "chromedriver_pinned_present": os.path.exists(
            CertificateService._CHROMEDRIVER_PATH
        ),
        "chromedriver_on_path": _version("chromedriver"),
    }

    try:
        import selenium

        report["selenium_version"] = selenium.__version__
    except Exception as exc:
        report["selenium_version"] = f"import failed: {exc}"

    # Actually try to start a driver — the only way to know whether rendering
    # works, since driver resolution is where it usually breaks.
    driver = None
    try:
        from selenium.webdriver.chrome.options import Options

        opts = Options()
        for arg in (
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-zygote",
            "--disable-extensions",
        ):
            opts.add_argument(arg)

        driver = CertificateService._build_chrome_driver(opts)
        report["driver_start"] = "ok"
        report["browser_version"] = driver.capabilities.get("browserVersion")
    except Exception as exc:
        report["driver_start"] = "FAILED"
        report["driver_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    report["renders_real_certificate"] = report.get("driver_start") == "ok"
    if not report["renders_real_certificate"]:
        report["consequence"] = (
            "Certificate downloads will silently serve the legacy ReportLab "
            "design instead of the HTML template."
        )

    return report


@router.post("/certificate-pdf-cache/purge")
async def purge_certificate_pdf_cache(
    cert_id: Optional[str] = Query(
        None,
        description="Purge one certificate's cached PDF; omit to purge all.",
    ),
    current_user: User = Depends(AuthService.require_admin),
):
    """Delete cached Chrome-rendered certificate PDFs so they re-render.

    A successful render is cached to disk forever and served on every later
    download. If Chrome produced a bad PDF once — a blank page because the
    template bundle hadn't finished loading, say — that bad file keeps being
    served even after the underlying problem is fixed, because nothing
    invalidates it. Rebuilding the image is therefore not enough on its own;
    the stale cache has to go too.

    Only files matching the cache prefix are touched. The generated
    certificates in the same directory (certificate_<uuid>.pdf) and the
    template are left alone.
    """
    import glob
    import os

    from app.services.certificate_service import CertificateService

    cache_dir = CertificateService._html_pdf_cache_dir

    if cert_id:
        safe_id = "".join(ch for ch in str(cert_id) if ch.isalnum())
        if not safe_id:
            raise HTTPException(status_code=400, detail="Invalid cert_id")
        targets = [os.path.join(cache_dir, f"cert_html_{safe_id}.pdf")]
    else:
        targets = glob.glob(os.path.join(cache_dir, "cert_html_*.pdf"))

    removed, errors = [], []
    for path in targets:
        if not os.path.basename(path).startswith("cert_html_"):
            continue  # defensive: never touch anything outside the cache
        try:
            if os.path.exists(path):
                os.remove(path)
                removed.append(os.path.basename(path))
        except OSError as exc:
            errors.append(f"{os.path.basename(path)}: {exc}")

    logging.info(
        "Certificate PDF cache purged by user_id=%s (removed=%d, errors=%d)",
        current_user.id, len(removed), len(errors),
    )

    return {
        "removed_count": len(removed),
        "removed": removed,
        "errors": errors,
        "message": (
            "Cached PDFs deleted; the next download re-renders via Chrome."
            if removed
            else "Nothing cached to purge."
        ),
    }


@router.get("/certificate-templates")
async def get_certificate_templates_admin(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Get all certificate templates"""
    from sqlalchemy import text
    rows = db.execute(text("""
        SELECT id, post_title, background_color, title_font_color, title_font_family
        FROM certificates WHERE post_status='publish' ORDER BY id
    """)).fetchall()
    return [{"id": r.id, "name": r.post_title, "bg_color": r.background_color,
             "title_color": r.title_font_color, "font": r.title_font_family} for r in rows]


# ============================================================================
# Certificate Template Management (Admin)
# ============================================================================

class CertificateTemplateCreateV2(BaseModel):
    name: str
    description: str = ""
    template_type: str = "builder"
    background: dict
    dimensions: dict
    elements: list
    orientation: str = "landscape"
    is_default: bool = False


class CertificateTemplateUpdateV2(BaseModel):
    name: str = None
    description: str = None
    background: dict = None
    dimensions: dict = None
    elements: list = None
    orientation: str = None
    is_default: bool = None


class UploadedTemplateCreateV2(BaseModel):
    name: str
    description: str = ""
    file_url: str
    file_type: str = "image"
    orientation: str = "landscape"


@router.get("/certificate-templates-v2")
async def get_certificate_templates_v2(
    request: Request,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all certificate templates with full details including builder and uploaded templates
    """
    from app.models.certificate import CertificateElementTemplate

    # Get builder templates from certificates table
    builder_templates = db.query(Certificate).filter(
        Certificate.post_status == "publish"
    ).all()

    result = []

    for template in builder_templates:
        # Card preview: builder templates use their background image if any;
        # HTML/legacy templates use their pre-rendered design thumbnail so the
        # grid shows each distinct design rather than an empty placeholder.
        if template.elements_config and template.background_image:
            preview_url = template.background_image
        else:
            preview_url = _certificate_template_thumbnail(request, template.post_name)

        result.append({
            "id": template.id,
            "name": template.post_title,
            "description": template.post_content or "",
            "template_type": "builder" if template.elements_config else "legacy",
            "orientation": template.certificate_orientation,
            "background": {
                "type": "color",
                "value": template.background_color,
                "image_url": template.background_image
            },
            "dimensions": {
                "width": template.certificate_width,
                "height": template.certificate_height
            },
            "elements": template.elements_config or [],
            "preview_url": preview_url,
            "is_default": False,
            "created_by": template.post_author,
            "created_at": template.post_date,
            "updated_at": template.post_modified,
            "usage_count": len(template.issued_certificates)
        })

    # Get uploaded templates from certificate_element_templates table
    uploaded_templates = db.query(CertificateElementTemplate).filter(
        CertificateElementTemplate.element_type == "template",
        CertificateElementTemplate.is_active == True
    ).all()

    for tmpl in uploaded_templates:
        result.append({
            "id": tmpl.id + 100000,  # Offset ID to distinguish from Certificate table
            "name": tmpl.element_name,
            "description": tmpl.element_content or "",
            "template_type": "upload",
            "orientation": "landscape",  # Default for uploaded
            "background": {
                "type": "image",
                "image_url": tmpl.element_image_url
            },
            "dimensions": {
                "width": tmpl.default_width,
                "height": tmpl.default_height
            },
            "elements": [],
            "preview_url": tmpl.element_image_url,
            "is_default": False,
            "created_by": tmpl.created_by,
            "created_at": tmpl.created_at,
            "updated_at": tmpl.updated_at,
            "usage_count": tmpl.usage_count
        })

    return result


@router.post("/certificate-templates-v2")
async def create_certificate_template_v2(
    template_data: CertificateTemplateCreateV2,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new certificate template (builder type)
    """
    new_template = Certificate(
        post_author=current_user.id,
        post_title=template_data.name,
        post_content=template_data.description,
        post_status="publish",
        post_type="tutor_certificates",
        certificate_orientation=template_data.orientation,
        background_color=template_data.background.get("value", "#ffffff"),
        background_image=template_data.background.get("image_url", ""),
        certificate_width=template_data.dimensions.get("width", 1123),
        certificate_height=template_data.dimensions.get("height", 794),
        elements_config=template_data.elements,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    return {
        "id": new_template.id,
        "name": new_template.post_title,
        "message": "Certificate template created successfully"
    }


@router.put("/certificate-templates-v2/{template_id}")
async def update_certificate_template_v2(
    template_id: int,
    template_data: CertificateTemplateUpdateV2,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Update an existing certificate template
    """
    template = db.query(Certificate).filter(
        Certificate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Update fields if provided
    if template_data.name:
        template.post_title = template_data.name
    if template_data.description is not None:
        template.post_content = template_data.description
    if template_data.orientation:
        template.certificate_orientation = template_data.orientation
    if template_data.background:
        template.background_color = template_data.background.get("value", template.background_color)
        template.background_image = template_data.background.get("image_url", template.background_image)
    if template_data.dimensions:
        template.certificate_width = template_data.dimensions.get("width", template.certificate_width)
        template.certificate_height = template_data.dimensions.get("height", template.certificate_height)
    if template_data.elements is not None:
        template.elements_config = template_data.elements

    template.post_modified = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Template updated successfully"}


@router.delete("/certificate-templates-v2/{template_id}")
async def delete_certificate_template_v2(
    template_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a certificate template
    """
    template = db.query(Certificate).filter(
        Certificate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check if template is in use
    if len(template.issued_certificates) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete template that has been used to issue certificates"
        )

    db.delete(template)
    db.commit()

    return {"message": "Template deleted successfully"}


@router.post("/certificate-templates/upload")
async def upload_certificate_template(
    template_data: UploadedTemplateCreateV2,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Create an uploaded certificate template (image/PDF based)
    """
    from app.models.certificate import CertificateElementTemplate

    # Check if file_url is valid
    if not template_data.file_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_url is required"
        )

    new_template = CertificateElementTemplate(
        element_name=template_data.name,
        element_type="template",
        element_content=template_data.description,
        element_image_url=template_data.file_url,
        element_styles={
            "file_type": template_data.file_type,
            "orientation": template_data.orientation
        },
        default_position_x=0,
        default_position_y=0,
        default_width=1123,
        default_height=794,
        is_active=True,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    return {
        "id": new_template.id,
        "name": new_template.element_name,
        "message": "Certificate template uploaded successfully"
    }


def _public_base_url(request: Request) -> str:
    """Public origin of this request, as the browser sees it.

    `request.base_url` is the origin uvicorn was reached on — behind nginx that
    is `http://127.0.0.1/`, which is dead in the user's browser. Prefer the
    proxy's forwarded headers, then the configured public site URL, and only
    fall back to base_url when running without a proxy.

    The forwarded host is only honoured when it is one of ALLOWED_HOSTS —
    `X-Forwarded-Host` is caller-supplied and, unlike `Host`, is not vetted by
    TrustedHostMiddleware, so an unchecked value would let a request dictate the
    URLs we hand back.
    """
    from app.core.config import get_settings
    settings = get_settings()

    allowed = {str(h).lower() for h in (settings.ALLOWED_HOSTS or [])}
    local = {"127.0.0.1", "localhost", "backend"}

    for header in ("x-forwarded-host", "host"):
        host = request.headers.get(header)
        if not host:
            continue
        hostname = host.split(":")[0].lower()
        if hostname in local:
            continue
        if allowed and hostname not in allowed:
            continue
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        return f"{proto}://{host}"

    if settings.FRONTEND_URL:
        return settings.FRONTEND_URL.rstrip("/")
    return str(request.base_url).rstrip("/")


def _certificate_template_thumbnail(request: Request, slug: str) -> str:
    """Absolute URL of a template's pre-rendered thumbnail.

    Mirrors `_thumb` in routers/certificates.py: the design PNGs live under
    certificates/thumbnails/<slug>.png (default.png when there is no slug) and
    are served from the /certificate-files static mount. Returned absolute so it
    resolves in a preview window opened as about:blank (relative URLs would not).
    """
    name = (slug or "").strip() or "default"
    return f"{_public_base_url(request)}/certificate-files/thumbnails/{name}.png"


@router.post("/certificate-templates/{template_id}/preview")
async def preview_certificate_template(
    template_id: int,
    request: Request,
    preview_data: dict = None,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate a preview of a certificate template with sample data.

    Always returns a PDF data URL (`preview_type="pdf"`) so it renders through
    the admin UI's existing application/pdf viewer — each source resolving to the
    template's OWN design:
      * Builder templates (a Certificate row with elements_config) are rendered
        from their saved background + positioned elements.
      * HTML/legacy Certificate rows (the hand-authored designs — Sasha 3D,
        Royal Navy, Modern Minimal, Aurora Gradient, and the default) wrap their
        pre-rendered thumbnail into a PDF.
      * Uploaded templates (exposed by the list endpoint with a +100000 id
        offset, stored in CertificateElementTemplate) wrap their uploaded image.
    If an image can't be loaded, falls back to returning its URL
    (`preview_type="image"`).
    """
    from app.models.certificate import CertificateElementTemplate
    from app.services.certificate_service import CertificateService
    import tempfile, os, base64

    # Use sample data for preview if none provided
    sample_data = preview_data or {
        "student_name": "John Doe",
        "course_title": "Sample Course Title",
        "instructor_name": "Instructor Name",
        "completion_date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "certificate_id": "PREVIEW"
    }

    def _pdf_response(temp_path: str):
        with open(temp_path, "rb") as fh:
            pdf_bytes = fh.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode()
        return {
            "preview_url": f"data:application/pdf;base64,{pdf_base64}",
            "preview_type": "pdf",
            "template_id": template_id,
            "sample_data": sample_data,
        }

    def _image_response(image_url: str):
        return {
            "preview_url": image_url,
            "preview_type": "image",
            "template_id": template_id,
            "sample_data": sample_data,
        }

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name

        # ── Uploaded (image) templates: +100000 id offset from the list endpoint.
        UPLOADED_ID_OFFSET = 100000
        if template_id >= UPLOADED_ID_OFFSET:
            uploaded = db.query(CertificateElementTemplate).filter(
                CertificateElementTemplate.id == template_id - UPLOADED_ID_OFFSET
            ).first()
            if not uploaded:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )
            if CertificateService.render_image_pdf(uploaded.element_image_url, temp_path):
                return _pdf_response(temp_path)
            # Could not load the image — hand the raw URL back for the client to show.
            return _image_response(uploaded.element_image_url)

        template = db.query(Certificate).filter(
            Certificate.id == template_id
        ).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        if template.elements_config:
            # Builder template — render its saved design (background + positioned
            # elements) so the preview matches exactly what the admin laid out.
            template_design = {
                "dimensions": {
                    "width": template.certificate_width,
                    "height": template.certificate_height,
                },
                "background": {
                    "type": "image" if template.background_image else "color",
                    "value": template.background_color,
                    "image_url": template.background_image,
                },
                "elements": template.elements_config or [],
            }
            CertificateService.render_template_preview(template_design, sample_data, temp_path)
            return _pdf_response(temp_path)

        # HTML/legacy templates (the hand-authored designs — Sasha 3D, Royal
        # Navy, Modern Minimal, Aurora Gradient, default): the design lives in
        # certificates/templates/<slug>.html with a matching pre-rendered
        # thumbnail. Wrap that thumbnail into a PDF so each previews as its OWN
        # design rather than the built-in ReportLab default.
        slug = (template.post_name or "").strip() or "default"
        thumb_path = os.path.join("/app/certificates/thumbnails", f"{slug}.png")
        if CertificateService.render_image_pdf(thumb_path, temp_path):
            return _pdf_response(temp_path)
        # Thumbnail missing on disk — return the served URL as a last resort.
        return _image_response(_certificate_template_thumbnail(request, template.post_name))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )
    finally:
        # Always clean up the scratch PDF, whichever branch (or error) we took.
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@router.get("/instructors/list")
async def list_instructors_simple(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Get all instructors, SPOCs, and admins for dropdown (used in internship approval)"""
    from sqlalchemy import or_
    instructors = db.query(User).filter(or_(User.role == "instructor", User.role == "admin", User.role == "spoc")).all()
    return [{"id": u.id, "name": (u.display_name or u.user_login) + (" [" + u.role.upper() + "]" if u.role in ("admin", "spoc") else ""), "email": u.user_email, "role": u.role} for u in instructors]

@router.post("/courses/{course_id}/assign-instructor")
async def assign_instructor_to_course(
    course_id: int,
    data: dict,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Assign or reassign a course to an instructor"""
    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    instructor_id = data.get("instructor_id")
    from sqlalchemy import or_
    instructor = db.query(User).filter(User.id == instructor_id, or_(User.role == "instructor", User.role == "admin")).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor/Admin not found")
    course.post_author = instructor_id
    db.commit()
    return {"message": f"Course assigned to {instructor.display_name or instructor.user_login}"}

@router.patch("/courses/{course_id}/force-publish")
async def force_publish_course(
    course_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Force publish a course directly - admin only"""
    from app.models.course import Course
    from sqlalchemy import text
    db.execute(text("UPDATE courses SET post_status='publish' WHERE id=:id"), {"id": course_id})
    db.commit()
    return {"message": "Course published", "course_id": course_id}

@router.patch("/courses/{course_id}/lessons/{lesson_id}/order")
async def update_lesson_order(
    course_id: int,
    lesson_id: int,
    data: dict,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Update lesson order and section info"""
    from app.models.course import Lesson
    from sqlalchemy import text
    order = data.get("order", 0)
    db.execute(text("UPDATE lessons SET menu_order=:order WHERE id=:id AND post_parent=:cid"),
               {"order": order, "id": lesson_id, "cid": course_id})
    db.commit()
    return {"message": "Updated"}


@router.get("/lessons")
async def list_all_lessons(
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    course_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List all lessons across courses for admin management."""
    query = db.query(Lesson).options(joinedload(Lesson.course))
    if course_id:
        query = query.filter(Lesson.post_parent == course_id)
    total = query.count()
    lessons = query.order_by(Lesson.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": l.id,
                "title": l.post_title,
                "course_id": l.post_parent,
                "course_title": l.course.post_title if l.course else "",
                "type": "video" if (l.lesson_video_url or l.lesson_youtube_url) else "text",
                "duration": l.lesson_video_duration or "",
                "status": l.post_status,
                "order": l.menu_order or 0,
                "created_at": l.created_at,
            }
            for l in lessons
        ],
    }


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_lesson(
    lesson_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Delete a lesson by id (admin-scoped, no course_id required)."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    db.delete(lesson)
    db.commit()
    return None


@router.get("/quizzes")
async def list_all_quizzes(
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    course_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List all quizzes across courses for admin management."""
    query = db.query(Quiz).options(joinedload(Quiz.course))
    if course_id:
        query = query.filter(Quiz.post_parent == course_id)
    total = query.count()
    quizzes = query.order_by(Quiz.created_at.desc()).offset(skip).limit(limit).all()
    items = []
    for q in quizzes:
        question_count = db.query(func.count(QuizQuestion.question_id)).filter(QuizQuestion.quiz_id == q.id).scalar() or 0
        attempt_count = db.query(func.count(QuizAttempt.attempt_id)).filter(QuizAttempt.quiz_id == q.id).scalar() or 0
        items.append({
            "id": q.id,
            "title": q.post_title,
            "course_id": q.post_parent,
            "course_title": q.course.post_title if q.course else "",
            "total_questions": question_count,
            "time_limit": q.quiz_time_limit or 0,
            "passing_grade": q.quiz_passing_grade or 0,
            "attempts": attempt_count,
            "status": q.post_status,
            "created_at": q.created_at,
        })
    return {"total": total, "items": items}


@router.delete("/quizzes/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_quiz(
    quiz_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Delete a quiz by id (admin-scoped)."""
    from app.models.quiz import QuizAttempt, QuizAttemptAnswer, QuizQuestion, QuizQuestionAnswer

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    # Delete quiz attempts first (foreign key constraint)
    attempts = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id).all()
    for attempt in attempts:
        db.query(QuizAttemptAnswer).filter(QuizAttemptAnswer.quiz_attempt_id == attempt.attempt_id).delete()
        db.delete(attempt)

    # Delete questions and answers
    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).all()
    for question in questions:
        db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).delete()
        db.delete(question)

    db.delete(quiz)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Admin "View as Instructor" impersonation
# ---------------------------------------------------------------------------
#
# Flow:
#   1. Admin hits POST /admin/impersonate/{target_user_id} — backend mints
#      a 30-minute impersonation_access JWT whose `sub` is the instructor
#      and whose `impersonated_by` is the admin. One AdminImpersonationLog
#      row is inserted with started_at=now, ended_at=NULL.
#   2. Frontend stashes the admin's original access+refresh under
#      sessionStorage and uses the impersonation token for subsequent calls.
#   3. Admin hits POST /admin/impersonate/end to close out the audit row.
#      Idempotent: if no open row exists (e.g. token already expired and
#      was lazily closed), still returns 200.
#
# Guardrails enforced here:
#   - require_admin gate (role must be admin)
#   - target role MUST be "instructor" (400 otherwise)
#   - if the current caller was itself authenticated via an impersonation
#     token (i.e. chained impersonation), reject with 403
#   - tokens expire hard in 30 minutes; they cannot be refreshed (see
#     /auth/refresh handler)

# NOTE: this literal route MUST stay above @router.post("/impersonate/{target_user_id}").
# FastAPI matches in registration order, and the parametrised route's require_admin
# dependency is solved before the path param is validated — so while /end sat below it,
# every call was answered by start_impersonation and rejected with 403 (an admin caller
# would have got 422 on int("end")). The audit rows were never closed.
@router.post("/impersonate/end")
async def end_impersonation(
    request: Request,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Close out the latest open impersonation audit row for this session.

    Accepts either:
      - an admin access token (caller is the admin exiting), OR
      - an impersonation_access token (frontend might call this while
        still carrying the impersonated token before restoring).

    Idempotent: if no open row is found (already closed, or never existed)
    we still return {ok: true, closed: False}.
    """
    # Get the authorization header and decode the token directly to extract impersonated_by
    # This provides a fallback if the _impersonated_by attribute was not set correctly
    auth_header = request.headers.get("Authorization", "")
    token_impersonated_by = None

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from app.core.security import jwt, settings
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            token_type = payload.get("type")
            if token_type == "impersonation_access":
                token_impersonated_by = payload.get("impersonated_by")
                logger.info(f"Token is impersonation_access: impersonated_by={token_impersonated_by}")
        except Exception as e:
            logger.warning(f"Failed to decode token: {e}")

    # First try to get from the User object attribute
    impersonated_by = getattr(current_user, "_impersonated_by", None)

    # If not set on the User object, fall back to token payload
    if impersonated_by is None and token_impersonated_by is not None:
        impersonated_by = token_impersonated_by
        logger.info(f"Using impersonated_by from token payload: {impersonated_by}")

    logger.info(f"end_impersonation called: user_id={current_user.id}, role={current_user.role}, impersonated_by={impersonated_by}")

    # Work out which (admin_id, target_id) pair to close.
    if impersonated_by is not None:
        admin_id = int(impersonated_by)
        target_id = current_user.id
    else:
        # Caller is the admin themselves. Close their most recent open row,
        # whoever the target was. SuperAdmin inherits this fallback.
        if current_user.role not in ("admin", "superadmin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins or active impersonation sessions can end impersonation",
            )
        admin_id = current_user.id
        target_id = None

    try:
        q = db.query(AdminImpersonationLog).filter(
            AdminImpersonationLog.admin_user_id == admin_id,
            AdminImpersonationLog.ended_at.is_(None),
        )
        if target_id is not None:
            q = q.filter(AdminImpersonationLog.target_user_id == target_id)
        log_row = q.order_by(AdminImpersonationLog.started_at.desc()).first()

        if log_row is None:
            return {"ok": True, "closed": False}

        log_row.ended_at = datetime.now(timezone.utc)
        db.commit()
        return {"ok": True, "closed": True, "log_id": log_row.id}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to end impersonation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end impersonation session",
        )



@router.post("/impersonate/{target_user_id}")
async def start_impersonation(
    target_user_id: int,
    payload: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Mint a 30-minute impersonation access token scoped to `target_user_id`
    (which must be an instructor). Returns the token plus a minimal target
    descriptor for the banner. Records the session in
    admin_impersonation_logs.
    """
    # Block chained impersonation. require_admin already rejects non-admin
    # callers, but a plain admin token and an admin-via-impersonation token
    # look identical at the role layer — we distinguish via the attr that
    # get_current_user attaches.
    if getattr(current_user, "_impersonated_by", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonation sessions cannot start another impersonation",
        )

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    if target.role != "instructor":
        raise HTTPException(
            status_code=400,
            detail="Only instructor accounts can be impersonated",
        )

    reason = None
    if payload and isinstance(payload, dict):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = raw_reason.strip()[:1000]

    # Import lazily so the security module stays a thin dep.
    from app.core.security import (
        create_impersonation_token,
        IMPERSONATION_TOKEN_EXPIRE_MINUTES,
    )

    try:
        log_row = AdminImpersonationLog(
            admin_user_id=current_user.id,
            target_user_id=target.id,
            started_at=datetime.now(timezone.utc),
            reason=reason,
        )
        db.add(log_row)
        db.commit()
        db.refresh(log_row)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record impersonation log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start impersonation session",
        )

    token = create_impersonation_token(
        target_user_id=target.id,
        admin_id=current_user.id,
    )

    logger.info(
        f"Admin {current_user.id} ({current_user.user_email}) started "
        f"impersonation of instructor {target.id} ({target.user_email}) "
        f"log_id={log_row.id}"
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": IMPERSONATION_TOKEN_EXPIRE_MINUTES * 60,
        "target": {
            "id": target.id,
            "display_name": target.display_name,
            "role": target.role,
            "email": target.user_email,
        },
        "log_id": log_row.id,
    }



@router.post("/impersonate/company/{company_id}")
async def impersonate_company(
    company_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Start an admin-as-company impersonation session.

    Mints a 30-minute impersonation_access JWT and logs the action.
    Returns the access token and the redirect path for the frontend.
    """
    from app.core.security import create_access_token

    # Block chained impersonation
    if getattr(current_user, "_impersonated_by", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonation sessions cannot start another impersonation",
        )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    owner = db.query(User).filter(User.id == company.owner_user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Company owner not found")

    # Mint the impersonation token
    token_data = {
        "sub": str(owner.id),
        "type": "impersonation_access",
        "impersonated_by": current_user.id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=30),
    )

    # Audit log entry
    log = AdminImpersonationLog(
        admin_user_id=current_user.id,
        target_user_id=owner.id,
        reason=f"View as company {company.name}",
    )
    db.add(log)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "redirect": f"/company/dashboard",
        "company_name": company.name,
        "owner_email": owner.user_email,
    }


@router.post("/impersonate/spoc/{spoc_user_id}")
async def impersonate_spoc(
    spoc_user_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Start an admin-as-SPOC impersonation session.

    Mints a 30-minute impersonation_access JWT and logs the action.
    Returns the access token and the SPOC details for the frontend.
    """
    from app.core.security import create_access_token

    # Block chained impersonation
    if getattr(current_user, "_impersonated_by", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonation sessions cannot start another impersonation",
        )

    spoc = db.query(User).filter(User.id == spoc_user_id).first()
    if not spoc:
        raise HTTPException(status_code=404, detail="SPOC not found")

    if spoc.role != "spoc":
        raise HTTPException(
            status_code=400,
            detail="Target user is not a SPOC",
        )

    # Mint the impersonation token
    token_data = {
        "sub": str(spoc.id),
        "type": "impersonation_access",
        "impersonated_by": current_user.id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=30),
    )

    # Audit log entry
    log = AdminImpersonationLog(
        admin_user_id=current_user.id,
        target_user_id=spoc.id,
        reason=f"View as SPOC {spoc.display_name}",
    )
    db.add(log)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,
        "target": {
            "id": spoc.id,
            "display_name": spoc.display_name,
            "email": spoc.user_email,
            "role": "spoc",
        },
    }


@router.post("/impersonate/student/{student_id}")
async def impersonate_student(
    student_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Start an admin-as-student impersonation session.

    Mints a 30-minute impersonation_access JWT and logs the action.
    Returns the access token and the student details for the frontend.
    """
    from app.core.security import create_access_token

    # Block chained impersonation
    if getattr(current_user, "_impersonated_by", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonation sessions cannot start another impersonation",
        )

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.role != "student":
        raise HTTPException(
            status_code=400,
            detail="Target user is not a student",
        )

    # Mint the impersonation token
    token_data = {
        "sub": str(student.id),
        "type": "impersonation_access",
        "impersonated_by": current_user.id,
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=30),
    )

    # Audit log entry
    log = AdminImpersonationLog(
        admin_user_id=current_user.id,
        target_user_id=student.id,
        reason=f"View as student {student.display_name}",
    )
    db.add(log)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,
        "target": {
            "id": student.id,
            "display_name": student.display_name,
            "email": student.user_email,
            "role": "student",
        },
    }


@router.get("/analytics/heatmaps")
async def get_analytics_heatmaps(
    days: int = 90,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Get all heatmap data in one call."""
    from sqlalchemy import text

    cutoff = datetime.utcnow() - timedelta(days=days)

    enrollment_daily = db.execute(text("""
        SELECT DATE(enrollment_date) as day, COUNT(*) as count
        FROM enrollments
        WHERE enrollment_date >= :cutoff
        GROUP BY DATE(enrollment_date)
        ORDER BY day
    """), {"cutoff": cutoff}).fetchall()

    registration_hourly = db.execute(text("""
        SELECT
            EXTRACT(DOW FROM user_registered) as dow,
            EXTRACT(HOUR FROM user_registered) as hour,
            COUNT(*) as count
        FROM users
        WHERE user_status = 1 AND user_registered >= :cutoff
        GROUP BY dow, hour
    """), {"cutoff": cutoff}).fetchall()

    course_engagement = db.execute(text("""
        SELECT
            c.id as course_id,
            c.post_title as course_name,
            EXTRACT(DOW FROM e.enrollment_date) as dow,
            COUNT(*) as count
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.enrollment_date >= :cutoff
        GROUP BY c.id, c.post_title, dow
        ORDER BY c.id, dow
    """), {"cutoff": cutoff}).fetchall()

    revenue_daily = db.execute(text("""
        SELECT DATE(created_at) as day, COALESCE(SUM(amount), 0) as revenue
        FROM payments
        WHERE payment_status = 'COMPLETED' AND created_at >= :cutoff
        GROUP BY DATE(created_at)
        ORDER BY day
    """), {"cutoff": cutoff}).fetchall()

    return {
        "enrollment_activity": [{"day": str(r[0]), "count": r[1]} for r in enrollment_daily],
        "user_registration": [
            {"dow": int(r[0]), "hour": int(r[1]), "count": r[2]} for r in registration_hourly
        ],
        "course_engagement": [
            {"course_id": r[0], "course_name": r[1], "dow": int(r[2]), "count": r[3]}
            for r in course_engagement
        ],
        "revenue_activity": [{"day": str(r[0]), "revenue": float(r[1])} for r in revenue_daily],
        "period_days": days,
    }


@router.get("/analytics/learning-progress")
async def get_learning_progress_timeseries(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Average learning progress over time across all active enrollments.

    Buckets by day (7d/30d), week (90d), or month (1y). Each point reports
    the mean course_progress_percentage of enrollments created on/before
    that bucket boundary.
    """
    from sqlalchemy import text

    period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period, 30)
    cutoff = datetime.utcnow() - timedelta(days=period_days)

    if period_days <= 30:
        trunc = "day"
    elif period_days <= 90:
        trunc = "week"
    else:
        trunc = "month"

    rows = db.execute(text(f"""
        SELECT
            DATE_TRUNC('{trunc}', enrollment_date) AS bucket,
            COALESCE(AVG(course_progress_percentage), 0) AS avg_progress,
            COALESCE(AVG(CASE WHEN total_lessons > 0
                THEN (completed_lessons::float / total_lessons) * 100
                ELSE 0 END), 0) AS avg_completion,
            COUNT(*) AS enrolled_count
        FROM enrollments
        WHERE enrollment_date >= :cutoff
        GROUP BY bucket
        ORDER BY bucket
    """), {"cutoff": cutoff}).fetchall()

    return {
        "period": period,
        "bucket": trunc,
        "series": [
            {
                "date": r[0].strftime("%Y-%m-%d") if r[0] else None,
                "avg_progress": round(float(r[1]), 2),
                "avg_completion": round(float(r[2]), 2),
                "enrolled_count": int(r[3]),
            }
            for r in rows
        ],
    }


@router.get("/analytics/courses-progress")
async def get_courses_progress(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Per-course average learning progress across all enrollments.

    Returns one row per published course with avg_progress (0-100),
    avg_completion (lessons completed / total lessons), total enrollment
    count, and completed enrollment count.
    """
    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT
            c.id AS course_id,
            c.post_title AS course_title,
            COALESCE(AVG(e.course_progress_percentage), 0) AS avg_progress,
            COALESCE(AVG(CASE WHEN e.total_lessons > 0
                THEN (e.completed_lessons::float / e.total_lessons) * 100
                ELSE 0 END), 0) AS avg_completion,
            COUNT(e.id) AS total_enrollments,
            COUNT(e.id) FILTER (WHERE e.enrollment_status = 'completed') AS completed_enrollments
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        GROUP BY c.id, c.post_title
        ORDER BY total_enrollments DESC, c.id
    """)).fetchall()

    return {
        "courses": [
            {
                "course_id": int(r[0]),
                "course_title": r[1] or "Untitled",
                "avg_progress": round(float(r[2]), 2),
                "avg_completion": round(float(r[3]), 2),
                "total_enrollments": int(r[4]),
                "completed_enrollments": int(r[5]),
            }
            for r in rows
        ]
    }


@router.get("/analytics/internships")
async def get_internship_analytics(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Aggregate internship voucher metrics for the admin analytics page.

    Returns four series:
      - timeseries: vouchers issued vs redeemed per bucket
      - status_breakdown: total issued vs redeemed
      - top_internships: top 6 internships by vouchers issued
      - revenue_timeseries: voucher revenue per bucket
    """
    from sqlalchemy import text

    period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period, 30)
    cutoff = datetime.utcnow() - timedelta(days=period_days)

    if period_days <= 30:
        trunc = "day"
    elif period_days <= 90:
        trunc = "week"
    else:
        trunc = "month"

    # Each series is bucketed on its OWN date: issued on created_at, redeemed on
    # redeemed_at. Bucketing redemptions on the issue date put them on the wrong
    # day and left the redeemed axis without any redemption dates at all.
    timeseries = db.execute(text(f"""
        WITH issued AS (
            SELECT DATE_TRUNC('{trunc}', created_at) AS bucket, COUNT(*) AS issued
            FROM internship_vouchers
            WHERE created_at >= :cutoff
            GROUP BY bucket
        ),
        redeemed AS (
            SELECT DATE_TRUNC('{trunc}', redeemed_at) AS bucket, COUNT(*) AS redeemed
            FROM internship_vouchers
            WHERE redeemed_at IS NOT NULL AND redeemed_at >= :cutoff
            GROUP BY bucket
        )
        SELECT
            COALESCE(i.bucket, r.bucket) AS bucket,
            COALESCE(i.issued, 0) AS issued,
            COALESCE(r.redeemed, 0) AS redeemed
        FROM issued i
        FULL OUTER JOIN redeemed r ON i.bucket = r.bucket
        ORDER BY bucket
    """), {"cutoff": cutoff}).fetchall()

    status_rows = db.execute(text("""
        SELECT status, COUNT(*) AS count
        FROM internship_vouchers
        GROUP BY status
    """)).fetchall()

    top_rows = db.execute(text("""
        SELECT
            i.title AS name,
            COUNT(v.id) AS issued,
            COUNT(v.id) FILTER (WHERE v.status = 'redeemed') AS redeemed
        FROM internships i
        LEFT JOIN internship_vouchers v ON v.internship_id = i.id
        GROUP BY i.id, i.title
        ORDER BY issued DESC
        LIMIT 6
    """)).fetchall()

    revenue_rows = db.execute(text(f"""
        SELECT
            DATE_TRUNC('{trunc}', created_at) AS bucket,
            COALESCE(SUM(amount_paid), 0) AS revenue
        FROM internship_vouchers
        WHERE created_at >= :cutoff
        GROUP BY bucket
        ORDER BY bucket
    """), {"cutoff": cutoff}).fetchall()

    return {
        "period": period,
        "bucket": trunc,
        "timeseries": [
            {
                "date": r[0].strftime("%Y-%m-%d") if r[0] else None,
                "issued": int(r[1]),
                "redeemed": int(r[2]),
            }
            for r in timeseries
        ],
        "status_breakdown": [
            {"status": r[0], "count": int(r[1])} for r in status_rows
        ],
        "top_internships": [
            {"name": r[0], "issued": int(r[1]), "redeemed": int(r[2])}
            for r in top_rows
        ],
        "revenue_timeseries": [
            {
                "date": r[0].strftime("%Y-%m-%d") if r[0] else None,
                "revenue": float(r[1]),
            }
            for r in revenue_rows
        ],
    }


# ===========================================================================
# Course Review Moderation (admin)
# ===========================================================================

from pydantic import BaseModel, Field
from typing import Literal


class AdminReviewModerateRequest(BaseModel):
    status: Literal["approved", "rejected"]
    admin_notes: Optional[str] = None


def _recompute_course_rating_admin(db: Session, course_id: int) -> None:
    """Recompute Course.average_rating + total_reviews using only approved
    reviews. Caller commits."""
    row = (
        db.query(
            func.coalesce(func.avg(CourseReview.rating), 0),
            func.count(CourseReview.id),
        )
        .filter(
            CourseReview.course_id == course_id,
            CourseReview.status == "approved",
        )
        .one()
    )
    avg_rating = float(row[0] or 0)
    total = int(row[1] or 0)
    db.query(Course).filter(Course.id == course_id).update(
        {Course.average_rating: round(avg_rating, 2), Course.total_reviews: total},
        synchronize_session=False,
    )


@router.get("/course-reviews")
async def admin_list_course_reviews(
    status: Optional[str] = Query("pending"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """List course reviews filtered by moderation status (default: pending)."""
    q = db.query(CourseReview).options(
        joinedload(CourseReview.user).joinedload(User.profile),
        joinedload(CourseReview.course),
    )
    if status and status != "all":
        q = q.filter(CourseReview.status == status)

    reviews = q.order_by(CourseReview.created_at.desc()).all()

    out = []
    for r in reviews:
        u = r.user
        c = r.course
        out.append({
            "id": r.id,
            "rating": r.rating,
            "review_title": r.review_title or "",
            "review_content": r.review_content or "",
            "status": r.status,
            "admin_notes": r.admin_notes or "",
            "created_at": r.created_at,
            "course": {
                "id": c.id if c else None,
                "title": c.post_title if c else "—",
            },
            "user": {
                "id": u.id if u else None,
                "name": u.display_name if u else "Anonymous",
                "email": u.user_email if u else "",
                "avatar": (u.profile.profile_photo or "") if u and u.profile else "",
            },
        })
    return {"reviews": out, "total": len(out)}


@router.patch("/course-reviews/{review_id}")
async def admin_moderate_course_review(
    review_id: int,
    payload: AdminReviewModerateRequest,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    try:
        review.status = payload.status
        review.review_status = payload.status
        if payload.admin_notes is not None:
            review.admin_notes = payload.admin_notes
        db.flush()
        _recompute_course_rating_admin(db, review.course_id)
        db.commit()
        db.refresh(review)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to moderate: {exc}")

    return {
        "id": review.id,
        "status": review.status,
        "message": f"Review {review.status}",
    }


@router.delete("/course-reviews/{review_id}")
async def admin_delete_course_review(
    review_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    course_id = review.course_id
    try:
        db.delete(review)
        db.flush()
        _recompute_course_rating_admin(db, course_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete review: {exc}")

    return {"message": "Review deleted", "id": review_id}


# ===========================================================================
# Settings Management (admin)
# ===========================================================================

class SystemSettingsUpdate(BaseModel):
    """Schema for updating system settings"""
    site_name: Optional[str] = None
    site_description: Optional[str] = None
    site_url: Optional[str] = None
    admin_email: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    payment_gateway: Optional[str] = None
    razorpay_key: Optional[str] = None
    razorpay_secret: Optional[str] = None
    email_provider: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    auto_enroll_free: Optional[bool] = None
    require_approval: Optional[bool] = None
    allow_reviews: Optional[bool] = None
    allow_qa: Optional[bool] = None
    certificate_enabled: Optional[bool] = None
    certificate_template: Optional[str] = None
    email_notifications: Optional[bool] = None
    enrollment_notification: Optional[bool] = None
    completion_notification: Optional[bool] = None
    new_course_notification: Optional[bool] = None


@router.get("/settings")
async def get_system_settings(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Get system settings (currently returns defaults).
    In production, these would be stored in a settings table or database.
    """
    from app.core.config import get_settings
    config_settings = get_settings()

    return {
        "site_name": "SashaInfinity LMS",
        "site_description": "Learn and grow with expert-led courses",
        "site_url": getattr(config_settings, "SERVER_NAME", "") or "https://sashainfinity.com",
        "admin_email": getattr(config_settings, "ADMIN_EMAIL", "") or "admin@sashainfinity.com",
        "timezone": "UTC",
        "language": "en",
        "currency": "INR",
        "currency_symbol": "₹",
        "payment_gateway": "razorpay",
        "razorpay_key": config_settings.RAZORPAY_KEY if hasattr(config_settings, 'RAZORPAY_KEY') else "",
        "razorpay_secret": "",  # Never expose secret
        "email_provider": "smtp",
        "smtp_host": "",
        "smtp_port": "587",
        "smtp_user": "",
        "smtp_password": "",
        "email_from": "noreply@sashainfinity.com",
        "auto_enroll_free": True,
        "require_approval": True,
        "allow_reviews": True,
        "allow_qa": True,
        "certificate_enabled": True,
        "certificate_template": "default",
        "email_notifications": True,
        "enrollment_notification": True,
        "completion_notification": True,
        "new_course_notification": False,
    }


@router.put("/settings")
async def update_system_settings(
    payload: SystemSettingsUpdate,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Update system settings.
    Note: This is a simplified implementation. In production, settings should be
    persisted to a database table and referenced throughout the application.
    Currently returns success but doesn't persist (would require DB schema changes).
    """
    # In a full implementation, you would:
    # 1. Create a SystemSettings model/table
    # 2. Update the settings in the database
    # 3. Optionally reload config or clear caches

    # For now, log the update and return success
    # You could add specific handling for critical settings like payment gateway
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Settings update requested by admin {current_user.id}: {payload.model_dump(exclude_unset=True)}")

    return {
        "success": True,
        "message": "Settings updated successfully",
        "updated_fields": list(payload.model_dump(exclude_unset=True).keys())
    }


# ---------------- Internship Requests Management ----------------

@router.get("/internship-requests", response_model=InternshipRequestListResponse)
async def list_internship_requests(
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(InternshipRequest)
    if status_filter:
        q = q.filter(InternshipRequest.status == status_filter)

    requests = q.order_by(InternshipRequest.created_at.desc()).all()

    # Fetch related data
    company_ids = {r.company_id for r in requests}
    requester_ids = {r.requested_by for r in requests}
    reviewer_ids = {r.reviewed_by for r in requests if r.reviewed_by}

    companies = {c.id: c for c in db.query(Company).filter(Company.id.in_(list(company_ids) or [-1])).all()}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(list(requester_ids | reviewer_ids) or [-1])).all()}

    items = []
    for r in requests:
        company = companies.get(r.company_id)
        requester = users.get(r.requested_by)
        reviewer = users.get(r.reviewed_by) if r.reviewed_by else None
        items.append(InternshipRequestItem(
            id=r.id,
            company_id=r.company_id,
            company_name=company.name if company else f"Company #{invoice.company_id} (record removed)",
            requested_by=r.requested_by,
            requester_name=requester.display_name if requester else "",
            title=r.title,
            start_date=r.start_date,
            end_date=r.end_date,
            intern_count=r.intern_count,
            description=r.description,
            status=r.status,
            rejection_reason=r.rejection_reason,
            approved_internship_id=r.approved_internship_id,
            reviewed_by=r.reviewed_by,
            reviewer_name=reviewer.display_name if reviewer else None,
            reviewed_at=r.reviewed_at,
            created_at=r.created_at,
        ))
    return InternshipRequestListResponse(items=items)


@router.post("/internship-requests/{request_id}/approve")
async def approve_internship_request(
    request_id: int,
    body: ApproveInternshipRequestRequest,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    req = db.query(InternshipRequest).filter(InternshipRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status == "approved":
        raise HTTPException(status_code=409, detail="Request already approved")

    # Generate slug from title if not provided
    slug = body.slug or body.title.lower().replace(" ", "-")[:50]

    # Get or create a default cohort
    cohort = db.query(Cohort).filter(Cohort.slug == "general").first()
    if not cohort:
        cohort = Cohort(name="General", slug="general")
        db.add(cohort)
        db.flush()

    # Create the internship
    from app.models.internship import Internship
    internship = Internship(
        title=req.title,
        slug=slug,
        description=req.description,
        price=body.price,
        spoc_user_id=body.spoc_user_id,
        cohort_id=cohort.id,
        created_by=req.requested_by,
        is_active=True,
    )
    db.add(internship)
    db.flush()

    # Update the request
    req.status = "approved"
    req.approved_internship_id = internship.id
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # Send notification email (if email service is set up)
    try:
        from app.services.email_service import EmailService
        company = db.query(Company).filter(Company.id == req.company_id).first()
        if company and company.contact_email:
            EmailService.send_internship_request_approved_email(
                company.contact_email,
                req.title,
                internship.slug,
            )
    except Exception:
        pass  # Email failures should not block approval

    return {
        "message": "Internship request approved",
        "internship_id": internship.id,
        "slug": internship.slug,
    }


@router.post("/internship-requests/{request_id}/reject")
async def reject_internship_request(
    request_id: int,
    body: RejectInternshipRequestRequest,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    req = db.query(InternshipRequest).filter(InternshipRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status == "approved":
        raise HTTPException(status_code=400, detail="Cannot reject an approved request")

    req.status = "rejected"
    req.rejection_reason = body.reason
    req.reviewed_by = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    # Send notification email (if email service is set up)
    try:
        from app.services.email_service import EmailService
        company = db.query(Company).filter(Company.id == req.company_id).first()
        if company and company.contact_email:
            EmailService.send_internship_request_rejected_email(
                company.contact_email,
                req.title,
                body.reason,
            )
    except Exception:
        pass  # Email failures should not block rejection

    return {"message": "Internship request rejected"}


@router.delete("/internship-requests/{request_id}", status_code=204)
async def delete_internship_request(
    request_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Delete an internship request. Only pending requests can be deleted."""
    req = db.query(InternshipRequest).filter(InternshipRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status == "approved":
        raise HTTPException(status_code=400, detail="Cannot delete an approved request")

    db.delete(req)
    db.commit()
    return

# ============================================================
# Blog Management Endpoints
# ============================================================

@router.get("/blogs")
async def list_all_blogs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title/content"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT/PUBLISHED)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    List all blog posts with pagination, search, and filtering.
    Admin can see all blogs regardless of author.
    """
    query = db.query(BlogPost).options(joinedload(BlogPost.author))

    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (BlogPost.title.ilike(search_pattern)) |
            (BlogPost.content.ilike(search_pattern))
        )

    # Apply status filter
    if status:
        query = query.filter(BlogPost.status == status.upper())

    # Apply category filter
    if category:
        query = query.filter(BlogPost.category == category)

    # Order by created_at descending
    query = query.order_by(desc(BlogPost.created_at))

    # Pagination
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    blogs = query.offset(offset).limit(page_size).all()

    # Build response with author names
    result = []
    for blog in blogs:
        result.append({
            "id": blog.id,
            "title": blog.title,
            "slug": blog.slug,
            "status": blog.status.lower(),
            "category": blog.category,
            "author_name": blog.author.display_name or blog.author.user_login,
            "views": blog.view_count,
            "created_at": blog.created_at.isoformat() if blog.created_at else None
        })

    return {
        "blogs": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/blogs/categories")
async def list_blog_categories(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    M-4: every distinct, non-empty blog category currently in use.

    BlogPost.category (models/blog.py:38) is a free-text String column, not
    an FK to a categories table — there is no separate category catalog to
    read from. Deliberately declared BEFORE the app never mounted a
    conflicting GET /blogs/{blog_id}, and without a trailing slash to match
    every other route in this file (redirect_slashes=False app-wide).
    """
    rows = (
        db.query(BlogPost.category)
        .filter(BlogPost.category.isnot(None), BlogPost.category != "")
        .distinct()
        .order_by(BlogPost.category)
        .all()
    )
    return [r[0] for r in rows]


@router.put("/blogs/{blog_id}", response_model=BlogManagementResponse)
async def update_blog_post(
    blog_id: int,
    update_data: BlogUpdateRequest,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Update any blog post. Admin can edit any blog regardless of author.
    Updates slug if title changes.
    """
    blog = db.query(BlogPost).filter(BlogPost.id == blog_id).first()
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )

    # Update fields if provided
    if update_data.title is not None:
        blog.title = update_data.title
        # Generate new slug from title
        base_slug = re.sub(r"[^a-z0-9]+", "-", (update_data.title or "").lower()).strip("-")
        base_slug = base_slug or "blog"
        # Ensure uniqueness
        existing = db.query(BlogPost).filter(
            BlogPost.slug == base_slug,
            BlogPost.id != blog_id
        ).first()
        if existing:
            blog.slug = f"{base_slug}-{blog_id}"
        else:
            blog.slug = base_slug

    if update_data.content is not None:
        blog.content = update_data.content
    if update_data.excerpt is not None:
        blog.excerpt = update_data.excerpt
    if update_data.featured_image is not None:
        blog.featured_image = update_data.featured_image
    if update_data.category is not None:
        blog.category = update_data.category
    if update_data.tags is not None:
        blog.tags = update_data.tags
    if update_data.status is not None:
        blog.status = update_data.status.upper()

    blog.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(blog)

    # Load author for response
    blog = db.query(BlogPost).options(joinedload(BlogPost.author)).filter(BlogPost.id == blog_id).first()

    return BlogManagementResponse(
        id=blog.id,
        title=blog.title,
        slug=blog.slug,
        status=blog.status,
        category=blog.category,
        author_name=f"{blog.author.first_name or ''} {blog.author.last_name or ''}".strip() or blog.author.display_name or blog.author.user_login,
        view_count=blog.view_count,
        created_at=blog.created_at
    )


@router.delete("/blogs/{blog_id}")
async def delete_blog_post(
    blog_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete any blog post. Admin can delete any blog regardless of author.
    """
    blog = db.query(BlogPost).filter(BlogPost.id == blog_id).first()
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )

    db.delete(blog)
    db.commit()

    return {"message": "Blog post deleted successfully"}


@router.patch("/blogs/{blog_id}/status")
async def update_blog_status(
    blog_id: int,
    status_data: BlogStatusUpdateRequest,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Update blog post status.
    Supports: DRAFT, PUBLISHED, PENDING (for student submissions)
    """
    valid_statuses = ["DRAFT", "PUBLISHED", "PENDING"]
    status_upper = status_data.status.upper()

    if status_upper not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    blog = db.query(BlogPost).filter(BlogPost.id == blog_id).first()
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )

    blog.status = status_upper
    blog.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(blog)

    return {"message": f"Blog post status updated to {status_upper}"}


@router.post("/blogs/bulk-delete")
async def bulk_delete_blogs(
    request_data: BulkDeleteRequest,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete multiple blog posts at once.
    """
    if not request_data.blog_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="blog_ids cannot be empty"
        )

    # Check which blogs exist
    blogs = db.query(BlogPost).filter(BlogPost.id.in_(request_data.blog_ids)).all()
    found_ids = {blog.id for blog in blogs}
    missing_ids = set(request_data.blog_ids) - found_ids

    # Delete all found blogs
    for blog in blogs:
        db.delete(blog)

    db.commit()

    return {
        "message": f"Deleted {len(blogs)} blog post(s)",
        "deleted_count": len(blogs),
        "not_found": list(missing_ids) if missing_ids else None
    }
