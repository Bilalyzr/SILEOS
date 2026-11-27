"""Phase 4: coding challenges in live class sessions.

Mounted at /api/v1/live (see app/main.py). Business rules live in
app/services/coding_live_service.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.coding_assessment import SubmissionCreate
from app.schemas.coding_live import LivePushIn
from app.services import coding_live_service as service
from app.services.auth_service import AuthService


router = APIRouter()


@router.post("/classes/{class_id}/coding-challenges", status_code=201)
def push_challenge(
    class_id: int,
    command: LivePushIn,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.push(db, class_id, command, user)


@router.get("/classes/{class_id}/coding-challenges")
def list_challenges(
    class_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.list_for_class(db, class_id, user)


@router.post("/coding-challenges/{live_id}/close")
def close_challenge(
    live_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.close(db, live_id, user)


@router.post("/coding-challenges/{live_id}/reveal")
def reveal_solution(
    live_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.reveal(db, live_id, user)


@router.get("/coding-challenges/{live_id}")
def learner_challenge(
    live_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.learner_view(db, live_id, user)


@router.post("/coding-challenges/{live_id}/submissions", status_code=202)
def submit_challenge(
    live_id: int,
    command: SubmissionCreate,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.submit(db, live_id, command, user)


@router.get("/coding-challenges/{live_id}/board")
def results_board(
    live_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.board(db, live_id, user)
