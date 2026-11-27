"""Phase 6 monitoring: judge queue depth, latency and failure rate.

Read-only. Used by the Prometheus scrape endpoint (app/routers/observability.py),
so it returns plain numbers and never learner data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

from sqlalchemy import func

from app.models.coding_assessment import CodingJudgeJob, CodingSubmission


WINDOW = timedelta(hours=1)
FINAL_STATUSES = ("passed", "failed", "error")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(pct / 100 * len(ordered)) - 1)
    return round(ordered[index], 3)


def judge_health(db) -> dict:
    now = _now()
    since = now - WINDOW

    queued = db.query(func.count(CodingJudgeJob.id)).filter(CodingJudgeJob.status == "queued").scalar() or 0
    leased = db.query(func.count(CodingJudgeJob.id)).filter(CodingJudgeJob.status == "leased").scalar() or 0
    oldest = (
        db.query(func.min(CodingJudgeJob.available_at))
        .filter(CodingJudgeJob.status == "queued")
        .scalar()
    )
    oldest = _as_utc(oldest)
    oldest_age = round((now - oldest).total_seconds(), 1) if oldest else 0.0

    final = (
        db.query(CodingSubmission.status, func.count(CodingSubmission.id))
        .filter(
            CodingSubmission.status.in_(FINAL_STATUSES),
            CodingSubmission.completed_at >= since,
        )
        .group_by(CodingSubmission.status)
        .all()
    )
    counts = {status: int(count) for status, count in final}
    total_final = sum(counts.values())
    error_ratio = round(counts.get("error", 0) / total_final, 4) if total_final else 0.0

    latencies = [
        (_as_utc(completed) - _as_utc(submitted)).total_seconds()
        for submitted, completed in (
            db.query(CodingSubmission.submitted_at, CodingSubmission.completed_at)
            .filter(
                CodingSubmission.status.in_(FINAL_STATUSES),
                CodingSubmission.completed_at >= since,
            )
            .order_by(CodingSubmission.completed_at.desc())
            .limit(500)
            .all()
        )
        if submitted is not None and completed is not None
    ]

    return {
        "queue_queued": int(queued),
        "queue_leased": int(leased),
        "queue_oldest_seconds": oldest_age,
        "completed_last_hour": total_final,
        "error_ratio_last_hour": error_ratio,
        "judge_latency_p95_seconds": _percentile([max(0.0, value) for value in latencies], 95),
        "judge_latency_p50_seconds": _percentile([max(0.0, value) for value in latencies], 50),
    }
