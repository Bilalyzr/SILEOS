"""Meiporul field operations.

Revision ID: 0047
Revises: 0046
"""

from alembic import op
import sqlalchemy as sa

from app.core.migration_operations import idempotent_create_operations


revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None
op = idempotent_create_operations(op)


def upgrade():
    op.create_table(
        "immersive_lab_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("address", sa.JSON(), nullable=False),
        sa.Column("room_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("headset_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("network_readiness", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("safety_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("go_live_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('planned','installing','active','paused','retired')", name="ck_immersive_site_status"),
        sa.CheckConstraint("network_readiness IN ('unknown','failed','conditional','ready')", name="ck_immersive_site_network"),
        sa.CheckConstraint("safety_status IN ('pending','failed','conditional','passed')", name="ck_immersive_site_safety"),
        sa.CheckConstraint("room_count > 0", name="ck_immersive_site_rooms"),
        sa.CheckConstraint("headset_capacity >= 0", name="ck_immersive_site_capacity"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contract_id"], ["commercial_contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_immersive_site_tenant_code"),
    )
    for name, columns in (
        ("ix_immersive_lab_sites_tenant_id", ["tenant_id"]),
        ("ix_immersive_lab_sites_institution_id", ["institution_id"]),
        ("ix_immersive_lab_sites_status", ["status"]),
        ("ix_immersive_site_tenant_status", ["tenant_id", "status"]),
    ): op.create_index(name, "immersive_lab_sites", columns)

    op.create_table(
        "immersive_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("asset_tag", sa.String(80), nullable=False),
        sa.Column("serial_number", sa.String(160), nullable=False, server_default=""),
        sa.Column("device_type", sa.String(24), nullable=False),
        sa.Column("vendor", sa.String(100), nullable=False, server_default=""),
        sa.Column("model", sa.String(100), nullable=False, server_default=""),
        sa.Column("os_version", sa.String(80), nullable=False, server_default=""),
        sa.Column("firmware_version", sa.String(80), nullable=False, server_default=""),
        sa.Column("status", sa.String(24), nullable=False, server_default="inventory"),
        sa.Column("assigned_room", sa.String(80), nullable=False, server_default=""),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("commissioned_on", sa.Date(), nullable=True),
        sa.Column("warranty_through", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("device_type IN ('headset','controller','workstation','router','haptic','other')", name="ck_immersive_device_type"),
        sa.CheckConstraint("status IN ('inventory','provisioning','ready','deployed','maintenance','quarantined','retired')", name="ck_immersive_device_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["site_id"], ["immersive_lab_sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "asset_tag", name="uq_immersive_device_asset_tag"),
    )
    for name, columns in (
        ("ix_immersive_devices_tenant_id", ["tenant_id"]),
        ("ix_immersive_devices_site_id", ["site_id"]),
        ("ix_immersive_devices_status", ["status"]),
        ("ix_immersive_device_site_status", ["site_id", "status"]),
    ): op.create_index(name, "immersive_devices", columns)

    op.create_table(
        "immersive_safety_inspections",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False), sa.Column("inspection_type", sa.String(24), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checklist", sa.JSON(), nullable=False), sa.Column("findings", sa.Text(), nullable=False, server_default=""),
        sa.Column("corrective_actions", sa.Text(), nullable=False, server_default=""), sa.Column("next_due_on", sa.Date(), nullable=True),
        sa.Column("inspector_id", sa.Integer(), nullable=True), sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("inspection_type IN ('pre_install','routine','incident','post_repair')", name="ck_immersive_inspection_type"),
        sa.CheckConstraint("status IN ('scheduled','passed','failed','conditional')", name="ck_immersive_inspection_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["site_id"], ["immersive_lab_sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inspector_id"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (("ix_immersive_safety_inspections_tenant_id", ["tenant_id"]), ("ix_immersive_safety_inspections_site_id", ["site_id"]), ("ix_immersive_safety_inspections_status", ["status"]), ("ix_immersive_inspection_site_schedule", ["site_id", "scheduled_for"])): op.create_index(name, "immersive_safety_inspections", columns)

    op.create_table(
        "immersive_deployment_milestones",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("tenant_id", sa.Integer(), nullable=False), sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("title", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="not_started"), sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("evidence_urls", sa.JSON(), nullable=False), sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("sequence > 0", name="ck_immersive_milestone_sequence"),
        sa.CheckConstraint("status IN ('not_started','in_progress','blocked','completed','skipped')", name="ck_immersive_milestone_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["site_id"], ["immersive_lab_sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("site_id", "sequence", name="uq_immersive_milestone_sequence"),
    )
    for name, columns in (("ix_immersive_deployment_milestones_tenant_id", ["tenant_id"]), ("ix_immersive_deployment_milestones_site_id", ["site_id"]), ("ix_immersive_deployment_milestones_status", ["status"]), ("ix_immersive_milestone_site_status", ["site_id", "status"])): op.create_index(name, "immersive_deployment_milestones", columns)

    op.create_table(
        "immersive_service_tickets",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("tenant_id", sa.Integer(), nullable=False), sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True), sa.Column("contract_id", sa.Integer(), nullable=True),
        sa.Column("reference", sa.String(40), nullable=False), sa.Column("category", sa.String(24), nullable=False),
        sa.Column("priority", sa.String(12), nullable=False, server_default="normal"), sa.Column("status", sa.String(24), nullable=False, server_default="open"),
        sa.Column("subject", sa.String(200), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True), sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True), sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("category IN ('hardware','software','network','content','safety','training','other')", name="ck_immersive_ticket_category"),
        sa.CheckConstraint("priority IN ('low','normal','high','critical')", name="ck_immersive_ticket_priority"),
        sa.CheckConstraint("status IN ('open','triaged','in_progress','waiting_customer','resolved','closed')", name="ck_immersive_ticket_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["site_id"], ["immersive_lab_sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["immersive_devices.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["contract_id"], ["commercial_contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("reference"),
    )
    for name, columns in (("ix_immersive_service_tickets_tenant_id", ["tenant_id"]), ("ix_immersive_service_tickets_site_id", ["site_id"]), ("ix_immersive_service_tickets_device_id", ["device_id"]), ("ix_immersive_service_tickets_reference", ["reference"]), ("ix_immersive_service_tickets_priority", ["priority"]), ("ix_immersive_service_tickets_status", ["status"]), ("ix_immersive_ticket_tenant_status", ["tenant_id", "status"]), ("ix_immersive_ticket_sla", ["status", "sla_due_at"])): op.create_index(name, "immersive_service_tickets", columns)


def downgrade():
    bind = op.get_bind()
    for table_name in ("immersive_service_tickets", "immersive_deployment_milestones", "immersive_safety_inspections", "immersive_devices", "immersive_lab_sites"):
        if sa.inspect(bind).has_table(table_name): op.drop_table(table_name)
