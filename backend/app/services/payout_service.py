"""Instructor payout ledger and state machine.

Payouts do not move money inside SashaInfinity: instructors request against
their available course revenue and an administrator records the manual
NEFT/UPI transfer.  This module is the single balance authority.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.payment import Order, OrderItem, OrderStatus, Withdrawal
from app.services.platform_tenant_service import audit, enqueue

logger = logging.getLogger(__name__)

BALANCE_BLOCKING_STATUSES = ("pending", "approved", "paid")
TRANSITIONS = {
    ("pending", "approved"),
    ("pending", "rejected"),
    ("approved", "paid"),
}


class WithdrawalStateError(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def instructor_earned_by_course(
    db: Session, course_ids: list[int]
) -> dict[int, float]:
    """Return captured, non-refunded course-line revenue by course.

    OrderItem totals are used so bundles and paid carts are allocated once per
    line instead of multiplying an order's full Payment amount by line count.
    """
    if not course_ids:
        return {}
    rows = (
        db.query(OrderItem.course_id, func.sum(OrderItem.total))
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            OrderItem.course_id.in_(course_ids),
            Order.order_status == OrderStatus.COMPLETED,
            func.coalesce(Order.payment_method, "") != "mock",
        )
        .group_by(OrderItem.course_id)
        .all()
    )
    return {
        int(course_id): round(float(amount or 0), 2)
        for course_id, amount in rows
        if course_id is not None
    }


def instructor_balance(db: Session, user_id: int) -> dict[str, float]:
    course_ids = [
        row[0]
        for row in db.query(Course.id).filter(Course.post_author == user_id).all()
    ]
    earned = round(sum(instructor_earned_by_course(db, course_ids).values()), 2)
    held = db.query(func.sum(Withdrawal.amount)).filter(
        Withdrawal.user_id == user_id,
        Withdrawal.status.in_(BALANCE_BLOCKING_STATUSES),
    ).scalar()
    withdrawn_or_pending = round(float(held or 0), 2)
    return {
        "earned": earned,
        "withdrawn_or_pending": withdrawn_or_pending,
        "available": max(0.0, round(earned - withdrawn_or_pending, 2)),
    }


def transition_withdrawal(
    db: Session,
    withdrawal: Withdrawal,
    *,
    to_status: str,
    actor_id: int,
    reject_detail: str = "",
    paid_reference: str = "",
) -> Withdrawal:
    """Apply pending→approved/rejected or approved→paid; caller commits."""
    from_status = withdrawal.status
    if (from_status, to_status) not in TRANSITIONS:
        raise WithdrawalStateError(
            f"Cannot move withdrawal from '{from_status}' to '{to_status}'"
        )
    withdrawal.status = to_status
    withdrawal.processed_by = actor_id
    withdrawal.processed_at = datetime.now(timezone.utc)
    if to_status == "rejected":
        withdrawal.reject_detail = reject_detail.strip()
    elif to_status == "paid":
        withdrawal.paid_reference = paid_reference.strip()
    db.flush()
    audit(
        db,
        tenant_id=None,
        actor_id=actor_id,
        action=f"withdrawal.{to_status}",
        target_type="withdrawal",
        target_id=withdrawal.withdraw_id,
        reason=reject_detail.strip() if to_status == "rejected" else "",
        before={"status": from_status},
        after={"status": to_status, "amount": float(withdrawal.amount or 0)},
    )
    enqueue(
        db,
        tenant_id=None,
        topic="commerce.withdrawal.transitioned",
        aggregate_type="withdrawal",
        aggregate_id=withdrawal.withdraw_id,
        payload={
            "withdrawal_id": withdrawal.withdraw_id,
            "instructor_id": withdrawal.user_id,
            "amount": float(withdrawal.amount or 0),
            "from_status": from_status,
            "to_status": to_status,
            "actor_id": actor_id,
        },
        idempotency_key=f"withdrawal:{withdrawal.withdraw_id}:{to_status}",
    )
    # Never log method_data or bank/UPI values.
    logger.info(
        "withdrawal transition from=%s to=%s withdraw_id=%s user_id=%s "
        "amount=%s actor_id=%s",
        from_status,
        to_status,
        withdrawal.withdraw_id,
        withdrawal.user_id,
        float(withdrawal.amount or 0),
        actor_id,
    )
    return withdrawal
