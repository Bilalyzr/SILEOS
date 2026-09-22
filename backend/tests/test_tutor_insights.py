"""Sasha tutor learning monitor: privacy, access and explainable scoring."""
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.mastery import ConceptLink, LearnerMastery
from app.models.tutor_learning_signal import TutorLearningSignal
from app.models.user import InstructorProfile


def _world(db, make_user):
    instructor = make_user(role="instructor")
    learner = make_user(role="student")
    outsider = make_user(role="instructor")
    unenrolled = make_user(role="student")
    db.add_all([
        InstructorProfile(user_id=instructor.id, is_approved=True),
        InstructorProfile(user_id=outsider.id, is_approved=True),
    ])
    course = Course(post_author=instructor.id, post_title="Physics foundations", post_status="publish")
    db.add(course)
    db.flush()
    db.add(Enrollment(user_id=learner.id, course_id=course.id, enrollment_status="enrolled"))
    db.add(ConceptLink(kind="course", ref_id=str(course.id), course_id=course.id,
                       concept="projectile motion", created_by=instructor.id))
    db.add(LearnerMastery(user_id=learner.id, concept="projectile motion",
                          estimate=32, confidence=0.7, evidence_count=3))
    db.commit()
    return instructor, learner, outsider, unenrolled, course


def test_course_linked_tutor_signals_are_private_and_actionable(
    client, db, make_user, auth_headers, monkeypatch,
):
    from app.routers import ai_tutor

    instructor, learner, outsider, unenrolled, course = _world(db, make_user)
    instructor_headers = auth_headers(instructor.user_email)
    learner_headers = auth_headers(learner.user_email)
    outsider_headers = auth_headers(outsider.user_email)
    unenrolled_headers = auth_headers(unenrolled.user_email)
    monkeypatch.setenv("GLM_API_KEY", "test-key")
    monkeypatch.setattr(ai_tutor, "call_glm", lambda *_args, **_kwargs: "Let us draw the motion first.")

    # General Sasha use stays outside instructor analytics.
    general = client.post("/api/v1/ai/tutor/chat", headers=learner_headers, json={
        "message": "Help me plan my week", "session_id": "general-space",
    })
    assert general.status_code == 200, general.text
    assert general.json()["learning_signal"] is None
    assert db.query(TutorLearningSignal).count() == 0

    linked = client.post("/api/v1/ai/tutor/chat", headers=learner_headers, json={
        "course_id": course.id,
        "message": "I am still confused. Explain projectile motion again with an example.",
        "session_id": "course-space",
    })
    assert linked.status_code == 200, linked.text
    signal = linked.json()["learning_signal"]
    assert signal["concept"] == "projectile motion"
    assert signal["severity"] == "high"
    assert signal["score"] >= 75

    denied = client.post("/api/v1/ai/tutor/chat", headers=unenrolled_headers, json={
        "course_id": course.id, "message": "Explain projectile motion",
    })
    assert denied.status_code == 403

    result = client.get(
        f"/api/v1/signals/courses/{course.id}/sasha-insights?days=30",
        headers=instructor_headers,
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["summary"]["students_needing_attention"] == 1
    assert body["students"][0]["name"] == learner.display_name
    assert body["students"][0]["likely_gap"] == "Foundational Gap"
    assert body["concepts"][0]["concept"] == "projectile motion"
    assert "reply" not in body["recent"][0]
    assert "General Sasha chats" in body["privacy"]

    assert client.get(
        f"/api/v1/signals/courses/{course.id}/sasha-insights",
        headers=learner_headers,
    ).status_code == 403
    assert client.get(
        f"/api/v1/signals/courses/{course.id}/sasha-insights",
        headers=outsider_headers,
    ).status_code == 403


def test_repeated_course_questions_raise_explainable_concern(
    client, db, make_user, auth_headers, monkeypatch,
):
    from app.routers import ai_tutor

    instructor, learner, _outsider, _unenrolled, course = _world(db, make_user)
    learner_headers = auth_headers(learner.user_email)
    monkeypatch.setenv("GLM_API_KEY", "test-key")
    monkeypatch.setattr(ai_tutor, "call_glm", lambda *_args, **_kwargs: "We can work through it.")

    scores = []
    for _ in range(3):
        response = client.post("/api/v1/ai/tutor/chat", headers=learner_headers, json={
            "course_id": course.id,
            "message": "How do I solve a projectile motion problem?",
            "session_id": "repeat-space",
        })
        assert response.status_code == 200, response.text
        scores.append(response.json()["learning_signal"]["score"])
    assert scores == sorted(scores)
    latest = db.query(TutorLearningSignal).order_by(TutorLearningSignal.id.desc()).first()
    assert latest.repeat_count == 2
    assert any("earlier Sasha questions" in reason for reason in latest.reasons)
