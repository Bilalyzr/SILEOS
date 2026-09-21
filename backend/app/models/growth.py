"""Revenue operations: billing schedules, delivery, attribution and experiments.

Commercial invoices and revenue_ledger_events remain the financial authorities.
These tables add workflow and provenance, never a second payment ledger.
"""
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric, JSON, Boolean, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class BillingPolicy(Base):
    __tablename__ = "growth_billing_policies"
    contract_id = Column(Integer, ForeignKey("commercial_contracts.id", ondelete="CASCADE"), primary_key=True)
    tax_profile = Column(JSON, nullable=False, default=dict)
    resource_type = Column(String(40), nullable=False, default="service")
    resource_reference = Column(String(180), nullable=False, default="")
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    partner_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    partner_bps = Column(Integer, nullable=False, default=0)
    payment_terms_days = Column(Integer, nullable=False, default=14)
    automation_enabled = Column(Boolean, nullable=False, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (CheckConstraint("partner_bps BETWEEN 0 AND 10000", name="ck_growth_partner_bps"),)


class BillingOccurrence(Base):
    __tablename__ = "growth_billing_occurrences"
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("commercial_contracts.id"), nullable=False, index=True)
    period_key = Column(String(100), nullable=False)
    invoice_id = Column(Integer, ForeignKey("commercial_invoices.id"), nullable=False, unique=True)
    snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("contract_id", "period_key", name="uq_growth_billing_period"),)


class CommercialDelivery(Base):
    __tablename__ = "growth_deliveries"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("commercial_invoices.id"), nullable=False, unique=True)
    tenant_id = Column(Integer, ForeignKey("platform_tenants.id"), nullable=False, index=True)
    resource_type = Column(String(40), nullable=False)
    resource_reference = Column(String(180), nullable=False, default="")
    recipient_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(24), nullable=False, default="pending")
    evidence = Column(String(1000), nullable=False, default="")
    valid_until = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("status IN ('pending','active','completed','revoked','expired')", name="ck_growth_delivery_status"),)


class PartnerAccrual(Base):
    __tablename__ = "growth_partner_accruals"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("revenue_ledger_events.id"), nullable=False, unique=True)
    partner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(13, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    available_on = Column(Date, nullable=False)
    settlement_id = Column(Integer, ForeignKey("growth_partner_settlements.id"), nullable=True, index=True)


class PartnerSettlement(Base):
    __tablename__ = "growth_partner_settlements"
    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(String(3), nullable=False)
    amount = Column(Numeric(13, 2), nullable=False)
    reference = Column(String(160), nullable=False, unique=True)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GrowthLead(Base):
    __tablename__ = "growth_leads"
    id = Column(Integer, primary_key=True)
    campus_lead_id = Column(Integer, ForeignKey("campus_leads.id"), unique=True)
    tenant_id = Column(Integer, ForeignKey("platform_tenants.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    business_vertical = Column(String(30), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(254), nullable=False)
    company = Column(String(180), nullable=False, default="")
    stage = Column(String(20), nullable=False, default="new", index=True)
    source = Column(String(80), nullable=False, default="direct")
    campaign = Column(String(100), nullable=False, default="")
    expected_amount = Column(Numeric(13, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="INR")
    owner_id = Column(Integer, ForeignKey("users.id"))
    signals = Column(JSON, nullable=False, default=dict)
    score = Column(Integer, nullable=False, default=0)
    consent_at = Column(DateTime(timezone=True), nullable=False)
    next_follow_up = Column(Date)
    contract_id = Column(Integer, ForeignKey("commercial_contracts.id"))
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    __table_args__ = (CheckConstraint("stage IN ('new','contacted','qualified','proposal','won','lost')", name="ck_growth_lead_stage"),)


class GrowthTask(Base):
    __tablename__ = "growth_tasks"
    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("growth_leads.id", ondelete="CASCADE"), nullable=False, index=True)
    dedupe_key = Column(String(120), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    due_on = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="open")


class MarketingSpend(Base):
    __tablename__ = "growth_marketing_spend"
    id = Column(Integer, primary_key=True)
    source_key = Column(String(120), nullable=False, unique=True)
    source = Column(String(80), nullable=False)
    campaign = Column(String(100), nullable=False, default="")
    business_vertical = Column(String(30), nullable=False)
    incurred_on = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(13, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_growth_spend_amount"),)


class GrowthTouch(Base):
    __tablename__ = "growth_touches"
    id = Column(Integer, primary_key=True)
    event_key = Column(String(100), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(24), nullable=False)
    source = Column(String(80), nullable=False, default="direct")
    medium = Column(String(80), nullable=False, default="")
    campaign = Column(String(100), nullable=False, default="")
    offer_id = Column(Integer, ForeignKey("commercial_offers.id"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class GrowthExperiment(Base):
    __tablename__ = "growth_experiments"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    kind = Column(String(24), nullable=False)
    offer_id = Column(Integer, ForeignKey("commercial_offers.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft")
    variants = Column(JSON, nullable=False)
    minimum_sample = Column(Integer, nullable=False, default=100)
    starts_at = Column(DateTime(timezone=True))
    ends_at = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (CheckConstraint("status IN ('draft','running','paused','completed')", name="ck_growth_experiment_status"),)


class GrowthAssignment(Base):
    __tablename__ = "growth_assignments"
    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("growth_experiments.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    variant = Column(String(20), nullable=False)
    exposed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("experiment_id", "user_id", name="uq_growth_experiment_subject"),)


class GrowthRecommendation(Base):
    __tablename__ = "growth_recommendations"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("platform_tenants.id"), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GrowthValidation(Base):
    __tablename__ = "growth_validations"
    id = Column(Integer, primary_key=True)
    area = Column(String(40), nullable=False)
    environment = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    evidence = Column(String(1500), nullable=False)
    release_ref = Column(String(80), nullable=False)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
