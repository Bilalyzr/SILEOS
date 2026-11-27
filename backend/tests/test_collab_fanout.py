"""Cross-worker fan-out for pair rooms, using two RoomHub instances as two workers.

Needs a reachable Redis (the app's REDIS_URL). Skips when Redis is not there.
"""

import asyncio
import uuid

import pytest

import redis.asyncio as redis_asyncio

from app.core.config import get_settings
from app.services.collab_hub import RedisBus, RoomHub


class FakeSocket:
    def __init__(self):
        self.frames: list[bytes] = []

    async def send_bytes(self, data: bytes) -> None:
        self.frames.append(data)


async def _redis_or_skip():
    # The test suite replaces the app's Redis singleton with MockRedis, so build
    # a real client from the configured URL here.
    client = redis_asyncio.from_url(get_settings().REDIS_URL, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        pytest.skip("Redis is not reachable from the test environment")
    return client


async def _wait_for(predicate, timeout=5.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.05)
    return False


def test_frames_cross_workers_through_redis():
    async def scenario():
        client = await _redis_or_skip()
        bus = RedisBus(client)
        worker_a, worker_b = RoomHub(), RoomHub()
        room_id = int(uuid.uuid4().int % 10**9)
        sender, listener = FakeSocket(), FakeSocket()
        sender_conn, listener_conn = uuid.uuid4().hex, uuid.uuid4().hex
        try:
            await worker_a.connect(room_id, sender_conn, sender, bus)
            await worker_b.connect(room_id, listener_conn, listener, bus)

            await worker_a.publish(room_id, sender_conn, bytes([0]) + b"edit-1", bus)
            await worker_b.publish(room_id, listener_conn, bytes([1]) + b"snap", bus)

            assert await _wait_for(lambda: listener.frames == [bytes([0]) + b"edit-1"])
            assert await _wait_for(lambda: sender.frames == [bytes([1]) + b"snap"])
            # Senders do not get their own frame back.
            assert len(listener.frames) == 1
            assert len(sender.frames) == 1
        finally:
            await worker_a.disconnect(room_id, sender_conn)
            await worker_b.disconnect(room_id, listener_conn)
            await client.aclose()

    asyncio.run(scenario())
