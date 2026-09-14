"""Assessment Studio publication metadata; frozen schema. Revision 0022."""
from alembic import op
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, MetaData, Table, inspect
from sqlalchemy.sql import func
revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def schema():
    metadata = MetaData()
    for parent in ("users", "courses", "bank_questions"):
        Table(parent, metadata, Column("id", Integer, primary_key=True))
    Table("studio_questions", metadata,
        Column('id', Integer, primary_key=True),
        Column('course_id', Integer, ForeignKey('courses.id'), nullable=False, index=True),
        Column('bank_question_id', Integer, ForeignKey('bank_questions.id'), nullable=False, unique=True),
        Column('concept', String(80), nullable=False, index=True),
        Column('purpose', String(20), nullable=False, default='practice'),
        Column('status', String(20), nullable=False, default='draft'),
        Column('version', Integer, nullable=False, default=1),
        Column('published_snapshot', JSON, nullable=True),
        Column('history', JSON, nullable=False, default=list),
        Column('created_by', Integer, ForeignKey('users.id'), nullable=False),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    )
    return metadata


def upgrade():
    schema().tables["studio_questions"].create(op.get_bind(), checkfirst=True)


def downgrade():
    if inspect(op.get_bind()).has_table("studio_questions"):
        op.drop_table("studio_questions")
