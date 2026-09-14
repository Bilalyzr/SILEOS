"""Shared commercial catalog, contracts, invoices, and immutable revenue events."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


VERTICAL_CHECK = "business_vertical IN ('meiporul','seyappaduporul','utporul')"


class CommercialInvoiceCounter(Base):
    """Transaction-locked fiscal-year sequence for statutory invoice numbers."""

    __tablename__ = "commercial_invoice_counters"

    fiscal_year = Column(String(9), primary_key=True)
    next_number = Column(Integer, nullable=False, default=1)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("next_number > 0", name="ck_commercial_invoice_counter"),
    )


class CommercialOffer(Base):
    """Sellable definition shared by direct, recurring, and enterprise sales."""

    __tablename__ = "commercial_offers"

    id = Column(Integer, primary_key=True)
    sku = Column(String(80), nullable=False, unique=True, index=True)
    business_vertical = Column(String(30), nullable=False, index=True)
    revenue_stream = Column(String(60), nullable=False, index=True)
    name = Column(String(180), nullable=False)
    description = Column(Text, nullable=False, default="")
    billing_model = Column(String(24), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    unit_amount = Column(Numeric(13, 2), nullable=False)
    tax_code = Column(String(40), nullable=False, default="")
    entitlement_grants = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(VERTICAL_CHECK, name="ck_commercial_offer_vertical"),
        CheckConstraint(
            "billing_model IN ('one_time','subscription','usage','royalty','milestone')",
            name="ck_commercial_offer_billing_model",
        ),
        CheckConstraint("unit_amount >= 0", name="ck_commercial_offer_amount"),
        CheckConstraint("length(currency) = 3", name="ck_commercial_offer_currency"),
        Index(
            "ix_commercial_offer_catalog",
            "business_vertical",
            "revenue_stream",
            "is_active",
        ),
    )


class CommercialContract(Base):
    """A tenant's agreement for an offer, including future recurring billing."""

    __tablename__ = "commercial_contracts"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    offer_id = Column(
        Integer,
        ForeignKey("commercial_offers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, default="draft", index=True)
    quantity = Column(Numeric(13, 3), nullable=False, default=1)
    unit_amount = Column(Numeric(13, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    billing_interval = Column(String(20), nullable=True)
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=True)
    next_billing_on = Column(Date, nullable=True, index=True)
    external_reference = Column(String(120), nullable=False, default="")
    terms = Column(JSON, nullable=False, default=dict)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','paused','completed','cancelled')",
            name="ck_commercial_contract_status",
        ),
        CheckConstraint("quantity > 0", name="ck_commercial_contract_quantity"),
        CheckConstraint("unit_amount >= 0", name="ck_commercial_contract_amount"),
        CheckConstraint(
            "billing_interval IS NULL OR billing_interval IN ('monthly','quarterly','annual')",
            name="ck_commercial_contract_interval",
        ),
        CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on",
            name="ck_commercial_contract_dates",
        ),
        Index("ix_commercial_contract_tenant_status", "tenant_id", "status"),
    )


class CommercialInvoice(Base):
    __tablename__ = "commercial_invoices"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    contract_id = Column(
        Integer,
        ForeignKey("commercial_contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_number = Column(String(60), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    currency = Column(String(3), nullable=False, default="INR")
    subtotal = Column(Numeric(13, 2), nullable=False)
    tax_amount = Column(Numeric(13, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(13, 2), nullable=False, default=0)
    total_amount = Column(Numeric(13, 2), nullable=False)
    lines = Column(JSON, nullable=False, default=list)
    due_on = Column(Date, nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    gateway_order_id = Column(String(120), nullable=False, default="", index=True)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','issued','paid','overdue','void','refunded')",
            name="ck_commercial_invoice_status",
        ),
        CheckConstraint("subtotal >= 0", name="ck_commercial_invoice_subtotal"),
        CheckConstraint("tax_amount >= 0", name="ck_commercial_invoice_tax"),
        CheckConstraint("discount_amount >= 0", name="ck_commercial_invoice_discount"),
        CheckConstraint("total_amount >= 0", name="ck_commercial_invoice_total"),
        Index("ix_commercial_invoice_tenant_status", "tenant_id", "status", "due_on"),
    )


class RevenueLedgerEvent(Base):
    """Append-only reporting event; corrections are explicit reversal events."""

    __tablename__ = "revenue_ledger_events"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    business_vertical = Column(String(30), nullable=False, index=True)
    revenue_stream = Column(String(60), nullable=False, index=True)
    event_type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="posted", index=True)
    source_type = Column(String(60), nullable=False)
    source_id = Column(String(100), nullable=False)
    source_event_key = Column(String(180), nullable=False, unique=True)
    invoice_id = Column(
        Integer,
        ForeignKey("commercial_invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    currency = Column(String(3), nullable=False, default="INR")
    gross_amount = Column(Numeric(13, 2), nullable=False)
    tax_amount = Column(Numeric(13, 2), nullable=False, default=0)
    gateway_fee = Column(Numeric(13, 2), nullable=False, default=0)
    partner_share = Column(Numeric(13, 2), nullable=False, default=0)
    net_amount = Column(Numeric(13, 2), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    recorded_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reverses_event_id = Column(
        Integer,
        ForeignKey("revenue_ledger_events.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(VERTICAL_CHECK, name="ck_revenue_ledger_vertical"),
        CheckConstraint(
            "event_type IN ('capture','refund','adjustment')",
            name="ck_revenue_ledger_event_type",
        ),
        CheckConstraint(
            "status IN ('posted','void')", name="ck_revenue_ledger_status"
        ),
        CheckConstraint("gross_amount >= 0", name="ck_revenue_ledger_gross"),
        CheckConstraint("tax_amount >= 0", name="ck_revenue_ledger_tax"),
        CheckConstraint("gateway_fee >= 0", name="ck_revenue_ledger_gateway_fee"),
        CheckConstraint("partner_share >= 0", name="ck_revenue_ledger_partner_share"),
        CheckConstraint("net_amount >= 0", name="ck_revenue_ledger_net"),
        CheckConstraint(
            "(event_type = 'refund' AND reverses_event_id IS NOT NULL) "
            "OR event_type <> 'refund'",
            name="ck_revenue_ledger_refund_reversal",
        ),
        Index(
            "ix_revenue_ledger_reporting",
            "occurred_at",
            "business_vertical",
            "revenue_stream",
            "currency",
        ),
        Index("ix_revenue_ledger_tenant_reporting", "tenant_id", "occurred_at"),
    )
