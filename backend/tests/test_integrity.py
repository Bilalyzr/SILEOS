"""R8 assessment integrity: timed windows enforced at attempt start (owner
exempt), retired questions excluded from new attempts but kept in history,
integrity events recorded on the attempt (advisory), instructor summary and
the review-queue integrity lane.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="int-inst@example.com")
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
    c = Course(post_title="Integrity course", post_content="d", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=0, course_type="utporul")
    db.add(c)
    db.commit()
    db.refresh(c)
    db.add(Enrollment(user_id=student_user.id, course_id=c.id, enrollment_status="enrolled"))
    db.commit()
    return c


@pytest.fixture
def quiz(db, course, instructor):
    q = Quiz(post_author=instructor.id, post_title="Timed quiz", post_parent=course.id, post_status="publish", quiz_time_limit=10)
    db.add(q)
    db.commit()
    for i in range(3):
        db.add(QuizQuestion(quiz_id=q.id, question_title=f"Question {i}?", question_type="multiple_choice", question_order=i))
    db.commit()
    return q


def test_timed_window_enforced_for_learners_only(client, db, quiz, headers, student_headers):
    now = datetime.now(timezone.utc)
    r = client.put(f"/api/v1/courses/{quiz.post_parent}/quizzes/{quiz.id}", headers=headers,
                   json={"availableFrom": (now + timedelta(hours=1)).isoformat(), "availableUntil": (now + timedelta(hours=3)).isoformat()})
    assert r.status_code == 200, r.text
    g = client.get(f"/api/v1/courses/{quiz.post_parent}/quizzes/{quiz.id}", headers=headers).json()
    assert g["availableFrom"] and g["availableUntil"]
    r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=student_headers)
    assert r.status_code == 403 and "opens at" in r.json()["detail"]
    assert client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers).status_code == 200   # owner may test
    db.refresh(quiz)
    quiz.quiz_available_from = now - timedelta(hours=3)
    quiz.quiz_available_until = now - timedelta(hours=1)
    db.commit()
    r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=student_headers)
    assert r.status_code == 403 and "closed" in r.json()["detail"]
    r = client.put(f"/api/v1/courses/{quiz.post_parent}/quizzes/{quiz.id}", headers=headers, json={"availableFrom": "", "availableUntil": ""})
    assert r.status_code == 200
    assert client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=student_headers).status_code == 200
    assert client.put(f"/api/v1/courses/{quiz.post_parent}/quizzes/{quiz.id}", headers=headers, json={"availableFrom": "not a date"}).status_code == 422


def test_retired_questions_leave_new_attempts(client, db, quiz, headers, student_headers):
    qid = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.question_order).first().question_id
    assert client.post(f"/api/v1/ai/review-queue/items/{qid}/retire", headers=student_headers).status_code == 403
    r = client.post(f"/api/v1/ai/review-queue/items/{qid}/retire", headers=headers)
    assert r.status_code == 200 and r.json()["is_retired"] is True
    start = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=student_headers).json()
    assert start["total_questions"] == 2
    served = client.get(f"/api/v1/courses/{quiz.post_parent}/quizzes/{quiz.id}", headers=student_headers).json()
    titles = [q.get("question_title") or q.get("title") for q in served.get("questions", [])]
    assert "Question 0?" not in titles and len(titles) == 2
    assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count() == 3   # history intact
    assert client.post(f"/api/v1/ai/review-queue/items/{qid}/unretire", headers=headers).json()["is_retired"] is False


def test_integrity_events_summary_and_lane(client, db, quiz, headers, student_headers, student_user):
    start = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=student_headers).json()
    aid = start["attempt_id"]
    assert client.post(f"/api/v1/quiz-attempts/{aid}/integrity", headers=student_headers, json={"event": "teleport"}).status_code == 422
    assert client.post(f"/api/v1/quiz-attempts/{aid}/integrity", headers=headers, json={"event": "tab_hidden"}).status_code == 404   # not the owner
    for ev in ("tab_hidden", "tab_visible", "tab_hidden", "tab_hidden", "paste"):
        r = client.post(f"/api/v1/quiz-attempts/{aid}/integrity", headers=student_headers, json={"event": ev})
        assert r.status_code == 200 and r.json()["recorded"] is True
    a = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == aid).one()
    db.refresh(a)
    assert a.attempt_info["integrity"]["tab_hidden"] == 3 and a.attempt_info["integrity"]["paste"] == 1
    assert a.earned_marks in (None, 0)   # never touches the score
    s = client.get(f"/api/v1/courses/{quiz.post_parent}/quizzes/{quiz.id}/integrity", headers=headers).json()
    assert s["flagged"] == 1 and "left the tab 3 times" in s["attempts"][0]["flags"] and "pasted text 1x" in s["attempts"][0]["flags"]
    assert client.get(f"/api/v1/courses/{quiz.post_parent}/quizzes/{quiz.id}/integrity", headers=student_headers).status_code == 403
    lane = client.get("/api/v1/ai/review-queue/integrity", headers=headers).json()["attempts"]
    assert len(lane) == 1 and lane[0]["user_id"] == student_user.id and lane[0]["tab_hidden"] == 3
