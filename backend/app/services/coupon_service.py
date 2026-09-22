"""
Coupon / ReferralCode validation shared by the coupon router, the
Razorpay single-course purchase flow, the cart-style /orders flow,
and the free-course /enroll flow.

Two entry points:
  - `validate_and_compute(...)` — legacy Coupon-only path. Kept for
    back-compat with existing callers. Mirrors `POST /coupons/validate`.
  - `resolve_checkout_code(...)` — unified resolver that accepts a single
    user-supplied code and detects whether it is a ReferralCode (cohort
    signup) or a Coupon (discount). Callers use this for the checkout
    field where the user does not know which kind the code is.

Business rules (enforced centrally so every call site behaves the same):
  * Paid courses NEVER get their Razorpay amount waived. A ReferralCode
    applied to a paid course just sets the cohort mapping; discount is
    zero. A Coupon with a cohort_id on a paid course still applies its
    discount but cannot force final_amount to 0 unless the discount
    legitimately covers the full price.
  * Free courses: either code enrols the user; if the code has a cohort
    it becomes a CohortMembership too.
  * Code lookup is case-insensitive via `ilike`.
  * Cohort capacity, referral max_uses and expiry, coupon is_active /
    valid_from / valid_until / usage_limit / per_user_limit /
    minimum_purchase_amount / course restrictions are all checked here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Optional, Literal

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.coupon import Coupon, CouponUsage
from app.models.cohort import Cohort, CohortMembership, ReferralCode
from app.models.internship import InternshipVoucher
from app.services.pricing import effective_course_price


class CouponError(Exception):
    """Raised when a coupon/code cannot be applied. `message` is user-safe."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass
class CouponResult:
    coupon: Coupon
    discount_amount: float  # in rupees
    final_amount: float     # in rupees, clamped >= 0


ResolvedKind = Optional[Literal["voucher", "referral", "coupon"]]


@dataclass
class ResolvedCode:
    """Outcome of the unified checkout-code resolver.

    kind = 'voucher'  — the code matched an `InternshipVoucher` owned by
        `user_id` that is still in status 'issued'. `voucher_row` and
        `cohort` (from the internship's 1:1 cohort) are populated.
        `discount_amount = base_price`, `final_amount = 0` — a voucher
        always enrolls free. Caller must call `lock_voucher_and_redeem`
        inside the enrollment transaction to atomically mark redeemed.
    kind = 'referral' — the code matched a ReferralCode. `referral_row`
        and `cohort` are populated. `discount_amount` is 0; a referral
        never waives Razorpay payment on a paid course.
    kind = 'coupon'   — the code matched a Coupon. `coupon` is populated.
        `cohort` is populated if the coupon is linked to a cohort.
        `discount_amount` and `final_amount` are computed against the
        supplied base price.
    kind = None       — no match; caller decides whether to reject.
    """

    kind: ResolvedKind = None
    referral_row: Optional[ReferralCode] = None
    coupon: Optional[Coupon] = None
    cohort: Optional[Cohort] = None
    voucher_row: Optional[InternshipVoucher] = None
    discount_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    final_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    max_students_reached: bool = False


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime is tz-aware (assume UTC if naive). See auth.py:357."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def validate_and_compute(
    db: Session,
    *,
    code: str,
    user_id: int,
    course_ids: Iterable[int],
    total_amount: float,
) -> CouponResult:
    """Validate a coupon and compute the discount.

    Raises `CouponError` with a user-safe message on any failure.
    Mirrors `routers.coupons.validate_coupon`. Keep in sync.
    """
    if not code:
        raise CouponError("Invalid coupon code")

    coupon = db.query(Coupon).filter(Coupon.code.ilike(code.strip())).first()
    if not coupon:
        raise CouponError("Invalid coupon code")

    if not coupon.is_active:
        raise CouponError("This coupon is no longer active")

    now = datetime.now(timezone.utc)
    valid_from = _aware(coupon.valid_from)
    if valid_from and now < valid_from:
        raise CouponError("This coupon is not yet valid")

    valid_until = _aware(coupon.valid_until)
    if valid_until and now > valid_until:
        raise CouponError("This coupon has expired")

    if total_amount < float(coupon.minimum_purchase_amount or 0):
        raise CouponError(
            f"Minimum purchase amount of Rs.{float(coupon.minimum_purchase_amount)} required"
        )

    if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
        raise CouponError("This coupon has reached its usage limit")

    user_usage_count = db.query(CouponUsage).filter(
        and_(
            CouponUsage.coupon_id == coupon.id,
            CouponUsage.user_id == user_id,
        )
    ).count()
    if user_usage_count >= (coupon.per_user_limit or 1):
        raise CouponError(
            f"You have already used this coupon the maximum number of times ({coupon.per_user_limit})"
        )

    if coupon.applicability == 'specific_courses':
        applicable_ids = {r.course_id for r in coupon.course_restrictions}
        if not any(cid in applicable_ids for cid in course_ids):
            raise CouponError("This coupon is not applicable to the selected courses")

    if coupon.discount_type == 'percentage':
        # Clamp defensive: a percentage above 100 (e.g. a legacy or
        # schema-bypassing row) must never discount more than the total.
        pct = min(100.0, float(coupon.discount_value))
        discount_amount = (total_amount * pct) / 100.0
        max_cap = getattr(coupon, "max_discount_amount", None)
        if max_cap is not None and float(max_cap) > 0:
            discount_amount = min(discount_amount, float(max_cap))
    else:  # fixed
        discount_amount = min(float(coupon.discount_value), total_amount)

    final_amount = max(0.0, total_amount - discount_amount)
    return CouponResult(
        coupon=coupon,
        discount_amount=discount_amount,
        final_amount=final_amount,
    )


def _cohort_full(db: Session, cohort: Cohort, user_id: int) -> bool:
    """True if cohort.max_students is reached AND the user is not already
    a member. max_students == 0 (or falsy) means no limit."""
    if not cohort.max_students or int(cohort.max_students) <= 0:
        return False
    # Already a member? Then they're not taking a new seat.
    already = db.query(CohortMembership).filter(
        CohortMembership.cohort_id == cohort.id,
        CohortMembership.user_id == user_id,
    ).first()
    if already:
        return False
    count = db.query(func.count(CohortMembership.id)).filter(
        CohortMembership.cohort_id == cohort.id
    ).scalar() or 0
    return int(count) >= int(cohort.max_students)


def resolve_checkout_code(
    db: Session,
    *,
    code: Optional[str],
    user_id: int,
    course,  # Course model instance
    for_paid: bool,
) -> ResolvedCode:
    """Unified resolver for the checkout field.

    Try ReferralCode first, then fall back to Coupon. Raises CouponError
    (user-safe) on any validation failure for a matched code. Returns a
    ResolvedCode with kind=None if `code` is empty/whitespace or does
    not match either table.

    `for_paid` is informational — it does NOT change whether a code is
    accepted. It only affects computed discount semantics:
      - A referral on a paid course has discount=0 (payment still due).
      - A coupon on a paid course applies its normal discount.
      - Free courses: discount collapses to 0 either way.
    """
    if not code or not str(code).strip():
        return ResolvedCode(kind=None)

    normalized = str(code).strip()
    # The base a coupon (or voucher 100%-off) discounts from is the price
    # the buyer was actually offered — the effective (sale, if any) price —
    # not always the list price. Audit finding A5 (platform audit
    # 2026-09-03): a 10% coupon on a Rs.499 sale course must yield
    # Rs.449.10, not Rs.899.10.
    base_price = float(effective_course_price(course)) if course else 0.0

    # 1) InternshipVoucher lookup (case-insensitive). Vouchers take priority
    # because their code-space ("INTR-XXXXXXXX") is distinct and they imply
    # a 100% discount the other tables can't express.
    voucher = (
        db.query(InternshipVoucher)
        .filter(InternshipVoucher.code.ilike(normalized))
        .first()
    )
    if voucher:
        if voucher.buyer_user_id != user_id:
            raise CouponError("This voucher belongs to a different account")
        if voucher.status != "issued":
            raise CouponError("This voucher has already been redeemed")

        internship = getattr(voucher, "internship", None)
        if internship is None:
            raise CouponError("Voucher is not linked to an internship")
        v_cohort = getattr(internship, "cohort", None)
        if v_cohort is None and getattr(internship, "cohort_id", None):
            v_cohort = db.query(Cohort).filter(Cohort.id == internship.cohort_id).first()

        return ResolvedCode(
            kind="voucher",
            voucher_row=voucher,
            coupon=None,
            referral_row=None,
            cohort=v_cohort,
            discount_amount=Decimal(str(base_price)),
            final_amount=Decimal("0"),
            max_students_reached=False,
        )

    # 2) ReferralCode lookup (case-insensitive)
    rc = db.query(ReferralCode).filter(ReferralCode.code.ilike(normalized)).first()
    if rc:
        now = datetime.now(timezone.utc)
        expires_at = _aware(rc.expires_at)
        if expires_at and expires_at < now:
            raise CouponError("This referral code has expired")
        if rc.max_uses and (rc.used_count or 0) >= rc.max_uses:
            raise CouponError("This referral code is fully used")

        cohort = db.query(Cohort).filter(Cohort.id == rc.cohort_id).first()
        if not cohort or not cohort.is_active:
            raise CouponError("Referral code's cohort is not active")

        # A referral maps a user to a cohort. If the referral's cohort
        # is tied to a course, enforce that it matches the course being
        # purchased (otherwise the mapping makes no sense).
        if cohort.course_id and course and cohort.course_id != course.id:
            raise CouponError("This referral code is not valid for this course")

        full = _cohort_full(db, cohort, user_id)
        # A referral never waives payment for paid courses.
        return ResolvedCode(
            kind="referral",
            referral_row=rc,
            coupon=None,
            cohort=cohort,
            discount_amount=Decimal("0"),
            final_amount=Decimal(str(base_price)),
            max_students_reached=full,
        )

    # 3) Coupon fallback
    try:
        result = validate_and_compute(
            db,
            code=normalized,
            user_id=user_id,
            course_ids=[course.id] if course else [],
            total_amount=base_price,
        )
    except CouponError:
        # Distinguish "no such code at all" from "matched Coupon but
        # invalid" — validate_and_compute raises "Invalid coupon code"
        # for the miss case; re-raise as a generic unified message when
        # neither table matched.
        any_coupon = db.query(Coupon).filter(Coupon.code.ilike(normalized)).first()
        if not any_coupon:
            raise CouponError("Invalid code")
        raise

    cohort = None
    full = False
    if getattr(result.coupon, "cohort_id", None):
        cohort = db.query(Cohort).filter(Cohort.id == result.coupon.cohort_id).first()
        if cohort and not cohort.is_active:
            # A discount coupon linked to an inactive cohort still
            # discounts but can't map the user to that cohort.
            cohort = None
        if cohort:
            full = _cohort_full(db, cohort, user_id)

    return ResolvedCode(
        kind="coupon",
        referral_row=None,
        coupon=result.coupon,
        cohort=cohort,
        discount_amount=Decimal(str(result.discount_amount)),
        final_amount=Decimal(str(result.final_amount)),
        max_students_reached=full,
    )


def lock_referral_and_bump(
    db: Session, referral_id: int
) -> ReferralCode:
    """Atomically increment ReferralCode.used_count under SELECT FOR UPDATE.

    Call INSIDE the enrollment transaction (do NOT commit here — caller
    owns the commit). Raises CouponError if the code has been exhausted
    by a racing redemption.
    """
    locked = (
        db.query(ReferralCode)
        .filter(ReferralCode.id == referral_id)
        .with_for_update()
        .first()
    )
    if not locked:
        raise CouponError("Referral code no longer exists")
    if locked.max_uses and (locked.used_count or 0) >= locked.max_uses:
        raise CouponError("This referral code is fully used")
    locked.used_count = (locked.used_count or 0) + 1
    db.flush()
    return locked


def lock_voucher_and_redeem(
    db: Session, voucher_id: int, course_id: int
) -> InternshipVoucher:
    """Atomically redeem an InternshipVoucher against a course.

    Call INSIDE the enrollment transaction (do NOT commit here — caller
    owns the commit). Re-checks status under SELECT FOR UPDATE so two
    concurrent enroll calls with the same voucher can't both succeed.
    Raises CouponError if the voucher was already redeemed (race).
    """
    locked = (
        db.query(InternshipVoucher)
        .filter(InternshipVoucher.id == voucher_id)
        .with_for_update()
        .first()
    )
    if not locked:
        raise CouponError("Voucher no longer exists")
    if locked.status != "issued":
        raise CouponError("This voucher has already been redeemed")
    locked.status = "redeemed"
    locked.redeemed_on_course_id = course_id
    locked.redeemed_at = datetime.now(timezone.utc)
    db.flush()
    return locked
