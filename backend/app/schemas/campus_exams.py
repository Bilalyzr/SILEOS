from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")


ExamKind = Literal["unit", "midterm", "final", "practical", "other"]


class ExamCreate(Command):
    term_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=160)
    kind: ExamKind = "other"


class ExamUpdate(Command):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    kind: ExamKind | None = None


class PaperCreate(Command):
    batch_id: int = Field(gt=0)
    subject: str = Field(min_length=1, max_length=120)
    max_marks: float = Field(gt=0, le=1000)
    pass_marks: float = Field(default=0, ge=0)
    starts_at: datetime
    duration_minutes: int = Field(ge=15, le=600)
    room: str = Field(default="", max_length=80)

    @model_validator(mode="after")
    def valid(self):
        if self.starts_at.tzinfo is None:
            raise ValueError("Paper times must include a UTC offset.")
        if self.pass_marks > self.max_marks:
            raise ValueError("Pass marks cannot exceed maximum marks.")
        return self


class PaperUpdate(Command):
    subject: str | None = Field(default=None, min_length=1, max_length=120)
    max_marks: float | None = Field(default=None, gt=0, le=1000)
    pass_marks: float | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=600)
    room: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def valid(self):
        if self.starts_at is not None and self.starts_at.tzinfo is None:
            raise ValueError("Paper times must include a UTC offset.")
        return self


class MarkEntry(Command):
    member_id: int = Field(gt=0)
    marks: float | None = None
    absent: bool = False
    remarks: str = Field(default="", max_length=500)


class MarksPut(Command):
    entries: list[MarkEntry] = Field(min_length=1, max_length=500)
