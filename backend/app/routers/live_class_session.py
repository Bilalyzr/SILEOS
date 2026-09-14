"""Live-class session lifecycle: start / end / join-token / heartbeat.

Mounted at /api/v1/live (see app/main.py) alongside the scheduling, polls,
attendance, and recordings routers from later tasks — all share the one
prefix per the plan's Global Constraints.

This is the security core of the feature: join-token issuance is the only
place a Jitsi JWT gets minted for a human, and every mint is gated by
live_class_service.user_can_access_class (instructor / admin / enrolled
student) plus a join-window rule for students (T-15min).
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.core.redis import MockRedis, get_redis
from app.models.live_class import (
    LiveClass,
    LiveClassAttendance,
    LiveClassJoinToken,
    LiveClassStatus,
    RecordingStatus,
)
from app.models.user import User
from app.schemas.live_class import HeartbeatIn, HeartbeatOut, JoinTokenOut, LiveClassOut
from app.services import live_class_service
from app.services.auth_service import AuthService
from app.services import jitsi_token_service
from app.services.jitsi_token_service import mint_jitsi_jwt

logger = logging.getLogger(__name__)
router = APIRouter()

JOIN_TOKEN_RATE_LIMIT = 5          # per user, per 60s window
JOIN_TOKEN_RATE_WINDOW = 60
STUDENT_JOIN_WINDOW_MINUTES = 15
START_LOCK_TTL_SECONDS = 15


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Shared with live_class_service so router and service math never drift.
_as_utc = live_class_service._as_utc


def _get_class_or_404(db: Session, class_id: int) -> LiveClass:
    # deleted_at must gate independently of status: a soft-cancelled/deleted
    # class must 404 even if some stale row still reads LIVE/SCHEDULED.
    lc = (
        db.query(LiveClass)
        .filter(LiveClass.id == class_id, LiveClass.deleted_at.is_(None))
        .first()
    )
    if not lc:
        raise HTTPException(status_code=404, detail="Live class not found")
    return lc


# Shared with live_class_service (and live_classes.py) so every router hands
# the frontend an identical LiveClassOut shape — a duplicate _to_out here
# previously drifted from live_class_service.live_class_to_out (it emitted
# naive datetimes with no re-attached UTC tzinfo, unlike the shared
# version), producing a 5h30m discrepancy on IST clients between this
# router's responses and live_classes.py's. Deleted; call the shared
# functions directly.
_is_assigned_instructor_or_admin = live_class_service.is_assigned_instructor_or_admin
_to_out = live_class_service.live_class_to_out


async def _is_usable_redis(client) -> bool:
    """True if `client` is a real, reachable Redis connection.

    MockRedis is deliberately treated as NOT usable here, even though it
    won't raise: its `expire()` is a documented no-op (see
    app/core/redis.py), so a rate-limit counter incremented against it would
    never reset and would permanently lock a user out of join-token after
    their 5th call in dev/tests. The DB-count fallback windows correctly
    (it filters on `issued_at >= window_start`), so MockRedis must route
    there instead of through the (silently broken) INCR+EXPIRE path.

    A real client that's simply unreachable (dev/test boxes without a
    broker running) degrades the same way, for the same reason: better a
    correct DB-backed fallback than a rate limiter that raises or misbehaves.
    """
    if isinstance(client, MockRedis):
        return False
    try:
        await client.ping()
        return True
    except Exception:
        return False


async def _redis_incr_with_expiry(key: str, window: int) -> int | None:
    """INCR a counter key, setting its expiry only on the first increment
    (mirrors the classic fixed-window rate-limit recipe). Returns None if
    Redis is unavailable so the caller can fall back to the DB-count path —
    never raises out of the request."""
    client = await get_redis()
    if not await _is_usable_redis(client):
        return None
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window)
        return count
    except Exception:
        logger.warning("Redis unavailable for join-token rate limit; falling back to DB count", exc_info=True)
        return None


async def _acquire_start_lock(class_id: int) -> bool:
    """Best-effort idempotency lock for POST /start. Returns True if the
    caller won the lock (or Redis is unavailable/mocked — the router's own
    already-LIVE check under the DB is the authoritative idempotency guard
    in that case)."""
    client = await get_redis()
    if not await _is_usable_redis(client):
        # No atomic NX support (mock) or no broker reachable — tolerate and
        # fall through to the DB-level idempotency check in the endpoint.
        return True
    key = f"live:class:{class_id}:startlock"
    try:
        won = await client.set(key, "1", nx=True, ex=START_LOCK_TTL_SECONDS)
        return bool(won)
    except TypeError:
        # Older client without nx/ex kwargs — degrade the same way as mock.
        return True
    except Exception:
        logger.warning("Redis unavailable for start lock; falling back to DB check", exc_info=True)
        return True


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------

@router.post("/classes/{class_id}/start", response_model=LiveClassOut)
async def start_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    if not _is_assigned_instructor_or_admin(live_class, current_user):
        raise HTTPException(status_code=403, detail="Only the assigned instructor may start this class")

    if live_class.status == LiveClassStatus.LIVE:
        # Idempotent: a second Start click (double-tap, stale tab) returns
        # the current state without logging a duplicate event.
        return _to_out(db, live_class, current_user)

    if live_class.status != LiveClassStatus.SCHEDULED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot start a class in status {live_class.status.value}",
        )

    acquired = await _acquire_start_lock(class_id)

    # Re-check under the DB after the (best-effort) lock — this is the
    # authoritative idempotency guard when Redis is a MockRedis.
    db.refresh(live_class)
    if live_class.status == LiveClassStatus.LIVE:
        return _to_out(db, live_class, current_user)

    if not acquired:
        # A concurrent /start holds the lock. It may not have committed yet,
        # so the refresh above can still read SCHEDULED — proceeding here is
        # exactly the double-start the lock exists to prevent (two
        # `class.started` events, two started_at writes). Return the current
        # state instead: the winner's commit lands within the lock's 15s TTL
        # and the client's next poll sees LIVE. Whoever loses the race gets
        # the same shape as the plain-idempotent path above, no error.
        logger.info(
            "start lock held by a concurrent request for class %s; returning current state",
            class_id,
        )
        return _to_out(db, live_class, current_user)

    live_class.status = LiveClassStatus.LIVE
    live_class.started_at = datetime.now(timezone.utc)
    live_class_service.log_event(db, live_class.id, current_user.id, "class.started")
    db.commit()
    db.refresh(live_class)
    return _to_out(db, live_class, current_user)


@router.post("/classes/{class_id}/end", response_model=LiveClassOut)
async def end_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    if not _is_assigned_instructor_or_admin(live_class, current_user):
        raise HTTPException(status_code=403, detail="Only the assigned instructor may end this class")

    if live_class.status != LiveClassStatus.LIVE:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot end a class in status {live_class.status.value}",
        )

    live_class.status = LiveClassStatus.ENDED
    live_class.ended_at = datetime.now(timezone.utc)

    live_class_service.finalize_attendance(db, live_class)

    # v2.0 §7.3 permanent report + §7.4 retention clock (WP5) — same transaction as the status flip.
    from app.services import class_report_service
    class_report_service.generate_report(db, live_class)
    class_report_service.set_retention_on_end(live_class)

    if (live_class.settings or {}).get("record") and live_class.recording_status == RecordingStatus.REQUESTED:
        live_class.recording_status = RecordingStatus.PROCESSING

    live_class_service.log_event(db, live_class.id, current_user.id, "class.ended")
    db.commit()
    db.refresh(live_class)

    # Gamification: sequenced AFTER the commit above so award()'s own
    # flush/rollback can never touch this request's just-persisted
    # attendance present-flags (H1 review fix).
    live_class_service.award_attendance_xp(db, live_class)

    return _to_out(db, live_class, current_user)


@router.post("/classes/{class_id}/join-token", response_model=JoinTokenOut)
async def join_token(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)

    if not live_class_service.user_can_access_class(db, live_class, current_user):
        live_class_service.log_event(db, live_class.id, current_user.id, "join.denied")
        db.commit()
        raise HTTPException(status_code=403, detail="You do not have access to this class")

    if live_class.status in (LiveClassStatus.ENDED, LiveClassStatus.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail=f"This class is {live_class.status.value} and can no longer be joined",
        )

    is_staff = _is_assigned_instructor_or_admin(live_class, current_user)
    if not is_staff and live_class.status == LiveClassStatus.SCHEDULED:
        join_opens_at = _as_utc(live_class.scheduled_start) - timedelta(minutes=STUDENT_JOIN_WINDOW_MINUTES)
        now = datetime.now(timezone.utc)
        if now < join_opens_at:
            raise HTTPException(
                status_code=409,
                detail=f"Join opens at {join_opens_at.isoformat()}",
            )

    # Rate limit: 5/min/user. Prefer Redis INCR+EXPIRE; when Redis is
    # unavailable (MockRedis in tests/dev, or a real client with no broker
    # reachable), fall back to counting LiveClassJoinToken rows issued by
    # this user in the last window.
    rl_key = f"rl:join-token:{current_user.id}"
    count = await _redis_incr_with_expiry(rl_key, JOIN_TOKEN_RATE_WINDOW)
    if count is None:
        window_start = datetime.now(timezone.utc) - timedelta(seconds=JOIN_TOKEN_RATE_WINDOW)
        count = 1 + (
            db.query(LiveClassJoinToken)
            .filter(
                LiveClassJoinToken.user_id == current_user.id,
                LiveClassJoinToken.issued_at >= window_start,
            )
            .count()
        )
    if count > JOIN_TOKEN_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many join-token requests; try again shortly")

    moderator = is_staff
    token, jti = mint_jitsi_jwt(user=current_user, live_class=live_class, moderator=moderator)

    # Advertise the token's ACTUAL lifetime, not a hardcoded 900s. The minted
    # exp is max(now+15min, scheduled_end+30min), which for any class not
    # already near its end is far longer than 900s — a client that believed
    # 900 would pointlessly re-request a token (burning its 5/min rate-limit
    # budget) while the one it holds is still perfectly valid. Both numbers
    # come from jitsi_token_service.token_expiry_for so they cannot drift.
    expires_at = jitsi_token_service.token_expiry_for(live_class)
    expires_in = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    db.add(LiveClassJoinToken(
        class_id=live_class.id,
        user_id=current_user.id,
        jti=jti,
        moderator=moderator,
        expires_at=expires_at,
    ))

    attendance = (
        db.query(LiveClassAttendance)
        .filter(
            LiveClassAttendance.class_id == live_class.id,
            LiveClassAttendance.user_id == current_user.id,
        )
        .first()
    )
    if attendance is None:
        attendance = LiveClassAttendance(class_id=live_class.id, user_id=current_user.id)
        db.add(attendance)

    live_class_service.log_event(
        db, live_class.id, current_user.id, "join.token_issued",
        payload={"moderator": moderator},
    )
    db.commit()
    db.refresh(live_class)

    settings = get_settings()
    return JoinTokenOut(
        class_summary=_to_out(db, live_class, current_user),
        room_name=live_class.room_name,
        jitsi_url=settings.JITSI_PUBLIC_URL,
        jwt=token,
        expires_in=expires_in,
    )


@router.post("/classes/{class_id}/heartbeat", response_model=HeartbeatOut)
async def heartbeat(
    class_id: int,
    payload: HeartbeatIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)

    if live_class.status in (LiveClassStatus.ENDED, LiveClassStatus.CANCELLED):
        raise HTTPException(status_code=409, detail="This class has ended")

    # Re-check access on every heartbeat, not just at join-token time — a
    # student unenrolled mid-class (or an instructor reassigned off it) must
    # stop accruing attendance immediately rather than keep beating through
    # a still-open attendance row.
    if not live_class_service.user_can_access_class(db, live_class, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this class")

    attendance = (
        db.query(LiveClassAttendance)
        .filter(
            LiveClassAttendance.class_id == live_class.id,
            LiveClassAttendance.user_id == current_user.id,
        )
        .first()
    )
    if attendance is None:
        raise HTTPException(status_code=403, detail="No active join for this class")

    was_first_beat = attendance.last_heartbeat_at is None
    now = datetime.now(timezone.utc)
    delta = live_class_service.apply_heartbeat(db, attendance, now)

    if was_first_beat:
        # Mark the join token(s) for this user on this class redeemed on
        # the very first heartbeat — this is when we know the client
        # actually connected to the room, not just that a token was minted.
        token_row = (
            db.query(LiveClassJoinToken)
            .filter(
                LiveClassJoinToken.class_id == live_class.id,
                LiveClassJoinToken.user_id == current_user.id,
                LiveClassJoinToken.redeemed_at.is_(None),
            )
            .order_by(LiveClassJoinToken.issued_at.desc())
            .first()
        )
        if token_row is not None:
            token_row.redeemed_at = now
        live_class_service.log_event(db, live_class.id, current_user.id, "join.redeemed")

    db.commit()
    return {"accumulated_seconds": attendance.accumulated_seconds, "delta": delta}
