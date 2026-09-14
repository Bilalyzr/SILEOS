"""
M-4 — frontend calls GET /admin/blogs/categories (api/blog.ts:80) with no
backend route; the category filter dropdown on the admin blogs page
silently fails. Adds an admin-guarded route returning every distinct,
non-empty category actually present on BlogPost rows (category is a
free-text String column, not an FK to a separate catalog table).
"""
from app.models.blog import BlogPost


def _blog(db, author_id, n, category):
    b = BlogPost(
        author_id=author_id, title=f"Post {n}", slug=f"post-{n}",
        content="content", category=category,
    )
    db.add(b)
    return b


def test_blog_categories_returns_distinct_non_empty_categories(client, db, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)

    _blog(db, admin.id, 1, "Tech")
    _blog(db, admin.id, 2, "Tech")
    _blog(db, admin.id, 3, "Design")
    _blog(db, admin.id, 4, None)
    _blog(db, admin.id, 5, "")
    db.commit()

    resp = client.get("/api/v1/admin/blogs/categories")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert sorted(body) == ["Design", "Tech"]


def test_blog_categories_no_trailing_slash_declared(client, db, make_user, as_user):
    """Route must be declared WITHOUT a trailing slash (redirect_slashes=False
    app-wide) — hitting it with an appended slash must not silently redirect
    or succeed via FastAPI's default trailing-slash handling."""
    admin = make_user(role="admin")
    as_user(admin)

    ok = client.get("/api/v1/admin/blogs/categories")
    assert ok.status_code == 200

    trailing = client.get("/api/v1/admin/blogs/categories/", follow_redirects=False)
    assert trailing.status_code == 404


def test_blog_categories_requires_admin(client, db, make_user, auth_headers):
    """`as_user` overrides AuthService.require_admin unconditionally (see
    test_company_billing_api.py's module docstring for the same caveat),
    so a real login is used here to exercise the actual role check."""
    make_user(role="student", email="student1@example.com")

    headers = auth_headers("student1@example.com")
    resp = client.get("/api/v1/admin/blogs/categories", headers=headers)
    assert resp.status_code == 403
