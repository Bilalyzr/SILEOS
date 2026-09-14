from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeaveTypeIn(Command):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    annual_quota: int = Field(ge=0, le=366)

    @field_validator("code")
    @classmethod
    def clean_code(cls, value):
        value = value.strip().upper().replace(" ", "_")
        if not value.replace("_", "a").isalnum():
            raise ValueError("Leave codes use letters, digits and underscores only.")
        return value


class LeaveTypesPut(Command):
    academic_year: str = Field(min_length=1, max_length=32)
    types: list[LeaveTypeIn] = Field(max_length=20)

    @field_validator("types")
    @classmethod
    def unique_codes(cls, value):
        codes = [item.code for item in value]
        if len(set(codes)) != len(codes):
            raise ValueError("Leave codes must be unique.")
        return value


class LeaveCreate(Command):
    type_id: int = Field(gt=0)
    starts_on: date
    ends_on: date
    note: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def valid_range(self):
        if self.ends_on < self.starts_on:
            raise ValueError("Leave must end on or after the day it starts.")
        if (self.ends_on - self.starts_on).days >= 60:
            raise ValueError("A single leave request covers at most 60 days.")
        return self


class Decision(Command):
    override: bool = False
    note: str = Field(default="", max_length=500)


class RejectIn(Command):
    note: str = Field(min_length=1, max_length=500)


class AssignIn(Command):
    substitute_member_id: int = Field(gt=0)
    note: str = Field(default="", max_length=500)
