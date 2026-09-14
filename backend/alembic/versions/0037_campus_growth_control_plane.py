"""Campus growth, Today actions, identity and privacy control plane.

Revision ID: 0037
Revises: 0036
"""

from alembic import op
import sqlalchemy as sa


revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("campus_leads"):
        op.create_table(
            "campus_leads",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("dedupe_key", sa.String(64), nullable=False),
            sa.Column("contact_name", sa.String(120), nullable=False),
            sa.Column("work_email", sa.String(254), nullable=False),
            sa.Column("phone", sa.String(20), nullable=False, server_default=""),
            sa.Column("institution_name", sa.String(180), nullable=False),
            sa.Column("institution_kind", sa.String(20), nullable=False),
            sa.Column("learner_count", sa.String(24), nullable=False),
            sa.Column("interest", sa.String(30), nullable=False, server_default="demo"),
            sa.Column("message", sa.Text(), nullable=False, server_default=""),
            sa.Column("source", sa.String(80), nullable=False, server_default="campus-page"),
            sa.Column("attribution", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="new"),
            sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("assigned_to", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("dedupe_key", name="uq_campus_lead_dedupe"),
        )
        op.create_index("ix_campus_leads_work_email", "campus_leads", ["work_email"])
        op.create_index("ix_campus_leads_status", "campus_leads", ["status"])
        op.create_index("ix_campus_leads_created_at", "campus_leads", ["created_at"])

    if not inspector.has_table("campus_action_items"):
        op.create_table(
            "campus_action_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(30), nullable=False, server_default="task"),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("assigned_member_id", sa.Integer(), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("action_url", sa.String(500), nullable=False, server_default=""),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["assigned_member_id"], ["institution_members.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_campus_action_items_institution_id", "campus_action_items", ["institution_id"])
        op.create_index("ix_campus_action_items_status", "campus_action_items", ["status"])
        op.create_index("ix_campus_action_items_priority", "campus_action_items", ["priority"])
        op.create_index("ix_campus_action_items_assigned_member_id", "campus_action_items", ["assigned_member_id"])
        op.create_index("ix_campus_action_items_due_at", "campus_action_items", ["due_at"])
        op.create_index("ix_campus_action_items_created_at", "campus_action_items", ["created_at"])

    if not inspector.has_table("campus_domains"):
        op.create_table(
            "campus_domains",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("hostname", sa.String(253), nullable=False),
            sa.Column("verification_token", sa.String(80), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("hostname"),
            sa.UniqueConstraint("verification_token"),
        )
        op.create_index("ix_campus_domains_institution_id", "campus_domains", ["institution_id"])

    if not inspector.has_table("campus_integrations"):
        op.create_table(
            "campus_integrations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(40), nullable=False),
            sa.Column("display_name", sa.String(120), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("secret_reference", sa.String(180), nullable=False, server_default=""),
            sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.String(500), nullable=False, server_default=""),
            sa.Column("updated_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("institution_id", "kind", name="uq_campus_integration_kind"),
        )
        op.create_index("ix_campus_integrations_institution_id", "campus_integrations", ["institution_id"])

    if not inspector.has_table("campus_retention_policies"):
        op.create_table(
            "campus_retention_policies",
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("inactive_account_days", sa.Integer(), nullable=False, server_default="730"),
            sa.Column("learning_record_days", sa.Integer(), nullable=False, server_default="2555"),
            sa.Column("financial_record_days", sa.Integer(), nullable=False, server_default="2920"),
            sa.Column("application_record_days", sa.Integer(), nullable=False, server_default="730"),
            sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("updated_by", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("institution_id"),
        )

    if not inspector.has_table("campus_privacy_requests"):
        op.create_table(
            "campus_privacy_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("requester_user_id", sa.Integer(), nullable=False),
            sa.Column("subject_user_id", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(24), nullable=False),
            sa.Column("status", sa.String(24), nullable=False, server_default="submitted"),
            sa.Column("detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("resolution_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["subject_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_campus_privacy_requests_institution_id", "campus_privacy_requests", ["institution_id"])
        op.create_index("ix_campus_privacy_requests_requester_user_id", "campus_privacy_requests", ["requester_user_id"])
        op.create_index("ix_campus_privacy_requests_subject_user_id", "campus_privacy_requests", ["subject_user_id"])
        op.create_index("ix_campus_privacy_requests_status", "campus_privacy_requests", ["status"])

    if not inspector.has_table("campus_consent_receipts"):
        op.create_table(
            "campus_consent_receipts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("subject_user_id", sa.Integer(), nullable=False),
            sa.Column("recorded_by_user_id", sa.Integer(), nullable=False),
            sa.Column("purpose", sa.String(80), nullable=False),
            sa.Column("notice_version", sa.String(40), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["subject_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("institution_id", "subject_user_id", "purpose", name="uq_campus_consent_purpose"),
        )
        op.create_index("ix_campus_consent_receipts_institution_id", "campus_consent_receipts", ["institution_id"])
        op.create_index("ix_campus_consent_receipts_subject_user_id", "campus_consent_receipts", ["subject_user_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in (
        "campus_consent_receipts",
        "campus_privacy_requests",
        "campus_retention_policies",
        "campus_integrations",
        "campus_domains",
        "campus_action_items",
        "campus_leads",
    ):
        if inspector.has_table(table):
            op.drop_table(table)

