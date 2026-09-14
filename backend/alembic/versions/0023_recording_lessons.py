"""Private recording lesson workbench. Revision 0023."""
from alembic import op
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, MetaData, Table
from sqlalchemy.sql import func
revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def schema():
    metadata = MetaData()
    for parent in ("live_classes", "lessons", "users"):
        Table(parent, metadata, Column("id", Integer, primary_key=True))
    Table("recording_lessons", metadata,
        Column("id", Integer, primary_key=True),
        Column("class_id", Integer, ForeignKey("live_classes.id"), nullable=False, unique=True),
        Column("source_path", Text, nullable=False, default=""),
        Column("status", String(24), nullable=False, default="queued", index=True),
        Column("language", String(12), nullable=False, default="auto"),
        Column("version", Integer, nullable=False, default=1),
        Column("attempts", Integer, nullable=False, default=0),
        Column("error", String(500), nullable=True),
        Column("title", String(200), nullable=False, default=""),
        Column("notes", Text, nullable=False, default=""),
        Column("segments", JSON, nullable=False, default=list),
        Column("chapters", JSON, nullable=False, default=list),
        Column("concepts", JSON, nullable=False, default=list),
        Column("question_ids", JSON, nullable=False, default=list),
        Column("lesson_id", Integer, ForeignKey("lessons.id"), nullable=True, unique=True),
        Column("reviewed_by", Integer, ForeignKey("users.id"), nullable=True),
        Column("started_at", DateTime(timezone=True), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    )
    return metadata


def upgrade():
    schema().tables["recording_lessons"].create(op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("recording_lessons")
