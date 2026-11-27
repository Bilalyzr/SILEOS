"""Phase 5 (part A): line-anchored review comments and the instructor review queue.

Who can do what:
- The submission owner and course editors (instructors, co-editors, admins)
  can read and comment on a submission. Anyone else gets 404.
- Only the owner can ask for a review, and only for a final submission.
- Only course editors can resolve comments and mark a review as done.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func

from app.models.coding_assessment import CodingChallenge, CodingSubmission
from app.models.coding_review import CodingReviewComment, CodingReviewRequest
from app.models.course import Course
from app.models.user import User
from app.services import coding_assessment_service as coding
from app.services.course_access import ADMIN_ROLES, can_edit


FINAL_STATUSES = ("passed", "failed", "error")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _submission(db, submission_id: int, user) -> tuple[CodingSubmission, CodingChallenge, Course]:
    submission = db.get(CodingSubmission, submission_id)
    if submission is None or not coding._can_view_submission(db, submission, user):
        raise HTTPException(404, "Submission not found.")
    challenge = db.get(CodingChallenge, submission.challenge_id)
    course = db.get(Course, challenge.course_id)
    return submission, challenge, course


def _is_editor(db, course: Course, user) -> bool:
    return user.role in ADMIN_ROLES or can_edit(db, course, user)


def _line_count(source: str) -> int:
    return max(1, len(source.splitlines()))


def _comment_out(db, comment: CodingReviewComment, submission: CodingSubmission) -> dict:
    author = db.get(User, comment.author_id)
    return {
        "id": comment.id,
        "submission_id": comment.submission_id,
        "line": comment.line,
        "body": comment.body,
        "status": comment.status,
        "author_name": author.display_name if author else "",
        # Staff are anyone who is not the submission owner.
        "author_is_staff": comment.author_id != submission.user_id,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "resolved_at": comment.resolved_at.isoformat() if comment.resolved_at else None,
    }


def create_comment(db, submission_id: int, command, user) -> dict:
    submission, _challenge, _course = _submission(db, submission_id, user)
    if command.line > _line_count(submission.source_code):
        raise HTTPException(422, "That line is past the end of this submission.")
    comment = CodingReviewComment(
        submission_id=submission.id,
        author_id=user.id,
        line=command.line,
        body=command.body,
        status="open",
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_out(db, comment, submission)


def list_comments(db, submission_id: int, user) -> list[dict]:
    submission, _challenge, _course = _submission(db, submission_id, user)
    rows = (
        db.query(CodingReviewComment)
        .filter(CodingReviewComment.submission_id == submission.id)
        .order_by(CodingReviewComment.line, CodingReviewComment.id)
        .all()
    )
    return [_comment_out(db, row, submission) for row in rows]


def resolve_comment(db, comment_id: int, user) -> dict:
    comment = db.get(CodingReviewComment, comment_id)
    if comment is None:
        raise HTTPException(404, "Comment not found.")
    submission, _challenge, course = _submission(db, comment.submission_id, user)
    if not _is_editor(db, course, user):
        raise HTTPException(403, "Only course editors can resolve comments.")
    if comment.status != "resolved":
        comment.status = "resolved"
        comment.resolved_at = _now()
        db.commit()
        db.refresh(comment)
    return _comment_out(db, comment, submission)


def request_review(db, submission_id: int, user) -> dict:
    submission, _challenge, _course = _submission(db, submission_id, user)
    if submission.user_id != user.id:
        raise HTTPException(403, "Only the submitter can ask for a review.")
    if submission.status not in FINAL_STATUSES:
        raise HTTPException(409, "Wait for the run to finish before asking for a review.")
    existing = db.query(CodingReviewRequest).filter_by(submission_id=submission.id).first()
    if existing is None:
        db.add(CodingReviewRequest(submission_id=submission.id, requested_by=user.id))
        coding._save(db)
        existing = db.query(CodingReviewRequest).filter_by(submission_id=submission.id).first()
    return {"submission_id": submission.id, "requested": True, "reviewed": existing.reviewed}


def mark_reviewed(db, submission_id: int, user) -> dict:
    submission, _challenge, course = _submission(db, submission_id, user)
    if not _is_editor(db, course, user):
        raise HTTPException(403, "Only course editors can close a review.")
    request = db.query(CodingReviewRequest).filter_by(submission_id=submission.id).first()
    if request is None:
        raise HTTPException(404, "No review was requested for this submission.")
    if not request.reviewed:
        request.reviewed = True
        request.reviewed_by = user.id
        request.reviewed_at = _now()
        db.commit()
    return {"submission_id": submission.id, "requested": True, "reviewed": True}


def review_queue(db, course_id: int, user) -> dict:
    course = coding._course_editor(db, course_id, user)
    rows = (
        db.query(CodingReviewRequest, CodingSubmission, CodingChallenge, User)
        .join(CodingSubmission, CodingSubmission.id == CodingReviewRequest.submission_id)
        .join(CodingChallenge, CodingChallenge.id == CodingSubmission.challenge_id)
        .join(User, User.id == CodingSubmission.user_id)
        .filter(
            CodingChallenge.course_id == course.id,
            CodingReviewRequest.reviewed.is_(False),
        )
        .order_by(CodingReviewRequest.requested_at, CodingReviewRequest.id)
        .all()
    )
    ids = [submission.id for _req, submission, _ch, _u in rows]
    open_counts = dict(
        db.query(CodingReviewComment.submission_id, func.count(CodingReviewComment.id))
        .filter(
            CodingReviewComment.submission_id.in_(ids or [-1]),
            CodingReviewComment.status == "open",
        )
        .group_by(CodingReviewComment.submission_id)
        .all()
    )
    items = [
        {
            "submission_id": submission.id,
            "challenge_slug": challenge.slug,
            "challenge_title": challenge.title,
            "learner_name": learner.display_name,
            "language": submission.language,
            "status": submission.status,
            "score": float(submission.score),
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "requested_at": request.requested_at.isoformat() if request.requested_at else None,
            "open_comments": int(open_counts.get(submission.id, 0)),
        }
        for request, submission, challenge, learner in rows
    ]
    return {"course_id": course.id, "count": len(items), "items": items}
