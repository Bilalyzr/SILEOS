"""Internal-only endpoints for server-to-server calls from the finalize
worker (deploy/scripts/finalize_recordings.py). Never exposed publicly —
mounted at /api/v1/internal/live and additionally guarded per-request by
`_require_internal_access` (see below); nginx also returns 404 for
/api/v1/internal/ and never proxies it (deploy/nginx/conf.d/10-app.conf),
but the guard here does not rely on that.

Guard, in order:

1. INTERNAL_TOKEN unset/blank -> 503 (endpoint not configured, not "public
   with no guard").
2. `X-Internal-Token` missing, or not constant-time-equal to
   settings.INTERNAL_TOKEN -> 403.
3. The request carries `X-Forwarded-For` or `X-Forwarded-Host` -> 403.

Why (3) replaced the earlier loopback client-host check: uvicorn runs with
`--proxy-headers --forwarded-allow-ips "*"` (see
deploy/docker-compose.app.yml), so `request.client.host` is NOT the peer's
real address — it is whatever the request's own X-Forwarded-For header
says. A check against 127.0.0.1/::1 was therefore trivially spoofable by
anyone who could reach the app tier, and simultaneously would have
REJECTED the legitimate worker had proxy-headers been off (docker's
userland proxy rewrites the peer address to the bridge gateway, not
loopback). Neither direction of that check was ever load-bearing.

The forwarded-header test is the honest inverse: nginx unconditionally sets
X-Forwarded-For on everything it proxies, so any request that reached this
endpoint through the edge is refused REGARDLESS of its token — an attacker
who somehow obtained the token still cannot use it from the internet. The
cron worker connects directly to the colour's 127.0.0.1-bound port
(deploy/scripts/finalize_recordings.sh) and sends neither header, so it
passes. A client that can already open a socket on the host's loopback
interface — and therefore forge an absent XFF — is inside the trust
boundary the docker network itself grants; the token remains the primary
gate for it.
"""
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel as _BaseModel, Field as _Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.live_class import LiveClass
from app.schemas.live_class import RecordingIngestIn, RecordingIngestOut
from app.services.live_recording_service import RecordingPathError, ingest_recording, validate_recording_path

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def _require_internal_access(
    x_internal_token: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
    x_forwarded_host: str | None = Header(default=None),
) -> None:
    if not settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=503, detail="Internal endpoint not configured")

    if not x_internal_token or not hmac.compare_digest(x_internal_token, settings.INTERNAL_TOKEN):
        raise HTTPException(status_code=403, detail="Invalid internal token")

    # Proxied request => came through the edge => not the local worker.
    if x_forwarded_for is not None or x_forwarded_host is not None:
        raise HTTPException(status_code=403, detail="Internal endpoint is not reachable through the edge")


@router.post("/recordings", response_model=RecordingIngestOut, dependencies=[Depends(_require_internal_access)])
async def ingest_recording_callback(
    payload: RecordingIngestIn,
    db: Session = Depends(get_db),
):
    """Called by the finalize worker once per finished `*.mp4`. Resolves
    the target LiveClass by `room_name` (not a caller-supplied numeric id):
    Jibri names recording files/directories after the opaque room being
    recorded, never after the LiveClass id, so `room_name` is the only
    identifier the worker can honestly derive from what it finds on disk —
    see RecordingIngestIn's docstring. Idempotent per class+file: if the
    class already has a `recording_video_id`, this is a no-op
    (skipped=True) rather than uploading a duplicate — the worker's own
    sidecar `.ingested` marker is the primary de-dupe, this is a second,
    server-side backstop against a retried/duplicated POST.

    Before anything touches the filesystem, `validate_recording_path`
    enforces that `payload.file_path` resolves inside
    `settings.JITSI_RECORDINGS_DIR` (rejecting traversal and symlink
    escapes) AND that its room-name path component matches this class's
    own `room_name` — resolving by room_name above already makes a
    cross-class mismatch here effectively impossible by construction, but
    the check stays as defense-in-depth against a caller sending a
    `room_name` that doesn't match the `file_path` it also sent. Either
    failure is a 422, not a 403/404 — the request is well-formed but its
    file_path claim is invalid for this class."""
    live_class = db.query(LiveClass).filter(LiveClass.room_name == payload.room_name).first()
    if not live_class:
        raise HTTPException(status_code=404, detail="Live class not found for this room_name")

    if live_class.recording_video_id:
        return RecordingIngestOut(
            class_id=live_class.id,
            recording_status=live_class.recording_status.value,
            recording_video_id=live_class.recording_video_id,
            skipped=True,
        )

    try:
        resolved_path = validate_recording_path(payload.file_path, live_class)
    except RecordingPathError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    live_class = await ingest_recording(db, live_class, str(resolved_path))
    db.commit()
    db.refresh(live_class)

    # Upload has committed. A workbench failure must never fail recording ingest.
    try:
        from app.services.recording_lesson_service import register
        register(db, live_class, resolved_path)
    except Exception:
        db.rollback()
        logger.exception("Could not queue transcription for class %s", live_class.id)

    return RecordingIngestOut(
        class_id=live_class.id,
        recording_status=live_class.recording_status.value,
        recording_video_id=live_class.recording_video_id,
        skipped=False,
    )


class TranscriptIngestIn(_BaseModel):
    class_id: int
    transcript: str = _Field(min_length=20, max_length=400_000)


@router.post("/transcripts", dependencies=[Depends(_require_internal_access)])
async def ingest_transcript(payload: TranscriptIngestIn, db: Session = Depends(get_db)):
    """Engine A (v2.0 §9.1, WP7): the transcription worker posts the finished
    transcript here. Stored on the permanent ClassReport; segmented into
    topics/concepts when GLM_API_KEY is set, else left `transcribed`."""
    from app.models.live_class_report import ClassReport
    from app.services import ai_layer_service as ai_svc
    report = db.query(ClassReport).filter(ClassReport.class_id == payload.class_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="No class report yet — the class must have ended")
    result = ai_svc.process_transcript(db, report, payload.transcript)
    return {"class_id": payload.class_id, **result}
