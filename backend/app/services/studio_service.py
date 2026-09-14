"""Studio faces service (v2.0 §4 — WP6).

* defaults_for_type — Parent View defaults (SP: attendance + completion only)
  and Reward defaults per course type; data, not code.
* parent_view — what a guardian may see for a course (consumed by the
  parents digest and the class-report guardian share).
* rewards — points overrides consumed by gamification.award(), custom course
  badges evaluated after every award (stored as XpEvents of type
  `course_badge`, idempotent), streak-freeze allowance (max across the
  learner's enrolled courses; consumed by touch_streak), leaderboard opt-out.
* term_schedule / clone_week — the SP Schedule Builder over live classes.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.course_settings import CourseStudioSettings

logger = logging.getLogger(__name__)

PARENT_VIEW_KEYS = ["attendance", "completion", "scores", "time_spent", "teacher_notes", "class_reports"]
BADGE_RULES = {"lessons_completed", "quizzes_passed", "live_classes_attended", "games_completed", "labs_completed", "streak_days"}
RULE_EVENT = {
    "lessons_completed": "lesson_completed", "quizzes_passed": "quiz_passed", "live_classes_attended": "live_class_attended",
    "games_completed": "game_completed", "labs_completed": "lab_completed",
}
OVERRIDABLE_EVENTS = {"lesson_completed", "quiz_passed", "quiz_passed_bonus", "assignment_submitted", "assignment_graded_pass",
                      "course_completed", "live_class_attended", "h5p_completed", "game_completed", "game_perfect",
                      "lab_completed", "lab_perfect", "three_d_task_completed", "three_d_task_perfect"}
MAX_BADGES = 12


def defaults_for_type(course_type: Optional[str]) -> Dict[str, Any]:
    ct = (course_type or "").lower()
    parent_view = {"attendance": True, "completion": True, "scores": False, "time_spent": False,
                   "teacher_notes": False, "class_reports": False}
    if ct == "utporul":
        parent_view.update({"scores": True})
    rewards = {"points": {}, "badges": [], "streak_freeze_days_per_month": 1 if ct == "seyappaduporul" else 0,
               "leaderboard_opt_out": False}
    face = {"meiporul": "asset_library", "seyappaduporul": "schedule", "utporul": "outcome"}.get(ct, "curriculum")
    return {"parent_view": parent_view, "rewards": rewards, "opening_face": face}


def _course_type(db: Session, course_id: int) -> Optional[str]:
    from app.models.course import Course
    c = db.query(Course.course_type).filter(Course.id == course_id).first()
    return c[0] if c else None


def get_settings(db: Session, course_id: int) -> Dict[str, Any]:
    d = defaults_for_type(_course_type(db, course_id))
    row = db.query(CourseStudioSettings).filter(CourseStudioSettings.course_id == course_id).first()
    if row:
        pv = dict(d["parent_view"]); pv.update({k: bool(v) for k, v in (row.parent_view or {}).items() if k in PARENT_VIEW_KEYS})
        rw = dict(d["rewards"]); rw.update(row.rewards or {})
        d["parent_view"], d["rewards"], d["face_dismissed"] = pv, rw, bool(row.face_dismissed)
    else:
        d["face_dismissed"] = False
    d["course_id"] = course_id
    return d


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-")[:40] or "badge"


def validate_rewards(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("rewards must be an object")
    points = raw.get("points") or {}
    if not isinstance(points, dict):
        raise ValueError("rewards.points must be an object")
    clean_points = {}
    for k, v in points.items():
        if k not in OVERRIDABLE_EVENTS:
            raise ValueError(f"unknown activity '{k}' (allowed: {sorted(OVERRIDABLE_EVENTS)})")
        if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v <= 1000):
            raise ValueError(f"points for '{k}' must be an integer 0..1000")
        clean_points[k] = v
    badges = raw.get("badges") or []
    if not isinstance(badges, list) or len(badges) > MAX_BADGES:
        raise ValueError(f"rewards.badges must be a list of at most {MAX_BADGES}")
    clean_badges, seen = [], set()
    for b in badges:
        if not isinstance(b, dict):
            raise ValueError("each badge must be an object")
        name = str(b.get("name") or "").strip()[:60]
        rule = b.get("rule")
        threshold = b.get("threshold")
        pts = b.get("points", 25)
        if not name:
            raise ValueError("badge name is required")
        if rule not in BADGE_RULES:
            raise ValueError(f"badge rule must be one of {sorted(BADGE_RULES)}")
        if isinstance(threshold, bool) or not isinstance(threshold, int) or not (1 <= threshold <= 1000):
            raise ValueError("badge threshold must be an integer 1..1000")
        if isinstance(pts, bool) or not isinstance(pts, int) or not (0 <= pts <= 1000):
            raise ValueError("badge points must be an integer 0..1000")
        slug = _slug(name)
        if slug in seen:
            raise ValueError(f"duplicate badge '{name}'")
        seen.add(slug)
        clean_badges.append({"name": name, "slug": slug, "rule": rule, "threshold": threshold, "points": pts})
    freeze = raw.get("streak_freeze_days_per_month", 0)
    if isinstance(freeze, bool) or not isinstance(freeze, int) or not (0 <= freeze <= 10):
        raise ValueError("streak_freeze_days_per_month must be an integer 0..10")
    opt_out = raw.get("leaderboard_opt_out", False)
    if not isinstance(opt_out, bool):
        raise ValueError("leaderboard_opt_out must be true/false")
    return {"points": clean_points, "badges": clean_badges, "streak_freeze_days_per_month": freeze, "leaderboard_opt_out": opt_out}


def validate_parent_view(raw: Any) -> Dict[str, bool]:
    if not isinstance(raw, dict):
        raise ValueError("parent_view must be an object")
    out = {}
    for k, v in raw.items():
        if k not in PARENT_VIEW_KEYS:
            raise ValueError(f"unknown parent_view key '{k}' (allowed: {PARENT_VIEW_KEYS})")
        if not isinstance(v, bool):
            raise ValueError(f"parent_view.{k} must be true/false")
        out[k] = v
    return out


def put_settings(db: Session, course_id: int, user_id: int, parent_view: Optional[dict] = None,
                 rewards: Optional[dict] = None, face_dismissed: Optional[bool] = None) -> Dict[str, Any]:
    row = db.query(CourseStudioSettings).filter(CourseStudioSettings.course_id == course_id).first()
    if row is None:
        row = CourseStudioSettings(course_id=course_id, parent_view={}, rewards={})
        db.add(row)
    if parent_view is not None:
        merged = dict(row.parent_view or {}); merged.update(validate_parent_view(parent_view)); row.parent_view = merged
    if rewards is not None:
        row.rewards = validate_rewards(rewards)
    if face_dismissed is not None:
        row.face_dismissed = bool(face_dismissed)
    row.updated_by = user_id
    db.commit()
    return get_settings(db, course_id)


# ---------------------------------------------------------------- consumers

def parent_view(db: Session, course_id: int) -> Dict[str, bool]:
    return get_settings(db, course_id)["parent_view"]


def points_override(db: Session, course_id: Optional[int], event_type: str) -> Optional[int]:
    if course_id is None:
        return None
    try:
        pts = get_settings(db, course_id)["rewards"].get("points") or {}
        v = pts.get(event_type)
        return int(v) if isinstance(v, int) and not isinstance(v, bool) else None
    except Exception:
        return None


def leaderboard_opted_out(db: Session, course_id: int) -> bool:
    try:
        return bool(get_settings(db, course_id)["rewards"].get("leaderboard_opt_out"))
    except Exception:
        return False


def streak_freeze_allowance(db: Session, user_id: int) -> int:
    """Max freeze days per month across the learner's enrolled courses (a
    streak is user-level, the allowance is a course-designer setting)."""
    try:
        from app.models.enrollment import Enrollment
        rows = db.query(Enrollment.course_id).filter(Enrollment.user_id == user_id,
                                                     Enrollment.enrollment_status.in_(["enrolled", "completed"])).all()
        best = 0
        for (cid,) in rows:
            best = max(best, int(get_settings(db, cid)["rewards"].get("streak_freeze_days_per_month") or 0))
        return best
    except Exception:
        return 0


def evaluate_course_badges(db: Session, user_id: int, course_id: Optional[int]) -> List[dict]:
    """Grant custom course badges whose thresholds are now met. Flush-only,
    idempotent on event_key; returns the badges granted in this call."""
    if course_id is None:
        return []
    from app.models.gamification import UserGameStats, XpEvent
    badges = get_settings(db, course_id)["rewards"].get("badges") or []
    if not badges:
        return []
    granted = []
    stats = db.query(UserGameStats).filter(UserGameStats.user_id == user_id).first()
    for b in badges:
        key = f"course_badge:{course_id}:{b['slug']}:user:{user_id}"
        if db.query(XpEvent.id).filter(XpEvent.event_key == key).first() is not None:
            continue
        if b["rule"] == "streak_days":
            count = int(stats.current_streak or 0) if stats else 0
        else:
            ev = RULE_EVENT[b["rule"]]
            q = db.query(XpEvent).filter(XpEvent.user_id == user_id, XpEvent.event_type == ev)
            if b["rule"] != "streak_days":
                q = q.filter(XpEvent.course_id == course_id)
            count = q.count()
        if count >= int(b["threshold"]):
            db.add(XpEvent(user_id=user_id, event_key=key, event_type="course_badge", points=int(b["points"]),
                           course_id=course_id, meta={"badge": b["name"], "slug": b["slug"], "rule": b["rule"],
                                                      "threshold": b["threshold"], "seen": False}))
            if stats is not None:
                stats.total_xp = (stats.total_xp or 0) + int(b["points"])
            granted.append(b)
    if granted:
        db.flush()
    return granted


def my_course_rewards(db: Session, user_id: int, course_id: int) -> Dict[str, Any]:
    from app.models.gamification import XpEvent
    s = get_settings(db, course_id)
    earned = {e.meta.get("slug"): e for e in db.query(XpEvent)
              .filter(XpEvent.user_id == user_id, XpEvent.course_id == course_id, XpEvent.event_type == "course_badge").all()
              if e.meta}
    points_here = sum(int(e.points or 0) for e in db.query(XpEvent)
                      .filter(XpEvent.user_id == user_id, XpEvent.course_id == course_id).all())
    badges = []
    for b in s["rewards"].get("badges") or []:
        if b["rule"] == "streak_days":
            from app.models.gamification import UserGameStats
            st = db.query(UserGameStats).filter(UserGameStats.user_id == user_id).first()
            progress = int(st.current_streak or 0) if st else 0
        else:
            progress = db.query(XpEvent).filter(XpEvent.user_id == user_id, XpEvent.course_id == course_id,
                                                XpEvent.event_type == RULE_EVENT[b["rule"]]).count()
        badges.append({**b, "earned": b["slug"] in earned, "progress": min(progress, b["threshold"])})
    return {"course_id": course_id, "points_in_course": points_here, "badges": badges,
            "leaderboard_opt_out": bool(s["rewards"].get("leaderboard_opt_out")),
            "streak_freeze_days_per_month": int(s["rewards"].get("streak_freeze_days_per_month") or 0)}


# ---------------------------------------------------------------- schedule builder (§4.2)

def _utc(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def term_schedule(db: Session, course_id: int) -> Dict[str, Any]:
    from app.models.live_class import LiveClass
    from app.models.course import Lesson
    from app.models.quiz import Quiz
    classes = (db.query(LiveClass).filter(LiveClass.course_id == course_id, LiveClass.deleted_at.is_(None))
               .order_by(LiveClass.scheduled_start.asc()).all())
    weeks: Dict[str, dict] = {}
    for c in classes:
        start = _utc(c.scheduled_start)
        monday = (start - timedelta(days=start.weekday())).date()
        w = weeks.setdefault(monday.isoformat(), {"week_start": monday.isoformat(), "sessions": []})
        w["sessions"].append({
            "kind": "live", "class_id": c.id, "title": c.title, "start": start, "end": _utc(c.scheduled_end),
            "status": c.status.value if c.status else None, "purpose": getattr(c, "purpose", None),
            "mode": getattr(c, "mode", None), "has_recording": bool(c.recording_video_id),
        })
    lessons = db.query(Lesson).filter(Lesson.post_parent == course_id).count()
    quizzes = db.query(Quiz).filter(Quiz.post_parent == course_id).count()
    return {"course_id": course_id, "weeks": sorted(weeks.values(), key=lambda w: w["week_start"]),
            "live_classes": len(classes), "recorded_lessons": lessons, "assessments": quizzes}


def clone_week(db: Session, course_id: int, instructor_id: int, from_week_start: date, to_week_start: date) -> List[int]:
    """Copy every live class of one week into another (same weekday/time,
    fresh room, scheduled). Returns the new class ids."""
    from app.models.live_class import LiveClass, LiveClassStatus
    from app.services.live_class_service import generate_room_name
    if to_week_start == from_week_start:
        raise ValueError("target week must differ from the source week")
    delta = timedelta(days=(to_week_start - from_week_start).days)
    lo = datetime.combine(from_week_start, datetime.min.time(), tzinfo=timezone.utc)
    hi = lo + timedelta(days=7)
    src = (db.query(LiveClass).filter(LiveClass.course_id == course_id, LiveClass.deleted_at.is_(None),
                                      LiveClass.scheduled_start >= lo, LiveClass.scheduled_start < hi).all())
    if not src:
        raise ValueError("no live classes in the source week")
    new_ids = []
    for c in src:
        lc = LiveClass(schedule_id=c.schedule_id, course_id=course_id, lesson_id=c.lesson_id, instructor_id=instructor_id,
                       title=c.title, description=c.description, scheduled_start=_utc(c.scheduled_start) + delta,
                       scheduled_end=_utc(c.scheduled_end) + delta, timezone=c.timezone, room_name=generate_room_name(),
                       status=LiveClassStatus.SCHEDULED, settings=dict(c.settings or {}),
                       purpose=getattr(c, "purpose", None), mode=getattr(c, "mode", None),
                       audience=getattr(c, "audience", None), recording_policy=getattr(c, "recording_policy", None))
        db.add(lc)
        db.flush()
        new_ids.append(lc.id)
    db.commit()
    return new_ids
