"""
Chunked Upload Router
Handles large file uploads by splitting them into chunks.

Session metadata is persisted in Redis (key: chunked_upload:session:{upload_id})
so that multi-worker uvicorn deployments route every chunk correctly and
abandoned uploads auto-expire via TTL. Chunk files remain on disk.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional, Any, Dict
import os
import shutil
import logging
from pathlib import Path
import uuid
import json
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.redis import get_redis
from app.services.auth_service import AuthService
from app.models.user import User
from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Redis key scheme and TTL for session metadata.
SESSION_KEY_PREFIX = "chunked_upload:session:"
SESSION_TTL_SECONDS = 24 * 60 * 60  # 24 hours; TTL replaces the old /init cleanup sweep

# ---------------------------------------------------------------------------
# Per-type file whitelists (mirror uploads.py's ALLOWED_*_TYPES).
#
# /complete used to assemble whatever filename/extension the client declared
# at /init and store it under /uploads (served straight back by nginx) — an
# upload_type=image session with evil.html produced a stored-XSS landing
# page. Both the extension AND the declared content_type must belong to the
# session's upload_type, enforced at /init (fail fast) and again at
# /complete (authoritative — the session could have been crafted).
# ---------------------------------------------------------------------------
CHUNKED_UPLOAD_RULES: Dict[str, Dict[str, set]] = {
    "image": {
        "extensions": {".jpg", ".jpeg", ".png", ".gif", ".webp"},
        "content_types": {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"},
    },
    "video": {
        "extensions": {".mp4", ".webm", ".ogg", ".avi", ".mov"},
        "content_types": {"video/mp4", "video/webm", "video/ogg", "video/avi", "video/mov"},
    },
    "document": {
        "extensions": {".pdf", ".doc", ".docx"},
        "content_types": {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
    },
    # H5P packages are zip archives (the .h5p extension is just a renamed
    # .zip). This whitelist only gates what /complete will assemble and
    # write to disk as an opaque, UNVALIDATED blob under _h5p_temp_dir()
    # (a sibling of UPLOAD_DIR, outside every static mount — see that
    # function's docstring) — it is NOT the security boundary for H5P
    # content. The actual package (path
    # traversal, symlinks, per-file/total size, extension allowlist INSIDE
    # the archive, zip-bomb guard) is validated by
    # app.services.h5p_service.validate_and_extract, called from
    # app.routers.h5p's /finalize endpoint against the file this router
    # assembles. Browsers/clients send varying content-types for zip-like
    # files (some omit it or send octet-stream), so the whitelist here is
    # intentionally permissive on content_type and strict only on extension.
    "h5p": {
        "extensions": {".h5p", ".zip"},
        "content_types": {
            "application/zip",
            "application/x-zip-compressed",
            "application/octet-stream",
        },
    },
}


def _validate_upload_type_file(upload_type: str, filename: str, content_type: str) -> None:
    """Raise 400 unless the (extension, content_type) pair is legal for the
    declared upload_type. Raises 400 for an unknown upload_type as well."""
    rules = CHUNKED_UPLOAD_RULES.get(upload_type)
    if not rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload type",
        )
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in rules["extensions"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid file extension '{ext}' for upload_type={upload_type}. "
                f"Allowed: {', '.join(sorted(rules['extensions']))}"
            ),
        )
    if (content_type or "").split(";")[0].strip().lower() not in rules["content_types"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type for upload_type={upload_type}",
        )


def _session_key(upload_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{upload_id}"


def _upload_dir() -> str:
    return getattr(settings, "UPLOAD_DIR", "/app/uploads")


def _h5p_temp_dir() -> Path:
    """Assembly directory for h5p-type chunked uploads. Deliberately a
    SIBLING of UPLOAD_DIR, not a subdirectory of it — UPLOAD_DIR is the
    directory main.py mounts at /uploads via StaticFiles (nginx serves the
    same bind mount unauthenticated in production), so anything placed
    under UPLOAD_DIR is servable to anyone who can guess/observe its path.
    An assembled h5p blob here is an UNVALIDATED raw upload — it must not
    be reachable until app.routers.h5p's /finalize has run it through
    h5p_service.validate_and_extract. Putting it outside the static root
    entirely removes the question of whether some future refactor of the
    static mount config could accidentally start serving it.
    """
    return Path(_upload_dir()).parent / "h5p_temp"


def _temp_dir_for(upload_id: str) -> Path:
    return Path(_upload_dir()) / "temp" / upload_id


def _chunk_path(upload_id: str, chunk_number: int) -> Path:
    return _temp_dir_for(upload_id) / f"chunk_{chunk_number:05d}"


def _cleanup_temp_dir(upload_id: str) -> None:
    temp_dir = _temp_dir_for(upload_id)
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


async def _redis():
    """
    Get the async Redis client, failing fast with 503 if unavailable.

    We deliberately do NOT fall back to in-memory storage — that defeats
    the whole point of moving session state off-process.
    """
    try:
        client = await get_redis()
        # Probe the connection; if it's the real client this round-trips,
        # if it's the mock it just returns b"PONG".
        await client.ping()
        return client
    except Exception as e:
        logger.error("Redis unavailable for chunked upload: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload service temporarily unavailable (session store offline)",
        )


async def _load_session(client, upload_id: str) -> Optional[Dict[str, Any]]:
    raw = await client.get(_session_key(upload_id))
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        logger.error("Corrupt chunked-upload session payload for %s", upload_id)
        return None


async def _save_session(
    client,
    upload_id: str,
    data: Dict[str, Any],
    *,
    new: bool = False,
) -> None:
    """
    Persist session JSON. On create we set the 24h TTL; on update we
    preserve it (SET with KEEPTTL semantics via a separate helper).
    """
    payload = json.dumps(data)
    key = _session_key(upload_id)
    if new:
        await client.setex(key, SESSION_TTL_SECONDS, payload)
        return
    # Preserve remaining TTL on updates. Try KEEPTTL; fall back to pipeline
    # that reads ttl and re-applies it (works against mock + old redis-py).
    try:
        await client.set(key, payload, keepttl=True)
    except TypeError:
        # Older redis client or mock without keepttl kwarg
        try:
            ttl = await client.ttl(key)
        except Exception:
            ttl = SESSION_TTL_SECONDS
        if not isinstance(ttl, int) or ttl <= 0:
            ttl = SESSION_TTL_SECONDS
        await client.setex(key, ttl, payload)


async def _delete_session(client, upload_id: str) -> None:
    await client.delete(_session_key(upload_id))


@router.post("/init")
async def initialize_chunked_upload(
    filename: str = Form(...),
    file_size: int = Form(...),
    content_type: str = Form(...),
    total_chunks: int = Form(...),
    upload_type: str = Form(...),  # 'image', 'video', or 'document'
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initialize a chunked upload session.
    """
    # Role guard: only instructors / admins may start an upload
    if getattr(current_user, "role", None) not in ("instructor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors or admins may upload files",
        )

    # Validate upload type
    if upload_type not in ("image", "video", "document", "h5p"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload type",
        )

    # Fail fast on disallowed extension/content_type for this upload_type
    # (authoritatively re-checked at /complete).
    _validate_upload_type_file(upload_type, filename, content_type)

    # Validate file size limits
    max_sizes = {
        "image": getattr(settings, "MAX_IMAGE_SIZE_MB", 10) * 1024 * 1024,
        "video": getattr(settings, "MAX_VIDEO_SIZE_MB", 500) * 1024 * 1024,
        "document": getattr(settings, "MAX_DOCUMENT_SIZE_MB", 50) * 1024 * 1024,
        # Spec B4 / plan Task 4 item 4: 100MB cap for chunked H5P uploads.
        "h5p": 100 * 1024 * 1024,
    }
    if file_size > max_sizes.get(upload_type, 10 * 1024 * 1024):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed for {upload_type}",
        )

    client = await _redis()

    upload_id = str(uuid.uuid4())
    temp_dir = _temp_dir_for(upload_id)
    temp_dir.mkdir(parents=True, exist_ok=True)

    session_data: Dict[str, Any] = {
        "upload_id": upload_id,
        "filename": filename,
        "file_size": file_size,
        "content_type": content_type,
        "total_chunks": total_chunks,
        "upload_type": upload_type,
        "user_id": current_user.id,
        "received_chunks": [],
        "temp_dir": str(temp_dir),
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        await _save_session(client, upload_id, session_data, new=True)
    except Exception as e:
        # Roll back the temp dir we just created so we don't leak empty dirs
        _cleanup_temp_dir(upload_id)
        logger.error("Failed to persist upload session %s: %s", upload_id, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload service temporarily unavailable (session store offline)",
        )

    return {
        "upload_id": upload_id,
        "message": "Upload session initialized",
    }


@router.post("/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    chunk: UploadFile = File(...),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    Upload a single chunk.
    """
    client = await _redis()
    session = await _load_session(client, upload_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found or expired",
        )

    # Verify user
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this upload",
        )

    # Verify chunk number
    if chunk_number < 0 or chunk_number >= total_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chunk number",
        )

    # Save chunk to temp file
    chunk_path = _chunk_path(upload_id, chunk_number)
    chunk_path.parent.mkdir(parents=True, exist_ok=True)
    with chunk_path.open("wb") as buffer:
        shutil.copyfileobj(chunk.file, buffer)

    # Cumulative-bytes enforcement: the bytes on disk for this upload may
    # never exceed the file_size declared at /init. Without this a client
    # could declare a tiny file_size (passing the size-limit check) and then
    # stream unbounded chunks — /complete's equality check would only reject
    # it after the disk had already absorbed the full payload.
    total_on_disk = sum(
        p.stat().st_size for p in chunk_path.parent.glob("chunk_*") if p.is_file()
    )
    if total_on_disk > int(session["file_size"]):
        try:
            chunk_path.unlink(missing_ok=True)
        except Exception:
            logger.exception("Failed to roll back overshooting chunk %s", chunk_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Chunk exceeds declared file size: {total_on_disk} bytes received "
                f"of {session['file_size']} declared"
            ),
        )

    # Update received-chunks list in Redis. If the Redis write fails after
    # the chunk hit disk, roll back the chunk file so client can safely retry.
    received = set(session.get("received_chunks", []))
    received.add(chunk_number)
    session["received_chunks"] = sorted(received)

    try:
        await _save_session(client, upload_id, session, new=False)
    except Exception as e:
        logger.error(
            "Chunk write succeeded but Redis update failed for %s chunk %s: %s — rolling back chunk file",
            upload_id,
            chunk_number,
            e,
        )
        try:
            if chunk_path.exists():
                chunk_path.unlink()
        except Exception:
            logger.exception("Failed to roll back chunk file %s", chunk_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload service temporarily unavailable (session store offline)",
        )

    return {
        "chunk_id": f"{upload_id}_{chunk_number}",
        "chunk_number": chunk_number,
        "received": True,
        "total_received": len(session["received_chunks"]),
        "total_chunks": session["total_chunks"],
    }


@router.post("/complete")
async def complete_chunked_upload(
    upload_id: str = Form(...),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    Complete upload and assemble chunks into final file.
    """
    client = await _redis()
    session = await _load_session(client, upload_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found",
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this upload",
        )

    received = list(session.get("received_chunks", []))
    total_chunks = session["total_chunks"]
    if len(received) != total_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not all chunks received. Got {len(received)}/{total_chunks}",
        )

    # Authoritative whitelist check at assembly time: the session's filename
    # extension AND content_type must match the declared upload_type. This is
    # the gate that decides what actually lands under /uploads (which nginx
    # serves straight back), so it cannot live only at /init.
    _validate_upload_type_file(
        session["upload_type"], session.get("filename") or "", session.get("content_type") or ""
    )

    # Final output path
    file_ext = os.path.splitext(session["filename"])[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"

    if session["upload_type"] == "h5p":
        # h5p assembles OUTSIDE the static /uploads root entirely (see
        # _h5p_temp_dir's docstring) — this is just the assembled raw
        # .h5p/.zip blob, not yet validated/extracted.
        # app.routers.h5p's /finalize endpoint reads this file, runs it
        # through h5p_service.validate_and_extract, and is responsible for
        # cleaning it up (success or failure) — it is never served
        # statically from here, by construction (no static mount covers
        # this directory).
        #
        # Also namespaced per-uploader (h5p_temp/{user_id}/...) — unlike
        # image/video/document, which land under the shared /uploads
        # static mount keyed by an unguessable uuid filename, an h5p blob
        # is looked up by /finalize from a session/filename an
        # authenticated caller supplies themselves. Without the per-user
        # subdirectory, instructor B could guess or be handed instructor
        # A's assembled-blob filename and finalize (and thereby delete)
        # A's in-flight upload. The uuid filename itself still isn't
        # guessable, but namespacing removes any reliance on that being
        # the only protection.
        upload_subdir = "h5p_temp"
        final_dir = _h5p_temp_dir() / str(current_user.id)
    else:
        type_dir_map = {"image": "images", "video": "videos", "document": "documents"}
        upload_subdir = type_dir_map.get(session["upload_type"], "files")
        final_dir = Path(_upload_dir()) / upload_subdir
    final_dir.mkdir(parents=True, exist_ok=True)
    final_path = final_dir / unique_filename

    try:
        # Assemble chunks into final file
        with final_path.open("wb") as final_file:
            for chunk_num in sorted(received):
                cp = _chunk_path(upload_id, chunk_num)
                with cp.open("rb") as chunk_file:
                    shutil.copyfileobj(chunk_file, final_file)

        # Verify file size
        actual_size = final_path.stat().st_size
        if actual_size != session["file_size"]:
            final_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"File assembly failed. Expected {session['file_size']} bytes, "
                    f"got {actual_size}"
                ),
            )

        if session["upload_type"] == "h5p":
            # NOT a servable URL — h5p_temp/ lives outside every static
            # mount (see _h5p_temp_dir), so there is no route that serves
            # this path. Reported as an opaque, non-"/uploads/"-prefixed
            # string purely for internal consistency/debugging so nothing
            # about this value could look like a working static link.
            # app.routers.h5p's /finalize looks this blob up by
            # (current_user.id, filename) directly, never by this string.
            file_url = f"h5p_temp/{current_user.id}/{unique_filename}"
        else:
            file_url = f"/uploads/{upload_subdir}/{unique_filename}"

        # Cleanup: remove chunk temp dir and drop session from Redis.
        _cleanup_temp_dir(upload_id)
        try:
            await _delete_session(client, upload_id)
        except Exception:
            # TTL will eventually clean it up; don't fail the response.
            logger.exception("Failed to delete session key for %s post-assembly", upload_id)

        return {
            "success": True,
            "upload_id": upload_id,
            "file_url": file_url,
            "filename": unique_filename,
            "original_filename": session["filename"],
            "size": session["file_size"],
            "content_type": session["content_type"],
        }

    except HTTPException:
        raise
    except Exception as e:
        if final_path.exists():
            try:
                final_path.unlink()
            except Exception:
                pass
        logger.exception("Failed to assemble file for upload %s", upload_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assemble file: {str(e)}",
        )


@router.post("/cancel")
async def cancel_chunked_upload(
    upload_id: str = Form(...),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    Cancel upload and cleanup.
    """
    client = await _redis()
    session = await _load_session(client, upload_id)
    if not session:
        return {"success": True, "message": "Upload session not found or already cancelled"}

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this upload",
        )

    _cleanup_temp_dir(upload_id)
    try:
        await _delete_session(client, upload_id)
    except Exception:
        logger.exception("Failed to delete session key during cancel for %s", upload_id)

    return {
        "success": True,
        "message": "Upload cancelled and cleaned up",
    }


@router.get("/status/{upload_id}")
async def get_upload_status(
    upload_id: str,
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    Get status of chunked upload.
    """
    client = await _redis()
    session = await _load_session(client, upload_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found",
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this upload",
        )

    received = list(session.get("received_chunks", []))
    total_chunks = session["total_chunks"]

    return {
        "upload_id": upload_id,
        "filename": session["filename"],
        "file_size": session["file_size"],
        "total_chunks": total_chunks,
        "received_chunks": len(received),
        "is_complete": len(received) == total_chunks,
        "created_at": session["created_at"],
    }
