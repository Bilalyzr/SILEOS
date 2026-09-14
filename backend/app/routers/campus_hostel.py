"""Campus hostel: blocks, rooms, allocations, passes, visitors, occupancy."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.campus_hostel import (
    AllocationCreate,
    BlockCreate,
    BlockUpdate,
    PassCreate,
    PassDecision,
    RoomsPut,
    VisitorCreate,
)
from app.services import campus_hostel as service
from app.services.auth_service import AuthService


router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


@router.get("/{institution_id}/hostel/blocks")
def blocks(institution_id: int, db: Session = Depends(get_db), user=Current):
    return service.list_blocks(db, institution_id, user)


@router.post("/{institution_id}/hostel/blocks", status_code=201)
def block_create(institution_id: int, data: BlockCreate, db: Session = Depends(get_db), user=Current):
    return service.create_block(db, institution_id, user, data)


@router.patch("/{institution_id}/hostel/blocks/{block_id}")
def block_update(institution_id: int, block_id: int, data: BlockUpdate, db: Session = Depends(get_db), user=Current):
    return service.update_block(db, institution_id, user, block_id, data)


@router.put("/{institution_id}/hostel/blocks/{block_id}/rooms")
def rooms_put(institution_id: int, block_id: int, data: RoomsPut, db: Session = Depends(get_db), user=Current):
    return service.put_rooms(db, institution_id, user, block_id, data)


@router.get("/{institution_id}/hostel/occupancy")
def occupancy(institution_id: int, db: Session = Depends(get_db), user=Current):
    return service.occupancy(db, institution_id, user)


@router.get("/{institution_id}/hostel/occupancy.csv")
def occupancy_csv(institution_id: int, db: Session = Depends(get_db), user=Current):
    return Response(
        service.occupancy_csv(db, institution_id, user).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="hostel-occupancy.csv"', "Cache-Control": "private, no-store"},
    )


@router.post("/{institution_id}/hostel/rooms/{room_id}/allocations", status_code=201)
def allocate(institution_id: int, room_id: int, data: AllocationCreate, db: Session = Depends(get_db), user=Current):
    return service.allocate(db, institution_id, user, room_id, data)


@router.post("/{institution_id}/hostel/allocations/{allocation_id}/checkout")
def allocation_checkout(institution_id: int, allocation_id: int, db: Session = Depends(get_db), user=Current):
    return service.checkout(db, institution_id, user, allocation_id)


@router.get("/{institution_id}/hostel/passes")
def passes(
    institution_id: int,
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected|returned)$"),
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.list_passes(db, institution_id, user, status, student_user_id)


@router.post("/{institution_id}/hostel/passes", status_code=201)
def pass_create(institution_id: int, data: PassCreate, db: Session = Depends(get_db), user=Current):
    return service.create_pass(db, institution_id, user, data)


@router.post("/{institution_id}/hostel/passes/{pass_id}/approve")
def pass_approve(institution_id: int, pass_id: int, data: PassDecision, db: Session = Depends(get_db), user=Current):
    return service.decide_pass(db, institution_id, user, pass_id, True, data)


@router.post("/{institution_id}/hostel/passes/{pass_id}/reject")
def pass_reject(institution_id: int, pass_id: int, data: PassDecision, db: Session = Depends(get_db), user=Current):
    return service.decide_pass(db, institution_id, user, pass_id, False, data)


@router.post("/{institution_id}/hostel/passes/{pass_id}/return")
def pass_return(institution_id: int, pass_id: int, db: Session = Depends(get_db), user=Current):
    return service.mark_returned(db, institution_id, user, pass_id)


@router.get("/{institution_id}/hostel/visitors")
def visitors(institution_id: int, day: date | None = None, db: Session = Depends(get_db), user=Current):
    return service.list_visitors(db, institution_id, user, day)


@router.post("/{institution_id}/hostel/visitors", status_code=201)
def visitor_create(institution_id: int, data: VisitorCreate, db: Session = Depends(get_db), user=Current):
    return service.log_visitor(db, institution_id, user, data)


@router.post("/{institution_id}/hostel/visitors/{visitor_id}/checkout")
def visitor_checkout(institution_id: int, visitor_id: int, db: Session = Depends(get_db), user=Current):
    return service.visitor_checkout(db, institution_id, user, visitor_id)


@router.get("/{institution_id}/hostel/me")
def me(
    institution_id: int,
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.me(db, institution_id, user, student_user_id)
