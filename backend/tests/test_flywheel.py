"""WP8 flywheel extras (v2.0 §10) + WP9 GLB budget (§11): next-class agenda
derived from report + mastery + open loops (no LLM), insight cards from 3D
path evidence × quiz outcomes, peer teach-back write/rate/hide with XP and
a weak mastery signal, DigiLocker adapter honest 503, and the GLB budget
parser rejecting over hard caps / warning per tier on upload + import.
"""
import json
import struct
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="fly-inst@example.com")
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
def peer(db, make_user):
    return make_user(role="student", email="fly-peer@example.com")


@pytest.fixture
def peer_headers(peer):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(peer.id)})}"}


@pytest.fixture
def course(db, instructor, student_user, peer):
    from app.models.course import Course
    c = Course(post_title="Flywheel course", post_content="d", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=0, course_type="seyappaduporul")
    db.add(c)
    db.commit()
    db.refresh(c)
    for u in (student_user, peer):
        db.add(Enrollment(user_id=u.id, course_id=c.id, enrollment_status="enrolled"))
    db.commit()
    return c


def _glb(doc: dict) -> bytes:
    body = json.dumps(doc).encode()
    body += b" " * ((4 - len(body) % 4) % 4)
    return b"glTF" + struct.pack("<II", 2, 12 + 8 + len(body)) + struct.pack("<II", len(body), 0x4E4F534A) + body


def _doc(triangles: int, texture_bytes: int = 0) -> dict:
    return {"asset": {"version": "2.0"},
            "accessors": [{"count": triangles * 3}, {"count": 100}],
            "bufferViews": [{"byteLength": texture_bytes}],
            "images": [{"bufferView": 0}] if texture_bytes else [],
            "meshes": [{"primitives": [{"indices": 0, "attributes": {"POSITION": 1}}]}],
            "materials": [{}], "textures": [{"source": 0}] if texture_bytes else []}


def test_glb_budget_parser_and_tiers():
    from app.services.glb_budget import analyze_glb, GlbBudgetError
    r = analyze_glb(_glb(_doc(120_000, 5 * 1024 * 1024)))
    assert r["triangles"] == 120_000 and r["texture_bytes"] == 5 * 1024 * 1024 and r["meshes"] == 1
    assert r["tiers_ok"] == {"T1": True, "T2": True, "T3": False} and r["lowest_full_tier"] == "T1"
    assert any(w.startswith("T3:") for w in r["warnings"]) and r["reject_reason"] is None
    r = analyze_glb(_glb(_doc(2_000_000)))
    assert r["reject_reason"] and "hard cap" in r["reject_reason"]
    with pytest.raises(GlbBudgetError):
        analyze_glb(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 8 + b"\x00" * 8)


def test_glb_upload_and_import_enforce_budget(client, db, headers, make_user):
    ok = _glb(_doc(1000))
    r = client.post("/api/v1/three-d/models?title=small", headers=headers, files={"file": ("small.glb", ok, "model/gltf-binary")})
    assert r.status_code == 201, r.text
    assert r.json()["budget"]["triangles"] == 1000 and r.json()["budget"]["tiers_ok"]["T3"] is True
    huge = _glb(_doc(1_600_000))
    r = client.post("/api/v1/three-d/models?title=huge", headers=headers, files={"file": ("huge.glb", huge, "model/gltf-binary")})
    assert r.status_code == 422 and "hard cap" in r.json()["detail"]
    from app.core.security import create_access_token
    admin = make_user(role="admin", email="fly-admin@example.com")
    ah = {"Authorization": f"Bearer {create_access_token({'sub': str(admin.id)})}"}
    r = client.post("/api/v1/admin/content-library/three-d/import", headers=ah,
                    files=[("files", ("a.glb", ok, "model/gltf-binary")), ("files", ("b.glb", huge, "model/gltf-binary"))])
    assert r.status_code == 422   # all-or-nothing: the bad file blocks the batch
    from app.models.three_d import ThreeDModel
    assert db.query(ThreeDModel).filter(ThreeDModel.is_library.is_(True)).count() == 0
    r = client.post("/api/v1/admin/content-library/three-d/import", headers=ah, files=[("files", ("a.glb", ok, "model/gltf-binary"))])
    assert r.status_code == 201 and r.json()["models"][0]["budget"]["triangles"] == 1000


def test_next_agenda_is_derived_without_llm(client, db, course, instructor, student_user, peer, headers, student_headers, monkeypatch):
    from app.models.live_class import LiveClass, LiveClassStatus
    from app.models.live_class_report import ClassReport
    from app.models.mastery import LearnerMastery
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    now = datetime.now(timezone.utc)
    lc = LiveClass(course_id=course.id, instructor_id=instructor.id, title="Week 3", room_name="fly-room",
                   scheduled_start=now - timedelta(hours=2), scheduled_end=now - timedelta(hours=1), status=LiveClassStatus.ENDED,
                   started_at=now - timedelta(hours=2), ended_at=now - timedelta(hours=1), settings={})
    db.add(lc)
    db.commit()
    db.add(ClassReport(class_id=lc.id, course_id=course.id, instructor_id=instructor.id, title="Week 3",
                       attendance=[{"user_id": student_user.id, "present": True}], event_log=[], poll_results=[], engagement={},
                       ai_topics=[{"topic": "Balancing equations"}, {"topic": "Limiting reagent"}]))
    for uid, est in ((student_user.id, 30.0), (peer.id, 45.0)):
        db.add(LearnerMastery(user_id=uid, concept="stoichiometry", estimate=est, confidence=0.6, evidence_count=2))
    db.add(LearnerMastery(user_id=peer.id, concept="gas laws", estimate=80.0, confidence=0.6, evidence_count=2))
    db.commit()
    client.post("/api/v1/ai/tutor/escalate", headers=student_headers, json={"course_id": course.id, "question": "Why does the limiting reagent decide the yield?"})
    assert client.get(f"/api/v1/flywheel/courses/{course.id}/next-agenda", headers=student_headers).status_code == 403
    r = client.get(f"/api/v1/flywheel/courses/{course.id}/next-agenda", headers=headers)
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["based_on_class_id"] == lc.id and a["absent_count"] == 1 and a["open_escalations"] == 1
    assert a["weak_concepts"] == [{"concept": "stoichiometry", "learners": 2, "avg_estimate": 37.5}]
    kinds = [i["kind"] for i in a["agenda"]]
    assert kinds == ["recap", "reteach", "catch_up", "questions"]
    assert "Balancing equations" in a["agenda"][0]["text"] and a["prose"] is None and a["llm_configured"] is False


def test_insight_cards_from_3d_paths(client, db, course, instructor, student_user, peer, headers):
    from app.models.mastery import MasteryEvidence
    from app.models.quiz import Quiz
    from app.models.three_d import ThreeDModel
    from app.models.three_d_task import ThreeDTask, ThreeDTaskAttempt
    model = ThreeDModel(owner_id=instructor.id, title="m", file_path="x/y.glb", file_size_bytes=10, format="glb")
    db.add(model)
    db.commit()
    task = ThreeDTask(owner_id=instructor.id, model_id=model.id, title="Heart chambers", task_type="identify",
                      config={"anchors": [], "prompts": []}, concepts=["heart anatomy"], status="published")
    db.add(task)
    db.commit()
    db.add(Quiz(post_author=instructor.id, post_title="Unit quiz", post_parent=course.id,
                interactive_modules=[{"kind": "three_d_task", "id": task.id, "title": "Heart chambers"}]))
    db.add_all([
        ThreeDTaskAttempt(task_id=task.id, user_id=student_user.id, score=40, max_score=40, mode="T1", confidence="clean"),
        ThreeDTaskAttempt(task_id=task.id, user_id=peer.id, score=40, max_score=40, mode="T1", confidence="trial_and_error"),
        MasteryEvidence(user_id=student_user.id, concept="heart anatomy", source_kind="quiz", source_ref="1", score_pct=90, weight=1),
        MasteryEvidence(user_id=peer.id, concept="heart anatomy", source_kind="quiz", source_ref="1", score_pct=40, weight=1),
    ])
    db.commit()
    r = client.get(f"/api/v1/flywheel/courses/{course.id}/insight-cards", headers=headers)
    assert r.status_code == 200, r.text
    card = r.json()["cards"][0]
    assert card["task_title"] == "Heart chambers" and card["attempts"] == 2
    assert card["paths"]["clean"]["avg_quiz_score"] == 90 and card["paths"]["trial_and_error"]["avg_quiz_score"] == 40
    texts = " ".join(card["insights"])
    assert "trial and error" in texts and "path signal predicts understanding" in texts and "full marks" in texts


def test_teach_back_write_rate_hide(client, db, course, student_user, peer, headers, student_headers, peer_headers):
    from app.models.gamification import XpEvent
    from app.models.mastery import LearnerMastery
    short = client.post("/api/v1/flywheel/teach-back", headers=student_headers, json={"concept": "Stoichiometry", "text": "too short", "course_id": course.id})
    assert short.status_code == 422
    text = "Stoichiometry is just bookkeeping for atoms: balance the equation, convert grams to moles, use the ratio, convert back."
    r = client.post("/api/v1/flywheel/teach-back", headers=student_headers, json={"concept": "Stoichiometry", "text": text, "course_id": course.id})
    assert r.status_code == 201, r.text
    tb = r.json()
    assert tb["concept"] == "stoichiometry" and tb["helpful_count"] == 0
    assert db.query(XpEvent).filter(XpEvent.event_type == "teach_back_written", XpEvent.user_id == student_user.id).count() == 1
    lm = db.query(LearnerMastery).filter(LearnerMastery.user_id == student_user.id, LearnerMastery.concept == "stoichiometry").first()
    assert lm is not None and lm.evidence_count == 1
    # author cannot self-rate; peer can, and can change their vote
    assert client.post(f"/api/v1/flywheel/teach-back/{tb['id']}/rate", headers=student_headers, json={"helpful": True}).status_code == 422
    r = client.post(f"/api/v1/flywheel/teach-back/{tb['id']}/rate", headers=peer_headers, json={"helpful": True})
    assert r.status_code == 200 and r.json()["helpful_count"] == 1 and r.json()["changed"] is True
    r = client.post(f"/api/v1/flywheel/teach-back/{tb['id']}/rate", headers=peer_headers, json={"helpful": True})
    assert r.json()["changed"] is False and r.json()["helpful_count"] == 1
    r = client.post(f"/api/v1/flywheel/teach-back/{tb['id']}/rate", headers=peer_headers, json={"helpful": False})
    assert r.json()["helpful_count"] == 0 and r.json()["not_helpful_count"] == 1
    lst = client.get("/api/v1/flywheel/teach-back?concept=stoichiometry", headers=peer_headers).json()["teach_backs"]
    assert len(lst) == 1 and lst[0]["my_vote"] is False and lst[0]["author"]
    # moderation: owner hides, list no longer shows it
    assert client.post(f"/api/v1/flywheel/teach-back/{tb['id']}/hide", headers=headers).status_code == 200
    assert client.get("/api/v1/flywheel/teach-back?concept=stoichiometry", headers=peer_headers).json()["teach_backs"] == []


def test_digilocker_adapter_honest_503(client, db, course, student_user, student_headers, monkeypatch):
    from app.models.certificate import Certificate, IssuedCertificate
    monkeypatch.delenv("DIGILOCKER_CLIENT_ID", raising=False)
    monkeypatch.delenv("DIGILOCKER_CLIENT_SECRET", raising=False)
    st = client.get("/api/v1/flywheel/digilocker/status", headers=student_headers).json()
    assert st["configured"] is False and "DIGILOCKER_CLIENT_ID" in st["needs"]
    cert = Certificate(post_author=course.post_author, post_title="Completion")
    db.add(cert)
    db.commit()
    issued = IssuedCertificate(certificate_id=cert.id, course_id=course.id, user_id=student_user.id, certificate_hash="h1",
                               secure_certificate_id="SI-0001", certificate_title="Completion", completion_date=datetime.now(timezone.utc))
    db.add(issued)
    db.commit()
    r = client.post(f"/api/v1/flywheel/certificates/{issued.id}/digilocker", headers=student_headers)
    assert r.status_code == 503 and "DIGILOCKER_CLIENT_ID" in r.json()["detail"]
    monkeypatch.setenv("DIGILOCKER_CLIENT_ID", "x")
    monkeypatch.setenv("DIGILOCKER_CLIENT_SECRET", "y")
    r = client.post(f"/api/v1/flywheel/certificates/{issued.id}/digilocker", headers=student_headers)
    assert r.status_code == 200 and r.json()["document"]["uri_suffix"] == "SI-0001"
