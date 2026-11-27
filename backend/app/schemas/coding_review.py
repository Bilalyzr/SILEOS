"""Commands for line-anchored review comments on coding submissions."""

from pydantic import BaseModel, ConfigDict, Field


class Command(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ReviewCommentIn(Command):
    line: int = Field(ge=1, le=20_000)
    body: str = Field(min_length=1, max_length=2000)
