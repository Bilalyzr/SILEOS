"""Content libraries (2026-09-05): admin-curated virtual labs, prebuilt game
packs, and the shared 3D asset library — plus the instructor-side seams
(catalog listing, native lab results, cross-owner attach rules).
"""
import pytest

GLB = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 60
ADMIN_BASE = "/api/v1/admin/content-library"


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="lib-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def instructor_headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def admin(make_user):
    return make_user(role="admin", email="lib-admin@example.com")


@pytest.fixture
def admin_headers(admin):
    # Admin logins require TOTP; mint the bearer directly (same as test_bundle_api).
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(admin.id)})}"}


def _course(db, instructor, course_type="utporul"):
    from app.models.course import Course
    c = Course(post_title=f"Lib course {course_type}", post_content="d", post_excerpt="p",
               post_status="publish", post_author=instructor.id,
               course_price=0, course_type=course_type)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ------------------------------------------------------------ catalog

@pytest.mark.usefixtures("authored_native_labs")
def test_catalog_merges_builtins_and_native_detail(client, instructor_headers):
    r = client.get("/api/v1/virtual-labs")
    assert r.status_code == 200
    by_slug = {l["slug"]: l for l in r.json()["labs"]}
    assert "cbse-projectile-motion" in by_slug and by_slug["cbse-projectile-motion"]["provider"] == "embed"
    native = by_slug["fixture-reaction-lab"]
    assert native["provider"] == "native" and native["native_template"] == "reaction_lab"
    assert native["max_score"] == 100          # 10 reactions × 10, derived
    assert "config" not in native              # list never ships answer keys
    assert by_slug["fixture-cell-identify"]["max_score"] == 110
    assert by_slug["fixture-skeleton-identify"]["max_score"] == 140

    r = client.get("/api/v1/virtual-labs?subject=biology")
    assert all(l["subject"] == "biology" for l in r.json()["labs"])

    # detail (auth) ships the config for the player
    r = client.get("/api/v1/virtual-labs/fixture-reaction-lab", headers=instructor_headers)
    assert r.status_code == 200
    assert len(r.json()["config"]["reactions"]) == 10
    assert r.json()["best_score"] is None
    assert client.get("/api/v1/virtual-labs/fixture-reaction-lab").status_code == 401
    assert client.get("/api/v1/virtual-labs/no-such-lab", headers=instructor_headers).status_code == 404


@pytest.mark.usefixtures("authored_native_labs")
def test_builtin_native_configs_pass_their_own_validator(authored_native_labs):
    from app.routers.virtual_labs import BUILTIN_LABS
    from app.schemas.lab_config import validate_lab_config
    assert len(BUILTIN_LABS) == 59
    assert all(lab['provider'] == 'embed' for lab in BUILTIN_LABS)
    assert len(authored_native_labs) == 3
    for lab in authored_native_labs:
        validate_lab_config(lab.native_template, lab.config)


def test_reaction_validator_rejects_unbalanced_and_non_lowest_terms():
    from app.schemas.lab_config import LabConfigError, parse_formula, validate_lab_config
    assert parse_formula("Ca(OH)2") == {"Ca": 1, "O": 2, "H": 2}
    assert parse_formula("Fe2(SO4)3") == {"Fe": 2, "S": 3, "O": 12}
    base = {"reactants": [{"formula": "H2", "name": "h"}, {"formula": "O2", "name": "o"}],
            "products": [{"formula": "H2O", "name": "w"}]}
    with pytest.raises(LabConfigError) as e:
        validate_lab_config("reaction_lab", {"reactions": [dict(base, coefficients=[1, 1, 1])]})
    assert "balance" in e.value.detail
    with pytest.raises(LabConfigError) as e:
        validate_lab_config("reaction_lab", {"reactions": [dict(base, coefficients=[4, 2, 4])]})
    assert "lowest terms" in e.value.detail
    ok = validate_lab_config("reaction_lab", {"reactions": [dict(base, coefficients=[2, 1, 2])]})
    assert ok["reactions"][0]["coefficients"] == [2, 1, 2]
    with pytest.raises(LabConfigError):
        validate_lab_config("identify_lab", {"diagram": "brain", "hotspots": [
            {"id": "a", "label": "A", "x": 1, "y": 1}, {"id": "b", "label": "B", "x": 2, "y": 2},
            {"id": "a", "label": "C", "x": 3, "y": 3}]})


# ------------------------------------------------------------ admin labs

def test_admin_lab_crud_import_and_instructor_attach(client, db, admin_headers, instructor, instructor_headers):
    # authz
    r = client.post(f"{ADMIN_BASE}/labs", json={"slug": "x-lab", "title": "X", "provider": "embed",
                                               "embed_url": "https://example.org/x"}, headers=instructor_headers)
    assert r.status_code == 403

    r = client.post(f"{ADMIN_BASE}/labs", json={
        "slug": "chem-titration", "title": "Acid-base titration", "subject": "chemistry",
        "provider": "embed", "embed_url": "https://example.org/titration",
    }, headers=admin_headers)
    assert r.status_code == 201, r.text
    lab_id = r.json()["catalog_id"]
    assert client.post(f"{ADMIN_BASE}/labs", json={
        "slug": "chem-titration", "title": "dup", "provider": "embed", "embed_url": "https://example.org/x",
    }, headers=admin_headers).status_code == 409

    # native entry with a wrong answer key is refused with the reason
    r = client.post(f"{ADMIN_BASE}/labs", json={
        "slug": "bad-reactions", "title": "Bad", "provider": "native", "native_template": "reaction_lab",
        "config": {"reactions": [{"reactants": [{"formula": "H2", "name": "h"}, {"formula": "O2", "name": "o"}],
                                  "products": [{"formula": "H2O", "name": "w"}], "coefficients": [1, 1, 1]}]},
    }, headers=admin_headers)
    assert r.status_code == 400 and "balance" in r.json()["detail"]

    # pack import: phet (embed_url derived) + native identify; all-or-nothing
    pack = {"labs": [
        {"slug": "density", "title": "Density", "subject": "physics", "provider": "phet"},
        {"slug": "leaf-identify", "title": "Leaf parts", "subject": "biology", "provider": "native",
         "native_template": "identify_lab",
         "config": {"diagram": "https://example.org/leaf.png", "hotspots": [
             {"id": "blade", "label": "Blade", "x": 50, "y": 40},
             {"id": "midrib", "label": "Midrib", "x": 50, "y": 60},
             {"id": "petiole", "label": "Petiole", "x": 50, "y": 90}]}},
    ]}
    r = client.post(f"{ADMIN_BASE}/labs/import", json=pack, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"created": 2, "updated": 0, "slugs": ["density", "leaf-identify"]}
    r = client.post(f"{ADMIN_BASE}/labs/import", json=pack, headers=admin_headers)
    assert r.json()["updated"] == 2 and r.json()["created"] == 0
    bad_pack = {"labs": pack["labs"] + [{"slug": "broken", "title": "B", "provider": "embed", "embed_url": "http://insecure"}]}
    r = client.post(f"{ADMIN_BASE}/labs/import", json=bad_pack, headers=admin_headers)
    assert r.status_code == 400 and "labs[2]" in r.json()["detail"]

    listed = {l["slug"]: l for l in client.get("/api/v1/virtual-labs").json()["labs"]}
    assert "density" not in listed  # retired PhET rows stay out of the active library
    assert listed["leaf-identify"]["max_score"] == 30
    assert "chem-titration" in listed
    admin_view = client.get(f"{ADMIN_BASE}/labs", headers=admin_headers).json()
    assert {l["slug"] for l in admin_view["labs"]} == {"chem-titration", "density", "leaf-identify"}
    assert any(b["slug"] == "cbse-projectile-motion" for b in admin_view["builtin"])

    # instructor attaches the admin-added lab; unknown slug is a 422
    course = _course(db, instructor)
    r = client.post(f"/api/v1/courses/{course.id}/lessons", json={
        "title": "Titration", "lesson_content_type": "virtual_lab", "virtual_lab_sim": "chem-titration",
    }, headers=instructor_headers)
    assert r.status_code == 200, r.text
    assert r.json()["virtual_lab_sim"] == "chem-titration"
    r = client.post(f"/api/v1/courses/{course.id}/lessons", json={
        "title": "Nope", "lesson_content_type": "virtual_lab", "virtual_lab_sim": "unknown-lab",
    }, headers=instructor_headers)
    assert r.status_code == 422

    # unpublish hides it from the catalog and from new attaches
    r = client.put(f"{ADMIN_BASE}/labs/{lab_id}", json={
        "slug": "chem-titration", "title": "Acid-base titration", "subject": "chemistry",
        "provider": "embed", "embed_url": "https://example.org/titration", "is_published": False,
    }, headers=admin_headers)
    assert r.status_code == 200 and r.json()["is_published"] is False
    assert "chem-titration" not in {l["slug"] for l in client.get("/api/v1/virtual-labs").json()["labs"]}
    r = client.post(f"/api/v1/courses/{course.id}/lessons", json={
        "title": "Again", "lesson_content_type": "virtual_lab", "virtual_lab_sim": "chem-titration",
    }, headers=instructor_headers)
    assert r.status_code == 422

    # delete blocked while a lesson references the slug
    assert client.delete(f"{ADMIN_BASE}/labs/{lab_id}", headers=admin_headers).status_code == 409


# ------------------------------------------------------------ native results + XP

@pytest.mark.usefixtures("authored_native_labs")
def test_native_lab_results_cap_and_award_xp(client, db, student_user, as_user):
    as_user(student_user)
    r = client.post("/api/v1/virtual-labs/fixture-reaction-lab/results", json={"score": 50, "duration_s": 120})
    assert r.status_code == 201, r.text
    assert r.json()["max_score"] == 100 and r.json()["best_score"] == 50
    assert client.post("/api/v1/virtual-labs/fixture-reaction-lab/results", json={"score": 101}).status_code == 400
    assert client.post("/api/v1/virtual-labs/projectile-motion/results", json={"score": 1}).status_code == 400
    assert client.post("/api/v1/virtual-labs/fixture-reaction-lab/results", json={"score": "50"}).status_code == 422
    r = client.post("/api/v1/virtual-labs/fixture-reaction-lab/results", json={"score": 100})
    assert r.status_code == 201 and r.json()["best_score"] == 100

    from app.services import gamification_service as gs
    events = {e.event_type for e in db.query(gs.XpEvent).filter(gs.XpEvent.user_id == student_user.id).all()}
    assert {"lab_completed", "lab_perfect"} <= events
    r = client.get("/api/v1/virtual-labs/fixture-reaction-lab")
    assert r.json()["best_score"] == 100


# ------------------------------------------------------------ prebuilt games

def test_game_pack_import_publishes_to_marketplace_and_attaches_cross_owner(
        client, db, admin_headers, instructor, instructor_headers):
    r = client.post(f"{ADMIN_BASE}/games/import-defaults", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert len(r.json()["created"]) == 7 and r.json()["skipped"] == []
    r = client.post(f"{ADMIN_BASE}/games/import-defaults", headers=admin_headers)
    assert len(r.json()["created"]) == 0 and len(r.json()["skipped"]) == 7

    # a bad pack is rejected before anything is written
    r = client.post(f"{ADMIN_BASE}/games/import", json={"games": [
        {"title": "Broken", "template": "quiz_rush",
         "config": {"items": [{"prompt": "?", "options": ["a", "b"], "answer_index": 5}]}}]},
        headers=admin_headers)
    assert r.status_code == 400 and "games[0]" in r.json()["detail"]
    assert client.post(f"{ADMIN_BASE}/games/import-defaults", headers=instructor_headers).status_code == 403

    mkt = client.get("/api/v1/games/marketplace", headers=instructor_headers).json()
    titles = {g["title"] for g in (mkt if isinstance(mkt, list) else mkt.get("games", []))}
    assert "Stages of Mitosis in Order" in titles
    prebuilt = [g for g in client.get(f"{ADMIN_BASE}/games", headers=admin_headers).json()["games"]
                if g["title"] == "Stages of Mitosis in Order"][0]
    assert prebuilt["status"] == "published" and prebuilt["is_listed"] is True

    course = _course(db, instructor, course_type="seyappaduporul")
    r = client.post(f"/api/v1/courses/{course.id}/lessons", json={
        "title": "Mitosis game", "lesson_content_type": "game", "game_id": prebuilt["id"],
    }, headers=instructor_headers)
    assert r.status_code == 200, r.text
    assert r.json()["game_id"] == prebuilt["id"]


# ------------------------------------------------------------ 3D library

def test_three_d_library_import_and_cross_owner_attach(
        client, db, admin_headers, instructor, instructor_headers, tmp_path, monkeypatch):
    from app.routers import three_d as three_d_mod
    monkeypatch.setattr(three_d_mod, "BASE_DIR", str(tmp_path))

    assert client.get(f"{ADMIN_BASE}/three-d", headers=instructor_headers).status_code == 403

    # all-or-nothing: one bad file rejects the whole batch
    r = client.post(f"{ADMIN_BASE}/three-d/import", headers=admin_headers, files=[
        ("files", ("skull.glb", GLB, "model/gltf-binary")),
        ("files", ("junk.glb", b"not a glb at all", "model/gltf-binary")),
    ])
    assert r.status_code == 422 and "junk.glb" in r.json()["detail"]
    assert client.get(f"{ADMIN_BASE}/three-d", headers=admin_headers).json()["models"] == []

    r = client.post(f"{ADMIN_BASE}/three-d/import", headers=admin_headers, files=[
        ("files", ("skull.glb", GLB, "model/gltf-binary")),
        ("files", ("cell.glb", GLB, "model/gltf-binary")),
    ])
    assert r.status_code == 201, r.text
    models = r.json()["models"]
    assert {m["title"] for m in models} == {"skull", "cell"}
    assert all(m["is_library"] for m in models)
    skull = next(m for m in models if m["title"] == "skull")

    # instructors see the shared library (separate from their own uploads)
    mine = client.get("/api/v1/three-d/models", headers=instructor_headers).json()
    assert mine["models"] == [] and {m["id"] for m in mine["library"]} == {m["id"] for m in models}
    assert client.get(f"/api/v1/three-d/models/{skull['id']}/file", headers=instructor_headers).status_code == 200

    # cross-owner attach allowed for library models (UP course), 403 once un-shared
    course = _course(db, instructor, course_type="utporul")
    r = client.post(f"/api/v1/courses/{course.id}/lessons", json={
        "title": "Skull", "lesson_content_type": "three_d", "three_d_model_id": skull["id"],
    }, headers=instructor_headers)
    assert r.status_code == 200, r.text
    assert r.json()["three_d_model_id"] == skull["id"]

    cell = next(m for m in models if m["title"] == "cell")
    r = client.patch(f"{ADMIN_BASE}/three-d/{cell['id']}", json={"is_library": False}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["is_library"] is False
    r = client.post(f"/api/v1/courses/{course.id}/lessons", json={
        "title": "Cell", "lesson_content_type": "three_d", "three_d_model_id": cell["id"],
    }, headers=instructor_headers)
    assert r.status_code == 403

    # delete blocked while attached; free model deletes
    assert client.delete(f"{ADMIN_BASE}/three-d/{skull['id']}", headers=admin_headers).status_code == 409
    assert client.delete(f"{ADMIN_BASE}/three-d/{cell['id']}", headers=admin_headers).status_code == 200
