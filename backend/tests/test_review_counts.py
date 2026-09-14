"""R2: cheap review-queue counts for the sidebar badge, and the course
language hint reaching the tutor prompt (Tamil-medium courses answer in Tamil).
"""
import pytest

from app.models.enrollment import Enrollment


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="rc-inst@example.com")
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
def course(db, instructor, student_user):
    from app.models.course import Course
    c = Course(post_title="Tamil physics", post_content="d", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=0, course_type="seyappaduporul", course_language="Tamil")
    db.add(c)
    db.commit()
    db.refresh(c)
    db.add(Enrollment(user_id=student_user.id, course_id=c.id, enrollment_status="enrolled"))
    db.commit()
    return c


def test_counts_and_badge_total(client, db, course, headers, student_headers):
    assert client.get("/api/v1/ai/review-queue/counts", headers=student_headers).status_code == 403
    assert client.get("/api/v1/ai/review-queue/counts", headers=headers).json()["total"] == 0
    client.post("/api/v1/ai/tutor/escalate", headers=student_headers, json={"course_id": course.id, "question": "Why does the ball curve?"})
    client.post("/api/v1/ai/error-reports", headers=student_headers, json={"course_id": course.id, "kind": "lesson", "message": "Slide 3 has a typo in the formula"})
    c = client.get("/api/v1/ai/review-queue/counts", headers=headers).json()
    assert c == {"escalations": 1, "error_reports": 1, "ai_drafts": 0, "total": 2}


def test_tutor_prompt_carries_course_language(client, db, course, student_headers, monkeypatch):
    from app.routers import ai_tutor
    monkeypatch.setenv("GLM_API_KEY", "test-key")
    seen = {}

    def fake(system, prompt, **kw):
        seen["prompt"] = prompt
        return "வணக்கம் — let us start from Newton's second law."
    monkeypatch.setattr(ai_tutor, "call_glm", fake)
    r = client.post("/api/v1/ai/tutor/chat", headers=student_headers, json={"course_id": course.id, "message": "How do I start a projectile motion problem?"})
    assert r.status_code == 200, r.text
    assert "LANGUAGE: reply in Tamil" in seen["prompt"]
