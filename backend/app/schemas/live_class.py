"""Pydantic schemas for Live Classes.

No response envelope — plain `response_model` per endpoint (deviations file
item 2). Mirrors app/models/live_class.py; routers/services in later tasks
(3-6) import these exact names.
"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


VALID_WEEKDAYS = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class LiveClassSettings(BaseModel):
    """Per-class settings JSON. Defaults match the brief's documented
    default: {lobby_enabled: true, start_muted: true, allow_chat: true,
    allow_share: true, record: false, attendance_threshold_pct: 60}."""

    lobby_enabled: bool = True
    start_muted: bool = True
    allow_chat: bool = True
    allow_share: bool = True
    record: bool = False
    attendance_threshold_pct: int = Field(default=60, ge=0, le=100)
    # v2.0 §7.1 classification + §7.4 retention (WP5); all optional so old clients keep working
    purpose: str | None = None
    mode: str | None = None
    audience: str | None = None
    recording_policy: str | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)

    @field_validator("purpose", "mode", "audience", "recording_policy")
    @classmethod
    def _classification(cls, v, info):
        from app.services.class_report_service import AUDIENCES, MODES, PURPOSES, RECORDING_POLICIES
        allowed = {"purpose": PURPOSES, "mode": MODES, "audience": AUDIENCES, "recording_policy": RECORDING_POLICIES}[info.field_name]
        if v is not None and v not in allowed:
            raise ValueError(f"{info.field_name} must be one of {sorted(allowed)}")
        return v


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

class LiveClassCreate(BaseModel):
    course_id: int
    lesson_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    scheduled_start: datetime  # must be timezone-aware
    duration_minutes: int = Field(ge=15, le=480)
    timezone: str | None = None
    recurrence_weekly: list[str] | None = Field(default=None, max_length=7)
    weeks: int | None = Field(default=None, ge=1, le=12)
    settings: LiveClassSettings | None = None

    def model_post_init(self, __context) -> None:
        if self.recurrence_weekly:
            invalid = set(self.recurrence_weekly) - VALID_WEEKDAYS
            if invalid:
                raise ValueError(
                    f"recurrence_weekly contains invalid day codes: {sorted(invalid)}"
                )


class LiveClassSettingsPatch(BaseModel):
    """Partial settings update — every field optional and left `None` when
    not supplied, so PATCH can shallow-merge only the provided keys over
    the class's existing settings dict. Unlike `LiveClassSettings` (used at
    create time, where every field legitimately has a default), this schema
    must NOT fill unspecified fields with defaults — the router uses
    presence (`exclude_unset`) to know which keys the caller actually meant
    to change, so a PATCH of just `{"record": true}` doesn't reset
    `attendance_threshold_pct` back to 60."""

    lobby_enabled: bool | None = None
    start_muted: bool | None = None
    allow_chat: bool | None = None
    allow_share: bool | None = None
    record: bool | None = None
    attendance_threshold_pct: int | None = Field(default=None, ge=0, le=100)
    purpose: str | None = None
    mode: str | None = None
    audience: str | None = None
    recording_policy: str | None = None
    retention_days: int | None = Field(default=None, ge=1, le=3650)


class LiveClassUpdate(BaseModel):
    """Editable only while the class is SCHEDULED (409 otherwise)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    scheduled_start: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=480)
    timezone: str | None = None
    settings: LiveClassSettingsPatch | None = None


class LiveClassOut(BaseModel):
    id: int
    schedule_id: int | None
    course_id: int
    lesson_id: int | None
    instructor_id: int
    title: str
    description: str | None
    scheduled_start: datetime
    scheduled_end: datetime
    timezone: str
    room_name: str
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    live_participants: int
    recording_video_id: str | None
    recording_status: str
    settings: dict
    purpose: str | None = None
    mode: str | None = None
    audience: str | None = None
    recording_policy: str | None = None
    retention_until: datetime | None = None
    recording_deleted_at: datetime | None = None
    lifecycle: str | None = None

    # Derived / request-time fields — computed by the router, not stored.
    server_ts: datetime
    my_attendance: dict | None = None
    can_start: bool = False
    join_opens_at: datetime


# ---------------------------------------------------------------------------
# Session (join / heartbeat)
# ---------------------------------------------------------------------------

class JoinTokenOut(BaseModel):
    class_summary: LiveClassOut
    room_name: str
    jitsi_url: str
    jwt: str
    expires_in: int


class HeartbeatIn(BaseModel):
    client_ts: datetime


class HeartbeatOut(BaseModel):
    accumulated_seconds: int
    delta: int


# ---------------------------------------------------------------------------
# Polls
# ---------------------------------------------------------------------------

class PollCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=10)
    show_results: bool = True


class PollOut(BaseModel):
    id: int
    class_id: int
    question: str
    options: list[str]
    status: str
    show_results: bool
    created_at: datetime
    activated_at: datetime | None
    closed_at: datetime | None

    # Role-aware extras: instructor gets tallies always; student gets their
    # own vote and (if show_results) tallies. None when not applicable.
    tallies: list[int] | None = None
    my_vote: int | None = None


class PollVoteIn(BaseModel):
    option_index: int = Field(ge=0)


# ---------------------------------------------------------------------------
# Recordings (Task 6)
# ---------------------------------------------------------------------------

class RecordingIntentOut(BaseModel):
    """Response for POST .../recording/start|stop — records intent only;
    actual Jibri control is client-side per the brief. `recording_status`
    reflects the LiveClass row after the transition."""

    class_id: int
    recording_status: str


class RecordingIngestIn(BaseModel):
    """Body for the internal finalize-worker callback
    POST /api/v1/internal/live/recordings.

    `room_name` (not `class_id`) identifies the target class: Jibri names
    recording files/directories after the room being recorded (opaque
    `si-<random8>` strings — see live_class_service.generate_room_name),
    never after the numeric LiveClass id, so the worker can only ever know
    the room name from the filename it found on disk. The backend resolves
    `room_name` to a LiveClass server-side (404 if no match) — this also
    makes the room-name-matches-file-path ownership check in
    live_recording_service.validate_recording_path trivially satisfied by
    construction rather than a separate cross-check the caller could get
    wrong."""

    room_name: str
    file_path: str
    size_bytes: int = Field(ge=0)
    duration_seconds: int = Field(ge=0)


class RecordingIngestOut(BaseModel):
    class_id: int
    recording_status: str
    recording_video_id: str | None = None
    skipped: bool = False


class RecordingPlaybackOut(BaseModel):
    class_id: int
    video_id: str
    hls_url: str
    expires_in: int | None = None
    signed: bool = False


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class AttendanceRowOut(BaseModel):
    user_id: int
    name: str
    email: str
    first_joined_at: datetime | None
    accumulated_minutes: int
    present: bool | None


# ---------------------------------------------------------------------------
# List (paginated)
# ---------------------------------------------------------------------------

class LiveClassListOut(BaseModel):
    """Response shape for GET /classes — paginated, role-scoped."""

    items: list[LiveClassOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Live-now
# ---------------------------------------------------------------------------

class LiveNowOut(BaseModel):
    classes: list[LiveClassOut]
