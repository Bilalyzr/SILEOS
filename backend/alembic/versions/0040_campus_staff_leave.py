"""Staff leave types, requests and timetable substitutions.

Revision ID: 0040
Revises: 0039
"""

from alembic import op
import sqlalchemy as sa


revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("campus_leave_types"):
        op.create_table(
            "campus_leave_types",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("academic_year", sa.String(32), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("annual_quota", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("institution_id", "academic_year", "code", name="uq_campus_leave_type"),
        )
        op.create_index("ix_campus_leave_types_institution_id", "campus_leave_types", ["institution_id"])

    if not inspector.has_table("campus_leave_requests"):
        op.create_table(
            "campus_leave_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("type_id", sa.Integer(), nullable=False),
            sa.Column("starts_on", sa.Date(), nullable=False),
            sa.Column("ends_on", sa.Date(), nullable=False),
            sa.Column("days", sa.Integer(), nullable=False),
            sa.Column("note", sa.String(500), nullable=False, server_default=""),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("decided_by", sa.Integer(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decision_note", sa.String(500), nullable=False, server_default=""),
            sa.Column("override", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["type_id"], ["campus_leave_types.id"]),
            sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_campus_leave_requests_member_id", "campus_leave_requests", ["member_id"])
        op.create_index("ix_campus_leave_requests_institution_status", "campus_leave_requests", ["institution_id", "status"])

    if not inspector.has_table("campus_substitutions"):
        op.create_table(
            "campus_substitutions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("leave_id", sa.Integer(), nullable=False),
            sa.Column("event_id", sa.Integer(), nullable=False),
            sa.Column("absent_member_id", sa.Integer(), nullable=False),
            sa.Column("substitute_member_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("assigned_by", sa.Integer(), nullable=True),
            sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.String(500), nullable=False, server_default=""),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["leave_id"], ["campus_leave_requests.id"]),
            sa.ForeignKeyConstraint(["event_id"], ["campus_events.id"]),
            sa.ForeignKeyConstraint(["absent_member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["substitute_member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("leave_id", "event_id", name="uq_campus_substitution"),
        )
        for column in ("institution_id", "leave_id", "event_id", "substitute_member_id", "status"):
            op.create_index(f"ix_campus_substitutions_{column}", "campus_substitutions", [column])


def downgrade():
    op.drop_table("campus_substitutions")
    op.drop_table("campus_leave_requests")
    op.drop_table("campus_leave_types")
