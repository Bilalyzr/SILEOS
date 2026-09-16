"""Applies a stored WebhookEvent to local state. Idempotent: safe to run on
the same event any number of times (fulfillment is keyed on the gateway
payment id; refund/failed handlers are naturally idempotent updates)."""
import functools
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.fulfillment_service import fulfill_course_purchase
from app.services.email_service import EmailService
from app.services.pricing import resolve_expected_purchase

logger = logging.getLogger(__name__)

SUBSCRIPTION_EVENTS = {
    "subscription.activated", "subscription.charged", "subscription.halted",
    "subscription.cancelled", "subscription.completed", "subscription.pending",
}
HANDLED_EVENTS = {
    "payment.captured", "payment.failed", "refund.processed",
} | SUBSCRIPTION_EVENTS


class UnrecoverableEvent(Exception):
    """Event can never be applied (bad notes etc.) — alert, don't retry."""


def process_webhook_event(db: Session, event: WebhookEvent) -> None:
    event.attempts = (event.attempts or 0) + 1
    event.last_attempt_at = datetime.now(timezone.utc)
    try:
        if event.event_type not in HANDLED_EVENTS:
            event.status = WebhookEventStatus.SKIPPED
        elif event.event_type == "payment.captured":
            _handle_payment_captured(db, event)
            event.status = WebhookEventStatus.PROCESSED
        elif event.event_type == "payment.failed":
            # No local Order exists before fulfillment, so there is usually
            # nothing to update — recording the event IS the handling.
            event.status = WebhookEventStatus.PROCESSED
        elif event.event_type == "refund.processed":
            _handle_refund_processed(db, event)
            event.status = WebhookEventStatus.PROCESSED
        elif event.event_type in SUBSCRIPTION_EVENTS:
            _handle_subscription_event(db, event)
            event.status = WebhookEventStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        event.last_error = None
        db.commit()
    except UnrecoverableEvent as exc:
        db.rollback()
        # rollback() discards the in-memory bookkeeping set at the top of this
        # function, so re-apply it before the failure commit.
        event.status = WebhookEventStatus.FAILED
        event.attempts = 5  # exhaust retries: retrying cannot fix this
        event.last_attempt_at = datetime.now(timezone.utc)
        event.last_error = str(exc)
        db.commit()
        EmailService.send_payment_alert(
            f"unrecoverable webhook event {event.event_id}",
            f"type={event.event_type} error={exc}\nManual reconciliation needed.",
        )
    except Exception as exc:
        db.rollback()
        # Same as above: without re-applying attempts/last_attempt_at the
        # rollback would reset them, making the sweeper retry forever.
        event.attempts = (event.attempts or 0) + 1
        event.last_attempt_at = datetime.now(timezone.utc)
        event.status = WebhookEventStatus.FAILED
        event.last_error = f"{type(exc).__name__}: {exc}"
        db.commit()
        logger.exception("webhook event %s processing failed", event.event_id)


def _payment_entity(event: WebhookEvent) -> dict:
    return ((event.payload or {}).get("payload", {})
            .get("payment", {}).get("entity", {}))


def _subscription_entity(event: WebhookEvent) -> dict:
    return ((event.payload or {}).get("payload", {})
            .get("subscription", {}).get("entity", {}))


def _handle_subscription_event(db: Session, event: WebhookEvent) -> None:
    from app.services.campus_billing import handle_event as campus_event
    if campus_event(db, event):
        return
    from app.models.membership import Membership, MembershipPlan, MembershipStatus
    from app.services.membership_access import grant_membership_enrollments

    entity = _subscription_entity(event)
    sub_id = entity.get("id")
    if not sub_id:
        raise UnrecoverableEvent("subscription event without subscription id")
    membership = db.query(Membership).filter(
        Membership.razorpay_subscription_id == str(sub_id)).first()
    if membership is None:
        raise UnrecoverableEvent(f"no membership for subscription {sub_id}")

    etype = event.event_type

    # CANCELLED/COMPLETED are absorbing states: once a membership reaches one,
    # no later/out-of-order event may resurrect it. Razorpay doesn't guarantee
    # delivery ordering and the durable-inbox sweeper retries FAILED events, so
    # a late `activated`/`charged`/`halted` for an already-terminated
    # subscription must not flip status back to ACTIVE/GRACE or re-grant
    # enrollments. A `charged` event still carries real money, though, so the
    # Payment row is recorded regardless of the membership's terminal state.
    terminal = membership.status in (MembershipStatus.CANCELLED,
                                     MembershipStatus.COMPLETED)

    if etype in ("subscription.activated", "subscription.charged"):
        current_end = entity.get("current_end")
        if current_end and not terminal:
            membership.current_period_end = datetime.fromtimestamp(
                int(current_end), tz=timezone.utc)

    if etype == "subscription.activated":
        if not terminal:
            membership.status = MembershipStatus.ACTIVE
            membership.grace_until = None
            grant_membership_enrollments(db, membership)
    elif etype == "subscription.charged":
        if not terminal:
            membership.status = MembershipStatus.ACTIVE
            membership.grace_until = None
            grant_membership_enrollments(db, membership)
        pay_entity = ((event.payload or {}).get("payload", {})
                      .get("payment", {}).get("entity", {}))
        if pay_entity.get("id"):
            _record_subscription_charge(db, membership, pay_entity)
    elif etype == "subscription.halted":
        if not terminal:
            plan = db.query(MembershipPlan).filter(
                MembershipPlan.id == membership.plan_id).one()
            # `or 7` would silently turn an intentional grace_days=0 tier
            # (no grace at all) into a week of free access.
            grace_days = plan.grace_days if plan.grace_days is not None else 7
            membership.status = MembershipStatus.GRACE
            membership.grace_until = (datetime.now(timezone.utc)
                                      + timedelta(days=grace_days))
    elif etype == "subscription.cancelled":
        membership.status = MembershipStatus.CANCELLED
    elif etype == "subscription.completed":
        membership.status = MembershipStatus.COMPLETED
    # subscription.pending: recorded only — no state change, no current_end
    # write. Razorpay sends this while retrying a FAILED charge; accepting its
    # current_end would extend paid access for a cycle that hasn't been paid.


def _record_subscription_charge(db: Session, membership, pay_entity: dict) -> None:
    """Order+Payment rows for a renewal charge — same idempotency key as
    course purchases (gateway_payment_id). No OrderItem: OrderItem.course_id
    is NOT NULL and a membership renewal has no single course."""
    import uuid
    from app.models.payment import Order, OrderStatus, Payment, PaymentStatus
    from app.models.membership import MembershipPlan

    pay_id = str(pay_entity.get("id"))
    if db.query(Payment).filter(Payment.gateway_payment_id == pay_id).first():
        return
    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == membership.plan_id).one()
    amount = int(pay_entity.get("amount") or 0) / 100.0
    currency = str(pay_entity.get("currency") or "INR")
    order = Order(
        user_id=membership.user_id,
        order_key=f"SUB_{uuid.uuid4().hex[:12].upper()}",
        order_status=OrderStatus.COMPLETED,
        currency=currency,
        subtotal_amount=amount, total_amount=amount,
        payment_method="razorpay_subscription",
        payment_method_title=f"Membership: {plan.name}",
        transaction_id=pay_id,
        date_paid=datetime.now(timezone.utc),
        date_completed=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    db.add(Payment(user_id=membership.user_id, order_id=order.id,
                   payment_method="razorpay_subscription",
                   gateway_transaction_id=pay_id, gateway_payment_id=pay_id,
                   gateway_order_id=str(pay_entity.get("order_id") or ""),
                   amount=amount, currency=currency,
                   payment_status=PaymentStatus.COMPLETED,
                   processed_date=datetime.now(timezone.utc)))


def _is_edgyy_entity(entity: dict) -> bool:
    """Orders created by the Edgyy payment proxy (routers/payments_proxy.py)
    are tagged in their Razorpay notes; they have no user_id/course_id and
    must not go through LMS course fulfillment."""
    notes = entity.get("notes") or {}
    return bool(notes.get("edgyy_registration_id")) or notes.get("source") == "edgyy.in"


def _extract_ids(notes) -> tuple[int, int] | None:
    """(user_id, course_id) from a Razorpay notes dict, or None if unusable."""
    notes = notes or {}
    try:
        return int(notes.get("user_id")), int(notes.get("course_id"))
    except (TypeError, ValueError, AttributeError):
        return None


def _gateway_client():
    """Razorpay client for the notes fallback, or None if creds are unset.
    Kept module-level so tests can monkeypatch it."""
    from app.routers.payments import _razorpay_creds
    import razorpay
    key_id, key_secret = _razorpay_creds()
    if not key_id or not key_secret:
        return None
    client = razorpay.Client(auth=(key_id, key_secret))
    # The SDK's requests.Session has no default timeout; a hung gateway would
    # otherwise stall webhook processing indefinitely.
    client.session.request = functools.partial(client.session.request, timeout=30)
    return client


def _fetch_order_notes(order_id) -> dict:
    """Notes of the gateway order backing this payment. Returns {} when the
    gateway is unconfigured/unreachable — callers treat that as 'no notes'."""
    if not order_id:
        return {}
    try:
        client = _gateway_client()
        if client is None:
            return {}
        order = client.order.fetch(str(order_id)) or {}
        return order.get("notes") or {}
    except Exception:
        logger.exception("gateway order fetch failed for %s", order_id)
        return {}


def _fulfill_bundle_from_notes(db: Session, entity: dict, notes: dict) -> None:
    from app.services.fulfillment_service import fulfill_bundle_purchase

    payment_id = str(entity.get("id"))
    if db.query(Payment).filter(Payment.gateway_payment_id == payment_id).first():
        return
    try:
        user_id = int(notes.get("user_id"))
        bundle_id = int(notes.get("bundle_id"))
        course_ids = [int(x) for x in str(notes.get("bundle_course_ids") or "").split(",") if x]
    except (TypeError, ValueError):
        raise UnrecoverableEvent(f"unusable bundle notes on payment {payment_id}: {notes!r}")
    if not course_ids:
        raise UnrecoverableEvent(f"bundle payment {payment_id} without course snapshot")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnrecoverableEvent(f"user {user_id} not found for bundle payment {payment_id}")
    fulfill_bundle_purchase(
        db, user=user, bundle_id=bundle_id, course_ids=course_ids,
        razorpay_order_id=str(entity.get("order_id") or ""),
        razorpay_payment_id=payment_id,
        paid_amount=int(entity.get("amount") or 0) / 100.0,
        currency=str(entity.get("currency") or "INR"))


def _fulfill_ebook_from_notes(db: Session, entity: dict, notes: dict) -> None:
    """Webhook leg of the ebook triple-redundancy. Converges on the same
    `fulfill_ebook_purchase` as /verify and the sweeper, and prices the
    capture off the same `ebook_price_inr` order-notes snapshot.

    The gateway's captured amount — not the snapshot — is what is booked as
    `paid_amount`: this is a record of money that already moved. A mismatch
    against the snapshot is alerted (retries cannot fix an amount) but never
    blocks the grant, mirroring `_settle_invoice_from_notes`' posture of
    never letting a pricing disagreement silently swallow a real capture."""
    from app.models.ebook import Ebook, snapshot_prices_from_notes
    from app.services.fulfillment_service import fulfill_ebook_purchase

    payment_id = str(entity.get("id"))
    if db.query(Payment).filter(Payment.gateway_payment_id == payment_id).first():
        return
    try:
        user_id = int(notes.get("user_id"))
        ebook_id = int(notes.get("ebook_id"))
    except (TypeError, ValueError):
        raise UnrecoverableEvent(
            f"unusable ebook notes on payment {payment_id}: {notes!r}")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnrecoverableEvent(
            f"user {user_id} not found for ebook payment {payment_id}")

    ebook = db.query(Ebook).filter(Ebook.id == ebook_id).first()
    snapshot_inr, list_inr = snapshot_prices_from_notes(notes, ebook)

    captured_paise = int(entity.get("amount") or 0)
    paid_amount = captured_paise / 100.0
    if snapshot_inr:
        expected_paise = max(int(round(float(snapshot_inr) * 100)), 100)
        if captured_paise != expected_paise:
            EmailService.send_payment_alert(
                f"captured amount mismatch for ebook {ebook_id} payment {payment_id}",
                f"user_id={user_id} expected_paise={expected_paise} "
                f"captured_paise={captured_paise}. Granted at the captured "
                "amount — verify the price snapshot manually.",
            )

    fulfill_ebook_purchase(
        db, user=user, ebook_id=ebook_id,
        razorpay_order_id=str(entity.get("order_id") or ""),
        razorpay_payment_id=payment_id,
        paid_amount=paid_amount,
        list_price_inr=list_inr,
        currency=str(entity.get("currency") or "INR"))


def _settle_invoice_from_notes(db: Session, entity: dict, notes: dict) -> None:
    from app.models.company_invoice import CompanyInvoice, InvoiceStatus
    from app.services.invoice_service import settle_invoice

    payment_id = str(entity.get("id"))
    if db.query(Payment).filter(Payment.gateway_payment_id == payment_id).first():
        return
    try:
        invoice_id = int(notes.get("invoice_id"))
    except (TypeError, ValueError):
        raise UnrecoverableEvent(f"unusable invoice notes on payment {payment_id}: {notes!r}")
    invoice = db.query(CompanyInvoice).filter(CompanyInvoice.id == invoice_id).first()
    if not invoice:
        raise UnrecoverableEvent(f"invoice {invoice_id} not found for payment {payment_id}")

    captured_paise = int(entity.get("amount") or 0)
    expected_paise = max(int(round(float(invoice.total) * 100)), 100)
    if captured_paise != expected_paise:
        # Retries can't fix an amount mismatch — record via alert, not
        # UnrecoverableEvent (event still PROCESSED; the alert is the record).
        EmailService.send_payment_alert(
            f"captured amount mismatch for invoice {invoice_id} payment {payment_id}",
            f"invoice_number={invoice.invoice_number} status={invoice.status.value} "
            f"expected_paise={expected_paise} captured_paise={captured_paise}. "
            "Not settled — investigate manually.",
        )
        return

    settled = settle_invoice(
        db, invoice, via="razorpay", reference=payment_id,
        gateway_payment_id=payment_id,
        gateway_order_id=str(entity.get("order_id") or ""),
    )
    if not settled and invoice.status != InvoiceStatus.PAID:
        # Money was captured but the invoice can't be settled (draft,
        # cancelled, or otherwise not ISSUED) — this must never be silent.
        # Already-PAID is a genuine idempotent replay and stays silent.
        EmailService.send_payment_alert(
            f"captured payment for unsettleable invoice {invoice_id}",
            f"invoice_number={invoice.invoice_number} status={invoice.status.value} "
            f"payment_id={payment_id} amount_paise={captured_paise}. "
            "Not settled — investigate manually.",
        )


def _handle_payment_captured(db: Session, event: WebhookEvent) -> None:
    entity = _payment_entity(event)
    payment_id = entity.get("id")
    if not payment_id:
        raise UnrecoverableEvent("payment.captured without payment id")

    if _is_edgyy_entity(entity):
        _handle_edgyy_payment_captured(db, event, entity)
        return

    if entity.get("subscription_id"):
        from app.models.campus_operations import CampusSubscription
        if db.query(CampusSubscription).filter_by(gateway_subscription_id=str(entity["subscription_id"])).first():
            # The charged event carries the billing period and is the campus
            # entitlement convergence point. A bare capture never grants seats.
            return
        from app.models.membership import Membership
        membership = db.query(Membership).filter(
            Membership.razorpay_subscription_id == str(entity["subscription_id"])
        ).first()
        if membership is not None:
            _record_subscription_charge(db, membership, entity)
            return
        raise UnrecoverableEvent(
            f"captured payment for unknown subscription {entity['subscription_id']}")

    from app.models.tuition_collection import TuitionOnlineOrder
    from app.services.tuition_collection import fulfil_online_order
    tuition_order = (
        db.query(TuitionOnlineOrder).filter(TuitionOnlineOrder.gateway_order_id == entity.get("order_id")).first()
        if entity.get("order_id") else None
    )
    if tuition_order is not None:
        # A mismatch raises ValueError; the outer handler records it as a
        # failed event instead of retrying, which is the honest outcome.
        fulfil_online_order(db, tuition_order, entity)
        return

    from app.models.exam_paper import ExamPaper
    from app.services.exam_paper_service import fulfill_capture
    paper = db.query(ExamPaper).filter(ExamPaper.gateway_order_id == entity.get('order_id')).first() if entity.get('order_id') else None
    if paper is not None:
        fulfill_capture(db, paper, entity)
        return

    if db.query(Payment).filter(Payment.gateway_payment_id == str(payment_id)).first():
        return  # /verify (or a prior run) already fulfilled — no-op

    notes = entity.get("notes") or {}
    ids = _extract_ids(notes)
    if (ids is None and not notes.get("bundle_id")
            and not notes.get("invoice_id") and not notes.get("ebook_id")):
        # Spec fallback: the payment entity's notes can be empty even though
        # the ORDER carries them. Ask the gateway before giving up. The order's
        # notes then also supply cohort_id / referral_code_id below (and may
        # themselves carry a bundle_id/invoice_id/ebook_id, handled the same
        # way as entity notes).
        order_notes = _fetch_order_notes(entity.get("order_id"))
        ids = _extract_ids(order_notes)
        if (ids is not None or order_notes.get("bundle_id")
                or order_notes.get("invoice_id") or order_notes.get("ebook_id")):
            notes = order_notes

    if notes.get("bundle_id"):
        _fulfill_bundle_from_notes(db, entity, notes)
        return

    if notes.get("invoice_id"):
        _settle_invoice_from_notes(db, entity, notes)
        return

    # Before the course branch: an ebook capture carries user_id but no
    # course_id, so _extract_ids returns None for it and it would otherwise
    # fall through to the "unusable notes" escalation below.
    if notes.get("ebook_id"):
        _fulfill_ebook_from_notes(db, entity, notes)
        return

    if ids is None:
        raise UnrecoverableEvent(
            f"unusable notes on payment {payment_id}: "
            f"{(entity.get('notes') or {})!r} (amount={entity.get('amount')})"
        )
    user_id, course_id = ids

    user = db.query(User).filter(User.id == user_id).first()
    course = db.query(Course).filter(Course.id == course_id).first()
    if not user or not course:
        raise UnrecoverableEvent(
            f"user {user_id} or course {course_id} not found for payment {payment_id}"
        )

    paid_amount = int(entity.get("amount") or 0) / 100.0
    gateway_order_id = str(entity.get("order_id") or "")

    # Single source of truth shared with /verify and the sweeper — resolves
    # the effective (sale, if any) price, applies a coupon note's discount,
    # or a seat-price override, but ONLY for a cohort note that is active
    # and bound to THIS course (never trusts a stale/forged cohort_id
    # pointing at another course's cheaper seat cohort — audit A5 follow-up,
    # platform audit 2026-09-03 round 3). `paid_amount`/`order_id` let it
    # skip an implausible seat-price override (more than Rs.1 below what was
    # actually captured) instead of silently producing a corrupt Order row.
    expected = resolve_expected_purchase(
        db, course, notes, user_id=user.id,
        paid_amount=paid_amount, order_id=gateway_order_id,
    )
    # subtotal_price (pre-discount), not expected_price (net of a coupon's
    # discount) — see ExpectedPurchase's docstring; using expected_price
    # here would double-subtract a coupon's discount from the Order row.
    base_price = float(expected.subtotal_price)
    coupon_discount = (
        float(expected.coupon_discount) if expected.is_coupon
        else max(0.0, base_price - paid_amount)
    )

    fulfill_course_purchase(
        db, user=user, course=course,
        razorpay_order_id=gateway_order_id,
        razorpay_payment_id=str(payment_id),
        paid_amount=paid_amount, base_price=base_price,
        coupon_discount=coupon_discount,
        currency=str(entity.get("currency") or "INR"),
        cohort=expected.cohort,
        referral_code_id=expected.referral_code_id,
        coupon=None,  # webhook path records the discount amount, not CouponUsage
    )


def _handle_edgyy_payment_captured(db: Session, event: WebhookEvent, entity: dict) -> None:
    """Edgyy-proxy equivalent of course fulfillment: mark the proxy payment
    (or hosted session) paid and deliver the completion callback to Edgyy.
    Keyed on webhook_delivered, so re-runs are no-ops."""
    from app.models.edgyy_payment import (
        EdgyyPayment,
        EdgyyPaymentStatus,
        EdgyyPaymentSession,
        EdgyyPaymentSessionStatus,
    )

    order_id = entity.get("order_id")
    if not order_id:
        raise UnrecoverableEvent("edgyy payment.captured without order_id")

    # Same two-table split as the proxy /verify endpoint: /create-order rows
    # live in edgyy_payments, hosted /create-session rows in edgyy_payment_sessions.
    payment = db.query(EdgyyPayment).filter(
        EdgyyPayment.razorpay_order_id == str(order_id)
    ).first()
    paid_status = EdgyyPaymentStatus.PAID
    if not payment:
        payment = db.query(EdgyyPaymentSession).filter(
            EdgyyPaymentSession.razorpay_order_id == str(order_id)
        ).first()
        paid_status = EdgyyPaymentSessionStatus.PAID
    if not payment:
        raise UnrecoverableEvent(
            f"edgyy order {order_id} not found in edgyy_payments/edgyy_payment_sessions"
        )

    if payment.webhook_delivered:
        return  # already delivered to Edgyy — no-op

    if payment.status != paid_status:
        payment.status = paid_status
        payment.razorpay_payment_id = str(entity.get("id") or "")
        payment.paid_at = datetime.now(timezone.utc)
        payment.gateway_response = {"webhook": event.payload}

    payment.webhook_delivered = True
    payment.webhook_delivered_at = datetime.now(timezone.utc)
    db.commit()

    # Local import: routers.payments_proxy pulls in razorpay/httpx setup that
    # the processor doesn't otherwise need at import time.
    from app.routers.payments_proxy import _trigger_edgyy_webhook
    _trigger_edgyy_webhook(payment)


def _handle_refund_processed(db: Session, event: WebhookEvent) -> None:
    entity = ((event.payload or {}).get("payload", {})
              .get("refund", {}).get("entity", {}))
    payment_id = entity.get("payment_id")
    if not payment_id:
        raise UnrecoverableEvent("refund.processed without payment_id")
    from app.services.exam_paper_service import revoke_payment
    revoke_payment(db, str(payment_id))
    payment = db.query(Payment).filter(
        Payment.gateway_payment_id == str(payment_id)
    ).first()
    if not payment:
        return  # nothing local to converge; the event record is the handling

    if payment.refund_status in ("requested", "processed"):
        # ADMIN-INITIATED (spec §1.5). The refund endpoint persisted its intent
        # before calling the gateway, so this event either finishes a refund
        # that crashed after the gateway call, or re-confirms one that already
        # completed. Either way: converge — order REFUNDED and exactly this
        # order's enrollments cancelled. apply_refund_effects is idempotent, so
        # a duplicate delivery changes nothing (the first refund id wins).
        from app.services.refund_service import apply_refund_effects
        refund_id = entity.get("id")
        revoked, released = apply_refund_effects(
            db, payment, gateway_refund_id=str(refund_id) if refund_id else None
        )
        logger.info(
            "refund.processed converged (admin-initiated) event_id=%s order_id=%s "
            "payment_id=%s gateway_refund_id=%s revoked_course_ids=%s released_course_ids=%s",
            event.event_id, payment.order_id, payment.id,
            payment.gateway_refund_id, revoked, released,
        )
        return

    # EXTERNALLY-INITIATED (Razorpay dashboard, no intent row — or an intent we
    # recorded as 'failed'): today's behavior is deliberately preserved. The
    # payment is marked REFUNDED but enrollment is NOT revoked —
    # /admin/payment-health surfaces refunded payments with live enrollments so
    # a human decides. Idempotent: re-setting the same status changes nothing.
    payment.payment_status = PaymentStatus.REFUNDED
    logger.info(
        "refund.processed recorded (external, access left for human decision) "
        "event_id=%s order_id=%s payment_id=%s gateway_payment_id=%s",
        event.event_id, payment.order_id, payment.id, payment.gateway_payment_id,
    )
