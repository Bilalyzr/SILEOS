"""Refunds (docs/superpowers/specs/2026-09-04-money-ops-design.md §1).

Task 2: refund_service unit tests (gateway monkeypatched at
refund_service._gateway_refund). Task 3 appends the admin endpoint, webhook
convergence and payment-health tests.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderItem, OrderStatus, Payment, PaymentStatus
from app.services import refund_service
from app.services.refund_service import RefundError, refund_order, to_paise


# ----- factories -------------------------------------------------------------

def _second_course(db, title="Course B", price=300.0):
    from app.models.course import Course
    from app.models.user import User
    author = db.query(User).filter(User.user_email == "instructor1@example.com").first()
    c = Course(post_author=author.id, post_title=title,
               course_price_type="paid", course_price=price)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _paid_order(db, user, courses, *, pay_id="pay_RF1", amount=500.0,
                method="razorpay", bundle_id=None):
    """A COMPLETED order + COMPLETED gateway payment + one enrolled row per
    course carrying THIS order's id (exactly what fulfillment writes)."""
    order = Order(user_id=user.id, order_key=f"RZP_{pay_id}", bundle_id=bundle_id,
                  order_status=OrderStatus.COMPLETED, total_amount=amount,
                  payment_method=method, date_paid=datetime.now(timezone.utc))
    db.add(order)
    db.flush()
    for c in courses:
        db.add(OrderItem(order_id=order.id, course_id=c.id, order_item_name=c.post_title,
                         total=amount / len(courses)))
        db.add(Enrollment(user_id=user.id, course_id=c.id, order_id=order.id,
                          enrollment_status="enrolled",
                          enrollment_source="bundle" if bundle_id else None))
    payment = Payment(user_id=user.id, order_id=order.id, payment_method=method,
                      gateway_payment_id=pay_id, gateway_order_id=f"order_{pay_id}",
                      amount=amount, payment_status=PaymentStatus.COMPLETED,
                      processed_date=datetime.now(timezone.utc))
    db.add(payment)
    db.commit()
    db.refresh(order)
    db.refresh(payment)
    return order, payment


class FakeGateway:
    """Stands in for refund_service._gateway_refund. Records calls; returns
    the dict shape PaymentService.process_refund produces."""
    calls: list = []
    fail = False

    @classmethod
    def reset(cls, fail=False):
        cls.calls = []
        cls.fail = fail

    @classmethod
    def __call__(cls, gateway_payment_id, amount_paise, reason):  # pragma: no cover
        raise NotImplementedError


def _fake_gateway(gateway_payment_id, amount_paise, reason):
    FakeGateway.calls.append((gateway_payment_id, amount_paise, reason))
    if FakeGateway.fail:
        return {"status": "failed", "error": "BAD_REQUEST_ERROR: insufficient balance"}
    return {"status": "processed", "refund_id": f"rfnd_{len(FakeGateway.calls)}",
            "amount": amount_paise, "currency": "INR"}


@pytest.fixture()
def gateway(monkeypatch):
    FakeGateway.reset()
    monkeypatch.setattr(refund_service, "_gateway_refund", _fake_gateway)
    return FakeGateway


REASON = "Student requested a refund within the cooling-off window"


# ============================================================================
# Task 2: service
# ============================================================================


class TestToPaise:
    def test_rounding_and_floor(self):
        assert to_paise(500) == 50000
        assert to_paise(499.995) == 50000
        assert to_paise(0.5) == 100          # Razorpay minimum is 100 paise
        assert to_paise("123.45") == 12345


class TestRefundOrderService:
    def test_happy_path_course_order(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        result = refund_order(db, order.id, reason=REASON, actor_id=99)

        assert gateway.calls == [("pay_RF1", 50000, REASON)]  # amount from Payment, in paise
        db.refresh(order)
        db.refresh(payment)
        assert order.order_status == OrderStatus.REFUNDED
        assert payment.payment_status == PaymentStatus.REFUNDED
        assert payment.refund_status == "processed"
        assert payment.refund_reason == REASON
        assert payment.refund_requested_by == 99
        assert payment.refund_requested_at is not None
        assert payment.refund_processed_at is not None
        assert payment.gateway_refund_id == "rfnd_1"
        row = db.query(Enrollment).filter_by(order_id=order.id).one()
        assert row.enrollment_status == "cancelled"
        assert result["revoked_course_ids"] == [course.id]
        assert result["gateway_refund_id"] == "rfnd_1"
        assert result["amount"] == 500.0

    def test_already_refunded_409(self, db, gateway, student_user, course):
        order, _ = _paid_order(db, student_user, [course])
        refund_order(db, order.id, reason=REASON, actor_id=1)
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 409
        assert len(gateway.calls) == 1  # no second gateway call

    def test_in_flight_409(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        payment.refund_status = "requested"
        # a refund issued just now is genuinely in flight (a STALE 'requested'
        # is crash debris and takes the retry path — see TestI1)
        payment.refund_requested_at = datetime.now(timezone.utc)
        db.commit()
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 409
        assert gateway.calls == []

    def test_no_captured_gateway_payment_400(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course], pay_id="", method="bank_transfer")
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 400
        assert "offline" in exc.value.detail.lower() or "gateway" in exc.value.detail.lower()
        assert gateway.calls == []

    def test_pending_payment_is_not_refundable(self, db, gateway, student_user, course):
        """A gateway payment that never captured (still PENDING) is not
        refundable, and nothing is written to it."""
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_PEND")
        payment.payment_status = PaymentStatus.PENDING
        db.commit()
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 400
        assert gateway.calls == []
        db.refresh(order)
        db.refresh(payment)
        assert payment.refund_status is None
        assert payment.refund_reason is None
        assert payment.refund_requested_by is None
        assert payment.payment_status == PaymentStatus.PENDING
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"

    def test_mock_payment_is_not_refundable(self, db, gateway, student_user, course):
        """Legacy mock carts carry a gateway id but never moved money."""
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_MOCK", method="mock")
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 400
        assert gateway.calls == []
        db.refresh(payment)
        assert payment.refund_status is None

    def test_unknown_order_404(self, db, gateway):
        with pytest.raises(RefundError) as exc:
            refund_order(db, 424242, reason=REASON, actor_id=1)
        assert exc.value.status_code == 404

    def test_gateway_failure_marks_failed_and_leaves_access(self, db, gateway, student_user, course):
        gateway.reset(fail=True)
        order, payment = _paid_order(db, student_user, [course])
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=7)
        assert exc.value.status_code == 502
        db.refresh(order)
        db.refresh(payment)
        # intent was persisted BEFORE the call, then flipped to failed
        assert payment.refund_status == "failed"
        assert "insufficient balance" in (payment.refund_error or "")
        assert payment.refund_requested_by == 7
        assert payment.payment_status == PaymentStatus.COMPLETED
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"
        assert len(gateway.calls) == 1  # called exactly once, never retried in-band

    def test_failed_refund_can_be_retried(self, db, gateway, monkeypatch, student_user, course):
        """Task 3 tightened this path: a retry first asks the gateway which
        refunds already exist (hazard (c)). With none, it re-issues normally.
        refund_error then carries the audit note saying which path was taken —
        see TestRetryAfterFailedDoesNotDoubleRefund for the full matrix."""
        monkeypatch.setattr(refund_service, "_gateway_list_refunds", lambda pid: [])
        gateway.reset(fail=True)
        order, payment = _paid_order(db, student_user, [course])
        with pytest.raises(RefundError):
            refund_order(db, order.id, reason=REASON, actor_id=7)
        gateway.reset(fail=False)
        refund_order(db, order.id, reason=REASON, actor_id=7)
        db.refresh(payment)
        assert payment.refund_status == "processed"
        assert payment.payment_status == PaymentStatus.REFUNDED
        assert "issued a new gateway refund" in (payment.refund_error or "")

    def test_bundle_order_revokes_all_its_rows_and_nothing_else(self, db, gateway, student_user, course):
        from app.models.bundle import Bundle
        c2 = _second_course(db)
        c3 = _second_course(db, title="Course C (bought separately)")
        b = Bundle(name="Pack", slug="pack-rf", bundle_price=700.0)
        db.add(b)
        db.commit()
        bundle_order, _ = _paid_order(db, student_user, [course, c2], pay_id="pay_BND",
                                      amount=700.0, method="razorpay_bundle", bundle_id=b.id)
        other_order, _ = _paid_order(db, student_user, [c3], pay_id="pay_OTHER", amount=300.0)
        # a membership row (order_id NULL) and a company row (different order) must survive
        db.add(Enrollment(user_id=student_user.id, course_id=c3.id, enrollment_status="enrolled",
                          enrollment_source="membership", order_id=None))
        db.commit()

        result = refund_order(db, bundle_order.id, reason=REASON, actor_id=1)

        assert sorted(result["revoked_course_ids"]) == sorted([course.id, c2.id])
        statuses = {(e.course_id, e.order_id): e.enrollment_status
                    for e in db.query(Enrollment).filter_by(user_id=student_user.id).all()}
        assert statuses[(course.id, bundle_order.id)] == "cancelled"
        assert statuses[(c2.id, bundle_order.id)] == "cancelled"
        assert statuses[(c3.id, other_order.id)] == "enrolled"   # different order_id untouched
        assert statuses[(c3.id, None)] == "enrolled"             # membership row untouched
        db.refresh(other_order)
        assert other_order.order_status == OrderStatus.COMPLETED

    def test_membership_and_company_rows_for_same_course_are_untouched(
            self, db, gateway, student_user, course):
        """The refunded order's own row is cancelled; a membership row (order_id
        NULL) and a company-seat row (another order) for the SAME user and the
        SAME course keep their access."""
        order, _ = _paid_order(db, student_user, [course])
        company_order, _ = _paid_order(db, student_user, [], pay_id="pay_CO", amount=1000.0)
        company_row = Enrollment(user_id=student_user.id, course_id=course.id,
                                 order_id=company_order.id, enrollment_source="company",
                                 enrollment_status="enrolled")
        membership_row = Enrollment(user_id=student_user.id, course_id=course.id,
                                    order_id=None, enrollment_source="membership",
                                    enrollment_status="enrolled")
        db.add_all([company_row, membership_row])
        db.commit()

        result = refund_order(db, order.id, reason=REASON, actor_id=1)

        assert result["revoked_course_ids"] == [course.id]
        db.refresh(company_row)
        db.refresh(membership_row)
        assert company_row.enrollment_status == "enrolled"
        assert membership_row.enrollment_status == "enrolled"
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "cancelled"
        db.refresh(company_order)
        assert company_order.order_status == OrderStatus.COMPLETED

    def test_apply_refund_effects_is_idempotent(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        first = refund_service.apply_refund_effects(db, payment, gateway_refund_id="rfnd_X")
        db.commit()
        second = refund_service.apply_refund_effects(db, payment, gateway_refund_id="rfnd_Y")
        db.commit()
        assert first == ([course.id], [])          # (revoked, released)
        assert second == ([], [])                  # nothing left to settle
        assert payment.gateway_refund_id == "rfnd_X"  # first id wins, never overwritten


class TestAmountDerivation:
    """The gateway must receive the captured amount on the Payment, in paise —
    never a request-supplied figure."""

    def test_fractional_rupees_reach_the_gateway_as_paise(self, db, gateway, student_user, course):
        order, _ = _paid_order(db, student_user, [course], pay_id="pay_499", amount=499.99)
        refund_order(db, order.id, reason=REASON, actor_id=1)
        assert gateway.calls == [("pay_499", 49999, REASON)]

    def test_sub_rupee_capture_is_clamped_to_the_gateway_minimum(
            self, db, gateway, student_user, course):
        order, _ = _paid_order(db, student_user, [course], pay_id="pay_050", amount=0.50)
        refund_order(db, order.id, reason=REASON, actor_id=1)
        assert gateway.calls == [("pay_050", 100, REASON)]


class TestIntentIsPersistedBeforeTheGatewayCall:
    def test_intent_row_is_committed_when_the_gateway_is_called(
            self, db, monkeypatch, student_user, course, TestingSessionLocal):
        """Proven from the gateway's own vantage point: a stub that reads the DB
        when called must already see refund_status='requested' with the
        reason/actor, and the session must hold NO pending (uncommitted) changes
        for that row — i.e. the intent was written AND committed before any money
        moved, so a crash mid-gateway leaves a durable record instead of a silent
        money movement.

        (The test engine is a StaticPool in-memory SQLite — one shared
        connection — so a second Session would see flushed-but-uncommitted rows
        too. The `db.dirty` / `db.new` assertion is what actually distinguishes
        "committed" from "merely flushed".)
        """
        order, payment = _paid_order(db, student_user, [course])
        seen = {}

        def _inspecting_gateway(gateway_payment_id, amount_paise, reason):
            other = TestingSessionLocal()
            try:
                row = other.query(Payment).filter(Payment.id == payment.id).one()
                seen["refund_status"] = row.refund_status
                seen["refund_reason"] = row.refund_reason
                seen["refund_requested_by"] = row.refund_requested_by
                seen["refund_requested_at_set"] = row.refund_requested_at is not None
                seen["payment_status"] = row.payment_status
                seen["enrollment_status"] = other.query(Enrollment).filter(
                    Enrollment.order_id == order.id).one().enrollment_status
            finally:
                other.close()
            # nothing left uncommitted in the caller's session at gateway time
            seen["pending_changes"] = bool(db.dirty) or bool(db.new) or bool(db.deleted)
            return {"status": "processed", "refund_id": "rfnd_ORDER", "amount": amount_paise,
                    "currency": "INR"}

        monkeypatch.setattr(refund_service, "_gateway_refund", _inspecting_gateway)
        refund_order(db, order.id, reason=REASON, actor_id=42)

        assert seen["refund_status"] == "requested"
        assert seen["refund_reason"] == REASON
        assert seen["refund_requested_by"] == 42
        assert seen["refund_requested_at_set"] is True
        assert seen["pending_changes"] is False   # committed, not merely flushed
        # ...and the effects had NOT yet been applied at gateway-call time
        assert seen["payment_status"] == PaymentStatus.COMPLETED
        assert seen["enrollment_status"] == "enrolled"


# ============================================================================
# Task 3: admin endpoint + webhook convergence + payment-health + /orders/me
# ============================================================================

import inspect  # noqa: E402

from app.models.webhook_event import WebhookEvent, WebhookEventStatus  # noqa: E402
from app.services.webhook_processor import process_webhook_event  # noqa: E402


def _refund_event(db, pay_id, refund_id="rfnd_WH1", event_id="evt_rf1"):
    ev = WebhookEvent(
        event_id=event_id, event_type="refund.processed",
        payload={"payload": {"refund": {"entity": {
            "id": refund_id, "payment_id": pay_id, "amount": 50000, "currency": "INR",
            "status": "processed",
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()
    return ev


class FakeRefundLister:
    """Stands in for refund_service._gateway_list_refunds (hazard (c)):
    what the gateway says already exists for a payment."""
    calls: list = []
    items: list = []
    raises = False

    @classmethod
    def reset(cls, items=None, raises=False):
        cls.calls = []
        cls.items = list(items or [])
        cls.raises = raises


def _fake_list_refunds(gateway_payment_id):
    FakeRefundLister.calls.append(gateway_payment_id)
    if FakeRefundLister.raises:
        raise RuntimeError("gateway list unavailable")
    return list(FakeRefundLister.items)


@pytest.fixture()
def refund_lister(monkeypatch):
    FakeRefundLister.reset()
    monkeypatch.setattr(refund_service, "_gateway_list_refunds", _fake_list_refunds)
    return FakeRefundLister


class TestAdminRefundEndpoint:
    def test_happy_path_returns_refund_id_and_revoked_courses(self, client, db, gateway, as_user,
                                                              student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        as_user(student_user)  # require_admin overridden by fixture
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["gateway_refund_id"] == "rfnd_1"
        assert body["revoked_course_ids"] == [course.id]
        assert body["amount"] == 500.0
        assert gateway.calls == [("pay_RF1", 50000, REASON)]  # exactly once, paise from Payment
        db.refresh(order)
        db.refresh(payment)
        assert order.order_status == OrderStatus.REFUNDED
        assert payment.payment_status == PaymentStatus.REFUNDED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "cancelled"

    def test_endpoint_is_a_plain_def_not_async(self):
        """BINDING: refund_service._gateway_refund drives an `async def` with
        asyncio.run, which explodes inside a running event loop. FastAPI runs
        sync endpoints in a threadpool - so this endpoint must stay `def`."""
        from app.routers.admin import refund_order_endpoint
        assert inspect.iscoroutinefunction(refund_order_endpoint) is False

    def test_short_reason_422(self, client, db, gateway, as_user, student_user, course):
        order, _ = _paid_order(db, student_user, [course])
        as_user(student_user)
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": "too short"})
        assert r.status_code == 422
        assert gateway.calls == []

    def test_amount_in_the_request_body_is_ignored(self, client, db, gateway, as_user,
                                                   student_user, course):
        """The amount NEVER comes from the request (spec section 1.2)."""
        order, _ = _paid_order(db, student_user, [course])
        as_user(student_user)
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund",
                        json={"reason": REASON, "amount": 1, "amount_paise": 1})
        assert r.status_code == 200, r.text
        assert gateway.calls == [("pay_RF1", 50000, REASON)]
        assert r.json()["amount"] == 500.0

    def test_already_refunded_409(self, client, db, gateway, as_user, student_user, course):
        order, _ = _paid_order(db, student_user, [course])
        as_user(student_user)
        assert client.post(f"/api/v1/admin/orders/{order.id}/refund",
                           json={"reason": REASON}).status_code == 200
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON})
        assert r.status_code == 409
        assert len(gateway.calls) == 1

    def test_in_flight_409(self, client, db, gateway, as_user, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        payment.refund_status = "requested"
        payment.refund_requested_at = datetime.now(timezone.utc)
        db.commit()
        as_user(student_user)
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON})
        assert r.status_code == 409
        assert gateway.calls == []

    def test_unknown_order_404(self, client, db, gateway, as_user, student_user):
        as_user(student_user)
        r = client.post("/api/v1/admin/orders/424242/refund", json={"reason": REASON})
        assert r.status_code == 404

    def test_offline_order_400(self, client, db, gateway, as_user, student_user, course):
        order, _ = _paid_order(db, student_user, [course], pay_id="", method="bank_transfer")
        as_user(student_user)
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON})
        assert r.status_code == 400
        assert "offline" in r.json()["detail"].lower()   # guidance, not a bare failure
        assert gateway.calls == []
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"

    def test_gateway_failure_502_leaves_access(self, client, db, gateway, as_user,
                                               student_user, course):
        gateway.reset(fail=True)
        order, payment = _paid_order(db, student_user, [course])
        as_user(student_user)
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON})
        assert r.status_code == 502
        db.refresh(order)
        db.refresh(payment)
        assert payment.refund_status == "failed"          # intent persisted
        assert "insufficient balance" in (payment.refund_error or "")
        assert payment.payment_status == PaymentStatus.COMPLETED
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"

    def test_student_forbidden(self, client, db, gateway, make_user, auth_headers,
                               student_user, course):
        order, _ = _paid_order(db, student_user, [course])
        stu = make_user(role="student")
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON},
                        headers=auth_headers(stu.user_email, stu._test_password))
        assert r.status_code == 403
        assert gateway.calls == []
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"

    def test_orders_list_exposes_refund_fields(self, client, db, gateway, as_user,
                                               student_user, course):
        order, _ = _paid_order(db, student_user, [course])
        as_user(student_user)
        client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON})
        r = client.get("/api/v1/admin/orders")
        assert r.status_code == 200
        row = next(o for o in r.json() if o["id"] == order.id)
        assert row["status"] == "refunded"
        assert row["refund_status"] == "processed"
        assert row["refund_reason"] == REASON
        assert row["gateway_refund_id"] == "rfnd_1"
        assert row["refund_processed_at"] is not None

    def test_orders_list_shows_the_payment_that_carries_the_refund(
            self, client, db, gateway, as_user, student_user, course):
        """An order with several Payment rows must not show blank refund
        columns next to a REFUNDED status because an unrefunded sibling row
        happened to be picked.

        The refunded row here is deliberately the OLDER one AND a newer
        sibling exists, so neither "newest wins" nor "first row wins" would
        produce this result — only preferring the row that carries the refund
        does.
        """
        order, refunded_row = _paid_order(db, student_user, [course])
        as_user(student_user)
        assert client.post(f"/api/v1/admin/orders/{order.id}/refund",
                           json={"reason": REASON}).status_code == 200

        # a later, unrefunded payment row on the same order (a retried
        # checkout that landed after the refund)
        sibling = Payment(user_id=student_user.id, order_id=order.id,
                          payment_method="razorpay", gateway_payment_id="pay_SIBLING",
                          amount=500.0, payment_status=PaymentStatus.COMPLETED,
                          processed_date=datetime.now(timezone.utc))
        db.add(sibling)
        db.commit()
        assert sibling.id > refunded_row.id          # the sibling IS the newest

        row = next(o for o in client.get("/api/v1/admin/orders").json()
                   if o["id"] == order.id)
        assert row["status"] == "refunded"
        assert row["refund_status"] == "processed"   # not the blank sibling row
        assert row["gateway_refund_id"] == "rfnd_1"
        assert row["refund_reason"] == REASON


class TestRetryAfterFailedDoesNotDoubleRefund:
    """HAZARD (c): a 'failed' intent may mean the gateway actually processed
    the refund and only the response was lost. Before re-issuing, the service
    asks the gateway what refunds already exist for the payment and ADOPTS a
    matching one instead of creating a second."""

    def _fail_once(self, db, gateway, student_user, course):
        gateway.reset(fail=True)
        order, payment = _paid_order(db, student_user, [course])
        with pytest.raises(RefundError):
            refund_order(db, order.id, reason=REASON, actor_id=7)
        gateway.reset(fail=False)
        return order, payment

    def test_existing_matching_refund_is_adopted_not_reissued(
            self, db, gateway, refund_lister, student_user, course):
        order, payment = self._fail_once(db, gateway, student_user, course)
        refund_lister.reset(items=[{"id": "rfnd_GATEWAY", "amount": 50000,
                                    "status": "processed"}])

        result = refund_order(db, order.id, reason=REASON, actor_id=7)

        assert refund_lister.calls == ["pay_RF1"]
        assert gateway.calls == []                       # NOT re-issued
        db.refresh(payment)
        db.refresh(order)
        assert payment.gateway_refund_id == "rfnd_GATEWAY"
        assert payment.refund_status == "processed"
        assert payment.payment_status == PaymentStatus.REFUNDED
        assert order.order_status == OrderStatus.REFUNDED
        assert result["revoked_course_ids"] == [course.id]
        assert result["adopted_existing_refund"] is True
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "cancelled"
        # audit trail: which path was taken is persisted
        assert "adopted" in (payment.refund_error or "").lower()

    def test_no_existing_refund_reissues_and_succeeds(
            self, db, gateway, refund_lister, student_user, course):
        order, payment = self._fail_once(db, gateway, student_user, course)
        refund_lister.reset(items=[])

        result = refund_order(db, order.id, reason=REASON, actor_id=7)

        assert refund_lister.calls == ["pay_RF1"]
        assert gateway.calls == [("pay_RF1", 50000, REASON)]   # re-issued exactly once
        db.refresh(payment)
        assert payment.gateway_refund_id == "rfnd_1"
        assert payment.refund_status == "processed"
        assert result["adopted_existing_refund"] is False

    def test_amount_mismatch_is_not_adopted(self, db, gateway, refund_lister,
                                            student_user, course):
        """A partial refund someone made in the dashboard is NOT our full
        refund - re-issue rather than silently under-refunding."""
        order, payment = self._fail_once(db, gateway, student_user, course)
        refund_lister.reset(items=[{"id": "rfnd_PARTIAL", "amount": 10000,
                                    "status": "processed"}])

        refund_order(db, order.id, reason=REASON, actor_id=7)

        assert gateway.calls == [("pay_RF1", 50000, REASON)]
        db.refresh(payment)
        assert payment.gateway_refund_id == "rfnd_1"

    def test_failed_gateway_side_refund_is_not_adopted(self, db, gateway, refund_lister,
                                                       student_user, course):
        order, payment = self._fail_once(db, gateway, student_user, course)
        refund_lister.reset(items=[{"id": "rfnd_DEAD", "amount": 50000, "status": "failed"}])

        refund_order(db, order.id, reason=REASON, actor_id=7)

        assert gateway.calls == [("pay_RF1", 50000, REASON)]
        db.refresh(payment)
        assert payment.gateway_refund_id == "rfnd_1"

    def test_lookup_failure_blocks_the_retry_rather_than_risking_a_double_refund(
            self, db, gateway, refund_lister, student_user, course):
        order, payment = self._fail_once(db, gateway, student_user, course)
        refund_lister.reset(raises=True)

        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=7)

        assert exc.value.status_code == 502
        assert gateway.calls == []                       # never blindly re-issued
        db.refresh(payment)
        db.refresh(order)
        assert payment.refund_status == "failed"
        assert payment.payment_status == PaymentStatus.COMPLETED
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"

    def test_first_attempt_never_lists_refunds(self, db, gateway, refund_lister,
                                               student_user, course):
        """No prior intent -> nothing could have been refunded behind our back;
        the extra gateway round-trip is only paid on a retry."""
        order, _ = _paid_order(db, student_user, [course])
        refund_order(db, order.id, reason=REASON, actor_id=1)
        assert refund_lister.calls == []
        assert gateway.calls == [("pay_RF1", 50000, REASON)]


class TestWebhookConvergence:
    def test_admin_initiated_converges_and_is_idempotent(self, db, student_user, course):
        """Intent persisted (crash before local effects) -> the webhook
        completes the refund: order REFUNDED, enrollment cancelled, refund id
        stored. A second event changes nothing."""
        order, payment = _paid_order(db, student_user, [course])
        payment.refund_status = "requested"
        payment.refund_reason = REASON
        db.commit()

        ev = _refund_event(db, "pay_RF1")
        process_webhook_event(db, ev)
        assert ev.status == WebhookEventStatus.PROCESSED
        db.refresh(order)
        db.refresh(payment)
        assert order.order_status == OrderStatus.REFUNDED
        assert payment.payment_status == PaymentStatus.REFUNDED
        assert payment.refund_status == "processed"
        assert payment.gateway_refund_id == "rfnd_WH1"
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "cancelled"

        ev2 = _refund_event(db, "pay_RF1", refund_id="rfnd_DUP", event_id="evt_rf2")
        process_webhook_event(db, ev2)
        assert ev2.status == WebhookEventStatus.PROCESSED
        db.refresh(payment)
        assert payment.gateway_refund_id == "rfnd_WH1"      # unchanged
        assert db.query(Enrollment).filter_by(order_id=order.id).count() == 1

    def test_after_endpoint_the_webhook_is_a_noop(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        refund_order(db, order.id, reason=REASON, actor_id=1)
        ev = _refund_event(db, "pay_RF1", refund_id="rfnd_LATE")
        process_webhook_event(db, ev)
        db.refresh(payment)
        assert payment.gateway_refund_id == "rfnd_1"         # endpoint's id kept
        assert payment.refund_status == "processed"
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "cancelled"

    def test_external_refund_keeps_access_and_is_idempotent(self, db, student_user, course):
        """Dashboard-initiated refund (no intent row): today's behavior -
        payment REFUNDED, order + enrollment untouched for a human decision."""
        order, payment = _paid_order(db, student_user, [course])
        ev = _refund_event(db, "pay_RF1")
        process_webhook_event(db, ev)
        db.refresh(order)
        db.refresh(payment)
        assert payment.payment_status == PaymentStatus.REFUNDED
        assert payment.refund_status is None
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"
        ev2 = _refund_event(db, "pay_RF1", event_id="evt_rf3")
        process_webhook_event(db, ev2)
        assert ev2.status == WebhookEventStatus.PROCESSED
        db.refresh(order)
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"

    def test_external_refund_shows_up_in_payment_health(self, client, db, as_user,
                                                        student_user, course):
        """The human-decision queue: an external refund whose access is still
        live must appear under refunded_with_active_enrollment."""
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_EXT")
        process_webhook_event(db, _refund_event(db, "pay_EXT"))
        as_user(student_user)
        data = client.get("/api/v1/admin/payment-health").json()
        assert any(i["gateway_payment_id"] == "pay_EXT"
                   for i in data["refunded_with_active_enrollment"]["items"])

    def test_failed_intent_does_not_converge(self, db, gateway, student_user, course):
        """A payment whose intent is 'failed' is not admin-initiated-in-flight;
        a refund.processed for it is treated as external (access left alone)."""
        gateway.reset(fail=True)
        order, payment = _paid_order(db, student_user, [course])
        with pytest.raises(RefundError):
            refund_order(db, order.id, reason=REASON, actor_id=1)
        process_webhook_event(db, _refund_event(db, "pay_RF1"))
        db.refresh(order)
        db.refresh(payment)
        assert payment.payment_status == PaymentStatus.REFUNDED
        assert payment.refund_status == "failed"
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"

    def test_unknown_payment_is_processed_not_failed(self, db):
        ev = _refund_event(db, "pay_NOBODY")
        process_webhook_event(db, ev)
        assert ev.status == WebhookEventStatus.PROCESSED


class TestPaymentHealthFailedRefunds:
    def test_failed_intents_are_listed(self, client, db, gateway, as_user, student_user, course):
        gateway.reset(fail=True)
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_H_FAIL")
        with pytest.raises(RefundError):
            refund_order(db, order.id, reason=REASON, actor_id=student_user.id)
        as_user(student_user)
        data = client.get("/api/v1/admin/payment-health").json()
        assert data["refunds"]["failed"]["count"] == 1
        item = data["refunds"]["failed"]["items"][0]
        assert item["order_id"] == order.id
        assert item["payment_id"] == payment.id
        assert item["gateway_payment_id"] == "pay_H_FAIL"
        assert "insufficient balance" in item["error"]
        assert item["requested_at"] is not None
        assert item["requested_by"] == student_user.id

    def test_successful_refund_is_not_listed_anywhere_needing_a_human(
            self, client, db, gateway, as_user, student_user, course):
        order, _ = _paid_order(db, student_user, [course], pay_id="pay_H_OK")
        refund_order(db, order.id, reason=REASON, actor_id=1)
        as_user(student_user)
        data = client.get("/api/v1/admin/payment-health").json()
        assert data["refunds"]["failed"]["count"] == 0
        assert all(i["gateway_payment_id"] != "pay_H_OK"
                   for i in data["refunded_with_active_enrollment"]["items"])


class TestMyOrders:
    def test_student_sees_own_orders_with_status_and_items(self, client, db, gateway, as_user,
                                                           student_user, make_user, course):
        order, _ = _paid_order(db, student_user, [course])
        other = make_user(role="student")
        _paid_order(db, other, [course], pay_id="pay_OTHERS")
        refund_order(db, order.id, reason=REASON, actor_id=1)
        as_user(student_user)
        r = client.get("/api/v1/orders/me")
        assert r.status_code == 200, r.text
        rows = r.json()
        assert [o["id"] for o in rows] == [order.id]         # only own orders
        row = rows[0]
        assert row["status"] == "refunded"
        assert row["total_amount"] == 500.0
        assert row["items"] == [{"course_id": course.id, "title": course.post_title,
                                 "total": 500.0}]
        assert row["refunded_at"] is not None
        assert row["order_key"] == order.order_key
        assert row["currency"] == "INR"
        assert "refund_reason" not in row                      # admin-internal
        assert "billing_email" not in row

    def test_non_refunded_order_has_no_refunded_at(self, client, db, as_user,
                                                   student_user, course):
        order, _ = _paid_order(db, student_user, [course])
        as_user(student_user)
        row = client.get("/api/v1/orders/me").json()[0]
        assert row["status"] == "completed"
        assert row["refunded_at"] is None
        assert row["discount_amount"] == 0.0
        assert row["payment_method"] == "razorpay"

    def test_rows_are_explicit_dicts_not_orm_rows(self, client, db, as_user,
                                                  student_user, course):
        """A raw ORM dump would leak every column (billing_*, transaction_id,
        ip_address...). The shape is a closed allow-list."""
        _paid_order(db, student_user, [course])
        as_user(student_user)
        row = client.get("/api/v1/orders/me").json()[0]
        assert set(row) == {
            "id", "order_key", "status", "total_amount", "discount_amount",
            "currency", "payment_method", "created_at", "refunded_at", "items",
        }


# ============================================================================
# Task 3 add-ons: controller rulings from the Task 2 review (C1, C2, I1-I4,
# M2, M3). Each is a way a refund could move money or destroy access wrongly.
# ============================================================================

from app.models.membership import Membership, MembershipPlan, MembershipStatus  # noqa: E402


def _plan(db, name="Pro", all_access=True):
    p = MembershipPlan(name=name, razorpay_plan_id=f"plan_rzp_{name.lower()}",
                       price=999.0, period="monthly", interval=1,
                       all_access=all_access, is_active=True)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _membership(db, user, plan, status=MembershipStatus.ACTIVE):
    m = Membership(user_id=user.id, plan_id=plan.id, status=status,
                   razorpay_subscription_id=f"sub_{user.id}_{plan.id}")
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _rescued_row(db, user, course, order, *, source, membership_id=None):
    """The EXACT shape grant_purchased_course / fulfill_course_purchase leave
    behind when a purchase RESCUES a pre-existing membership/company row: ONE
    row, source unchanged, order_id now stamped with the purchase's order."""
    row = db.query(Enrollment).filter(
        Enrollment.user_id == user.id, Enrollment.course_id == course.id).one()
    row.enrollment_source = source
    row.membership_id = membership_id
    row.order_id = order.id
    db.commit()
    db.refresh(row)
    return row


class TestC1RescuedRowsAreNeverCancelled:
    """C1 (CRITICAL): fulfillment RESCUES an existing membership/company
    enrollment in place and stamps this order's id on it — one row, source
    still 'membership'. Cancelling it on refund would destroy access the buyer
    still pays for, UNRECOVERABLY (membership_access only re-grants rows that
    are 'suspended' AND have no order_id). The refund must UN-STAMP instead."""

    def test_membership_rescue_row_is_unstamped_and_kept_enrolled(
            self, db, gateway, student_user, course):
        plan = _plan(db)
        m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
        order, _ = _paid_order(db, student_user, [course])
        row = _rescued_row(db, student_user, course, order,
                           source="membership", membership_id=m.id)

        result = refund_order(db, order.id, reason=REASON, actor_id=1)

        db.refresh(row)
        assert row.enrollment_source == "membership"   # never rewritten
        assert row.order_id is None                    # un-stamped, not cancelled
        assert row.enrollment_status == "enrolled"     # membership is ACTIVE
        assert row.membership_id == m.id
        assert result["revoked_course_ids"] == []      # nothing was revoked
        assert course.id in result["released_course_ids"]

    def test_membership_rescue_row_is_suspended_when_the_membership_lapsed(
            self, db, gateway, student_user, course):
        """Un-stamping restores the row to the state the membership's own
        lifecycle would have left it in — a lapsed membership means suspended,
        and (order_id now NULL) membership_access can rescue it again later."""
        plan = _plan(db)
        m = _membership(db, student_user, plan, status=MembershipStatus.SUSPENDED)
        order, _ = _paid_order(db, student_user, [course])
        row = _rescued_row(db, student_user, course, order,
                           source="membership", membership_id=m.id)

        refund_order(db, order.id, reason=REASON, actor_id=1)

        db.refresh(row)
        assert row.order_id is None
        assert row.enrollment_status == "suspended"
        assert row.enrollment_source == "membership"

    def test_grace_membership_counts_as_active(self, db, gateway, student_user, course):
        plan = _plan(db)
        m = _membership(db, student_user, plan, status=MembershipStatus.GRACE)
        order, _ = _paid_order(db, student_user, [course])
        row = _rescued_row(db, student_user, course, order,
                           source="membership", membership_id=m.id)
        refund_order(db, order.id, reason=REASON, actor_id=1)
        db.refresh(row)
        assert row.enrollment_status == "enrolled"
        assert row.order_id is None

    def test_company_seat_rescue_row_is_unstamped_not_cancelled(
            self, db, gateway, student_user, course):
        """Same shape via company_billing's assign_seat (source 'company').
        The seat is the company's; a refund of the student's own purchase must
        not take it away."""
        order, _ = _paid_order(db, student_user, [course])
        row = _rescued_row(db, student_user, course, order, source="company")

        result = refund_order(db, order.id, reason=REASON, actor_id=1)

        db.refresh(row)
        assert row.enrollment_source == "company"
        assert row.order_id is None
        assert row.enrollment_status == "enrolled"
        assert result["revoked_course_ids"] == []

    def test_a_row_this_order_actually_created_is_still_cancelled(
            self, db, gateway, student_user, course):
        """The regression guard: un-stamping must not become a blanket
        'never revoke'. A plain purchase row (source NULL) is this order's own
        grant and MUST be cancelled."""
        order, _ = _paid_order(db, student_user, [course])
        row = db.query(Enrollment).filter_by(order_id=order.id).one()
        assert row.enrollment_source is None          # what fulfillment writes

        result = refund_order(db, order.id, reason=REASON, actor_id=1)

        db.refresh(row)
        assert row.enrollment_status == "cancelled"
        assert row.order_id == order.id               # kept, for the audit trail
        assert result["revoked_course_ids"] == [course.id]
        assert result["released_course_ids"] == []

    def test_bundle_rows_are_still_cancelled(self, db, gateway, student_user, course):
        c2 = _second_course(db)
        order, _ = _paid_order(db, student_user, [course, c2], pay_id="pay_BND2",
                               amount=700.0, bundle_id=None)
        for row in db.query(Enrollment).filter_by(order_id=order.id).all():
            row.enrollment_source = "bundle"
        db.commit()

        result = refund_order(db, order.id, reason=REASON, actor_id=1)

        assert sorted(result["revoked_course_ids"]) == sorted([course.id, c2.id])
        assert all(r.enrollment_status == "cancelled"
                   for r in db.query(Enrollment).filter_by(order_id=order.id).all())

    def test_mixed_order_revokes_its_own_rows_and_releases_the_rescued_one(
            self, db, gateway, student_user, course):
        c2 = _second_course(db)
        plan = _plan(db)
        m = _membership(db, student_user, plan)
        order, _ = _paid_order(db, student_user, [course, c2], pay_id="pay_MIX", amount=800.0)
        rescued = _rescued_row(db, student_user, course, order,
                               source="membership", membership_id=m.id)

        result = refund_order(db, order.id, reason=REASON, actor_id=1)

        assert result["revoked_course_ids"] == [c2.id]
        assert result["released_course_ids"] == [course.id]
        db.refresh(rescued)
        assert rescued.enrollment_status == "enrolled" and rescued.order_id is None
        assert db.query(Enrollment).filter_by(
            order_id=order.id).one().course_id == c2.id

    def test_release_is_idempotent(self, db, gateway, student_user, course):
        """apply_refund_effects runs again from the webhook; the second pass
        must not re-touch a row it already released (it no longer matches)."""
        plan = _plan(db)
        m = _membership(db, student_user, plan)
        order, payment = _paid_order(db, student_user, [course])
        row = _rescued_row(db, student_user, course, order,
                           source="membership", membership_id=m.id)
        refund_order(db, order.id, reason=REASON, actor_id=1)
        refund_service.apply_refund_effects(db, payment, gateway_refund_id="rfnd_X")
        db.commit()
        db.refresh(row)
        assert row.enrollment_status == "enrolled"
        assert row.order_id is None


class TestC2ConcurrentRefundsClaimAtomically:
    """C2 (CRITICAL): the 409 guards were read-then-write, so two concurrent
    admins could both pass them and issue TWO gateway refunds. The intent
    write must be an atomic conditional UPDATE that exactly one caller wins."""

    def test_two_concurrent_calls_produce_exactly_one_gateway_refund(
            self, db, monkeypatch, TestingSessionLocal, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        calls = []
        outcomes = []

        def _reentrant_gateway(gateway_payment_id, amount_paise, reason):
            # Re-enter from a SECOND session while the first refund is mid-flight
            # (its claim committed, gateway not yet returned) — exactly the
            # window the read-then-write guards left open.
            if len(calls) == 0:
                calls.append((gateway_payment_id, amount_paise, reason))
                other = TestingSessionLocal()
                try:
                    refund_order(other, order.id, reason=REASON, actor_id=2)
                    outcomes.append("second call refunded")
                except RefundError as exc:
                    outcomes.append(exc.status_code)
                finally:
                    other.close()
            else:
                calls.append((gateway_payment_id, amount_paise, reason))
            return {"status": "processed", "refund_id": f"rfnd_{len(calls)}",
                    "amount": amount_paise, "currency": "INR"}

        monkeypatch.setattr(refund_service, "_gateway_refund", _reentrant_gateway)
        refund_order(db, order.id, reason=REASON, actor_id=1)

        assert outcomes == [409]        # the loser is told it is in flight
        assert len(calls) == 1          # money moved exactly once

    def test_claim_loses_against_an_already_processed_refund(
            self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        refund_order(db, order.id, reason=REASON, actor_id=1)
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=2)
        assert exc.value.status_code == 409
        assert len(gateway.calls) == 1

    def test_the_claim_itself_refuses_an_already_refunded_payment(
            self, db, gateway, student_user, course):
        """The claim is the LAST line of defence, so it re-checks
        payment_status itself rather than trusting the caller's earlier read —
        that read is exactly what a concurrent refund invalidates."""
        order, payment = _paid_order(db, student_user, [course])
        payment.payment_status = PaymentStatus.REFUNDED
        db.commit()
        assert refund_service._claim_refund(
            db, payment, reason=REASON, actor_id=1) is False
        db.refresh(payment)
        assert payment.refund_status is None       # no intent was written

    def test_the_claim_wins_once_and_then_refuses(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        assert refund_service._claim_refund(db, payment, reason=REASON, actor_id=1) is True
        assert refund_service._claim_refund(db, payment, reason=REASON, actor_id=2) is False
        db.refresh(payment)
        assert payment.refund_requested_by == 1    # the winner's claim stands

    def test_a_failed_intent_can_still_be_claimed(self, db, gateway, monkeypatch,
                                                  student_user, course):
        """'failed' stays retryable — the claim must accept it, not 409."""
        monkeypatch.setattr(refund_service, "_gateway_list_refunds", lambda pid: [])
        gateway.reset(fail=True)
        order, payment = _paid_order(db, student_user, [course])
        with pytest.raises(RefundError):
            refund_order(db, order.id, reason=REASON, actor_id=1)
        gateway.reset(fail=False)
        refund_order(db, order.id, reason=REASON, actor_id=1)
        db.refresh(payment)
        assert payment.refund_status == "processed"


class TestI1StuckRequestedRefunds:
    """I1: a crash between the gateway call and the local commit leaves
    refund_status='requested' while the gateway may already hold the refund.
    Adoption must therefore cover 'requested', not only 'failed' — and stuck
    'requested' rows need their own ops queue."""

    def test_requested_intent_adopts_an_existing_gateway_refund(
            self, db, gateway, refund_lister, student_user, course):
        order, payment = _paid_order(db, student_user, [course])
        payment.refund_status = "requested"     # crashed after the gateway call
        payment.refund_requested_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db.commit()
        refund_lister.reset(items=[{"id": "rfnd_CRASHED", "amount": 50000,
                                    "status": "processed"}])

        result = refund_order(db, order.id, reason=REASON, actor_id=1)

        assert refund_lister.calls == ["pay_RF1"]
        assert gateway.calls == []                    # NOT refunded a second time
        db.refresh(payment)
        assert payment.gateway_refund_id == "rfnd_CRASHED"
        assert payment.refund_status == "processed"
        assert result["adopted_existing_refund"] is True

    def test_requested_intent_with_no_gateway_refund_is_reissued(
            self, db, gateway, refund_lister, student_user, course):
        """The crash happened BEFORE the gateway call — nothing exists there,
        so re-issuing is correct and safe."""
        order, payment = _paid_order(db, student_user, [course])
        payment.refund_status = "requested"
        payment.refund_requested_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db.commit()
        refund_lister.reset(items=[])

        refund_order(db, order.id, reason=REASON, actor_id=1)

        assert gateway.calls == [("pay_RF1", 50000, REASON)]
        db.refresh(payment)
        assert payment.gateway_refund_id == "rfnd_1"

    def test_a_fresh_requested_intent_is_still_409_in_flight(
            self, db, gateway, refund_lister, student_user, course):
        """A refund issued seconds ago is genuinely in flight — do not race it."""
        order, payment = _paid_order(db, student_user, [course])
        payment.refund_status = "requested"
        payment.refund_requested_at = datetime.now(timezone.utc)
        db.commit()
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 409
        assert gateway.calls == []
        assert refund_lister.calls == []

    def test_payment_health_lists_stuck_requested_refunds(
            self, client, db, as_user, student_user, course):
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_STUCK")
        payment.refund_status = "requested"
        payment.refund_reason = REASON
        payment.refund_requested_by = student_user.id
        payment.refund_requested_at = datetime.now(timezone.utc) - timedelta(minutes=45)
        db.commit()
        as_user(student_user)
        data = client.get("/api/v1/admin/payment-health").json()
        assert data["refunds"]["stuck"]["count"] == 1
        item = data["refunds"]["stuck"]["items"][0]
        assert item["order_id"] == order.id
        assert item["gateway_payment_id"] == "pay_STUCK"
        assert item["requested_at"] is not None
        assert item["minutes_pending"] >= 15

    def test_a_recent_requested_refund_is_not_yet_stuck(
            self, client, db, as_user, student_user, course):
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_FRESH")
        payment.refund_status = "requested"
        payment.refund_requested_at = datetime.now(timezone.utc)
        db.commit()
        as_user(student_user)
        data = client.get("/api/v1/admin/payment-health").json()
        assert data["refunds"]["stuck"]["count"] == 0


class TestI2ErrorsAreSanitizedBeforeBeingStored:
    """I2: refund_error is shown in the admin UI and written to logs. A raw
    Razorpay error can carry key ids, account ids and the payer's email —
    none of which belong in an ops queue or a log aggregator."""

    RAW = ("BAD_REQUEST_ERROR: Refund failed for rzp_live_AbCdEf123456 on "
           "account acc_JK9pQ2rS4tU6vW for student1@example.com; contact support")

    def test_secrets_are_redacted_from_the_persisted_error(
            self, db, gateway, monkeypatch, student_user, course):
        monkeypatch.setattr(refund_service, "_gateway_refund",
                            lambda pid, amt, reason: {"status": "failed", "error": self.RAW})
        order, payment = _paid_order(db, student_user, [course])
        with pytest.raises(RefundError):
            refund_order(db, order.id, reason=REASON, actor_id=1)
        db.refresh(payment)
        stored = payment.refund_error or ""
        assert "rzp_live_AbCdEf123456" not in stored
        assert "acc_JK9pQ2rS4tU6vW" not in stored
        assert "student1@example.com" not in stored
        # ...but it stays diagnosable: the error CODE and shape survive
        assert "BAD_REQUEST_ERROR" in stored
        assert "[redacted]" in stored

    def test_the_stored_error_is_length_capped(self, db, gateway, monkeypatch,
                                               student_user, course):
        monkeypatch.setattr(refund_service, "_gateway_refund",
                            lambda pid, amt, reason: {"status": "failed", "error": "E" * 9000})
        order, payment = _paid_order(db, student_user, [course])
        with pytest.raises(RefundError):
            refund_order(db, order.id, reason=REASON, actor_id=1)
        db.refresh(payment)
        assert len(payment.refund_error or "") <= 500

    def test_sanitize_helper_redacts_each_secret_shape(self):
        s = refund_service._sanitize_error
        assert "rzp_test_9999AAAA" not in s("key rzp_test_9999AAAA leaked")
        assert "acc_ABCDEFGH1234" not in s("acc_ABCDEFGH1234")
        assert "a.b@c.co" not in s("mail a.b@c.co now")
        assert s("") == ""

    def test_the_502_detail_never_carries_the_raw_error(
            self, client, db, gateway, monkeypatch, as_user, student_user, course):
        monkeypatch.setattr(refund_service, "_gateway_refund",
                            lambda pid, amt, reason: {"status": "failed", "error": self.RAW})
        order, _ = _paid_order(db, student_user, [course])
        as_user(student_user)
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON})
        assert r.status_code == 502
        assert "rzp_live_AbCdEf123456" not in r.text
        assert "student1@example.com" not in r.text


class TestI3CapturedPaymentSelection:
    """I3: order.payments has no guaranteed order. An older REFUNDED row must
    never shadow the newer capture that actually holds the money."""

    def test_a_newer_completed_capture_wins_over_an_older_refunded_row(
            self, db, gateway, student_user, course):
        order, first = _paid_order(db, student_user, [course])
        first.payment_status = PaymentStatus.REFUNDED
        first.gateway_payment_id = "pay_OLD_REFUNDED"
        newer = Payment(user_id=student_user.id, order_id=order.id,
                        payment_method="razorpay", gateway_payment_id="pay_NEW_CAPTURE",
                        amount=500.0, payment_status=PaymentStatus.COMPLETED,
                        processed_date=datetime.now(timezone.utc))
        db.add(newer)
        db.commit()

        result = refund_order(db, order.id, reason=REASON, actor_id=1)

        assert gateway.calls == [("pay_NEW_CAPTURE", 50000, REASON)]
        assert result["gateway_payment_id"] == "pay_NEW_CAPTURE"
        db.refresh(newer)
        assert newer.payment_status == PaymentStatus.REFUNDED

    def test_selection_is_deterministic_newest_first(self, db, gateway, student_user, course):
        """Two eligible captures -> always the newest (highest id), on every run."""
        order, older = _paid_order(db, student_user, [course], pay_id="pay_A")
        newer = Payment(user_id=student_user.id, order_id=order.id,
                        payment_method="razorpay", gateway_payment_id="pay_B",
                        amount=500.0, payment_status=PaymentStatus.COMPLETED,
                        processed_date=datetime.now(timezone.utc))
        db.add(newer)
        db.commit()
        assert refund_service.captured_payment(order).gateway_payment_id == "pay_B"

    def test_all_payments_refunded_is_still_409_not_a_second_refund(
            self, db, gateway, student_user, course):
        order, only = _paid_order(db, student_user, [course])
        only.payment_status = PaymentStatus.REFUNDED
        db.commit()
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 409
        assert gateway.calls == []


class TestI4MembershipChargesAreNotRefundableHere:
    """I4: a membership charge is refunded by CANCELLING the subscription
    (spec §2), not through this endpoint — refunding one charge while the
    subscription keeps billing is worse than doing nothing."""

    def test_subscription_order_is_400_with_guidance(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_SUB",
                                     method="razorpay_subscription")
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 400
        assert "membership" in exc.value.detail.lower()
        assert "cancel" in exc.value.detail.lower()
        assert gateway.calls == []
        db.refresh(order)
        db.refresh(payment)
        assert payment.refund_status is None          # no intent written
        assert payment.payment_status == PaymentStatus.COMPLETED
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"

    def test_endpoint_returns_400_for_a_subscription_order(
            self, client, db, gateway, as_user, student_user, course):
        order, _ = _paid_order(db, student_user, [course], pay_id="pay_SUB2",
                               method="razorpay_subscription")
        as_user(student_user)
        r = client.post(f"/api/v1/admin/orders/{order.id}/refund", json={"reason": REASON})
        assert r.status_code == 400
        assert "membership" in r.json()["detail"].lower()


class TestM2ZeroAmountOrders:
    """M2: to_paise clamps to the gateway's 100-paise minimum, which would
    turn a free/zero order into a real ₹1 refund. Zero or negative is simply
    not refundable."""

    def test_zero_amount_is_not_refundable(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_FREE", amount=0)
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 400
        assert gateway.calls == []
        db.refresh(payment)
        assert payment.refund_status is None

    def test_negative_amount_is_not_refundable(self, db, gateway, student_user, course):
        order, payment = _paid_order(db, student_user, [course], pay_id="pay_NEG", amount=-10)
        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)
        assert exc.value.status_code == 400
        assert gateway.calls == []

    def test_the_paise_floor_still_applies_above_zero(self, db, gateway, student_user, course):
        order, _ = _paid_order(db, student_user, [course], pay_id="pay_TINY", amount=0.5)
        refund_order(db, order.id, reason=REASON, actor_id=1)
        assert gateway.calls == [("pay_TINY", 100, REASON)]


class TestM3:
    def test_refund_order_has_no_dead_gateway_parameter(self):
        """M3: the injectable `gateway=` param was never used — tests
        monkeypatch _gateway_refund. Dead injection points on a money path are
        a liability."""
        params = inspect.signature(refund_order).parameters
        assert "gateway" not in params
        assert set(params) == {"db", "order_id", "reason", "actor_id"}

    def test_a_raising_gateway_is_recorded_as_failed_not_propagated(
            self, db, monkeypatch, student_user, course):
        """The adapter returns {'status': 'failed'} today, but an SDK upgrade
        (or a socket timeout) can RAISE. That must still land as a persisted
        'failed' intent + 502, never a 500 with access half-revoked."""
        def _boom(gateway_payment_id, amount_paise, reason):
            raise ConnectionError("connection reset by peer for rzp_live_SECRET123")

        monkeypatch.setattr(refund_service, "_gateway_refund", _boom)
        order, payment = _paid_order(db, student_user, [course])

        with pytest.raises(RefundError) as exc:
            refund_order(db, order.id, reason=REASON, actor_id=1)

        assert exc.value.status_code == 502
        db.refresh(order)
        db.refresh(payment)
        assert payment.refund_status == "failed"
        assert "ConnectionError" in (payment.refund_error or "")
        assert "rzp_live_SECRET123" not in (payment.refund_error or "")   # sanitized
        assert payment.payment_status == PaymentStatus.COMPLETED
        assert order.order_status == OrderStatus.COMPLETED
        assert db.query(Enrollment).filter_by(order_id=order.id).one().enrollment_status == "enrolled"
