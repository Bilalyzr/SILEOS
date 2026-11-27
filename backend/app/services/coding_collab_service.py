"""Phase 5 (part B): pair coding rooms.

- Any enrolled learner can open a room for a published challenge and share
  the invite code. Joining needs the code and enrolment in the same course.
  Codes are random, so rooms cannot be found by guessing ids.
- Members (up to 4) can open the shared editor. The WebSocket needs a
  single-use ticket issued to a member for that room (60 seconds).
- The latest full document snapshot is kept in Redis so a learner who joins
  later starts from the current text. Snapshots expire after 7 days.
"""

from __future__ import annotations

import base64
import json
import secrets

from fastapi import HTTPException

from app.models.coding_assessment import CodingChallenge
from app.models.coding_collab import CodingCollabMember, CodingCollabRoom
from app.models.user import User
from app.services import coding_assessment_service as coding


MAX_MEMBERS = 4
TICKET_SECONDS = 60
SNAPSHOT_SECONDS = 7 * 24 * 3600
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


def _snapshot_key(room_id: int) -> str:
    return f"coding:collab:snapshot:{room_id}"


def _ticket_key(token: str) -> str:
    return f"coding:collab:ticket:{token}"


def _members(db, room: CodingCollabRoom) -> list[CodingCollabMember]:
    return (
        db.query(CodingCollabMember)
        .filter(CodingCollabMember.room_id == room.id)
        .order_by(CodingCollabMember.id)
        .all()
    )


def _is_member(db, room: CodingCollabRoom, user_id: int) -> bool:
    return (
        db.query(CodingCollabMember.id)
        .filter(CodingCollabMember.room_id == room.id, CodingCollabMember.user_id == user_id)
        .first()
        is not None
    )


def _room_or_404(db, room_id: int, user) -> CodingCollabRoom:
    room = db.get(CodingCollabRoom, room_id)
    if room is None or not _is_member(db, room, user.id):
        raise HTTPException(404, "Pair room not found.")
    return room


def _room_out(db, room: CodingCollabRoom, user) -> dict:
    challenge = db.get(CodingChallenge, room.challenge_id)
    members = _members(db, room)
    names = dict(
        db.query(User.id, User.display_name)
        .filter(User.id.in_([m.user_id for m in members] or [-1]))
        .all()
    )
    return {
        "id": room.id,
        "challenge_slug": challenge.slug if challenge else "",
        "challenge_title": challenge.title if challenge else "",
        "language": room.language,
        "invite_code": room.invite_code,
        "is_owner": room.owner_id == user.id,
        "members": [
            {"user_id": m.user_id, "name": names.get(m.user_id, ""), "is_owner": m.user_id == room.owner_id}
            for m in members
        ],
        "max_members": MAX_MEMBERS,
    }


def create_room(db, slug: str, command, user) -> dict:
    challenge = coding._student_challenge(db, slug, user)
    languages = challenge.allowed_languages or []
    language = command.language or (languages[0] if languages else "python")
    if language not in languages:
        raise HTTPException(422, "This language is not enabled for the challenge.")
    room = CodingCollabRoom(
        challenge_id=challenge.id,
        owner_id=user.id,
        language=language,
        invite_code=secrets.token_urlsafe(12),
    )
    db.add(room)
    db.flush()
    db.add(CodingCollabMember(room_id=room.id, user_id=user.id))
    coding._save(db)
    db.refresh(room)
    return _room_out(db, room, user)


def join_room(db, code: str, user) -> dict:
    room = db.query(CodingCollabRoom).filter_by(invite_code=code.strip()).first()
    if room is None:
        raise HTTPException(404, "No pair room matches that code.")
    challenge = db.get(CodingChallenge, room.challenge_id)
    coding._student_challenge(db, challenge.slug, user)
    if not _is_member(db, room, user.id):
        if len(_members(db, room)) >= MAX_MEMBERS:
            raise HTTPException(409, "This pair room is full.")
        db.add(CodingCollabMember(room_id=room.id, user_id=user.id))
        coding._save(db)
    return _room_out(db, room, user)


def get_room(db, room_id: int, user) -> dict:
    return _room_out(db, _room_or_404(db, room_id, user), user)


async def issue_ticket(client, db, room_id: int, user) -> dict:
    room = _room_or_404(db, room_id, user)
    token = secrets.token_urlsafe(24)
    await client.setex(
        _ticket_key(token),
        TICKET_SECONDS,
        json.dumps({"user_id": user.id, "room_id": room.id}),
    )
    return {"ticket": token, "expires_in": TICKET_SECONDS}


async def redeem_ticket(client, token: str, room_id: int, db) -> int | None:
    """Single use: the ticket is removed as it is read. Returns the user id if valid."""
    if not token:
        return None
    key = _ticket_key(token)
    if hasattr(client, "getdel"):
        raw = await client.getdel(key)
    else:
        raw = await client.get(key)
        if raw is not None:
            await client.delete(key)
    if raw is None:
        return None
    data = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    if data.get("room_id") != room_id:
        return None
    room = db.get(CodingCollabRoom, room_id)
    if room is None or not _is_member(db, room, data["user_id"]):
        return None
    return int(data["user_id"])


async def load_snapshot(client, room_id: int) -> bytes | None:
    raw = await client.get(_snapshot_key(room_id))
    if raw is None:
        return None
    text = raw.decode() if isinstance(raw, bytes) else raw
    return base64.b64decode(text)


async def store_snapshot(client, room_id: int, data: bytes) -> None:
    if len(data) > MAX_SNAPSHOT_BYTES:
        return
    await client.setex(_snapshot_key(room_id), SNAPSHOT_SECONDS, base64.b64encode(data).decode())

