"""Live-class attendance: role-scoped rows, CSV export, threshold recompute.

Mounted at /api/v1/live (see app/main.py) alongside the other live-class
routers. All three endpoints are gated to the assigned instructor or an
admin/superadmin (`live_class_service.is_assigned_instructor_or_admin`) — a
student never sees the roster, only their own `my_attendance` on
LiveClassOut (see live_class_service.live_class_to_out).
"""
import csv
import io
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.csv_safety import sanitize_csv_cell
from app.core.database import get_db
from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassStatus
from app.models.user import User
from app.schemas.live_class import AttendanceRowOut
from app.services import live_class_service
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_class_or_404(db: Session, class_id: int) -> LiveClass:
    # Mirrors live_class_session._get_class_or_404 / live_classes._get_class_or_404
    # — deleted_at must gate independently of status everywhere.
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
            detail="Only the assigned instructor may view attendance for this class",
        )


def _attendance_rows(db: Session, live_class: LiveClass) -> list[AttendanceRowOut]:
    rows = (
        db.query(LiveClassAttendance, User)
        .join(User, User.id == LiveClassAttendance.user_id)
        .filter(LiveClassAttendance.class_id == live_class.id)
        .order_by(User.display_name.asc())
        .all()
    )
    out: list[AttendanceRowOut] = []
    for att, user in rows:
        out.append(AttendanceRowOut(
            user_id=user.id,
            name=user.display_name or user.user_email,
            email=user.user_email,
            first_joined_at=att.first_joined_at,
            accumulated_minutes=(att.accumulated_seconds or 0) // 60,
            present=att.present,
        ))
    return out


# A participant counts as "live now" if their last heartbeat landed within
# this window. The clients beat every 60s (web JitsiStage and the Flutter
# join screen), so 2 minutes tolerates exactly one dropped/late beat before
# someone is considered gone — short enough that the number tracks reality,
# long enough not to flicker on a single slow request.
LIVE_PARTICIPANT_WINDOW_SECONDS = 120


def _live_participant_count(db: Session, live_class: LiveClass) -> int:
    """Participants currently in the room, derived from heartbeat recency.

    `LiveClass.live_participants` is a column that nothing ever writes, so
    reading it always returned 0 — the report tile was permanently dead.
    Counting recent heartbeats is the only signal the server actually has;
    it needs no new writer and no new column.

    Only meaningful while the class is LIVE: once it has ended the last
    heartbeats are still recent for up to two minutes, which would show
    phantom attendees on a finished class. Anything not LIVE is 0.
    """
    if live_class.status != LiveClassStatus.LIVE:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=LIVE_PARTICIPANT_WINDOW_SECONDS)
    rows = (
        db.query(LiveClassAttendance.last_heartbeat_at)
        .filter(
            LiveClassAttendance.class_id == live_class.id,
            LiveClassAttendance.last_heartbeat_at.isnot(None),
        )
        .all()
    )
    # Compare in Python via the service's _as_utc rather than in SQL: SQLite
    # strips tzinfo on round-trip (Postgres does not), so a naive stored value
    # compared against an aware cutoff raises there. _as_utc is the same
    # normaliser every other live-class time comparison uses.
    return sum(1 for (beat,) in rows if beat is not None and live_class_service._as_utc(beat) >= cutoff)


class AttendanceSummaryOut(BaseModel):
    rows: list[AttendanceRowOut]
    total_participants: int
    present_count: int
    live_participants: int


class RecomputeIn(BaseModel):
    threshold_pct: int = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# GET /classes/{id}/attendance
# ---------------------------------------------------------------------------

@router.get("/classes/{class_id}/attendance", response_model=AttendanceSummaryOut)
async def get_attendance(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    _require_staff(live_class, current_user)

    rows = _attendance_rows(db, live_class)
    present_count = sum(1 for r in rows if r.present is True)

    return AttendanceSummaryOut(
        rows=rows,
        total_participants=len(rows),
        present_count=present_count,
        live_participants=_live_participant_count(db, live_class),
    )


# ---------------------------------------------------------------------------
# GET /classes/{id}/attendance/export.csv
# ---------------------------------------------------------------------------

@router.get("/classes/{class_id}/attendance/export.csv")
async def export_attendance_csv(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    _require_staff(live_class, current_user)

    rows = _attendance_rows(db, live_class)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["name", "email", "first_join", "total_minutes", "present"])
    for row in rows:
        writer.writerow([
            sanitize_csv_cell(row.name),
            sanitize_csv_cell(row.email),
            row.first_joined_at.isoformat() if row.first_joined_at else "",
            row.accumulated_minutes,
            "" if row.present is None else str(row.present),
        ])
    csv_body = buffer.getvalue()

    live_class_service.log_event(
        db, live_class.id, current_user.id, "attendance.exported",
        payload={"row_count": len(rows)},
    )
    db.commit()

    filename = f"attendance-{live_class.id}.csv"
    return StreamingResponse(
        iter([csv_body]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /classes/{id}/attendance/recompute
# ---------------------------------------------------------------------------

@router.post("/classes/{class_id}/attendance/recompute", response_model=AttendanceSummaryOut)
async def recompute_attendance(
    class_id: int,
    payload: RecomputeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    _require_staff(live_class, current_user)

    if live_class.status != LiveClassStatus.ENDED:
        raise HTTPException(
            status_code=409,
            detail="Attendance can only be recomputed for a class that has ended",
        )

    merged = dict(live_class.settings or {})
    merged["attendance_threshold_pct"] = payload.threshold_pct
    live_class.settings = merged

    live_class_service.finalize_attendance(db, live_class)
    live_class_service.log_event(
        db, live_class.id, current_user.id, "attendance.recomputed",
        payload={"threshold_pct": payload.threshold_pct},
    )
    db.commit()
    db.refresh(live_class)

    # Gamification: sequenced AFTER the commit above so award()'s own
    # flush/rollback can never touch this request's just-persisted
    # attendance present-flags (H1 review fix). Idempotent — a re-recompute
    # never double-awards a user already credited for this class.
    live_class_service.award_attendance_xp(db, live_class)

    rows = _attendance_rows(db, live_class)
    present_count = sum(1 for r in rows if r.present is True)
    return AttendanceSummaryOut(
        rows=rows,
        total_participants=len(rows),
        present_count=present_count,
        live_participants=_live_participant_count(db, live_class),
    )
