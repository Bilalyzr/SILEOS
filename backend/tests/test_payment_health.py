from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderStatus, Payment, PaymentStatus
from app.models.webhook_event import WebhookEvent, WebhookEventStatus


def _seed(db, student_user, course):
    db.add(WebhookEvent(event_id="evt_bad1", event_type="payment.captured",
                        payload={}, signature_valid=True,
                        status=WebhookEventStatus.FAILED, attempts=5,
                        last_error="boom"))
    db.add(WebhookEvent(event_id="evt_skip1", event_type="subscription.charged",
                        payload={}, signature_valid=True,
                        status=WebhookEventStatus.SKIPPED))
    order = Order(user_id=student_user.id, order_key="RZP_TEST1",
                  order_status=OrderStatus.COMPLETED, total_amount=500)
    db.add(order)
    db.flush()
    db.add(Payment(user_id=student_user.id, order_id=order.id,
                   payment_method="razorpay", gateway_payment_id="pay_refunded",
                   amount=500, payment_status=PaymentStatus.REFUNDED))
    db.add(Enrollment(user_id=student_user.id, course_id=course.id,
                      enrollment_status="enrolled", order_id=order.id))
    db.commit()


def test_payment_health_reports_pipeline_state(client, db, as_user, student_user, course):
    _seed(db, student_user, course)
    as_user(student_user)  # require_admin overridden by fixture
    r = client.get("/api/v1/admin/payment-health")
    assert r.status_code == 200
    data = r.json()
    assert data["failed_events"]["count"] == 1
    assert data["failed_events"]["items"][0]["event_id"] == "evt_bad1"
    assert data["skipped_events"]["count"] == 1
    assert data["refunded_with_active_enrollment"]["count"] == 1
    assert data["refunded_with_active_enrollment"]["items"][0]["gateway_payment_id"] == "pay_refunded"


def test_payment_health_surfaces_failed_refunds_and_drops_revoked(client, db, as_user, student_user,
                                                                  course, monkeypatch):
    """Task 3: the ops queue distinguishes a refund that needs retrying
    (refunds.failed) from an external refund that needs a human access
    decision (refunded_with_active_enrollment)."""
    from tests.test_refunds import _paid_order, _fake_gateway, FakeGateway, REASON
    from app.services import refund_service
    from app.services.refund_service import RefundError, refund_order
    monkeypatch.setattr(refund_service, "_gateway_refund", _fake_gateway)

    # a failed refund attempt -> shows up under refunds.failed
    FakeGateway.reset(fail=True)
    o1, p1 = _paid_order(db, student_user, [course], pay_id="pay_H_FAIL")
    try:
        refund_order(db, o1.id, reason=REASON, actor_id=1)
    except RefundError:
        pass
    # a successful admin refund -> enrollment cancelled, so NOT "refunded with active enrollment"
    FakeGateway.reset(fail=False)
    o2, p2 = _paid_order(db, student_user, [course], pay_id="pay_H_OK")
    refund_order(db, o2.id, reason=REASON, actor_id=1)

    as_user(student_user)
    data = client.get("/api/v1/admin/payment-health").json()
    assert data["refunds"]["failed"]["count"] == 1
    item = data["refunds"]["failed"]["items"][0]
    assert item["order_id"] == o1.id and item["gateway_payment_id"] == "pay_H_FAIL"
    assert "insufficient balance" in item["error"]
    assert all(i["gateway_payment_id"] != "pay_H_OK"
               for i in data["refunded_with_active_enrollment"]["items"])
