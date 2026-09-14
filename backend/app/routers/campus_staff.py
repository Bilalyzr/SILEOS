"""Staff leave, balances, substitutions and the leave report."""

from datetime import datetime
import re

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.campus_staff import AssignIn, Decision, LeaveCreate, LeaveTypesPut, RejectIn
from app.services import campus_staff as service
from app.services.auth_service import AuthService


router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


@router.get("/{institution_id}/staff/leave/types")
def leave_types(institution_id: int, academic_year: str | None = None, db: Session = Depends(get_db), user=Current):
    return service.list_types(db, institution_id, user, academic_year)


@router.put("/{institution_id}/staff/leave/types")
def leave_types_put(institution_id: int, data: LeaveTypesPut, db: Session = Depends(get_db), user=Current):
    return service.put_types(db, institution_id, user, data)


@router.get("/{institution_id}/staff/leave/balances")
def leave_balances(
    institution_id: int,
    member_id: int | None = Query(default=None, gt=0),
    academic_year: str | None = None,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.balances(db, institution_id, user, member_id, academic_year)


@router.get("/{institution_id}/staff/leave/report")
def leave_report(
    institution_id: int,
    academic_year: str | None = None,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    user=Current,
):
    report = service.leave_report(db, institution_id, user, academic_year)
    if format == "csv":
        # Header values must be latin-1; academic years often carry an en dash.
        label = re.sub(r"[^A-Za-z0-9._-]+", "-", report["academic_year"]).strip("-") or "campus"
        return Response(
            service.leave_report_csv(report).encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="leave-report-{label}.csv"',
                "Cache-Control": "private, no-store",
            },
        )
    return report


@router.get("/{institution_id}/staff/leave")
def leave_list(
    institution_id: int,
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected|cancelled)$"),
    member_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.list_leave(db, institution_id, user, status, member_id)


@router.post("/{institution_id}/staff/leave", status_code=201)
def leave_create(institution_id: int, data: LeaveCreate, db: Session = Depends(get_db), user=Current):
    return service.create_leave(db, institution_id, user, data)


@router.post("/{institution_id}/staff/leave/{leave_id}/approve")
def leave_approve(institution_id: int, leave_id: int, data: Decision, db: Session = Depends(get_db), user=Current):
    return service.approve_leave(db, institution_id, user, leave_id, data)


@router.post("/{institution_id}/staff/leave/{leave_id}/reject")
def leave_reject(institution_id: int, leave_id: int, data: RejectIn, db: Session = Depends(get_db), user=Current):
    return service.reject_leave(db, institution_id, user, leave_id, data)


@router.post("/{institution_id}/staff/leave/{leave_id}/cancel")
def leave_cancel(institution_id: int, leave_id: int, db: Session = Depends(get_db), user=Current):
    return service.cancel_leave(db, institution_id, user, leave_id)


@router.get("/{institution_id}/staff/substitutions")
def substitutions(
    institution_id: int,
    status: str | None = Query(default=None, pattern="^(open|assigned|released)$"),
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.list_substitutions(db, institution_id, user, status, starts_after, starts_before)


@router.get("/{institution_id}/staff/substitutions/{sub_id}/candidates")
def substitution_candidates(institution_id: int, sub_id: int, db: Session = Depends(get_db), user=Current):
    return service.candidates(db, institution_id, user, sub_id)


@router.post("/{institution_id}/staff/substitutions/{sub_id}/assign")
def substitution_assign(institution_id: int, sub_id: int, data: AssignIn, db: Session = Depends(get_db), user=Current):
    return service.assign(db, institution_id, user, sub_id, data)


@router.post("/{institution_id}/staff/substitutions/{sub_id}/unassign")
def substitution_unassign(institution_id: int, sub_id: int, db: Session = Depends(get_db), user=Current):
    return service.unassign(db, institution_id, user, sub_id)
