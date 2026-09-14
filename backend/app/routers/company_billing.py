"""
Company billing portal — company-facing invoicing/seat-pool API.

Mounted at /api/v1/companies/billing.

Cross-company isolation is the top requirement: every endpoint resolves the
caller's own company (owner via Company.owner_user_id, or manager via the
CompanyManager link — mirrors app/services/company_scope.get_my_company /
app/routers/company_dashboard.py's resolution pattern) and 404s (never
403-leaks existence) on any resource that belongs to a different company.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy import func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.bundle import Bundle, BundleCourse
from app.models.company import Company
from app.models.company_dashboard import CompanyManager
from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatAssignment, CompanySeatPool,
    InvoiceStatus,
)
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.company_billing import (
    CompanyBillingProfileOut, CompanyBillingProfileUpdate,
    CompanyInvoiceItemOut, CompanyInvoiceOut,
    SeatAssignRequest, SeatAssignmentOut, SeatPoolOut,
)
from app.services.auth_service import AuthService
from app.services.fulfillment_service import grant_purchased_course
from app.services.invoice_pdf import ensure_invoice_pdf
from app.services.membership_access import PUBLISHED_STATUSES

router = APIRouter()


# ---------------- Auth helper ----------------

def _resolve_company(db: Session, user: User) -> Company:
    """Return the company the authenticated user belongs to — owner via
    Company.owner_user_id == user.id, or manager via the CompanyManager
    link. No company found → 403 (the caller has a company-eligible role
    but no company profile / manager link to act on)."""
    if user.role == "company":
        c = db.query(Company).filter(Company.owner_user_id == user.id).first()
        if not c:
            raise HTTPException(status_code=403, detail="No company profile")
        return c
    if user.role == "company_manager":
        link = db.query(CompanyManager).filter(CompanyManager.user_id == user.id).first()
        if not link:
            raise HTTPException(status_code=403, detail="Manager not linked to a company")
        c = db.query(Company).filter(Company.id == link.company_id).first()
        if not c:
            raise HTTPException(status_code=403, detail="No company profile")
        return c
    raise HTTPException(status_code=403, detail="Company access required")


# ---------------- Profile ----------------

@router.get("/profile", response_model=CompanyBillingProfileOut)
def get_billing_profile(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = _resolve_company(db, user)
    return CompanyBillingProfileOut(
        name=company.name,
        gstin=company.gstin or "",
        legal_name=company.legal_name or "",
        billing_address=company.billing_address or "",
        state_code=company.state_code or "",
    )


@router.patch("/profile", response_model=CompanyBillingProfileOut)
def update_billing_profile(
    body: CompanyBillingProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = _resolve_company(db, user)
    if body.gstin is not None:
        company.gstin = body.gstin
    if body.legal_name is not None:
        company.legal_name = body.legal_name
    if body.billing_address is not None:
        company.billing_address = body.billing_address
    if body.state_code is not None:
        company.state_code = body.state_code
    db.commit()
    db.refresh(company)
    return CompanyBillingProfileOut(
        name=company.name,
        gstin=company.gstin or "",
        legal_name=company.legal_name or "",
        billing_address=company.billing_address or "",
        state_code=company.state_code or "",
    )


# ---------------- Invoices ----------------

_VISIBLE_STATUSES = (InvoiceStatus.ISSUED, InvoiceStatus.PAID, InvoiceStatus.CANCELLED)


def _invoice_out(db: Session, invoice: CompanyInvoice) -> CompanyInvoiceOut:
    items = db.query(CompanyInvoiceItem).filter(
        CompanyInvoiceItem.invoice_id == invoice.id).order_by(CompanyInvoiceItem.id).all()
    return CompanyInvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
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
        notes=invoice.notes or "",
        items=[
            CompanyInvoiceItemOut(
                description=it.description,
                quantity=it.quantity,
                unit_price=float(it.unit_price),
                line_total=float(it.line_total),
            )
            for it in items
        ],
    )


@router.get("/invoices", response_model=list[CompanyInvoiceOut])
def list_invoices(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = _resolve_company(db, user)
    invoices = (
        db.query(CompanyInvoice)
        .filter(
            CompanyInvoice.company_id == company.id,
            CompanyInvoice.status.in_(_VISIBLE_STATUSES),
        )
        .order_by(CompanyInvoice.created_at.desc())
        .all()
    )
    return [_invoice_out(db, inv) for inv in invoices]


def _get_own_invoice_or_404(db: Session, company: Company, invoice_id: int) -> CompanyInvoice:
    invoice = db.query(CompanyInvoice).filter(
        CompanyInvoice.id == invoice_id,
        CompanyInvoice.company_id == company.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/invoices/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: int = Path(...),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = _resolve_company(db, user)
    invoice = _get_own_invoice_or_404(db, company, invoice_id)
    # Re-render on demand if the file went missing (lost bind mount / recreated
    # volume) — see ensure_invoice_pdf.
    path = ensure_invoice_pdf(db, invoice)
    if not path:
        raise HTTPException(status_code=404, detail="Invoice PDF not available")
    db.commit()
    filename = os.path.basename(path)
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.post("/invoices/{invoice_id}/pay")
def pay_invoice(
    invoice_id: int = Path(...),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.routers.payments import create_invoice_order_payload

    company = _resolve_company(db, user)
    invoice = _get_own_invoice_or_404(db, company, invoice_id)
    return create_invoice_order_payload(db, invoice, user)


# ---------------- Seat pools ----------------

def _seat_pool_out(db: Session, pool: CompanySeatPool) -> SeatPoolOut:
    course_title = None
    bundle_name = None
    if pool.course_id:
        course = db.query(Course).filter(Course.id == pool.course_id).first()
        course_title = course.post_title if course else None
    if pool.bundle_id:
        bundle = db.query(Bundle).filter(Bundle.id == pool.bundle_id).first()
        bundle_name = bundle.name if bundle else None
    return SeatPoolOut(
        id=pool.id,
        course_id=pool.course_id,
        bundle_id=pool.bundle_id,
        course_title=course_title,
        bundle_name=bundle_name,
        total_seats=pool.total_seats,
        used_seats=pool.used_seats,
    )


@router.get("/seat-pools", response_model=list[SeatPoolOut])
def list_seat_pools(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = _resolve_company(db, user)
    pools = db.query(CompanySeatPool).filter(
        CompanySeatPool.company_id == company.id).order_by(CompanySeatPool.id).all()
    return [_seat_pool_out(db, p) for p in pools]


def _get_own_pool_or_404(db: Session, company: Company, pool_id: int) -> CompanySeatPool:
    pool = db.query(CompanySeatPool).filter(
        CompanySeatPool.id == pool_id,
        CompanySeatPool.company_id == company.id,
    ).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Seat pool not found")
    return pool


def _bundle_published_paid_course_ids(db: Session, bundle_id: int) -> list[int]:
    """Every CURRENT published, paid course of a bundle — mirrors
    app/routers/bundles.py's catalog filter (PUBLISHED_STATUSES +
    course_price_type == 'paid')."""
    rows = (
        db.query(Course.id)
        .join(BundleCourse, BundleCourse.course_id == Course.id)
        .filter(
            BundleCourse.bundle_id == bundle_id,
            Course.course_price_type == "paid",
            Course.post_status.in_(PUBLISHED_STATUSES),
        )
        .all()
    )
    return [r[0] for r in rows]


@router.post("/seat-pools/{pool_id}/assign", response_model=SeatAssignmentOut, status_code=201)
def assign_seat(
    body: SeatAssignRequest,
    pool_id: int = Path(...),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    """Order of operations (binding): resolve pool (own, 404) -> resolve
    user (exact-match email, 404) -> duplicate check (409) -> resolve course
    list + already-enrolled check for course pools (409) -> atomic seat
    consume (409 on rowcount 0) -> assignment row + grants -> commit."""
    company = _resolve_company(db, user)
    pool = _get_own_pool_or_404(db, company, pool_id)

    # Exact-match lookup only — User.user_email.ilike(email) treats the
    # input as a LIKE pattern, so "%@example.com" would match (and enroll)
    # an arbitrary user at that domain. Mirrors app/routers/cohorts.py's
    # sa_func.lower(User.user_email) == email pattern.
    email = body.email.strip().lower()
    target = db.query(User).filter(sa_func.lower(User.user_email) == email).first()
    if not target:
        raise HTTPException(
            status_code=404,
            detail="No account with that email — ask them to sign up first",
        )

    existing = db.query(CompanySeatAssignment).filter(
        CompanySeatAssignment.pool_id == pool.id,
        CompanySeatAssignment.user_id == target.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already assigned a seat in this pool")

    # Resolve what this seat would actually convey BEFORE consuming it.
    course_ids: list[int] = []
    if pool.course_id:
        course_ids = [pool.course_id]
        already_enrolled = db.query(Enrollment).filter(
            Enrollment.course_id == pool.course_id,
            Enrollment.user_id == target.id,
            Enrollment.enrollment_status == "enrolled",
        ).first()
        if already_enrolled:
            raise HTTPException(
                status_code=409, detail="User already has access to this course",
            )
    elif pool.bundle_id:
        course_ids = _bundle_published_paid_course_ids(db, pool.bundle_id)
        if not course_ids:
            raise HTTPException(
                status_code=409,
                detail="This bundle currently has no available courses — contact support",
            )

    # Atomic, dialect-portable conditional update: only succeeds if a seat
    # is actually available at commit time, closing the non-atomic
    # read-modify-write race where two concurrent requests for the last
    # seat could both pass a prior `used_seats >= total_seats` check.
    result = db.query(CompanySeatPool).filter(
        CompanySeatPool.id == pool.id,
        CompanySeatPool.used_seats < CompanySeatPool.total_seats,
    ).update(
        {CompanySeatPool.used_seats: CompanySeatPool.used_seats + 1},
        synchronize_session=False,
    )
    if result == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="No seats left in this pool")

    assignment = CompanySeatAssignment(
        pool_id=pool.id, user_id=target.id, assigned_by=user.id,
    )
    db.add(assignment)

    order_id = pool.order_id
    granted_course_ids: list[int] = []
    already_had_course_ids: list[int] = []
    for course_id in course_ids:
        changed = grant_purchased_course(
            db, user_id=target.id, course_id=course_id,
            order_id=order_id, source="company",
        )
        (granted_course_ids if changed else already_had_course_ids).append(course_id)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already assigned a seat in this pool")
    db.refresh(assignment)

    return SeatAssignmentOut(
        user_id=target.id, email=target.user_email, assigned_at=assignment.assigned_at,
        granted_course_ids=granted_course_ids,
        already_had_course_ids=already_had_course_ids,
    )


@router.get("/seat-pools/{pool_id}/assignments", response_model=list[SeatAssignmentOut])
def list_seat_assignments(
    pool_id: int = Path(...),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = _resolve_company(db, user)
    pool = _get_own_pool_or_404(db, company, pool_id)
    rows = (
        db.query(CompanySeatAssignment, User)
        .join(User, User.id == CompanySeatAssignment.user_id)
        .filter(CompanySeatAssignment.pool_id == pool.id)
        .order_by(CompanySeatAssignment.assigned_at)
        .all()
    )
    return [
        SeatAssignmentOut(user_id=u.id, email=u.user_email, assigned_at=a.assigned_at)
        for a, u in rows
    ]
