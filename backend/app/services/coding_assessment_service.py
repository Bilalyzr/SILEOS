"""Secure API-side lifecycle for Utporul coding assessments.

Untrusted source is never executed in the web process. Submissions are placed
in a lease-based judge queue and completed by a separately isolated runner.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import re
import secrets

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.models.coding_assessment import (
    CodingCaseResult,
    CodingChallenge,
    CodingJudgeJob,
    CodingSubmission,
    CodingTestCase,
)
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.services.course_access import ADMIN_ROLES, can_edit


ACTIVE_ENROLLMENTS = ("enrolled", "active", "completed")
LEASE_SECONDS = 90
MAX_JUDGE_ATTEMPTS = 5


def _now():
    return datetime.now(timezone.utc)


def _slug(title: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:90] or "challenge"
    return f"{stem}-{secrets.token_hex(4)}"


def _save(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This coding record already exists. Refresh and retry.") from None


def _course_editor(db, course_id: int, user, *, lock: bool = False) -> Course:
    query = db.query(Course).filter_by(id=course_id)
    course = query.with_for_update().first() if lock else query.first()
    if course is None:
        raise HTTPException(404, "Course not found.")
    if (course.course_type or "").lower() != "utporul":
        raise HTTPException(
            422,
            "Coding assessments belong to Utporul skill-development courses.",
        )
    if not can_edit(db, course, user):
        raise HTTPException(403, "You cannot edit this course.")
    return course


def _challenge_editor(db, challenge_id: int, user, *, lock: bool = False):
    query = db.query(CodingChallenge).filter_by(id=challenge_id)
    challenge = query.with_for_update().first() if lock else query.first()
    if challenge is None:
        raise HTTPException(404, "Coding challenge not found.")
    _course_editor(db, challenge.course_id, user)
    return challenge


def _editor_dict(db, challenge: CodingChallenge) -> dict:
    return {
        **_challenge_dict(challenge),
        "test_cases": [
            {
                "id": row.id,
                "ordinal": row.ordinal,
                "visibility": row.visibility,
                "input_text": row.input_text,
                "expected_output": row.expected_output,
                "comparison": row.comparison,
                "weight": float(row.weight),
            }
            for row in db.query(CodingTestCase)
            .filter_by(challenge_id=challenge.id)
            .order_by(CodingTestCase.ordinal)
            .all()
        ],
    }


def _challenge_dict(challenge: CodingChallenge) -> dict:
    return {
        "id": challenge.id,
        "course_id": challenge.course_id,
        "tenant_id": challenge.tenant_id,
        "slug": challenge.slug,
        "title": challenge.title,
        "problem_statement": challenge.problem_statement,
        "input_format": challenge.input_format,
        "output_format": challenge.output_format,
        "constraints_text": challenge.constraints_text,
        "allowed_languages": challenge.allowed_languages,
        "starter_code": challenge.starter_code,
        "time_limit_ms": challenge.time_limit_ms,
        "memory_limit_mb": challenge.memory_limit_mb,
        "max_source_bytes": challenge.max_source_bytes,
        "max_attempts": challenge.max_attempts,
        "status": challenge.status,
        "version": challenge.version,
        "published_at": challenge.published_at,
    }


def list_for_editor(db, course_id: int, user) -> list[dict]:
    _course_editor(db, course_id, user)
    return [
        _editor_dict(db, row)
        for row in db.query(CodingChallenge)
        .filter_by(course_id=course_id)
        .order_by(CodingChallenge.id.desc())
        .all()
    ]


def list_editor_courses(db, user) -> list[dict]:
    """Return only the Utporul courses this author may manage."""
    query = db.query(Course).filter(func.lower(Course.course_type) == "utporul")
    if user.role not in ADMIN_ROLES:
        from app.models.course_ops import CourseCollaborator

        collaborated = db.query(CourseCollaborator.course_id).filter(
            CourseCollaborator.user_id == user.id
        )
        query = query.filter(
            or_(Course.post_author == user.id, Course.id.in_(collaborated))
        )
    return [
        {
            "id": course.id,
            "title": course.post_title,
            "status": course.post_status,
            "course_type": course.course_type,
        }
        for course in query.order_by(Course.post_title, Course.id).all()
    ]


def list_for_learner(db, user) -> list[dict]:
    """Discover published challenges across a learner's active enrolments."""
    if user.role in ADMIN_ROLES:
        rows = (
            db.query(CodingChallenge, Course.post_title)
            .join(Course, Course.id == CodingChallenge.course_id)
            .filter(CodingChallenge.status == "published")
            .order_by(Course.post_title, CodingChallenge.title)
            .all()
        )
    else:
        rows = (
            db.query(CodingChallenge, Course.post_title)
            .join(Course, Course.id == CodingChallenge.course_id)
            .join(
                Enrollment,
                (Enrollment.course_id == CodingChallenge.course_id)
                & (Enrollment.user_id == user.id),
            )
            .filter(
                CodingChallenge.status == "published",
                Course.post_status.in_(("publish", "published")),
                Enrollment.enrollment_status.in_(ACTIVE_ENROLLMENTS),
            )
            .order_by(Course.post_title, CodingChallenge.title)
            .all()
        )
    challenge_ids = [challenge.id for challenge, _ in rows]
    attempts_by_challenge = dict(
        db.query(CodingSubmission.challenge_id, func.count(CodingSubmission.id))
        .filter(
            CodingSubmission.user_id == user.id,
            CodingSubmission.challenge_id.in_(challenge_ids or [-1]),
        )
        .group_by(CodingSubmission.challenge_id)
        .all()
    )
    return [
        {
            "id": challenge.id,
            "slug": challenge.slug,
            "course_id": challenge.course_id,
            "course_title": course_title,
            "title": challenge.title,
            "allowed_languages": challenge.allowed_languages,
            "time_limit_ms": challenge.time_limit_ms,
            "memory_limit_mb": challenge.memory_limit_mb,
            "max_attempts": challenge.max_attempts,
            "attempts_used": attempts_by_challenge.get(challenge.id, 0),
        }
        for challenge, course_title in rows
    ]


def _apply_definition(challenge: CodingChallenge, command):
    for field in (
        "title",
        "problem_statement",
        "input_format",
        "output_format",
        "constraints_text",
        "allowed_languages",
        "starter_code",
        "time_limit_ms",
        "memory_limit_mb",
        "max_source_bytes",
        "max_attempts",
    ):
        setattr(challenge, field, getattr(command, field))
    unknown_starters = set(command.starter_code) - set(command.allowed_languages)
    if unknown_starters:
        raise HTTPException(422, "Starter code contains a language that is not allowed.")


def _replace_cases(db, challenge: CodingChallenge, cases):
    db.query(CodingTestCase).filter_by(challenge_id=challenge.id).delete(
        synchronize_session=False
    )
    for ordinal, case in enumerate(cases, start=1):
        db.add(
            CodingTestCase(
                challenge_id=challenge.id,
                ordinal=ordinal,
                **case.model_dump(),
            )
        )


def create_challenge(db, course_id: int, command, user) -> dict:
    _course_editor(db, course_id, user, lock=True)
    challenge = CodingChallenge(
        course_id=course_id,
        # Courses may be licensed to several institutions. Their canonical
        # assessment content therefore stays global; attempts are scoped by
        # the enrolled learner instead of being incorrectly assigned to the
        # first connected institution.
        tenant_id=None,
        slug=_slug(command.title),
        created_by=user.id,
        status="draft",
        version=1,
    )
    _apply_definition(challenge, command)
    db.add(challenge)
    db.flush()
    _replace_cases(db, challenge, command.test_cases)
    _save(db)
    return _editor_dict(db, challenge)


def update_challenge(db, challenge_id: int, command, user) -> dict:
    challenge = _challenge_editor(db, challenge_id, user, lock=True)
    if challenge.version != command.version:
        raise HTTPException(409, "This challenge changed. Refresh before saving.")
    if challenge.status != "draft":
        raise HTTPException(409, "Published or retired challenges are immutable.")
    _apply_definition(challenge, command)
    _replace_cases(db, challenge, command.test_cases)
    challenge.version += 1
    _save(db)
    return _editor_dict(db, challenge)


def challenge_action(db, challenge_id: int, command, user) -> dict:
    challenge = _challenge_editor(db, challenge_id, user, lock=True)
    if challenge.version != command.version:
        raise HTTPException(409, "This challenge changed. Refresh before publishing.")
    if command.action == "publish":
        if challenge.status != "draft":
            raise HTTPException(409, "Only a draft can be published.")
        cases = db.query(CodingTestCase).filter_by(challenge_id=challenge.id).all()
        if not cases or not any(row.visibility == "hidden" for row in cases):
            raise HTTPException(422, "Publish requires at least one hidden test case.")
        challenge.status = "published"
        challenge.published_at = _now()
    else:
        if challenge.status != "published":
            raise HTTPException(409, "Only a published challenge can be retired.")
        challenge.status = "retired"
    challenge.version += 1
    _save(db)
    return _editor_dict(db, challenge)


def _student_challenge(db, slug: str, user) -> CodingChallenge:
    challenge = db.query(CodingChallenge).filter_by(slug=slug, status="published").first()
    if challenge is None:
        raise HTTPException(404, "Coding challenge not found.")
    course = db.get(Course, challenge.course_id)
    if user.role in ADMIN_ROLES or can_edit(db, course, user):
        return challenge
    if course is None or course.post_status not in {"publish", "published"}:
        raise HTTPException(404, "Coding challenge not found.")
    enrolled = (
        db.query(Enrollment.id)
        .filter(
            Enrollment.course_id == challenge.course_id,
            Enrollment.user_id == user.id,
            Enrollment.enrollment_status.in_(ACTIVE_ENROLLMENTS),
        )
        .first()
    )
    if enrolled is None:
        raise HTTPException(403, "Enroll in this course to access the coding assessment.")
    return challenge


def learner_challenge(db, slug: str, user) -> dict:
    challenge = _student_challenge(db, slug, user)
    samples = [
        {
            "ordinal": row.ordinal,
            "input_text": row.input_text,
            "expected_output": row.expected_output,
            "comparison": row.comparison,
        }
        for row in db.query(CodingTestCase)
        .filter_by(challenge_id=challenge.id, visibility="sample")
        .order_by(CodingTestCase.ordinal)
        .all()
    ]
    attempts = (
        db.query(CodingSubmission)
        .filter_by(challenge_id=challenge.id, user_id=user.id)
        .count()
    )
    return {**_challenge_dict(challenge), "sample_cases": samples, "attempts_used": attempts}


def submit(db, slug: str, command, user) -> dict:
    challenge = _student_challenge(db, slug, user)
    if command.language not in (challenge.allowed_languages or []):
        raise HTTPException(422, "This language is not enabled for the challenge.")
    source = command.source_code.replace("\x00", "")
    if len(source.encode("utf-8")) > challenge.max_source_bytes:
        raise HTTPException(413, "Source code exceeds this challenge's size limit.")
    existing = (
        db.query(CodingSubmission)
        .filter_by(user_id=user.id, idempotency_key=command.idempotency_key)
        .first()
    )
    if existing:
        if existing.challenge_id != challenge.id:
            raise HTTPException(409, "This submission key was already used.")
        return submission_detail(db, existing.id, user)
    # Serialize attempt numbering and quota checks on the user row.
    from app.models.user import User

    db.query(User).filter_by(id=user.id).with_for_update().one()
    attempts = (
        db.query(func.count(CodingSubmission.id))
        .filter(
            CodingSubmission.challenge_id == challenge.id,
            CodingSubmission.user_id == user.id,
        )
        .scalar()
        or 0
    )
    if attempts >= challenge.max_attempts:
        raise HTTPException(409, "The maximum number of attempts has been reached.")
    submission = CodingSubmission(
        challenge_id=challenge.id,
        user_id=user.id,
        language=command.language,
        source_code=source,
        source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        idempotency_key=command.idempotency_key,
        status="queued",
        score=0,
        passed_cases=0,
        total_cases=db.query(CodingTestCase).filter_by(challenge_id=challenge.id).count(),
        attempt_number=attempts + 1,
    )
    db.add(submission)
    db.flush()
    db.add(CodingJudgeJob(submission_id=submission.id, status="queued", priority=100))
    _save(db)
    return submission_detail(db, submission.id, user)


def _can_view_submission(db, submission: CodingSubmission, user) -> bool:
    if submission.user_id == user.id or user.role in ADMIN_ROLES:
        return True
    challenge = db.get(CodingChallenge, submission.challenge_id)
    return bool(challenge and can_edit(db, db.get(Course, challenge.course_id), user))


def submission_detail(db, submission_id: int, user) -> dict:
    submission = db.get(CodingSubmission, submission_id)
    if submission is None or not _can_view_submission(db, submission, user):
        raise HTTPException(404, "Submission not found.")
    challenge = db.get(CodingChallenge, submission.challenge_id)
    cases = {
        row.id: row
        for row in db.query(CodingTestCase)
        .filter_by(challenge_id=submission.challenge_id)
        .all()
    }
    results = []
    for row in (
        db.query(CodingCaseResult)
        .filter_by(submission_id=submission.id)
        .order_by(CodingCaseResult.id)
        .all()
    ):
        case = cases[row.test_case_id]
        visible = case.visibility == "sample" or user.role in ADMIN_ROLES or can_edit(
            db, db.get(Course, challenge.course_id), user
        )
        results.append(
            {
                "test_case_id": row.test_case_id if visible else None,
                "visibility": case.visibility,
                "status": row.status,
                "actual_output": row.actual_output if visible else "",
                "stderr": row.stderr if visible else "",
                "execution_ms": row.execution_ms,
                "memory_kb": row.memory_kb,
                "score_awarded": float(row.score_awarded),
            }
        )
    return {
        "id": submission.id,
        "challenge_id": submission.challenge_id,
        "challenge_slug": challenge.slug,
        "language": submission.language,
        "source_code": submission.source_code,
        "source_sha256": submission.source_sha256,
        "status": submission.status,
        "score": float(submission.score),
        "passed_cases": submission.passed_cases,
        "total_cases": submission.total_cases,
        "error_code": submission.error_code,
        "attempt_number": submission.attempt_number,
        "judge_version": submission.judge_version,
        "submitted_at": submission.submitted_at,
        "started_at": submission.started_at,
        "completed_at": submission.completed_at,
        "results": results,
    }


def _normalize_output(value: str, comparison: str):
    value = value.replace("\r\n", "\n")
    if comparison == "exact":
        return value
    if comparison == "tokens":
        return value.split()
    return "\n".join(line.rstrip() for line in value.strip().split("\n"))


def claim_job(db, judge_version: str) -> dict | None:
    now = _now()
    # A worker can disappear after taking its fifth and final lease. Close
    # those exhausted jobs before looking for more work so submissions never
    # remain in `running` forever.
    exhausted = (
        db.query(CodingJudgeJob)
        .filter(
            CodingJudgeJob.status == "leased",
            CodingJudgeJob.lease_expires_at < now,
            CodingJudgeJob.attempts >= MAX_JUDGE_ATTEMPTS,
        )
        .with_for_update(skip_locked=True)
        .all()
    )
    for stale in exhausted:
        stale.status = "failed"
        stale.last_error = "Judge lease expired after maximum delivery attempts."
        stale.lease_token = ""
        stale.lease_expires_at = None
        submission = db.get(CodingSubmission, stale.submission_id)
        submission.status = "error"
        submission.error_code = "judge_unavailable"
        submission.completed_at = now
    if exhausted:
        db.flush()
    job = (
        db.query(CodingJudgeJob)
        .filter(
            or_(
                CodingJudgeJob.status == "queued",
                (CodingJudgeJob.status == "leased")
                & (CodingJudgeJob.lease_expires_at < now),
            ),
            CodingJudgeJob.available_at <= now,
            CodingJudgeJob.attempts < MAX_JUDGE_ATTEMPTS,
        )
        .order_by(CodingJudgeJob.priority, CodingJudgeJob.id)
        .with_for_update(skip_locked=True)
        .first()
    )
    if job is None:
        return None
    submission = db.get(CodingSubmission, job.submission_id)
    challenge = db.get(CodingChallenge, submission.challenge_id)
    cases = (
        db.query(CodingTestCase)
        .filter_by(challenge_id=challenge.id)
        .order_by(CodingTestCase.ordinal)
        .all()
    )
    job.status = "leased"
    job.attempts += 1
    job.lease_token = secrets.token_urlsafe(32)
    job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    submission.status = "running"
    submission.started_at = now
    submission.judge_version = judge_version
    _save(db)
    return {
        "job_id": job.id,
        "submission_id": submission.id,
        "lease_token": job.lease_token,
        "lease_expires_at": job.lease_expires_at,
        "language": submission.language,
        "source_code": submission.source_code,
        "source_sha256": submission.source_sha256,
        "limits": {
            "time_ms": challenge.time_limit_ms,
            "memory_mb": challenge.memory_limit_mb,
            "source_bytes": challenge.max_source_bytes,
            "network": "disabled",
        },
        "test_cases": [
            {"id": row.id, "input_text": row.input_text}
            for row in cases
        ],
    }


def complete_job(db, job_id: int, command) -> dict:
    now = _now()
    job = db.query(CodingJudgeJob).filter_by(id=job_id).with_for_update().first()
    if job is None:
        raise HTTPException(404, "Judge job not found.")
    if job.status == "completed":
        submission = db.get(CodingSubmission, job.submission_id)
        return {"submission_id": submission.id, "status": submission.status}
    if (
        job.status != "leased"
        or not secrets.compare_digest(job.lease_token, command.lease_token)
        or job.lease_expires_at is None
        or (job.lease_expires_at.replace(tzinfo=timezone.utc) if job.lease_expires_at.tzinfo is None else job.lease_expires_at) < now
    ):
        raise HTTPException(409, "Judge lease is invalid or expired.")
    submission = db.get(CodingSubmission, job.submission_id)
    challenge = db.get(CodingChallenge, submission.challenge_id)
    cases = {
        row.id: row
        for row in db.query(CodingTestCase)
        .filter_by(challenge_id=challenge.id)
        .all()
    }
    provided = {row.test_case_id for row in command.results}
    if provided != set(cases) or len(provided) != len(command.results):
        raise HTTPException(422, "Judge results must cover every test case exactly once.")

    total_weight = sum((Decimal(case.weight) for case in cases.values()), Decimal("0"))
    awarded = Decimal("0")
    passed = 0
    terminal_error = ""
    for result in command.results:
        case = cases[result.test_case_id]
        status = result.status
        if status == "completed":
            status = (
                "passed"
                if _normalize_output(result.actual_output, case.comparison)
                == _normalize_output(case.expected_output, case.comparison)
                else "wrong_answer"
            )
        score = Decimal(case.weight) if status == "passed" else Decimal("0")
        if status == "passed":
            passed += 1
            awarded += score
        elif status in {"compile_error", "internal_error"}:
            terminal_error = status
        db.add(
            CodingCaseResult(
                submission_id=submission.id,
                test_case_id=case.id,
                status=status,
                actual_output=result.actual_output[:100_000],
                stderr=result.stderr[:20_000],
                execution_ms=result.execution_ms,
                memory_kb=result.memory_kb,
                score_awarded=score,
            )
        )
    score_percent = awarded * Decimal("100") / total_weight
    submission.score = score_percent.quantize(Decimal("0.001"))
    submission.passed_cases = passed
    submission.total_cases = len(cases)
    submission.error_code = terminal_error
    submission.status = (
        "error" if terminal_error else "passed" if passed == len(cases) else "failed"
    )
    submission.completed_at = now
    job.status = "completed"
    job.lease_token = ""
    job.lease_expires_at = None
    _save(db)
    return {"submission_id": submission.id, "status": submission.status, "score": float(submission.score)}


def fail_job(db, job_id: int, command) -> dict:
    """Release a transient judge failure or terminally close the submission."""
    now = _now()
    job = db.query(CodingJudgeJob).filter_by(id=job_id).with_for_update().first()
    if job is None:
        raise HTTPException(404, "Judge job not found.")
    if job.status in {"completed", "failed", "cancelled"}:
        return {"job_id": job.id, "status": job.status}
    if job.status != "leased" or not secrets.compare_digest(
        job.lease_token, command.lease_token
    ):
        raise HTTPException(409, "Judge lease is invalid.")
    submission = db.get(CodingSubmission, job.submission_id)
    job.last_error = command.error[:2000]
    job.lease_token = ""
    job.lease_expires_at = None
    if command.retryable and job.attempts < MAX_JUDGE_ATTEMPTS:
        job.status = "queued"
        job.available_at = now + timedelta(seconds=min(300, 2 ** job.attempts))
        submission.status = "queued"
    else:
        job.status = "failed"
        submission.status = "error"
        submission.error_code = "judge_unavailable"
        submission.completed_at = now
    _save(db)
    return {"job_id": job.id, "status": job.status}
