"""
Analytics router - tracking + aggregation endpoints for the whole app.

Covers:
  * page-view ingestion (POST /track)
  * overview dashboard (/overview) matching the admin analytics layout
  * per-course analytics (/courses/{id})
  * per-blog analytics (/blog/{id})
  * student progress heatmap (/students/{user_id}/heatmap, /students/heatmap)

Admin-only by default. Tracking endpoint is unauthenticated so the frontend
beacon works for anonymous visitors.
"""
from datetime import datetime, timedelta, date
from hashlib import sha256
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, case, cast, Date
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.models.page_view import PageView
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment, LessonProgress, StudentCourseActivity
from app.models.quiz import Quiz, QuizAttempt
from app.models.blog import BlogPost
from app.models.payment import Payment, Order, PaymentStatus, OrderStatus, OrderItem
from app.services.auth_service import AuthService

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _range_start(days: int) -> datetime:
    days = max(1, min(days, 365))
    return datetime.utcnow() - timedelta(days=days)


def _hash_ip(request: Request) -> str:
    client = request.client.host if request.client else ""
    return sha256(client.encode()).hexdigest()[:32] if client else ""


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class TrackPayload(BaseModel):
    path: str
    referrer: Optional[str] = ""
    session_id: Optional[str] = None
    duration_ms: Optional[int] = 0
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


@router.post("/track", status_code=status.HTTP_204_NO_CONTENT)
async def track_page_view(
    payload: TrackPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    """Record a page view. Unauthenticated — the frontend beacon calls this on
    every client-side route change. Associates a user if an auth token is
    present, otherwise tracks anonymously by ip-hash + session."""
    user_id: Optional[int] = None
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        try:
            token = auth_header.split(" ", 1)[1]
            token_payload = verify_token(token)
            if token_payload and isinstance(token_payload, dict):
                raw = token_payload.get("sub") or token_payload.get("user_id")
                if raw is not None:
                    try:
                        user_id = int(raw)
                    except (TypeError, ValueError):
                        user_id = None
        except Exception:
            user_id = None

    pv = PageView(
        path=payload.path[:500],
        referrer=(payload.referrer or "")[:500],
        user_id=user_id if isinstance(user_id, int) else None,
        session_id=(payload.session_id or "")[:64] or None,
        ip_hash=_hash_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:500],
        duration_ms=payload.duration_ms or 0,
        entity_type=(payload.entity_type or None),
        entity_id=payload.entity_id,
    )
    db.add(pv)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Overview (admin analytics dashboard)
# ---------------------------------------------------------------------------

@router.get("/overview")
async def analytics_overview(
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Aggregated metrics for the admin analytics page. Returns the building
    blocks the frontend needs: totals, daily views series, top pages,
    payment-mode donut, most-visited page."""
    start = _range_start(days)

    # ---- Page views ----------------------------------------------------
    total_views = db.query(func.count(PageView.id)).filter(PageView.created_at >= start).scalar() or 0

    # Unique visitors = distinct user_id (for logged-in) + distinct ip_hash (for anons)
    distinct_users = (
        db.query(func.count(func.distinct(PageView.user_id)))
        .filter(PageView.created_at >= start, PageView.user_id.isnot(None))
        .scalar() or 0
    )
    distinct_anon = (
        db.query(func.count(func.distinct(PageView.ip_hash)))
        .filter(PageView.created_at >= start, PageView.user_id.is_(None), PageView.ip_hash.isnot(None))
        .scalar() or 0
    )
    unique_visitors = int(distinct_users) + int(distinct_anon)

    # daily views series
    daily_rows = (
        db.query(cast(PageView.created_at, Date).label("d"), func.count(PageView.id).label("views"))
        .filter(PageView.created_at >= start)
        .group_by("d")
        .order_by("d")
        .all()
    )
    daily_views = [{"date": row.d.isoformat() if row.d else None, "views": int(row.views)} for row in daily_rows]

    # top pages
    top_pages_rows = (
        db.query(PageView.path, func.count(PageView.id).label("views"))
        .filter(PageView.created_at >= start)
        .group_by(PageView.path)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )
    top_pages = [{"path": row.path, "views": int(row.views)} for row in top_pages_rows]

    most_visited = top_pages[0] if top_pages else {"path": "/", "views": 0}

    # ---- Payment modes -------------------------------------------------
    payment_rows = (
        db.query(
            Order.payment_method_title,
            func.count(Order.id).label("count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total"),
        )
        .filter(Order.date_created >= start)
        .filter(Order.order_status == OrderStatus.COMPLETED)
        .group_by(Order.payment_method_title)
        .all()
    )
    payment_modes = [
        {
            "label": (row.payment_method_title or "Other"),
            "count": int(row.count),
            "total": float(row.total or 0),
        }
        for row in payment_rows
    ]
    total_orders = sum(p["count"] for p in payment_modes)
    total_revenue = sum(p["total"] for p in payment_modes)

    # ---- High-level totals --------------------------------------------
    user_count = db.query(func.count(User.id)).scalar() or 0
    course_count = db.query(func.count(Course.id)).scalar() or 0
    enrollment_count = db.query(func.count(Enrollment.id)).scalar() or 0
    blog_count = db.query(func.count(BlogPost.id)).scalar() or 0

    return {
        "range_days": days,
        "totals": {
            "page_views": int(total_views),
            "unique_visitors": int(unique_visitors),
            "users": int(user_count),
            "courses": int(course_count),
            "enrollments": int(enrollment_count),
            "blog_posts": int(blog_count),
            "orders": int(total_orders),
            "revenue": float(total_revenue),
        },
        "daily_views": daily_views,
        "top_pages": top_pages,
        "most_visited_page": most_visited,
        "payment_modes": payment_modes,
    }


# ---------------------------------------------------------------------------
# Per-course analytics
# ---------------------------------------------------------------------------

@router.get("/courses/{course_id}")
async def course_analytics(
    course_id: int,
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Per-course analytics. Available to admin + the course's instructor."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != "admin" and course.post_author != current_user.id:
        raise HTTPException(status_code=403, detail="Not your course")

    start = _range_start(days)

    # Enrollments over time
    enroll_rows = (
        db.query(cast(Enrollment.enrollment_date, Date).label("d"), func.count(Enrollment.id).label("c"))
        .filter(Enrollment.course_id == course_id)
        .filter(Enrollment.enrollment_date >= start)
        .group_by("d").order_by("d").all()
    )
    enrollments_series = [{"date": r.d.isoformat() if r.d else None, "count": int(r.c)} for r in enroll_rows]

    total_enrollments = db.query(func.count(Enrollment.id)).filter(Enrollment.course_id == course_id).scalar() or 0
    completed = (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.course_id == course_id, Enrollment.completion_date.isnot(None))
        .scalar() or 0
    )
    completion_rate = (completed / total_enrollments * 100) if total_enrollments else 0

    # Views (from PageView where entity_type='course' and entity_id=course_id)
    view_rows = (
        db.query(cast(PageView.created_at, Date).label("d"), func.count(PageView.id).label("c"))
        .filter(PageView.entity_type == "course", PageView.entity_id == course_id)
        .filter(PageView.created_at >= start)
        .group_by("d").order_by("d").all()
    )
    views_series = [{"date": r.d.isoformat() if r.d else None, "views": int(r.c)} for r in view_rows]
    total_views = sum(v["views"] for v in views_series)

    # Lesson completion stats
    lesson_count = db.query(func.count(Lesson.id)).filter(Lesson.post_parent == course_id).scalar() or 0
    lessons_completed = (
        db.query(func.count(LessonProgress.id))
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .filter(Lesson.post_parent == course_id, LessonProgress.progress_status == "completed")
        .scalar() or 0
    )

    # Revenue attributed to this course (via order_items.course_id)
    revenue = (
        db.query(func.coalesce(func.sum(OrderItem.subtotal), 0))
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.course_id == course_id)
        .filter(Order.order_status == OrderStatus.COMPLETED)
        .scalar() or 0
    )

    return {
        "course": {"id": course.id, "title": course.post_title},
        "range_days": days,
        "totals": {
            "enrollments": int(total_enrollments),
            "completed": int(completed),
            "completion_rate": float(completion_rate),
            "views": int(total_views),
            "lessons": int(lesson_count),
            "lessons_completed": int(lessons_completed),
            "revenue": float(revenue),
            "rating": float(course.average_rating or 0),
            "reviews": int(course.total_reviews or 0),
        },
        "enrollments_series": enrollments_series,
        "views_series": views_series,
    }


# ---------------------------------------------------------------------------
# Student Activity (Issue 8) — time spent, watch sessions, last active,
# current activity and viewing history, derived from WatchSession rows.
# ---------------------------------------------------------------------------

from app.models.enrollment import WatchSession  # noqa: E402


@router.get("/courses/{course_id}/student-activity")
async def course_student_activity(
    course_id: int,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Per-course student activity panel (Issue 8).

    For every enrolled student: total time spent watching, number of watch
    sessions, last-active timestamp and a live 'currently_watching' flag
    (a watch event in the last 5 minutes). Admin or the course instructor
    only.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != "admin" and course.post_author != current_user.id:
        raise HTTPException(status_code=403, detail="Not your course")

    enrollments = (
        db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    )

    # Pre-aggregate watch stats per user for this course in one pass.
    user_ids = [e.user_id for e in enrollments]
    rows = (
        db.query(
            WatchSession.user_id,
            func.coalesce(func.sum(WatchSession.duration_seconds), 0).label("time_spent"),
            func.count(WatchSession.id).label("sessions"),
            func.max(WatchSession.started_at).label("last_active"),
            func.max(WatchSession.created_at).label("last_event_at"),
        )
        .filter(
            WatchSession.course_id == course_id,
            WatchSession.user_id.in_(user_ids) if user_ids else False,
        )
        .group_by(WatchSession.user_id)
        .all()
    )
    stats_by_user = {
        r.user_id: {
            "time_spent_seconds": int(r.time_spent or 0),
            "watch_sessions": int(r.sessions or 0),
            "last_active": r.last_active,
            "last_event_at": r.last_event_at,
        }
        for r in rows
    }

    now = datetime.utcnow()
    active_threshold = now - timedelta(minutes=5)

    students = []
    for e in enrollments:
        s = stats_by_user.get(e.user_id, {})
        last_event = s.get("last_event_at")
        students.append({
            "user_id": e.user_id,
            "student_name": e.student.display_name if e.student else f"User {e.user_id}",
            "email": e.student.user_email if e.student else "",
            "progress": e.course_progress_percentage or 0,
            "time_spent_seconds": s.get("time_spent_seconds", 0),
            "watch_sessions": s.get("watch_sessions", 0),
            "last_active": s.get("last_active"),
            # Currently watching = a watch event in the last 5 minutes.
            "currently_watching": bool(last_event and last_event >= active_threshold),
            "enrollment_status": e.enrollment_status,
            "completion_date": e.completion_date,
        })

    # Newest activity first; students with no activity last.
    students.sort(key=lambda x: x.get("last_active") or datetime.min, reverse=True)

    return {
        "course": {"id": course.id, "title": course.post_title},
        "students": students,
    }


@router.get("/students/{user_id}/courses/{course_id}/history")
async def student_viewing_history(
    user_id: int,
    course_id: int,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Per-student viewing history for a course (Issue 8).

    Returns the timeline of watch events (started / paused / resumed /
    completed) with position and duration, plus the discrete activity log
    (lesson_completed / quiz_passed / assignment_submitted). Admin or the
    course instructor only.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != "admin" and course.post_author != current_user.id:
        raise HTTPException(status_code=403, detail="Not your course")

    watch_rows = (
        db.query(WatchSession)
        .filter(
            WatchSession.user_id == user_id,
            WatchSession.course_id == course_id,
        )
        .order_by(WatchSession.started_at.desc())
        .limit(limit)
        .all()
    )

    activity_rows = (
        db.query(StudentCourseActivity)
        .filter(
            StudentCourseActivity.user_id == user_id,
            StudentCourseActivity.course_id == course_id,
        )
        .order_by(StudentCourseActivity.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "user_id": user_id,
        "course_id": course_id,
        "watch_history": [
            {
                "lesson_id": w.lesson_id,
                "event": w.event,
                "duration_seconds": w.duration_seconds,
                "position_seconds": w.position_seconds,
                "at": w.started_at,
            }
            for w in watch_rows
        ],
        "activities": [
            {
                "type": a.activity_type,
                "lesson_id": a.lesson_id,
                "quiz_id": a.quiz_id,
                "at": a.created_at,
            }
            for a in activity_rows
        ],
    }


@router.get("/courses/{course_id}/statistics")
async def course_statistics(
    course_id: int,
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Course-level statistics for the admin Activity Panel (Issue 2).

    Aggregates:
      * Quiz attempts — total attempts, pass rate, average score
      * Struggles — ended attempts that did NOT meet the passing grade
        (a proxy for repeated / failing attempts), plus students with the
        most failed attempts
      * Revisits — repeat watch sessions per lesson (sessions beyond the
        first per user per lesson), plus the most-revisited lessons
      * Average frequency / progress — avg progress %, avg watch sessions
        and avg time spent across enrolled students

    Admin or the course instructor only.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role != "admin" and course.post_author != current_user.id:
        raise HTTPException(status_code=403, detail="Not your course")

    quizzes = db.query(Quiz).filter(Quiz.post_parent == course_id).all()
    quiz_ids = [q.id for q in quizzes]
    passing_by_quiz = {q.id: (q.quiz_passing_grade or 0) for q in quizzes}

    # --- Quiz attempts ---
    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.course_id == course_id,
            QuizAttempt.quiz_id.in_(quiz_ids) if quiz_ids else False,
            QuizAttempt.attempt_status == "attempt_ended",
        )
        .all()
    )

    total_attempts = len(attempts)
    passed = 0
    failed = 0
    scores = []
    failed_by_user = {}  # user_id -> failed count (struggles)
    for a in attempts:
        if a.total_marks and float(a.total_marks) > 0:
            pct = (float(a.earned_marks) / float(a.total_marks)) * 100
        else:
            pct = 0
        scores.append(pct)
        if pct >= passing_by_quiz.get(a.quiz_id, 0):
            passed += 1
        else:
            failed += 1
            failed_by_user[a.user_id] = failed_by_user.get(a.user_id, 0) + 1

    avg_score = (sum(scores) / len(scores)) if scores else 0
    pass_rate = (passed / total_attempts * 100) if total_attempts else 0

    # Top strugglers (most failed attempts).
    strugglers = sorted(failed_by_user.items(), key=lambda kv: kv[1], reverse=True)[:10]
    struggler_ids = [u for u, _ in strugglers]
    struggler_names = {
        u.id: u.display_name
        for u in db.query(User).filter(User.id.in_(struggler_ids)).all()
    } if struggler_ids else {}
    top_strugglers = [
        {"user_id": uid, "student_name": struggler_names.get(uid, f"User {uid}"), "failed_attempts": cnt}
        for uid, cnt in strugglers
    ]

    # --- Revisits (repeat watch sessions per lesson) ---
    # A revisit = any watch session for a (user, lesson) beyond the first.
    revisit_rows = (
        db.query(
            WatchSession.user_id,
            WatchSession.lesson_id,
            func.count(WatchSession.id).label("n"),
        )
        .filter(WatchSession.course_id == course_id)
        .group_by(WatchSession.user_id, WatchSession.lesson_id)
        .all()
    )
    total_revisits = sum(max(0, r.n - 1) for r in revisit_rows)

    revisits_by_lesson = {}
    for r in revisit_rows:
        revisits_by_lesson[r.lesson_id] = revisits_by_lesson.get(r.lesson_id, 0) + max(0, r.n - 1)
    top_revisited = sorted(revisits_by_lesson.items(), key=lambda kv: kv[1], reverse=True)[:10]
    revisited_lesson_ids = [lid for lid, _ in top_revisited]
    lesson_titles = {
        l.id: l.post_title
        for l in db.query(Lesson).filter(Lesson.id.in_(revisited_lesson_ids)).all()
    } if revisited_lesson_ids else {}
    most_revisited_lessons = [
        {"lesson_id": lid, "title": lesson_titles.get(lid, f"Lesson {lid}"), "revisits": cnt}
        for lid, cnt in top_revisited
    ]

    # --- Average frequency / progress across enrolled students ---
    enrollments = (
        db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    )
    enrolled_user_ids = [e.user_id for e in enrollments]
    avg_progress = (
        sum((e.course_progress_percentage or 0) for e in enrollments) / len(enrollments)
        if enrollments else 0
    )

    agg = (
        db.query(
            func.count(WatchSession.id).label("sessions"),
            func.coalesce(func.sum(WatchSession.duration_seconds), 0).label("time"),
        )
        .filter(
            WatchSession.course_id == course_id,
            WatchSession.user_id.in_(enrolled_user_ids) if enrolled_user_ids else False,
        )
        .one()
    )
    total_sessions = int(agg.sessions or 0)
    total_time = int(agg.time or 0)
    avg_sessions = (total_sessions / len(enrollments)) if enrollments else 0
    avg_time_spent = (total_time / len(enrollments)) if enrollments else 0

    return {
        "course": {"id": course.id, "title": course.post_title},
        "enrolled_students": len(enrollments),
        "quiz": {
            "total_quizzes": len(quizzes),
            "total_attempts": total_attempts,
            "passed": passed,
            "failed": failed,
            "pass_rate": float(pass_rate),
            "average_score": float(avg_score),
        },
        "struggles": {
            "total_failed_attempts": failed,
            "top_strugglers": top_strugglers,
        },
        "revisits": {
            "total_revisits": total_revisits,
            "most_revisited_lessons": most_revisited_lessons,
        },
        "averages": {
            "progress": float(avg_progress),
            "watch_sessions_per_student": float(avg_sessions),
            "time_spent_per_student_seconds": float(avg_time_spent),
        },
    }


# ---------------------------------------------------------------------------
# Per-blog analytics
# ---------------------------------------------------------------------------

@router.get("/blog/{blog_id}")
async def blog_analytics(
    blog_id: int,
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Per-blog analytics. Admins see any, instructors see their own."""
    post = db.query(BlogPost).filter(BlogPost.id == blog_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    if current_user.role != "admin" and post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your blog post")

    start = _range_start(days)
    view_rows = (
        db.query(
            cast(PageView.created_at, Date).label("d"),
            func.count(PageView.id).label("c"),
            func.coalesce(func.avg(PageView.duration_ms), 0).label("avg_ms"),
        )
        .filter(PageView.entity_type == "blog", PageView.entity_id == blog_id)
        .filter(PageView.created_at >= start)
        .group_by("d").order_by("d").all()
    )
    series = [
        {"date": r.d.isoformat() if r.d else None, "views": int(r.c), "avg_read_ms": int(r.avg_ms or 0)}
        for r in view_rows
    ]
    total_views = sum(r["views"] for r in series)
    avg_read_ms = int(sum(r["avg_read_ms"] * r["views"] for r in series) / total_views) if total_views else 0

    return {
        "blog": {"id": post.id, "title": post.title, "slug": post.slug},
        "range_days": days,
        "totals": {
            "views": int(total_views),
            "comments": int(post.comment_count or 0),
            "avg_read_ms": int(avg_read_ms),
            "stored_view_count": int(post.view_count or 0),
        },
        "series": series,
    }


# ---------------------------------------------------------------------------
# Student progress heatmap
# ---------------------------------------------------------------------------

def _build_heatmap(db: Session, user_id: Optional[int], days: int) -> Dict[str, Any]:
    start = _range_start(days)

    q = db.query(
        cast(StudentCourseActivity.created_at, Date).label("d"),
        func.count(StudentCourseActivity.id).label("c"),
    ).filter(StudentCourseActivity.created_at >= start)
    if user_id is not None:
        q = q.filter(StudentCourseActivity.user_id == user_id)
    rows = q.group_by("d").order_by("d").all()

    by_date = {r.d.isoformat(): int(r.c) for r in rows if r.d}
    out = []
    day = start.date()
    end = date.today()
    while day <= end:
        key = day.isoformat()
        out.append({"date": key, "count": by_date.get(key, 0)})
        day += timedelta(days=1)
    return {"range_days": days, "heatmap": out, "max": max((x["count"] for x in out), default=0)}


@router.get("/students/heatmap")
async def overall_student_heatmap(
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Platform-wide student activity heatmap (admin)."""
    return _build_heatmap(db, user_id=None, days=days)


@router.get("/students/{user_id}/heatmap")
async def student_heatmap(
    user_id: int,
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Per-student activity heatmap. A user can see their own; admins can see anyone."""
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Cannot view another user's heatmap")
    return _build_heatmap(db, user_id=user_id, days=days)
