"""Phase 5 (part B): pair coding rooms and their realtime document socket.

Mounted at /api/v1/utporul/coding (see app/main.py).

The socket accepts only binary frames, relays them to the other members
(across workers, via Redis), and keeps the latest snapshot. Frame format:
  byte 0 = 0 (incremental Yjs update) or 1 (full snapshot), then the bytes.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.coding_collab import RoomCreateIn, RoomJoinIn
from app.services import coding_collab_service as collab
from app.services.auth_service import AuthService
from app.services.collab_hub import KIND_SNAPSHOT, KIND_UPDATE, MAX_FRAME_BYTES, bus_from_client, hub


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/challenges/{slug}/collab-rooms", status_code=201)
def create_room(
    slug: str,
    command: RoomCreateIn,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return collab.create_room(db, slug, command, user)


@router.post("/collab-rooms/join")
def join_room(
    command: RoomJoinIn,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return collab.join_room(db, command.code, user)


@router.get("/collab-rooms/{room_id}")
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return collab.get_room(db, room_id, user)


@router.post("/collab-rooms/{room_id}/ticket")
async def room_ticket(
    room_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    client = await get_redis()
    return await collab.issue_ticket(client, db, room_id, user)


@router.websocket("/collab-rooms/{room_id}/ws")
async def room_socket(
    websocket: WebSocket,
    room_id: int,
    ticket: str = "",
    db: Session = Depends(get_db),
):
    client = await get_redis()
    user_id = await collab.redeem_ticket(client, ticket, room_id, db)
    # Release the pooled connection now; the socket can live for hours.
    db.close()
    if user_id is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    bus = bus_from_client(client)
    conn_id = uuid.uuid4().hex
    await hub.connect(room_id, conn_id, websocket, bus)
    try:
        snapshot = await collab.load_snapshot(client, room_id)
        if snapshot is not None:
            await websocket.send_bytes(bytes([KIND_SNAPSHOT]) + snapshot)
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            frame = message.get("bytes")
            if frame is None or len(frame) < 2 or len(frame) > MAX_FRAME_BYTES or frame[0] not in (KIND_UPDATE, KIND_SNAPSHOT):
                await websocket.close(code=1003)
                break
            if frame[0] == KIND_SNAPSHOT:
                await collab.store_snapshot(client, room_id, frame[1:])
            await hub.publish(room_id, conn_id, frame, bus)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("collab socket error in room %s", room_id)
    finally:
        await hub.disconnect(room_id, conn_id)
