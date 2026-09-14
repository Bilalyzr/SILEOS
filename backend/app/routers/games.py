"""Learning Games API (spec §3) — mounted at /api/v1/games.

redirect_slashes=False: every path here is declared WITHOUT a trailing
slash (create is @router.post("")), and '/games' is in axios.ts's
noSlashEndpoints — the gamification-404 lesson.

Ownership (spec §3/§7): configs are owner/admin-only ALWAYS — another
instructor can never read a game's config, draft or published. Students
get published games only through /play (Task 4), gated by enrollment in a
course whose lesson references the game.

Task 4 review ruling (documented, no behavior change): an instructor who is
NOT the owner but enrolls as a student in a course carrying the game's
lesson CAN read the config (including answers) via GET /play. This is
correct, not a leak: /play is the play surface, and every enrolled player
— instructor or student — gets the same advisory-scored payload by design
(grading is client-side; see the class docstring on get_game_play). The
§3 "other instructors never read configs" invariant governs the
CRUD/authoring surface only (GET /{game_id} correctly 403s a non-owner
instructor regardless of their enrollment). Do not re-litigate this in a
later review — the two surfaces have deliberately different access rules.

Response style: plain dicts, no envelopes (matches h5p.py/gradebook.py).
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Lesson
from app.models.enrollment import Enrollment
from app.models.game import Game, GameResult
from app.models.user import User
from app.schemas.game_config import (
    GameConfigError,
    derive_max_score,
    validate_game_config,
)
from app.services.auth_service import AuthService

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_DURATION_S = 86400


class GameCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    template: str
    config: dict


class GameUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    config: Optional[dict] = None


class GameResultSubmit(BaseModel):
    # StrictInt: matches game_config.py's standard (see answer_index/
    # category_index) -- rejects bool/str coercion (True -> 1, "15" -> 15).
    score: StrictInt
    max_score: StrictInt
    duration_s: StrictInt = 0


def _get_game_or_404(db: Session, game_id: int) -> Game:
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return game


def _require_owner_or_admin(game: Game, current_user: User) -> None:
    if game.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this game",
        )


def _attached_lessons(db: Session, game_id: int):
    return db.query(Lesson).filter(Lesson.game_id == game_id).all()


def _game_dict(game: Game, include_config: bool = True) -> dict:
    d = {
        "id": game.id,
        "owner_id": game.owner_id,
        "title": game.title,
        "template": game.template,
        "status": game.status,
        "item_count": len((game.config or {}).get("items") or []),
        "max_score": derive_max_score(game.template, game.config),
        "created_at": game.created_at,
        "updated_at": game.updated_at,
    }
    if include_config:
        d["config"] = game.config
    return d


@router.post("")
async def create_game(
    payload: GameCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Create a draft game. Config fully validated per template."""
    try:
        normalized = validate_game_config(payload.template, payload.config)
    except GameConfigError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)

    game = Game(
        owner_id=current_user.id,
        title=payload.title.strip(),
        template=payload.template,
        config=normalized,
        status="draft",
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return _game_dict(game)


@router.get("/marketplace")
async def list_marketplace_games(
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_user),
):
    """Marketplace v1: published games from every instructor, insertable
    into any course (attribution preserved via owner)."""
    from sqlalchemy import or_
    rows = (db.query(Game)
            .filter(Game.status == "published", Game.is_listed == True)  # noqa: E712
            .order_by(Game.created_at.desc()).limit(100).all())
    return {"games": [
        {"id": g.id, "title": g.title, "template": g.template,
         "owner_id": g.owner_id, "source": "marketplace"}
        for g in rows
    ]}


@router.post("/{game_id}/list")
async def toggle_marketplace_listing(
    game_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your game")
    game.is_listed = bool(payload.get("listed", True))
    db.commit()
    return {"id": game.id, "is_listed": game.is_listed}


@router.get("/mine")
async def list_my_games(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Own games (instructor); admin sees all. Summary rows only (no config)."""
    query = db.query(Game)
    if current_user.role != "admin":
        query = query.filter(Game.owner_id == current_user.id)
    games = query.order_by(Game.updated_at.desc()).all()

    # attached_lesson_count in one grouped query instead of N+1.
    counts = dict(
        db.query(Lesson.game_id, func.count(Lesson.id))
        .filter(Lesson.game_id.in_([g.id for g in games]))
        .group_by(Lesson.game_id)
        .all()
    ) if games else {}

    rows = []
    for g in games:
        row = _game_dict(g, include_config=False)
        row["attached_lesson_count"] = counts.get(g.id, 0)
        rows.append(row)
    return {"games": rows, "count": len(rows)}


@router.get("/{game_id}")
async def get_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Full game incl. config — owner/admin only, ALWAYS (spec §3: any other
    instructor cannot read configs, draft or published)."""
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)
    return _game_dict(game)


@router.put("/{game_id}")
async def update_game(
    game_id: int,
    payload: GameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Update title/config (owner/admin). Re-validates config; allowed while
    published (spec §3)."""
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)

    if payload.config is not None:
        try:
            game.config = validate_game_config(game.template, payload.config)
        except GameConfigError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
    if payload.title is not None:
        game.title = payload.title.strip()

    db.commit()
    db.refresh(game)
    return _game_dict(game)


@router.post("/{game_id}/publish")
async def publish_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Publish re-runs FULL config validation (spec §1: re-validated at publish)."""
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)
    try:
        validate_game_config(game.template, game.config)
    except GameConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish: {exc.detail}",
        )
    game.status = "published"
    db.commit()
    db.refresh(game)
    return _game_dict(game)


@router.post("/{game_id}/unpublish")
async def unpublish_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)
    attached = _attached_lessons(db, game.id)
    if attached:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot unpublish: {len(attached)} lesson(s) still use this game. "
                "Detach it from those lessons first."
            ),
        )
    game.status = "draft"
    db.commit()
    db.refresh(game)
    return _game_dict(game)


@router.delete("/{game_id}")
async def delete_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)
    attached = _attached_lessons(db, game.id)
    if attached:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete: {len(attached)} lesson(s) still use this game. "
                "Detach it from those lessons first."
            ),
        )
    db.query(GameResult).filter(GameResult.game_id == game.id).delete()
    db.delete(game)
    db.commit()
    return {"success": True, "id": game_id}


def _course_ids_with_game_lesson(db: Session, game_id: int) -> set:
    return {
        lesson.post_parent
        for lesson in db.query(Lesson).filter(Lesson.game_id == game_id).all()
    }


def _user_enrolled_for_game(db: Session, game: Game, current_user: User) -> bool:
    """Active enrollment in ANY course containing a lesson attached to this
    game (mirrors h5p.py's _course_for_content_access status filter)."""
    course_ids = _course_ids_with_game_lesson(db, game.id)
    if not course_ids:
        return False
    return (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id.in_(course_ids),
            Enrollment.enrollment_status.notin_(["cancelled", "suspended"]),
        )
        .first()
        is not None
    )


def _gate_play(db: Session, game: Game, current_user: User) -> bool:
    """Shared gate for /play and POST /results. Returns is_preview.
    Owner/admin: always allowed (preview). Others: game must be published
    (404 hides drafts entirely) AND the caller enrolled via an attached
    lesson (403 otherwise)."""
    if game.owner_id == current_user.id or current_user.role == "admin":
        return True
    if game.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    if not _user_enrolled_for_game(db, game, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in a course containing this game to play it",
        )
    return False


@router.get("/{game_id}/play")
async def get_game_play(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user),
):
    """Playable payload. Includes answers — grading is client-side for
    instant feedback, so scores are ADVISORY ONLY and never enter the
    gradebook (spec §3; matches the H5P advisory-score decision)."""
    game = _get_game_or_404(db, game_id)
    if current_user is None:
        # Public-preview lessons (2026-09-05): visitors get the payload only when
        # a public-preview lesson in a published course embeds this game.
        from app.services.public_preview import require_anonymous_preview
        if game.status != "published":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
        require_anonymous_preview(db, "game_id", game_id, "This game")
        is_preview = True   # nothing is recorded for a visitor
    else:
        is_preview = _gate_play(db, game, current_user)
    return {
        "id": game.id,
        "title": game.title,
        "template": game.template,
        "config": game.config,
        "max_score": derive_max_score(game.template, game.config),
        "preview": is_preview,
    }


@router.post("/{game_id}/results")
async def submit_game_result(
    game_id: int,
    payload: GameResultSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    """Record one advisory attempt. Server recomputes max_score from config
    and clamps score/duration — the client-reported numbers are never
    trusted. Owner/admin preview writes NOTHING ({"preview": true} skip)."""
    game = _get_game_or_404(db, game_id)
    is_preview = _gate_play(db, game, current_user)
    if is_preview:
        return {"preview": True}

    derived_max = derive_max_score(game.template, game.config)
    score = max(0, min(int(payload.score), derived_max))
    duration_s = max(0, min(int(payload.duration_s), MAX_DURATION_S))

    result = GameResult(
        game_id=game.id,
        user_id=current_user.id,
        score=score,
        max_score=derived_max,
        duration_s=duration_s,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    # Gamification (spec §4). Sequenced AFTER the result row's own commit so
    # award()'s flush-only contract holds: this commit/rollback covers ONLY
    # the gamification rows. Best-effort — an XP hiccup never fails the POST.
    try:
        from app.services.gamification_service import award as _award_xp

        course_ids = _course_ids_with_game_lesson(db, game.id)
        course_id = min(course_ids) if course_ids else None

        if score > 0:
            _award_xp(
                db, current_user.id, "game_completed",
                event_key=f"game:{game.id}:completed:user:{current_user.id}",
                course_id=course_id,
                meta={"game_id": game.id, "template": game.template},
            )
        if score == derived_max:
            _award_xp(
                db, current_user.id, "game_perfect",
                event_key=f"game:{game.id}:perfect:user:{current_user.id}",
                course_id=course_id,
                meta={"game_id": game.id, "template": game.template},
            )
        db.commit()
    except Exception as game_err:
        logger.warning("Gamification award failed for game result: %s", game_err)
        try:
            db.rollback()
        except Exception:
            pass

    # Mastery graph (v2.0 §9.5) — best-effort, after the result + XP commits.
    from app.services.mastery_service import safe_record_evidence
    safe_record_evidence(db, user_id=current_user.id, kind="game", ref_id=game.id, score=float(score),
                         max_score=float(derived_max), course_id=course_id)

    best_score = (
        db.query(func.max(GameResult.score))
        .filter(GameResult.game_id == game.id, GameResult.user_id == current_user.id)
        .scalar()
        or 0
    )
    return {
        "game_id": game.id,
        "user_id": current_user.id,
        "score": result.score,
        "max_score": result.max_score,
        "duration_s": result.duration_s,
        "best_score": best_score,
        "created_at": result.created_at,
    }


@router.get("/{game_id}/results")
async def list_game_results(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Owner/admin: per-student best score, attempts, last played.
    display_name ONLY — never emails (spec §3).

    best_score's max_score must come from the SAME row as the best score
    (a config edit can shrink/grow derived max_score between attempts, so
    independently taking max(score) and max(max_score) across a student's
    rows can pair a score with a max_score from a DIFFERENT attempt — a
    chimera pairing that never actually happened). A window function
    ranks each student's rows by score desc, created_at desc, id desc
    (tie-break: most recent), and rank 1 supplies the paired max_score —
    bounded to two queries total, no N+1. id.desc() is the FINAL tie-break
    key because created_at has only second-level resolution on SQLite
    (server_default=func.now()) — two same-score attempts landing in the
    same second would otherwise make rank 1 implementation-defined; id is
    strictly increasing (autoincrement PK) so it deterministically picks
    the later-inserted row when created_at ties."""
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)

    ranked = (
        select(
            GameResult.user_id,
            GameResult.score,
            GameResult.max_score,
            func.row_number()
            .over(
                partition_by=GameResult.user_id,
                order_by=(
                    GameResult.score.desc(),
                    GameResult.created_at.desc(),
                    GameResult.id.desc(),
                ),
            )
            .label("rn"),
        )
        .where(GameResult.game_id == game.id)
        .subquery()
    )
    best_rows = {
        row.user_id: row
        for row in db.execute(select(ranked).where(ranked.c.rn == 1)).all()
    }

    rollup = (
        db.query(
            GameResult.user_id,
            func.count(GameResult.id).label("attempts"),
            func.max(GameResult.created_at).label("last_played"),
        )
        .filter(GameResult.game_id == game.id)
        .group_by(GameResult.user_id)
        .all()
    )
    user_ids = [row.user_id for row in rollup]
    users_by_id = {
        u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    rows = [{
        "user_id": row.user_id,
        "user_name": users_by_id[row.user_id].display_name if row.user_id in users_by_id else "Unknown",
        "best_score": best_rows[row.user_id].score,
        "max_score": best_rows[row.user_id].max_score,
        "attempts": row.attempts,
        "last_played": row.last_played,
    } for row in rollup]
    return {"game_id": game.id, "results": rows, "count": len(rows)}
