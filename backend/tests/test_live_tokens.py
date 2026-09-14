"""Jitsi JWT minting — claim shape, exp math, moderator/feature flags, jti
uniqueness, and the blank-secret RuntimeError guard.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import get_settings
from app.models.live_class import LiveClass
from app.services.jitsi_token_service import mint_jitsi_jwt


@pytest.fixture()
def instructor(db):
    from app.models.user import User

    u = User(
        user_login="tok_instructor", user_pass="x", user_nicename="tok_instructor",
        user_email="tok_instructor@example.com", display_name="Tok Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def student(db):
    from app.models.user import User

    u = User(
        user_login="tok_student", user_pass="x", user_nicename="tok_student",
        user_email="tok_student@example.com", display_name="Tok Student",
        role="student",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def live_course(db, instructor):
    from app.models.course import Course

    c = Course(post_author=instructor.id, post_title="Tok Course",
               course_price_type="free", course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_class(db, course, instructor, room_name="si-tok00001"):
    now = datetime.now(timezone.utc)
    lc = LiveClass(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Token Test Class",
        scheduled_start=now + timedelta(minutes=5),
        scheduled_end=now + timedelta(minutes=65),
        room_name=room_name,
        settings={
            "lobby_enabled": True, "start_muted": True, "allow_chat": True,
            "allow_share": True, "record": False, "attendance_threshold_pct": 60,
        },
    )
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


def _decode(token, secret):
    return jwt.decode(token, secret, algorithms=["HS256"], audience=get_settings().JITSI_JWT_APP_ID)


class TestClaimShape:
    def test_instructor_moderator_claims(self, db, monkeypatch, live_course, instructor):
        monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "test-jitsi-secret-0123456789")
        lc = _make_class(db, live_course, instructor)
        token, jti = mint_jitsi_jwt(user=instructor, live_class=lc, moderator=True)

        claims = _decode(token, get_settings().JITSI_JWT_SECRET)
        app_id = get_settings().JITSI_JWT_APP_ID
        assert claims["iss"] == app_id
        assert claims["aud"] == app_id
        assert claims["sub"] == app_id
        assert claims["room"] == lc.room_name
        assert claims["jti"] == jti

        user_ctx = claims["context"]["user"]
        assert user_ctx["id"] == str(instructor.id)
        assert user_ctx["name"] == instructor.display_name
        assert user_ctx["email"] == instructor.user_email
        assert user_ctx["avatar"] == ""
        assert user_ctx["moderator"] == "true"

        features = claims["context"]["features"]
        assert features["screen-sharing"] == "true"
        assert features["recording"] == "true"
        assert features["livestreaming"] == "false"
        assert features["transcription"] == "false"

    def test_student_non_moderator_claims(self, db, monkeypatch, live_course, instructor, student):
        monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "test-jitsi-secret-0123456789")
        lc = _make_class(db, live_course, instructor)
        token, _jti = mint_jitsi_jwt(user=student, live_class=lc, moderator=False)

        claims = _decode(token, get_settings().JITSI_JWT_SECRET)
        user_ctx = claims["context"]["user"]
        assert user_ctx["moderator"] == "false"

        features = claims["context"]["features"]
        assert features["screen-sharing"] == "false"
        assert features["recording"] == "false"
        assert features["livestreaming"] == "false"
        assert features["transcription"] == "false"

    def test_exp_equals_scheduled_end_plus_30min(self, db, monkeypatch, live_course, instructor):
        monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "test-jitsi-secret-0123456789")
        lc = _make_class(db, live_course, instructor)
        token, _jti = mint_jitsi_jwt(user=instructor, live_class=lc, moderator=True)

        claims = _decode(token, get_settings().JITSI_JWT_SECRET)
        # SQLite drops tzinfo on round-trip; scheduled_end is still UTC
        # wall-clock time, so re-attach UTC before computing the expected
        # epoch (mirrors the fix in jitsi_token_service.mint_jitsi_jwt).
        scheduled_end = lc.scheduled_end
        if scheduled_end.tzinfo is None:
            scheduled_end = scheduled_end.replace(tzinfo=timezone.utc)
        expected_exp = int((scheduled_end + timedelta(minutes=30)).timestamp())
        assert abs(claims["exp"] - expected_exp) <= 5

    def test_exp_floored_at_now_plus_15min_for_overtime_class(self, db, monkeypatch, live_course, instructor):
        """A class whose scheduled_end + 30min grace has ALREADY elapsed must
        still mint a usable token — `scheduled_end + 30min` alone would be in
        the past, and Jitsi rejects an expired token outright, making an
        overtime class unjoinable for late arrivals and reconnects."""
        monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "test-jitsi-secret-0123456789")
        now = datetime.now(timezone.utc)
        lc = _make_class(db, live_course, instructor, room_name="si-tok00090")
        # Ended 2h ago: scheduled_end + 30min is ~90min in the PAST.
        lc.scheduled_start = now - timedelta(hours=3)
        lc.scheduled_end = now - timedelta(hours=2)
        db.commit()
        db.refresh(lc)

        token, _jti = mint_jitsi_jwt(user=instructor, live_class=lc, moderator=True)
        claims = _decode(token, get_settings().JITSI_JWT_SECRET)

        assert claims["exp"] > int(now.timestamp()), "overtime class minted an already-expired token"
        expected_exp = int((now + timedelta(minutes=15)).timestamp())
        assert abs(claims["exp"] - expected_exp) <= 5

    def test_floor_does_not_shorten_a_future_class(self, db, monkeypatch, live_course, instructor):
        """The floor only ever raises exp: for a class ending well in the
        future the grace branch is later and must win unchanged."""
        monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "test-jitsi-secret-0123456789")
        lc = _make_class(db, live_course, instructor, room_name="si-tok00091")
        token, _jti = mint_jitsi_jwt(user=instructor, live_class=lc, moderator=True)
        claims = _decode(token, get_settings().JITSI_JWT_SECRET)

        scheduled_end = lc.scheduled_end
        if scheduled_end.tzinfo is None:
            scheduled_end = scheduled_end.replace(tzinfo=timezone.utc)
        expected_exp = int((scheduled_end + timedelta(minutes=30)).timestamp())
        assert abs(claims["exp"] - expected_exp) <= 5

    def test_jti_unique_across_two_mints(self, db, monkeypatch, live_course, instructor):
        monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "test-jitsi-secret-0123456789")
        lc = _make_class(db, live_course, instructor)
        _token1, jti1 = mint_jitsi_jwt(user=instructor, live_class=lc, moderator=True)
        _token2, jti2 = mint_jitsi_jwt(user=instructor, live_class=lc, moderator=True)
        assert jti1 != jti2

    def test_blank_secret_raises_runtime_error(self, db, monkeypatch, live_course, instructor):
        monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "")
        lc = _make_class(db, live_course, instructor)
        with pytest.raises(RuntimeError):
            mint_jitsi_jwt(user=instructor, live_class=lc, moderator=True)
