"""
File Upload Router - Handle image, video, and document uploads
Files are organized by user context (avatars, courses, blogs, certificates, etc.)
"""
import os
import uuid
import shutil
import json
from typing import List, Optional
from fastapi import BackgroundTasks, APIRouter, Depends, File, UploadFile, HTTPException, status, Query
from fastapi.responses import FileResponse
from pathlib import Path
from io import BytesIO
from PIL import Image
from sqlalchemy.orm import Session

from app.services.auth_service import AuthService
from app.models.user import User
from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter()

# Upload directory configuration
UPLOAD_DIR = Path(get_settings().UPLOAD_DIR)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg", "video/avi", "video/mov"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}

# Max file sizes (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB

# Server-side ceiling for /assignment-file (spec A1.8 + review finding I2):
# an instructor-controlled assignment.allowed_file_types list is untrusted
# input from the instructor's own browser — it must never be able to WIDEN
# what the upload endpoint accepts past this set. In particular html/htm/
# svg/js/mjs/xml are excluded even if an instructor configures them,
# because they execute same-origin under the public /uploads static mount
# (stored-XSS). The assignment's own list is always intersected with this
# set, never used on its own.
SAFE_ASSIGNMENT_EXTENSIONS = {
    "pdf", "doc", "docx", "txt", "rtf", "odt",
    "ppt", "pptx", "xls", "xlsx", "csv", "md", "zip",
    "png", "jpg", "jpeg",
}

# Per-extension content-type allowlist for /assignment-file, mirroring the
# double-check pattern /document already applies via ALLOWED_DOCUMENT_TYPES
# — the client-supplied filename extension and the client-supplied
# content_type must agree, or the upload is rejected. Browsers/clients that
# don't send a specific type (generic octet-stream) are allowed through
# only for extensions with no safer, more specific MIME type in common use.
_ASSIGNMENT_CONTENT_TYPES = {
    "pdf": {"application/pdf"},
    "doc": {"application/msword"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "txt": {"text/plain"},
    "rtf": {"application/rtf", "text/rtf"},
    "odt": {"application/vnd.oasis.opendocument.text"},
    "ppt": {"application/vnd.ms-powerpoint"},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    "xls": {"application/vnd.ms-excel"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "csv": {"text/csv", "application/vnd.ms-excel"},
    "md": {"text/markdown", "text/plain"},
    "zip": {"application/zip", "application/x-zip-compressed"},
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
}
# A generic/absent content_type is tolerated (many clients send this for
# non-image documents) but never for the extensions that most commonly
# masquerade as something else.
_GENERIC_CONTENT_TYPES = {"application/octet-stream", "", None}
_NEVER_GENERIC_EXTENSIONS = {"png", "jpg", "jpeg", "zip"}


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    return os.path.splitext(filename)[1].lower()


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename using UUID"""
    ext = get_file_extension(original_filename)
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


def validate_file_type(content_type: str, allowed_types: set) -> bool:
    """Validate file MIME type"""
    return content_type in allowed_types


def validate_file_size(file_size: int, max_size: int) -> bool:
    """Validate file size"""
    return file_size <= max_size


def optimize_image(image_data: bytes, max_size_kb: int = 300, max_width: int = 1200) -> bytes:
    """
    Optimize image for social media sharing.
    Resizes if needed and compresses to meet size limit.
    """
    img = Image.open(BytesIO(image_data))

    # Convert RGBA to RGB for JPEG compatibility
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background

    # Resize if width exceeds max_width
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    # Compress to meet size limit
    quality = 95
    output = BytesIO()

    while quality > 10:
        output.seek(0)
        output.truncate()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        size_kb = len(output.getvalue()) / 1024

        if size_kb <= max_size_kb:
            break
        quality -= 5

    return output.getvalue()


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    context: Optional[str] = Query(None, description="Upload context: avatar, blog, course, certificate, etc."),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Upload image file organized by context

    Contexts:
    - avatar: User profile photos (stored in avatars/{user_id}/)
    - blog: Blog featured images (stored in blogs/)
    - course: Course thumbnails (stored in courses/)
    - certificate: Certificate templates (stored in certificates/)
    - general: Default (stored in images/)
    """
    # Validate file type
    if not validate_file_type(file.content_type, ALLOWED_IMAGE_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

    # Read file content
    contents = await file.read()
    file_size = len(contents)

    # Validate file size
    if not validate_file_size(file_size, MAX_IMAGE_SIZE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_IMAGE_SIZE / (1024 * 1024)} MB"
        )

    # Verify the bytes are a real, decodable image. The client-supplied
    # content_type and filename are both untrusted — without this, an .html
    # payload sent as content_type=image/png would be stored under /uploads
    # and served as HTML (stored XSS). The saved extension is derived from the
    # format Pillow actually detects, never from the client filename.
    _IMG_FORMAT_EXT = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "WEBP": ".webp"}
    try:
        with Image.open(BytesIO(contents)) as probe:
            probe.verify()
            detected_format = probe.format
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupt image file",
        )
    safe_ext = _IMG_FORMAT_EXT.get(detected_format)
    if not safe_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format",
        )

    # Generate unique filename with a safe, format-derived extension
    unique_filename = f"{uuid.uuid4()}{safe_ext}"

    # Organize by context
    if context == "avatar":
        subfolder = f"avatars/{current_user.id}"
    elif context == "blog":
        subfolder = "blogs"
    elif context == "course":
        subfolder = "courses"
    elif context == "certificate":
        subfolder = "certificates"
    else:
        subfolder = "images"

    file_path = UPLOAD_DIR / subfolder / unique_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Optimize images for social media (blog, course contexts)
    if context in ('blog', 'course'):
        try:
            contents = optimize_image(contents, max_size_kb=300, max_width=1200)
            # Update extension to .jpg for optimized images
            unique_filename = unique_filename.rsplit('.', 1)[0] + '.jpg'
            file_path = UPLOAD_DIR / subfolder / unique_filename
        except Exception as e:
            print(f"Image optimization failed: {e}. Using original.")

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    # Return file URL
    file_url = f"/uploads/{subfolder}/{unique_filename}"
    return {
        "success": True,
        "file_url": file_url,
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": file_size,
        "content_type": file.content_type,
        "context": context
    }


def _build_audio_rendition(path: str) -> None:
    try:
        from app.services.media_pipeline import build_audio_rendition
        build_audio_rendition(path)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("audio rendition failed for %s", path)


@router.post("/video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Upload video file
    Only authenticated instructors and admins can upload videos
    """
    # Check if user is instructor or admin
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can upload videos"
        )

    # Validate file type
    if not validate_file_type(file.content_type, ALLOWED_VIDEO_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_VIDEO_TYPES)}"
        )

    # Generate unique filename first
    unique_filename = generate_unique_filename(file.filename)
    file_path = UPLOAD_DIR / "videos" / unique_filename

    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file in chunks to handle large files
    total_size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # Read 1MB at a time
            total_size += len(chunk)

            # Check size limit
            if total_size > MAX_VIDEO_SIZE:
                # Delete partial file
                os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large. Maximum size: {MAX_VIDEO_SIZE / (1024 * 1024)} MB"
                )

            f.write(chunk)

    # Roadmap item 9: audio-only rendition next to the video, in the background
    audio_status = "unavailable"
    try:
        from app.services import media_pipeline as mp
        if mp.ffmpeg_path() and background_tasks is not None:
            background_tasks.add_task(_build_audio_rendition, str(file_path))
            audio_status = "queued"
    except Exception:
        pass

    # Return file URL
    file_url = f"/uploads/videos/{unique_filename}"
    return {
        "success": True,
        "file_url": file_url,
        "audio_url": file_url.rsplit('.', 1)[0] + '.m4a',
        "audio_status": audio_status,
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": total_size,
        "content_type": file.content_type
    }


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    context: Optional[str] = Query(None, description="Upload context: resume, certificate, general"),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Upload document file organized by context

    Contexts:
    - resume: Student resumes (any authenticated user)
    - certificate: Certificate templates (instructors/admins only)
    - general: Default (instructors/admins only)
    """
    # Students can only upload resumes
    if context == "resume":
        # Allow all authenticated users to upload resumes
        pass
    elif current_user.role not in ["instructor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors and admins can upload documents (students can upload resumes)"
        )

    # Validate file type
    if not validate_file_type(file.content_type, ALLOWED_DOCUMENT_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: PDF, DOC, DOCX"
        )

    # Read file content
    contents = await file.read()
    file_size = len(contents)

    # Validate file size
    if not validate_file_size(file_size, MAX_DOCUMENT_SIZE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_DOCUMENT_SIZE / (1024 * 1024)} MB"
        )

    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename)

    # Organize by context
    if context == "certificate":
        subfolder = "certificates"
    else:
        subfolder = "documents"

    file_path = UPLOAD_DIR / subfolder / unique_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    # Return file URL
    file_url = f"/uploads/{subfolder}/{unique_filename}"
    return {
        "success": True,
        "file_url": file_url,
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": file_size,
        "content_type": file.content_type,
        "context": context
    }


def _assignment_upload_dir(assignment_id: int) -> Path:
    return UPLOAD_DIR / "assignments" / str(assignment_id)


def _user_file_prefix(user_id: int) -> str:
    """Filenames on disk are prefixed `u{user_id}_` so per-user file counts
    (review finding I1) and per-user ownership checks (review finding I4)
    can both be enforced by looking at the filesystem — the actual source
    of truth for what's uploaded — rather than trusting a submission row
    the client fully controls."""
    return f"u{user_id}_"


def _referenced_filenames(submission) -> set:
    """Filenames (not full URLs) referenced by a submission's `files` list.
    Mirrors assignments.py's `_file_url_of` shape — each entry may be a
    dict with file_url/filename/url, or a plain string URL."""
    if not submission or not submission.files:
        return set()
    files = submission.files
    if isinstance(files, str):
        try:
            files = json.loads(files) if files else []
        except (json.JSONDecodeError, TypeError):
            files = []
    names = set()
    for f in files or []:
        if isinstance(f, dict):
            url = str(f.get("file_url") or f.get("filename") or f.get("url") or "")
        else:
            url = str(f)
        if url:
            names.add(url.rsplit("/", 1)[-1])
    return names


def _reclaim_orphaned_user_files(db, assignment_id: int, user_id: int) -> int:
    """Delete this user's uploaded files for this assignment that are NOT
    referenced by their current live (non-RETURNED) submission, then
    return the remaining (post-cleanup) on-disk count. This is the
    "supersede" fix for the review's HIGH finding: without it, max_files
    counted every file the user ever uploaded and nothing ever reclaimed
    the budget — a RETURNED submission's old files, or files from
    uploads that were never submitted at all, sat on disk forever and
    permanently exhausted max_files.

    A submission counts as "live" (its files are protected from deletion)
    when it exists and its status is anything other than RETURNED
    (SUBMITTED and GRADED both still represent real, referenced work —
    review finding I4's guarantee: a file referenced by a submitted,
    non-RETURNED submission must never be deleted). When the submission
    is RETURNED or doesn't exist at all, every one of this user's files
    for this assignment is an orphan and is deleted, fully reclaiming the
    budget for a replacement upload.
    """
    from app.models.assignment import AssignmentSubmission, SubmissionStatus

    directory = _assignment_upload_dir(assignment_id)
    if not directory.is_dir():
        return 0

    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id,
        AssignmentSubmission.user_id == user_id,
    ).first()

    is_live = submission is not None and submission.status != SubmissionStatus.RETURNED
    protected_names = _referenced_filenames(submission) if is_live else set()

    prefix = _user_file_prefix(user_id)
    remaining = 0
    for p in directory.iterdir():
        if not p.is_file() or not p.name.startswith(prefix):
            continue
        if p.name in protected_names:
            remaining += 1
            continue
        try:
            p.unlink()
        except OSError:
            # Best-effort — a file that can't be removed (permissions,
            # already gone) still gets counted so max_files stays a safe
            # upper bound rather than under-reporting usage.
            remaining += 1

    return remaining


@router.post("/assignment-file")
async def upload_assignment_file(
    assignment_id: int = Query(..., description="Assignment this file is being submitted against"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    Upload a file destined for one assignment's submission. Enforces the
    ASSIGNMENT's own allowed_file_types / max_file_size / max_files
    (spec A1.8) — stricter than, and layered on top of, the global
    document rules (ALLOWED_DOCUMENT_TYPES/MAX_DOCUMENT_SIZE) enforced by
    `/document`. Requires the caller be enrolled in the assignment's
    course (or be the course owner/admin) — mirrors submit_assignment's
    guard (review finding C3: this endpoint previously had none). Stored
    under uploads/assignments/{assignment_id}/ with a UUID filename
    prefixed by the uploader's user id (review findings I1/I4 — enables
    counting/ownership checks against the filesystem, the actual source of
    truth, rather than a submission row the client fully controls).
    """
    from app.models.assignment import Assignment
    from app.models.course import Course
    from app.models.enrollment import Enrollment

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    # Enrollment / ownership check (review finding C3) — mirrors
    # submit_assignment's guard in app/routers/assignments.py exactly:
    # enrolled OR course owner OR admin.
    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    is_owner_or_admin = course is not None and (
        course.post_author == current_user.id or current_user.role == "admin"
    )
    if not is_owner_or_admin:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == assignment.course_id,
            Enrollment.user_id == current_user.id,
        ).first()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enrolled in this course"
            )

    # Extension allowlist (review finding I2): the assignment's own list is
    # UNTRUSTED instructor input and is always intersected with the
    # server-side SAFE_ASSIGNMENT_EXTENSIONS ceiling — it can only narrow,
    # never widen, what's accepted. An assignment with no restriction
    # configured gets the full safe set (not the old, narrower
    # pdf/doc/docx-only fallback).
    try:
        allowed_raw = assignment.allowed_file_types
        if isinstance(allowed_raw, str):
            allowed_raw = json.loads(allowed_raw) if allowed_raw else []
        assignment_exts = {str(t).lower().lstrip(".") for t in (allowed_raw or [])}
    except Exception:
        assignment_exts = set()

    allowed_exts = (
        (assignment_exts & SAFE_ASSIGNMENT_EXTENSIONS) if assignment_exts
        else set(SAFE_ASSIGNMENT_EXTENSIONS)
    )

    ext = get_file_extension(file.filename).lstrip(".").lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '.{ext}' not allowed for this assignment. Allowed: {sorted(allowed_exts)}"
        )

    # content_type must agree with the extension (review finding I2) — a
    # crafted request pairing a safe extension with an unrelated/dangerous
    # content_type (or vice versa) is rejected, same double-check pattern
    # /document applies via ALLOWED_DOCUMENT_TYPES.
    declared_type = (file.content_type or "").lower()
    expected_types = _ASSIGNMENT_CONTENT_TYPES.get(ext, set())
    type_ok = declared_type in expected_types
    if not type_ok and declared_type in _GENERIC_CONTENT_TYPES and ext not in _NEVER_GENERIC_EXTENSIONS:
        type_ok = True
    if not type_ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content-Type '{file.content_type}' does not match file extension '.{ext}'"
        )

    # Size cap: the stricter of the assignment's max_file_size (MB) and the
    # global MAX_DOCUMENT_SIZE.
    assignment_max_bytes = (assignment.max_file_size or 10) * 1024 * 1024
    max_bytes = min(assignment_max_bytes, MAX_DOCUMENT_SIZE)

    contents = await file.read()
    file_size = len(contents)
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size for this assignment: {max_bytes / (1024 * 1024):.1f} MB"
        )

    # Per-user file count against this assignment's max_files (review
    # finding I1, budget-reclaim fix for the follow-up HIGH finding):
    # count files this user ALREADY HAS ON DISK for this assignment
    # (identified by the u{user_id}_ filename prefix), not files recorded
    # on a submission row — a submission row may not exist yet pre-submit,
    # or may be stale/client-controlled, so it undercounted. Orphaned
    # files (not referenced by a current, non-RETURNED submission — i.e.
    # leftovers from an abandoned upload, or from a submission the
    # instructor RETURNED for changes) are deleted here BEFORE counting,
    # so a replacement upload reclaims the budget instead of hitting
    # max_files forever. Files referenced by a live (SUBMITTED/GRADED)
    # submission are never touched (review finding I4's guarantee).
    max_files = assignment.max_files or 5
    existing_count = _reclaim_orphaned_user_files(db, assignment_id, current_user.id)
    if existing_count + 1 > max_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files: max {max_files} allowed for this assignment (you have {existing_count})"
        )

    unique_filename = f"{_user_file_prefix(current_user.id)}{uuid.uuid4()}.{ext}" if ext else f"{_user_file_prefix(current_user.id)}{uuid.uuid4()}"
    file_path = _assignment_upload_dir(assignment_id) / unique_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/assignments/{assignment_id}/{unique_filename}"
    return {
        "success": True,
        "file_url": file_url,
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": file_size,
        "content_type": file.content_type,
        "assignment_id": assignment_id,
    }


@router.delete("/file")
async def delete_file(
    file_url: str,
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Delete uploaded file from local filesystem
    Only instructors and admins can delete files
    """
    # Check if user is admin or instructor
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

    # Extract file path from URL
    # URL format: /uploads/{subfolder}/filename.ext
    try:
        path_parts = file_url.strip("/").split("/")
        if len(path_parts) < 3 or path_parts[0] != "uploads":
            raise ValueError("Invalid file URL format")

        # Path could be uploads/avatars/123/filename.jpg or uploads/images/filename.jpg
        filename = path_parts[-1]
        subfolder = "/".join(path_parts[1:-1])  # Everything between uploads/ and filename

        # Resolve and confirm the target stays inside UPLOAD_DIR. Without this a
        # crafted URL like /uploads/../../etc/passwd would escape the upload
        # root (path traversal) and delete arbitrary files.
        upload_root = UPLOAD_DIR.resolve()
        file_path = (upload_root / subfolder / filename).resolve()
        if not file_path.is_relative_to(upload_root):
            raise ValueError("Invalid file path")

        # If the file is already gone, treat as idempotent success
        if not file_path.exists():
            return {
                "success": True,
                "message": "File already removed",
                "already_missing": True,
            }

        # Delete file
        os.remove(file_path)

        return {
            "success": True,
            "message": "File deleted successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/info")
async def get_upload_info(
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get upload configuration info
    """
    return {
        "max_image_size_mb": MAX_IMAGE_SIZE / (1024 * 1024),
        "max_video_size_mb": MAX_VIDEO_SIZE / (1024 * 1024),
        "max_document_size_mb": MAX_DOCUMENT_SIZE / (1024 * 1024),
        "allowed_image_types": list(ALLOWED_IMAGE_TYPES),
        "allowed_video_types": list(ALLOWED_VIDEO_TYPES),
        "allowed_document_types": list(ALLOWED_DOCUMENT_TYPES)
    }
