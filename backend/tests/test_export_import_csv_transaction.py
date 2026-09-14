"""
B7 — POST /admin/import/{section} (CSV/Excel bulk import) used to commit
once per row, so a batch reporting errors still left every prior
successful row written (partial-write on failure). Fix: process the whole
file in one transaction — flush (not commit) each row, and only commit
once at the very end if every row succeeded; any failing row rejects the
WHOLE file with 400 (still HTTP 200 envelope, per the endpoint's existing
error-reporting contract — see error_count/errors) and nothing is written.

Uses the "blogs" CSV section rather than "companies": the companies
import branch hardcodes owner_user_id=1 for every new row (a pre-existing,
out-of-scope bug — collides on a UNIQUE constraint for any 2+ row batch
and would otherwise mask what these tests are checking).
"""
import io

from app.models.blog import BlogPost


def _csv_bytes(header: list, rows: list) -> bytes:
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(str(v) for v in row))
    return ("\n".join(lines) + "\n").encode("utf-8")


BLOG_HEADER = [
    "id", "title", "slug", "author_id", "author_email",
    "status", "category", "view_count", "published_at", "created_at",
]


def _blog_row(n: int, author_id: int) -> list:
    return [
        "", f"Post {n}", f"post-{n}", str(author_id), "author@example.com",
        "DRAFT", "General", "0", "", "",
    ]


def test_csv_import_all_valid_rows_writes_all(client, db, make_user, as_user):
    admin = make_user(role="admin")  # becomes users.id == 1 in a fresh test DB
    as_user(admin)

    csv_bytes = _csv_bytes(
        BLOG_HEADER,
        [_blog_row(1, admin.id), _blog_row(2, admin.id), _blog_row(3, admin.id)],
    )
    resp = client.post(
        "/api/v1/admin/import/blogs",
        files={"file": ("blogs.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success_count"] == 3
    assert body["error_count"] == 0

    assert db.query(BlogPost).count() == 3


def test_csv_import_one_bad_row_writes_zero_rows(client, db, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)

    # A row whose slug collides with an earlier row in the SAME file trips
    # BlogPost.slug's UNIQUE constraint on flush — a genuine DB-level
    # failure, not just a missing-column check. (SQLite's test engine
    # doesn't enforce FK constraints by default, so a bad foreign key
    # wouldn't actually fail here — UNIQUE is enforced regardless.)
    good1 = _blog_row(1, admin.id)
    dup_slug_row = _blog_row(1, admin.id)  # same n=1 -> same slug as good1

    csv_bytes = _csv_bytes(
        BLOG_HEADER,
        [good1, dup_slug_row, _blog_row(2, admin.id)],
    )

    resp = client.post(
        "/api/v1/admin/import/blogs",
        files={"file": ("blogs.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success_count"] == 0
    assert body["error_count"] >= 1

    # No partial writes — not even the valid rows were created.
    assert db.query(BlogPost).count() == 0


def test_csv_import_missing_required_column_rejects_whole_file(client, db, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)

    # Drop a required column ("author_id") from the header entirely.
    header = [c for c in BLOG_HEADER if c != "author_id"]
    full_row = _blog_row(1, admin.id)
    rows = [[v for c, v in zip(BLOG_HEADER, full_row) if c != "author_id"]]

    csv_bytes = _csv_bytes(header, rows)
    resp = client.post(
        "/api/v1/admin/import/blogs",
        files={"file": ("blogs.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success_count"] == 0
    assert body["error_count"] == 1
    assert "Missing columns" in body["errors"][0]["error"]

    assert db.query(BlogPost).count() == 0
