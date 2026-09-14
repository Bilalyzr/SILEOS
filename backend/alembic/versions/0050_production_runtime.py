"""Persistent runtime schedules and execution history.

Revision ID: 0050
Revises: 0049
"""
from alembic import op
import sqlalchemy as sa

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade():
    # Frozen schema: future model changes must not rewrite this migration.
    if not sa.inspect(op.get_bind()).has_table("runtime_jobs"):
        op.create_table("runtime_jobs",
            sa.Column("name", sa.String(64), primary_key=True),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("lease_token", sa.String(36)),
            sa.Column("lease_until", sa.DateTime(timezone=True)),
            sa.Column("last_finished_at", sa.DateTime(timezone=True)),
            sa.Column("last_error", sa.String(120)),
            sa.CheckConstraint("status IN ('ready','running','retry','dead')", name="ck_runtime_job_status"))
    if not sa.inspect(op.get_bind()).has_table("runtime_runs"):
        op.create_table("runtime_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("job_name", sa.String(64), sa.ForeignKey("runtime_jobs.name"), nullable=False),
            sa.Column("worker_id", sa.String(80), nullable=False),
            sa.Column("status", sa.String(24), nullable=False),
            sa.Column("attempt", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.Column("error_code", sa.String(120)),
            sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")))
    for table, name, columns in (("runtime_jobs", "ix_runtime_job_due", ["status", "next_run_at"]),
        ("runtime_runs", "ix_runtime_runs_job_started", ["job_name", "started_at"]),
        ("runtime_runs", "ix_runtime_runs_started", ["started_at"])):
        if name not in {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table)}:
            op.create_index(name, table, columns)


def downgrade():
    for name in ("runtime_runs", "runtime_jobs"):
        if sa.inspect(op.get_bind()).has_table(name):
            op.drop_table(name)
