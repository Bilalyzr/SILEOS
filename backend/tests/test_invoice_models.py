import pytest
from sqlalchemy.exc import IntegrityError

from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatAssignment,
    CompanySeatPool, InvoiceCounter, InvoiceStatus,
)


def _company(db, owner):
    from app.models.company import Company
    c = Company(owner_user_id=owner.id, name="Acme", slug="acme",
                contact_email="a@acme.test", is_approved=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_invoice_roundtrip_defaults(db, student_user):
    co = _company(db, student_user)
    inv = CompanyInvoice(company_id=co.id, subtotal=1000, total=1000)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(invoice_id=inv.id, description="Seats",
                              quantity=10, unit_price=100, line_total=1000))
    db.commit()
    db.refresh(inv)
    assert inv.status == InvoiceStatus.DRAFT
    assert inv.invoice_number is None
    assert co.gstin == "" and co.state_code == ""


def test_assignment_unique_per_pool(db, student_user):
    co = _company(db, student_user)
    inv = CompanyInvoice(company_id=co.id, subtotal=0, total=0)
    db.add(inv)
    db.flush()
    pool = CompanySeatPool(company_id=co.id, invoice_id=inv.id,
                           course_id=None, bundle_id=None, total_seats=5)
    db.add(pool)
    db.flush()
    db.add(CompanySeatAssignment(pool_id=pool.id, user_id=student_user.id,
                                 assigned_by=student_user.id))
    db.commit()
    db.add(CompanySeatAssignment(pool_id=pool.id, user_id=student_user.id,
                                 assigned_by=student_user.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_counter_and_settings(db):
    db.add(InvoiceCounter(fiscal_year="2627", last_number=0))
    db.commit()
    from app.core.config import get_settings
    s = get_settings()
    assert s.GST_RATE_PERCENT == 18.0
    assert s.SELLER_GSTIN == ""
