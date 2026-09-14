"""courses.is_template + course_collaborators (roadmap R6, 2026-09-05)

Revision ID: 0016
Revises: 0015
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table, col):
    return insp.has_table(table) and any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("courses") and not _has_column(insp, "courses", "is_template"):
        op.add_column("courses", sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.false()))
    insp = sa.inspect(bind)
    if not insp.has_table("course_collaborators"):
        op.create_table(
            "course_collaborators",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="co_instructor"),
            sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("course_id", "user_id", name="uq_course_collaborator"),
        )
        op.create_index("ix_course_collaborators_course_id", "course_collaborators", ["course_id"])
        op.create_index("ix_course_collaborators_user_id", "course_collaborators", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("course_collaborators"):
        op.drop_table("course_collaborators")
    if _has_column(insp, "courses", "is_template"):
        with op.batch_alter_table("courses", reflect_kwargs={"resolve_fks": False}) as b:
            b.drop_column("is_template")
