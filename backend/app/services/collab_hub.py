"""Fan-out for coding pair rooms.

Each uvicorn worker keeps its own sockets. Frames from one socket reach the
sockets on other workers through a pub/sub channel per room. With Redis that
channel is real, so all workers see each other. Without Redis (tests, or a
single local process) an in-memory bus is used instead.

The server does not read or interpret Yjs updates. It relays opaque frames:
  byte 0 = 0 (incremental update) or 1 (full snapshot), then the Yjs bytes.
"""

from __future__ import annotations

import asyncio
import base64
from collections import defaultdict
from contextlib import asynccontextmanager
import json
import logging
from typing import AsyncIterator

from fastapi import WebSocket


logger = logging.getLogger(__name__)

MAX_FRAME_BYTES = 512 * 1024
KIND_UPDATE = 0
KIND_SNAPSHOT = 1


def channel_for(room_id: int) -> str:
    return f"coding:collab:{room_id}"


class InMemoryBus:
    """Same-process bus. Only correct with one worker."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, channel: str, message: str) -> None:
        for queue in list(self._subscribers.get(channel, ())):
            queue.put_nowait(message)

    @asynccontextmanager
    async def subscription(self, channel: str):
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[channel].add(queue)

        async def messages() -> AsyncIterator[str]:
            while True:
                yield await queue.get()

        try:
            yield messages()
        finally:
            self._subscribers[channel].discard(queue)


class RedisBus:
    """Cross-worker bus backed by Redis pub/sub."""

    def __init__(self, client) -> None:
        self._client = client

    async def publish(self, channel: str, message: str) -> None:
        await self._client.publish(channel, message)

    @asynccontextmanager
    async def subscription(self, channel: str):
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)

        async def messages() -> AsyncIterator[str]:
            async for item in pubsub.listen():
                if item.get("type") != "message":
                    continue
                data = item["data"]
                yield data.decode() if isinstance(data, bytes) else data

        try:
            yield messages()
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


class RoomHub:
    def __init__(self) -> None:
        self._sockets: dict[int, dict[str, WebSocket]] = {}
        self._pumps: dict[int, asyncio.Task] = {}

    async def connect(self, room_id: int, conn_id: str, websocket: WebSocket, bus) -> None:
        self._sockets.setdefault(room_id, {})[conn_id] = websocket
        if room_id not in self._pumps:
            ready = asyncio.Event()
            self._pumps[room_id] = asyncio.create_task(self._pump(room_id, bus, ready))
            # Wait until this worker is subscribed, so frames sent right after
            # connect are not missed.
            await ready.wait()

    async def disconnect(self, room_id: int, conn_id: str) -> None:
        sockets = self._sockets.get(room_id, {})
        sockets.pop(conn_id, None)
        if not sockets:
            self._sockets.pop(room_id, None)
            task = self._pumps.pop(room_id, None)
            if task is not None:
                task.cancel()

    async def publish(self, room_id: int, conn_id: str, frame: bytes, bus) -> None:
        envelope = json.dumps({"o": conn_id, "d": base64.b64encode(frame).decode()})
        await bus.publish(channel_for(room_id), envelope)

    async def _pump(self, room_id: int, bus, ready: asyncio.Event) -> None:
        try:
            async with bus.subscription(channel_for(room_id)) as messages:
                ready.set()
                async for raw in messages:
                    envelope = json.loads(raw)
                    origin = envelope["o"]
                    frame = base64.b64decode(envelope["d"])
                    for conn_id, websocket in list(self._sockets.get(room_id, {}).items()):
                        if conn_id == origin:
                            continue
                        try:
                            await websocket.send_bytes(frame)
                        except Exception:
                            self._sockets.get(room_id, {}).pop(conn_id, None)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("collab pump failed for room %s", room_id)
        finally:
            ready.set()


hub = RoomHub()
_memory_bus = InMemoryBus()


def bus_from_client(client):
    """Pick the bus for this process: Redis when available, otherwise in-memory."""
    from app.core.redis import MockRedis

    if client is None or isinstance(client, MockRedis):
        return _memory_bus
    return RedisBus(client)
