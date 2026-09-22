"""Instructor requests and admin processing for manual payouts."""

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.payment import Withdrawal
from app.models.user import User
from app.schemas.payout import (
    AdminWithdrawalOut,
    BalanceOut,
    InstructorWithdrawalsOut,
    MarkPaidRequest,
    RejectRequest,
    WithdrawalCreate,
    WithdrawalOut,
)
from app.services import payout_service
from app.services.auth_service import AuthService
from app.services.platform_tenant_service import audit, enqueue

logger = logging.getLogger(__name__)

instructor_router = APIRouter()
admin_router = APIRouter()


def _withdrawal_out(row: Withdrawal) -> WithdrawalOut:
    return WithdrawalOut(
        id=row.withdraw_id,
        amount=float(row.amount or 0),
        method_data=dict(row.method_data or {}),
        status=row.status,
        reject_detail=row.reject_detail or "",
        paid_reference=row.paid_reference or "",
        created_at=row.created_at,
        processed_at=row.processed_at,
    )


@instructor_router.get("", response_model=InstructorWithdrawalsOut)
def list_my_withdrawals(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    rows = (
        db.query(Withdrawal)
        .filter(Withdrawal.user_id == current_user.id)
        .order_by(Withdrawal.created_at.desc(), Withdrawal.withdraw_id.desc())
        .all()
    )
    return InstructorWithdrawalsOut(
        balance=BalanceOut(**payout_service.instructor_balance(db, current_user.id)),
        min_withdrawal_inr=get_settings().MIN_WITHDRAWAL_INR,
        items=[_withdrawal_out(row) for row in rows],
    )


@instructor_router.post("", response_model=WithdrawalOut, status_code=201)
def request_withdrawal(
    body: WithdrawalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    amount = round(float(body.amount), 2)
    minimum = get_settings().MIN_WITHDRAWAL_INR
    if not math.isfinite(amount) or amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    if amount < minimum:
        raise HTTPException(
            status_code=400, detail=f"Minimum withdrawal is INR {minimum}"
        )

    # Serialize payout requests per instructor so simultaneous tabs cannot
    # both spend the same available balance on PostgreSQL.
    db.query(User).filter(User.id == current_user.id).with_for_update().one()
    balance = payout_service.instructor_balance(db, current_user.id)
    if amount > balance["available"]:
        raise HTTPException(
            status_code=400,
            detail=("Amount exceeds your available balance "
                    f"(INR {balance['available']:.2f})"),
        )
    row = Withdrawal(
        user_id=current_user.id,
        amount=amount,
        method_data=body.method_data.model_dump(),
        status="pending",
    )
    db.add(row)
    db.flush()
    audit(
        db,
        tenant_id=None,
        actor_id=current_user.id,
        action="withdrawal.requested",
        target_type="withdrawal",
        target_id=row.withdraw_id,
        after={"status": "pending", "amount": amount},
    )
    enqueue(
        db,
        tenant_id=None,
        topic="commerce.withdrawal.requested",
        aggregate_type="withdrawal",
        aggregate_id=row.withdraw_id,
        payload={
            "withdrawal_id": row.withdraw_id,
            "instructor_id": current_user.id,
            "amount": amount,
        },
        idempotency_key=f"withdrawal:{row.withdraw_id}:requested",
    )
    db.commit()
    db.refresh(row)
    logger.info(
        "withdrawal requested withdraw_id=%s user_id=%s amount=%s method_type=%s",
        row.withdraw_id,
        current_user.id,
        amount,
        body.method_data.type,
    )
    return _withdrawal_out(row)


_ADMIN_STATUSES = ("pending", "approved", "rejected", "paid")


def _admin_out(row: Withdrawal, user: User) -> AdminWithdrawalOut:
    base = _withdrawal_out(row)
    return AdminWithdrawalOut(
        **base.model_dump(),
        user_id=user.id,
        user_email=user.user_email or "",
        display_name=user.display_name or "",
        processed_by=row.processed_by,
    )


def _load_withdrawal(
    db: Session, withdraw_id: int, *, lock: bool = False
) -> tuple[Withdrawal, User]:
    query = (
        db.query(Withdrawal, User)
        .join(User, User.id == Withdrawal.user_id)
        .filter(Withdrawal.withdraw_id == withdraw_id)
    )
    if lock:
        query = query.with_for_update()
    result = query.first()
    if not result:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    return result


def _transition(
    db: Session,
    withdraw_id: int,
    *,
    to_status: str,
    actor: User,
    reject_detail: str = "",
    paid_reference: str = "",
) -> AdminWithdrawalOut:
    row, user = _load_withdrawal(db, withdraw_id, lock=True)
    try:
        payout_service.transition_withdrawal(
            db,
            row,
            to_status=to_status,
            actor_id=actor.id,
            reject_detail=reject_detail,
            paid_reference=paid_reference,
        )
    except payout_service.WithdrawalStateError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=exc.detail)
    db.commit()
    db.refresh(row)
    return _admin_out(row, user)


@admin_router.get("", response_model=list[AdminWithdrawalOut])
def list_withdrawals_admin(
    payout_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    if payout_status is not None and payout_status not in _ADMIN_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {', '.join(_ADMIN_STATUSES)}",
        )
    query = db.query(Withdrawal, User).join(User, User.id == Withdrawal.user_id)
    if payout_status:
        query = query.filter(Withdrawal.status == payout_status)
    rows = (
        query.order_by(Withdrawal.created_at.desc(), Withdrawal.withdraw_id.desc())
        .limit(500)
        .all()
    )
    return [_admin_out(row, user) for row, user in rows]


@admin_router.post("/{withdraw_id}/approve", response_model=AdminWithdrawalOut)
def approve_withdrawal(
    withdraw_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    return _transition(
        db, withdraw_id, to_status="approved", actor=current_user
    )


@admin_router.post("/{withdraw_id}/reject", response_model=AdminWithdrawalOut)
def reject_withdrawal(
    withdraw_id: int,
    body: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    return _transition(
        db,
        withdraw_id,
        to_status="rejected",
        actor=current_user,
        reject_detail=body.reject_detail,
    )


@admin_router.post("/{withdraw_id}/mark-paid", response_model=AdminWithdrawalOut)
def mark_withdrawal_paid(
    withdraw_id: int,
    body: MarkPaidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    return _transition(
        db,
        withdraw_id,
        to_status="paid",
        actor=current_user,
        paid_reference=body.paid_reference,
    )
