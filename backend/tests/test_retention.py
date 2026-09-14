"""Roadmap item 3 — learner retention loop: streak nudge (once per day),
near-certificate prompt (once per course), 7-day re-engagement (once per
14 days), weekly digest (once per 7 days, silent when nothing happened).
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.course import Course
from app.models.enrollment import Enrollment, LessonProgress
from app.models.gamification import UserGameStats, XpEvent
from app.models.notification import Notification


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="ret2-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def course(db, instructor):
    c = Course(post_title="Retention course", post_content="d", post_excerpt="p", post_status="publish", post_author=instructor.id, course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _types(db, uid):
    return sorted(n.type for n in db.query(Notification).filter(Notification.user_id == uid).all())


def test_streak_nudge_once_per_day(db, student_user):
    from app.services.retention_service import retention_pass
    now = datetime.now(timezone.utc)
    db.add(UserGameStats(user_id=student_user.id, total_xp=10, current_streak=4, longest_streak=4, last_active_date=(now - timedelta(days=1)).date()))
    db.commit()
    assert retention_pass(db, now)["streak_nudge"] == 1
    assert retention_pass(db, now)["streak_nudge"] == 0
    n = db.query(Notification).filter(Notification.type == "streak_nudge").one()
    assert "4-day streak" in n.title


def test_near_certificate_once_per_course(db, course, student_user):
    from app.services.retention_service import retention_pass
    db.add(Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled", course_progress_percentage=85, total_lessons=10, completed_lessons=8))
    db.commit()
    r = retention_pass(db)
    assert r["near_certificate"] == 1
    n = db.query(Notification).filter(Notification.type == "near_certificate").one()
    assert "85%" in n.title and "2 lessons to go" in n.message and n.related_id == course.id
    assert retention_pass(db)["near_certificate"] == 0


def test_reengage_after_a_quiet_week(db, course, student_user, make_user):
    from app.services.retention_service import retention_pass
    now = datetime.now(timezone.utc)
    active = make_user(role="student", email="ret2-active@example.com")
    for u in (student_user, active):
        db.add(Enrollment(user_id=u.id, course_id=course.id, enrollment_status="enrolled", enrollment_date=now - timedelta(days=20), course_progress_percentage=20))
    db.commit()
    enr_active = db.query(Enrollment).filter(Enrollment.user_id == active.id).one()
    from app.models.course import Lesson
    lesson = Lesson(post_author=course.post_author, post_parent=course.id, post_title="L", post_status="publish", post_type="lesson")
    db.add(lesson)
    db.commit()
    db.add(LessonProgress(user_id=active.id, course_id=course.id, lesson_id=lesson.id, enrollment_id=enr_active.id, progress_status="started", updated_at=now - timedelta(days=1)))
    db.commit()
    r = retention_pass(db, now)
    assert r["reengage"] == 1
    assert _types(db, student_user.id) == ["reengage"] and "reengage" not in _types(db, active.id)
    assert retention_pass(db, now)["reengage"] == 0                       # 14-day cool-down
    # 15 days later both learners have been quiet for a week: the first one is
    # nudged again (cool-down passed) and the once-active one for the first time.
    assert retention_pass(db, now + timedelta(days=15))["reengage"] == 2
    assert _types(db, student_user.id) == ["reengage", "reengage"]


def test_weekly_digest_is_silent_without_activity(db, course, student_user, make_user):
    from app.services.retention_service import retention_pass
    now = datetime.now(timezone.utc)
    quiet = make_user(role="student", email="ret2-quiet@example.com")
    for u in (student_user, quiet):
        db.add(Enrollment(user_id=u.id, course_id=course.id, enrollment_status="enrolled", enrollment_date=now - timedelta(days=1)))
    db.add(XpEvent(user_id=student_user.id, event_key=f"lesson:1:completed:user:{student_user.id}", event_type="lesson_completed", points=10, created_at=now - timedelta(days=2)))
    db.commit()
    r = retention_pass(db, now)
    assert r["weekly_digest"] == 1
    n = db.query(Notification).filter(Notification.type == "weekly_digest").one()
    assert n.user_id == student_user.id and "10 XP" in n.message
    assert retention_pass(db, now)["weekly_digest"] == 0



@pytest.mark.parametrize("learners,hot_count,expected", [(3, 3, 2), (2, 3, 0), (3, 1, 0)])
def test_hot_segments_threshold_and_editor_cooldown(db, course, make_user, learners, hot_count, expected):
    from app.models.course import Lesson
    from app.models.course_ops import CourseCollaborator
    from app.services.learning_signals_service import ingest
    from app.services.retention_service import hot_segment_alerts
    editor = make_user(role="instructor", email="hot-collab@example.com")
    db.add(CourseCollaborator(course_id=course.id, user_id=editor.id))
    lesson = Lesson(post_parent=course.id, post_author=course.post_author, post_title="Hot lesson", post_type="lesson")
    db.add(lesson)
    db.commit()
    for i in range(learners):
        u = make_user(role="student", email=f"ret-hot{i}@example.com")
        ingest(db, u.id, [{"kind": "video_rewind", "lesson_id": lesson.id, "position_s": 200}] * hot_count +
               [{"kind": "video_rewind", "lesson_id": lesson.id, "position_s": pos} for pos in (10, 20)])
    assert hot_segment_alerts(db) == expected
    assert hot_segment_alerts(db) == 0
    rows = db.query(Notification).filter(Notification.type == "hot_segment").all()
    assert len(rows) == expected
    if expected:
        assert {r.user_id for r in rows} == {course.post_author, editor.id}
        assert all("segment=20" in r.link for r in rows)



def test_alert_cooldown_is_per_segment_and_old_events_expire(db, course, make_user):
    from app.models.course import Lesson
    from app.models.learning_signals import LearningSignal
    from app.services.learning_signals_service import ingest
    from app.services.retention_service import hot_segment_alerts
    lesson = Lesson(post_parent=course.id, post_author=course.post_author, post_title="Two hotspots", post_type="lesson")
    db.add(lesson)
    db.commit()
    for i in range(3):
        u = make_user(role="student", email=f"twohot{i}@example.com")
        events = [{"kind": "video_rewind", "lesson_id": lesson.id, "position_s": p} for p in (10, 20, 30)]
        for pos in (200, 400):
            events += [{"kind": "video_rewind", "lesson_id": lesson.id, "position_s": pos}] * 4
        ingest(db, u.id, events)
    assert hot_segment_alerts(db) == 2
    assert hot_segment_alerts(db) == 0
    db.query(Notification).filter(Notification.type == "hot_segment").update({"created_at": datetime.now(timezone.utc) - timedelta(days=8)})
    db.commit()
    assert hot_segment_alerts(db) == 2
    db.query(LearningSignal).update({"created_at": datetime.now(timezone.utc) - timedelta(days=8)})
    db.commit()
    assert hot_segment_alerts(db) == 0
