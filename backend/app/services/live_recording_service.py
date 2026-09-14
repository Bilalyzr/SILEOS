"""Recording ingest: finalize-worker callback -> Bunny upload -> AVAILABLE,
with a local-disk fallback and a FAILED+alert path if both fail.

`ingest_recording` is the single entry point (called by
app/routers/live_class_internal.py). It is idempotent per class+file: if the
class already has a `recording_video_id`, the caller skips re-ingesting
entirely (checked in the router before calling this — see its idempotency
comment) rather than uploading a second time.

Bunny wiring reuses the exact two-call shape from app/routers/bunny.py's
`upload_video_to_bunny` (create video object, then PUT the bytes) — that
file is NOT imported/modified; the minimal HTTP shape is duplicated here
so this module can be independently unit-tested by monkeypatching
`httpx.AsyncClient` without touching the bunny router's own test surface.

Security (post-review hardening, see task-6-report.md "Fix section"):
the internal endpoint accepts a caller-supplied `file_path` string. Before
this module ever opens that path, `validate_recording_path` must be called
by the router to (a) confirm it resolves inside `settings.
JITSI_RECORDINGS_DIR` — rejecting traversal (`../../etc/passwd`, absolute
paths outside the dir, and symlinks that resolve outside it) — and (b)
confirm the path's room-name component matches the target LiveClass's own
`room_name`, so one class's callback can't be pointed at another class's
recording file.
"""
import asyncio
import logging
import os
import shutil
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.models.live_class import LiveClass, RecordingStatus
from app.models.user import User
from app.services import live_class_service
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)
settings = get_settings()

BUNNY_LIBRARY_ID = os.getenv("BUNNY_LIBRARY_ID", "618286")
BUNNY_API_KEY = os.getenv("BUNNY_API_KEY", "")

# Bunny upload is retried this many times (simple loop + fixed backoff — no
# tenacity dependency per the plan) before falling back to local disk.
BUNNY_UPLOAD_ATTEMPTS = 3
BUNNY_UPLOAD_BACKOFF_SECONDS = 1.0

# Fallback destination when every Bunny attempt fails — relative to the
# backend/ working directory.
#
# NOT under uploads/. app/main.py mounts `uploads/` at /uploads with
# StaticFiles, which serves every file beneath it to anyone who knows (or
# guesses) the URL, with no auth check whatsoever. A class recording copied
# to uploads/live-recordings/ was therefore a paid-content leak: the whole
# point of the Bunny path is signed, enrollment-gated playback, and the
# fallback silently downgraded that to "public if you have the filename".
# recordings_fallback/ sits outside every StaticFiles mount (only `uploads`
# and `certificates` are mounted — see app/main.py), so the files are
# reachable only through code that checks access.
LOCAL_FALLBACK_DIR = "recordings_fallback"


class RecordingPathError(ValueError):
    """Raised by `validate_recording_path` for any rejected `file_path` —
    outside the configured recordings dir, a symlink escaping it, or not
    matching the target class's room_name. The router maps this to a 422
    with the exception's message as `detail`."""


def validate_recording_path(file_path: str, live_class: LiveClass) -> Path:
    """Validate a finalize-worker-supplied `file_path` before anything ever
    opens it. Returns the resolved Path on success; raises
    `RecordingPathError` otherwise. Two independent checks:

    1. Containment: `settings.JITSI_RECORDINGS_DIR` must be configured
       (non-blank), and the RESOLVED file_path (symlinks followed) must be
       relative to the RESOLVED recordings dir — `Path.resolve()` on both
       sides before comparing, so neither a `../..` traversal nor a
       symlink inside the recordings dir that points outside it can pass.
       `Path.resolve()` itself can raise `OSError` (symlink cycle, a path
       component that isn't a directory, etc.) — caught and converted to
       `RecordingPathError` so a hostile/malformed path 422s instead of
       500ing.
    2. Ownership: the resolved path's room-name component must match the
       target class's own `room_name` EXACTLY — not merely as a prefix.
       Accepted forms: a full path segment equal to `room_name`; a
       filename stem equal to `room_name`; or a filename stem that starts
       with `room_name` followed by a non-alphanumeric separator (`-`,
       `_`, `.`) — e.g. `si-abcd1234-part2.mp4` for room `si-abcd1234`.
       A bare `str.startswith` check would let a shorter room_name like
       "si-ab" match a file actually belonging to "si-abcd1234" (Python's
       `"si-abcd1234".startswith("si-ab")` is True); requiring an exact
       segment or a separator-bounded prefix closes that gap. Jibri names
       recordings after the room being recorded, so this stops class A's
       callback from being pointed at class B's file even when both live
       under the same recordings dir.
    """
    recordings_dir = settings.JITSI_RECORDINGS_DIR
    if not recordings_dir:
        raise RecordingPathError("Recording ingest is not configured (JITSI_RECORDINGS_DIR is blank)")

    try:
        base = Path(recordings_dir).resolve()
        candidate = Path(file_path)
        if not candidate.is_absolute():
            candidate = base / candidate
        resolved = candidate.resolve()
    except OSError:
        raise RecordingPathError("invalid recording path")

    if not (resolved == base or base in resolved.parents):
        raise RecordingPathError("file_path is outside the configured recordings directory")

    room_name = live_class.room_name
    rel = resolved.relative_to(base)
    path_parts = list(rel.parts)
    filename_stem = rel.stem
    separator_boundary = filename_stem[len(room_name):len(room_name) + 1]
    matches_room = (
        any(part == room_name for part in path_parts)
        or filename_stem == room_name
        or (filename_stem.startswith(room_name) and separator_boundary in ("-", "_", "."))
    )
    if not matches_room:
        raise RecordingPathError("file_path does not belong to this class (room_name mismatch)")

    return resolved


async def _upload_to_bunny(file_path: str, title: str) -> str | None:
    """Create a Bunny video object and upload `file_path`'s bytes to it.
    Returns the Bunny video GUID on success, None on any failure (network
    error, non-200 response, missing file). Mirrors
    app/routers/bunny.py:upload_video_to_bunny's two-call shape exactly so
    the resulting video_id/playback URL behave identically to a manually
    uploaded lesson video.
    """
    # A class recording is a multi-hundred-MB file. Reading it with a bare
    # fh.read() on the event loop stalls EVERY other request in this worker
    # for the duration of the disk read — and this runs inside a request
    # handler (the internal ingest callback), not a background job. Off to a
    # thread.
    #
    # RAM caveat: the whole file is still held in memory to hand httpx a
    # single `content=` body, because streaming it would mean either an
    # async file-reader dependency (aiofiles) or a sync generator that httpx
    # would consume on the event loop — reintroducing the stall this fix
    # removes, for a rewrite well past the size that was in scope here. So
    # peak RSS during an ingest is roughly one recording. Documented in
    # docs/LIVE_CLASSES.md; revisit if recordings outgrow the box's memory.
    def _read_file() -> bytes:
        with open(file_path, "rb") as fh:
            return fh.read()

    try:
        video_bytes = await asyncio.to_thread(_read_file)
    except OSError:
        logger.warning("recording file unreadable: %s", file_path, exc_info=True)
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            create_res = await client.post(
                f"https://video.bunnycdn.com/library/{BUNNY_LIBRARY_ID}/videos",
                headers={"AccessKey": BUNNY_API_KEY, "Content-Type": "application/json"},
                json={"title": title},
            )
            if create_res.status_code != 200:
                logger.warning("bunny create-video failed: status=%s", create_res.status_code)
                return None
            video_id = create_res.json()["guid"]

        async with httpx.AsyncClient(timeout=300) as client:
            upload_res = await client.put(
                f"https://video.bunnycdn.com/library/{BUNNY_LIBRARY_ID}/videos/{video_id}",
                headers={"AccessKey": BUNNY_API_KEY, "Content-Type": "application/octet-stream"},
                content=video_bytes,
            )
            if upload_res.status_code != 200:
                logger.warning("bunny upload failed: status=%s", upload_res.status_code)
                return None

        return video_id
    except Exception:
        logger.warning("bunny upload raised", exc_info=True)
        return None


async def _upload_to_bunny_with_retries(file_path: str, title: str) -> str | None:
    """3-attempt loop with a small fixed backoff between tries (no
    tenacity dependency — plan says "tenacity-free simple loop with
    backoff"). Sleeps async so the caller's event loop stays responsive."""
    for attempt in range(1, BUNNY_UPLOAD_ATTEMPTS + 1):
        video_id = await _upload_to_bunny(file_path, title)
        if video_id:
            return video_id
        if attempt < BUNNY_UPLOAD_ATTEMPTS:
            logger.info(
                "bunny upload attempt %s/%s failed for %s; retrying",
                attempt, BUNNY_UPLOAD_ATTEMPTS, file_path,
            )
            await asyncio.sleep(BUNNY_UPLOAD_BACKOFF_SECONDS)
    return None


def _copy_to_local_fallback(file_path: str, class_id: int) -> str | None:
    """Copy the recording into LOCAL_FALLBACK_DIR (created if missing).
    Returns the relative destination path on success, None on any
    filesystem error (caller treats that as the fallback path also having
    failed -> FAILED + alert).

    Stays synchronous — `ingest_recording` runs it via
    `asyncio.to_thread` so the multi-hundred-MB shutil.copy2 never blocks
    the event loop. Keeping the sync body means tests can call it directly
    and monkeypatch LOCAL_FALLBACK_DIR without an event loop.
    """
    try:
        dest_dir = Path(LOCAL_FALLBACK_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = f"class-{class_id}-{Path(file_path).name}"
        dest_path = dest_dir / filename
        shutil.copy2(file_path, dest_path)
        return str(dest_path)
    except OSError:
        logger.error("local fallback copy failed for class %s: %s", class_id, file_path, exc_info=True)
        return None


async def ingest_recording(db, live_class: LiveClass, file_path: str) -> LiveClass:
    """Ingest one finished recording for `live_class`.

    1. Upload to Bunny (3 attempts). On success: recording_video_id set,
       recording_status=AVAILABLE, event `recording.available`, instructor
       notified by email.
    2. On Bunny exhaustion: copy the file into recordings_fallback/ (NOT
       under uploads/, which app/main.py serves publicly via StaticFiles —
       see LOCAL_FALLBACK_DIR). On
       success: recording_status=AVAILABLE with
       settings["recording_fallback"]=true, event `recording.available`
       (fallback path is still "available" to the instructor/student, just
       not on the CDN).
    3. If the local copy ALSO fails: recording_status=FAILED, event
       `recording.failed`, admin ops alert via
       EmailService.send_payment_alert (reused as a generic ops-alert
       channel per the plan — not payments-specific, but it is the only
       existing "email the admins about an operational failure" helper in
       this codebase, so reusing it avoids introducing a near-duplicate).

    Does not commit — caller (the internal router) owns the transaction
    boundary, consistent with live_class_service.log_event's convention.
    """
    title = f"{live_class.title} — recording"

    video_id = await _upload_to_bunny_with_retries(file_path, title)
    if video_id:
        live_class.recording_video_id = video_id
        live_class.recording_status = RecordingStatus.AVAILABLE
        live_class_service.log_event(
            db, live_class.id, None, "recording.available",
            payload={"video_id": video_id, "source": "bunny"},
        )
        _notify_instructor_recording_ready(db, live_class)
        return live_class

    # shutil.copy2 of a large recording blocks the event loop just as the
    # read above does — same treatment (I8).
    fallback_path = await asyncio.to_thread(_copy_to_local_fallback, file_path, live_class.id)
    if fallback_path:
        live_class.recording_status = RecordingStatus.AVAILABLE
        current_settings = dict(live_class.settings or {})
        current_settings["recording_fallback"] = True
        current_settings["recording_fallback_path"] = fallback_path
        live_class.settings = current_settings
        live_class_service.log_event(
            db, live_class.id, None, "recording.available",
            payload={"source": "local_fallback", "path": fallback_path},
        )
        _notify_instructor_recording_ready(db, live_class)
        return live_class

    # Both paths failed.
    live_class.recording_status = RecordingStatus.FAILED
    live_class_service.log_event(
        db, live_class.id, None, "recording.failed",
        payload={"file_path": file_path},
    )
    _alert_recording_failed(live_class, file_path)
    return live_class


def _notify_instructor_recording_ready(db, live_class: LiveClass) -> None:
    instructor = db.query(User).filter(User.id == live_class.instructor_id).first()
    to_email = getattr(instructor, "user_email", None) if instructor else None
    if not to_email:
        return
    try:
        EmailService._send_or_mock(
            to_email,
            "Class recording ready",
            f"The recording for '{live_class.title}' is now available.",
        )
    except Exception:
        logger.warning("recording-ready email failed for class %s", live_class.id, exc_info=True)


def _alert_recording_failed(live_class: LiveClass, file_path: str) -> None:
    try:
        EmailService.send_payment_alert(
            "Live class recording failed",
            (
                f"Recording ingest failed for class {live_class.id} "
                f"('{live_class.title}') after Bunny upload and local "
                f"fallback both failed. Source file: {file_path}"
            ),
        )
    except Exception:
        logger.warning("recording-failed alert email failed for class %s", live_class.id, exc_info=True)
