"""content libraries — virtual_lab_catalog, virtual_lab_results, three_d_models.is_library

Guarded like 0003/0004: init_db()'s create_all may already have created the
tables via the SQLAlchemy models, so every operation checks has_table /
_has_column first. The new column is a plain BOOLEAN NOT NULL DEFAULT false
(no FK), so ALTER TABLE ADD COLUMN works on SQLite without a batch op.

Revision ID: 0007
Revises: 0006c
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table_name: str, column_name: str) -> bool:
    if not insp.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in insp.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("virtual_lab_catalog"):
        op.create_table(
            "virtual_lab_catalog",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("slug", sa.String(50), nullable=False, unique=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("subject", sa.String(50), nullable=False, server_default="general"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("provider", sa.String(16), nullable=False, server_default="embed"),
            sa.Column("embed_url", sa.String(1000), nullable=True),
            sa.Column("native_template", sa.String(32), nullable=True),
            sa.Column("config", sa.JSON(), nullable=True),
            sa.Column("attribution", sa.String(300), nullable=True),
            sa.Column("thumbnail_url", sa.String(1000), nullable=True),
            sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_virtual_lab_catalog_slug", "virtual_lab_catalog", ["slug"], unique=True)
    else:
        print("[0007_content_libraries] virtual_lab_catalog already exists — skipping create.")

    insp = sa.inspect(bind)
    if not insp.has_table("virtual_lab_results"):
        op.create_table(
            "virtual_lab_results",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("lab_slug", sa.String(50), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("max_score", sa.Integer(), nullable=False),
            sa.Column("duration_s", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_virtual_lab_results_lab_slug", "virtual_lab_results", ["lab_slug"])
        op.create_index("ix_virtual_lab_results_user_id", "virtual_lab_results", ["user_id"])
    else:
        print("[0007_content_libraries] virtual_lab_results already exists — skipping create.")

    insp = sa.inspect(bind)
    if insp.has_table("three_d_models") and not _has_column(insp, "three_d_models", "is_library"):
        op.add_column(
            "three_d_models",
            sa.Column("is_library", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    else:
        print("[0007_content_libraries] three_d_models.is_library present (or table missing) — skipping.")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_column(insp, "three_d_models", "is_library"):
        with op.batch_alter_table("three_d_models") as batch_op:
            batch_op.drop_column("is_library")
    insp = sa.inspect(bind)
    if insp.has_table("virtual_lab_results"):
        op.drop_table("virtual_lab_results")
    insp = sa.inspect(bind)
    if insp.has_table("virtual_lab_catalog"):
        op.drop_table("virtual_lab_catalog")
