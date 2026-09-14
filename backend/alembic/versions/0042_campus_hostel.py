"""Campus hostel blocks, rooms, allocations, passes and visitors.

Revision ID: 0042
Revises: 0041
"""

from alembic import op
import sqlalchemy as sa


revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("campus_hostel_blocks"):
        op.create_table(
            "campus_hostel_blocks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("warden_member_id", sa.Integer(), nullable=True),
            sa.Column("gender", sa.String(10), nullable=False, server_default="any"),
            sa.Column("fee_amount", sa.Numeric(13, 2), nullable=True),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("fee_plan_id", sa.Integer(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["warden_member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["fee_plan_id"], ["tuition_fee_plans.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("institution_id", "name", name="uq_campus_hostel_block"),
        )
        op.create_index("ix_campus_hostel_blocks_institution_id", "campus_hostel_blocks", ["institution_id"])

    if not inspector.has_table("campus_hostel_rooms"):
        op.create_table(
            "campus_hostel_rooms",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("block_id", sa.Integer(), nullable=False),
            sa.Column("number", sa.String(20), nullable=False),
            sa.Column("floor", sa.String(20), nullable=False, server_default=""),
            sa.Column("room_type", sa.String(20), nullable=False, server_default="double"),
            sa.Column("capacity", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.ForeignKeyConstraint(["block_id"], ["campus_hostel_blocks.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("block_id", "number", name="uq_campus_hostel_room"),
        )
        op.create_index("ix_campus_hostel_rooms_block_id", "campus_hostel_rooms", ["block_id"])

    if not inspector.has_table("campus_hostel_allocations"):
        op.create_table(
            "campus_hostel_allocations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("room_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("fee_assignment_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("checked_in_on", sa.Date(), nullable=False),
            sa.Column("checked_out_on", sa.Date(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["room_id"], ["campus_hostel_rooms.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["fee_assignment_id"], ["tuition_fee_assignments.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_campus_hostel_allocations_institution_id", "campus_hostel_allocations", ["institution_id"])
        op.create_index("ix_campus_hostel_allocations_room_id", "campus_hostel_allocations", ["room_id"])
        op.create_index("ix_campus_hostel_allocations_member_status", "campus_hostel_allocations", ["member_id", "status"])

    if not inspector.has_table("campus_hostel_passes"):
        op.create_table(
            "campus_hostel_passes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False, server_default="outpass"),
            sa.Column("reason", sa.String(500), nullable=False, server_default=""),
            sa.Column("leaves_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("returns_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("decided_by", sa.Integer(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decision_note", sa.String(500), nullable=False, server_default=""),
            sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("institution_id", "member_id", "status"):
            op.create_index(f"ix_campus_hostel_passes_{column}", "campus_hostel_passes", [column])

    if not inspector.has_table("campus_hostel_visitors"):
        op.create_table(
            "campus_hostel_visitors",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("visitor_name", sa.String(120), nullable=False),
            sa.Column("relation", sa.String(60), nullable=False, server_default=""),
            sa.Column("phone", sa.String(20), nullable=False, server_default=""),
            sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("recorded_by", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["recorded_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("institution_id", "member_id", "checked_in_at"):
            op.create_index(f"ix_campus_hostel_visitors_{column}", "campus_hostel_visitors", [column])


def downgrade():
    op.drop_table("campus_hostel_visitors")
    op.drop_table("campus_hostel_passes")
    op.drop_table("campus_hostel_allocations")
    op.drop_table("campus_hostel_rooms")
    op.drop_table("campus_hostel_blocks")
