"""Admin-initiated, full-amount refunds (spec 2026-09-04-money-ops §1, R2).

Order of operations (BINDING):
  1. load Order + its captured gateway Payment (409 already refunded / in
     flight; 400 no captured gateway payment — offline/company-invoice/
     membership-charge orders are out of scope);
  2. amount = the captured amount on the Payment, converted to paise here and
     ONLY here (never from the request);
  3. CLAIM THE REFUND ATOMICALLY (see below) — that claim IS the persisted
     intent (refund_status='requested' + reason/actor/at) — and commit, THEN
     call the gateway. Gateway failure -> refund_status='failed' +
     refund_error, 502, access intact;
  4. gateway success -> apply_refund_effects(): Payment + Order REFUNDED,
     gateway_refund_id stored, and settle EXACTLY the enrollments this order
     touched (Enrollment.order_id == order.id) — see ENROLLMENT SETTLEMENT;
  5. The refund.processed webhook (webhook_processor._handle_refund_processed)
     calls apply_refund_effects() for admin-initiated refunds so both paths
     converge idempotently.

ATOMIC CLAIM (no double refund under concurrency). The 409 guards used to be
read-then-write, so two admins clicking Refund at the same moment could both
pass them and issue two gateway refunds. The intent write is therefore a
CONDITIONAL UPDATE — "set refund_status='requested' WHERE this payment is
still COMPLETED and its refund_status is NULL or 'failed' (or a stale
'requested')" — and a rowcount of 0 means somebody else won: 409. The winner
commits its claim before touching the gateway.

RETRY SAFETY (no double refund after a crash or a lost response). A 'failed'
intent may mean the gateway never refunded — or that it did and we lost the
response. A stale 'requested' intent means the same thing after a crash
between the gateway call and the local commit. Neither is re-issued blind:
the retry first asks the gateway which refunds already exist for this payment
(_gateway_list_refunds) and, if one matches this refund's amount and is not
itself failed, ADOPTS it (stores its id + applies effects) instead of creating
a second. If that lookup itself fails we refuse with 502 rather than risk
refunding twice. Which path was taken is persisted in refund_error for audit.

ENROLLMENT SETTLEMENT (never destroy access the buyer still owns). Fulfillment
RESCUES a pre-existing enrollment in place: a membership or company-seat row
keeps its `enrollment_source` and merely gets this order's id stamped on it.
Cancelling such a row on refund would revoke access the buyer still pays for —
and irreversibly, because membership_access only re-grants rows that are
'suspended' AND carry no order_id. So settlement splits by source:
  * rows this order actually created (source NULL = plain course purchase, or
    'bundle') -> cancelled, order_id kept for the audit trail;
  * rescued rows ('membership', 'company', or any other non-purchase source)
    -> order_id UN-STAMPED and the status restored to what that source's own
    lifecycle implies (enrolled while the membership is live, else suspended).
    Never cancelled.

REDACTION. Gateway error text reaches both the admin UI and the logs, and can
carry key ids, account ids and the payer's email. Everything persisted or
logged goes through _sanitize_error first.

No admin audit model exists in this repo (only AdminImpersonationLog), so
every refund writes ONE logger.info line with order/payment/actor ids.
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderStatus, Payment, PaymentStatus
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

# Payment.payment_method values that never carry a refundable gateway capture.
_OFFLINE_METHODS = {"bank_transfer", "mock"}

# Membership charges are refunded by CANCELLING the subscription (spec §2),
# never one charge at a time — refunding a charge while the subscription keeps
# billing is worse than doing nothing. Set by webhook_processor on both the
# Order and the Payment it writes for a subscription charge.
_SUBSCRIPTION_METHODS = {"razorpay_subscription"}

# enrollment_source values that mean "this order created this row". NULL is
# what fulfill_course_purchase writes for a plain single-course purchase.
_ORDER_OWNED_SOURCES = {None, "", "bundle"}

# A 'requested' intent older than this is not in flight any more — it is the
# debris of a crash between the gateway call and the local commit, and is
# eligible for the adopt-or-reissue retry path.
STALE_REQUESTED_AFTER = timedelta(minutes=15)

# Persisted/logged error text: short enough for an ops table, long enough to
# diagnose.
_MAX_ERROR_CHARS = 500

_REDACTIONS = (
    # Razorpay key / account / entity ids, e.g. rzp_live_AbC123, acc_JK9pQ2
    re.compile(r"\b(?:rzp|acc)_[A-Za-z0-9_]{4,}\b"),
    # email addresses
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)


def _sanitize_error(text) -> str:
    """Redact secrets and personal data, then cap the length.

    refund_error is rendered in the admin ops queue and echoed into logs, so
    it must never carry an API key id, a gateway account id or the payer's
    email. The error CODE and shape are preserved so the failure stays
    diagnosable.
    """
    if not text:
        return ""
    out = str(text)
    for pattern in _REDACTIONS:
        out = pattern.sub("[redacted]", out)
    if len(out) > _MAX_ERROR_CHARS:
        out = out[:_MAX_ERROR_CHARS - 3] + "..."
    return out


class RefundError(Exception):
    """Business-rule failure the router maps 1:1 onto an HTTP status."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class NotRefundable(RefundError):
    """This order can never be refunded through this endpoint (400): no
    captured gateway payment, a zero/negative capture, or a membership charge
    that must be handled by cancelling the subscription instead."""

    def __init__(self, detail: str):
        super().__init__(400, detail)


def to_paise(rupees) -> int:
    """Rupees -> paise at the Razorpay boundary (repo convention).

    The 100-paise floor is the gateway's minimum for a REAL refund; callers
    must reject zero/negative captures before reaching here (see
    `refundable_amount`), or a free order would be refunded ₹1 of real money.
    """
    return max(int(round(float(rupees) * 100)), 100)


def refundable_amount(payment: Payment) -> float:
    """The rupee amount this payment can be refunded, or 0 when it cannot."""
    try:
        amount = float(payment.amount or 0)
    except (TypeError, ValueError):
        return 0.0
    return amount if amount > 0 else 0.0


def _gateway_refund(gateway_payment_id: str, amount_paise: int, reason: str) -> dict:
    """Sync adapter over PaymentService.process_refund.

    process_refund is declared `async def` but never awaits (it drives the
    blocking razorpay SDK), so running it to completion with asyncio.run is
    safe — PROVIDED the caller is not itself inside a running event loop.
    The admin refund endpoint is therefore a plain `def` (FastAPI runs it in
    the threadpool). Tests monkeypatch this function.
    """
    return asyncio.run(PaymentService.process_refund(gateway_payment_id, amount_paise, reason))


def _gateway_list_refunds(gateway_payment_id: str) -> list[dict]:
    """Every refund the gateway already holds for this payment.

    Used ONLY on a retry (a 'failed' or stale 'requested' intent), to tell
    "the refund never happened" apart from "the refund happened and we lost
    the response". Raises on transport/auth failure — the caller must NOT
    re-issue blind. Tests monkeypatch this function.
    """
    client = PaymentService().razorpay_client
    result = client.payment.fetch_multiple_refund(gateway_payment_id) or {}
    if isinstance(result, dict):
        items = result.get("items") or []
    else:  # some SDK paths return the list directly
        items = result or []
    return [r for r in items if isinstance(r, dict)]


def _matching_existing_refund(refunds: list[dict], amount_paise: int) -> dict | None:
    """A refund at the gateway that IS the one we were trying to create:
    same amount, and not itself failed. A partial refund (different amount)
    is somebody else's action and must not be mistaken for ours."""
    for r in refunds:
        try:
            r_amount = int(r.get("amount"))
        except (TypeError, ValueError):
            continue
        if r_amount != amount_paise:
            continue
        if str(r.get("status") or "").lower() == "failed":
            continue
        if not r.get("id"):
            continue
        return r
    return None


def captured_payment(order: Order) -> Payment | None:
    """The gateway payment that actually captured money for this order.

    Deterministic and COMPLETED-first: an order can carry several Payment rows
    (a retried checkout, an earlier partially-handled attempt), and an older
    REFUNDED row must never shadow the newer capture that still holds the
    money. Within a status class the newest row (highest id) wins.
    """
    def _eligible(p: Payment) -> bool:
        return bool(
            p.gateway_payment_id
            and p.payment_method not in _OFFLINE_METHODS
            and p.payment_status in (PaymentStatus.COMPLETED, PaymentStatus.REFUNDED)
        )

    rows = [p for p in order.payments if _eligible(p)]
    if not rows:
        return None
    rows.sort(key=lambda p: (p.payment_status != PaymentStatus.COMPLETED, -(p.id or 0)))
    return rows[0]


def is_subscription_order(order: Order, payment: Payment | None) -> bool:
    """A membership/subscription charge (spec §2 territory, not this
    endpoint's). Checked on both rows because webhook_processor stamps the
    method on the Order and the Payment it creates."""
    if (order.payment_method or "") in _SUBSCRIPTION_METHODS:
        return True
    return bool(payment is not None and (payment.payment_method or "") in _SUBSCRIPTION_METHODS)


def _membership_is_live(db: Session, enrollment: Enrollment) -> bool:
    """Does the membership that owns this rescued row still confer access?

    Mirrors membership_access's own notion: ACTIVE and GRACE keep access
    (grace = renewal failed but not yet expired); everything else does not.
    """
    from app.models.membership import Membership, MembershipStatus

    if not enrollment.membership_id:
        return False
    m = db.query(Membership).filter(Membership.id == enrollment.membership_id).first()
    if m is None:
        return False
    return m.status in (MembershipStatus.ACTIVE, MembershipStatus.GRACE)


def settle_order_enrollments(db: Session, order_id: int) -> tuple[list[int], list[int]]:
    """Undo what this order did to enrollments, and NOTHING else.

    Returns (revoked_course_ids, released_course_ids):
      * revoked  — rows this order created (source NULL/'bundle'), cancelled;
      * released — rows this order merely RESCUED (membership / company seat /
        any other source): order_id un-stamped and status restored, never
        cancelled, because that access is not this order's to take away.

    Idempotent: already-cancelled rows and already-released rows (which no
    longer carry this order_id) are skipped, so a re-run returns ([], []).
    """
    rows = db.query(Enrollment).filter(Enrollment.order_id == order_id).all()
    revoked: list[int] = []
    released: list[int] = []

    for row in rows:
        source = row.enrollment_source
        if source in _ORDER_OWNED_SOURCES:
            if row.enrollment_status != "cancelled":
                row.enrollment_status = "cancelled"
                revoked.append(row.course_id)
            continue

        # Rescued row: hand it back to whatever granted it originally. The
        # un-stamp is what makes this reversible — membership_access can only
        # re-grant rows with a NULL order_id.
        row.order_id = None
        if source == "membership":
            row.enrollment_status = "enrolled" if _membership_is_live(db, row) else "suspended"
        else:
            # company seat (or any other externally-owned source): the grant
            # stands on its own; only the purchase stamp goes away.
            if row.enrollment_status == "cancelled":
                row.enrollment_status = "enrolled"
        released.append(row.course_id)

    return sorted(revoked), sorted(released)


def apply_refund_effects(db: Session, payment: Payment, *,
                         gateway_refund_id: str | None) -> tuple[list[int], list[int]]:
    """Converge local state on 'this payment was refunded and it was
    admin-initiated'. Idempotent — safe from the endpoint AND the webhook,
    any number of times. Returns (revoked, released). Caller commits."""
    now = datetime.now(timezone.utc)
    payment.payment_status = PaymentStatus.REFUNDED
    from app.services.exam_paper_service import revoke_payment
    revoke_payment(db, payment.gateway_payment_id)
    payment.refund_status = "processed"
    if gateway_refund_id and not payment.gateway_refund_id:
        payment.gateway_refund_id = gateway_refund_id
    if payment.refund_processed_at is None:
        payment.refund_processed_at = now
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order is not None:
        order.order_status = OrderStatus.REFUNDED
    return settle_order_enrollments(db, payment.order_id)


def _claim_refund(db: Session, payment: Payment, *, reason: str, actor_id: int) -> bool:
    """Atomically take ownership of this payment's refund.

    ONE conditional UPDATE does the whole guard: it only matches a payment
    that is still COMPLETED and whose refund_status is NULL, 'failed', or a
    STALE 'requested'. Two concurrent callers therefore cannot both proceed —
    the loser's rowcount is 0 and it gets a 409. The claim IS the persisted
    intent required before any gateway call, and the caller commits it.

    Returns True when this caller won the claim.
    """
    now = datetime.now(timezone.utc)
    stale_before = now - STALE_REQUESTED_AFTER
    matched = (
        db.query(Payment)
        .filter(
            Payment.id == payment.id,
            Payment.payment_status == PaymentStatus.COMPLETED,
            or_(
                Payment.refund_status.is_(None),
                Payment.refund_status == "failed",
                # a 'requested' intent this old is crash debris, not in flight
                (Payment.refund_status == "requested")
                & (
                    Payment.refund_requested_at.is_(None)
                    | (Payment.refund_requested_at < stale_before)
                ),
            ),
        )
        .update(
            {
                Payment.refund_status: "requested",
                Payment.refund_reason: reason,
                Payment.refund_requested_by: actor_id,
                Payment.refund_requested_at: now,
                Payment.refund_error: None,
            },
            synchronize_session=False,
        )
    )
    if not matched:
        db.rollback()
        return False
    db.commit()
    db.refresh(payment)
    return True


def refund_order(db: Session, order_id: int, *, reason: str, actor_id: int) -> dict:
    """Full refund of one order. Raises RefundError(404/400/409/502).

    The gateway is reached through the module-level `_gateway_refund` /
    `_gateway_list_refunds` functions (which tests monkeypatch) — there is
    deliberately no injectable parameter on a money-moving entry point.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise RefundError(404, "Order not found")
    if order.order_status == OrderStatus.REFUNDED:
        raise RefundError(409, "Order is already refunded")

    payment = captured_payment(order)
    if payment is None:
        raise NotRefundable(
            "This order has no captured gateway payment (offline / company-invoice / mock "
            "orders must be refunded outside the product); nothing was changed"
        )
    if is_subscription_order(order, payment):
        raise NotRefundable(
            "This is a membership subscription charge. Refunding a single charge would leave "
            "the subscription billing — cancel the membership instead (admin > memberships > "
            "cancel), which stops future charges and settles access; nothing was changed"
        )
    if payment.payment_status == PaymentStatus.REFUNDED:
        raise RefundError(409, "Payment is already refunded")

    amount = refundable_amount(payment)
    if amount <= 0:
        raise NotRefundable(
            "This order captured no money (zero or negative amount), so there is nothing to "
            "refund; nothing was changed"
        )
    amount_paise = to_paise(amount)  # full refund; NEVER from the request

    # A retry is the ONLY case where the gateway may already hold a refund we
    # do not know about: a 'failed' intent (the call may have succeeded and the
    # response been lost) or a STALE 'requested' one (a crash between the
    # gateway call and the local commit). A first attempt cannot, so it skips
    # the extra round-trip.
    is_retry = payment.refund_status in ("failed", "requested")

    # ---- 1. atomic claim = the persisted intent, committed -------------------
    if not _claim_refund(db, payment, reason=reason, actor_id=actor_id):
        raise RefundError(409, "A refund for this order is already in flight")

    # ---- 1b. retry: adopt an existing gateway refund instead of a second one --
    if is_retry:
        try:
            existing = _gateway_list_refunds(payment.gateway_payment_id)
        except Exception as exc:
            # We cannot tell whether money already moved. Refusing is the only
            # safe answer — re-issuing blind risks refunding the customer twice.
            payment.refund_status = "failed"
            payment.refund_error = _sanitize_error(
                f"retry blocked: could not list existing refunds at the gateway "
                f"({type(exc).__name__}: {exc})"
            )
            db.commit()
            logger.warning(
                "refund RETRY BLOCKED order_id=%s payment_id=%s gateway_payment_id=%s "
                "actor_id=%s error=%s",
                order.id, payment.id, payment.gateway_payment_id, actor_id, payment.refund_error,
            )
            raise RefundError(
                502,
                "Could not confirm with the payment gateway whether this refund already "
                "exists; nothing was re-sent and access is intact — retry later",
            )
        match = _matching_existing_refund(existing, amount_paise)
        if match is not None:
            refund_id = str(match.get("id"))
            # Audit: record that this refund was ADOPTED, not newly issued.
            payment.refund_error = _sanitize_error(
                f"adopted existing gateway refund {refund_id} on retry "
                f"(amount_paise={amount_paise}); no new refund was created"
            )
            revoked, released = apply_refund_effects(db, payment, gateway_refund_id=refund_id)
            db.commit()
            logger.info(
                "refund ADOPTED existing gateway refund order_id=%s payment_id=%s "
                "payment_method=%s gateway_refund_id=%s amount_paise=%s actor_id=%s "
                "revoked_course_ids=%s released_course_ids=%s",
                order.id, payment.id, payment.payment_method, payment.gateway_refund_id,
                amount_paise, actor_id, revoked, released,
            )
            return _refund_result(order, payment, amount_paise, revoked, released, adopted=True)

    # ---- 2. gateway -----------------------------------------------------------
    try:
        result = _gateway_refund(payment.gateway_payment_id, amount_paise, reason)
    except Exception as exc:  # the SDK adapter catches today; an upgrade may not
        result = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

    if result.get("status") != "processed":
        payment.refund_status = "failed"
        payment.refund_error = _sanitize_error(result.get("error") or "gateway error")
        db.commit()
        logger.warning(
            "refund FAILED order_id=%s payment_id=%s payment_method=%s actor_id=%s error=%s",
            order.id, payment.id, payment.payment_method, actor_id, payment.refund_error,
        )
        raise RefundError(502, "Refund failed at the payment gateway; access left intact — retry later")

    # ---- 3. converge locally ----------------------------------------------------
    refund_id = str(result.get("refund_id") or "") or None
    if is_retry:
        # Audit: this retry genuinely issued a NEW refund (the gateway reported
        # no pre-existing one for this amount).
        payment.refund_error = _sanitize_error(
            f"retry issued a new gateway refund {refund_id or '?'} "
            f"(no matching existing refund at the gateway)"
        )
    revoked, released = apply_refund_effects(db, payment, gateway_refund_id=refund_id)
    db.commit()
    logger.info(
        "refund processed order_id=%s payment_id=%s payment_method=%s gateway_refund_id=%s "
        "amount_paise=%s actor_id=%s retry=%s revoked_course_ids=%s released_course_ids=%s",
        order.id, payment.id, payment.payment_method, payment.gateway_refund_id,
        amount_paise, actor_id, is_retry, revoked, released,
    )
    return _refund_result(order, payment, amount_paise, revoked, released, adopted=False)


def _refund_result(order: Order, payment: Payment, amount_paise: int,
                   revoked: list[int], released: list[int], *, adopted: bool) -> dict:
    """The endpoint's 200 body. Nullable/"" text columns are read defensively
    so the router never surfaces a bare NULL to the admin UI."""
    return {
        "order_id": order.id,
        "payment_id": payment.id,
        "gateway_payment_id": payment.gateway_payment_id or "",
        "gateway_refund_id": payment.gateway_refund_id or "",
        "amount": float(payment.amount or 0),
        "amount_paise": amount_paise,
        "currency": payment.currency or "INR",
        "status": "refunded",
        # Access this order granted and has now taken back.
        "revoked_course_ids": revoked,
        # Access this order only RESCUED (membership / company seat): handed
        # back to its original owner, deliberately NOT revoked.
        "released_course_ids": released,
        # True when a retry adopted a refund the gateway already held rather
        # than creating a second one (no money moved on this call).
        "adopted_existing_refund": adopted,
    }
