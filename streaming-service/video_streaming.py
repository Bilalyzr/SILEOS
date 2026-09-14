"""
YouTube Video Streaming Proxy Service
- Standalone service for streaming video server-side
- No YouTube branding on the frontend
- Supports unlisted videos via video ID
- Direct streaming with range request support
"""

import os
import re
import time
import yt_dlp
from typing import Dict, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from functools import lru_cache

app = FastAPI(
    title="SashaInfinity YouTube Streaming Service",
    description="Standalone YouTube video streaming proxy",
    version="1.0.0"
)

# CORS middleware for streaming service.
# Restrict to the SashaInfinity origins; override via STREAMING_ALLOWED_ORIGINS
# (comma-separated) if additional origins are ever needed.
_default_origins = [
    "https://sashainfinity.com",
    "https://www.sashainfinity.com",
]
_env_origins = os.getenv("STREAMING_ALLOWED_ORIGINS", "").strip()
ALLOWED_ORIGINS = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else _default_origins
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Simple in-memory cache: {video_id: (url, fetched_at)}
_url_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 60 * 10  # 10 minutes (YouTube URLs typically expire in ~6 hours but refresh often)

def extract_video_id(youtube_url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/shorts\/([^&\n?#]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            candidate = match.group(1)
            # Only accept a well-formed YouTube video id. This prevents SSRF:
            # a raw url is never handed to yt-dlp — callers rebuild a canonical
            # https://www.youtube.com/watch?v=<id> URL from this validated id.
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                return candidate
    return None

_VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")


def get_video_url(video_id: str) -> str:
    """Extract direct MP4 URL using yt-dlp (runs on the server, so IP matches)."""
    if not _VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError("Invalid video id")
    now = time.time()
    cached = _url_cache.get(video_id)
    if cached and (now - cached[1]) < CACHE_TTL:
        return cached[0]

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sashainfinity-youtube-streaming",
        "version": "1.0.0",
        "cache_size": len(_url_cache),
        "cache_hits": len([k for k, v in _url_cache.items() if time.time() - v[1] < CACHE_TTL])
    }

@app.get("/stream/{video_id}")
async def stream_video(video_id: str, request: Request):
    """
    Proxy-stream the YouTube video through your server.
    Supports HTTP Range requests for seeking.
    """
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

@app.get("/info/{video_id}")
async def video_info(video_id: str):
    """Get video title and thumbnail (for your frontend player UI)."""
    if not _VIDEO_ID_RE.fullmatch(video_id):
        raise HTTPException(status_code=400, detail="Invalid video id")
    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
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

@app.get("/extract")
async def extract_video_url(
    url: str = Query(..., description="YouTube video URL"),
    quality: str = Query("720", description="Video quality (max height)")
) -> JSONResponse:
    """
    Enhanced video extraction with better error handling and caching
    """
    try:
        video_id = extract_video_id(url)
        if not video_id:
            return JSONResponse(content={"success": False, "error": "Invalid YouTube URL"}, status_code=400)

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

        # Extract video info
        ydl_opts = {
            "format": f"best[height<={quality}][ext=mp4]/best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
        }

        # SSRF-safe: rebuild a canonical URL from the validated video_id rather
        # than passing the raw, attacker-controlled `url` to yt-dlp.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )

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

@app.get("/cache/status")
async def get_cache_status() -> JSONResponse:
    """Get current cache status"""
    now = time.time()
    active = {k: v for k, v in _url_cache.items() if v[1] > now}
    return JSONResponse(content={
        "success": True,
        "cache_size": len(active),
        "cached_videos": list(active.keys()),
        "total_cache_entries": len(_url_cache)
    })

@app.get("/")
async def root():
    return {
        "status": "ok",
        "usage": "GET /stream/{youtube_video_id} or GET /info/{youtube_video_id}",
        "cache_info": f"Active entries: {len([k for k, v in _url_cache.items() if time.time() - v[1] < CACHE_TTL])}",
        "service": "SashaInfinity YouTube Streaming"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)