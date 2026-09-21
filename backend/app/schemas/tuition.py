"""Validated commands and public response shapes for institution tuition fees."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.institution import Command


MoneyInput = Decimal


class FeeComponentCreate(Command):
    code: str = Field(
        min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
    )
    name: str = Field(min_length=2, max_length=120)
    amount: MoneyInput = Field(gt=0, max_digits=13, decimal_places=2)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class InstallmentTemplateCreate(Command):
    name: str = Field(min_length=2, max_length=120)
    due_on: date
    amount: MoneyInput = Field(gt=0, max_digits=13, decimal_places=2)


class FeePlanCreate(Command):
    name: str = Field(min_length=2, max_length=160)
    academic_year: str = Field(min_length=4, max_length=32)
    currency: str = Field(
        default="INR", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"
    )
    description: str = Field(default="", max_length=1000)
    components: list[FeeComponentCreate] = Field(min_length=1, max_length=50)
    installments: list[InstallmentTemplateCreate] = Field(min_length=1, max_length=24)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_totals_and_duplicates(self):
        component_total = sum((row.amount for row in self.components), Decimal("0"))
        installment_total = sum((row.amount for row in self.installments), Decimal("0"))
        if component_total != installment_total:
            raise ValueError("Fee component and installment totals must match exactly.")
        codes = [row.code for row in self.components]
        if len(codes) != len(set(codes)):
            raise ValueError("Fee component codes must be unique.")
        return self


class FeeAssignmentCreate(Command):
    student_member_id: int = Field(gt=0)
    plan_id: int = Field(gt=0)
    note: str = Field(default="", max_length=500)


class TuitionPaymentCreate(Command):
    amount: MoneyInput = Field(gt=0, max_digits=13, decimal_places=2)
    paid_at: datetime | None = None
    method: Literal["cash", "bank_transfer", "card", "upi", "cheque", "online"]
    reference: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=500)
    # Required for cash and cheque: the staff member who took the money.
    received_by_member_id: int | None = Field(default=None, gt=0)


class PaymentVerify(Command):
    note: str = Field(default="", max_length=300)


class InvoiceCreate(Command):
    installment_id: int | None = Field(default=None, gt=0)


class OnlineOrderCreate(Command):
    installment_id: int | None = Field(default=None, gt=0)
    amount: Annotated[MoneyInput, Field(gt=0, max_digits=13, decimal_places=2)] | None = None


class OnlineVerify(Command):
    razorpay_order_id: str = Field(min_length=1, max_length=64)
    razorpay_payment_id: str = Field(min_length=1, max_length=64)
    razorpay_signature: str = Field(min_length=1, max_length=200)


class TuitionAdjustmentCreate(Command):
    kind: Literal["discount", "waiver"]
    amount: MoneyInput = Field(gt=0, max_digits=13, decimal_places=2)
    reason: str = Field(min_length=3, max_length=500)
    installment_id: int | None = Field(default=None, gt=0)


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FeeComponentOut(Out):
    id: int
    code: str
    name: str
    amount: float


class InstallmentTemplateOut(Out):
    id: int
    name: str
    sequence: int
    due_on: date
    amount: float


class FeePlanOut(Out):
    id: int
    name: str
    academic_year: str
    currency: str
    description: str
    status: str
    total_amount: float
    components: list[FeeComponentOut]
    installments: list[InstallmentTemplateOut]
    created_at: datetime


class FeePlanListOut(Out):
    items: list[FeePlanOut]


class TuitionStudentOut(Out):
    member_id: int
    user_id: int
    name: str
    email: str


class TuitionAssignmentPlanOut(Out):
    id: int
    name: str
    academic_year: str


class TuitionInstallmentOut(Out):
    id: int
    name: str
    sequence: int
    due_on: date
    amount_due: float
    credited: float
    balance: float
    status: Literal["paid", "due", "overdue", "upcoming"]


class TuitionReceiptBriefOut(Out):
    id: int
    receipt_number: str
    issued_at: datetime


class TuitionPersonOut(Out):
    id: int
    name: str


class TuitionVerificationOut(Out):
    status: Literal["not_required", "pending", "verified"]
    verified_by: TuitionPersonOut | None
    verified_at: datetime | None
    note: str


class TuitionPaymentOut(Out):
    id: int
    amount: float
    paid_at: datetime
    method: str
    reference: str
    note: str
    status: str
    receipt: TuitionReceiptBriefOut
    received_by: TuitionPersonOut | None = None
    verification: TuitionVerificationOut


class TuitionAdjustmentOut(Out):
    id: int
    kind: str
    amount: float
    reason: str
    installment_id: int | None
    status: str
    created_at: datetime


class TuitionAssignmentOut(Out):
    id: int
    institution_id: int
    student: TuitionStudentOut
    plan: TuitionAssignmentPlanOut
    currency: str
    status: str
    assigned_on: date
    note: str
    gross_amount: float
    discounts_total: float
    waivers_total: float
    paid_total: float
    balance: float
    installments: list[TuitionInstallmentOut]
    payments: list[TuitionPaymentOut]
    adjustments: list[TuitionAdjustmentOut]


class TuitionSelfAccountsOut(Out):
    student: TuitionStudentOut
    assignments: list[TuitionAssignmentOut]


class TuitionAccountRowOut(Out):
    id: int
    student: TuitionStudentOut
    plan: TuitionAssignmentPlanOut
    currency: str
    status: str
    gross_amount: float
    balance: float
    overdue: float
    next_due_on: date | None


class TuitionAccountListOut(Out):
    items: list[TuitionAccountRowOut]
    next_cursor: int | None


class TuitionAgingBucketsOut(Out):
    current: float
    days_1_30: float
    days_31_60: float
    days_61_90: float
    days_91_plus: float


class TuitionSummaryTotalsOut(Out):
    assessed: float
    discounts: float
    waivers: float
    paid: float
    outstanding: float
    overdue: float
    due_today: float
    due_next_30_days: float


class TuitionSummaryAccountsOut(Out):
    total: int
    with_balance: int
    overdue: int


class TuitionSummaryOut(Out):
    as_of: date
    currency: str | None
    mixed_currency: bool
    totals: TuitionSummaryTotalsOut
    accounts: TuitionSummaryAccountsOut
    aging: TuitionAgingBucketsOut


class TuitionAgingRowOut(Out):
    assignment_id: int
    student_member_id: int
    student_user_id: int
    student_name: str
    plan_name: str
    currency: str
    outstanding: float
    overdue: float
    oldest_due_on: date | None
    aging: TuitionAgingBucketsOut


class TuitionAgingOut(Out):
    as_of: date
    rows: list[TuitionAgingRowOut]
    next_cursor: int | None


class TuitionPaymentRecordedOut(Out):
    replayed: bool
    payment: TuitionPaymentOut
    balance: float


class TuitionAdjustmentRecordedOut(Out):
    replayed: bool
    adjustment: TuitionAdjustmentOut
    balance: float


class TuitionReceiptOut(Out):
    id: int
    receipt_number: str
    issued_at: datetime
    institution_id: int
    institution_name: str
    student: TuitionStudentOut
    plan: TuitionAssignmentPlanOut
    amount: float
    currency: str
    balance_after: float
    paid_at: datetime
    method: str
    reference: str
