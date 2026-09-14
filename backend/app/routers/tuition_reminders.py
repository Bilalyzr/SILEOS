"""Tuition fee reminder policy, delivery log and manual triggers (managers only)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.tuition_reminders import PolicyPut
from app.services import tuition_reminders as service
from app.services.auth_service import AuthService


router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


@router.get("/{institution_id}/fees/reminders/policy")
def policy(institution_id: int, db: Session = Depends(get_db), user=Current):
    return service.get_policy(db, institution_id, user)


@router.put("/{institution_id}/fees/reminders/policy")
def policy_put(institution_id: int, data: PolicyPut, db: Session = Depends(get_db), user=Current):
    return service.save_policy(db, institution_id, user, data)


@router.get("/{institution_id}/fees/reminders")
def reminders(
    institution_id: int,
    status: str | None = Query(default=None, pattern="^(queued|sent|failed|skipped)$"),
    after_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.list_reminders(db, institution_id, user, status=status, after_id=after_id, limit=limit)


@router.post("/{institution_id}/fees/reminders/run-now")
def run_now(institution_id: int, db: Session = Depends(get_db), user=Current):
    return service.run_now(db, institution_id, user)


@router.post("/{institution_id}/fees/reminders/{reminder_id}/retry")
def retry(institution_id: int, reminder_id: int, db: Session = Depends(get_db), user=Current):
    return service.retry(db, institution_id, user, reminder_id)


@router.post("/{institution_id}/fees/assignments/{assignment_id}/remind", status_code=201)
def remind(institution_id: int, assignment_id: int, db: Session = Depends(get_db), user=Current):
    return service.remind_assignment(db, institution_id, user, assignment_id)
