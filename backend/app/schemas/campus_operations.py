from datetime import date
from typing import Literal
from pydantic import Field, model_validator
from app.schemas.institution import Command


class BulkInvite(Command):
    csv: str = Field(min_length=1, max_length=100_000)
    commit: bool = False


class TermCreate(Command):
    name: str = Field(min_length=2, max_length=100)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def dates(self):
        if self.ends_on < self.starts_on:
            raise ValueError("The term must end on or after its start date.")
        return self


class AttendanceEntry(Command):
    member_id: int = Field(gt=0)
    status: Literal["present", "absent", "late", "excused"]


class AttendanceSave(Command):
    batch_id: int = Field(gt=0)
    day: date
    entries: list[AttendanceEntry] = Field(min_length=1, max_length=1000)


class AssessmentCreate(Command):
    batch_id: int = Field(gt=0)
    term_id: int | None = None
    title: str = Field(min_length=2, max_length=160)
    max_score: float = Field(gt=0, le=10000, allow_inf_nan=False)
    due_on: date | None = None


class ScoreEntry(Command):
    member_id: int = Field(gt=0)
    score: float = Field(ge=0, le=10000, allow_inf_nan=False)
    feedback: str = Field(default="", max_length=1000)


class ScoresSave(Command):
    entries: list[ScoreEntry] = Field(min_length=1, max_length=1000)


class BrandingSave(Command):
    title: str = Field(min_length=2, max_length=160)
    subtitle: str = Field(default="", max_length=320)


class LinkDecision(Command):
    status: Literal["approved", "declined", "revoked"]


class Subscribe(Command):
    plan: Literal["campus", "enterprise"]
    expected_plan_id: str | None = Field(default=None, max_length=80)


class ReconcileSubscription(Command):
    subscription_id: str = Field(pattern=r"^sub_[A-Za-z0-9]+$", max_length=80)


class CampusCourseDraft(Command):
    title: str = Field(min_length=2, max_length=160)
    summary: str = Field(default="", max_length=1000)
    batch_id: int | None = Field(default=None, gt=0)


class CampusLessonDraft(Command):
    title: str = Field(min_length=2, max_length=160)
    body: str = Field(min_length=1, max_length=32000)
    resource_id: int | None = Field(default=None, gt=0)


class CampusPublish(Command):
    published: bool
