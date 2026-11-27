"""Phase 3 analytics for Utporul coding challenges.

Scoring rule: pass rate (weighted test score) is primary. Execution time and
peak memory from the judge break ties between equal scores, and submission
time breaks any remaining tie. Read-only: nothing here changes judge state.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import median

from sqlalchemy import func

from app.models.coding_assessment import (
    CodingCaseResult,
    CodingChallenge,
    CodingSubmission,
    CodingTestCase,
)
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User
from app.services.coding_assessment_service import (
    ACTIVE_ENROLLMENTS,
    _course_editor,
    _now,
)
from app.services.course_access import ADMIN_ROLES


FINAL_STATUSES = ("passed", "failed", "error")
LEADERBOARD_LIMIT = 50
FAILING_CASE_LIMIT = 10
HISTORY_LIMIT = 20


def ranking_key(score, total_ms: int, peak_kb: int, submitted_at):
    """Sort key: higher score first, then lower time, lower memory, earlier submit."""
    return (-float(score), int(total_ms), int(peak_kb), submitted_at)


def _performance_by_submission(db, submission_ids: list[int]) -> dict[int, tuple[int, int]]:
    """Total execution ms and peak memory KB per submission, from case results."""
    if not submission_ids:
        return {}
    rows = (
        db.query(
            CodingCaseResult.submission_id,
            func.coalesce(func.sum(CodingCaseResult.execution_ms), 0),
            func.coalesce(func.max(CodingCaseResult.memory_kb), 0),
        )
        .filter(CodingCaseResult.submission_id.in_(submission_ids))
        .group_by(CodingCaseResult.submission_id)
        .all()
    )
    return {int(sid): (int(total_ms), int(peak_kb)) for sid, total_ms, peak_kb in rows}


def _final_submissions(db, challenge_id: int) -> list[CodingSubmission]:
    return (
        db.query(CodingSubmission)
        .filter(
            CodingSubmission.challenge_id == challenge_id,
            CodingSubmission.status.in_(FINAL_STATUSES),
        )
        .order_by(CodingSubmission.submitted_at, CodingSubmission.id)
        .all()
    )


def _learner_names(db, user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    return dict(
        db.query(User.id, User.display_name).filter(User.id.in_(user_ids)).all()
    )


def _challenge_ranking(db, challenge: CodingChallenge) -> list[dict]:
    """One row per learner, ordered best first using the ranking key."""
    subs = _final_submissions(db, challenge.id)
    perf = _performance_by_submission(db, [s.id for s in subs])
    by_learner: dict[int, list[CodingSubmission]] = defaultdict(list)
    for sub in subs:
        by_learner[sub.user_id].append(sub)
    names = _learner_names(db, list(by_learner))

    rows = []
    for user_id, items in by_learner.items():
        best = min(
            items,
            key=lambda s: ranking_key(s.score, *perf.get(s.id, (0, 0)), s.submitted_at),
        )
        best_ms, best_kb = perf.get(best.id, (0, 0))
        passed = any(s.status == "passed" for s in items)
        rows.append(
            {
                "user_id": user_id,
                "learner_name": names.get(user_id, ""),
                "best_submission_id": best.id,
                "best_score": float(best.score),
                "passed": passed,
                "attempts": len(items),
                "total_ms": best_ms,
                "peak_memory_kb": best_kb,
                "_sort": ranking_key(best.score, best_ms, best_kb, best.submitted_at),
            }
        )
    rows.sort(key=lambda row: row.pop("_sort"))
    for position, row in enumerate(rows, start=1):
        row["rank"] = position
    return rows


def _minutes_to_first_pass(db, challenge: CodingChallenge) -> list[float]:
    subs = _final_submissions(db, challenge.id)
    first_seen: dict[int, object] = {}
    first_pass: dict[int, object] = {}
    for sub in subs:
        first_seen.setdefault(sub.user_id, sub.submitted_at)
        if sub.status == "passed":
            first_pass.setdefault(sub.user_id, sub.submitted_at)
    return [
        round((first_pass[user_id] - first_seen[user_id]).total_seconds() / 60, 1)
        for user_id in first_pass
    ]


def _failing_cases(db, challenge: CodingChallenge) -> list[dict]:
    """Per test case: how many final runs failed it, and how. No inputs are returned."""
    cases = {
        case.id: case
        for case in db.query(CodingTestCase).filter_by(challenge_id=challenge.id).all()
    }
    counts = (
        db.query(
            CodingCaseResult.test_case_id,
            CodingCaseResult.status,
            func.count(CodingCaseResult.id),
        )
        .join(CodingSubmission, CodingSubmission.id == CodingCaseResult.submission_id)
        .filter(
            CodingSubmission.challenge_id == challenge.id,
            CodingSubmission.status.in_(FINAL_STATUSES),
        )
        .group_by(CodingCaseResult.test_case_id, CodingCaseResult.status)
        .all()
    )
    per_case: dict[int, dict] = {}
    for case_id, status, count in counts:
        entry = per_case.setdefault(
            case_id, {"runs": 0, "failed": 0, "failure_breakdown": {}}
        )
        entry["runs"] += int(count)
        if status != "passed":
            entry["failed"] += int(count)
            entry["failure_breakdown"][status] = int(count)
    failing = [
        {
            "ordinal": cases[case_id].ordinal,
            "visibility": cases[case_id].visibility,
            "runs": entry["runs"],
            "failed": entry["failed"],
            "failure_breakdown": entry["failure_breakdown"],
        }
        for case_id, entry in per_case.items()
        if case_id in cases and entry["failed"] > 0
    ]
    failing.sort(key=lambda row: (-row["failed"], row["ordinal"]))
    return failing[:FAILING_CASE_LIMIT]


def _course_challenges(db, course: Course) -> list[CodingChallenge]:
    return (
        db.query(CodingChallenge)
        .filter(
            CodingChallenge.course_id == course.id,
            CodingChallenge.status != "draft",
        )
        .order_by(CodingChallenge.id)
        .all()
    )


def _challenge_metrics(db, challenge: CodingChallenge, ranking: list[dict]) -> dict:
    attempted = len(ranking)
    passed = sum(1 for row in ranking if row["passed"])
    minutes = _minutes_to_first_pass(db, challenge)
    return {
        "id": challenge.id,
        "slug": challenge.slug,
        "title": challenge.title,
        "status": challenge.status,
        "learners_attempted": attempted,
        "learners_passed": passed,
        "pass_rate": round(passed / attempted, 3) if attempted else 0.0,
        "total_submissions": sum(row["attempts"] for row in ranking),
        "median_minutes_to_first_pass": round(median(minutes), 1) if minutes else None,
        "failing_cases": _failing_cases(db, challenge),
        "leaderboard": ranking[:LEADERBOARD_LIMIT],
    }


def _authorize_course(db, course_id: int, user) -> Course:
    # Same editor rule as the authoring API: owners, co-editors and admins.
    return _course_editor(db, course_id, user)


def instructor_metrics(db, course_id: int, user) -> dict:
    course = _authorize_course(db, course_id, user)
    payload = []
    for challenge in _course_challenges(db, course):
        ranking = _challenge_ranking(db, challenge)
        payload.append(_challenge_metrics(db, challenge, ranking))
    return {
        "course_id": course.id,
        "generated_at": _now().isoformat(),
        "challenges": payload,
    }


def instructor_metrics_rows(db, course_id: int, user) -> list[list]:
    """Flat per-learner rows for CSV export. Caller sanitises cells for CSV."""
    course = _authorize_course(db, course_id, user)
    rows: list[list] = [
        [
            "challenge_slug",
            "challenge_title",
            "rank",
            "learner_id",
            "learner_name",
            "best_score",
            "passed",
            "attempts",
            "total_ms",
            "peak_memory_kb",
        ]
    ]
    for challenge in _course_challenges(db, course):
        for row in _challenge_ranking(db, challenge):
            rows.append(
                [
                    challenge.slug,
                    challenge.title,
                    row["rank"],
                    row["user_id"],
                    row["learner_name"],
                    row["best_score"],
                    "yes" if row["passed"] else "no",
                    row["attempts"],
                    row["total_ms"],
                    row["peak_memory_kb"],
                ]
            )
    return rows


def learner_progress(db, user) -> dict:
    """The learner's own scores over time, across active enrolments."""
    if user.role in ADMIN_ROLES:
        challenges = (
            db.query(CodingChallenge, Course.post_title)
            .join(Course, Course.id == CodingChallenge.course_id)
            .filter(CodingChallenge.status == "published")
            .all()
        )
    else:
        challenges = (
            db.query(CodingChallenge, Course.post_title)
            .join(Course, Course.id == CodingChallenge.course_id)
            .join(
                Enrollment,
                (Enrollment.course_id == CodingChallenge.course_id)
                & (Enrollment.user_id == user.id),
            )
            .filter(
                CodingChallenge.status == "published",
                Enrollment.enrollment_status.in_(ACTIVE_ENROLLMENTS),
            )
            .all()
        )
    by_id = {challenge.id: (challenge, title) for challenge, title in challenges}
    subs = (
        db.query(CodingSubmission)
        .filter(
            CodingSubmission.user_id == user.id,
            CodingSubmission.status.in_(FINAL_STATUSES),
            CodingSubmission.challenge_id.in_(list(by_id) or [-1]),
        )
        .order_by(CodingSubmission.submitted_at.desc(), CodingSubmission.id.desc())
        .all()
    )
    perf = _performance_by_submission(db, [s.id for s in subs])

    grouped: dict[int, list[CodingSubmission]] = defaultdict(list)
    for sub in subs:
        grouped[sub.challenge_id].append(sub)

    progress = []
    for challenge_id, (challenge, course_title) in by_id.items():
        items = grouped.get(challenge_id, [])
        best = (
            min(items, key=lambda s: ranking_key(s.score, *perf.get(s.id, (0, 0)), s.submitted_at))
            if items
            else None
        )
        passes = [s for s in items if s.status == "passed"]
        first_pass = min(passes, key=lambda s: s.submitted_at) if passes else None
        progress.append(
            {
                "slug": challenge.slug,
                "title": challenge.title,
                "course_title": course_title,
                "attempts": len(items),
                "max_attempts": challenge.max_attempts,
                "best_score": float(best.score) if best else 0.0,
                "best_total_ms": perf.get(best.id, (0, 0))[0] if best else None,
                "passed": first_pass is not None,
                "first_passed_at": first_pass.submitted_at.isoformat() if first_pass else None,
                "last_submitted_at": items[0].submitted_at.isoformat() if items else None,
            }
        )

    history = []
    for sub in subs[:HISTORY_LIMIT]:
        challenge, _ = by_id[sub.challenge_id]
        total_ms, peak_kb = perf.get(sub.id, (0, 0))
        history.append(
            {
                "submission_id": sub.id,
                "challenge_slug": challenge.slug,
                "challenge_title": challenge.title,
                "language": sub.language,
                "status": sub.status,
                "score": float(sub.score),
                "submitted_at": sub.submitted_at.isoformat(),
                "total_ms": total_ms,
                "peak_memory_kb": peak_kb,
            }
        )

    return {
        "summary": {
            "challenges_total": len(progress),
            "challenges_attempted": sum(1 for row in progress if row["attempts"]),
            "challenges_passed": sum(1 for row in progress if row["passed"]),
        },
        "challenges": progress,
        "history": history,
    }
