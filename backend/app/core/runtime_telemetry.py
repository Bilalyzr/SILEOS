"""Bounded Redis metrics and structured request logs without bodies or secrets."""
import json
import logging
import time
from uuid import uuid4
import redis.asyncio as redis
from app.core.config import get_settings

logger = logging.getLogger("sasha.requests")
logger.setLevel(logging.INFO)
BUCKETS = (0.1, 0.3, 1.0, 3.0, 10.0)


class Telemetry:
    def __init__(self):
        self.client = None
        self.retry_after = 0

    def connection(self):
        if self.client is None:
            self.client = redis.from_url(get_settings().REDIS_URL, decode_responses=True,
                socket_connect_timeout=0.2, socket_timeout=0.2, retry_on_timeout=False)
        return self.client

    async def record(self, elapsed, status):
        if not get_settings().RUNTIME_METRICS_ENABLED or time.monotonic() < self.retry_after:
            return
        try:
            key = f"sasha:http:minute:{int(time.time() // 60)}"
            async with self.connection().pipeline(transaction=True) as pipe:
                pipe.hincrby(key, "requests", 1)
                pipe.hincrby(key, "errors", int(status >= 500))
                pipe.hincrby(key, "slow", int(elapsed > 1))
                pipe.hincrbyfloat(key, "duration", elapsed)
                for bucket in BUCKETS:
                    pipe.hincrby(key, f"le_{bucket}", int(elapsed <= bucket))
                pipe.expire(key, 1200)
                await pipe.execute()
        except Exception:
            self.retry_after = time.monotonic() + 30

    async def snapshot(self):
        if not get_settings().RUNTIME_METRICS_ENABLED:
            return {"status": "disabled", "window_minutes": 15, "detail": "Request metrics are disabled."}
        try:
            minute = int(time.time() // 60)
            async with self.connection().pipeline(transaction=False) as pipe:
                for offset in range(15):
                    pipe.hgetall(f"sasha:http:minute:{minute - offset}")
                rows = await pipe.execute()
            values = {key: sum(float(row.get(key, 0)) for row in rows)
                      for key in ("requests", "errors", "slow", "duration")}
            count = values["requests"]
            return {"status": "available", "window_minutes": 15,
                "requests": int(count), "errors": int(values["errors"]),
                "slow_requests": int(values["slow"]),
                "average_ms": round(values["duration"] * 1000 / count, 1) if count else None,
                "error_percent": round(values["errors"] * 100 / count, 2) if count else None,
                "latency_buckets": {str(b): sum(int(row.get(f"le_{b}", 0)) for row in rows) for b in BUCKETS}}
        except Exception:
            return {"status": "unavailable", "window_minutes": 15,
                    "detail": "Redis metrics are unavailable; this is not a zero-traffic reading."}


telemetry = Telemetry()


class RuntimeTelemetryMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started, status = time.perf_counter(), 500
        async def capture(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)
        try:
            await self.app(scope, receive, capture)
        finally:
            elapsed = time.perf_counter() - started
            state = scope.get("state", {})
            route = getattr(scope.get("route"), "path", "unmatched")
            # Log route templates, not URLs, query strings, user text, JWTs or email.
            logger.info(json.dumps({"event": "http_request", "request_id": state.get("request_id", uuid4().hex),
                "route": route, "method": scope.get("method"), "status": status,
                "duration_ms": round(elapsed * 1000, 2), "role": state.get("actor_role", "anonymous"),
                "tenant_id": state.get("tenant_id"), "vertical": state.get("business_vertical", "shared")}))
            if not scope.get("path", "").startswith(("/health", "/api/v1/admin/operations/telemetry", "/api/v1/internal/observability")):
                await telemetry.record(elapsed, status)
