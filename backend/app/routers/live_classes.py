"""Live-class scheduling CRUD: create (one-off + weekly recurrence),
role-aware listing, detail, patch, soft-cancel, live-now, and ICS export.

Mounted at /api/v1/live (see app/main.py) alongside the session router.
Shares LiveClass access rules with live_class_session.py:
`live_class_service.user_can_access_class` (assigned instructor / admin /
enrolled student). Creation and mutation additionally require the caller to
be the assigned instructor or an admin/superadmin ("assigned instructor or
admin" — deviations file item 3).

Response assembly (LiveClassOut), recurrence date math, list/live-now
visibility scoping, and ICS body building live in live_class_service.py to
keep this router under the ~400-line-per-router budget.
"""
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.live_class import LiveClass, LiveClassSchedule, LiveClassStatus
from app.models.user import User
from app.schemas.live_class import (
    LiveClassCreate,
    LiveClassListOut,
    LiveClassOut,
    LiveClassUpdate,
    LiveNowOut,
)
from app.services import live_class_service
from app.services.auth_service import AuthService
from app.services.course_access import can_edit

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

_as_utc = live_class_service._as_utc
_to_out = live_class_service.live_class_to_out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_class_or_404(db: Session, class_id: int) -> LiveClass:
    # deleted_at must gate independently of status — mirrors
    # live_class_session._get_class_or_404 so a soft-cancelled class 404s
    # everywhere, not just in the session router.
    lc = (
        db.query(LiveClass)
        .filter(LiveClass.id == class_id, LiveClass.deleted_at.is_(None))
        .first()
    )
    if not lc:
        raise HTTPException(status_code=404, detail="Live class not found")
    return lc


def _get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# ---------------------------------------------------------------------------
# POST /classes — create (one-off or weekly recurrence)
# ---------------------------------------------------------------------------

@router.post("/classes", response_model=list[LiveClassOut], status_code=201)
async def create_class(
    payload: LiveClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    course = _get_course_or_404(db, payload.course_id)
    if not can_edit(db, course, current_user):
        raise HTTPException(status_code=403, detail="You do not own this course")

    tz_name = payload.timezone or "Asia/Kolkata"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Unknown timezone: {tz_name}")

    duration = timedelta(minutes=payload.duration_minutes)
    settings_dict = (payload.settings.model_dump() if payload.settings else None) or {
        "lobby_enabled": True, "start_muted": True, "allow_chat": True,
        "allow_share": True, "record": False, "attendance_threshold_pct": 60,
    }

    is_recurring = bool(payload.recurrence_weekly and payload.weeks)
    if is_recurring:
        starts_local = live_class_service.generate_occurrence_starts(
            payload.scheduled_start, payload.recurrence_weekly, payload.weeks, tz,
        )
    else:
        starts_local = [payload.scheduled_start.astimezone(tz)]

    # Every POST /classes call creates exactly one LiveClassSchedule parent
    # — including a one-off class — so every LiveClass row always has a
    # schedule_id to group by (a one-off is simply a schedule with one
    # occurrence). recurrence_weekly/weeks stay null on the schedule row for
    # a one-off, matching LiveClassCreate's own optionality.
    schedule = LiveClassSchedule(
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        instructor_id=current_user.id,
        title=payload.title,
        description=payload.description,
        timezone=tz_name,
        recurrence_weekly=list(payload.recurrence_weekly) if is_recurring else None,
        weeks=payload.weeks if is_recurring else None,
    )
    db.add(schedule)
    db.flush()

    created_rows: list[LiveClass] = []
    for start_local in starts_local:
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = start_utc + duration
        lc = LiveClass(
            schedule_id=schedule.id,
            course_id=payload.course_id,
            lesson_id=payload.lesson_id,
            instructor_id=current_user.id,
            title=payload.title,
            description=payload.description,
            scheduled_start=start_utc,
            scheduled_end=end_utc,
            timezone=tz_name,
            room_name=live_class_service.generate_room_name(),
            status=LiveClassStatus.SCHEDULED,
            settings=dict(settings_dict),
            purpose=settings_dict.get("purpose"), mode=settings_dict.get("mode"),
            audience=settings_dict.get("audience"), recording_policy=settings_dict.get("recording_policy"),
        )
        db.add(lc)
        db.flush()
        live_class_service.log_event(db, lc.id, current_user.id, "class.created")
        created_rows.append(lc)

    db.commit()
    for lc in created_rows:
        db.refresh(lc)

    return [_to_out(db, lc, current_user) for lc in created_rows]


# ---------------------------------------------------------------------------
# GET /classes — role-aware list
# ---------------------------------------------------------------------------

@router.get("/classes", response_model=LiveClassListOut)
async def list_classes(
    scope: str = Query(default="upcoming"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    page_size = min(page_size, MAX_PAGE_SIZE)
    now = datetime.now(timezone.utc)

    query = db.query(LiveClass).filter(LiveClass.deleted_at.is_(None))
    query = live_class_service.apply_scope_visibility(query, scope, current_user, db)

    if scope == "upcoming":
        query = query.filter(
            LiveClass.scheduled_start >= now,
            LiveClass.status.in_([LiveClassStatus.SCHEDULED, LiveClassStatus.LIVE]),
        ).order_by(LiveClass.scheduled_start.asc())
    elif scope == "past":
        query = query.filter(
            (LiveClass.status == LiveClassStatus.ENDED) | (LiveClass.scheduled_end < now)
        ).order_by(LiveClass.scheduled_start.desc())
    elif scope == "live":
        query = query.filter(LiveClass.status == LiveClassStatus.LIVE).order_by(
            LiveClass.scheduled_start.asc()
        )
    elif scope.startswith("course:"):
        query = query.order_by(LiveClass.scheduled_start.asc())
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scope: {scope}")

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [_to_out(db, lc, current_user) for lc in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


# ---------------------------------------------------------------------------
# GET /live-now
# ---------------------------------------------------------------------------

@router.get("/live-now", response_model=LiveNowOut)
async def live_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    query = db.query(LiveClass).filter(
        LiveClass.deleted_at.is_(None), LiveClass.status == LiveClassStatus.LIVE,
    )
    query = live_class_service.apply_scope_visibility(query, "live", current_user, db)
    rows = query.order_by(LiveClass.scheduled_start.asc()).all()
    return LiveNowOut(classes=[_to_out(db, lc, current_user) for lc in rows])


# ---------------------------------------------------------------------------
# GET /classes/{id} — detail
# ---------------------------------------------------------------------------

@router.get("/classes/{class_id}", response_model=LiveClassOut)
async def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    if not live_class_service.user_can_access_class(db, live_class, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this class")
    return _to_out(db, live_class, current_user)


# ---------------------------------------------------------------------------
# PATCH /classes/{id}
# ---------------------------------------------------------------------------

@router.patch("/classes/{class_id}", response_model=LiveClassOut)
async def update_class(
    class_id: int,
    payload: LiveClassUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    if not live_class_service.is_assigned_instructor_or_admin(live_class, current_user):
        raise HTTPException(status_code=403, detail="Only the assigned instructor may edit this class")

    if live_class.status != LiveClassStatus.SCHEDULED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit a class in status {live_class.status.value}",
        )

    duration_minutes = payload.duration_minutes
    new_start = payload.scheduled_start
    if new_start is not None or duration_minutes is not None:
        start_utc = _as_utc(new_start) if new_start is not None else _as_utc(live_class.scheduled_start)
        if duration_minutes is not None:
            duration = timedelta(minutes=duration_minutes)
        else:
            duration = _as_utc(live_class.scheduled_end) - _as_utc(live_class.scheduled_start)
        live_class.scheduled_start = start_utc
        live_class.scheduled_end = start_utc + duration

    if payload.title is not None:
        live_class.title = payload.title
    if payload.description is not None:
        live_class.description = payload.description
    if payload.timezone is not None:
        live_class.timezone = payload.timezone
    if payload.settings is not None:
        # Shallow-merge only the keys the caller actually set (exclude_unset)
        # over the existing settings dict — LiveClassSettingsPatch leaves
        # every unspecified field None rather than filling it with a
        # default, so `exclude_unset=True` (not a plain model_dump(), which
        # would include every None) is what makes a PATCH of just
        # {"record": true} preserve an existing attendance_threshold_pct of
        # 90 instead of resetting it to LiveClassSettings' default of 60.
        merged = dict(live_class.settings or {})
        merged.update(payload.settings.model_dump(exclude_unset=True))
        live_class.settings = merged

    live_class_service.log_event(db, live_class.id, current_user.id, "class.updated")
    db.commit()
    db.refresh(live_class)
    return _to_out(db, live_class, current_user)


# ---------------------------------------------------------------------------
# DELETE /classes/{id} — soft cancel
# ---------------------------------------------------------------------------

@router.delete("/classes/{class_id}", response_model=LiveClassOut)
async def cancel_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    # _get_class_or_404 filters deleted_at.is_(None), so a class already
    # cancelled by a prior DELETE never reaches this handler again — it
    # 404s at the lookup instead. There is no reachable "already CANCELLED"
    # state here to special-case; a second DELETE on the same class is
    # exercised as a 404, not a no-op 200 (see
    # test_cancel_twice_404s_on_second_call).
    live_class = _get_class_or_404(db, class_id)
    if not live_class_service.is_assigned_instructor_or_admin(live_class, current_user):
        raise HTTPException(status_code=403, detail="Only the assigned instructor may cancel this class")

    if live_class.status == LiveClassStatus.ENDED:
        raise HTTPException(status_code=409, detail="Cannot cancel a class that has already ended")

    live_class.status = LiveClassStatus.CANCELLED
    live_class.deleted_at = datetime.now(timezone.utc)
    live_class_service.log_event(db, live_class.id, current_user.id, "class.cancelled")
    db.commit()
    db.refresh(live_class)

    return _to_out(db, live_class, current_user)


# ---------------------------------------------------------------------------
# GET /classes/{id}/calendar.ics
# ---------------------------------------------------------------------------

@router.get("/classes/{class_id}/calendar.ics")
async def calendar_ics(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    live_class = _get_class_or_404(db, class_id)
    if not live_class_service.user_can_access_class(db, live_class, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this class")

    body = live_class_service.build_ics(live_class)
    return Response(
        content=body,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="live-class-{live_class.id}.ics"',
        },
    )
