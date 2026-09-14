"""live classes — classification axes, retention/soft-delete columns,
class_reports, recording_audit (v2.0 §7, WP5)

Guarded: has_table / _has_column checks everywhere.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_COLUMNS = [
    ("purpose", sa.String(24)), ("mode", sa.String(24)), ("audience", sa.String(16)),
    ("recording_policy", sa.String(12)), ("retention_until", sa.DateTime(timezone=True)),
    ("recording_deleted_at", sa.DateTime(timezone=True)), ("recording_deleted_by", sa.Integer()),
    ("recording_delete_reason", sa.String(300)),
]


def _has_column(insp, table, col):
    return insp.has_table(table) and any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("live_classes"):
        for name, typ in NEW_COLUMNS:
            if not _has_column(insp, "live_classes", name):
                op.add_column("live_classes", sa.Column(name, typ, nullable=True))
    insp = sa.inspect(bind)
    if not insp.has_table("class_reports"):
        op.create_table(
            "class_reports",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("class_id", sa.Integer(), sa.ForeignKey("live_classes.id"), nullable=False, unique=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column("instructor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("purpose", sa.String(24), nullable=True),
            sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_s", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("attendance", sa.JSON(), nullable=False),
            sa.Column("event_log", sa.JSON(), nullable=False),
            sa.Column("poll_results", sa.JSON(), nullable=False),
            sa.Column("engagement", sa.JSON(), nullable=False),
            sa.Column("instructor_notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("transcript", sa.Text(), nullable=True),
            sa.Column("ai_topics", sa.JSON(), nullable=True),
            sa.Column("processing_status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("shared_with_guardians", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_class_reports_course_id", "class_reports", ["course_id"])
    insp = sa.inspect(bind)
    if not insp.has_table("recording_audit"):
        op.create_table(
            "recording_audit",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("class_id", sa.Integer(), sa.ForeignKey("live_classes.id"), nullable=False),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("action", sa.String(24), nullable=False),
            sa.Column("reason", sa.String(300), nullable=True),
            sa.Column("detail", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_recording_audit_class_id", "recording_audit", ["class_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for t in ("recording_audit", "class_reports"):
        if sa.inspect(bind).has_table(t):
            op.drop_table(t)
    insp = sa.inspect(bind)
    if insp.has_table("live_classes"):
        with op.batch_alter_table("live_classes", reflect_kwargs={"resolve_fks": False}) as batch_op:
            for name, _ in NEW_COLUMNS:
                if _has_column(insp, "live_classes", name):
                    batch_op.drop_column(name)
