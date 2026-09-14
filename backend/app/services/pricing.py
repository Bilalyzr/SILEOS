"""
Single pricing authority for single-course chargeable/expected/verified
amounts (audit finding A5, platform audit 2026-09-03).

Bug this fixes: the direct Razorpay checkout path (payments.py
create-order/verify) computed the amount to charge from
`course.course_price` alone, never reading `course.course_sale_price` —
even though the storefront (checkout.tsx) advertises the sale price and
the cart path (orders.py) already honored it. Two purchase paths, two
different prices for the same course.

Rule: a sale price only applies when it is STRICTLY between zero and the
list price — `0 < sale_price < price`. A sale price that is zero, absent,
equal to, or above the list price is not a sale; the list price applies.
This is a stricter rule than orders.py's old inline check (which accepted
`sale_price >= price`, so a sale price entered above list price would
incorrectly win) — see the regression tests in
tests/test_sale_price_pricing.py for the documented behavior change on
the cart path.

Every site in the codebase that computes a chargeable, expected, or
verified amount FOR A SINGLE COURSE must route through
`effective_course_price`. This explicitly does NOT cover:
  - bundle pricing (Bundle.bundle_price) — bundles have their own price,
    unrelated to any one course's list/sale price.
  - seat-priced cohort overrides (Cohort.seat_price) — a seat price
    overrides the course price entirely; that precedence is preserved by
    callers applying the seat-price check AFTER calling this function.
  - membership / subscription pricing.
  - invoice line pricing.
  - display-only catalog serialization that already returns both
    `price` and `sale_price` to the client (e.g. checkout.py's
    `/checkout/summary`-style endpoints) — those are correct as-is and
    are not a "chargeable amount" computation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union

logger = logging.getLogger(__name__)

Number = Union[int, float, Decimal]


def _is_positive(value) -> bool:
    """True if `value` is a real, strictly-positive number. Treats None
    and falsy DB defaults (0, Decimal('0')) as "no sale price set"."""
    if value is None:
        return False
    try:
        return value > 0
    except TypeError:
        return False


def is_on_sale(course) -> bool:
    """True iff `course.course_sale_price` is a valid sale: strictly
    greater than zero AND strictly less than `course.course_price`."""
    price = course.course_price
    sale = course.course_sale_price
    if not _is_positive(sale):
        return False
    if price is None:
        return False
    return sale < price


def effective_course_price(course) -> Number:
    """The price to charge/expect/verify for a single-course purchase.

    Returns `course.course_sale_price` when it is a valid sale
    (`0 < sale_price < course_price`), otherwise `course.course_price`
    (or 0 if that is also unset, matching the free-course convention
    used throughout the payments code).
    """
    if is_on_sale(course):
        return course.course_sale_price
    return course.course_price if course.course_price is not None else 0


# Postgres `integer` (and the id columns this is used against) is a 32-bit
# signed int; SQLite has no such ceiling itself, but the driver/ORM layer
# can still choke on an arbitrarily large Python int passed into a filter
# (OverflowError on SQLite, a driver-level error on Postgres) — the exact
# denial-of-fulfilment class (webhook event FAILED forever / sweeper orphan)
# that guarding against non-numeric notes was meant to close.
_MIN_NOTE_ID = 1
_MAX_NOTE_ID = 2 ** 31 - 1


def _parse_note_id(notes: dict, key: str) -> Optional[int]:
    """Parse an id out of a gateway-order notes dict, treating anything
    non-numeric (missing, empty, garbage like 'abc'), non-positive, or
    outside the valid 32-bit id range as absent rather than raising or
    handing an unqueryable value to the ORM. Notes are gateway-round-
    tripped strings, not trusted input — a bare `int(notes[key])` throws on
    a stale/forged/malformed value and (pre-fix) took down the whole
    webhook event or sweeper capture instead of just skipping the optional
    cohort/referral mapping."""
    raw = notes.get(key)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning("pricing.resolve_expected_purchase: non-numeric %s in "
                       "notes: %r — treating as absent", key, raw)
        return None
    if not (_MIN_NOTE_ID <= value <= _MAX_NOTE_ID):
        logger.warning(
            "pricing.resolve_expected_purchase: %s in notes out of valid "
            "id range: %r — treating as absent", key, raw,
        )
        return None
    return value


@dataclass
class ExpectedPurchase:
    """What a single-course purchase should cost and map to, resolved
    identically for /verify, the webhook handler, and the reconciliation
    sweeper — the "three-path agreement" contract.

    expected_price: the price to charge/expect/verify against the gateway
        capture, in rupees. Effective (sale, if any) course price, UNLESS
        a coupon note resolves to a cheaper `final_amount`, or a
        legitimate seat-price override applies (see `cohort` below) — in
        precedence order: seat price > coupon final_amount > effective
        course price. This is what the buyer actually paid.
    subtotal_price: the PRE-discount amount an Order row's
        `subtotal_amount` should record, in rupees. Equals `expected_price`
        in every case EXCEPT a coupon purchase, where `expected_price` is
        already net of the discount — `subtotal_price` there is the
        effective course price the coupon discounted FROM, so that
        `subtotal_price - coupon_discount == expected_price` holds for the
        written Order row (paid == subtotal - discount).
    cohort: the Cohort to map the enrollment to, or None. Populated ONLY
        when `notes["cohort_id"]` names a cohort that (a) exists,
        (b) is_active, and (c) is bound to THIS course
        (`cohort.course_id == course.id` OR the cohort has no course
        binding at all) — mirrors `coupon_service.resolve_checkout_code`'s
        referral-resolution rule. A cohort naming a *different* course is
        never trusted, no matter what the notes claim — that was the
        privilege-escalation gap this helper closes (a stale/forged
        cohort_id from another course's cheaper seat cohort could
        otherwise both under-charge the buyer and mis-map the enrollment).
    referral_code_id: the ReferralCode id to bump `used_count` for, or
        None. Populated only alongside a trusted `cohort` (never on its
        own), and only when that id actually names a ReferralCode row
        that maps to `cohort` — a referral_code_id note pointing at some
        other cohort's code is ignored the same way a mismatched
        cohort_id is.
    is_coupon: True when `expected_price` came from a coupon note.
    coupon: the Coupon row when `is_coupon` is True, else None — for
        callers that record `CouponUsage` / bump `usage_count`.
    coupon_discount: the coupon's own `discount_amount` (rupees) when
        `is_coupon` is True, else 0.0. Callers should use THIS instead of
        deriving `effective_price - paid_amount` themselves — it is
        `resolve_checkout_code`'s own computed discount (percentage/fixed,
        with its max-discount-cap already applied), not a re-derivation.
    """
    expected_price: float
    subtotal_price: float = 0.0
    cohort: Optional[object] = None
    referral_code_id: Optional[int] = None
    is_coupon: bool = False
    coupon: Optional[object] = None
    coupon_discount: float = 0.0


def resolve_expected_purchase(
    db, course, notes: Optional[dict], *, user_id: Optional[int] = None,
    paid_amount: Optional[float] = None, order_id: Optional[str] = None,
) -> ExpectedPurchase:
    """Single source of truth for what a single-course purchase's Razorpay
    order notes SHOULD resolve to — used by /verify, the webhook handler,
    and the reconciliation sweeper so all three agree field-for-field on
    the same purchase (audit finding A5 follow-up, platform audit
    2026-09-03 round 3).

    Precedence, exactly mirroring the pre-refactor logic that only
    `/verify` implemented correctly:
      1. A `coupon_code` (or `referral_code` naming a Coupon) note ->
         re-resolve via `resolve_checkout_code`; `expected_price` becomes
         the coupon's `final_amount`. A cohort note is NOT applied as a
         price override in this case (coupons on seat-priced cohorts are
         rejected at create-order; a coupon's own resolved cohort is
         still returned for enrollment mapping, but never overrides the
         price).
      2. Otherwise (no code, or a code that resolved to "referral"/None):
         `notes["cohort_id"]` is looked up DIRECTLY (not by trusting the
         referral code's own cohort — the note is authoritative for which
         cohort to assign, matching the pre-refactor `/verify` behavior)
         and is applied ONLY IF that cohort exists, is active, and is
         bound to this course (`cohort.course_id == course.id`, or the
         cohort has no course binding at all — a mismatched cohort_id is
         NEVER trusted, no matter what the notes claim). If a
         `referral_code_id` note is also present and names a ReferralCode
         mapped to that same trusted cohort, AND the cohort carries a
         `seat_price`, `expected_price` becomes the seat price — UNLESS
         `paid_amount` was supplied and is more than ₹1 below that seat
         price (see below).
      3. Otherwise: `expected_price` is `effective_course_price(course)`.

    A malformed/non-numeric `cohort_id` or `referral_code_id` note is
    treated as absent (never raises) — see `_parse_note_id`.

    `paid_amount` / `order_id` (optional, used by the webhook/sweeper
    callers which fulfil on captured money rather than re-verifying an
    exact amount): when supplied and the seat-price override would make
    `expected_price` more than ₹1 BELOW `paid_amount`, the override is
    skipped (falls back to `effective_course_price`) and a warning is
    logged naming `order_id` — this must never silently clamp or produce
    a written Order where `subtotal - discount != paid` because a seat
    price turned out to be less than what was actually captured (e.g. a
    forged/mismatched note that still happened to name a real, correctly
    course-bound cohort with an implausibly low seat price). `/verify`
    does not pass `paid_amount`/`order_id` — it has its own strict
    amount-equality check downstream that already rejects any mismatch.
    """
    from app.services.coupon_service import CouponError, resolve_checkout_code

    notes = notes or {}

    base_price = float(effective_course_price(course))
    expected_price = base_price
    is_coupon = False
    coupon_discount = 0.0
    resolved_cohort = None
    resolved_kind_cohort = None
    resolved_kind_coupon = None

    note_code = notes.get("coupon_code") or notes.get("referral_code")
    if note_code:
        resolved = None
        try:
            resolved = resolve_checkout_code(
                db, code=str(note_code), user_id=user_id, course=course,
                for_paid=True,
            )
        except CouponError as exc:
            logger.warning(
                "pricing.resolve_expected_purchase: code %r no longer "
                "valid for course %s (%s) — falling back to effective "
                "course price", note_code, course.id, exc.message,
            )

        if resolved is not None and resolved.kind == "coupon":
            expected_price = float(resolved.final_amount)
            is_coupon = True
            coupon_discount = float(resolved.discount_amount)
            resolved_kind_cohort = resolved.cohort
            resolved_kind_coupon = resolved.coupon

    if not is_coupon:
        cohort_id = _parse_note_id(notes, "cohort_id")
        if cohort_id is not None:
            from app.models.cohort import Cohort

            candidate = db.query(Cohort).filter(Cohort.id == cohort_id).first()
            if candidate is None:
                logger.warning(
                    "pricing.resolve_expected_purchase: cohort_id %s in "
                    "notes does not exist (course %s) — ignoring",
                    cohort_id, course.id,
                )
            elif not candidate.is_active:
                logger.warning(
                    "pricing.resolve_expected_purchase: cohort_id %s in "
                    "notes is not active (course %s) — ignoring",
                    cohort_id, course.id,
                )
            elif candidate.course_id and candidate.course_id != course.id:
                # The privilege-escalation gap this helper exists to close:
                # a stale/forged/mismatched cohort_id pointing at ANOTHER
                # course's (possibly much cheaper) seat-priced cohort must
                # never be trusted for pricing or enrollment mapping.
                logger.warning(
                    "pricing.resolve_expected_purchase: cohort_id %s in "
                    "notes is bound to course %s, not the purchased "
                    "course %s (order_id=%s) — ignoring (possible "
                    "forged/stale note)",
                    cohort_id, candidate.course_id, course.id, order_id,
                )
            else:
                resolved_cohort = candidate

        referral_code_id = None
        if resolved_cohort is not None:
            note_referral_id = _parse_note_id(notes, "referral_code_id")
            if note_referral_id is not None:
                from app.models.cohort import ReferralCode

                rc = db.query(ReferralCode).filter(
                    ReferralCode.id == note_referral_id).first()
                if rc is None or rc.cohort_id != resolved_cohort.id:
                    logger.warning(
                        "pricing.resolve_expected_purchase: referral_code_id "
                        "%s in notes does not map to cohort %s — ignoring "
                        "for seat-price override (enrollment mapping still "
                        "uses the trusted cohort)",
                        note_referral_id, resolved_cohort.id,
                    )
                else:
                    referral_code_id = rc.id
                    if resolved_cohort.seat_price is not None:
                        seat_price = float(resolved_cohort.seat_price)
                        if paid_amount is not None and seat_price < paid_amount - 1.0:
                            # A seat-price override that is more than ₹1
                            # below what was actually captured would make
                            # this write paid > subtotal - discount for a
                            # coupon_discount of 0 — never trust it blindly;
                            # fall back to the effective course price and
                            # flag it for manual review instead.
                            logger.warning(
                                "pricing.resolve_expected_purchase: cohort %s "
                                "seat_price %.2f is more than Rs.1 below the "
                                "captured amount %.2f (course %s, order_id=%s) "
                                "— skipping seat-price override, using "
                                "effective course price instead",
                                resolved_cohort.id, seat_price, paid_amount,
                                course.id, order_id,
                            )
                        else:
                            expected_price = seat_price

        return ExpectedPurchase(
            expected_price=expected_price,
            subtotal_price=expected_price,  # no discount split here — the
            # seat price (if it applies) or the effective course price IS
            # what the buyer was offered pre-any-discount.
            cohort=resolved_cohort,
            referral_code_id=referral_code_id,
            is_coupon=False,
            coupon_discount=0.0,
        )

    return ExpectedPurchase(
        expected_price=expected_price,
        subtotal_price=base_price,  # the effective course price the
        # coupon discounted FROM — expected_price is already net of
        # coupon_discount, so subtotal_price MUST stay pre-discount or a
        # written Order row's subtotal - discount would double-subtract
        # the coupon and no longer equal what was actually paid.
        cohort=resolved_kind_cohort,
        referral_code_id=None,
        is_coupon=True,
        coupon=resolved_kind_coupon,
        coupon_discount=coupon_discount,
    )
