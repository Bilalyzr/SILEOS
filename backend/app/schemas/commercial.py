"""Validated commands for cross-vertical commercial operations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Command(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class EntitlementGrant(Command):
    vertical: Literal["meiporul", "seyappaduporul", "utporul"]
    feature_key: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_\-]+$")
    quota: dict = Field(default_factory=dict)


class OfferCreate(Command):
    sku: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9._\-]+$")
    business_vertical: Literal["meiporul", "seyappaduporul", "utporul"]
    revenue_stream: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=180)
    description: str = Field(default="", max_length=3000)
    billing_model: Literal["one_time", "subscription", "usage", "royalty", "milestone"]
    currency: str = Field(default="INR", min_length=3, max_length=3)
    unit_amount: Decimal = Field(ge=0, max_digits=13, decimal_places=2)
    tax_code: str = Field(default="", max_length=40)
    entitlement_grants: list[EntitlementGrant] = Field(default_factory=list, max_length=50)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value):
        if not value.isalpha():
            raise ValueError("currency must be a three-letter ISO code")
        return value.upper()


class ContractCreate(Command):
    tenant_id: int = Field(gt=0)
    offer_id: int = Field(gt=0)
    quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=13, decimal_places=3)
    unit_amount: Annotated[Decimal, Field(ge=0, max_digits=13, decimal_places=2)] | None = None
    billing_interval: Literal["monthly", "quarterly", "annual"] | None = None
    starts_on: date
    ends_on: date | None = None
    next_billing_on: date | None = None
    external_reference: str = Field(default="", max_length=120)
    terms: dict = Field(default_factory=dict)

    @field_validator("ends_on")
    @classmethod
    def valid_end(cls, value, info):
        start = info.data.get("starts_on")
        if value is not None and start is not None and value < start:
            raise ValueError("ends_on cannot be earlier than starts_on")
        return value


class InvoiceCreate(Command):
    contract_id: int = Field(gt=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=13, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=13, decimal_places=2)
    due_on: date
    note: str = Field(default="", max_length=500)


class PaymentRecord(Command):
    source_event_key: str = Field(min_length=8, max_length=180)
    payment_reference: str = Field(min_length=3, max_length=180)
    occurred_at: datetime
    gateway_fee: Decimal = Field(default=Decimal("0"), ge=0, max_digits=13, decimal_places=2)
    partner_share: Decimal = Field(default=Decimal("0"), ge=0, max_digits=13, decimal_places=2)
    metadata: dict = Field(default_factory=dict)
    reason: str = Field(min_length=3, max_length=500)


class RefundRecord(Command):
    source_event_key: str = Field(min_length=8, max_length=180)
    refund_reference: str = Field(min_length=3, max_length=180)
    amount: Decimal = Field(gt=0, max_digits=13, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=13, decimal_places=2)
    occurred_at: datetime
    metadata: dict = Field(default_factory=dict)
    reason: str = Field(min_length=3, max_length=500)
