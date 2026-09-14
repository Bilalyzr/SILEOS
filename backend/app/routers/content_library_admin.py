"""Admin content libraries (2026-09-05) — mounted at /api/v1/admin/content-library.

Three admin-curated libraries that instructors pull into a curriculum:
  /labs      — virtual lab catalog rows (CRUD + JSON pack import; see
               app/schemas/lab_config.LabCatalogEntryIn for the entry shape).
  /games     — prebuilt learning games: a JSON pack of {title, template,
               config} validated by the SAME per-template validators as the
               instructor builder, created admin-owned, published and listed
               so they show in every instructor's marketplace section.
               /games/import-defaults loads backend/seed_packs/prebuilt_games.json.
  /three-d   — shared 3D asset library: bulk GLB import (magic-byte + size
               checked exactly like the instructor upload) stored under
               backend/three_d/{admin_id}/ with is_library=True, visible to
               every instructor's picker and attachable cross-owner.

Every import is all-or-nothing: the whole pack is validated before a single
row is written, so a bad entry never leaves a half-imported library.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.content_library import VirtualLabCatalog
from app.models.game import Game
from app.models.three_d import ThreeDModel
from app.models.user import User
from app.routers.three_d import GLB_MAGIC, MAX_GLB_BYTES, _model_dict, _model_dir, _resolve
from app.routers.virtual_labs import BUILTIN_BY_SLUG, _row_dict
from app.schemas.game_config import GameConfigError, validate_game_config
from app.schemas.lab_config import LabCatalogEntryIn, LabConfigError
from app.services.auth_service import AuthService

router = APIRouter()

SEED_PACK_DIR = Path(__file__).resolve().parent.parent.parent / "seed_packs"
MAX_PACK_ENTRIES = 100


# =============================================================== labs

def _lab_in_use(db: Session, slug: str) -> int:
    from app.models.course import Lesson
    return db.query(Lesson).filter(Lesson.virtual_lab_sim == slug).count()


def _apply_entry(row: VirtualLabCatalog, data: dict, admin_id: int) -> None:
    for k in ("slug", "title", "subject", "description", "provider", "embed_url",
              "native_template", "config", "attribution", "thumbnail_url", "is_published"):
        setattr(row, k, data[k])
    if row.created_by is None:
        row.created_by = admin_id


@router.get("/labs")
async def admin_list_labs(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    rows = db.query(VirtualLabCatalog).order_by(VirtualLabCatalog.subject, VirtualLabCatalog.title).all()
    return {
        "labs": [_row_dict(r) for r in rows],
        "builtin": [
            {"slug": l["slug"], "title": l["title"], "subject": l["subject"], "provider": l["provider"],
             "overridden": any(r.slug == l["slug"] for r in rows)}
            for l in BUILTIN_BY_SLUG.values()
        ],
    }


@router.post("/labs", status_code=201)
async def admin_create_lab(
    payload: LabCatalogEntryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    try:
        data = payload.normalized()
        if data.get('native_template') == 'concept_lab':
            from app.services.lab_model_service import require_attachable
            require_attachable(db, data['config'].get('model_id'), current_user)
    except LabConfigError as exc:
        raise HTTPException(status_code=400, detail=exc.detail)
    if db.query(VirtualLabCatalog).filter(VirtualLabCatalog.slug == data["slug"]).first():
        raise HTTPException(status_code=409, detail="A catalog entry with this slug already exists")
    row = VirtualLabCatalog()
    _apply_entry(row, data, current_user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_dict(row)


@router.put("/labs/{lab_id}")
async def admin_update_lab(
    lab_id: int,
    payload: LabCatalogEntryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    row = db.query(VirtualLabCatalog).filter(VirtualLabCatalog.id == lab_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    try:
        data = payload.normalized()
        if data.get('native_template') == 'concept_lab':
            from app.services.lab_model_service import require_attachable
            require_attachable(db, data['config'].get('model_id'), current_user)
    except LabConfigError as exc:
        raise HTTPException(status_code=400, detail=exc.detail)
    clash = (db.query(VirtualLabCatalog)
             .filter(VirtualLabCatalog.slug == data["slug"], VirtualLabCatalog.id != lab_id).first())
    if clash:
        raise HTTPException(status_code=409, detail="Another catalog entry already uses this slug")
    if data["slug"] != row.slug and _lab_in_use(db, row.slug):
        raise HTTPException(status_code=409, detail="Slug is attached to lessons — create a new entry instead of renaming")
    _apply_entry(row, data, current_user.id)
    db.commit()
    db.refresh(row)
    return _row_dict(row)


@router.delete("/labs/{lab_id}")
async def admin_delete_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    row = db.query(VirtualLabCatalog).filter(VirtualLabCatalog.id == lab_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    in_use = _lab_in_use(db, row.slug)
    if in_use and row.slug not in BUILTIN_BY_SLUG:
        raise HTTPException(status_code=409, detail=f"Attached to {in_use} lesson(s) — detach first or unpublish")
    db.delete(row)
    db.commit()
    return {"deleted": True, "id": lab_id}


class LabPackIn(BaseModel):
    labs: List[LabCatalogEntryIn] = Field(..., min_items=1, max_items=MAX_PACK_ENTRIES)


@router.post("/labs/import")
async def admin_import_labs(
    pack: LabPackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Upsert by slug. Validates EVERY entry before writing any (all-or-nothing)."""
    normalized: List[dict] = []
    seen = set()
    for i, entry in enumerate(pack.labs):
        try:
            data = entry.normalized()
            if data.get('native_template') == 'concept_lab':
                from app.services.lab_model_service import require_attachable
                require_attachable(db, data['config'].get('model_id'), current_user)
        except LabConfigError as exc:
            raise HTTPException(status_code=400, detail=f"labs[{i}] ({entry.slug}): {exc.detail}")
        if data["slug"] in seen:
            raise HTTPException(status_code=400, detail=f"labs[{i}]: duplicate slug '{data['slug']}' in pack")
        seen.add(data["slug"])
        normalized.append(data)

    created = updated = 0
    for data in normalized:
        row = db.query(VirtualLabCatalog).filter(VirtualLabCatalog.slug == data["slug"]).first()
        if row:
            _apply_entry(row, data, current_user.id)
            updated += 1
        else:
            row = VirtualLabCatalog()
            _apply_entry(row, data, current_user.id)
            db.add(row)
            created += 1
    db.commit()
    return {"created": created, "updated": updated, "slugs": [d["slug"] for d in normalized]}


# =============================================================== games

class GamePackEntry(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    template: str
    config: dict


class GamePackIn(BaseModel):
    games: List[GamePackEntry] = Field(..., min_items=1, max_items=MAX_PACK_ENTRIES)


def _import_games(db: Session, entries: List[GamePackEntry], admin_id: int) -> dict:
    validated = []
    for i, e in enumerate(entries):
        try:
            validated.append((e.title.strip(), e.template, validate_game_config(e.template, e.config)))
        except GameConfigError as exc:
            raise HTTPException(status_code=400, detail=f"games[{i}] ({e.title}): {exc.detail}")

    created, skipped = [], []
    for title, template, config in validated:
        existing = (db.query(Game)
                    .filter(Game.owner_id == admin_id, Game.title == title, Game.template == template)
                    .first())
        if existing:
            skipped.append({"id": existing.id, "title": title})
            continue
        g = Game(owner_id=admin_id, title=title, template=template, config=config,
                 status="published", is_listed=True)
        db.add(g)
        db.flush()
        created.append({"id": g.id, "title": title})
    db.commit()
    return {"created": created, "skipped": skipped}


@router.get("/games")
async def admin_list_prebuilt_games(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    from app.routers.games import _game_dict
    rows = (db.query(Game).filter(Game.owner_id == current_user.id)
            .order_by(Game.created_at.desc()).all())
    return {"games": [dict(_game_dict(g, include_config=False), is_listed=bool(g.is_listed)) for g in rows]}


@router.post("/games/import")
async def admin_import_games(
    pack: GamePackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    return _import_games(db, pack.games, current_user.id)


@router.post("/games/import-defaults")
async def admin_import_default_games(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Load the shipped pack (backend/seed_packs/prebuilt_games.json). Idempotent."""
    path = SEED_PACK_DIR / "prebuilt_games.json"
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Shipped pack missing: seed_packs/prebuilt_games.json")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        pack = GamePackIn(**raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Shipped pack is invalid: {exc}")
    return _import_games(db, pack.games, current_user.id)


# =============================================================== 3D assets

@router.get("/three-d")
async def admin_list_library_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    rows = (db.query(ThreeDModel).filter(ThreeDModel.is_library == True)  # noqa: E712
            .order_by(ThreeDModel.created_at.desc()).all())
    return {"models": [_model_dict(m) for m in rows]}


@router.post("/three-d/import", status_code=201)
async def admin_import_models(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Bulk GLB import into the shared library. Every file is validated before
    any is stored; titles come from the filenames."""
    if not files or len(files) > 50:
        raise HTTPException(status_code=400, detail="Upload 1-50 .glb files")
    blobs = []
    budgets = {}
    for f in files:
        raw = await f.read()
        name = os.path.basename(f.filename or "model.glb")
        if len(raw) > MAX_GLB_BYTES:
            raise HTTPException(status_code=413, detail=f"{name}: exceeds the 50MB limit")
        if len(raw) < 4 or raw[:4] != GLB_MAGIC:
            raise HTTPException(status_code=422, detail=f"{name}: not a valid GLB file (magic bytes missing)")
        from app.services.glb_budget import check_or_raise as _glb_budget
        budgets[name] = _glb_budget(raw, name)   # WP9: all-or-nothing, before any file is stored
        blobs.append((name, raw))

    out = []
    for name, raw in blobs:
        rel = os.path.join(str(current_user.id), f"{uuid.uuid4()}.glb")
        full_dir = _model_dir(current_user.id)
        with open(os.path.join(full_dir, os.path.basename(rel)), "wb") as fh:
            fh.write(raw)
        m = ThreeDModel(
            owner_id=current_user.id,
            title=(os.path.splitext(name)[0] or "model")[:200],
            file_path=rel, file_size_bytes=len(raw), format="glb", is_library=True,
        )
        db.add(m)
        db.flush()
        out.append(m)
    db.commit()
    return {"models": [{**_model_dict(m), "budget": budgets.get(name)} for (name, _), m in zip(blobs, out)]}


class LibraryModelPatch(BaseModel):
    is_library: Optional[bool] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)


@router.patch("/three-d/{model_id}")
async def admin_patch_model(
    model_id: int,
    payload: LibraryModelPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    m = db.query(ThreeDModel).filter(ThreeDModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="3D model not found")
    if payload.is_library is not None:
        m.is_library = payload.is_library
    if payload.title is not None:
        m.title = payload.title.strip()[:200]
    db.commit()
    db.refresh(m)
    return _model_dict(m)


@router.delete("/three-d/{model_id}")
async def admin_delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    m = db.query(ThreeDModel).filter(ThreeDModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="3D model not found")
    from app.models.course import Lesson
    in_use = db.query(Lesson).filter(Lesson.three_d_model_id == model_id).count()
    if in_use:
        raise HTTPException(status_code=409, detail=f"Attached to {in_use} lesson(s) — detach first")
    full = _resolve(m.file_path)
    db.delete(m)
    db.commit()
    try:
        os.remove(full)
    except OSError:
        pass
    return {"deleted": True, "id": model_id}
