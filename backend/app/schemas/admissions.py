"""Strict request and response contracts for the campus admissions API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import EmailStr, Field, field_validator, model_validator

from app.schemas.institution import Command


ProgramStatus = Literal["draft", "active", "archived"]
ProgramLevel = Literal[
    "school", "undergraduate", "postgraduate", "diploma", "certificate", "other"
]
IntakeStatus = Literal["draft", "open", "closed", "archived"]
ApplicationStage = Literal[
    "draft",
    "submitted",
    "screening",
    "documents",
    "assessment",
    "interview",
    "decision",
    "waitlisted",
    "offered",
    "admitted",
    "rejected",
    "withdrawn",
    "enrolled",
]
OfferStatus = Literal[
    "none", "draft", "issued", "accepted", "declined", "expired", "revoked"
]
DocumentStatus = Literal["pending", "submitted", "verified", "rejected", "waived"]
TaskStatus = Literal["open", "in_progress", "completed", "cancelled"]
LearnerStatus = Literal[
    "enrolled", "active", "on_leave", "completed", "withdrawn", "transferred"
]


class ProgramCreate(Command):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(
        min_length=2, max_length=24, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
    )
    level: ProgramLevel = "other"
    department: str = Field(default="", max_length=100)
    duration_months: int = Field(ge=1, le=240)
    status: ProgramStatus = "draft"

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.upper()


class ProgramUpdate(Command):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=24,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
    )
    level: ProgramLevel | None = None
    department: str | None = Field(default=None, max_length=100)
    duration_months: int | None = Field(default=None, ge=1, le=240)
    status: ProgramStatus | None = None

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @model_validator(mode="after")
    def has_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one program change.")
        return self


class ProgramOut(Command):
    id: int
    name: str
    code: str
    level: str
    department: str
    duration_months: int
    status: str
    created_at: datetime


class IntakeCreate(Command):
    program_id: int = Field(gt=0)
    batch_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=2, max_length=120)
    academic_year: str = Field(min_length=4, max_length=32)
    starts_on: date
    closes_on: date
    capacity: int = Field(ge=1, le=100_000)
    status: IntakeStatus = "draft"

    @model_validator(mode="after")
    def valid_dates(self):
        if self.closes_on > self.starts_on:
            raise ValueError(
                "Applications must close on or before the intake start date."
            )
        return self


class IntakeUpdate(Command):
    batch_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    academic_year: str | None = Field(default=None, min_length=4, max_length=32)
    starts_on: date | None = None
    closes_on: date | None = None
    capacity: int | None = Field(default=None, ge=1, le=100_000)
    status: IntakeStatus | None = None

    @model_validator(mode="after")
    def has_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one intake change.")
        return self


class IntakeOut(Command):
    id: int
    program_id: int
    program_name: str
    batch_id: int | None
    name: str
    academic_year: str
    starts_on: date
    closes_on: date
    capacity: int
    status: str
    applications: int
    enrolled: int
    available: int


class ApplicationCreate(Command):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    phone: str = Field(default="", max_length=20, pattern=r"^$|^\+[1-9]\d{7,14}$")
    program_id: int = Field(gt=0)
    intake_id: int = Field(gt=0)
    date_of_birth: date | None = None
    address: str = Field(default="", max_length=1000)
    prior_institution: str = Field(default="", max_length=160)
    source: str = Field(default="manual", min_length=2, max_length=60)

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_is_past(cls, value: date | None) -> date | None:
        if value and value >= date.today():
            raise ValueError("Date of birth must be in the past.")
        return value


class ApplicationUpdate(Command):
    expected_version: int = Field(gt=0)
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(
        default=None, max_length=20, pattern=r"^$|^\+[1-9]\d{7,14}$"
    )
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=1000)
    prior_institution: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, min_length=2, max_length=60)
    owner_member_id: int | None = Field(default=None, gt=0)

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_is_past(cls, value: date | None) -> date | None:
        if value and value >= date.today():
            raise ValueError("Date of birth must be in the past.")
        return value

    @model_validator(mode="after")
    def has_change(self):
        if self.model_fields_set == {"expected_version"}:
            raise ValueError("Provide at least one application change.")
        return self


class StageUpdate(Command):
    stage: ApplicationStage
    reason: str = Field(default="", max_length=1000)
    expected_version: int = Field(gt=0)


class DocumentCreate(Command):
    kind: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    label: str = Field(min_length=2, max_length=120)
    required: bool = True
    due_on: date | None = None


class DocumentUpdate(Command):
    status: DocumentStatus
    rejection_reason: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def valid_rejection(self):
        if self.status == "rejected" and not self.rejection_reason:
            raise ValueError("A rejection reason is required.")
        if self.status != "rejected" and self.rejection_reason:
            raise ValueError("A rejection reason is only valid for rejected documents.")
        return self


class NoteCreate(Command):
    body: str = Field(min_length=1, max_length=4000)


class TaskCreate(Command):
    title: str = Field(min_length=2, max_length=200)
    due_on: date | None = None
    assignee_member_id: int | None = Field(default=None, gt=0)


class TaskUpdate(Command):
    status: TaskStatus
    title: str | None = Field(default=None, min_length=2, max_length=200)
    due_on: date | None = None
    assignee_member_id: int | None = Field(default=None, gt=0)


class OfferUpdate(Command):
    status: OfferStatus
    expires_on: date | None = None
    conditions: str = Field(default="", max_length=4000)
    tuition_amount: Decimal | None = Field(
        default=None, ge=0, le=Decimal("9999999999.99")
    )
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    reason: str = Field(default="", max_length=1000)
    expected_version: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_issue(self):
        if (
            self.status == "issued"
            and self.expires_on
            and self.expires_on < date.today()
        ):
            raise ValueError("An issued offer cannot already be expired.")
        return self

    @field_validator("tuition_amount")
    @classmethod
    def cents_only(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value.as_tuple().exponent < -2:
            raise ValueError("Tuition amount supports at most two decimal places.")
        return value


class ConversionCreate(Command):
    member_id: int | None = Field(default=None, gt=0)
    batch_id: int | None = Field(default=None, gt=0)
    admission_number: str | None = Field(
        default=None,
        min_length=2,
        max_length=32,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_/-]*$",
    )
    joined_on: date | None = None
    expected_version: int = Field(gt=0)


class LearnerLifecycleUpdate(Command):
    status: LearnerStatus
    reason: str = Field(default="", max_length=1000)
    effective_on: date | None = None
    expected_version: int = Field(gt=0)


class DocumentOut(Command):
    id: int
    kind: str
    label: str
    required: bool
    status: str
    due_on: date | None
    rejection_reason: str
    verified_at: datetime | None


class NoteOut(Command):
    id: int
    body: str
    author_id: int | None
    author_name: str
    created_at: datetime


class TaskOut(Command):
    id: int
    title: str
    due_on: date | None
    status: str
    assignee_member_id: int | None
    assignee_name: str
    completed_at: datetime | None
    created_at: datetime


class HistoryOut(Command):
    id: int
    from_stage: str | None
    to_stage: str
    reason: str
    actor_id: int | None
    actor_name: str
    created_at: datetime


class LearnerHistoryOut(Command):
    id: int
    from_status: str | None
    to_status: str
    reason: str
    effective_on: date
    actor_id: int | None
    actor_name: str
    created_at: datetime


class LearnerProfileOut(Command):
    id: int
    member_id: int
    learner_name: str
    learner_email: str
    application_id: int | None
    program_id: int
    program_name: str
    intake_id: int
    intake_name: str
    admission_number: str
    status: str
    joined_on: date
    expected_completion_on: date | None
    completed_on: date | None
    exit_reason: str
    version: int
    history: list[LearnerHistoryOut] = Field(default_factory=list)


class ApplicationListItem(Command):
    id: int
    application_number: str
    full_name: str
    email: str
    phone: str
    program_id: int
    program_name: str
    intake_id: int
    intake_name: str
    stage: str
    offer_status: str
    source: str
    owner_member_id: int | None
    enrollment_member_id: int | None
    submitted_at: datetime
    updated_at: datetime
    version: int


class ApplicationDetail(ApplicationListItem):
    date_of_birth: date | None
    address: str
    prior_institution: str
    offer_expires_on: date | None
    offer_conditions: str
    tuition_amount: Decimal | None
    offer_currency: str
    invitation_id: int | None
    documents: list[DocumentOut]
    notes: list[NoteOut]
    tasks: list[TaskOut]
    history: list[HistoryOut]
    learner_profile: LearnerProfileOut | None


class ApplicationPage(Command):
    items: list[ApplicationListItem]
    total: int
    limit: int
    offset: int


class MetricCount(Command):
    stage: str | None = None
    status: str | None = None
    count: int


class SummaryCounts(Command):
    total: int
    active: int
    offered: int
    admitted: int
    enrolled: int
    rejected: int
    withdrawn: int


class TaskCounts(Command):
    open: int
    overdue: int
    due_soon: int


class AdmissionsSummary(Command):
    counts: SummaryCounts
    stage_counts: list[MetricCount]
    offer_counts: list[MetricCount]
    tasks: TaskCounts
    intakes: list[IntakeOut]
    recent_applications: list[ApplicationListItem]


class ConversionOut(Command):
    outcome: Literal["enrolled", "invited"]
    application: ApplicationDetail
    learner_profile: LearnerProfileOut | None = None
    invitation_id: int | None = None
