from datetime import date
from decimal import Decimal
from typing import Annotated
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")


TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class StopIn(Command):
    name: str = Field(min_length=1, max_length=120)
    pickup_time: str = Field(default="", max_length=5)
    drop_time: str = Field(default="", max_length=5)
    landmark: str = Field(default="", max_length=200)

    @field_validator("pickup_time", "drop_time")
    @classmethod
    def clock(cls, value):
        value = value.strip()
        if value and not TIME.match(value):
            raise ValueError("Times use the 24-hour HH:MM form.")
        return value


class RouteCreate(Command):
    name: str = Field(min_length=1, max_length=120)
    vehicle_number: str = Field(default="", max_length=40)
    driver_name: str = Field(default="", max_length=120)
    driver_phone: str = Field(default="", max_length=20)
    capacity: int = Field(default=40, ge=1, le=200)
    fee_amount: Annotated[Decimal, Field(ge=0, max_digits=13, decimal_places=2)] | None = None
    currency: str = Field(default="INR", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    stops: list[StopIn] = Field(default_factory=list, max_length=60)


class RouteUpdate(Command):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    vehicle_number: str | None = Field(default=None, max_length=40)
    driver_name: str | None = Field(default=None, max_length=120)
    driver_phone: str | None = Field(default=None, max_length=20)
    capacity: int | None = Field(default=None, ge=1, le=200)
    active: bool | None = None
    stops: list[StopIn] | None = Field(default=None, max_length=60)


class AssignmentCreate(Command):
    member_id: int = Field(gt=0)
    stop_id: int = Field(gt=0)


class BoardingEntry(Command):
    member_id: int = Field(gt=0)
    boarded: bool = False
    dropped: bool = False


class BoardingPut(Command):
    day: date
    entries: list[BoardingEntry] = Field(min_length=1, max_length=300)
