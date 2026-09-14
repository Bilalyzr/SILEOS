"""Live Classes — Teachmint-style self-hosted Jitsi sessions.

Tables: live_class_schedules, live_classes, live_class_join_tokens,
live_class_attendance, live_class_polls, live_class_poll_votes,
live_class_events. See docs/superpowers/specs/2026-09-02-live-classes-brief.md
("Data model") and the deviations file (Integer PKs/FKs, not UUID) for the
authoritative shape. Owned by the live-classes feature; routers/services in
later tasks (3-6) import these exact names.

Room names are opaque `si-<random8>` strings generated server-side
(live_class_service.generate_room_name) — never derived from course/class
ids, so a leaked room name can't be guessed from a course URL. Enums are
stored by NAME (repo convention — see app/models/payment.py OrderStatus).
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON, Enum
from sqlalchemy.sql import func

from app.core.database import Base


class LiveClassStatus(enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


class RecordingStatus(enum.Enum):
    NONE = "none"
    REQUESTED = "requested"
    PROCESSING = "processing"
    AVAILABLE = "available"
    FAILED = "failed"


class PollStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class AttendanceSource(enum.Enum):
    WEB = "web"
    MOBILE = "mobile"


class LiveClassSchedule(Base):
    """Parent grouping for a recurring set of LiveClass occurrences.

    Created once per POST /classes call that specifies weekly recurrence
    (or a single one-off class); each generated occurrence is its own
    LiveClass row with its own room_name, sharing this schedule_id so the
    UI can show "part of a weekly series".
    """
    __tablename__ = "live_class_schedules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")

    # Recurrence definition — informational once occurrences are generated;
    # the occurrences themselves (LiveClass rows) are the source of truth
    # for actual scheduling.
    recurrence_weekly = Column(JSON, nullable=True)  # e.g. ["MO", "WE"]
    weeks = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<LiveClassSchedule(id={self.id}, course_id={self.course_id}, title={self.title})>"


class LiveClass(Base):
    """A single scheduled/live/ended live-class occurrence."""
    __tablename__ = "live_classes"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("live_class_schedules.id"), nullable=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")

    # Opaque, server-generated — never derived from course/class ids so a
    # room name can't be guessed. See live_class_service.generate_room_name.
    room_name = Column(String(120), unique=True, nullable=False, index=True)

    status = Column(Enum(LiveClassStatus), nullable=False, default=LiveClassStatus.SCHEDULED)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    live_participants = Column(Integer, nullable=False, default=0)

    # Bunny video GUIDs are opaque string ids (verified against
    # app/routers/bunny.py's video_id path param and its "guid" field from
    # the Bunny create-video response) — NOT integers, so this stays a
    # String column even though every other FK/PK in this file is Integer.
    recording_video_id = Column(String(64), nullable=True)
    recording_status = Column(Enum(RecordingStatus), nullable=False, default=RecordingStatus.NONE)

    # Per-class settings: lobby_enabled, start_muted, allow_chat, allow_share,
    # record, attendance_threshold_pct (see LiveClassSettings schema).
    settings = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # soft-cancel marker
    # v2.0 §7.1 classification axes (WP5) + §7.4 retention / soft-delete state
    purpose = Column(String(24), nullable=True)            # lecture | doubt_clearing | revision | lab_demo | assessment_viva | orientation | guest
    mode = Column(String(24), nullable=True)               # instructor_led | interactive_workshop | breakout | one_to_one
    audience = Column(String(16), nullable=True)           # full_cohort | batch | selected | open
    recording_policy = Column(String(12), nullable=True)   # always | on_start | never
    retention_until = Column(DateTime(timezone=True), nullable=True)
    recording_deleted_at = Column(DateTime(timezone=True), nullable=True)   # soft delete; purged after 30 days
    recording_deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    recording_delete_reason = Column(String(300), nullable=True)

    __table_args__ = (
        Index("ix_live_classes_course_start", "course_id", "scheduled_start"),
        Index("ix_live_classes_instructor_start", "instructor_id", "scheduled_start"),
        Index("ix_live_classes_status", "status"),
    )

    def __repr__(self):
        return f"<LiveClass(id={self.id}, title={self.title}, status={self.status})>"


class LiveClassJoinToken(Base):
    """Record of a minted Jitsi JWT — one row per join-token issuance.

    Not the JWT itself (that's never stored server-side beyond issuance);
    `jti` is the token's unique claim so redemption/heartbeat can be tied
    back to the specific token that was issued.
    """
    __tablename__ = "live_class_join_tokens"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("live_classes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    jti = Column(String(64), unique=True, nullable=False, index=True)
    moderator = Column(Boolean, nullable=False, default=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<LiveClassJoinToken(id={self.id}, class_id={self.class_id}, user_id={self.user_id})>"


class LiveClassAttendance(Base):
    """Server-truth attendance: join-token redemption + heartbeat deltas.

    One row per (class, user) — created as a stub on join-token issuance,
    updated by heartbeats, finalized (accumulated_seconds -> present) by
    live_class_service.finalize_attendance when the class ends.
    """
    __tablename__ = "live_class_attendance"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("live_classes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    source = Column(Enum(AttendanceSource), nullable=False, default=AttendanceSource.WEB)
    first_joined_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    accumulated_seconds = Column(Integer, nullable=False, default=0)
    present = Column(Boolean, nullable=True)  # null until finalized

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("class_id", "user_id", name="uq_live_class_attendance_class_user"),
    )

    def __repr__(self):
        return f"<LiveClassAttendance(class_id={self.class_id}, user_id={self.user_id}, present={self.present})>"


class LiveClassPoll(Base):
    """A quick poll posed during a live class. Options + tallies as JSON —
    portable across Postgres/SQLite and simple enough not to warrant a
    separate options table for this feature's scope."""
    __tablename__ = "live_class_polls"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("live_classes.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    question = Column(String(500), nullable=False)
    options = Column(JSON, nullable=False)  # list[str]
    status = Column(Enum(PollStatus), nullable=False, default=PollStatus.DRAFT)
    show_results = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    activated_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<LiveClassPoll(id={self.id}, class_id={self.class_id}, status={self.status})>"


class LiveClassPollVote(Base):
    """One vote per (poll, user) — enforced by the unique constraint so a
    duplicate vote attempt raises IntegrityError rather than needing a
    read-then-write race check in the router."""
    __tablename__ = "live_class_poll_votes"

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("live_class_polls.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    option_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("poll_id", "user_id", name="uq_live_class_poll_votes_poll_user"),
    )

    def __repr__(self):
        return f"<LiveClassPollVote(poll_id={self.poll_id}, user_id={self.user_id})>"


class LiveClassEvent(Base):
    """Append-only audit trail — class.started, join.token_issued,
    poll.voted, recording.available, etc. (see the brief's event-name list).
    Never updated after insert; id is a plain autoincrement PK (BigInteger
    with autoincrement on Postgres per the migration — high write volume
    expected from heartbeats/polls over a long-running deployment)."""
    __tablename__ = "live_class_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("live_classes.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    event = Column(String(64), nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<LiveClassEvent(id={self.id}, class_id={self.class_id}, event={self.event})>"
