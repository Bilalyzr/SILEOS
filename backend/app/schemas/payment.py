"""
Payment Schemas - Pydantic models for payment endpoints
"""

from pydantic import BaseModel, Field, model_validator, validator
from typing import Optional, Dict, Any
from datetime import datetime

class PaymentIntentRequest(BaseModel):
    course_id: int

class PaymentIntentResponse(BaseModel):
    payment_intent_id: Optional[str]
    client_secret: Optional[str]
    amount: float
    currency: str
    status: str
    enrollment_id: Optional[int]
    is_free_course: bool

class PaymentConfirmRequest(BaseModel):
    payment_intent_id: str
    payment_method_id: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    payment_intent_id: str
    course_id: int
    student_id: int
    amount: float
    currency: str
    status: str
    enrollment_id: int
    created_at: datetime

class TransactionResponse(BaseModel):
    id: int
    course_title: str
    amount: float
    currency: str
    status: str
    payment_method: str
    transaction_date: datetime

class RefundRequest(BaseModel):
    payment_id: int
    reason: str

    @validator('reason')
    def validate_reason(cls, v):
        if len(v) < 10:
            raise ValueError('Refund reason must be at least 10 characters')
        return v


_ONE_OF_MESSAGE = (
    "Provide exactly one of course_id, bundle_id, invoice_id, or ebook_id"
)


class CreateOrderRequest(BaseModel):
    """Body of POST /api/v1/payments/create-order. Field names mirror the
    frontend payload exactly — do not rename. Exactly one of
    course_id / bundle_id / invoice_id / ebook_id."""
    course_id: int | None = None
    bundle_id: int | None = None
    invoice_id: int | None = None
    ebook_id: int | None = None
    coupon_code: str | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self):
        targets = [self.course_id, self.bundle_id, self.invoice_id, self.ebook_id]
        if sum(bool(t) for t in targets) != 1:
            raise ValueError(_ONE_OF_MESSAGE)
        return self


class VerifyPaymentRequest(BaseModel):
    """Body of POST /api/v1/payments/verify. Exactly one of
    course_id / bundle_id / invoice_id / ebook_id."""
    razorpay_order_id: str = Field(pattern=r"^order_[A-Za-z0-9]+$", max_length=64)
    razorpay_payment_id: str = Field(pattern=r"^pay_[A-Za-z0-9]+$", max_length=64)
    razorpay_signature: str = Field(min_length=32, max_length=256)
    course_id: int | None = None
    bundle_id: int | None = None
    invoice_id: int | None = None
    ebook_id: int | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self):
        targets = [self.course_id, self.bundle_id, self.invoice_id, self.ebook_id]
        if sum(bool(t) for t in targets) != 1:
            raise ValueError(_ONE_OF_MESSAGE)
        return self


class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    cohort_id: int | None = None