from datetime import datetime, timedelta, timezone

from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.reconciliation import retry_failed_events, reconcile_gateway_orders


def _failed_event(db, user, course, event_id="evt_f1", attempts=1, minutes_ago=60):
    ev = WebhookEvent(
        event_id=event_id,
        event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": f"pay_{event_id}", "order_id": "order_f", "amount": 50000,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(user.id)},
        }}}},
        signature_valid=True,
        status=WebhookEventStatus.FAILED,
        attempts=attempts,
        last_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    db.add(ev)
    db.commit()
    return ev


def test_retry_reprocesses_eligible_failed_event(db, student_user, course):
    _failed_event(db, student_user, course)
    n = retry_failed_events(db)
    assert n == 1
    ev = db.query(WebhookEvent).filter_by(event_id="evt_f1").one()
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Enrollment).count() == 1


def test_retry_respects_backoff_and_max_attempts(db, student_user, course):
    _failed_event(db, student_user, course, event_id="evt_young", attempts=3, minutes_ago=1)
    _failed_event(db, student_user, course, event_id="evt_dead", attempts=5, minutes_ago=999)
    assert retry_failed_events(db) == 0
    assert db.query(Enrollment).count() == 0


def test_forged_event_never_swept(db, student_user, course):
    db.add(WebhookEvent(
        event_id="evt_forged", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_forged", "order_id": "order_x", "amount": 50000, "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id)}}}}},
        signature_valid=False, status=WebhookEventStatus.FAILED,
        attempts=1, last_attempt_at=datetime.now(timezone.utc)-timedelta(minutes=600)))
    db.commit()
    assert retry_failed_events(db) == 0
    assert db.query(Enrollment).count() == 0


class FakeRzpClient:
    """Mimics razorpay.Client surface used by the sweeper."""
    def __init__(self, orders, payments_by_order):
        self._orders = orders
        self._pbo = payments_by_order
        self.order = self

    def all(self, opts):
        return {"items": self._orders}

    def payments(self, order_id):
        return {"items": self._pbo.get(order_id, [])}


def test_gateway_diff_fulfills_orphan(db, student_user, course):
    client = FakeRzpClient(
        orders=[{"id": "order_G1", "status": "paid", "amount": 50000,
                 "notes": {"course_id": str(course.id), "user_id": str(student_user.id)}}],
        payments_by_order={"order_G1": [
            {"id": "pay_G1", "status": "captured", "amount": 50000, "currency": "INR"},
        ]},
    )
    n = reconcile_gateway_orders(db, client)
    assert n == 1
    assert db.query(Payment).filter_by(gateway_payment_id="pay_G1").count() == 1
    assert db.query(Enrollment).count() == 1
    # Second run: nothing to do.
    assert reconcile_gateway_orders(db, client) == 0


def test_gateway_diff_alerts_on_garbage_notes(db, monkeypatch):
    sent = []
    from app.services import reconciliation as rec
    monkeypatch.setattr(
        rec.EmailService, "send_payment_alert",
        staticmethod(lambda subject, body: sent.append(subject) or True),
    )
    client = FakeRzpClient(
        orders=[{"id": "order_BAD", "status": "paid", "amount": 50000, "notes": {}}],
        payments_by_order={"order_BAD": [
            {"id": "pay_BAD", "status": "captured", "amount": 50000, "currency": "INR"},
        ]},
    )
    assert reconcile_gateway_orders(db, client) == 0
    assert len(sent) == 1


def test_exhausted_retries_alerts_exactly_once(db, monkeypatch, student_user, course):
    """I4: an event that burns its last attempt must page ops — once. The
    next sweep excludes attempts >= MAX_ATTEMPTS, so it cannot re-alert."""
    from app.services import reconciliation as rec
    from app.services import webhook_processor as wp

    # rec.EmailService and wp.EmailService are the SAME class object, so patch
    # it once and separate the two alert sites by subject.
    sent = []
    monkeypatch.setattr(
        rec.EmailService, "send_payment_alert",
        staticmethod(lambda subject, body: sent.append(subject) or True),
    )

    def _boom(*a, **kw):
        raise RuntimeError("gateway down")

    monkeypatch.setattr(wp, "fulfill_course_purchase", _boom)

    # attempts=4 → this sweep takes it to 5 == MAX_ATTEMPTS.
    _failed_event(db, student_user, course, event_id="evt_last", attempts=4, minutes_ago=99999)
    assert retry_failed_events(db) == 1
    ev = db.query(WebhookEvent).filter_by(event_id="evt_last").one()
    assert ev.status == WebhookEventStatus.FAILED
    assert ev.attempts == 5
    exhausted = [s for s in sent if "exhausted retries" in s]
    assert len(exhausted) == 1
    assert "evt_last" in exhausted[0]

    # Second sweep: the row is now excluded, so no duplicate page.
    assert retry_failed_events(db) == 0
    assert len([s for s in sent if "exhausted retries" in s]) == 1
