"""Guided lab evidence and idempotent offline sync."""
from alembic import op
import sqlalchemy as sa
revision='0029'
down_revision='0028'
branch_labels=None
depends_on=None


def upgrade():
    bind=op.get_bind()
    from app.models.learning_release import LabInvestigationAttempt, OfflineSyncReceipt
    LabInvestigationAttempt.__table__.create(bind,checkfirst=True)
    OfflineSyncReceipt.__table__.create(bind,checkfirst=True)


def downgrade():
    op.drop_table('offline_sync_receipts')
    op.drop_table('lab_investigation_attempts')
