"""Live-class polls: create/activate/close/vote/list + SSE result stream.

Mounted at /api/v1/live (see app/main.py). Single-ACTIVE-poll-per-class
invariant: activating a poll auto-closes any other ACTIVE poll on the same
class (see `_activate`). Voting is participant-gated (must hold an
attendance row on the class AND pass user_can_access_class); duplicate votes
are rejected via the DB unique constraint (poll_id, user_id) caught as an
IntegrityError, not a pre-check — avoids a read-then-write race.

SSE (deviations file item 6): real Redis publishes/subscribes on channel
`live:class:{class_id}`; when Redis is a MockRedis (tests/dev, no broker),
the stream falls back to yielding exactly one snapshot event
`{"type": "poll", "poll": <PollOut dict>}` followed by keepalive comments
every 15s, honoring client disconnect.

Published Redis messages are deliberately role-neutral —
`{"type": "poll_changed", "poll_id": ...}` — never a rendered PollOut: a
PollOut is scoped to whoever triggered the change (instructor tallies, or
a voter's own my_vote/show_results-gated tallies), and broadcasting it
verbatim would leak live tallies to students on a show_results=False poll
and disclose every voter's ballot to every other subscriber. Each
subscriber re-projects the notification for itself
(`live_class_service.reproject_poll_for_viewer`, fresh DB read) before
forwarding to its own stream.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.database import SessionLocal, get_db
from app.core.redis import MockRedis, get_redis
from app.models.live_class import (
    LiveClass,
    LiveClassAttendance,
    LiveClassPoll,
    LiveClassPollVote,
    PollStatus,
)
from app.models.user import User
from app.schemas.live_class import PollCreate, PollOut, PollVoteIn
from app.services import live_class_service
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()

SSE_KEEPALIVE_SECONDS = 15


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_class_or_404(db: Session, class_id: int) -> LiveClass:
    lc = (
        db.query(LiveClass)
        .filter(LiveClass.id == class_id, LiveClass.deleted_at.is_(None))
        .first()
    )
    if not lc:
        raise HTTPException(status_code=404, detail="Live class not found")
    return lc


def _get_poll_or_404(db: Session, class_id: int, poll_id: int) -> LiveClassPoll:
    poll = (
        db.query(LiveClassPoll)
        .filter(LiveClassPoll.id == poll_id, LiveClassPoll.class_id == class_id)
        .first()
    )
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll


def _require_staff(live_class: LiveClass, user: User) -> None:
    if not live_class_service.is_assigned_instructor_or_admin(live_class, user):
        raise HTTPException(
            status_code=403,
            detail="Only the assigned instructor may manage polls for this class",
        )


def _is_staff(live_class: LiveClass, user: User) -> bool:
    return live_class_service.is_assigned_instructor_or_admin(live_class, user)


# Role-aware PollOut assembly (tallies/my_vote) lives in live_class_service.
_poll_to_out_impl = live_class_service.poll_to_out


async def _publish_poll_changed(class_id: int, poll_id: int) -> None:
    """Fire-and-forget publish to the class's poll channel: the role-neutral
    `{"type": "poll_changed", "poll_id": ...}` envelope only (see module
    docstring for why — never a rendered PollOut). Tolerates MockRedis
    (no-op) and any Redis unavailability — publishing must never fail the
    request that triggered it.

    No `asyncio.wait_for` around the redis-py call: externally cancelling
    an in-flight connection-pool operation can leave the pool's internal
    lock held forever, deadlocking every later call through the same
    shared client. Plain try/except (matching live_class_session.py) is
    slower per call against a dead broker but never corrupts pool state.
    """
    try:
        client = await get_redis()
        if isinstance(client, MockRedis):
            return
        payload = json.dumps({"type": "poll_changed", "poll_id": poll_id})
        await client.publish(f"live:class:{class_id}", payload)
    except Exception:
        logger.warning("poll publish failed for class %s", class_id, exc_info=True)


# ---------------------------------------------------------------------------
# POST /classes/{id}/polls — create (draft)
# ---------------------------------------------------------------------------

@router.post("/classes/{class_id}/polls", response_model=PollOut, status_code=201)
async def create_poll(
    class_id: int,
    payload: PollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    _require_staff(live_class, current_user)

    cleaned_options = [opt.strip() for opt in payload.options]
    if any(not opt for opt in cleaned_options):
        raise HTTPException(status_code=422, detail="Poll options must be non-empty strings")
    if len(cleaned_options) < 2 or len(cleaned_options) > 10:
        raise HTTPException(status_code=422, detail="Poll must have between 2 and 10 options")

    poll = LiveClassPoll(
        class_id=live_class.id,
        created_by=current_user.id,
        question=payload.question,
        options=cleaned_options,
        status=PollStatus.DRAFT,
        show_results=payload.show_results,
    )
    db.add(poll)
    db.flush()
    live_class_service.log_event(db, live_class.id, current_user.id, "poll.created", payload={"poll_id": poll.id})
    db.commit()
    db.refresh(poll)

    return _poll_to_out_impl(db, poll, current_user)


# ---------------------------------------------------------------------------
# POST /classes/{id}/polls/{pid}/activate
# ---------------------------------------------------------------------------

@router.post("/classes/{class_id}/polls/{poll_id}/activate", response_model=PollOut)
async def activate_poll(
    class_id: int,
    poll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    _require_staff(live_class, current_user)
    poll = _get_poll_or_404(db, class_id, poll_id)

    if poll.status == PollStatus.CLOSED:
        raise HTTPException(status_code=409, detail="Cannot activate a closed poll")

    now = datetime.now(timezone.utc)

    # Single-ACTIVE-poll-per-class invariant: auto-close any other ACTIVE
    # poll on this class before activating this one.
    others = (
        db.query(LiveClassPoll)
        .filter(
            LiveClassPoll.class_id == class_id,
            LiveClassPoll.status == PollStatus.ACTIVE,
            LiveClassPoll.id != poll.id,
        )
        .all()
    )
    for other in others:
        other.status = PollStatus.CLOSED
        other.closed_at = now
        live_class_service.log_event(db, class_id, current_user.id, "poll.closed", payload={"poll_id": other.id})

    poll.status = PollStatus.ACTIVE
    poll.activated_at = now
    live_class_service.log_event(db, class_id, current_user.id, "poll.activated", payload={"poll_id": poll.id})
    db.commit()
    db.refresh(poll)

    out = _poll_to_out_impl(db, poll, current_user)
    await _publish_poll_changed(class_id, poll.id)
    return out


# ---------------------------------------------------------------------------
# POST /classes/{id}/polls/{pid}/close
# ---------------------------------------------------------------------------

@router.post("/classes/{class_id}/polls/{poll_id}/close", response_model=PollOut)
async def close_poll(
    class_id: int,
    poll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    _require_staff(live_class, current_user)
    poll = _get_poll_or_404(db, class_id, poll_id)

    if poll.status != PollStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Only an active poll can be closed")

    poll.status = PollStatus.CLOSED
    poll.closed_at = datetime.now(timezone.utc)
    live_class_service.log_event(db, class_id, current_user.id, "poll.closed", payload={"poll_id": poll.id})
    db.commit()
    db.refresh(poll)

    out = _poll_to_out_impl(db, poll, current_user)
    await _publish_poll_changed(class_id, poll.id)
    return out


# ---------------------------------------------------------------------------
# POST /classes/{id}/polls/{pid}/vote
# ---------------------------------------------------------------------------

@router.post("/classes/{class_id}/polls/{poll_id}/vote", response_model=PollOut)
async def vote_poll(
    class_id: int,
    poll_id: int,
    payload: PollVoteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    if not live_class_service.user_can_access_class(db, live_class, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this class")

    attendance = (
        db.query(LiveClassAttendance)
        .filter(
            LiveClassAttendance.class_id == class_id,
            LiveClassAttendance.user_id == current_user.id,
        )
        .first()
    )
    if attendance is None:
        raise HTTPException(status_code=403, detail="You must join this class before voting")

    poll = _get_poll_or_404(db, class_id, poll_id)
    if poll.status != PollStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="This poll is not currently active")

    if payload.option_index < 0 or payload.option_index >= len(poll.options or []):
        raise HTTPException(status_code=422, detail="option_index is out of range for this poll")

    vote = LiveClassPollVote(poll_id=poll.id, user_id=current_user.id, option_index=payload.option_index)
    db.add(vote)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already voted on this poll")

    live_class_service.log_event(
        db, class_id, current_user.id, "poll.voted",
        payload={"poll_id": poll.id, "option_index": payload.option_index},
    )
    db.commit()
    db.refresh(poll)

    out = _poll_to_out_impl(db, poll, current_user)
    await _publish_poll_changed(class_id, poll.id)
    return out


# ---------------------------------------------------------------------------
# GET /classes/{id}/polls — role-aware list
# ---------------------------------------------------------------------------

@router.get("/classes/{class_id}/polls", response_model=list[PollOut])
async def list_polls(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    if not live_class_service.user_can_access_class(db, live_class, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this class")

    if _is_staff(live_class, current_user):
        polls = (
            db.query(LiveClassPoll)
            .filter(LiveClassPoll.class_id == class_id)
            .order_by(LiveClassPoll.created_at.desc())
            .all()
        )
        return [_poll_to_out_impl(db, p, current_user) for p in polls]

    # Student: only the currently ACTIVE poll (if any), plus their own vote
    # and tallies iff show_results.
    active = (
        db.query(LiveClassPoll)
        .filter(LiveClassPoll.class_id == class_id, LiveClassPoll.status == PollStatus.ACTIVE)
        .order_by(LiveClassPoll.activated_at.desc())
        .first()
    )
    if active is None:
        return []
    return [_poll_to_out_impl(db, active, current_user)]


# ---------------------------------------------------------------------------
# GET /classes/{id}/polls/{pid}/stream — SSE
# ---------------------------------------------------------------------------

# Per-viewer re-projection for a received poll_changed notification — lives
# in live_class_service (with poll_to_out/poll_tallies) to stay under budget.
reproject_poll_for_viewer = live_class_service.reproject_poll_for_viewer


@router.get("/classes/{class_id}/polls/{poll_id}/stream")
async def poll_stream(
    class_id: int,
    poll_id: int,
    _request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    if not live_class_service.user_can_access_class(db, live_class, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this class")
    poll = _get_poll_or_404(db, class_id, poll_id)

    snapshot = _poll_to_out_impl(db, poll, current_user).model_dump(mode="json")
    channel = f"live:class:{class_id}"
    user_id = current_user.id

    async def _event_generator():
        client = await get_redis()
        # Mirrors live_class_session._is_usable_redis: MockRedis is never
        # usable, and a real client with no reachable broker (dev/tests
        # without Redis running) must degrade the same way rather than hang
        # or raise mid-stream.
        usable_redis = False
        if not isinstance(client, MockRedis):
            try:
                await client.ping()
                usable_redis = True
            except Exception:
                usable_redis = False

        # NOTE: no `request.is_disconnected()` polling here — sse-starlette
        # races this generator against its own disconnect listener and
        # cancels it on client disconnect; a second concurrent read of the
        # same ASGI receive channel here can deadlock the connection.
        if usable_redis:
            pubsub = None
            try:
                pubsub = client.pubsub()
                await pubsub.subscribe(channel)
                # Always hand the subscriber a starting snapshot — a client
                # that connects between publishes should not sit with no
                # data until the next poll event fires.
                yield {"event": "message", "data": json.dumps({"type": "poll", "poll": snapshot})}
                while True:
                    try:
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=SSE_KEEPALIVE_SECONDS)
                    except Exception:
                        logger.warning("SSE pubsub read failed for class %s", class_id, exc_info=True)
                        break
                    if message is not None and message.get("type") == "message":
                        # Role-neutral {"type": "poll_changed", "poll_id": ...}
                        # (see _publish_poll_changed) — re-project for THIS
                        # subscriber on a fresh session (the request-scoped
                        # `db` may already be closed by the time this fires).
                        try:
                            raw = json.loads(message["data"])
                        except (TypeError, ValueError):
                            continue
                        if raw.get("type") != "poll_changed" or raw.get("poll_id") != poll_id:
                            continue
                        fresh_db = SessionLocal()
                        try:
                            projected = reproject_poll_for_viewer(fresh_db, class_id, poll_id, user_id)
                        finally:
                            fresh_db.close()
                        if projected is None:
                            continue
                        yield {"event": "message", "data": json.dumps({"type": "poll", "poll": projected})}
                    else:
                        yield {"comment": "keepalive"}
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.unsubscribe(channel)
                        await pubsub.close()
                    except Exception:
                        pass
        else:
            # MockRedis / unusable broker fallback (deviations file item 6):
            # yield exactly one snapshot event, then keepalive comments every
            # 15s until sse-starlette cancels this generator on disconnect.
            # Already per-viewer (built above from the request-scoped `db`
            # and `current_user` before this generator started) — no
            # re-projection needed since there is no broadcast channel here.
            yield {"event": "message", "data": json.dumps({"type": "poll", "poll": snapshot})}
            while True:
                await asyncio.sleep(SSE_KEEPALIVE_SECONDS)
                yield {"comment": "keepalive"}

    return EventSourceResponse(_event_generator())
