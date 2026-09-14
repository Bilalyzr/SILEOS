"""
Fulfillment Service - SashaInfinity LMS

Shared idempotent Order/Payment/Enrollment write block, extracted from
`/verify` in `app.routers.payments`. Money trail write only — this
service does NOT commit; the caller owns commit/rollback and decides
how to map a propagated `CouponError` (from `lock_referral_and_bump`)
to an HTTP response.

Keyed on the gateway payment id (not on the enrollment) so a replay of
the caller's verify/confirm flow can never create a second order or
double-count revenue.

A genuinely concurrent race (two callers past the exists-check at once) is
resolved by the partial unique index `uq_payments_gateway_payment_id`: the
loser's whole transaction (Order + Payment + Enrollment) fails at commit, so
/verify returns its generic 500 while the winner has already enrolled the
buyer, and the webhook side marks the event FAILED and no-ops on the
sweeper's retry via the Payment-exists check above.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.cohort import Cohort, CohortMembership
from app.models.coupon import Coupon, CouponUsage
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.payment import (
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentStatus,
)
from app.models.user import User
from app.core.business_verticals import revenue_metadata
from app.services.coupon_service import lock_referral_and_bump

logger = logging.getLogger(__name__)


@dataclass
class FulfillmentResult:
    created_order: bool          # False when payment id already had an Order (no-op replay)
    order_id: int
    is_new_enrollment: bool
    cohort_id: int | None


def grant_purchased_course(
    db: Session, *, user_id: int, course_id: int, order_id: int, source: str,
) -> bool:
    """Grant (or rescue) access to one purchased course. Shared by every
    purchase-style fulfillment path (bundle rescue loop, company invoice
    settlement) that needs "enroll or rescue a suspended row" semantics.

    An existing (user, course) row is RESCUED rather than skipped: status
    flips to "enrolled" if it wasn't already, and a NULL order_id is stamped
    with this order — that stamp is load-bearing, see
    `fulfill_bundle_purchase`'s docstring for why (membership-suspension
    exemption). `enrollment_source` is NEVER rewritten on an existing row —
    a rescued row keeps whatever source first created it.

    No existing row: create one with the given `source`, stamp order_id,
    and bump Course.total_enrollments.

    Returns True only when access genuinely changed for this user (newly
    created, or rescued from a non-enrolled status) — never when the row
    was already enrolled (that's a no-op re-grant, not a rescue).
    """
    row = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == user_id,
    ).first()

    if row is not None:
        was_enrolled = row.enrollment_status == "enrolled"
        if not was_enrolled:
            row.enrollment_status = "enrolled"
        if not row.order_id:
            row.order_id = order_id
        return not was_enrolled

    db.add(Enrollment(
        course_id=course_id, user_id=user_id,
        enrollment_status="enrolled",
        enrollment_source=source,
        order_id=order_id,
    ))
    db.query(Course).filter(Course.id == course_id).update(
        {Course.total_enrollments: (Course.total_enrollments or 0) + 1},
        synchronize_session=False,
    )
    return True


def fulfill_course_purchase(
    db: Session,
    *,
    user: User,
    course: Course,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    paid_amount: float,          # rupees actually captured
    base_price: float,           # price offered pre-coupon: effective
                                  # (sale, if any) price, or the seat price
                                  # when a cohort seat-price override applies
    coupon_discount: float = 0.0,
    currency: str = "INR",
    cohort: Cohort | None = None,
    referral_code_id: int | None = None,
    coupon: "Coupon | None" = None,   # when set, records CouponUsage + bumps usage_count
) -> FulfillmentResult:
    """Write the idempotent Order/Payment/Enrollment trail for a successful
    course purchase. Does not commit — caller owns commit/rollback. May
    raise `CouponError` (propagated from `lock_referral_and_bump` if the
    referral code was exhausted after payment); callers decide policy.
    """
    # Persist the money trail. Buy-Now previously recorded only an
    # Enrollment, so the amount actually paid was never stored: purchase
    # history, /admin/orders and revenue all fell back to
    # course.course_price and showed the pre-coupon list price.
    # Keyed on the gateway payment id (not on the enrollment) so a replay
    # of /verify can never create a second order or double-count revenue.
    order_row = db.query(Order).join(Payment, Payment.order_id == Order.id).filter(
        Payment.gateway_payment_id == str(razorpay_payment_id)
    ).first()

    created_order = order_row is None

    if order_row is None:
        order_currency = currency or "INR"
        order_row = Order(
            user_id=user.id,
            order_key=f"RZP_{uuid.uuid4().hex[:12].upper()}",
            order_status=OrderStatus.COMPLETED,
            currency=order_currency,
            subtotal_amount=base_price,      # list price before any coupon
            discount_amount=coupon_discount,
            total_amount=paid_amount,        # what actually changed hands
            payment_method="razorpay",
            payment_method_title="Razorpay",
            transaction_id=str(razorpay_payment_id),
            billing_email=user.user_email or "",
            date_paid=datetime.now(timezone.utc),
            date_completed=datetime.now(timezone.utc),
        )
        db.add(order_row)
        db.flush()  # assign order_row.id

        db.add(OrderItem(
            order_id=order_row.id,
            course_id=course.id,
            order_item_name=course.post_title or f"Course {course.id}",
            order_item_type="line_item",
            quantity=1,
            subtotal=base_price,
            total=paid_amount,
            product_data=revenue_metadata(course.course_type),
        ))
        db.add(Payment(
            user_id=user.id,
            order_id=order_row.id,
            payment_method="razorpay",
            gateway_transaction_id=str(razorpay_payment_id),
            gateway_payment_id=str(razorpay_payment_id),
            gateway_order_id=str(razorpay_order_id),
            amount=paid_amount,
            currency=order_currency,
            payment_status=PaymentStatus.COMPLETED,
            processed_date=datetime.now(timezone.utc),
        ))

    existing = db.query(Enrollment).filter(
        Enrollment.course_id == course.id,
        Enrollment.user_id == user.id,
    ).first()

    is_new_enrollment = existing is None

    if existing:
        existing.enrollment_status = "enrolled"
        if cohort and not existing.cohort_id:
            existing.cohort_id = cohort.id
        if not existing.order_id:
            existing.order_id = order_row.id
    else:
        db.add(Enrollment(
            course_id=course.id,
            user_id=user.id,
            enrollment_status="enrolled",
            order_id=order_row.id,
            cohort_id=cohort.id if cohort else None,
        ))
        db.query(Course).filter(Course.id == course.id).update(
            {Course.total_enrollments: (Course.total_enrollments or 0) + 1},
            synchronize_session=False,
        )

    # Idempotent CohortMembership.
    if cohort:
        already_member = db.query(CohortMembership).filter(
            CohortMembership.cohort_id == cohort.id,
            CohortMembership.user_id == user.id,
        ).first()
        if not already_member:
            db.add(CohortMembership(
                cohort_id=cohort.id,
                user_id=user.id,
            ))

    # Atomically bump ReferralCode.used_count ONLY on new enrollment
    # so a retry/replay of /verify on the same successful payment
    # can't inflate used_count.
    if is_new_enrollment and referral_code_id:
        lock_referral_and_bump(db, int(referral_code_id))

    # Record coupon redemption so per-user-limit and usage analytics
    # apply to the Buy-Now flow the same way they do for the cart/orders path.
    # Only for new enrollments to keep it idempotent on retries.
    if is_new_enrollment and coupon is not None:
        db.add(CouponUsage(
            coupon_id=coupon.id,
            user_id=user.id,
            order_id=order_row.id,
            discount_amount=coupon_discount,
        ))
        # Keep usage_count in sync for admin analytics.
        coupon.usage_count = (coupon.usage_count or 0) + 1

    return FulfillmentResult(
        created_order=created_order,
        order_id=order_row.id,
        is_new_enrollment=is_new_enrollment,
        cohort_id=cohort.id if cohort else None,
    )


def fulfill_cart_purchase(
    db: Session,
    *,
    user: User,
    line_prices_paise: dict[int, int],
    razorpay_order_id: str,
    razorpay_payment_id: str,
    paid_amount: float,
    coupon_discount: float = 0.0,
    currency: str = "INR",
    coupon: Coupon | None = None,
) -> FulfillmentResult:
    """Write one paid multi-course cart and grant every snapshotted course.

    Prices are the immutable checkout-time amounts from the gateway order
    notes, expressed in paise.  Like the other fulfillment functions this is
    idempotent on ``gateway_payment_id`` and deliberately does not commit.
    """
    order_row = db.query(Order).join(Payment, Payment.order_id == Order.id).filter(
        Payment.gateway_payment_id == str(razorpay_payment_id)
    ).first()
    created_order = order_row is None
    if order_row is not None and order_row.user_id != user.id:
        raise ValueError("Gateway payment already belongs to another user")

    unique_ids = list(dict.fromkeys(int(cid) for cid in line_prices_paise))
    courses = db.query(Course).filter(Course.id.in_(unique_ids)).all()
    found = {course.id: course for course in courses}
    course_list = [found[cid] for cid in unique_ids if cid in found]
    missing = [cid for cid in unique_ids if cid not in found]

    snapshot_subtotal = sum(int(value) for value in line_prices_paise.values()) / 100.0
    if abs((snapshot_subtotal - float(coupon_discount)) - float(paid_amount)) > 0.011:
        raise ValueError("Cart payment does not reconcile with its snapshot")

    if missing:
        from app.services.email_service import EmailService

        logger.error(
            "cart fulfillment: deleted courses %s (user=%s payment=%s)",
            missing, user.id, razorpay_payment_id,
        )
        EmailService.send_payment_alert(
            "cart payment references deleted courses",
            f"user_id={user.id}\nrazorpay_payment_id={razorpay_payment_id}\n"
            f"razorpay_order_id={razorpay_order_id}\nmissing course_ids={missing}\n"
            "The payment trail was preserved and remaining courses were granted. "
            "Refund or hand-grant the missing lines.",
        )

    if created_order:
        now = datetime.now(timezone.utc)
        order_row = Order(
            user_id=user.id,
            order_key=f"CRT_{uuid.uuid4().hex[:12].upper()}",
            order_status=OrderStatus.COMPLETED,
            currency=currency or "INR",
            subtotal_amount=snapshot_subtotal,
            discount_amount=coupon_discount,
            total_amount=paid_amount,
            payment_method="razorpay_cart",
            payment_method_title="Razorpay (cart)",
            transaction_id=str(razorpay_payment_id),
            billing_email=user.user_email or "",
            date_paid=now,
            date_completed=now,
        )
        db.add(order_row)
        db.flush()

        # Allocate the captured amount across the surviving course lines in
        # proportion to their checkout prices.  The final line absorbs paise
        # rounding so per-vertical revenue sums exactly to the payment.
        found_weight = sum(line_prices_paise[c.id] for c in course_list)
        remaining = round(float(paid_amount), 2)
        for index, course in enumerate(course_list):
            line_subtotal = line_prices_paise[course.id] / 100.0
            if index == len(course_list) - 1:
                line_total = remaining
            else:
                weight = (
                    line_prices_paise[course.id] / found_weight
                    if found_weight else 1 / max(len(course_list), 1)
                )
                line_total = round(float(paid_amount) * weight, 2)
                remaining = round(remaining - line_total, 2)
            db.add(OrderItem(
                order_id=order_row.id,
                course_id=course.id,
                order_item_name=course.post_title or f"Course {course.id}",
                order_item_type="cart_item",
                quantity=1,
                subtotal=line_subtotal,
                total=line_total,
                product_data=revenue_metadata(course.course_type),
            ))

        db.add(Payment(
            user_id=user.id,
            order_id=order_row.id,
            payment_method="razorpay_cart",
            gateway_transaction_id=str(razorpay_payment_id),
            gateway_payment_id=str(razorpay_payment_id),
            gateway_order_id=str(razorpay_order_id),
            amount=paid_amount,
            currency=currency or "INR",
            payment_status=PaymentStatus.COMPLETED,
            processed_date=now,
        ))

        if coupon is not None:
            db.add(CouponUsage(
                coupon_id=coupon.id,
                user_id=user.id,
                order_id=order_row.id,
                discount_amount=coupon_discount,
            ))
            coupon.usage_count = (coupon.usage_count or 0) + 1

    any_new = False
    for course in course_list:
        if grant_purchased_course(
            db,
            user_id=user.id,
            course_id=course.id,
            order_id=order_row.id,
            source="cart",
        ):
            any_new = True

    return FulfillmentResult(
        created_order=created_order,
        order_id=order_row.id,
        is_new_enrollment=any_new,
        cohort_id=None,
    )


def fulfill_bundle_purchase(
    db: Session, *,
    user: User,
    bundle_id: int,
    course_ids: list[int],
    razorpay_order_id: str,
    razorpay_payment_id: str,
    paid_amount: float,
    currency: str = "INR",
) -> FulfillmentResult:
    """Grant every course in a purchased bundle. Idempotent on
    gateway_payment_id; bundle enrollments carry order_id (they are
    purchases — never suspendable).

    An existing (user, course) row is RESCUED rather than skipped, mirroring
    `fulfill_course_purchase`: status flips back to "enrolled" and a NULL
    order_id is stamped with this order. That stamp is load-bearing — a
    suspended membership row (source="membership", order_id NULL) is exactly
    what the create-order guard lets a user pay for, and per the memberships
    contract in `membership_access.suspend_membership_enrollments` an
    order_id makes the row permanently exempt from re-suspension.
    `enrollment_source` is never rewritten: a rescued membership row keeps
    its source and simply gains a purchase's protection."""
    order_row = db.query(Order).join(Payment, Payment.order_id == Order.id).filter(
        Payment.gateway_payment_id == str(razorpay_payment_id)
    ).first()
    created_order = order_row is None

    unique_course_ids = list(dict.fromkeys(course_ids))  # order-preserving dedupe:
    # BundleCourse has no unique (bundle_id, course_id) constraint, and
    # webhook/sweeper callers parse course_ids from an order-notes string, so
    # duplicates are possible. Without dedupe: duplicate OrderItems split
    # revenue against an inflated combined price, Order.subtotal_amount is
    # fictitious, the same course gets two Enrollment rows, and
    # total_enrollments is double-bumped.
    courses = db.query(Course).filter(Course.id.in_(unique_course_ids)).all()
    found = {c.id: c for c in courses}
    for missing in set(unique_course_ids) - set(found):
        logger.warning("bundle %s fulfillment: course %s missing, skipped",
                       bundle_id, missing)
    course_list = [found[cid] for cid in unique_course_ids if cid in found]
    if not course_list:
        # Money moved but NOTHING is grantable — every snapshot id is gone.
        # The Order+Payment are still written below (the capture is real and
        # must stay reconcilable); this alert is the trigger for a human to
        # refund or hand-grant.
        from app.services.email_service import EmailService
        logger.error(
            "bundle %s fulfillment: no resolvable courses (user=%s payment=%s "
            "snapshot=%s) — order written with zero enrollments",
            bundle_id, user.id, razorpay_payment_id, unique_course_ids,
        )
        EmailService.send_payment_alert(
            "bundle payment with no resolvable courses",
            f"bundle_id={bundle_id} user_id={user.id}\n"
            f"razorpay_payment_id={razorpay_payment_id}\n"
            f"razorpay_order_id={razorpay_order_id}\n"
            f"paid_amount={paid_amount} {currency}\n"
            f"snapshot course_ids={unique_course_ids}\n"
            "Order + Payment were written; ZERO enrollments granted. "
            "Refund or grant access manually.",
        )
    combined = sum(float(c.course_price or 0) for c in course_list) or 1.0

    if created_order:
        order_row = Order(
            user_id=user.id,
            bundle_id=bundle_id,
            order_key=f"BND_{uuid.uuid4().hex[:12].upper()}",
            order_status=OrderStatus.COMPLETED,
            currency=currency,
            subtotal_amount=combined,
            total_amount=paid_amount,
            payment_method="razorpay_bundle",
            payment_method_title="Razorpay (bundle)",
            transaction_id=str(razorpay_payment_id),
            billing_email=user.user_email or "",
            date_paid=datetime.now(timezone.utc),
            date_completed=datetime.now(timezone.utc),
        )
        db.add(order_row)
        db.flush()

        remaining = round(paid_amount, 2)
        for i, c in enumerate(course_list):
            list_price = float(c.course_price or 0)
            if i < len(course_list) - 1:
                share = round(paid_amount * (list_price / combined), 2)
                remaining = round(remaining - share, 2)
            else:
                share = remaining  # last item absorbs rounding
            db.add(OrderItem(
                order_id=order_row.id, course_id=c.id,
                order_item_name=c.post_title or f"Course {c.id}",
                order_item_type="bundle_item", quantity=1,
                subtotal=list_price, total=share,
                product_data=revenue_metadata(c.course_type),
            ))
        db.add(Payment(
            user_id=user.id, order_id=order_row.id,
            payment_method="razorpay_bundle",
            gateway_transaction_id=str(razorpay_payment_id),
            gateway_payment_id=str(razorpay_payment_id),
            gateway_order_id=str(razorpay_order_id),
            amount=paid_amount, currency=currency,
            payment_status=PaymentStatus.COMPLETED,
            processed_date=datetime.now(timezone.utc),
        ))

    # A replay with a wider course_ids grants the new courses against the
    # existing order — intentional self-healing; the grant is deliberately
    # not gated on created_order.
    any_new = False
    for c in course_list:
        if grant_purchased_course(db, user_id=user.id, course_id=c.id,
                                  order_id=order_row.id, source="bundle"):
            any_new = True

    return FulfillmentResult(
        created_order=created_order, order_id=order_row.id,
        is_new_enrollment=any_new, cohort_id=None,
    )


def grant_ebook(
    db: Session, *, ebook_id: int, user_id: int,
    order_id: "int | None", source: str,
) -> bool:
    """Get-or-create one EbookGrant. UNIQUE(ebook_id, user_id) backs the
    race: the loser's transaction fails at commit exactly like the
    gateway_payment_id partial unique index does for payments.

    An existing grant is a no-op EXCEPT that a NULL order_id is stamped with
    this order — a free-claim row later purchased keeps one row, now tied to
    the money trail. `source` is NEVER rewritten on an existing row (mirrors
    `grant_purchased_course`'s enrollment_source rule): an admin hand-grant
    that is later paid for keeps source="admin" and simply gains the money
    trail.

    Returns True only when a new grant was created."""
    from app.models.ebook import EbookGrant

    row = db.query(EbookGrant).filter(
        EbookGrant.ebook_id == ebook_id,
        EbookGrant.user_id == user_id,
    ).first()
    if row is not None:
        if order_id and not row.order_id:
            row.order_id = order_id
        return False
    db.add(EbookGrant(ebook_id=ebook_id, user_id=user_id,
                      order_id=order_id, source=source))
    return True


def fulfill_ebook_purchase(
    db: Session, *,
    user: User,
    ebook_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    paid_amount: float,               # rupees actually captured
    list_price_inr: "float | None" = None,  # checkout-time LIST price (rupees)
    currency: str = "INR",
) -> FulfillmentResult:
    """Write the idempotent Order/OrderItem/Payment/EbookGrant trail for a
    successful ebook purchase. Template: `fulfill_bundle_purchase` — keyed on
    `Payment.gateway_payment_id`, converged on by /verify, the webhook
    processor, and the reconciliation sweeper. NEVER touches enrollments
    (spec §2). Does not commit — caller owns commit/rollback.

    `list_price_inr` is the checkout-time list price from the order-notes
    snapshot, so `Order.subtotal_amount` / `discount_amount` record the deal
    the buyer was actually offered. It is NOT read off the live Ebook row:
    a price edit between checkout and fulfillment would otherwise rewrite
    history and make `subtotal - discount != total`. It falls back to the
    live list price (hand-built orders with no snapshot), and finally to
    `paid_amount` (nothing else is knowable).
    """
    from app.models.ebook import Ebook

    order_row = db.query(Order).join(Payment, Payment.order_id == Order.id).filter(
        Payment.gateway_payment_id == str(razorpay_payment_id)
    ).first()
    created_order = order_row is None

    ebook = db.query(Ebook).filter(Ebook.id == ebook_id).first()

    if ebook is None and created_order:
        # Money moved but the product row is gone (delete is 409-blocked once
        # any grant exists, so this is the narrow pre-first-sale window).
        # The Order + Payment are still written below — the capture is real
        # and must stay reconcilable; the alert is the trigger for a human
        # refund or hand-grant. Mirrors the bundle no-resolvable-courses path.
        # Gated on created_order so a webhook/sweeper replay of the same
        # ungrantable capture does not page a human a second time.
        from app.services.email_service import EmailService
        logger.error(
            "ebook %s fulfillment: ebook missing (user=%s payment=%s)",
            ebook_id, user.id, razorpay_payment_id,
        )
        EmailService.send_payment_alert(
            "ebook payment with no resolvable ebook",
            f"ebook_id={ebook_id} user_id={user.id}\n"
            f"razorpay_payment_id={razorpay_payment_id}\n"
            f"razorpay_order_id={razorpay_order_id}\n"
            f"paid_amount={paid_amount} {currency}\n"
            "Order + Payment were written; NO grant created. "
            "Refund or grant access manually.",
        )

    if created_order:
        if list_price_inr is not None:
            list_price = float(list_price_inr)
        elif ebook is not None:
            list_price = float(ebook.price_inr or 0)
        else:
            list_price = float(paid_amount)
        # A snapshot below what was captured would make discount_amount
        # negative and subtotal < total — never let bad notes corrupt the row.
        list_price = max(list_price, float(paid_amount))

        order_row = Order(
            user_id=user.id,
            ebook_id=ebook.id if ebook is not None else None,
            order_key=f"EBK_{uuid.uuid4().hex[:12].upper()}",
            order_status=OrderStatus.COMPLETED,
            currency=currency,
            subtotal_amount=list_price,                        # list price (rupees)
            discount_amount=max(0.0, list_price - paid_amount),
            total_amount=paid_amount,                          # what changed hands
            payment_method="razorpay_ebook",
            payment_method_title="Razorpay (ebook)",
            transaction_id=str(razorpay_payment_id),
            billing_email=user.user_email or "",
            date_paid=datetime.now(timezone.utc),
            date_completed=datetime.now(timezone.utc),
        )
        db.add(order_row)
        db.flush()
        if ebook is not None:
            # One OrderItem for the ebook so revenue reports stay meaningful
            # (spec §2). course_id NULL / ebook_id set — 0005 relaxed the FK.
            db.add(OrderItem(
                order_id=order_row.id,
                course_id=None,
                ebook_id=ebook.id,
                order_item_name=ebook.title or f"Ebook {ebook.id}",
                order_item_type="ebook_item",
                quantity=1,
                subtotal=list_price,
                total=paid_amount,
                product_data=revenue_metadata("seyappaduporul", "digital_resources"),
            ))
        db.add(Payment(
            user_id=user.id,
            order_id=order_row.id,
            payment_method="razorpay_ebook",
            gateway_transaction_id=str(razorpay_payment_id),
            gateway_payment_id=str(razorpay_payment_id),
            gateway_order_id=str(razorpay_order_id),
            amount=paid_amount,
            currency=currency,
            payment_status=PaymentStatus.COMPLETED,
            processed_date=datetime.now(timezone.utc),
        ))

    any_new = False
    if ebook is not None:
        # Deliberately NOT gated on created_order — a replay against an
        # existing order self-heals a missing grant (bundle posture).
        any_new = grant_ebook(db, ebook_id=ebook.id, user_id=user.id,
                              order_id=order_row.id, source="purchase")

    return FulfillmentResult(
        created_order=created_order,
        order_id=order_row.id,
        is_new_enrollment=any_new,
        cohort_id=None,
    )
