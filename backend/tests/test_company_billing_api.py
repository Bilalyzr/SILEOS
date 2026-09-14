"""
Tests for the company-facing billing portal API (app/routers/company_billing.py),
mounted at /api/v1/companies/billing.

Cross-company isolation is the top concern: every endpoint must 404 (never
403-leak existence) on another company's resources.

NOTE: the shared `as_user` fixture (conftest.py) overrides
`AuthService.get_current_active_user` and `AuthService.require_admin` only.
`AuthService.require_company_or_manager` — which every endpoint in this
router depends on — has its own `Depends(get_current_active_user)`
resolved at class-definition time against the *unbound staticmethod
descriptor*, not the plain function `AuthService.get_current_active_user`
points to after class construction; the two are different objects, so
`as_user`'s override does not propagate to it. A local `as_company_user`
fixture below overrides `AuthService.require_company_or_manager` directly
(conftest.py is intentionally left untouched).
"""
import pytest

from app.models.bundle import Bundle, BundleCourse
from app.models.company import Company
from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatAssignment, CompanySeatPool,
    InvoiceStatus,
)
from app.models.enrollment import Enrollment
from app.models.user import User
from app.services.invoice_service import issue_invoice, settle_invoice


# ---------------- fixtures ----------------

@pytest.fixture()
def as_company_user(client, as_user):
    """Like `as_user`, but also overrides
    `AuthService.require_company_or_manager` — see module docstring."""
    from app.services.auth_service import AuthService
    from app.main import app

    def _impl(user_obj):
        as_user(user_obj)
        app.dependency_overrides[AuthService.require_company_or_manager] = lambda: user_obj
        return user_obj

    yield _impl
    app.dependency_overrides.pop(AuthService.require_company_or_manager, None)


# ---------------- helpers ----------------

def _company(db, owner, name="Acme", slug="acme"):
    c = Company(owner_user_id=owner.id, name=name, slug=slug,
                contact_email=owner.user_email, is_approved=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _bundle(db, course_ids, price=799.0, active=True, slug="pack"):
    b = Bundle(name="Pack", slug=slug, bundle_price=price, is_active=active)
    db.add(b)
    db.flush()
    for cid in course_ids:
        db.add(BundleCourse(bundle_id=b.id, course_id=cid))
    db.commit()
    db.refresh(b)
    return b


def _paid_settled_invoice(db, co, course=None, bundle=None, qty=5, unit=200.0):
    """A PAID invoice with one line item, settled via bank_transfer, whose
    seat pool carries an order_id (per settle_invoice)."""
    inv = CompanyInvoice(company_id=co.id, subtotal=qty * unit, total=qty * unit)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(
        invoice_id=inv.id, description="Seats",
        course_id=course.id if course else None,
        bundle_id=bundle.id if bundle else None,
        quantity=qty, unit_price=unit, line_total=qty * unit))
    db.commit()
    db.refresh(inv)
    issue_invoice(db, inv, pdf_renderer=lambda i: "invoices/test.pdf")
    db.commit()
    db.refresh(inv)
    ok = settle_invoice(db, inv, via="bank_transfer", reference="REF1")
    assert ok
    db.commit()
    db.refresh(inv)
    return inv


def _issued_invoice(db, co, course=None, qty=5, unit=200.0):
    inv = CompanyInvoice(company_id=co.id, subtotal=qty * unit, total=qty * unit)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(
        invoice_id=inv.id, description="Seats",
        course_id=course.id if course else None,
        quantity=qty, unit_price=unit, line_total=qty * unit))
    db.commit()
    db.refresh(inv)
    issue_invoice(db, inv, pdf_renderer=lambda i: "invoices/test.pdf")
    db.commit()
    db.refresh(inv)
    return inv


def _draft_invoice(db, co, qty=2, unit=100.0):
    inv = CompanyInvoice(company_id=co.id, subtotal=qty * unit, total=qty * unit)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(invoice_id=inv.id, description="Seats",
                              quantity=qty, unit_price=unit, line_total=qty * unit))
    db.commit()
    db.refresh(inv)
    return inv


class FakeOrders:
    last_payload = None
    class order:
        @staticmethod
        def create(payload):
            FakeOrders.last_payload = payload
            return {"id": "order_TEST1", "amount": payload["amount"],
                    "currency": "INR", "notes": payload["notes"]}
        @staticmethod
        def fetch(order_id):
            return {"id": order_id, "amount": FakeOrders.last_payload["amount"],
                    "amount_paid": FakeOrders.last_payload["amount"],
                    "currency": "INR", "notes": FakeOrders.last_payload["notes"]}


def _patch_gateway(monkeypatch):
    import app.routers.payments as pay
    monkeypatch.setattr(pay, "_razorpay_client", lambda: FakeOrders)
    monkeypatch.setattr(pay, "_razorpay_creds", lambda: ("rzp_key", "secret"))


# ---------------- profile ----------------

def test_profile_get_and_patch_roundtrip(client, db, as_company_user, student_user):
    co = _company(db, student_user)
    student_user.role = "company"
    db.commit()
    as_company_user(student_user)

    r = client.get("/api/v1/companies/billing/profile")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == co.name
    assert body["gstin"] == ""
    assert body["state_code"] == ""

    r = client.patch("/api/v1/companies/billing/profile", json={
        "gstin": "29ABCDE1234F1Z5",
        "legal_name": "Acme Pvt Ltd",
        "billing_address": "1 MG Road, Bangalore",
        "state_code": "29",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["gstin"] == "29ABCDE1234F1Z5"
    assert body["legal_name"] == "Acme Pvt Ltd"
    assert body["billing_address"] == "1 MG Road, Bangalore"
    assert body["state_code"] == "29"

    r = client.get("/api/v1/companies/billing/profile")
    assert r.json()["state_code"] == "29"


def test_profile_patch_bad_state_code_422(client, db, as_company_user, student_user):
    _company(db, student_user)
    student_user.role = "company"
    db.commit()
    as_company_user(student_user)

    r = client.patch("/api/v1/companies/billing/profile", json={"state_code": "ABC"})
    assert r.status_code == 422

    r = client.patch("/api/v1/companies/billing/profile", json={"state_code": "9"})
    assert r.status_code == 422

    # empty string is allowed
    r = client.patch("/api/v1/companies/billing/profile", json={"state_code": ""})
    assert r.status_code == 200


def test_profile_patch_rejects_oversized_fields(client, db, as_company_user, student_user):
    """Billing fields land on a rendered tax invoice and in VARCHAR columns —
    over-length input must 422 at the edge, not 500 at the DB."""
    _company(db, student_user)
    student_user.role = "company"
    db.commit()
    as_company_user(student_user)

    # gstin: column is String(20)
    assert client.patch("/api/v1/companies/billing/profile",
                        json={"gstin": "2" * 21}).status_code == 422
    assert client.patch("/api/v1/companies/billing/profile",
                        json={"gstin": "2" * 20}).status_code == 200
    # legal_name: column is String(255)
    assert client.patch("/api/v1/companies/billing/profile",
                        json={"legal_name": "L" * 256}).status_code == 422
    # billing_address: Text column, policy-capped at 2000
    assert client.patch("/api/v1/companies/billing/profile",
                        json={"billing_address": "A" * 2001}).status_code == 422
    assert client.patch("/api/v1/companies/billing/profile",
                        json={"billing_address": "A" * 2000}).status_code == 200


def test_profile_no_company_403(client, as_company_user, student_user):
    student_user.role = "company"
    as_company_user(student_user)
    r = client.get("/api/v1/companies/billing/profile")
    assert r.status_code == 403


# ---------------- invoices ----------------

def test_invoices_list_hides_drafts_and_other_companies(client, db, as_company_user, student_user, course):
    owner_a = student_user
    owner_a.role = "company"
    db.commit()
    co_a = _company(db, owner_a, name="Acme", slug="acme")

    owner_b = User(user_login="ownerb", user_pass="x", user_nicename="ownerb",
                   user_email="ownerb@example.com", display_name="ownerb", role="company")
    db.add(owner_b)
    db.commit()
    db.refresh(owner_b)
    co_b = _company(db, owner_b, name="Globex", slug="globex")

    inv_issued = _issued_invoice(db, co_a, course, qty=3, unit=100.0)
    inv_draft = _draft_invoice(db, co_a)
    inv_other = _issued_invoice(db, co_b, course, qty=1, unit=50.0)

    as_company_user(owner_a)
    r = client.get("/api/v1/companies/billing/invoices")
    assert r.status_code == 200, r.text
    ids = [i["id"] for i in r.json()]
    assert inv_issued.id in ids
    assert inv_draft.id not in ids
    assert inv_other.id not in ids


def test_invoice_pdf_404_for_other_company(client, db, as_company_user, student_user, course):
    owner_a = student_user
    owner_a.role = "company"
    db.commit()
    co_a = _company(db, owner_a, name="Acme", slug="acme")

    owner_b = User(user_login="ownerb2", user_pass="x", user_nicename="ownerb2",
                   user_email="ownerb2@example.com", display_name="ownerb2", role="company")
    db.add(owner_b)
    db.commit()
    db.refresh(owner_b)
    co_b = _company(db, owner_b, name="Globex", slug="globex2")
    inv_other = _issued_invoice(db, co_b, course, qty=1, unit=50.0)

    as_company_user(owner_a)
    r = client.get(f"/api/v1/companies/billing/invoices/{inv_other.id}/pdf")
    assert r.status_code == 404


def test_invoice_pdf_rerendered_when_file_missing(client, db, as_company_user,
                                                   student_user, course):
    """Company-side mirror of the admin re-render test: a PDF whose file has
    vanished (missing bind mount / recreated volume) is re-rendered from the
    invoice snapshot instead of 404-ing forever."""
    import os

    from app.services.invoice_pdf import render_invoice_pdf

    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)

    inv = CompanyInvoice(company_id=co.id, subtotal=300.0, total=300.0)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(invoice_id=inv.id, description="Seats",
                              course_id=course.id, quantity=3,
                              unit_price=100.0, line_total=300.0))
    db.commit()
    db.refresh(inv)
    issue_invoice(db, inv, pdf_renderer=lambda i: render_invoice_pdf(db, i))
    db.commit()
    db.refresh(inv)

    assert inv.pdf_path and os.path.isfile(inv.pdf_path)
    os.remove(inv.pdf_path)

    as_company_user(student_user)
    r = client.get(f"/api/v1/companies/billing/invoices/{inv.id}/pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    db.expire_all()
    assert os.path.isfile(db.query(CompanyInvoice).filter_by(id=inv.id).one().pdf_path)


def test_invoice_pay_returns_order_payload(client, db, as_company_user, student_user, course, monkeypatch):
    _patch_gateway(monkeypatch)
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=5, unit=200.0)  # total = 1000

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/invoices/{inv.id}/pay")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["amount"] == int(round(float(inv.total) * 100))
    assert body["order_id"] == "order_TEST1"


def test_invoice_pay_other_company_404(client, db, as_company_user, student_user, course, monkeypatch):
    _patch_gateway(monkeypatch)
    student_user.role = "company"
    db.commit()
    co_a = _company(db, student_user, name="Acme", slug="acme3")

    owner_b = User(user_login="ownerb3", user_pass="x", user_nicename="ownerb3",
                   user_email="ownerb3@example.com", display_name="ownerb3", role="company")
    db.add(owner_b)
    db.commit()
    db.refresh(owner_b)
    co_b = _company(db, owner_b, name="Globex", slug="globex3")
    inv_other = _issued_invoice(db, co_b, course, qty=1, unit=50.0)

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/invoices/{inv_other.id}/pay")
    assert r.status_code == 404


# ---------------- seat pools / assignment ----------------

def test_seat_pool_assign_happy_path(client, db, as_company_user, student_user, course):
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=3, unit=200.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()
    assert pool.order_id is not None
    assert pool.used_seats == 0

    recipient = User(user_login="recip1", user_pass="x", user_nicename="recip1",
                     user_email="Recipient1@Example.com", display_name="recip1")
    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": " recipient1@example.com "})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user_id"] == recipient.id

    db.expire_all()
    pool = db.query(CompanySeatPool).filter_by(id=pool.id).one()
    assert pool.used_seats == 1

    enr = db.query(Enrollment).filter_by(user_id=recipient.id, course_id=course.id).one()
    assert enr.enrollment_status == "enrolled"
    assert enr.enrollment_source == "company"
    assert enr.order_id == pool.order_id


def test_seat_pool_assign_duplicate_409(client, db, as_company_user, student_user, course):
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=3, unit=200.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()

    recipient = User(user_login="recip2", user_pass="x", user_nicename="recip2",
                     user_email="recipient2@example.com", display_name="recip2")
    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recipient2@example.com"})
    assert r.status_code == 201

    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recipient2@example.com"})
    assert r.status_code == 409


def test_seat_pool_assign_exhausted_409(client, db, as_company_user, student_user, course):
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=1, unit=200.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()
    assert pool.total_seats == 1

    recipient1 = User(user_login="recip3", user_pass="x", user_nicename="recip3",
                      user_email="recipient3@example.com", display_name="recip3")
    recipient2 = User(user_login="recip4", user_pass="x", user_nicename="recip4",
                      user_email="recipient4@example.com", display_name="recip4")
    db.add_all([recipient1, recipient2])
    db.commit()

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recipient3@example.com"})
    assert r.status_code == 201

    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recipient4@example.com"})
    assert r.status_code == 409
    assert "No seats left" in r.json()["detail"]


def test_seat_pool_assign_wildcard_email_404(client, db, as_company_user, student_user, course):
    """A LIKE-pattern email ("%@example.com") must never match an arbitrary
    account by wildcard — only an exact (case-insensitive) match is
    accepted. A real user at that domain exists, but assignment must 404
    and grant nothing."""
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=3, unit=200.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()

    real_user = User(user_login="realuser1", user_pass="x", user_nicename="realuser1",
                     user_email="realuser1@example.com", display_name="realuser1")
    db.add(real_user)
    db.commit()
    db.refresh(real_user)

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "%@example.com"})
    assert r.status_code == 404

    db.expire_all()
    pool = db.query(CompanySeatPool).filter_by(id=pool.id).one()
    assert pool.used_seats == 0
    assert db.query(CompanySeatAssignment).filter_by(pool_id=pool.id).count() == 0


def test_seat_pool_assign_atomic_rowcount_zero_when_prefilled(client, db, as_company_user,
                                                               student_user, course):
    """Directly exercises the rowcount-0 branch of the atomic conditional
    update (the real cross-request race isn't reproducible on a
    single-connection SQLite test session): pre-fill used_seats ==
    total_seats, then assignment must 409 without touching the pool or
    creating an assignment row."""
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=2, unit=200.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()
    pool.used_seats = pool.total_seats
    db.commit()

    recipient = User(user_login="recip_race", user_pass="x", user_nicename="recip_race",
                     user_email="recip_race@example.com", display_name="recip_race")
    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recip_race@example.com"})
    assert r.status_code == 409
    assert "No seats left" in r.json()["detail"]

    db.expire_all()
    pool = db.query(CompanySeatPool).filter_by(id=pool.id).one()
    assert pool.used_seats == pool.total_seats
    assert db.query(CompanySeatAssignment).filter_by(pool_id=pool.id).count() == 0


def test_seat_pool_assign_already_enrolled_course_409(client, db, as_company_user,
                                                       student_user, course):
    """Course-pool assignment for a user already enrolled in that course
    must 409 and consume no seat."""
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=3, unit=200.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()

    recipient = User(user_login="recip_already", user_pass="x", user_nicename="recip_already",
                     user_email="recip_already@example.com", display_name="recip_already")
    db.add(recipient)
    db.commit()
    db.refresh(recipient)
    db.add(Enrollment(course_id=course.id, user_id=recipient.id,
                      enrollment_status="enrolled", enrollment_source="free"))
    db.commit()

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recip_already@example.com"})
    assert r.status_code == 409
    assert "already has access" in r.json()["detail"]

    db.expire_all()
    pool = db.query(CompanySeatPool).filter_by(id=pool.id).one()
    assert pool.used_seats == 0
    assert db.query(CompanySeatAssignment).filter_by(pool_id=pool.id).count() == 0


def test_bundle_pool_assign_empty_course_list_409(client, db, as_company_user, student_user, course):
    """A bundle pool whose CURRENT published-paid course list resolves
    empty must 409 before consuming a seat — never burn a seat for
    nothing."""
    from app.models.course import Course

    instructor = db.query(User).filter_by(id=course.post_author).first()
    # Only a free course and an unpublished paid course in the bundle — the
    # published-paid filter resolves to an empty list.
    free_course = Course(post_author=instructor.id, post_title="Free",
                         course_price_type="free", course_price=0, post_status="publish")
    unpublished = Course(post_author=instructor.id, post_title="Unpublished",
                         course_price_type="paid", course_price=100.0, post_status="draft")
    db.add_all([free_course, unpublished])
    db.commit()
    db.refresh(free_course)
    db.refresh(unpublished)

    bundle = _bundle(db, [free_course.id, unpublished.id], price=300.0, slug="empty-bundle")

    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, bundle=bundle, qty=2, unit=300.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()

    recipient = User(user_login="recip_empty", user_pass="x", user_nicename="recip_empty",
                     user_email="recip_empty@example.com", display_name="recip_empty")
    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recip_empty@example.com"})
    assert r.status_code == 409
    assert "no available courses" in r.json()["detail"]

    db.expire_all()
    pool = db.query(CompanySeatPool).filter_by(id=pool.id).one()
    assert pool.used_seats == 0
    assert db.query(CompanySeatAssignment).filter_by(pool_id=pool.id).count() == 0


def test_bundle_pool_assign_partial_overlap_reports_granted_and_already(
        client, db, as_company_user, student_user, course):
    """When the recipient already owns some of the bundle's current
    published-paid courses, assignment still succeeds (normal case) and
    the response reports which courses were newly granted vs already
    held, and the seat is consumed exactly once."""
    from app.models.course import Course

    instructor = db.query(User).filter_by(id=course.post_author).first()
    other_course = Course(post_author=instructor.id, post_title="Other Paid Published",
                          course_price_type="paid", course_price=300.0, post_status="publish")
    db.add(other_course)
    db.commit()
    db.refresh(other_course)
    course.post_status = "publish"
    db.commit()

    bundle = _bundle(db, [course.id, other_course.id], price=500.0, slug="partial-bundle")

    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, bundle=bundle, qty=2, unit=500.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()

    recipient = User(user_login="recip_partial", user_pass="x", user_nicename="recip_partial",
                     user_email="recip_partial@example.com", display_name="recip_partial")
    db.add(recipient)
    db.commit()
    db.refresh(recipient)
    # Recipient already owns `course` from elsewhere (free-standing purchase).
    db.add(Enrollment(course_id=course.id, user_id=recipient.id,
                      enrollment_status="enrolled", enrollment_source="direct"))
    db.commit()

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recip_partial@example.com"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body["granted_course_ids"]) == {other_course.id}
    assert set(body["already_had_course_ids"]) == {course.id}

    db.expire_all()
    pool = db.query(CompanySeatPool).filter_by(id=pool.id).one()
    assert pool.used_seats == 1


def test_seat_pool_assign_unknown_email_404(client, db, as_company_user, student_user, course):
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=3, unit=200.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "nobody@example.com"})
    # NOTE: app.main's global @app.exception_handler(404) rewrites every 404
    # detail to "Endpoint not found" (see test_invoice_payments.py and other
    # existing tests, which likewise assert status only) — the specific
    # "No account with that email" detail is set by the router
    # (app/routers/company_billing.py::assign_seat) but is not
    # client-observable through that handler.
    assert r.status_code == 404


def test_seat_pool_other_company_404(client, db, as_company_user, student_user, course):
    student_user.role = "company"
    db.commit()
    co_a = _company(db, student_user, name="Acme", slug="acme4")

    owner_b = User(user_login="ownerb4", user_pass="x", user_nicename="ownerb4",
                   user_email="ownerb4@example.com", display_name="ownerb4", role="company")
    db.add(owner_b)
    db.commit()
    db.refresh(owner_b)
    co_b = _company(db, owner_b, name="Globex", slug="globex4")
    inv_b = _paid_settled_invoice(db, co_b, course=course, qty=3, unit=200.0)
    pool_b = db.query(CompanySeatPool).filter_by(invoice_id=inv_b.id).one()

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool_b.id}/assign",
                    json={"email": "recipient5@example.com"})
    assert r.status_code == 404

    r = client.get(f"/api/v1/companies/billing/seat-pools/{pool_b.id}/assignments")
    assert r.status_code == 404


def test_seat_pool_assignments_list(client, db, as_company_user, student_user, course):
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=3, unit=200.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()

    recipient = User(user_login="recip6", user_pass="x", user_nicename="recip6",
                     user_email="recipient6@example.com", display_name="recip6")
    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recipient6@example.com"})
    assert r.status_code == 201

    r = client.get(f"/api/v1/companies/billing/seat-pools/{pool.id}/assignments")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["user_id"] == recipient.id
    assert body[0]["email"] == "recipient6@example.com"


def test_seat_pool_list_shows_titles(client, db, as_company_user, student_user, course):
    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, course=course, qty=3, unit=200.0)

    as_company_user(student_user)
    r = client.get("/api/v1/companies/billing/seat-pools")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["course_id"] == course.id
    assert body[0]["course_title"] == course.post_title
    assert body[0]["total_seats"] == 3
    assert body[0]["used_seats"] == 0


# ---------------- bundle pool assignment ----------------

def test_bundle_pool_assign_grants_published_paid_courses(client, db, as_company_user, student_user, course):
    from app.models.course import Course

    instructor = db.query(User).filter_by(id=course.post_author).first()

    other_paid_published = Course(
        post_author=instructor.id, post_title="Other Paid Published",
        course_price_type="paid", course_price=300.0, post_status="publish",
    )
    unpublished_paid = Course(
        post_author=instructor.id, post_title="Unpublished Paid",
        course_price_type="paid", course_price=300.0, post_status="draft",
    )
    free_published = Course(
        post_author=instructor.id, post_title="Free Published",
        course_price_type="free", course_price=0, post_status="publish",
    )
    db.add_all([other_paid_published, unpublished_paid, free_published])
    db.commit()
    db.refresh(other_paid_published)
    db.refresh(unpublished_paid)
    db.refresh(free_published)

    course.post_status = "publish"
    db.commit()

    bundle = _bundle(db, [course.id, other_paid_published.id, unpublished_paid.id,
                          free_published.id], price=500.0, slug="bundle-assign")

    student_user.role = "company"
    db.commit()
    co = _company(db, student_user)
    inv = _paid_settled_invoice(db, co, bundle=bundle, qty=2, unit=500.0)
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()
    assert pool.bundle_id == bundle.id

    recipient = User(user_login="recip7", user_pass="x", user_nicename="recip7",
                     user_email="recipient7@example.com", display_name="recip7")
    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    as_company_user(student_user)
    r = client.post(f"/api/v1/companies/billing/seat-pools/{pool.id}/assign",
                    json={"email": "recipient7@example.com"})
    assert r.status_code == 201, r.text

    enrolled_course_ids = {
        e.course_id for e in db.query(Enrollment).filter_by(user_id=recipient.id).all()
    }
    assert enrolled_course_ids == {course.id, other_paid_published.id}
    for e in db.query(Enrollment).filter_by(user_id=recipient.id).all():
        assert e.enrollment_source == "company"
        assert e.order_id == pool.order_id
