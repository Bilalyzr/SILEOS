"""
B3 — the SPOC blog page's Export button called GET /export-import/export/
blogs (spoc/blog.tsx:70), which doesn't exist (real admin path is
GET /admin/export/blogs, admin-only) — visible error toast on click.

Fix: a new SPOC-scoped section 'spoc_blogs' on the existing
GET /spoc/export/{section} route (export_import.py:2548), scoped
identically to GET /blog/spoc/my-posts (the SPOC's own authored posts
only) so one SPOC can never export another's drafts.
"""
import pytest

from app.models.blog import BlogPost


@pytest.fixture()
def as_spoc_user(client, as_user):
    """Like `as_user`, but also overrides AuthService.require_spoc — its
    Depends() is resolved against the unbound staticmethod descriptor at
    class-definition time, so the plain as_user override does not
    propagate to it (same caveat documented in test_company_billing_api.py)."""
    from app.services.auth_service import AuthService
    from app.main import app

    def _impl(user_obj):
        as_user(user_obj)
        app.dependency_overrides[AuthService.require_spoc] = lambda: user_obj
        return user_obj

    yield _impl
    app.dependency_overrides.pop(AuthService.require_spoc, None)


def test_spoc_export_blogs_returns_only_own_posts(client, db, make_user, as_spoc_user):
    spoc = make_user(role="spoc")
    other_spoc = make_user(role="spoc")
    as_spoc_user(spoc)

    db.add(BlogPost(author_id=spoc.id, title="Mine", slug="mine", content="x", status="PUBLISHED"))
    db.add(BlogPost(author_id=other_spoc.id, title="Not mine", slug="not-mine", content="x", status="PUBLISHED"))
    db.commit()

    # format=pdf: the test venv doesn't have pandas installed (excel export
    # requires it), but reportlab (pdf export) is available — this still
    # exercises the same scoping/serialization code as the excel path.
    resp = client.get("/api/v1/spoc/export/spoc_blogs", params={"format": "pdf"})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/pdf")
    assert len(resp.content) > 0


def test_get_role_section_query_scopes_spoc_blogs_to_author(db, make_user):
    """Direct unit check of the scoping query (PDF bytes aren't easily
    asserted on) — confirms 'spoc_blogs' only returns the calling SPOC's
    own posts, never another SPOC's."""
    from app.routers.export_import import get_role_section_query

    spoc = make_user(role="spoc")
    other_spoc = make_user(role="spoc")

    mine = BlogPost(author_id=spoc.id, title="Mine", slug="mine-2", content="x", status="PUBLISHED")
    db.add(mine)
    db.add(BlogPost(author_id=other_spoc.id, title="Not mine", slug="not-mine-2", content="x", status="PUBLISHED"))
    db.commit()

    results = get_role_section_query(db, "spoc_blogs", spoc)
    assert [r.id for r in results] == [mine.id]


def test_spoc_export_blogs_no_trailing_slash_declared(client, db, make_user, as_spoc_user):
    spoc = make_user(role="spoc")
    as_spoc_user(spoc)

    ok = client.get("/api/v1/spoc/export/spoc_blogs", params={"format": "pdf"})
    assert ok.status_code == 200

    trailing = client.get(
        "/api/v1/spoc/export/spoc_blogs/", params={"format": "pdf"}, follow_redirects=False
    )
    assert trailing.status_code == 404


def test_spoc_export_blogs_requires_spoc_role(client, db, make_user, auth_headers):
    make_user(role="student", email="student2@example.com")
    headers = auth_headers("student2@example.com")

    resp = client.get("/api/v1/spoc/export/spoc_blogs", headers=headers)
    assert resp.status_code == 403
