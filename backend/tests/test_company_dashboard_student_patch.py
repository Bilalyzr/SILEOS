"""
C-H1 + C-H2 — PATCH /companies/me/students/{user_id}.

C-H1: the notes branch was a literal `pass` — company "Save notes" was a
no-op (silent data loss). C-H2: the schema advertised an `internship_status`
field the handler never read — company could not close/complete a student's
internship engagement.

Fix: persist notes onto InternshipVoucher.company_notes; validate and
persist internship_status onto InternshipVoucher.engagement_status
(distinct from the sensitive `status` redemption-tracking column, which
this endpoint never touches), rejecting unknown values with 422.
"""
import pytest

from app.models.company import Company
from app.models.cohort import Cohort
from app.models.internship import Internship, InternshipVoucher


@pytest.fixture()
def as_company_user(client, as_user):
    """Like `as_user`, but also overrides
    `AuthService.require_company_or_manager` (its Depends() is resolved
    against the unbound staticmethod descriptor at class-definition time,
    so the plain `as_user` override does not propagate to it)."""
    from app.services.auth_service import AuthService
    from app.main import app

    def _impl(user_obj):
        as_user(user_obj)
        app.dependency_overrides[AuthService.require_company_or_manager] = lambda: user_obj
        return user_obj

    yield _impl
    app.dependency_overrides.pop(AuthService.require_company_or_manager, None)


def _company(db, owner, name="Acme", slug="acme"):
    c = Company(owner_user_id=owner.id, name=name, slug=slug,
                contact_email=owner.user_email, is_approved=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _internship_voucher(db, company, buyer, spoc):
    cohort = Cohort(spoc_user_id=spoc.id, name="Cohort A", slug="cohort-a")
    db.add(cohort)
    db.flush()

    internship = Internship(
        title="Backend Internship", slug="backend-internship",
        price=999, is_published=True,
        spoc_user_id=spoc.id, cohort_id=cohort.id,
    )
    db.add(internship)
    db.flush()

    voucher = InternshipVoucher(
        code="VCH-TEST-1", internship_id=internship.id,
        buyer_user_id=buyer.id, amount_paid=999,
        status="redeemed", hired_by_company_id=company.id,
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return voucher


def test_save_notes_persists(client, db, make_user, as_company_user):
    owner = make_user(role="company")
    spoc = make_user(role="admin")
    student = make_user(role="student")
    company = _company(db, owner)
    voucher = _internship_voucher(db, company, student, spoc)
    as_company_user(owner)

    resp = client.patch(
        f"/api/v1/companies/me/students/{student.id}",
        json={"notes": "Strong performer, promote to lead."},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["notes"] == "Strong performer, promote to lead."

    db.refresh(voucher)
    assert voucher.company_notes == "Strong performer, promote to lead."

    # Round-trip via GET too
    resp2 = client.get(f"/api/v1/companies/me/students/{student.id}")
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["notes"] == "Strong performer, promote to lead."


def test_internship_status_transition_persists(client, db, make_user, as_company_user):
    owner = make_user(role="company")
    spoc = make_user(role="admin")
    student = make_user(role="student")
    company = _company(db, owner)
    voucher = _internship_voucher(db, company, student, spoc)
    as_company_user(owner)

    resp = client.patch(
        f"/api/v1/companies/me/students/{student.id}",
        json={"internship_status": "completed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["internship_status"] == "completed"

    db.refresh(voucher)
    assert voucher.engagement_status == "completed"
    # The sensitive redemption-tracking column must never be touched by
    # this endpoint.
    assert voucher.status == "redeemed"


def test_invalid_internship_status_rejected(client, db, make_user, as_company_user):
    owner = make_user(role="company")
    spoc = make_user(role="admin")
    student = make_user(role="student")
    company = _company(db, owner)
    voucher = _internship_voucher(db, company, student, spoc)
    as_company_user(owner)

    resp = client.patch(
        f"/api/v1/companies/me/students/{student.id}",
        json={"internship_status": "banana"},
    )
    assert resp.status_code == 422, resp.text

    db.refresh(voucher)
    assert voucher.engagement_status == "active"
