"""Gamification API (plan Task 9, spec D items 1-5,7) — mounted at
/api/v1/gamification.

Endpoints (all require auth; no admin role needed):
  GET  /me                       - stats + level progress + badges + recent events
  GET  /me/unseen                - badge/level-up XpEvents with meta.seen == false
  POST /me/unseen/mark-seen      - flip meta.seen -> true for the given event ids
  GET  /leaderboard               - top 50 (global) / top 20 (course:{id}) + caller's rank
  POST /me/settings               - {leaderboard_visible: bool}

Leaderboard entries expose display_name + level + XP only — never email
(spec D5). Only leaderboard_visible users are listed; a caller can always
see their OWN rank regardless of their own visibility toggle.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.gamification import Badge, UserBadge, UserGameStats, XpEvent
from app.models.user import User
from app.services import gamification_service as game
from app.services.auth_service import AuthService

router = APIRouter()


class UnseenMarkSeenIn(BaseModel):
    event_ids: List[int]


class SettingsIn(BaseModel):
    leaderboard_visible: bool


def _stats_out(stats: Optional[UserGameStats]) -> dict:
    total_xp = stats.total_xp if stats else 0
    progress = game.level_progress(total_xp or 0)
    return {
        "total_xp": total_xp or 0,
        "current_streak": stats.current_streak if stats else 0,
        "longest_streak": stats.longest_streak if stats else 0,
        "last_active_date": stats.last_active_date.isoformat() if stats and stats.last_active_date else None,
        "leaderboard_visible": stats.leaderboard_visible if stats else True,
        "badges_count": stats.badges_count if stats else 0,
        **progress,
    }


def _badge_out(badge: Badge, awarded_at) -> dict:
    return {
        "slug": badge.slug,
        "name": badge.name,
        "description": badge.description,
        "icon": badge.icon,
        "awarded_at": awarded_at.isoformat() if awarded_at else None,
    }


def _event_out(ev: XpEvent) -> dict:
    meta = ev.meta or {}
    return {
        "id": ev.id,
        "event_type": ev.event_type,
        "points": ev.points,
        "course_id": ev.course_id,
        "meta": meta,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


@router.get("/me")
async def get_my_gamification(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    stats = db.query(UserGameStats).filter(UserGameStats.user_id == current_user.id).first()

    badge_rows = (
        db.query(UserBadge, Badge)
        .join(Badge, Badge.id == UserBadge.badge_id)
        .filter(UserBadge.user_id == current_user.id)
        .order_by(UserBadge.awarded_at.desc())
        .all()
    )
    badges = [_badge_out(badge, ub.awarded_at) for ub, badge in badge_rows]

    recent_events = (
        db.query(XpEvent)
        .filter(XpEvent.user_id == current_user.id)
        .order_by(XpEvent.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "stats": _stats_out(stats),
        "badges": badges,
        "recent_events": [_event_out(ev) for ev in recent_events],
    }


@router.get("/me/unseen")
async def get_unseen_awards(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Badge/level-up/streak-milestone XpEvents not yet acknowledged by the
    client (meta.seen == false). Points-only events (lesson_completed etc.)
    are never marked unseen — only celebratory moments are surfaced here."""
    events = (
        db.query(XpEvent)
        .filter(XpEvent.user_id == current_user.id)
        .order_by(XpEvent.created_at.desc())
        .limit(200)
        .all()
    )
    unseen = [ev for ev in events if isinstance(ev.meta, dict) and ev.meta.get("seen") is False]
    return {"unseen": [_event_out(ev) for ev in unseen]}


@router.post("/me/unseen/mark-seen")
async def mark_unseen_seen(
    body: UnseenMarkSeenIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    if not body.event_ids:
        return {"updated": 0}

    events = (
        db.query(XpEvent)
        .filter(XpEvent.user_id == current_user.id, XpEvent.id.in_(body.event_ids))
        .all()
    )
    updated = 0
    for ev in events:
        if isinstance(ev.meta, dict) and ev.meta.get("seen") is False:
            new_meta = dict(ev.meta)
            new_meta["seen"] = True
            ev.meta = new_meta
            updated += 1
    if updated:
        db.commit()
    return {"updated": updated}


@router.get("/leaderboard")
async def get_leaderboard(
    scope: str = Query("global", description="'global' or 'course:{id}'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    if scope != "global" and not scope.startswith("course:"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scope must be 'global' or 'course:{id}'")

    if scope.startswith("course:"):
        # v2.0 §4 (WP6): Reward System Designer can switch a course leaderboard off.
        from app.services import studio_service
        try:
            cid = int(scope.split(":", 1)[1])
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scope must be 'global' or 'course:{id}'")
        if studio_service.leaderboard_opted_out(db, cid):
            return {"scope": scope, "entries": [], "my_rank": None, "opted_out": True}

    entries = await game.leaderboard(db, scope=scope)
    # M2 review fix: derive my_rank from the SAME cached `entries` list when
    # the caller is in it, so one response payload can never show
    # entries[i].rank disagreeing with my_rank.rank for the same user.
    my_rank = game.user_rank(db, current_user.id, scope=scope, entries=entries)

    return {
        "scope": scope,
        "entries": entries,
        "my_rank": my_rank,
    }


@router.post("/me/settings")
async def update_settings(
    body: SettingsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    stats = db.query(UserGameStats).filter(UserGameStats.user_id == current_user.id).first()
    if stats is None:
        stats = UserGameStats(user_id=current_user.id, total_xp=0, current_streak=0, longest_streak=0)
        db.add(stats)
    stats.leaderboard_visible = body.leaderboard_visible
    db.commit()
    db.refresh(stats)
    return _stats_out(stats)
