"""Learner retention loop (roadmap item 3, 2026-09-06).

Four rules, each idempotent through the notification row it creates
(type + related_id + created_at window), run from the reminders loop:

  streak_nudge      — streak ≥ 2 and last active yesterday → "don't break it" (once per day)
  near_certificate  — course progress ≥ 80% and not completed → "N lessons to go" (once per course)
  reengage          — enrolled ≥ 7 days, no lesson touched for 7 days → nudge (once per 14 days per course)
  weekly_digest     — lessons completed / XP gained / streak this week (once per 7 days per learner)

This service creates in-app notification rows. Email and account-wide WhatsApp
delivery belong to their dedicated channel services; this retention pass does
not send WhatsApp messages.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

NEAR_CERT_PCT = 80
REENGAGE_AFTER_DAYS = 7
REENGAGE_EVERY_DAYS = 14
DIGEST_EVERY_DAYS = 7
ACTIVE_STATUSES = ("enrolled", "completed")


def _sent_since(
    db: Session,
    user_id: int,
    ntype: str,
    since: Optional[datetime],
    related_id: Optional[int] = None,
    link: Optional[str] = None,
) -> bool:
    from app.models.notification import Notification

    q = db.query(Notification.id).filter(
        Notification.user_id == user_id, Notification.type == ntype
    )
    if related_id is not None:
        q = q.filter(Notification.related_id == related_id)
    if link is not None:
        q = q.filter(Notification.link == link)
    if since is not None:
        q = q.filter(Notification.created_at >= since)
    return q.first() is not None


def _notify(
    db: Session,
    user_id: int,
    ntype: str,
    title: str,
    message: str,
    link: str,
    related_id: Optional[int],
) -> bool:
    from app.services.notification_service import create_notification

    try:
        create_notification(
            db,
            user_id=user_id,
            type=ntype,
            title=title,
            message=message,
            link=link,
            related_id=related_id,
        )
        return True
    except Exception:
        db.rollback()
        logger.exception("retention notification failed (%s user=%s)", ntype, user_id)
        return False


def streak_nudges(db: Session, today: date) -> int:
    from app.models.gamification import UserGameStats

    yesterday = today - timedelta(days=1)
    start_of_day = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    sent = 0
    rows = (
        db.query(UserGameStats)
        .filter(
            UserGameStats.current_streak >= 2,
            UserGameStats.last_active_date == yesterday,
        )
        .all()
    )
    for st in rows:
        if _sent_since(db, st.user_id, "streak_nudge", start_of_day):
            continue
        if _notify(
            db,
            st.user_id,
            "streak_nudge",
            f"Keep your {st.current_streak}-day streak alive",
            "One lesson, quiz or lab today keeps it going. Freezes cover a missed day only if your course allows them.",
            "/dashboard",
            None,
        ):
            sent += 1
    return sent


def near_certificate(db: Session) -> int:
    from app.models.course import Course
    from app.models.enrollment import Enrollment

    sent = 0
    rows = (
        db.query(Enrollment, Course)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(
            Enrollment.enrollment_status == "enrolled",
            Enrollment.course_progress_percentage >= NEAR_CERT_PCT,
        )
        .all()
    )
    for enr, course in rows:
        if _sent_since(db, enr.user_id, "near_certificate", None, related_id=course.id):
            continue
        remaining = max(
            0, int(enr.total_lessons or 0) - int(enr.completed_lessons or 0)
        )
        what = (
            f"{remaining} lesson{'s' if remaining != 1 else ''} to go"
            if remaining
            else "almost there"
        )
        if _notify(
            db,
            enr.user_id,
            "near_certificate",
            f"You're {int(enr.course_progress_percentage)}% through {course.post_title}",
            f"{what} — finish and your certificate is issued automatically.",
            f"/courses/{course.id}",
            course.id,
        ):
            sent += 1
    return sent


def reengage(db: Session, now: datetime) -> int:
    from app.models.course import Course
    from app.models.enrollment import Enrollment, LessonProgress

    cutoff = now - timedelta(days=REENGAGE_AFTER_DAYS)
    window = now - timedelta(days=REENGAGE_EVERY_DAYS)
    sent = 0
    rows = (
        db.query(Enrollment, Course)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(
            Enrollment.enrollment_status == "enrolled",
            Enrollment.enrollment_date <= cutoff,
            Enrollment.course_progress_percentage < 100,
        )
        .all()
    )
    for enr, course in rows:
        last = (
            db.query(func.max(LessonProgress.updated_at))
            .filter(
                LessonProgress.user_id == enr.user_id,
                LessonProgress.course_id == course.id,
            )
            .scalar()
        )
        if last is not None:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last > cutoff:
                continue
        if _sent_since(db, enr.user_id, "reengage", window, related_id=course.id):
            continue
        if _notify(
            db,
            enr.user_id,
            "reengage",
            f"{course.post_title} is waiting for you",
            "It has been a week. Pick up the next lesson — five minutes is enough to get back into it.",
            f"/courses/{course.id}",
            course.id,
        ):
            sent += 1
    return sent


def weekly_digest(db: Session, now: datetime) -> int:
    from app.models.enrollment import Enrollment, LessonProgress
    from app.models.gamification import UserGameStats, XpEvent

    window = now - timedelta(days=DIGEST_EVERY_DAYS)
    sent = 0
    learners = [
        uid
        for (uid,) in db.query(Enrollment.user_id)
        .filter(Enrollment.enrollment_status.in_(ACTIVE_STATUSES))
        .distinct()
        .all()
    ]
    for uid in learners:
        if _sent_since(db, uid, "weekly_digest", window):
            continue
        lessons = (
            db.query(func.count(LessonProgress.id))
            .filter(
                LessonProgress.user_id == uid,
                LessonProgress.progress_status == "completed",
                LessonProgress.completion_date >= window,
            )
            .scalar()
            or 0
        )
        xp = (
            db.query(func.coalesce(func.sum(XpEvent.points), 0))
            .filter(XpEvent.user_id == uid, XpEvent.created_at >= window)
            .scalar()
            or 0
        )
        st = db.query(UserGameStats).filter(UserGameStats.user_id == uid).first()
        streak = int(st.current_streak or 0) if st else 0
        if lessons == 0 and xp == 0 and streak == 0:
            continue  # nothing to say — the re-engagement rule handles silence
        if _notify(
            db,
            uid,
            "weekly_digest",
            "Your week in numbers",
            f"{lessons} lesson{'s' if lessons != 1 else ''} completed · {int(xp)} XP earned · {streak}-day streak. Keep going.",
            "/dashboard",
            None,
        ):
            sent += 1
    return sent


def retention_pass(db: Session, now: Optional[datetime] = None) -> Dict[str, int]:
    now = now or datetime.now(timezone.utc)
    from app.services.learning_planner_service import planner_pass

    out: Dict[str, int] = {}
    for name, fn in (
        ("streak_nudge", lambda: streak_nudges(db, now.date())),
        ("near_certificate", lambda: near_certificate(db)),
        ("reengage", lambda: reengage(db, now)),
        ("weekly_digest", lambda: weekly_digest(db, now)),
        ("hot_segment", lambda: hot_segment_alerts(db, now)),
        ("planner", lambda: planner_pass(db, now)),
    ):
        try:
            out[name] = fn()
        except Exception:
            db.rollback()
            logger.exception("retention rule %s failed", name)
            out[name] = 0
    return out


HOT_SEGMENT_MULTIPLIER = 3
HOT_SEGMENT_MIN_LEARNERS = 3
HOT_SEGMENT_DAYS = 7


def hot_segment_alerts(db: Session, now: Optional[datetime] = None) -> int:
    from statistics import median
    from collections import defaultdict
    from app.models.course import Course, Lesson
    from app.models.course_ops import CourseCollaborator
    from app.models.learning_signals import LearningSignal
    from app.services.learning_signals_service import course_segments, _fmt_pos

    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=HOT_SEGMENT_DAYS)
    course_ids = (
        db.query(Lesson.post_parent)
        .join(LearningSignal, LearningSignal.lesson_id == Lesson.id)
        .filter(LearningSignal.created_at >= since, LearningSignal.segment.isnot(None))
        .distinct()
        .all()
    )
    sent = 0
    for (cid,) in course_ids:
        course = db.query(Course).filter(Course.id == cid).first()
        if not course:
            continue
        segments = course_segments(db, cid, HOT_SEGMENT_DAYS, now)["segments"]
        scores = defaultdict(list)
        for s in segments:
            scores[s["lesson_id"]].append(s["score"])
        editors = {course.post_author} | {
            uid
            for (uid,) in db.query(CourseCollaborator.user_id)
            .filter(CourseCollaborator.course_id == cid)
            .all()
        }
        for s in segments:
            if (
                s["score"] <= 0
                or s["learners"] < HOT_SEGMENT_MIN_LEARNERS
                or s["score"] < HOT_SEGMENT_MULTIPLIER * median(scores[s["lesson_id"]])
            ):
                continue
            link = f"/instructor/insights?course_id={cid}&tab=hotspots&lesson_id={s['lesson_id']}&segment={s['segment']}"
            for uid in sorted(editors - {None}):
                if _sent_since(
                    db, uid, "hot_segment", since, s["lesson_id"], link=link
                ):
                    continue
                if _notify(
                    db,
                    uid,
                    "hot_segment",
                    f"Review {s['lesson_title']}"[:255],
                    f"{s['learners']} learners struggled at {_fmt_pos(s['start_s'])}–{_fmt_pos(s['end_s'])}. Segment score: {s['score']}.",
                    link,
                    s["lesson_id"],
                ):
                    sent += 1
    return sent
