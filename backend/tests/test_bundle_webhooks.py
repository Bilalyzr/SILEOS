from app.models.bundle import Bundle, BundleCourse
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.webhook_processor import process_webhook_event
from app.services.reconciliation import reconcile_gateway_orders


def _bundle(db, course_ids):
    b = Bundle(name="WPack", slug="wpack", bundle_price=799.0)
    db.add(b)
    db.flush()
    for cid in course_ids:
        db.add(BundleCourse(bundle_id=b.id, course_id=cid))
    db.commit()
    return b


def _captured(db, user, b, course_ids, pay_id="pay_WB1", event_id="evt_wb1"):
    ev = WebhookEvent(
        event_id=event_id, event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": pay_id, "order_id": "order_WB1", "amount": 79900,
            "currency": "INR",
            "notes": {"bundle_id": str(b.id), "user_id": str(user.id),
                      "bundle_course_ids": ",".join(map(str, course_ids))},
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()
    return ev


def test_webhook_fulfills_bundle(db, student_user, course):
    b = _bundle(db, [course.id])
    ev = _captured(db, student_user, b, [course.id])
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Payment).filter_by(gateway_payment_id="pay_WB1").count() == 1
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 1


def test_webhook_bundle_duplicate_noop(db, student_user, course):
    b = _bundle(db, [course.id])
    process_webhook_event(db, _captured(db, student_user, b, [course.id],
                                        event_id="evt_a"))
    process_webhook_event(db, _captured(db, student_user, b, [course.id],
                                        event_id="evt_b"))
    assert db.query(Payment).count() == 1
    assert db.query(Enrollment).count() == 1


def test_webhook_bundle_bad_user_unrecoverable(db, course):
    b = _bundle(db, [course.id])
    ev = WebhookEvent(
        event_id="evt_bad", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_BAD", "amount": 79900, "currency": "INR",
            "notes": {"bundle_id": str(b.id), "user_id": "999999",
                      "bundle_course_ids": str(course.id)},
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.FAILED
    assert ev.attempts == 5


class FakeRzpClient:
    def __init__(self, orders, payments_by_order):
        self._orders = orders
        self._pbo = payments_by_order
        self.order = self
    def all(self, opts):
        return {"items": self._orders}
    def payments(self, order_id):
        return {"items": self._pbo.get(order_id, [])}


def test_sweeper_fulfills_orphan_bundle(db, student_user, course):
    b = _bundle(db, [course.id])
    client = FakeRzpClient(
        orders=[{"id": "order_GB1", "status": "paid", "amount": 79900,
                 "notes": {"bundle_id": str(b.id),
                           "user_id": str(student_user.id),
                           "bundle_course_ids": str(course.id)}}],
        payments_by_order={"order_GB1": [
            {"id": "pay_GB1", "status": "captured", "amount": 79900,
             "currency": "INR"}]})
    assert reconcile_gateway_orders(db, client) == 1
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 1
    assert reconcile_gateway_orders(db, client) == 0


def test_webhook_bundle_notes_from_gateway_order_fallback(db, monkeypatch, student_user, course):
    """I2 for bundles: payment-entity notes can be empty while the ORDER
    carries them (mirrors test_webhook_endpoint.py's course-path fallback
    test) — the bundle branch must re-check the fallback's order notes too."""
    from app.services import webhook_processor as wp

    b = _bundle(db, [course.id])

    class _FakeOrderApi:
        def __init__(self, notes):
            self._notes = notes

        def fetch(self, order_id):
            return {"id": order_id, "notes": self._notes}

    class _FakeClient:
        def __init__(self, notes):
            self.order = _FakeOrderApi(notes)

    fake = _FakeClient({"bundle_id": str(b.id), "user_id": str(student_user.id),
                         "bundle_course_ids": str(course.id)})
    monkeypatch.setattr(wp, "_gateway_client", lambda: fake)

    ev = WebhookEvent(
        event_id="evt_wb_fallback", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_WB_FALLBACK", "order_id": "order_WB_FALLBACK",
            "amount": 79900, "currency": "INR", "notes": {},
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()

    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Payment).filter_by(gateway_payment_id="pay_WB_FALLBACK").count() == 1
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 1
