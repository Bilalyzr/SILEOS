"""
Tests for the bundle checkout branch and cohort seat pricing in
create-order / verify (app.routers.payments).
"""
import hashlib
import hmac

from app.models.bundle import Bundle, BundleCourse
from app.models.cohort import Cohort, ReferralCode
from app.models.enrollment import Enrollment


def _bundle(db, course_ids, price=799.0, active=True):
    b = Bundle(name="Pack", slug=f"pack-{price}", bundle_price=price,
               is_active=active)
    db.add(b)
    db.flush()
    for cid in course_ids:
        db.add(BundleCourse(bundle_id=b.id, course_id=cid))
    db.commit()
    db.refresh(b)
    return b


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


def test_create_order_rejects_both_ids(client, as_user, student_user):
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order",
                    json={"course_id": 1, "bundle_id": 1})
    assert r.status_code == 422
    r = client.post("/api/v1/payments/create-order", json={})
    assert r.status_code == 422


def test_bundle_order_uses_server_price_and_snapshot(client, db, as_user,
                                                     student_user, course,
                                                     monkeypatch):
    _patch_gateway(monkeypatch)
    b = _bundle(db, [course.id])
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"bundle_id": b.id})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == 79900
    notes = FakeOrders.last_payload["notes"]
    assert notes["bundle_id"] == str(b.id)
    assert notes["bundle_course_ids"] == str(course.id)


def test_bundle_coupon_rejected_and_inactive_rejected(client, db, as_user,
                                                      student_user, course,
                                                      monkeypatch):
    _patch_gateway(monkeypatch)
    b = _bundle(db, [course.id])
    inactive = _bundle(db, [course.id], price=1.0, active=False)
    as_user(student_user)
    assert client.post("/api/v1/payments/create-order",
                       json={"bundle_id": b.id, "coupon_code": "X"}).status_code == 400
    assert client.post("/api/v1/payments/create-order",
                       json={"bundle_id": inactive.id}).status_code == 404


def test_seat_price_overrides_course_price(client, db, as_user, student_user,
                                           course, monkeypatch):
    _patch_gateway(monkeypatch)
    # The `course` fixture persists with post_status="draft" (SQLAlchemy
    # column default isn't applied at construction time), but create-order
    # requires a published course — set it explicitly for this test.
    course.post_status = "publish"
    db.commit()
    cohort = Cohort(name="Paid", spoc_user_id=student_user.id,
                    course_id=course.id, seat_price=250.0, is_active=True)
    db.add(cohort)
    db.flush()
    db.add(ReferralCode(cohort_id=cohort.id, code="SEAT250", max_uses=10))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order",
                    json={"course_id": course.id, "coupon_code": "SEAT250"})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == 25000  # seat price, not 50000


def test_verify_bundle_enrolls_all(client, db, as_user, student_user, course,
                                   monkeypatch):
    _patch_gateway(monkeypatch)
    b = _bundle(db, [course.id])
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"bundle_id": b.id})
    assert r.status_code == 200
    sig = hmac.new(b"secret", b"order_TEST1|pay_TEST1", hashlib.sha256).hexdigest()
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_TEST1",
        "razorpay_signature": sig, "bundle_id": b.id,
    })
    assert r.status_code == 200, r.text
    assert db.query(Enrollment).filter_by(user_id=student_user.id,
                                          course_id=course.id).count() == 1


def test_create_order_allowed_when_all_courses_suspended(client, db, as_user,
                                                         student_user, course,
                                                         monkeypatch):
    """C1 guard consistency: suspended rows are not "owned", so the user may
    still buy the bundle that would restore them."""
    _patch_gateway(monkeypatch)
    b = _bundle(db, [course.id], price=499.0)
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="suspended",
                      enrollment_source="membership"))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"bundle_id": b.id})
    assert r.status_code == 200, r.text


def test_verify_bundle_rejects_empty_course_snapshot(client, db, as_user,
                                                     student_user, course,
                                                     monkeypatch):
    """I1: an empty bundle_course_ids note must 400 BEFORE any write, so the
    webhook/sweeper are still armed to fulfil the capture."""
    from app.models.payment import Order, Payment

    _patch_gateway(monkeypatch)
    b = _bundle(db, [course.id], price=699.0)
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"bundle_id": b.id})
    assert r.status_code == 200
    FakeOrders.last_payload["notes"]["bundle_course_ids"] = ""

    sig = hmac.new(b"secret", b"order_TEST1|pay_EMPTY", hashlib.sha256).hexdigest()
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_EMPTY",
        "razorpay_signature": sig, "bundle_id": b.id,
    })
    assert r.status_code == 400, r.text
    assert "do not pay again" in r.json()["detail"]
    assert db.query(Order).count() == 0
    assert db.query(Payment).count() == 0
    assert db.query(Enrollment).count() == 0


def test_verify_bundle_rejects_malformed_course_snapshot(client, db, as_user,
                                                         student_user, course,
                                                         monkeypatch):
    """The unguarded int() parse used to 500 after the card was charged."""
    from app.models.payment import Order, Payment

    _patch_gateway(monkeypatch)
    b = _bundle(db, [course.id], price=899.0)
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"bundle_id": b.id})
    assert r.status_code == 200
    FakeOrders.last_payload["notes"]["bundle_course_ids"] = "12,abc"

    sig = hmac.new(b"secret", b"order_TEST1|pay_BAD", hashlib.sha256).hexdigest()
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_BAD",
        "razorpay_signature": sig, "bundle_id": b.id,
    })
    assert r.status_code == 400, r.text
    assert db.query(Order).count() == 0
    assert db.query(Payment).count() == 0
