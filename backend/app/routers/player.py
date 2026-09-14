import time, httpx, asyncio, os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from jose import jwt

router = APIRouter()

_DEFAULT_VIDEO_SECRET = "sasha-video-secret-change-this"
VIDEO_SECRET = os.getenv("VIDEO_SECRET", _DEFAULT_VIDEO_SECRET)
TOKEN_TTL = 3600


def validate_video_secret(secret: str, environment: str) -> None:
    """Fail fast when the video-token signing secret is not production-grade.

    Anyone holding the well-known default (shipped in the repo) can mint
    stream tokens for any lesson, so running production on it means the
    enrollment gate on /token is decorative. Raise at import time — a
    container that starts with a guessable secret is worse than one that
    doesn't start. The default stays allowed in development/tests.
    """
    if environment != "production":
        return
    if not secret or secret == _DEFAULT_VIDEO_SECRET:
        raise RuntimeError(
            "VIDEO_SECRET is unset or still the repo default. Set a strong, "
            "unique VIDEO_SECRET in the production .env before starting the "
            "backend (ENVIRONMENT=production)."
        )


validate_video_secret(VIDEO_SECRET, os.getenv("ENVIRONMENT", "production"))

YTDLP = os.getenv("YTDLP_PATH", "yt-dlp")
COOKIES = os.getenv("YOUTUBE_COOKIES_PATH", "/app/youtube_cookies.txt")

url_cache = {}


def make_token(user_id: int, lesson_id: int) -> str:
    payload = {"uid": user_id, "lid": lesson_id, "exp": time.time() + TOKEN_TTL}
    return jwt.encode(payload, VIDEO_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, VIDEO_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid or expired video token")


async def get_stream_url(youtube_url: str) -> str:
    cmd = [YTDLP, "--cookies", COOKIES, "--js-runtimes", "node",
           "-f", "best[height<=720][ext=mp4]/best[ext=mp4]/best",
           "--get-url", "--no-playlist", "--quiet", youtube_url]
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail="Could not extract video URL")
    return stdout.decode().strip()


@router.get("/token")
async def get_video_token(
    lesson_id: int = Query(...),
    current_user=Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    # Enforce enrollment before minting a token. Without this any logged-in
    # user could mint a token for any lesson and stream paid content.
    # Lesson lives in app.models.course (there is no app.models.lesson).
    from app.models.course import Lesson
    from app.models.enrollment import Enrollment
    from app.models.course import Course

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    course_id = getattr(lesson, "post_parent", None)
    if not course_id:
        raise HTTPException(status_code=403, detail="Lesson has no course")

    if current_user.role != "admin":
        is_owning_instructor = False
        if current_user.role == "instructor":
            course = db.query(Course).filter(Course.id == course_id).first()
            is_owning_instructor = bool(
                course and getattr(course, "post_author", None) == current_user.id
            )

        if not is_owning_instructor:
            enrolled = db.query(Enrollment).filter(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == course_id,
                Enrollment.enrollment_status == "enrolled",
            ).first()
            if not enrolled:
                raise HTTPException(status_code=403, detail="Not enrolled in this course")

    token = make_token(current_user.id, lesson_id)
    return JSONResponse({"token": token, "expires_in": TOKEN_TTL})


@router.get("/stream-url")
async def get_stream_url_endpoint(
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    payload = verify_token(token)
    lesson_id = payload["lid"]

    from app.models.course import Lesson
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    # `lesson_video_url` is the real column (Lesson has no `video_url`
    # attribute — the old lookup raised AttributeError → 500 on every call).
    if not lesson or not lesson.lesson_video_url:
        raise HTTPException(status_code=404, detail="Lesson video not found")

    cached = url_cache.get(lesson_id)
    if cached and cached["expires"] > time.time():
        return JSONResponse({"url": cached["url"], "cached": True})

    stream_url = await get_stream_url(lesson.lesson_video_url)
    url_cache[lesson_id] = {"url": stream_url, "expires": time.time() + 14400}
    return JSONResponse({"url": stream_url, "cached": False})
