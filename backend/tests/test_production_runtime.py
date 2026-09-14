import asyncio
from datetime import timedelta
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.models.runtime import RuntimeJob, RuntimeRun
from app.models.platform_tenant import PlatformAuditEvent
from app.services import runtime_service as svc
from app.workers.runtime import validate_api_mode, LeaderLease

JOB = "payment_reconciliation"


def test_claim_is_exclusive_and_completed_job_is_not_immediately_reclaimed(db):
    svc.ensure_schedules(db)
    token = svc.claim(db, JOB, "worker-one")
    assert token
    assert svc.claim(db, JOB, "worker-two") is None
    assert not svc.finish(db, JOB, "wrong-owner")
    assert svc.finish(db, JOB, token)
    assert svc.claim(db, JOB, "worker-two") is None
    assert db.get(RuntimeRun, token).status == "succeeded"


def test_expired_lease_recovers_and_old_owner_cannot_acknowledge(db):
    svc.ensure_schedules(db)
    at = svc.now()
    old = svc.claim(db, JOB, "old", at)
    later = at + timedelta(seconds=svc.LEASE_SECONDS + 1)
    assert not svc.renew(db, JOB, old, later)
    assert not svc.finish(db, JOB, old, at=later)
    new = svc.claim(db, JOB, "new", later)
    assert new and new != old
    assert not svc.finish(db, JOB, old, at=later)
    assert db.get(RuntimeRun, old).status == "interrupted"
    assert svc.finish(db, JOB, new, at=later)


def test_bounded_backoff_dead_letter_and_audited_retry(db, make_user):
    actor = make_user(role="admin")
    svc.ensure_schedules(db)
    at = svc.now()
    for attempt in range(1, svc.MAX_ATTEMPTS + 1):
        token = svc.claim(db, JOB, "failing", at)
        assert token
        assert svc.finish(db, JOB, token, RuntimeError("secret provider payload"), at)
        db.expire_all()
        job = db.get(RuntimeJob, JOB)
        assert job.attempts == attempt
        assert "secret" not in job.last_error
        assert svc.claim(db, JOB, "early", at) is None
        at = svc.utc(job.next_run_at) + timedelta(seconds=1)
    assert job.status == "dead"
    assert svc.claim(db, JOB, "late", at) is None
    assert svc.request_retry(db, JOB, actor)["status"] == "queued"
    assert db.query(PlatformAuditEvent).filter_by(action="runtime.retry", actor_id=actor.id).count() == 1
    assert db.query(RuntimeRun).filter_by(status="retry_requested", requested_by=actor.id).count() == 1
    with pytest.raises(HTTPException) as exc:
        svc.request_retry(db, JOB, actor)
    assert exc.value.status_code == 409


def test_repeated_crashes_eventually_stop(db):
    svc.ensure_schedules(db)
    at = svc.now()
    for _ in range(svc.MAX_ATTEMPTS):
        assert svc.claim(db, JOB, "crashed", at)
        at += timedelta(seconds=svc.LEASE_SECONDS + 1)
    assert svc.claim(db, JOB, "new", at) is None
    assert db.get(RuntimeJob, JOB).status == "dead"


@pytest.mark.parametrize("role", ["student", "instructor", "company", "parent", "spoc"])
def test_runtime_is_admin_only(client, make_user, role):
    from app.core.security import create_access_token
    user = make_user(role=role)
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(user.id)})
    for method, path in [("get", "/runtime"), ("post", "/runtime/x/retry"), ("get", "/telemetry")]:
        assert getattr(client, method)("/api/v1/admin/operations" + path).status_code == 403


def test_admin_empty_runtime_is_unknown_not_healthy(client, as_user, make_user):
    as_user(make_user(role="admin"))
    result = client.get("/api/v1/admin/operations/runtime")
    assert result.status_code == 200
    assert result.json()["worker"]["status"] == "unknown"
    assert all(j["status"] == "not_started" for j in result.json()["jobs"])


def test_runtime_dates_are_timezone_aware(db):
    svc.ensure_schedules(db)
    value = svc.snapshot(db)
    assert all(job["next_run_at"].utcoffset() == timedelta(0) for job in value["jobs"])
    assert set(value["queues"]) == {"payment_webhooks", "coding", "email", "whatsapp", "recordings"}


@pytest.mark.parametrize("mode", ["inline", "disabled"])
def test_production_cannot_embed_or_disable_schedulers(mode):
    with pytest.raises(RuntimeError):
        validate_api_mode(SimpleNamespace(ENVIRONMENT="production", BACKGROUND_TASK_MODE=mode))
    validate_api_mode(SimpleNamespace(ENVIRONMENT="development", BACKGROUND_TASK_MODE=mode))


def test_redis_lock_release_and_renew_are_owner_conditional():
    class Redis:
        owner = None
        async def set(self, key, token, nx, ex):
            if self.owner:
                return False
            self.owner = token
            return True
        async def eval(self, script, keys, key, token, *args):
            assert "redis.call('get',KEYS[1]) == ARGV[1]" in script
            if token != self.owner:
                return 0
            if not args:
                self.owner = None
            return 1
    async def run():
        redis = Redis()
        first, second = LeaderLease(redis), LeaderLease(redis)
        assert await first.tick()
        assert not await second.tick()
        redis.owner = second.token  # TTL expiry and takeover
        assert not await first.tick()
        await first.close()
        assert redis.owner == second.token
    asyncio.run(run())


def test_metrics_token_is_separate_from_user_auth(client, as_user, make_user, monkeypatch):
    from app.routers import observability
    secret = "metrics-test-token-" + "x" * 40
    monkeypatch.setattr(observability, "get_settings", lambda: SimpleNamespace(OBSERVABILITY_TOKEN=secret))
    as_user(make_user(role="admin"))
    path = "/api/v1/internal/observability/metrics"
    assert client.get(path).status_code == 403
    assert client.get(path, headers={"Authorization": "Bearer incorrect"}).status_code == 403
    response = client.get(path, headers={"Authorization": "Bearer " + secret})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "sasha_runtime_worker_age_seconds -1" in response.text
    assert "sasha_telemetry_available 0" in response.text
    assert secret not in response.text


def test_disabled_metrics_do_not_open_redis(monkeypatch):
    from app.core.runtime_telemetry import Telemetry
    instance = Telemetry()
    monkeypatch.setattr(instance, "connection", lambda: pytest.fail("Disabled metrics must not connect"))
    assert asyncio.run(instance.snapshot())["status"] == "disabled"


def test_error_reporting_scrubs_credentials_and_personal_details():
    from app.core.error_reporting import scrub_event
    event = {"request": {"url": "https://example.org/api?token=secret", "headers": {"Authorization": "secret"},
        "cookies": "private", "data": "student names", "query_string": "secret", "env": {}},
        "user": {"email": "student@example.org"}, "spans": [{"description": "SQL secret"}],
        "extra": {"secret": "value"}, "breadcrumbs": {"values": ["secret"]},
        "exception": {"values": [{"value": "key exposed", "stacktrace": {"frames": [{"vars": {"api_key": "secret"}, "filename": "worker.py"}]}}]}}
    cleaned = scrub_event(event, {})
    assert cleaned["request"] == {"url": "https://example.org/api"}
    assert all(key not in cleaned for key in ("user", "extra", "breadcrumbs", "spans"))
    assert "vars" not in cleaned["exception"]["values"][0]["stacktrace"]["frames"][0]
    assert "key exposed" not in str(cleaned)


def test_runtime_migration_reentrant_and_roundtrip(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    from sqlalchemy import create_engine, inspect, text
    from app.core.database import Base
    backend = Path(__file__).resolve().parents[1]
    url = "sqlite:///" + (tmp_path / "runtime.sqlite").as_posix()
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))
    engine = create_engine(url)
    try:
        Base.metadata.create_all(engine)
        command.stamp(cfg, "0049")
        import logging
        operational_logger = logging.getLogger("app.services.runtime_service")
        operational_logger.disabled = False
        command.upgrade(cfg, "head")
        assert not operational_logger.disabled
        command.upgrade(cfg, "head")
        assert {"runtime_jobs", "runtime_runs"} <= set(inspect(engine).get_table_names())
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0050"
        command.downgrade(cfg, "0049")
        assert "runtime_jobs" not in inspect(engine).get_table_names()
        command.upgrade(cfg, "head")
        assert "runtime_runs" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
