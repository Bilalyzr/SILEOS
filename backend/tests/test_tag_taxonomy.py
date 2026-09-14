"""WP4 — emergent taxonomy (v2.0 §3): normalisation, clustering by
similarity / prefix / co-occurrence, query expansion inside course search,
suggested tags on save, aliases, admin cluster labels, and the type filter
as an implicit catalogue filter.
"""
import json

import pytest


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="tag-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def admin_headers(make_user):
    from app.core.security import create_access_token
    a = make_user(role="admin", email="tag-admin@example.com")
    return {"Authorization": f"Bearer {create_access_token({'sub': str(a.id)})}"}


def _course(db, instructor, title, tags, course_type="seyappaduporul"):
    from app.models.course import Course
    c = Course(post_title=title, post_content="body text here", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=0, course_type=course_type, course_tags=json.dumps(tags))
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_normalisation_and_similarity():
    from app.services.tag_service import normalize_tag, similarity, compute_clusters
    assert normalize_tag(" Class-10_Trigo ") == "class 10 trigo"
    assert normalize_tag("Fractions") == "fraction"
    assert similarity("Trigonometry", "trigonometry") == 1.0
    assert similarity("trigonometry", "trigonometry basics") > 0.5
    clusters = compute_clusters([
        (1, ["trigonometry", "class10-trigo"]),
        (2, ["Trigonometry", "trig"]),
        (3, ["Photosynthesis"]),
        (4, ["maths-trig", "class10-trigo"]),
    ])
    joined = [set(c) for c in clusters]
    trig = next(c for c in joined if "trigonometry" in c)
    assert {"trigonometry", "Trigonometry", "trig", "maths-trig", "class10-trigo"} <= trig   # case, prefix, co-occurrence
    assert {"Photosynthesis"} in joined


def test_search_expands_across_the_cluster(client, db, instructor):
    a = _course(db, instructor, "Angles and triangles", ["Trigonometry"])
    b = _course(db, instructor, "Board exam maths", ["trig", "maths-trig"])
    c = _course(db, instructor, "Plant biology", ["Photosynthesis"])
    r = client.get("/api/v1/courses/?search=trig")
    assert r.status_code == 200, r.text
    ids = {x["id"] for x in r.json().get("courses", r.json().get("items", []))}
    assert {a.id, b.id} <= ids and c.id not in ids
    r = client.get("/api/v1/tag-taxonomy/expand?q=trigo")
    assert set(r.json()["tags"]) >= {"Trigonometry", "trig", "maths-trig"}
    r = client.get("/api/v1/tag-taxonomy/aliases?tag=trig")
    assert "Trigonometry" in r.json()["aliases"]


def test_type_is_an_implicit_filter(client, db, instructor):
    mp = _course(db, instructor, "3D geometry", ["solids"], course_type="meiporul")
    sp = _course(db, instructor, "Class 9 tuition", ["algebra"], course_type="seyappaduporul")
    r = client.get("/api/v1/courses/?course_type=meiporul")
    ids = {x["id"] for x in r.json().get("courses", r.json().get("items", []))}
    assert mp.id in ids and sp.id not in ids


def test_suggestions_and_admin_labels(client, db, instructor, headers, admin_headers):
    _course(db, instructor, "Organic chemistry crash course", ["Organic Chemistry", "hydrocarbons"])
    r = client.get("/api/v1/tag-taxonomy/suggest", params={
        "title": "Hydrocarbons and alkanes explained", "description": "Naming alkanes, alkenes and functional groups",
        "existing": "alkanes"}, headers=headers)
    assert r.status_code == 200
    sug = r.json()["suggestions"]
    assert "hydrocarbons" in sug and "alkanes" not in sug and "alkenes" in sug
    assert client.get("/api/v1/tag-taxonomy/suggest?title=x").status_code == 401
    # clusters are public; labels are admin-only and survive a recluster
    r = client.get("/api/v1/tag-taxonomy/clusters")
    cluster = next(c for c in r.json()["clusters"] if "hydrocarbons" in c["member_tags"])
    assert client.put(f"/api/v1/tag-taxonomy/clusters/{cluster['id']}", json={"label": "Hydrocarbons"}, headers=headers).status_code == 403
    r = client.put(f"/api/v1/tag-taxonomy/clusters/{cluster['id']}", json={"label": "Hydrocarbons"}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["label"] == "Hydrocarbons"
    r = client.post("/api/v1/tag-taxonomy/clusters/recluster", headers=admin_headers)
    assert r.status_code == 200 and r.json()["clusters"] >= 1
    r = client.get("/api/v1/tag-taxonomy/clusters")
    assert any(c["label"] == "Hydrocarbons" and "hydrocarbons" in c["member_tags"] for c in r.json()["clusters"])
    # a labelled cluster is searchable by its label
    assert "hydrocarbons" in client.get("/api/v1/tag-taxonomy/expand?q=Hydrocarbons").json()["tags"]
