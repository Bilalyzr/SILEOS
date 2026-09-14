"""Company invoicing models — tax invoices, seat pools, and fulfillment.

Owned by the company-invoicing implementer.

Tables:
  - company_invoices: invoice header (status, GST breakdown, due date, payment tracking).
  - company_invoice_items: line items per invoice (course/bundle seat counts, pricing).
  - company_seat_pools: materialized seat packages created at SETTLEMENT
    (invoice_service.settle_invoice, i.e. when the invoice becomes PAID) — not
    at issue. An issued-but-unpaid invoice conveys no seats.
    One pool per (course, bundle) per invoice — seats assigned from pools as users enroll.
  - company_seat_assignments: who is assigned to which seat in a pool.
  - invoice_counter: fiscal-year tracking for invoice number generation.
"""
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    Boolean,
)
from sqlalchemy.types import Enum, Numeric
from sqlalchemy.sql import func

from app.core.database import Base


class InvoiceStatus(enum.Enum):
    DRAFT = "draft"           # Not yet issued; no invoice_number yet
    ISSUED = "issued"         # Invoice number assigned + PDF rendered; no seats yet
    PAID = "paid"             # Payment confirmed (paid_at + paid_via set); seat pools created
    CANCELLED = "cancelled"   # Void


class CompanyInvoice(Base):
    """Tax invoice for a company's bulk seat purchase."""
    __tablename__ = "company_invoices"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )

    invoice_number = Column(String(30), unique=True, nullable=True)  # Assigned at ISSUED
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.DRAFT)

    subtotal = Column(Numeric(12, 2), nullable=False)  # Before tax
    cgst = Column(Numeric(12, 2), nullable=False, default=0)  # Central GST (within-state)
    sgst = Column(Numeric(12, 2), nullable=False, default=0)  # State GST (within-state)
    igst = Column(Numeric(12, 2), nullable=False, default=0)  # Integrated GST (inter-state)
    total = Column(Numeric(12, 2), nullable=False)  # subtotal + cgst + sgst + igst

    tax_note = Column(String(255), default="")  # e.g. "CGST: 9%, SGST: 9%"
    due_date = Column(DateTime(timezone=True), nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    paid_via = Column(String(50), default="")  # 'razorpay', 'bank_transfer', 'check', ...
    payment_reference = Column(String(100), default="")  # Gateway ID, check #, etc.
    pdf_path = Column(String(500), default="")  # Relative path to uploaded PDF
    notes = Column(Text, default="")  # Internal notes

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return (
            f"<CompanyInvoice(id={self.id}, company_id={self.company_id}, "
            f"invoice_number={self.invoice_number}, status={self.status})>"
        )


class CompanyInvoiceItem(Base):
    """Line item on an invoice — one course or bundle per row."""
    __tablename__ = "company_invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(
        Integer, ForeignKey("company_invoices.id"), nullable=False, index=True
    )

    description = Column(String(255), nullable=False)  # "Python 101", "Spring Bundle", etc.
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)  # OR
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=True)  # one of these

    quantity = Column(Integer, nullable=False)  # Number of seats
    unit_price = Column(Numeric(10, 2), nullable=False)  # Price per seat
    line_total = Column(Numeric(12, 2), nullable=False)  # quantity * unit_price

    def __repr__(self):
        return (
            f"<CompanyInvoiceItem(id={self.id}, invoice_id={self.invoice_id}, "
            f"description={self.description})>"
        )


class CompanySeatPool(Base):
    """A pool of seats purchased for a course or bundle.

    Created by invoice_service.settle_invoice when the invoice is SETTLED
    (status -> PAID), not when it is issued: an issued-but-unpaid invoice
    conveys no seats. order_id is stamped in the same call and used by seat
    assignment to give the granted enrollments a purchase-class order backing.
    """
    __tablename__ = "company_seat_pools"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    invoice_id = Column(
        Integer, ForeignKey("company_invoices.id"), nullable=False, index=True
    )
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # Stamped by settle_invoice

    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)  # OR
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=True)  # one of these

    total_seats = Column(Integer, nullable=False)
    used_seats = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return (
            f"<CompanySeatPool(id={self.id}, company_id={self.company_id}, "
            f"total_seats={self.total_seats}, used_seats={self.used_seats})>"
        )


class CompanySeatAssignment(Base):
    """Maps a user to a seat in a pool."""
    __tablename__ = "company_seat_assignments"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(
        Integer, ForeignKey("company_seat_pools.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("pool_id", "user_id", name="uq_seat_assignment_pool_user"),
    )

    def __repr__(self):
        return (
            f"<CompanySeatAssignment(id={self.id}, pool_id={self.pool_id}, "
            f"user_id={self.user_id})>"
        )


class InvoiceCounter(Base):
    """Fiscal-year invoice number generation."""
    __tablename__ = "invoice_counter"

    fiscal_year = Column(String(4), primary_key=True)  # '2627', '2728', etc.
    last_number = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return (
            f"<InvoiceCounter(fiscal_year={self.fiscal_year}, "
            f"last_number={self.last_number})>"
        )
