"""H5P content API (plan Task 4, spec B4/B8) — mounted at /api/v1/h5p.

Endpoints:
  POST   /finalize            - validate+extract an uploaded package, create
                                 the H5PContent row (require_instructor).
                                 Also enforces a 2GB per-owner aggregate
                                 disk-usage cap on top of the per-package
                                 300MB zip-bomb guard (MAX_OWNER_AGGREGATE_BYTES).
  GET    /                    - list own contents (instructor); admin sees all
  GET    /{public_id}         - metadata (owner instructor, admin, or any
                                 enrolled user of a course whose lesson
                                 references this content)
  DELETE /{public_id}         - remove (owner/admin; 409 if referenced by a
                                 lesson)
  POST   /{public_id}/result  - upsert the caller's advisory result
  GET    /{public_id}/results - per-user rollup (owner instructor/admin)

Response style matches the rest of this codebase's newer routers (see
gradebook.py): plain dicts, no response envelopes, `require_instructor`/
inline course-owner-or-admin checks.
"""
import logging
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.h5p import H5PContent, H5PResult
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.h5p_service import (
    H5PValidationError,
    generate_public_id,
    peek_declared_total_size,
    validate_and_extract,
)

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(get_settings().UPLOAD_DIR)
# H5P_DIR is the VALIDATED-EXTRACTION target — it legitimately lives under
# UPLOAD_DIR because main.py mounts UPLOAD_DIR at /uploads via StaticFiles,
# and the player iframe is supposed to fetch these files statically once
# validate_and_extract has cleared them (spec B3's sandboxed-iframe model).
H5P_DIR = UPLOAD_DIR / "h5p"
# H5P_TEMP_DIR holds UNVALIDATED raw upload blobs and is deliberately a
# SIBLING of UPLOAD_DIR, never a subdirectory of it — UPLOAD_DIR is served
# unauthenticated by both this app's StaticFiles mount and nginx's parallel
# bind mount in production (see CLAUDE.md's "Static files & uploads"
# section), so anything placed inside it is reachable by anyone who can
# guess/observe its path. A raw chunked-upload blob here has NOT yet been
# through h5p_service.validate_and_extract, so it must not be servable
# under any circumstance until /finalize either extracts it (into H5P_DIR)
# or rejects it. Mirrors app.routers.chunked_upload._h5p_temp_dir(), which
# must resolve to the exact same path.
H5P_TEMP_DIR = UPLOAD_DIR.parent / "h5p_temp"

# Direct-upload path only (no chunked session) — cap per spec B8.
DIRECT_UPLOAD_MAX_BYTES = 20 * 1024 * 1024
ALLOWED_DIRECT_EXTENSIONS = {".h5p", ".zip"}

MAX_SCORE_CEILING = 10000

# Per-owner aggregate disk-usage cap. The per-package 300MB zip-bomb guard
# (h5p_service.MAX_TOTAL_UNCOMPRESSED_BYTES) is spec-compliant on its own,
# but nothing stops one instructor from uploading many packages just under
# that cap — this is a cheap additional ceiling on top, not a replacement.
# Not in the original spec; added as a low-cost hardening pass (Task 4
# review M-2) — see docs/LEARNING_EXPERIENCE.md (Task 10) for ops framing.
MAX_OWNER_AGGREGATE_BYTES = 2 * 1024 * 1024 * 1024  # 2GB


def _require_instructor_or_admin_owner(content: H5PContent, current_user: User) -> None:
    if content.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this H5P content",
        )


def _get_content_or_404(db: Session, public_id: str) -> H5PContent:
    content = db.query(H5PContent).filter(H5PContent.public_id == public_id).first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="H5P content not found")
    return content


def _referencing_lessons(db: Session, content_id: int):
    return db.query(Lesson).filter(Lesson.h5p_content_id == content_id).all()


def _user_can_view_content(db: Session, content: H5PContent, current_user: User) -> bool:
    """Owner instructor or admin always can. Otherwise the user must be
    actively enrolled in a course whose lesson references this content —
    students need the metadata (title/status) to know whether to play it."""
    if content.owner_id == current_user.id or current_user.role == "admin":
        return True

    lessons = _referencing_lessons(db, content.id)
    if not lessons:
        return False
    course_ids = {lesson.post_parent for lesson in lessons}
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id.in_(course_ids),
        )
        .all()
    )
    return any(e.enrollment_status not in ("cancelled", "suspended") for e in enrollment)


def _course_for_content_access(db: Session, content: H5PContent, current_user: User) -> Optional[Course]:
    """Find a course the current_user is enrolled in whose lesson references
    this content. Returns None if no such course exists (including for the
    owner/admin path, where enrollment isn't the access basis)."""
    lessons = _referencing_lessons(db, content.id)
    if not lessons:
        return None
    course_ids = {lesson.post_parent for lesson in lessons}
    if not course_ids:
        return None
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id.in_(course_ids),
            Enrollment.enrollment_status.notin_(["cancelled", "suspended"]),
        )
        .first()
    )
    if not enrollment:
        return None
    return db.query(Course).filter(Course.id == enrollment.course_id).first()


def _content_dict(content: H5PContent) -> dict:
    return {
        # Integer PK — plan Task 5's frontend lesson editor needs this to
        # populate Lesson.h5p_content_id (the FK column; see
        # app/models/course.py), which is the value courses.py's
        # _resolve_lesson_content_fields validates and persists. Every other
        # field here was already public_id-first by design (spec B4's
        # opaque-handle convention for URLs/results) — this is purely
        # additive and never used as a lookup key by this router itself.
        "id": content.id,
        "public_id": content.public_id,
        "owner_id": content.owner_id,
        "title": content.title,
        "library": content.library,
        "size_bytes": content.size_bytes,
        "status": content.status,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


@router.post("/finalize")
async def finalize_h5p_upload(
    chunked_session_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Validate + extract an already-uploaded `.h5p`/`.zip` package into an
    H5PContent row. Accepts EITHER a completed chunked-upload session
    (`chunked_session_id`, assembled by /api/v1/upload/chunked/complete into
    H5P_TEMP_DIR — a sibling of the static uploads root, never served) OR a
    direct small multipart upload (<=20MB).
    """
    if not chunked_session_id and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either chunked_session_id or a direct file upload",
        )
    if chunked_session_id and file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide only one of chunked_session_id or a direct file upload",
        )

    H5P_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    raw_path: Optional[Path] = None
    original_filename = "package.h5p"

    try:
        if chunked_session_id:
            # The chunked-upload router writes assembled h5p files under
            # H5P_TEMP_DIR/{uploader_user_id}/ (a sibling of the static
            # uploads root — see H5P_TEMP_DIR's module-level comment) with
            # a random uuid filename — we only trust the session_id as a
            # lookup key
            # WITHIN THE CALLER'S OWN NAMESPACE, then re-validate the
            # actual bytes ourselves (authoritative re-check, same
            # double-validation posture as chunked_upload.py's own
            # /init + /complete). Resolving is scoped to
            # H5P_TEMP_DIR/{current_user.id}/ so instructor B can never
            # name instructor A's blob, even if B could guess/observe its
            # filename — cross-user lookup is impossible by construction,
            # not just rejected after the fact.
            user_temp_dir = (H5P_TEMP_DIR / str(current_user.id)).resolve()
            candidate = user_temp_dir / chunked_session_id

            # Resolve-and-contain BEFORE any filesystem existence check.
            # Checking exists()/is_file() first would let a caller probe
            # for filenames outside their namespace (or containing "..")
            # by reading the 404-vs-400 response — an existence oracle.
            # Containment is verified purely from the resolved path, with
            # no stat() call preceding it.
            resolved = candidate.resolve()
            if user_temp_dir != resolved and user_temp_dir not in resolved.parents:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session id")

            if not resolved.exists() or not resolved.is_file():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chunked upload session file not found — complete the upload first",
                )
            raw_path = resolved
            original_filename = chunked_session_id
        else:
            ext = Path(file.filename or "").suffix.lower()
            if ext not in ALLOWED_DIRECT_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file extension '{ext}'. Allowed: .h5p, .zip",
                )
            original_filename = file.filename or "package.h5p"
            raw_path = H5P_TEMP_DIR / f"direct-{generate_public_id()}{ext}"
            size = 0
            with raw_path.open("wb") as out:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > DIRECT_UPLOAD_MAX_BYTES:
                        out.close()
                        raw_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Direct upload exceeds the {DIRECT_UPLOAD_MAX_BYTES} byte cap; use chunked upload",
                        )
                    out.write(chunk)

        # Per-owner aggregate disk-usage cap (Task 4 review M-2): sum this
        # owner's existing `ready`/`uploaded` content's on-disk size plus
        # this package's DECLARED total, and reject before ever touching
        # H5P_DIR if it would push the owner over the ceiling. This is a
        # cheap pre-flight against declared sizes, not the security
        # boundary — that's still validate_and_extract's streamed
        # enforcement — so a lying header can at worst let one oversized
        # package slip past this particular check (it will still be
        # caught by the per-package 300MB cap during extraction).
        try:
            declared_size = peek_declared_total_size(raw_path)
        except H5PValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
        existing_total = (
            db.query(func.coalesce(func.sum(H5PContent.size_bytes), 0))
            .filter(H5PContent.owner_id == current_user.id, H5PContent.status != "failed")
            .scalar()
            or 0
        )
        if existing_total + declared_size > MAX_OWNER_AGGREGATE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"This upload would exceed your {MAX_OWNER_AGGREGATE_BYTES} byte "
                    "aggregate H5P storage limit. Delete unused content and try again."
                ),
            )

        public_id = generate_public_id()
        dest_dir = H5P_DIR / public_id

        content = H5PContent(
            public_id=public_id,
            owner_id=current_user.id,
            title=(title or Path(original_filename).stem or "Untitled H5P content").strip()[:255],
            library=None,
            size_bytes=0,
            status="uploaded",
        )
        db.add(content)
        db.commit()
        db.refresh(content)

        try:
            result = validate_and_extract(raw_path, dest_dir)
        except H5PValidationError as exc:
            content.status = "failed"
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)

        try:
            content.library = result.library
            content.size_bytes = result.size_bytes
            content.status = "ready"
            db.commit()
            db.refresh(content)
        except Exception:
            # Extraction itself succeeded, but persisting the "ready" state
            # failed — a DB error here must not leave validated files on
            # disk with no corresponding "ready" row (or worse, a row stuck
            # at "uploaded" pointing at a directory that silently exists).
            # Roll back the DB session, mark the row failed, and remove the
            # files so this content simply doesn't exist rather than
            # existing in an inconsistent half-state.
            db.rollback()
            shutil.rmtree(dest_dir, ignore_errors=True)
            try:
                content.status = "failed"
                db.commit()
            except Exception:
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save H5P content after extraction",
            )

        return _content_dict(content)
    finally:
        # Always clean up the raw uploaded blob. It was never reachable via
        # any static route to begin with (H5P_TEMP_DIR is outside every
        # static mount) — this cleanup is about not leaking disk space, not
        # about closing an exposure window.
        if raw_path is not None:
            try:
                raw_path.unlink(missing_ok=True)
            except Exception:
                pass


@router.get("/")
async def list_h5p_contents(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Own contents (instructor); admin sees all."""
    query = db.query(H5PContent)
    if current_user.role != "admin":
        query = query.filter(H5PContent.owner_id == current_user.id)
    contents = query.order_by(H5PContent.created_at.desc()).all()

    # I-H4: the instructor H5P Library page shows how many lessons still
    # reference each package (DELETE 409s while that count is > 0), so
    # surface it here in one grouped query rather than N+1 per row.
    ids = [c.id for c in contents]
    attached: dict[int, int] = {}
    if ids:
        rows = (
            db.query(Lesson.h5p_content_id, func.count(Lesson.id))
            .filter(Lesson.h5p_content_id.in_(ids))
            .group_by(Lesson.h5p_content_id)
            .all()
        )
        attached = {cid: int(n) for cid, n in rows}

    items = []
    for c in contents:
        d = _content_dict(c)
        d["attached_lesson_count"] = attached.get(c.id, 0)
        items.append(d)
    return {"contents": items, "count": len(contents)}


@router.get("/{public_id}")
async def get_h5p_content(
    public_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    """Meta: instructor owner, admin, or any enrolled user of a course whose
    lesson references this content (students need this to play it)."""
    content = _get_content_or_404(db, public_id)
    if not _user_can_view_content(db, content, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this H5P content")
    return _content_dict(content)


@router.delete("/{public_id}")
async def delete_h5p_content(
    public_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Owner/admin only; 409 if any lesson still references it."""
    content = _get_content_or_404(db, public_id)
    _require_instructor_or_admin_owner(content, current_user)

    referencing = _referencing_lessons(db, content.id)
    if referencing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete: {len(referencing)} lesson(s) still reference this content. "
                "Remove or repoint those lessons first."
            ),
        )

    db.query(H5PResult).filter(H5PResult.content_id == content.id).delete()
    db.delete(content)
    db.commit()

    dest_dir = H5P_DIR / public_id
    shutil.rmtree(dest_dir, ignore_errors=True)

    return {"success": True, "public_id": public_id}


@router.post("/{public_id}/result")
async def submit_h5p_result(
    public_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    """Upsert the caller's advisory result. Enrollment-checked via the
    referencing lesson's course — rejects if no lesson references the
    content or the user lacks access to that course. Per spec B6/B8 this is
    advisory engagement data (feeds gamification), NOT gradebook truth.

    The content owner and admins bypass the enrollment check (same
    owner/admin testing-and-preview bypass pattern as the assignment submit
    guard, spec A1.6) — an instructor previewing their own H5P content
    isn't, and shouldn't need to be, enrolled in their own course."""
    content = _get_content_or_404(db, public_id)

    if content.owner_id != current_user.id and current_user.role != "admin":
        course = _course_for_content_access(db, content, current_user)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No accessible course lesson references this H5P content",
            )

    score = body.get("score")
    max_score = body.get("max_score")
    completed = bool(body.get("completed", False))

    if score is not None or max_score is not None:
        try:
            score = int(score) if score is not None else None
            max_score = int(max_score) if max_score is not None else None
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="score/max_score must be integers")

        if max_score is not None and not (0 <= max_score <= MAX_SCORE_CEILING):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"max_score must be between 0 and {MAX_SCORE_CEILING}",
            )
        if score is not None:
            if score < 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="score must be >= 0")
            if max_score is not None and score > max_score:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="score must be <= max_score",
                )

    existing = (
        db.query(H5PResult)
        .filter(H5PResult.content_id == content.id, H5PResult.user_id == current_user.id)
        .first()
    )
    was_already_completed = bool(existing and existing.completed)
    if existing:
        existing.score = score
        existing.max_score = max_score
        existing.completed = completed
        db.commit()
        db.refresh(existing)
        result_row = existing
    else:
        result_row = H5PResult(
            content_id=content.id,
            user_id=current_user.id,
            score=score,
            max_score=max_score,
            completed=completed,
        )
        db.add(result_row)
        db.commit()
        # Mastery graph (v2.0 §9.5) — best-effort, after the result commit.
        if score is not None and max_score:
            from app.services.mastery_service import safe_record_evidence
            safe_record_evidence(db, user_id=current_user.id, kind="h5p", ref_id=content.id, score=float(score), max_score=float(max_score))
        db.refresh(result_row)

    # Gamification (spec D1): +10 XP the FIRST time this user completes this
    # H5P content — guarded by was_already_completed so replaying/updating
    # an already-completed result never re-awards. Best-effort.
    if completed and not was_already_completed:
        try:
            from app.services.gamification_service import award as _award_xp
            referencing = _referencing_lessons(db, content.id)
            course_id = referencing[0].post_parent if referencing else None
            _award_xp(
                db, current_user.id, "h5p_completed",
                event_key=f"h5p:{content.id}:completed:user:{current_user.id}",
                course_id=course_id,
                meta={"h5p_content_id": content.id, "public_id": public_id},
            )
            # award() only flushes (H1 review fix) — the result row itself
            # was already committed above, so this commit covers only the
            # gamification rows.
            db.commit()
        except Exception as game_err:
            logger.warning("Gamification award failed for H5P result: %s", game_err)
            try:
                db.rollback()
            except Exception:
                pass

    return {
        "content_public_id": public_id,
        "user_id": current_user.id,
        "score": result_row.score,
        "max_score": result_row.max_score,
        "completed": result_row.completed,
        "updated_at": result_row.updated_at,
    }


@router.get("/{public_id}/results")
async def list_h5p_results(
    public_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Instructor owner/admin: per-user rollup."""
    content = _get_content_or_404(db, public_id)
    _require_instructor_or_admin_owner(content, current_user)

    results = db.query(H5PResult).filter(H5PResult.content_id == content.id).all()

    # Prefetch every referenced user in one query instead of N+1 lookups.
    user_ids = {r.user_id for r in results}
    users_by_id = {
        u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    rows = []
    for r in results:
        user = users_by_id.get(r.user_id)
        rows.append({
            "user_id": r.user_id,
            "user_name": user.display_name if user else "Unknown",
            "user_email": user.user_email if user else None,
            "score": r.score,
            "max_score": r.max_score,
            "completed": r.completed,
            "updated_at": r.updated_at,
        })
    return {"content_public_id": public_id, "results": rows, "count": len(rows)}
