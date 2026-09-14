from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.core.config import get_settings
from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatPool, InvoiceStatus,
)
from app.models.enrollment import Enrollment
from app.models.payment import Order, Payment
from app.services.fulfillment_service import grant_purchased_course
from app.services.invoice_service import (
    allocate_invoice_number, compute_gst, issue_invoice, settle_invoice,
)
from tests.test_invoice_models import _company


def _invoice(db, co, course=None, qty=5, unit=200.0):
    inv = CompanyInvoice(company_id=co.id, subtotal=qty * unit, total=qty * unit)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(
        invoice_id=inv.id, description="Seats",
        course_id=course.id if course else None,
        quantity=qty, unit_price=unit, line_total=qty * unit))
    db.commit()
    db.refresh(inv)
    return inv


def test_gst_matrix(db, student_user, monkeypatch):
    co = _company(db, student_user)
    s = get_settings()
    # unregistered seller
    monkeypatch.setattr(s, "SELLER_GSTIN", "", raising=False)
    cgst, sgst, igst, note = compute_gst(1000.0, co, s)
    assert (cgst, sgst, igst) == (Decimal("0.00"),) * 3 or (float(cgst), float(sgst), float(igst)) == (0, 0, 0)
    assert "unregistered" in note.lower()
    # same state
    monkeypatch.setattr(s, "SELLER_GSTIN", "33AAAAA0000A1Z5", raising=False)
    monkeypatch.setattr(s, "SELLER_STATE_CODE", "33", raising=False)
    co.state_code = "33"
    cgst, sgst, igst, note = compute_gst(1000.0, co, s)
    assert float(cgst) == 90.0 and float(sgst) == 90.0 and float(igst) == 0
    # inter-state
    co.state_code = "29"
    cgst, sgst, igst, note = compute_gst(1000.0, co, s)
    assert float(igst) == 180.0 and float(cgst) == 0


def test_gst_split_rounds_to_exact_total_no_paise_drift(db, student_user, monkeypatch):
    """Regression: cgst+sgst must equal the correctly-rounded 18% exactly —
    independently rounding each half can overcount by 0.01 when the exact
    half ends in a 5 at the third decimal (e.g. subtotal 14998.50)."""
    co = _company(db, student_user)
    s = get_settings()
    monkeypatch.setattr(s, "SELLER_GSTIN", "33AAAAA0000A1Z5", raising=False)
    monkeypatch.setattr(s, "SELLER_STATE_CODE", "33", raising=False)

    subtotal = 14998.50
    expected_tax = Decimal("14998.50") * Decimal("18") / Decimal("100")
    expected_tax = expected_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    co.state_code = "33"  # same-state
    cgst, sgst, igst, _ = compute_gst(subtotal, co, s)
    assert cgst + sgst == expected_tax
    assert igst == Decimal("0.00")

    co.state_code = "29"  # inter-state
    cgst2, sgst2, igst2, _ = compute_gst(subtotal, co, s)
    assert igst2 == expected_tax
    assert cgst2 == Decimal("0.00") and sgst2 == Decimal("0.00")

    # Same-state total must agree with inter-state total for the same subtotal.
    assert cgst + sgst == igst2


def test_gst_split_whole_rupee_still_splits_evenly(db, student_user, monkeypatch):
    co = _company(db, student_user)
    s = get_settings()
    monkeypatch.setattr(s, "SELLER_GSTIN", "33AAAAA0000A1Z5", raising=False)
    monkeypatch.setattr(s, "SELLER_STATE_CODE", "33", raising=False)
    co.state_code = "33"
    cgst, sgst, igst, _ = compute_gst(1000.0, co, s)
    assert cgst == Decimal("90.00") and sgst == Decimal("90.00") and igst == Decimal("0.00")


def test_numbering_sequence_and_fy(db):
    n1 = allocate_invoice_number(db, datetime(2026, 9, 1, tzinfo=timezone.utc))
    n2 = allocate_invoice_number(db, datetime(2026, 9, 2, tzinfo=timezone.utc))
    n3 = allocate_invoice_number(db, datetime(2027, 4, 1, tzinfo=timezone.utc))
    assert n1 == "INV-2627-0001" and n2 == "INV-2627-0002"
    assert n3 == "INV-2728-0001"


def test_issue_then_settle_creates_pools_and_money(db, student_user, course):
    co = _company(db, student_user)
    inv = _invoice(db, co, course=course)
    issue_invoice(db, inv, pdf_renderer=lambda i: "invoices/test.pdf")
    db.commit()
    assert inv.status == InvoiceStatus.ISSUED and inv.invoice_number
    assert settle_invoice(db, inv, via="bank_transfer", reference="NEFT-1") is True
    db.commit()
    assert inv.status == InvoiceStatus.PAID
    pool = db.query(CompanySeatPool).one()
    assert pool.course_id == course.id and pool.total_seats == 5
    assert db.query(Order).count() == 1 and db.query(Payment).count() == 1
    # idempotent: already PAID
    assert settle_invoice(db, inv, via="bank_transfer", reference="NEFT-1") is False
    assert db.query(Order).count() == 1


def test_settle_replay_by_gateway_id_noop(db, student_user, course):
    co = _company(db, student_user)
    inv = _invoice(db, co, course=course)
    issue_invoice(db, inv, pdf_renderer=lambda i: "x.pdf")
    db.commit()
    assert settle_invoice(db, inv, via="razorpay", reference="pay_I1",
                          gateway_payment_id="pay_I1") is True
    db.commit()
    inv.status = InvoiceStatus.ISSUED  # simulate replayed webhook racing state
    db.commit()
    assert settle_invoice(db, inv, via="razorpay", reference="pay_I1",
                          gateway_payment_id="pay_I1") is False


def test_grant_purchased_course_rescues(db, student_user, course, order_row):
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="suspended",
                      enrollment_source="membership"))
    db.commit()
    assert grant_purchased_course(db, user_id=student_user.id,
                                  course_id=course.id,
                                  order_id=order_row.id, source="company") is True
    db.commit()
    row = db.query(Enrollment).one()
    assert row.enrollment_status == "enrolled"
    assert row.enrollment_source == "membership"  # source preserved
    assert row.order_id == order_row.id
