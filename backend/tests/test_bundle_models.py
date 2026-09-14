import pytest
from sqlalchemy.exc import IntegrityError

from app.models.bundle import Bundle, BundleCourse
from app.models.cohort import Cohort
from app.models.payment import Order, OrderStatus


def test_bundle_roundtrip(db, course):
    b = Bundle(name="Starter Pack", slug="starter-pack", bundle_price=799.0)
    db.add(b)
    db.flush()
    db.add(BundleCourse(bundle_id=b.id, course_id=course.id))
    db.commit()
    db.refresh(b)
    assert b.is_active is True
    assert db.query(BundleCourse).filter_by(bundle_id=b.id).count() == 1


def test_bundle_slug_unique(db):
    db.add(Bundle(name="A", slug="dup", bundle_price=1.0))
    db.commit()
    db.add(Bundle(name="B", slug="dup", bundle_price=2.0))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_order_bundle_id_and_cohort_seat_price(db, student_user):
    b = Bundle(name="P", slug="p", bundle_price=5.0)
    db.add(b)
    db.flush()
    o = Order(user_id=student_user.id, order_key="RZP_B1",
              order_status=OrderStatus.COMPLETED, total_amount=5, bundle_id=b.id)
    db.add(o)
    c = Cohort(name="C1", spoc_user_id=student_user.id, seat_price=250.0)
    db.add(c)
    db.commit()
    assert db.query(Order).filter(Order.bundle_id == b.id).count() == 1
    db.refresh(c)
    assert float(c.seat_price) == 250.0
