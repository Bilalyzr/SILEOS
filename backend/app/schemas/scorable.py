"""ScorableItem contract (v2.0 §5.1 / §12) — the one interface every module
inside a quiz implements, so games, H5P, labs and 3D tasks are scored, tracked
and rolled into the gradebook with no per-kind work.

Stored inline on `Quiz.interactive_modules` (JSON) as normalized dicts:

    {kind, id, title, max_score, weight, attempts_allowed, grading_mode,
     practice_only, tier_floor}

Doctrine:
  * `max_score` is DERIVED from the referenced module (never trusted from
    the client) — games: 10 × items, native labs: 10 × units, H5P: 100
    (results are stored as score/max and normalised to percent).
  * `tier_floor` is the lowest degradation tier at which the item is still
    gradeable (sasha-tier-ladder). A graded (non-practice) item whose floor
    is above T4 — i.e. T0..T3 — BLOCKS publication (422): a learner on a
    low-end phone must be able to earn every mark. Practice-only items may
    have any floor.
  * `practice_only` items are played and tracked but never count toward the
    grade (§5.2 — without this flag instructors stop inserting games).
  * Registry (§12 `scorable_items`) is DERIVED, not stored: see
    routers/scorable_items.py, which lists every item the caller may insert
    with its derived max_score and default floor (derived-over-stored, §11).

Old entries `{kind, id, title}` (pre-2026-09-05) normalise with defaults, so
existing quizzes keep working unchanged.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

TIERS = ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7"]
GRADEABLE_FLOOR = "T4"                     # §5.3 non-negotiable rule
SCORABLE_KINDS = {"h5p", "game", "lab", "three_d_task"}
GRADING_MODES = {"auto", "auto_with_review", "manual"}
DEFAULT_TIER_FLOOR = {"h5p": "T4", "game": "T4", "lab": "T4", "three_d_task": "T4"}
# Which cumulative-grade bucket (type_profiles.default_assessment_weights key)
# an item's score rolls into (§5.3: "3D / simulation tasks" vs "games and H5P").
KIND_BUCKET = {"h5p": "games_h5p", "game": "games_h5p", "lab": "three_d_tasks", "three_d_task": "three_d_tasks"}
MAX_ITEMS_PER_QUIZ = 30


def tier_rank(tier: str) -> int:
    return TIERS.index(tier)


def _err(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _resolve_reference(db: Session, kind: str, ref: Any, current_user) -> Tuple[Any, str, int, Optional[str]]:
    """Return (id_as_stored, title, derived_max_score, extra) after existence +
    ownership checks. `extra` carries the H5P public_id the player needs."""
    if kind == "h5p":
        from app.models.h5p import H5PContent
        if not isinstance(ref, int) or isinstance(ref, bool):
            raise _err(422, "h5p items need an integer id")
        row = db.query(H5PContent).filter(H5PContent.id == ref).first()
        if not row:
            raise _err(404, f"h5p module {ref} not found")
        if row.owner_id != current_user.id and current_user.role != "admin":
            raise _err(403, f"not your h5p module {ref}")
        return ref, str(row.title or ""), 100, getattr(row, "public_id", None)

    if kind == "game":
        from app.models.game import Game
        from app.schemas.game_config import derive_max_score
        if not isinstance(ref, int) or isinstance(ref, bool):
            raise _err(422, "game items need an integer id")
        row = db.query(Game).filter(Game.id == ref).first()
        if not row:
            raise _err(404, f"game module {ref} not found")
        listed = bool(getattr(row, "is_listed", False)) and row.status == "published"
        if row.owner_id != current_user.id and current_user.role != "admin" and not listed:
            raise _err(403, f"not your game module {ref} (and it is not in the marketplace)")
        return ref, str(row.title or ""), derive_max_score(row.template, row.config or {}), None

    if kind == "lab":
        from app.routers.virtual_labs import get_lab
        from app.schemas.lab_config import derive_lab_max_score
        if not isinstance(ref, str) or not ref.strip():
            raise _err(422, "lab items need the catalog slug as id")
        lab = get_lab(db, ref.strip())
        if not lab:
            raise _err(422, f"unknown or unpublished virtual lab '{ref}'")
        if lab["provider"] != "native" or derive_lab_max_score(lab.get("native_template"), lab.get("config") or {}) <= 0:
            raise _err(422, f"lab '{ref}' has no gradeable result — attach it as a lesson investigation")
        return lab["slug"], lab["title"], derive_lab_max_score(lab["native_template"], lab.get("config") or {}), None

    if kind == "three_d_task":
        # Registered by WP2 (3D match-and-verify). Until that lands the kind
        # is reserved so old clients get a clear message, not a silent 'video'.
        try:
            from app.routers.three_d_tasks import resolve_task_for_quiz  # type: ignore
        except ImportError:
            raise _err(422, "3D tasks are not available in this build")
        return resolve_task_for_quiz(db, ref, current_user)

    raise _err(422, f"kind must be one of {sorted(SCORABLE_KINDS)}")


def normalize_scorable_item(db: Session, raw: Dict[str, Any], current_user) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise _err(422, "interactive_modules entries must be objects")
    kind = raw.get("kind")
    if kind not in SCORABLE_KINDS:
        raise _err(422, f"interactive_modules entries need kind in {sorted(SCORABLE_KINDS)}")
    ref, title, max_score, extra = _resolve_reference(db, kind, raw.get("id"), current_user)

    weight = raw.get("weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not (0 <= float(weight) <= 100):
        raise _err(422, f"{kind} {ref}: weight must be a number between 0 and 100")
    attempts = raw.get("attempts_allowed", 0)
    if isinstance(attempts, bool) or not isinstance(attempts, int) or not (0 <= attempts <= 99):
        raise _err(422, f"{kind} {ref}: attempts_allowed must be an integer 0 (unlimited) .. 99")
    grading_mode = raw.get("grading_mode", "auto")
    if grading_mode not in GRADING_MODES:
        raise _err(422, f"{kind} {ref}: grading_mode must be one of {sorted(GRADING_MODES)}")
    practice_only = raw.get("practice_only", False)
    if not isinstance(practice_only, bool):
        raise _err(422, f"{kind} {ref}: practice_only must be true/false")
    tier_floor = raw.get("tier_floor") or DEFAULT_TIER_FLOOR[kind]
    if tier_floor not in TIERS:
        raise _err(422, f"{kind} {ref}: tier_floor must be one of {TIERS}")

    item = {
        "kind": kind,
        "id": ref,
        "title": (raw.get("title") or title or f"{kind} {ref}")[:200] if raw.get("title") else (title or f"{kind} {ref}")[:200],
        "max_score": int(max_score),
        "weight": float(weight),
        "attempts_allowed": int(attempts),
        "grading_mode": grading_mode,
        "practice_only": practice_only,
        "tier_floor": tier_floor,
    }
    if extra:
        item["public_id"] = extra
    return item


def normalize_scorable_items(db: Session, raws: Optional[List[Dict[str, Any]]], current_user) -> List[Dict[str, Any]]:
    raws = raws or []
    if len(raws) > MAX_ITEMS_PER_QUIZ:
        raise _err(422, f"a quiz may hold at most {MAX_ITEMS_PER_QUIZ} scorable items")
    items = [normalize_scorable_item(db, r, current_user) for r in raws]
    seen = set()
    for it in items:
        key = (it["kind"], str(it["id"]))
        if key in seen:
            raise _err(422, f"duplicate scorable item {it['kind']} {it['id']}")
        seen.add(key)
    return items


def assert_publishable(items: List[Dict[str, Any]]) -> None:
    """§5.3 rule: a graded item whose tier floor is above T4 cannot ship."""
    blocked = [it for it in items
               if not it.get("practice_only") and tier_rank(it.get("tier_floor", "T4")) < tier_rank(GRADEABLE_FLOOR)]
    if blocked:
        names = ", ".join(f"{it['title']} ({it['tier_floor']})" for it in blocked)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("Cannot publish: graded items must be completable at tier T4 (still images, "
                    f"low-end phone). Mark these practice-only or lower their tier floor: {names}"),
        )


def best_item_score(db: Session, item: Dict[str, Any], user_id: int) -> Optional[Tuple[float, float]]:
    """Best (raw, max) the learner has recorded for this item, or None."""
    kind, ref = item["kind"], item["id"]
    if kind == "h5p":
        from app.models.h5p import H5PResult
        res = (db.query(H5PResult)
               .filter(H5PResult.content_id == ref, H5PResult.user_id == user_id)
               .order_by(H5PResult.score.desc()).first())
        if res and res.max_score:
            return float(res.score or 0), float(res.max_score)
        return None
    if kind == "game":
        from app.models.game import GameResult
        res = (db.query(GameResult)
               .filter(GameResult.game_id == ref, GameResult.user_id == user_id)
               .order_by(GameResult.score.desc()).first())
        if res and getattr(res, "max_score", 0):
            return float(res.score), float(res.max_score)
        return None
    if kind == "lab":
        from app.routers.virtual_labs import get_lab
        lab = get_lab(db, ref)
        if lab and lab.get('native_template') == 'concept_lab':
            from app.services.lab_investigation_service import best_score
            return best_score(db, ref, user_id, lab.get('config') or {})
        from app.models.content_library import VirtualLabResult
        res = (db.query(VirtualLabResult)
               .filter(VirtualLabResult.lab_slug == ref, VirtualLabResult.user_id == user_id)
               .order_by(VirtualLabResult.score.desc()).first())
        if res and res.max_score:
            return float(res.score), float(res.max_score)
        return None
    if kind == "three_d_task":
        try:
            from app.routers.three_d_tasks import best_task_score  # type: ignore
        except ImportError:
            return None
        return best_task_score(db, ref, user_id)
    return None
