"""Class reports, recording retention and the deletion audit (v2.0 §7 — WP5).

Retention doctrine: "media expires, knowledge does not". A recording gets
`retention_until` = ended_at + retention_days (per-class setting, owner default
365 days, capped by the tenant ceiling RECORDING_RETENTION_MAX_DAYS). Deleting
a recording is SOFT for 30 days (restorable), then the sweeper hard-deletes
by clearing the Bunny reference; the ClassReport, transcript, attendance and
audit rows are never touched. Expiry warnings go out at 14 and 3 days with a
one-click extend. Every action is audit-logged.

All sweeper work is per-class fault-isolated and idempotent (LiveClassEvent
markers), mirroring live_reminders.py.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.live_class import (LiveClass, LiveClassAttendance, LiveClassEvent, LiveClassPoll,
                                   LiveClassStatus)
from app.models.live_class_report import ClassReport, RecordingAudit
from app.models.user import User

logger = logging.getLogger(__name__)

PURPOSES = {"lecture", "doubt_clearing", "revision", "lab_demo", "assessment_viva", "orientation", "guest"}
MODES = {"instructor_led", "interactive_workshop", "breakout", "one_to_one"}
AUDIENCES = {"full_cohort", "batch", "selected", "open"}
RECORDING_POLICIES = {"always", "on_start", "never"}
# Report template hints per purpose (§7.1 "report template, default duration,
# whether attendance affects grade").
PURPOSE_META = {
    "lecture": {"default_minutes": 60, "attendance_affects_grade": True},
    "doubt_clearing": {"default_minutes": 45, "attendance_affects_grade": False},
    "revision": {"default_minutes": 60, "attendance_affects_grade": True},
    "lab_demo": {"default_minutes": 90, "attendance_affects_grade": True},
    "assessment_viva": {"default_minutes": 30, "attendance_affects_grade": True},
    "orientation": {"default_minutes": 45, "attendance_affects_grade": False},
    "guest": {"default_minutes": 60, "attendance_affects_grade": False},
}

SOFT_DELETE_GRACE_DAYS = 30
WARNING_DAYS = (14, 3)


def retention_default_days() -> int:
    return int(os.environ.get("RECORDING_RETENTION_DEFAULT_DAYS", "365") or 365)


def retention_max_days() -> int:
    return int(os.environ.get("RECORDING_RETENTION_MAX_DAYS", "365") or 365)


def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def clamp_retention_days(days: Optional[int]) -> int:
    d = int(days) if days is not None else retention_default_days()
    return max(1, min(d, retention_max_days()))


# ---------------------------------------------------------------- lifecycle

def lifecycle(live_class: LiveClass, report: Optional[ClassReport] = None, now: Optional[datetime] = None) -> str:
    """SCHEDULED → LIVE → ENDED → PROCESSED → ARCHIVED → DELETED (§7.2)."""
    now = now or datetime.now(timezone.utc)
    if live_class.deleted_at:
        return "cancelled"
    st = live_class.status
    if st == LiveClassStatus.SCHEDULED:
        return "scheduled"
    if st == LiveClassStatus.LIVE:
        return "live"
    if st == LiveClassStatus.CANCELLED:
        return "cancelled"
    # ended
    if getattr(live_class, "recording_deleted_at", None) and not live_class.recording_video_id:
        return "deleted"
    if getattr(live_class, "recording_deleted_at", None):
        return "deleted"       # soft-deleted (restorable inside the grace window)
    ru = _utc(getattr(live_class, "retention_until", None))
    if ru and ru < now:
        return "archived"
    if report and report.processing_status == "processed":
        return "processed"
    return "ended"


# ---------------------------------------------------------------- report generation (§7.3)

def generate_report(db: Session, live_class: LiveClass) -> ClassReport:
    """Idempotent: (re)builds the permanent report for an ended class. Flush-only;
    the caller commits (end_class does, right after)."""
    atts = db.query(LiveClassAttendance).filter(LiveClassAttendance.class_id == live_class.id).all()
    user_ids = {a.user_id for a in atts}
    names = {u.id: (u.display_name or u.user_login or f"user {u.id}") for u in
             db.query(User).filter(User.id.in_(list(user_ids) or [-1])).all()}
    attendance = []
    for a in atts:
        attendance.append({
            "user_id": a.user_id, "name": names.get(a.user_id, f"user {a.user_id}"),
            "joined_at": _utc(a.first_joined_at).isoformat() if a.first_joined_at else None,
            "left_at": _utc(a.last_heartbeat_at).isoformat() if a.last_heartbeat_at else None,
            "duration_s": int(a.accumulated_seconds or 0), "present": bool(a.present),
            "source": a.source.value if getattr(a, "source", None) is not None else None,
        })
    attendance.sort(key=lambda r: (-r["duration_s"], r["name"].lower()))

    polls = []
    from app.services.live_class_service import poll_tallies
    for p in db.query(LiveClassPoll).filter(LiveClassPoll.class_id == live_class.id).order_by(LiveClassPoll.id).all():
        try:
            tallies = poll_tallies(db, p)
        except Exception:
            tallies = []
        polls.append({"question": p.question, "options": list(p.options or []), "tallies": tallies,
                      "total": int(sum(tallies)) if tallies else 0, "status": p.status.value if p.status else None})

    events = []
    for e in (db.query(LiveClassEvent).filter(LiveClassEvent.class_id == live_class.id)
              .order_by(LiveClassEvent.created_at.asc(), LiveClassEvent.id.asc()).limit(500).all()):
        if e.event in ("heartbeat",):
            continue
        events.append({"t": _utc(e.created_at).isoformat() if e.created_at else None, "user_id": e.user_id,
                       "event": e.event, "payload": e.payload})

    started, ended = _utc(live_class.started_at), _utc(live_class.ended_at)
    duration_s = int((ended - started).total_seconds()) if started and ended and ended > started else 0
    from app.models.enrollment import Enrollment
    enrolled = db.query(Enrollment).filter(Enrollment.course_id == live_class.course_id,
                                           Enrollment.enrollment_status.in_(["enrolled", "completed"])).count()
    present = sum(1 for a in attendance if a["present"])
    joined = len(attendance)
    poll_votes = sum(p["total"] for p in polls)
    engagement = {
        "enrolled": enrolled, "joined": joined, "present": present,
        "present_pct": round(present / enrolled * 100, 1) if enrolled else None,
        "avg_duration_s": int(sum(a["duration_s"] for a in attendance) / joined) if joined else 0,
        "poll_votes": poll_votes, "events": len(events),
    }

    report = db.query(ClassReport).filter(ClassReport.class_id == live_class.id).first()
    if report is None:
        report = ClassReport(class_id=live_class.id, course_id=live_class.course_id,
                             instructor_id=live_class.instructor_id, title=live_class.title)
        db.add(report)
    report.title = live_class.title
    report.purpose = getattr(live_class, "purpose", None)
    report.scheduled_start = live_class.scheduled_start
    report.started_at = live_class.started_at
    report.ended_at = live_class.ended_at
    report.duration_s = duration_s
    report.attendance = attendance
    report.event_log = events
    report.poll_results = polls
    report.engagement = engagement
    db.flush()
    return report


def report_dict(db: Session, live_class: LiveClass, report: ClassReport) -> dict:
    return {
        "class_id": live_class.id, "course_id": live_class.course_id, "title": report.title,
        "purpose": report.purpose, "mode": getattr(live_class, "mode", None), "audience": getattr(live_class, "audience", None),
        "recording_policy": getattr(live_class, "recording_policy", None),
        "lifecycle": lifecycle(live_class, report),
        "scheduled_start": _utc(report.scheduled_start), "started_at": _utc(report.started_at), "ended_at": _utc(report.ended_at),
        "duration_s": report.duration_s, "attendance": report.attendance or [], "event_log": report.event_log or [],
        "poll_results": report.poll_results or [], "engagement": report.engagement or {},
        "instructor_notes": report.instructor_notes or "", "transcript": report.transcript, "ai_topics": report.ai_topics,
        "processing_status": report.processing_status, "shared_with_guardians": bool(report.shared_with_guardians),
        "recording": {
            "exists": bool(live_class.recording_video_id) and not getattr(live_class, "recording_deleted_at", None),
            "retention_until": _utc(getattr(live_class, "retention_until", None)),
            "deleted_at": _utc(getattr(live_class, "recording_deleted_at", None)),
            "restorable_until": (_utc(getattr(live_class, "recording_deleted_at", None)) + timedelta(days=SOFT_DELETE_GRACE_DAYS))
            if getattr(live_class, "recording_deleted_at", None) else None,
            "days_left": (_utc(live_class.retention_until) - datetime.now(timezone.utc)).days
            if getattr(live_class, "retention_until", None) else None,
        },
        "generated_at": _utc(report.generated_at), "updated_at": _utc(report.updated_at),
    }


# ---------------------------------------------------------------- retention actions (§7.4)

def _audit(db: Session, class_id: int, actor_id: Optional[int], action: str, reason: Optional[str] = None,
           detail: Optional[dict] = None) -> None:
    db.add(RecordingAudit(class_id=class_id, actor_id=actor_id, action=action, reason=(reason or "")[:300] or None,
                          detail=detail))


def set_retention_on_end(live_class: LiveClass) -> None:
    days = clamp_retention_days((live_class.settings or {}).get("retention_days"))
    base = _utc(live_class.ended_at) or datetime.now(timezone.utc)
    live_class.retention_until = base + timedelta(days=days)


def soft_delete_recording(db: Session, live_class: LiveClass, actor: User, reason: str = "") -> None:
    if not live_class.recording_video_id:
        raise ValueError("No recording to delete")
    if getattr(live_class, "recording_deleted_at", None):
        raise ValueError("Recording is already deleted (restorable for 30 days)")
    live_class.recording_deleted_at = datetime.now(timezone.utc)
    live_class.recording_deleted_by = actor.id
    live_class.recording_delete_reason = (reason or "")[:300] or None
    _audit(db, live_class.id, actor.id, "soft_delete", reason)
    db.commit()


def restore_recording(db: Session, live_class: LiveClass, actor: User) -> None:
    deleted_at = _utc(getattr(live_class, "recording_deleted_at", None))
    if not deleted_at:
        raise ValueError("Recording is not deleted")
    if not live_class.recording_video_id:
        raise ValueError("Recording media is already purged and cannot be restored")
    if datetime.now(timezone.utc) > deleted_at + timedelta(days=SOFT_DELETE_GRACE_DAYS):
        raise ValueError("The 30-day restore window has passed")
    live_class.recording_deleted_at = None
    live_class.recording_deleted_by = None
    live_class.recording_delete_reason = None
    _audit(db, live_class.id, actor.id, "restore")
    db.commit()


def extend_retention(db: Session, live_class: LiveClass, actor: User, days: int) -> datetime:
    days = max(1, int(days))
    base = _utc(live_class.retention_until) or datetime.now(timezone.utc)
    ceiling = (_utc(live_class.ended_at) or datetime.now(timezone.utc)) + timedelta(days=retention_max_days())
    new_until = min(base + timedelta(days=days), ceiling)
    if new_until <= base:
        raise ValueError(f"Retention already at the tenant ceiling ({retention_max_days()} days after the class)")
    live_class.retention_until = new_until
    _audit(db, live_class.id, actor.id, "extend", detail={"days": days, "until": new_until.isoformat()})
    db.commit()
    return new_until


def expiring_recordings(db: Session, instructor_id: Optional[int], within_days: int = 14) -> List[LiveClass]:
    now = datetime.now(timezone.utc)
    q = (db.query(LiveClass)
         .filter(LiveClass.deleted_at.is_(None), LiveClass.recording_video_id.isnot(None),
                 LiveClass.recording_deleted_at.is_(None), LiveClass.retention_until.isnot(None),
                 LiveClass.retention_until <= now + timedelta(days=within_days)))
    if instructor_id is not None:
        q = q.filter(LiveClass.instructor_id == instructor_id)
    return q.order_by(LiveClass.retention_until.asc()).all()


def _already(db: Session, class_id: int, event: str) -> bool:
    return db.query(LiveClassEvent).filter(LiveClassEvent.class_id == class_id, LiveClassEvent.event == event).first() is not None


def retention_pass(db: Session, now: Optional[datetime] = None) -> Dict[str, int]:
    """Sweeper: expiry warnings at 14/3 days (idempotent via events + audit),
    hard purge past retention or 30 days after a soft delete. Reports stay."""
    now = now or datetime.now(timezone.utc)
    stats = {"warned": 0, "purged": 0}
    from app.services.live_class_service import log_event
    candidates = (db.query(LiveClass)
                  .filter(LiveClass.deleted_at.is_(None), LiveClass.recording_video_id.isnot(None)).all())
    for lc in candidates:
        try:
            ru = _utc(lc.retention_until)
            sd = _utc(getattr(lc, "recording_deleted_at", None))
            purge = (ru is not None and ru <= now) or (sd is not None and sd + timedelta(days=SOFT_DELETE_GRACE_DAYS) <= now)
            if purge:
                lc.recording_video_id = None
                lc.recording_deleted_at = lc.recording_deleted_at or now
                _audit(db, lc.id, None, "hard_delete", "retention expired" if ru and ru <= now else "grace window ended",
                       detail={"retention_until": ru.isoformat() if ru else None})
                log_event(db, lc.id, None, "recording.purged")
                db.commit()
                stats["purged"] += 1
                continue
            if ru is None or sd is not None:
                continue
            # Most urgent applicable window first: at 10 days left send the 14-day
            # warning, at ≤3 days the 3-day one (each once), never a stale 14-day
            # warning after the 3-day one already went out.
            days_left = (ru - now).total_seconds() / 86400
            applicable = [d for d in sorted(WARNING_DAYS) if days_left <= d]
            if applicable:
                d = applicable[0]
                marker = f"recording.expiry_warning_{d}d"
                if not _already(db, lc.id, marker):
                    log_event(db, lc.id, None, marker, {"retention_until": ru.isoformat(), "days": d})
                    _audit(db, lc.id, None, "expiry_warning", f"{d} days before expiry")
                    db.commit()
                    stats["warned"] += 1
                    _notify_expiry(db, lc, d)
        except Exception:
            db.rollback()
            logger.exception("retention pass failed for class %s", lc.id)
    return stats


def _notify_expiry(db: Session, lc: LiveClass, days: int) -> None:
    """Best-effort: email the instructor with a one-click extend link."""
    try:
        from app.services.email_service import EmailService  # type: ignore
        u = db.query(User).filter(User.id == lc.instructor_id).first()
        if not u or not u.user_email:
            return
        EmailService.send_email(  # type: ignore[attr-defined]
            to=u.user_email, subject=f"Recording of '{lc.title}' expires in {days} days",
            body=(f"The recording of your class '{lc.title}' will be deleted in {days} days "
                  f"(retention until {lc.retention_until}). Open Past classes → Extend to keep it. "
                  "The class report, attendance and transcript are kept forever."),
        )
    except Exception:
        pass


def download_manifest(db: Session, course_id: int, instructor_id: Optional[int]) -> List[dict]:
    """'Download all first' — every live recording in a course as a manifest."""
    q = (db.query(LiveClass)
         .filter(LiveClass.course_id == course_id, LiveClass.deleted_at.is_(None),
                 LiveClass.recording_video_id.isnot(None), LiveClass.recording_deleted_at.is_(None)))
    if instructor_id is not None:
        q = q.filter(LiveClass.instructor_id == instructor_id)
    return [{"class_id": lc.id, "title": lc.title, "ended_at": _utc(lc.ended_at), "recording_video_id": lc.recording_video_id,
             "retention_until": _utc(lc.retention_until), "download_endpoint": f"/api/v1/live/classes/{lc.id}/recording-download"}
            for lc in q.order_by(LiveClass.scheduled_start.desc()).all()]


# ---------------------------------------------------------------- PDF export (§7.3)

def render_report_pdf(data: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    st = getSampleStyleSheet()
    story = [Paragraph(f"Class report — {data['title']}", st["Title"]),
             Paragraph(f"Purpose: {data.get('purpose') or '—'} · Started: {data.get('started_at') or '—'} · "
                       f"Ended: {data.get('ended_at') or '—'} · Duration: {data.get('duration_s', 0) // 60} min", st["Normal"]),
             Spacer(1, 10)]
    eng = data.get("engagement") or {}
    story.append(Paragraph(f"Engagement: enrolled {eng.get('enrolled', 0)}, joined {eng.get('joined', 0)}, "
                           f"present {eng.get('present', 0)} ({eng.get('present_pct') or 0}%), poll votes {eng.get('poll_votes', 0)}", st["Normal"]))
    story.append(Spacer(1, 8))
    rows = [["Learner", "Joined", "Left", "Minutes", "Present"]]
    for a in data.get("attendance") or []:
        rows.append([a.get("name", ""), (a.get("joined_at") or "")[11:16], (a.get("left_at") or "")[11:16],
                     str(int(a.get("duration_s", 0) // 60)), "yes" if a.get("present") else "no"])
    t = Table(rows, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                           ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    story.append(t)
    for p in data.get("poll_results") or []:
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"Poll: {p['question']}", st["Heading4"]))
        for opt, n in zip(p.get("options") or [], p.get("tallies") or []):
            story.append(Paragraph(f"• {opt}: {n}", st["Normal"]))
    if data.get("instructor_notes"):
        story.append(Spacer(1, 8))
        story.append(Paragraph("Instructor notes", st["Heading4"]))
        story.append(Paragraph(str(data["instructor_notes"]).replace("\n", "<br/>"), st["Normal"]))
    if data.get("ai_topics"):
        story.append(Spacer(1, 8))
        story.append(Paragraph("Key topics", st["Heading4"]))
        for tpc in data["ai_topics"]:
            story.append(Paragraph(f"• {tpc.get('topic', tpc) if isinstance(tpc, dict) else tpc}", st["Normal"]))
    doc.build(story)
    return buf.getvalue()
