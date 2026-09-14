"""
B7 — POST /companies/admin/bulk-invite used to commit once per row, so a
batch reported as "errors: n" left every successful row already written
(partial-write on failure). Fix: validate every row first, write nothing
until the whole batch validates, then one commit for all rows. Any
invalid row rejects the WHOLE batch with 400 and zero writes.
"""
from app.models.company import Company
from app.models.user import User


def test_bulk_invite_all_valid_rows_creates_all_companies(client, db, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)

    entries = [
        {"name": "Acme Corp", "email": "acme@example.com"},
        {"name": "Beta LLC", "email": "beta@example.com"},
        {"name": "Gamma Inc", "email": "gamma@example.com"},
    ]
    resp = client.post(
        "/api/v1/companies/admin/bulk-invite",
        json={"entries": entries, "send_setup_email": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["invited"] == 3
    assert body["errors"] == 0

    companies = db.query(Company).all()
    assert len(companies) == 3
    emails = {c.contact_email for c in companies}
    assert emails == {"acme@example.com", "beta@example.com", "gamma@example.com"}


def test_bulk_invite_one_bad_row_writes_zero_rows(client, db, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)

    entries = [
        {"name": "Acme Corp", "email": "acme@example.com"},
        {"name": "Bad Row", "email": "not-an-email"},
        {"name": "Gamma Inc", "email": "gamma@example.com"},
    ]
    resp = client.post(
        "/api/v1/companies/admin/bulk-invite",
        json={"entries": entries, "send_setup_email": False},
    )
    assert resp.status_code == 400, resp.text

    # No partial writes — not even the valid rows were created.
    assert db.query(Company).count() == 0
    assert db.query(User).filter(User.user_email.in_(
        ["acme@example.com", "gamma@example.com"]
    )).count() == 0

    detail = resp.json()["detail"]
    assert detail["failed"] == 1
    failing_emails = {r["email"] for r in detail["results"] if r["status"] == "error"}
    assert "not-an-email" in failing_emails


def test_bulk_invite_duplicate_email_within_batch_rejects_whole_batch(client, db, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)

    entries = [
        {"name": "Acme Corp", "email": "dupe@example.com"},
        {"name": "Acme Corp Two", "email": "dupe@example.com"},
    ]
    resp = client.post(
        "/api/v1/companies/admin/bulk-invite",
        json={"entries": entries, "send_setup_email": False},
    )
    assert resp.status_code == 400, resp.text
    assert db.query(Company).count() == 0


def test_bulk_invite_existing_user_email_rejects_whole_batch(client, db, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)
    make_user(email="existing@example.com")

    entries = [
        {"name": "Acme Corp", "email": "new@example.com"},
        {"name": "Existing Co", "email": "existing@example.com"},
    ]
    resp = client.post(
        "/api/v1/companies/admin/bulk-invite",
        json={"entries": entries, "send_setup_email": False},
    )
    assert resp.status_code == 400, resp.text
    assert db.query(Company).count() == 0
    assert db.query(User).filter(User.user_email == "new@example.com").count() == 0
