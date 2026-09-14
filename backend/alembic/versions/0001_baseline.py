"""baseline — pre-existing schema stamp

This revision is intentionally empty. Every table that existed before the
Live Classes feature (users, courses, enrollments, payments, memberships,
bundles, company invoicing, etc.) is owned by `init_db()`
(app/core/database.py, `Base.metadata.create_all`) plus the hand-applied
SQL files under `backend/migrations/*.sql` — NOT by Alembic. This revision
exists purely so a fresh database can be `alembic stamp head`-ed at this
point without Alembic trying to (re)create anything that create_all/manual
SQL already owns.

Alembic only becomes the source of truth starting with the next revision
(0002_add_live_class_tables), which is the first migration that actually
creates tables. See deviations file item 9.

Revision ID: 0001
Revises:
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: pre-existing schema is owned by init_db() + backend/migrations/*.sql."""
    pass


def downgrade() -> None:
    """No-op: nothing was created by upgrade()."""
    pass
