"""Round-trip tests for the seven Live Classes models.

Uses the shared `db` fixture (in-memory SQLite, fresh per test) from
conftest.py. Covers: each table roundtrips, room_name uniqueness,
(class_id, user_id) uniqueness on attendance, (poll_id, user_id) uniqueness
on poll votes.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.live_class import (
    AttendanceSource,
    LiveClass,
    LiveClassAttendance,
    LiveClassEvent,
    LiveClassJoinToken,
    LiveClassPoll,
    LiveClassPollVote,
    LiveClassSchedule,
    LiveClassStatus,
    PollStatus,
    RecordingStatus,
)


@pytest.fixture()
def instructor(db):
    from app.models.user import User

    u = User(
        user_login="live_instructor",
        user_pass="x",
        user_nicename="live_instructor",
        user_email="live_instructor@example.com",
        display_name="Live Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def live_course(db, instructor):
    from app.models.course import Course

    c = Course(post_author=instructor.id, post_title="Live Course", course_price_type="free", course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def student(db):
    from app.models.user import User

    u = User(
        user_login="live_student",
        user_pass="x",
        user_nicename="live_student",
        user_email="live_student@example.com",
        display_name="Live Student",
        role="student",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_class(db, course, instructor, room_name="si-aaaaaaaa", **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Intro to Testing",
        scheduled_start=now + timedelta(hours=1),
        scheduled_end=now + timedelta(hours=2),
        room_name=room_name,
        settings={
            "lobby_enabled": True,
            "start_muted": True,
            "allow_chat": True,
            "allow_share": True,
            "record": False,
            "attendance_threshold_pct": 60,
        },
    )
    defaults.update(overrides)
    lc = LiveClass(**defaults)
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


class TestLiveClassSchedule:
    def test_roundtrip(self, db, live_course, instructor):
        sched = LiveClassSchedule(
            course_id=live_course.id,
            instructor_id=instructor.id,
            title="Weekly Series",
            timezone="Asia/Kolkata",
            recurrence_weekly=["MO", "WE"],
            weeks=3,
        )
        db.add(sched)
        db.commit()
        db.refresh(sched)

        fetched = db.query(LiveClassSchedule).filter_by(id=sched.id).first()
        assert fetched.title == "Weekly Series"
        assert fetched.recurrence_weekly == ["MO", "WE"]
        assert fetched.weeks == 3
        assert fetched.timezone == "Asia/Kolkata"


class TestLiveClass:
    def test_roundtrip_and_defaults(self, db, live_course, instructor):
        lc = _make_class(db, live_course, instructor)

        fetched = db.query(LiveClass).filter_by(id=lc.id).first()
        assert fetched.title == "Intro to Testing"
        assert fetched.status == LiveClassStatus.SCHEDULED
        assert fetched.recording_status == RecordingStatus.NONE
        assert fetched.live_participants == 0
        assert fetched.room_name == "si-aaaaaaaa"
        assert fetched.recording_video_id is None
        assert fetched.settings["attendance_threshold_pct"] == 60

    def test_room_name_unique(self, db, live_course, instructor):
        _make_class(db, live_course, instructor, room_name="si-dupdupdu")
        with pytest.raises(IntegrityError):
            _make_class(db, live_course, instructor, room_name="si-dupdupdu")
        db.rollback()

    def test_recording_video_id_is_string(self, db, live_course, instructor):
        """Bunny video GUIDs are opaque strings (verified against
        app/routers/bunny.py) — not integers."""
        lc = _make_class(
            db, live_course, instructor, room_name="si-recid001",
            recording_video_id="8f4b9c1a-guid-like-string",
            recording_status=RecordingStatus.AVAILABLE,
        )
        fetched = db.query(LiveClass).filter_by(id=lc.id).first()
        assert fetched.recording_video_id == "8f4b9c1a-guid-like-string"
        assert isinstance(fetched.recording_video_id, str)


class TestLiveClassJoinToken:
    def test_roundtrip(self, db, live_course, instructor, student):
        lc = _make_class(db, live_course, instructor, room_name="si-jointok1")
        now = datetime.now(timezone.utc)
        token = LiveClassJoinToken(
            class_id=lc.id,
            user_id=student.id,
            jti="jti-unique-1",
            moderator=False,
            expires_at=now + timedelta(minutes=15),
        )
        db.add(token)
        db.commit()
        db.refresh(token)

        fetched = db.query(LiveClassJoinToken).filter_by(id=token.id).first()
        assert fetched.jti == "jti-unique-1"
        assert fetched.moderator is False
        assert fetched.redeemed_at is None

    def test_jti_unique(self, db, live_course, instructor, student):
        lc = _make_class(db, live_course, instructor, room_name="si-jointok2")
        now = datetime.now(timezone.utc)
        db.add(LiveClassJoinToken(class_id=lc.id, user_id=student.id, jti="dup-jti", expires_at=now))
        db.commit()
        db.add(LiveClassJoinToken(class_id=lc.id, user_id=student.id, jti="dup-jti", expires_at=now))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


class TestLiveClassAttendance:
    def test_roundtrip(self, db, live_course, instructor, student):
        lc = _make_class(db, live_course, instructor, room_name="si-attend01")
        att = LiveClassAttendance(
            class_id=lc.id,
            user_id=student.id,
            source=AttendanceSource.WEB,
            accumulated_seconds=120,
        )
        db.add(att)
        db.commit()
        db.refresh(att)

        fetched = db.query(LiveClassAttendance).filter_by(id=att.id).first()
        assert fetched.accumulated_seconds == 120
        assert fetched.present is None
        assert fetched.source == AttendanceSource.WEB

    def test_unique_class_user(self, db, live_course, instructor, student):
        lc = _make_class(db, live_course, instructor, room_name="si-attend02")
        db.add(LiveClassAttendance(class_id=lc.id, user_id=student.id))
        db.commit()
        db.add(LiveClassAttendance(class_id=lc.id, user_id=student.id))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


class TestLiveClassPoll:
    def test_roundtrip(self, db, live_course, instructor):
        lc = _make_class(db, live_course, instructor, room_name="si-poll0001")
        poll = LiveClassPoll(
            class_id=lc.id,
            created_by=instructor.id,
            question="Ready to continue?",
            options=["Yes", "No"],
            status=PollStatus.DRAFT,
        )
        db.add(poll)
        db.commit()
        db.refresh(poll)

        fetched = db.query(LiveClassPoll).filter_by(id=poll.id).first()
        assert fetched.options == ["Yes", "No"]
        assert fetched.status == PollStatus.DRAFT
        assert fetched.show_results is True


class TestLiveClassPollVote:
    def test_roundtrip(self, db, live_course, instructor, student):
        lc = _make_class(db, live_course, instructor, room_name="si-poll0002")
        poll = LiveClassPoll(
            class_id=lc.id, created_by=instructor.id, question="Q", options=["A", "B"],
            status=PollStatus.ACTIVE,
        )
        db.add(poll)
        db.commit()
        db.refresh(poll)

        vote = LiveClassPollVote(poll_id=poll.id, user_id=student.id, option_index=1)
        db.add(vote)
        db.commit()
        db.refresh(vote)

        fetched = db.query(LiveClassPollVote).filter_by(id=vote.id).first()
        assert fetched.option_index == 1

    def test_unique_poll_user(self, db, live_course, instructor, student):
        lc = _make_class(db, live_course, instructor, room_name="si-poll0003")
        poll = LiveClassPoll(
            class_id=lc.id, created_by=instructor.id, question="Q", options=["A", "B"],
            status=PollStatus.ACTIVE,
        )
        db.add(poll)
        db.commit()
        db.refresh(poll)

        db.add(LiveClassPollVote(poll_id=poll.id, user_id=student.id, option_index=0))
        db.commit()
        db.add(LiveClassPollVote(poll_id=poll.id, user_id=student.id, option_index=1))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


class TestLiveClassEvent:
    def test_roundtrip(self, db, live_course, instructor):
        lc = _make_class(db, live_course, instructor, room_name="si-event001")
        event = LiveClassEvent(
            class_id=lc.id,
            user_id=instructor.id,
            event="class.created",
            payload={"title": lc.title},
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        fetched = db.query(LiveClassEvent).filter_by(id=event.id).first()
        assert fetched.event == "class.created"
        assert fetched.payload == {"title": "Intro to Testing"}
        assert fetched.user_id == instructor.id

    def test_user_id_nullable(self, db, live_course, instructor):
        """System-generated events (e.g. reminder.sent) have no acting user."""
        lc = _make_class(db, live_course, instructor, room_name="si-event002")
        event = LiveClassEvent(class_id=lc.id, event="reminder.sent")
        db.add(event)
        db.commit()
        db.refresh(event)
        assert event.user_id is None
