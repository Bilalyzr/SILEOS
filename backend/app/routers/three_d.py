"""3D model library — instructor GLB upload/list/stream/delete (Phase 2).

Hardening (blueprint §8.4 doctrine, scaled to this phase):
  - magic-byte check: the file MUST start with b"glTF" (GLB container) —
    extension is never trusted;
  - hard size cap 50MB (per-file; budget enforcement deepens in the
    optimisation-pipeline phase);
  - uuid filenames stored PRIVATELY under backend/three_d/{owner_id}/ —
    never nginx-served; streams require auth via this router;
  - owner-or-admin access on every surface.
"""
import os
import uuid
from pathlib import Path, PureWindowsPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.three_d import ThreeDModel
from app.services.auth_service import AuthService

router = APIRouter()

MAX_GLB_BYTES = 50 * 1024 * 1024
GLB_MAGIC = b"glTF"
BASE_DIR = os.environ.get('THREE_D_ROOT') or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "three_d")


def _model_dir(owner_id: int) -> str:
    d = os.path.join(BASE_DIR, str(owner_id))
    os.makedirs(d, exist_ok=True)
    return d


def _resolve(rel_path: str) -> str:
    """Path-traversal guard: resolved path must stay inside BASE_DIR."""
    # Older Windows uploads stored backslashes; Linux needs normalized paths.
    relative = rel_path.replace('\\', '/')
    base = Path(BASE_DIR).resolve()
    if PureWindowsPath(relative).drive or relative.startswith('/') or '..' in relative.split('/'):
        raise HTTPException(status_code=404, detail="File not found")
    full = (base / relative).resolve()
    if base not in full.parents or not full.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return str(full)


def _get_owned(db: Session, model_id: int, user) -> ThreeDModel:
    m = db.query(ThreeDModel).filter(ThreeDModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="3D model not found")
    if m.owner_id != user.id and user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Not your 3D model")
    return m


def _model_dict(m: ThreeDModel) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "format": m.format,
        "file_size_bytes": m.file_size_bytes,
        "created_at": m.created_at,
        "owner_id": m.owner_id,
        "is_library": bool(getattr(m, "is_library", False)),
    }


@router.post("/models", status_code=201)
async def upload_model(
    title: str = "",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    raw = await file.read(MAX_GLB_BYTES + 1)
    if len(raw) > MAX_GLB_BYTES:
        raise HTTPException(status_code=413,
                            detail="GLB exceeds the 50MB limit")
    if len(raw) < 4 or raw[:4] != GLB_MAGIC:
        raise HTTPException(status_code=422,
                            detail="Not a valid GLB file (magic bytes missing)")
    # v2.0 §11 (WP9): budget check — 422 over hard caps, tier warnings returned
    from app.services.lab_model_service import validate_glb
    budget = validate_glb(raw)

    rel = f"{current_user.id}/{uuid.uuid4()}.glb"
    full = _model_dir(current_user.id)
    os.makedirs(full, exist_ok=True)
    with open(os.path.join(full, os.path.basename(rel)), "wb") as f:
        f.write(raw)

    m = ThreeDModel(
        owner_id=current_user.id,
        title=(title or os.path.basename(file.filename or "model"))[:200],
        file_path=rel,
        file_size_bytes=len(raw),
        format="glb",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {**_model_dict(m), "budget": budget}


@router.get("/models")
async def list_models(
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    rows = (db.query(ThreeDModel)
            .filter(ThreeDModel.owner_id == current_user.id)
            .order_by(ThreeDModel.created_at.desc()).all())
    # Admin-curated shared library (content libraries, 2026-09-05): every
    # instructor can browse + attach these; excludes the caller's own rows.
    library = (db.query(ThreeDModel)
               .filter(ThreeDModel.is_library == True, ThreeDModel.owner_id != current_user.id)  # noqa: E712
               .order_by(ThreeDModel.title).all())
    return {"models": [_model_dict(m) for m in rows], "library": [_model_dict(m) for m in library]}


@router.post('/models/restore-library')
def restore_bundled_library(db: Session = Depends(get_db), current_user=Depends(AuthService.require_admin)):
    from app.services.model_library_service import install_library
    try:
        return {'models': install_library(db, current_user)}
    except (ValueError, OSError) as exc:
        raise HTTPException(422, 'The bundled model library is incomplete or invalid. Check the release assets.') from exc


@router.get("/models/{model_id}/file")
async def stream_model(
    model_id: int,
    tier: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_optional_current_user),
):
    from app.services.lab_model_service import referencing_labs
    public_lab = referencing_labs(db, model_id).filter_by(is_published=True).first() is not None
    if current_user is None and not public_lab:
        # Public-preview lessons (2026-09-05): visitors may stream ONLY models
        # attached to a lesson the instructor opened as a public preview.
        from app.services.public_preview import require_anonymous_preview
        require_anonymous_preview(db, "three_d_model_id", model_id, "This 3D model")
    # Private drafts stay private; published labs and preview lessons are public.
    m = db.query(ThreeDModel).filter(ThreeDModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="3D model not found")
    if current_user is not None and not public_lab:
        from app.services.public_preview import allows_anonymous
        from app.models.course import Course, Lesson
        from app.models.enrollment import Enrollment
        from app.models.three_d_task import ThreeDTask
        allowed = (m.owner_id == current_user.id or current_user.role in ('admin', 'superadmin')
                   or (m.is_library and current_user.role == 'instructor')
                   or allows_anonymous(db, 'three_d_model_id', model_id))
        if not allowed:
            allowed = db.query(Lesson.id).join(Enrollment, Enrollment.course_id == Lesson.post_parent).filter(
                Lesson.three_d_model_id == model_id, Enrollment.user_id == current_user.id,
                Enrollment.enrollment_status.in_(('enrolled', 'completed'))).first() is not None
        if not allowed:
            allowed = db.query(Lesson.id).join(Course, Course.id == Lesson.post_parent).filter(
                Lesson.three_d_model_id == model_id, Course.post_author == current_user.id).first() is not None
        if not allowed:
            allowed = db.query(ThreeDTask.id).filter(ThreeDTask.model_id == model_id,
                (ThreeDTask.status == 'published') | (ThreeDTask.owner_id == current_user.id)).first() is not None
        if not allowed:
            allowed = referencing_labs(db, model_id).filter_by(created_by=current_user.id).first() is not None
        if not allowed:
            raise HTTPException(403, 'This model is private. Open it through an accessible lesson or published lab.')
    rel = m.file_path
    tiers = getattr(m, "tier_files", None) or {}
    if tier and tier.upper() in tiers:
        try:
            _resolve(tiers[tier.upper()])
            rel = tiers[tier.upper()]
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            # Missing optional tiers must fall back to the original on phones.
    full = _resolve(rel)
    return FileResponse(full, media_type="model/gltf-binary",
                        filename=f"{m.id}.glb",
                        headers={"Cache-Control": "private, no-store", "X-Tier": (tier or "T1").upper() if rel != m.file_path else "T1"})


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    m = _get_owned(db, model_id, current_user)
    from app.models.course import Lesson
    from app.services.lab_model_service import referencing_labs
    from app.models.three_d_task import ThreeDTask
    if referencing_labs(db, model_id).first() or db.query(ThreeDTask.id).filter_by(model_id=model_id).first():
        raise HTTPException(409, 'This model is attached to a lab or 3D task. Detach it first.')
    in_use = db.query(Lesson).filter(
        Lesson.three_d_model_id == model_id).count()
    if in_use:
        raise HTTPException(status_code=409,
                            detail=f"Attached to {in_use} lesson(s) — detach first")
    full = _resolve(m.file_path)
    db.delete(m)
    db.commit()
    try:
        os.remove(full)
    except OSError:
        pass
    return {"deleted": True, "id": model_id}


@router.get("/tools")
async def media_tools(current_user=Depends(AuthService.require_instructor)):
    """Which media tools the host has (roadmap item 9). Honest: nothing is faked."""
    from app.services.media_pipeline import tool_status
    return tool_status()


@router.post("/models/{model_id}/build-tiers")
async def build_tiers(
    model_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Pre-generate T2/T3 GLBs with gltf-transform (simplify + webp textures).
    503 with the install hint when the tool is missing."""
    from app.services import media_pipeline as mp
    m = db.query(ThreeDModel).filter(ThreeDModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="3D model not found")
    if m.owner_id != current_user.id and current_user.role not in ("admin", "superadmin") and not m.is_library:
        raise HTTPException(status_code=403, detail="Not your model")
    if not mp.gltf_transform_path():
        raise HTTPException(status_code=503, detail="gltf-transform is not installed on this server (npm i -g @gltf-transform/cli)")
    src = _resolve(m.file_path)
    try:
        built = mp.build_glb_tiers(src)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Tier build failed: {str(exc)[:300]}")
    base_dir = os.path.dirname(m.file_path)
    m.tier_files = {tier: os.path.join(base_dir, os.path.basename(path)).replace("\\", "/") for tier, path in built.items()}
    db.commit()
    sizes = {tier: os.path.getsize(_resolve(rel)) for tier, rel in m.tier_files.items()}
    return {"model_id": m.id, "tiers": m.tier_files, "sizes": {"T1": m.file_size_bytes, **sizes}}
