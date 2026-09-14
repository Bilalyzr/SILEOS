"""Supervised maintenance worker: python -m app.workers.runtime.

Redis selects a scheduler; durable DB claims and the handlers' Postgres advisory
locks remain the safety boundary during Redis failover. External effects retain
their source-specific idempotency, rather than claiming exactly-once delivery.
"""
import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import signal
import socket
import time
from uuid import uuid4
import redis.asyncio as redis
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.services import runtime_service as svc
from app.services.operations_service import heartbeat
from app import models  # noqa: F401

logger = logging.getLogger("sasha.runtime")
LOCK_KEY = "sasha:runtime:scheduler"
HEALTH_FILE = Path(os.getenv("RUNTIME_HEALTH_FILE", "/tmp/sasha-runtime-health.json"))
RENEW = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('expire',KEYS[1],ARGV[2]) else return 0 end"
RELEASE = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end"


def validate_api_mode(settings):
    if settings.ENVIRONMENT == "production" and settings.BACKGROUND_TASK_MODE != "worker":
        raise RuntimeError("Production requires BACKGROUND_TASK_MODE=worker and the dedicated runtime service")


class LeaderLease:
    def __init__(self, client):
        self.client, self.token, self.owned = client, str(uuid4()), False

    async def tick(self):
        if self.owned:
            self.owned = bool(await self.client.eval(RENEW, 1, LOCK_KEY, self.token, 30))
        else:
            self.owned = bool(await self.client.set(LOCK_KEY, self.token, nx=True, ex=30))
        return self.owned

    async def close(self):
        await self.client.eval(RELEASE, 1, LOCK_KEY, self.token)


def db_call(fn, *args):
    with SessionLocal() as db:
        return fn(db, *args)


async def execute(name):
    if name == "payment_reconciliation":
        from app.services.reconciliation import _run_cycle
        # Wall-clock slot survives process restarts; gateway diff runs every 30m.
        await asyncio.to_thread(_run_cycle, int(time.time() // 300))
    elif name == "live_reminders":
        from app.services.live_reminders import _run_cycle
        await _run_cycle()
    elif name == "campus_maintenance":
        from app.services.campus_worker import tick
        await asyncio.to_thread(tick)
    else:
        raise ValueError("Unsupported maintenance job")


async def run_claim(name, token):
    task = asyncio.create_task(execute(name))
    try:
        while not task.done():
            await asyncio.wait({task}, timeout=20)
            if not task.done() and not await asyncio.to_thread(db_call, svc.renew, name, token):
                # Do not falsely acknowledge lost ownership. In-flight blocking
                # provider calls must drain; handler advisory locks protect them.
                logger.error(json.dumps({"event": "lease_lost", "job": name, "run_id": token}))
                await task
                return
        error = task.exception()
        await asyncio.to_thread(db_call, svc.finish, name, token, error)
        logger.info(json.dumps({"event": "job_finished", "job": name, "run_id": token,
            "status": "failed" if error else "succeeded", "error_code": type(error).__name__ if error else None}))
    finally:
        # Shielding avoids cancelling a Python thread while its provider call
        # still runs. Forced process termination is recovered by the DB lease.
        if not task.done():
            await asyncio.shield(task)


async def serve(once=False, allow_local=False):
    settings = get_settings()
    if settings.BACKGROUND_TASK_MODE != "worker":
        raise RuntimeError("Worker requires BACKGROUND_TASK_MODE=worker")
    if allow_local and settings.ENVIRONMENT == "production":
        raise RuntimeError("Local runtime mode is forbidden in production")
    if not allow_local and engine.dialect.name != "postgresql":
        raise RuntimeError("Use PostgreSQL, or explicitly --allow-local for development only")
    client = redis.from_url(settings.REDIS_URL, decode_responses=True,
        socket_connect_timeout=2, socket_timeout=2, retry_on_timeout=False)
    lease = LeaderLease(client)
    if not allow_local:
        await client.ping()  # fail closed; never silently use MockRedis for leadership
    await asyncio.to_thread(db_call, svc.ensure_schedules)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass  # Windows; container production uses Unix signals
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
    running = {}
    try:
        while not stop.is_set():
            for name, task in list(running.items()):
                if task.done():
                    if not task.cancelled() and task.exception():
                        logger.error(json.dumps({"event": "runtime_failure", "job": name,
                            "error_code": type(task.exception()).__name__}))
                    del running[name]
            try:
                leader = allow_local or await lease.tick()
                if leader:
                    for name in svc.SCHEDULES:
                        if name not in running:
                            token = await asyncio.to_thread(db_call, svc.claim, name, worker_id)
                            if token:
                                running[name] = asyncio.create_task(run_claim(name, token))
                    await asyncio.to_thread(heartbeat, "runtime_worker", "ok", {"worker_id": worker_id})
                HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
                HEALTH_FILE.write_text(json.dumps({"at": time.time(), "leader": leader}), encoding="utf-8")
            except Exception as exc:
                lease.owned = False
                logger.error(json.dumps({"event": "scheduler_unavailable", "error_code": type(exc).__name__}))
                if once:
                    raise
            if once:
                break
            try:
                await asyncio.wait_for(stop.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
        await asyncio.gather(*running.values())
    finally:
        # Keep leadership until running work drains on normal shutdown.
        await asyncio.gather(*running.values(), return_exceptions=True)
        if not allow_local:
            await lease.close()
        await client.aclose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--allow-local", action="store_true")
    parser.add_argument("--health", action="store_true")
    args = parser.parse_args()
    if args.health:
        try:
            healthy = time.time() - json.loads(HEALTH_FILE.read_text())["at"] < 90
        except (OSError, ValueError, KeyError):
            healthy = False
        raise SystemExit(0 if healthy else 1)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(serve(args.once, args.allow_local))


if __name__ == "__main__":
    main()
