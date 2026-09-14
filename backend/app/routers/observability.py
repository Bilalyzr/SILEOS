"""Private Prometheus scrape endpoint; a distinct token grants metrics only."""
import hmac
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.runtime_telemetry import telemetry
from app.services.runtime_service import snapshot, utc, now

router = APIRouter()


def authorize(authorization: str = Header(default="")):
    expected = get_settings().OBSERVABILITY_TOKEN
    supplied = authorization[7:] if authorization.startswith("Bearer ") else ""
    if len(expected) < 32 or not hmac.compare_digest(expected, supplied):
        raise HTTPException(403, "Metrics access denied")


@router.get("/metrics", dependencies=[Depends(authorize)])
async def metrics(db: Session = Depends(get_db)):
    counters = await telemetry.snapshot()
    runtime = snapshot(db)
    pulse = runtime["worker"]
    age = max(0, (now() - utc(pulse["last_seen"])).total_seconds()) if pulse["last_seen"] else -1
    lines = ["# TYPE sasha_runtime_worker_age_seconds gauge", f"sasha_runtime_worker_age_seconds {age}",
             "# TYPE sasha_runtime_worker_healthy gauge", f"sasha_runtime_worker_healthy {int(pulse['status'] == 'ok')}",
             "# TYPE sasha_runtime_job_dead gauge"]
    for job in runtime["jobs"]:
        lines.append(f'sasha_runtime_job_dead{{job="{job["name"]}"}} {int(job["status"] == "dead")}')
    lines += ["# TYPE sasha_telemetry_available gauge", f"sasha_telemetry_available {int(counters['status'] == 'available')}"]
    if counters["status"] == "available":
        lines += ["# TYPE sasha_http_requests_15m gauge", f"sasha_http_requests_15m {counters['requests']}",
                  "# TYPE sasha_http_error_ratio_15m gauge", f"sasha_http_error_ratio_15m {(counters['error_percent'] or 0) / 100}",
                  "# TYPE sasha_http_average_ms_15m gauge", f"sasha_http_average_ms_15m {counters['average_ms'] or 0}"]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4", headers={"Cache-Control": "no-store"})
