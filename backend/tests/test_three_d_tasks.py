"""WP2 — 3D match-and-verify tasks (v2.0 §6): config validation for all
seven types, server-side parameter grading, evidence → confidence signal,
authoring authz (own / library models), publish gating, quiz insertion via
the ScorableItem contract, and the cumulative three_d_tasks bucket.
"""
import pytest
import json
import struct

_BODY = json.dumps({'asset': {'version': '2.0'}, 'scenes': [], 'nodes': []}).encode()
_BODY += b' ' * (-len(_BODY) % 4)
GLB = b'glTF' + struct.pack('<IIII', 2, 20 + len(_BODY), len(_BODY), 0x4e4f534a) + _BODY
A = {"id": "apex", "label": "Apex", "position": [0.5, 1.0, 0.5]}
B = {"id": "base", "label": "Base", "position": [0.5, 0.0, 0.5]}
C = {"id": "side", "label": "Lateral face", "position": [0.9, 0.5, 0.5]}


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="td-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def other_headers(client, db, make_user, auth_headers):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="td-other@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return auth_headers(u.user_email)


@pytest.fixture
def model_id(client, headers, tmp_path, monkeypatch):
    from app.routers import three_d as three_d_mod
    monkeypatch.setattr(three_d_mod, "BASE_DIR", str(tmp_path))
    r = client.post("/api/v1/three-d/models?title=Cone", headers=headers,
                    files={"file": ("cone.glb", GLB, "model/gltf-binary")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture
def student_headers(student_user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}


def _create(client, headers, model_id, task_type, config, expect=201, **extra):
    r = client.post("/api/v1/three-d-tasks", json={"title": f"{task_type} task", "model_id": model_id,
                                                   "task_type": task_type, "config": config, **extra}, headers=headers)
    assert r.status_code == expect, r.text
    return r.json()


def _publish(client, headers, tid):
    r = client.post(f"/api/v1/three-d-tasks/{tid}/publish", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


MATCH = {"anchors": [A, B, C], "pairs": [{"label": "Apex", "anchor_id": "apex"}, {"label": "Base", "anchor_id": "base"}]}
IDENTIFY = {"anchors": [A, B, C], "prompts": [{"condition": "The point farthest from the base", "anchor_id": "apex"}]}
VERIFY = {"parameters": [{"id": "angle", "label": "Plane angle", "min": 0, "max": 90, "unit": "°", "default": 10}],
          "claim": "Slicing at the slant angle gives a parabola", "claim_holds": True,
          "expected_state": [{"param_id": "angle", "min": 44, "max": 46}],
          "must_explore": [{"param_id": "angle", "min": 30, "max": 60}]}
ASSEMBLE = {"slots": [{"id": "top", "label": "Top"}, {"id": "bottom", "label": "Bottom"}],
            "parts": [{"id": "cap", "label": "Cap", "slot_id": "top"}, {"id": "foot", "label": "Foot", "slot_id": "bottom"}]}
MEASURE = {"anchors": [A, B], "questions": [{"prompt": "Height apex→base (cm)", "answer": 12.0, "tolerance": 0.5, "unit": "cm",
                                              "anchor_a": "apex", "anchor_b": "base"}]}
MANIPULATE = {"parameters": [{"id": "r", "label": "Radius", "min": 1, "max": 10}],
              "targets": [{"prompt": "Set the radius so the volume is 100", "param_id": "r", "min": 3, "max": 4}]}
SEQUENCE = {"steps": [{"id": "s1", "text": "Fix the base"}, {"id": "s2", "text": "Attach the shaft"}, {"id": "s3", "text": "Cap it"}]}


def test_all_seven_types_validate_and_derive_max(client, headers, model_id):
    expect = {"match": 20, "identify": 10, "verify": 10, "assemble": 20, "measure": 10, "manipulate": 10, "sequence": 30}
    cfgs = {"match": MATCH, "identify": IDENTIFY, "verify": VERIFY, "assemble": ASSEMBLE, "measure": MEASURE,
            "manipulate": MANIPULATE, "sequence": SEQUENCE}
    for tt, cfg in cfgs.items():
        t = _create(client, headers, model_id, tt, cfg)
        assert t["max_score"] == expect[tt], tt
        assert t["status"] == "draft" and t["tier_floor"] == "T4"
    # regions auto-named, never the label
    t = _create(client, headers, model_id, "match", MATCH)
    assert [a["region"] for a in t["config"]["anchors"]] == ["Region 1", "Region 2", "Region 3"]


def test_config_rejections(client, headers, model_id):
    bad = dict(MATCH, pairs=[{"label": "X", "anchor_id": "nope"}])
    r = client.post("/api/v1/three-d-tasks", json={"title": "b", "model_id": model_id, "task_type": "match", "config": bad}, headers=headers)
    assert r.status_code == 400 and "unknown anchor" in r.json()["detail"]
    bad = dict(MATCH, anchors=[A, dict(B, position=[0.5, 1.5, 0.5])])
    assert client.post("/api/v1/three-d-tasks", json={"title": "b", "model_id": model_id, "task_type": "match", "config": bad}, headers=headers).status_code == 400
    bad = dict(VERIFY, expected_state=[{"param_id": "angle", "min": 80, "max": 100}])
    assert client.post("/api/v1/three-d-tasks", json={"title": "b", "model_id": model_id, "task_type": "verify", "config": bad}, headers=headers).status_code == 400
    bad = dict(ASSEMBLE, parts=[{"id": "cap", "label": "Cap", "slot_id": "nowhere"}, {"id": "x", "label": "X", "slot_id": "top"}])
    assert client.post("/api/v1/three-d-tasks", json={"title": "b", "model_id": model_id, "task_type": "assemble", "config": bad}, headers=headers).status_code == 400
    assert client.post("/api/v1/three-d-tasks", json={"title": "b", "model_id": model_id, "task_type": "teleport", "config": {}}, headers=headers).status_code == 422
    assert client.post("/api/v1/three-d-tasks", json={"title": "b", "model_id": model_id, "task_type": "match", "config": dict(MATCH, extra=1)}, headers=headers).status_code == 400


def test_grading_is_parameter_based_for_every_type():
    from app.schemas.three_d_task_config import grade_task, validate_task_config
    m = validate_task_config("match", MATCH)
    assert grade_task("match", m, {"pairs": {"0": "apex", "1": "side"}})[0] == 10
    i = validate_task_config("identify", IDENTIFY)
    assert grade_task("identify", i, {"selections": ["apex"]})[0] == 10
    assert grade_task("identify", i, {"selections": ["base"]})[0] == 0
    v = validate_task_config("verify", VERIFY)
    ev = [{"type": "param", "param_id": "angle", "value": 20}, {"type": "param", "param_id": "angle", "value": 45}]
    score, d = grade_task("verify", v, {"claim_holds": True, "final_state": {"angle": 45}}, ev)
    assert (score, d["verdict_correct"], d["final_state_ok"], d["path_tested_claim"]) == (10, True, True, True)
    score, d = grade_task("verify", v, {"claim_holds": True, "final_state": {"angle": 45}}, [])
    assert score == 8 and d["path_tested_claim"] is False       # right, but never tested the claim
    assert grade_task("verify", v, {"claim_holds": False, "final_state": {"angle": 10}}, [])[0] == 0
    a = validate_task_config("assemble", ASSEMBLE)
    assert grade_task("assemble", a, {"placements": {"cap": "top", "foot": "top"}})[0] == 10
    me = validate_task_config("measure", MEASURE)
    assert grade_task("measure", me, {"values": [12.4]})[0] == 10
    assert grade_task("measure", me, {"values": ["12.6"]})[0] == 0
    ma = validate_task_config("manipulate", MANIPULATE)
    assert grade_task("manipulate", ma, {"final_state": {"r": 3.5}})[0] == 10
    assert grade_task("manipulate", ma, {"final_state": {"r": 7}})[0] == 0
    s = validate_task_config("sequence", SEQUENCE)
    assert grade_task("sequence", s, {"order": ["s1", "s3", "s2"]})[0] == 10
    assert grade_task("sequence", s, {"order": ["s1", "s2", "s3"]})[0] == 30


def test_confidence_signal_reads_the_path():
    from app.schemas.three_d_task_config import confidence_signal
    clean = [{"type": "rotate"}, {"type": "select", "correct": True}]
    assert confidence_signal(clean, 10, 10)[0] == "clean"
    fumbling = [{"type": "select", "correct": False}, {"type": "select", "correct": False}, {"type": "reset"},
                {"type": "select", "correct": True}]
    label, detail = confidence_signal(fumbling, 10, 10)
    assert label == "trial_and_error" and "trial and error" in detail["note"]
    assert confidence_signal([], 5, 10)[0] == "unknown"


def test_authz_publish_play_attempt_and_quiz_insertion(client, db, headers, other_headers, model_id, student_headers, student_user, instructor):
    t = _create(client, headers, model_id, "identify", IDENTIFY, concepts=["Conic Sections", "conic sections", " apex "])
    assert t["concepts"] == ["conic sections", "apex"]
    tid = t["id"]
    # others cannot read/edit; unpublished task is not playable by students
    assert client.get(f"/api/v1/three-d-tasks/{tid}", headers=other_headers).status_code == 403
    assert client.get(f"/api/v1/three-d-tasks/{tid}/play", headers=student_headers).status_code == 403
    # other instructor cannot build on my private model
    assert client.post("/api/v1/three-d-tasks", json={"title": "x", "model_id": model_id, "task_type": "identify", "config": IDENTIFY},
                       headers=other_headers).status_code == 403
    # quiz insertion refuses drafts, accepts published
    from app.models.course import Course
    course = Course(post_title="3D course", post_content="d", post_excerpt="p", post_status="publish",
                    post_author=instructor.id, course_price=0, course_type="meiporul")
    db.add(course)
    db.commit()
    r = client.post(f"/api/v1/courses/{course.id}/quizzes", json={"title": "q", "questions": [],
                    "interactive_modules": [{"kind": "three_d_task", "id": tid}]}, headers=headers)
    assert r.status_code == 422 and "not published" in r.json()["detail"]
    _publish(client, headers, tid)
    r = client.post(f"/api/v1/courses/{course.id}/quizzes", json={"title": "q", "questions": [],
                    "interactive_modules": [{"kind": "three_d_task", "id": tid, "weight": 2}]}, headers=headers)
    assert r.status_code == 200, r.text
    item = r.json()["interactive_modules"][0]
    assert item["max_score"] == 10 and item["kind"] == "three_d_task"
    # registry lists it
    reg = client.get("/api/v1/scorable-items", headers=headers).json()["items"]
    assert any(i["kind"] == "three_d_task" and i["id"] == tid and i["bucket"] == "three_d_tasks" for i in reg)
    # delete blocked while in a quiz
    assert client.delete(f"/api/v1/three-d-tasks/{tid}", headers=headers).status_code == 409

    # student plays: config ships (advisory), attempt graded server-side, evidence → confidence, XP
    play = client.get(f"/api/v1/three-d-tasks/{tid}/play", headers=student_headers).json()
    assert play["config"]["prompts"][0]["anchor_id"] == "apex" and play["best_score"] is None
    r = client.post(f"/api/v1/three-d-tasks/{tid}/attempts", json={
        "answers": {"selections": ["apex"]}, "mode": "T4", "duration_s": 40,
        "evidence": [{"type": "mode", "value": "T4"}, {"type": "select", "anchor_id": "base", "correct": False},
                     {"type": "select", "anchor_id": "side", "correct": False}, {"type": "select", "anchor_id": "apex", "correct": True}],
    }, headers=student_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["score"] == 10 and body["max_score"] == 10 and body["confidence"] == "trial_and_error" and body["preview"] is False
    # a client-supplied score is ignored — grading comes from state
    r = client.post(f"/api/v1/three-d-tasks/{tid}/attempts", json={"answers": {"selections": ["base"]}, "score": 999}, headers=student_headers)
    assert r.status_code == 201 and r.json()["score"] == 0 and r.json()["best_score"] == 10
    assert client.post(f"/api/v1/three-d-tasks/{tid}/attempts", json={"answers": {}, "evidence": [{"type": "teleport"}]},
                       headers=student_headers).status_code == 422

    from app.services import gamification_service as gs
    kinds = {e.event_type for e in db.query(gs.XpEvent).filter(gs.XpEvent.user_id == student_user.id).all()}
    assert {"three_d_task_completed", "three_d_task_perfect"} <= kinds

    # instructor sees attempts with the confidence signal; owner preview never stores
    att = client.get(f"/api/v1/three-d-tasks/{tid}/attempts", headers=headers).json()["attempts"]
    assert len(att) == 2 and any(a["confidence"] == "trial_and_error" for a in att)
    r = client.post(f"/api/v1/three-d-tasks/{tid}/attempts", json={"answers": {"selections": ["apex"]}}, headers=headers)
    assert r.json()["preview"] is True
    assert len(client.get(f"/api/v1/three-d-tasks/{tid}/attempts", headers=headers).json()["attempts"]) == 2

    # cumulative grade: enrol the student → three_d_tasks bucket = 100
    from app.models.enrollment import Enrollment
    db.add(Enrollment(course_id=course.id, user_id=student_user.id, enrollment_status="enrolled"))
    db.commit()
    g = client.get(f"/api/v1/analytics/courses/{course.id}/students/{student_user.id}/cumulative-grade", headers=student_headers).json()
    assert g["breakdown"]["three_d_tasks"]["average"] == 100.0 and g["cumulative_grade"] == 100.0
