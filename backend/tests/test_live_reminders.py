"""Reminder loop (app/services/live_reminders.py): T-15min email batch +
idempotent second cycle, and LIVE class go-live broadcast event.

Uses the pure `_run_reminder_pass(db)` coroutine directly (same style as
reconciliation.py's pure functions being unit-tested without the outer
`reconciliation_loop`) so tests don't need a running event loop wrapper or
a Postgres advisory lock (SQLite in tests skips the lock branch entirely,
mirroring `_run_cycle`'s `engine.dialect.name == "postgresql"` guard).
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassEvent, LiveClassStatus
from app.services import live_reminders


@pytest.fixture()
def instructor_user(db):
    from app.models.user import User

    u = User(
        user_login="rem_instructor", user_pass="x", user_nicename="rem_instructor",
        user_email="rem_instructor@example.com", display_name="Rem Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def live_course(db, instructor_user):
    from app.models.course import Course

    c = Course(post_author=instructor_user.id, post_title="Reminder Course",
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


def _make_class(db, course, instructor, room_name, status=LiveClassStatus.SCHEDULED, **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Reminder Test Class",
        scheduled_start=now + timedelta(minutes=10),
        scheduled_end=now + timedelta(minutes=70),
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


def _run(coro):
    return asyncio.run(coro)


class TestUpcomingReminders:
    def test_class_10min_out_sends_one_batch_and_second_cycle_noops(self, db, instructor_user, live_course, student_user, monkeypatch):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-rem00001",
                          scheduled_start=datetime.now(timezone.utc) + timedelta(minutes=10))

        sent = []

        def _fake_send_or_mock(to_email, subject, body, html_body=None):
            sent.append((to_email, subject))
            return True

        monkeypatch.setattr("app.services.email_service.EmailService._send_or_mock", staticmethod(_fake_send_or_mock))

        _run(live_reminders._run_reminder_pass(db))

        assert len(sent) == 1
        assert sent[0][0] == student_user.user_email
        assert lc.title in sent[0][1]

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="reminder.sent").all()
        assert len(events) == 1

        # Second cycle: idempotent — no new email, no new event.
        _run(live_reminders._run_reminder_pass(db))
        assert len(sent) == 1
        events2 = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="reminder.sent").all()
        assert len(events2) == 1

    def test_class_outside_window_not_reminded(self, db, instructor_user, live_course, student_user, monkeypatch):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-rem00002",
                          scheduled_start=datetime.now(timezone.utc) + timedelta(minutes=45))

        sent = []
        monkeypatch.setattr(
            "app.services.email_service.EmailService._send_or_mock",
            staticmethod(lambda *a, **k: sent.append(a) or True),
        )

        _run(live_reminders._run_reminder_pass(db))
        assert len(sent) == 0
        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="reminder.sent").all()
        assert len(events) == 0

    def test_live_class_inside_window_still_gets_reminder_once(self, db, instructor_user, live_course, student_user, monkeypatch):
        """An instructor who starts the class a few minutes early (still
        inside the T-15 window) must not skip the T-15 reminder — status
        SCHEDULED is not required, only the scheduled_start window."""
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-rem00006",
                          status=LiveClassStatus.LIVE,
                          scheduled_start=datetime.now(timezone.utc) + timedelta(minutes=10),
                          started_at=datetime.now(timezone.utc))

        sent = []
        monkeypatch.setattr(
            "app.services.email_service.EmailService._send_or_mock",
            staticmethod(lambda *a, **k: sent.append(a) or True),
        )

        _run(live_reminders._run_reminder_pass(db))
        assert len(sent) == 1
        assert sent[0][0] == student_user.user_email

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="reminder.sent").all()
        assert len(events) == 1

        # Second cycle: still idempotent — one email, one event total.
        _run(live_reminders._run_reminder_pass(db))
        assert len(sent) == 1
        events2 = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="reminder.sent").all()
        assert len(events2) == 1

    def test_reminder_never_raises_on_bad_class(self, db, instructor_user, live_course, student_user, monkeypatch):
        """Per-class fault isolation: an exception processing one class must
        not prevent the pass from completing (never raises out)."""
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-rem00003",
                          scheduled_start=datetime.now(timezone.utc) + timedelta(minutes=5))

        def _boom(*a, **k):
            raise RuntimeError("smtp exploded")

        monkeypatch.setattr("app.services.email_service.EmailService._send_or_mock", staticmethod(_boom))

        # Must not raise.
        _run(live_reminders._run_reminder_pass(db))


class TestGoLiveBroadcast:
    def test_live_class_gets_one_broadcast_event(self, db, instructor_user, live_course, student_user, monkeypatch):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-rem00004",
                          status=LiveClassStatus.LIVE,
                          scheduled_start=datetime.now(timezone.utc) - timedelta(minutes=5),
                          started_at=datetime.now(timezone.utc) - timedelta(minutes=5))

        _run(live_reminders._run_reminder_pass(db))

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="class.live_broadcast").all()
        assert len(events) == 1

        # Second cycle: idempotent.
        _run(live_reminders._run_reminder_pass(db))
        events2 = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="class.live_broadcast").all()
        assert len(events2) == 1

    def test_scheduled_class_gets_no_broadcast(self, db, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-rem00005",
                          status=LiveClassStatus.SCHEDULED,
                          scheduled_start=datetime.now(timezone.utc) + timedelta(hours=5))

        _run(live_reminders._run_reminder_pass(db))

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="class.live_broadcast").all()
        assert len(events) == 0
