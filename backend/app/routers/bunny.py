import httpx, os, hashlib, base64, time, logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.course import Lesson, Course
from app.models.enrollment import Enrollment
from app.services.auth_service import AuthService

router = APIRouter()
logger = logging.getLogger(__name__)

BUNNY_LIBRARY_ID = os.getenv("BUNNY_LIBRARY_ID", "618286")
BUNNY_API_KEY = os.getenv("BUNNY_API_KEY", "")
BUNNY_CDN_HOSTNAME = os.getenv("BUNNY_CDN_HOSTNAME", "vz-60dda74a-f32.b-cdn.net")
# Optional: Bunny Stream / Pull Zone Token Authentication key.
# When set, playback URLs are signed with a short-lived token so leaked GUIDs
# cannot be streamed indefinitely.
BUNNY_TOKEN_AUTH_KEY = os.getenv("BUNNY_TOKEN_AUTH_KEY", "")
# Signed URL validity window (seconds). Short-lived by default.
BUNNY_SIGNED_URL_TTL = int(os.getenv("BUNNY_SIGNED_URL_TTL", "3600"))


def _require_bunny_video_access(video_id: str, current_user: User, db: Session) -> None:
    """
    Enforce that `current_user` can stream the Bunny video identified by `video_id`.

    Resolve the owning Lesson by LIKE-matching the video GUID, then require an
    active Enrollment in the course. Admins and the course's instructor
    (post_author) bypass the check.

    The GUID is matched against BOTH `lesson_video_url` and `lesson_youtube_url`.
    Despite its name, `lesson_youtube_url` is where the admin/course editor
    actually stores Bunny iframe URLs (e.g.
    https://iframe.mediadelivery.net/play/<library>/<guid>) — matching only
    `lesson_video_url` meant every Bunny lesson 404'd here and played as a black
    frame, even for enrolled users.
    """
    if getattr(current_user, "role", None) == "admin":
        return

    lesson = db.query(Lesson).filter(
        or_(
            Lesson.lesson_video_url.like(f"%{video_id}%"),
            Lesson.lesson_youtube_url.like(f"%{video_id}%"),
        )
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Video not associated with any lesson")

    course_id = getattr(lesson, "post_parent", None)
    if not course_id:
        raise HTTPException(status_code=403, detail="Lesson has no course")

    if getattr(current_user, "role", None) == "instructor":
        course = db.query(Course).filter(Course.id == course_id).first()
        if course and getattr(course, "post_author", None) == current_user.id:
            return

    enrolled = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == course_id,
        Enrollment.enrollment_status == "enrolled",
    ).first()
    if not enrolled:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")


def _sign_bunny_url(url_path: str, ttl_seconds: int = None) -> str:
    """
    Build a Bunny CDN Token Authentication signed URL path+query.

    Bunny's algorithm (Pull Zone / Stream token auth):
        token = base64url( md5_binary( token_key + url_path + expiry_timestamp ) )
    with trailing `=` stripped and `+`/`/` replaced with `-`/`_`.

    Returns a "path?token=...&expires=..." suffix; caller prepends scheme+host.
    When BUNNY_TOKEN_AUTH_KEY is empty, returns the unsigned path and logs a
    warning so operators know signing is disabled.
    """
    if not BUNNY_TOKEN_AUTH_KEY:
        logger.warning(
            "BUNNY_TOKEN_AUTH_KEY is not configured; returning unsigned Bunny URL "
            "for %s. Playback is protected by auth+enrollment only.",
            url_path,
        )
        return url_path

    expires = int(time.time()) + (ttl_seconds or BUNNY_SIGNED_URL_TTL)
    # Bunny expects the path to start with '/'.
    path = url_path if url_path.startswith("/") else f"/{url_path}"
    raw = f"{BUNNY_TOKEN_AUTH_KEY}{path}{expires}".encode("utf-8")
    digest = hashlib.md5(raw).digest()
    token = base64.b64encode(digest).decode("ascii")
    token = token.replace("\n", "").rstrip("=").replace("+", "-").replace("/", "_")
    return f"{path}?token={token}&expires={expires}"


def _playback_url(video_id: str) -> str:
    """Return a (possibly signed) absolute HLS playback URL for this video."""
    signed = _sign_bunny_url(f"/{video_id}/playlist.m3u8")
    return f"https://{BUNNY_CDN_HOSTNAME}{signed}"


@router.post("/video")
async def upload_video_to_bunny(
    file: UploadFile = File(...),
    current_user=Depends(AuthService.get_current_user)
):
    """Upload video directly to Bunny Stream"""
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Only instructors can upload videos")

    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")

    try:
        # Step 1: Create video object in Bunny
        async with httpx.AsyncClient(timeout=30) as client:
            create_res = await client.post(
                f"https://video.bunnycdn.com/library/{BUNNY_LIBRARY_ID}/videos",
                headers={"AccessKey": BUNNY_API_KEY, "Content-Type": "application/json"},
                json={"title": file.filename or "Untitled"}
            )
            if create_res.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to create video on Bunny")
            video_data = create_res.json()
            video_id = video_data["guid"]

        # Step 2: Upload video content to Bunny
        video_content = await file.read()
        async with httpx.AsyncClient(timeout=300) as client:
            upload_res = await client.put(
                f"https://video.bunnycdn.com/library/{BUNNY_LIBRARY_ID}/videos/{video_id}",
                headers={"AccessKey": BUNNY_API_KEY, "Content-Type": "application/octet-stream"},
                content=video_content
            )
            if upload_res.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to upload video to Bunny")

        # Upload response: return the raw (unsigned) HLS URL so the uploader can
        # persist it as `lesson_video_url`. Playback endpoints are responsible
        # for signing/auth.
        hls_url = f"https://{BUNNY_CDN_HOSTNAME}/{video_id}/playlist.m3u8"
        thumbnail_url = f"https://{BUNNY_CDN_HOSTNAME}/{video_id}/thumbnail.jpg"

        return JSONResponse({
            "success": True,
            "video_id": video_id,
            "file_url": hls_url,
            "thumbnail_url": thumbnail_url,
            "hls_url": hls_url,
            "filename": file.filename,
            "original_filename": file.filename,
            "size": len(video_content),
            "content_type": file.content_type
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/{video_id}/status")
async def get_video_status(
    video_id: str,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Check Bunny video processing status. Requires auth + enrollment."""
    _require_bunny_video_access(video_id, current_user, db)

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.get(
            f"https://video.bunnycdn.com/library/{BUNNY_LIBRARY_ID}/videos/{video_id}",
            headers={"AccessKey": BUNNY_API_KEY}
        )
        data = res.json()
        # status 4 = ready, 3 = processing, 2 = queued
        return JSONResponse({
            "status": data.get("status"),
            "ready": data.get("status") == 4,
            "title": data.get("title"),
            "length": data.get("length"),
            "hls_url": _playback_url(video_id),
        })


def _is_preview_video(video_id: str, db: Session) -> bool:
    """
    True if `video_id` belongs to publicly-previewable content: a course's
    intro video, or a lesson explicitly flagged as a preview. Used to decide
    whether a signed URL can be issued without auth/enrollment.
    """
    course = db.query(Course).filter(
        Course.course_intro_video.like(f"%{video_id}%")
    ).first()
    if course:
        return True

    lesson = db.query(Lesson).filter(
        Lesson.lesson_video_url.like(f"%{video_id}%"),
        Lesson.lesson_preview.is_(True),
    ).first()
    return lesson is not None


@router.get("/video/{video_id}/preview-playback")
async def get_preview_playback_url(
    video_id: str,
    db: Session = Depends(get_db),
):
    """
    Return a (possibly signed) HLS playback URL for *preview* content only —
    course intro videos and lessons marked as preview. No auth/enrollment is
    required, so this endpoint only signs videos that are explicitly public
    previews; anything else is rejected.
    """
    if not _is_preview_video(video_id, db):
        raise HTTPException(status_code=403, detail="Video is not a public preview")
    return JSONResponse({
        "video_id": video_id,
        "hls_url": _playback_url(video_id),
        "expires_in": BUNNY_SIGNED_URL_TTL if BUNNY_TOKEN_AUTH_KEY else None,
        "signed": bool(BUNNY_TOKEN_AUTH_KEY),
    })


@router.get("/video/{video_id}/playback")
async def get_video_playback_url(
    video_id: str,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return a short-lived signed HLS playback URL for the Bunny video."""
    _require_bunny_video_access(video_id, current_user, db)
    return JSONResponse({
        "video_id": video_id,
        "hls_url": _playback_url(video_id),
        "expires_in": BUNNY_SIGNED_URL_TTL if BUNNY_TOKEN_AUTH_KEY else None,
        "signed": bool(BUNNY_TOKEN_AUTH_KEY),
    })
