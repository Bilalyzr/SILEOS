"""Polls router: create/activate/close/vote/list + SSE stream.

Covers: lifecycle draft->active->closed, second activation auto-closes the
first, duplicate vote 409, out-of-range option rejected, student list hides
tallies when show_results is false, and the SSE endpoint's content-type +
first snapshot frame shape.
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassPoll, LiveClassStatus, PollStatus


@pytest.fixture()
def instructor_user(db):
    from app.models.user import User

    u = User(
        user_login="poll_instructor", user_pass="x", user_nicename="poll_instructor",
        user_email="poll_instructor@example.com", display_name="Poll Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def live_course(db, instructor_user):
    from app.models.course import Course

    c = Course(post_author=instructor_user.id, post_title="Poll Course",
               course_price_type="free", course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _enroll(db, student, course):
    e = Enrollment(course_id=course.id, user_id=student.id, enrollment_status="enrolled")
    db.add(e)
    db.commit()
    return e


def _make_class(db, course, instructor, room_name, status=LiveClassStatus.LIVE, **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Poll Test Class",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(minutes=95),
        room_name=room_name,
        status=status,
        settings={
            "lobby_enabled": True, "start_muted": True, "allow_chat": True,
            "allow_share": True, "record": False, "attendance_threshold_pct": 60,
        },
    )
    defaults.update(overrides)
    lc = LiveClass(**defaults)
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


def _give_attendance(db, lc, user):
    db.add(LiveClassAttendance(class_id=lc.id, user_id=user.id))
    db.commit()


class TestPollLifecycle:
    def test_create_activate_close(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-poll0001")
        as_user(instructor_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Favorite color?", "options": ["Red", "Blue"], "show_results": True,
        })
        assert r.status_code == 201, r.text
        poll = r.json()
        assert poll["status"] == "draft"

        r = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/activate")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "active"

        r = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/close")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "closed"

    def test_second_activation_closes_first(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-poll0002")
        as_user(instructor_user)

        r1 = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q1", "options": ["A", "B"],
        })
        poll1 = r1.json()
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll1['id']}/activate")

        r2 = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q2", "options": ["C", "D"],
        })
        poll2 = r2.json()
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll2['id']}/activate")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "active"

        poll1_row = db.query(LiveClassPoll).filter_by(id=poll1["id"]).one()
        assert poll1_row.status == PollStatus.CLOSED

    def test_create_rejects_invalid_options(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-poll0003")
        as_user(instructor_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q", "options": ["only one"],
        })
        assert r.status_code == 422

    def test_non_staff_cannot_create(self, client, db, as_user, student_user, live_course, instructor_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0004")
        _enroll(db, student_user, live_course)
        as_user(student_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q", "options": ["A", "B"],
        })
        assert r.status_code == 403


class TestPollVoting:
    def _active_poll(self, client, as_user, instructor_user, lc):
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q", "options": ["A", "B", "C"],
        })
        poll = r.json()
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/activate")
        return poll

    def test_vote_happy_path(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0005")
        _enroll(db, student_user, live_course)
        poll = self._active_poll(client, as_user, instructor_user, lc)
        _give_attendance(db, lc, student_user)

        as_user(student_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 1})
        assert r.status_code == 200, r.text
        assert r.json()["my_vote"] == 1

    def test_duplicate_vote_409(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0006")
        _enroll(db, student_user, live_course)
        poll = self._active_poll(client, as_user, instructor_user, lc)
        _give_attendance(db, lc, student_user)

        as_user(student_user)
        r1 = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 0})
        assert r1.status_code == 200, r1.text
        r2 = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 1})
        assert r2.status_code == 409

    def test_out_of_range_option_rejected(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0007")
        _enroll(db, student_user, live_course)
        poll = self._active_poll(client, as_user, instructor_user, lc)
        _give_attendance(db, lc, student_user)

        as_user(student_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 99})
        assert r.status_code in (400, 422)

    def test_vote_without_attendance_row_403(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0008")
        _enroll(db, student_user, live_course)
        poll = self._active_poll(client, as_user, instructor_user, lc)

        as_user(student_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 0})
        assert r.status_code == 403

    def test_vote_on_non_active_poll_409(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0009")
        _enroll(db, student_user, live_course)
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q", "options": ["A", "B"],
        })
        poll = r.json()  # still DRAFT
        _give_attendance(db, lc, student_user)

        as_user(student_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 0})
        assert r.status_code == 409


class TestPollListRoleAware:
    def test_instructor_sees_all_with_tallies(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0010")
        _enroll(db, student_user, live_course)
        poll = self._make_active_with_vote(client, db, as_user, instructor_user, live_course, student_user, lc)

        as_user(instructor_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/polls")
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body) == 1
        assert body[0]["tallies"] is not None
        assert sum(body[0]["tallies"]) == 1

    def test_student_hides_tallies_when_show_results_false(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0011")
        _enroll(db, student_user, live_course)
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q", "options": ["A", "B"], "show_results": False,
        })
        poll = r.json()
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/activate")
        _give_attendance(db, lc, student_user)

        as_user(student_user)
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 0})

        r = client.get(f"/api/v1/live/classes/{lc.id}/polls")
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body) == 1
        assert body[0]["tallies"] is None
        assert body[0]["my_vote"] == 0

    def test_student_sees_tallies_when_show_results_true(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0012")
        _enroll(db, student_user, live_course)
        poll = self._make_active_with_vote(client, db, as_user, instructor_user, live_course, student_user, lc)

        as_user(student_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/polls")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body[0]["tallies"] is not None

    def _make_active_with_vote(self, client, db, as_user, instructor_user, live_course, student_user, lc):
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q", "options": ["A", "B"], "show_results": True,
        })
        poll = r.json()
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/activate")
        _give_attendance(db, lc, student_user)
        as_user(student_user)
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 0})
        return poll


class TestPollStreamSSE:
    def test_sse_content_type_and_snapshot_frame(self, client, db, as_user, instructor_user, live_course, student_user):
        """Neither Starlette's TestClient.stream() nor httpx.ASGITransport
        actually stream incrementally in this environment — both fully
        drain the ASGI app coroutine to completion before handing back a
        response (verified directly: `handle_request`/`handle_async_request`
        both `await self.app(...)` in full before returning). Since this
        SSE endpoint's generator only ever terminates when sse-starlette
        detects a client disconnect, driving it through either of those
        transports deadlocks forever — there is no client-side disconnect
        signal available until the (still-blocked) call returns.

        A real uvicorn server bound to a real socket has no such buffering:
        the client can read one line and close its connection independent
        of the server coroutine's lifecycle. So this test spins up the
        actual FastAPI `app` (with this test's DB override already wired by
        the `client` fixture) on a background thread and hits it with a
        genuine HTTP client, which is what "TestClient streaming — read
        first chunk then close" means in practice here.
        """
        import socket
        import threading
        import time

        import httpx
        import uvicorn

        lc = _make_class(db, live_course, instructor_user, "si-poll0013")
        _enroll(db, student_user, live_course)
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Stream Q", "options": ["A", "B"],
        })
        poll = r.json()
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/activate")

        from app.main import app

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical", lifespan="off")
        server = uvicorn.Server(config)

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            deadline = time.time() + 10
            while not server.started and time.time() < deadline:
                time.sleep(0.05)
            assert server.started, "uvicorn server did not start in time"

            data_line = None
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10.0) as http_client:
                with http_client.stream(
                    "GET", f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/stream",
                ) as resp:
                    assert resp.status_code == 200
                    assert "text/event-stream" in resp.headers["content-type"]
                    for line in resp.iter_lines():
                        if line.startswith("data:"):
                            data_line = line
                            break
        finally:
            server.should_exit = True
            thread.join(timeout=10)

        assert data_line is not None, "no data: frame received from the SSE stream"
        payload = json.loads(data_line[len("data:"):].strip())
        assert payload["type"] == "poll"
        assert payload["poll"]["id"] == poll["id"]
        assert payload["poll"]["question"] == "Stream Q"

    def test_sse_requires_access(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0014")
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Q", "options": ["A", "B"],
        })
        poll = r.json()
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/activate")

        # student_user not enrolled -> no access.
        as_user(student_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/stream")
        assert r.status_code == 403


class _CapturingFakeRedis:
    """A fake Redis client with real-Redis-like pub/sub semantics (unlike
    MockRedis, which live_class_polls._is_usable_redis-equivalent checks
    deliberately treat as unusable) — `ping()` succeeds, `publish()` records
    every raw payload AND fans it out to any subscribed `_FakePubSub`
    instances so a stream reading via `get_message()` sees it, just like a
    real Redis pub/sub channel."""

    def __init__(self):
        self.published: list[tuple[str, str]] = []
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    async def ping(self):
        return True

    async def publish(self, channel: str, message: str) -> int:
        self.published.append((channel, message))
        for queue in self._subscribers.get(channel, []):
            await queue.put(message)
        return len(self._subscribers.get(channel, []))

    def pubsub(self):
        return _FakePubSub(self)


class _FakePubSub:
    def __init__(self, redis: "_CapturingFakeRedis"):
        self._redis = redis
        self._channel = None
        self._queue: asyncio.Queue | None = None

    async def subscribe(self, channel: str):
        self._channel = channel
        self._queue = asyncio.Queue()
        self._redis._subscribers.setdefault(channel, []).append(self._queue)

    async def get_message(self, ignore_subscribe_messages=True, timeout=15):
        try:
            data = await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
        return {"type": "message", "data": data}

    async def unsubscribe(self, channel: str):
        subs = self._redis._subscribers.get(channel, [])
        if self._queue in subs:
            subs.remove(self._queue)

    async def close(self):
        pass


class TestPollStreamRoleNeutralPublish:
    """The published Redis payload must never carry role-scoped rendering
    (tallies/my_vote) — it must be JUST {"type": "poll_changed", "poll_id":
    N}. Each subscriber re-projects that notification for its own viewer
    from a fresh DB read before forwarding to its own stream."""

    def _setup_class_and_poll(self, client, db, as_user, instructor_user, live_course, student_user):
        lc = _make_class(db, live_course, instructor_user, "si-poll0015")
        _enroll(db, student_user, live_course)
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls", json={
            "question": "Leak check", "options": ["A", "B"], "show_results": False,
        })
        poll = r.json()
        client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/activate")
        _give_attendance(db, lc, student_user)
        return lc, poll

    def test_published_payload_has_no_tallies_or_my_vote(
        self, client, db, as_user, instructor_user, live_course, student_user, monkeypatch,
    ):
        lc, poll = self._setup_class_and_poll(client, db, as_user, instructor_user, live_course, student_user)

        fake_redis = _CapturingFakeRedis()

        async def _fake_get_redis():
            return fake_redis

        monkeypatch.setattr("app.routers.live_class_polls.get_redis", _fake_get_redis)

        as_user(student_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/polls/{poll['id']}/vote", json={"option_index": 1})
        assert r.status_code == 200, r.text

        assert len(fake_redis.published) == 1
        channel, raw_message = fake_redis.published[0]
        assert channel == f"live:class:{lc.id}"
        payload = json.loads(raw_message)

        assert payload == {"type": "poll_changed", "poll_id": poll["id"]}
        assert "tallies" not in payload
        assert "my_vote" not in payload
        assert "poll" not in payload

    def test_forwarded_event_is_reprojected_per_viewer(
        self, db, as_user, instructor_user, live_course, student_user,
    ):
        """A show_results=False ACTIVE poll: `reproject_poll_for_viewer` —
        the exact function the SSE stream loop calls for every forwarded
        `poll_changed` notification (see live_class_polls.poll_stream) —
        must render tallies=None for a student, and real tallies for the
        instructor, from the SAME underlying poll/vote state. This is the
        function-level counterpart to
        `test_published_payload_has_no_tallies_or_my_vote` (which proves
        the published Redis payload never carries a rendered PollOut): this
        test proves the per-viewer re-projection on the receiving side is
        actually role-correct, not just present.
        """
        from app.routers.live_class_polls import reproject_poll_for_viewer

        lc = _make_class(db, live_course, instructor_user, "si-poll0016")
        _enroll(db, student_user, live_course)
        poll_row = LiveClassPoll(
            class_id=lc.id, created_by=instructor_user.id, question="Reproj check",
            options=["A", "B"], status=PollStatus.ACTIVE, show_results=False,
            activated_at=datetime.now(timezone.utc),
        )
        db.add(poll_row)
        db.commit()
        db.refresh(poll_row)
        _give_attendance(db, lc, student_user)

        as_user(student_user)
        # (No HTTP call needed to cast the vote for this test — write the
        # vote row directly, since only the re-projection is under test.)
        from app.models.live_class import LiveClassPollVote
        db.add(LiveClassPollVote(poll_id=poll_row.id, user_id=student_user.id, option_index=0))
        db.commit()

        student_projection = reproject_poll_for_viewer(db, lc.id, poll_row.id, student_user.id)
        assert student_projection is not None
        assert student_projection["tallies"] is None
        assert student_projection["my_vote"] == 0

        instructor_projection = reproject_poll_for_viewer(db, lc.id, poll_row.id, instructor_user.id)
        assert instructor_projection is not None
        assert instructor_projection["tallies"] is not None
        assert sum(instructor_projection["tallies"]) == 1
        assert instructor_projection["my_vote"] is None

    def test_reproject_returns_none_for_deleted_poll_or_user(self, db, instructor_user, live_course, student_user):
        """Defensive path: the poll or the subscriber's user may have
        disappeared between subscribing and a later published event
        (e.g. a hard-deleted test row) — must return None, not raise."""
        from app.routers.live_class_polls import reproject_poll_for_viewer

        lc = _make_class(db, live_course, instructor_user, "si-poll0017")
        assert reproject_poll_for_viewer(db, lc.id, 999999, instructor_user.id) is None
        assert reproject_poll_for_viewer(db, lc.id, 1, 999999) is None
