"""Recordings: start/stop intent endpoints, internal ingest auth matrix +
idempotency, ingest_recording's bunny/fallback/failure paths, the
recording-playback endpoint's enrollment gate + signing requirement, and
the internal endpoint's file_path validation (directory containment +
room_name ownership).

Bunny HTTP calls are monkeypatched at the module level
(app.services.live_recording_service._upload_to_bunny) — the real Bunny API
is never called.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassStatus, RecordingStatus
from app.services import live_recording_service


# ---------------------------------------------------------------------------
# fixtures (local helper pattern per test_live_polls.py)
# ---------------------------------------------------------------------------

@pytest.fixture()
def rec_instructor(db):
    from app.models.user import User

    u = User(
        user_login="rec_instructor", user_pass="x", user_nicename="rec_instructor",
        user_email="rec_instructor@example.com", display_name="Rec Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def other_instructor(db):
    from app.models.user import User

    u = User(
        user_login="rec_other_instructor", user_pass="x", user_nicename="rec_other_instructor",
        user_email="rec_other_instructor@example.com", display_name="Other Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def rec_course(db, rec_instructor):
    from app.models.course import Course

    c = Course(post_author=rec_instructor.id, post_title="Recording Course",
               course_price_type="free", course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def other_course(db, other_instructor):
    from app.models.course import Course

    c = Course(post_author=other_instructor.id, post_title="Other Course",
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


def _make_student(db, login):
    """Direct User construction (plaintext user_pass, matching
    test_live_polls.py's fixture pattern) — avoids the make_user fixture's
    bcrypt hashing, which is broken in this venv (pre-existing baseline
    issue, unrelated to this feature)."""
    from app.models.user import User

    u = User(
        user_login=login, user_pass="x", user_nicename=login,
        user_email=f"{login}@example.com", display_name=login, role="student",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_class(db, course, instructor, room_name, status=LiveClassStatus.LIVE, **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Recording Test Class",
        scheduled_start=now - timedelta(minutes=5),
        scheduled_end=now + timedelta(minutes=55),
        room_name=room_name,
        status=status,
        settings={
            "lobby_enabled": True, "start_muted": True, "allow_chat": True,
            "allow_share": True, "record": True, "attendance_threshold_pct": 60,
        },
    )
    defaults.update(overrides)
    lc = LiveClass(**defaults)
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


@pytest.fixture()
def internal_token(monkeypatch):
    """Configure settings.INTERNAL_TOKEN for the internal-endpoint tests.
    get_settings() is an lru_cache'd singleton (matches how the rest of the
    suite mutates settings — see live_reminders tests) so we monkeypatch the
    attribute directly on the cached instance."""
    settings = get_settings()
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", "test-internal-token-0123456789")
    return settings.INTERNAL_TOKEN


@pytest.fixture()
def recordings_dir(tmp_path, monkeypatch):
    """Configure settings.JITSI_RECORDINGS_DIR to a tmp_path directory and
    return it — used by both the path-validation tests and the happy-path
    internal-endpoint tests so file_path values resolve inside it."""
    settings = get_settings()
    d = tmp_path / "recordings"
    d.mkdir()
    monkeypatch.setattr(settings, "JITSI_RECORDINGS_DIR", str(d))
    return d


@pytest.fixture()
def bunny_signing_key(monkeypatch):
    """Configure a non-blank BUNNY_TOKEN_AUTH_KEY on the bunny router module
    — required for the playback endpoint to return a URL at all (I1
    hardening: it 503s without one)."""
    from app.routers import bunny as bunny_router

    monkeypatch.setattr(bunny_router, "BUNNY_TOKEN_AUTH_KEY", "test-signing-key")
    return "test-signing-key"


# ---------------------------------------------------------------------------
# Recording start/stop intent
# ---------------------------------------------------------------------------

class TestRecordingIntent:
    def test_start_requires_assigned_instructor(self, client, db, as_user, other_instructor, rec_course, rec_instructor):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec00001")
        as_user(other_instructor)

        r = client.post(f"/api/v1/live/classes/{lc.id}/recording/start")
        assert r.status_code == 403, r.text

    def test_start_sets_requested_and_logs_event(self, client, db, as_user, rec_instructor, rec_course):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec00002")
        as_user(rec_instructor)

        r = client.post(f"/api/v1/live/classes/{lc.id}/recording/start")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["recording_status"] == "requested"

        db.refresh(lc)
        assert lc.recording_status == RecordingStatus.REQUESTED

        from app.models.live_class import LiveClassEvent
        events = db.query(LiveClassEvent).filter(LiveClassEvent.class_id == lc.id).all()
        assert any(e.event == "recording.started" for e in events)

    def test_stop_logs_event(self, client, db, as_user, rec_instructor, rec_course):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec00003", recording_status=RecordingStatus.REQUESTED)
        as_user(rec_instructor)

        r = client.post(f"/api/v1/live/classes/{lc.id}/recording/stop")
        assert r.status_code == 200, r.text

        from app.models.live_class import LiveClassEvent
        events = db.query(LiveClassEvent).filter(LiveClassEvent.class_id == lc.id).all()
        assert any(e.event == "recording.stopped" for e in events)

    def test_admin_may_start_recording(self, client, db, as_user, rec_instructor, rec_course):
        from app.models.user import User

        admin = User(
            user_login="rec_admin", user_pass="x", user_nicename="rec_admin",
            user_email="rec_admin@example.com", display_name="Rec Admin", role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        lc = _make_class(db, rec_course, rec_instructor, "si-rec00004")
        as_user(admin)

        r = client.post(f"/api/v1/live/classes/{lc.id}/recording/start")
        assert r.status_code == 200, r.text

    def test_start_404_for_missing_class(self, client, as_user, rec_instructor):
        as_user(rec_instructor)
        r = client.post("/api/v1/live/classes/999999/recording/start")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Internal ingest endpoint — auth matrix
# ---------------------------------------------------------------------------

class TestInternalAuthMatrix:
    def test_no_token_configured_returns_503(self, client, db, rec_instructor, rec_course, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "INTERNAL_TOKEN", "")
        lc = _make_class(db, rec_course, rec_instructor, "si-rec10001")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": "/tmp/x.mp4", "size_bytes": 10, "duration_seconds": 5},
            headers={"X-Internal-Token": "anything"},
        )
        assert r.status_code == 503, r.text

    def test_missing_header_returns_403(self, client, db, rec_instructor, rec_course, internal_token):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec10002")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": "/tmp/x.mp4", "size_bytes": 10, "duration_seconds": 5},
        )
        assert r.status_code == 403, r.text

    def test_wrong_token_returns_403(self, client, db, rec_instructor, rec_course, internal_token):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec10003")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": "/tmp/x.mp4", "size_bytes": 10, "duration_seconds": 5},
            headers={"X-Internal-Token": "wrong-token"},
        )
        assert r.status_code == 403, r.text

    def test_happy_path_returns_200(self, client, db, rec_instructor, rec_course, internal_token, recordings_dir, monkeypatch):
        async def _fake_upload(file_path, title):
            return "bunny-guid-happy"

        monkeypatch.setattr(live_recording_service, "_upload_to_bunny", _fake_upload)

        lc = _make_class(db, rec_course, rec_instructor, "si-rec10004")
        recording_file = recordings_dir / f"{lc.room_name}.mp4"
        recording_file.write_bytes(b"fake mp4 bytes")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": str(recording_file), "size_bytes": 14, "duration_seconds": 30},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["recording_status"] == "available"
        assert body["recording_video_id"] == "bunny-guid-happy"
        assert body["skipped"] is False

    def test_idempotent_when_already_ingested(self, client, db, rec_instructor, rec_course, internal_token):
        lc = _make_class(
            db, rec_course, rec_instructor, "si-rec10005",
            recording_status=RecordingStatus.AVAILABLE, recording_video_id="already-set-guid",
        )

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": "/tmp/dup.mp4", "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["skipped"] is True
        assert body["recording_video_id"] == "already-set-guid"

    def test_missing_class_returns_404(self, client, internal_token):
        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": "si-doesnotexist", "file_path": "/tmp/x.mp4", "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 404, r.text

    # -- edge-origination guard (C2c) ---------------------------------------
    # nginx unconditionally sets X-Forwarded-For on everything it proxies, so
    # its presence proves the request came through the edge rather than from
    # the local finalize worker — refused even with a VALID token. TestClient
    # sends no forwarded headers by default, which is why the happy-path
    # cases above still pass.

    def test_valid_token_with_x_forwarded_for_is_403(
        self, client, db, rec_instructor, rec_course, internal_token, recordings_dir, monkeypatch,
    ):
        async def _fake_upload(file_path, title):  # must never be reached
            raise AssertionError("ingest ran for an edge-originated request")

        monkeypatch.setattr(live_recording_service, "_upload_to_bunny", _fake_upload)

        lc = _make_class(db, rec_course, rec_instructor, "si-rec10006")
        recording_file = recordings_dir / f"{lc.room_name}.mp4"
        recording_file.write_bytes(b"fake mp4 bytes")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": str(recording_file), "size_bytes": 14, "duration_seconds": 30},
            headers={"X-Internal-Token": internal_token, "X-Forwarded-For": "127.0.0.1"},
        )
        assert r.status_code == 403, r.text

    def test_valid_token_with_x_forwarded_host_is_403(
        self, client, db, rec_instructor, rec_course, internal_token, recordings_dir,
    ):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec10007")
        recording_file = recordings_dir / f"{lc.room_name}.mp4"
        recording_file.write_bytes(b"fake mp4 bytes")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": str(recording_file), "size_bytes": 14, "duration_seconds": 30},
            headers={"X-Internal-Token": internal_token, "X-Forwarded-Host": "backend.sashainfinity.com"},
        )
        assert r.status_code == 403, r.text

    def test_blank_token_still_503_even_with_forwarded_header(
        self, client, db, rec_instructor, rec_course, monkeypatch,
    ):
        # Ordering check: "not configured" is reported before the edge test,
        # so a misconfigured deployment is diagnosable rather than looking
        # like a routing problem.
        settings = get_settings()
        monkeypatch.setattr(settings, "INTERNAL_TOKEN", "")
        lc = _make_class(db, rec_course, rec_instructor, "si-rec10008")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": "/tmp/x.mp4", "size_bytes": 10, "duration_seconds": 5},
            headers={"X-Internal-Token": "anything", "X-Forwarded-For": "203.0.113.7"},
        )
        assert r.status_code == 503, r.text


# ---------------------------------------------------------------------------
# Internal ingest endpoint — file_path validation (C1: traversal/symlink
# containment; I3: room_name ownership cross-check)
# ---------------------------------------------------------------------------

class TestFilePathValidation:
    def test_traversal_with_dotdot_is_rejected(self, client, db, rec_instructor, rec_course, internal_token, recordings_dir, monkeypatch):
        opened = {"called": False}
        real_open = open

        def _tracking_open(path, *a, **k):
            if str(path) == "/etc/passwd":
                opened["called"] = True
            return real_open(path, *a, **k)

        monkeypatch.setattr("builtins.open", _tracking_open)

        lc = _make_class(db, rec_course, rec_instructor, "si-rec40001")
        traversal_path = str(recordings_dir / ".." / ".." / "etc" / "passwd")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": traversal_path, "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 422, r.text
        assert opened["called"] is False

    def test_absolute_path_outside_recordings_dir_is_rejected(self, client, db, rec_instructor, rec_course, internal_token, recordings_dir, monkeypatch):
        opened = {"called": False}
        real_open = open

        def _tracking_open(path, *a, **k):
            opened["called"] = True
            return real_open(path, *a, **k)

        monkeypatch.setattr("builtins.open", _tracking_open)

        lc = _make_class(db, rec_course, rec_instructor, "si-rec40002")
        outside_path = "/etc/passwd" if os.name != "nt" else "C:\\Windows\\win.ini"

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": outside_path, "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 422, r.text
        assert opened["called"] is False

    @pytest.mark.skipif(sys.platform == "win32", reason="symlink creation requires elevated privileges on Windows")
    def test_symlink_escaping_recordings_dir_is_rejected(self, client, db, rec_instructor, rec_course, internal_token, recordings_dir, tmp_path):
        outside_target = tmp_path / "outside_secret.mp4"
        outside_target.write_bytes(b"secret")
        symlink_path = recordings_dir / "escape.mp4"
        symlink_path.symlink_to(outside_target)

        lc = _make_class(db, rec_course, rec_instructor, "si-rec40003")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": str(symlink_path), "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 422, r.text

    def test_blank_recordings_dir_is_rejected(self, client, db, rec_instructor, rec_course, internal_token, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "JITSI_RECORDINGS_DIR", "")
        lc = _make_class(db, rec_course, rec_instructor, "si-rec40004")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": "/tmp/anything.mp4", "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 422, r.text

    def test_room_name_mismatch_is_rejected(self, client, db, rec_instructor, rec_course, internal_token, recordings_dir):
        """A file that lives inside the recordings dir but under a DIFFERENT
        room's name than the target class — the ownership cross-check must
        reject this even though containment alone would pass."""
        lc = _make_class(db, rec_course, rec_instructor, "si-rec40005")
        other_lc = _make_class(db, rec_course, rec_instructor, "si-rec40006")

        mismatched_file = recordings_dir / f"{other_lc.room_name}.mp4"
        mismatched_file.write_bytes(b"belongs to the other class")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": str(mismatched_file), "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 422, r.text

    def test_happy_path_under_recordings_dir_still_ingests(self, client, db, rec_instructor, rec_course, internal_token, recordings_dir, monkeypatch):
        async def _fake_upload(file_path, title):
            return "bunny-guid-validated"

        monkeypatch.setattr(live_recording_service, "_upload_to_bunny", _fake_upload)

        lc = _make_class(db, rec_course, rec_instructor, "si-rec40007")
        nested_dir = recordings_dir / lc.room_name
        nested_dir.mkdir()
        recording_file = nested_dir / "output.mp4"
        recording_file.write_bytes(b"valid recording bytes")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": str(recording_file), "size_bytes": 22, "duration_seconds": 10},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 200, r.text
        assert r.json()["recording_video_id"] == "bunny-guid-validated"

    def test_prefix_room_name_does_not_match_longer_room(self, client, db, rec_instructor, rec_course, internal_token, recordings_dir):
        """I3 residual: a bare str.startswith check would let a SHORTER
        room_name ("si-ab") match a file that actually belongs to a LONGER
        room ("si-abcd1234") purely because it's a string prefix. The
        ownership check must require an exact path segment, an exact
        filename stem, or a stem that starts with room_name followed by a
        non-alphanumeric separator — not a bare prefix. The short room_name
        is created directly on a LiveClass row (bypassing
        generate_room_name, which would never itself produce such a short
        opaque string) specifically to exercise this boundary."""
        short_room_lc = _make_class(db, rec_course, rec_instructor, "si-ab")

        mismatched_file = recordings_dir / "si-abcd1234.mp4"
        mismatched_file.write_bytes(b"belongs to a different, longer-named room")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": short_room_lc.room_name, "file_path": str(mismatched_file), "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 422, r.text

    def test_resolve_oserror_returns_422_not_500(self, client, db, rec_instructor, rec_course, internal_token, recordings_dir, monkeypatch):
        """A symlink cycle or other filesystem oddity can make
        Path.resolve() raise OSError — this must surface as a 422
        (invalid recording path), never an unhandled 500."""
        real_resolve = Path.resolve

        def _flaky_resolve(self, *a, **k):
            if self.name.startswith("si-flaky"):
                raise OSError("simulated symlink cycle")
            return real_resolve(self, *a, **k)

        monkeypatch.setattr(Path, "resolve", _flaky_resolve)

        lc = _make_class(db, rec_course, rec_instructor, "si-flakyroom")

        r = client.post(
            "/api/v1/internal/live/recordings",
            json={"room_name": lc.room_name, "file_path": str(recordings_dir / "si-flakyroom.mp4"), "size_bytes": 1, "duration_seconds": 1},
            headers={"X-Internal-Token": internal_token},
        )
        assert r.status_code == 422, r.text


# ---------------------------------------------------------------------------
# validate_recording_path — direct unit coverage
# ---------------------------------------------------------------------------

class TestValidateRecordingPathUnit:
    def test_relative_path_resolved_against_recordings_dir(self, db, rec_instructor, rec_course, recordings_dir):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec50001")
        (recordings_dir / f"{lc.room_name}.mp4").write_bytes(b"x")

        resolved = live_recording_service.validate_recording_path(f"{lc.room_name}.mp4", lc)
        assert resolved == (recordings_dir / f"{lc.room_name}.mp4").resolve()

    def test_dotdot_traversal_raises(self, db, rec_instructor, rec_course, recordings_dir):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec50002")
        with pytest.raises(live_recording_service.RecordingPathError):
            live_recording_service.validate_recording_path("../../etc/passwd", lc)

    def test_exact_stem_matches(self, db, rec_instructor, rec_course, recordings_dir):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec50003")
        (recordings_dir / f"{lc.room_name}.mp4").write_bytes(b"x")
        live_recording_service.validate_recording_path(f"{lc.room_name}.mp4", lc)

    def test_separator_bounded_suffix_matches(self, db, rec_instructor, rec_course, recordings_dir):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec50004")
        (recordings_dir / f"{lc.room_name}-part2.mp4").write_bytes(b"x")
        live_recording_service.validate_recording_path(f"{lc.room_name}-part2.mp4", lc)

    def test_bare_prefix_without_separator_is_rejected(self, db, rec_instructor, rec_course, recordings_dir):
        """"si-abcd1234".startswith("si-ab") is True in plain Python string
        terms, but that must NOT be accepted as an ownership match — the
        boundary check requires an exact segment/stem or a
        separator ('-', '_', '.') right after the room_name prefix."""
        short_room_lc = _make_class(db, rec_course, rec_instructor, "si-ab")
        (recordings_dir / "si-abcd1234.mp4").write_bytes(b"x")

        with pytest.raises(live_recording_service.RecordingPathError):
            live_recording_service.validate_recording_path("si-abcd1234.mp4", short_room_lc)

    def test_resolve_oserror_is_wrapped(self, db, rec_instructor, rec_course, recordings_dir, monkeypatch):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec50005")

        def _raise_oserror(self, *a, **k):
            raise OSError("simulated symlink cycle")

        monkeypatch.setattr(Path, "resolve", _raise_oserror)

        with pytest.raises(live_recording_service.RecordingPathError):
            live_recording_service.validate_recording_path(f"{lc.room_name}.mp4", lc)


# ---------------------------------------------------------------------------
# ingest_recording — bunny success / retry-then-fallback / total failure
# ---------------------------------------------------------------------------

class TestIngestRecordingPaths:
    @pytest.mark.asyncio
    async def test_bunny_success_sets_available(self, db, rec_instructor, rec_course, tmp_path, monkeypatch):
        async def _fake_upload(file_path, title):
            return "bunny-guid-1"

        monkeypatch.setattr(live_recording_service, "_upload_to_bunny", _fake_upload)
        sent = {}
        monkeypatch.setattr(
            live_recording_service.EmailService, "_send_or_mock",
            staticmethod(lambda to, subject, body, html_body=None: sent.update(to=to, subject=subject) or True),
        )

        lc = _make_class(db, rec_course, rec_instructor, "si-rec20001")
        recording_file = tmp_path / "rec.mp4"
        recording_file.write_bytes(b"data")

        result = await live_recording_service.ingest_recording(db, lc, str(recording_file))
        db.commit()

        assert result.recording_status == RecordingStatus.AVAILABLE
        assert result.recording_video_id == "bunny-guid-1"
        assert sent.get("subject") == "Class recording ready"

    @pytest.mark.asyncio
    async def test_bunny_fails_three_times_then_local_fallback(self, db, rec_instructor, rec_course, tmp_path, monkeypatch):
        attempts = {"n": 0}

        async def _always_fail(file_path, title):
            attempts["n"] += 1
            return None

        monkeypatch.setattr(live_recording_service, "_upload_to_bunny", _always_fail)
        monkeypatch.setattr(live_recording_service, "BUNNY_UPLOAD_BACKOFF_SECONDS", 0)
        monkeypatch.setattr(live_recording_service.EmailService, "_send_or_mock", staticmethod(lambda *a, **k: True))

        fallback_dir = tmp_path / "fallback"
        monkeypatch.setattr(live_recording_service, "LOCAL_FALLBACK_DIR", str(fallback_dir))

        lc = _make_class(db, rec_course, rec_instructor, "si-rec20002")
        recording_file = tmp_path / "rec2.mp4"
        recording_file.write_bytes(b"data2")

        result = await live_recording_service.ingest_recording(db, lc, str(recording_file))
        db.commit()

        assert attempts["n"] == live_recording_service.BUNNY_UPLOAD_ATTEMPTS
        assert result.recording_status == RecordingStatus.AVAILABLE
        assert result.settings.get("recording_fallback") is True
        fallback_path = Path(result.settings["recording_fallback_path"])
        assert fallback_path.exists()

    @pytest.mark.asyncio
    async def test_both_bunny_and_fallback_fail_marks_failed_and_alerts(self, db, rec_instructor, rec_course, tmp_path, monkeypatch):
        async def _always_fail(file_path, title):
            return None

        monkeypatch.setattr(live_recording_service, "_upload_to_bunny", _always_fail)
        monkeypatch.setattr(live_recording_service, "BUNNY_UPLOAD_BACKOFF_SECONDS", 0)
        monkeypatch.setattr(live_recording_service, "_copy_to_local_fallback", lambda file_path, class_id: None)

        alerted = {}
        monkeypatch.setattr(
            live_recording_service.EmailService, "send_payment_alert",
            staticmethod(lambda subject, body: alerted.update(subject=subject, body=body) or True),
        )

        lc = _make_class(db, rec_course, rec_instructor, "si-rec20003")
        recording_file = tmp_path / "rec3.mp4"
        recording_file.write_bytes(b"data3")

        result = await live_recording_service.ingest_recording(db, lc, str(recording_file))
        db.commit()

        assert result.recording_status == RecordingStatus.FAILED
        assert "Live class recording failed" in alerted.get("subject", "")

        from app.models.live_class import LiveClassEvent
        events = db.query(LiveClassEvent).filter(LiveClassEvent.class_id == lc.id).all()
        assert any(e.event == "recording.failed" for e in events)


# ---------------------------------------------------------------------------
# Recording playback endpoint — enrollment gate + signing requirement (I1)
# ---------------------------------------------------------------------------

class TestRecordingPlayback:
    def test_no_recording_returns_404(self, client, db, as_user, rec_instructor, rec_course, bunny_signing_key):
        lc = _make_class(db, rec_course, rec_instructor, "si-rec30001")
        as_user(rec_instructor)

        r = client.get(f"/api/v1/live/classes/{lc.id}/recording-playback")
        assert r.status_code == 404, r.text

    def test_instructor_can_view_own_class_recording(self, client, db, as_user, rec_instructor, rec_course, bunny_signing_key):
        lc = _make_class(
            db, rec_course, rec_instructor, "si-rec30002",
            recording_status=RecordingStatus.AVAILABLE, recording_video_id="guid-abc",
        )
        as_user(rec_instructor)

        r = client.get(f"/api/v1/live/classes/{lc.id}/recording-playback")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["video_id"] == "guid-abc"
        assert body["signed"] is True
        assert body["expires_in"] is not None
        assert "hls_url" in body

    def test_enrolled_student_can_view(self, client, db, as_user, rec_instructor, rec_course, bunny_signing_key):
        student = _make_student(db, "rec_student_1")
        _enroll(db, student, rec_course)
        lc = _make_class(
            db, rec_course, rec_instructor, "si-rec30003",
            recording_status=RecordingStatus.AVAILABLE, recording_video_id="guid-def",
        )
        as_user(student)

        r = client.get(f"/api/v1/live/classes/{lc.id}/recording-playback")
        assert r.status_code == 200, r.text

    def test_student_of_another_course_is_403(self, client, db, as_user, rec_instructor, rec_course, other_course, bunny_signing_key):
        student = _make_student(db, "rec_student_2")
        _enroll(db, student, other_course)
        lc = _make_class(
            db, rec_course, rec_instructor, "si-rec30004",
            recording_status=RecordingStatus.AVAILABLE, recording_video_id="guid-ghi",
        )
        as_user(student)

        r = client.get(f"/api/v1/live/classes/{lc.id}/recording-playback")
        assert r.status_code == 403, r.text

    def test_bunny_direct_playback_endpoint_404s_for_live_recording(self, client, db, as_user, rec_instructor, rec_course):
        """Documents the Task 6 finding: the EXISTING bunny playback endpoint
        resolves video ownership via a Lesson row (LIKE-match on
        lesson_video_url/lesson_youtube_url); a live-class recording's Bunny
        video id is never written to any Lesson, so it 404s even for the
        assigned instructor. This is why /classes/{id}/recording-playback
        exists as a separate endpoint."""
        lc = _make_class(
            db, rec_course, rec_instructor, "si-rec30005",
            recording_status=RecordingStatus.AVAILABLE, recording_video_id="guid-not-a-lesson",
        )
        as_user(rec_instructor)

        r = client.get(f"/api/v1/bunny/video/{lc.recording_video_id}/playback")
        assert r.status_code == 404, r.text

    def test_unsigned_returns_503_when_signing_key_blank(self, client, db, as_user, rec_instructor, rec_course, monkeypatch):
        """I1: playback must never hand out a permanent unsigned CDN URL —
        when BUNNY_TOKEN_AUTH_KEY is blank, refuse with 503 rather than
        falling back to bunny.py's own unsigned-URL behavior."""
        from app.routers import bunny as bunny_router

        monkeypatch.setattr(bunny_router, "BUNNY_TOKEN_AUTH_KEY", "")

        lc = _make_class(
            db, rec_course, rec_instructor, "si-rec30006",
            recording_status=RecordingStatus.AVAILABLE, recording_video_id="guid-unsigned",
        )
        as_user(rec_instructor)

        r = client.get(f"/api/v1/live/classes/{lc.id}/recording-playback")
        assert r.status_code == 503, r.text
        assert r.json()["detail"] == "Recording playback is not configured"

    def test_signed_returns_url_with_expiry(self, client, db, as_user, rec_instructor, rec_course, bunny_signing_key):
        lc = _make_class(
            db, rec_course, rec_instructor, "si-rec30007",
            recording_status=RecordingStatus.AVAILABLE, recording_video_id="guid-signed",
        )
        as_user(rec_instructor)

        r = client.get(f"/api/v1/live/classes/{lc.id}/recording-playback")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["signed"] is True
        assert isinstance(body["expires_in"], int)
        assert "token=" in body["hls_url"]
