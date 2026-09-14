"""teach_backs + teach_back_ratings (v2.0 §10 flywheel extras, WP8)

Guarded: has_table checks everywhere.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("teach_backs"):
        op.create_table(
            "teach_backs",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
            sa.Column("concept", sa.String(80), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="visible"),
            sa.Column("helpful_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("not_helpful_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        for col in ("user_id", "course_id", "concept"):
            op.create_index(f"ix_teach_backs_{col}", "teach_backs", [col])
    insp = sa.inspect(bind)
    if not insp.has_table("teach_back_ratings"):
        op.create_table(
            "teach_back_ratings",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("teach_back_id", sa.Integer(), sa.ForeignKey("teach_backs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rater_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("helpful", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("teach_back_id", "rater_id", name="uq_teach_back_rating"),
        )
        op.create_index("ix_teach_back_ratings_teach_back_id", "teach_back_ratings", ["teach_back_id"])
        op.create_index("ix_teach_back_ratings_rater_id", "teach_back_ratings", ["rater_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for t in ("teach_back_ratings", "teach_backs"):
        if sa.inspect(bind).has_table(t):
            op.drop_table(t)
