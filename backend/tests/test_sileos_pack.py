"""SILEOS feature pack tests (docs/SILEOS_FEATURES.md).

Covers: question banks (CRUD, import-from-quiz snapshot, item analysis),
prerequisites + unlock-status, learning paths, xAPI ingest/emitters,
mastery math, at-risk rules, AI generation (503 without key; provider
monkeypatched for the happy path — no network in tests).
"""
import json
from datetime import datetime, timedelta, timezone

import pytest


# ---------------------------------------------------------------- fixtures

@pytest.fixture
def instructor(db, make_user):
    """An APPROVED instructor — login gates on InstructorProfile.status."""
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="banker@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def instructor_headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def bank(client, instructor_headers):
    r = client.post("/api/v1/question-banks",
                    json={"title": "Physics Pools", "description": "kinematics"},
                    headers=instructor_headers)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def mc_question_payload():
    return {
        "question_title": "SI unit of acceleration?",
        "question_type": "multiple_choice",
        "question_mark": 2,
        "options": ["m/s", "m/s^2", "N", "kg"],
        "correct_answer": 1,
        "answer_explanation": "a = dv/dt → m/s^2",
        "difficulty": "easy",
        "tags": ["kinematics"],
    }


@pytest.fixture
def course_for(db, instructor):
    """A published course owned by `instructor`."""
    from app.models.course import Course
    c = Course(post_title="Physics 101", post_content="d",
               post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _enroll(db, user, course, progress=0, status="enrolled",
            enrolled_days_ago=0):
    from app.models.enrollment import Enrollment
    e = Enrollment(
        course_id=course.id, user_id=user.id,
        enrollment_status=status,
        course_progress_percentage=progress,
        total_lessons=10, completed_lessons=int(progress / 10),
        enrollment_date=datetime.now(timezone.utc) - timedelta(days=enrolled_days_ago),
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


# --------------------------------------------------------- question banks

def test_bank_crud_and_question_validation(client, instructor_headers, bank,
                                           mc_question_payload):
    r = client.get("/api/v1/question-banks", headers=instructor_headers)
    assert r.status_code == 200
    assert any(b["id"] == bank["id"] for b in r.json()["banks"])

    r = client.post(f"/api/v1/question-banks/{bank['id']}/questions",
                    json=mc_question_payload, headers=instructor_headers)
    assert r.status_code == 200, r.text
    qid = r.json()["id"]

    # wrong-type question rejected with 422
    bad = dict(mc_question_payload, question_type="essay")
    r = client.post(f"/api/v1/question-banks/{bank['id']}/questions",
                    json=bad, headers=instructor_headers)
    assert r.status_code == 422

    # out-of-range correct index rejected
    bad = dict(mc_question_payload, correct_answer=9)
    r = client.post(f"/api/v1/question-banks/{bank['id']}/questions",
                    json=bad, headers=instructor_headers)
    assert r.status_code == 422

    # delete-with-content is a guarded 409 (sold/generated content safety)
    r = client.delete(f"/api/v1/question-banks/{bank['id']}",
                      headers=instructor_headers)
    assert r.status_code == 409


def test_import_from_quiz_snapshots(client, db, instructor, instructor_headers,
                                    bank, course_for):
    """Import copies live quiz questions into the bank — the live quiz keeps
    its rows ( provenance via source_quiz_question_id)."""
    from app.models.quiz import Quiz, QuizQuestion
    quiz = Quiz(post_author=instructor.id, post_title="Q1",
                post_parent=course_for.id)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    db.add(QuizQuestion(quiz_id=quiz.id, question_title="What is 2+2?",
                        question_type="multiple_choice", question_mark=1,
                        question_settings={"options": ["3", "4"],
                                           "correct_answer": 1},
                        question_order=0))
    db.commit()

    r = client.post(
        f"/api/v1/question-banks/{bank['id']}/import-from-quiz/{quiz.id}",
        headers=instructor_headers)
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 1

    live_count = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz.id).count()
    assert live_count == 1  # snapshot, not move


def test_item_analysis_flags(client, db, instructor, instructor_headers, bank):
    """Facility + discrimination computed from live quiz answers, with
    sensible flags (no attempts → no_data)."""
    from app.models.quiz import (Quiz, QuizAttempt, QuizAttemptAnswer,
                                 QuizQuestion)
    quiz = Quiz(post_author=instructor.id, post_title="Q2",
                post_parent=0)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    q = QuizQuestion(quiz_id=quiz.id, question_title="Force = ?",
                     question_type="fill_in_blanks", question_mark=1,
                     question_order=0)
    db.add(q)
    db.commit()
    db.refresh(q)

    r = client.post(f"/api/v1/question-banks/{bank['id']}/import-from-quiz/{quiz.id}",
                    headers=instructor_headers)
    assert r.status_code == 200

    # 6 attempts: 3 strong students all correct, 3 weak all wrong
    for i in range(6):
        att = QuizAttempt(course_id=0, quiz_id=quiz.id, user_id=instructor.id,
                          total_marks=1, earned_marks=1 if i < 3 else 0,
                          attempt_status="attempt_submitted")
        db.add(att)
        db.commit()
        db.refresh(att)
        db.add(QuizAttemptAnswer(
            user_id=instructor.id, quiz_id=quiz.id, question_id=q.question_id,
            quiz_attempt_id=att.attempt_id,
            question_mark=1, achieved_mark=1 if i < 3 else 0,
            is_correct=(i < 3)))
    db.commit()

    r = client.get(f"/api/v1/question-banks/{bank['id']}/analysis",
                   headers=instructor_headers)
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["attempts"] == 6
    assert item["facility"] == 0.5
    assert item["discrimination"] == 1.0  # strong all right, weak all wrong
    assert item["flag"] == "ok"


# ---------------------------------------------------------- prerequisites

def test_prerequisites_and_unlock(client, db, instructor, instructor_headers,
                                  course_for, make_user, auth_headers):
    from app.models.course import Course
    prereq_course = Course(post_title="Maths Primer", post_content="d",
                           post_excerpt="p", post_status="publish",
                           post_author=instructor.id, course_price=0)
    db.add(prereq_course)
    db.commit()
    db.refresh(prereq_course)

    r = client.put(
        f"/api/v1/courses/{course_for.id}/prerequisites",
        json={"items": [{"requires_course_id": prereq_course.id,
                          "min_progress_percentage": 50}]},
        headers=instructor_headers)
    assert r.status_code == 200, r.text

    # self-reference rejected
    r = client.put(
        f"/api/v1/courses/{course_for.id}/prerequisites",
        json={"items": [{"requires_course_id": course_for.id}]},
        headers=instructor_headers)
    assert r.status_code == 422

    # a student with 20% progress on the prereq → locked
    student = make_user(role="student")
    _enroll(db, student, prereq_course, progress=20)
    student_headers = auth_headers(student.user_email)
    r = client.get(f"/api/v1/courses/{course_for.id}/unlock-status",
                   headers=student_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["unlocked"] is False
    assert body["unmet_count"] == 1
    assert body["rules"][0]["progress_percentage"] == 20

    # raise progress to 60% on the SAME enrollment → unlocked
    from app.models.enrollment import Enrollment
    row = (db.query(Enrollment)
           .filter(Enrollment.user_id == student.id,
                   Enrollment.course_id == prereq_course.id).first())
    row.course_progress_percentage = 60
    db.commit()
    r = client.get(f"/api/v1/courses/{course_for.id}/unlock-status",
                   headers=student_headers)
    assert r.json()["unlocked"] is True


def test_learning_path_progress(client, db, instructor, instructor_headers,
                                course_for, make_user, auth_headers):
    from app.models.course import Course
    c2 = Course(post_title="Physics 102", post_content="d", post_excerpt="p",
                post_status="publish", post_author=instructor.id, course_price=0)
    db.add(c2)
    db.commit()
    db.refresh(c2)

    r = client.post("/api/v1/learning-paths",
                    json={"title": "Physics track",
                          "course_ids": [course_for.id, c2.id]},
                    headers=instructor_headers)
    assert r.status_code == 200, r.text
    path_id = r.json()["id"]

    student = make_user(role="student")
    _enroll(db, student, course_for, progress=100, status="completed")
    student_headers = auth_headers(student.user_email)

    r = client.get(f"/api/v1/learning-paths/{path_id}/progress",
                   headers=student_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["completed_steps"] == 1
    assert body["total_steps"] == 2


# ------------------------------------------------------------- xAPI spine

def test_xapi_ingest_and_privacy(client, db, make_user, auth_headers,
                                 instructor):
    student = make_user(role="student")
    headers = auth_headers(student.user_email)

    r = client.post("/api/v1/xapi/statements", json={
        "verb": "watched", "object_type": "lesson", "object_id": "12",
        "result": {"duration_seconds": 300},
    }, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["stored"] is True

    # invalid verb rejected
    r = client.post("/api/v1/xapi/statements", json={
        "verb": "hacked", "object_type": "lesson", "object_id": "12",
    }, headers=headers)
    assert r.status_code == 422

    # own stream visible
    r = client.get("/api/v1/xapi/me/statements", headers=headers)
    assert r.status_code == 200
    assert any(s["verb"] == "watched" for s in r.json()["statements"])

    # admin sees the firehose (admin login requires TOTP — seed a secret
    # and answer the challenge with a current code, same as production)
    import pyotp
    from app.models.user import User
    admin = make_user(role="admin", email="xapi-admin@example.com")
    secret = pyotp.random_base32()
    admin.totp_secret = secret
    admin.totp_enabled = True
    db.commit()
    r = client.post("/api/v1/auth/login", json={
        "email": admin.user_email, "password": "Test@123",
        "otp_code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200, r.text
    admin_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.get("/api/v1/xapi/statements", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()["statements"]) >= 1


def test_watch_event_emits_xapi(client, db, make_user, auth_headers,
                                course_for, instructor, TestingSessionLocal,
                                monkeypatch):
    """The emitter hook: recording a watch-event must land an xAPI
    statement (best-effort, post-commit)."""
    from app.models.course import Lesson
    from app.models.sileos_pack import XapiStatement
    from app.services import xapi_service
    # The emitter writes through its own SessionLocal — point it at the
    # test database so the assertion can observe the statement.
    monkeypatch.setattr(xapi_service, "SessionLocal", TestingSessionLocal)
    student = make_user(role="student")
    _enroll(db, student, course_for, progress=0)
    lesson = Lesson(post_author=instructor.id, post_title="L1",
                    post_parent=course_for.id)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    headers = auth_headers(student.user_email)

    r = client.post("/api/v1/progress/watch-event", json={
        "course_id": course_for.id,
        "lesson_id": lesson.id,
        "event": "started",
        "duration_seconds": 10,
        "position_seconds": 0,
    }, headers=headers)
    assert r.status_code == 200, r.text

    stmts = (db.query(XapiStatement)
             .filter(XapiStatement.actor_user_id == student.id).all())
    assert any(s.verb == "watched" and s.object_type == "lesson"
               for s in stmts)


# ---------------------------------------------------------------- mastery

def test_mastery_math(client, db, make_user, course_for, auth_headers,
                      instructor):
    from app.models.quiz import Quiz, QuizAttempt
    student = make_user(role="student")
    _enroll(db, student, course_for, progress=50, status="enrolled")

    quiz = Quiz(post_author=instructor.id, post_title="M1",
                post_parent=course_for.id, quiz_passing_grade=80)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    db.add(QuizAttempt(course_id=course_for.id, quiz_id=quiz.id,
                       user_id=student.id, total_marks=10, earned_marks=9,
                       attempt_status="attempt_submitted"))
    db.commit()

    headers = auth_headers(student.user_email)
    r = client.get(f"/api/v1/analytics/students/{student.id}/mastery",
                   headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    course = body["courses"][0]
    assert course["completion_percentage"] == 50
    assert course["quiz_pass_rate"] == 100.0
    # weighting: 0.6*50 + 0.4*100 = 70.0
    assert course["mastery"] == 70.0
    assert course["level"] == "proficient"

    # privacy: another student cannot read someone else's mastery
    other = make_user(role="student", email="other@example.com")
    other_headers = auth_headers(other.user_email)
    r = client.get(f"/api/v1/analytics/students/{student.id}/mastery",
                   headers=other_headers)
    assert r.status_code == 403


# ---------------------------------------------------------------- at-risk

def test_at_risk_rules_explainable(client, db, instructor, instructor_headers,
                                   course_for, make_user):
    stalled = make_user(role="student", email="stalled@example.com")
    _enroll(db, stalled, course_for, progress=0, enrolled_days_ago=30)
    healthy = make_user(role="student", email="healthy@example.com")
    _enroll(db, healthy, course_for, progress=80, enrolled_days_ago=2)

    r = client.get(f"/api/v1/analytics/courses/{course_for.id}/at-risk",
                   headers=instructor_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["students_scanned"] == 2
    assert body["flagged"] == 1
    result = body["results"][0]
    assert result["user_id"] == stalled.id
    assert result["severity"] in ("medium", "high")
    assert any("zero recorded activity" in reason or "stalled" in reason
               for reason in result["reasons"])
    assert body["rules"]["stalled_days"] == 7  # explainability contract

    # recomputed flags persist (idempotent upsert)
    from app.models.sileos_pack import StudentRiskFlag
    flags = (db.query(StudentRiskFlag)
             .filter(StudentRiskFlag.course_id == course_for.id).all())
    assert len(flags) == 1
    client.get(f"/api/v1/analytics/courses/{course_for.id}/at-risk",
               headers=instructor_headers)
    assert (db.query(StudentRiskFlag)
            .filter(StudentRiskFlag.course_id == course_for.id).count() == 1)


# -------------------------------------------------------------------- AI

def test_ai_generation_503_without_key(client, instructor_headers, bank):
    import os
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        r = client.post("/api/v1/ai/generate-questions", json={
            "topic": "Newton's laws", "count": 3, "bank_id": bank["id"],
        }, headers=instructor_headers)
        assert r.status_code == 503
        assert "GLM_API_KEY" in r.json()["detail"]
    finally:
        if saved:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_ai_generation_happy_path_monkeypatched(client, db, instructor,
                                                instructor_headers, monkeypatch):
    """The provider is monkeypatched (no network in tests) — everything
    around it (job audit, validation, bank writes, tags) runs for real."""
    from app.routers import ai as ai_router

    fake_reply = json.dumps([
        {"question_title": "State Newton's second law.",
         "question_type": "fill_in_blanks", "question_mark": 1,
         "correct_answer": "F = ma",
         "answer_explanation": "Force equals mass times acceleration.",
         "difficulty": "easy"},
        {"question_title": "Broken — no correct answer",
         "question_type": "multiple_choice", "options": ["only one"],
         "difficulty": "hard"},  # rejected by validation
    ])

    calls = {}

    def fake_call(system, prompt):
        calls["prompt"] = prompt
        return fake_reply

    monkeypatch.setattr(ai_router, "call_glm", fake_call)
    monkeypatch.setenv("GLM_API_KEY", "test-key-for-ci")

    r = client.post("/api/v1/ai/generate-questions", json={
        "topic": "Newton's laws", "count": 2,
    }, headers=instructor_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["generated"] == 1          # valid question stored
    assert len(body["rejected"]) == 1      # invalid one reported, not stored

    # job audit trail exists and is done
    r = client.get(f"/api/v1/ai/jobs/{body['job_id']}",
                   headers=instructor_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["input"]["topic"] == "Newton's laws"

    # the draft landed in the bank tagged ai-draft
    from app.models.sileos_pack import BankQuestion
    q = db.query(BankQuestion).filter(BankQuestion.id == body["question_ids"][0]).first()
    assert "ai-draft" in q.tags


# ------------------------------------------------- ebook free-claim (gap fix)

def test_library_free_claim_flow(client, db, make_user, auth_headers,
                                 instructor, instructor_headers):
    """POST /library/{id}/claim — the endpoint payments points free ebooks
    at, which existed in an error message but not in the router until this
    build. Idempotent + draft-404 + paid-422 + grant visible in /library/me."""
    from app.models.ebook import Ebook
    free = Ebook(owner_id=instructor.id, title="Free Notes",
                 slug="free-notes", description="d", category="guide",
                 price_inr=0, status="published")
    paid = Ebook(owner_id=instructor.id, title="Paid Book",
                 slug="paid-book", description="d", category="book",
                 price_inr=299, status="published")
    draft = Ebook(owner_id=instructor.id, title="Draft",
                  slug="draft", description="d", category="guide",
                  price_inr=0, status="draft")
    db.add_all([free, paid, draft])
    db.commit()
    db.refresh(free); db.refresh(paid); db.refresh(draft)

    student = make_user(role="student")
    headers = auth_headers(student.user_email)

    # paid ebook is rejected — money must flow through create-order
    r = client.post(f"/api/v1/library/{paid.id}/claim", headers=headers)
    assert r.status_code == 422
    # draft is a 404 (no inventory probing)
    r = client.post(f"/api/v1/library/{draft.id}/claim", headers=headers)
    assert r.status_code == 404

    # free claim grants, is idempotent, and shows in My Library
    r = client.post(f"/api/v1/library/{free.id}/claim", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["owned"] is True
    assert r.json()["newly_granted"] is True
    r = client.post(f"/api/v1/library/{free.id}/claim", headers=headers)
    assert r.status_code == 200
    assert r.json()["newly_granted"] is False  # no-op, same row

    r = client.get("/api/v1/library/me", headers=headers)
    assert [i["title"] for i in r.json()["items"]] == ["Free Notes"]
