"""
YouTube Video Streaming Proxy
- Streams video server-side to avoid IP/token expiry issues
- No YouTube branding on the frontend
- Supports unlisted videos via video ID
- Direct streaming with range request support
"""

import os
import re
import time
import yt_dlp
from typing import Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import StreamingResponse, JSONResponse


def _cookiefile_opts() -> dict:
    """yt-dlp opts enabling the exported YouTube cookie jar when present.

    YouTube serves "Sign in to confirm you're not a bot" (and a gutted format
    list that then fails format selection with 'Requested format is not
    available') to datacenter IPs making unauthenticated extraction requests.
    The exported cookie file shipped beside the app restores access; without
    it extraction still works from clean residential IPs, so absence is not
    fatal — the option is only added when the file exists.
    """
    path = "/app/youtube_cookies.txt"
    return {"cookiefile": path} if os.path.exists(path) else {}
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_
from sqlalchemy.orm import Session
import httpx
import asyncio
from functools import lru_cache

from app.core.database import get_db
from app.models.user import User
from app.models.course import Lesson
from app.models.enrollment import Enrollment
from app.services.auth_service import AuthService

router = APIRouter()


def _require_video_access(video_id: str, current_user: User, db: Session) -> None:
    """
    Enforce that `current_user` can stream `video_id`.

    Resolves the lesson by LIKE-matching the video id against BOTH
    `lesson_video_url` and `lesson_youtube_url`, then checks for an active
    enrollment in the owning course. Admins and the course's instructor bypass
    the enrollment check.

    Both columns are searched because the course editor stores video URLs in
    `lesson_youtube_url` (regardless of the actual provider), leaving
    `lesson_video_url` empty — matching only the latter made every such lesson
    404 here even for enrolled users.
    """
    if not _YOUTUBE_ID_RE.fullmatch(video_id):
        raise HTTPException(status_code=400, detail="Invalid video id")
    if current_user.role in ("admin", "superadmin"):
        return

    # `contains(..., autoescape=True)` is deliberate: `_` is valid inside a
    # YouTube id but is a wildcard in SQL LIKE. The old `%{video_id}%` query
    # could authorize the wrong lesson for ids containing an underscore.
    lessons = db.query(Lesson).filter(
        or_(
            Lesson.lesson_video_url.contains(video_id, autoescape=True),
            Lesson.lesson_youtube_url.contains(video_id, autoescape=True),
        )
    ).all()
    if not lessons:
        raise HTTPException(status_code=404, detail="Video not associated with any lesson")

    course_ids = {getattr(lesson, "post_parent", None) for lesson in lessons}
    course_ids.discard(None)
    if not course_ids:
        raise HTTPException(status_code=403, detail="Video lessons have no course")
    from app.models.course import Course
    from app.services.course_access import can_edit
    if current_user.role == "instructor":
        for course in db.query(Course).filter(Course.id.in_(course_ids)).all():
            if can_edit(db, course, current_user):
                return
    enrolled = db.query(Enrollment.id).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id.in_(course_ids),
        Enrollment.enrollment_status.in_(("enrolled", "active", "completed")),
    ).first()
    if not enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

# Simple in-memory cache: {video_id: (url, fetched_at)}
_url_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 60 * 10  # 10 minutes (YouTube URLs typically expire in ~6 hours but refresh often)

def extract_video_id(youtube_url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/shorts/([^&\n?#]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None


# A YouTube id is exactly 11 chars of this alphabet — anything else means the
# "id" is actually path/userinfo junk from a crafted URL.
_YOUTUBE_ID_RE = re.compile(r'[A-Za-z0-9_-]{11}')

# Quality values we will interpolate into the yt-dlp format selector.
ALLOWED_EXTRACT_QUALITIES = {"360", "480", "720", "1080", "1440"}


def canonical_youtube_watch_url(youtube_url: str) -> str:
    """Validate a user-supplied "YouTube URL" and rebuild the canonical watch URL.

    extract_video_id only pattern-matches ANYWHERE in the string, so inputs
    like ``http://evil.com/proxy?u=https://youtube.com/watch?v=abc`` pass it
    while naming a host we never intended to visit (SSRF via yt-dlp's generic
    extractor). Here the extracted id must fullmatch the strict 11-char
    alphabet, and the REBUILT canonical URL — never the raw input — is what
    the caller hands to yt-dlp.

    Raises ValueError when the URL/extracted id is not acceptable.
    """
    video_id = extract_video_id(youtube_url)
    if not video_id or not _YOUTUBE_ID_RE.fullmatch(video_id):
        raise ValueError("Invalid YouTube URL")
    return f"https://www.youtube.com/watch?v={video_id}"


def validate_extract_quality(quality: str) -> str:
    """Allowlist the quality interpolated into the yt-dlp ``-f`` selector.

    The raw query param used to be interpolated unchecked, letting a caller
    inject format-selector syntax. Only known heights pass; the value is
    returned as a plain string safe to interpolate.
    """
    q = str(quality).strip()
    if q not in ALLOWED_EXTRACT_QUALITIES:
        raise ValueError("Invalid quality")
    return q

def get_video_url(video_id: str) -> str:
    """Extract direct MP4 URL using yt-dlp (runs on the server, so IP matches)."""
    now = time.time()
    cached = _url_cache.get(video_id)
    if cached and (now - cached[1]) < CACHE_TTL:
        return cached[0]

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        **_cookiefile_opts(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}",
            download=False
        )

    # Prefer a single progressive MP4 URL
    url = None
    formats = info.get("formats", [])

    # Try to find best single-file progressive MP4
    progressive = [
        f for f in formats
        if f.get("ext") == "mp4"
        and f.get("acodec") != "none"
        and f.get("vcodec") != "none"
        and f.get("url")
    ]

    if progressive:
        best = max(progressive, key=lambda f: f.get("height", 0))
        url = best["url"]
    elif info.get("url"):
        url = info["url"]
    else:
        raise ValueError("Could not extract a streamable URL")

    _url_cache[video_id] = (url, now)
    return url

@router.get("/stream/{video_id}")
async def stream_video(
    video_id: str,
    request: Request,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Proxy-stream the YouTube video through your server.
    Supports HTTP Range requests for seeking.
    Requires the caller to be enrolled in the course owning this video.
    """
    _require_video_access(video_id, current_user, db)
    try:
        direct_url = get_video_url(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video URL: {e}")

    range_header = request.headers.get("Range")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.youtube.com/",
    }
    if range_header:
        headers["Range"] = range_header

    async def stream():
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            async with client.stream("GET", direct_url, headers=headers) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=1024 * 64):  # 64KB chunks
                    yield chunk

    # Pass through range/content headers from YouTube
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        head = await client.head(direct_url, headers=headers)

    response_headers = {
        "Content-Type": head.headers.get("Content-Type", "video/mp4"),
        "Accept-Ranges": "bytes",
    }
    if "Content-Length" in head.headers:
        response_headers["Content-Length"] = head.headers["Content-Length"]
    if "Content-Range" in head.headers:
        response_headers["Content-Range"] = head.headers["Content-Range"]

    status = 206 if range_header else 200
    return StreamingResponse(stream(), status_code=status, headers=response_headers)

@router.get("/info/{video_id}")
async def video_info(
    video_id: str,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get video title and thumbnail (for your frontend player UI)."""
    _require_video_access(video_id, current_user, db)
    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True, **_cookiefile_opts()}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=False
            )
        return {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "description": info.get("description", "")[:300],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/extract")
async def extract_video_url(
    url: str = Query(..., description="YouTube video URL"),
    quality: str = Query("720", description="Video quality (max height)"),
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Enhanced video extraction with better error handling and caching
    """
    try:
        # SSRF gate: validate the URL strictly and rebuild the canonical
        # watch URL from the extracted id — the raw `url` query param must
        # never reach yt-dlp.
        try:
            canonical_url = canonical_youtube_watch_url(url)
            video_id = extract_video_id(canonical_url)
        except ValueError:
            return JSONResponse(content={"success": False, "error": "Invalid YouTube URL"}, status_code=400)

        # Quality is interpolated into the format selector — allowlist it.
        try:
            quality = validate_extract_quality(quality)
        except ValueError:
            return JSONResponse(
                content={"success": False, "error": "Invalid quality"},
                status_code=400,
            )

        _require_video_access(video_id, current_user, db)

        cache_key = f"{video_id}:{quality}"
        now = time.time()

        # Check cache
        if cache_key in _url_cache:
            cached_data = _url_cache[cache_key]
            if now - cached_data[1] < CACHE_TTL:
                return JSONResponse(content={
                    "success": True,
                    "data": {
                        "url": cached_data[0],
                        "title": "Cached Video",
                        "duration": None,
                        "quality": f"{quality}p",
                        "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                        "expires": cached_data[1] + CACHE_TTL
                    }
                })

        # Extract video info — always from the REBUILT canonical URL.
        ydl_opts = {
            "format": f"best[height<={quality}][ext=mp4]/best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            **_cookiefile_opts(),
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(canonical_url, download=False)

        # Store in cache
        _url_cache[cache_key] = (info.get('url'), now)

        return JSONResponse(content={
            "success": True,
            "data": {
                "videoId": video_id,
                "title": info.get('title'),
                "url": info.get('url'),
                "duration": info.get('duration'),
                "quality": f"{info.get('height', quality)}p",
                "thumbnail": info.get('thumbnail'),
                "author": info.get('uploader'),
                "expires": now + CACHE_TTL,
                "cached": False
            }
        })

    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@router.get("/cache/status")
async def get_cache_status(
    current_user: User = Depends(AuthService.require_admin),
) -> JSONResponse:
    """Get current cache status (admin only — leaks resolved video URLs)."""
    now = time.time()
    active = {k: v for k, v in _url_cache.items() if (now - v[1]) < CACHE_TTL}
    return JSONResponse(content={
        "success": True,
        "cache_size": len(active),
        "cached_videos": list(active.keys()),
        "total_cache_entries": len(_url_cache)
    })

@router.get("/")
async def root():
    return {
        "status": "ok",
        "usage": "GET /stream/{youtube_video_id} or GET /info/{youtube_video_id}",
        "cache_info": f"Active entries: {len([k for k, v in _url_cache.items() if time.time() - v[1] < CACHE_TTL])}"
    }
