"""Anon-only SWR cache headers on public catalog endpoints (Task 1)."""


def _assert_public(r, s_maxage):
    cc = r.headers.get("cache-control", "")
    assert f"s-maxage={s_maxage}" in cc and "stale-while-revalidate=600" in cc
    assert "public" in cc
    assert r.headers.get("vary", "").lower() == "authorization"


def test_bundles_list_cache_headers_anon(client):
    r = client.get("/api/v1/bundles")
    assert r.status_code == 200
    _assert_public(r, 300)


def test_bundle_detail_cache_headers_anon(client, db, course):
    from app.models.bundle import Bundle, BundleCourse
    b = Bundle(name="C", slug="cache-pack", bundle_price=9.0)
    db.add(b)
    db.flush()
    db.add(BundleCourse(bundle_id=b.id, course_id=course.id))
    db.commit()
    r = client.get("/api/v1/bundles/cache-pack")
    assert r.status_code == 200
    _assert_public(r, 60)


def test_membership_plans_cache_headers_anon(client):
    r = client.get("/api/v1/memberships/plans")
    assert r.status_code == 200
    _assert_public(r, 300)


def test_courses_listing_cache_headers_anon(client):
    # NOTE: app.main sets redirect_slashes=False, and the listing handler is
    # registered at "/" under the /api/v1/courses prefix, so only the
    # trailing-slash form resolves (the bare path 405s) — pre-existing
    # routing behavior, unrelated to this task's changes.
    r = client.get("/api/v1/courses/")
    assert r.status_code == 200
    _assert_public(r, 60)


def test_authed_request_gets_private_no_store(client, db, course):
    r = client.get("/api/v1/bundles", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "no-store" in cc and "private" in cc
    assert "s-maxage" not in cc


def test_unwired_endpoint_has_no_public_cache(client):
    r = client.get("/api/v1/memberships/plans")
    assert "s-maxage" in r.headers.get("cache-control", "")  # sanity wired
    r2 = client.get("/health")
    assert "s-maxage" not in r2.headers.get("cache-control", "")
