"""Event-sourced gamification models (plan Task 9, spec D items 1-5,7).

`XpEvent` is the append-only ledger — one row per award, idempotent on
`event_key` (a caller-constructed string like `lesson:123:completed:user:9`;
a duplicate key is caught as an IntegrityError by
app.services.gamification_service.award and treated as a no-op). `meta`
carries a `{"seen": false}` marker for badge/level-up events so the frontend
can poll GET /api/v1/gamification/me/unseen and mark them seen once shown.

`UserGameStats` is the derived, transactionally-maintained summary row per
user — the single source of truth for total XP, level (computed from XP, not
stored), and streaks. `dashboard.py`'s `_compute_streaks` and
`superadmin.py`'s `streak_map` both read from this table now, falling back to
their own historical computation only when a user has no stats row yet (spec
D4).

`Badge` is the seeded rule catalog (~15 rows, see
gamification_service.ensure_badges); `UserBadge` is the award join row,
unique per (user_id, badge_id).
"""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class XpEvent(Base):
    """Append-only XP ledger. One row per award; `event_key` is the
    idempotency key so the same trigger firing twice (retry, duplicate
    webhook-like call) never double-awards."""
    __tablename__ = "xp_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Idempotency key, e.g. "lesson:123:completed:user:9". Unique across the
    # whole table (not scoped to user_id) since the key already embeds the
    # user, matching the spec's example verbatim.
    event_key = Column(String(120), unique=True, nullable=False, index=True)

    # e.g. "lesson_completed", "quiz_passed", "badge:first-lesson",
    # "level_up", "streak_milestone:7".
    event_type = Column(String(40), nullable=False, index=True)

    points = Column(Integer, nullable=False, default=0)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)

    # Free-form context (e.g. {"quiz_id": 5, "percentage": 92}) plus the
    # unseen-awards marker {"seen": false} for badge/level-up events.
    meta = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<XpEvent(id={self.id}, user_id={self.user_id}, type={self.event_type}, points={self.points})>"


class UserGameStats(Base):
    """One row per user — the maintained summary gamification_service.award
    keeps in sync with the xp_events ledger inside the same transaction."""
    __tablename__ = "user_game_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    total_xp = Column(Integer, nullable=False, default=0)

    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    # DATE, not DateTime — streak math compares calendar days in UTC.
    last_active_date = Column(Date, nullable=True)

    # Opt-out toggle (spec D5) — default True, flipped via
    # POST /api/v1/gamification/me/settings.
    leaderboard_visible = Column(Boolean, nullable=False, default=True)

    badges_count = Column(Integer, nullable=False, default=0)

    # v2.0 §4 (WP6) streak freezes: course-designer allowance per month
    # (studio_service.streak_freeze_allowance) consumed by touch_streak.
    streak_freeze_month = Column(String(7), nullable=True)   # 'YYYY-MM'
    streak_freezes_used = Column(Integer, nullable=False, default=0)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<UserGameStats(user_id={self.user_id}, total_xp={self.total_xp}, streak={self.current_streak})>"


class Badge(Base):
    """Seeded rule-based badge catalog (spec D3, ~15 rows). Seeded lazily
    and idempotently by gamification_service.ensure_badges."""
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(60), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(String(255), nullable=False, default="")
    # lucide-react icon name (frontend maps this string to a <Icon /> import).
    icon = Column(String(40), nullable=False, default="award")

    # Machine-readable rule the service evaluates after each award — see
    # gamification_service.BADGE_RULES for the rule_type -> checker mapping.
    rule_type = Column(String(40), nullable=False)
    rule_value = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Badge(slug={self.slug}, rule_type={self.rule_type}, rule_value={self.rule_value})>"


class UserBadge(Base):
    """Award join row — a user earns a badge at most once."""
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False, index=True)

    awarded_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )

    def __repr__(self):
        return f"<UserBadge(user_id={self.user_id}, badge_id={self.badge_id})>"
