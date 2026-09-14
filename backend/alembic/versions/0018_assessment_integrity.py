"""quizzes availability window + quiz_questions.is_retired (roadmap R8, 2026-09-05)

Revision ID: 0018
Revises: 0017
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table, col):
    return insp.has_table(table) and any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("quizzes"):
        for col in ("quiz_available_from", "quiz_available_until"):
            if not _has_column(insp, "quizzes", col):
                op.add_column("quizzes", sa.Column(col, sa.DateTime(timezone=True), nullable=True))
    insp = sa.inspect(bind)
    if insp.has_table("quiz_questions") and not _has_column(insp, "quiz_questions", "is_retired"):
        op.add_column("quiz_questions", sa.Column("is_retired", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_column(insp, "quiz_questions", "is_retired"):
        with op.batch_alter_table("quiz_questions", reflect_kwargs={"resolve_fks": False}) as b:
            b.drop_column("is_retired")
    insp = sa.inspect(bind)
    if _has_column(insp, "quizzes", "quiz_available_from"):
        with op.batch_alter_table("quizzes", reflect_kwargs={"resolve_fks": False}) as b:
            b.drop_column("quiz_available_from")
            b.drop_column("quiz_available_until")
