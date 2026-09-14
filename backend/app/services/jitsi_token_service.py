"""Mints short-lived, room-pinned Jitsi Meet JWTs.

See docs/superpowers/specs/2026-09-02-live-classes-brief.md ("Jitsi
integration", §6.2) for the authoritative claim shape. HS256 via PyJWT,
signed with the dedicated `settings.JITSI_JWT_SECRET` (never the platform
`JWT_SECRET` — see app/main.py's production fail-fast check).

The `room` claim pins the token to the exact class room so a leaked token
cannot be replayed into a different conference; `jti` gives every mint a
unique identity that live_class_service ties back to a
LiveClassJoinToken row for redemption/heartbeat bookkeeping.
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings
from app.models.live_class import LiveClass
from app.models.user import User

# Token validity = max(now + MIN_TOKEN_LIFETIME_MINUTES,
#                      scheduled_end + POST_CLASS_GRACE_MINUTES).
# The grace covers a class that runs slightly long; the now-floor covers a
# class ALREADY past its scheduled end, whose grace window has elapsed.
MIN_TOKEN_LIFETIME_MINUTES = 15
POST_CLASS_GRACE_MINUTES = 30


def token_expiry_for(live_class: LiveClass, now: datetime | None = None) -> datetime:
    """The `exp` a token minted for `live_class` right now would carry:
    `max(now + 15min, scheduled_end + 30min)`, as an aware UTC datetime.

    Exposed separately from `mint_jitsi_jwt` so the join-token endpoint can
    advertise a truthful `expires_in` without decoding the JWT it just
    signed, and so both numbers are computed by one piece of code that
    cannot drift.
    """
    now = now or datetime.now(timezone.utc)

    # SQLite drops tzinfo on round-trip even for DateTime(timezone=True)
    # columns (Postgres preserves it) — the value is still UTC wall-clock
    # time, so a naive datetime here means "UTC, tzinfo stripped", not
    # "local time". Re-attach UTC before doing epoch math so .timestamp()
    # doesn't apply the host's local offset.
    scheduled_end = live_class.scheduled_end
    if scheduled_end.tzinfo is None:
        scheduled_end = scheduled_end.replace(tzinfo=timezone.utc)

    # Floor the expiry at now+15min. `scheduled_end + 30min` alone mints an
    # ALREADY-EXPIRED token whenever a class runs past its slot — the exact
    # moment a late joiner or a reconnecting participant needs one. Jitsi
    # rejects such a token outright, so overtime classes became unjoinable
    # even for the instructor still in the room. The floor keeps every mint
    # usable for at least one join attempt without extending a normal
    # class's window: for a class ending in the future, `scheduled_end +
    # 30min` is already the later value and wins unchanged.
    return max(
        now + timedelta(minutes=MIN_TOKEN_LIFETIME_MINUTES),
        scheduled_end + timedelta(minutes=POST_CLASS_GRACE_MINUTES),
    )


def mint_jitsi_jwt(*, user: User, live_class: LiveClass, moderator: bool) -> tuple[str, str]:
    """Mint a room-pinned Jitsi JWT for `user` joining `live_class`.

    Returns (jwt, jti). Raises RuntimeError if JITSI_JWT_SECRET is blank —
    minting must never silently produce an unusable/insecure token.
    """
    settings = get_settings()
    secret = settings.JITSI_JWT_SECRET
    if not secret:
        raise RuntimeError(
            "JITSI_JWT_SECRET is not configured; cannot mint Jitsi tokens."
        )

    app_id = settings.JITSI_JWT_APP_ID
    jti = uuid.uuid4().hex
    now = datetime.now(timezone.utc)

    exp = token_expiry_for(live_class, now=now)

    claims = {
        "iss": app_id,
        "aud": app_id,
        "sub": app_id,
        "room": live_class.room_name,
        "jti": jti,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "context": {
            "user": {
                "id": str(user.id),
                "name": user.display_name,
                "email": user.user_email,
                "avatar": "",
                "moderator": "true" if moderator else "false",
            },
            "features": {
                "screen-sharing": "true" if moderator else "false",
                "recording": "true" if moderator else "false",
                "livestreaming": "false",
                "transcription": "false",
            },
        },
    }

    token = jwt.encode(claims, secret, algorithm="HS256")
    return token, jti
