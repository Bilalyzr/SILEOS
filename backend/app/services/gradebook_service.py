"""Gradebook matrix builder (spec A2).

Builds a students x items matrix — one column per quiz and per PUBLISHED
assignment in a course, one row per enrolled student — for the instructor
gradebook endpoints (app/routers/gradebook.py).

Deliberately reuses `CourseService.passed_distinct_quizzes` for quiz
pass/fail semantics rather than forking completion logic (plan Task 2
instruction) — the gradebook's "best quiz attempt" selection below mirrors
that helper's own attempt-selection rules (latest ENDED attempt scoring
highest counts) so the displayed score never contradicts progress/
certificate math elsewhere in the app.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.assignment import Assignment, AssignmentSubmission, AssignmentStatus, SubmissionStatus
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, QuizAttempt
from app.models.user import User


def _quiz_item(quiz: Quiz) -> Dict[str, Any]:
    return {
        "type": "quiz",
        "id": quiz.id,
        "title": quiz.post_title,
        "max": _quiz_max_marks(quiz),
    }


def _assignment_item(assignment: Assignment) -> Dict[str, Any]:
    return {
        "type": "assignment",
        "id": assignment.id,
        "title": assignment.title,
        "max": assignment.total_points,
    }


def _quiz_max_marks(quiz: Quiz) -> float:
    """Sum of question_mark across the quiz's questions — the same
    denominator submit_quiz/finalize compute total_marks from. Falls back
    to 0 for an empty quiz (no questions authored yet)."""
    total = 0.0
    for question in quiz.questions or []:
        total += float(question.question_mark or 0)
    return total


def _best_quiz_attempt(attempts: List[QuizAttempt]) -> Optional[QuizAttempt]:
    """Pick the attempt to display for a student x quiz cell.

    A `pending_review` attempt (awaiting instructor grading) takes priority
    over any `attempt_ended` one — it is the most actionable state for the
    instructor and must not be masked by an older finished attempt. Among
    `attempt_ended` attempts, the highest-scoring percentage wins (mirrors
    how a student would want their best attempt reflected); `attempt_started`
    (still in progress) attempts are never shown as a scoreable cell.
    """
    pending = [a for a in attempts if a.attempt_status == "pending_review"]
    if pending:
        # Most recently started pending-review attempt.
        return max(pending, key=lambda a: a.attempt_started_at or 0)

    ended = [a for a in attempts if a.attempt_status == "attempt_ended"]
    if not ended:
        return None

    def _pct(a: QuizAttempt) -> float:
        total = float(a.total_marks or 0)
        if total <= 0:
            return 0.0
        return float(a.earned_marks or 0) / total

    return max(ended, key=_pct)


def _quiz_cell(quiz: Quiz, attempts: List[QuizAttempt]) -> Dict[str, Any]:
    item_max = _quiz_max_marks(quiz)
    attempt = _best_quiz_attempt(attempts)
    if attempt is None:
        return {"score": None, "max": item_max, "status": "missing", "is_late": False}

    if attempt.attempt_status == "pending_review":
        return {"score": None, "max": item_max, "status": "pending", "is_late": False}

    # attempt_ended
    return {
        "score": float(attempt.earned_marks or 0),
        "max": item_max,
        "status": "graded",
        "is_late": False,
    }


def _assignment_cell(assignment: Assignment, submission: Optional[AssignmentSubmission]) -> Dict[str, Any]:
    item_max = assignment.total_points
    if submission is None:
        return {"score": None, "max": item_max, "status": "missing", "is_late": False}

    is_late = bool(submission.is_late)

    if submission.status == SubmissionStatus.GRADED:
        return {
            "score": float(submission.grade) if submission.grade is not None else None,
            "max": item_max,
            "status": "graded",
            "is_late": is_late,
        }

    # SUBMITTED (awaiting grading) or RETURNED (sent back for changes) both
    # read as actionable-pending in the gradebook — RETURNED has no grade
    # and no work currently "missing" (the student had submitted once).
    if is_late:
        return {"score": None, "max": item_max, "status": "late", "is_late": True}
    return {"score": None, "max": item_max, "status": "pending", "is_late": False}


def build_matrix(db: Session, course: Course) -> Dict[str, Any]:
    """Build the students x items gradebook matrix for one course.

    Returns {"items": [...], "students": [...], "rows": [...]}:
      - items: ordered list of {type, id, title, max} — one per quiz then
        one per PUBLISHED assignment (draft/closed assignments are excluded
        from the gradebook, matching what students can see/submit).
      - rows: one per enrolled student — {student: {id, name, email},
        cells: {"quiz:{id}": {...}, "assignment:{id}": {...}}}.
    """
    quizzes = (
        db.query(Quiz)
        .filter(Quiz.post_parent == course.id)
        .order_by(Quiz.menu_order.asc(), Quiz.id.asc())
        .all()
    )
    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.course_id == course.id,
            Assignment.status == AssignmentStatus.PUBLISHED,
        )
        .order_by(Assignment.order.asc(), Assignment.id.asc())
        .all()
    )

    items: List[Dict[str, Any]] = [_quiz_item(q) for q in quizzes] + [
        _assignment_item(a) for a in assignments
    ]

    # Deliberate per-status visibility decision for the gradebook roster —
    # four enrollment_status values exist in this app:
    #   - "enrolled"   VISIBLE (the normal case).
    #   - "completed"  VISIBLE. calculate_course_progress flips a student's
    #                  status to "completed" once they finish the course —
    #                  excluding it here would drop every student who
    #                  finished from their own gradebook.
    #   - "suspended"  VISIBLE. Set by
    #                  membership_access.suspend_membership_enrollments on a
    #                  lapsed membership payment. This is a grace-period
    #                  state, not a removal — the member typically
    #                  reactivates, and hiding their row (and any work
    #                  they've already submitted) mid-grace-period would
    #                  break grading continuity and confuse the instructor
    #                  about who they're grading. ADJUDICATED: stays
    #                  visible.
    #   - "cancelled"  HIDDEN. Review finding: an instructor could see (and
    #                  export via CSV) a row for a student whose enrollment
    #                  was cancelled — proven live. Cancellation is a
    #                  deliberate removal, unlike a lapsed-but-recoverable
    #                  membership, so it is excluded.
    # This is why the filter below is a deny-list on "cancelled" rather
    # than an allow-list on "enrolled" (the plain "== enrolled" filter used
    # at access-grant call sites elsewhere — course_service,
    # live_class_service, payments, player, bunny, ... — would wrongly hide
    # both "completed" and "suspended" rows here).
    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course.id,
            Enrollment.enrollment_status != "cancelled",
        )
        .order_by(Enrollment.id.asc())
        .all()
    )
    student_ids = [e.user_id for e in enrollments]
    students = {
        u.id: u
        for u in db.query(User).filter(User.id.in_(student_ids)).all()
    } if student_ids else {}

    # Preload attempts/submissions grouped by (student, item) to avoid N+1
    # queries per cell.
    quiz_ids = [q.id for q in quizzes]
    attempts_by_key: Dict[tuple, List[QuizAttempt]] = {}
    if quiz_ids and student_ids:
        all_attempts = (
            db.query(QuizAttempt)
            .filter(
                QuizAttempt.quiz_id.in_(quiz_ids),
                QuizAttempt.user_id.in_(student_ids),
            )
            .all()
        )
        for a in all_attempts:
            attempts_by_key.setdefault((a.user_id, a.quiz_id), []).append(a)

    assignment_ids = [a.id for a in assignments]
    submission_by_key: Dict[tuple, AssignmentSubmission] = {}
    if assignment_ids and student_ids:
        all_submissions = (
            db.query(AssignmentSubmission)
            .filter(
                AssignmentSubmission.assignment_id.in_(assignment_ids),
                AssignmentSubmission.user_id.in_(student_ids),
            )
            .all()
        )
        for s in all_submissions:
            submission_by_key[(s.user_id, s.assignment_id)] = s

    rows: List[Dict[str, Any]] = []
    for student_id in student_ids:
        user = students.get(student_id)
        cells: Dict[str, Any] = {}
        for quiz in quizzes:
            key = f"quiz:{quiz.id}"
            cells[key] = _quiz_cell(quiz, attempts_by_key.get((student_id, quiz.id), []))
        for assignment in assignments:
            key = f"assignment:{assignment.id}"
            cells[key] = _assignment_cell(
                assignment, submission_by_key.get((student_id, assignment.id))
            )
        rows.append({
            "student": {
                "id": student_id,
                "name": user.display_name if user else "Unknown",
                "email": user.user_email if user else None,
            },
            "cells": cells,
        })

    return {"items": items, "rows": rows}
