#!/usr/bin/env python3
"""finalize_recordings.py — scan the Jibri recordings directory for finished
`*.mp4` files and hand each one to the backend's internal ingest endpoint.

Stdlib-only (no requests/httpx) per the plan — the finalize worker runs on
the VPS host, outside the backend's Python venv, via cron.

Usage:
    JITSI_RECORDINGS_DIR=/path/to/recordings \
    INTERNAL_TOKEN=... \
    python3 finalize_recordings.py [--backend-url http://127.0.0.1:8000] [--min-age-seconds 120]

Algorithm:
  1. List `*.mp4` files directly under JITSI_RECORDINGS_DIR (non-recursive —
     matches Jibri's flat per-recording output layout).
  2. Skip a file if a sidecar `<file>.ingested` marker already exists next
     to it (idempotency: a file is only ever POSTed once from this worker;
     the internal endpoint has its own server-side idempotency backstop —
     see live_class_internal.py — for the case a marker write itself failed
     after a successful POST).
  3. Skip a file younger than `--min-age-seconds` (default 120s) — Jibri
     may still be writing to it; POSTing a half-written file would ingest
     garbage.
  4. Derive `room_name` from the filename: Jibri names recording
     files/directories after the room being recorded — this worker expects
     the deployment's Jibri to be configured (see compose.live.yml) to name
     each file/directory after the LiveClass's own opaque `room_name`
     (`si-<random8>` — see app/services/live_class_service.
     generate_room_name), e.g. `si-a1b2c3d4.mp4` or
     `si-a1b2c3d4/output.mp4` — the leading path component (directory name,
     or filename stem when there is no subdirectory) is sent as-is. This
     replaces an earlier "leading integer = class_id" convention that did
     not match how Jibri actually names recordings (by room, never by the
     numeric LiveClass id) and could never have matched a real file in
     production — see task-6-report.md's fix-up notes for the incident.
     The backend resolves `room_name` to a LiveClass server-side (404 if no
     match) and independently verifies the room name is actually a
     component of `file_path` before touching the file (defense in depth
     against a mismatched pair in the request body).
  5. POST {room_name, file_path, size_bytes, duration_seconds} as JSON to
     POST {backend_url}/api/v1/internal/live/recordings with header
     X-Internal-Token. duration_seconds is best-effort 0 when it cannot be
     determined without a media-parsing dependency (stdlib-only constraint)
     — the backend does not require an accurate value for ingest to
     succeed.

     `file_path` is sent RELATIVE to the recordings dir (e.g.
     `si-a1b2c3d4.mp4` or `si-a1b2c3d4/output.mp4`), never absolute. This
     worker runs on the HOST and sees the recordings at
     $JITSI_RECORDINGS_DIR (deploy/recordings); the backend runs in a
     container and sees the SAME files bind-mounted at its own
     JITSI_RECORDINGS_DIR (/app/recordings_live — see
     deploy/docker-compose.app.yml). An absolute host path is meaningless
     inside the container and was rejected by the backend's containment
     check, which is how the ingest chain was silently broken. A relative
     path is the only value that means the same thing on both sides:
     app/services/live_recording_service.validate_recording_path joins it
     onto its own configured base before resolving, so containment and the
     room_name ownership check still apply exactly as before.
  6. On HTTP 200: write the `.ingested` sidecar file (empty, just a marker)
     so this file is never POSTed again.
  7. On any other status or a network error: log and move on to the next
     file — a single failure must not abort the whole scan (per-item fault
     isolation, same principle as reconciliation.py's loop). The backend's
     response body is logged truncated to ~200 chars — long enough to see
     an error detail, short enough that a pathological/huge response body
     can't bloat the log file.

Exit code is always 0 unless argument parsing fails (2) — a cron job should
not fail-alert on a single file's transient upload error; failures are
visible in the log output (deploy/scripts/finalize_recordings.sh redirects
this script's stdout/stderr to logs/finalize_recordings.log).
"""
import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("finalize_recordings")

DEFAULT_MIN_AGE_SECONDS = 120
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
INGEST_PATH = "/api/v1/internal/live/recordings"

# Truncate a logged backend response body to this many characters — long
# enough to see an error detail, short enough that a pathological/huge
# response can't bloat the log file (I2 hardening).
LOGGED_RESPONSE_BODY_LIMIT = 200


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recordings-dir",
        default=os.environ.get("JITSI_RECORDINGS_DIR", ""),
        help="Directory to scan for *.mp4 files (default: $JITSI_RECORDINGS_DIR)",
    )
    parser.add_argument(
        "--backend-url",
        default=os.environ.get("FINALIZE_BACKEND_URL", DEFAULT_BACKEND_URL),
        help=f"Backend base URL (default: {DEFAULT_BACKEND_URL})",
    )
    parser.add_argument(
        "--internal-token",
        default=os.environ.get("INTERNAL_TOKEN", ""),
        help="Value for the X-Internal-Token header (default: $INTERNAL_TOKEN)",
    )
    parser.add_argument(
        "--min-age-seconds",
        type=int,
        default=DEFAULT_MIN_AGE_SECONDS,
        help=f"Skip files newer than this many seconds (default: {DEFAULT_MIN_AGE_SECONDS})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout in seconds (default: 30)",
    )
    return parser.parse_args(argv)


def _room_name_from_path(recordings_dir: Path, mp4_path: Path) -> str | None:
    """Leading path component relative to recordings_dir, treated as the
    room name — either the filename stem (`si-a1b2c3d4.mp4`) or the first
    path segment (`si-a1b2c3d4/output.mp4`). Returns None only if that
    component is empty (should not happen for a real file)."""
    rel = mp4_path.relative_to(recordings_dir)
    first_part = rel.parts[0]
    stem = first_part.split(".")[0]
    return stem or None


def _find_candidate_files(recordings_dir: Path, min_age_seconds: int) -> list[Path]:
    """*.mp4 files anywhere under recordings_dir (Jibri may nest one level
    per room), skipping already-ingested (sidecar marker present) and
    too-young files."""
    now = time.time()
    candidates: list[Path] = []
    for mp4_path in sorted(recordings_dir.rglob("*.mp4")):
        if not mp4_path.is_file():
            continue
        marker = mp4_path.with_suffix(mp4_path.suffix + ".ingested")
        if marker.exists():
            continue
        try:
            mtime = mp4_path.stat().st_mtime
        except OSError:
            continue
        if (now - mtime) < min_age_seconds:
            logger.info("skip (too young): %s", mp4_path)
            continue
        candidates.append(mp4_path)
    return candidates


def _post_ingest(backend_url: str, token: str, timeout: float, body: dict) -> tuple[int, str]:
    url = backend_url.rstrip("/") + INGEST_PATH
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Internal-Token": token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)


def run(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args(argv)

    if not args.recordings_dir:
        logger.error("no recordings dir given (--recordings-dir or $JITSI_RECORDINGS_DIR)")
        return 2
    if not args.internal_token:
        logger.error("no internal token given (--internal-token or $INTERNAL_TOKEN)")
        return 2

    recordings_dir = Path(args.recordings_dir)
    if not recordings_dir.is_dir():
        logger.error("recordings dir does not exist: %s", recordings_dir)
        return 0

    candidates = _find_candidate_files(recordings_dir, args.min_age_seconds)
    if not candidates:
        logger.info("no eligible recordings found in %s", recordings_dir)
        return 0

    processed = 0
    failed = 0
    for mp4_path in candidates:
        room_name = _room_name_from_path(recordings_dir, mp4_path)
        if room_name is None:
            logger.warning("skip (cannot derive room_name): %s", mp4_path)
            continue

        try:
            size_bytes = mp4_path.stat().st_size
        except OSError:
            size_bytes = 0

        # RELATIVE to the recordings dir — the backend sees these same files
        # under a DIFFERENT absolute path (container bind-mount), so an
        # absolute host path would never resolve there. See the module
        # docstring, step 5. as_posix() keeps the separator stable if this
        # ever runs on a non-POSIX host.
        rel_file_path = mp4_path.relative_to(recordings_dir).as_posix()

        body = {
            "room_name": room_name,
            "file_path": rel_file_path,
            "size_bytes": size_bytes,
            # Duration is best-effort 0 (stdlib-only — no media parsing dep);
            # the backend does not require an accurate value to ingest.
            "duration_seconds": 0,
        }

        status, response_text = _post_ingest(args.backend_url, args.internal_token, args.timeout, body)
        logged_body = response_text[:LOGGED_RESPONSE_BODY_LIMIT]
        if len(response_text) > LOGGED_RESPONSE_BODY_LIMIT:
            logged_body += "...(truncated)"
        if status == 200:
            marker = mp4_path.with_suffix(mp4_path.suffix + ".ingested")
            try:
                marker.touch()
            except OSError:
                logger.error("ingested OK but failed to write marker for %s", mp4_path, exc_info=True)
            logger.info("ingested: %s (room_name=%s)", mp4_path, room_name)
            processed += 1
        else:
            logger.error(
                "ingest failed for %s (room_name=%s): status=%s body=%s",
                mp4_path, room_name, status, logged_body,
            )
            failed += 1

    logger.info("done: %d ingested, %d failed, %d total candidates", processed, failed, len(candidates))
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
