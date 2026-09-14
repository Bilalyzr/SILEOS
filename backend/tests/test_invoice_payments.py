"""
Tests for the invoice_id payment target across create-order / verify
(app.routers.payments), the webhook processor, and the reconciliation
sweeper. Mirrors tests/test_bundle_checkout.py + tests/test_bundle_webhooks.py.
"""
import hashlib
import hmac

from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatPool, InvoiceStatus,
)
from app.models.payment import Order, Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.invoice_service import issue_invoice
from app.services.reconciliation import reconcile_gateway_orders
from app.services.webhook_processor import process_webhook_event
from tests.test_invoice_models import _company


def _issued_invoice(db, co, course=None, qty=5, unit=200.0):
    """An ISSUED invoice with one line item, ready to pay."""
    inv = CompanyInvoice(company_id=co.id, subtotal=qty * unit, total=qty * unit)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(
        invoice_id=inv.id, description="Seats",
        course_id=course.id if course else None,
        quantity=qty, unit_price=unit, line_total=qty * unit))
    db.commit()
    db.refresh(inv)
    issue_invoice(db, inv, pdf_renderer=lambda i: "invoices/test.pdf")
    db.commit()
    db.refresh(inv)
    return inv


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


# ---------------- create-order ----------------

def test_invoice_order_uses_invoice_total_and_notes(client, db, as_user,
                                                     student_user, course,
                                                     monkeypatch):
    _patch_gateway(monkeypatch)
    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=5, unit=200.0)  # total = 1000
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"invoice_id": inv.id})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == int(round(float(inv.total) * 100))
    notes = FakeOrders.last_payload["notes"]
    assert notes["invoice_id"] == str(inv.id)
    assert notes["user_id"] == str(student_user.id)


def test_invoice_order_403_for_non_company_user(client, db, as_user,
                                                 student_user, course,
                                                 monkeypatch):
    _patch_gateway(monkeypatch)
    from app.models.user import User
    owner = User(user_login="invowner1", user_pass="x", user_nicename="invowner1",
                 user_email="invowner1@example.com", display_name="invowner1")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    co = _company(db, owner)
    inv = _issued_invoice(db, co, course)
    as_user(student_user)  # not the owner, not a linked manager
    r = client.post("/api/v1/payments/create-order", json={"invoice_id": inv.id})
    assert r.status_code == 403


def test_invoice_order_409_for_draft_invoice(client, db, as_user,
                                             student_user, course,
                                             monkeypatch):
    _patch_gateway(monkeypatch)
    co = _company(db, student_user)
    inv = CompanyInvoice(company_id=co.id, subtotal=1000, total=1000)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(invoice_id=inv.id, description="Seats",
                              course_id=course.id, quantity=5,
                              unit_price=200.0, line_total=1000))
    db.commit()
    db.refresh(inv)
    assert inv.status == InvoiceStatus.DRAFT
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"invoice_id": inv.id})
    assert r.status_code == 409


def test_invoice_order_coupon_rejected(client, db, as_user, student_user,
                                       course, monkeypatch):
    _patch_gateway(monkeypatch)
    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course)
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order",
                    json={"invoice_id": inv.id, "coupon_code": "X"})
    assert r.status_code == 400


def test_invoice_order_404_missing_invoice(client, db, as_user, student_user,
                                           monkeypatch):
    _patch_gateway(monkeypatch)
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"invoice_id": 999999})
    assert r.status_code == 404


# ---------------- /verify ----------------

def test_verify_invoice_settles_and_creates_pool(client, db, as_user,
                                                  student_user, course,
                                                  monkeypatch):
    _patch_gateway(monkeypatch)
    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=5, unit=200.0)
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"invoice_id": inv.id})
    assert r.status_code == 200

    sig = hmac.new(b"secret", b"order_TEST1|pay_INV1", hashlib.sha256).hexdigest()
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_INV1",
        "razorpay_signature": sig, "invoice_id": inv.id,
    })
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "Invoice paid — seats activated"

    db.expire_all()
    assert inv.status == InvoiceStatus.PAID
    pool = db.query(CompanySeatPool).filter_by(invoice_id=inv.id).one()
    assert pool.course_id == course.id and pool.total_seats == 5
    assert db.query(Order).count() == 1
    assert db.query(Payment).filter_by(gateway_payment_id="pay_INV1").count() == 1


# ---------------- webhook ----------------

def _captured_invoice_event(inv, user, pay_id="pay_WI1", event_id="evt_wi1",
                            notes=None):
    amount = int(round(float(inv.total) * 100))
    return WebhookEvent(
        event_id=event_id, event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": pay_id, "order_id": "order_WI1", "amount": amount,
            "currency": "INR",
            "notes": notes if notes is not None else {
                "invoice_id": str(inv.id), "user_id": str(user.id)},
        }}}},
        signature_valid=True)


def test_webhook_settles_invoice_idempotently_across_two_events(db, student_user,
                                                                 course):
    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=3, unit=100.0)

    ev1 = _captured_invoice_event(inv, student_user, pay_id="pay_WI1", event_id="evt_a")
    db.add(ev1)
    db.commit()
    process_webhook_event(db, ev1)
    assert ev1.status == WebhookEventStatus.PROCESSED
    db.expire_all()
    assert inv.status == InvoiceStatus.PAID
    assert db.query(Payment).count() == 1
    assert db.query(Order).count() == 1

    # A second, differently-id'd event for the same payment must be a no-op
    # (idempotent on gateway_payment_id).
    ev2 = _captured_invoice_event(inv, student_user, pay_id="pay_WI1", event_id="evt_b")
    db.add(ev2)
    db.commit()
    process_webhook_event(db, ev2)
    assert ev2.status == WebhookEventStatus.PROCESSED
    assert db.query(Payment).count() == 1
    assert db.query(Order).count() == 1


def test_webhook_already_paid_invoice_processed_no_second_order(db, student_user,
                                                                 course):
    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=2, unit=150.0)

    ev1 = _captured_invoice_event(inv, student_user, pay_id="pay_WI2", event_id="evt_c")
    db.add(ev1)
    db.commit()
    process_webhook_event(db, ev1)
    assert ev1.status == WebhookEventStatus.PROCESSED
    db.expire_all()
    assert inv.status == InvoiceStatus.PAID

    # A distinct payment id (e.g. a stray re-delivery with a fresh payment
    # entity) for an invoice that is already PAID: settle_invoice's
    # ISSUED-status gate returns False, but the handler still completes.
    ev2 = _captured_invoice_event(inv, student_user, pay_id="pay_WI2_DUP",
                                  event_id="evt_d")
    db.add(ev2)
    db.commit()
    process_webhook_event(db, ev2)
    assert ev2.status == WebhookEventStatus.PROCESSED
    assert db.query(Order).count() == 1


def test_webhook_unknown_invoice_id_unrecoverable(db):
    ev = WebhookEvent(
        event_id="evt_badinv", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_BADINV", "order_id": "order_BADINV", "amount": 10000,
            "currency": "INR",
            "notes": {"invoice_id": "999999", "user_id": "1"},
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.FAILED
    assert ev.attempts == 5


def test_webhook_invoice_notes_from_gateway_order_fallback(db, monkeypatch,
                                                            student_user, course):
    """Mirrors the bundle order-notes fallback test: payment-entity notes can
    be empty while the ORDER carries them — the invoice branch must be
    re-checked after the fallback re-fetch too."""
    from app.services import webhook_processor as wp

    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=4, unit=250.0)

    class _FakeOrderApi:
        def __init__(self, notes):
            self._notes = notes

        def fetch(self, order_id):
            return {"id": order_id, "notes": self._notes}

    class _FakeClient:
        def __init__(self, notes):
            self.order = _FakeOrderApi(notes)

    fake = _FakeClient({"invoice_id": str(inv.id), "user_id": str(student_user.id)})
    monkeypatch.setattr(wp, "_gateway_client", lambda: fake)

    ev = WebhookEvent(
        event_id="evt_wi_fallback", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_WI_FALLBACK", "order_id": "order_WI_FALLBACK",
            "amount": int(round(float(inv.total) * 100)), "currency": "INR",
            "notes": {},
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()

    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Payment).filter_by(gateway_payment_id="pay_WI_FALLBACK").count() == 1
    db.expire_all()
    assert inv.status == InvoiceStatus.PAID


# ---------------- sweeper ----------------

class FakeRzpClient:
    def __init__(self, orders, payments_by_order):
        self._orders = orders
        self._pbo = payments_by_order
        self.order = self
    def all(self, opts):
        return {"items": self._orders}
    def payments(self, order_id):
        return {"items": self._pbo.get(order_id, [])}


def test_sweeper_settles_orphan_invoice_capture_once(db, student_user, course):
    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=6, unit=100.0)
    amount = int(round(float(inv.total) * 100))
    client = FakeRzpClient(
        orders=[{"id": "order_GI1", "status": "paid", "amount": amount,
                 "notes": {"invoice_id": str(inv.id),
                           "user_id": str(student_user.id)}}],
        payments_by_order={"order_GI1": [
            {"id": "pay_GI1", "status": "captured", "amount": amount,
             "currency": "INR"}]})
    assert reconcile_gateway_orders(db, client) == 1
    db.expire_all()
    assert inv.status == InvoiceStatus.PAID
    assert reconcile_gateway_orders(db, client) == 0


# ---------------- unsettleable-invoice / amount-mismatch regressions ----------------

def _alert_spy(monkeypatch, target_module):
    calls = []
    monkeypatch.setattr(
        target_module.EmailService, "send_payment_alert",
        staticmethod(lambda subject, body: calls.append((subject, body)) or True),
    )
    return calls


def test_verify_for_cancelled_invoice_409s_and_alerts(client, db, as_user,
                                                       student_user, course,
                                                       monkeypatch):
    """/verify must not report success when settle_invoice refuses an
    invoice that is not PAID: the money was captured but nothing was booked.
    Alert once, write no Order/Payment, and 409 with a do-not-pay-again
    message."""
    import app.routers.payments as pay

    _patch_gateway(monkeypatch)
    calls = _alert_spy(monkeypatch, pay)

    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=5, unit=200.0)
    as_user(student_user)
    # Create the order while the invoice is still ISSUED (so the signed order
    # amount matches), then cancel it before the browser calls back.
    assert client.post("/api/v1/payments/create-order",
                       json={"invoice_id": inv.id}).status_code == 200
    inv.status = InvoiceStatus.CANCELLED
    db.commit()

    sig = hmac.new(b"secret", b"order_TEST1|pay_INVCANCEL", hashlib.sha256).hexdigest()
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1",
        "razorpay_payment_id": "pay_INVCANCEL",
        "razorpay_signature": sig, "invoice_id": inv.id,
    })
    assert r.status_code == 409, r.text
    assert "Do not pay again" in r.json()["detail"]
    assert "pay_INVCANCEL" in r.json()["detail"]

    assert len(calls) == 1
    assert "unsettleable invoice" in calls[0][0] and "verify" in calls[0][0]

    db.expire_all()
    assert inv.status == InvoiceStatus.CANCELLED  # untouched
    assert db.query(Order).count() == 0
    assert db.query(Payment).count() == 0
    assert db.query(CompanySeatPool).count() == 0


def test_verify_replay_on_already_paid_invoice_still_succeeds(client, db, as_user,
                                                               student_user, course,
                                                               monkeypatch):
    """The already-PAID replay is a genuine idempotent status check and must
    keep returning success (no alert, no second Order)."""
    import app.routers.payments as pay

    _patch_gateway(monkeypatch)
    calls = _alert_spy(monkeypatch, pay)

    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=5, unit=200.0)
    as_user(student_user)
    assert client.post("/api/v1/payments/create-order",
                       json={"invoice_id": inv.id}).status_code == 200

    sig = hmac.new(b"secret", b"order_TEST1|pay_INVREPLAY", hashlib.sha256).hexdigest()
    body = {"razorpay_order_id": "order_TEST1",
            "razorpay_payment_id": "pay_INVREPLAY",
            "razorpay_signature": sig, "invoice_id": inv.id}
    assert client.post("/api/v1/payments/verify", json=body).status_code == 200
    # Second call: settle_invoice returns False (duplicate gateway_payment_id)
    # but the invoice is PAID, so this is success, not a 409.
    r = client.post("/api/v1/payments/verify", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "Invoice paid — seats activated"
    assert calls == []
    assert db.query(Order).count() == 1
    assert db.query(Payment).count() == 1


def test_webhook_capture_for_cancelled_invoice_alerts_and_drops_no_state(
        db, monkeypatch, student_user, course):
    """FINDING 1: money captured for a non-ISSUED (e.g. CANCELLED) invoice
    must never be silently dropped — settle_invoice returns False, the
    webhook still PROCESSES (retries can't fix a cancelled invoice), but an
    alert must fire and no Order/Payment may be written."""
    from app.services import webhook_processor as wp

    calls = _alert_spy(monkeypatch, wp)

    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=3, unit=200.0)  # total = 600
    inv.status = InvoiceStatus.CANCELLED
    db.commit()

    ev = _captured_invoice_event(inv, student_user, pay_id="pay_CANCELLED",
                                 event_id="evt_cancelled")
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)

    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Order).count() == 0
    assert db.query(Payment).count() == 0
    assert len(calls) == 1
    assert "unsettleable invoice" in calls[0][0]
    db.expire_all()
    assert inv.status == InvoiceStatus.CANCELLED  # untouched


def test_webhook_capture_amount_mismatch_alerts_and_stays_issued(
        db, monkeypatch, student_user, course):
    """FINDING 2: a captured amount that doesn't match invoice.total must not
    be booked at the invoice's full total — alert and skip settling."""
    from app.services import webhook_processor as wp

    calls = _alert_spy(monkeypatch, wp)

    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=3, unit=200.0)  # total = 600 => 60000 paise
    ev = _captured_invoice_event(inv, student_user, pay_id="pay_MISMATCH",
                                 event_id="evt_mismatch")
    # Tamper the captured amount to 100 paise (₹1) instead of the full total.
    ev.payload["payload"]["payment"]["entity"]["amount"] = 100
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)

    assert ev.status == WebhookEventStatus.PROCESSED
    db.expire_all()
    assert inv.status == InvoiceStatus.ISSUED
    assert db.query(Payment).count() == 0
    assert db.query(Order).count() == 0
    assert len(calls) == 1
    assert "mismatch" in calls[0][0]


def test_sweeper_orphan_amount_mismatch_alerts_and_stays_issued(
        db, monkeypatch, student_user, course):
    """FINDING 2 for the sweeper: a same-order-different-amount orphan
    capture must not settle the invoice at its full total."""
    from app.services import reconciliation as recon

    calls = _alert_spy(monkeypatch, recon)

    co = _company(db, student_user)
    inv = _issued_invoice(db, co, course, qty=3, unit=200.0)  # total = 600
    client = FakeRzpClient(
        orders=[{"id": "order_GI_MISMATCH", "status": "paid", "amount": 100,
                 "notes": {"invoice_id": str(inv.id),
                           "user_id": str(student_user.id)}}],
        payments_by_order={"order_GI_MISMATCH": [
            {"id": "pay_GI_MISMATCH", "status": "captured", "amount": 100,
             "currency": "INR"}]})

    assert reconcile_gateway_orders(db, client) == 0
    db.expire_all()
    assert inv.status == InvoiceStatus.ISSUED
    assert db.query(Payment).count() == 0
    assert len(calls) == 1
    assert "mismatch" in calls[0][0]
