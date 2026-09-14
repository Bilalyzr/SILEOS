import re, time, json, asyncio, os, shutil
from typing import Dict, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter()

def _find_ytdlp() -> Optional[str]:
    """Locate yt-dlp. The historic hardcoded path only exists on the host
    venv, not inside the deployed container image (which installs the pip
    package onto PATH) — the mismatch made every extraction fail."""
    found = shutil.which('yt-dlp')
    if found:
        return found
    for candidate in (
        '/www/wwwroot/sasha_lms/sasha_lms/sasha_lms/backend/venv/bin/yt-dlp',
        '/usr/local/bin/yt-dlp',
    ):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None

YTDLP = _find_ytdlp()
COOKIES = '/www/wwwroot/sasha_lms/sasha_lms/sasha_lms/backend/youtube_cookies.txt'
cache: Dict[str, Dict] = {}

# yt-dlp extractions spawn a subprocess each and can take tens of seconds.
# Without a cap, N concurrent unauthenticated requests pin the CPU/memory
# of the whole backend. 4 concurrent extractions max; further callers get
# an immediate 429 rather than queueing.
MAX_CONCURRENT_EXTRACTIONS = 4
_extraction_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)

def get_video_id(url: str) -> Optional[str]:
    for p in [r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)", r"youtube\.com/shorts/([^&\n?#]+)"]:
        m = re.search(p, url)
        if m:
            candidate = m.group(1)
            # Only accept a well-formed 11-char YouTube id. Callers rebuild a
            # canonical watch URL from this — the raw url is never handed to
            # yt-dlp, which would otherwise allow SSRF.
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                return candidate
    return None

async def extract(url: str, quality: str) -> dict:
    if not YTDLP:
        raise Exception("yt-dlp is not installed on this server")
    cmd = [YTDLP]
    # Cookies are optional: the file only exists if the operator exported
    # their YouTube cookies. Passing --cookies for a missing file makes
    # yt-dlp fail before it even contacts YouTube.
    if os.path.isfile(COOKIES):
        cmd += ["--cookies", COOKIES]
    cmd += ["--js-runtimes", "node",
           "-f", f"best[height<={quality}][ext=mp4]/best[ext=mp4]/best",
           "--dump-json", "--no-playlist", "--quiet", url]
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
    if proc.returncode != 0:
        raise Exception(stderr.decode().strip().split("\n")[-1])
    return json.loads(stdout.decode())

@router.get("/video")
@router.get("/video/")
async def get_video(
    url: str = Query(...),
    quality: str = Query("720"),
    current_user: User = Depends(AuthService.get_current_user),
) -> JSONResponse:
    """Resolve a YouTube URL to a direct stream URL.

    Requires ANY authenticated user (this used to be fully anonymous — a
    free, unthrottled yt-dlp runner for anyone on the internet). Extraction
    is additionally capped by a semaphore; a full slot answers 429 instead
    of queueing more subprocesses.
    """
    try:
        # Fast-fail when all extraction slots are busy, before doing any work.
        if _extraction_semaphore.locked():
            return JSONResponse(
                {"success": False, "error": "Extraction capacity reached, try again shortly"},
                status_code=429,
            )
        vid = get_video_id(url)
        if not vid:
            return JSONResponse({"success": False, "error": "Invalid URL"}, status_code=400)
        key = f"{vid}:{quality}"
        if key in cache and cache[key]["expires"] > time.time():
            return JSONResponse({"success": True, "data": {**cache[key], "cached": True}})
        # SSRF-safe: rebuild a canonical URL from the validated id, and hold
        # an extraction slot for the duration of the subprocess run.
        async with _extraction_semaphore:
            info = await extract(f"https://www.youtube.com/watch?v={vid}", quality)
        result = {"videoId": vid, "title": info.get("title"), "url": info.get("url"),
            "duration": info.get("duration"), "quality": f"{info.get('height','unknown')}p",
            "thumbnail": info.get("thumbnail"), "author": info.get("uploader"),
            "expires": time.time() + 14400, "cached": False}
        cache[key] = result
        return JSONResponse({"success": True, "data": result})
    except asyncio.TimeoutError:
        return JSONResponse({"success": False, "error": "Timed out"}, status_code=504)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/video/cache/status")
async def cache_status():
    active = {k: v for k, v in cache.items() if v["expires"] > time.time()}
    return JSONResponse({"success": True, "cache_size": len(active)})

# Alias for backward compatibility
extract_video_id = get_video_id
