"""Map the existing legacy course tool additions on every database dialect."""
from alembic import op
import sqlalchemy as sa
revision = '0025'
down_revision = '0024'
branch_labels = None
depends_on = None

def upgrade():
    inspector = sa.inspect(op.get_bind())
    # The SQLite migration-only harness intentionally omits legacy tables.
    # init_db/create_all owns those tables and includes this column when created later.
    if inspector.has_table('courses'):
        columns = {c['name'] for c in inspector.get_columns('courses')}
        if 'enabled_tools' not in columns:
            op.add_column('courses', sa.Column('enabled_tools', sa.JSON(), nullable=True))
    transfer_columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('course_transfers')}
    if 'staging_cleaned_at' not in transfer_columns:
        op.add_column('course_transfers', sa.Column('staging_cleaned_at', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    # Legacy PostgreSQL installations already owned this column before Alembic.
    # Preserve their tool selections when rolling the revision back.
    pass
