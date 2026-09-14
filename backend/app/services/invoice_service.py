"""Invoice lifecycle: GST snapshot, sequential numbering, settlement.

settle_invoice is the single convergence point for ALL payment routes
(online verify/webhook/sweeper and offline mark-paid) — idempotent via
status gate + gateway_payment_id check. Callers commit.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatPool, InvoiceCounter,
    InvoiceStatus,
)
from app.models.payment import Order, OrderItem, OrderStatus, Payment, PaymentStatus
from app.models.course import Course
from app.core.business_verticals import revenue_metadata

logger = logging.getLogger(__name__)

_TWO = Decimal("0.01")


def _d(x) -> Decimal:
    return Decimal(str(x)).quantize(_TWO, rounding=ROUND_HALF_UP)


def compute_gst(subtotal: float, company: Company, settings):
    sub = _d(subtotal)
    rate = Decimal(str(settings.GST_RATE_PERCENT)) / Decimal("100")
    zero = _d(0)
    if not (settings.SELLER_GSTIN or "").strip():
        return zero, zero, zero, "No GST — seller unregistered"
    seller_state = (settings.SELLER_STATE_CODE or "").strip()
    buyer_state = (company.state_code or "").strip()
    if seller_state and buyer_state and seller_state == buyer_state:
        tax = _d(sub * rate)
        cgst = _d(tax / 2)
        sgst = tax - cgst  # absorbs the odd paise; cgst + sgst == tax exactly
        pct = settings.GST_RATE_PERCENT / 2
        return cgst, sgst, zero, f"CGST {pct:g}% + SGST {pct:g}%"
    return zero, zero, _d(sub * rate), f"IGST {settings.GST_RATE_PERCENT:g}%"


def fiscal_year_label(now: datetime) -> str:
    fy = now.year if now.month >= 4 else now.year - 1
    return f"{fy % 100:02d}{(fy + 1) % 100:02d}"


def allocate_invoice_number(db: Session, now: datetime) -> str:
    fy = fiscal_year_label(now)
    q = db.query(InvoiceCounter).filter(InvoiceCounter.fiscal_year == fy)
    if db.bind.dialect.name == "postgresql":
        q = q.with_for_update()
    counter = q.first()
    if counter is None:
        counter = InvoiceCounter(fiscal_year=fy, last_number=0)
        db.add(counter)
        db.flush()
    counter.last_number += 1
    return f"INV-{fy}-{counter.last_number:04d}"


def issue_invoice(db: Session, invoice: CompanyInvoice, *, pdf_renderer=None) -> None:
    if invoice.status != InvoiceStatus.DRAFT:
        raise ValueError("Only draft invoices can be issued")
    items = db.query(CompanyInvoiceItem).filter(
        CompanyInvoiceItem.invoice_id == invoice.id).all()
    if not items:
        raise ValueError("Invoice has no items")
    company = db.query(Company).filter(Company.id == invoice.company_id).one()
    from app.core.config import get_settings
    settings = get_settings()
    subtotal = _d(sum(float(i.line_total) for i in items))
    cgst, sgst, igst, note = compute_gst(float(subtotal), company, settings)
    invoice.subtotal = subtotal
    invoice.cgst, invoice.sgst, invoice.igst = cgst, sgst, igst
    invoice.total = _d(subtotal + cgst + sgst + igst)
    invoice.tax_note = note
    now = datetime.now(timezone.utc)
    invoice.invoice_number = allocate_invoice_number(db, now)
    invoice.issued_at = now
    invoice.status = InvoiceStatus.ISSUED
    if pdf_renderer is not None:
        invoice.pdf_path = pdf_renderer(invoice) or ""


def settle_invoice(db: Session, invoice: CompanyInvoice, *, via: str,
                   reference: str, gateway_payment_id: str = "",
                   gateway_order_id: str = "") -> bool:
    if gateway_payment_id and db.query(Payment).filter(
            Payment.gateway_payment_id == gateway_payment_id).first():
        return False
    if invoice.status != InvoiceStatus.ISSUED:
        return False
    company = db.query(Company).filter(Company.id == invoice.company_id).one()
    items = db.query(CompanyInvoiceItem).filter(
        CompanyInvoiceItem.invoice_id == invoice.id).all()
    now = datetime.now(timezone.utc)
    method = "razorpay_invoice" if via == "razorpay" else "bank_transfer"
    order = Order(
        user_id=company.owner_user_id,
        order_key=f"INV_{invoice.invoice_number or invoice.id}",
        order_status=OrderStatus.COMPLETED,
        currency="INR",
        subtotal_amount=invoice.subtotal, total_amount=invoice.total,
        payment_method=method,
        payment_method_title=f"Invoice {invoice.invoice_number or ''}".strip(),
        transaction_id=gateway_payment_id or reference,
        billing_company=company.legal_name or company.name,
        billing_email=company.contact_email or "",
        date_paid=now, date_completed=now,
    )
    db.add(order)
    db.flush()
    for it in items:
        # OrderItem.course_id is NOT NULL (WooCommerce-style schema). A line
        # with no course_id (a description-only line, or a bundle-ref line —
        # bundle_id has no OrderItem.bundle_id column either) gets NO
        # OrderItem row: the Order + Payment already carry the money, and
        # this mirrors the existing precedent for subscription/membership
        # orders, which likewise have no per-line OrderItem breakdown.
        if it.course_id:
            course = db.get(Course, it.course_id)
            db.add(OrderItem(order_id=order.id, course_id=it.course_id,
                             order_item_name=it.description,
                             order_item_type="invoice_item",
                             quantity=it.quantity,
                             subtotal=it.line_total, total=it.line_total,
                             product_data=revenue_metadata(course.course_type) if course else {}))
        if it.course_id or it.bundle_id:
            db.add(CompanySeatPool(
                company_id=company.id, invoice_id=invoice.id,
                order_id=order.id,
                course_id=it.course_id, bundle_id=it.bundle_id,
                total_seats=it.quantity))
    db.add(Payment(user_id=company.owner_user_id, order_id=order.id,
                   payment_method=method,
                   gateway_transaction_id=gateway_payment_id,
                   gateway_payment_id=gateway_payment_id,
                   gateway_order_id=gateway_order_id,
                   amount=invoice.total, currency="INR",
                   payment_status=PaymentStatus.COMPLETED,
                   processed_date=now))
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = now
    invoice.paid_via = via
    invoice.payment_reference = reference
    return True
