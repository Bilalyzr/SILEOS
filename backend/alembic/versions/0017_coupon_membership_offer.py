"""coupons.razorpay_offer_id (roadmap R7 coupons on memberships, 2026-09-05)

Revision ID: 0017
Revises: 0016
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table, col):
    return insp.has_table(table) and any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("coupons") and not _has_column(insp, "coupons", "razorpay_offer_id"):
        op.add_column("coupons", sa.Column("razorpay_offer_id", sa.String(64), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_column(insp, "coupons", "razorpay_offer_id"):
        with op.batch_alter_table("coupons", reflect_kwargs={"resolve_fks": False}) as b:
            b.drop_column("razorpay_offer_id")
