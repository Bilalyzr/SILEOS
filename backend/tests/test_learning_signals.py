"""Learning-signals engine: ingest (validated batch), lesson heat-map with
concept markers turning segments into concepts, learner struggle profile
with explainable "why", adaptive practice built from the profile and graded
server-side into mastery evidence.
"""
import pytest

from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.learning_signals import LearningSignal
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="sig-inst@example.com")
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
def world(db, instructor, student_user):
    from app.services.mastery_service import set_links
    course = Course(post_title="Signals course", post_content="d", post_excerpt="p", post_status="publish", post_author=instructor.id, course_price=0, course_type="utporul")
    db.add(course)
    db.commit()
    db.add(Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled"))
    lesson = Lesson(post_author=instructor.id, post_parent=course.id, post_title="Stoichiometry", post_status="publish", post_type="lesson", menu_order=1)
    db.add(lesson)
    db.commit()
    set_links(db, "lesson", lesson.id, ["mole ratio", "limiting reagent"], course_id=course.id)
    quiz = Quiz(post_author=instructor.id, post_title="Unit quiz", post_parent=course.id, post_status="publish")
    db.add(quiz)
    db.commit()
    qs = []
    for i, (concept, diff) in enumerate([("limiting reagent", "easy"), ("limiting reagent", "medium"), ("mole ratio", "medium"), ("gas laws", "hard")]):
        q = QuizQuestion(quiz_id=quiz.id, question_title=f"Q{i} about {concept}?", question_type="multiple_choice", question_mark=1,
                         question_order=i, question_settings={"difficulty": diff})
        db.add(q)
        db.commit()
        db.add_all([QuizQuestionAnswer(belongs_question_id=q.question_id, answer_title="right", is_correct=True, answer_order=1),
                    QuizQuestionAnswer(belongs_question_id=q.question_id, answer_title="wrong", is_correct=False, answer_order=2)])
        db.commit()
        set_links(db, "question", q.question_id, [concept], course_id=course.id)
        qs.append(q)
    db.commit()
    return course, lesson, quiz, qs


def test_ingest_heatmap_and_markers(client, db, world, headers, student_headers, student_user):
    course, lesson, quiz, qs = world
    r = client.post("/api/v1/signals/events", headers=student_headers, json={"events": [
        {"kind": "video_rewind", "course_id": course.id, "lesson_id": lesson.id, "position_s": 205, "value": 12},
        {"kind": "video_rewind", "course_id": course.id, "lesson_id": lesson.id, "position_s": 208, "value": 8},
        {"kind": "video_replay", "course_id": course.id, "lesson_id": lesson.id, "position_s": 200},
        {"kind": "video_skip", "course_id": course.id, "lesson_id": lesson.id, "position_s": 40, "value": 30},
        {"kind": "note_written", "course_id": course.id, "lesson_id": lesson.id, "position_s": 60},
        {"kind": "teleport", "course_id": course.id},
    ]})
    assert r.status_code == 201 and r.json()["recorded"] == 5
    # no markers yet: every segment is attributed to the lesson's concepts
    h = client.get(f"/api/v1/signals/lessons/{lesson.id}/heatmap", headers=headers).json()
    hot = h["struggle_segments"][0]
    assert hot["segment"] == 20 and hot["rewinds"] == 2 and hot["replays"] == 1 and set(hot["concepts"]) == {"mole ratio", "limiting reagent"}
    # markers: from 3:00 the lesson is about the limiting reagent
    assert client.post(f"/api/v1/signals/lessons/{lesson.id}/markers", headers=student_headers, json={"time_s": 180, "concept": "Limiting Reagent"}).status_code == 403
    r = client.post(f"/api/v1/signals/lessons/{lesson.id}/markers", headers=headers, json={"time_s": 180, "concept": "Limiting Reagent"})
    assert r.status_code == 201 and r.json()["markers"][0]["concept"] == "limiting reagent"
    client.post(f"/api/v1/signals/lessons/{lesson.id}/markers", headers=headers, json={"time_s": 0, "concept": "mole ratio"})
    h = client.get(f"/api/v1/signals/lessons/{lesson.id}/heatmap", headers=headers).json()
    hot = h["struggle_segments"][0]
    assert hot["concepts"] == ["limiting reagent"]
    early = [s for s in h["segments"] if s["segment"] == 4][0]
    assert early["concepts"] == ["mole ratio"] and early["skips"] == 1
    # learners only see their own heat-map, whatever they ask for
    mine = client.get(f"/api/v1/signals/lessons/{lesson.id}/heatmap?user_id=999", headers=student_headers).json()
    assert mine["struggle_segments"][0]["learners"] == 1


def test_profile_explains_the_struggle(client, db, world, headers, student_headers, student_user):
    course, lesson, quiz, qs = world
    client.post(f"/api/v1/signals/lessons/{lesson.id}/markers", headers=headers, json={"time_s": 180, "concept": "limiting reagent"})
    client.post(f"/api/v1/signals/lessons/{lesson.id}/markers", headers=headers, json={"time_s": 0, "concept": "mole ratio"})
    client.post("/api/v1/signals/events", headers=student_headers, json={"events": [
        {"kind": "video_rewind", "course_id": course.id, "lesson_id": lesson.id, "position_s": 200, "value": 10},
        {"kind": "video_rewind", "course_id": course.id, "lesson_id": lesson.id, "position_s": 210, "value": 10},
        {"kind": "video_rewind", "course_id": course.id, "lesson_id": lesson.id, "position_s": 215, "value": 10},
        {"kind": "quit_early", "course_id": course.id, "lesson_id": lesson.id, "position_s": 230, "value": 45},
        {"kind": "question_time", "course_id": course.id, "quiz_id": quiz.id, "question_id": qs[0].question_id, "value": 70},
        {"kind": "answer_change", "course_id": course.id, "quiz_id": quiz.id, "question_id": qs[0].question_id, "value": 3},
        {"kind": "note_written", "course_id": course.id, "lesson_id": lesson.id, "position_s": 30},
        {"kind": "question_time", "course_id": course.id, "quiz_id": quiz.id, "question_id": qs[2].question_id, "value": 12},
    ]})
    p = client.get(f"/api/v1/signals/me/profile?course_id={course.id}", headers=student_headers).json()
    assert p["signals"] == 8
    top = p["concepts"][0]
    assert top["concept"] == "limiting reagent" and top["struggle"] == 100.0
    assert "rewound 3×" in top["why"] and "left early 1×" in top["why"] and "hesitated on 1 question" in top["why"] and "changed answers 1×" in top["why"]
    mole = [c for c in p["concepts"] if c["concept"] == "mole ratio"][0]
    assert mole["raw"] < 0 and "took 1 note" in mole["why"]   # notes count as engagement; a 12s answer is not hesitation
    assert p["struggling"][0]["concept"] == "limiting reagent" and p["confident"][0]["concept"] == "mole ratio"
    # instructor view of the same learner (course editor only)
    assert client.get(f"/api/v1/signals/students/{student_user.id}/profile?course_id={course.id}", headers=headers).status_code == 200


def test_adaptive_practice_targets_struggle_and_feeds_mastery(client, db, world, headers, student_headers, student_user):
    from app.models.learning_signals import AdaptiveSession
    from app.models.mastery import LearnerMastery, MasteryEvidence
    course, lesson, quiz, qs = world
    client.post(f"/api/v1/signals/lessons/{lesson.id}/markers", headers=headers, json={"time_s": 180, "concept": "limiting reagent"})
    client.post("/api/v1/signals/events", headers=student_headers, json={"events": [
        {"kind": "video_rewind", "course_id": course.id, "lesson_id": lesson.id, "position_s": 200, "value": 10},
        {"kind": "video_rewind", "course_id": course.id, "lesson_id": lesson.id, "position_s": 205, "value": 10},
        {"kind": "quit_early", "course_id": course.id, "lesson_id": lesson.id, "position_s": 230, "value": 40},
    ]})
    db.add(LearnerMastery(user_id=student_user.id, concept="limiting reagent", estimate=30.0, confidence=0.5, evidence_count=1))
    db.commit()
    r = client.post(f"/api/v1/signals/adaptive/{course.id}/build?count=3", headers=student_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["plan"]["concepts"][0] == "limiting reagent" and "rewound 2×" in body["plan"]["why"][0]
    concepts = [set(q["concepts"]) for q in body["questions"]]
    assert {"limiting reagent"} in concepts and len(body["questions"]) == 3
    assert all("expected" not in q and "options" in q for q in body["questions"])   # no answer keys leak
    lr = [q for q in body["questions"] if q["concepts"] == ["limiting reagent"]]
    assert all(q["difficulty"] == "easy" for q in lr)   # mastery 30 → easy items first
    sid = body["session_id"]
    answers = {str(q["question_id"]): ("right" if q["concepts"] == ["limiting reagent"] else "wrong") for q in body["questions"]}
    r = client.post(f"/api/v1/signals/adaptive/{sid}/submit", headers=student_headers, json={"answers": answers})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["max_score"] == 3 and res["score"] == sum(1 for q in body["questions"] if q["concepts"] == ["limiting reagent"])
    by = {b["concept"]: b for b in res["by_concept"]}
    assert by["limiting reagent"]["correct"] == by["limiting reagent"]["total"]
    assert client.post(f"/api/v1/signals/adaptive/{sid}/submit", headers=student_headers, json={"answers": answers}).status_code == 409
    # evidence landed in the mastery graph for the practised concept
    ev = db.query(MasteryEvidence).filter(MasteryEvidence.user_id == student_user.id, MasteryEvidence.concept == "limiting reagent").count()
    assert ev >= 1
    assert db.query(LearningSignal).filter(LearningSignal.kind == "adaptive_result").count() == 1
    sess = db.query(AdaptiveSession).filter(AdaptiveSession.id == sid).one()
    assert sess.submitted_at is not None and sess.results[0]["expected"] == ["right"]



def test_course_hotspots_scoped_ranked_and_editor_only(client, db, world, headers, student_headers, make_user):
    from app.services.learning_signals_service import ingest
    from app.models.learning_signals import LessonConceptMarker
    from app.models.course_ops import CourseCollaborator
    from app.core.security import create_access_token
    course, lesson, quiz, qs = world
    db.add(LessonConceptMarker(lesson_id=lesson.id, time_s=180, concept="limiting reagent"))
    db.commit()
    for i in range(3):
        user = make_user(role="student", email=f"hot{i}@example.com")
        ingest(db, user.id, [{"kind": "video_rewind", "lesson_id": lesson.id, "position_s": 201}] * 2 +
               [{"kind": "quit_early", "lesson_id": lesson.id, "position_s": 201}])
    r = client.get(f"/api/v1/signals/courses/{course.id}/hotspots", headers=headers)
    assert r.status_code == 200, r.text
    hot = r.json()["hotspots"][0]
    assert (hot["lesson_id"], hot["start_s"], hot["score"], hot["learners"]) == (lesson.id, 200, 12, 3)
    assert hot["concepts"] == ["limiting reagent"] and hot["early_quits"] == 3
    assert r.json()["struggling_by_concept"] == [{"concept": "limiting reagent", "learners": 3}]
    assert client.get(f"/api/v1/signals/courses/{course.id}/hotspots", headers=student_headers).status_code == 403
    other = make_user(role="instructor", email="hot-editor@example.com")
    token = {"Authorization": "Bearer " + create_access_token({"sub": str(other.id)})}
    assert client.get(f"/api/v1/signals/courses/{course.id}/hotspots", headers=token).status_code == 403
    db.add(CourseCollaborator(course_id=course.id, user_id=other.id))
    db.commit()
    assert client.get(f"/api/v1/signals/courses/{course.id}/hotspots", headers=token).status_code == 200
    assert client.get(f"/api/v1/signals/courses/{course.id}/hotspots?days=0", headers=headers).status_code == 422


def test_focus_practice_prioritizes_linked_concept(client, db, world, student_headers):
    course, lesson, quiz, qs = world
    r = client.post(f"/api/v1/signals/adaptive/{course.id}/build?count=3&focus=Gas%20Laws", headers=student_headers)
    assert r.status_code == 201, r.text
    assert r.json()["questions"][0]["concepts"] == ["gas laws"]
    assert r.json()["plan"]["focus_concepts"] == ["gas laws"]


def test_wrong_quiz_answers_return_weak_concepts_without_feedback_leak(client, db, world, student_headers):
    course, lesson, quiz, qs = world
    r = client.post(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit", headers=student_headers,
                    json={"answers": {str(q.question_id): 1 if i == 0 else 0 for i, q in enumerate(qs)}})
    assert r.status_code == 200, r.text
    assert r.json()["weak_concepts"] == ["limiting reagent"]
    aid = r.json()["attempt_id"]
    assert client.get(f"/api/v1/quiz-attempts/{aid}/results", headers=student_headers).json()["weak_concepts"] == ["limiting reagent"]
    quiz.quiz_feedback_mode = "reveal_never"
    db.commit()
    assert client.get(f"/api/v1/quiz-attempts/{aid}/results", headers=student_headers).json()["weak_concepts"] == []


def test_tutor_context_is_learner_scoped_and_keeps_no_key_guard(client, db, world, student_user, student_headers, monkeypatch):
    from app.routers import ai_tutor, ai_engines
    from app.services import ai_layer_service
    from app.services.learning_signals_service import ingest
    course, lesson, quiz, qs = world
    ingest(db, student_user.id, [{"kind": "video_rewind", "course_id": course.id, "lesson_id": lesson.id, "position_s": 200}] * 3)
    calls = []
    def fake(system, prompt, **kwargs):
        calls.append(system)
        return "Try a worked example."
    for module in (ai_tutor, ai_engines, ai_layer_service):
        monkeypatch.setattr(module, "call_glm", fake)
    monkeypatch.setenv("GLM_API_KEY", "test-key")
    r = client.post("/api/v1/ai/tutor/chat", headers=student_headers, json={"course_id": course.id, "message": "Help me plan my revision"})
    assert r.status_code == 200, r.text
    assert "rewound 3×" in calls[0] and "Prefer worked examples" in calls[0]
    monkeypatch.delenv("GLM_API_KEY")
    monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)
    assert client.post("/api/v1/ai/tutor/chat", headers=student_headers, json={"course_id": course.id, "message": "Help me plan my revision"}).status_code == 503
    assert client.post("/api/v1/ai/tutor/chat", headers=student_headers, json={"course_id": course.id, "message": qs[0].question_title}).json()["guarded"] is True
    assert len(calls) == 1



def test_hotspots_use_lesson_ownership_and_time_window(db, world, student_user):
    from datetime import datetime, timedelta, timezone
    from app.services.learning_signals_service import course_hotspots, ingest
    course, lesson, quiz, qs = world
    other = Course(post_author=course.post_author, post_title="Other", post_status="publish")
    db.add(other)
    db.commit()
    foreign = Lesson(post_author=course.post_author, post_parent=other.id, post_title="Foreign", post_type="lesson")
    db.add(foreign)
    db.commit()
    ingest(db, student_user.id, [{"kind": "video_rewind", "course_id": course.id, "lesson_id": foreign.id, "position_s": 200}] * 10)
    ingest(db, student_user.id, [{"kind": "video_rewind", "course_id": other.id, "lesson_id": lesson.id, "position_s": 10}])
    db.add(LearningSignal(user_id=student_user.id, lesson_id=lesson.id, kind="video_replay", segment=20, position_s=200,
                          created_at=datetime.now(timezone.utc) - timedelta(days=31)))
    db.commit()
    result = course_hotspots(db, course.id)
    assert len(result["hotspots"]) == 1
    assert result["hotspots"][0]["start_s"] == 10
    assert result["hotspots"][0]["score"] == 1



def test_manual_weak_concepts_wait_for_finalization(client, db, world, student_headers, headers):
    from app.models.quiz import QuizAttemptAnswer
    course, lesson, quiz, qs = world
    qs[0].question_type = "essay"
    db.commit()
    answers = {str(q.question_id): "An explanation" if i == 0 else 0 for i, q in enumerate(qs)}
    r = client.post(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit", headers=student_headers, json={"answers": answers})
    assert r.status_code == 200, r.text
    assert r.json()["pending_review"] and r.json()["weak_concepts"] == []
    aid = r.json()["attempt_id"]
    row = db.query(QuizAttemptAnswer).filter(QuizAttemptAnswer.quiz_attempt_id == aid, QuizAttemptAnswer.question_id == qs[0].question_id).one()
    r = client.post(f"/api/v1/quiz-attempts/{aid}/answers/{row.attempt_answer_id}/grade", headers=headers, json={"achieved_mark": 0})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/quiz-attempts/{aid}/finalize", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["weak_concepts"] == ["limiting reagent"]
