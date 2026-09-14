from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Channel = Literal["whatsapp", "email"]


class PolicyPut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    days_before: list[int] = Field(default_factory=lambda: [7, 1], max_length=5)
    overdue_every_days: int = Field(default=7, ge=1, le=30)
    overdue_max: int = Field(default=3, ge=0, le=12)
    send_hour: int = Field(default=9, ge=0, le=23)
    channels: list[Channel] = Field(default_factory=lambda: ["whatsapp", "email"], min_length=1)
    whatsapp_template: str = Field(default="", max_length=120)
    whatsapp_language: str = Field(default="en", max_length=20)

    @field_validator("days_before")
    @classmethod
    def distinct_days(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("days_before must not repeat a value.")
        if any(day < 0 or day > 60 for day in value):
            raise ValueError("days_before values must be between 0 and 60.")
        return sorted(value, reverse=True)

    @field_validator("channels")
    @classmethod
    def distinct_channels(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("channels must not repeat a value.")
        return value

    @field_validator("whatsapp_template")
    @classmethod
    def template_shape(cls, value):
        value = value.strip()
        if value and not value.replace("_", "a").isalnum():
            raise ValueError("Template names use letters, digits and underscores only.")
        return value
