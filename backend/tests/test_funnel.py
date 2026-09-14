"""R1 conversion funnel: anonymous + logged-in event capture, derived summary
with enrolments from the enrollments table, owner-only summary, continue-
where-you-left-off, and the idempotent abandoned-checkout reminder pass.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment, LessonProgress
from app.models.funnel import FunnelEvent


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="fun-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def student_headers(student_user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}


@pytest.fixture
def course(db, instructor):
    c = Course(post_title="Funnel course", post_content="d", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=299, course_type="utporul")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_events_summary_and_access(client, db, course, student_user, headers, student_headers):
    sid = "sess-anonymous-0001"
    assert client.post("/api/v1/funnel/events", json={"kind": "course_view", "course_id": course.id, "session_id": sid}).status_code == 201
    assert client.post("/api/v1/funnel/events", json={"kind": "preview_open", "course_id": course.id, "session_id": sid, "meta": {"lesson_id": 7, "evil": {"x": 1}}}).status_code == 201
    assert client.post("/api/v1/funnel/events", json={"kind": "preview_open", "course_id": course.id, "session_id": sid, "meta": {"lesson_id": 7}}).status_code == 201
    assert client.post("/api/v1/funnel/events", json={"kind": "bogus", "course_id": course.id, "session_id": sid}).status_code == 422
    assert client.post("/api/v1/funnel/events", json={"kind": "course_view", "course_id": 999999, "session_id": sid}).status_code == 404
    r = client.post("/api/v1/funnel/events", headers=student_headers, json={"kind": "checkout_start", "course_id": course.id, "session_id": "sess-student-00001"})
    assert r.status_code == 201
    ev = db.query(FunnelEvent).filter(FunnelEvent.kind == "checkout_start").one()
    assert ev.user_id == student_user.id
    assert db.query(FunnelEvent).filter(FunnelEvent.kind == "preview_open").first().meta == {"lesson_id": 7}   # nested meta dropped
    db.add(Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled"))
    db.commit()
    assert client.get(f"/api/v1/funnel/courses/{course.id}/summary", headers=student_headers).status_code == 403
    s = client.get(f"/api/v1/funnel/courses/{course.id}/summary", headers=headers).json()
    assert s["views"] == 1 and s["preview_opens"] == 1 and s["checkout_starts"] == 1 and s["enrolments"] == 1
    assert s["rates"]["checkout_to_enrol"] == 100.0 and s["top_preview_lessons"] == [{"lesson_id": "7", "opens": 2}]
    ov = client.get("/api/v1/funnel/overview", headers=headers).json()["courses"]
    assert ov[0]["course_id"] == course.id and ov[0]["title"] == "Funnel course"


def test_continue_learning(client, db, course, instructor, student_user, student_headers):
    enr = Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled", course_progress_percentage=40)
    db.add(enr)
    l1 = Lesson(post_author=instructor.id, post_parent=course.id, post_title="Older", post_status="publish", post_type="lesson", menu_order=1)
    l2 = Lesson(post_author=instructor.id, post_parent=course.id, post_title="Newest", post_status="publish", post_type="lesson", menu_order=2)
    db.add_all([l1, l2])
    db.commit()
    now = datetime.now(timezone.utc)
    db.add(LessonProgress(user_id=student_user.id, course_id=course.id, lesson_id=l1.id, enrollment_id=enr.id, progress_status="completed", updated_at=now - timedelta(days=2)))
    db.add(LessonProgress(user_id=student_user.id, course_id=course.id, lesson_id=l2.id, enrollment_id=enr.id, progress_status="started", video_completion_percentage=35, updated_at=now))
    db.commit()
    items = client.get("/api/v1/funnel/me/continue", headers=student_headers).json()["items"]
    assert len(items) == 1 and items[0]["lesson_title"] == "Newest" and items[0]["video_pct"] == 35 and items[0]["course_pct"] == 40


def test_abandoned_checkout_reminder_is_idempotent(client, db, course, student_user, make_user):
    from app.models.notification import Notification
    from app.services import funnel_service as svc
    other = make_user(role="student", email="fun-other@example.com")
    now = datetime.now(timezone.utc)
    db.add(FunnelEvent(kind="checkout_start", course_id=course.id, user_id=student_user.id, session_id="s1", created_at=now - timedelta(hours=30)))
    db.add(FunnelEvent(kind="checkout_start", course_id=course.id, user_id=other.id, session_id="s2", created_at=now - timedelta(hours=30)))
    db.add(FunnelEvent(kind="checkout_start", course_id=course.id, user_id=None, session_id="s3", created_at=now - timedelta(hours=30)))   # anonymous: nobody to remind
    db.add(Enrollment(user_id=other.id, course_id=course.id, enrollment_status="enrolled"))   # completed the purchase
    db.commit()
    assert svc.abandoned_checkout_pass(db, now) == 1
    n = db.query(Notification).filter(Notification.type == "checkout_reminder").all()
    assert len(n) == 1 and n[0].user_id == student_user.id and n[0].related_id == course.id and n[0].link == f"/checkout/{course.id}"
    assert svc.abandoned_checkout_pass(db, now) == 0   # once per user/course
    # too fresh (< 24h) -> not yet
    db.add(FunnelEvent(kind="checkout_start", course_id=course.id, user_id=student_user.id, session_id="s4", created_at=now - timedelta(hours=2)))
    db.commit()
    assert svc.abandoned_checkout_pass(db, now) == 0
