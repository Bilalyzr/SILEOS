"""Commands for pushing Utporul coding challenges into live class sessions."""

from pydantic import BaseModel, ConfigDict, Field


class Command(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class LivePushIn(Command):
    challenge_id: int = Field(gt=0)
    graded: bool = False
    instructions: str = Field(default="", max_length=2000)
    model_solution: str = Field(default="", max_length=65536)
