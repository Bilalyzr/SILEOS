"""Campus onboarding, calendar, notices, goals, report cards and WhatsApp."""

from alembic import op
import sqlalchemy as sa


revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "campus_onboarding_states",
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("dismissed", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("institution_id"),
    )
    op.create_table(
        "campus_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("room", sa.String(80), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("series", sa.String(40), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["institution_batches.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["institution_members.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_campus_events_institution_id", "campus_events", ["institution_id"]
    )
    op.create_index("ix_campus_events_starts_at", "campus_events", ["starts_at"])
    op.create_index("ix_campus_events_series", "campus_events", ["series"])
    op.create_table(
        "campus_announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["institution_batches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_campus_announcements_institution_id",
        "campus_announcements",
        ["institution_id"],
    )
    op.create_table(
        "campus_notice_reads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["announcement_id"], ["campus_announcements.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "announcement_id", "member_id", name="uq_campus_notice_read"
        ),
    )
    op.create_table(
        "campus_goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campus_goals_member_id", "campus_goals", ["member_id"])
    op.create_table(
        "campus_grade_policies",
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("bands", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.PrimaryKeyConstraint("institution_id"),
    )
    op.create_table(
        "campus_report_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(2000), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
        sa.ForeignKeyConstraint(["term_id"], ["campus_terms.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("member_id", "term_id", name="uq_campus_report_comment"),
    )
    op.create_table(
        "campus_whatsapp_contacts",
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("challenge", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
        sa.PrimaryKeyConstraint("member_id"),
        sa.UniqueConstraint("challenge"),
    )
    op.create_table(
        "campus_whatsapp_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("request_key", sa.String(64), nullable=False),
        sa.Column("template", sa.String(120), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("header_image_url", sa.String(500), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["institution_batches.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id", "request_key", name="uq_campus_wa_campaign"
        ),
    )
    op.create_index(
        "ix_campus_whatsapp_campaigns_institution_id",
        "campus_whatsapp_campaigns",
        ["institution_id"],
    )
    op.create_table(
        "campus_whatsapp_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider_id", sa.String(250), nullable=True),
        sa.Column("error", sa.String(200), nullable=False),
        sa.Column("callback_key", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("last_event_at", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["campus_whatsapp_campaigns.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id"),
        sa.UniqueConstraint("callback_key"),
        sa.UniqueConstraint("campaign_id", "member_id", name="uq_campus_wa_message"),
    )
    op.create_index(
        "ix_campus_whatsapp_messages_campaign_id",
        "campus_whatsapp_messages",
        ["campaign_id"],
    )
    op.create_table(
        "campus_whatsapp_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(250), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )


def downgrade():
    op.drop_table("campus_whatsapp_webhook_events")
    op.drop_index(
        "ix_campus_whatsapp_messages_campaign_id", table_name="campus_whatsapp_messages"
    )
    op.drop_table("campus_whatsapp_messages")
    op.drop_index(
        "ix_campus_whatsapp_campaigns_institution_id",
        table_name="campus_whatsapp_campaigns",
    )
    op.drop_table("campus_whatsapp_campaigns")
    op.drop_table("campus_whatsapp_contacts")
    op.drop_table("campus_report_comments")
    op.drop_table("campus_grade_policies")
    op.drop_index("ix_campus_goals_member_id", table_name="campus_goals")
    op.drop_table("campus_goals")
    op.drop_table("campus_notice_reads")
    op.drop_index(
        "ix_campus_announcements_institution_id", table_name="campus_announcements"
    )
    op.drop_table("campus_announcements")
    op.drop_index("ix_campus_events_series", table_name="campus_events")
    op.drop_index("ix_campus_events_starts_at", table_name="campus_events")
    op.drop_index("ix_campus_events_institution_id", table_name="campus_events")
    op.drop_table("campus_events")
    op.drop_table("campus_onboarding_states")
