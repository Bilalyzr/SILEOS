"""Phase 4: coding challenges pushed into live class sessions.

Rules enforced here:
- Only the assigned instructor (or an admin) pushes, closes or reveals.
- A push must be a published challenge from the class's own course.
- At most one open challenge per class at a time.
- Learners submit only while the challenge is open, the class is running, and
  they have joined the class (attendance row). Submissions go through the
  normal judge pipeline; the link row only records which submission belongs
  to the live session.
- The model solution is hidden from learners until the instructor reveals it
  after closing the challenge.
- Learners see only their own board row. Instructors see the full board.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.coding_assessment import CodingChallenge, CodingSubmission
from app.models.coding_live import LiveCodingChallenge, LiveCodingSubmission
from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassStatus
from app.services import coding_analytics_service as analytics
from app.services import coding_assessment_service as coding
from app.services import live_class_service


CLOSED_CLASS_STATUSES = (LiveClassStatus.ENDED, LiveClassStatus.CANCELLED)
FINAL_STATUSES = analytics.FINAL_STATUSES


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _class(db, class_id: int, *, lock: bool = False) -> LiveClass:
    query = db.query(LiveClass).filter(LiveClass.id == class_id, LiveClass.deleted_at.is_(None))
    live_class = query.with_for_update().first() if lock else query.first()
    if live_class is None:
        raise HTTPException(404, "Live class not found.")
    return live_class


def _live(db, live_id: int) -> tuple[LiveCodingChallenge, LiveClass]:
    row = db.get(LiveCodingChallenge, live_id)
    if row is None:
        raise HTTPException(404, "Live challenge not found.")
    return row, _class(db, row.class_id)


def _require_staff(live_class: LiveClass, user) -> None:
    if not live_class_service.is_assigned_instructor_or_admin(live_class, user):
        raise HTTPException(403, "Only the assigned instructor can run live challenges.")


def _require_participant(db, live_class: LiveClass, user) -> None:
    if not live_class_service.user_can_access_class(db, live_class, user):
        raise HTTPException(403, "You do not have access to this class.")


def _require_joined(db, live_class: LiveClass, user) -> None:
    joined = (
        db.query(LiveClassAttendance)
        .filter(LiveClassAttendance.class_id == live_class.id, LiveClassAttendance.user_id == user.id)
        .first()
    )
    if joined is None:
        raise HTTPException(403, "Join the class before working on a live challenge.")


def _out(db, row: LiveCodingChallenge, user, *, staff: bool) -> dict:
    challenge = db.get(CodingChallenge, row.challenge_id)
    revealed = row.solution_revealed_at is not None
    return {
        "id": row.id,
        "class_id": row.class_id,
        "challenge_id": row.challenge_id,
        "challenge_slug": challenge.slug if challenge else "",
        "challenge_title": challenge.title if challenge else "",
        "status": row.status,
        "graded": row.graded,
        "instructions": row.instructions,
        "pushed_at": row.pushed_at.isoformat() if row.pushed_at else None,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "solution_revealed": revealed,
        "model_solution": (
            row.model_solution if staff or revealed else None
        ),
    }


def push(db, class_id: int, command, user) -> dict:
    live_class = _class(db, class_id, lock=True)
    _require_staff(live_class, user)
    if live_class.status in CLOSED_CLASS_STATUSES:
        raise HTTPException(422, "This class has already ended.")
    challenge = db.get(CodingChallenge, command.challenge_id)
    if (
        challenge is None
        or challenge.course_id != live_class.course_id
        or challenge.status != "published"
    ):
        raise HTTPException(422, "Only published challenges from this class's course can be pushed.")
    already_open = (
        db.query(LiveCodingChallenge)
        .filter(LiveCodingChallenge.class_id == class_id, LiveCodingChallenge.status == "open")
        .first()
    )
    if already_open is not None:
        raise HTTPException(409, "Close the open challenge before pushing another.")
    row = LiveCodingChallenge(
        class_id=class_id,
        challenge_id=challenge.id,
        pushed_by=user.id,
        status="open",
        graded=command.graded,
        instructions=command.instructions,
        model_solution=command.model_solution,
        pushed_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(db, row, user, staff=True)


def list_for_class(db, class_id: int, user) -> list[dict]:
    live_class = _class(db, class_id)
    _require_participant(db, live_class, user)
    staff = live_class_service.is_assigned_instructor_or_admin(live_class, user)
    rows = (
        db.query(LiveCodingChallenge)
        .filter(LiveCodingChallenge.class_id == class_id)
        .order_by(LiveCodingChallenge.id.desc())
        .all()
    )
    return [_out(db, row, user, staff=staff) for row in rows]


def close(db, live_id: int, user) -> dict:
    row, live_class = _live(db, live_id)
    _require_staff(live_class, user)
    if row.status != "closed":
        row.status = "closed"
        row.closed_at = _now()
        db.commit()
        db.refresh(row)
    return _out(db, row, user, staff=True)


def reveal(db, live_id: int, user) -> dict:
    row, live_class = _live(db, live_id)
    _require_staff(live_class, user)
    if row.status != "closed":
        raise HTTPException(409, "Close the challenge before revealing the solution.")
    if not row.model_solution.strip():
        raise HTTPException(422, "No model solution was saved with this challenge.")
    if row.solution_revealed_at is None:
        row.solution_revealed_at = _now()
        db.commit()
        db.refresh(row)
    return _out(db, row, user, staff=True)


def learner_view(db, live_id: int, user) -> dict:
    row, live_class = _live(db, live_id)
    _require_participant(db, live_class, user)
    _require_joined(db, live_class, user)
    if live_class_service.is_assigned_instructor_or_admin(live_class, user):
        raise HTTPException(403, "Instructors view live challenges from the console.")
    challenge = db.get(CodingChallenge, row.challenge_id)
    return {
        "live": _out(db, row, user, staff=False),
        "challenge": coding.learner_challenge(db, challenge.slug, user),
    }


def submit(db, live_id: int, command, user) -> dict:
    row, live_class = _live(db, live_id)
    _require_participant(db, live_class, user)
    if live_class_service.is_assigned_instructor_or_admin(live_class, user):
        raise HTTPException(403, "Instructors do not submit to live challenges.")
    _require_joined(db, live_class, user)
    if row.status != "open":
        raise HTTPException(409, "This live challenge is closed.")
    if live_class.status in CLOSED_CLASS_STATUSES:
        raise HTTPException(409, "This class has ended.")
    challenge = db.get(CodingChallenge, row.challenge_id)
    detail = coding.submit(db, challenge.slug, command, user)
    existing = (
        db.query(LiveCodingSubmission)
        .filter(LiveCodingSubmission.submission_id == detail["id"])
        .first()
    )
    if existing is None:
        db.add(
            LiveCodingSubmission(
                live_id=row.id,
                submission_id=detail["id"],
                user_id=user.id,
                counts_for_grade=row.graded,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return {"live_id": row.id, "counts_for_grade": row.graded, "submission": detail}


def board(db, live_id: int, user) -> dict:
    row, live_class = _live(db, live_id)
    _require_participant(db, live_class, user)
    staff = live_class_service.is_assigned_instructor_or_admin(live_class, user)
    links = (
        db.query(LiveCodingSubmission)
        .filter(LiveCodingSubmission.live_id == row.id)
        .all()
    )
    sub_ids = [link.submission_id for link in links]
    subs = (
        db.query(CodingSubmission)
        .filter(CodingSubmission.id.in_(sub_ids or [-1]))
        .all()
    )
    pending = sum(1 for sub in subs if sub.status not in FINAL_STATUSES)
    final = [sub for sub in subs if sub.status in FINAL_STATUSES]
    perf = analytics._performance_by_submission(db, [sub.id for sub in final])

    by_learner: dict[int, list[CodingSubmission]] = {}
    for sub in final:
        by_learner.setdefault(sub.user_id, []).append(sub)
    attempts_by_learner: dict[int, int] = {}
    for link in links:
        attempts_by_learner[link.user_id] = attempts_by_learner.get(link.user_id, 0) + 1
    names = analytics._learner_names(db, list(attempts_by_learner))

    rows = []
    for user_id, items in by_learner.items():
        best = min(
            items,
            key=lambda s: analytics.ranking_key(s.score, *perf.get(s.id, (0, 0)), s.submitted_at),
        )
        best_ms, best_kb = perf.get(best.id, (0, 0))
        rows.append(
            {
                "user_id": user_id,
                "learner_name": names.get(user_id, ""),
                "best_score": float(best.score),
                "passed": any(s.status == "passed" for s in items),
                "attempts": attempts_by_learner.get(user_id, len(items)),
                "total_ms": best_ms,
                "peak_memory_kb": best_kb,
                "_sort": analytics.ranking_key(best.score, best_ms, best_kb, best.submitted_at),
            }
        )
    # Learners who have submitted but whose runs are all still pending.
    for user_id in attempts_by_learner:
        if user_id not in by_learner:
            rows.append(
                {
                    "user_id": user_id,
                    "learner_name": names.get(user_id, ""),
                    "best_score": 0.0,
                    "passed": False,
                    "attempts": attempts_by_learner[user_id],
                    "total_ms": 0,
                    "peak_memory_kb": 0,
                    "_sort": (0.0, 0, 0, _now()),
                }
            )
    rows.sort(key=lambda item: item.pop("_sort"))
    for position, item in enumerate(rows, start=1):
        item["rank"] = position

    payload = {
        "live_id": row.id,
        "status": row.status,
        "graded": row.graded,
        "pending_submissions": pending,
        "summary": {
            "learners_submitted": len(attempts_by_learner),
            "learners_passed": sum(1 for item in rows if item["passed"]),
        },
    }
    if staff:
        payload["rows"] = rows
    else:
        payload["my_row"] = next((item for item in rows if item["user_id"] == user.id), None)
    return payload
