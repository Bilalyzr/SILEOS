"""three_d_models.tier_files (roadmap item 9 pre-built 3D tiers, 2026-09-06)

Revision ID: 0019
Revises: 0018
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table, col):
    return insp.has_table(table) and any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("three_d_models") and not _has_column(insp, "three_d_models", "tier_files"):
        op.add_column("three_d_models", sa.Column("tier_files", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_column(insp, "three_d_models", "tier_files"):
        with op.batch_alter_table("three_d_models", reflect_kwargs={"resolve_fks": False}) as b:
            b.drop_column("tier_files")
