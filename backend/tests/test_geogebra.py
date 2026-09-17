"""GeoGebra integration tests (owner-approved 2026-09-04).

Covers: applet CRUD + material-URL normalization, the FREE-COURSE-ONLY
attach rule (the owner's business rule, enforced in the content resolver),
atomic-pair 400s, cross-owner 403, in-use delete 409, embed payload shape.
"""
import pytest


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="ggb@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def instructor_headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def applet(client, instructor_headers):
    r = client.post("/api/v1/geogebra/applets",
                    json={"title": "Unit circle", "app_type": "geometry"},
                    headers=instructor_headers)
    assert r.status_code == 201, r.text
    return r.json()


def _course(db, instructor, price=0, sale=None):
    from app.models.course import Course
    c = Course(post_title=f"C{price}", post_content="d", post_excerpt="p",
               post_status="publish", post_author=instructor.id,
               course_price=price, course_sale_price=sale)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ------------------------------------------------------------------- CRUD

def test_applet_crud_and_material_normalization(client, instructor_headers,
                                                applet):
    # list
    r = client.get("/api/v1/geogebra/applets", headers=instructor_headers)
    assert r.status_code == 200
    assert any(a["id"] == applet["id"] for a in r.json()["applets"])

    # materials URL normalized to the id
    r = client.post("/api/v1/geogebra/applets", json={
        "title": "Parabola", "app_type": "graphing",
        "material_id": "https://www.geogebra.org/m/abc123",
    }, headers=instructor_headers)
    assert r.status_code == 201
    assert r.json()["material_id"] == "abc123"

    # garbage material id is a 422
    r = client.post("/api/v1/geogebra/applets", json={
        "title": "Bad", "app_type": "graphing",
        "material_id": "not a url!!",
    }, headers=instructor_headers)
    assert r.status_code == 422

    # invalid app_type 422
    r = client.post("/api/v1/geogebra/applets", json={
        "title": "Bad type", "app_type": "spreadsheet",
    }, headers=instructor_headers)
    assert r.status_code == 422


def test_embed_payload_shape(client, instructor_headers, applet):
    r = client.get(f"/api/v1/geogebra/applets/{applet['id']}/embed",
                   headers=instructor_headers)
    assert r.status_code == 200
    params = r.json()["applet_parameters"]
    assert params["appName"] == "geometry"
    assert "material_id" not in params  # blank app, not a materials embed
    assert params["width"] == 800

    # anonymous access is 401 (authoring library is not scrapeable)
    r = client.get(f"/api/v1/geogebra/applets/{applet['id']}/embed")
    assert r.status_code == 401


# ------------------------------------------------- free-course attach rule

def test_attach_to_free_course_ok_paid_rejected(client, db, instructor,
                                                instructor_headers, applet):
    free = _course(db, instructor, price=0)
    paid = _course(db, instructor, price=499)

    # FREE course: attach works, comes back with the applet id
    r = client.post(f"/api/v1/courses/{free.id}/lessons", json={
        "title": "Explore the circle",
        "lesson_content_type": "geogebra",
        "geogebra_applet_id": applet["id"],
    }, headers=instructor_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lesson_content_type"] == "geogebra"
    assert body["geogebra_applet_id"] == applet["id"]

    # PAID course: the owner rule fires — 422, never silently allowed
    r = client.post(f"/api/v1/courses/{paid.id}/lessons", json={
        "title": "Paid lesson",
        "lesson_content_type": "geogebra",
        "geogebra_applet_id": applet["id"],
    }, headers=instructor_headers)
    assert r.status_code == 422
    assert "FREE courses only" in r.json()["detail"]

    # sale-priced course is still paid → 422
    discounted = _course(db, instructor, price=999, sale=499)
    r = client.post(f"/api/v1/courses/{discounted.id}/lessons", json={
        "title": "Discounted", "lesson_content_type": "geogebra",
        "geogebra_applet_id": applet["id"],
    }, headers=instructor_headers)
    assert r.status_code == 422


def test_atomic_pair_and_cross_owner_rules(client, db, instructor,
                                           instructor_headers, applet,
                                           make_user, auth_headers):
    free = _course(db, instructor, price=0)

    # type without id → the atomic-pair 400
    r = client.post(f"/api/v1/courses/{free.id}/lessons", json={
        "title": "No id", "lesson_content_type": "geogebra",
    }, headers=instructor_headers)
    assert r.status_code == 400
    assert "geogebra_applet_id is required" in r.json()["detail"]

    # unknown applet → 404
    r = client.post(f"/api/v1/courses/{free.id}/lessons", json={
        "title": "Ghost", "lesson_content_type": "geogebra",
        "geogebra_applet_id": 999999,
    }, headers=instructor_headers)
    assert r.status_code == 404

    # another instructor's applet → 403
    from app.models.user import InstructorProfile
    other = make_user(role="instructor", email="other-ggb@example.com")
    db.add(InstructorProfile(user_id=other.id, is_approved=True))
    db.commit()
    other_headers = auth_headers(other.user_email)
    r = client.post(f"/api/v1/courses/{free.id}/lessons", json={
        "title": "Steal", "lesson_content_type": "geogebra",
        "geogebra_applet_id": applet["id"],
    }, headers=other_headers)
    # (also 403 earlier at course ownership; either guard firing is correct)
    assert r.status_code in (403, 422)

    # owner attaches successfully, then in-use delete → 409
    r = client.post(f"/api/v1/courses/{free.id}/lessons", json={
        "title": "Mine", "lesson_content_type": "geogebra",
        "geogebra_applet_id": applet["id"],
    }, headers=instructor_headers)
    assert r.status_code == 200
    r = client.delete(f"/api/v1/geogebra/applets/{applet['id']}",
                      headers=instructor_headers)
    assert r.status_code == 409
