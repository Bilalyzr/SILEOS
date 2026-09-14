"""learning_signals + lesson_concept_markers + adaptive_sessions (2026-09-06)

Revision ID: 0020
Revises: 0019
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("learning_signals"):
        op.create_table(
            "learning_signals",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
            sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=True),
            sa.Column("quiz_id", sa.Integer(), nullable=True),
            sa.Column("question_id", sa.Integer(), nullable=True),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("position_s", sa.Integer(), nullable=True),
            sa.Column("segment", sa.Integer(), nullable=True),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        for col in ("user_id", "course_id", "lesson_id", "quiz_id", "question_id", "kind", "created_at"):
            op.create_index(f"ix_learning_signals_{col}", "learning_signals", [col])
    insp = sa.inspect(bind)
    if not insp.has_table("lesson_concept_markers"):
        op.create_table(
            "lesson_concept_markers",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=False),
            sa.Column("time_s", sa.Integer(), nullable=False),
            sa.Column("concept", sa.String(80), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_lesson_concept_markers_lesson_id", "lesson_concept_markers", ["lesson_id"])
    insp = sa.inspect(bind)
    if not insp.has_table("adaptive_sessions"):
        op.create_table(
            "adaptive_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("question_ids", sa.JSON(), nullable=False),
            sa.Column("plan", sa.JSON(), nullable=True),
            sa.Column("answers", sa.JSON(), nullable=True),
            sa.Column("results", sa.JSON(), nullable=True),
            sa.Column("score", sa.Integer(), nullable=True),
            sa.Column("max_score", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_adaptive_sessions_user_id", "adaptive_sessions", ["user_id"])
        op.create_index("ix_adaptive_sessions_course_id", "adaptive_sessions", ["course_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for t in ("adaptive_sessions", "lesson_concept_markers", "learning_signals"):
        if sa.inspect(bind).has_table(t):
            op.drop_table(t)
