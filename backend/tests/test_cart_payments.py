"""Paid multi-course cart checkout and its three convergence paths."""

import hashlib
import hmac

from app.models.course import Course
from app.models.coupon import Coupon
from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderItem, Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.reconciliation import reconcile_gateway_orders
from app.services.webhook_processor import process_webhook_event


class FakeGateway:
    last_payload = None

    class order:
        @staticmethod
        def create(payload):
            FakeGateway.last_payload = payload
            return {
                "id": "order_CART1",
                "amount": payload["amount"],
                "currency": payload["currency"],
            }

        @staticmethod
        def fetch(order_id):
            payload = FakeGateway.last_payload
            return {
                "id": order_id,
                "amount": payload["amount"],
                "amount_paid": payload["amount"],
                "currency": payload["currency"],
                "notes": payload["notes"],
            }


def _patch_gateway(monkeypatch):
    import app.routers.payments as payments

    FakeGateway.last_payload = None
    monkeypatch.setattr(payments, "_razorpay_client", lambda: FakeGateway)
    monkeypatch.setattr(payments, "_razorpay_creds", lambda: ("rzp_key", "secret"))


def _published_pair(db, course):
    course.post_status = "publish"
    course.course_price = 500
    second = Course(
        post_author=course.post_author,
        post_title="Second Course",
        post_status="publish",
        course_price_type="paid",
        course_price=300,
        course_type="meiporul",
    )
    db.add(second)
    db.commit()
    return course, second


def _signature(payment_id="pay_CART1"):
    return hmac.new(
        b"secret", f"order_CART1|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()


def test_cart_target_contract_rejects_ambiguous_and_duplicate_sets(
    client, as_user, student_user
):
    as_user(student_user)
    assert client.post(
        "/api/v1/payments/create-order",
        json={"course_id": 1, "course_ids": [2]},
    ).status_code == 422
    assert client.post(
        "/api/v1/payments/create-order", json={"course_ids": [1, 1]}
    ).status_code == 422
    assert client.post(
        "/api/v1/payments/create-order", json={"course_ids": list(range(1, 12))}
    ).status_code == 422


def test_paid_cart_create_verify_and_replay_are_idempotent(
    client, db, as_user, student_user, course, monkeypatch
):
    _patch_gateway(monkeypatch)
    first, second = _published_pair(db, course)
    as_user(student_user)

    created = client.post(
        "/api/v1/payments/create-order",
        json={"course_ids": [second.id, first.id]},
    )
    assert created.status_code == 200, created.text
    assert created.json()["amount"] == 80000
    notes = FakeGateway.last_payload["notes"]
    assert notes["checkout_type"] == "cart"
    assert notes["cart_lines"] == f"{first.id}:50000,{second.id}:30000"

    body = {
        "razorpay_order_id": "order_CART1",
        "razorpay_payment_id": "pay_CART1",
        "razorpay_signature": _signature(),
        "course_ids": [second.id, first.id],
    }
    assert client.post("/api/v1/payments/verify", json=body).status_code == 200
    assert client.post("/api/v1/payments/verify", json=body).status_code == 200

    db.expire_all()
    assert db.query(Order).count() == 1
    assert db.query(Payment).count() == 1
    assert db.query(OrderItem).count() == 2
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 2
    order = db.query(Order).one()
    assert float(order.subtotal_amount) == 800
    assert float(order.total_amount) == 800
    assert order.payment_method == "razorpay_cart"
    assert round(sum(float(item.total) for item in order.order_items), 2) == 800


def test_cart_verify_requires_the_exact_course_set(
    client, db, as_user, student_user, course, monkeypatch
):
    _patch_gateway(monkeypatch)
    first, second = _published_pair(db, course)
    as_user(student_user)
    assert client.post(
        "/api/v1/payments/create-order", json={"course_ids": [first.id, second.id]}
    ).status_code == 200

    response = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_CART1",
        "razorpay_payment_id": "pay_CART1",
        "razorpay_signature": _signature(),
        "course_ids": [first.id],
    })
    assert response.status_code == 400
    assert db.query(Payment).count() == 0
    assert db.query(Enrollment).count() == 0


def test_paid_cart_still_fulfills_if_coupon_is_deleted_after_capture(
    client, db, as_user, student_user, course, monkeypatch
):
    _patch_gateway(monkeypatch)
    first, second = _published_pair(db, course)
    coupon = Coupon(
        code="CART100",
        description="Cart discount",
        discount_type="fixed",
        discount_value=100,
        applicability="all_courses",
        usage_count=0,
        per_user_limit=1,
        is_active=True,
        created_by=course.post_author,
    )
    db.add(coupon)
    db.commit()
    as_user(student_user)
    created = client.post(
        "/api/v1/payments/create-order",
        json={"course_ids": [first.id, second.id], "coupon_code": "CART100"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["amount"] == 70000

    db.delete(coupon)
    db.commit()
    import app.routers.payments as payments

    alerts = []
    monkeypatch.setattr(
        payments.EmailService,
        "send_payment_alert",
        lambda subject, body: alerts.append((subject, body)) or True,
    )
    response = client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": "order_CART1",
            "razorpay_payment_id": "pay_CARTCOUPONGONE",
            "razorpay_signature": _signature("pay_CARTCOUPONGONE"),
            "course_ids": [first.id, second.id],
        },
    )
    assert response.status_code == 200, response.text
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 2
    assert alerts and alerts[0][0] == "cart coupon changed after capture"


def test_cart_webhook_and_reconciliation_converge(
    db, student_user, course
):
    first, second = _published_pair(db, course)
    notes = {
        "checkout_type": "cart",
        "user_id": str(student_user.id),
        "cart_lines": f"{first.id}:50000,{second.id}:30000",
        "cart_subtotal_paise": "80000",
        "cart_discount_paise": "0",
        "cart_total_paise": "80000",
    }
    event = WebhookEvent(
        event_id="evt_cart_1",
        event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_CART_WEBHOOK",
            "order_id": "order_CART_WEBHOOK",
            "amount": 80000,
            "currency": "INR",
            "notes": notes,
        }}}},
        signature_valid=True,
    )
    db.add(event)
    db.commit()
    process_webhook_event(db, event)
    assert event.status == WebhookEventStatus.PROCESSED
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 2

    # The sweeper sees the same capture as already fulfilled and no-ops.
    class Gateway:
        order = None

        def __init__(self):
            self.order = self

        def all(self, options):
            return {"items": [{
                "id": "order_CART_WEBHOOK", "status": "paid",
                "amount": 80000, "notes": notes,
            }]}

        def payments(self, order_id):
            return {"items": [{
                "id": "pay_CART_WEBHOOK", "status": "captured",
                "amount": 80000, "currency": "INR",
            }]}

    assert reconcile_gateway_orders(db, Gateway()) == 0
    assert db.query(Payment).count() == 1


def test_reconciliation_recovers_an_orphaned_cart(db, student_user, course):
    first, second = _published_pair(db, course)
    notes = {
        "checkout_type": "cart",
        "user_id": str(student_user.id),
        "cart_lines": f"{first.id}:50000,{second.id}:30000",
        "cart_subtotal_paise": "80000",
        "cart_discount_paise": "0",
        "cart_total_paise": "80000",
    }

    class Gateway:
        def __init__(self):
            self.order = self

        def all(self, options):
            return {"items": [{
                "id": "order_CART_SWEEP", "status": "paid",
                "amount": 80000, "notes": notes,
            }]}

        def payments(self, order_id):
            return {"items": [{
                "id": "pay_CART_SWEEP", "status": "captured",
                "amount": 80000, "currency": "INR",
            }]}

    assert reconcile_gateway_orders(db, Gateway()) == 1
    assert db.query(Payment).filter_by(gateway_payment_id="pay_CART_SWEEP").count() == 1
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 2
