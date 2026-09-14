"""Gamification backend (Task 9 of the Learning Experience plan).

Covers docs/superpowers/specs/2026-09-02-learning-experience-design.md
section D items 1-5,7:

  - Idempotent award() on event_key (duplicate -> one event, XP once).
  - Level thresholds (spec D2: 100*n*(n+1)/2).
  - Streak advance / gap reset / milestone bonuses (spec D4).
  - Badge rule matrix (spec D3) — each seeded badge's rule is triggerable.
  - Leaderboard visibility toggle + rank + no-email leak (spec D5).
  - Best-effort isolation: award() raising never fails the host request.
  - Trigger integration: lesson complete, quiz pass, H5P completed.
  - Daily-first-activity: single award per day.
"""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
from app.models.certificate import IssuedCertificate
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment, LessonProgress
from app.models.gamification import Badge, UserBadge, UserGameStats, XpEvent
from app.models.h5p import H5PContent, H5PResult
from app.models.live_class import (
    LiveClass,
    LiveClassAttendance,
    LiveClassStatus,
    RecordingStatus,
    AttendanceSource,
)
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer, QuizAttempt, QuizAttemptAnswer
from app.services import gamification_service as game


# ----- factories (mirrors test_gradebook.py / test_h5p.py) -----------------


def _make_approved_instructor(db, make_user, email):
    from app.models.user import InstructorProfile

    instructor = make_user(role="instructor", email=email)
    profile = db.query(InstructorProfile).filter_by(user_id=instructor.id).first()
    if profile:
        profile.is_approved = True
    else:
        db.add(InstructorProfile(user_id=instructor.id, is_approved=True))
    db.commit()
    return instructor


def _make_course(db, instructor, title="Gamification Course"):
    course = Course(
        post_author=instructor.id,
        post_title=title,
        post_content="content",
        post_excerpt="excerpt",
        post_status="published",
        post_name=title.lower().replace(" ", "-"),
        course_thumbnail="",
        course_price=0,
        course_level="beginner",
        course_category="Meiporul",
        course_language="English",
        course_duration="10",
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def _enroll(db, user, course, status="enrolled"):
    e = Enrollment(course_id=course.id, user_id=user.id, enrollment_status=status)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _make_lesson(db, course, title="Lesson 1"):
    lesson = Lesson(post_author=course.post_author, post_parent=course.id, post_title=title, post_content="")
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# ============================================================================
# Core award() idempotency + level math
# ============================================================================


class TestAwardIdempotency:
    def test_same_event_key_twice_creates_one_event_and_awards_xp_once(self, db, make_user):
        student = make_user(role="student", email="idem1@example.com")

        ev1 = game.award(db, student.id, "lesson_completed", event_key="lesson:1:completed:user:%d" % student.id)
        ev2 = game.award(db, student.id, "lesson_completed", event_key="lesson:1:completed:user:%d" % student.id)

        assert ev1 is not None
        assert ev2 is None  # duplicate -> no-op

        count = db.query(XpEvent).filter(
            XpEvent.user_id == student.id, XpEvent.event_type == "lesson_completed"
        ).count()
        assert count == 1

        stats = db.query(UserGameStats).filter_by(user_id=student.id).first()
        assert stats.total_xp == game.DEFAULT_POINTS["lesson_completed"] + game.DEFAULT_POINTS["daily_first_activity"]

    def test_explicit_points_override_default(self, db, make_user):
        student = make_user(role="student", email="idem2@example.com")
        ev = game.award(db, student.id, "quiz_passed", event_key=f"custom:{student.id}", points=42)
        assert ev.points == 42


class TestAwardTransactionOwnership:
    """H1 review fix regression coverage: award() must never own the
    caller's transaction boundary. It only flush()es; the CALLER commits.
    Proves the exact failure mode the reviewer found live: a caller
    mutates state, calls award(), and then the CALLER's own commit fails —
    the caller's mutation and the XpEvent must BOTH roll back together
    (atomicity), not have the XpEvent (or the caller's mutation) already
    leaked out via a premature commit inside award()."""

    def test_award_never_calls_commit(self, db, make_user, monkeypatch):
        """H1's actual contract: award() must never call db.commit() at
        all — proven by monkeypatching Session.commit to explode and
        confirming award() still returns successfully (it never reaches a
        commit call in any branch: success, duplicate-key no-op, or the
        internal failure handler)."""
        student = make_user(role="student", email="txn1@example.com")

        from sqlalchemy.orm import Session as _Session

        def _commit_boom(self):
            raise AssertionError("award() must never call db.commit() — the caller owns the transaction boundary")

        monkeypatch.setattr(_Session, "commit", _commit_boom)

        ev = game.award(db, student.id, "lesson_completed", event_key=f"txn1:{student.id}")
        assert ev is not None  # did not raise/explode via the patched commit

        # Duplicate-key no-op path must not commit either.
        ev2 = game.award(db, student.id, "lesson_completed", event_key=f"txn1:{student.id}")
        assert ev2 is None

    def test_callers_own_rollback_undoes_both_mutation_and_award_atomically(
        self, db, make_user
    ):
        """The exact scenario the reviewer proved live: a caller mutates
        its own state, calls award() (which must only flush), and then the
        CALLER's own subsequent commit fails and rolls back. Neither the
        caller's mutation nor the XpEvent may survive that rollback —
        atomicity restored (this is what H1 was about: with award() ending
        in db.commit(), the caller's mutation persisted even though the
        caller's own commit never actually succeeded)."""
        student = make_user(role="student", email="txn2@example.com")
        instructor = make_user(role="instructor", email="txn2_instr@example.com")
        course = _make_course(db, instructor, title="Txn Course")
        enrollment = _enroll(db, student, course)

        # Simulate a caller like calculate_course_progress: mutate its own
        # state, then call award() with that mutation still uncommitted.
        enrollment.course_progress_percentage = 100
        db.flush()  # visible in-session, still uncommitted — like a real caller mid-transaction

        ev = game.award(
            db, student.id, "course_completed",
            event_key=f"txn2:{student.id}",
            course_id=course.id,
        )
        assert ev is not None  # award() succeeded (flushed)

        # Now the CALLER's own commit fails (simulated) and it rolls back —
        # exactly what a real caller's `except: db.rollback()` does.
        db.rollback()

        db.refresh(enrollment)
        assert enrollment.course_progress_percentage != 100  # caller's mutation did NOT leak out
        assert db.query(XpEvent).filter_by(event_key=f"txn2:{student.id}").first() is None  # award did NOT leak out either
        assert db.query(UserGameStats).filter_by(user_id=student.id).first() is None

    def test_award_success_persists_once_caller_commits(self, db, make_user):
        """Mirror image of the above: when the caller's OWN commit succeeds
        (the normal path), award()'s flushed rows persist along with it —
        proving flush-then-caller-commit is not silently losing writes."""
        student = make_user(role="student", email="txn3@example.com")

        ev = game.award(db, student.id, "lesson_completed", event_key=f"txn3:{student.id}")
        assert ev is not None
        db.commit()  # the caller's own commit — award() itself never called this

        stats = db.query(UserGameStats).filter_by(user_id=student.id).first()
        assert stats is not None
        assert stats.total_xp > 0
        assert db.query(XpEvent).filter_by(event_key=f"txn3:{student.id}").first() is not None


class TestLevelMath:
    @pytest.mark.parametrize("level,expected_xp", [
        (1, 100),
        (2, 300),
        (3, 600),
        (4, 1000),
        (5, 1500),
    ])
    def test_xp_for_level_thresholds(self, level, expected_xp):
        assert game.xp_for_level(level) == expected_xp

    @pytest.mark.parametrize("xp,expected_level", [
        (0, 0),
        (99, 0),
        (100, 1),
        (299, 1),
        (300, 2),
        (599, 2),
        (600, 3),
        (1499, 4),
        (1500, 5),
    ])
    def test_level_from_xp_boundaries(self, xp, expected_level):
        assert game.level_from_xp(xp) == expected_level

    def test_level_progress_shape(self):
        progress = game.level_progress(150)
        assert progress["level"] == 1
        assert progress["current_level_floor_xp"] == 100
        assert progress["next_level_xp"] == 300
        assert progress["xp_into_level"] == 50
        assert progress["xp_to_next_level"] == 150
        assert 0 < progress["progress_fraction"] < 1


# ============================================================================
# Streaks (spec D4)
# ============================================================================


class TestStreaks:
    def test_streak_advances_on_consecutive_days(self, db, make_user):
        student = make_user(role="student", email="streak1@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()

        day1 = date(2026, 1, 1)
        day2 = date(2026, 1, 2)
        day3 = date(2026, 1, 3)

        game.touch_streak(db, stats, on_date=day1)
        assert stats.current_streak == 1
        game.touch_streak(db, stats, on_date=day2)
        assert stats.current_streak == 2
        game.touch_streak(db, stats, on_date=day3)
        assert stats.current_streak == 3
        assert stats.longest_streak == 3

    def test_streak_resets_on_gap(self, db, make_user):
        student = make_user(role="student", email="streak2@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()

        game.touch_streak(db, stats, on_date=date(2026, 1, 1))
        game.touch_streak(db, stats, on_date=date(2026, 1, 2))
        assert stats.current_streak == 2

        # Gap of 3 days -> reset to 1.
        game.touch_streak(db, stats, on_date=date(2026, 1, 5))
        assert stats.current_streak == 1
        assert stats.longest_streak == 2  # preserved

    def test_same_day_touch_is_noop(self, db, make_user):
        student = make_user(role="student", email="streak3@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()

        game.touch_streak(db, stats, on_date=date(2026, 1, 1))
        assert stats.current_streak == 1
        game.touch_streak(db, stats, on_date=date(2026, 1, 1))
        assert stats.current_streak == 1  # unchanged

    @pytest.mark.parametrize("streak_len,bonus", [(7, 50), (30, 200), (100, 500)])
    def test_streak_milestones_award_bonus(self, db, make_user, streak_len, bonus):
        student = make_user(role="student", email=f"streak_milestone{streak_len}@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()

        base_day = date(2026, 1, 1)
        events = []
        for i in range(streak_len):
            events = game.touch_streak(db, stats, on_date=base_day + timedelta(days=i))
        db.commit()

        assert stats.current_streak == streak_len
        assert len(events) == 1
        assert events[0].points == bonus

        milestone_key = f"streak:{streak_len}:user:{student.id}"
        row = db.query(XpEvent).filter_by(event_key=milestone_key).first()
        assert row is not None
        assert row.points == bonus

    def test_get_streak_for_user_returns_none_without_stats_row(self, db, make_user):
        student = make_user(role="student", email="streak_none@example.com")
        assert game.get_streak_for_user(db, student.id) is None

    def test_get_streak_for_user_reads_stats_row(self, db, make_user):
        student = make_user(role="student", email="streak_read@example.com")
        game.award(db, student.id, "lesson_completed", event_key=f"lesson:x:user:{student.id}")
        streaks = game.get_streak_for_user(db, student.id)
        assert streaks == {"current_streak": 1, "longest_streak": 1}

    def test_get_streak_for_user_zeroes_current_streak_when_stale(self, db, make_user):
        """M1 review fix: a current_streak from 60 days ago must read as 0
        (dead) — UserGameStats.current_streak is only ever mutated by the
        NEXT touch_streak call, so without this the value would sit stale
        forever once a user stops being active, regressing the behavior of
        the retired _compute_streaks (which zeroed a broken streak)."""
        student = make_user(role="student", email="streak_stale@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()

        long_ago = date(2025, 1, 1)
        game.touch_streak(db, stats, on_date=long_ago)
        game.touch_streak(db, stats, on_date=long_ago + timedelta(days=1))
        db.commit()
        assert stats.current_streak == 2  # sanity: streak WAS built up

        streaks = game.get_streak_for_user(db, student.id)
        assert streaks["current_streak"] == 0  # stale -> dead
        assert streaks["longest_streak"] == 2  # historical high-water mark preserved

    def test_get_streak_for_user_still_alive_yesterday(self, db, make_user):
        """The boundary case: exactly one day since last activity must
        still read as alive (matches touch_streak's own advance-on-gap==1
        semantics and the retired _compute_streaks' "today or yesterday"
        rule)."""
        student = make_user(role="student", email="streak_yesterday@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()

        yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
        game.touch_streak(db, stats, on_date=yesterday)
        db.commit()

        streaks = game.get_streak_for_user(db, student.id)
        assert streaks["current_streak"] == 1

    def test_dashboard_streak_read_reflects_staleness(self, db, make_user):
        """dashboard.py's _get_streaks routes through get_streak_for_user —
        confirms the M1 fix is visible through that call path too, not just
        the service function directly."""
        from app.routers.dashboard import _get_streaks

        student = make_user(role="student", email="streak_dashboard@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()
        game.touch_streak(db, stats, on_date=date(2025, 1, 1))
        db.commit()

        streaks = _get_streaks(db, student.id, active_days=[])
        assert streaks["current_streak"] == 0

    def test_superadmin_streak_map_reflects_staleness(self, client, db, make_user):
        """superadmin.py's bulk streak_map query inlines the same
        staleness rule (it bypasses get_streak_for_user for N+1 avoidance)
        — confirms that inlined copy agrees with the service function."""
        import pyotp
        from app.core import totp

        admin = make_user(role="superadmin", email="streak_admin@example.com")
        admin.totp_enabled = True
        admin.totp_secret = totp.generate_secret()
        db.commit()
        admin_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": admin.user_email,
                "password": admin._test_password,
                "otp_code": pyotp.TOTP(admin.totp_secret).now(),
            },
        )
        assert admin_login.status_code == 200, admin_login.text
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        student = make_user(role="student", email="streak_student_admin@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()
        game.touch_streak(db, stats, on_date=date(2025, 1, 1))
        db.commit()

        r = client.get("/api/v1/superadmin/students?limit=50", headers=admin_headers)
        assert r.status_code == 200, r.text
        items = r.json().get("items", [])
        row = next((it for it in items if it["id"] == student.id), None)
        assert row is not None
        assert row["streak_days"] == 0


# ============================================================================
# Badge rule matrix (spec D3)
# ============================================================================


class TestBadgeRules:
    def test_ensure_badges_seeds_full_catalog(self, db):
        game.ensure_badges(db)
        count = db.query(Badge).count()
        assert count == len(game.BADGE_CATALOG)

    def test_ensure_badges_is_idempotent(self, db):
        game.ensure_badges(db)
        game.ensure_badges(db)
        count = db.query(Badge).count()
        assert count == len(game.BADGE_CATALOG)

    def test_first_lesson_badge(self, db, make_user):
        student = make_user(role="student", email="badge_lesson@example.com")
        game.award(db, student.id, "lesson_completed", event_key=f"lesson:1:user:{student.id}")
        badge = db.query(Badge).filter_by(slug="first-lesson").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_five_lessons_badge(self, db, make_user):
        student = make_user(role="student", email="badge_5lessons@example.com")
        for i in range(5):
            game.award(db, student.id, "lesson_completed", event_key=f"lesson:{i}:user:{student.id}")
        badge = db.query(Badge).filter_by(slug="five-lessons").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_course_finisher_badge(self, db, make_user):
        student = make_user(role="student", email="badge_finisher@example.com")
        game.award(db, student.id, "course_completed", event_key=f"course:1:user:{student.id}")
        badge = db.query(Badge).filter_by(slug="course-finisher").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_three_courses_badge(self, db, make_user):
        student = make_user(role="student", email="badge_3courses@example.com")
        for i in range(3):
            game.award(db, student.id, "course_completed", event_key=f"course:{i}:user:{student.id}")
        badge = db.query(Badge).filter_by(slug="three-courses").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_quiz_ace_badge(self, db, make_user):
        student = make_user(role="student", email="badge_quizace@example.com")
        for i in range(5):
            game.award(db, student.id, "quiz_passed_bonus", event_key=f"quizbonus:{i}:user:{student.id}")
        badge = db.query(Badge).filter_by(slug="quiz-ace").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_streak_7_badge(self, db, make_user):
        student = make_user(role="student", email="badge_streak7@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()
        base_day = date(2026, 2, 1)
        for i in range(7):
            game.touch_streak(db, stats, on_date=base_day + timedelta(days=i))
        game._evaluate_badges(db, student.id, stats)
        db.commit()
        badge = db.query(Badge).filter_by(slug="streak-7").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_early_bird_badge(self, db, make_user):
        student = make_user(role="student", email="badge_earlybird@example.com")
        ev = XpEvent(
            user_id=student.id, event_key=f"manual:earlybird:{student.id}",
            event_type="lesson_completed", points=10,
        )
        db.add(ev)
        db.flush()
        ev.created_at = datetime(2026, 1, 1, 5, 30, tzinfo=timezone.utc)  # 5:30am
        db.commit()
        stats = game._get_or_create_stats(db, student.id)
        db.commit()
        game._evaluate_badges(db, student.id, stats)
        db.commit()
        badge = db.query(Badge).filter_by(slug="early-bird").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_night_owl_badge(self, db, make_user):
        student = make_user(role="student", email="badge_nightowl@example.com")
        ev = XpEvent(
            user_id=student.id, event_key=f"manual:nightowl:{student.id}",
            event_type="lesson_completed", points=10,
        )
        db.add(ev)
        db.flush()
        ev.created_at = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)  # 11pm
        db.commit()
        stats = game._get_or_create_stats(db, student.id)
        db.commit()
        game._evaluate_badges(db, student.id, stats)
        db.commit()
        badge = db.query(Badge).filter_by(slug="night-owl").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_early_bird_boundary_not_satisfied_at_7am(self, db, make_user):
        """7:00am exactly must NOT count as early-bird (rule is < 7)."""
        student = make_user(role="student", email="badge_earlybird_boundary@example.com")
        ev = XpEvent(
            user_id=student.id, event_key=f"manual:earlybird_boundary:{student.id}",
            event_type="lesson_completed", points=10,
        )
        db.add(ev)
        db.flush()
        ev.created_at = datetime(2026, 1, 1, 7, 0, tzinfo=timezone.utc)
        db.commit()
        stats = game._get_or_create_stats(db, student.id)
        db.commit()
        game._evaluate_badges(db, student.id, stats)
        db.commit()
        badge = db.query(Badge).filter_by(slug="early-bird").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is None

    def test_utc_hour_expr_uses_plain_extract_on_sqlite(self, db):
        """M3 review fix: on SQLite (this test suite's dialect), stored
        datetimes are already-naive UTC by this codebase's convention, so
        _utc_hour_expr must use a plain EXTRACT(HOUR, ...) — never
        func.timezone(), which SQLite doesn't support and would error."""
        assert db.get_bind().dialect.name == "sqlite"
        expr = game._utc_hour_expr(db, XpEvent.created_at)
        # Must not raise when compiled/executed against SQLite.
        compiled = str(expr.compile(dialect=db.get_bind().dialect))
        assert "timezone" not in compiled.lower()

    def test_utc_hour_expr_wraps_with_timezone_utc_on_postgresql(self):
        """The Postgres branch must force an explicit UTC conversion via
        func.timezone('UTC', ...) before extracting the hour — a plain
        EXTRACT(HOUR FROM timestamptz) on Postgres implicitly converts to
        the session's `timezone` setting first, which need not be UTC."""
        from unittest.mock import MagicMock

        fake_db = MagicMock()
        fake_db.get_bind.return_value.dialect.name = "postgresql"
        expr = game._utc_hour_expr(fake_db, XpEvent.created_at)
        compiled = str(expr)
        assert "timezone" in compiled.lower()
        # The "UTC" literal is a bound parameter (shows as :timezone_1 in the
        # unparametrized SQL string), not inlined text — confirm the actual
        # bound value instead of grepping the SQL string for it.
        bound_params = expr.compile().params
        assert "UTC" in bound_params.values()

    def test_live_regular_badge(self, db, make_user):
        student = make_user(role="student", email="badge_liveregular@example.com")
        for i in range(5):
            game.award(db, student.id, "live_class_attended", event_key=f"live:{i}:user:{student.id}")
        badge = db.query(Badge).filter_by(slug="live-regular").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_h5p_explorer_badge(self, db, make_user):
        student = make_user(role="student", email="badge_h5p@example.com")
        game.award(db, student.id, "h5p_completed", event_key=f"h5p:1:user:{student.id}")
        badge = db.query(Badge).filter_by(slug="h5p-explorer").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_assignment_perfect_badge(self, db, make_user):
        student = make_user(role="student", email="badge_perfect@example.com")
        game.award(
            db, student.id, "assignment_perfect",
            event_key=f"assignment:1:perfect:user:{student.id}", points=0,
        )
        badge = db.query(Badge).filter_by(slug="assignment-perfect").first()
        earned = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).first()
        assert earned is not None

    def test_xp_level_badges(self, db, make_user):
        student = make_user(role="student", email="badge_levels@example.com")
        # 1500 XP -> level 5 -> xp-level-5 badge.
        game.award(db, student.id, "custom", event_key=f"big:{student.id}", points=1500)
        badge5 = db.query(Badge).filter_by(slug="xp-level-5").first()
        earned5 = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge5.id).first()
        assert earned5 is not None

    def test_badge_awarded_only_once(self, db, make_user):
        student = make_user(role="student", email="badge_once@example.com")
        game.award(db, student.id, "lesson_completed", event_key=f"lesson:1:user:{student.id}")
        game.award(db, student.id, "lesson_completed", event_key=f"lesson:2:user:{student.id}")
        badge = db.query(Badge).filter_by(slug="first-lesson").first()
        count = db.query(UserBadge).filter_by(user_id=student.id, badge_id=badge.id).count()
        assert count == 1


# ============================================================================
# Leaderboard (spec D5)
# ============================================================================


class TestLeaderboard:
    def test_visibility_toggle_hides_from_leaderboard(self, db, make_user):
        visible_student = make_user(role="student", email="lb_visible@example.com")
        hidden_student = make_user(role="student", email="lb_hidden@example.com")

        game.award(db, visible_student.id, "custom", event_key=f"lb1:{visible_student.id}", points=500)
        game.award(db, hidden_student.id, "custom", event_key=f"lb1:{hidden_student.id}", points=1000)

        stats = db.query(UserGameStats).filter_by(user_id=hidden_student.id).first()
        stats.leaderboard_visible = False
        db.commit()

        entries = asyncio.run(game.leaderboard(db, scope="global"))
        user_ids = {e["user_id"] for e in entries}
        assert visible_student.id in user_ids
        assert hidden_student.id not in user_ids

    def test_leaderboard_no_email_leak(self, db, make_user):
        student = make_user(role="student", email="lb_noemail@example.com")
        game.award(db, student.id, "custom", event_key=f"lb2:{student.id}", points=100)

        entries = asyncio.run(game.leaderboard(db, scope="global"))
        entry = next(e for e in entries if e["user_id"] == student.id)
        assert set(entry.keys()) == {"rank", "user_id", "display_name", "level", "total_xp"}
        for value in entry.values():
            assert "@" not in str(value)

    def test_leaderboard_ordered_by_xp_desc(self, db, make_user):
        low = make_user(role="student", email="lb_low@example.com")
        high = make_user(role="student", email="lb_high@example.com")
        game.award(db, low.id, "custom", event_key=f"lb3:{low.id}", points=50)
        game.award(db, high.id, "custom", event_key=f"lb3:{high.id}", points=5000)

        entries = asyncio.run(game.leaderboard(db, scope="global"))
        ranked_ids = [e["user_id"] for e in entries]
        assert ranked_ids.index(high.id) < ranked_ids.index(low.id)

    def test_user_rank_computed_even_when_hidden(self, db, make_user):
        student = make_user(role="student", email="lb_rank_hidden@example.com")
        game.award(db, student.id, "custom", event_key=f"lb4:{student.id}", points=10)
        stats = db.query(UserGameStats).filter_by(user_id=student.id).first()
        stats.leaderboard_visible = False
        db.commit()

        rank = game.user_rank(db, student.id, scope="global")
        assert rank is not None
        assert rank["total_xp"] == 10 + game.DEFAULT_POINTS["daily_first_activity"]

    def test_user_rank_none_without_stats(self, db, make_user):
        student = make_user(role="student", email="lb_rank_none@example.com")
        assert game.user_rank(db, student.id, scope="global") is None

    def test_course_scoped_leaderboard_filters_by_course(self, db, make_user):
        s1 = make_user(role="student", email="lb_course1@example.com")
        s2 = make_user(role="student", email="lb_course2@example.com")
        game.award(db, s1.id, "custom", event_key=f"lbc1:{s1.id}", points=10, course_id=1)
        game.award(db, s2.id, "custom", event_key=f"lbc2:{s2.id}", points=10, course_id=2)

        entries = asyncio.run(game.leaderboard(db, scope="course:1"))
        ids = {e["user_id"] for e in entries}
        assert s1.id in ids
        assert s2.id not in ids

    def test_tied_users_ranked_deterministically_by_user_id(self, db, make_user):
        """M4 review fix: two users with identical total_xp must always
        sort in the same order (user_id ASC) across repeated calls — not
        left to whatever order the DB happens to return ties in."""
        first = make_user(role="student", email="lb_tie_a@example.com")
        second = make_user(role="student", email="lb_tie_b@example.com")
        assert first.id < second.id  # make_user increments sequentially

        game.award(db, first.id, "custom", event_key=f"lbtie1:{first.id}", points=200)
        game.award(db, second.id, "custom", event_key=f"lbtie1:{second.id}", points=200)
        db.commit()

        # Verify they are in fact tied on XP (both got the same +5 daily bonus too).
        s1 = db.query(UserGameStats).filter_by(user_id=first.id).first()
        s2 = db.query(UserGameStats).filter_by(user_id=second.id).first()
        assert s1.total_xp == s2.total_xp

        entries_a = asyncio.run(game.leaderboard(db, scope="global"))
        entries_b = asyncio.run(game.leaderboard(db, scope="global"))

        def _rank_of(entries, uid):
            return next(e["rank"] for e in entries if e["user_id"] == uid)

        # Stable across repeated calls (both pull from the same live query
        # here since these two specific ids are outside the 300s cache TTL
        # window set up by an earlier test in this class — the ordering
        # guarantee is what matters, not cache-freshness).
        assert _rank_of(entries_a, first.id) < _rank_of(entries_a, second.id)
        assert _rank_of(entries_b, first.id) < _rank_of(entries_b, second.id)

    def test_user_rank_tiebreak_matches_leaderboard_tiebreak(self, db, make_user):
        """M4: user_rank's competition-rank math must agree with
        _leaderboard_query's ORDER BY total_xp DESC, user_id ASC — the
        lower-user_id member of a tied pair ranks strictly ahead of the
        higher-user_id member in BOTH code paths."""
        first = make_user(role="student", email="lb_tie_rank_a@example.com")
        second = make_user(role="student", email="lb_tie_rank_b@example.com")
        assert first.id < second.id

        game.award(db, first.id, "custom", event_key=f"lbtie2:{first.id}", points=300)
        game.award(db, second.id, "custom", event_key=f"lbtie2:{second.id}", points=300)
        db.commit()

        rank_first = game.user_rank(db, first.id, scope="global")
        rank_second = game.user_rank(db, second.id, scope="global")
        assert rank_first["total_xp"] == rank_second["total_xp"]  # confirmed tied
        assert rank_first["rank"] < rank_second["rank"]  # lower user_id ranks ahead

    def test_my_rank_matches_entries_when_user_is_in_cached_list(self, db, make_user):
        """M2 review fix: my_rank derived from the SAME `entries` list must
        report the identical rank/xp/level as that user's own row in
        `entries` — the failure mode being guarded against is my_rank
        coming from a fresh live query while entries came from a stale
        cached snapshot, which could disagree whenever XP changed between
        the two, or a tiebreak resolved differently."""
        student = make_user(role="student", email="lb_consistency@example.com")
        game.award(db, student.id, "custom", event_key=f"lbcons1:{student.id}", points=750)
        db.commit()

        entries = asyncio.run(game.leaderboard(db, scope="global"))
        my_entry = next(e for e in entries if e["user_id"] == student.id)

        my_rank = game.user_rank(db, student.id, scope="global", entries=entries)
        assert my_rank == {
            "rank": my_entry["rank"],
            "total_xp": my_entry["total_xp"],
            "level": my_entry["level"],
        }

    def test_my_rank_falls_back_to_live_query_when_not_in_entries(self, db, make_user):
        """A user outside the passed-in entries list (e.g. below the top-N,
        or entries=None) still gets a correct rank via the live
        competition-rank query fallback."""
        student = make_user(role="student", email="lb_fallback@example.com")
        game.award(db, student.id, "custom", event_key=f"lbcons2:{student.id}", points=42)
        db.commit()

        # Empty/foreign entries list -> user not present -> falls back to live query.
        my_rank = game.user_rank(db, student.id, scope="global", entries=[])
        assert my_rank is not None
        assert my_rank["total_xp"] == 42 + game.DEFAULT_POINTS["daily_first_activity"]

        # entries=None (default) behaves identically.
        my_rank_default = game.user_rank(db, student.id, scope="global")
        assert my_rank_default == my_rank

    def test_gamification_router_my_rank_consistent_with_entries(self, client, db, make_user, auth_headers):
        """End-to-end: the GET /leaderboard response's my_rank must always
        agree with this user's own row in entries when they're in it."""
        student = make_user(role="student", email="lb_api_consistency@example.com")
        game.award(db, student.id, "custom", event_key=f"lbapi1:{student.id}", points=999)
        db.commit()
        headers = auth_headers("lb_api_consistency@example.com")

        r = client.get("/api/v1/gamification/leaderboard?scope=global", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        my_entry = next(e for e in body["entries"] if e["user_id"] == student.id)
        assert body["my_rank"]["rank"] == my_entry["rank"]
        assert body["my_rank"]["total_xp"] == my_entry["total_xp"]
        assert body["my_rank"]["level"] == my_entry["level"]


# ============================================================================
# API endpoints
# ============================================================================


class TestGamificationAPI:
    def test_me_endpoint_shape(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="api_me@example.com")
        game.award(db, student.id, "lesson_completed", event_key=f"api1:{student.id}")
        headers = auth_headers("api_me@example.com")

        r = client.get("/api/v1/gamification/me", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "stats" in body and "badges" in body and "recent_events" in body
        assert body["stats"]["total_xp"] > 0

    def test_unseen_and_mark_seen_flow(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="api_unseen@example.com")
        # Trigger a badge award (badges are always unseen initially).
        game.award(db, student.id, "lesson_completed", event_key=f"api2:{student.id}")
        headers = auth_headers("api_unseen@example.com")

        r = client.get("/api/v1/gamification/me/unseen", headers=headers)
        assert r.status_code == 200, r.text
        unseen = r.json()["unseen"]
        assert len(unseen) >= 1
        ids = [e["id"] for e in unseen]

        r2 = client.post("/api/v1/gamification/me/unseen/mark-seen", json={"event_ids": ids}, headers=headers)
        assert r2.status_code == 200, r2.text
        assert r2.json()["updated"] == len(ids)

        r3 = client.get("/api/v1/gamification/me/unseen", headers=headers)
        assert r3.json()["unseen"] == []

    def test_settings_toggle_visibility(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="api_settings@example.com")
        headers = auth_headers("api_settings@example.com")

        r = client.post("/api/v1/gamification/me/settings", json={"leaderboard_visible": False}, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["leaderboard_visible"] is False

        stats = db.query(UserGameStats).filter_by(user_id=student.id).first()
        assert stats.leaderboard_visible is False

    def test_leaderboard_endpoint_includes_my_rank(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="api_leaderboard@example.com")
        game.award(db, student.id, "custom", event_key=f"api3:{student.id}", points=20)
        headers = auth_headers("api_leaderboard@example.com")

        r = client.get("/api/v1/gamification/leaderboard?scope=global", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["scope"] == "global"
        assert body["my_rank"] is not None
        assert "entries" in body

    def test_leaderboard_invalid_scope_rejected(self, client, make_user, auth_headers):
        make_user(role="student", email="api_badscope@example.com")
        headers = auth_headers("api_badscope@example.com")
        r = client.get("/api/v1/gamification/leaderboard?scope=nonsense", headers=headers)
        assert r.status_code == 400


# ============================================================================
# Trigger integration + best-effort isolation
# ============================================================================


class TestTriggerIntegration:
    def test_lesson_complete_creates_xp_event(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "trig_instr1@example.com")
        student = make_user(role="student", email="trig_student1@example.com")
        course = _make_course(db, instructor)
        lesson = _make_lesson(db, course)
        _enroll(db, student, course)
        headers = auth_headers("trig_student1@example.com")

        r = client.post(f"/api/v1/courses/{course.id}/lessons/{lesson.id}/complete", headers=headers)
        assert r.status_code == 200, r.text

        ev = db.query(XpEvent).filter_by(
            user_id=student.id, event_type="lesson_completed"
        ).first()
        assert ev is not None
        assert ev.points == game.DEFAULT_POINTS["lesson_completed"]

    def test_one_lesson_course_completion_reports_correctly_same_request(
        self, client, db, make_user, auth_headers, monkeypatch
    ):
        """Regression test for the reorder-introduced bug: completing the
        ONLY lesson of a one-lesson course must report completed_lessons=1,
        progress_percentage=100, course_completed=true IN THE SAME RESPONSE
        (not just on a later re-query), a certificate must be issued, and
        the course_completed XP event must exist. Before the db.flush()
        fix, calculate_course_progress's own fresh SELECT over
        LessonProgress missed the just-added row (autoflush=False), so this
        response read 0%/no completion/no certificate despite the
        LessonProgress row being correctly committed moments later."""
        from app.services.certificate_service import CertificateService

        monkeypatch.setattr(CertificateService, "_generate_pdf", lambda data, path: None)
        monkeypatch.setattr(CertificateService, "warm_render_cache", lambda certificate: None)

        instructor = _make_approved_instructor(db, make_user, "trig_instr_1lesson@example.com")
        student = make_user(role="student", email="trig_student_1lesson@example.com")
        course = _make_course(db, instructor, title="One Lesson Course")
        lesson = _make_lesson(db, course)
        _enroll(db, student, course)
        headers = auth_headers("trig_student_1lesson@example.com")

        r = client.post(f"/api/v1/courses/{course.id}/lessons/{lesson.id}/complete", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()

        assert body["completed_lessons"] == 1
        assert body["progress_percentage"] == 100
        assert body["course_completed"] is True

        cert = db.query(IssuedCertificate).filter_by(user_id=student.id, course_id=course.id).first()
        assert cert is not None

        ev = db.query(XpEvent).filter_by(user_id=student.id, event_type="course_completed").first()
        assert ev is not None
        assert ev.points == game.DEFAULT_POINTS["course_completed"]

    def test_two_lesson_course_first_completion_reports_50_percent(
        self, client, db, make_user, auth_headers
    ):
        """A two-lesson course's FIRST lesson completion must report
        completed_lessons=1 / progress_percentage=50 in that same
        response — not 0, and not prematurely 100."""
        instructor = _make_approved_instructor(db, make_user, "trig_instr_2lesson@example.com")
        student = make_user(role="student", email="trig_student_2lesson@example.com")
        course = _make_course(db, instructor, title="Two Lesson Course")
        lesson1 = _make_lesson(db, course, title="Lesson 1")
        _make_lesson(db, course, title="Lesson 2")
        _enroll(db, student, course)
        headers = auth_headers("trig_student_2lesson@example.com")

        r = client.post(f"/api/v1/courses/{course.id}/lessons/{lesson1.id}/complete", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()

        assert body["completed_lessons"] == 1
        assert body["progress_percentage"] == 50
        assert body["course_completed"] is False

    def test_quiz_pass_creates_xp_event(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "trig_instr2@example.com")
        student = make_user(role="student", email="trig_student2@example.com")
        course = _make_course(db, instructor)
        quiz = Quiz(post_author=instructor.id, post_parent=course.id, post_title="Q", quiz_passing_grade=50)
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        question = QuizQuestion(
            quiz_id=quiz.id, question_title="Pick one",
            question_type="multiple_choice", question_mark=10.0,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        db.add_all([
            QuizQuestionAnswer(belongs_question_id=question.question_id, answer_title="A", is_correct=True, answer_order=0),
            QuizQuestionAnswer(belongs_question_id=question.question_id, answer_title="B", is_correct=False, answer_order=1),
        ])
        db.commit()
        _enroll(db, student, course)
        headers = auth_headers("trig_student2@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["passed"] is True

        ev = db.query(XpEvent).filter_by(user_id=student.id, event_type="quiz_passed").first()
        assert ev is not None

    def test_h5p_completed_creates_xp_event(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "trig_instr3@example.com")
        student = make_user(role="student", email="trig_student3@example.com")
        course = _make_course(db, instructor)

        from app.services.h5p_service import generate_public_id
        content = H5PContent(
            public_id=generate_public_id(), owner_id=instructor.id,
            title="Interactive", library="H5P.InteractiveVideo 1.22",
            size_bytes=100, status="ready",
        )
        db.add(content)
        db.commit()
        db.refresh(content)

        lesson = Lesson(
            post_author=instructor.id, post_parent=course.id, post_title="H5P Lesson",
            post_content="", lesson_content_type="h5p", h5p_content_id=content.id,
        )
        db.add(lesson)
        db.commit()

        _enroll(db, student, course)
        headers = auth_headers("trig_student3@example.com")

        r = client.post(
            f"/api/v1/h5p/{content.public_id}/result",
            json={"completed": True, "score": 8, "max_score": 10},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        ev = db.query(XpEvent).filter_by(user_id=student.id, event_type="h5p_completed").first()
        assert ev is not None
        assert ev.points == game.DEFAULT_POINTS["h5p_completed"]

    def test_h5p_result_update_does_not_double_award(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "trig_instr4@example.com")
        student = make_user(role="student", email="trig_student4@example.com")
        course = _make_course(db, instructor)

        from app.services.h5p_service import generate_public_id
        content = H5PContent(
            public_id=generate_public_id(), owner_id=instructor.id,
            title="Interactive", library="H5P.InteractiveVideo 1.22",
            size_bytes=100, status="ready",
        )
        db.add(content)
        db.commit()
        db.refresh(content)
        lesson = Lesson(
            post_author=instructor.id, post_parent=course.id, post_title="H5P Lesson",
            post_content="", lesson_content_type="h5p", h5p_content_id=content.id,
        )
        db.add(lesson)
        db.commit()
        _enroll(db, student, course)
        headers = auth_headers("trig_student4@example.com")

        client.post(f"/api/v1/h5p/{content.public_id}/result", json={"completed": True}, headers=headers)
        client.post(f"/api/v1/h5p/{content.public_id}/result", json={"completed": True}, headers=headers)

        count = db.query(XpEvent).filter_by(user_id=student.id, event_type="h5p_completed").count()
        assert count == 1

    def test_award_failure_never_fails_lesson_complete(self, client, db, make_user, auth_headers, monkeypatch):
        instructor = _make_approved_instructor(db, make_user, "trig_instr5@example.com")
        student = make_user(role="student", email="trig_student5@example.com")
        course = _make_course(db, instructor)
        lesson = _make_lesson(db, course)
        enrollment = _enroll(db, student, course)
        headers = auth_headers("trig_student5@example.com")

        import app.routers.courses as courses_module

        def _boom(*args, **kwargs):
            raise RuntimeError("gamification service exploded")

        monkeypatch.setattr("app.services.gamification_service.award", _boom)

        r = client.post(f"/api/v1/courses/{course.id}/lessons/{lesson.id}/complete", headers=headers)
        assert r.status_code == 200, r.text

        # L1 review fix: the exploded award() must not have taken the
        # lesson-completion write down with it. Query via a fresh read
        # (expire_all forces a real re-SELECT, not stale identity-map data)
        # to prove the completion is actually durable — committed to the
        # database, not merely uncommitted-but-visible.
        db.expire_all()
        progress = db.query(LessonProgress).filter_by(
            enrollment_id=enrollment.id, lesson_id=lesson.id
        ).first()
        assert progress is not None
        assert progress.progress_status == "completed"
        assert progress.completion_date is not None

        # Now that the db.flush() fix (mark_lesson_complete, right before
        # calculate_course_progress) makes this handler's own pending
        # writes visible to its own next read, the full progress
        # computation is also intact despite award() exploding —
        # completed_lessons/progress_percentage in the SAME response, not
        # just on a later re-query.
        db.refresh(enrollment)
        assert enrollment.total_lessons == 1
        assert enrollment.completed_lessons == 1
        assert enrollment.course_progress_percentage == 100

        # And no gamification row leaked out despite the exception either.
        assert db.query(XpEvent).filter_by(
            user_id=student.id, event_type="lesson_completed"
        ).first() is None

    def test_live_class_finalize_attendance_awards_present_only(self, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "trig_instr6@example.com")
        present_student = make_user(role="student", email="trig_present@example.com")
        absent_student = make_user(role="student", email="trig_absent@example.com")
        course = _make_course(db, instructor)

        now = datetime.now(timezone.utc)
        live_class = LiveClass(
            course_id=course.id,
            instructor_id=instructor.id,
            title="Live Session",
            scheduled_start=now - timedelta(hours=1),
            scheduled_end=now,
            room_name="room-trig-1",
            status=LiveClassStatus.LIVE,
            settings={"attendance_threshold_pct": 60},
        )
        db.add(live_class)
        db.commit()
        db.refresh(live_class)

        db.add_all([
            LiveClassAttendance(
                class_id=live_class.id, user_id=present_student.id,
                source=AttendanceSource.WEB, accumulated_seconds=3000,  # >= 60% of 3600s
            ),
            LiveClassAttendance(
                class_id=live_class.id, user_id=absent_student.id,
                source=AttendanceSource.WEB, accumulated_seconds=100,
            ),
        ])
        db.commit()

        from app.services.live_class_service import finalize_attendance, award_attendance_xp
        finalize_attendance(db, live_class)
        db.commit()
        # H1 review fix: gamification is awarded AFTER finalize_attendance's
        # own commit, via the separate award_attendance_xp step (mirrors
        # live_class_session.py's end_class / live_class_attendance.py's
        # recompute_attendance call order).
        award_attendance_xp(db, live_class)

        present_ev = db.query(XpEvent).filter_by(user_id=present_student.id, event_type="live_class_attended").first()
        absent_ev = db.query(XpEvent).filter_by(user_id=absent_student.id, event_type="live_class_attended").first()
        assert present_ev is not None
        assert present_ev.points == game.DEFAULT_POINTS["live_class_attended"]
        assert absent_ev is None

    def test_course_completion_awards_xp_once(self, db, make_user):
        instructor = _make_approved_instructor(db, make_user, "trig_instr7@example.com")
        student = make_user(role="student", email="trig_course_complete@example.com")
        course = _make_course(db, instructor)
        lesson = _make_lesson(db, course)
        enrollment = _enroll(db, student, course)

        db.add(LessonProgress(
            user_id=student.id, course_id=course.id, lesson_id=lesson.id,
            enrollment_id=enrollment.id, progress_status="completed",
            completion_date=datetime.now(timezone.utc),
        ))
        db.commit()

        from app.services.course_service import CourseService
        CourseService.calculate_course_progress(db, enrollment)

        ev = db.query(XpEvent).filter_by(user_id=student.id, event_type="course_completed").first()
        assert ev is not None
        assert ev.points == game.DEFAULT_POINTS["course_completed"]

        # Recalculating again (already completed) must not double-award.
        CourseService.calculate_course_progress(db, enrollment)
        count = db.query(XpEvent).filter_by(user_id=student.id, event_type="course_completed").count()
        assert count == 1

    def test_assignment_submit_and_grade_award_xp(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "trig_instr8@example.com")
        student = make_user(role="student", email="trig_assign@example.com")
        course = _make_course(db, instructor)
        assignment = Assignment(
            course_id=course.id, created_by=instructor.id, title="HW1",
            status="published", total_points=100,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        _enroll(db, student, course)

        student_headers = auth_headers("trig_assign@example.com")
        instr_headers = auth_headers("trig_instr8@example.com")

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "my work", "files": []},
            headers=student_headers,
        )
        assert r.status_code == 200, r.text
        submitted_ev = db.query(XpEvent).filter_by(user_id=student.id, event_type="assignment_submitted").first()
        assert submitted_ev is not None

        submission = db.query(AssignmentSubmission).filter_by(assignment_id=assignment.id, user_id=student.id).first()
        r2 = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={"grade": 80, "feedback": "Good"},
            headers=instr_headers,
        )
        assert r2.status_code == 200, r2.text
        graded_ev = db.query(XpEvent).filter_by(user_id=student.id, event_type="assignment_graded_pass").first()
        assert graded_ev is not None


# ============================================================================
# Video-watch completion path (review finding I3)
# ============================================================================


class TestVideoThresholdXP:
    """Crossing the 90% watch threshold in /api/v1/progress/save is a real
    lesson completion and must award the same lesson XP the explicit
    'mark complete' button awards — and the two paths must converge to
    exactly ONE award because they share an event_key."""

    def test_video_threshold_completion_creates_lesson_xp(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "vid_instr@example.com")
        student = make_user(role="student", email="vid_student@example.com")
        course = _make_course(db, instructor, title="Video Course")
        lesson = _make_lesson(db, course, title="Video Lesson")
        _enroll(db, student, course)
        headers = auth_headers("vid_student@example.com")

        # 95% watched — past VIDEO_COMPLETION_THRESHOLD (0.9)
        r = client.post(
            "/api/v1/progress/save",
            json={
                "lesson_id": lesson.id,
                "course_id": course.id,
                "watched_seconds": 95,
                "total_seconds": 100,
            },
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["completed"] is True

        ev = db.query(XpEvent).filter_by(
            user_id=student.id,
            event_key=f"lesson:{lesson.id}:completed:user:{student.id}",
        ).first()
        assert ev is not None, "video-threshold completion awarded no lesson XP"
        assert ev.event_type == "lesson_completed"

    def test_video_threshold_then_explicit_complete_does_not_double_award(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "vid_instr2@example.com")
        student = make_user(role="student", email="vid_student2@example.com")
        course = _make_course(db, instructor, title="Video Course 2")
        lesson = _make_lesson(db, course, title="Video Lesson 2")
        _enroll(db, student, course)
        headers = auth_headers("vid_student2@example.com")

        client.post(
            "/api/v1/progress/save",
            json={
                "lesson_id": lesson.id,
                "course_id": course.id,
                "watched_seconds": 95,
                "total_seconds": 100,
            },
            headers=headers,
        )
        client.post(
            f"/api/v1/courses/{course.id}/lessons/{lesson.id}/complete",
            headers=headers,
        )

        events = db.query(XpEvent).filter_by(
            user_id=student.id,
            event_key=f"lesson:{lesson.id}:completed:user:{student.id}",
        ).all()
        assert len(events) == 1, (
            "video-watch and button completion must share one event_key and "
            f"award once, got {len(events)} events"
        )

    def test_below_threshold_awards_nothing(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "vid_instr3@example.com")
        student = make_user(role="student", email="vid_student3@example.com")
        course = _make_course(db, instructor, title="Video Course 3")
        lesson = _make_lesson(db, course, title="Video Lesson 3")
        _enroll(db, student, course)
        headers = auth_headers("vid_student3@example.com")

        r = client.post(
            "/api/v1/progress/save",
            json={
                "lesson_id": lesson.id,
                "course_id": course.id,
                "watched_seconds": 50,
                "total_seconds": 100,
            },
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["completed"] is False

        ev = db.query(XpEvent).filter_by(
            user_id=student.id,
            event_key=f"lesson:{lesson.id}:completed:user:{student.id}",
        ).first()
        assert ev is None


# ============================================================================
# Quiz XP farming (review finding M4)
# ============================================================================


class TestQuizPassXPKeying:
    """The quiz-pass award is keyed on (quiz, user), NOT on the attempt, so a
    pass is worth XP once ever. A per-attempt key let a student farm unbounded
    XP simply by re-taking a quiz they had already passed."""

    def _build_quiz(self, db, instructor, course, passing_grade=50):
        quiz = Quiz(
            post_author=instructor.id,
            post_parent=course.id,
            post_title="Farmable Quiz",
            post_content="",
            quiz_passing_grade=passing_grade,
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        question = QuizQuestion(
            quiz_id=quiz.id, question_title="Pick one",
            question_type="multiple_choice", question_mark=10.0,
        )
        db.add(question)
        db.commit()
        db.refresh(question)
        db.add_all([
            QuizQuestionAnswer(belongs_question_id=question.question_id, answer_title="A", is_correct=True, answer_order=0),
            QuizQuestionAnswer(belongs_question_id=question.question_id, answer_title="B", is_correct=False, answer_order=1),
        ])
        db.commit()
        return quiz, question

    def test_quiz_pass_event_key_is_per_quiz_not_per_attempt(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "qkey_instr@example.com")
        student = make_user(role="student", email="qkey_student@example.com")
        course = _make_course(db, instructor, title="Quiz Key Course")
        quiz, question = self._build_quiz(db, instructor, course)
        _enroll(db, student, course)
        headers = auth_headers("qkey_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["passed"] is True

        ev = db.query(XpEvent).filter_by(
            user_id=student.id,
            event_key=f"quiz:{quiz.id}:passed:user:{student.id}",
        ).first()
        assert ev is not None, (
            "quiz pass must be keyed quiz:{id}:passed:user:{uid} — a "
            "per-attempt key allows unbounded XP farming by re-taking"
        )

    def test_retaking_a_passed_quiz_awards_no_additional_xp(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "qkey_instr2@example.com")
        student = make_user(role="student", email="qkey_student2@example.com")
        course = _make_course(db, instructor, title="Quiz Key Course 2")
        quiz, question = self._build_quiz(db, instructor, course)
        _enroll(db, student, course)
        headers = auth_headers("qkey_student2@example.com")

        for _ in range(3):
            client.post(
                f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
                json={"answers": {str(question.question_id): 0}},
                headers=headers,
            )

        events = db.query(XpEvent).filter_by(
            user_id=student.id, event_type="quiz_passed",
        ).all()
        assert len(events) == 1, (
            f"re-taking a passed quiz farmed extra XP: {len(events)} events"
        )


# ============================================================================
# Daily-first-activity (spec D1)
# ============================================================================


class TestDailyFirstActivity:
    def test_single_daily_award_per_day_across_multiple_events(self, db, make_user):
        student = make_user(role="student", email="daily1@example.com")
        game.award(db, student.id, "lesson_completed", event_key=f"daily1a:{student.id}")
        game.award(db, student.id, "lesson_completed", event_key=f"daily1b:{student.id}")

        daily_count = db.query(XpEvent).filter_by(
            user_id=student.id, event_type="daily_first_activity"
        ).count()
        assert daily_count == 1

        lesson_events = db.query(XpEvent).filter_by(
            user_id=student.id, event_type="lesson_completed"
        ).count()
        assert lesson_events == 2

    def test_daily_award_repeats_on_new_day(self, db, make_user):
        student = make_user(role="student", email="daily2@example.com")
        stats = game._get_or_create_stats(db, student.id)
        db.commit()

        ev1 = XpEvent(
            user_id=student.id, event_key=f"daily2a:{student.id}",
            event_type="lesson_completed", points=10,
        )
        db.add(ev1)
        db.flush()
        ev1.created_at = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        stats.total_xp = 10
        db.commit()
        game.touch_streak(db, stats, on_date=date(2026, 1, 1))
        db.add(XpEvent(
            user_id=student.id, event_key=f"daily:2026-01-01:user:{student.id}",
            event_type="daily_first_activity", points=5,
        ))
        db.commit()

        # Now a fresh award() call on a later day should grant a new daily bonus.
        game.award(db, student.id, "lesson_completed", event_key=f"daily2b:{student.id}")
        daily_count = db.query(XpEvent).filter_by(
            user_id=student.id, event_type="daily_first_activity"
        ).count()
        assert daily_count == 2
