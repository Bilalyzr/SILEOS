"""Session lifecycle router: start/end/join-token/heartbeat.

Covers: join happy path (enrolled student) + DB row shape, 403+join.denied
for non-enrolled, 409 for ended/cancelled, instructor pre-window access,
student pre-T-15 409 (detail names the opens time), rate limit trips on the
6th call/min, heartbeat math (60s beats accumulate ~60s, 90s cap, first beat
= 0 + stamps), start idempotency (one class.started event across two
starts), and end-time attendance finalization at the 60% threshold boundary.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import get_settings
from app.models.enrollment import Enrollment
from app.models.live_class import (
    LiveClass,
    LiveClassAttendance,
    LiveClassEvent,
    LiveClassJoinToken,
    LiveClassStatus,
)


@pytest.fixture(autouse=True)
def _jitsi_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "test-jitsi-secret-0123456789")
    monkeypatch.setattr(get_settings(), "JITSI_PUBLIC_URL", "https://live.example.test")


@pytest.fixture()
def instructor_user(db):
    from app.models.user import User

    u = User(
        user_login="sess_instructor", user_pass="x", user_nicename="sess_instructor",
        user_email="sess_instructor@example.com", display_name="Sess Instructor",
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
        user_login="sess_other_instructor", user_pass="x", user_nicename="sess_other_instructor",
        user_email="sess_other_instructor@example.com", display_name="Other Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def live_course(db, instructor_user):
    from app.models.course import Course

    c = Course(post_author=instructor_user.id, post_title="Sess Course",
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


def _make_class(db, course, instructor, room_name, status=LiveClassStatus.SCHEDULED,
                 start_delta=timedelta(minutes=30), duration_minutes=100, **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Session Test Class",
        scheduled_start=now + start_delta,
        scheduled_end=now + start_delta + timedelta(minutes=duration_minutes),
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


# ---------------------------------------------------------------------------
# join-token
# ---------------------------------------------------------------------------

class TestJoinToken:
    def test_enrolled_student_happy_path(self, client, db, as_user, student_user, live_course, instructor_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-join0001",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-5))
        as_user(student_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["room_name"] == lc.room_name
        assert body["jitsi_url"] == "https://live.example.test"
        # expires_in mirrors the JWT's real exp — max(now+15min,
        # scheduled_end+30min) — not the old hardcoded 900s. This class
        # started 5min ago and runs 100min, so it ends ~95min out and the
        # grace branch wins: ~125min of validity.
        assert body["expires_in"] > 900
        assert abs(body["expires_in"] - 125 * 60) <= 60
        assert body["jwt"]
        assert body["class_summary"]["id"] == lc.id

        token_row = db.query(LiveClassJoinToken).filter_by(class_id=lc.id, user_id=student_user.id).one()
        assert token_row.moderator is False
        assert token_row.redeemed_at is None

        att = db.query(LiveClassAttendance).filter_by(class_id=lc.id, user_id=student_user.id).one()
        assert att.accumulated_seconds == 0

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="join.token_issued").all()
        assert len(events) == 1

    def test_non_enrolled_student_403_and_denied_event(self, client, db, as_user, student_user, live_course, instructor_user):
        lc = _make_class(db, live_course, instructor_user, "si-join0002",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-5))
        as_user(student_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 403

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="join.denied").all()
        assert len(events) == 1
        assert events[0].user_id == student_user.id

    def test_ended_class_409(self, client, db, as_user, student_user, live_course, instructor_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-join0003",
                          status=LiveClassStatus.ENDED, start_delta=timedelta(minutes=-60))
        as_user(student_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 409

    def test_cancelled_class_409(self, client, db, as_user, student_user, live_course, instructor_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-join0004",
                          status=LiveClassStatus.CANCELLED, start_delta=timedelta(minutes=30))
        as_user(student_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 409

    def test_instructor_allowed_before_join_window(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-join0005",
                          status=LiveClassStatus.SCHEDULED, start_delta=timedelta(hours=5))
        as_user(instructor_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 200, r.text
        token_row = db.query(LiveClassJoinToken).filter_by(class_id=lc.id, user_id=instructor_user.id).one()
        assert token_row.moderator is True

    def test_student_409_before_t_minus_15_names_opens_time(self, client, db, as_user, student_user, live_course, instructor_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-join0006",
                          status=LiveClassStatus.SCHEDULED, start_delta=timedelta(hours=2))
        as_user(student_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 409
        opens_at = lc.scheduled_start - timedelta(minutes=15)
        assert opens_at.isoformat()[:16] in r.json()["detail"]

    def test_student_allowed_within_t_minus_15(self, client, db, as_user, student_user, live_course, instructor_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-join0007",
                          status=LiveClassStatus.SCHEDULED, start_delta=timedelta(minutes=10))
        as_user(student_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 200, r.text

    def test_rate_limit_trips_on_sixth_call(self, client, db, as_user, student_user, live_course, instructor_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-join0008",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-5))
        as_user(student_user)

        for i in range(5):
            r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
            assert r.status_code == 200, f"call {i} failed: {r.text}"

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 429

    def test_soft_deleted_class_404s_even_if_status_live(self, client, db, as_user, student_user, live_course, instructor_user):
        """deleted_at must gate independently of status — a soft-cancelled
        class 404s even if some stale row still reads LIVE."""
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-join0009",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-5))
        lc.deleted_at = datetime.now(timezone.utc)
        db.commit()
        as_user(student_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# heartbeat
# ---------------------------------------------------------------------------

class TestHeartbeat:
    def _issue_join(self, client, as_user, student_user, live_course, instructor_user, db):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-hb000001",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-5))
        as_user(student_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/join-token")
        assert r.status_code == 200, r.text
        return lc

    def test_first_beat_is_zero_and_stamps_first_joined(self, client, db, as_user, student_user, live_course, instructor_user):
        lc = self._issue_join(client, as_user, student_user, live_course, instructor_user, db)
        r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={
            "client_ts": datetime.now(timezone.utc).isoformat(),
        })
        assert r.status_code == 200, r.text
        assert r.json()["delta"] == 0
        assert r.json()["accumulated_seconds"] == 0

        att = db.query(LiveClassAttendance).filter_by(class_id=lc.id, user_id=student_user.id).one()
        assert att.first_joined_at is not None
        assert att.last_heartbeat_at is not None

        token_row = db.query(LiveClassJoinToken).filter_by(class_id=lc.id, user_id=student_user.id).one()
        assert token_row.redeemed_at is not None
        redeemed_events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="join.redeemed").all()
        assert len(redeemed_events) == 1

    def test_two_beats_60s_apart_accumulate_60(self, client, db, as_user, student_user, live_course, instructor_user, monkeypatch):
        lc = self._issue_join(client, as_user, student_user, live_course, instructor_user, db)

        import app.routers.live_class_session as sess_mod

        t0 = datetime.now(timezone.utc)

        class _FixedDatetime(datetime):
            _now = t0

            @classmethod
            def now(cls, tz=None):
                return cls._now

        monkeypatch.setattr(sess_mod, "datetime", _FixedDatetime)
        r1 = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
        assert r1.status_code == 200, r1.text
        assert r1.json()["delta"] == 0

        _FixedDatetime._now = t0 + timedelta(seconds=60)
        r2 = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
        assert r2.status_code == 200, r2.text
        assert 59 <= r2.json()["delta"] <= 61
        assert 59 <= r2.json()["accumulated_seconds"] <= 61

    def test_ten_minute_gap_caps_at_90(self, client, db, as_user, student_user, live_course, instructor_user, monkeypatch):
        lc = self._issue_join(client, as_user, student_user, live_course, instructor_user, db)

        import app.routers.live_class_session as sess_mod

        t0 = datetime.now(timezone.utc)

        class _FixedDatetime(datetime):
            _now = t0

            @classmethod
            def now(cls, tz=None):
                return cls._now

        monkeypatch.setattr(sess_mod, "datetime", _FixedDatetime)
        r1 = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
        assert r1.status_code == 200, r1.text

        _FixedDatetime._now = t0 + timedelta(minutes=10)
        r2 = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
        assert r2.status_code == 200, r2.text
        assert r2.json()["delta"] == 90
        assert r2.json()["accumulated_seconds"] == 90

    def test_heartbeat_409_after_class_ended(self, client, db, as_user, student_user, live_course, instructor_user):
        lc = self._issue_join(client, as_user, student_user, live_course, instructor_user, db)
        lc.status = LiveClassStatus.ENDED
        lc.ended_at = datetime.now(timezone.utc)
        db.commit()

        r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={
            "client_ts": datetime.now(timezone.utc).isoformat(),
        })
        assert r.status_code == 409

    def test_unenrolled_mid_class_heartbeat_403(self, client, db, as_user, student_user, live_course, instructor_user):
        """A student unenrolled after joining must stop accruing attendance
        immediately — heartbeat re-checks access on every call, not just at
        join-token time."""
        lc = self._issue_join(client, as_user, student_user, live_course, instructor_user, db)

        db.query(Enrollment).filter_by(
            course_id=live_course.id, user_id=student_user.id,
        ).update({"enrollment_status": "cancelled"})
        db.commit()

        r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={
            "client_ts": datetime.now(timezone.utc).isoformat(),
        })
        assert r.status_code == 403

    def test_61_beats_1s_apart_accumulate_within_58_62(self, client, db, as_user, student_user, live_course, instructor_user, monkeypatch):
        """Sub-cap regime, floor-with-carry: each 1s-apart beat floors its
        own delta to 1 with nothing left to carry, so 61 beats 1s apart (60
        gaps) accumulate almost exactly 60s."""
        lc = self._issue_join(client, as_user, student_user, live_course, instructor_user, db)

        import app.routers.live_class_session as sess_mod

        t0 = datetime.now(timezone.utc)

        class _FixedDatetime(datetime):
            _now = t0

            @classmethod
            def now(cls, tz=None):
                return cls._now

        monkeypatch.setattr(sess_mod, "datetime", _FixedDatetime)

        r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
        assert r.status_code == 200, r.text

        for i in range(1, 61):
            _FixedDatetime._now = t0 + timedelta(seconds=i)
            r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
            assert r.status_code == 200, r.text

        assert 58 <= r.json()["accumulated_seconds"] <= 62

    def test_100_beats_half_second_apart_accumulate_within_48_52(self, client, db, as_user, student_user, live_course, instructor_user, monkeypatch):
        """Sub-cap regime, floor-with-carry: 100 beats 0.5s apart (each gap
        < 1s) would each floor to a 0 delta and accumulate NOTHING if the
        fractional remainder were discarded every beat instead of carried
        forward via last_heartbeat_at. With the carry, the credited total
        converges to the true elapsed 50s."""
        lc = self._issue_join(client, as_user, student_user, live_course, instructor_user, db)

        import app.routers.live_class_session as sess_mod

        t0 = datetime.now(timezone.utc)

        class _FixedDatetime(datetime):
            _now = t0

            @classmethod
            def now(cls, tz=None):
                return cls._now

        monkeypatch.setattr(sess_mod, "datetime", _FixedDatetime)

        r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
        assert r.status_code == 200, r.text

        for i in range(1, 101):
            _FixedDatetime._now = t0 + timedelta(seconds=0.5 * i)
            r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
            assert r.status_code == 200, r.text

        assert 48 <= r.json()["accumulated_seconds"] <= 52

    def test_beyond_cap_gap_does_not_leave_debt_for_next_beats(self, client, db, as_user, student_user, live_course, instructor_user, monkeypatch):
        """Regression for the beyond-cap-remainder bug: an earlier version
        of apply_heartbeat used the sub-cap carry rule unconditionally, so a
        beat after a long (>90s) silence advanced last_heartbeat_at by only
        the capped 90s, not to `now` — leaving the beyond-cap remainder
        (510s here) stuck in the marker. Every follow-up beat then still saw
        a >90s gap against that un-advanced marker and got credited another
        full 90s, so five 1s-apart beats after a single 10-minute absence
        inflated to 5x90=450s of bogus extra credit (540s total for the
        whole sequence) instead of the ~90s a 10-minute absence should cost.

        Trap: beat, 600s silence, beat (must credit exactly 90) — then five
        beats 1s apart (each must credit <= 2, not another 90) — and the
        running total after all of it must stay bounded (<= 100), not blow
        up to hundreds of seconds from a single absence.
        """
        lc = self._issue_join(client, as_user, student_user, live_course, instructor_user, db)

        import app.routers.live_class_session as sess_mod

        t0 = datetime.now(timezone.utc)

        class _FixedDatetime(datetime):
            _now = t0

            @classmethod
            def now(cls, tz=None):
                return cls._now

        monkeypatch.setattr(sess_mod, "datetime", _FixedDatetime)

        r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
        assert r.status_code == 200, r.text

        # 10 minutes of silence, then one beat: must credit exactly the cap.
        _FixedDatetime._now = t0 + timedelta(seconds=600)
        r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
        assert r.status_code == 200, r.text
        assert r.json()["delta"] == 90

        # Five follow-up beats 1s apart: each must be a normal sub-cap
        # credit (<= 2s), never another 90 from stale beyond-cap debt.
        for i in range(1, 6):
            _FixedDatetime._now = t0 + timedelta(seconds=600 + i)
            r = client.post(f"/api/v1/live/classes/{lc.id}/heartbeat", json={"client_ts": t0.isoformat()})
            assert r.status_code == 200, r.text
            assert r.json()["delta"] <= 2, f"beat {i} credited {r.json()['delta']}s — beyond-cap debt leaked"

        assert r.json()["accumulated_seconds"] <= 100


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

class TestStart:
    def test_start_idempotent_single_event(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-start0001",
                          status=LiveClassStatus.SCHEDULED, start_delta=timedelta(minutes=1))
        as_user(instructor_user)

        r1 = client.post(f"/api/v1/live/classes/{lc.id}/start")
        assert r1.status_code == 200, r1.text
        assert r1.json()["status"] == "live"

        r2 = client.post(f"/api/v1/live/classes/{lc.id}/start")
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "live"

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="class.started").all()
        assert len(events) == 1

    def test_non_assigned_instructor_403(self, client, db, as_user, other_instructor, live_course, instructor_user):
        lc = _make_class(db, live_course, instructor_user, "si-start0002",
                          status=LiveClassStatus.SCHEDULED, start_delta=timedelta(minutes=1))
        as_user(other_instructor)

        r = client.post(f"/api/v1/live/classes/{lc.id}/start")
        assert r.status_code == 403

    def test_start_ended_class_409(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-start0003",
                          status=LiveClassStatus.ENDED, start_delta=timedelta(minutes=-60))
        as_user(instructor_user)

        r = client.post(f"/api/v1/live/classes/{lc.id}/start")
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# end + attendance finalization threshold
# ---------------------------------------------------------------------------

class TestEnd:
    def test_end_requires_live(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-end00001",
                          status=LiveClassStatus.SCHEDULED, start_delta=timedelta(minutes=1))
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/end")
        assert r.status_code == 409

    def test_end_finalizes_present_at_61_percent(self, client, db, as_user, instructor_user, live_course, student_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-end00002",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-100),
                          duration_minutes=100)
        # 100-minute class, threshold 60% => 60 minutes = 3600s required.
        # 61% = 3660s -> present True.
        db.add(LiveClassAttendance(class_id=lc.id, user_id=student_user.id, accumulated_seconds=3660))
        db.commit()

        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/end")
        assert r.status_code == 200, r.text

        att = db.query(LiveClassAttendance).filter_by(class_id=lc.id, user_id=student_user.id).one()
        assert att.present is True

    def test_end_finalizes_absent_at_59_percent(self, client, db, as_user, instructor_user, live_course, student_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-end00003",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-100),
                          duration_minutes=100)
        # 59% of 6000s = 3540s -> present False.
        db.add(LiveClassAttendance(class_id=lc.id, user_id=student_user.id, accumulated_seconds=3540))
        db.commit()

        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/end")
        assert r.status_code == 200, r.text

        att = db.query(LiveClassAttendance).filter_by(class_id=lc.id, user_id=student_user.id).one()
        assert att.present is False

    def test_end_with_null_threshold_pct_does_not_raise_and_uses_60(self, client, db, as_user, instructor_user, live_course, student_user):
        """settings can carry attendance_threshold_pct as an explicit null
        (partial settings payload) rather than the key being absent — that
        must not TypeError on `None / 100`, and must fall back to 60%."""
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-end00004",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-100),
                          duration_minutes=100,
                          settings={"attendance_threshold_pct": None})
        # 61% of 6000s = 3660s -> present True under the 60% fallback.
        db.add(LiveClassAttendance(class_id=lc.id, user_id=student_user.id, accumulated_seconds=3660))
        db.commit()

        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/end")
        assert r.status_code == 200, r.text

        att = db.query(LiveClassAttendance).filter_by(class_id=lc.id, user_id=student_user.id).one()
        assert att.present is True
