"""Conversion funnel (roadmap R1): record events, derive per-course summaries,
"continue where you left off", and the abandoned-checkout reminder pass.
Everything a report shows is computed at read time from funnel_events +
enrollments; nothing is pre-aggregated.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.funnel import FunnelEvent

logger = logging.getLogger(__name__)

KINDS = ("course_view", "preview_open", "checkout_start")
ABANDON_AFTER_HOURS = 24
ABANDON_MAX_AGE_DAYS = 7


def record(db: Session, kind: str, course_id: int, session_id: str, user_id: Optional[int] = None,
           meta: Optional[dict] = None) -> FunnelEvent:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    ev = FunnelEvent(kind=kind, course_id=course_id, user_id=user_id, session_id=(session_id or "")[:64], meta=meta or {})
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def _window(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def summary(db: Session, course_id: int, days: int = 30) -> Dict[str, Any]:
    from app.models.enrollment import Enrollment
    since = _window(days)
    rows = (db.query(FunnelEvent.kind, func.count(FunnelEvent.id), func.count(func.distinct(FunnelEvent.session_id)))
            .filter(FunnelEvent.course_id == course_id, FunnelEvent.created_at >= since)
            .group_by(FunnelEvent.kind).all())
    counts = {k: {"events": 0, "sessions": 0} for k in KINDS}
    for kind, n, s in rows:
        counts[kind] = {"events": int(n), "sessions": int(s)}
    enrolments = (db.query(func.count(Enrollment.id))
                  .filter(Enrollment.course_id == course_id, Enrollment.enrollment_date >= since,
                          Enrollment.enrollment_status.in_(["enrolled", "completed"])).scalar() or 0)
    views = counts["course_view"]["sessions"]
    previews = counts["preview_open"]["sessions"]
    checkouts = counts["checkout_start"]["sessions"]
    pct = lambda a, b: (round(100.0 * a / b, 1) if b else None)  # noqa: E731
    # which preview lessons pull people in
    lesson_rows = (db.query(FunnelEvent.meta).filter(FunnelEvent.course_id == course_id, FunnelEvent.kind == "preview_open",
                                                     FunnelEvent.created_at >= since).all())
    by_lesson: Dict[str, int] = {}
    for (m,) in lesson_rows:
        lid = str((m or {}).get("lesson_id") or "?")
        by_lesson[lid] = by_lesson.get(lid, 0) + 1
    top = sorted(by_lesson.items(), key=lambda kv: -kv[1])[:5]
    return {
        "course_id": course_id, "days": days,
        "views": views, "preview_opens": previews, "checkout_starts": checkouts, "enrolments": int(enrolments),
        "rates": {"view_to_preview": pct(previews, views), "preview_to_checkout": pct(checkouts, previews),
                  "checkout_to_enrol": pct(enrolments, checkouts), "view_to_enrol": pct(enrolments, views)},
        "top_preview_lessons": [{"lesson_id": lid, "opens": n} for lid, n in top],
        "raw": counts,
    }


def overview(db: Session, days: int = 30, instructor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    from app.models.course import Course
    q = db.query(Course.id, Course.post_title)
    if instructor_id:
        q = q.filter(Course.post_author == instructor_id)
    out = []
    for cid, title in q.order_by(Course.id.desc()).limit(200).all():
        s = summary(db, cid, days)
        if s["views"] or s["enrolments"] or s["preview_opens"]:
            out.append({"title": title, **s})
    out.sort(key=lambda r: (-(r["enrolments"]), -(r["views"])))
    return out


def continue_learning(db: Session, user_id: int, limit: int = 3) -> List[Dict[str, Any]]:
    """Latest touched lessons across enrolled courses — the dashboard's
    'continue where you left off' rail."""
    from app.models.course import Course, Lesson
    from app.models.enrollment import Enrollment, LessonProgress
    rows = (db.query(LessonProgress, Lesson, Course, Enrollment)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(Course, Course.id == LessonProgress.course_id)
            .join(Enrollment, Enrollment.id == LessonProgress.enrollment_id)
            .filter(LessonProgress.user_id == user_id, Enrollment.enrollment_status.in_(["enrolled", "completed"]))
            .order_by(LessonProgress.updated_at.desc()).limit(limit * 3).all())
    out, seen = [], set()
    for lp, lesson, course, enr in rows:
        if course.id in seen:
            continue
        seen.add(course.id)
        out.append({
            "course_id": course.id, "course_title": course.post_title, "course_slug": course.post_name,
            "lesson_id": lesson.id, "lesson_title": lesson.post_title, "lesson_type": lesson.lesson_content_type or "video",
            "lesson_status": lp.progress_status, "video_pct": int(lp.video_completion_percentage or 0),
            "course_pct": int(enr.course_progress_percentage or 0), "touched_at": lp.updated_at.isoformat() if lp.updated_at else None,
        })
        if len(out) >= limit:
            break
    return out


def abandoned_checkout_pass(db: Session, now: Optional[datetime] = None) -> int:
    """Once per (user, course): a checkout started >24h ago with no enrolment
    since → in-app notification (+ best-effort email). Idempotent via the
    notification row itself (type=checkout_reminder, related_id=course_id)."""
    from app.models.course import Course
    from app.models.enrollment import Enrollment
    from app.models.notification import Notification
    from app.services.notification_service import create_notification
    now = now or datetime.now(timezone.utc)
    lo, hi = now - timedelta(days=ABANDON_MAX_AGE_DAYS), now - timedelta(hours=ABANDON_AFTER_HOURS)
    starts = (db.query(FunnelEvent.user_id, FunnelEvent.course_id, func.max(FunnelEvent.created_at))
              .filter(FunnelEvent.kind == "checkout_start", FunnelEvent.user_id.isnot(None),
                      FunnelEvent.created_at >= lo, FunnelEvent.created_at <= hi)
              .group_by(FunnelEvent.user_id, FunnelEvent.course_id).all())
    sent = 0
    for uid, cid, _last in starts:
        enrolled = db.query(Enrollment.id).filter(Enrollment.user_id == uid, Enrollment.course_id == cid,
                                                  Enrollment.enrollment_status.in_(["enrolled", "completed"])).first()
        if enrolled:
            continue
        already = db.query(Notification.id).filter(Notification.user_id == uid, Notification.type == "checkout_reminder",
                                                   Notification.related_id == cid).first()
        if already:
            continue
        course = db.query(Course).filter(Course.id == cid).first()
        if not course:
            continue
        try:
            create_notification(db, user_id=uid, type="checkout_reminder", title=f"Your seat in {course.post_title} is waiting",
                                message="You started enrolling but did not finish. Pick up where you left off — the free previews are still open.",
                                link=f"/checkout/{cid}", related_id=cid)
            sent += 1
        except Exception:
            db.rollback()
            logger.exception("checkout reminder failed for user %s course %s", uid, cid)
    return sent


# ---------------------------------------------------------------- item 4: instructor earnings

PAID_ORDER_STATUSES = ("completed", "processing")


def earnings(db: Session, days: int = 30, instructor_id: Optional[int] = None) -> Dict[str, Any]:
    """Per-course money view for an instructor (or everything for admin):
    paid orders, gross (sum of the course line items), refunds (processed
    refund intents on those orders), net, enrolments and the funnel rates."""
    from app.models.course import Course
    from app.models.payment import Order, OrderItem, Payment
    since = _window(days)
    cq = db.query(Course.id, Course.post_title)
    if instructor_id:
        cq = cq.filter(Course.post_author == instructor_id)
    rows = []
    totals = {"orders": 0, "gross": 0.0, "refunds": 0.0, "net": 0.0, "enrolments": 0}
    for cid, title in cq.order_by(Course.id.desc()).limit(300).all():
        items = (db.query(OrderItem, Order).join(Order, Order.id == OrderItem.order_id)
                 .filter(OrderItem.course_id == cid, Order.created_at >= since).all())
        paid = [(it, o) for it, o in items if (o.order_status.value if hasattr(o.order_status, "value") else str(o.order_status)) in PAID_ORDER_STATUSES]
        gross = sum(float(it.total or 0) for it, _ in paid)
        order_ids = {o.id for _, o in paid}
        refunds = 0.0
        if order_ids:
            refunds = sum(float(p.amount or 0) for p in db.query(Payment)
                          .filter(Payment.order_id.in_(list(order_ids)), Payment.refund_status == "processed").all())
        f = summary(db, cid, days)
        if not paid and not f["views"] and not f["enrolments"]:
            continue
        row = {"course_id": cid, "title": title, "orders": len(paid), "gross": round(gross, 2), "refunds": round(refunds, 2),
               "net": round(gross - refunds, 2), "refund_rate": round(100.0 * refunds / gross, 1) if gross else 0.0,
               "enrolments": f["enrolments"], "views": f["views"], "preview_opens": f["preview_opens"], "rates": f["rates"]}
        rows.append(row)
        totals["orders"] += row["orders"]; totals["gross"] += row["gross"]; totals["refunds"] += row["refunds"]
        totals["net"] += row["net"]; totals["enrolments"] += row["enrolments"]
    rows.sort(key=lambda r: (-r["net"], -r["enrolments"]))
    totals = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in totals.items()}
    return {"days": days, "courses": rows, "totals": totals}


def report_pdf(db: Session, days: int, instructor_name: str, instructor_id: Optional[int]) -> bytes:
    """Monthly-style PDF an instructor can forward to a school: earnings +
    funnel per course, orange brand band. ReportLab (already a dependency)."""
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    data = earnings(db, days, instructor_id)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    st = getSampleStyleSheet()
    brand = ParagraphStyle("brand", parent=st["Normal"], fontSize=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#f97316"))
    h = ParagraphStyle("h", parent=st["Heading2"], textColor=colors.HexColor("#1f2937"))
    small = ParagraphStyle("small", parent=st["Normal"], fontSize=8, textColor=colors.HexColor("#6b7280"))
    story = [Paragraph("SashaInfinity", brand), Paragraph(f"Instructor report — {instructor_name}", h),
             Paragraph(f"Last {days} days · generated {datetime.now(timezone.utc):%d %b %Y}", small), Spacer(1, 6 * mm)]
    t = data["totals"]
    story.append(Paragraph(f"<b>Net earnings ₹{t['net']:,.0f}</b> · gross ₹{t['gross']:,.0f} · refunds ₹{t['refunds']:,.0f} · "
                           f"{t['orders']} paid orders · {t['enrolments']} enrolments", st["Normal"]))
    story.append(Spacer(1, 4 * mm))
    rows = [["Course", "Visits", "Previews", "Enrolled", "Orders", "Gross ₹", "Refunds ₹", "Net ₹"]]
    for r in data["courses"]:
        rows.append([r["title"][:38], r["views"], r["preview_opens"], r["enrolments"], r["orders"], f"{r['gross']:,.0f}", f"{r['refunds']:,.0f}", f"{r['net']:,.0f}"])
    if len(rows) == 1:
        rows.append(["No activity in this window", "", "", "", "", "", "", ""])
    tbl = Table(rows, repeatRows=1)
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff7ed")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#9a3412")),
                             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")), ("FONTSIZE", (0, 0), (-1, -1), 8),
                             ("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
    story.append(tbl)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Funnel: visit → free preview → checkout → enrolment. Refunds are processed refund intents on paid orders. "
                           "Figures are derived from live records at generation time.", small))
    doc.build(story)
    return buf.getvalue()
