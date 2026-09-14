"""
Video Embed URL Generator
Provides safe YouTube embed URLs with reduced branding
"""

import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter()

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

@router.get("", include_in_schema=True)
async def get_embed_url(
    url: str = Query(..., description="YouTube video URL"),
    controls: bool = Query(True, description="Show video controls"),
    autoplay: bool = Query(False, description="Auto-play video"),
    mute: bool = Query(True, description="Mute for auto-play compliance"),
    modestbranding: bool = Query(True, description="Use minimal YouTube branding"),
    rel: bool = Query(False, description="Show related videos"),
    showinfo: bool = Query(False, description="Show video information"),
    current_user: User = Depends(AuthService.get_current_active_user),
) -> JSONResponse:
    """
    Generate a safe YouTube embed URL with specified parameters.

    This endpoint creates embed URLs with reduced YouTube branding and
    optimized for educational platforms.
    """
    try:
        # Extract video ID from URL
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid YouTube URL format"
            )

        # Build embed URL with parameters
        embed_params = {
            'v': video_id,
            'modestbranding': 1 if modestbranding else 0,
            'rel': 1 if rel else 0,
            'showinfo': 1 if showinfo else 0,
            'controls': 1 if controls else 0,
            'autoplay': 1 if autoplay else 0,
            'mute': 1 if mute else 0,
            'playsinline': 1,  # Mobile compatibility
        }

        # Build URL string
        param_strings = [f"{k}={v}" for k, v in embed_params.items() if v]
        embed_url = f"https://www.youtube.com/embed/{video_id}?" + "&".join(param_strings)

        return JSONResponse(content={
            "success": True,
            "embed_url": embed_url,
            "video_id": video_id,
            "params": embed_params,
            "original_url": url
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embed URL: {str(e)}"
        )

@router.get("/embed", include_in_schema=False)
async def get_embed_url_legacy(
    url: str = Query(..., description="YouTube video URL"),
    controls: bool = Query(True, description="Show video controls"),
    autoplay: bool = Query(False, description="Auto-play video"),
    mute: bool = Query(True, description="Mute for auto-play compliance"),
    modestbranding: bool = Query(True, description="Use minimal YouTube branding"),
    rel: bool = Query(False, description="Show related videos"),
    showinfo: bool = Query(False, description="Show video information")
) -> JSONResponse:
    """
    Legacy endpoint with trailing slash (deprecated)
    """
    return await get_embed_url(
        url, controls, autoplay, mute, modestbranding, rel, showinfo
    )

@router.get("/validate")
async def validate_youtube_url(
    url: str = Query(..., description="URL to validate")
) -> JSONResponse:
    """
    Validate if a URL is a valid YouTube URL
    """
    try:
        video_id = extract_video_id(url)

        if video_id:
            return JSONResponse(content={
                "valid": True,
                "video_id": video_id,
                "is_youtube": True
            })
        else:
            return JSONResponse(content={
                "valid": False,
                "is_youtube": False,
                "error": "Not a valid YouTube URL"
            })

    except Exception as e:
        return JSONResponse(content={
            "valid": False,
            "is_youtube": False,
            "error": str(e)
        })

@router.get("/")
async def root():
    """API information"""
    return {
        "name": "Video Embed API",
        "version": "1.0.0",
        "description": "Safe YouTube embed URL generator with reduced branding",
        "endpoints": {
            "GET /embed": "Generate embed URL",
            "GET /validate": "Validate YouTube URL",
            "GET /": "API info"
        },
        "usage": "GET /embed?url=YOUR_YOUTUBE_URL"
    }