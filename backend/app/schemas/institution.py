"""Validated institution commands; no client-supplied owner, tenant, or plan state."""
from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator


class Command(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class InstitutionCreate(Command):
    name: str = Field(min_length=2, max_length=160)
    kind: Literal["school", "college"] = "school"
    academic_year: str = Field(min_length=4, max_length=32)
    timezone: str = "Asia/Kolkata"
    description: str = Field(default="", max_length=1000)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Choose a valid IANA timezone") from None
        return value


class InviteCreate(Command):
    email: EmailStr
    role: Literal["admin", "teacher", "student"] = "student"
    department: str = Field(default="", max_length=100)


class MemberUpdate(Command):
    role: Literal["admin", "teacher", "student"]
    department: str = Field(default="", max_length=100)
    status: Literal["active", "suspended"] = "active"


class BatchCreate(Command):
    name: str = Field(min_length=2, max_length=100)
    department: str = Field(default="", max_length=100)
    academic_year: str = Field(min_length=4, max_length=32)


class BatchMembers(Command):
    member_ids: list[int] = Field(min_length=1, max_length=100)


class CourseConnect(Command):
    course_id: int = Field(gt=0)


class AssignmentCreate(Command):
    institution_course_id: int = Field(gt=0)
    due_date: date | None = None


class PlanRequestCreate(Command):
    plan: Literal["campus", "enterprise"]
    note: str = Field(default="", max_length=1000)


class PlanRequestReview(Command):
    status: Literal["reviewed", "declined"]
    note: str = Field(min_length=3, max_length=200)
