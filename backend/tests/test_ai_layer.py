"""WP7 — AI layer completion (v2.0 §9): graded-item answer guard (no key
needed), Engine C escalation + instructor reply with notifications, learner
error reports → instructor inbox → resolve, Engine D review queue (AI drafts
approve/reject + derived item flags), Engine B/C LLM endpoints honest-503
without a key and working with a fake provider, Engine A transcript ingest
(worker + instructor paste) with and without the LLM.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassStatus
from app.models.quiz import Quiz, QuizQuestion


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="ai-inst@example.com")
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
    c = Course(post_title="AI layer course", post_content="d", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=0, course_type="utporul")
    db.add(c)
    db.commit()
    db.refresh(c)
    db.add(Enrollment(user_id=student_user.id, course_id=c.id, enrollment_status="enrolled"))
    db.commit()
    return c


@pytest.fixture
def no_llm(monkeypatch):
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    monkeypatch.delenv("ZHIPUAI_API_KEY", raising=False)


@pytest.fixture
def fake_llm(monkeypatch):
    """Configured provider whose reply is chosen per test via `calls`."""
    from app.services import ai_layer_service
    from app.routers import ai_engines
    monkeypatch.setenv("GLM_API_KEY", "test-key")
    calls = {"reply": "{}", "prompts": []}

    def fake_call(system, prompt, **kw):
        calls["prompts"].append((system, prompt))
        return calls["reply"]
    monkeypatch.setattr(ai_layer_service, "call_glm", fake_call)
    monkeypatch.setattr(ai_engines, "call_glm", fake_call)
    return calls


def _quiz(db, course, instructor, title):
    q = Quiz(post_author=instructor.id, post_title="Graded quiz", post_parent=course.id)
    db.add(q)
    db.commit()
    qq = QuizQuestion(quiz_id=q.id, question_title=title, question_type="multiple_choice")
    db.add(qq)
    db.commit()
    return q, qq


def test_graded_item_guard_refuses_without_llm(client, db, course, instructor, student_headers, no_llm):
    _quiz(db, course, instructor, "What is the molar mass of calcium carbonate in grams per mole?")
    r = client.post("/api/v1/ai/tutor/chat", headers=student_headers,
                    json={"course_id": course.id, "message": "what is the molar mass of calcium carbonate in grams per mole"})
    assert r.status_code == 200, r.text
    assert r.json()["guarded"] is True and "won't give" in r.json()["reply"]
    # an ordinary question still needs the key -> honest 503
    r = client.post("/api/v1/ai/tutor/chat", headers=student_headers,
                    json={"course_id": course.id, "message": "How do I approach balancing any equation?"})
    assert r.status_code == 503


def test_escalation_roundtrip_with_notifications(client, db, course, instructor, student_user, headers, student_headers):
    from app.models.notification import Notification
    r = client.post("/api/v1/ai/tutor/escalate", headers=student_headers, json={
        "course_id": course.id, "question": "I still don't get why the ratio is 2:1",
        "history": [{"role": "user", "content": "why 2:1?"}, {"role": "assistant", "content": "think about the coefficients"}]})
    assert r.status_code == 201, r.text
    esc = r.json()
    assert esc["status"] == "open" and esc["instructor_id"] == instructor.id and len(esc["context"]["history"]) == 2
    assert db.query(Notification).filter(Notification.user_id == instructor.id, Notification.type == "tutor_escalation").count() == 1
    # instructor sees it in the review queue and replies
    q = client.get("/api/v1/ai/review-queue", headers=headers).json()
    assert q["counts"]["escalations"] == 1 and q["llm_configured"] in (True, False)
    r = client.post(f"/api/v1/ai/tutor/escalations/{esc['id']}/reply", headers=headers, json={"reply": "Because two moles of H2 react per O2."})
    assert r.status_code == 200 and r.json()["status"] == "answered"
    assert db.query(Notification).filter(Notification.user_id == student_user.id, Notification.type == "tutor_escalation_reply").count() == 1
    # learner lists only their own
    mine = client.get("/api/v1/ai/tutor/escalations", headers=student_headers).json()["escalations"]
    assert [e["id"] for e in mine] == [esc["id"]] and mine[0]["instructor_reply"].startswith("Because")
    # the learner cannot reply on the instructor's behalf
    assert client.post(f"/api/v1/ai/tutor/escalations/{esc['id']}/reply", headers=student_headers, json={"reply": "x"}).status_code == 403


def test_error_report_flow(client, db, course, instructor, student_user, headers, student_headers):
    from app.models.notification import Notification
    bad = client.post("/api/v1/ai/error-reports", headers=student_headers,
                      json={"course_id": course.id, "kind": "salary", "message": "Option B is also correct"})
    assert bad.status_code == 422
    r = client.post("/api/v1/ai/error-reports", headers=student_headers,
                    json={"course_id": course.id, "kind": "quiz_question", "ref_id": 7, "message": "Option B is also correct"})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert db.query(Notification).filter(Notification.user_id == instructor.id, Notification.type == "content_error_report").count() == 1
    q = client.get("/api/v1/ai/review-queue", headers=headers).json()
    assert q["counts"]["error_reports"] == 1 and q["error_reports"][0]["kind"] == "quiz_question"
    assert client.post(f"/api/v1/ai/error-reports/{rid}/resolve", headers=student_headers, json={"status": "resolved"}).status_code == 403
    r = client.post(f"/api/v1/ai/error-reports/{rid}/resolve", headers=headers, json={"status": "resolved", "resolution": "Fixed the key"})
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    assert client.get("/api/v1/ai/review-queue", headers=headers).json()["counts"]["error_reports"] == 0
    assert db.query(Notification).filter(Notification.user_id == student_user.id, Notification.type == "content_error_resolved").count() == 1


def test_review_queue_drafts_and_item_flags(client, db, course, instructor, headers):
    from app.models.sileos_pack import BankQuestion, QuestionBank
    from app.services import ai_layer_service as svc
    bank = QuestionBank(instructor_id=instructor.id, title="AI drafts")
    db.add(bank)
    db.commit()
    d1 = BankQuestion(bank_id=bank.id, question_title="Draft one?", question_type="multiple_choice", options=["a", "b"], correct_answer=0, tags=["ai-draft"])
    d2 = BankQuestion(bank_id=bank.id, question_title="Draft two?", question_type="multiple_choice", options=["a", "b"], correct_answer=1, tags=["ai-draft"])
    human = BankQuestion(bank_id=bank.id, question_title="Human?", question_type="multiple_choice", options=["a", "b"], correct_answer=1, tags=[])
    db.add_all([d1, d2, human])
    db.commit()
    q = client.get("/api/v1/ai/review-queue", headers=headers).json()
    assert q["counts"]["ai_drafts"] == 2 and {d["question_title"] for d in q["ai_drafts"]} == {"Draft one?", "Draft two?"}
    ok = client.post(f"/api/v1/ai/review-queue/questions/{d1.id}/approve", headers=headers)
    assert ok.status_code == 200 and ok.json()["tags"] == ["reviewed"]
    assert client.post(f"/api/v1/ai/review-queue/questions/{human.id}/reject", headers=headers).status_code == 409
    assert client.post(f"/api/v1/ai/review-queue/questions/{d2.id}/reject", headers=headers).status_code == 200
    assert client.get("/api/v1/ai/review-queue", headers=headers).json()["counts"]["ai_drafts"] == 0
    # derived, explainable flags
    assert svc.flag_reasons({"attempts": 12, "facility": 0.1, "discrimination": 0.3})[0].startswith("very hard")
    assert svc.flag_reasons({"attempts": 12, "facility": 0.98, "discrimination": 0.3})[0].startswith("trivial")
    assert any(r.startswith("negative discrimination") for r in svc.flag_reasons({"attempts": 8, "facility": 0.5, "discrimination": -0.2}))
    assert svc.flag_reasons({"attempts": 4, "facility": 0.0, "discrimination": None}) == []   # too few attempts
    assert svc.flag_reasons({"attempts": 30, "facility": 0.6, "discrimination": 0.4}) == []


def test_adaptive_lesson_and_check_question(client, db, course, instructor, student_user, headers, student_headers, no_llm, fake_llm):
    from app.services import ai_layer_service as svc
    # mode is chosen from the learner's mastery estimate
    assert svc.choose_mode(None) == "consolidate" and svc.choose_mode(20) == "recover" and svc.choose_mode(90) == "extend"
    assert svc.calibrate(20) == "easy" and svc.calibrate(60) == "medium" and svc.calibrate(90) == "hard"
    # fake_llm set the key; verify the 503 path by clearing it again
    import os
    saved = os.environ.pop("GLM_API_KEY")
    r = client.post(f"/api/v1/ai/adaptive-lesson/{course.id}", headers=student_headers, json={})
    assert r.status_code == 503
    os.environ["GLM_API_KEY"] = saved
    fake_llm["reply"] = '{"title": "Ratios, again", "sections": [{"heading": "Why 2:1", "body": "..."}], "check": {"question": "?", "answer": "2"}}'
    r = client.post(f"/api/v1/ai/adaptive-lesson/{course.id}", headers=student_headers, json={"mode": "recover", "concept": "stoichiometry"})
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "recover" and r.json()["lesson"]["title"] == "Ratios, again" and r.json()["job_id"]
    assert "MODE: recover" in fake_llm["prompts"][-1][1]
    assert client.post(f"/api/v1/ai/adaptive-lesson/{course.id}", headers=student_headers, json={"mode": "faster"}).status_code == 422
    # a learner cannot target another learner; the owner can
    assert client.post(f"/api/v1/ai/adaptive-lesson/{course.id}", headers=student_headers, json={"student_id": instructor.id}).status_code == 403
    assert client.post(f"/api/v1/ai/adaptive-lesson/{course.id}", headers=headers, json={"student_id": student_user.id}).status_code == 200
    fake_llm["reply"] = '{"question": "What limits the yield?", "kind": "open", "answer": "the limiting reagent", "why": "core idea"}'
    r = client.post("/api/v1/ai/tutor/check-question", headers=student_headers, json={"course_id": course.id, "concept": "stoichiometry"})
    assert r.status_code == 200 and r.json()["check"]["kind"] == "open" and r.json()["level"] == "medium"


def _ended_class(db, course, instructor):
    from app.services import class_report_service as crs
    now = datetime.now(timezone.utc)
    lc = LiveClass(course_id=course.id, instructor_id=instructor.id, title="Transcribed class", room_name="ai-room-1",
                   scheduled_start=now - timedelta(hours=2), scheduled_end=now - timedelta(hours=1),
                   status=LiveClassStatus.ENDED, started_at=now - timedelta(hours=2), ended_at=now - timedelta(hours=1), settings={})
    db.add(lc)
    db.commit()
    db.refresh(lc)
    crs.generate_report(db, lc)
    db.commit()
    return lc


def test_transcript_ingest_without_and_with_llm(client, db, course, instructor, headers, student_headers, no_llm, monkeypatch):
    from app.core.config import get_settings
    from app.models.live_class_report import ClassReport
    from app.models.mastery import ConceptLink
    lc = _ended_class(db, course, instructor)
    text = "Today we balance equations. Coefficients scale whole molecules. " * 5
    # learner cannot paste
    assert client.post(f"/api/v1/live/classes/{lc.id}/report/transcript", headers=student_headers, json={"transcript": text}).status_code == 403
    r = client.post(f"/api/v1/live/classes/{lc.id}/report/transcript", headers=headers, json={"transcript": text})
    assert r.status_code == 200, r.text
    assert r.json()["processing_status"] == "transcribed" and r.json()["ai_topics"] is None
    rep = db.query(ClassReport).filter(ClassReport.class_id == lc.id).first()
    db.refresh(rep)
    assert rep.transcript.startswith("Today we balance") and rep.processing_status == "transcribed"
    # worker path: internal token required
    settings = get_settings()
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", "test-internal-token-0123456789")
    assert client.post("/api/v1/internal/live/transcripts", json={"class_id": lc.id, "transcript": text}).status_code == 403
    # with the LLM configured the worker ingest segments + propagates concepts
    from app.services import ai_layer_service
    monkeypatch.setenv("GLM_API_KEY", "test-key")
    monkeypatch.setattr(ai_layer_service, "call_glm", lambda system, prompt, **kw:
                        '[{"topic": "Balancing equations", "summary": "s", "concepts": ["Balancing Chemical Equations", "coefficients"], "start_hint": "Today"}]')
    r = client.post("/api/v1/internal/live/transcripts", headers={"X-Internal-Token": "test-internal-token-0123456789"},
                    json={"class_id": lc.id, "transcript": text})
    assert r.status_code == 200, r.text
    assert r.json()["processing_status"] == "processed" and r.json()["ai_topics"][0]["topic"] == "Balancing equations"
    db.refresh(rep)
    assert rep.processing_status == "processed" and rep.ai_topics[0]["concepts"][1] == "coefficients"
    links = {l.concept for l in db.query(ConceptLink).filter(ConceptLink.kind == "live_class", ConceptLink.ref_id == str(lc.id)).all()}
    assert links == {"balancing chemical equations", "coefficients"}
    # the report endpoint exposes the transcript + topics to the owner
    rep_out = client.get(f"/api/v1/live/classes/{lc.id}/report", headers=headers).json()
    assert rep_out["processing_status"] == "processed" and rep_out["ai_topics"]
