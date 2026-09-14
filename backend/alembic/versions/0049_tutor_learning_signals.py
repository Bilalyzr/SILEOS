"""Course-linked Sasha tutor learning signals.

Revision ID: 0049
Revises: 0048
"""
from alembic import op
import sqlalchemy as sa

from app.core.migration_operations import idempotent_create_operations


revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None
op = idempotent_create_operations(op)


def upgrade():
    op.create_table(
        "tutor_learning_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("session_key", sa.String(64), nullable=False, server_default=""),
        sa.Column("prompt_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("concept", sa.String(80), nullable=False, server_default="General course support"),
        sa.Column("struggle_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="developing"),
        sa.Column("likely_gap", sa.String(32), nullable=False, server_default="concept_clarity"),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("repeat_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_guarded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_tutor_learning_signals_user_id", ["user_id"]),
        ("ix_tutor_learning_signals_course_id", ["course_id"]),
        ("ix_tutor_learning_signals_created_at", ["created_at"]),
        ("ix_tutor_signal_course_created", ["course_id", "created_at"]),
        ("ix_tutor_signal_learner_course_created", ["user_id", "course_id", "created_at"]),
        ("ix_tutor_signal_course_concept", ["course_id", "concept"]),
    ):
        op.create_index(name, "tutor_learning_signals", columns)


def downgrade():
    op.drop_table("tutor_learning_signals")
