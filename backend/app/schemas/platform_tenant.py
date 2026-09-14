"""Validated commands for the SashaInfinity tenant control plane."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Command(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class TenantStatusUpdate(Command):
    status: Literal["trial", "active", "suspended", "archived"]
    reason: str = Field(min_length=3, max_length=500)


class EntitlementUpdate(Command):
    enabled: bool
    quota: dict = Field(default_factory=dict)
    effective_from: datetime | None = None
    effective_through: datetime | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("effective_through")
    @classmethod
    def valid_window(cls, value, info):
        start = info.data.get("effective_from")
        if value is not None and start is not None and value <= start:
            raise ValueError("effective_through must be later than effective_from")
        return value


class TenantDomainCreate(Command):
    hostname: str = Field(min_length=4, max_length=253)
    vertical: Literal["meiporul", "seyappaduporul", "utporul"] | None = None
    is_primary: bool = False
