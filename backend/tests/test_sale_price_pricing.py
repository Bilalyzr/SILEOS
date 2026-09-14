"""
Tests for the sale-price pricing authority (audit A5).

Bug: the direct Razorpay checkout path (payments.py create-order/verify)
always charged `course.course_price`, ignoring `course.course_sale_price`
even when it was set and advertised at checkout. The cart path
(orders.py) already honored the sale price. This file pins:

  1. `app.services.pricing.effective_course_price` / `is_on_sale` as the
     single pricing authority (0 < sale < price -> sale, else price).
  2. create-order / verify route the Razorpay amount through it.
  3. Coupon discounts are computed off the effective price, not list price.
  4. Seat-price cohort overrides still take precedence over course price
     (including over a sale price).
  5. The webhook/sweeper fulfillment path agrees with the authority.
  6. The cart path (orders.py) keeps its existing behavior for sale<price
     and documents the change for sale>=price (audit fix: authority uses
     strict 0 < sale < price; a sale >= list price is now ignored instead
     of always winning).
"""
import hashlib
import hmac

import pytest

from app.models.cohort import Cohort, ReferralCode
from app.models.coupon import Coupon
from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderItem, Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.pricing import effective_course_price, is_on_sale, resolve_expected_purchase
from app.services.reconciliation import reconcile_gateway_orders
from app.services.webhook_processor import process_webhook_event


# ---------------------------------------------------------------------------
# 1. Pure pricing-authority unit tests
# ---------------------------------------------------------------------------

def _course_with(db, course, price, sale):
    course.course_price = price
    course.course_sale_price = sale
    db.commit()
    db.refresh(course)
    return course


def test_authority_sale_below_price_wins(db, course):
    c = _course_with(db, course, price=999, sale=499)
    assert effective_course_price(c) == 499
    assert is_on_sale(c) is True


def test_authority_sale_equal_price_ignored(db, course):
    c = _course_with(db, course, price=999, sale=999)
    assert effective_course_price(c) == 999
    assert is_on_sale(c) is False


def test_authority_sale_above_price_ignored(db, course):
    c = _course_with(db, course, price=999, sale=1500)
    assert effective_course_price(c) == 999
    assert is_on_sale(c) is False


def test_authority_sale_zero_ignored(db, course):
    c = _course_with(db, course, price=999, sale=0)
    assert effective_course_price(c) == 999
    assert is_on_sale(c) is False


def test_authority_sale_none_ignored(db, course):
    c = _course_with(db, course, price=999, sale=None)
    assert effective_course_price(c) == 999
    assert is_on_sale(c) is False


def test_authority_free_course(db, course):
    c = _course_with(db, course, price=0, sale=0)
    assert effective_course_price(c) == 0
    assert is_on_sale(c) is False


# ---------------------------------------------------------------------------
# Fakes / helpers for the Razorpay-mocked router tests. Mirrors
# tests/test_bundle_checkout.py's FakeOrders pattern.
# ---------------------------------------------------------------------------

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


def _publish(db, course):
    course.post_status = "publish"
    db.commit()


def _verify_sig(order_id, payment_id):
    return hmac.new(b"secret", f"{order_id}|{payment_id}".encode(),
                     hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# 2. create-order charges the sale price, and stamps notes with both prices
# ---------------------------------------------------------------------------

def test_create_order_charges_sale_price_in_paise(client, db, as_user,
                                                   student_user, course,
                                                   monkeypatch):
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order", json={"course_id": course.id})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == 49900

    notes = FakeOrders.last_payload["notes"]
    assert notes["list_price"] == "999.00"
    assert notes["sale_price"] == "499.00"


def test_create_order_no_sale_charges_list_price(client, db, as_user,
                                                  student_user, course,
                                                  monkeypatch):
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=0)
    _publish(db, course)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order", json={"course_id": course.id})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == 99900


# ---------------------------------------------------------------------------
# 3. verify: pre-fix behavior inverted — assert BOTH directions
# ---------------------------------------------------------------------------

def test_verify_accepts_sale_price_amount(client, db, as_user, student_user,
                                          course, monkeypatch):
    """Post-fix: a gateway order actually opened (and captured) for the
    sale-price amount (49900 paise) must verify successfully. Pre-fix,
    /verify recomputed expected_price from course.course_price alone and
    would have REJECTED this with 400 'Order amount does not match'."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order", json={"course_id": course.id})
    assert r.status_code == 200
    assert FakeOrders.last_payload["amount"] == 49900

    sig = _verify_sig("order_TEST1", "pay_SALEOK")
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_SALEOK",
        "razorpay_signature": sig, "course_id": course.id,
    })
    assert r.status_code == 200, r.text
    assert db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id).count() == 1


def test_verify_rejects_list_price_amount_when_course_on_sale(
        client, db, as_user, student_user, course, monkeypatch):
    """Pre-fix behavior inverted: the OLD code would have accepted a gateway
    order opened for the full list-price amount (99900 paise) even though
    the course is on sale. Post-fix this must be REJECTED, since the
    authority-derived expected price is the sale price (49900)."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    as_user(student_user)

    # Simulate a gateway order that was (somehow) opened for the full list
    # price — e.g. a stale/forged order — rather than going through
    # create-order's correct sale-price computation.
    FakeOrders.last_payload = {
        "amount": 99900,
        "currency": "INR",
        "notes": {"course_id": str(course.id), "user_id": str(student_user.id)},
    }

    sig = _verify_sig("order_TEST1", "pay_LISTBAD")
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_LISTBAD",
        "razorpay_signature": sig, "course_id": course.id,
    })
    assert r.status_code == 400
    assert "does not match" in r.json()["detail"]
    assert db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id).count() == 0


# ---------------------------------------------------------------------------
# 4. Coupons compute their base off the effective (sale) price
# ---------------------------------------------------------------------------

def _percentage_coupon(db, course, code="SALE10", pct=10):
    c = Coupon(code=code, discount_type="percentage", discount_value=pct,
              is_active=True, applicability="all_courses",
              created_by=course.post_author)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _fixed_coupon(db, course, code="FLAT50", amount=50):
    c = Coupon(code=code, discount_type="fixed", discount_value=amount,
              is_active=True, applicability="all_courses",
              created_by=course.post_author)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_percentage_coupon_bases_off_sale_price(client, db, as_user,
                                                student_user, course,
                                                monkeypatch):
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    _percentage_coupon(db, course, code="SALE10", pct=10)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order",
                    json={"course_id": course.id, "coupon_code": "SALE10"})
    assert r.status_code == 200, r.text
    # 10% off 499 = 44910 paise, NOT 10% off 999 (89910).
    assert FakeOrders.last_payload["amount"] == 44910


def test_fixed_coupon_bases_off_sale_price(client, db, as_user, student_user,
                                           course, monkeypatch):
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    _fixed_coupon(db, course, code="FLAT50", amount=50)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order",
                    json={"course_id": course.id, "coupon_code": "FLAT50"})
    assert r.status_code == 200, r.text
    # 499 - 50 = 449 -> 44900 paise.
    assert FakeOrders.last_payload["amount"] == 44900


# ---------------------------------------------------------------------------
# 5. Seat-priced cohort precedence is preserved (overrides even a sale price)
# ---------------------------------------------------------------------------

def test_seat_price_still_overrides_sale_price(client, db, as_user,
                                               student_user, course,
                                               monkeypatch):
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
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
    assert FakeOrders.last_payload["amount"] == 25000  # seat price wins over sale price


# ---------------------------------------------------------------------------
# 6. Webhook fulfillment path agrees with the authority: the Order written
# carries the effective (sale) price as its subtotal, not the list price.
# ---------------------------------------------------------------------------

def _captured_event(user, course, event_id="evt_1", pay_id="pay_W1", amount_paise=49900):
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


def test_webhook_fulfillment_records_effective_price_as_subtotal(
        client, db, monkeypatch, student_user, course):
    from app.core.config import get_settings
    import json

    _course_with(db, course, price=999, sale=499)

    settings = get_settings()
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "whsec_test", raising=False)

    payload = _captured_event(student_user, course, amount_paise=49900)
    body = json.dumps(payload).encode()
    sig = hmac.new(b"whsec_test", body, hashlib.sha256).hexdigest()

    r = client.post(
        "/api/v1/payments/webhook", content=body,
        headers={"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": "evt_sale_wh",
                "Content-Type": "application/json"},
    )
    assert r.status_code == 200, r.text

    ev = db.query(WebhookEvent).filter_by(event_id="evt_sale_wh").one()
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_W1").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    # Effective price (sale price), not list price, and zero coupon discount
    # since the full sale price was captured.
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0


# ---------------------------------------------------------------------------
# 7. Cart path (orders.py) regression + documented behavior change
# ---------------------------------------------------------------------------

def test_cart_path_unchanged_for_sale_below_price(client, db, as_user,
                                                   student_user, course):
    """sale < price: orders.py already honored this — must keep doing so.

    The /orders endpoint only ever completes (200) a fully-discounted
    order — any positive final_amount is 402'd because there is no
    multi-course gateway flow. A 100%-fixed coupon drives final_amount
    to 0 so we can observe the pre-discount subtotal it computed from
    the course's sale price."""
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    _fixed_coupon(db, course, code="FULL499", amount=499)
    as_user(student_user)

    r = client.post("/api/v1/orders/", json={
        "course_ids": [course.id], "coupon_code": "FULL499",
    })
    assert r.status_code == 200, r.text
    order_row = db.query(Order).filter_by(id=r.json()["id"]).one()
    assert float(order_row.subtotal_amount) == 499.0  # sale price, not 999
    assert float(order_row.total_amount) == 0.0


def test_cart_path_sale_above_price_now_ignored(client, db, as_user,
                                                student_user, course):
    """Documented behavior change: orders.py's OLD inline rule accepted
    `sale_price >= price` (any positive sale_price won regardless of
    whether it was above list price). The new shared authority requires
    strict `0 < sale < price` — a sale price at or above list price is
    now correctly ignored on the cart path too, matching the Razorpay
    direct-checkout path and the audit's stated rule."""
    _course_with(db, course, price=999, sale=1500)
    _publish(db, course)
    _fixed_coupon(db, course, code="FULL999", amount=999)
    as_user(student_user)

    r = client.post("/api/v1/orders/", json={
        "course_ids": [course.id], "coupon_code": "FULL999",
    })
    assert r.status_code == 200, r.text
    order_row = db.query(Order).filter_by(id=r.json()["id"]).one()
    assert float(order_row.subtotal_amount) == 999.0  # list price wins; sale (1500) ignored
    assert float(order_row.total_amount) == 0.0


# ---------------------------------------------------------------------------
# 8. Seat-priced purchase: verify/webhook/sweeper must agree field-for-field
# (review follow-up on the seat-price + sale-price interaction).
#
# Pre-fix bug: when the seat-price cohort override fired in /verify, only
# `expected_price` was overridden to the seat price — `base_price` (passed
# to fulfill_course_purchase as the Order's pre-coupon subtotal) still held
# the course's effective (sale) price. That wrote subtotal=499/discount=0/
# paid=250 from /verify, while webhook/sweeper (which derive their discount
# as base_price - paid_amount) wrote subtotal=499/discount=249/paid=250.
# Both individually satisfy paid == subtotal - discount, but the three paths
# disagreed on what the Order actually records for the identical purchase.
# ---------------------------------------------------------------------------

def _seat_priced_cohort(db, course, seat_price=250.0, code="SEATSALE"):
    cohort = Cohort(name="Seat", spoc_user_id=course.post_author,
                    course_id=course.id, seat_price=seat_price, is_active=True)
    db.add(cohort)
    db.flush()
    rc = ReferralCode(cohort_id=cohort.id, code=code, max_uses=10)
    db.add(rc)
    db.commit()
    db.refresh(cohort)
    db.refresh(rc)
    return cohort, rc


def _order_fields(order_row):
    """The fields that must agree field-for-field across verify/webhook/
    sweeper for the same purchase."""
    return {
        "subtotal_amount": float(order_row.subtotal_amount),
        "discount_amount": float(order_row.discount_amount),
        "total_amount": float(order_row.total_amount),
        "currency": order_row.currency,
    }


def test_verify_seat_price_order_row_is_internally_consistent(
        client, db, as_user, student_user, course, monkeypatch):
    """paid == subtotal - discount must hold for the Order /verify writes
    on a seat-priced purchase into a course that also happens to be on
    sale (999 list / 499 sale / 250 seat)."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    cohort, rc = _seat_priced_cohort(db, course, seat_price=250.0, code="SEATV")
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order",
                    json={"course_id": course.id, "coupon_code": "SEATV"})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == 25000  # seat price, not sale/list

    sig = _verify_sig("order_TEST1", "pay_SEATV1")
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_SEATV1",
        "razorpay_signature": sig, "course_id": course.id,
    })
    assert r.status_code == 200, r.text

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_SEATV1").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 250.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 250.0
    assert (float(order_row.subtotal_amount) - float(order_row.discount_amount)
            == float(order_row.total_amount))


def test_verify_and_webhook_seat_price_rows_match_field_for_field(
        client, db, as_user, student_user, course, monkeypatch):
    """The Order row /verify writes for a seat-priced purchase must match
    (subtotal/discount/total/currency) the Order row the webhook path
    writes for an equivalent seat-priced purchase — same course, same
    cohort, same seat price actually paid, different gateway_payment_id."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    cohort, rc = _seat_priced_cohort(db, course, seat_price=250.0, code="SEATCMP")
    as_user(student_user)

    # --- verify path ---
    r = client.post("/api/v1/payments/create-order",
                    json={"course_id": course.id, "coupon_code": "SEATCMP"})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == 25000

    sig = _verify_sig("order_TEST1", "pay_SEATCMPV")
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_SEATCMPV",
        "razorpay_signature": sig, "course_id": course.id,
    })
    assert r.status_code == 200, r.text

    verify_payment = db.query(Payment).filter_by(
        gateway_payment_id="pay_SEATCMPV").one()
    verify_order = db.query(Order).filter_by(id=verify_payment.order_id).one()

    # --- webhook path: a second student, same course/cohort/seat price ---
    from app.models.user import User
    student2 = User(user_login="student2", user_pass="x", user_nicename="student2",
                    user_email="student2@example.com", display_name="student2")
    db.add(student2)
    db.commit()
    db.refresh(student2)

    ev = WebhookEvent(
        event_id="evt_seatcmp", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_SEATCMPW", "order_id": "order_SEATCMPW", "amount": 25000,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student2.id),
                      "cohort_id": str(cohort.id), "referral_code_id": str(rc.id)},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    webhook_payment = db.query(Payment).filter_by(
        gateway_payment_id="pay_SEATCMPW").one()
    webhook_order = db.query(Order).filter_by(id=webhook_payment.order_id).one()

    assert _order_fields(verify_order) == _order_fields(webhook_order)
    assert float(verify_order.subtotal_amount) == 250.0
    assert float(verify_order.discount_amount) == 0.0


# ---------------------------------------------------------------------------
# 9. Sweeper (reconciliation.py) three-path agreement on a plain sale-priced
# purchase (no cohort/seat price involved) — matches verify and webhook.
# ---------------------------------------------------------------------------

class FakeRzpClient:
    """Mimics razorpay.Client surface used by the sweeper (see
    tests/test_reconciliation.py)."""
    def __init__(self, orders, payments_by_order):
        self._orders = orders
        self._pbo = payments_by_order
        self.order = self

    def all(self, opts):
        return {"items": self._orders}

    def payments(self, order_id):
        return {"items": self._pbo.get(order_id, [])}


def test_sweeper_matches_verify_and_webhook_for_sale_priced_purchase(
        client, db, as_user, student_user, course, monkeypatch):
    """Same 999/499 sale-priced course, fulfilled three different ways for
    three different buyers (via /verify, via the webhook, and via the
    sweeper's orphan-capture path). All three Order rows must agree
    field-for-field: subtotal=499 (sale price), discount=0, total=499."""
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)

    # --- verify path ---
    _patch_gateway(monkeypatch)
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"course_id": course.id})
    assert r.status_code == 200
    assert FakeOrders.last_payload["amount"] == 49900
    sig = _verify_sig("order_TEST1", "pay_SALEV1")
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_SALEV1",
        "razorpay_signature": sig, "course_id": course.id,
    })
    assert r.status_code == 200, r.text
    verify_payment = db.query(Payment).filter_by(gateway_payment_id="pay_SALEV1").one()
    verify_order = db.query(Order).filter_by(id=verify_payment.order_id).one()

    # --- webhook path: second buyer ---
    from app.models.user import User
    student2 = User(user_login="saleb2", user_pass="x", user_nicename="saleb2",
                    user_email="saleb2@example.com", display_name="saleb2")
    db.add(student2)
    db.commit()
    db.refresh(student2)

    ev = WebhookEvent(
        event_id="evt_salecmp", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_SALEW1", "order_id": "order_SALEW1", "amount": 49900,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student2.id)},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED
    webhook_payment = db.query(Payment).filter_by(gateway_payment_id="pay_SALEW1").one()
    webhook_order = db.query(Order).filter_by(id=webhook_payment.order_id).one()

    # --- sweeper path: third buyer, an orphaned gateway capture ---
    from app.models.user import User as _User
    student3 = _User(user_login="saleb3", user_pass="x", user_nicename="saleb3",
                     user_email="saleb3@example.com", display_name="saleb3")
    db.add(student3)
    db.commit()
    db.refresh(student3)

    sweep_client = FakeRzpClient(
        orders=[{"id": "order_SALESWEEP", "status": "paid", "amount": 49900,
                "notes": {"course_id": str(course.id), "user_id": str(student3.id)}}],
        payments_by_order={"order_SALESWEEP": [
            {"id": "pay_SALESWEEP", "status": "captured", "amount": 49900,
             "currency": "INR"},
        ]},
    )
    n = reconcile_gateway_orders(db, sweep_client)
    assert n == 1
    sweep_payment = db.query(Payment).filter_by(gateway_payment_id="pay_SALESWEEP").one()
    sweep_order = db.query(Order).filter_by(id=sweep_payment.order_id).one()

    assert _order_fields(verify_order) == _order_fields(webhook_order)
    assert _order_fields(webhook_order) == _order_fields(sweep_order)
    assert float(verify_order.subtotal_amount) == 499.0
    assert float(verify_order.discount_amount) == 0.0


# ---------------------------------------------------------------------------
# 10. Paise-boundary pins at create-order and verify.
# ---------------------------------------------------------------------------

def test_create_order_sale_price_with_paise_fraction(client, db, as_user,
                                                      student_user, course,
                                                      monkeypatch):
    """A sale price with a paise fraction (₹499.99) must convert to exactly
    49999 paise — no silent rounding drift."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499.99)
    _publish(db, course)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order", json={"course_id": course.id})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == 49999


def test_create_order_sub_rupee_sale_clamped_to_razorpay_minimum(
        client, db, as_user, student_user, course, monkeypatch):
    """A sale price of ₹0.01 is below Razorpay's minimum chargeable amount
    (₹1 / 100 paise) — create-order must clamp up to 100 paise rather than
    send an amount Razorpay will reject."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=0.01)
    _publish(db, course)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order", json={"course_id": course.id})
    assert r.status_code == 200, r.text
    assert FakeOrders.last_payload["amount"] == 100


def test_verify_sale_price_with_paise_fraction(client, db, as_user,
                                               student_user, course,
                                               monkeypatch):
    """The same ₹499.99 sale-price boundary, round-tripped through verify:
    a gateway order actually captured for 49999 paise must be accepted."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499.99)
    _publish(db, course)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order", json={"course_id": course.id})
    assert r.status_code == 200
    assert FakeOrders.last_payload["amount"] == 49999

    sig = _verify_sig("order_TEST1", "pay_PAISEV1")
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_PAISEV1",
        "razorpay_signature": sig, "course_id": course.id,
    })
    assert r.status_code == 200, r.text


def test_verify_sub_rupee_sale_clamped_to_razorpay_minimum(
        client, db, as_user, student_user, course, monkeypatch):
    """The ₹0.01 sale-price boundary, round-tripped through verify: a
    gateway order captured for the clamped 100 paise must be accepted
    (not rejected as a mismatch against the unclamped ₹0.01)."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=0.01)
    _publish(db, course)
    as_user(student_user)

    r = client.post("/api/v1/payments/create-order", json={"course_id": course.id})
    assert r.status_code == 200
    assert FakeOrders.last_payload["amount"] == 100

    sig = _verify_sig("order_TEST1", "pay_PAISEV2")
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_PAISEV2",
        "razorpay_signature": sig, "course_id": course.id,
    })
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# 11. CRITICAL regression (review round 3): webhook_processor.py and
# reconciliation.py must never trust notes["cohort_id"] for pricing or
# enrollment mapping without the SAME course-binding check /verify's
# resolver enforces. Round 2 introduced this gap when it added a
# seat-price override to those two paths without it — a stale/forged
# cohort_id pointing at a DIFFERENT course's (cheaper) seat-priced cohort
# could under-charge the buyer, mis-map the enrollment, and burn a
# ReferralCode's used_count that was never legitimately presented for
# this purchase.
# ---------------------------------------------------------------------------

def _other_course_with_cheap_seat_cohort(db, seat_price=1.0, code="FORGED"):
    """A second, unrelated course with its own seat-priced cohort — used to
    simulate a forged/stale cohort_id note pointing at someone else's cheap
    seat cohort."""
    from app.models.course import Course
    from app.models.user import User

    other_instructor = User(
        user_login="other_instr", user_pass="x", user_nicename="other_instr",
        user_email="other_instr@example.com", display_name="other_instr",
    )
    db.add(other_instructor)
    db.commit()
    db.refresh(other_instructor)

    other_course = Course(
        post_author=other_instructor.id, post_title="Other Course",
        course_price_type="paid", course_price=1.0,
    )
    db.add(other_course)
    db.commit()
    db.refresh(other_course)

    other_cohort = Cohort(name="ForgedSeat", spoc_user_id=other_instructor.id,
                          course_id=other_course.id, seat_price=seat_price,
                          is_active=True)
    db.add(other_cohort)
    db.flush()
    other_rc = ReferralCode(cohort_id=other_cohort.id, code=code, max_uses=10)
    db.add(other_rc)
    db.commit()
    db.refresh(other_cohort)
    db.refresh(other_rc)
    return other_course, other_cohort, other_rc


def test_webhook_ignores_cohort_note_from_a_different_course(
        db, student_user, course):
    """A ₹499-sale-priced course purchase whose gateway-order notes carry a
    forged cohort_id pointing at ANOTHER course's ₹1-seat cohort must be
    fulfilled at the course's own effective price (499), with NO cohort
    mapping and NO referral bump — not silently discounted to ₹1."""
    _course_with(db, course, price=999, sale=499)
    other_course, other_cohort, other_rc = _other_course_with_cheap_seat_cohort(db)

    ev = WebhookEvent(
        event_id="evt_forged_cohort", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_FORGED1", "order_id": "order_FORGED1", "amount": 49900,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "cohort_id": str(other_cohort.id),
                      "referral_code_id": str(other_rc.id)},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_FORGED1").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 499.0

    enrollment = db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id).one()
    assert enrollment.cohort_id is None

    db.refresh(other_rc)
    assert other_rc.used_count == 0


def test_sweeper_ignores_cohort_note_from_a_different_course(
        db, student_user, course):
    """Same forged-cohort scenario, driven through the sweeper's
    orphan-capture path instead of the webhook."""
    _course_with(db, course, price=999, sale=499)
    other_course, other_cohort, other_rc = _other_course_with_cheap_seat_cohort(
        db, seat_price=1.0, code="FORGEDSWEEP")

    sweep_client = FakeRzpClient(
        orders=[{"id": "order_FORGEDSWEEP", "status": "paid", "amount": 49900,
                "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                          "cohort_id": str(other_cohort.id),
                          "referral_code_id": str(other_rc.id)}}],
        payments_by_order={"order_FORGEDSWEEP": [
            {"id": "pay_FORGEDSWEEP", "status": "captured", "amount": 49900,
             "currency": "INR"},
        ]},
    )
    n = reconcile_gateway_orders(db, sweep_client)
    assert n == 1

    payment_row = db.query(Payment).filter_by(
        gateway_payment_id="pay_FORGEDSWEEP").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 499.0

    enrollment = db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id).one()
    assert enrollment.cohort_id is None

    db.refresh(other_rc)
    assert other_rc.used_count == 0


def test_webhook_seat_price_below_paid_amount_skips_override_and_warns(
        db, student_user, course, caplog):
    """A legitimate, correctly course-bound cohort whose seat_price is
    implausibly far below what was actually captured (more than Rs.1) must
    NOT be trusted for pricing — the override is skipped, the effective
    course price is used instead, and a warning is logged. This guards
    against a correctly-bound-but-corrupted/misconfigured seat_price
    still producing paid != subtotal - discount."""
    _course_with(db, course, price=999, sale=499)
    cohort, rc = _seat_priced_cohort(db, course, seat_price=1.0, code="CHEAPSEAT")

    ev = WebhookEvent(
        event_id="evt_cheap_seat", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_CHEAPSEAT", "order_id": "order_CHEAPSEAT", "amount": 49900,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "cohort_id": str(cohort.id), "referral_code_id": str(rc.id)},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    import logging
    with caplog.at_level(logging.WARNING, logger="app.services.pricing"):
        process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_CHEAPSEAT").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    # Falls back to the effective course price (499), NOT the seat price (1).
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 499.0
    assert (float(order_row.subtotal_amount) - float(order_row.discount_amount)
            == float(order_row.total_amount))
    assert any("seat_price" in rec.message and "skipping" in rec.message
              for rec in caplog.records)


def test_webhook_non_numeric_cohort_id_note_processed_normally(
        db, student_user, course):
    """A non-numeric cohort_id note (e.g. 'abc') must not crash the
    webhook handler — it is treated as absent and the event still
    fulfils normally at the effective course price."""
    _course_with(db, course, price=999, sale=499)

    ev = WebhookEvent(
        event_id="evt_bad_cohort", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_BADCOHORT", "order_id": "order_BADCOHORT", "amount": 49900,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "cohort_id": "abc"},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_BADCOHORT").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0


def test_webhook_nonexistent_numeric_cohort_id_note_processed_normally(
        db, student_user, course):
    """A numeric but nonexistent cohort_id (999999) must not crash the
    webhook handler either — treated as "no such cohort", fulfils
    normally at the effective course price."""
    _course_with(db, course, price=999, sale=499)

    ev = WebhookEvent(
        event_id="evt_missing_cohort", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_MISSINGCOHORT", "order_id": "order_MISSINGCOHORT",
            "amount": 49900, "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "cohort_id": "999999"},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(
        gateway_payment_id="pay_MISSINGCOHORT").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0


def test_sweeper_non_numeric_referral_code_id_note_processed_normally(
        db, student_user, course):
    """A non-numeric referral_code_id note must not crash the sweeper —
    treated as absent; the sweeper still fulfils at the effective price
    with no cohort mapping (cohort_id itself is absent here too)."""
    _course_with(db, course, price=999, sale=499)

    sweep_client = FakeRzpClient(
        orders=[{"id": "order_BADREF", "status": "paid", "amount": 49900,
                "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                          "referral_code_id": "not-a-number"}}],
        payments_by_order={"order_BADREF": [
            {"id": "pay_BADREF", "status": "captured", "amount": 49900,
             "currency": "INR"},
        ]},
    )
    n = reconcile_gateway_orders(db, sweep_client)
    assert n == 1

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_BADREF").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0


def test_webhook_legitimate_referral_into_own_course_seat_cohort_still_works(
        db, student_user, course):
    """Regression guard: a LEGITIMATE referral into a seat-priced cohort
    that IS bound to the purchased course must still charge the seat
    price via the webhook path — the course-binding check must not
    over-correct into rejecting valid same-course cohorts."""
    _course_with(db, course, price=999, sale=499)
    cohort, rc = _seat_priced_cohort(db, course, seat_price=250.0, code="LEGITSEAT")

    ev = WebhookEvent(
        event_id="evt_legit_seat", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_LEGITSEAT", "order_id": "order_LEGITSEAT", "amount": 25000,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "cohort_id": str(cohort.id), "referral_code_id": str(rc.id)},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_LEGITSEAT").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 250.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 250.0

    enrollment = db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id).one()
    assert enrollment.cohort_id == cohort.id


def test_sweeper_legitimate_referral_into_own_course_seat_cohort_still_works(
        db, student_user, course):
    """Same legitimate same-course seat-price scenario via the sweeper."""
    _course_with(db, course, price=999, sale=499)
    cohort, rc = _seat_priced_cohort(db, course, seat_price=250.0, code="LEGITSWEEP")

    sweep_client = FakeRzpClient(
        orders=[{"id": "order_LEGITSWEEP", "status": "paid", "amount": 25000,
                "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                          "cohort_id": str(cohort.id), "referral_code_id": str(rc.id)}}],
        payments_by_order={"order_LEGITSWEEP": [
            {"id": "pay_LEGITSWEEP", "status": "captured", "amount": 25000,
             "currency": "INR"},
        ]},
    )
    n = reconcile_gateway_orders(db, sweep_client)
    assert n == 1

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_LEGITSWEEP").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 250.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 250.0

    enrollment = db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id).one()
    assert enrollment.cohort_id == cohort.id


def test_verify_ignores_forged_cohort_from_a_different_course(
        client, db, as_user, student_user, course, monkeypatch):
    """/verify itself must also reject a hand-crafted gateway order whose
    notes carry a cohort_id from a DIFFERENT course — a hand-crafted order
    can't be created via create-order (it always writes a course-bound
    cohort_id), so this simulates a forged/replayed note directly."""
    _patch_gateway(monkeypatch)
    _course_with(db, course, price=999, sale=499)
    _publish(db, course)
    other_course, other_cohort, other_rc = _other_course_with_cheap_seat_cohort(
        db, seat_price=1.0, code="FORGEDVERIFY")
    as_user(student_user)

    # A hand-crafted gateway order for the correct sale-price amount (499)
    # but with a cohort_id/referral_code_id note pointing at the OTHER
    # course's Rs.1 seat cohort.
    FakeOrders.last_payload = {
        "amount": 49900, "currency": "INR",
        "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                  "cohort_id": str(other_cohort.id),
                  "referral_code_id": str(other_rc.id)},
    }

    sig = _verify_sig("order_TEST1", "pay_VFORGED1")
    r = client.post("/api/v1/payments/verify", json={
        "razorpay_order_id": "order_TEST1", "razorpay_payment_id": "pay_VFORGED1",
        "razorpay_signature": sig, "course_id": course.id,
    })
    # The order was captured for the correct sale-price amount (499, not
    # the forged Rs.1 seat price) since the cohort note is untrusted and
    # the effective price (499) applies — so verify's amount-equality
    # check passes and the purchase succeeds at the correct price, WITHOUT
    # mapping the enrollment to the foreign cohort.
    assert r.status_code == 200, r.text

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_VFORGED1").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0

    enrollment = db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id).one()
    assert enrollment.cohort_id is None

    db.refresh(other_rc)
    assert other_rc.used_count == 0


def test_coupon_order_with_cohort_note_gets_no_seat_price_override(
        db, student_user, course):
    """Pin the `is_coupon` kind check explicitly (not the mere presence of
    a cohort note): a coupon-code purchase whose notes ALSO happen to
    carry a cohort_id (e.g. because the coupon itself is cohort-linked)
    must price off the coupon's discount, never the cohort's seat price —
    even when that cohort legitimately belongs to this course."""
    _course_with(db, course, price=999, sale=499)
    cohort, rc = _seat_priced_cohort(db, course, seat_price=1.0, code="CPNCOHORT")
    coupon = Coupon(code="CPN10", discount_type="percentage", discount_value=10,
                    is_active=True, applicability="all_courses",
                    created_by=course.post_author)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)

    ev = WebhookEvent(
        event_id="evt_coupon_with_cohort", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_CPNCOHORT", "order_id": "order_CPNCOHORT", "amount": 44910,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "coupon_code": "CPN10", "coupon_id": str(coupon.id),
                      # A cohort note present alongside a coupon note must
                      # never trigger the seat-price override.
                      "cohort_id": str(cohort.id)},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_CPNCOHORT").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    # 10% off the sale price (499) = 449.10, NOT the Rs.1 seat price.
    assert float(order_row.subtotal_amount) == 499.0
    assert abs(float(order_row.discount_amount) - 49.9) < 0.01
    assert abs(float(order_row.total_amount) - 449.1) < 0.01


# ---------------------------------------------------------------------------
# 12. Round-4 gate follow-up:
#   (a) IMPORTANT — _parse_note_id must reject out-of-range ids (too large
#       for SQLite/Postgres to even query, or non-positive) the same way it
#       already rejects non-numeric ones — never let an unqueryable value
#       reach the ORM and blow up the whole webhook event / sweeper capture.
#   (b) MINOR — resolve_expected_purchase(db, course, None) must not raise.
# ---------------------------------------------------------------------------

def test_webhook_oversized_cohort_id_processed_normally(db, student_user, course):
    """A cohort_id note that parses as a valid int but is far outside any
    real database id (e.g. a 30-digit number) must not crash the webhook
    handler — SQLite raises OverflowError, Postgres a driver-level error,
    trying to query Cohort.id == that value. Treated as absent; the event
    still fulfils normally at the effective course price."""
    _course_with(db, course, price=999, sale=499)

    ev = WebhookEvent(
        event_id="evt_huge_cohort", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_HUGECOHORT", "order_id": "order_HUGECOHORT", "amount": 49900,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "cohort_id": "1000000000000000000000000000000"},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_HUGECOHORT").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 499.0


def test_webhook_negative_cohort_id_processed_normally(db, student_user, course):
    """A negative cohort_id note ('-5') is a valid int but never a valid id
    — must be treated as absent, not queried."""
    _course_with(db, course, price=999, sale=499)

    ev = WebhookEvent(
        event_id="evt_negative_cohort", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_NEGCOHORT", "order_id": "order_NEGCOHORT", "amount": 49900,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "cohort_id": "-5"},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_NEGCOHORT").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0


def test_webhook_zero_cohort_id_processed_normally(db, student_user, course):
    """A cohort_id note of '0' is a valid int but never a valid id (ids
    start at 1) — must be treated as absent, not queried."""
    _course_with(db, course, price=999, sale=499)

    ev = WebhookEvent(
        event_id="evt_zero_cohort", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_ZEROCOHORT", "order_id": "order_ZEROCOHORT", "amount": 49900,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                      "cohort_id": "0"},
        }}}},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_ZEROCOHORT").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0


def test_sweeper_oversized_cohort_id_fulfills_normally(db, student_user, course):
    """Same oversized-id scenario via the sweeper's orphan-capture path."""
    _course_with(db, course, price=999, sale=499)

    sweep_client = FakeRzpClient(
        orders=[{"id": "order_HUGESWEEP", "status": "paid", "amount": 49900,
                "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                          "cohort_id": "1000000000000000000000000000000"}}],
        payments_by_order={"order_HUGESWEEP": [
            {"id": "pay_HUGESWEEP", "status": "captured", "amount": 49900,
             "currency": "INR"},
        ]},
    )
    n = reconcile_gateway_orders(db, sweep_client)
    assert n == 1

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_HUGESWEEP").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 499.0


def test_sweeper_negative_and_zero_cohort_id_fulfill_normally(db, student_user, course):
    """Same negative/zero-id scenario via the sweeper — two captures, two
    different bad cohort_id notes, both fulfil normally."""
    _course_with(db, course, price=999, sale=499)

    sweep_client = FakeRzpClient(
        orders=[
            {"id": "order_NEGSWEEP", "status": "paid", "amount": 49900,
             "notes": {"course_id": str(course.id), "user_id": str(student_user.id),
                       "cohort_id": "-5"}},
        ],
        payments_by_order={"order_NEGSWEEP": [
            {"id": "pay_NEGSWEEP", "status": "captured", "amount": 49900,
             "currency": "INR"},
        ]},
    )
    n = reconcile_gateway_orders(db, sweep_client)
    assert n == 1

    payment_row = db.query(Payment).filter_by(gateway_payment_id="pay_NEGSWEEP").one()
    order_row = db.query(Order).filter_by(id=payment_row.order_id).one()
    assert float(order_row.subtotal_amount) == 499.0
    assert float(order_row.discount_amount) == 0.0
    assert float(order_row.total_amount) == 499.0


def test_resolve_expected_purchase_none_notes_does_not_raise(db, course):
    """resolve_expected_purchase(db, course, None) must not raise —
    honors the documented "never raises on malformed notes" contract.
    Falls back to the effective course price with no cohort/coupon."""
    _course_with(db, course, price=999, sale=499)

    result = resolve_expected_purchase(db, course, None)

    assert result.expected_price == 499.0
    assert result.subtotal_price == 499.0
    assert result.cohort is None
    assert result.referral_code_id is None
    assert result.is_coupon is False
