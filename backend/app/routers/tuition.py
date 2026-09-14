"""Institution tuition fee API.

Mount this router at ``/api/v1/institutions``.  It is intentionally separate
from the campus subscription and SashaInfinity commerce routers.
"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.tuition import (
    FeeAssignmentCreate,
    FeePlanCreate,
    FeePlanListOut,
    FeePlanOut,
    TuitionAccountListOut,
    TuitionAdjustmentCreate,
    TuitionAdjustmentRecordedOut,
    TuitionAgingOut,
    TuitionAssignmentOut,
    TuitionPaymentCreate,
    TuitionPaymentRecordedOut,
    TuitionReceiptOut,
    TuitionSelfAccountsOut,
    TuitionSummaryOut,
)
from app.services.auth_service import AuthService
from app.services import tuition_service as service


router = APIRouter()
CurrentUser = Depends(AuthService.get_current_active_user)


@router.get("/{institution_id}/fees/plans", response_model=FeePlanListOut)
def list_fee_plans(
    institution_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.list_plans(db, institution_id, user)


@router.post(
    "/{institution_id}/fees/plans",
    response_model=FeePlanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_fee_plan(
    institution_id: int,
    data: FeePlanCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.create_plan(db, institution_id, user, data)


@router.post(
    "/{institution_id}/fees/plans/{plan_id}/publish", response_model=FeePlanOut
)
def publish_fee_plan(
    institution_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.publish_plan(db, institution_id, plan_id, user)


@router.get("/{institution_id}/fees/assignments", response_model=TuitionAccountListOut)
def list_fee_assignments(
    institution_id: int,
    status_filter: Literal["active", "settled", "cancelled"]
    | None = Query(default=None, alias="status"),
    student_member_id: int | None = Query(default=None, gt=0),
    after_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.list_assignments(
        db,
        institution_id,
        user,
        status=status_filter,
        student_member_id=student_member_id,
        after_id=after_id,
        limit=limit,
    )


@router.post(
    "/{institution_id}/fees/assignments",
    response_model=TuitionAssignmentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_fee_assignment(
    institution_id: int,
    data: FeeAssignmentCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.assign_plan(db, institution_id, user, data)


@router.get(
    "/{institution_id}/fees/assignments/{assignment_id}",
    response_model=TuitionAssignmentOut,
)
def get_fee_assignment(
    institution_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.assignment_detail(db, institution_id, assignment_id, user)


@router.post(
    "/{institution_id}/fees/assignments/{assignment_id}/payments",
    response_model=TuitionPaymentRecordedOut,
    status_code=status.HTTP_201_CREATED,
)
def record_fee_payment(
    institution_id: int,
    assignment_id: int,
    data: TuitionPaymentCreate,
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.record_payment(
        db, institution_id, assignment_id, user, data, idempotency_key
    )


@router.post(
    "/{institution_id}/fees/assignments/{assignment_id}/adjustments",
    response_model=TuitionAdjustmentRecordedOut,
    status_code=status.HTTP_201_CREATED,
)
def record_fee_adjustment(
    institution_id: int,
    assignment_id: int,
    data: TuitionAdjustmentCreate,
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.record_adjustment(
        db, institution_id, assignment_id, user, data, idempotency_key
    )


@router.get("/{institution_id}/fees/me", response_model=TuitionSelfAccountsOut)
def my_tuition_accounts(
    institution_id: int,
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.self_accounts(db, institution_id, user, student_user_id)


@router.get("/{institution_id}/fees/summary", response_model=TuitionSummaryOut)
def tuition_summary(
    institution_id: int,
    as_of: date | None = None,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.summary(db, institution_id, user, as_of)


@router.get("/{institution_id}/fees/aging", response_model=TuitionAgingOut)
def tuition_aging(
    institution_id: int,
    as_of: date | None = None,
    after_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.aging(
        db, institution_id, user, as_of, after_id=after_id, limit=limit
    )


@router.get(
    "/{institution_id}/fees/receipts/{receipt_id}", response_model=TuitionReceiptOut
)
def tuition_receipt(
    institution_id: int,
    receipt_id: int,
    response: Response,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return service.receipt_detail(db, institution_id, receipt_id, user)
