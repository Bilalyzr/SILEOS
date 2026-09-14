import hashlib
import hmac
import json

from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.models.payment import Order, Payment
from app.models.enrollment import Enrollment
from app.core.config import get_settings

SECRET = "whsec_test"


def _sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def _captured_event(user, course, event_id="evt_1", pay_id="pay_W1", amount_paise=50000):
    return {
        "entity": "event",
        "event": "payment.captured",
        "id": event_id,
        "payload": {"payment": {"entity": {
            "id": pay_id,
            "order_id": "order_W1",
            "amount": amount_paise,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(user.id)},
        }}},
    }


def _post(client, payload, event_id=None, sig=None):
    body = json.dumps(payload).encode()
    headers = {"X-Razorpay-Signature": sig if sig is not None else _sign(body)}
    if event_id:
        headers["X-Razorpay-Event-Id"] = event_id
    return client.post(
        "/api/v1/payments/webhook", content=body,
        headers={**headers, "Content-Type": "application/json"},
    )


def _set_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "RAZORPAY_WEBHOOK_SECRET", SECRET, raising=False)


def test_invalid_signature_stored_unprocessed_400(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    r = _post(client, _captured_event(student_user, course), event_id="evt_bad", sig="0" * 64)
    assert r.status_code == 400
    ev = db.query(WebhookEvent).filter_by(event_id="evt_bad").one()
    assert ev.signature_valid is False
    assert ev.status != WebhookEventStatus.PROCESSED
    assert db.query(Enrollment).count() == 0


def test_captured_event_enrolls_buyer(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    r = _post(client, _captured_event(student_user, course), event_id="evt_ok")
    assert r.status_code == 200
    ev = db.query(WebhookEvent).filter_by(event_id="evt_ok").one()
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Payment).filter_by(gateway_payment_id="pay_W1").count() == 1
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 1


def test_duplicate_delivery_is_noop(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    payload = _captured_event(student_user, course, event_id="evt_dup2")
    assert _post(client, payload, event_id="evt_dup2").status_code == 200
    assert _post(client, payload, event_id="evt_dup2").status_code == 200
    assert db.query(WebhookEvent).filter_by(event_id="evt_dup2").count() == 1
    assert db.query(Order).count() == 1
    assert db.query(Enrollment).count() == 1


def test_webhook_after_verify_is_noop(client, db, monkeypatch, student_user, course):
    """The /verify-vs-webhook race: whichever runs first wins, second no-ops.
    Simulates /verify having already fulfilled by calling the same service."""
    _set_secret(monkeypatch)
    from app.services.fulfillment_service import fulfill_course_purchase
    fulfill_course_purchase(
        db, user=student_user, course=course,
        razorpay_order_id="order_W1", razorpay_payment_id="pay_race",
        paid_amount=500.0, base_price=500.0,
    )
    db.commit()
    payload = _captured_event(student_user, course, event_id="evt_race", pay_id="pay_race")
    assert _post(client, payload, event_id="evt_race").status_code == 200
    ev = db.query(WebhookEvent).filter_by(event_id="evt_race").one()
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Order).count() == 1
    assert db.query(Payment).count() == 1
    assert db.query(Enrollment).count() == 1


def test_unknown_event_type_skipped(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    # order.paid is a real Razorpay event type with no handler in this pipeline
    # (subscription.* events are now handled — see test_subscription_webhooks.py).
    payload = {"entity": "event", "event": "order.paid", "id": "evt_sub", "payload": {}}
    assert _post(client, payload, event_id="evt_sub").status_code == 200
    ev = db.query(WebhookEvent).filter_by(event_id="evt_sub").one()
    assert ev.status == WebhookEventStatus.SKIPPED


def test_refund_marks_payment_refunded_keeps_enrollment(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    _post(client, _captured_event(student_user, course, event_id="evt_c", pay_id="pay_R1"), event_id="evt_c")
    refund = {
        "entity": "event", "event": "refund.processed", "id": "evt_r",
        "payload": {"refund": {"entity": {"id": "rfnd_1", "payment_id": "pay_R1"}}},
    }
    assert _post(client, refund, event_id="evt_r").status_code == 200
    from app.models.payment import PaymentStatus
    p = db.query(Payment).filter_by(gateway_payment_id="pay_R1").one()
    assert p.payment_status == PaymentStatus.REFUNDED
    assert db.query(Enrollment).count() == 1  # NOT revoked


def test_generic_failure_records_attempt_bookkeeping(client, db, monkeypatch, student_user, course):
    """C1: db.rollback() in the generic except handler discards the in-memory
    attempts/last_attempt_at bump. If they aren't re-applied the sweeper's
    backoff/max-attempts guard never engages and retries are unbounded."""
    from app.services import webhook_processor as wp

    def _boom(*a, **kw):
        raise RuntimeError("fulfillment exploded")

    monkeypatch.setattr(wp, "fulfill_course_purchase", _boom)
    _set_secret(monkeypatch)

    r = _post(client, _captured_event(student_user, course, event_id="evt_boom",
                                      pay_id="pay_boom"), event_id="evt_boom")
    assert r.status_code == 200
    db.expire_all()
    ev = db.query(WebhookEvent).filter_by(event_id="evt_boom").one()
    assert ev.status == WebhookEventStatus.FAILED
    assert ev.attempts == 1
    assert ev.last_attempt_at is not None
    assert db.query(Enrollment).count() == 0


def test_forged_first_delivery_does_not_poison_event_id(client, db, monkeypatch, student_user, course):
    """I1: a forged delivery landing first must not permanently occupy the
    event_id — the genuine delivery of the same event still gets processed."""
    _set_secret(monkeypatch)
    payload = _captured_event(student_user, course, event_id="evt_poison", pay_id="pay_poison")

    assert _post(client, payload, event_id="evt_poison", sig="0" * 64).status_code == 400
    db.expire_all()
    ev = db.query(WebhookEvent).filter_by(event_id="evt_poison").one()
    assert ev.signature_valid is False
    assert ev.status != WebhookEventStatus.PROCESSED

    # Same event id, this time correctly signed.
    assert _post(client, payload, event_id="evt_poison").status_code == 200
    db.expire_all()
    ev = db.query(WebhookEvent).filter_by(event_id="evt_poison").one()
    assert ev.signature_valid is True
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(WebhookEvent).filter_by(event_id="evt_poison").count() == 1
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 1


def test_second_forged_delivery_still_acked_unprocessed(client, db, monkeypatch, student_user, course):
    """I1 must not let an invalid signature overwrite a stored row."""
    _set_secret(monkeypatch)
    payload = _captured_event(student_user, course, event_id="evt_twice_bad", pay_id="pay_tb")
    assert _post(client, payload, event_id="evt_twice_bad", sig="0" * 64).status_code == 400
    assert _post(client, payload, event_id="evt_twice_bad", sig="1" * 64).status_code == 200
    db.expire_all()
    ev = db.query(WebhookEvent).filter_by(event_id="evt_twice_bad").one()
    assert ev.signature_valid is False
    assert ev.status != WebhookEventStatus.PROCESSED
    assert db.query(Enrollment).count() == 0


def test_empty_entity_notes_fall_back_to_gateway_order(client, db, monkeypatch, student_user, course):
    """I2: payment-entity notes can be empty while the ORDER carries them."""
    from app.services import webhook_processor as wp

    class _FakeOrderApi:
        def __init__(self, notes):
            self._notes = notes
            self.fetched = []

        def fetch(self, order_id):
            self.fetched.append(order_id)
            return {"id": order_id, "notes": self._notes}

    class _FakeClient:
        def __init__(self, notes):
            self.order = _FakeOrderApi(notes)

    fake = _FakeClient({"course_id": str(course.id), "user_id": str(student_user.id)})
    monkeypatch.setattr(wp, "_gateway_client", lambda: fake)
    _set_secret(monkeypatch)

    payload = _captured_event(student_user, course, event_id="evt_notes", pay_id="pay_notes")
    payload["payload"]["payment"]["entity"]["notes"] = {}

    assert _post(client, payload, event_id="evt_notes").status_code == 200
    db.expire_all()
    ev = db.query(WebhookEvent).filter_by(event_id="evt_notes").one()
    assert ev.status == WebhookEventStatus.PROCESSED
    assert fake.order.fetched == ["order_W1"]
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 1


def test_gateway_fallback_unavailable_stays_unrecoverable(client, db, monkeypatch, student_user, course):
    """I2: no client / still-unusable notes → UnrecoverableEvent as before."""
    from app.services import webhook_processor as wp
    monkeypatch.setattr(wp, "_gateway_client", lambda: None)
    monkeypatch.setattr(
        wp.EmailService, "send_payment_alert",
        staticmethod(lambda subject, body: True),
    )
    _set_secret(monkeypatch)

    payload = _captured_event(student_user, course, event_id="evt_nonotes", pay_id="pay_nonotes")
    payload["payload"]["payment"]["entity"]["notes"] = {}

    assert _post(client, payload, event_id="evt_nonotes").status_code == 200
    db.expire_all()
    ev = db.query(WebhookEvent).filter_by(event_id="evt_nonotes").one()
    assert ev.status == WebhookEventStatus.FAILED
    assert ev.attempts == 5  # unrecoverable: retries exhausted immediately
    assert ev.last_attempt_at is not None
    assert db.query(Enrollment).count() == 0
