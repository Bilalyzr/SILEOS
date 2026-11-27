"""Phase 5 (part A): review comments and review queue for coding submissions.

Mounted at /api/v1/utporul/coding (see app/main.py). Rules live in
app/services/coding_review_service.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.coding_review import ReviewCommentIn
from app.services import coding_review_service as service
from app.services.auth_service import AuthService


router = APIRouter()


@router.get("/submissions/{submission_id}/comments")
def list_comments(
    submission_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.list_comments(db, submission_id, user)


@router.post("/submissions/{submission_id}/comments", status_code=201)
def create_comment(
    submission_id: int,
    command: ReviewCommentIn,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.create_comment(db, submission_id, command, user)


@router.post("/comments/{comment_id}/resolve")
def resolve_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.resolve_comment(db, comment_id, user)


@router.post("/submissions/{submission_id}/review-request", status_code=201)
def request_review(
    submission_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.request_review(db, submission_id, user)


@router.post("/submissions/{submission_id}/review-done")
def mark_reviewed(
    submission_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.mark_reviewed(db, submission_id, user)


@router.get("/courses/{course_id}/review-queue")
def review_queue(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.review_queue(db, course_id, user)
