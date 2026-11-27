"""Utporul coding assessment authoring and learner submission APIs."""

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.csv_safety import sanitize_csv_cell
from app.core.database import get_db
from app.schemas.coding_assessment import (
    ChallengeAction,
    ChallengeCreate,
    ChallengeUpdate,
    DraftSave,
    LessonBlocksReplace,
    SubmissionCreate,
)
from app.services import coding_analytics_service as analytics
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


@router.get("/courses/{course_id}/metrics")
def course_metrics(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return analytics.instructor_metrics(db, course_id, user)


@router.get("/courses/{course_id}/metrics.csv")
def course_metrics_csv(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    rows = analytics.instructor_metrics_rows(db, course_id, user)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow([sanitize_csv_cell(cell) for cell in row])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="coding-metrics-course-{course_id}.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/learner/progress")
def learner_progress(
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return analytics.learner_progress(db, user)


@router.get("/submissions/{submission_id}")
def submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.submission_detail(db, submission_id, user)


@router.get("/courses/{course_id}/lessons/{lesson_id}/blocks")
def lesson_blocks(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.lesson_blocks(db, course_id, lesson_id, user)


@router.put("/courses/{course_id}/lessons/{lesson_id}/blocks")
def replace_lesson_blocks(
    course_id: int,
    lesson_id: int,
    command: LessonBlocksReplace,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.replace_lesson_blocks(db, course_id, lesson_id, command, user)


@router.get("/challenges/{slug}/draft")
def get_draft(
    slug: str,
    language: str,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.get_draft(db, slug, language, user)


@router.put("/challenges/{slug}/draft")
def save_draft(
    slug: str,
    command: DraftSave,
    db: Session = Depends(get_db),
    user=Depends(AuthService.get_current_active_user),
):
    return service.save_draft(db, slug, command, user)
