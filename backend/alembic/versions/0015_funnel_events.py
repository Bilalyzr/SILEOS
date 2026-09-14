"""funnel_events (roadmap R1 conversion funnel, 2026-09-05)

Revision ID: 0015
Revises: 0014
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("funnel_events"):
        op.create_table(
            "funnel_events",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("kind", sa.String(24), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("session_id", sa.String(64), nullable=False),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        for col in ("kind", "course_id", "user_id", "session_id", "created_at"):
            op.create_index(f"ix_funnel_events_{col}", "funnel_events", [col])


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("funnel_events"):
        op.drop_table("funnel_events")
