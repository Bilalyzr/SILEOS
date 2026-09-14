"""Scorable-item registry (v2.0 §12 `scorable_items`) — DERIVED, not stored.

`GET /api/v1/scorable-items` lists every module the caller may insert into a
quiz, each with its derived `max_score` and default `tier_floor`, so the quiz
builder's single "Add item" palette (§5.2) has one source of truth. Kinds:
h5p (own, ready), game (own published + marketplace), lab (native catalog
entries), three_d_task (own, published — registered by WP2 when present).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.scorable import DEFAULT_TIER_FLOOR, KIND_BUCKET
from app.services.auth_service import AuthService

router = APIRouter()


def _entry(kind: str, ref, title: str, max_score: int, **extra) -> dict:
    return {
        "kind": kind, "id": ref, "title": title, "max_score": int(max_score),
        "tier_floor": DEFAULT_TIER_FLOOR[kind], "bucket": KIND_BUCKET[kind], **extra,
    }


@router.get("")
async def list_scorable_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    items = []

    from app.models.h5p import H5PContent
    for row in (db.query(H5PContent)
                .filter(H5PContent.owner_id == current_user.id, H5PContent.status == "ready")
                .order_by(H5PContent.title).all()):
        items.append(_entry("h5p", row.id, row.title or f"H5P #{row.id}", 100,
                            public_id=getattr(row, "public_id", None)))

    from app.models.game import Game
    from app.schemas.game_config import derive_max_score
    own = (db.query(Game)
           .filter(Game.owner_id == current_user.id, Game.status == "published")
           .order_by(Game.title).all())
    listed = (db.query(Game)
              .filter(Game.status == "published", Game.is_listed == True,  # noqa: E712
                      Game.owner_id != current_user.id)
              .order_by(Game.title).all())
    for row in own:
        items.append(_entry("game", row.id, row.title, derive_max_score(row.template, row.config or {}),
                            template=row.template, source="mine"))
    for row in listed:
        items.append(_entry("game", row.id, row.title, derive_max_score(row.template, row.config or {}),
                            template=row.template, source="marketplace", owner_id=row.owner_id))

    from app.routers.virtual_labs import catalog
    from app.schemas.lab_config import derive_lab_max_score
    for lab in sorted(catalog(db).values(), key=lambda l: (l["subject"], l["title"])):
        if lab["provider"] != "native" or derive_lab_max_score(lab.get("native_template"), lab.get("config") or {}) <= 0:
            continue
        items.append(_entry("lab", lab["slug"], lab["title"],
                            derive_lab_max_score(lab["native_template"], lab.get("config") or {}),
                            subject=lab["subject"], template=lab["native_template"]))

    try:
        from app.routers.three_d_tasks import list_tasks_for_palette  # type: ignore
        items.extend(list_tasks_for_palette(db, current_user))
    except ImportError:
        pass

    return {"items": items, "tiers": ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7"],
            "gradeable_floor": "T4"}
