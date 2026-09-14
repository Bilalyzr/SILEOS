from app.models.bundle import Bundle, BundleCourse
from app.models.cohort import Cohort
from app.models.payment import Order, OrderStatus


def _bundle(db, course_ids, **kw):
    b = Bundle(name=kw.get("name", "Pack"), slug=kw.get("slug", "pack"),
               bundle_price=kw.get("price", 799.0),
               is_active=kw.get("active", True))
    db.add(b)
    db.flush()
    for cid in course_ids:
        db.add(BundleCourse(bundle_id=b.id, course_id=cid))
    db.commit()
    db.refresh(b)
    return b


def test_public_list_active_only_with_prices(client, db, course):
    # The shared `course` fixture persists with post_status="draft" (a
    # pre-existing fixture gap — see task-3-report.md); the public catalog
    # only lists published paid courses, so flip it here rather than in
    # conftest.py.
    course.post_status = "publish"
    db.commit()
    _bundle(db, [course.id])
    _bundle(db, [course.id], name="Off", slug="off", active=False)
    r = client.get("/api/v1/bundles")
    assert r.status_code == 200
    data = r.json()
    assert [b["slug"] for b in data] == ["pack"]
    assert data[0]["combined_price"] == 500.0
    assert data[0]["courses"][0]["id"] == course.id


def test_public_detail_owned_overlap(client, db, student_user, course):
    # GET /{slug} takes AuthService.get_optional_current_user (a real Bearer
    # decode, not the require_admin/get_current_active_user pair the shared
    # `as_user` fixture overrides), so exercise it with a real access token
    # rather than `as_user` — matches the task-3 precedent of fixing gaps
    # like this locally instead of broadening a shared conftest fixture.
    from app.core.security import create_access_token
    from app.models.enrollment import Enrollment
    course.post_status = "publish"
    db.commit()
    b = _bundle(db, [course.id])
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="enrolled"))
    db.commit()
    token = create_access_token({"sub": str(student_user.id)})
    r = client.get(f"/api/v1/bundles/{b.slug}",
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["owned_course_ids"] == [course.id]


def test_public_detail_suspended_row_not_owned(client, db, student_user, course):
    """C1: a suspended membership row must not light the "you already own
    this" badge — the user can still buy the bundle to restore access."""
    from app.core.security import create_access_token
    from app.models.enrollment import Enrollment
    course.post_status = "publish"
    db.commit()
    b = _bundle(db, [course.id])
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="suspended",
                      enrollment_source="membership"))
    db.commit()
    token = create_access_token({"sub": str(student_user.id)})
    r = client.get(f"/api/v1/bundles/{b.slug}",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["owned_course_ids"] == []


def test_public_detail_anonymous_owned_empty(client, db, course):
    course.post_status = "publish"
    db.commit()
    b = _bundle(db, [course.id])
    r = client.get(f"/api/v1/bundles/{b.slug}")
    assert r.status_code == 200
    assert r.json()["owned_course_ids"] == []


def test_public_detail_404_when_inactive(client, db, course):
    course.post_status = "publish"
    db.commit()
    b = _bundle(db, [course.id], active=False)
    r = client.get(f"/api/v1/bundles/{b.slug}")
    assert r.status_code == 404


def test_admin_create_rejects_duplicate_slug(client, db, as_user, student_user, course):
    from tests.test_bundle_fulfillment import _second_course
    c2 = _second_course(db, title="Course DupSlug")
    as_user(student_user)
    r = client.post("/api/v1/admin/bundles", json={
        "name": "First", "slug": "dup-slug", "bundle_price": 100.0,
        "course_ids": [course.id, c2.id]})
    assert r.status_code == 200, r.text
    r = client.post("/api/v1/admin/bundles", json={
        "name": "Second", "slug": "dup-slug", "bundle_price": 200.0,
        "course_ids": [course.id, c2.id]})
    assert r.status_code == 409, r.text


def test_admin_create_validates_min_courses(client, db, as_user, student_user, course):
    as_user(student_user)
    r = client.post("/api/v1/admin/bundles", json={
        "name": "One", "slug": "one", "bundle_price": 100.0,
        "course_ids": [course.id]})
    assert r.status_code == 422


def test_admin_crud_and_sales_count(client, db, as_user, student_user, course):
    from tests.test_bundle_fulfillment import _second_course
    c2 = _second_course(db, title="Course C")
    as_user(student_user)
    r = client.post("/api/v1/admin/bundles", json={
        "name": "Two", "slug": "two", "bundle_price": 700.0,
        "course_ids": [course.id, c2.id]})
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    db.add(Order(user_id=student_user.id, order_key="RZP_S1",
                 order_status=OrderStatus.COMPLETED, total_amount=700,
                 bundle_id=bid))
    db.commit()
    r = client.get("/api/v1/admin/bundles")
    row = next(b for b in r.json() if b["id"] == bid)
    assert row["sales_count"] == 1
    r = client.patch(f"/api/v1/admin/bundles/{bid}", json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False


def test_admin_create_caps_at_20_courses(client, db, as_user, student_user):
    from tests.test_bundle_fulfillment import _second_course
    courses = [_second_course(db, title=f"Course {i}") for i in range(21)]
    as_user(student_user)
    r = client.post("/api/v1/admin/bundles", json={
        "name": "TooBig", "slug": "too-big", "bundle_price": 100.0,
        "course_ids": [c.id for c in courses]})
    assert r.status_code == 422


def test_admin_create_dedupes_course_ids(client, db, as_user, student_user, course):
    from tests.test_bundle_fulfillment import _second_course
    c2 = _second_course(db, title="Course D")
    as_user(student_user)
    r = client.post("/api/v1/admin/bundles", json={
        "name": "Dupe", "slug": "dupe", "bundle_price": 100.0,
        "course_ids": [course.id, c2.id, course.id]})
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    rows = db.query(BundleCourse).filter(BundleCourse.bundle_id == bid).all()
    assert len(rows) == 2
    assert {row.course_id for row in rows} == {course.id, c2.id}


def test_admin_create_rejects_nonexistent_course_id(client, db, as_user, student_user, course):
    as_user(student_user)
    r = client.post("/api/v1/admin/bundles", json={
        "name": "Bad", "slug": "bad", "bundle_price": 100.0,
        "course_ids": [course.id, 999999]})
    assert r.status_code == 400
    assert "999999" in r.text


def test_admin_update_dedupes_and_validates_course_ids(client, db, as_user, student_user, course):
    from tests.test_bundle_fulfillment import _second_course
    c2 = _second_course(db, title="Course E")
    as_user(student_user)
    r = client.post("/api/v1/admin/bundles", json={
        "name": "Upd", "slug": "upd", "bundle_price": 100.0,
        "course_ids": [course.id, c2.id]})
    bid = r.json()["id"]

    r = client.patch(f"/api/v1/admin/bundles/{bid}", json={
        "course_ids": [c2.id, c2.id, course.id]})
    assert r.status_code == 200, r.text
    rows = db.query(BundleCourse).filter(BundleCourse.bundle_id == bid).all()
    assert len(rows) == 2

    r = client.patch(f"/api/v1/admin/bundles/{bid}", json={
        "course_ids": [course.id, 424242]})
    assert r.status_code == 400


# ---------- Cohort seat_price admin passthrough ----------
# cohorts.router is mounted at /api/v1/cohorts and the update handler's own
# route is /admin/cohorts/{id}, so the full path nests both segments.

def _cohort(db, student_user, **kw):
    c = Cohort(spoc_user_id=student_user.id, name=kw.get("name", "Cohort A"))
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_cohort_update_sets_seat_price(client, db, as_user, student_user):
    cohort = _cohort(db, student_user)
    as_user(student_user)
    r = client.put(f"/api/v1/cohorts/admin/cohorts/{cohort.id}",
                    json={"seat_price": 1499.0})
    assert r.status_code == 200, r.text
    assert r.json()["seat_price"] == 1499.0
    db.refresh(cohort)
    assert float(cohort.seat_price) == 1499.0


def test_cohort_update_clears_seat_price_with_null(client, db, as_user, student_user):
    cohort = _cohort(db, student_user)
    cohort.seat_price = 999.0
    db.commit()
    as_user(student_user)
    r = client.put(f"/api/v1/cohorts/admin/cohorts/{cohort.id}",
                    json={"seat_price": None})
    assert r.status_code == 200, r.text
    assert r.json()["seat_price"] is None
    db.refresh(cohort)
    assert cohort.seat_price is None


def test_cohort_update_rejects_non_positive_seat_price(client, db, as_user, student_user):
    cohort = _cohort(db, student_user)
    as_user(student_user)
    r = client.put(f"/api/v1/cohorts/admin/cohorts/{cohort.id}",
                    json={"seat_price": 0})
    assert r.status_code == 422
    r = client.put(f"/api/v1/cohorts/admin/cohorts/{cohort.id}",
                    json={"seat_price": -5})
    assert r.status_code == 422
