from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")


RoomType = Literal["single", "double", "triple", "dormitory"]


class RoomIn(Command):
    number: str = Field(min_length=1, max_length=20)
    floor: str = Field(default="", max_length=20)
    room_type: RoomType = "double"
    capacity: int = Field(default=2, ge=1, le=20)
    active: bool = True


class BlockCreate(Command):
    name: str = Field(min_length=1, max_length=120)
    warden_member_id: int | None = Field(default=None, gt=0)
    gender: Literal["any", "male", "female"] = "any"
    fee_amount: Annotated[Decimal, Field(ge=0, max_digits=13, decimal_places=2)] | None = None
    currency: str = Field(default="INR", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    rooms: list[RoomIn] = Field(default_factory=list, max_length=500)


class BlockUpdate(Command):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    warden_member_id: int | None = Field(default=None, gt=0)
    gender: Literal["any", "male", "female"] | None = None
    active: bool | None = None


class RoomsPut(Command):
    rooms: list[RoomIn] = Field(max_length=500)


class AllocationCreate(Command):
    member_id: int = Field(gt=0)


class PassCreate(Command):
    kind: Literal["outpass", "leave"] = "outpass"
    reason: str = Field(min_length=3, max_length=500)
    leaves_at: datetime
    returns_at: datetime

    @model_validator(mode="after")
    def valid(self):
        if self.leaves_at.tzinfo is None or self.returns_at.tzinfo is None:
            raise ValueError("Pass times must include a UTC offset.")
        if self.returns_at <= self.leaves_at:
            raise ValueError("The return time must be after the leaving time.")
        if (self.returns_at - self.leaves_at).days > 30:
            raise ValueError("A pass covers at most 30 days.")
        return self


class PassDecision(Command):
    note: str = Field(default="", max_length=500)


class VisitorCreate(Command):
    member_id: int = Field(gt=0)
    visitor_name: str = Field(min_length=1, max_length=120)
    relation: str = Field(default="", max_length=60)
    phone: str = Field(default="", max_length=20)
