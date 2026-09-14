"""Event-sourced gamification service (plan Task 9, spec D items 1-5,7).

Single entry point for every award in the platform: `award(db, user_id,
event_type, event_key, ...)`. Idempotent on `event_key` (a duplicate key
raises IntegrityError, caught here and treated as a no-op — the caller
never needs to pre-check). Every caller wraps this in try/except (see the
trigger points in courses.py/quizzes.py/assignments.py/course_service.py/
live_class_service.py/h5p.py) so an award failure NEVER fails the host
request — that contract lives at the CALL SITE, not here, but `award`
itself is written to degrade gracefully (flush + return None on failure)
rather than raise past a caller who forgot to guard.

TRANSACTION OWNERSHIP (post-review fix): `award()` never calls
`db.commit()`. It only `flush()`es — every trigger site (courses.py's
mark_lesson_complete, quizzes.py's submit/finalize, assignments.py's
submit/grade, course_service.calculate_course_progress,
live_class_service.award_attendance_xp via live_class_session.py's
end_class + live_class_attendance.py's recompute_attendance, h5p.py's
result endpoint) calls `award()` and then commits itself — either
immediately after (when the session had no other pending state at that
point) or deliberately sequenced AFTER that request's own unrelated commit
already landed (course completion, lesson completion, live-class
attendance finalization — see each call site's own comment for why).
Earlier this function ended with `db.commit()`, which committed the
CALLER's own pending, uncommitted changes mid-flight — so if the caller's
*own* subsequent commit then failed and rolled back (proven live:
`calculate_course_progress`'s `enrollment.completion_date`/
`enrollment_status` writes persisted even when the certificate-issuance
path after it failed), the gamification side-effect (and the caller's
unrelated mutation!) had already leaked out as a partial write with no way
to undo it. `award()` now stops at `flush()` in every branch — success,
duplicate-key no-op, and the outer failure handler — so whichever commit
governs a given call site correctly covers (or a rollback correctly
unwinds) the gamification rows together with everything else in that unit
of work.

Levels are computed from total_xp, never stored (spec D2):
    level_n threshold = 100 * n * (n+1) / 2   (L1=100, L2=300, L3=600, ...)

Streaks (spec D4) are maintained by `touch_streak`, called from inside
`award` itself — ANY award advances the day. `dashboard.py` and
`superadmin.py` read `UserGameStats.current_streak`/`longest_streak`
directly now, falling back to their own historical computation only when a
user has no stats row yet.

Badges (spec D3) are rule-evaluated after every award via
`_evaluate_badges`. The catalog is seeded lazily and idempotently by
`ensure_badges` (slug-keyed upsert-by-absence, safe to call every request —
it short-circuits once the 15 rows exist).

Leaderboard (spec D5) is Redis-cached 300s with the repo's MockRedis
fallback (app.core.redis) — never wrapped in asyncio.wait_for per the repo
convention.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.redis import RedisClient
from app.models.gamification import Badge, UserBadge, UserGameStats, XpEvent
from app.models.user import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Points table (spec D1)
# ---------------------------------------------------------------------------

DEFAULT_POINTS: Dict[str, int] = {
    "lesson_completed": 10,
    "quiz_passed": 20,
    "quiz_passed_bonus": 10,          # >= 90% on a quiz, awarded alongside quiz_passed
    "assignment_submitted": 10,
    "assignment_graded_pass": 15,     # graded, grade >= 50% of total_points
    "course_completed": 100,
    "live_class_attended": 25,
    "h5p_completed": 10,
    "daily_first_activity": 5,
    "game_completed": 20,             # first completed learning game with score>0 (spec §4)
    "game_perfect": 10,               # first score == max_score on a learning game (spec §4)
    "lab_completed": 20,              # virtual lab result with score>0 (Content Libraries)
    "lab_perfect": 10,
    "three_d_task_completed": 20,     # 3D match-and-verify attempt with score>0 (WP2)
    "three_d_task_perfect": 10,
}

QUIZ_BONUS_THRESHOLD_PCT = 90.0
ASSIGNMENT_PASS_FRACTION = 0.5  # "passing" = grade >= 50% of total_points (spec interpretation, task brief)

STREAK_MILESTONES: Dict[int, int] = {7: 50, 30: 200, 100: 500}

LEADERBOARD_CACHE_TTL_SECONDS = 300
LEADERBOARD_GLOBAL_LIMIT = 50
LEADERBOARD_COURSE_LIMIT = 20


# ---------------------------------------------------------------------------
# Level math (spec D2) — computed, never stored.
# ---------------------------------------------------------------------------

def xp_for_level(n: int) -> int:
    """Total XP required to REACH level n (n >= 1). level_n = 100*n*(n+1)/2."""
    if n < 1:
        return 0
    return 100 * n * (n + 1) // 2


def level_from_xp(total_xp: int) -> int:
    """Highest level whose threshold total_xp has met/exceeded. Level 0 if
    total_xp < xp_for_level(1) (100)."""
    if total_xp < xp_for_level(1):
        return 0
    # 100*n*(n+1)/2 <= xp  =>  n*(n+1) <= xp/50  ->  solve the quadratic and
    # walk down/up from the estimate to correct for rounding at the boundary.
    n = int((-1 + math.sqrt(1 + 4 * (total_xp / 50.0))) / 2)
    n = max(n, 1)
    while xp_for_level(n + 1) <= total_xp:
        n += 1
    while n > 0 and xp_for_level(n) > total_xp:
        n -= 1
    return n


def level_progress(total_xp: int) -> Dict[str, Any]:
    """Progress-ring shape the /me endpoint returns: current level, XP into
    the level, XP needed for the next level, and a 0-1 fraction."""
    level = level_from_xp(total_xp)
    floor_xp = xp_for_level(level)
    next_xp = xp_for_level(level + 1)
    span = next_xp - floor_xp
    into = total_xp - floor_xp
    return {
        "level": level,
        "total_xp": total_xp,
        "current_level_floor_xp": floor_xp,
        "next_level_xp": next_xp,
        "xp_into_level": into,
        "xp_to_next_level": max(next_xp - total_xp, 0),
        "progress_fraction": round(into / span, 4) if span > 0 else 1.0,
    }


# ---------------------------------------------------------------------------
# Badge catalog (spec D3, ~15 badges) — seeded lazily by ensure_badges.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _BadgeDef:
    slug: str
    name: str
    description: str
    icon: str
    rule_type: str
    rule_value: Optional[int] = None


BADGE_CATALOG: List[_BadgeDef] = [
    _BadgeDef("first-lesson", "First Steps", "Complete your first lesson.", "footprints", "lessons_completed", 1),
    _BadgeDef("course-finisher", "Course Finisher", "Complete your first course.", "graduation-cap", "courses_completed", 1),
    _BadgeDef("three-courses", "Triple Threat", "Complete 3 courses.", "trophy", "courses_completed", 3),
    _BadgeDef("quiz-ace", "Quiz Ace", "Score 90%+ on 5 quizzes.", "target", "quizzes_90_plus", 5),
    _BadgeDef("streak-7", "Week Warrior", "Reach a 7-day streak.", "flame", "streak", 7),
    _BadgeDef("streak-30", "Month Master", "Reach a 30-day streak.", "flame", "streak", 30),
    _BadgeDef("streak-100", "Century Streak", "Reach a 100-day streak.", "flame", "streak", 100),
    _BadgeDef("early-bird", "Early Bird", "Complete an activity before 7am.", "sunrise", "early_bird", None),
    _BadgeDef("night-owl", "Night Owl", "Complete an activity after 10pm.", "moon", "night_owl", None),
    _BadgeDef("live-regular", "Live Regular", "Attend 5 live classes.", "video", "live_classes_attended", 5),
    _BadgeDef("h5p-explorer", "H5P Explorer", "Complete an interactive H5P activity.", "puzzle", "h5p_completed", 1),
    _BadgeDef("assignment-perfect", "Perfectionist", "Score a perfect grade on an assignment.", "star", "assignment_perfect", None),
    _BadgeDef("xp-level-5", "Rising Star", "Reach level 5.", "sparkles", "level", 5),
    _BadgeDef("xp-level-10", "XP Legend", "Reach level 10.", "crown", "level", 10),
    _BadgeDef("five-lessons", "Getting Momentum", "Complete 5 lessons.", "footprints", "lessons_completed", 5),
    _BadgeDef("game_on", "Game On", "Completed your first learning game.", "gamepad-2", "games_completed", 1),
]


def ensure_badges(db: Session) -> None:
    """Idempotently seed the badge catalog. Cheap enough to call lazily on
    every award() (a single indexed slug lookup per missing row; short-
    circuits entirely once all 15 exist via one COUNT query)."""
    existing_count = db.query(func.count(Badge.id)).scalar() or 0
    if existing_count >= len(BADGE_CATALOG):
        return
    existing_slugs = {slug for (slug,) in db.query(Badge.slug).all()}
    added = False
    for b in BADGE_CATALOG:
        if b.slug in existing_slugs:
            continue
        db.add(Badge(
            slug=b.slug, name=b.name, description=b.description,
            icon=b.icon, rule_type=b.rule_type, rule_value=b.rule_value,
        ))
        added = True
    if added:
        try:
            # SAVEPOINT-scoped: ensure_badges is called lazily from inside
            # award()'s own transaction (via _evaluate_badges), which by
            # then already has an XpEvent + stats update pending — a plain
            # db.rollback() here on a concurrent-seeding race would discard
            # that pending state too (see award()'s docstring).
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            # Concurrent seeding race — another request already inserted the
            # same slugs. Fine, they exist now either way.
            pass


# ---------------------------------------------------------------------------
# Core award() entry point
# ---------------------------------------------------------------------------

def _get_or_create_stats(db: Session, user_id: int) -> UserGameStats:
    stats = db.query(UserGameStats).filter(UserGameStats.user_id == user_id).first()
    if stats is None:
        stats = UserGameStats(user_id=user_id, total_xp=0, current_streak=0, longest_streak=0)
        db.add(stats)
        db.flush()
    return stats


def _consume_streak_freeze(db: Session, stats: UserGameStats, today: date, missed_days: int) -> bool:
    """Spend `missed_days` streak freezes from this month's allowance (the
    max streak_freeze_days_per_month across the learner's courses — a
    Reward System Designer setting, WP6). Returns True when covered."""
    try:
        from app.services import studio_service
        allowance = studio_service.streak_freeze_allowance(db, stats.user_id)
    except Exception:
        return False
    if allowance <= 0:
        return False
    month = today.strftime('%Y-%m')
    if getattr(stats, 'streak_freeze_month', None) != month:
        stats.streak_freeze_month = month
        stats.streak_freezes_used = 0
    used = int(getattr(stats, 'streak_freezes_used', 0) or 0)
    if used + missed_days > allowance:
        return False
    stats.streak_freezes_used = used + missed_days
    return True


def touch_streak(db: Session, stats: UserGameStats, on_date: Optional[date] = None) -> List[XpEvent]:
    """Advance/reset the streak for a new day of activity. THE streak
    implementation (spec D4) — dashboard.py/superadmin.py read the result via
    UserGameStats, not their own computation, once a stats row exists.

    - Same calendar day as last_active_date: no-op (already counted today).
    - Exactly one day after last_active_date (or no prior date): streak +1.
    - Gap > 1 day: streak resets to 1.

    Returns any streak-milestone XpEvents created (7/30/100 -> +50/+200/+500,
    each with its own idempotent event_key so a milestone is awarded once).
    """
    today = on_date or datetime.now(timezone.utc).date()
    milestone_events: List[XpEvent] = []

    if stats.last_active_date == today:
        return milestone_events  # already touched today

    gap = (today - stats.last_active_date).days if stats.last_active_date is not None else None
    if gap == 1:
        stats.current_streak = (stats.current_streak or 0) + 1
    elif gap is not None and gap > 1 and _consume_streak_freeze(db, stats, today, gap - 1):
        stats.current_streak = (stats.current_streak or 0) + 1  # v2.0 §4 (WP6): freeze covered the missed days
    else:
        stats.current_streak = 1

    stats.longest_streak = max(stats.longest_streak or 0, stats.current_streak)
    stats.last_active_date = today

    milestone_points = STREAK_MILESTONES.get(stats.current_streak)
    if milestone_points:
        event_key = f"streak:{stats.current_streak}:user:{stats.user_id}"
        existing = db.query(XpEvent).filter(XpEvent.event_key == event_key).first()
        if existing is None:
            ev = XpEvent(
                user_id=stats.user_id,
                event_key=event_key,
                event_type=f"streak_milestone:{stats.current_streak}",
                points=milestone_points,
                meta={"seen": False, "streak": stats.current_streak},
            )
            db.add(ev)
            stats.total_xp = (stats.total_xp or 0) + milestone_points
            milestone_events.append(ev)

    return milestone_events


def _evaluate_badges(db: Session, user_id: int, stats: UserGameStats) -> List[UserBadge]:
    """Check every badge rule against the user's current state, awarding any
    newly-earned badge. Returns the newly-created UserBadge rows."""
    ensure_badges(db)

    already_earned = {
        badge_id for (badge_id,) in db.query(UserBadge.badge_id).filter(UserBadge.user_id == user_id).all()
    }
    all_badges = db.query(Badge).all()
    newly_awarded: List[UserBadge] = []

    for badge in all_badges:
        if badge.id in already_earned:
            continue
        if _badge_rule_satisfied(db, user_id, stats, badge):
            ub = UserBadge(user_id=user_id, badge_id=badge.id)
            try:
                # SAVEPOINT-scoped (see award()'s docstring for why a plain
                # db.rollback() here would be unsafe: this runs mid-way
                # through award()'s own transaction, with an XpEvent + stats
                # changes already pending).
                with db.begin_nested():
                    db.add(ub)
                    db.flush()
            except IntegrityError:
                # Concurrent award race for the same badge — fine, it exists.
                continue
            stats.badges_count = (stats.badges_count or 0) + 1
            event_key = f"badge:{badge.slug}:user:{user_id}"
            existing_ev = db.query(XpEvent).filter(XpEvent.event_key == event_key).first()
            if existing_ev is None:
                db.add(XpEvent(
                    user_id=user_id,
                    event_key=event_key,
                    event_type=f"badge:{badge.slug}",
                    points=0,
                    meta={"seen": False, "badge_slug": badge.slug, "badge_name": badge.name},
                ))
            newly_awarded.append(ub)

    return newly_awarded


def _utc_hour_expr(db: Session, column):
    """SQL expression for "hour-of-day of `column`, in UTC" — dialect-aware
    (M3 review fix).

    `XpEvent.created_at` is `DateTime(timezone=True)`. On Postgres, a plain
    `EXTRACT(HOUR FROM ts)` over a `timestamptz` column implicitly converts
    to the SESSION's `timezone` setting before extracting the hour — NOT
    necessarily UTC, so `early_bird`/`night_owl` could fire (or fail to
    fire) based on the DB session's configured timezone rather than the
    actual UTC instant the event happened at. `func.timezone("UTC", column)`
    forces that conversion to UTC explicitly before extracting.

    On SQLite there is no `timezone()` function and none is needed: this
    codebase's convention (see courses.py/course_service.py's `_as_utc`
    helpers) is that SQLite always stores naive datetimes that ARE already
    UTC (SQLite has no tz-aware storage at all — `DateTime(timezone=True)`
    degrades to naive on that dialect), so a plain `EXTRACT(HOUR FROM ...)`
    already reads the correct UTC hour there. Branching on `db.bind.dialect.name`
    (via `db.get_bind()`, which works for both a plain Session and one bound
    to an Engine) keeps both paths correct without a portable expression
    that would have to reimplement `timezone()` by hand.
    """
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return func.extract("hour", func.timezone("UTC", column))
    return func.extract("hour", column)


def _badge_rule_satisfied(db: Session, user_id: int, stats: UserGameStats, badge: Badge) -> bool:
    rt = badge.rule_type
    rv = badge.rule_value

    if rt == "lessons_completed":
        count = db.query(func.count(XpEvent.id)).filter(
            XpEvent.user_id == user_id, XpEvent.event_type == "lesson_completed"
        ).scalar() or 0
        return count >= (rv or 1)

    if rt == "courses_completed":
        count = db.query(func.count(XpEvent.id)).filter(
            XpEvent.user_id == user_id, XpEvent.event_type == "course_completed"
        ).scalar() or 0
        return count >= (rv or 1)

    if rt == "quizzes_90_plus":
        count = db.query(func.count(XpEvent.id)).filter(
            XpEvent.user_id == user_id, XpEvent.event_type == "quiz_passed_bonus"
        ).scalar() or 0
        return count >= (rv or 1)

    if rt == "streak":
        return (stats.longest_streak or 0) >= (rv or 1)

    if rt == "early_bird":
        return db.query(XpEvent.id).filter(
            XpEvent.user_id == user_id,
            _utc_hour_expr(db, XpEvent.created_at) < 7,
        ).first() is not None

    if rt == "night_owl":
        return db.query(XpEvent.id).filter(
            XpEvent.user_id == user_id,
            _utc_hour_expr(db, XpEvent.created_at) >= 22,
        ).first() is not None

    if rt == "live_classes_attended":
        count = db.query(func.count(XpEvent.id)).filter(
            XpEvent.user_id == user_id, XpEvent.event_type == "live_class_attended"
        ).scalar() or 0
        return count >= (rv or 1)

    if rt == "h5p_completed":
        count = db.query(func.count(XpEvent.id)).filter(
            XpEvent.user_id == user_id, XpEvent.event_type == "h5p_completed"
        ).scalar() or 0
        return count >= (rv or 1)

    if rt == "games_completed":
        count = db.query(func.count(XpEvent.id)).filter(
            XpEvent.user_id == user_id, XpEvent.event_type == "game_completed"
        ).scalar() or 0
        return count >= (rv or 1)

    if rt == "assignment_perfect":
        return db.query(XpEvent.id).filter(
            XpEvent.user_id == user_id, XpEvent.event_type == "assignment_perfect"
        ).first() is not None

    if rt == "level":
        return level_from_xp(stats.total_xp or 0) >= (rv or 1)

    return False


def award(
    db: Session,
    user_id: int,
    event_type: str,
    event_key: str,
    points: Optional[int] = None,
    course_id: Optional[int] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Optional[XpEvent]:
    """Idempotently record one XP event and keep UserGameStats/badges/streak
    in sync. No-op (returns None) on a duplicate event_key. Synchronous,
    best-effort by contract at the CALL SITE — every documented trigger
    point wraps this in try/except so a failure here never fails the host
    request.

    TRANSACTION OWNERSHIP: this function only ever `flush()`es — never
    `commit()`s. The CALLER owns the transaction boundary (see the module
    docstring's "TRANSACTION OWNERSHIP" note for the incident this fixed).
    Every trigger site either calls `award()` with a clean session (no
    unrelated pending changes) or deliberately AFTER its own unit of work
    has already committed, specifically so that this function's internal
    `db.rollback()` on an unexpected failure can only ever discard ITS OWN
    pending inserts — never a caller's unrelated mutation. Do not call this
    mid-transaction with other uncommitted changes still pending on `db`
    unless you have audited that a rollback here is safe for that call site
    too.

    Duplicate-event_key handling: checks for the duplicate with a plain
    SELECT first (the common, non-racy no-op path touches nothing), and
    only falls back to catching IntegrityError — scoped to a SAVEPOINT via
    `db.begin_nested()` so its rollback can never unwind anything but this
    function's own insert attempt — as a backstop for the rare
    concurrent-insert race.
    """
    resolved_points = DEFAULT_POINTS.get(event_type, 0) if points is None else points
    if course_id is not None:
        # v2.0 §4 (WP6): Reward System Designer per-course points override —
        # wins over both DEFAULT_POINTS and a trigger site's explicit value.
        # Events without course context (labs, 3D tasks, games played
        # outside a lesson) keep their defaults.
        try:
            from app.services import studio_service
            override = studio_service.points_override(db, course_id, event_type)
            if override is not None:
                resolved_points = override
        except Exception:
            logger.debug('studio points override lookup failed', exc_info=True)

    try:
        if db.query(XpEvent.id).filter(XpEvent.event_key == event_key).first() is not None:
            return None  # already awarded — no-op, caller's pending state untouched

        ev = XpEvent(
            user_id=user_id,
            event_key=event_key,
            event_type=event_type,
            points=resolved_points,
            course_id=course_id,
            meta=dict(meta or {}),
        )
        try:
            with db.begin_nested():  # SAVEPOINT — scopes any rollback to just this insert
                db.add(ev)
                db.flush()
        except IntegrityError:
            # Race: another concurrent award() inserted the same event_key
            # between our SELECT and this flush. The savepoint rollback
            # above already discarded only `ev` — the caller's own pending
            # changes on `db` are untouched.
            return None
    except Exception:
        logger.warning("gamification award() failed to insert XpEvent (event_key=%s)", event_key, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return None

    try:
        stats = _get_or_create_stats(db, user_id)
        stats.total_xp = (stats.total_xp or 0) + resolved_points

        # Any award advances the day (spec D1: "daily-first-activity ...
        # also advances streak" — read as: any event triggers touch_streak,
        # and the daily-first-activity award itself is granted below on the
        # FIRST touch of a new day).
        today = ev.created_at.date() if isinstance(ev.created_at, datetime) else datetime.now(timezone.utc).date()
        is_new_day = stats.last_active_date != today
        touch_streak(db, stats, on_date=today)

        if is_new_day and event_type != "daily_first_activity":
            daily_key = f"daily:{today.isoformat()}:user:{user_id}"
            existing_daily = db.query(XpEvent).filter(XpEvent.event_key == daily_key).first()
            if existing_daily is None:
                daily_points = DEFAULT_POINTS["daily_first_activity"]
                db.add(XpEvent(
                    user_id=user_id,
                    event_key=daily_key,
                    event_type="daily_first_activity",
                    points=daily_points,
                    meta={"seen": False},
                ))
                stats.total_xp = (stats.total_xp or 0) + daily_points

        level_before = level_from_xp((stats.total_xp or 0) - resolved_points)
        level_after = level_from_xp(stats.total_xp or 0)
        if level_after > level_before:
            level_key = f"level:{level_after}:user:{user_id}"
            existing_level_ev = db.query(XpEvent).filter(XpEvent.event_key == level_key).first()
            if existing_level_ev is None:
                db.add(XpEvent(
                    user_id=user_id,
                    event_key=level_key,
                    event_type="level_up",
                    points=0,
                    meta={"seen": False, "level": level_after},
                ))

        _evaluate_badges(db, user_id, stats)
        try:
            from app.services import studio_service
            studio_service.evaluate_course_badges(db, user_id, course_id)  # WP6 custom course badges
        except Exception:
            logger.debug('course badge evaluation failed', exc_info=True)

        # H1 review fix: flush only — award() never owns the transaction
        # boundary. The CALLER commits (every trigger site does, either
        # immediately after this call or via its own later commit that this
        # call was deliberately sequenced after — see the call sites in
        # courses.py/quizzes.py/assignments.py/course_service.py/
        # live_class_service.py/h5p.py). This is what makes the
        # gamification rows atomic with whatever else the caller's unit of
        # work touched: if the caller's own commit later fails and rolls
        # back, these flushed-but-uncommitted rows roll back with it
        # instead of having already leaked out via a premature commit here.
        db.flush()
    except Exception:
        logger.warning("gamification award() failed during stats/badge update (event_key=%s)", event_key, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return None

    return ev


# ---------------------------------------------------------------------------
# Streak read helpers (spec D4) — dashboard.py / superadmin.py call these
# instead of duplicating their own computation, falling back only when the
# user has no stats row yet.
# ---------------------------------------------------------------------------

def get_streak_for_user(db: Session, user_id: int) -> Optional[Dict[str, int]]:
    """Returns {"current_streak", "longest_streak"} from UserGameStats, or
    None if the user has no stats row yet (caller should fall back).

    M1 review fix: `current_streak` is only "alive" — i.e. returned as
    stored — when the user was active today or yesterday (matches the
    semantics of the retired `_compute_streaks`, which zeroed the current
    streak once more than a day had elapsed since the last active day).
    Without this, a user inactive for 60 days would still read a stale
    nonzero current_streak from the last time `touch_streak` ran, because
    `UserGameStats.current_streak` is only ever mutated on the NEXT award,
    not decayed by the passage of time on its own. `longest_streak` is a
    historical high-water mark and is always returned as stored.
    """
    stats = db.query(UserGameStats).filter(UserGameStats.user_id == user_id).first()
    if stats is None:
        return None

    current = stats.current_streak or 0
    if current > 0:
        today = datetime.now(timezone.utc).date()
        if stats.last_active_date is None or (today - stats.last_active_date).days > 1:
            current = 0

    return {
        "current_streak": current,
        "longest_streak": stats.longest_streak or 0,
    }


# ---------------------------------------------------------------------------
# Leaderboard (spec D5) — Redis 300s cache, MockRedis fallback = direct query.
# ---------------------------------------------------------------------------

async def _redis_get_json(key: str) -> Optional[Any]:
    try:
        client = await RedisClient.get_instance()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


async def _redis_set_json(key: str, value: Any, ttl: int) -> None:
    try:
        client = await RedisClient.get_instance()
        await client.setex(key, ttl, json.dumps(value))
    except Exception:
        # Cache is best-effort; a write failure must never break the read path.
        pass


def _course_user_ids(db: Session, course_id: int) -> List[int]:
    return [
        uid for (uid,) in
        db.query(XpEvent.user_id).filter(XpEvent.course_id == course_id).distinct().all()
    ]


def _parse_course_scope(scope: str) -> Optional[int]:
    if not scope.startswith("course:"):
        return None
    try:
        return int(scope.split(":", 1)[1])
    except ValueError:
        return None


def _leaderboard_query(db: Session, scope: str, limit: int) -> List[Dict[str, Any]]:
    q = (
        db.query(UserGameStats, User)
        .join(User, User.id == UserGameStats.user_id)
        .filter(UserGameStats.leaderboard_visible == True)  # noqa: E712
    )
    course_id = _parse_course_scope(scope)
    if course_id is not None:
        q = q.filter(UserGameStats.user_id.in_(_course_user_ids(db, course_id)))

    # M4 review fix: deterministic tie-break. total_xp DESC alone leaves the
    # order of tied users unspecified (SQL makes no ordering guarantee for
    # ties), which both reads inconsistently across requests/pages AND
    # disagrees with user_rank's competition-rank math below unless both use
    # the exact same tiebreak. user_id ASC is arbitrary but stable and cheap
    # (indexed PK) — documented here as the tie semantics for this feature:
    # among users with equal XP, the one who reached that total first (lower
    # user_id, a rough proxy — NOT literally "who leveled up first", just a
    # stable deterministic order) ranks higher.
    rows = q.order_by(UserGameStats.total_xp.desc(), UserGameStats.user_id.asc()).limit(limit).all()

    result = []
    for rank, (stats, user) in enumerate(rows, start=1):
        result.append({
            "rank": rank,
            "user_id": user.id,
            "display_name": user.display_name,
            "level": level_from_xp(stats.total_xp or 0),
            "total_xp": stats.total_xp or 0,
        })
    return result


async def leaderboard(db: Session, scope: str = "global", limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Top-N leaderboard entries (display_name + level + XP only — never
    email). scope is "global" or "course:{id}". Cached 300s in Redis
    (MockRedis in tests/dev = an in-process dict, so caching is transparent
    there too)."""
    resolved_limit = limit or (LEADERBOARD_COURSE_LIMIT if scope.startswith("course:") else LEADERBOARD_GLOBAL_LIMIT)
    cache_key = f"gamification:leaderboard:{scope}:{resolved_limit}"

    cached = await _redis_get_json(cache_key)
    if cached is not None:
        return cached

    result = _leaderboard_query(db, scope, resolved_limit)
    await _redis_set_json(cache_key, result, LEADERBOARD_CACHE_TTL_SECONDS)
    return result


def user_rank(
    db: Session,
    user_id: int,
    scope: str = "global",
    entries: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Caller's rank + XP within `scope`, regardless of their own visibility
    toggle (a user can always see their own rank).

    M2 review fix: if `entries` is given (the SAME list a prior `leaderboard()`
    call returned — pass it straight through, see the router) and the user
    appears in it, the rank is read directly off that entry instead of
    re-querying. This is what keeps one API response internally consistent:
    without it, `entries` reflects whatever was cached up to
    LEADERBOARD_CACHE_TTL_SECONDS ago while a fresh competition-rank query
    here reflects right now, so a user visible in the top-N could see an
    `entries[i].rank` that disagrees with `my_rank.rank` for the same user
    whenever XP changed in between (or another user's cache-vs-live-query
    tiebreak resolved differently — see M4). Falls back to the live
    competition-rank query (not cached; single indexed COUNT, cheap per
    request) when the user isn't in `entries` — out of the top-N, no
    `entries` was passed, or the user is leaderboard_visible=False (excluded
    from `entries` by construction, but their own rank is still computed:
    "regardless of their own visibility toggle" above).
    """
    stats = db.query(UserGameStats).filter(UserGameStats.user_id == user_id).first()
    if stats is None:
        return None

    if entries:
        for entry in entries:
            if entry.get("user_id") == user_id:
                return {
                    "rank": entry["rank"],
                    "total_xp": entry["total_xp"],
                    "level": entry["level"],
                }

    # M4 review fix: competition-rank tiebreak must match _leaderboard_query's
    # ORDER BY total_xp DESC, user_id ASC — "ahead of me" is total_xp
    # strictly greater, OR equal total_xp with a lower user_id (ranks
    # higher under that same tiebreak).
    my_xp = stats.total_xp or 0
    q = db.query(func.count(UserGameStats.id)).filter(
        UserGameStats.leaderboard_visible == True,  # noqa: E712
        or_(
            UserGameStats.total_xp > my_xp,
            and_(UserGameStats.total_xp == my_xp, UserGameStats.user_id < user_id),
        ),
    )
    course_id = _parse_course_scope(scope)
    if course_id is not None:
        q = q.filter(UserGameStats.user_id.in_(_course_user_ids(db, course_id)))

    ahead = q.scalar() or 0
    return {
        "rank": ahead + 1,
        "total_xp": my_xp,
        "level": level_from_xp(my_xp),
    }
