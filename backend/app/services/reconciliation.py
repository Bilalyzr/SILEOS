"""Reconciliation: the safety net behind /verify and the webhook.

Cycle cadence (driven by reconciliation_loop):
  - every RETRY_INTERVAL (5 min): re-run FAILED inbox events, backoff 2^attempts minutes, max 5 attempts
  - every RETRY_INTERVAL (5 min): expire lapsed memberships (grace_until / current_period_end passed)
  - every GATEWAY_DIFF_EVERY cycles (30 min): diff paid gateway orders vs local payments
  - every GATEWAY_DIFF_EVERY cycles (30 min): sync membership catalog (grant access to courses added since activation)

Postgres advisory lock makes the loop replica-safe; the pure functions
below take a Session and are unit-testable without the loop.
"""
import asyncio
import functools
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.membership import Membership, MembershipStatus
from app.models.payment import Payment
from app.models.user import User
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.email_service import EmailService
from app.services.fulfillment_service import (
    fulfill_bundle_purchase,
    fulfill_cart_purchase,
    fulfill_course_purchase,
)
from app.services.cart_checkout import CartSnapshotError, parse_cart_notes
from app.services.invoice_service import settle_invoice
from app.services.pricing import resolve_expected_purchase
from app.services.membership_access import (
    grant_membership_enrollments, suspend_membership_enrollments,
)
from app.services.webhook_processor import process_webhook_event

logger = logging.getLogger(__name__)

RETRY_INTERVAL_SECONDS = 300
GATEWAY_DIFF_EVERY = 6          # 6 * 5 min = 30 min
MAX_ATTEMPTS = 5
ADVISORY_LOCK_KEY = 931842
# A PENDING membership is a checkout that was started but never confirmed by a
# subscription.activated webhook. Well past any plausible payment-authorization
# window it is an abandoned checkout, and leaving it PENDING blocks the user's
# next /subscribe. 48h is generous enough for delayed mandate confirmations.
PENDING_ABANDON_HOURS = 48


def retry_failed_events(db: Session) -> int:
    """Reprocess eligible FAILED events. Returns number reprocessed."""
    now = datetime.now(timezone.utc)
    candidates = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.status == WebhookEventStatus.FAILED,
            WebhookEvent.attempts < MAX_ATTEMPTS,
            WebhookEvent.signature_valid.is_(True),
        )
        .all()
    )
    count = 0
    for ev in candidates:
        backoff = timedelta(minutes=2 ** (ev.attempts or 0))
        last = ev.last_attempt_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last is not None and now - last < backoff:
            continue
        process_webhook_event(db, ev)
        count += 1
        if ev.status == WebhookEventStatus.FAILED and (ev.attempts or 0) >= MAX_ATTEMPTS:
            # Fires exactly once per event: the next query excludes rows with
            # attempts >= MAX_ATTEMPTS, so this event is never swept again.
            EmailService.send_payment_alert(
                f"webhook event {ev.event_id} exhausted retries",
                f"type={ev.event_type} attempts={ev.attempts} "
                f"last_error={ev.last_error}",
            )
    return count


def reconcile_gateway_orders(db: Session, client, lookback_hours: int = 24) -> int:
    """Fulfill paid gateway orders that have no local Payment row.
    Returns number fulfilled. Alerts (never raises) on unusable orders."""
    since = int(time.time()) - lookback_hours * 3600
    try:
        orders = (client.order.all({"from": since, "count": 100}) or {}).get("items", [])
    except Exception:
        logger.exception("gateway order listing failed")
        return 0

    fulfilled = 0
    for order in orders:
        if order.get("status") != "paid":
            continue
        try:
            payments = (client.order.payments(order["id"]) or {}).get("items", [])
        except Exception:
            logger.exception("payments fetch failed for %s", order.get("id"))
            continue
        captured = next((p for p in payments if p.get("status") == "captured"), None)
        if not captured:
            continue
        pay_id = str(captured.get("id"))
        if db.query(Payment).filter(Payment.gateway_payment_id == pay_id).first():
            continue  # already fulfilled

        notes = order.get("notes") or {}
        from app.models.exam_paper import ExamPaper
        from app.services.exam_paper_service import fulfill_capture
        paper = db.query(ExamPaper).filter(ExamPaper.gateway_order_id == str(order['id'])).first()
        if paper is not None:
            try:
                fulfill_capture(db, paper, captured)
                db.commit()
                fulfilled += 1
            except Exception:
                db.rollback()
                logger.exception('Exam paper capture could not be reconciled: %s', pay_id)
            continue
        if notes.get("edgyy_registration_id") or notes.get("source") == "edgyy.in":
            # Edgyy proxy orders never get a local Payment row; they are
            # reconciled through their own webhook_events path. Alerting here
            # would page on every Edgyy sale for 24h.
            continue

        if notes.get("checkout_type") == "cart" or notes.get("cart_lines"):
            from app.models.coupon import Coupon

            try:
                user_id = int(notes.get("user_id"))
                snapshot = parse_cart_notes(notes)
            except (TypeError, ValueError, CartSnapshotError) as exc:
                EmailService.send_payment_alert(
                    f"orphaned cart capture {pay_id} — unusable notes",
                    f"gateway order {order.get('id')} notes={notes!r} "
                    f"error={exc}. Fulfil manually.",
                )
                continue
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                EmailService.send_payment_alert(
                    f"orphaned cart capture {pay_id} — user missing",
                    f"user_id={user_id} gateway order {order.get('id')}. "
                    "Fulfil manually.",
                )
                continue
            captured_paise = int(captured.get("amount") or 0)
            if captured_paise != snapshot.total_paise:
                EmailService.send_payment_alert(
                    f"orphaned cart capture {pay_id} — amount mismatch",
                    f"expected_paise={snapshot.total_paise} "
                    f"captured_paise={captured_paise} "
                    f"course_ids={snapshot.course_ids}. Fulfil manually.",
                )
                continue
            coupon = None
            if snapshot.coupon_id is not None:
                candidate = db.query(Coupon).filter(
                    Coupon.id == snapshot.coupon_id
                ).first()
                if candidate is not None and candidate.code.upper() == snapshot.coupon_code:
                    coupon = candidate
            try:
                fulfill_cart_purchase(
                    db,
                    user=user,
                    line_prices_paise=snapshot.line_prices_paise,
                    razorpay_order_id=str(order["id"]),
                    razorpay_payment_id=pay_id,
                    paid_amount=captured_paise / 100.0,
                    coupon_discount=snapshot.discount_paise / 100.0,
                    currency=str(captured.get("currency") or "INR"),
                    coupon=coupon,
                )
                db.commit()
                fulfilled += 1
                logger.warning(
                    "reconciliation fulfilled orphaned cart capture %s "
                    "(user %s, courses %s)",
                    pay_id, user_id, snapshot.course_ids,
                )
            except Exception as exc:
                db.rollback()
                logger.exception(
                    "reconciliation cart fulfillment failed for %s", pay_id
                )
                EmailService.send_payment_alert(
                    f"reconciliation failed for cart capture {pay_id}",
                    f"error: {exc}. Fulfil manually.",
                )
            continue

        if notes.get("bundle_id"):
            try:
                user_id = int(notes.get("user_id"))
                bundle_id = int(notes.get("bundle_id"))
                course_ids = [int(x) for x in
                              str(notes.get("bundle_course_ids") or "").split(",") if x]
            except (TypeError, ValueError):
                EmailService.send_payment_alert(
                    f"orphaned bundle capture {pay_id} — unusable notes",
                    f"gateway order {order.get('id')} amount={order.get('amount')} "
                    f"notes={notes!r}. Fulfil manually.",
                )
                continue
            if not course_ids:
                EmailService.send_payment_alert(
                    f"orphaned bundle capture {pay_id} — no course snapshot",
                    f"gateway order {order.get('id')} amount={order.get('amount')} "
                    f"notes={notes!r}. Fulfil manually.",
                )
                continue
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                EmailService.send_payment_alert(
                    f"orphaned bundle capture {pay_id} — user missing",
                    f"user_id={user_id} bundle_id={bundle_id} "
                    f"gateway order {order.get('id')}. Fulfil manually.",
                )
                continue
            try:
                fulfill_bundle_purchase(
                    db, user=user, bundle_id=bundle_id, course_ids=course_ids,
                    razorpay_order_id=str(order["id"]),
                    razorpay_payment_id=pay_id,
                    paid_amount=int(captured.get("amount") or 0) / 100.0,
                    currency=str(captured.get("currency") or "INR"),
                )
                db.commit()
                fulfilled += 1
                logger.warning(
                    "reconciliation fulfilled orphaned bundle capture %s "
                    "(user %s, bundle %s)", pay_id, user_id, bundle_id,
                )
            except Exception as exc:
                db.rollback()
                logger.exception("reconciliation bundle fulfillment failed for %s", pay_id)
                EmailService.send_payment_alert(
                    f"reconciliation failed for bundle capture {pay_id}",
                    f"error: {exc}. Fulfil manually.",
                )
            continue

        if notes.get("ebook_id"):
            # Third leg of the ebook triple-redundancy: same
            # fulfill_ebook_purchase, same ebook_price_inr notes snapshot as
            # /verify and the webhook processor.
            from app.models.ebook import Ebook, snapshot_prices_from_notes
            from app.services.fulfillment_service import fulfill_ebook_purchase
            try:
                user_id = int(notes.get("user_id"))
                ebook_id = int(notes.get("ebook_id"))
            except (TypeError, ValueError):
                EmailService.send_payment_alert(
                    f"orphaned ebook capture {pay_id} — unusable notes",
                    f"gateway order {order.get('id')} amount={order.get('amount')} "
                    f"notes={notes!r}. Fulfil manually.",
                )
                continue
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                EmailService.send_payment_alert(
                    f"orphaned ebook capture {pay_id} — user missing",
                    f"user_id={user_id} ebook_id={ebook_id} "
                    f"gateway order {order.get('id')}. Fulfil manually.",
                )
                continue
            try:
                ebook = db.query(Ebook).filter(Ebook.id == ebook_id).first()
                _, list_inr = snapshot_prices_from_notes(notes, ebook)
                fulfill_ebook_purchase(
                    db, user=user, ebook_id=ebook_id,
                    razorpay_order_id=str(order["id"]),
                    razorpay_payment_id=pay_id,
                    paid_amount=int(captured.get("amount") or 0) / 100.0,
                    list_price_inr=list_inr,
                    currency=str(captured.get("currency") or "INR"),
                )
                db.commit()
                fulfilled += 1
                logger.warning(
                    "reconciliation fulfilled orphaned ebook capture %s "
                    "(user %s, ebook %s)", pay_id, user_id, ebook_id,
                )
            except Exception as exc:
                db.rollback()
                logger.exception(
                    "reconciliation ebook fulfillment failed for %s", pay_id)
                EmailService.send_payment_alert(
                    f"reconciliation failed for ebook capture {pay_id}",
                    f"error: {exc}. Fulfil manually.",
                )
            continue

        if notes.get("invoice_id"):
            try:
                invoice_id = int(notes.get("invoice_id"))
            except (TypeError, ValueError):
                EmailService.send_payment_alert(
                    f"orphaned invoice capture {pay_id} — unusable notes",
                    f"gateway order {order.get('id')} amount={order.get('amount')} "
                    f"notes={notes!r}. Fulfil manually.",
                )
                continue
            from app.models.company_invoice import CompanyInvoice, InvoiceStatus
            invoice = db.query(CompanyInvoice).filter(
                CompanyInvoice.id == invoice_id).first()
            if not invoice:
                EmailService.send_payment_alert(
                    f"orphaned invoice capture {pay_id} — invoice missing",
                    f"invoice_id={invoice_id} gateway order {order.get('id')}. "
                    "Fulfil manually.",
                )
                continue

            captured_paise = int(captured.get("amount") or 0)
            expected_paise = max(int(round(float(invoice.total) * 100)), 100)
            if captured_paise != expected_paise:
                EmailService.send_payment_alert(
                    f"captured amount mismatch for invoice {invoice_id} capture {pay_id}",
                    f"invoice_number={invoice.invoice_number} status={invoice.status.value} "
                    f"expected_paise={expected_paise} captured_paise={captured_paise}. "
                    "Not settled — investigate manually.",
                )
                continue

            try:
                settled = settle_invoice(
                    db, invoice, via="razorpay", reference=pay_id,
                    gateway_payment_id=pay_id,
                    gateway_order_id=str(order["id"]),
                )
                if settled:
                    db.commit()
                    fulfilled += 1
                    logger.warning(
                        "reconciliation settled orphaned invoice capture %s "
                        "(invoice %s)", pay_id, invoice_id,
                    )
                else:
                    db.rollback()
                    if invoice.status != InvoiceStatus.PAID:
                        # Money captured but the invoice can't be settled
                        # (draft/cancelled/etc.) — must never be silent.
                        # Already-PAID is a genuine idempotent replay.
                        EmailService.send_payment_alert(
                            f"orphaned capture for unsettleable invoice {invoice_id}",
                            f"invoice_number={invoice.invoice_number} "
                            f"status={invoice.status.value} payment_id={pay_id} "
                            f"amount_paise={captured_paise}. Investigate manually.",
                        )
            except Exception as exc:
                db.rollback()
                logger.exception("reconciliation invoice settlement failed for %s", pay_id)
                EmailService.send_payment_alert(
                    f"reconciliation failed for invoice capture {pay_id}",
                    f"error: {exc}. Fulfil manually.",
                )
            continue

        try:
            user_id = int(notes.get("user_id"))
            course_id = int(notes.get("course_id"))
        except (TypeError, ValueError):
            EmailService.send_payment_alert(
                f"orphaned capture {pay_id} — unusable notes",
                f"gateway order {order.get('id')} amount={order.get('amount')} "
                f"notes={notes!r}. Fulfil manually.",
            )
            continue
        user = db.query(User).filter(User.id == user_id).first()
        course = db.query(Course).filter(Course.id == course_id).first()
        if not user or not course:
            EmailService.send_payment_alert(
                f"orphaned capture {pay_id} — user/course missing",
                f"user_id={user_id} course_id={course_id} "
                f"gateway order {order.get('id')}. Fulfil manually.",
            )
            continue
        try:
            paid_amount = int(captured.get("amount") or 0) / 100.0
            gateway_order_id = str(order["id"])

            # Single source of truth shared with /verify and the webhook
            # handler — see webhook_processor.py's identical call (audit A5
            # follow-up, platform audit 2026-09-03 round 3). Never trusts a
            # cohort_id note that doesn't belong to THIS course, and skips
            # an implausible seat-price override rather than corrupting the
            # written Order row.
            expected = resolve_expected_purchase(
                db, course, notes, user_id=user_id,
                paid_amount=paid_amount, order_id=gateway_order_id,
            )
            # subtotal_price (pre-discount), not expected_price (net of a
            # coupon's discount) — see ExpectedPurchase's docstring.
            base_price = float(expected.subtotal_price)
            coupon_discount = (
                float(expected.coupon_discount) if expected.is_coupon
                else max(0.0, base_price - paid_amount)
            )

            fulfill_course_purchase(
                db, user=user, course=course,
                razorpay_order_id=gateway_order_id,
                razorpay_payment_id=pay_id,
                paid_amount=paid_amount, base_price=base_price,
                coupon_discount=coupon_discount,
                currency=str(captured.get("currency") or "INR"),
                cohort=expected.cohort,
                referral_code_id=expected.referral_code_id,
            )
            db.commit()
            fulfilled += 1
            logger.warning(
                "reconciliation fulfilled orphaned capture %s (user %s, course %s)",
                pay_id, user_id, course_id,
            )
        except Exception as exc:
            db.rollback()
            logger.exception("reconciliation fulfillment failed for %s", pay_id)
            EmailService.send_payment_alert(
                f"reconciliation failed for capture {pay_id}",
                f"error: {exc}. Fulfil manually.",
            )
    return fulfilled


def _expire_abandoned_pending(db: Session, now: datetime) -> int:
    """Cancel PENDING memberships older than PENDING_ABANDON_HOURS.

    No enrollment changes: a PENDING membership never granted any. Per-row
    fault isolation, same as the rest of the pass.
    """
    cutoff = now - timedelta(hours=PENDING_ABANDON_HOURS)
    count = 0
    for m in db.query(Membership).filter(
            Membership.status == MembershipStatus.PENDING).all():
        try:
            created = m.created_at
            if created is None:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created >= cutoff:
                continue
            m.status = MembershipStatus.CANCELLED
            db.commit()
            count += 1
            logger.info("membership %s: abandoned checkout discarded "
                        "(pending since %s)", m.id, created)
        except Exception:
            db.rollback()
            logger.exception(
                "_expire_abandoned_pending failed for membership %s", m.id)
    return count


def expire_lapsed_memberships(db: Session) -> int:
    """Suspend memberships whose grace or paid period has run out, and discard
    abandoned checkouts.

    Never raises: each membership is isolated so one bad row can't block
    expiry for the rest of the pass (mirrors reconcile_gateway_orders).
    """
    now = datetime.now(timezone.utc)
    count = 0
    count += _expire_abandoned_pending(db, now)
    graced = db.query(Membership).filter(
        Membership.status == MembershipStatus.GRACE,
        Membership.grace_until.isnot(None),
    ).all()
    ended = db.query(Membership).filter(
        Membership.status.in_([MembershipStatus.CANCELLED,
                               MembershipStatus.COMPLETED]),
        Membership.current_period_end.isnot(None),
    ).all()
    for m in graced + ended:
        try:
            deadline = m.grace_until if m.status == MembershipStatus.GRACE else m.current_period_end
            if deadline is not None and deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if deadline is None or deadline > now:
                continue
            suspended = suspend_membership_enrollments(db, m)
            if m.status == MembershipStatus.GRACE:
                m.status = MembershipStatus.SUSPENDED
            elif suspended == 0:
                continue  # cancelled/completed with nothing left to suspend
            db.commit()
            count += 1
            logger.info("membership %s lapsed; %s enrollments suspended", m.id, suspended)
        except Exception:
            db.rollback()
            logger.exception("expire_lapsed_memberships failed for membership %s", m.id)
    return count


def sync_membership_catalog(db: Session) -> int:
    """Grant enrollments for courses added since a membership activated.

    Never raises: each membership is isolated so one bad row can't block
    catalog sync for the rest of the pass (mirrors reconcile_gateway_orders).
    """
    granted = 0
    active = db.query(Membership).filter(
        Membership.status == MembershipStatus.ACTIVE).all()
    for m in active:
        try:
            n = grant_membership_enrollments(db, m)
            if n:
                db.commit()
                granted += n
        except Exception:
            db.rollback()
            logger.exception("sync_membership_catalog failed for membership %s", m.id)
    return granted


def _run_cycle(cycle_index: int) -> None:
    """One synchronous sweep. Own session; advisory-locked on Postgres.

    The pg advisory lock is session-level and therefore CONNECTION-scoped.
    The work session commits mid-cycle, which returns its connection to the
    pool, so a lock taken on it could be unlocked on a different connection
    and leak. Hold the lock on a dedicated raw connection for the whole cycle
    instead, separate from the work session.
    """
    from app.core.database import SessionLocal, engine
    lock_conn = None
    if engine.dialect.name == "postgresql":
        lock_conn = engine.connect()
        try:
            locked = lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:k)"), {"k": ADVISORY_LOCK_KEY}
            ).scalar()
        except Exception:
            lock_conn.close()
            raise
        if not locked:
            lock_conn.close()
            return  # another replica holds the lock

    db = SessionLocal()
    try:
        retry_failed_events(db)
        expire_lapsed_memberships(db)
        if cycle_index % GATEWAY_DIFF_EVERY == 0:
            client = _gateway_client()
            if client is not None:
                reconcile_gateway_orders(db, client)
            sync_membership_catalog(db)
        from app.services.operations_service import heartbeat
        heartbeat("payment_reconciliation", "ok")
    finally:
        db.close()
        if lock_conn is not None:
            try:
                lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:k)"), {"k": ADVISORY_LOCK_KEY}
                )
            finally:
                lock_conn.close()


def _gateway_client():
    from app.routers.payments import _razorpay_creds
    import razorpay
    key_id, key_secret = _razorpay_creds()
    if not key_id or not key_secret:
        return None
    client = razorpay.Client(auth=(key_id, key_secret))
    # The SDK's requests.Session has no default timeout: a hung gateway would
    # block the sweeper thread forever. Bound every call at 30s.
    client.session.request = functools.partial(client.session.request, timeout=30)
    return client


async def reconciliation_loop() -> None:
    cycle = 0
    while True:
        try:
            await asyncio.to_thread(_run_cycle, cycle)
        except Exception:
            logger.exception("reconciliation cycle crashed (continuing)")
            from app.services.operations_service import heartbeat
            heartbeat("payment_reconciliation", "error")
        cycle += 1
        await asyncio.sleep(RETRY_INTERVAL_SECONDS)
