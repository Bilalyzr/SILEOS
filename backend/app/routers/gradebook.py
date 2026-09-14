"""Gradebook + grading-queue router (spec A1.12 + A2, plan Task 2).

Endpoints (course-owner/admin only):
  GET  /api/v1/courses/{course_id}/grading-queue   - merged pending queue
  GET  /api/v1/courses/{course_id}/gradebook        - matrix JSON
  GET  /api/v1/courses/{course_id}/gradebook.csv    - matrix CSV download

Rubric-scored grading (extends the existing assignment grade endpoint) is
implemented directly in app/routers/assignments.py, not here — this module
only owns the new read-side surfaces plus the queue.
"""
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.csv_safety import sanitize_csv_cell
from app.core.database import get_db
from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
from app.models.course import Course
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizQuestion
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.course_access import can_edit
from app.services.gradebook_service import build_matrix
from app.routers.quizzes import MANUAL_GRADE_QUESTION_TYPES, _attempt_info_dict

router = APIRouter()


def _require_course_owner_or_admin(db: Session, course_id: int, current_user: User) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view grading for this course",
        )
    return course


def _quiz_essay_queue_entries(db: Session, course_id: int) -> list:
    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.course_id == course_id,
            QuizAttempt.attempt_status == "pending_review",
        )
        .all()
    )
    entries = []
    for attempt in attempts:
        quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
        student = db.query(User).filter(User.id == attempt.user_id).first()
        manual_answers = (
            db.query(QuizAttemptAnswer)
            .join(QuizQuestion, QuizAttemptAnswer.question_id == QuizQuestion.question_id)
            .filter(
                QuizAttemptAnswer.quiz_attempt_id == attempt.attempt_id,
                QuizQuestion.question_type.in_(MANUAL_GRADE_QUESTION_TYPES),
            )
            .all()
        )
        graded_ids = set(_attempt_info_dict(attempt).get("_graded_answers") or [])
        ungraded_answer_ids = [
            a.attempt_answer_id for a in manual_answers if a.attempt_answer_id not in graded_ids
        ]
        started_at = attempt.attempt_started_at
        entries.append({
            "type": "quiz_essay",
            "sort_key": started_at or datetime.min.replace(tzinfo=timezone.utc),
            "attempt_id": attempt.attempt_id,
            "quiz_id": attempt.quiz_id,
            "quiz_title": quiz.post_title if quiz else None,
            "course_id": course_id,
            "student_id": attempt.user_id,
            "student_name": student.display_name if student else "Unknown",
            "student_email": student.user_email if student else None,
            "submitted_at": started_at.isoformat() if started_at else None,
            "manual_answer_ids": [a.attempt_answer_id for a in manual_answers],
            "ungraded_answer_ids": ungraded_answer_ids,
        })
    return entries


def _assignment_queue_entries(db: Session, course_id: int) -> list:
    submissions = (
        db.query(AssignmentSubmission)
        .join(Assignment, AssignmentSubmission.assignment_id == Assignment.id)
        .filter(
            Assignment.course_id == course_id,
            AssignmentSubmission.status == SubmissionStatus.SUBMITTED,
        )
        .all()
    )
    entries = []
    for sub in submissions:
        assignment = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
        student = db.query(User).filter(User.id == sub.user_id).first()
        submitted_at = sub.submitted_at
        entries.append({
            "type": "assignment",
            "sort_key": submitted_at or datetime.min.replace(tzinfo=timezone.utc),
            "submission_id": sub.id,
            "assignment_id": sub.assignment_id,
            "assignment_title": assignment.title if assignment else None,
            "course_id": course_id,
            "student_id": sub.user_id,
            "student_name": student.display_name if student else "Unknown",
            "student_email": student.user_email if student else None,
            "submitted_at": submitted_at.isoformat() if submitted_at else None,
            "is_late": bool(sub.is_late),
        })
    return entries


def _sort_key(entry: dict):
    key = entry["sort_key"]
    if key.tzinfo is None:
        key = key.replace(tzinfo=timezone.utc)
    return key


@router.get("/courses/{course_id}/grading-queue")
async def get_grading_queue(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Merged pending-review queue: ungraded essay/open-ended quiz answers
    (attempt-level, `pending_review`) + ungraded assignment submissions
    (`submitted`), sorted oldest-first so the instructor works the backlog
    in submission order regardless of type."""
    _require_course_owner_or_admin(db, course_id, current_user)

    entries = _quiz_essay_queue_entries(db, course_id) + _assignment_queue_entries(db, course_id)
    entries.sort(key=_sort_key)
    for entry in entries:
        entry.pop("sort_key", None)

    return {"queue": entries, "count": len(entries)}


@router.get("/courses/{course_id}/gradebook")
async def get_gradebook(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Gradebook matrix: students x (quizzes, published assignments)."""
    course = _require_course_owner_or_admin(db, course_id, current_user)
    return build_matrix(db, course)


@router.get("/courses/{course_id}/gradebook.csv")
async def get_gradebook_csv(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Gradebook matrix as a CSV download (stdlib csv, matches the
    live_class_attendance export pattern)."""
    course = _require_course_owner_or_admin(db, course_id, current_user)
    matrix = build_matrix(db, course)

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    header = ["Student", "Email"] + [
        sanitize_csv_cell(item["title"]) for item in matrix["items"]
    ]
    writer.writerow(header)

    for row in matrix["rows"]:
        line = [
            sanitize_csv_cell(row["student"]["name"]),
            sanitize_csv_cell(row["student"]["email"] or ""),
        ]
        for item in matrix["items"]:
            key = f"{item['type']}:{item['id']}"
            cell = row["cells"].get(key, {})
            score = cell.get("score")
            item_status = cell.get("status", "missing")
            if score is not None:
                cell_text = f"{score}/{item['max']}"
                if cell.get("is_late"):
                    cell_text += " (late)"
            else:
                cell_text = item_status
            # cell_text is always instructor/system-derived (a number or a
            # fixed status word), never raw student input — sanitize_csv_cell
            # is a no-op for it, but applying it uniformly avoids relying on
            # that invariant holding forever.
            line.append(sanitize_csv_cell(cell_text))
        writer.writerow(line)

    csv_body = buffer.getvalue()
    filename = f"gradebook-course-{course_id}.csv"
    return StreamingResponse(
        iter([csv_body]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
