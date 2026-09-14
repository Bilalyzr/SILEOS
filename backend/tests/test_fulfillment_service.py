from app.services.fulfillment_service import fulfill_course_purchase
from app.models.payment import Order, Payment
from app.models.enrollment import Enrollment


def _fulfill(db, user, course, pay_id="pay_A1", **kw):
    return fulfill_course_purchase(
        db, user=user, course=course,
        razorpay_order_id="order_A1", razorpay_payment_id=pay_id,
        paid_amount=500.0, base_price=500.0, **kw,
    )


def test_creates_order_payment_enrollment(db, student_user, course):
    res = _fulfill(db, student_user, course)
    db.commit()
    assert res.created_order and res.is_new_enrollment
    assert db.query(Order).count() == 1
    assert db.query(Payment).filter_by(gateway_payment_id="pay_A1").count() == 1
    assert db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id
    ).count() == 1


def test_replay_same_payment_id_is_noop(db, student_user, course):
    _fulfill(db, student_user, course)
    db.commit()
    res2 = _fulfill(db, student_user, course)
    db.commit()
    assert not res2.created_order
    assert db.query(Order).count() == 1
    assert db.query(Payment).count() == 1
    assert db.query(Enrollment).count() == 1


def test_coupon_discount_recorded_on_order(db, student_user, course):
    res = fulfill_course_purchase(
        db, user=student_user, course=course,
        razorpay_order_id="order_C1", razorpay_payment_id="pay_C1",
        paid_amount=400.0, base_price=500.0, coupon_discount=100.0,
    )
    db.commit()
    row = db.query(Order).get(res.order_id)
    assert float(row.total_amount) == 400.0
    assert float(row.discount_amount) == 100.0
    assert float(row.subtotal_amount) == 500.0


def test_duplicate_gateway_payment_id_rejected_by_db(db, student_user, course):
    """C3: the partial unique index is what makes a true concurrent race
    resolve to one winner instead of double-booking the buyer."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    _fulfill(db, student_user, course, pay_id="pay_UNIQ")
    db.commit()
    # Second Payment row with the SAME non-empty gateway payment id.
    db.add(Payment(
        order_id=db.query(Order).first().id,
        user_id=student_user.id,
        payment_method="razorpay",
        gateway_payment_id="pay_UNIQ",
        amount=500.0,
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_blank_gateway_payment_ids_are_not_unique_constrained(db, student_user, course):
    """Partial index: legacy rows default to "" and must still insert freely."""
    _fulfill(db, student_user, course, pay_id="pay_BASE")
    db.commit()
    order_id = db.query(Order).first().id
    for _ in range(2):
        db.add(Payment(
            order_id=order_id, user_id=student_user.id,
            payment_method="legacy", gateway_payment_id="", amount=1.0,
        ))
    db.commit()
    assert db.query(Payment).filter_by(gateway_payment_id="").count() == 2
