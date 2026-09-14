"""Utporul coding assessment authoring and learner submission APIs."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.coding_assessment import (
    ChallengeAction,
    ChallengeCreate,
    ChallengeUpdate,
    SubmissionCreate,
)
from app.services import coding_assessment_service as service
from app.services.auth_service import AuthService


router = APIRouter()


@router.get("/courses")
def editor_courses(
    db: Session = Depends(get_db),
    user=Depends(AuthService.require_instructor),
):
    return service.list_editor_courses(db, user)


@router.get("/learner/challenges")
def learner_challenges(
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.list_for_learner(db, user)


@router.get("/courses/{course_id}/challenges")
def editor_challenges(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.require_instructor),
):
    return service.list_for_editor(db, course_id, user)


@router.post("/courses/{course_id}/challenges", status_code=201)
def create_challenge(
    course_id: int,
    command: ChallengeCreate,
    db: Session = Depends(get_db),
    user=Depends(AuthService.require_instructor),
):
    return service.create_challenge(db, course_id, command, user)


@router.put("/challenges/{challenge_id}")
def update_challenge(
    challenge_id: int,
    command: ChallengeUpdate,
    db: Session = Depends(get_db),
    user=Depends(AuthService.require_instructor),
):
    return service.update_challenge(db, challenge_id, command, user)


@router.post("/challenges/{challenge_id}/action")
def challenge_action(
    challenge_id: int,
    command: ChallengeAction,
    db: Session = Depends(get_db),
    user=Depends(AuthService.require_instructor),
):
    return service.challenge_action(db, challenge_id, command, user)


@router.get("/challenges/{slug}")
def learner_challenge(
    slug: str,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.learner_challenge(db, slug, user)


@router.post("/challenges/{slug}/submissions", status_code=202)
def submit(
    slug: str,
    command: SubmissionCreate,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.submit(db, slug, command, user)


@router.get("/submissions/{submission_id}")
def submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.submission_detail(db, submission_id, user)
