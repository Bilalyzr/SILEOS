"""Tuition fee reminder policies and reminder ledger.

Revision ID: 0039
Revises: 0038
"""

from alembic import op
import sqlalchemy as sa


revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("tuition_reminder_policies"):
        op.create_table(
            "tuition_reminder_policies",
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("days_before", sa.JSON(), nullable=False),
            sa.Column("overdue_every_days", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("overdue_max", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("send_hour", sa.Integer(), nullable=False, server_default="9"),
            sa.Column("channels", sa.JSON(), nullable=False),
            sa.Column("whatsapp_template", sa.String(120), nullable=False, server_default=""),
            sa.Column("whatsapp_language", sa.String(20), nullable=False, server_default="en"),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("institution_id"),
        )

    if not inspector.has_table("tuition_reminders"):
        op.create_table(
            "tuition_reminders",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("assignment_id", sa.Integer(), nullable=False),
            sa.Column("installment_id", sa.Integer(), nullable=True),
            sa.Column("receipt_id", sa.Integer(), nullable=True),
            sa.Column("student_member_id", sa.Integer(), nullable=False),
            sa.Column("recipient_user_id", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("stage", sa.String(32), nullable=False),
            sa.Column("channel", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("skip_reason", sa.String(120), nullable=False, server_default=""),
            sa.Column("error", sa.String(250), nullable=False, server_default=""),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("amount", sa.Numeric(13, 2), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("due_on", sa.DateTime(timezone=False), nullable=True),
            sa.Column("dedupe_key", sa.String(120), nullable=False),
            sa.Column("whatsapp_message_id", sa.Integer(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["assignment_id"], ["tuition_fee_assignments.id"]),
            sa.ForeignKeyConstraint(["installment_id"], ["tuition_installments.id"]),
            sa.ForeignKeyConstraint(["receipt_id"], ["tuition_receipts.id"]),
            sa.ForeignKeyConstraint(["student_member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["whatsapp_message_id"], ["campus_whatsapp_messages.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("institution_id", "dedupe_key", name="uq_tuition_reminder_dedupe"),
        )
        op.create_index("ix_tuition_reminders_institution_id", "tuition_reminders", ["institution_id"])
        op.create_index("ix_tuition_reminders_assignment_id", "tuition_reminders", ["assignment_id"])
        op.create_index("ix_tuition_reminders_installment_id", "tuition_reminders", ["installment_id"])
        op.create_index("ix_tuition_reminders_student_member_id", "tuition_reminders", ["student_member_id"])
        op.create_index("ix_tuition_reminders_status_created", "tuition_reminders", ["status", "created_at"])


def downgrade():
    op.drop_table("tuition_reminders")
    op.drop_table("tuition_reminder_policies")
