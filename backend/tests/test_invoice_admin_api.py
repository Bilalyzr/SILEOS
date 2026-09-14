import os

from app.models.company_invoice import CompanyInvoice, InvoiceStatus
from tests.test_invoice_models import _company


def _create(client, co, course=None, qty=3, unit=500.0):
    item = {"description": "Course seats", "quantity": qty, "unit_price": unit}
    if course is not None:
        item["course_id"] = course.id
    return client.post("/api/v1/admin/company-invoices", json={
        "company_id": co.id, "items": [item]})


def test_draft_create_and_issue_flow(client, db, as_user, student_user, course):
    co = _company(db, student_user)
    as_user(student_user)
    r = _create(client, co, course=course)
    assert r.status_code == 200, r.text
    inv_id = r.json()["id"]
    assert r.json()["status"] == "draft"
    assert float(r.json()["items"][0]["line_total"]) == 1500.0
    r = client.post(f"/api/v1/admin/company-invoices/{inv_id}/issue")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "issued" and body["invoice_number"].startswith("INV-")
    # issued → PATCH forbidden
    assert client.patch(f"/api/v1/admin/company-invoices/{inv_id}",
                        json={"notes": "x"}).status_code == 409
    # pdf exists
    r = client.get(f"/api/v1/admin/company-invoices/{inv_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")


def test_item_validation(client, db, as_user, student_user, course):
    co = _company(db, student_user)
    as_user(student_user)
    r = client.post("/api/v1/admin/company-invoices", json={
        "company_id": co.id,
        "items": [{"description": "bad", "course_id": course.id,
                   "bundle_id": 1, "quantity": 1, "unit_price": 10}]})
    assert r.status_code == 422
    r = client.post("/api/v1/admin/company-invoices", json={
        "company_id": co.id, "items": []})
    assert r.status_code == 422


def test_mark_paid_creates_pool(client, db, as_user, student_user, course):
    from app.models.company_invoice import CompanySeatPool
    co = _company(db, student_user)
    as_user(student_user)
    inv_id = _create(client, co, course=course).json()["id"]
    client.post(f"/api/v1/admin/company-invoices/{inv_id}/issue")
    r = client.post(f"/api/v1/admin/company-invoices/{inv_id}/mark-paid",
                    json={"reference": "NEFT-77"})
    assert r.status_code == 200, r.text
    assert db.query(CompanySeatPool).filter_by(invoice_id=inv_id).one().total_seats == 3
    # double mark-paid → 409
    assert client.post(f"/api/v1/admin/company-invoices/{inv_id}/mark-paid",
                       json={"reference": "NEFT-77"}).status_code == 409


def test_cancel_only_issued_unpaid(client, db, as_user, student_user, course):
    co = _company(db, student_user)
    as_user(student_user)
    inv_id = _create(client, co, course=course).json()["id"]
    assert client.post(f"/api/v1/admin/company-invoices/{inv_id}/cancel").status_code == 409  # draft
    client.post(f"/api/v1/admin/company-invoices/{inv_id}/issue")
    assert client.post(f"/api/v1/admin/company-invoices/{inv_id}/cancel").status_code == 200


def test_issue_survives_unescaped_markup_in_billing_fields(client, db, as_user, student_user, course):
    """Regression: a stray '<' in company billing_address or invoice notes
    must not make reportlab's Paragraph parser raise and 400 /issue —
    invoice_pdf.py must escape all free text before building Paragraph
    markup."""
    co = _company(db, student_user)
    co.billing_address = "123 Main St <Suite 4B"
    co.state_code = "29"  # buyer state code is printed in the buyer block
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/admin/company-invoices", json={
        "company_id": co.id,
        "notes": "5 < 10",
        "items": [{"description": "Course seats", "course_id": course.id,
                   "quantity": 3, "unit_price": 500.0}]})
    assert r.status_code == 200, r.text
    inv_id = r.json()["id"]
    r = client.post(f"/api/v1/admin/company-invoices/{inv_id}/issue")
    assert r.status_code == 200, r.text
    r = client.get(f"/api/v1/admin/company-invoices/{inv_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")


def test_pdf_rerendered_when_file_missing_from_disk(client, db, as_user,
                                                     student_user, course):
    """Invoice PDFs live on a bind-mounted directory; if the mount is missing
    or the volume was recreated the row still points at a vanished file. Both
    PDF endpoints must re-render an ISSUED/PAID invoice from its snapshot
    rather than 404-ing a legal document forever."""
    co = _company(db, student_user)
    as_user(student_user)
    inv_id = _create(client, co, course=course).json()["id"]
    assert client.post(
        f"/api/v1/admin/company-invoices/{inv_id}/issue").status_code == 200

    inv = db.query(CompanyInvoice).filter_by(id=inv_id).one()
    path = inv.pdf_path
    assert path and os.path.isfile(path)
    os.remove(path)
    assert not os.path.isfile(path)

    r = client.get(f"/api/v1/admin/company-invoices/{inv_id}/pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    db.expire_all()
    inv = db.query(CompanyInvoice).filter_by(id=inv_id).one()
    assert inv.pdf_path and os.path.isfile(inv.pdf_path)


def test_pdf_not_rerendered_for_cancelled_invoice(client, db, as_user,
                                                   student_user, course):
    """A cancelled invoice must never have a fresh tax document minted for
    it — a missing file stays a 404."""
    co = _company(db, student_user)
    as_user(student_user)
    inv_id = _create(client, co, course=course).json()["id"]
    client.post(f"/api/v1/admin/company-invoices/{inv_id}/issue")
    assert client.post(
        f"/api/v1/admin/company-invoices/{inv_id}/cancel").status_code == 200

    inv = db.query(CompanyInvoice).filter_by(id=inv_id).one()
    assert inv.status == InvoiceStatus.CANCELLED
    os.remove(inv.pdf_path)

    assert client.get(
        f"/api/v1/admin/company-invoices/{inv_id}/pdf").status_code == 404
