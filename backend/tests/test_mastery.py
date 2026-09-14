"""WP3 — learner mastery graph (v2.0 §9.5, §8.3, §10.1): concept links,
evidence → estimate/confidence with source + path weighting, prerequisites
and recover-first gaps, the coverage/gap report + outcome definition, the
progress map, cross-type evidence from labs/games/3D tasks, and the at-risk
weak-concept rule. Learner-scoped: evidence from any course counts.
"""
import pytest
import json
import struct

_GLB_JSON = json.dumps({"asset": {"version": "2.0"}, "scenes": [], "nodes": []}).encode()
_GLB_JSON += b" " * (-len(_GLB_JSON) % 4)
GLB = b"glTF" + struct.pack("<IIII", 2, 20 + len(_GLB_JSON), len(_GLB_JSON), 0x4e4f534a) + _GLB_JSON
QUIZ_RUSH = {"items": [{"prompt": "2+2?", "options": ["3", "4"], "answer_index": 1}],
             "settings": {"seconds_per_question": 20, "shuffle": False}}


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="mast-inst@example.com")
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


def _course(db, instructor, course_type="utporul"):
    from app.models.course import Course
    c = Course(post_title="Mastery course", post_content="d", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=0, course_type=course_type)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_service_math_source_weights_recency_and_confidence(db, student_user):
    from app.services import mastery_service as ms
    ms.set_links(db, "quiz", 101, ["Fractions", " fractions ", "Ratios"])
    assert ms.concepts_for(db, "quiz", 101) == ["fractions", "ratios"]
    # one supervised quiz at 40% → estimate 40, confidence 1-1/(1+1)=0.5
    ms.record_evidence(db, student_user.id, "quiz", 101, 4, 10)
    g = ms.learner_graph(db, student_user.id)
    f = next(n for n in g["concepts"] if n["concept"] == "fractions")
    assert f["estimate"] == 40.0 and f["confidence"] == 0.5 and f["evidence_count"] == 1
    # a newer 100% game (weight 0.5) pulls the estimate up, recency favours it:
    # (100*0.5 + 40*1*0.85) / (0.5 + 0.85) = 62.2
    ms.set_links(db, "game", 7, ["fractions"])
    ms.record_evidence(db, student_user.id, "game", 7, 10, 10)
    f = next(n for n in ms.learner_graph(db, student_user.id)["concepts"] if n["concept"] == "fractions")
    assert f["estimate"] == 62.2 and f["confidence"] == round(1 - 1 / 2.5, 3)
    # a fumbling 3D path counts half as much as a clean one
    ms.set_links(db, "three_d_task", 3, ["ratios"])
    ms.record_evidence(db, student_user.id, "three_d_task", 3, 10, 10, path_confidence="trial_and_error")
    ev = ms.evidence_for_concept(db, student_user.id, "ratios")
    assert ev[0]["weight"] == 0.5 and ev[0]["detail"] == {"confidence": "trial_and_error"}
    # nothing declared → nothing recorded, no error
    assert ms.record_evidence(db, student_user.id, "quiz", 999, 5, 10) == []
    assert ms.weak_concepts(db, student_user.id) == []   # both ≥ 50 now


def test_prerequisites_and_recover_first(db, client, headers, student_user):
    from app.services import mastery_service as ms
    r = client.put("/api/v1/mastery/prerequisites", json={"concept": "Algebra", "requires": "Fractions"}, headers=headers)
    assert r.status_code == 200 and r.json() == {"concept": "algebra", "requires": "fractions"}
    assert client.put("/api/v1/mastery/prerequisites", json={"concept": "fractions", "requires": "algebra"}, headers=headers).status_code == 422  # cycle
    ms.set_links(db, "quiz", 1, ["fractions"])
    ms.set_links(db, "quiz", 2, ["algebra"])
    ms.record_evidence(db, student_user.id, "quiz", 1, 2, 10)   # fractions 20%
    ms.record_evidence(db, student_user.id, "quiz", 2, 5, 10)   # algebra 50%
    g = ms.learner_graph(db, student_user.id)
    alg = next(n for n in g["concepts"] if n["concept"] == "algebra")
    assert alg["requires"] == ["fractions"] and alg["prerequisite_gaps"] == ["fractions"]
    assert g["recover_first"] == [{"concept": "algebra", "recover_first": ["fractions"]}]
    assert g["weak_concepts"] == ["fractions"]


@pytest.mark.usefixtures("authored_native_labs")
def test_links_api_authz_and_native_lab_concepts(client, db, headers, student_headers, instructor):
    course = _course(db, instructor)
    r = client.put("/api/v1/mastery/links/quiz/55", json={"concepts": ["Kinematics", "Vectors"], "course_id": course.id}, headers=headers)
    assert r.status_code == 200 and r.json()["concepts"] == ["kinematics", "vectors"]
    assert client.put("/api/v1/mastery/links/quiz/55", json={"concepts": ["x"]}, headers=student_headers).status_code == 403
    assert client.put("/api/v1/mastery/links/spaceship/1", json={"concepts": ["x"]}, headers=headers).status_code == 422
    assert client.get("/api/v1/mastery/links/quiz/55", headers=student_headers).json()["concepts"] == ["kinematics", "vectors"]
    # Authored native labs declare their concepts through the mastery links API.
    assert client.get("/api/v1/mastery/links/lab/fixture-reaction-lab", headers=student_headers).json()["concepts"] == \
        ["balancing chemical equations", "conservation of mass", "stoichiometry"]
    assert client.get("/api/v1/mastery/links/lab/fixture-cell-identify", headers=student_headers).json()["concepts"] == ["cell biology", "organelles"]


@pytest.mark.usefixtures("authored_native_labs")
def test_scoring_paths_feed_the_graph_cross_type(client, db, headers, student_headers, student_user, tmp_path, monkeypatch):
    # lab result (native, concepts from catalog)
    r = client.post("/api/v1/virtual-labs/fixture-reaction-lab/results", json={"score": 80, "duration_s": 10}, headers=student_headers)
    assert r.status_code == 201
    g = client.get("/api/v1/mastery/me", headers=student_headers).json()
    st = {n["concept"]: n for n in g["concepts"]}
    assert st["stoichiometry"]["estimate"] == 80.0 and st["stoichiometry"]["evidence_count"] == 1
    # game result (concepts linked by the instructor)
    r = client.post("/api/v1/games", json={"title": "Frac", "template": "quiz_rush", "config": QUIZ_RUSH}, headers=headers)
    gid = r.json()["id"]
    client.post(f"/api/v1/games/{gid}/publish", headers=headers)
    client.put(f"/api/v1/mastery/links/game/{gid}", json={"concepts": ["stoichiometry"]}, headers=headers)
    # 3D task attempt (concepts on the task, mirrored into links on create)
    from app.routers import three_d as three_d_mod
    monkeypatch.setattr(three_d_mod, "BASE_DIR", str(tmp_path))
    m = client.post("/api/v1/three-d/models?title=M", headers=headers, files={"file": ("m.glb", GLB, "model/gltf-binary")}).json()
    cfg = {"anchors": [{"id": "a", "label": "A", "position": [0.5, 0.5, 0.5]}, {"id": "b", "label": "B", "position": [0.1, 0.1, 0.1]}],
           "prompts": [{"condition": "top", "anchor_id": "a"}]}
    t = client.post("/api/v1/three-d-tasks", json={"title": "T", "model_id": m["id"], "task_type": "identify", "config": cfg,
                                                   "concepts": ["Stoichiometry"]}, headers=headers).json()
    assert client.get(f"/api/v1/mastery/links/three_d_task/{t['id']}", headers=headers).json()["concepts"] == ["stoichiometry"]
    client.post(f"/api/v1/three-d-tasks/{t['id']}/publish", headers=headers)
    r = client.post(f"/api/v1/three-d-tasks/{t['id']}/attempts", json={"answers": {"selections": ["b"]}, "mode": "T4"}, headers=student_headers)
    assert r.status_code == 201 and r.json()["score"] == 0
    ev = client.get(f"/api/v1/mastery/students/{student_user.id}/concepts/stoichiometry", headers=headers).json()["evidence"]
    kinds = [e["source_kind"] for e in ev]
    assert kinds[0] == "three_d_task" and "lab" in kinds
    st = {n["concept"]: n for n in client.get("/api/v1/mastery/me", headers=student_headers).json()["concepts"]}
    assert st["stoichiometry"]["evidence_count"] == 2 and st["stoichiometry"]["estimate"] < 80.0
    # weak list is visible to the instructor (Engine D personalisation input)
    assert client.get(f"/api/v1/mastery/students/{student_user.id}/weak", headers=headers).status_code == 200


@pytest.mark.usefixtures("authored_native_labs")
def test_coverage_outcome_and_progress_map(client, db, headers, student_headers, student_user, instructor):
    from app.models.course import Lesson
    from app.models.enrollment import Enrollment
    course = _course(db, instructor, course_type="utporul")
    l1 = Lesson(post_author=instructor.id, post_title="Intro to moles", post_content="x", post_parent=course.id)
    l2 = Lesson(post_author=instructor.id, post_title="Reaction lab", post_content="x", post_parent=course.id,
                lesson_content_type="virtual_lab", virtual_lab_sim="fixture-reaction-lab")
    db.add_all([l1, l2])
    db.add(Enrollment(course_id=course.id, user_id=student_user.id, enrollment_status="enrolled"))
    db.commit()
    q = client.post(f"/api/v1/courses/{course.id}/quizzes", json={"title": "Moles quiz", "questions": [],
                    "interactive_modules": [{"kind": "lab", "id": "fixture-reaction-lab"}]}, headers=headers).json()
    client.put(f"/api/v1/mastery/links/lesson/{l1.id}", json={"concepts": ["mole concept"], "course_id": course.id}, headers=headers)
    client.put(f"/api/v1/mastery/links/quiz/{q['id']}", json={"concepts": ["mole concept", "limiting reagent"], "course_id": course.id}, headers=headers)
    r = client.put(f"/api/v1/mastery/courses/{course.id}/outcome",
                   json={"outcome_text": "Solve JEE stoichiometry problems", "target_concepts": ["stoichiometry", "gas laws"]}, headers=headers)
    assert r.status_code == 200
    assert client.put(f"/api/v1/mastery/courses/{course.id}/outcome", json={"outcome_text": "x"}, headers=student_headers).status_code == 403

    cov = client.get(f"/api/v1/mastery/courses/{course.id}/coverage", headers=headers).json()
    by = {c["concept"]: c for c in cov["concepts"]}
    assert by["mole concept"]["gap"] is None                       # taught (lesson) + assessed (quiz)
    assert by["limiting reagent"]["gap"] == "no_teaching"          # assessed but nothing teaches it
    assert by["stoichiometry"]["gap"] is None and by["stoichiometry"]["is_target"]   # the lab lesson teaches + assesses it
    assert by["gas laws"]["gap"] == "target_uncovered"
    assert cov["summary"]["gaps"] == 2 and cov["outcome"]["target_concepts"] == ["stoichiometry", "gas laws"]

    client.post("/api/v1/virtual-labs/fixture-reaction-lab/results", json={"score": 60}, headers=student_headers)
    pm = client.get(f"/api/v1/mastery/courses/{course.id}/students/{student_user.id}/progress-map", headers=student_headers).json()
    ms = {m["title"]: m for m in pm["milestones"]}
    lab = next(m for m in pm["milestones"] if m["kind"] == "lab")
    assert lab["state"] == "completed" and lab["score_pct"] == 60.0 and lab["mastery"] == 60.0
    assert ms["Intro to moles"]["state"] == "not_started" and ms["Moles quiz"]["state"] == "not_started"


def test_at_risk_flags_weak_concepts(client, db, headers, student_user, instructor):
    from app.models.enrollment import Enrollment
    from app.services import mastery_service as ms
    course = _course(db, instructor)
    db.add(Enrollment(course_id=course.id, user_id=student_user.id, enrollment_status="enrolled"))
    db.commit()
    for i, c in enumerate(["a", "b", "c"]):
        ms.set_links(db, "quiz", 500 + i, [c])
        ms.record_evidence(db, student_user.id, "quiz", 500 + i, 1, 10)   # 10%, confidence 0.5
    r = client.get(f"/api/v1/analytics/courses/{course.id}/at-risk", headers=headers)
    assert r.status_code == 200, r.text
    me = next(x for x in r.json()["results"] if x["user_id"] == student_user.id)
    assert any(reason.startswith("weak concepts: 3") for reason in me["reasons"])
