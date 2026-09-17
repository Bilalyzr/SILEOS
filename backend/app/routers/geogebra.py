"""GeoGebra applets — instructor CRUD + player embed payload.

⚠️ LICENCE: GeoGebra Apps are free for NON-COMMERCIAL use; a commercial
deployment needs an agreement with GeoGebra GmbH (blueprint §8.3). The
owner approved building this integration for preview/development on
2026-09-04. Resolve the licence before selling paid seats against it.

Attach rule (courses.py content resolver): applets attach to lessons of
FREE courses only — this router never checks that (separation of
concerns); it owns applet lifecycle, not the lesson contract.

No trailing slashes anywhere (redirect_slashes=False); '/geogebra' is on
the frontend noSlashEndpoints list.
"""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.geogebra import GEOGEBRA_APP_TYPES, GeoGebraApplet
from app.services.auth_service import AuthService

router = APIRouter()

_MATERIALS_RE = re.compile(r"geogebra\.org/m/([A-Za-z0-9]+)")


def _extract_material_id(raw: str | None) -> str | None:
    """Accept a full Materials URL or a bare id — normalize to the id."""
    if not raw:
        return None
    raw = raw.strip()
    m = _MATERIALS_RE.search(raw)
    if m:
        return m.group(1)
    # bare alphanumeric id (materials ids are short alnum strings)
    if re.fullmatch(r"[A-Za-z0-9]{3,40}", raw):
        return raw
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="material_id must be a GeoGebra Materials URL or id "
               "(e.g. https://www.geogebra.org/m/abc123)",
    )


def _applet_dict(a: GeoGebraApplet) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "app_type": a.app_type,
        "material_id": a.material_id,
        "config": a.config or {},
        "has_saved_state": bool(a.ggb_base64),
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


@router.post("/applets", status_code=status.HTTP_201_CREATED)
async def create_applet(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="title is required")
    app_type = payload.get("app_type", "graphing")
    if app_type not in GEOGEBRA_APP_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"app_type must be one of {GEOGEBRA_APP_TYPES}")

    material_id = _extract_material_id(payload.get("material_id"))
    applet = GeoGebraApplet(
        owner_id=current_user.id,
        title=title[:200],
        app_type=app_type,
        material_id=material_id,
        config=payload.get("config") or {},
    )
    db.add(applet)
    db.commit()
    db.refresh(applet)
    return _applet_dict(applet)


@router.get("/applets")
async def list_applets(
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    rows = (db.query(GeoGebraApplet)
            .filter(GeoGebraApplet.owner_id == current_user.id)
            .order_by(GeoGebraApplet.created_at.desc()).all())
    return {"applets": [_applet_dict(a) for a in rows]}


@router.put("/applets/{applet_id}")
async def update_applet(
    applet_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    applet = db.query(GeoGebraApplet).filter(GeoGebraApplet.id == applet_id).first()
    if not applet:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Applet not found")
    if applet.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your applet")

    if "title" in payload:
        title = (payload.get("title") or "").strip()
        if not title:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="title cannot be empty")
        applet.title = title[:200]
    if "app_type" in payload:
        if payload["app_type"] not in GEOGEBRA_APP_TYPES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"app_type must be one of {GEOGEBRA_APP_TYPES}")
        applet.app_type = payload["app_type"]
    if "material_id" in payload:
        applet.material_id = _extract_material_id(payload.get("material_id"))
    if "config" in payload and isinstance(payload["config"], dict):
        applet.config = payload["config"]
    if "ggb_base64" in payload:
        # Saved construction state from the authoring canvas. Size-capped:
        # a .ggb is a zip of XML — 10MB is already absurd, 20MB is a hard no.
        val = payload.get("ggb_base64") or None
        if val and len(val) > 20 * 1024 * 1024:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                detail="saved construction exceeds 20MB")
        applet.ggb_base64 = val
    db.commit()
    db.refresh(applet)
    return _applet_dict(applet)


@router.delete("/applets/{applet_id}")
async def delete_applet(
    applet_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    applet = db.query(GeoGebraApplet).filter(GeoGebraApplet.id == applet_id).first()
    if not applet:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Applet not found")
    if applet.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your applet")
    # Lessons reference applets via FK — block delete while in use, same
    # doctrine as ebooks (referenced content is never silently destroyed).
    from app.models.course import Lesson
    in_use = db.query(Lesson).filter(
        Lesson.geogebra_applet_id == applet_id).count()
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Applet is attached to {in_use} lesson(s) — detach them first")
    db.delete(applet)
    db.commit()
    return {"deleted": True, "id": applet_id}


@router.get("/applets/{applet_id}/embed")
async def embed_params(
    applet_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_optional_current_user),
):
    """The deployggb.js appletParameters for the player. Applets referenced
    by lessons of free courses are public content — no per-user data — but
    we still require auth to keep anonymous scraping of the authoring
    library off this endpoint."""
    if current_user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication required")
    applet = db.query(GeoGebraApplet).filter(GeoGebraApplet.id == applet_id).first()
    if not applet:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Applet not found")
    d = _applet_dict(applet)
    d["applet_parameters"] = applet.embed_params()
    return d
