"""Operations health and course transfer previews. Revision 0024."""
from alembic import op
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, MetaData, Table
from sqlalchemy.sql import func
revision = '0024'
down_revision = '0023'
branch_labels = None
depends_on = None


def schema():
    metadata = MetaData()
    for parent in ('users', 'courses'):
        Table(parent, metadata, Column('id', Integer, primary_key=True))
    Table('service_heartbeats', metadata,
        Column('name', String(64), primary_key=True),
        Column('status', String(24), nullable=False),
        Column('detail', JSON, nullable=False, default=dict),
        Column('seen_at', DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    Table('course_transfers', metadata,
        Column('id', String(36), primary_key=True),
        Column('owner_id', Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        Column('kind', String(20), nullable=False),
        Column('filename', String(255), nullable=False),
        Column('sha256', String(64), nullable=False),
        Column('manifest', JSON, nullable=False),
        Column('warnings', JSON, nullable=False, default=list),
        Column('status', String(20), nullable=False, default="preview"),
        Column('course_id', Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        Column('error', Text, nullable=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column('expires_at', DateTime(timezone=True), nullable=False),
    )
    return metadata


def upgrade():
    for name in ('service_heartbeats', 'course_transfers'):
        schema().tables[name].create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table('course_transfers')
    op.drop_table('service_heartbeats')
