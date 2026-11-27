"""Commands for pair coding rooms."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Command(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class RoomCreateIn(Command):
    language: Literal["python", "javascript", "typescript", "java", "cpp", "c"] | None = None


class RoomJoinIn(Command):
    code: str = Field(min_length=8, max_length=64)
