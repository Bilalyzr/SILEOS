"""Schemas for the company-facing billing portal API (app/routers/company_billing.py)."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------- Profile ----------------

class CompanyBillingProfileOut(BaseModel):
    name: str
    gstin: str
    legal_name: str
    billing_address: str
    state_code: str


class CompanyBillingProfileUpdate(BaseModel):
    # Lengths are bounded here so an oversized value 422s at the edge.
    # gstin/legal_name match their columns (companies.gstin String(20),
    # legal_name String(255)) — over-length is a 500 on Postgres and a
    # silently stored overflow on SQLite. billing_address is a Text column,
    # so its cap is a policy limit that keeps an unbounded blob out of the
    # buyer block of every rendered tax invoice.
    gstin: str | None = Field(default=None, max_length=20)
    legal_name: str | None = Field(default=None, max_length=255)
    billing_address: str | None = Field(default=None, max_length=2000)
    state_code: str | None = None

    @field_validator("state_code")
    @classmethod
    def _validate_state_code(cls, v):
        if v is None:
            return v
        if v == "" or (len(v) == 2 and v.isdigit()):
            return v
        raise ValueError("state_code must be a 2-digit code (e.g. '29') or empty")


# ---------------- Invoices ----------------

class CompanyInvoiceItemOut(BaseModel):
    description: str
    quantity: int
    unit_price: float
    line_total: float


class CompanyInvoiceOut(BaseModel):
    id: int
    invoice_number: str | None = None
    status: str
    subtotal: float
    cgst: float
    sgst: float
    igst: float
    total: float
    tax_note: str
    due_date: datetime | None = None
    issued_at: datetime | None = None
    paid_at: datetime | None = None
    notes: str
    items: list[CompanyInvoiceItemOut]


# ---------------- Seat pools ----------------

class SeatPoolOut(BaseModel):
    id: int
    course_id: int | None = None
    bundle_id: int | None = None
    course_title: str | None = None
    bundle_name: str | None = None
    total_seats: int
    used_seats: int


class SeatAssignRequest(BaseModel):
    email: EmailStr


class SeatAssignmentOut(BaseModel):
    user_id: int
    email: str
    assigned_at: datetime | None = None
    granted_course_ids: list[int] = Field(default_factory=list)
    already_had_course_ids: list[int] = Field(default_factory=list)
