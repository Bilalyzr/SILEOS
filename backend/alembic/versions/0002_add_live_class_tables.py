"""add live class tables

Creates the seven Live Classes tables: live_class_schedules, live_classes,
live_class_join_tokens, live_class_attendance, live_class_polls,
live_class_poll_votes, live_class_events. Columns/enums/uniques/indexes
mirror app/models/live_class.py exactly — see that file's docstring and
docs/superpowers/specs/2026-09-02-live-classes-brief.md ("Data model").

Enums are created as native Postgres ENUM types (SQLAlchemy's default for
`sa.Enum` on Postgres) and as VARCHAR + CHECK on SQLite — standard Alembic/
SQLAlchemy cross-dialect behavior, no special handling needed here.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dual-path transition (deviations file item 9): init_db() calls
    # Base.metadata.create_all() on EVERY app startup, and it now sees these
    # seven tables too (app/models/live_class.py is registered in
    # app/models/__init__.py). Nothing in the current deploy path invokes
    # Alembic before the app starts, so in practice create_all() usually
    # wins the race and creates the tables first — `alembic upgrade head`
    # must tolerate that instead of failing with "table already exists".
    # Bail out early (no-op) when the tables are already there; downgrade()
    # mirrors this by only dropping what's actually present.
    insp = sa.inspect(op.get_bind())
    if insp.has_table("live_class_schedules"):
        print(
            "[0002_add_live_class_tables] live_class_schedules already "
            "exists (created by init_db()'s create_all) — skipping table "
            "creation, treating this revision as already applied."
        )
        return

    live_class_status = sa.Enum(
        "SCHEDULED", "LIVE", "ENDED", "CANCELLED", name="liveclassstatus"
    )
    recording_status = sa.Enum(
        "NONE", "REQUESTED", "PROCESSING", "AVAILABLE", "FAILED", name="recordingstatus"
    )
    poll_status = sa.Enum("DRAFT", "ACTIVE", "CLOSED", name="pollstatus")
    attendance_source = sa.Enum("WEB", "MOBILE", name="attendancesource")

    op.create_table(
        "live_class_schedules",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False, index=True),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=True),
        sa.Column("instructor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("recurrence_weekly", sa.JSON(), nullable=True),
        sa.Column("weeks", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "live_classes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("live_class_schedules.id"), nullable=True, index=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("lesson_id", sa.Integer(), sa.ForeignKey("lessons.id"), nullable=True),
        sa.Column("instructor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("room_name", sa.String(120), nullable=False, unique=True, index=True),
        sa.Column("status", live_class_status, nullable=False, server_default="SCHEDULED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_participants", sa.Integer(), nullable=False, server_default="0"),
        # Bunny video GUIDs are opaque strings — see app/models/live_class.py.
        sa.Column("recording_video_id", sa.String(64), nullable=True),
        sa.Column("recording_status", recording_status, nullable=False, server_default="NONE"),
        # Model default is Python-level (default=dict); a server_default is
        # added here too so raw-SQL inserts (outside the ORM) don't violate
        # NOT NULL.
        sa.Column("settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_live_classes_course_start", "live_classes", ["course_id", "scheduled_start"])
    op.create_index("ix_live_classes_instructor_start", "live_classes", ["instructor_id", "scheduled_start"])
    op.create_index("ix_live_classes_status", "live_classes", ["status"])

    op.create_table(
        "live_class_join_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("live_classes.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("jti", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("moderator", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "live_class_attendance",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("live_classes.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("source", attendance_source, nullable=False, server_default="WEB"),
        sa.Column("first_joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accumulated_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("present", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("class_id", "user_id", name="uq_live_class_attendance_class_user"),
    )

    op.create_table(
        "live_class_polls",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("live_classes.id"), nullable=False, index=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("status", poll_status, nullable=False, server_default="DRAFT"),
        sa.Column("show_results", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "live_class_poll_votes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("poll_id", sa.Integer(), sa.ForeignKey("live_class_polls.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("option_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("poll_id", "user_id", name="uq_live_class_poll_votes_poll_user"),
    )

    op.create_table(
        "live_class_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, index=True, autoincrement=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("live_classes.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event", sa.String(64), nullable=False, index=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Mirrors upgrade()'s dual-path tolerance: only drop tables/indexes that
    # actually exist, so downgrade is safe to run regardless of whether
    # upgrade() actually created anything (it may have no-op'd because
    # init_db()'s create_all got there first) or whether the tables were
    # since dropped by some other path.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    if "live_class_events" in existing_tables:
        op.drop_table("live_class_events")
    if "live_class_poll_votes" in existing_tables:
        op.drop_table("live_class_poll_votes")
    if "live_class_polls" in existing_tables:
        op.drop_table("live_class_polls")
    if "live_class_attendance" in existing_tables:
        op.drop_table("live_class_attendance")
    if "live_class_join_tokens" in existing_tables:
        op.drop_table("live_class_join_tokens")

    if "live_classes" in existing_tables:
        existing_indexes = {ix["name"] for ix in insp.get_indexes("live_classes")}
        if "ix_live_classes_status" in existing_indexes:
            op.drop_index("ix_live_classes_status", table_name="live_classes")
        if "ix_live_classes_instructor_start" in existing_indexes:
            op.drop_index("ix_live_classes_instructor_start", table_name="live_classes")
        if "ix_live_classes_course_start" in existing_indexes:
            op.drop_index("ix_live_classes_course_start", table_name="live_classes")
        op.drop_table("live_classes")

    if "live_class_schedules" in existing_tables:
        op.drop_table("live_class_schedules")

    if bind.dialect.name == "postgresql":
        sa.Enum(name="attendancesource").drop(bind, checkfirst=True)
        sa.Enum(name="pollstatus").drop(bind, checkfirst=True)
        sa.Enum(name="recordingstatus").drop(bind, checkfirst=True)
        sa.Enum(name="liveclassstatus").drop(bind, checkfirst=True)
