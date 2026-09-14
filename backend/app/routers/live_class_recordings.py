"""Live-class recording intent endpoints + enrollment-gated playback.

Mounted at /api/v1/live (see app/main.py).

`POST .../recording/start|stop` record INTENT only — actual Jibri
start/stop is triggered client-side (per the brief's recording pipeline:
moderator-triggered file recording via the Jitsi IFrame API's
startRecording/stopRecording commands). This backend surface exists so the
UI has server-truth state (`recording_status`) and an audit trail
(`recording.started`/`recording.stopped` events) independent of whatever
the client-side Jitsi call actually did.

`GET .../recording-playback` exists because
GET /api/v1/bunny/video/{id}/playback's access check
(`_require_bunny_video_access` in app/routers/bunny.py) resolves the video
id's owning course by LIKE-matching a Lesson row's video URL columns — a
live-class recording's Bunny video id is never written into any Lesson row,
so that endpoint would 404 the video for EVERY caller, including the
assigned instructor and enrolled students. This endpoint enforces
`user_can_access_class` instead (the correct authorization boundary for a
live-class recording) and then delegates to the same Bunny URL-signing
helper bunny.py uses, so playback is protected identically (short-lived
signed HLS URL when BUNNY_TOKEN_AUTH_KEY is configured).

Unlike bunny.py's own playback endpoints (which fall back to an unsigned
URL — logging a warning — when BUNNY_TOKEN_AUTH_KEY is blank), this
endpoint REFUSES to serve an unsigned URL: recordings are meant to be
enrollment-gated, but the CDN URL itself has no auth of its own once
handed to the client, so an "unsigned" URL from here would be a permanent,
un-revocable public capability for anyone who obtains it (unlike the
request that fetched it, which was correctly access-checked). Returning
503 when signing isn't configured keeps that authorization boundary real
instead of silently downgrading it.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.live_class import LiveClass, RecordingStatus
from app.models.user import User
from app.routers import bunny as bunny_router
from app.schemas.live_class import RecordingIntentOut, RecordingPlaybackOut
from app.services import live_class_service
from app.services.auth_service import AuthService

router = APIRouter()


def _get_class_or_404(db: Session, class_id: int) -> LiveClass:
    lc = (
        db.query(LiveClass)
        .filter(LiveClass.id == class_id, LiveClass.deleted_at.is_(None))
        .first()
    )
    if not lc:
        raise HTTPException(status_code=404, detail="Live class not found")
    return lc


def _require_staff(live_class: LiveClass, user: User) -> None:
    if not live_class_service.is_assigned_instructor_or_admin(live_class, user):
        raise HTTPException(
            status_code=403,
            detail="Only the assigned instructor may control recording for this class",
        )


@router.post("/classes/{class_id}/recording/start", response_model=RecordingIntentOut)
async def start_recording(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    _require_staff(live_class, current_user)

    live_class.recording_status = RecordingStatus.REQUESTED
    live_class_service.log_event(db, live_class.id, current_user.id, "recording.started")
    db.commit()
    db.refresh(live_class)

    return RecordingIntentOut(class_id=live_class.id, recording_status=live_class.recording_status.value)


@router.post("/classes/{class_id}/recording/stop", response_model=RecordingIntentOut)
async def stop_recording(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    _require_staff(live_class, current_user)

    live_class_service.log_event(db, live_class.id, current_user.id, "recording.stopped")
    db.commit()
    db.refresh(live_class)

    return RecordingIntentOut(class_id=live_class.id, recording_status=live_class.recording_status.value)


@router.get("/past-classes-report")
async def past_classes_report(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Past-classes report (owner request 2026-09-04): one row per ended
    class — schedule, title, recording availability, live attendance count.
    Admins see every class; instructors see their own; students see classes
    of courses they are enrolled in."""
    from app.models.enrollment import Enrollment
    from app.models.live_class import LiveClassAttendance

    query = db.query(LiveClass).filter(LiveClass.deleted_at.is_(None))
    if current_user.role == "admin":
        pass
    elif current_user.role == "instructor":
        query = query.filter(LiveClass.instructor_id == current_user.id)
    else:
        enrolled = [e.course_id for e in db.query(Enrollment).filter(
            Enrollment.user_id == current_user.id).all()]
        query = query.filter(LiveClass.course_id.in_(enrolled or [-1]))
    if course_id:
        query = query.filter(LiveClass.course_id == course_id)

    rows = query.order_by(LiveClass.created_at.desc()).limit(200).all()
    report = []
    for c in rows:
        attendance = db.query(LiveClassAttendance).filter(
            LiveClassAttendance.class_id == c.id).count()
        ended = bool(c.ended_at) if getattr(c, "ended_at", None) is not None else None
        report.append({
            "class_id": c.id,
            "course_id": c.course_id,
            "title": c.title,
            "scheduled_at": c.created_at.isoformat() if c.created_at else None,
            "ended": ended,
            "attendance_count": attendance,
            "has_recording": bool(c.recording_video_id) and not getattr(c, "recording_deleted_at", None),
            # v2.0 §7 (WP5): lifecycle + retention state + permanent report presence
            "lifecycle": _lifecycle_of(db, c),
            "purpose": getattr(c, "purpose", None),
            "retention_until": _crs_utc(getattr(c, "retention_until", None)),
            "days_left": ((_crs_utc(c.retention_until) - datetime.now(timezone.utc)).days if getattr(c, "retention_until", None) else None),
            "recording_deleted_at": _crs_utc(getattr(c, "recording_deleted_at", None)),
            "has_report": _has_report(db, c.id),
        })
    return {"classes": report, "count": len(report)}


@router.get("/classes/{class_id}/recording-download")
async def recording_download(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Download intent for a recording: returns the same signed playback URL
    the player uses (HLS) — Bunny serves the media, gated identically to
    playback (admin sees all; instructor owns; student enrolled). The
    download-then-delete flow is: fetch this, capture offline, then DELETE."""
    return await get_recording_playback(class_id, db, current_user)


@router.delete("/classes/{class_id}/recording")
async def delete_recording(
    class_id: int,
    reason: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Soft-delete a class's recording (instructor owner or admin) — v2.0 §7.4:
    30-day grace with restore, audit-logged, hard purge by the sweeper. The
    class report, transcript and attendance are permanent and untouched."""
    live_class = db.query(LiveClass).filter(
        LiveClass.id == class_id, LiveClass.deleted_at.is_(None)).first()
    if not live_class:
        raise HTTPException(status_code=404, detail="Class not found")
    if current_user.role != "admin" and live_class.instructor_id != current_user.id:
        raise HTTPException(status_code=403,
                            detail="Only the class instructor or an admin can delete recordings")
    from app.services import class_report_service as crs
    try:
        crs.soft_delete_recording(db, live_class, current_user, reason or "")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"deleted": True, "class_id": class_id, "restorable_days": crs.SOFT_DELETE_GRACE_DAYS}


def _crs_utc(dt):
    from app.services.class_report_service import _utc
    return _utc(dt)


def _lifecycle_of(db: Session, c: LiveClass) -> str:
    from app.models.live_class_report import ClassReport
    from app.services.class_report_service import lifecycle
    rep = db.query(ClassReport).filter(ClassReport.class_id == c.id).first()
    return lifecycle(c, rep)


def _has_report(db: Session, class_id: int) -> bool:
    from app.models.live_class_report import ClassReport
    return db.query(ClassReport.id).filter(ClassReport.class_id == class_id).first() is not None


def _owner_or_admin(db: Session, class_id: int, current_user: User) -> LiveClass:
    live_class = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not live_class:
        raise HTTPException(status_code=404, detail="Class not found")
    if current_user.role != "admin" and live_class.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the class instructor or an admin may do this")
    return live_class


@router.post("/classes/{class_id}/recording/restore")
async def restore_recording(class_id: int, db: Session = Depends(get_db),
                            current_user: User = Depends(AuthService.get_current_active_user)):
    from app.services import class_report_service as crs
    live_class = _owner_or_admin(db, class_id, current_user)
    try:
        crs.restore_recording(db, live_class, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"restored": True, "class_id": class_id}


@router.post("/classes/{class_id}/recording/extend")
async def extend_recording(class_id: int, payload: dict, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    from app.services import class_report_service as crs
    live_class = _owner_or_admin(db, class_id, current_user)
    days = payload.get("days", 30)
    if not isinstance(days, int) or isinstance(days, bool) or days < 1:
        raise HTTPException(status_code=422, detail="days must be a positive integer")
    try:
        until = crs.extend_retention(db, live_class, current_user, days)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"class_id": class_id, "retention_until": until}


@router.get("/recordings/expiring")
async def expiring(within_days: int = 14, db: Session = Depends(get_db),
                   current_user: User = Depends(AuthService.get_current_active_user)):
    from app.services import class_report_service as crs
    if current_user.role not in ("instructor", "admin"):
        raise HTTPException(status_code=403, detail="Instructors and admins only")
    rows = crs.expiring_recordings(db, None if current_user.role == "admin" else current_user.id, max(1, min(within_days, 365)))
    return {"classes": [{"class_id": lc.id, "title": lc.title, "retention_until": crs._utc(lc.retention_until),
                         "days_left": (crs._utc(lc.retention_until) - datetime.now(timezone.utc)).days if lc.retention_until else None}
                        for lc in rows]}


@router.get("/courses/{course_id}/recordings/manifest")
async def recordings_manifest(course_id: int, db: Session = Depends(get_db),
                              current_user: User = Depends(AuthService.get_current_active_user)):
    """'Download all first' — one manifest of every live recording in a course."""
    from app.services import class_report_service as crs
    if current_user.role not in ("instructor", "admin"):
        raise HTTPException(status_code=403, detail="Instructors and admins only")
    return {"course_id": course_id,
            "recordings": crs.download_manifest(db, course_id, None if current_user.role == "admin" else current_user.id)}


@router.get("/recordings/audit")
async def recordings_audit(class_id: int | None = None, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.require_admin)):
    from app.models.live_class_report import RecordingAudit
    q = db.query(RecordingAudit)
    if class_id is not None:
        q = q.filter(RecordingAudit.class_id == class_id)
    rows = q.order_by(RecordingAudit.created_at.desc(), RecordingAudit.id.desc()).limit(500).all()
    return {"audit": [{"id": a.id, "class_id": a.class_id, "actor_id": a.actor_id, "action": a.action,
                       "reason": a.reason, "detail": a.detail, "created_at": a.created_at} for a in rows]}


def _report_access(db: Session, class_id: int, current_user: User):
    from app.models.live_class_report import ClassReport
    live_class = db.query(LiveClass).filter(LiveClass.id == class_id).first()
    if not live_class:
        raise HTTPException(status_code=404, detail="Class not found")
    report = db.query(ClassReport).filter(ClassReport.class_id == class_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="No report yet — reports are generated when a class ends")
    if current_user.role in ("admin", "superadmin") or live_class.instructor_id == current_user.id:
        return live_class, report, True
    if current_user.role == "student":
        from app.models.enrollment import Enrollment
        enrolled = db.query(Enrollment).filter(Enrollment.course_id == live_class.course_id, Enrollment.user_id == current_user.id,
                                               Enrollment.enrollment_status.in_(["enrolled", "completed"])).first()
        if enrolled:
            return live_class, report, False
    if current_user.role == "parent" and report.shared_with_guardians:
        return live_class, report, False
    raise HTTPException(status_code=403, detail="Not allowed to view this class report")


@router.get("/classes/{class_id}/report")
async def get_class_report(class_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    from app.services import class_report_service as crs
    live_class, report, full = _report_access(db, class_id, current_user)
    data = crs.report_dict(db, live_class, report)
    if not full:
        # learners/guardians: their own attendance row only, no event log
        data["attendance"] = [a for a in data["attendance"] if a.get("user_id") == current_user.id] if current_user.role == "student" else []
        data["event_log"] = []
    return data


@router.put("/classes/{class_id}/report/notes")
async def put_report_notes(class_id: int, payload: dict, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    from app.models.live_class_report import ClassReport
    _owner_or_admin(db, class_id, current_user)
    report = db.query(ClassReport).filter(ClassReport.class_id == class_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="No report yet")
    notes = payload.get("instructor_notes", "")
    if not isinstance(notes, str) or len(notes) > 20000:
        raise HTTPException(status_code=422, detail="instructor_notes must be a string (≤ 20000 chars)")
    report.instructor_notes = notes
    db.commit()
    return {"class_id": class_id, "instructor_notes": report.instructor_notes}


@router.post("/classes/{class_id}/report/share-guardians")
async def share_report_with_guardians(class_id: int, payload: dict, db: Session = Depends(get_db),
                                      current_user: User = Depends(AuthService.get_current_active_user)):
    from app.models.live_class_report import ClassReport
    _owner_or_admin(db, class_id, current_user)
    report = db.query(ClassReport).filter(ClassReport.class_id == class_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="No report yet")
    report.shared_with_guardians = bool(payload.get("shared", True))
    db.commit()
    return {"class_id": class_id, "shared_with_guardians": report.shared_with_guardians}


@router.get("/classes/{class_id}/report.pdf")
async def class_report_pdf(class_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    from fastapi.responses import Response
    from app.services import class_report_service as crs
    live_class, report, full = _report_access(db, class_id, current_user)
    if not full:
        raise HTTPException(status_code=403, detail="Only the instructor or an admin can export the full report")
    pdf = crs.render_report_pdf(crs.report_dict(db, live_class, report))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="class-{class_id}-report.pdf"'})


@router.get("/classes/{class_id}/recording-playback", response_model=RecordingPlaybackOut)
async def get_recording_playback(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Enrollment-gated playback for a live class's recording. See module
    docstring for why this exists instead of using
    GET /api/v1/bunny/video/{id}/playback directly."""
    live_class = _get_class_or_404(db, class_id)
    if not live_class_service.user_can_access_class(db, live_class, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this class")

    if not live_class.recording_video_id or getattr(live_class, "recording_deleted_at", None):
        raise HTTPException(status_code=404, detail="No recording is available for this class")

    if not bunny_router.BUNNY_TOKEN_AUTH_KEY:
        # See module docstring: an unsigned Bunny CDN URL is a permanent
        # public capability once issued, which would defeat the whole
        # point of enrollment-gating this endpoint. Refuse rather than
        # silently degrade to bunny.py's own unsigned fallback.
        raise HTTPException(status_code=503, detail="Recording playback is not configured")

    video_id = live_class.recording_video_id
    return RecordingPlaybackOut(
        class_id=live_class.id,
        video_id=video_id,
        hls_url=bunny_router._playback_url(video_id),
        expires_in=bunny_router.BUNNY_SIGNED_URL_TTL,
        signed=True,
    )


@router.post("/classes/{class_id}/report/transcript")
async def paste_transcript(class_id: int, payload: dict, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    """Engine A (WP7) manual path: the owner pastes a transcript (or the
    auto-captions export). Same processing as the worker ingest."""
    from app.models.live_class_report import ClassReport
    from app.services import ai_layer_service as ai_svc
    _owner_or_admin(db, class_id, current_user)
    transcript = (payload.get("transcript") or "").strip()
    if len(transcript) < 20:
        raise HTTPException(status_code=422, detail="transcript is too short")
    report = db.query(ClassReport).filter(ClassReport.class_id == class_id).first()
    if report is None:
        raise HTTPException(status_code=409, detail="No class report yet — end the class first")
    result = ai_svc.process_transcript(db, report, transcript, actor_id=current_user.id)
    return {"class_id": class_id, **result}
