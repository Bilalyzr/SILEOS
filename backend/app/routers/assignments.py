"""
Assignment Management Router - SashaInfinity LMS API
Handles assignment CRUD operations and submissions
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import logging

from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User
from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus, AssignmentStatus, LatePolicy
from app.models.course import Course
from app.services.auth_service import AuthService
from app.services.course_access import can_edit
from app.services.notification_service import create_notification

router = APIRouter()
logger = logging.getLogger(__name__)

VALID_LATE_POLICIES = {p.value for p in LatePolicy}
VALID_ASSIGNMENT_STATUSES = {s.value for s in AssignmentStatus}

# Same upload root uploads.py writes /assignment-file uploads under —
# needed here (review finding I4) to verify a submitted file_url actually
# exists on disk and belongs to the submitting user before accepting it.
_UPLOAD_DIR = Path(get_settings().UPLOAD_DIR)

MAX_RUBRIC_CRITERIA = 20


def _parse_due_date(raw, allow_past=False) -> datetime:
    """Parse a caller-supplied dueDate string (B12). Raises 422 on anything
    that doesn't parse instead of silently discarding it — a bad dueDate
    used to be swallowed and stored as None (create) or left unchanged
    (update) with no error back to the caller.

    A due date in the past is rejected on create/update unless `allow_past`
    is set (used when a caller re-reads a stored value): a deadline that
    already lapsed can never be met, and accepting it silently publishes
    assignments that are instantly overdue."""
    try:
        dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid dueDate: {raw!r}. Expected an ISO-8601 datetime string.",
        )
    if not allow_past and dt < datetime.now(dt.tzinfo or timezone.utc) - timedelta(minutes=5):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Due date cannot be in the past.",
        )
    return dt

def _json_list(value):
    """Tolerant reader for JSON-column list fields (B9). Writers now assign
    direct Python values (no json.dumps) to allowed_file_types/attachments/
    files — real JSON columns, same as `rubric`. Legacy rows written before
    this fix may still hold a double-encoded JSON string; this helper reads
    either shape: json.loads() a str, pass through anything else (list/None)."""
    if isinstance(value, str):
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError):
            return []
    return value or []


def _validate_rubric_shape(rubric) -> list:
    """Validate an assignment's rubric field on create/update (spec Task 2
    item 3): a list of at most MAX_RUBRIC_CRITERIA {criterion, max_points}
    entries, each with a non-empty string criterion and a positive numeric
    max_points. Returns the normalized list (max_points coerced to float)
    or raises 400. `None`/empty is valid (no rubric)."""
    if rubric is None:
        return []
    if not isinstance(rubric, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rubric must be a list of {criterion, max_points} entries",
        )
    if len(rubric) > MAX_RUBRIC_CRITERIA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"rubric may have at most {MAX_RUBRIC_CRITERIA} criteria",
        )
    normalized = []
    seen = set()
    for entry in rubric:
        if not isinstance(entry, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each rubric entry must be an object with criterion and max_points",
            )
        criterion = entry.get("criterion")
        if not isinstance(criterion, str) or not criterion.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each rubric entry needs a non-empty 'criterion' string",
            )
        if criterion in seen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate rubric criterion: {criterion}",
            )
        seen.add(criterion)
        max_points = entry.get("max_points")
        try:
            max_points = float(max_points)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rubric entry '{criterion}' needs a numeric max_points",
            )
        if max_points <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rubric entry '{criterion}' max_points must be > 0",
            )
        normalized.append({"criterion": criterion, "max_points": max_points})
    return normalized


def _as_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip — reattach UTC before comparing
    against an aware `now`. Mirrors live_class_service._as_utc /
    quizzes._as_utc."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _is_owner_or_admin(course: Course, current_user: User) -> bool:
    return course is not None and (
        course.post_author == current_user.id or current_user.role == "admin"
    )


@router.get("/assignments/{assignment_id}")
async def get_assignment_basic(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get basic assignment info (just course_id for navigation)
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "title": assignment.title
    }


@router.get("/courses/{course_id}/assignments")
async def get_course_assignments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get all assignments for a course. Students see only `published`
    assignments; the course owner and admins see every status (draft
    included) so they can manage unpublished work.
    """
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    query = db.query(Assignment).filter(Assignment.course_id == course_id)
    if not _is_owner_or_admin(course, current_user):
        query = query.filter(Assignment.status == AssignmentStatus.PUBLISHED)

    # Get all assignments for this course
    assignments = query.order_by(Assignment.created_at.desc()).all()

    # Parse and return assignments
    result = []
    for assignment in assignments:
        allowed_file_types = _json_list(assignment.allowed_file_types)
        attachments = _json_list(assignment.attachments)

        result.append({
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "instructions": assignment.instructions,
            "attachments": attachments,
            "dueDate": assignment.due_date.isoformat() if assignment.due_date else None,
            "totalPoints": assignment.total_points,
            "allowedFileTypes": allowed_file_types,
            "maxFileSize": assignment.max_file_size,
            "maxFiles": assignment.max_files,
            "submissionType": assignment.submission_type,
            "status": assignment.status.value if isinstance(assignment.status, AssignmentStatus) else assignment.status,
            "created_at": assignment.created_at.isoformat()
        })

    return result


@router.post("/courses/{course_id}/assignments")
async def create_assignment(
    course_id: int,
    assignment_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Create a new assignment for a course
    """
    # Verify course exists and user has permission
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add assignments to this course"
        )

    # Parse due date (B12: invalid dueDate now 422s instead of silently
    # storing None)
    due_date = None
    if assignment_data.get("dueDate"):
        due_date = _parse_due_date(assignment_data["dueDate"])

    # status lifecycle (spec A1.7): accept a caller-supplied status,
    # validated against the enum; default stays "published" for backward
    # compatibility with existing callers that don't send one.
    status_in = assignment_data.get("status", "published")
    if status_in not in VALID_ASSIGNMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {sorted(VALID_ASSIGNMENT_STATUSES)}"
        )

    # late_policy / late_penalty_pct (spec A1.5)
    late_policy_in = assignment_data.get("latePolicy", "allow")
    if late_policy_in not in VALID_LATE_POLICIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid latePolicy. Must be one of: {sorted(VALID_LATE_POLICIES)}"
        )
    late_penalty_pct_in = assignment_data.get("latePenaltyPct", 0)
    try:
        late_penalty_pct_in = int(late_penalty_pct_in)
    except (TypeError, ValueError):
        late_penalty_pct_in = 0
    late_penalty_pct_in = max(0, min(100, late_penalty_pct_in))

    rubric_in = _validate_rubric_shape(assignment_data.get("rubric"))

    # Create assignment
    new_assignment = Assignment(
        course_id=course_id,
        created_by=current_user.id,
        title=assignment_data.get("title", "Untitled Assignment"),
        description=assignment_data.get("description", ""),
        instructions=assignment_data.get("instructions", ""),
        due_date=due_date,
        total_points=assignment_data.get("totalPoints", 100),
        allowed_file_types=assignment_data.get("allowedFileTypes", []),
        max_file_size=assignment_data.get("maxFileSize", 10),
        max_files=assignment_data.get("maxFiles", 5),
        submission_type=assignment_data.get("submissionType", "both"),
        attachments=assignment_data.get("attachments", []),
        status=status_in,
        late_policy=late_policy_in,
        late_penalty_pct=late_penalty_pct_in,
        rubric=rubric_in,
    )

    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)

    return {
        "id": new_assignment.id,
        "message": "Assignment created successfully"
    }


@router.get("/courses/{course_id}/assignments/{assignment_id}")
async def get_assignment(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get assignment details. A DRAFT assignment is only visible to the
    course owner/admin — students get 404 (matches the list filter, and
    avoids leaking draft existence via a distinct 403).
    """
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if assignment.status != AssignmentStatus.PUBLISHED and not _is_owner_or_admin(course, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Parse allowed file types / attachments (tolerant of legacy
    # double-encoded rows — see _json_list)
    allowed_file_types = _json_list(assignment.allowed_file_types)
    attachments = _json_list(assignment.attachments)

    # Check if student has submitted
    submission = None
    if current_user.role == "student":
        submission = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.user_id == current_user.id
        ).first()

    return {
        "id": assignment.id,
        "title": assignment.title,
        "description": assignment.description,
        "instructions": assignment.instructions,
        "attachments": attachments,
        "dueDate": assignment.due_date.isoformat() if assignment.due_date else None,
        "totalPoints": assignment.total_points,
        "allowedFileTypes": allowed_file_types,
        "maxFileSize": assignment.max_file_size,
        "maxFiles": assignment.max_files,
        "submissionType": assignment.submission_type,
        "status": assignment.status.value if isinstance(assignment.status, AssignmentStatus) else assignment.status,
        "latePolicy": assignment.late_policy,
        "latePenaltyPct": assignment.late_penalty_pct,
        "rubric": assignment.rubric or [],
        "isSubmitted": submission is not None,
        "submission": {
            "id": submission.id,
            "textContent": submission.text_content,
            "files": _json_list(submission.files),
            "submittedAt": submission.submitted_at.isoformat() if submission.submitted_at else None,
            # `if submission.grade` treats a legitimate score of 0 as absent,
            # so a student who scored zero was reported as ungraded. Test for
            # None explicitly.
            "grade": float(submission.grade) if submission.grade is not None else None,
            "feedback": submission.feedback,
            "status": submission.status.value if isinstance(submission.status, SubmissionStatus) else submission.status,
            "isLate": submission.is_late,
            "rubricScores": submission.rubric_scores,
        } if submission else None
    }


@router.put("/courses/{course_id}/assignments/{assignment_id}")
async def update_assignment(
    course_id: int,
    assignment_id: int,
    assignment_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Update an existing assignment
    """
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Check permission
    course = db.query(Course).filter(Course.id == course_id).first()
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this assignment"
        )

    # Parse due date (B12: invalid dueDate now 422s instead of silently
    # leaving the previous value unchanged)
    if assignment_data.get("dueDate"):
        assignment.due_date = _parse_due_date(assignment_data["dueDate"])

    # Update fields
    assignment.title = assignment_data.get("title", assignment.title)
    assignment.description = assignment_data.get("description", assignment.description)
    assignment.instructions = assignment_data.get("instructions", assignment.instructions)
    assignment.total_points = assignment_data.get("totalPoints", assignment.total_points)
    assignment.max_file_size = assignment_data.get("maxFileSize", assignment.max_file_size)
    assignment.max_files = assignment_data.get("maxFiles", assignment.max_files)
    assignment.submission_type = assignment_data.get("submissionType", assignment.submission_type)

    if "allowedFileTypes" in assignment_data:
        assignment.allowed_file_types = assignment_data["allowedFileTypes"]

    if "attachments" in assignment_data:
        assignment.attachments = assignment_data["attachments"]

    # status lifecycle (spec A1.7): update now reads status too (previously
    # it never did, so a draft could never be published without direct DB
    # access).
    if "status" in assignment_data:
        status_in = assignment_data["status"]
        if status_in not in VALID_ASSIGNMENT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {sorted(VALID_ASSIGNMENT_STATUSES)}"
            )
        assignment.status = status_in

    if "latePolicy" in assignment_data:
        late_policy_in = assignment_data["latePolicy"]
        if late_policy_in not in VALID_LATE_POLICIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid latePolicy. Must be one of: {sorted(VALID_LATE_POLICIES)}"
            )
        assignment.late_policy = late_policy_in

    if "latePenaltyPct" in assignment_data:
        try:
            pct = int(assignment_data["latePenaltyPct"])
        except (TypeError, ValueError):
            pct = assignment.late_penalty_pct
        assignment.late_penalty_pct = max(0, min(100, pct))

    if "rubric" in assignment_data:
        assignment.rubric = _validate_rubric_shape(assignment_data["rubric"])

    db.commit()

    return {
        "id": assignment.id,
        "message": "Assignment updated successfully"
    }


@router.delete("/courses/{course_id}/assignments/{assignment_id}")
async def delete_assignment(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Delete an assignment
    """
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.course_id == course_id
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Check permission
    course = db.query(Course).filter(Course.id == course_id).first()
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this assignment"
        )

    db.delete(assignment)
    db.commit()

    return {"message": "Assignment deleted successfully"}


def _notify_instructor_of_submission(db, assignment, student, submission_id, background_tasks):
    """Notify the course instructor that a student submitted an assignment."""
    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    if course:
        create_notification(
            db, user_id=course.post_author,
            type="submission_received",
            title="New assignment submission",
            message=f"{student.display_name} submitted '{assignment.title}'.",
            link="/instructor/assignments",
            related_id=submission_id,
            send_email=True, background_tasks=background_tasks,
        )


def _file_url_of(f) -> str:
    if isinstance(f, dict):
        return str(f.get("file_url") or f.get("filename") or f.get("url") or "")
    return str(f)


def _validate_submission_files(assignment: Assignment, files: list, current_user: User) -> None:
    """Server-side re-check (spec A1.8) of the declared `files` list against
    the assignment's own allowed_file_types / max_files, PLUS ownership and
    existence (review finding I4): a submitted file_url is only accepted
    when it points at THIS assignment's upload directory, was uploaded by
    THIS user (u{user_id}_ filename prefix — see uploads.py
    _user_file_prefix), and actually exists on disk. Without this a
    student could submit a `files` list referencing another student's
    already-uploaded file (or an arbitrary path) with no server-side
    rejection — the upload endpoint's own validation only guards what IT
    accepts, not what submit_assignment is later told to attach.
    Extension check is case/dot-insensitive; a file dict/string with no
    recognizable extension is rejected rather than silently allowed."""
    if not files:
        return

    max_files = assignment.max_files or 5
    if len(files) > max_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files: max {max_files} allowed for this assignment"
        )

    allowed_types = {str(t).lower().lstrip(".") for t in _json_list(assignment.allowed_file_types)}

    # Path prefix + filename-ownership + on-disk-existence check (I4).
    # /uploads/assignments/{assignment_id}/u{user_id}_<uuid>.<ext> is the
    # exact shape uploads.py's /assignment-file endpoint writes.
    expected_prefix = f"/uploads/assignments/{assignment.id}/"
    expected_filename_prefix = f"u{current_user.id}_"
    upload_dir = (_UPLOAD_DIR / "assignments" / str(assignment.id)).resolve()

    for f in files:
        url = _file_url_of(f)
        name = url.rsplit("/", 1)[-1] if url else ""
        ext = name.rsplit(".", 1)[-1].lower() if name and "." in name else ""

        if allowed_types and ext not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File type '.{ext or '?'}' not allowed for this assignment. "
                    f"Allowed: {sorted(allowed_types)}"
                )
            )

        if not url.startswith(expected_prefix):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{url or name}' does not belong to this assignment's upload path"
            )
        if not name.startswith(expected_filename_prefix):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File was not uploaded by the submitting user"
            )
        # Resolve and confirm the file both stays inside the assignment's
        # upload directory (no path-traversal escape via a crafted
        # filename segment) and actually exists.
        candidate = (upload_dir / name).resolve()
        if not candidate.is_relative_to(upload_dir) or not candidate.is_file():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{url or name}' was not found"
            )


def _award_assignment_submitted_xp(db: Session, user_id: int, assignment: Assignment, submission_id: int) -> None:
    """+10 XP for submitting an assignment (spec D1). Idempotent per
    (assignment, submission) row so a returned-then-resubmitted assignment
    only ever counts once per submission id. Best-effort — never fails the
    submit. Callers already `db.commit()` the submission row immediately
    before calling this, so award()'s own flush + this function's commit
    only ever cover the gamification rows (H1 review fix: award() owns
    none of the caller's transaction boundary)."""
    try:
        from app.services.gamification_service import award as _award_xp
        _award_xp(
            db, user_id, "assignment_submitted",
            event_key=f"assignment:{assignment.id}:submission:{submission_id}:submitted:user:{user_id}",
            course_id=assignment.course_id,
            meta={"assignment_id": assignment.id, "submission_id": submission_id},
        )
        db.commit()
    except Exception as game_err:
        logger.warning("Gamification award failed for assignment submit: %s", game_err)
        try:
            db.rollback()
        except Exception:
            pass


@router.post("/assignments/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: int,
    submission_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Submit an assignment. Requires enrollment (course owner/admin bypass,
    mirroring the quizzes helper), the assignment to be `published`, and
    honors the assignment's due_date + late_policy (allow/block/penalty).
    """
    from app.models.enrollment import Enrollment

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    is_owner_or_admin = _is_owner_or_admin(course, current_user)

    # Enrollment check (spec A1.6) — mirrors the quizzes submit helper:
    # enrolled OR course owner OR admin.
    enrollment = None
    if not is_owner_or_admin:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == assignment.course_id,
            Enrollment.user_id == current_user.id
        ).first()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enrolled in this course"
            )
    else:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == assignment.course_id,
            Enrollment.user_id == current_user.id
        ).first()

    # Status lifecycle (spec A1.7): students may only submit to a published
    # assignment. Owner/admin bypass (testing/preview).
    if assignment.status != AssignmentStatus.PUBLISHED and not is_owner_or_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This assignment is not open for submission"
        )

    # Deadline + late_policy (spec A1.5)
    now = datetime.now(timezone.utc)
    is_late = False
    if assignment.due_date is not None:
        due = _as_utc(assignment.due_date)
        if now > due:
            is_late = True
            if assignment.late_policy == LatePolicy.BLOCK.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Submission deadline has passed "
                        f"(due {due.isoformat()}); this assignment blocks late submissions."
                    )
                )

    files = submission_data.get("files", [])
    _validate_submission_files(assignment, files, current_user)

    # Check if already submitted
    existing = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id,
        AssignmentSubmission.user_id == current_user.id
    ).first()

    if existing:
        # Only allow resubmission if status is "returned"
        # Prevent overwriting graded or submitted assignments
        if existing.status == SubmissionStatus.GRADED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot resubmit a graded assignment. This assignment has already been graded."
            )

        if existing.status == SubmissionStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment is already submitted and pending review. Cannot resubmit until instructor returns it."
            )

        # Allow resubmission only if status is "returned"
        if existing.status == SubmissionStatus.RETURNED:
            existing.text_content = submission_data.get("textContent", "")
            existing.files = files
            existing.submitted_at = now
            existing.status = SubmissionStatus.SUBMITTED
            existing.grade = None  # Clear any previous grade
            existing.feedback = ""  # Clear previous feedback
            existing.is_late = is_late
            db.commit()
            _award_assignment_submitted_xp(db, current_user.id, assignment, existing.id)
            _notify_instructor_of_submission(db, assignment, current_user, existing.id, background_tasks)
            return {"message": "Assignment resubmitted successfully", "id": existing.id, "isLate": is_late}

        # For any other status, reject
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            # Every other read of `.status` in this file guards with isinstance
            # because the column can hold a plain string as well as the enum.
            # This one did not, so the error path itself raised AttributeError
            # and the student got an opaque 500 instead of the message below.
            detail=(
                "Cannot resubmit assignment with status: "
                f"{existing.status.value if isinstance(existing.status, SubmissionStatus) else existing.status}"
            )
        )
    else:
        # Create new submission. assignment_id+user_id is now DB-unique
        # (uq_assignment_user) — a race here surfaces as an IntegrityError,
        # which is acceptable (client should retry the resubmit path).
        new_submission = AssignmentSubmission(
            assignment_id=assignment_id,
            user_id=current_user.id,
            text_content=submission_data.get("textContent", ""),
            files=files,
            status=SubmissionStatus.SUBMITTED,
            is_late=is_late,
        )
        db.add(new_submission)
        db.commit()
        db.refresh(new_submission)
        _award_assignment_submitted_xp(db, current_user.id, assignment, new_submission.id)
        _notify_instructor_of_submission(db, assignment, current_user, new_submission.id, background_tasks)
        return {"message": "Assignment submitted successfully", "id": new_submission.id, "isLate": is_late}


@router.get("/assignments/{assignment_id}/submissions")
async def get_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Get all submissions for an assignment (instructor only)
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Check permission
    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view submissions"
        )

    submissions = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id
    ).all()

    return {
        "submissions": [
            {
                "id": sub.id,
                "studentId": sub.user_id,
                "studentName": sub.student.display_name if sub.student else "Unknown",
                "studentEmail": sub.student.user_email if sub.student else "N/A",
                "submittedAt": sub.submitted_at.isoformat() if sub.submitted_at else None,
                "textContent": sub.text_content,
                "files": _json_list(sub.files),
                # See the note above: 0 is a valid grade, not a missing one.
                "grade": float(sub.grade) if sub.grade is not None else None,
                "feedback": sub.feedback,
                "status": sub.status.value if isinstance(sub.status, SubmissionStatus) else sub.status,
                # Who approved it — lets the UI show "Approved by instructor/admin".
                "gradedByRole": sub.graded_by_role,
                "isLate": sub.is_late,
                "rubricScores": sub.rubric_scores,
            }
            for sub in submissions
        ]
    }


@router.post("/submissions/{submission_id}/return")
async def return_submission(
    submission_id: int,
    return_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Return a submission as invalid (instructor only)
    """
    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    # Check permission
    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    course = db.query(Course).filter(Course.id == assignment.course_id).first()

    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to return this submission"
        )

    # Store previous grade if it existed (for logging/audit purposes)
    previous_grade = submission.grade if submission.grade is not None else None
    previous_status = submission.status

    # Update submission status to returned
    submission.status = SubmissionStatus.RETURNED
    submission.feedback = return_data.get("feedback", "")
    submission.grade = None  # Clear grade if any

    db.commit()
    db.refresh(submission)

    # Notify the student their submission needs changes.
    create_notification(
        db, user_id=submission.user_id, type="submission_returned",
        title="Assignment returned",
        message=f"Your submission for '{assignment.title}' needs changes. Please resubmit.",
        link="/dashboard", related_id=submission.id,
        send_email=True, background_tasks=background_tasks,
    )

    # Include warning if grade was cleared
    message = "Submission returned to student"
    if previous_grade is not None:
        message += f" (previous grade of {previous_grade} was cleared)"

    return {
        "message": message,
        "submission": {
            "id": submission.id,
            "status": submission.status.value if isinstance(submission.status, SubmissionStatus) else submission.status,
            "feedback": submission.feedback,
            "previous_status": previous_status.value if isinstance(previous_status, SubmissionStatus) else previous_status,
            "previous_grade": float(previous_grade) if previous_grade is not None else None
        }
    }


@router.post("/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: int,
    grade_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Grade an assignment submission (instructor only)
    """
    from app.models.enrollment import Enrollment
    from app.services.certificate_service import CertificateService

    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    # Check permission
    assignment = db.query(Assignment).filter(
        Assignment.id == submission.assignment_id
    ).first()
    course = db.query(Course).filter(Course.id == assignment.course_id).first()

    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to grade this submission"
        )

    # Update grade. `grade` from the instructor is treated as the RAW score;
    # for a `penalty` late_policy on a late submission, the stored grade is
    # the penalized value, with the raw score surfaced separately in the
    # response (spec A1.5 — "grade shown as raw + penalized").
    #
    # Rubric-scored grading (Task 2 / spec A1.12 item 3): optional
    # `rubricScores` = [{criterion, points}, ...] must match the
    # assignment's own rubric criteria (no unknown criteria, every
    # criterion covered) with each points value between 0 and that
    # criterion's max_points. When given, its sum becomes the candidate raw
    # grade — but an explicit `grade` field in the same request always wins
    # over the rubric sum (spec: "still overridable by explicit grade
    # field; if both given, explicit wins"). Late-penalty math (above
    # comment) still applies afterward regardless of which raw source was
    # used.
    rubric_scores_in = grade_data.get("rubricScores")
    rubric_sum = None
    if rubric_scores_in is not None:
        assignment_rubric = assignment.rubric or []
        if not assignment_rubric:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This assignment has no rubric to score against",
            )
        max_points_by_criterion = {
            entry.get("criterion"): float(entry.get("max_points") or 0)
            for entry in assignment_rubric
        }
        if not isinstance(rubric_scores_in, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rubricScores must be a list of {criterion, points} entries",
            )
        seen_criteria = set()
        rubric_sum = 0.0
        for entry in rubric_scores_in:
            if not isinstance(entry, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each rubricScores entry must be an object with criterion and points",
                )
            criterion = entry.get("criterion")
            if criterion not in max_points_by_criterion:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown rubric criterion: {criterion}",
                )
            if criterion in seen_criteria:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate rubric criterion in rubricScores: {criterion}",
                )
            seen_criteria.add(criterion)
            points = entry.get("points")
            try:
                points = float(points)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"rubricScores entry '{criterion}' needs a numeric points value",
                )
            max_points = max_points_by_criterion[criterion]
            if points < 0 or points > max_points:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{criterion}' points must be between 0 and {max_points}",
                )
            rubric_sum += points
        missing_criteria = set(max_points_by_criterion) - seen_criteria
        if missing_criteria:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"rubricScores is missing criteria: {sorted(missing_criteria)}",
            )

    raw_grade = grade_data.get("grade")
    if raw_grade is None and rubric_sum is not None:
        raw_grade = rubric_sum

    penalized_grade = raw_grade
    if (
        raw_grade is not None
        and submission.is_late
        and assignment.late_policy == LatePolicy.PENALTY.value
        and assignment.late_penalty_pct
    ):
        penalized_grade = float(raw_grade) * (1 - assignment.late_penalty_pct / 100.0)

    submission.grade = penalized_grade
    submission.feedback = grade_data.get("feedback", "")
    submission.status = SubmissionStatus.GRADED
    submission.graded_at = datetime.now(timezone.utc)
    # Audit who signed off. Instructors are the primary approvers; an admin
    # grading here is the fallback when the instructor didn't get to it.
    submission.graded_by = current_user.id
    submission.graded_by_role = current_user.role

    if rubric_scores_in is not None:
        submission.rubric_scores = [
            {"criterion": e["criterion"], "points": float(e["points"])}
            for e in rubric_scores_in
        ]

    db.commit()
    # Mastery graph (v2.0 §9.5) — best-effort, after the grade commit.
    from app.services.mastery_service import safe_record_evidence
    safe_record_evidence(db, user_id=getattr(submission, "user_id", None) or getattr(submission, "student_id", None),
                         kind="assignment", ref_id=submission.assignment_id, score=float(penalized_grade or 0),
                         max_score=float(getattr(assignment, "total_points", 0) or 0), course_id=getattr(assignment, "course_id", None))

    # Gamification (spec D1): +15 XP when the grade (post late-penalty, the
    # value actually recorded) meets passing — interpreted as >= 50% of the
    # assignment's total_points, mirroring the brief's "graded >= passing"
    # rule since Assignment has no separate passing-grade field. Also
    # awards a "perfect grade" signal for the assignment-perfect badge when
    # the RAW (pre-penalty) score is a perfect total_points.
    if penalized_grade is not None:
        try:
            from app.services.gamification_service import award as _award_xp, ASSIGNMENT_PASS_FRACTION
            total_points = assignment.total_points or 100
            if total_points > 0 and float(penalized_grade) >= total_points * ASSIGNMENT_PASS_FRACTION:
                _award_xp(
                    db, submission.user_id, "assignment_graded_pass",
                    event_key=f"assignment:{assignment.id}:submission:{submission.id}:graded:user:{submission.user_id}",
                    course_id=assignment.course_id,
                    meta={"assignment_id": assignment.id, "submission_id": submission.id, "grade": float(penalized_grade)},
                )
            if raw_grade is not None and total_points > 0 and float(raw_grade) >= total_points:
                _award_xp(
                    db, submission.user_id, "assignment_perfect",
                    event_key=f"assignment:{assignment.id}:submission:{submission.id}:perfect:user:{submission.user_id}",
                    course_id=assignment.course_id,
                    points=0,
                    meta={"assignment_id": assignment.id, "submission_id": submission.id},
                )
            # award() only flushes (H1 review fix) — the grade itself was
            # already committed just above, so this commit covers only the
            # gamification rows.
            db.commit()
        except Exception as game_err:
            logger.warning("Gamification award failed for assignment grade: %s", game_err)
            try:
                db.rollback()
            except Exception:
                pass

    # Check if all assignments for this student are graded
    student_id = submission.user_id
    course_id = assignment.course_id

    # Recalculate course progress after grading
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == student_id,
        Enrollment.course_id == course_id
    ).first()

    if enrollment:
        from app.services.course_service import CourseService
        CourseService.calculate_course_progress(db, enrollment)

    # Get all assignments for this course
    all_assignments = db.query(Assignment).filter(
        Assignment.course_id == course_id
    ).all()

    # Get all submissions by this student for this course
    student_submissions = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.user_id == student_id,
        AssignmentSubmission.assignment_id.in_([a.id for a in all_assignments])
    ).all()

    # Check if all assignments are graded
    all_graded = len(student_submissions) == len(all_assignments) and all(
        s.status == SubmissionStatus.GRADED for s in student_submissions
    )

    certificate_issued = False
    certificate_error = None
    if all_graded and enrollment:
        # Refresh enrollment to get updated progress (calculate_course_progress
        # above will have set completion_date and triggered auto-issue already
        # if the course is 100%). The block below is defensive — re-call the
        # idempotent issuance helper and send the email only on a fresh issue.
        db.refresh(enrollment)

        if enrollment.course_progress_percentage == 100 and enrollment.completion_date:
            try:
                from app.services.email_service import EmailService

                student = db.query(User).filter(User.id == student_id).first()
                course = db.query(Course).filter(Course.id == course_id).first()

                cert_row, newly_issued = CertificateService.issue_certificate_for_enrollment(
                    db, enrollment
                )
                certificate_issued = bool(newly_issued)

                # In-app notification on fresh issue (the cert email is sent
                # separately below, so this is in-app only to avoid double email).
                if newly_issued and cert_row and course:
                    create_notification(
                        db, user_id=student_id, type="cert_issued",
                        title="Certificate issued",
                        message=f"Your certificate for '{course.post_title}' is ready.",
                        link=f"/courses/{course.post_name or course.id}/certificate",
                        related_id=cert_row.id, send_email=False,
                    )

                # Send email only on fresh issue to avoid spamming the student
                # each time an assignment is re-graded on a 100% course.
                if newly_issued and student and course and cert_row:
                    certificate_url = cert_row.certificate_download_url or ""
                    completion_date = (
                        enrollment.completion_date.strftime('%B %d, %Y')
                        if enrollment.completion_date else datetime.utcnow().strftime('%B %d, %Y')
                    )
                    try:
                        EmailService.send_certificate_issued_notification(
                            student_email=student.user_email,
                            student_name=student.display_name,
                            course_title=course.post_title,
                            course_id=course_id,
                            certificate_url=certificate_url,
                            completion_date=completion_date
                        )
                    except Exception as email_err:
                        # Email failure must not void the cert.
                        print(f"[Certificate] email send failed: {email_err}")
            except Exception as e:
                error_msg = f"Failed to generate certificate or send email: {str(e)}"
                print(error_msg)
                certificate_error = str(e)

    response = {
        "message": "Submission graded successfully",
        "all_assignments_graded": all_graded,
        "certificate_issued": certificate_issued,
        "grade": float(penalized_grade) if penalized_grade is not None else None,
        "rawGrade": float(raw_grade) if raw_grade is not None else None,
        "isLate": submission.is_late,
        "latePenaltyApplied": penalized_grade != raw_grade,
    }

    # Include warning if certificate generation failed
    if certificate_error:
        response["warning"] = f"Grading succeeded but certificate generation failed: {certificate_error}"

    return response
