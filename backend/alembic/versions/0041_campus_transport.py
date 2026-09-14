"""Campus transport routes, stops, assignments and boarding logs.

Revision ID: 0041
Revises: 0040
"""

from alembic import op
import sqlalchemy as sa


revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("campus_transport_routes"):
        op.create_table(
            "campus_transport_routes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("vehicle_number", sa.String(40), nullable=False, server_default=""),
            sa.Column("driver_name", sa.String(120), nullable=False, server_default=""),
            sa.Column("driver_phone", sa.String(20), nullable=False, server_default=""),
            sa.Column("capacity", sa.Integer(), nullable=False, server_default="40"),
            sa.Column("fee_amount", sa.Numeric(13, 2), nullable=True),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("fee_plan_id", sa.Integer(), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["fee_plan_id"], ["tuition_fee_plans.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("institution_id", "name", name="uq_campus_transport_route"),
        )
        op.create_index("ix_campus_transport_routes_institution_id", "campus_transport_routes", ["institution_id"])

    if not inspector.has_table("campus_transport_stops"):
        op.create_table(
            "campus_transport_stops",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("route_id", sa.Integer(), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("pickup_time", sa.String(5), nullable=False, server_default=""),
            sa.Column("drop_time", sa.String(5), nullable=False, server_default=""),
            sa.Column("landmark", sa.String(200), nullable=False, server_default=""),
            sa.ForeignKeyConstraint(["route_id"], ["campus_transport_routes.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("route_id", "sequence", name="uq_campus_transport_stop"),
        )
        op.create_index("ix_campus_transport_stops_route_id", "campus_transport_stops", ["route_id"])

    if not inspector.has_table("campus_transport_assignments"):
        op.create_table(
            "campus_transport_assignments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("route_id", sa.Integer(), nullable=False),
            sa.Column("stop_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("fee_assignment_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("started_on", sa.Date(), nullable=False),
            sa.Column("ended_on", sa.Date(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["route_id"], ["campus_transport_routes.id"]),
            sa.ForeignKeyConstraint(["stop_id"], ["campus_transport_stops.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["fee_assignment_id"], ["tuition_fee_assignments.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_campus_transport_assignments_institution_id", "campus_transport_assignments", ["institution_id"])
        op.create_index("ix_campus_transport_assignments_route_id", "campus_transport_assignments", ["route_id"])
        op.create_index("ix_campus_transport_assignments_member_status", "campus_transport_assignments", ["member_id", "status"])

    if not inspector.has_table("campus_transport_logs"):
        op.create_table(
            "campus_transport_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("route_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("day", sa.Date(), nullable=False),
            sa.Column("boarded", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("dropped", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("recorded_by", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["route_id"], ["campus_transport_routes.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["recorded_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("route_id", "member_id", "day", name="uq_campus_transport_log"),
        )
        op.create_index("ix_campus_transport_logs_route_id", "campus_transport_logs", ["route_id"])
        op.create_index("ix_campus_transport_logs_day", "campus_transport_logs", ["day"])


def downgrade():
    op.drop_table("campus_transport_logs")
    op.drop_table("campus_transport_assignments")
    op.drop_table("campus_transport_stops")
    op.drop_table("campus_transport_routes")
