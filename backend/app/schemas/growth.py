"""Bounded, explicit commands for revenue operations."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, EmailStr, model_validator

Vertical = Literal["meiporul", "seyappaduporul", "utporul"]


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class TaxProfile(Command):
    supplier_name: str = Field(min_length=2, max_length=160)
    supplier_address: str = Field(min_length=5, max_length=500)
    supplier_gstin: str = Field(default="", max_length=15, pattern=r"^$|^[0-9]{2}[A-Z0-9]{13}$")
    supplier_state: str = Field(pattern=r"^[0-9]{2}$")
    customer_name: str = Field(min_length=2, max_length=160)
    customer_address: str = Field(min_length=5, max_length=500)
    customer_gstin: str = Field(default="", max_length=15, pattern=r"^$|^[0-9]{2}[A-Z0-9]{13}$")
    place_of_supply: str = Field(pattern=r"^[0-9]{2}$")
    hsn_sac: str = Field(min_length=4, max_length=8, pattern=r"^[0-9]+$")
    rate_bps: int = Field(ge=0, le=10000)
    exemption_reason: str = Field(default="", max_length=300)
    reviewed_by: str = Field(min_length=3, max_length=160)
    reverse_charge: bool = False

    @model_validator(mode="after")
    def classification(self):
        if self.rate_bps and not self.supplier_gstin:
            raise ValueError("A taxable profile needs the supplier GSTIN")
        if not self.rate_bps and not self.exemption_reason:
            raise ValueError("Record the basis for zero-rated or exempt treatment")
        if self.supplier_gstin and not self.supplier_gstin.startswith(self.supplier_state):
            raise ValueError("Supplier state and GSTIN prefix must match")
        return self


class PolicyCommand(Command):
    tax_profile: TaxProfile
    resource_type: Literal["asset_license", "lab_deployment", "amc", "device_service", "institution_saas", "franchise", "managed_service", "premium_credential", "career_service", "creator_commerce"]
    resource_reference: str = Field(min_length=1, max_length=180)
    recipient_id: int | None = Field(default=None, gt=0)
    partner_id: int | None = Field(default=None, gt=0)
    partner_bps: int = Field(default=0, ge=0, le=10000)
    payment_terms_days: int = Field(default=14, ge=0, le=90)
    automation_enabled: bool = False

    @model_validator(mode="after")
    def partner(self):
        if self.partner_bps and not self.partner_id:
            raise ValueError("Select the revenue-share recipient")
        return self


class IssueCommand(Command):
    period_key: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.:-]+$")
    milestone_bps: int = Field(default=10000, gt=0, le=10000)


class DeliveryCommand(Command):
    evidence: str = Field(min_length=5, max_length=1000)


class CancellationCommand(Command):
    reason: str = Field(min_length=5, max_length=500)


class SettlementCommand(Command):
    partner_id: int = Field(gt=0)
    currency: Literal["INR"] = "INR"
    reference: str = Field(min_length=8, max_length=160)
    expected_amount: Decimal = Field(gt=0, max_digits=13, decimal_places=2)


class LeadCreate(Command):
    business_vertical: Vertical
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    company: str = Field(default="", max_length=180)
    source: str = Field(default="direct", min_length=1, max_length=80)
    campaign: str = Field(default="", max_length=100)
    consent: Literal[True]
    expected_amount: Decimal = Field(default=0, ge=0, max_digits=13, decimal_places=2)
    tenant_id: int | None = Field(default=None, gt=0)


class LeadUpdate(Command):
    version: int = Field(gt=0)
    stage: Literal["new", "contacted", "qualified", "proposal", "won", "lost"]
    owner_id: int | None = Field(default=None, gt=0)
    next_follow_up: date | None = None
    budget_confirmed: bool = False
    decision_maker: bool = False
    demo_attended: bool = False
    contract_id: int | None = Field(default=None, gt=0)


class LeadWorkspace(Command):
    tenant_id: int = Field(gt=0)
    version: int = Field(gt=0)


class SpendCommand(Command):
    source_key: str = Field(min_length=8, max_length=120)
    source: str = Field(min_length=1, max_length=80)
    campaign: str = Field(default="", max_length=100)
    business_vertical: Vertical
    incurred_on: date
    amount: Decimal = Field(ge=0, max_digits=13, decimal_places=2)
    currency: Literal["INR"] = "INR"


class TouchCommand(Command):
    event_key: str = Field(min_length=8, max_length=100)
    kind: Literal["offer_view", "checkout_start", "campaign_click"]
    source: str = Field(default="direct", min_length=1, max_length=80)
    medium: str = Field(default="", max_length=80)
    campaign: str = Field(default="", max_length=100)
    offer_id: int | None = Field(default=None, gt=0)
    consent: Literal[True]


class Variant(Command):
    key: Literal["control", "variant"]
    headline: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=2, max_length=400)
    discount_bps: int = Field(default=0, ge=0, le=2000)


class ExperimentCommand(Command):
    name: str = Field(min_length=3, max_length=160)
    kind: Literal["pricing", "landing", "campaign"]
    offer_id: int = Field(gt=0)
    variants: list[Variant] = Field(min_length=2, max_length=2)
    minimum_sample: int = Field(default=100, ge=30, le=100000)

    @model_validator(mode="after")
    def variants_valid(self):
        if {v.key for v in self.variants} != {"control", "variant"}:
            raise ValueError("One control and one variant are required")
        if self.kind != "pricing" and any(v.discount_bps for v in self.variants):
            raise ValueError("Only pricing experiments may change price")
        if next(v for v in self.variants if v.key == "control").discount_bps:
            raise ValueError("The control must retain the catalog price")
        return self


class StatusCommand(Command):
    status: Literal["running", "paused", "completed"]


class AcceptOffer(Command):
    tenant_id: int = Field(gt=0)
    billing_interval: Literal["monthly", "quarterly", "annual"] | None = None


class VerifyCommand(Command):
    razorpay_order_id: str = Field(min_length=8, max_length=120)
    razorpay_payment_id: str = Field(min_length=8, max_length=120)
    razorpay_signature: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]+$")


class ValidationCommand(Command):
    area: Literal["payments", "ai", "tax", "postgres_restore", "worker_failover", "load", "mail", "whatsapp", "video", "coding"]
    environment: Literal["local", "sandbox", "staging", "production"]
    status: Literal["passed", "failed", "blocked"]
    evidence: str = Field(min_length=10, max_length=1500)
    release_ref: str = Field(min_length=7, max_length=80)
