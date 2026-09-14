"""Validated commands for the institution pilot workspace."""

from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import Field, HttpUrl, field_validator, model_validator

from app.schemas.institution import Command


class OnboardingUpdate(Command):
    dismissed: bool


class EventCreate(Command):
    title: str = Field(min_length=2, max_length=160)
    kind: Literal["class", "exam", "event", "holiday", "meeting"] = "class"
    starts_at: datetime
    ends_at: datetime
    batch_id: int | None = Field(default=None, gt=0)
    teacher_member_id: int | None = Field(default=None, gt=0)
    location: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=1000)
    recurrence: Literal["none", "daily", "weekly"] = "none"
    repeat_until: date | None = None

    @model_validator(mode="after")
    def valid_window(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Event times must include a UTC offset.")
        if self.ends_at <= self.starts_at:
            raise ValueError("The event must end after it starts.")
        if self.recurrence == "none" and self.repeat_until is not None:
            raise ValueError("repeat_until is only valid for recurring events.")
        if self.recurrence != "none":
            if self.repeat_until is None:
                raise ValueError("Recurring events require repeat_until.")
            if self.repeat_until < self.starts_at.date():
                raise ValueError("repeat_until cannot be before the first event.")
            if self.repeat_until > self.starts_at.date() + timedelta(days=366):
                raise ValueError("A recurring series cannot exceed one year.")
        return self


class AnnouncementCreate(Command):
    title: str = Field(min_length=2, max_length=160)
    body: str = Field(min_length=1, max_length=8000)
    batch_id: int | None = Field(default=None, gt=0)


class GoalCreate(Command):
    title: str = Field(min_length=2, max_length=160)
    target_date: date
    member_id: int | None = Field(default=None, gt=0)


class GoalUpdate(Command):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    target_date: date | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    status: Literal["planned", "in_progress", "completed"] | None = None

    @model_validator(mode="after")
    def has_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one goal field is required.")
        return self


class GradeBand(Command):
    label: str = Field(min_length=1, max_length=20)
    min_percent: float = Field(ge=0, le=100, allow_inf_nan=False)


class GradePolicySave(Command):
    bands: list[GradeBand] = Field(min_length=2, max_length=20)

    @field_validator("bands")
    @classmethod
    def valid_bands(cls, bands):
        labels = [band.label.casefold() for band in bands]
        thresholds = [band.min_percent for band in bands]
        if len(labels) != len(set(labels)) or len(thresholds) != len(set(thresholds)):
            raise ValueError("Grade labels and thresholds must be unique.")
        if thresholds != sorted(thresholds, reverse=True):
            raise ValueError("Grade bands must be ordered from highest to lowest.")
        if thresholds[-1] != 0:
            raise ValueError("The final grade band must start at 0 percent.")
        return bands


class ReportCommentSave(Command):
    term_id: int = Field(gt=0)
    overall_comment: str = Field(default="", max_length=2000)


class WhatsAppOptIn(Command):
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$", max_length=16)


class WhatsAppCampaignCreate(Command):
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")
    template: str = Field(pattern=r"^[a-z0-9_]{1,120}$")
    language: str = Field(default="en", pattern=r"^[A-Za-z_-]{2,20}$")
    parameters: list[str] = Field(default_factory=list, max_length=10)
    batch_id: int | None = Field(default=None, gt=0)
    header_image_url: HttpUrl | None = Field(default=None, max_length=500)

    @field_validator("parameters")
    @classmethod
    def bounded_parameters(cls, values):
        if any(not value.strip() or len(value) > 256 for value in values):
            raise ValueError("Template parameters must be 1 to 256 characters.")
        return [value.strip() for value in values]

    @field_validator("header_image_url")
    @classmethod
    def https_header(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("WhatsApp header images must use HTTPS.")
        return value
