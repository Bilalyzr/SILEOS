"""Cross-vertical offers, contracts, invoices, and revenue ledger.

Revision ID: 0045
Revises: 0044
"""

from alembic import op
import sqlalchemy as sa


revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("commercial_invoice_counters"):
        op.create_table(
            "commercial_invoice_counters",
            sa.Column("fiscal_year", sa.String(9), nullable=False),
            sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("next_number > 0", name="ck_commercial_invoice_counter"),
            sa.PrimaryKeyConstraint("fiscal_year"),
        )

    if not inspector.has_table("commercial_offers"):
        op.create_table(
            "commercial_offers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("sku", sa.String(80), nullable=False),
            sa.Column("business_vertical", sa.String(30), nullable=False),
            sa.Column("revenue_stream", sa.String(60), nullable=False),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("billing_model", sa.String(24), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("unit_amount", sa.Numeric(13, 2), nullable=False),
            sa.Column("tax_code", sa.String(40), nullable=False, server_default=""),
            sa.Column("entitlement_grants", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "business_vertical IN ('meiporul','seyappaduporul','utporul')",
                name="ck_commercial_offer_vertical",
            ),
            sa.CheckConstraint(
                "billing_model IN ('one_time','subscription','usage','royalty','milestone')",
                name="ck_commercial_offer_billing_model",
            ),
            sa.CheckConstraint("unit_amount >= 0", name="ck_commercial_offer_amount"),
            sa.CheckConstraint("length(currency) = 3", name="ck_commercial_offer_currency"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("sku"),
        )
        op.create_index("ix_commercial_offers_sku", "commercial_offers", ["sku"], unique=True)
        op.create_index("ix_commercial_offers_business_vertical", "commercial_offers", ["business_vertical"])
        op.create_index("ix_commercial_offers_revenue_stream", "commercial_offers", ["revenue_stream"])
        op.create_index("ix_commercial_offers_is_active", "commercial_offers", ["is_active"])
        op.create_index("ix_commercial_offer_catalog", "commercial_offers", ["business_vertical", "revenue_stream", "is_active"])

    if not inspector.has_table("commercial_contracts"):
        op.create_table(
            "commercial_contracts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("offer_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("quantity", sa.Numeric(13, 3), nullable=False, server_default="1"),
            sa.Column("unit_amount", sa.Numeric(13, 2), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("billing_interval", sa.String(20), nullable=True),
            sa.Column("starts_on", sa.Date(), nullable=False),
            sa.Column("ends_on", sa.Date(), nullable=True),
            sa.Column("next_billing_on", sa.Date(), nullable=True),
            sa.Column("external_reference", sa.String(120), nullable=False, server_default=""),
            sa.Column("terms", sa.JSON(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "status IN ('draft','active','paused','completed','cancelled')",
                name="ck_commercial_contract_status",
            ),
            sa.CheckConstraint("quantity > 0", name="ck_commercial_contract_quantity"),
            sa.CheckConstraint("unit_amount >= 0", name="ck_commercial_contract_amount"),
            sa.CheckConstraint(
                "billing_interval IS NULL OR billing_interval IN ('monthly','quarterly','annual')",
                name="ck_commercial_contract_interval",
            ),
            sa.CheckConstraint("ends_on IS NULL OR ends_on >= starts_on", name="ck_commercial_contract_dates"),
            sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["offer_id"], ["commercial_offers.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_commercial_contracts_tenant_id", "commercial_contracts", ["tenant_id"])
        op.create_index("ix_commercial_contracts_offer_id", "commercial_contracts", ["offer_id"])
        op.create_index("ix_commercial_contracts_status", "commercial_contracts", ["status"])
        op.create_index("ix_commercial_contracts_next_billing_on", "commercial_contracts", ["next_billing_on"])
        op.create_index("ix_commercial_contract_tenant_status", "commercial_contracts", ["tenant_id", "status"])

    if not inspector.has_table("commercial_invoices"):
        op.create_table(
            "commercial_invoices",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("contract_id", sa.Integer(), nullable=True),
            sa.Column("invoice_number", sa.String(60), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("subtotal", sa.Numeric(13, 2), nullable=False),
            sa.Column("tax_amount", sa.Numeric(13, 2), nullable=False, server_default="0"),
            sa.Column("discount_amount", sa.Numeric(13, 2), nullable=False, server_default="0"),
            sa.Column("total_amount", sa.Numeric(13, 2), nullable=False),
            sa.Column("lines", sa.JSON(), nullable=False),
            sa.Column("due_on", sa.Date(), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("gateway_order_id", sa.String(120), nullable=False, server_default=""),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "status IN ('draft','issued','paid','overdue','void','refunded')",
                name="ck_commercial_invoice_status",
            ),
            sa.CheckConstraint("subtotal >= 0", name="ck_commercial_invoice_subtotal"),
            sa.CheckConstraint("tax_amount >= 0", name="ck_commercial_invoice_tax"),
            sa.CheckConstraint("discount_amount >= 0", name="ck_commercial_invoice_discount"),
            sa.CheckConstraint("total_amount >= 0", name="ck_commercial_invoice_total"),
            sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["contract_id"], ["commercial_contracts.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("invoice_number"),
        )
        op.create_index("ix_commercial_invoices_tenant_id", "commercial_invoices", ["tenant_id"])
        op.create_index("ix_commercial_invoices_contract_id", "commercial_invoices", ["contract_id"])
        op.create_index("ix_commercial_invoices_status", "commercial_invoices", ["status"])
        op.create_index("ix_commercial_invoices_due_on", "commercial_invoices", ["due_on"])
        op.create_index("ix_commercial_invoices_gateway_order_id", "commercial_invoices", ["gateway_order_id"])
        op.create_index("ix_commercial_invoice_tenant_status", "commercial_invoices", ["tenant_id", "status", "due_on"])

    if not inspector.has_table("revenue_ledger_events"):
        op.create_table(
            "revenue_ledger_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("business_vertical", sa.String(30), nullable=False),
            sa.Column("revenue_stream", sa.String(60), nullable=False),
            sa.Column("event_type", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="posted"),
            sa.Column("source_type", sa.String(60), nullable=False),
            sa.Column("source_id", sa.String(100), nullable=False),
            sa.Column("source_event_key", sa.String(180), nullable=False),
            sa.Column("invoice_id", sa.Integer(), nullable=True),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("gross_amount", sa.Numeric(13, 2), nullable=False),
            sa.Column("tax_amount", sa.Numeric(13, 2), nullable=False, server_default="0"),
            sa.Column("gateway_fee", sa.Numeric(13, 2), nullable=False, server_default="0"),
            sa.Column("partner_share", sa.Numeric(13, 2), nullable=False, server_default="0"),
            sa.Column("net_amount", sa.Numeric(13, 2), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("recorded_by", sa.Integer(), nullable=True),
            sa.Column("reverses_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "business_vertical IN ('meiporul','seyappaduporul','utporul')",
                name="ck_revenue_ledger_vertical",
            ),
            sa.CheckConstraint(
                "event_type IN ('capture','refund','adjustment')",
                name="ck_revenue_ledger_event_type",
            ),
            sa.CheckConstraint("status IN ('posted','void')", name="ck_revenue_ledger_status"),
            sa.CheckConstraint("gross_amount >= 0", name="ck_revenue_ledger_gross"),
            sa.CheckConstraint("tax_amount >= 0", name="ck_revenue_ledger_tax"),
            sa.CheckConstraint("gateway_fee >= 0", name="ck_revenue_ledger_gateway_fee"),
            sa.CheckConstraint("partner_share >= 0", name="ck_revenue_ledger_partner_share"),
            sa.CheckConstraint("net_amount >= 0", name="ck_revenue_ledger_net"),
            sa.CheckConstraint(
                "(event_type = 'refund' AND reverses_event_id IS NOT NULL) OR event_type <> 'refund'",
                name="ck_revenue_ledger_refund_reversal",
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["invoice_id"], ["commercial_invoices.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["reverses_event_id"], ["revenue_ledger_events.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source_event_key"),
        )
        op.create_index("ix_revenue_ledger_events_tenant_id", "revenue_ledger_events", ["tenant_id"])
        op.create_index("ix_revenue_ledger_events_business_vertical", "revenue_ledger_events", ["business_vertical"])
        op.create_index("ix_revenue_ledger_events_revenue_stream", "revenue_ledger_events", ["revenue_stream"])
        op.create_index("ix_revenue_ledger_events_event_type", "revenue_ledger_events", ["event_type"])
        op.create_index("ix_revenue_ledger_events_status", "revenue_ledger_events", ["status"])
        op.create_index("ix_revenue_ledger_events_invoice_id", "revenue_ledger_events", ["invoice_id"])
        op.create_index("ix_revenue_ledger_events_occurred_at", "revenue_ledger_events", ["occurred_at"])
        op.create_index("ix_revenue_ledger_reporting", "revenue_ledger_events", ["occurred_at", "business_vertical", "revenue_stream", "currency"])
        op.create_index("ix_revenue_ledger_tenant_reporting", "revenue_ledger_events", ["tenant_id", "occurred_at"])


def downgrade():
    bind = op.get_bind()
    for table_name in (
        "revenue_ledger_events",
        "commercial_invoices",
        "commercial_contracts",
        "commercial_offers",
        "commercial_invoice_counters",
    ):
        if sa.inspect(bind).has_table(table_name):
            op.drop_table(table_name)
