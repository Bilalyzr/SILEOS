"""3D match-and-verify tasks — three_d_tasks, three_d_task_attempts (v2.0 §6, WP2)

Guarded like 0003/0004/0007: init_db()'s create_all may already have created
the tables via the SQLAlchemy models, so every operation checks has_table.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("three_d_tasks"):
        op.create_table(
            "three_d_tasks",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("model_id", sa.Integer(), sa.ForeignKey("three_d_models.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("task_type", sa.String(16), nullable=False),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("concepts", sa.JSON(), nullable=False),
            sa.Column("tier_floor", sa.String(2), nullable=False, server_default="T4"),
            sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_three_d_tasks_owner_id", "three_d_tasks", ["owner_id"])
        op.create_index("ix_three_d_tasks_model_id", "three_d_tasks", ["model_id"])
    else:
        print("[0008_three_d_tasks] three_d_tasks already exists — skipping create.")

    insp = sa.inspect(bind)
    if not insp.has_table("three_d_task_attempts"):
        op.create_table(
            "three_d_task_attempts",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("task_id", sa.Integer(), sa.ForeignKey("three_d_tasks.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("max_score", sa.Integer(), nullable=False),
            sa.Column("mode", sa.String(2), nullable=False, server_default="T1"),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("confidence", sa.String(16), nullable=False, server_default="unknown"),
            sa.Column("confidence_detail", sa.JSON(), nullable=False),
            sa.Column("duration_s", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_three_d_task_attempts_task_id", "three_d_task_attempts", ["task_id"])
        op.create_index("ix_three_d_task_attempts_user_id", "three_d_task_attempts", ["user_id"])
    else:
        print("[0008_three_d_tasks] three_d_task_attempts already exists — skipping create.")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("three_d_task_attempts"):
        op.drop_table("three_d_task_attempts")
    insp = sa.inspect(bind)
    if insp.has_table("three_d_tasks"):
        op.drop_table("three_d_tasks")
