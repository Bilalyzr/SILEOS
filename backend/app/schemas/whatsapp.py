"""Validation for account-wide WhatsApp self-service and admin campaigns."""

from typing import Literal

from pydantic import Field, HttpUrl, field_validator

from app.schemas.institution import Command


WHATSAPP_AUDIENCE_ROLES = (
    "student",
    "instructor",
    "admin",
    "superadmin",
    "spoc",
    "parent",
    "company",
    "company_manager",
)
WhatsAppAudienceRole = Literal[
    "student",
    "instructor",
    "admin",
    "superadmin",
    "spoc",
    "parent",
    "company",
    "company_manager",
]


class WhatsAppOptIn(Command):
    phone: str = Field(pattern=r"^\+[1-9][0-9]{7,14}$", max_length=16)


class WhatsAppCampaignCreate(Command):
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")
    template: str = Field(pattern=r"^[a-z0-9_]{1,120}$")
    language: str = Field(default="en", pattern=r"^[A-Za-z_-]{2,20}$")
    parameters: list[str] = Field(default_factory=list, max_length=10)
    roles: list[WhatsAppAudienceRole] = Field(
        min_length=1, max_length=len(WHATSAPP_AUDIENCE_ROLES)
    )
    header_image_url: HttpUrl | None = Field(default=None, max_length=500)

    @field_validator("parameters")
    @classmethod
    def bounded_parameters(cls, values):
        if any(not value.strip() or len(value) > 256 for value in values):
            raise ValueError("Template parameters must be 1 to 256 characters.")
        return [value.strip() for value in values]

    @field_validator("roles")
    @classmethod
    def unique_roles(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("Audience roles must be unique.")
        return sorted(values)

    @field_validator("header_image_url")
    @classmethod
    def https_header(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("WhatsApp header images must use HTTPS.")
        return value
