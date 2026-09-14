"""Shared helpers for the Live Classes session/scheduling/attendance routers.

Room-name generation, access control, event logging, the two pieces of
server-truth attendance math (heartbeat deltas + end-of-class finalization),
and (Task 4) the scheduling-CRUD helpers: LiveClassOut assembly, weekly
recurrence date math, role-aware list/live-now scoping, and ICS body
building. Kept here rather than duplicated per-router per the plan's Task 3
interface contract; later tasks (5-6) import these same names.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.live_class import (
    LiveClass,
    LiveClassAttendance,
    LiveClassEvent,
    LiveClassPoll,
    LiveClassPollVote,
    LiveClassStatus,
)
from app.models.user import User

logger = logging.getLogger(__name__)

ADMIN_ROLES = ("admin", "superadmin")

STUDENT_JOIN_WINDOW_MINUTES = 15
VALID_WEEKDAY_ORDER = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

# Heartbeats fire on a 60s client interval; cap each accumulated delta at
# 90s so a suspended tab / missed beat / clock jump can't inflate attendance
# far beyond what was actually observed.
HEARTBEAT_CAP_SECONDS = 90


def _as_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip even for DateTime(timezone=True)
    columns (Postgres preserves it) — the stored value is still UTC
    wall-clock time, so a naive datetime here means "UTC, tzinfo stripped",
    not "local time". Re-attach UTC so arithmetic/comparison against an
    aware `now` doesn't raise or apply the host's local offset."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def generate_room_name() -> str:
    """Opaque, server-generated room name — never derived from course/class
    ids so a leaked room name can't be guessed from a course URL."""
    return "si-" + secrets.token_hex(4)


def log_event(db: Session, class_id: int, user_id: int | None, event: str,
              payload: dict | None = None) -> LiveClassEvent:
    """Append a LiveClassEvent row. Does NOT commit — the caller (router)
    owns the transaction boundary so an event can be persisted atomically
    alongside the state change that produced it."""
    row = LiveClassEvent(class_id=class_id, user_id=user_id, event=event, payload=payload)
    db.add(row)
    db.flush()
    return row


def is_assigned_instructor_or_admin(live_class: LiveClass, user: User) -> bool:
    """True if `user` is the assigned instructor for `live_class` or holds
    an admin/superadmin role — the guard used for create/edit/cancel/start
    (a stricter check than `user_can_access_class`, which also admits
    enrolled students for read/join access)."""
    if live_class.instructor_id == user.id:
        return True
    return user.role in ADMIN_ROLES


def user_can_access_class(db: Session, live_class: LiveClass, user: User) -> bool:
    """True if `user` may view/join `live_class`: the assigned instructor,
    an admin/superadmin, or a student enrolled (status "enrolled") in the
    class's course."""
    if live_class.instructor_id == user.id:
        return True
    if user.role in ADMIN_ROLES:
        return True
    enrolled = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == live_class.course_id,
            Enrollment.user_id == user.id,
            Enrollment.enrollment_status == "enrolled",
        )
        .first()
    )
    return enrolled is not None


def apply_heartbeat(db: Session, attendance: LiveClassAttendance, now: datetime) -> int:
    """Apply one heartbeat to `attendance` at server time `now`.

    First-ever beat (last_heartbeat_at is None): stamps first_joined_at and
    last_heartbeat_at, contributes 0 seconds (there's no prior beat to
    measure a gap against), and returns 0.

    Subsequent beats fall into one of two regimes, and they must NOT share
    one code path:

    - Sub-cap gap (<= 90s): delta = floor(gap), and `last_heartbeat_at`
      advances by only that credited (floored) amount — NOT all the way to
      `now` — so any fractional remainder from this beat (e.g. a beat that
      landed 0.5s after the last one) stays "owed" and rolls into the next
      gap instead of being discarded. Without this carry, many honest
      sub-second-interval beats would each floor their own delta to 0 and
      the class would never accumulate any attendance at all.
    - Beyond-cap gap (> 90s, e.g. a suspended tab or a real absence): delta
      = 90 (the cap), and `last_heartbeat_at` jumps all the way to `now` —
      discarding the beyond-cap remainder entirely. This is the case the
      cap exists for: a 10-minute silence must cost the class only 90s of
      credit AND must not leave 510s of "debt" sitting in the marker for
      the *next* beat to still see and get capped again. (An earlier
      version of this function used the sub-cap carry rule unconditionally,
      which left exactly that debt behind: beat, 600s silence, beat
      (correctly credited 90) — but then five beats 1s apart each still saw
      a >90s gap against the un-advanced marker and were incorrectly
      credited 90 each, inflating a single 10-minute absence into 540s of
      credited attendance.)

    Returns the delta actually applied (whole seconds).
    """
    if attendance.last_heartbeat_at is None:
        attendance.first_joined_at = attendance.first_joined_at or now
        attendance.last_heartbeat_at = now
        db.flush()
        return 0

    # SQLite drops tzinfo on round-trip (Postgres preserves it); the stored
    # value is still UTC wall-clock time, so re-attach UTC before comparing
    # against the aware `now` passed in by the caller.
    last_heartbeat_at = attendance.last_heartbeat_at
    if last_heartbeat_at.tzinfo is None:
        last_heartbeat_at = last_heartbeat_at.replace(tzinfo=timezone.utc)

    # Negative NTP/clock skew (a heartbeat arrives "before" the last credited
    # position per server clock) must not go negative or rewind the marker —
    # treat it as a zero-length gap rather than replaying/shrinking time.
    gap_seconds = (now - last_heartbeat_at).total_seconds()
    if gap_seconds <= 0:
        db.flush()
        return 0

    if gap_seconds > HEARTBEAT_CAP_SECONDS:
        # Beyond the cap: credit exactly the cap and discard the remainder
        # by jumping the marker to `now` — otherwise the un-credited excess
        # would still be sitting there on the next beat, which would see
        # another >90s gap and get capped (and credited) all over again.
        delta = HEARTBEAT_CAP_SECONDS
        attendance.last_heartbeat_at = now
    else:
        # Sub-cap: floor and carry the fractional remainder forward by only
        # advancing the marker by the credited amount.
        delta = int(gap_seconds)
        attendance.last_heartbeat_at = last_heartbeat_at + timedelta(seconds=delta)

    attendance.accumulated_seconds = (attendance.accumulated_seconds or 0) + delta
    db.flush()
    return delta


def finalize_attendance(db: Session, live_class: LiveClass) -> int:
    """Mark present/absent for every attendance row on `live_class` based on
    accumulated_seconds vs. the class's configured attendance_threshold_pct
    of the *scheduled* duration (not actual elapsed time — a class that ran
    long or was cut short still grades against what was promised).

    Returns the number of rows updated. Only flushes — never commits/rolls
    back (H1 review fix: this runs mid-transaction inside callers that have
    their own uncommitted mutations already pending, e.g. end_class's
    live_class.status/ended_at, recompute_attendance's live_class.settings —
    the caller's own db.commit() after this call is what persists these
    present-flag writes). Gamification is intentionally NOT awarded here —
    see award_attendance_xp below, called by the same routers AFTER their
    commit, once `present` is durably persisted and readable.
    """
    # "or 60" (not just a dict .get default) because the key can be present
    # but explicitly null (e.g. a partial settings payload) — .get's default
    # only fires when the key is absent, not when its value is None.
    threshold_pct = (live_class.settings or {}).get("attendance_threshold_pct") or 60

    scheduled_start = _as_utc(live_class.scheduled_start)
    scheduled_end = _as_utc(live_class.scheduled_end)
    scheduled_seconds = (scheduled_end - scheduled_start).total_seconds()
    required_seconds = scheduled_seconds * (threshold_pct / 100)

    rows = (
        db.query(LiveClassAttendance)
        .filter(LiveClassAttendance.class_id == live_class.id)
        .all()
    )
    updated = 0
    for row in rows:
        row.present = (row.accumulated_seconds or 0) >= required_seconds
        updated += 1

    db.flush()
    return updated


def award_attendance_xp(db: Session, live_class: LiveClass) -> None:
    """Gamification (spec D1): +25 XP per present attendee on `live_class`.
    Call this AFTER the caller's own db.commit() that persisted
    finalize_attendance's present-flag writes (see end_class /
    recompute_attendance) — never before, so award()'s own flush/rollback
    (it owns none of the caller's transaction boundary) can only ever touch
    already-durable state. Best-effort, per-row try/except so one bad award
    never blocks the rest; own commit per row kept minimal and isolated.
    Idempotent per (class, user) via the event_key, so recompute_attendance
    re-running this (e.g. after an instructor adjusts the threshold) never
    double-awards.
    """
    rows = (
        db.query(LiveClassAttendance)
        .filter(LiveClassAttendance.class_id == live_class.id, LiveClassAttendance.present == True)  # noqa: E712
        .all()
    )
    for row in rows:
        try:
            from app.services.gamification_service import award as _award_xp
            _award_xp(
                db, row.user_id, "live_class_attended",
                event_key=f"live_class:{live_class.id}:attended:user:{row.user_id}",
                course_id=live_class.course_id,
                meta={"live_class_id": live_class.id},
            )
            db.commit()
        except Exception as game_err:
            logger.warning("Gamification award failed for live class attendance: %s", game_err)
            try:
                db.rollback()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Scheduling CRUD helpers (Task 4) — LiveClassOut assembly, weekly
# recurrence date math, role-aware list/live-now scoping, ICS body building.
# Imported by app/routers/live_classes.py (kept out of the router to stay
# under the ~400-line-per-router budget).
# ---------------------------------------------------------------------------

def live_class_to_out(db: Session, live_class: LiveClass, user: User):
    """Build the LiveClassOut response shape for a LiveClass row, filling
    the derived/request-time fields (server_ts, my_attendance, can_start,
    join_opens_at). Shared by live_classes.py and live_class_session.py so
    every router hands the frontend an identical shape."""
    from app.schemas.live_class import LiveClassOut  # local import: avoid a
    # schemas<->service import cycle (schemas don't import services, but
    # keeping this import here mirrors the routers' own local-import style
    # for the same schema and costs nothing at call time).

    now = datetime.now(timezone.utc)
    join_opens_at = _as_utc(live_class.scheduled_start) - timedelta(minutes=STUDENT_JOIN_WINDOW_MINUTES)

    my_attendance = None
    att = (
        db.query(LiveClassAttendance)
        .filter(
            LiveClassAttendance.class_id == live_class.id,
            LiveClassAttendance.user_id == user.id,
        )
        .first()
    )
    if att is not None:
        my_attendance = {
            "first_joined_at": att.first_joined_at,
            "accumulated_seconds": att.accumulated_seconds,
            "present": att.present,
        }

    can_start = (
        is_assigned_instructor_or_admin(live_class, user)
        and live_class.status == LiveClassStatus.SCHEDULED
    )

    return LiveClassOut(
        id=live_class.id,
        schedule_id=live_class.schedule_id,
        course_id=live_class.course_id,
        lesson_id=live_class.lesson_id,
        instructor_id=live_class.instructor_id,
        title=live_class.title,
        description=live_class.description,
        # SQLite drops tzinfo on DateTime(timezone=True) round-trip
        # (Postgres preserves it) — the stored value is still UTC
        # wall-clock time, so re-attach UTC before it's serialized, or a
        # naive value would be misread as local time by any client that
        # calls .astimezone() on it.
        scheduled_start=_as_utc(live_class.scheduled_start),
        scheduled_end=_as_utc(live_class.scheduled_end),
        timezone=live_class.timezone,
        room_name=live_class.room_name,
        status=live_class.status.value,
        started_at=_as_utc(live_class.started_at) if live_class.started_at else None,
        ended_at=_as_utc(live_class.ended_at) if live_class.ended_at else None,
        live_participants=live_class.live_participants,
        recording_video_id=live_class.recording_video_id,
        recording_status=live_class.recording_status.value,
        settings=live_class.settings or {},
        purpose=getattr(live_class, "purpose", None), mode=getattr(live_class, "mode", None),
        audience=getattr(live_class, "audience", None), recording_policy=getattr(live_class, "recording_policy", None),
        retention_until=_as_utc(live_class.retention_until) if getattr(live_class, "retention_until", None) else None,
        recording_deleted_at=_as_utc(live_class.recording_deleted_at) if getattr(live_class, "recording_deleted_at", None) else None,
        lifecycle=_lifecycle(live_class),
        server_ts=now,
        my_attendance=my_attendance,
        can_start=can_start,
        join_opens_at=join_opens_at,
    )


def generate_occurrence_starts(
    first_start_local: datetime, weekday_codes: list[str], weeks: int, tz: ZoneInfo,
) -> list[datetime]:
    """Compute occurrence start datetimes (aware, in `tz`) for a weekly
    recurrence: exactly `weeks` copies of EACH weekday in `weekday_codes`
    (total `weeks * len(weekday_codes)` occurrences), all at the SAME local
    wall-clock time as `first_start_local`.

    Each occurrence is built directly from local calendar fields (year/month/
    day/hour/minute/second) re-localized via `tz` per occurrence — never by
    adding a fixed UTC offset — so DST transitions (irrelevant for
    Asia/Kolkata, which has none, but binding for any other zone) are
    handled correctly per occurrence.

    No occurrence is ever generated before `first_start_local`'s own date
    (controller ruling). Per weekday, the FIRST occurrence is the earliest
    date on/after `first_start_local`'s date that falls on that weekday
    (which may be later in the same calendar week, or push into the next
    one), and the remaining `weeks - 1` occurrences for that weekday step
    forward 7 days at a time from there — so every weekday always
    contributes exactly `weeks` occurrences, none of them backdated. E.g.
    `scheduled_start` on a Friday with `recurrence_weekly=["MO"]`,
    `weeks=3` yields the *following* three Mondays (not a Monday two days
    in the past plus only two more).
    """
    weekday_index = {code: i for i, code in enumerate(VALID_WEEKDAY_ORDER)}
    first_local = first_start_local.astimezone(tz)
    anchor_date = first_local.date()

    starts: list[datetime] = []
    for code in weekday_codes:
        days_ahead = (weekday_index[code] - anchor_date.weekday()) % 7
        first_occurrence_date = anchor_date + timedelta(days=days_ahead)
        for week in range(weeks):
            day = first_occurrence_date + timedelta(days=7 * week)
            occurrence_local = datetime(
                day.year, day.month, day.day,
                first_local.hour, first_local.minute, first_local.second,
                first_local.microsecond, tzinfo=tz,
            )
            starts.append(occurrence_local)
    starts.sort()
    return starts


def apply_scope_visibility(query, scope_value: str, current_user: User, db: Session):
    """Narrow `query` (a LiveClass query) by role-based visibility for the
    given scope. Raises HTTPException(403) for an explicit course:{id}
    scope the caller can't see any of, or 404/400 for a bad course scope.
    Returns the narrowed query.

    The `course:{id}` scope ALWAYS narrows the query to that course — this
    is a hard filter, not merely a permission gate — and every role
    (including admin) goes through it. Admin only bypasses the *role*
    filters below (own-instructor / enrolled-student); it must never bypass
    the course filter itself, or `scope=course:{id}` would silently widen
    into "every class in the system" for anyone who happens to pass the
    permission check on that one course.
    """
    from fastapi import HTTPException  # local import: keep FastAPI out of
    # this module's top-level imports (it's a plain service module used by
    # multiple routers, not itself a router).

    if scope_value.startswith("course:"):
        try:
            course_id = int(scope_value.split(":", 1)[1])
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid course scope")
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        permitted = (
            current_user.role in ADMIN_ROLES
            or course.post_author == current_user.id
            or db.query(Enrollment)
            .filter(
                Enrollment.course_id == course_id,
                Enrollment.user_id == current_user.id,
                Enrollment.enrollment_status == "enrolled",
            )
            .first() is not None
        )
        if not permitted:
            raise HTTPException(status_code=403, detail="You do not have access to this course")
        # Hard filter — applies to every role, admin included.
        return query.filter(LiveClass.course_id == course_id)

    if current_user.role in ADMIN_ROLES:
        return query

    if current_user.role == "instructor":
        return query.filter(LiveClass.instructor_id == current_user.id)

    # Student (or any other non-admin role): visible via enrollment only.
    enrolled_course_ids = [
        row[0]
        for row in db.query(Enrollment.course_id)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.enrollment_status == "enrolled",
        )
        .all()
    ]
    return query.filter(LiveClass.course_id.in_(enrolled_course_ids))


def ics_escape(text: str) -> str:
    """Escape a text value for an ICS TEXT property (RFC 5545 §3.3.11):
    backslash, comma, semicolon, and newline all need escaping."""
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _ics_datetime(dt: datetime) -> str:
    utc = _as_utc(dt).astimezone(timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%SZ")


ICS_FOLD_LIMIT_OCTETS = 75


def _ics_fold(line: str) -> str:
    """Fold one logical ICS content line into RFC 5545 §3.1 physical lines:
    no physical line may exceed 75 octets (UTF-8 bytes, NOT characters —
    a multi-byte character must never be split across the boundary), and
    each continuation line starts with a single space.

    Splits on byte boundaries by encoding to UTF-8, slicing at <=75 bytes
    per physical line (76 for the first, which additionally is not preceded
    by a folding space), and never cutting a multi-byte codepoint in half —
    if the 75th byte would land inside a multi-byte sequence, back off to
    the previous codepoint boundary so re-encoding stays valid UTF-8.
    """
    encoded = line.encode("utf-8")
    if len(encoded) <= ICS_FOLD_LIMIT_OCTETS:
        return line

    physical_lines: list[bytes] = []
    remaining = encoded
    first = True
    while remaining:
        # Continuation lines are prefixed with one space, which itself
        # counts toward the 75-octet limit, so they get one less byte of
        # payload than the first line.
        limit = ICS_FOLD_LIMIT_OCTETS if first else ICS_FOLD_LIMIT_OCTETS - 1
        if len(remaining) <= limit:
            chunk, remaining = remaining, b""
        else:
            cut = limit
            # Back off while `cut` would split a UTF-8 continuation byte
            # (0b10xxxxxx) away from its leading byte.
            while cut > 0 and (remaining[cut] & 0xC0) == 0x80:
                cut -= 1
            chunk, remaining = remaining[:cut], remaining[cut:]
        physical_lines.append(chunk)
        first = False

    return ("\r\n ".join(part.decode("utf-8") for part in physical_lines))


def build_ics(live_class: LiveClass) -> str:
    """Hand-rolled minimal VCALENDAR/VEVENT body (no external dependency —
    deviations file item 7). UID `liveclass-{id}@sashainfinity.com`;
    DTSTART/DTEND/DTSTAMP in UTC `...Z` form; SUMMARY/DESCRIPTION escaped
    and folded per RFC 5545 §3.1 (no physical line over 75 octets)."""
    dtstamp = _ics_datetime(datetime.now(timezone.utc))
    dtstart = _ics_datetime(live_class.scheduled_start)
    dtend = _ics_datetime(live_class.scheduled_end)
    summary = ics_escape(live_class.title)
    description = ics_escape(live_class.description or "")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SashaInfinity//Live Classes//EN",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:liveclass-{live_class.id}@sashainfinity.com",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    folded = [_ics_fold(line) for line in lines]
    return "\r\n".join(folded) + "\r\n"


# ---------------------------------------------------------------------------
# Polls (Task 5) — role-aware PollOut assembly. Kept here (rather than in
# app/routers/live_class_polls.py) to stay under the ~400-line-per-router
# budget; imported by the polls router as `_poll_to_out_impl`.
# ---------------------------------------------------------------------------

def poll_tallies(db: Session, poll: LiveClassPoll) -> list[int]:
    """Per-option vote counts for `poll`, in option order."""
    counts = [0] * len(poll.options)
    votes = (
        db.query(LiveClassPollVote.option_index)
        .filter(LiveClassPollVote.poll_id == poll.id)
        .all()
    )
    for (idx,) in votes:
        if 0 <= idx < len(counts):
            counts[idx] += 1
    return counts


def poll_to_out(db: Session, poll: LiveClassPoll, user: User):
    """Role-aware PollOut assembly: the assigned instructor/admin always
    gets tallies; a student gets their own vote plus tallies only when the
    poll's `show_results` flag is set."""
    from app.schemas.live_class import PollOut  # local import: mirrors
    # live_class_to_out's own local schema import above (avoid a
    # schemas<->service import cycle; schemas never import services).

    live_class = db.query(LiveClass).filter(LiveClass.id == poll.class_id).first()
    is_staff = live_class is not None and is_assigned_instructor_or_admin(live_class, user)

    my_vote = None
    vote_row = (
        db.query(LiveClassPollVote)
        .filter(LiveClassPollVote.poll_id == poll.id, LiveClassPollVote.user_id == user.id)
        .first()
    )
    if vote_row is not None:
        my_vote = vote_row.option_index

    tallies = None
    if is_staff or poll.show_results:
        tallies = poll_tallies(db, poll)

    return PollOut(
        id=poll.id,
        class_id=poll.class_id,
        question=poll.question,
        options=list(poll.options or []),
        status=poll.status.value,
        show_results=poll.show_results,
        created_at=poll.created_at,
        activated_at=poll.activated_at,
        closed_at=poll.closed_at,
        tallies=tallies,
        my_vote=my_vote,
    )


def reproject_poll_for_viewer(fresh_db: Session, class_id: int, poll_id: int, user_id: int) -> dict | None:
    """Re-render PollOut for a single viewer (`user_id`), from a fresh DB
    read, on a fresh session — the SSE stream's forwarding path for a
    received `poll_changed` notification (live_class_polls.poll_stream).
    Never forward another viewer's rendered payload: the published Redis
    event is role-neutral on purpose (see live_class_polls._publish_poll_
    changed's docstring) specifically so each subscriber re-projects
    independently here, from its own DB read, rather than the actor's.
    Returns None if the poll or the viewer's user has disappeared since
    subscribing.
    """
    fresh_poll = (
        fresh_db.query(LiveClassPoll)
        .filter(LiveClassPoll.id == poll_id, LiveClassPoll.class_id == class_id)
        .first()
    )
    fresh_user = fresh_db.query(User).filter(User.id == user_id).first()
    if fresh_poll is None or fresh_user is None:
        return None
    return poll_to_out(fresh_db, fresh_poll, fresh_user).model_dump(mode="json")


def _lifecycle(live_class: LiveClass) -> str:
    try:
        from app.services.class_report_service import lifecycle
        return lifecycle(live_class)
    except Exception:
        return live_class.status.value if live_class.status else "unknown"
