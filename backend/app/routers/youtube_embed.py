from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
from datetime import datetime

from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter()

class VideoRequest(BaseModel):
    video_id: str
    title: str
    description: Optional[str] = None
    course_id: Optional[str] = None
    lesson_id: Optional[str] = None
    custom_thumbnail: Optional[str] = None
    duration: Optional[str] = None
    order: int = 0

class VideoResponse(BaseModel):
    video_id: str
    title: str
    description: Optional[str]
    duration: Optional[str]
    thumbnail_url: str
    embed_url: str
    is_valid: bool
    created_at: datetime

class VideoAnalytics(BaseModel):
    video_id: str
    course_id: Optional[str]
    lesson_id: Optional[str]
    user_id: str
    user_role: str
    timestamp: datetime
    event_type: str  # 'play', 'pause', 'complete', 'error'
    current_time: Optional[float] = None
    duration: Optional[float] = None

# Cache for video validation
video_cache = {}

@router.post("/validate-youtube-video", response_model=VideoResponse)
async def validate_youtube_video(
    request: VideoRequest,
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Validate YouTube video ID and return embed information"""

    # Check cache first
    cache_key = f"video_{request.video_id}"
    if cache_key in video_cache:
        return video_cache[cache_key]

    # Validate video ID format
    if not request.video_id or len(request.video_id) < 11:
        raise HTTPException(status_code=400, detail="Invalid YouTube video ID format")

    try:
        # Use YouTube oEmbed API to validate video
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://www.youtube.com/oembed",
                params={
                    "url": f"https://www.youtube.com/watch?v={request.video_id}",
                    "format": "json"
                }
            )

            if response.status_code == 200:
                oembed_data = response.json()

                video_info = VideoResponse(
                    video_id=request.video_id,
                    title=oembed_data.get("title", request.title),
                    description=request.description,
                    duration=request.duration,
                    thumbnail_url=f"https://img.youtube.com/vi/{request.video_id}/maxresdefault.jpg",
                    embed_url=f"https://www.youtube.com/embed/{request.video_id}",
                    is_valid=True,
                    created_at=datetime.now()
                )

                # Cache the result
                video_cache[cache_key] = video_info

                return video_info
            else:
                raise HTTPException(status_code=404, detail="Video not found or invalid")

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Video validation timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating video: {str(e)}")

@router.get("/video-thumbnail/{video_id}")
async def get_video_thumbnail(video_id: str):
    """Get video thumbnail URL with fallbacks"""

    thumbnail_sizes = [
        "maxresdefault.jpg",  # Highest quality
        "hqdefault.jpg",     # High quality
        "mqdefault.jpg",     # Medium quality
        "sddefault.jpg"      # Low quality
    ]

    thumbnail_urls = []

    for size in thumbnail_sizes:
        url = f"https://img.youtube.com/vi/{video_id}/{size}"
        thumbnail_urls.append(url)

    return {
        "video_id": video_id,
        "thumbnail_urls": thumbnail_urls,
        "recommended": thumbnail_urls[0]  # Return highest quality first
    }

@router.post("/analytics/video-play")
async def track_video_play(
    analytics: VideoAnalytics,
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Track video play events for analytics"""

    try:
        # Store analytics data
        print(f"Tracking video play: {analytics}")

        # Here you would save to your database
        # Example: await db.video_analytics.insert_one(analytics.dict())

        return {"status": "success", "message": "Analytics tracked"}

    except Exception as e:
        print(f"Error tracking analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to track analytics")

@router.get("/course-videos/{course_id}")
async def get_course_videos(course_id: str):
    """Get all videos for a specific course"""

    # This would typically fetch from your database
    # For now, return example data
    return {
        "course_id": course_id,
        "videos": [
            {
                "lesson_id": "lesson-1",
                "video_id": "dQw4w9WgXcQ",
                "title": "Introduction to Web Development",
                "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                "duration": "15:30",
                "order": 1
            }
        ]
    }

@router.get("/video-info/{video_id}")
async def get_video_info(video_id: str):
    """Get detailed information about a video"""

    try:
        # Get oEmbed data
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://www.youtube.com/oembed",
                params={
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "format": "json"
                }
            )

            if response.status_code == 200:
                oembed_data = response.json()

                # Generate additional embed URL with parameters
                embed_params = {
                    "autoplay": "0",
                    "controls": "1",
                    "rel": "0",
                    "playsinline": "1",
                    "enablejsapi": "1"
                }

                return {
                    "video_id": video_id,
                    "title": oembed_data.get("title"),
                    "author_name": oembed_data.get("author_name"),
                    "author_url": oembed_data.get("author_url"),
                    "thumbnail_url": oembed_data.get("thumbnail_url"),
                    "thumbnail_width": oembed_data.get("thumbnail_width"),
                    "thumbnail_height": oembed_data.get("thumbnail_height"),
                    "embed_url": f"https://www.youtube.com/embed/{video_id}?" + "&".join([f"{k}={v}" for k, v in embed_params.items()]),
                    "html": oembed_data.get("html"),
                    "provider_name": oembed_data.get("provider_name"),
                    "provider_url": oembed_data.get("provider_url"),
                    "video_duration": oembed_data.get("duration")
                }
            else:
                raise HTTPException(status_code=404, detail="Video not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting video info: {str(e)}")

@router.get("/embed-parameters")
async def get_embed_parameters():
    """Get recommended embed parameters for minimal branding"""

    return {
        "parameters": {
            "controls": "0",
            "rel": "0",
            "playsinline": "1",
            "enablejsapi": "1",
            "autoplay": "0"
        },
        "description": "Recommended parameters for minimal YouTube branding",
        "csp_compatible": True
    }

@router.post("/bulk-validate-videos")
async def bulk_validate_videos(
    videos: List[VideoRequest],
    current_user: User = Depends(AuthService.get_current_user),
):
    """Bulk validate multiple YouTube videos (authenticated; batch-capped).

    Each entry triggers an outbound YouTube request, so leaving this open let an
    anonymous caller amplify one request into many. Require auth and cap the
    batch size.
    """
    if len(videos) > 50:
        raise HTTPException(
            status_code=400,
            detail="Too many videos in one request (max 50).",
        )

    results = []
    for video_request in videos:
        try:
            # Validate single video
            result = await validate_youtube_video(video_request)
            results.append({
                "video_id": video_request.video_id,
                "status": "success",
                "data": result
            })
        except Exception as e:
            results.append({
                "video_id": video_request.video_id,
                "status": "error",
                "error": str(e)
            })

    return {"results": results}