"""Member-facing membership endpoints. State transitions are webhook/sweeper
owned — these endpoints only create/cancel gateway subscriptions and read."""
import functools
import logging

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache_headers import apply_public_cache
from app.core.database import get_db
from app.models.membership import Membership, MembershipPlan, MembershipStatus
from app.models.user import User
from app.routers.payments import _razorpay_creds
from app.schemas.membership import (
    MembershipOut, PlanOut, SubscribeRequest, SubscribeResponse,
)
from app.services.auth_service import AuthService
from app.services.membership_access import (
    covered_course_ids, suspend_membership_enrollments,
)

logger = logging.getLogger(__name__)
router = APIRouter()

BLOCKING_STATUSES = [MembershipStatus.PENDING, MembershipStatus.ACTIVE,
                     MembershipStatus.GRACE]

# Highest-priority first. A user can transiently hold more than one blocking
# row (e.g. a stale PENDING alongside a live ACTIVE in a database predating
# uq_memberships_one_blocking_per_user), and /me and /cancel must both pick the
# same, most-authoritative one rather than whatever the DB returns first.
_STATUS_PRIORITY = [MembershipStatus.ACTIVE, MembershipStatus.GRACE,
                    MembershipStatus.PENDING]
assert set(_STATUS_PRIORITY) == set(BLOCKING_STATUSES), \
    "_STATUS_PRIORITY must rank exactly the blocking statuses"


def _primary_membership(db: Session, user_id: int) -> Membership | None:
    """The blocking membership that represents this user, deterministically:
    ACTIVE > GRACE > PENDING, newest first within a status."""
    for status in _STATUS_PRIORITY:
        m = (db.query(Membership)
             .filter(Membership.user_id == user_id,
                     Membership.status == status)
             .order_by(Membership.created_at.desc(), Membership.id.desc())
             .first())
        if m is not None:
            return m
    return None


def _rzp_key_id() -> str:
    key_id, _ = _razorpay_creds()
    return key_id


def _rzp_client():
    key_id, key_secret = _razorpay_creds()
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")
    client = razorpay.Client(auth=(key_id, key_secret))
    client.session.request = functools.partial(client.session.request, timeout=30)
    return client


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(request: Request, response: Response, db: Session = Depends(get_db)):
    apply_public_cache(request, response, s_maxage=300, swr=600)
    plans = (db.query(MembershipPlan)
             .filter(MembershipPlan.is_active.is_(True))
             .order_by(MembershipPlan.price).all())
    return [PlanOut(
        id=p.id, name=p.name, description=p.description or "",
        all_access=p.all_access, period=p.period, interval=p.interval,
        price=float(p.price), covered_courses=len(covered_course_ids(db, p)),
    ) for p in plans]


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    request: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == request.plan_id,
        MembershipPlan.is_active.is_(True)).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    existing = _primary_membership(db, current_user.id)
    if existing is not None and existing.status != MembershipStatus.PENDING:
        # ACTIVE / GRACE: a real, paid-for membership is in the way.
        raise HTTPException(status_code=409, detail="You already have a membership")
    if existing is not None:
        # PENDING = a checkout that was started but never confirmed by a
        # webhook (the user dismissed the Razorpay modal). Without this the row
        # would block every future /subscribe forever.
        if existing.plan_id == plan.id:
            # Same tier: hand back the subscription they already have so the
            # frontend can just re-open checkout. No second gateway
            # subscription, no second local row.
            return SubscribeResponse(
                subscription_id=str(existing.razorpay_subscription_id),
                razorpay_key=_rzp_key_id())
        # Different tier: discard the abandoned attempt locally. No gateway
        # cancel call — nothing was ever authorized or charged on a `created`
        # subscription, and Razorpay rejects cancelling one.
        existing.status = MembershipStatus.CANCELLED
        db.flush()

    # R7: coupons on memberships — only a coupon carrying a Razorpay Offer id can
    # discount a subscription (the gateway applies it); anything else is refused
    # honestly instead of silently charging full price.
    offer_id = None
    code = (getattr(request, "coupon_code", None) or "").strip().upper()
    if code:
        from app.models.coupon import Coupon
        from app.services.coupon_service import _aware
        from datetime import datetime, timezone
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        now = datetime.now(timezone.utc)
        if coupon is None or not getattr(coupon, "razorpay_offer_id", None):
            raise HTTPException(status_code=422, detail="This coupon is not valid for memberships")
        if getattr(coupon, "is_active", True) is False or (coupon.valid_from and _aware(coupon.valid_from) > now) \
                or (coupon.valid_until and _aware(coupon.valid_until) < now):
            raise HTTPException(status_code=422, detail="This coupon is not active right now")
        if coupon.usage_limit and (coupon.usage_count or 0) >= coupon.usage_limit:
            raise HTTPException(status_code=422, detail="This coupon has been fully used")
        offer_id = coupon.razorpay_offer_id
    client = _rzp_client()
    try:
        sub_body = {
            "plan_id": plan.razorpay_plan_id,
            "total_count": 100,
            "customer_notify": 1,
            "notes": {"user_id": str(current_user.id), "plan_id": str(plan.id), **({"coupon": code} if code else {})},
        }
        if offer_id:
            sub_body["offer_id"] = offer_id
        sub = client.subscription.create(sub_body)
    except HTTPException:
        db.rollback()  # drop the pending-discard above; nothing was created
        raise
    except Exception:
        db.rollback()
        logger.exception("subscription create failed (user=%s plan=%s)",
                         current_user.id, plan.id)
        raise HTTPException(status_code=502, detail="Could not start subscription")

    db.add(Membership(user_id=current_user.id, plan_id=plan.id,
                      razorpay_subscription_id=str(sub["id"])))
    try:
        db.commit()
    except IntegrityError:
        # uq_memberships_one_blocking_per_user: a concurrent /subscribe won the
        # race between our read above and this insert. Loser reports the
        # conflict rather than creating a second blocking membership.
        db.rollback()
        logger.warning("concurrent subscribe lost the race (user=%s plan=%s)",
                       current_user.id, plan.id)
        raise HTTPException(status_code=409, detail="You already have a membership")
    return SubscribeResponse(subscription_id=str(sub["id"]),
                             razorpay_key=_rzp_key_id())


@router.get("/me", response_model=MembershipOut)
async def my_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    # Prefer the live membership (ACTIVE > GRACE > PENDING) so a leftover
    # PENDING row can never mask a paid ACTIVE one; fall back to the newest
    # terminal row so a lapsed/cancelled user still sees their own status.
    m = _primary_membership(db, current_user.id)
    if m is None:
        m = (db.query(Membership)
             .filter(Membership.user_id == current_user.id)
             .order_by(Membership.created_at.desc(), Membership.id.desc())
             .first())
    if not m:
        raise HTTPException(status_code=404, detail="No membership")
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == m.plan_id).one()
    return MembershipOut(
        plan_id=plan.id, plan_name=plan.name, status=m.status.value,
        current_period_end=m.current_period_end, grace_until=m.grace_until,
        cancel_at_period_end=m.cancel_at_period_end)


def cancel_membership_subscription(db: Session, membership: Membership, *,
                                   immediate: bool, actor_id: int) -> None:
    """Shared by self-service /cancel (immediate=False) and the admin cancel
    endpoint (spec 2026-09-04-money-ops §2).

    - PENDING: nothing was ever authorized on a `created` subscription and
      Razorpay rejects cancelling one -> discard locally, no gateway call.
    - Already CANCELLED: the cancel already landed -> no-op (idempotent
      re-run), no second gateway call.
    - immediate=False: Razorpay cancel_at_cycle_end=1 + cancel_at_period_end
      (today's semantics). Already flagged -> no-op (idempotent re-run).
    - immediate=True: Razorpay cancel now (cancel_at_cycle_end=0),
      status=CANCELLED, and suspend_membership_enrollments (the existing
      lapse logic: source=="membership" AND order_id IS NULL only).

    Nothing is persisted before the gateway call — a cancellation has no
    partial-money state to record — so a gateway failure raises 502 with the
    local row untouched. The status flip and the enrollment suspension happen
    together after gateway success; the caller commits them as one transaction.
    """
    if membership.status == MembershipStatus.PENDING:
        membership.status = MembershipStatus.CANCELLED
        db.flush()
        return
    if membership.status == MembershipStatus.CANCELLED:
        return  # idempotent re-run: already cancelled at the gateway
    if not immediate and membership.cancel_at_period_end:
        return  # idempotent re-run: already scheduled to end

    client = _rzp_client()
    try:
        client.subscription.cancel(membership.razorpay_subscription_id,
                                   {"cancel_at_cycle_end": 0 if immediate else 1})
    except Exception:
        logger.exception("subscription cancel failed (membership=%s immediate=%s actor=%s)",
                         membership.id, immediate, actor_id)
        raise HTTPException(status_code=502, detail="Could not cancel; try again")

    membership.cancel_at_period_end = True
    if immediate:
        membership.status = MembershipStatus.CANCELLED
        suspended = suspend_membership_enrollments(db, membership)
        logger.info("membership cancelled immediately membership_id=%s user_id=%s "
                    "actor_id=%s suspended_enrollments=%s",
                    membership.id, membership.user_id, actor_id, suspended)
    else:
        logger.info("membership cancel scheduled membership_id=%s user_id=%s actor_id=%s",
                    membership.id, membership.user_id, actor_id)
    db.flush()


@router.post("/cancel")
async def cancel_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    # Deterministic target: cancel the ACTIVE/GRACE membership, never a stale
    # PENDING row sitting beside it.
    m = _primary_membership(db, current_user.id)
    if not m:
        raise HTTPException(status_code=404, detail="No active membership")

    was_pending = m.status == MembershipStatus.PENDING
    cancel_membership_subscription(db, m, immediate=False, actor_id=current_user.id)
    db.commit()
    if was_pending:
        return {"success": True, "message": "Pending membership discarded"}
    return {"success": True,
            "message": "Membership will end at the current period's close"}
