"""course types — normalize every course into one of the three canonical types

Owner ruling 2026-09-04: every course must belong to exactly one of
meiporul / seyappaduporul / utporul. The column already exists (added by
ensure_schema); this migration only normalizes the DATA:
  - lowercase legacy capitalized values ("Meiporul" -> "meiporul")
  - blank/NULL rows fall back to the default type (meiporul)

The updates are skipped when the `courses` table does not exist: this
repo's alembic chain is PARTIAL (the full schema arrives via
init_db/create_all), so `upgrade head` on a fresh empty DB legitimately
has no courses table yet — create_all + ensure_schema will normalize on
first boot in that case.

Revision ID: 0006c
Revises: 0006m (merge of 0005 + 0005m)
Create Date: 2026-09-04
"""
from typing import Union

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "0006c"
down_revision: Union[str, None] = "0006m"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "courses" not in inspect(bind).get_table_names():
        # Fresh empty-DB path: no rows to normalize. ensure_schema +
        # create_all build the table on next boot; new rows get canonical
        # types from the API validators (create defaults to meiporul).
        return

    # Legacy edit-course stored capitalized values ("Meiporul"); the API now
    # canonicalizes to lowercase, so bring existing rows in line first.
    op.execute(
        "UPDATE courses SET course_type = lower(course_type) "
        "WHERE course_type IS NOT NULL AND course_type <> '' "
        "AND course_type <> lower(course_type)"
    )
    # Every course must have one of the three types; unclassified rows get
    # the default rather than staying blank.
    op.execute(
        "UPDATE courses SET course_type = 'meiporul' "
        "WHERE course_type IS NULL OR course_type = ''"
    )


def downgrade() -> None:
    # Data-only normalization; nothing to revert.
    pass
