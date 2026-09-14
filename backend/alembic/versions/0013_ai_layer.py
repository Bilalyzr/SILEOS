"""tutor_escalations + content_error_reports (v2.0 §9 AI layer, WP7)

Guarded: has_table checks everywhere.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("tutor_escalations"):
        op.create_table(
            "tutor_escalations",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("instructor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("context", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="open"),
            sa.Column("instructor_reply", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        )
        for col in ("course_id", "student_id", "instructor_id", "status"):
            op.create_index(f"ix_tutor_escalations_{col}", "tutor_escalations", [col])
    insp = sa.inspect(bind)
    if not insp.has_table("content_error_reports"):
        op.create_table(
            "content_error_reports",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("reporter_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("instructor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("ref_id", sa.Integer(), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="open"),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
        for col in ("reporter_id", "course_id", "instructor_id", "status"):
            op.create_index(f"ix_content_error_reports_{col}", "content_error_reports", [col])


def downgrade() -> None:
    bind = op.get_bind()
    for t in ("content_error_reports", "tutor_escalations"):
        if sa.inspect(bind).has_table(t):
            op.drop_table(t)
