"""merge digital-library (0005) and money-ops (0005m) branches

The two Sep-3 feature branches both chained off 0004 and were never
merge-revised, leaving alembic with multiple heads — `upgrade head`
(and every test fixture that runs it) fails with MultipleHeads. This
empty merge node joins the branches so the graph has one head again.

Revision ID: 0006m
Revises: 0005, 0005m
Create Date: 2026-09-04
"""
from typing import Union

from alembic import op

revision: str = "0006m"
down_revision: Union[str, None] = ("0005", "0005m")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge node: both child branches are already applied independently.
    pass


def downgrade() -> None:
    # A merge cannot be un-merged without re-branching; nothing to do.
    pass
