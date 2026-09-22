"""Private lease protocol for the isolated code-runner service."""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.coding_assessment import JudgeClaim, JudgeComplete, JudgeFail
from app.services import coding_assessment_service as service


router = APIRouter()


def require_code_runner(
    x_code_runner_token: str = Header(default="", alias="X-Code-Runner-Token"),
):
    configured = get_settings().CODE_RUNNER_TOKEN
    if len(configured) < 32:
        raise HTTPException(503, "Code runner is not configured.")
    if not secrets.compare_digest(configured, x_code_runner_token):
        raise HTTPException(401, "Invalid code runner credential.")


@router.post("/jobs/claim")
def claim(
    command: JudgeClaim,
    db: Session = Depends(get_db),
    _=Depends(require_code_runner),
):
    job = service.claim_job(db, command.judge_version)
    return {"job": job}


@router.post("/jobs/{job_id}/complete")
def complete(
    job_id: int,
    command: JudgeComplete,
    db: Session = Depends(get_db),
    _=Depends(require_code_runner),
):
    return service.complete_job(db, job_id, command)


@router.post("/jobs/{job_id}/fail")
def fail(
    job_id: int,
    command: JudgeFail,
    db: Session = Depends(get_db),
    _=Depends(require_code_runner),
):
    return service.fail_job(db, job_id, command)
