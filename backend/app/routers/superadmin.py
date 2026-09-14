"""
SuperAdmin router — supervisory role above `admin`.

Two responsibilities, both gated by `require_superadmin`:

  1. Impersonate ANY non-superadmin user (Phase 2).
     Unlike the admin router's instructor/student/spoc/company-only starters,
     this endpoint imposes no role restriction on the target except that the
     target must NOT be a superadmin (security invariant: no one may
     impersonate a superadmin). It reuses the existing
     `create_impersonation_token` (30-min, non-refreshable) and the existing
     `AdminImpersonationLog` audit table, tagging rows with
     `actor_role='superadmin'`.

  2. Monitoring dashboards (Phase 3).
     Cross-cutting aggregations over users / enrollments / courses /
     payments / page_views / audit logs, exposing the four KPI groups:
     student progress, instructor productivity, admin activity, platform
     health. The overview endpoint is Redis-cached (5-min TTL) and degrades
     gracefully to a no-op cache when Redis is unavailable.
"""
import csv
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, case, cast, Date
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import CacheManager
from app.core.security import (
    create_impersonation_token,
    IMPERSONATION_TOKEN_EXPIRE_MINUTES,
)
from app.models.user import User, AdminImpersonationLog, InstructorProfile
from app.models.course import Course, CourseReview
from app.models.enrollment import Enrollment, LessonProgress, StudentCourseActivity
from app.models.certificate import IssuedCertificate
from app.models.payment import Order, OrderItem, OrderStatus
from app.models.page_view import PageView
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()


# Which non-student roles we report on as "admins" for the admins dashboard.
# SuperAdmin itself is excluded from the managed-admins list (it supervises).
# Privileged roles the oversight screens cover. SuperAdmin is included so the
# "Admins" count and list agree with the role-distribution donut, which has
# always reported SuperAdmins as a slice of its own.
_ADMIN_ROLES = ("admin", "superadmin")

OVERVIEW_CACHE_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Phase 2 — Impersonate ANY user (including admins)
# ---------------------------------------------------------------------------
@router.post("/impersonate/{target_user_id}")
async def superadmin_impersonate(
    target_user_id: int,
    payload: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
):
    """
    Mint a 30-minute impersonation token for ANY target user, regardless of
    role — except `superadmin`, which can never be impersonated.

    Reuses the existing impersonation machinery:
      - `create_impersonation_token` (hard 30-min expiry, non-refreshable)
      - `AdminImpersonationLog` audit row (tagged actor_role='superadmin')
      - anti-chaining guard via `_impersonated_by`

    `reason` is REQUIRED when the target is an `admin` (compliance) and
    optional otherwise.
    """
    # Anti-chaining: a token already minted with impersonated_by cannot mint
    # another. This is the same guard the admin router uses.
    if getattr(current_user, "_impersonated_by", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonation sessions cannot start another impersonation",
        )

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")
    if not target.is_active:
        raise HTTPException(status_code=400, detail="Target user is inactive")

    # Security invariant: no one may impersonate a superadmin.
    if target.role == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SuperAdmin accounts cannot be impersonated",
        )

    # Parse + truncate reason exactly like the admin endpoint.
    reason: Optional[str] = None
    if payload and isinstance(payload, dict):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = raw_reason.strip()[:1000]

    # Compliance: impersonating another admin needs a recorded reason.
    if target.role in _ADMIN_ROLES and not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A reason is required to impersonate an admin account",
        )

    log_row = AdminImpersonationLog(
        admin_user_id=current_user.id,
        target_user_id=target.id,
        started_at=datetime.now(timezone.utc),
        reason=reason,
        actor_role="superadmin",
    )
    db.add(log_row)
    db.commit()
    db.refresh(log_row)

    token = create_impersonation_token(
        target_user_id=target.id, admin_id=current_user.id
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": IMPERSONATION_TOKEN_EXPIRE_MINUTES * 60,
        "target": {
            "id": target.id,
            "display_name": target.display_name,
            "role": target.role,
            "email": target.user_email,
        },
        "log_id": log_row.id,
        "actor_role": "superadmin",
    }


# ---------------------------------------------------------------------------
# Phase 3 — Monitoring dashboards
# ---------------------------------------------------------------------------
@router.get("/overview")
async def superadmin_overview(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """
    Platform-wide KPIs: active users by role, DAU/WAU (page views), 30-day
    revenue trend, open impersonation sessions, and headline totals.
    Redis-cached for 5 minutes; degrades gracefully when Redis is down.
    """
    cache_key = f"superadmin:overview:{days}"
    try:
        cached = await CacheManager.get(cache_key)
        if cached:
            if isinstance(cached, dict):
                cached["cached"] = True
                return cached
    except Exception:
        logger.warning("overview: cache read failed, computing fresh", exc_info=True)

    result = _compute_overview(db, days)
    result["cached"] = False

    try:
        await CacheManager.set(cache_key, result, expire=OVERVIEW_CACHE_TTL)
    except Exception:
        logger.warning("overview: cache write failed (non-fatal)", exc_info=True)

    return result


def _compute_overview(db: Session, days: int) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    today = now.date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    # --- Active users by role (registered users who viewed a page in window)
    role_counts_q = (
        db.query(User.role, func.count(func.distinct(PageView.user_id)))
        .join(PageView, PageView.user_id == User.id)
        .filter(PageView.created_at >= start)
        .group_by(User.role)
    )
    active_users_by_role = {role: int(cnt) for role, cnt in role_counts_q.all()}

    # --- DAU / WAU (distinct visitors incl. anon). Mirrors analytics.py
    # unique-visitor logic: logged-in users by user_id, anon by ip_hash.
    def _distinct_visitors(range_start) -> int:
        logged_in = (
            db.query(func.count(func.distinct(PageView.user_id)))
            .filter(PageView.created_at >= range_start, PageView.user_id.isnot(None))
            .scalar()
            or 0
        )
        anon = (
            db.query(func.count(func.distinct(PageView.ip_hash)))
            .filter(
                PageView.created_at >= range_start,
                PageView.user_id.is_(None),
                PageView.ip_hash.isnot(None),
            )
            .scalar()
            or 0
        )
        return int(logged_in) + int(anon)

    # DAU ≈ visitors in last 24h; WAU ≈ last 7d.
    dau = _distinct_visitors(now - timedelta(hours=24))
    wau = _distinct_visitors(now - timedelta(days=7))

    # --- 30-day revenue trend from completed orders
    rev_rows = (
        db.query(
            func.date(Order.date_created).label("day"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .filter(
            Order.order_status == OrderStatus.COMPLETED,
            Order.date_created >= start,
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    revenue_trend = [
        {"day": str(r.day), "revenue": float(r.revenue), "orders": int(r.orders)}
        for r in rev_rows
    ]

    # --- Active impersonation sessions.
    # ended_at is only written when someone clicks "Exit impersonation"; closing
    # the tab leaves the row open forever. Counting every open row therefore
    # reported hundreds of months-dead sessions. An impersonation token is hard
    # -expired after IMPERSONATION_TOKEN_EXPIRE_MINUTES, so a row older than
    # that cannot still be in use no matter what ended_at says.
    session_cutoff = now - timedelta(minutes=IMPERSONATION_TOKEN_EXPIRE_MINUTES)
    open_sessions = (
        db.query(func.count(AdminImpersonationLog.id))
        .filter(
            AdminImpersonationLog.ended_at.is_(None),
            AdminImpersonationLog.started_at >= session_cutoff,
        )
        .scalar()
        or 0
    )
    # Kept separate so the audit screen can still surface never-closed rows
    # without the headline KPI pretending they are live.
    stale_sessions = (
        db.query(func.count(AdminImpersonationLog.id))
        .filter(
            AdminImpersonationLog.ended_at.is_(None),
            AdminImpersonationLog.started_at < session_cutoff,
        )
        .scalar()
        or 0
    )

    # --- Headline totals
    students = (
        db.query(func.count(User.id)).filter(User.role == "student").scalar() or 0
    )
    instructors = (
        db.query(func.count(User.id)).filter(User.role == "instructor").scalar() or 0
    )
    admins = (
        db.query(func.count(User.id)).filter(User.role.in_(_ADMIN_ROLES)).scalar() or 0
    )
    courses = db.query(func.count(Course.id)).scalar() or 0
    enrollments = db.query(func.count(Enrollment.id)).scalar() or 0

    # --- Role distribution for the donut chart (all registered users)
    role_dist_rows = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    # Pretty label for each role slug, sorted largest-first so the donut
    # renders the dominant slice first.
    _role_label = {
        "student": "Students",
        "instructor": "Instructors",
        "admin": "Admins",
        "superadmin": "SuperAdmins",
        "spoc": "SPOCs",
        "company": "Companies",
        "company_manager": "Managers",
    }
    role_distribution = sorted(
        (
            {"name": _role_label.get(role, role.capitalize()), "value": int(cnt)}
            for role, cnt in role_dist_rows
            if cnt
        ),
        key=lambda r: r["value"],
        reverse=True,
    )

    # --- Enrollments trend (new enrollments per day) for a second chart series
    enr_rows = (
        db.query(
            func.date(Enrollment.enrollment_date).label("day"),
            func.count(Enrollment.id).label("count"),
        )
        .filter(Enrollment.enrollment_date >= start)
        .group_by("day")
        .order_by("day")
        .all()
    )
    # Merge into a per-day dict keyed by ISO date so the frontend can plot
    # revenue + enrollments on a shared x-axis where present.
    enr_by_day = {str(r.day): int(r.count) for r in enr_rows}

    # --- Daily active users (distinct visitors incl. anon) per day, for the
    # activity area chart. This is the most expensive query, so keep it bounded
    # to the requested window. Logged-in users are counted by user_id, anon
    # visitors by ip_hash; coalesce to a string sentinel so the types match.
    dau_rows = (
        db.query(
            func.date(PageView.created_at).label("day"),
            (
                func.count(func.distinct(PageView.user_id))
                + func.count(func.distinct(func.coalesce(PageView.ip_hash, "")))
            ).label("visitors"),
        )
        .filter(PageView.created_at >= start)
        .group_by("day")
        .order_by("day")
        .all()
    )
    dau_by_day = {str(r.day): int(r.visitors or 0) for r in dau_rows}

    # --- Activity trend: unified per-day series combining revenue, orders,
    # new enrollments, and active users. Days with no activity are filled with
    # zeros so the chart never shows a misleading gap.
    all_days: set[str] = set()
    for r in revenue_trend:
        all_days.add(r["day"])
    all_days.update(enr_by_day.keys())
    all_days.update(dau_by_day.keys())
    activity_trend: list[dict] = []
    for day in sorted(all_days):
        rev_match = next((r for r in revenue_trend if r["day"] == day), None)
        activity_trend.append(
            {
                "day": day,
                "revenue": rev_match["revenue"] if rev_match else 0.0,
                "orders": rev_match["orders"] if rev_match else 0,
                "enrollments": enr_by_day.get(day, 0),
                "active_users": dau_by_day.get(day, 0),
            }
        )

    return {
        "generated_at": now.isoformat(),
        "active_users_by_role": active_users_by_role,
        "dau": dau,
        "wau": wau,
        "revenue_trend": revenue_trend,
        "role_distribution": role_distribution,
        "activity_trend": activity_trend,
        "open_impersonation_sessions": int(open_sessions),
        "stale_impersonation_sessions": int(stale_sessions),
        "totals": {
            "students": int(students),
            "instructors": int(instructors),
            "admins": int(admins),
            "courses": int(courses),
            "enrollments": int(enrollments),
        },
    }


@router.get("/students")
async def superadmin_students(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Filter by name/email"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Per-student performance & work-progress metrics."""
    base = db.query(User).filter(User.role == "student")
    if search:
        like = f"%{search.strip()}%"
        base = base.filter(
            (User.display_name.ilike(like)) | (User.user_email.ilike(like))
        )

    total = base.count()
    users = base.order_by(User.id.desc()).offset(offset).limit(limit).all()
    if not users:
        return {"items": [], "total": total}

    user_ids = [u.id for u in users]

    # Enrollments + avg completion per student
    enr = (
        db.query(
            Enrollment.user_id,
            func.count(Enrollment.id).label("enrollments"),
            func.avg(Enrollment.course_progress_percentage).label("avg_completion"),
        )
        .filter(Enrollment.user_id.in_(user_ids))
        .group_by(Enrollment.user_id)
        .all()
    )
    enr_map = {
        r.user_id: {
            "enrollments": int(r.enrollments or 0),
            "completion_pct": round(float(r.avg_completion or 0), 1),
        }
        for r in enr
    }

    # Certificates issued per student
    cert_rows = (
        db.query(IssuedCertificate.user_id, func.count(IssuedCertificate.id))
        .filter(IssuedCertificate.user_id.in_(user_ids))
        .group_by(IssuedCertificate.user_id)
        .all()
    )
    cert_map = {uid: int(c) for uid, c in cert_rows}

    # Pass rate (quiz) per student from lesson-progress activity is not a
    # direct column; approximate using StudentCourseActivity success ratio.
    pass_rows = (
        db.query(
            StudentCourseActivity.user_id,
            func.avg(
                case(
                    (
                        StudentCourseActivity.activity_status == "completed",
                        100,
                    ),
                    else_=0,
                )
            ),
        )
        .filter(StudentCourseActivity.user_id.in_(user_ids))
        .group_by(StudentCourseActivity.user_id)
        .all()
    )
    pass_map = {uid: round(float(rate or 0), 1) for uid, rate in pass_rows}

    # Streak: distinct days with any activity in last 30d
    streak_rows = (
        db.query(
            StudentCourseActivity.user_id,
            func.count(func.distinct(cast(StudentCourseActivity.created_at, Date))),
        )
        .filter(
            StudentCourseActivity.user_id.in_(user_ids),
            StudentCourseActivity.created_at
            >= datetime.now(timezone.utc) - timedelta(days=30),
        )
        .group_by(StudentCourseActivity.user_id)
        .all()
    )
    streak_map = {uid: int(d) for uid, d in streak_rows}

    # Streak unification (spec D4): prefer gamification_service's
    # consecutive-day streak (UserGameStats.current_streak) over the
    # distinct-active-days-in-30d approximation above, for any user who has
    # a stats row. Users with no stats row yet (no gamification-triggering
    # activity) keep the historical approximation as a fallback.
    #
    # M1 review fix: current_streak is only "alive" when the user was
    # active today or yesterday — mirrors
    # gamification_service.get_streak_for_user's staleness rule (this bulk
    # query bypasses that per-user helper for N+1 avoidance, so the same
    # rule is inlined here instead). Without it, a user inactive for months
    # would still read whatever current_streak touch_streak last wrote,
    # since nothing decays it on its own with the passage of time.
    from app.models.gamification import UserGameStats

    _today_utc = datetime.now(timezone.utc).date()
    game_streak_rows = (
        db.query(
            UserGameStats.user_id,
            UserGameStats.current_streak,
            UserGameStats.last_active_date,
        )
        .filter(UserGameStats.user_id.in_(user_ids))
        .all()
    )
    for uid, current_streak, last_active_date in game_streak_rows:
        current_streak = int(current_streak or 0)
        if current_streak > 0 and (
            last_active_date is None or (_today_utc - last_active_date).days > 1
        ):
            current_streak = 0
        streak_map[uid] = current_streak

    # Last active: most recent activity, fall back to page view, then last_login
    last_activity_rows = (
        db.query(
            StudentCourseActivity.user_id,
            func.max(StudentCourseActivity.created_at),
        )
        .filter(StudentCourseActivity.user_id.in_(user_ids))
        .group_by(StudentCourseActivity.user_id)
        .all()
    )
    last_activity_map = {uid: ts for uid, ts in last_activity_rows}

    last_pv_rows = (
        db.query(PageView.user_id, func.max(PageView.created_at))
        .filter(PageView.user_id.in_(user_ids))
        .group_by(PageView.user_id)
        .all()
    )
    last_pv_map = {uid: ts for uid, ts in last_pv_rows}

    items = []
    for u in users:
        last_activity = (
            last_activity_map.get(u.id) or last_pv_map.get(u.id) or u.last_login
        )
        items.append(
            {
                "id": u.id,
                "display_name": u.display_name,
                "email": u.user_email,
                "enrollments": enr_map.get(u.id, {}).get("enrollments", 0),
                "completion_pct": enr_map.get(u.id, {}).get("completion_pct", 0.0),
                "pass_rate": pass_map.get(u.id, 0.0),
                "certificates": cert_map.get(u.id, 0),
                "streak_days": streak_map.get(u.id, 0),
                "last_active": last_activity.isoformat() if last_activity else None,
            }
        )

    return {"items": items, "total": total}


@router.get("/instructors")
async def superadmin_instructors(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Per-instructor productivity & work-progress metrics."""
    base = db.query(User).filter(User.role == "instructor")
    if search:
        like = f"%{search.strip()}%"
        base = base.filter(
            (User.display_name.ilike(like)) | (User.user_email.ilike(like))
        )

    total = base.count()
    users = base.order_by(User.id.desc()).offset(offset).limit(limit).all()
    if not users:
        return {"items": [], "total": total}

    user_ids = [u.id for u in users]

    # Courses published + students enrolled (via Course.total_enrollments)
    course_rows = (
        db.query(
            Course.post_author,
            func.count(Course.id).label("courses"),
            func.sum(Course.total_enrollments).label("students"),
        )
        .filter(Course.post_author.in_(user_ids))
        .group_by(Course.post_author)
        .all()
    )
    course_map = {
        r.post_author: {
            "courses_published": int(r.courses or 0),
            "students_enrolled": int(r.students or 0),
        }
        for r in course_rows
    }

    # Avg rating across the instructor's courses
    rating_rows = (
        db.query(Course.post_author, func.avg(Course.average_rating))
        .filter(Course.post_author.in_(user_ids))
        .group_by(Course.post_author)
        .all()
    )
    rating_map = {uid: round(float(r or 0), 2) for uid, r in rating_rows}

    # Revenue attributed: sum OrderItem.subtotal for completed orders whose
    # course belongs to the instructor.
    rev_rows = (
        db.query(
            Course.post_author,
            func.coalesce(func.sum(OrderItem.subtotal), 0),
        )
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Course, Course.id == OrderItem.course_id)
        .filter(
            Order.order_status == OrderStatus.COMPLETED,
            Course.post_author.in_(user_ids),
        )
        .group_by(Course.post_author)
        .all()
    )
    rev_map = {uid: float(amt or 0) for uid, amt in rev_rows}

    # Pending approvals: instructors whose profile isn't approved yet
    pending_rows = (
        db.query(InstructorProfile.user_id)
        .filter(
            InstructorProfile.user_id.in_(user_ids),
            InstructorProfile.is_approved.is_(False),
        )
        .all()
    )
    pending_set = {r.user_id for r in pending_rows}

    # Last activity via page views, fallback last_login
    last_pv_rows = (
        db.query(PageView.user_id, func.max(PageView.created_at))
        .filter(PageView.user_id.in_(user_ids))
        .group_by(PageView.user_id)
        .all()
    )
    last_pv_map = {uid: ts for uid, ts in last_pv_rows}

    items = []
    for u in users:
        last_active = last_pv_map.get(u.id) or u.last_login
        items.append(
            {
                "id": u.id,
                "display_name": u.display_name,
                "email": u.user_email,
                "courses_published": course_map.get(u.id, {}).get(
                    "courses_published", 0
                ),
                "students_enrolled": course_map.get(u.id, {}).get(
                    "students_enrolled", 0
                ),
                "avg_rating": rating_map.get(u.id, 0.0),
                "pending_approvals": 1 if u.id in pending_set else 0,
                "revenue_attributed": rev_map.get(u.id, 0.0),
                "last_active": last_active.isoformat() if last_active else None,
            }
        )

    return {"items": items, "total": total}


@router.get("/admins")
async def superadmin_admins(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Per-admin activity: logins, users managed, impersonations run."""
    base = db.query(User).filter(User.role.in_(_ADMIN_ROLES))
    if search:
        like = f"%{search.strip()}%"
        base = base.filter(
            (User.display_name.ilike(like)) | (User.user_email.ilike(like))
        )

    total = base.count()
    users = (
        base.order_by(User.last_login.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )
    if not users:
        return {"items": [], "total": total}

    user_ids = [u.id for u in users]

    # Impersonations each admin has started
    imp_rows = (
        db.query(
            AdminImpersonationLog.admin_user_id,
            func.count(AdminImpersonationLog.id),
        )
        .filter(AdminImpersonationLog.admin_user_id.in_(user_ids))
        .group_by(AdminImpersonationLog.admin_user_id)
        .all()
    )
    imp_map = {uid: int(c) for uid, c in imp_rows}

    # `users_managed` / `actions_taken` used to be emitted here hardcoded to 0.
    # Nothing writes them — there is no per-admin action audit table — so they
    # rendered as real zeros in the CSV export and read as "this admin did
    # nothing". Dropped rather than faked; reinstate them only alongside an
    # actual audit log. impersonations_run below is genuine, from
    # AdminImpersonationLog.
    items = []
    for u in users:
        items.append(
            {
                "id": u.id,
                "display_name": u.display_name,
                "email": u.user_email,
                "role": u.role,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "impersonations_run": imp_map.get(u.id, 0),
            }
        )

    return {"items": items, "total": total}


@router.get("/audit/impersonations")
async def superadmin_audit_impersonations(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    open_only: bool = Query(False, description="Only sessions not yet ended"),
):
    """Full AdminImpersonationLog feed (actor, target, duration, reason)."""
    q = db.query(AdminImpersonationLog)
    if open_only:
        q = q.filter(AdminImpersonationLog.ended_at.is_(None))

    total = q.count()
    rows = (
        q.order_by(AdminImpersonationLog.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    if not rows:
        return {"items": [], "total": total}

    # Resolve actor + target names/roles in two bulk queries.
    actor_ids = {r.admin_user_id for r in rows}
    target_ids = {r.target_user_id for r in rows}
    actors = {u.id: u for u in db.query(User).filter(User.id.in_(actor_ids)).all()}
    targets = {u.id: u for u in db.query(User).filter(User.id.in_(target_ids)).all()}

    items = []
    for r in rows:
        actor = actors.get(r.admin_user_id)
        target = targets.get(r.target_user_id)
        duration = None
        if r.ended_at and r.started_at:
            # Both are timezone-aware DB values; guard against naive types.
            ended = (
                r.ended_at
                if r.ended_at.tzinfo
                else r.ended_at.replace(tzinfo=timezone.utc)
            )
            started = (
                r.started_at
                if r.started_at.tzinfo
                else r.started_at.replace(tzinfo=timezone.utc)
            )
            duration = int((ended - started).total_seconds())
        items.append(
            {
                "id": r.id,
                "actor_user_id": r.admin_user_id,
                "actor_name": actor.display_name
                if actor
                else f"user#{r.admin_user_id}",
                "actor_role": r.actor_role or "admin",
                "target_user_id": r.target_user_id,
                "target_name": target.display_name
                if target
                else f"user#{r.target_user_id}",
                "target_role": target.role if target else "unknown",
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                "duration_seconds": duration,
                "reason": r.reason,
            }
        )

    return {"items": items, "total": total}


# ---------------------------------------------------------------------------
# Phase 4 — CSV export of the monitoring tables
# ---------------------------------------------------------------------------
_EXPORT_PAGE_SIZE = 500


async def _collect_all(fetch_page) -> List[Dict[str, Any]]:
    """Page through a list endpoint until every row is collected.

    The exports used to pass a single hardcoded limit (500 / 1000), which meant
    a platform that outgrew it produced a CSV that silently stopped short and
    looked complete. `fetch_page(limit, offset)` is awaited until it returns a
    short page or we have reached the reported total.
    """
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        data = await fetch_page(_EXPORT_PAGE_SIZE, offset)
        batch = data.get("items", []) or []
        rows.extend(batch)
        total = int(data.get("total") or 0)
        offset += _EXPORT_PAGE_SIZE
        if len(batch) < _EXPORT_PAGE_SIZE or len(rows) >= total:
            return rows


def _csv_stream(rows: List[Dict[str, Any]], columns: List[str]) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for r in rows:
        writer.writerow([r.get(c, "") for c in columns])
    buf.seek(0)

    def iterencode():
        yield buf.getvalue()

    return StreamingResponse(
        iterencode(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=superadmin-export.csv"},
    )


@router.get("/students/export")
async def superadmin_students_export(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
):
    """CSV export of all students with the same columns as /students."""
    rows = await _collect_all(
        lambda limit, offset: superadmin_students(
            current_user=current_user, db=db, search=None, limit=limit, offset=offset
        )
    )
    cols = [
        "id",
        "display_name",
        "email",
        "enrollments",
        "completion_pct",
        "pass_rate",
        "certificates",
        "streak_days",
        "last_active",
    ]
    return _csv_stream(rows, cols)


@router.get("/instructors/export")
async def superadmin_instructors_export(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
):
    rows = await _collect_all(
        lambda limit, offset: superadmin_instructors(
            current_user=current_user, db=db, search=None, limit=limit, offset=offset
        )
    )
    cols = [
        "id",
        "display_name",
        "email",
        "courses_published",
        "students_enrolled",
        "avg_rating",
        "pending_approvals",
        "revenue_attributed",
        "last_active",
    ]
    return _csv_stream(rows, cols)


@router.get("/admins/export")
async def superadmin_admins_export(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
):
    rows = await _collect_all(
        lambda limit, offset: superadmin_admins(
            current_user=current_user, db=db, search=None, limit=limit, offset=offset
        )
    )
    cols = [
        "id",
        "display_name",
        "email",
        "role",
        "last_login",
        "impersonations_run",
    ]
    return _csv_stream(rows, cols)


@router.get("/audit/impersonations/export")
async def superadmin_audit_export(
    current_user: User = Depends(AuthService.require_superadmin),
    db: Session = Depends(get_db),
):
    rows = await _collect_all(
        lambda limit, offset: superadmin_audit_impersonations(
            current_user=current_user,
            db=db,
            limit=limit,
            offset=offset,
            open_only=False,
        )
    )
    cols = [
        "id",
        "actor_user_id",
        "actor_name",
        "actor_role",
        "target_user_id",
        "target_name",
        "target_role",
        "started_at",
        "ended_at",
        "duration_seconds",
        "reason",
    ]
    return _csv_stream(rows, cols)
