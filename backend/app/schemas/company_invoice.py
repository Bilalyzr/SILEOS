from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class InvoiceItemIn(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    course_id: int | None = None
    bundle_id: int | None = None
    quantity: int = Field(ge=1)
    unit_price: float = Field(gt=0)

    @model_validator(mode="after")
    def _one_of_course_or_bundle(self):
        if self.course_id is not None and self.bundle_id is not None:
            raise ValueError("An item may reference at most one of course_id/bundle_id")
        return self


class InvoiceItemOut(BaseModel):
    id: int
    description: str
    course_id: int | None = None
    bundle_id: int | None = None
    quantity: int
    unit_price: float
    line_total: float


class InvoiceCreate(BaseModel):
    company_id: int
    due_date: datetime | None = None
    notes: str = ""
    items: list[InvoiceItemIn] = Field(min_length=1)


class InvoiceUpdate(BaseModel):
    due_date: datetime | None = None
    notes: str | None = None
    items: list[InvoiceItemIn] | None = None


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str | None = None
    company_id: int
    company_name: str
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
    paid_via: str
    payment_reference: str
    notes: str
    items: list[InvoiceItemOut]


class MarkPaidRequest(BaseModel):
    reference: str = Field(min_length=1)
