"""course_studio_settings + user_game_stats streak-freeze columns
(v2.0 §4 Studio faces, WP6)

Guarded: has_table / _has_column checks everywhere.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table, col):
    return insp.has_table(table) and any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("course_studio_settings"):
        op.create_table(
            "course_studio_settings",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False, unique=True),
            sa.Column("parent_view", sa.JSON(), nullable=False),
            sa.Column("rewards", sa.JSON(), nullable=False),
            sa.Column("face_dismissed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_course_studio_settings_course_id", "course_studio_settings", ["course_id"])
    insp = sa.inspect(bind)
    if insp.has_table("user_game_stats"):
        if not _has_column(insp, "user_game_stats", "streak_freeze_month"):
            op.add_column("user_game_stats", sa.Column("streak_freeze_month", sa.String(7), nullable=True))
        if not _has_column(insp, "user_game_stats", "streak_freezes_used"):
            op.add_column("user_game_stats", sa.Column("streak_freezes_used", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("course_studio_settings"):
        op.drop_table("course_studio_settings")
    if _has_column(insp, "user_game_stats", "streak_freezes_used"):
        with op.batch_alter_table("user_game_stats", reflect_kwargs={"resolve_fks": False}) as b:
            b.drop_column("streak_freezes_used")
            b.drop_column("streak_freeze_month")
