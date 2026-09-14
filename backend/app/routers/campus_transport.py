"""Campus transport: routes, stops, assignments, boarding and the learner view."""

from datetime import date
import re

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.campus_transport import AssignmentCreate, BoardingPut, RouteCreate, RouteUpdate
from app.services import campus_transport as service
from app.services.auth_service import AuthService


router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


def _ascii(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "route"


@router.get("/{institution_id}/transport/routes")
def routes(institution_id: int, db: Session = Depends(get_db), user=Current):
    return service.list_routes(db, institution_id, user)


@router.post("/{institution_id}/transport/routes", status_code=201)
def route_create(institution_id: int, data: RouteCreate, db: Session = Depends(get_db), user=Current):
    return service.create_route(db, institution_id, user, data)


@router.patch("/{institution_id}/transport/routes/{route_id}")
def route_update(institution_id: int, route_id: int, data: RouteUpdate, db: Session = Depends(get_db), user=Current):
    return service.update_route(db, institution_id, user, route_id, data)


@router.get("/{institution_id}/transport/routes/{route_id}/roster")
def roster(institution_id: int, route_id: int, day: date | None = None, db: Session = Depends(get_db), user=Current):
    return service.roster(db, institution_id, user, route_id, day)


@router.get("/{institution_id}/transport/routes/{route_id}/roster.csv")
def roster_csv(institution_id: int, route_id: int, db: Session = Depends(get_db), user=Current):
    body, name = service.roster_csv(db, institution_id, user, route_id)
    return Response(
        body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="transport-{_ascii(name)}.csv"',
            "Cache-Control": "private, no-store",
        },
    )


@router.put("/{institution_id}/transport/routes/{route_id}/boarding")
def boarding(institution_id: int, route_id: int, data: BoardingPut, db: Session = Depends(get_db), user=Current):
    return service.put_boarding(db, institution_id, user, route_id, data)


@router.post("/{institution_id}/transport/routes/{route_id}/assignments", status_code=201)
def assignment_create(institution_id: int, route_id: int, data: AssignmentCreate, db: Session = Depends(get_db), user=Current):
    return service.assign_student(db, institution_id, user, route_id, data)


@router.post("/{institution_id}/transport/assignments/{assignment_id}/end")
def assignment_end(institution_id: int, assignment_id: int, db: Session = Depends(get_db), user=Current):
    return service.end_assignment(db, institution_id, user, assignment_id)


@router.get("/{institution_id}/transport/me")
def me(
    institution_id: int,
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.me(db, institution_id, user, student_user_id)
