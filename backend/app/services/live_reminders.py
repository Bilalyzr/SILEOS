"""Live Classes reminder loop.

Deviations file item 5: no APScheduler — a dedicated asyncio loop in the
lifespan, mirroring app/services/reconciliation.py's `_run_cycle` pattern
exactly (dedicated advisory-lock connection held for the whole cycle,
separate from the work session; per-item fault isolation so one bad class
never blocks the rest of the pass; the loop itself never raises out).

Two responsibilities per cycle:
  (a) T-15min reminder: classes whose scheduled_start falls in
      [now, now+15min], status SCHEDULED **or LIVE** (an instructor who
      started the class a few minutes early must not skip the reminder —
      status alone doesn't mean the T-15 window has been serviced yet), and
      haven't already had a reminder sent — email every enrolled student +
      FCM broadcast + log event `reminder.sent`. Idempotency: Redis SETNX
      `live:reminder:{class_id}` (TTL 2h); when Redis is a MockRedis
      (tests/dev — its `expire()` is a documented no-op, same reasoning as
      live_class_session._is_usable_redis), fall back to checking whether a
      `reminder.sent` LiveClassEvent already exists for the class. The
      marker/event is per-class, not per-status, so an early start still
      sends the reminder exactly once.
  (b) go-live broadcast: classes currently LIVE that haven't already had a
      go-live marker set — log event `class.live_broadcast` + FCM. Same
      idempotency shape, marker key `live:golive:{class_id}`.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.redis import MockRedis, get_redis
from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassEvent, LiveClassStatus
from app.models.user import User
from app.services import live_class_service
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

REMINDER_LOOP_INTERVAL_SECONDS = 60
REMINDER_ADVISORY_LOCK_KEY = 931850
REMINDER_WINDOW_MINUTES = 15
REMINDER_MARKER_TTL_SECONDS = 2 * 60 * 60  # 2h


async def _is_usable_redis(client) -> bool:
    """Same reasoning as live_class_session._is_usable_redis: MockRedis's
    `expire()` is a documented no-op, so a SETNX-style marker against it
    would never expire — route it (and any unreachable real client) to the
    DB-backed idempotency fallback instead.

    Deliberately plain try/except, no `asyncio.wait_for` around the redis-py
    call: cancelling an in-flight connection-pool operation from the
    outside can leave the pool's internal asyncio.Lock held forever,
    deadlocking every subsequent call through the same shared client (see
    the equivalent note on live_class_polls._publish, where this was
    actually observed). A real client with no reachable broker is simply
    slower to fail here, never stuck.
    """
    if isinstance(client, MockRedis):
        return False
    try:
        await client.ping()
        return True
    except Exception:
        return False


async def _claim_marker(key: str) -> bool | None:
    """Best-effort SETNX-with-TTL idempotency marker. Returns True if this
    call won the claim, False if the marker already existed, or None if
    Redis is unusable (caller must fall back to a DB-backed check)."""
    client = await get_redis()
    if not await _is_usable_redis(client):
        return None
    try:
        won = await client.set(key, "1", nx=True, ex=REMINDER_MARKER_TTL_SECONDS)
        return bool(won)
    except TypeError:
        # Older client without nx/ex kwargs — degrade to the DB fallback.
        return None
    except Exception:
        logger.warning("Redis unavailable for reminder marker %s; falling back to DB check", key, exc_info=True)
        return None


def _reminder_already_sent(db: Session, class_id: int) -> bool:
    return (
        db.query(LiveClassEvent)
        .filter(LiveClassEvent.class_id == class_id, LiveClassEvent.event == "reminder.sent")
        .first()
        is not None
    )


def _golive_already_sent(db: Session, class_id: int) -> bool:
    return (
        db.query(LiveClassEvent)
        .filter(LiveClassEvent.class_id == class_id, LiveClassEvent.event == "class.live_broadcast")
        .first()
        is not None
    )


def _send_fcm_class_notification(live_class: LiveClass, kind: str) -> None:
    """Best-effort FCM broadcast through the existing backend helper.
    Guarded with try/except no-op — Firebase being unconfigured or failing
    must never break the reminder loop (deviations file item 12)."""
    try:
        from app.core import firebase_admin as firebase_admin_helper

        if not firebase_admin_helper._ensure_initialized():
            return
        from firebase_admin import messaging

        message = messaging.Message(
            topic="live-classes",
            data={
                "type": kind,
                "class_id": str(live_class.id),
                "title": live_class.title or "",
            },
        )
        messaging.send(message)
    except Exception:
        logger.warning("FCM broadcast failed for live class %s (%s)", live_class.id, kind, exc_info=True)


def _enrolled_student_emails(db: Session, course_id: int) -> list[str]:
    rows = (
        db.query(User.user_email)
        .join(Enrollment, Enrollment.user_id == User.id)
        .filter(Enrollment.course_id == course_id, Enrollment.enrollment_status == "enrolled")
        .all()
    )
    return [email for (email,) in rows if email]


async def _process_upcoming_reminder(db: Session, live_class: LiveClass) -> bool:
    """One class in the T-15min window. Returns True if a reminder was sent
    this cycle (for logging/metrics only — callers don't branch on it)."""
    marker_key = f"live:reminder:{live_class.id}"
    claimed = await _claim_marker(marker_key)

    if claimed is None:
        # Redis unusable — DB-backed idempotency fallback.
        if _reminder_already_sent(db, live_class.id):
            return False
    elif claimed is False:
        return False  # another cycle/replica already claimed it

    emails = _enrolled_student_emails(db, live_class.course_id)
    subject = f"Live class starting soon: {live_class.title}"
    body = (
        f"Your live class \"{live_class.title}\" starts at "
        f"{live_class_service._as_utc(live_class.scheduled_start).isoformat()}. "
        "Join from your dashboard."
    )
    # EmailService._send_or_mock opens a real blocking SMTP connection. Called
    # bare, it stalls the whole event loop once per recipient — and this loop
    # runs in the app's lifespan alongside every request handler, so a class
    # with a large roster (or a slow/hanging mail server) froze the API for
    # the length of the send. to_thread keeps each send off the loop; the
    # sends stay sequential, which is deliberate — the existing behaviour, and
    # it avoids opening N simultaneous SMTP connections to the same relay.
    for email in emails:
        try:
            await asyncio.to_thread(EmailService._send_or_mock, email, subject, body)
        except Exception:
            logger.warning("reminder email failed for %s (class %s)", email, live_class.id, exc_info=True)

    _send_fcm_class_notification(live_class, "class.reminder")

    live_class_service.log_event(
        db, live_class.id, None, "reminder.sent",
        payload={"recipient_count": len(emails)},
    )
    db.commit()
    return True


async def _process_golive_broadcast(db: Session, live_class: LiveClass) -> bool:
    marker_key = f"live:golive:{live_class.id}"
    claimed = await _claim_marker(marker_key)

    if claimed is None:
        if _golive_already_sent(db, live_class.id):
            return False
    elif claimed is False:
        return False

    _send_fcm_class_notification(live_class, "class.live_broadcast")

    live_class_service.log_event(db, live_class.id, None, "class.live_broadcast")
    db.commit()
    return True


_LAST_RETENTION_RUN = None


async def _run_reminder_pass(db: Session) -> None:
    """Per-class fault isolation, mirroring reconciliation.py's per-item
    isolation: one bad class must never block the rest of the pass."""
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=REMINDER_WINDOW_MINUTES)

    upcoming = (
        db.query(LiveClass)
        .filter(
            LiveClass.deleted_at.is_(None),
            # SCHEDULED or LIVE: an instructor who started the class a few
            # minutes early (still inside the T-15 window) must still get
            # the reminder sent to enrolled students — the per-class
            # marker/event below is what makes this idempotent, not status.
            LiveClass.status.in_([LiveClassStatus.SCHEDULED, LiveClassStatus.LIVE]),
            LiveClass.scheduled_start >= now,
            LiveClass.scheduled_start <= window_end,
        )
        .all()
    )
    for live_class in upcoming:
        try:
            await _process_upcoming_reminder(db, live_class)
        except Exception:
            db.rollback()
            logger.exception("reminder pass failed for class %s", live_class.id)

    live_now = (
        db.query(LiveClass)
        .filter(LiveClass.deleted_at.is_(None), LiveClass.status == LiveClassStatus.LIVE)
        .all()
    )
    for live_class in live_now:
        try:
            await _process_golive_broadcast(db, live_class)
        except Exception:
            db.rollback()
            logger.exception("go-live broadcast failed for class %s", live_class.id)

    # v2.0 §7.4 retention: expiry warnings (14/3 days) + hard purge (WP5).
    try:
        from app.services.class_report_service import retention_pass
        retention_pass(db, now)
    except Exception:
        db.rollback()
        logger.exception("retention pass failed")

    # Retention loop (roadmap item 3): at most every 6 hours — the rules are
    # idempotent through notification rows, this just bounds the scans.
    global _LAST_RETENTION_RUN
    if _LAST_RETENTION_RUN is None or (now - _LAST_RETENTION_RUN) >= timedelta(hours=6):
        try:
            from app.services.retention_service import retention_pass
            retention_pass(db, now)
            _LAST_RETENTION_RUN = now
        except Exception:
            db.rollback()
            logger.exception("retention pass failed")

    # R1 conversion funnel: abandoned-checkout reminders (once per user/course).
    try:
        from app.services.funnel_service import abandoned_checkout_pass
        abandoned_checkout_pass(db, now)
    except Exception:
        db.rollback()
        logger.exception("abandoned-checkout pass failed")


async def _run_cycle() -> None:
    """One asyncio-native sweep. Own session; advisory-locked on Postgres.

    Mirrors reconciliation.py's `_run_cycle` exactly: the pg advisory lock
    is session-level and therefore CONNECTION-scoped, so it must be held on
    a dedicated raw connection for the whole cycle, separate from the work
    session (which may commit mid-cycle and return its connection to the
    pool).
    """
    from app.core.database import SessionLocal, engine

    lock_conn = None
    if engine.dialect.name == "postgresql":
        lock_conn = engine.connect()
        try:
            locked = lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:k)"), {"k": REMINDER_ADVISORY_LOCK_KEY}
            ).scalar()
        except Exception:
            lock_conn.close()
            raise
        if not locked:
            lock_conn.close()
            return  # another replica holds the lock

    db = SessionLocal()
    try:
        await _run_reminder_pass(db)
    finally:
        db.close()
        if lock_conn is not None:
            try:
                lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:k)"), {"k": REMINDER_ADVISORY_LOCK_KEY}
                )
            finally:
                lock_conn.close()


async def live_reminders_loop() -> None:
    """Never raises out — a crashed cycle is logged and the loop continues
    on the next tick, exactly like reconciliation_loop."""
    while True:
        try:
            await _run_cycle()
        except Exception:
            logger.exception("live reminders cycle crashed (continuing)")
        await asyncio.sleep(REMINDER_LOOP_INTERVAL_SECONDS)
