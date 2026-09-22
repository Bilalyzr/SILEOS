"""Atomic claims, bounded retries and admin recovery. Never executes user code."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models.runtime import RuntimeJob, RuntimeRun

SCHEDULES = {
    "growth_maintenance": {"interval": 600, "label": "Commercial billing & sales follow-ups"},
    "payment_reconciliation": {"interval": 300, "label": "Payments & memberships"},
    "live_reminders": {"interval": 60, "label": "Live classes & learner reminders"},
    "campus_maintenance": {"interval": 60, "label": "Campus billing, email & WhatsApp"},
}
MAX_ATTEMPTS = 5
LEASE_SECONDS = 120


def now():
    return datetime.now(timezone.utc)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def ensure_schedules(db):
    for name in SCHEDULES:
        if db.get(RuntimeJob, name) is None:
            try:
                with db.begin_nested():
                    db.add(RuntimeJob(name=name, next_run_at=now()))
                    db.flush()
            except IntegrityError:
                pass  # another worker inserted the same schedule
    db.commit()


def claim(db, name, worker_id, at=None):
    if name not in SCHEDULES:
        raise ValueError("Unknown maintenance job")
    at = at or now()
    token = str(uuid4())
    # A conditional UPDATE is atomic on SQLite and PostgreSQL. No read-then-write claim.
    eligible = or_(
        and_(RuntimeJob.status.in_(["ready", "retry"]), RuntimeJob.next_run_at <= at),
        and_(RuntimeJob.status == "running", RuntimeJob.lease_until < at),
    )
    changed = db.query(RuntimeJob).filter(RuntimeJob.name == name, eligible).update({
        RuntimeJob.status: "running", RuntimeJob.lease_token: token,
        RuntimeJob.lease_until: at + timedelta(seconds=LEASE_SECONDS),
        RuntimeJob.attempts: RuntimeJob.attempts + 1,
    }, synchronize_session=False)
    if not changed:
        db.rollback()
        return None
    db.expire_all()
    job = db.get(RuntimeJob, name)
    db.query(RuntimeRun).filter_by(job_name=name, status="running").update(
        {"status": "interrupted", "finished_at": at, "error_code": "lease_expired"})
    if job.attempts > MAX_ATTEMPTS:
        job.status, job.lease_token, job.lease_until = "dead", None, None
        job.last_error = "repeated_worker_interruption"
        db.commit()
        return None
    db.add(RuntimeRun(id=token, job_name=name, worker_id=worker_id,
                      status="running", attempt=job.attempts, started_at=at))
    db.commit()
    return token


def renew(db, name, token, at=None):
    at = at or now()
    changed = db.query(RuntimeJob).filter_by(name=name, status="running", lease_token=token).filter(
        RuntimeJob.lease_until >= at).update({"lease_until": at + timedelta(seconds=LEASE_SECONDS)})
    db.commit()
    return bool(changed)


def finish(db, name, token, error=None, at=None):
    at = at or now()
    job = db.query(RuntimeJob).filter_by(name=name, lease_token=token, status="running").first()
    if job is None or utc(job.lease_until) < at:
        db.rollback()
        return False
    failure = type(error).__name__[:120] if error else None  # no provider credentials or payloads
    status = "dead" if error and job.attempts >= MAX_ATTEMPTS else "retry" if error else "ready"
    delay = min(1800, 30 * 2 ** (job.attempts - 1)) if error else SCHEDULES[name]["interval"]
    changed = db.query(RuntimeJob).filter_by(name=name, lease_token=token, status="running").update({
        "status": status, "next_run_at": at + timedelta(seconds=delay),
        "lease_token": None, "lease_until": None, "last_finished_at": at,
        "last_error": failure, "attempts": job.attempts if error else 0,
    }, synchronize_session=False)
    if changed:
        db.query(RuntimeRun).filter_by(id=token, status="running").update({
            "status": "failed" if error else "succeeded", "finished_at": at, "error_code": failure})
    db.commit()
    return bool(changed)


def request_retry(db, name, actor):
    if name not in SCHEDULES:
        raise HTTPException(404, "Unknown maintenance job")
    at = now()
    changed = db.query(RuntimeJob).filter(RuntimeJob.name == name,
        RuntimeJob.status.in_(["retry", "dead"])).update({
            "status": "ready", "next_run_at": at, "attempts": 0, "last_error": None})
    if not changed:
        db.rollback()
        raise HTTPException(409, "Only failed or dead-letter jobs can be retried")
    db.add(RuntimeRun(id=str(uuid4()), job_name=name, worker_id="admin",
        status="retry_requested", attempt=0, started_at=at, finished_at=at, requested_by=actor.id))
    from app.services.platform_tenant_service import audit
    audit(db, tenant_id=None, actor_id=actor.id, action="runtime.retry",
          target_type="runtime_job", target_id=name)
    db.commit()
    return {"status": "queued", "job": name}


def snapshot(db):
    from app.models.operations import ServiceHeartbeat
    at = now()
    rows = {row.name: row for row in db.query(RuntimeJob).all()}
    jobs = []
    for name, spec in SCHEDULES.items():
        job = rows.get(name)
        jobs.append({"name": name, **spec, "status": job.status if job else "not_started",
            "attempts": job.attempts if job else 0, "max_attempts": MAX_ATTEMPTS,
            "next_run_at": utc(job.next_run_at) if job else None,
            "last_finished_at": utc(job.last_finished_at) if job else None,
            "last_error": job.last_error if job else None,
            "lease_expired": bool(job and job.status == "running" and utc(job.lease_until) < at)})
    pulse = db.get(ServiceHeartbeat, "runtime_worker")
    age = (at - utc(pulse.seen_at)).total_seconds() if pulse else None
    runs = db.query(RuntimeRun).order_by(RuntimeRun.started_at.desc()).limit(100).all()
    from sqlalchemy import func
    from app.models.webhook_event import WebhookEvent
    from app.models.coding_assessment import CodingJudgeJob
    from app.models.campus_operations import CampusMailJob
    from app.models.campus_pilot import CampusWhatsAppMessage
    from app.models.recording_lesson import RecordingLesson
    from app.models.ai_provider import AiProviderCredential
    queues = {}
    for name, model in (("payment_webhooks", WebhookEvent), ("coding", CodingJudgeJob),
                        ("email", CampusMailJob), ("whatsapp", CampusWhatsAppMessage), ("recordings", RecordingLesson)):
        queues[name] = {getattr(status, "value", status): count for status, count in
                       db.query(model.status, func.count()).group_by(model.status)}
    providers = [{"provider": p.provider, "label": p.label, "status": p.health_status,
                  "failures": p.failure_count, "last_tested_at": utc(p.last_tested_at)}
                 for p in db.query(AiProviderCredential).filter_by(is_active=True).all()]
    return {"as_of": at, "queues": queues, "providers": providers,
        "worker": {"status": "unknown" if not pulse else "stale" if age > 90 else pulse.status,
        "last_seen": utc(pulse.seen_at) if pulse else None}, "jobs": jobs,
        "runs": [{"id": r.id, "job_name": r.job_name, "status": r.status, "attempt": r.attempt,
                  "started_at": utc(r.started_at), "finished_at": utc(r.finished_at),
                  "error_code": r.error_code, "requested_by": r.requested_by} for r in runs],
        "delivery_semantics": "At least once; each handler retains its own business idempotency checks."}
