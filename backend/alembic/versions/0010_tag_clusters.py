"""emergent tag taxonomy — tag_clusters (v2.0 §3, WP4)

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("tag_clusters"):
        op.create_table(
            "tag_clusters",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("label", sa.String(120), nullable=True),
            sa.Column("member_tags", sa.JSON(), nullable=False),
            sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("centroid", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("tag_clusters"):
        op.drop_table("tag_clusters")
