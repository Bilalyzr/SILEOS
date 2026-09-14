"""Staff leave and substitution.

Teachers apply, managers decide against derived balances, approval turns the
absent teacher's timetable slots into substitutions, and only genuinely free
colleagues can be assigned to them.
"""

import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, or_

from app.models.campus_pilot import CampusEvent
from app.models.campus_staff import CampusLeaveRequest, CampusLeaveType, CampusSubstitution
from app.models.institution import InstitutionBatch, InstitutionMember
from app.models.user import User
from app.services import institution_service as institution_svc


# ---------------------------------------------------------------- helpers


def _zone(institution):
    try:
        return ZoneInfo(institution.timezone)
    except Exception:
        return timezone.utc


def _local_date(value, zone):
    return institution_svc.utc(value).astimezone(zone).date()


def _range_bounds(starts_on, ends_on, zone):
    """UTC datetimes bounding the inclusive local date range."""
    start = datetime.combine(starts_on, datetime.min.time(), tzinfo=zone)
    end = datetime.combine(ends_on + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def _member_name(db, member_id):
    if not member_id:
        return None
    row = (
        db.query(User.display_name)
        .join(InstitutionMember, InstitutionMember.user_id == User.id)
        .filter(InstitutionMember.id == member_id)
        .first()
    )
    return row[0] if row else None


def _staff_member(db, institution_id, member_id):
    row = (
        db.query(InstitutionMember)
        .filter_by(id=member_id, institution_id=institution_id, status="active")
        .first()
    )
    if not row or row.role not in institution_svc.STAFF:
        raise HTTPException(404, "Staff member not found.")
    return row


def _leave(db, institution, leave_id, *, lock=False):
    query = db.query(CampusLeaveRequest).filter_by(id=leave_id, institution_id=institution.id)
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Leave request not found.")
    return row


def _type(db, institution, type_id):
    row = db.query(CampusLeaveType).filter_by(id=type_id, institution_id=institution.id).first()
    if not row:
        raise HTTPException(404, "Leave type not found.")
    return row




# ------------------------------------------------------------ leave types


def type_dict(row):
    return {
        "id": row.id,
        "academic_year": row.academic_year,
        "code": row.code,
        "name": row.name,
        "annual_quota": row.annual_quota,
    }


def list_types(db, institution_id, user, academic_year=None):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    year = academic_year or institution.academic_year
    rows = (
        db.query(CampusLeaveType)
        .filter_by(institution_id=institution.id, academic_year=year)
        .order_by(CampusLeaveType.code)
        .all()
    )
    return {"academic_year": year, "types": [type_dict(row) for row in rows]}


def put_types(db, institution_id, user, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    existing = {
        row.code: row
        for row in db.query(CampusLeaveType).filter_by(
            institution_id=institution.id, academic_year=data.academic_year
        )
    }
    wanted = {item.code for item in data.types}
    for code, row in existing.items():
        if code not in wanted:
            if db.query(CampusLeaveRequest).filter_by(type_id=row.id).count():
                raise HTTPException(409, f"Leave type {code} has requests and cannot be removed.")
            db.delete(row)
    for item in data.types:
        row = existing.get(item.code)
        if row is None:
            row = CampusLeaveType(
                institution_id=institution.id,
                academic_year=data.academic_year,
                code=item.code,
                created_by=user.id,
            )
            db.add(row)
        row.name = item.name.strip()
        row.annual_quota = item.annual_quota
    institution_svc.audit(db, institution.id, user, "staff.leave_types_saved", f"{data.academic_year}: {len(data.types)} type(s)")
    institution_svc.save(db)
    return list_types(db, institution_id, user, data.academic_year)


# --------------------------------------------------------------- balances


def _used_days(db, member_id, type_id, academic_year):
    total = (
        db.query(func.coalesce(func.sum(CampusLeaveRequest.days), 0))
        .join(CampusLeaveType, CampusLeaveType.id == CampusLeaveRequest.type_id)
        .filter(
            CampusLeaveRequest.member_id == member_id,
            CampusLeaveRequest.type_id == type_id,
            CampusLeaveRequest.status == "approved",
            CampusLeaveType.academic_year == academic_year,
        )
        .scalar()
    )
    return int(total or 0)


def _balances_for(db, institution, member, academic_year):
    rows = (
        db.query(CampusLeaveType)
        .filter_by(institution_id=institution.id, academic_year=academic_year)
        .order_by(CampusLeaveType.code)
        .all()
    )
    out = []
    for row in rows:
        used = _used_days(db, member.id, row.id, academic_year)
        out.append(
            {
                "type_id": row.id,
                "code": row.code,
                "name": row.name,
                "quota": row.annual_quota,
                "used": used,
                "remaining": max(0, row.annual_quota - used),
            }
        )
    return out


def balances(db, institution_id, user, member_id=None, academic_year=None):
    institution, actor = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    target = actor
    if member_id and member_id != actor.id:
        if actor.role not in institution_svc.MANAGERS:
            raise HTTPException(403, "Only managers can view another member's balances.")
        target = _staff_member(db, institution.id, member_id)
    year = academic_year or institution.academic_year
    return {
        "member_id": target.id,
        "name": _member_name(db, target.id),
        "academic_year": year,
        "balances": _balances_for(db, institution, target, year),
    }


# --------------------------------------------------------------- requests


def leave_dict(db, row):
    leave_type = db.get(CampusLeaveType, row.type_id)
    subs = db.query(CampusSubstitution).filter_by(leave_id=row.id).all()
    return {
        "id": row.id,
        "member_id": row.member_id,
        "member_name": _member_name(db, row.member_id),
        "type_id": row.type_id,
        "type_code": leave_type.code if leave_type else None,
        "type_name": leave_type.name if leave_type else None,
        "starts_on": row.starts_on.isoformat(),
        "ends_on": row.ends_on.isoformat(),
        "days": row.days,
        "note": row.note,
        "status": row.status,
        "decided_by": row.decided_by,
        "decided_at": institution_svc.utc(row.decided_at).isoformat() if row.decided_at else None,
        "decision_note": row.decision_note,
        "override": bool(row.override),
        "substitutions": {
            "total": len(subs),
            "open": sum(1 for s in subs if s.status == "open"),
            "assigned": sum(1 for s in subs if s.status == "assigned"),
        },
        "created_at": institution_svc.utc(row.created_at).isoformat() if row.created_at else None,
    }


def list_leave(db, institution_id, user, status=None, member_id=None, limit=200):
    institution, actor = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    query = db.query(CampusLeaveRequest).filter_by(institution_id=institution.id)
    if actor.role not in institution_svc.MANAGERS:
        query = query.filter(CampusLeaveRequest.member_id == actor.id)
    elif member_id:
        query = query.filter(CampusLeaveRequest.member_id == member_id)
    if status:
        query = query.filter(CampusLeaveRequest.status == status)
    rows = query.order_by(CampusLeaveRequest.starts_on.desc(), CampusLeaveRequest.id.desc()).limit(limit).all()
    return [leave_dict(db, row) for row in rows]


def create_leave(db, institution_id, user, data):
    institution, actor = institution_svc.scope(db, institution_id, user, institution_svc.STAFF, lock=True)
    leave_type = _type(db, institution, data.type_id)
    overlap = (
        db.query(CampusLeaveRequest)
        .filter(
            CampusLeaveRequest.member_id == actor.id,
            CampusLeaveRequest.status.in_(("pending", "approved")),
            CampusLeaveRequest.starts_on <= data.ends_on,
            CampusLeaveRequest.ends_on >= data.starts_on,
        )
        .first()
    )
    if overlap:
        raise HTTPException(409, "You already have a pending or approved leave in that period.")
    row = CampusLeaveRequest(
        institution_id=institution.id,
        member_id=actor.id,
        type_id=leave_type.id,
        starts_on=data.starts_on,
        ends_on=data.ends_on,
        days=(data.ends_on - data.starts_on).days + 1,
        note=data.note.strip(),
        status="pending",
    )
    db.add(row)
    institution_svc.audit(db, institution.id, user, "staff.leave_requested", f"{leave_type.code} {data.starts_on} to {data.ends_on}")
    institution_svc.save(db)
    db.refresh(row)
    return leave_dict(db, row)


def _events_in_range(db, institution, member_id, starts_on, ends_on):
    start, end = _range_bounds(starts_on, ends_on, _zone(institution))
    return (
        db.query(CampusEvent)
        .filter(
            CampusEvent.institution_id == institution.id,
            CampusEvent.teacher_id == member_id,
            CampusEvent.starts_at >= start,
            CampusEvent.starts_at < end,
        )
        .order_by(CampusEvent.starts_at)
        .all()
    )


def approve_leave(db, institution_id, user, leave_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    row = _leave(db, institution, leave_id, lock=True)
    if row.status != "pending":
        raise HTTPException(409, "Only pending requests can be approved.")
    leave_type = _type(db, institution, row.type_id)
    used = _used_days(db, row.member_id, row.type_id, leave_type.academic_year)
    if used + row.days > leave_type.annual_quota:
        if not data.override:
            raise HTTPException(
                422,
                f"Approving would exceed the {leave_type.code} quota "
                f"({used} used of {leave_type.annual_quota}, {row.days} requested). Override with a note to proceed.",
            )
        if not data.note.strip():
            raise HTTPException(422, "An override needs a note explaining the decision.")
    row.status = "approved"
    row.decided_by = user.id
    row.decided_at = datetime.now(timezone.utc)
    row.decision_note = data.note.strip()
    row.override = bool(data.override and used + row.days > leave_type.annual_quota)
    created = 0
    for event in _events_in_range(db, institution, row.member_id, row.starts_on, row.ends_on):
        exists = db.query(CampusSubstitution).filter_by(leave_id=row.id, event_id=event.id).first()
        if exists is None:
            db.add(
                CampusSubstitution(
                    institution_id=institution.id,
                    leave_id=row.id,
                    event_id=event.id,
                    absent_member_id=row.member_id,
                    status="open",
                )
            )
            created += 1
    institution_svc.audit(db, institution.id, user, "staff.leave_approved", f"#{row.id} {leave_type.code} {row.days} day(s), {created} substitution(s)")
    institution_svc.save(db)
    return leave_dict(db, row)


def reject_leave(db, institution_id, user, leave_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    row = _leave(db, institution, leave_id, lock=True)
    if row.status != "pending":
        raise HTTPException(409, "Only pending requests can be rejected.")
    row.status = "rejected"
    row.decided_by = user.id
    row.decided_at = datetime.now(timezone.utc)
    row.decision_note = data.note.strip()
    institution_svc.audit(db, institution.id, user, "staff.leave_rejected", f"#{row.id}: {row.decision_note[:120]}")
    institution_svc.save(db)
    return leave_dict(db, row)


def cancel_leave(db, institution_id, user, leave_id):
    institution, actor = institution_svc.scope(db, institution_id, user, institution_svc.STAFF, lock=True)
    row = _leave(db, institution, leave_id, lock=True)
    manager = actor.role in institution_svc.MANAGERS
    if row.member_id != actor.id and not manager:
        raise HTTPException(404, "Leave request not found.")
    if row.status not in ("pending", "approved"):
        raise HTTPException(409, "Only pending or approved requests can be cancelled.")
    if row.status == "approved" and not manager:
        today = datetime.now(_zone(institution)).date()
        if row.starts_on <= today:
            raise HTTPException(409, "Leave that has already started can only be cancelled by a manager.")
    row.status = "cancelled"
    row.decided_by = user.id
    row.decided_at = datetime.now(timezone.utc)
    released = 0
    for sub in db.query(CampusSubstitution).filter_by(leave_id=row.id):
        if sub.status != "released":
            sub.status = "released"
            released += 1
    institution_svc.audit(db, institution.id, user, "staff.leave_cancelled", f"#{row.id}, {released} substitution(s) released")
    institution_svc.save(db)
    return leave_dict(db, row)


# ---------------------------------------------------------- substitutions


def substitution_dict(db, row):
    event = db.get(CampusEvent, row.event_id)
    batch = db.get(InstitutionBatch, event.batch_id) if event and event.batch_id else None
    return {
        "id": row.id,
        "leave_id": row.leave_id,
        "event_id": row.event_id,
        "title": event.title if event else "",
        "kind": event.kind if event else "",
        "starts_at": institution_svc.utc(event.starts_at).isoformat() if event else None,
        "ends_at": institution_svc.utc(event.ends_at).isoformat() if event else None,
        "room": event.room if event else "",
        "batch_id": event.batch_id if event else None,
        "batch_name": batch.name if batch else None,
        "absent_member_id": row.absent_member_id,
        "absent_name": _member_name(db, row.absent_member_id),
        "substitute_member_id": row.substitute_member_id,
        "substitute_name": _member_name(db, row.substitute_member_id),
        "status": row.status,
        "note": row.note,
        "assigned_at": institution_svc.utc(row.assigned_at).isoformat() if row.assigned_at else None,
    }


def _substitution(db, institution, sub_id, *, lock=False):
    query = db.query(CampusSubstitution).filter_by(id=sub_id, institution_id=institution.id)
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Substitution not found.")
    return row


def list_substitutions(db, institution_id, user, status=None, starts_after=None, starts_before=None, limit=500):
    institution, actor = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    query = (
        db.query(CampusSubstitution)
        .join(CampusEvent, CampusEvent.id == CampusSubstitution.event_id)
        .filter(CampusSubstitution.institution_id == institution.id)
    )
    if actor.role not in institution_svc.MANAGERS:
        query = query.filter(
            or_(
                CampusSubstitution.absent_member_id == actor.id,
                CampusSubstitution.substitute_member_id == actor.id,
            )
        )
    if status:
        query = query.filter(CampusSubstitution.status == status)
    if starts_after:
        query = query.filter(CampusEvent.starts_at >= starts_after)
    if starts_before:
        query = query.filter(CampusEvent.starts_at < starts_before)
    rows = query.order_by(CampusEvent.starts_at, CampusSubstitution.id).limit(limit).all()
    return [substitution_dict(db, row) for row in rows]


def _busy_member_ids(db, institution, event, exclude_sub_id=None):
    """Members who cannot cover `event`: owners of overlapping events, already
    substituting an overlapping slot, or on approved leave that day."""
    overlapping_owner = {
        row[0]
        for row in db.query(CampusEvent.teacher_id).filter(
            CampusEvent.institution_id == institution.id,
            CampusEvent.teacher_id.isnot(None),
            CampusEvent.starts_at < event.ends_at,
            CampusEvent.ends_at > event.starts_at,
        )
    }
    sub_query = (
        db.query(CampusSubstitution.substitute_member_id)
        .join(CampusEvent, CampusEvent.id == CampusSubstitution.event_id)
        .filter(
            CampusSubstitution.institution_id == institution.id,
            CampusSubstitution.status == "assigned",
            CampusEvent.starts_at < event.ends_at,
            CampusEvent.ends_at > event.starts_at,
        )
    )
    if exclude_sub_id:
        sub_query = sub_query.filter(CampusSubstitution.id != exclude_sub_id)
    already_substituting = {row[0] for row in sub_query if row[0]}
    day = _local_date(event.starts_at, _zone(institution))
    on_leave = {
        row[0]
        for row in db.query(CampusLeaveRequest.member_id).filter(
            CampusLeaveRequest.institution_id == institution.id,
            CampusLeaveRequest.status == "approved",
            CampusLeaveRequest.starts_on <= day,
            CampusLeaveRequest.ends_on >= day,
        )
    }
    return overlapping_owner | already_substituting | on_leave


def candidates(db, institution_id, user, sub_id):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS)
    sub = _substitution(db, institution, sub_id)
    event = db.get(CampusEvent, sub.event_id)
    busy = _busy_member_ids(db, institution, event, exclude_sub_id=sub.id)
    busy.add(sub.absent_member_id)
    rows = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(
            InstitutionMember.institution_id == institution.id,
            InstitutionMember.status == "active",
            InstitutionMember.role.in_(institution_svc.STAFF),
            User.is_active.is_(True),
        )
        .order_by(User.display_name)
        .all()
    )
    return [
        {"member_id": member.id, "name": account.display_name, "role": member.role, "department": member.department}
        for member, account in rows
        if member.id not in busy
    ]


def assign(db, institution_id, user, sub_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    sub = _substitution(db, institution, sub_id, lock=True)
    if sub.status == "released":
        raise HTTPException(409, "This substitution was released when the leave was cancelled.")
    candidate = _staff_member(db, institution.id, data.substitute_member_id)
    if candidate.id == sub.absent_member_id:
        raise HTTPException(422, "The absent teacher cannot substitute their own class.")
    event = db.get(CampusEvent, sub.event_id)
    if candidate.id in _busy_member_ids(db, institution, event, exclude_sub_id=sub.id):
        raise HTTPException(422, "That teacher is not free for this slot.")
    sub.substitute_member_id = candidate.id
    sub.status = "assigned"
    sub.assigned_by = user.id
    sub.assigned_at = datetime.now(timezone.utc)
    sub.note = data.note.strip()
    institution_svc.audit(db, institution.id, user, "staff.substitution_assigned", f"#{sub.id} → member {candidate.id}")
    institution_svc.save(db)
    return substitution_dict(db, sub)


def unassign(db, institution_id, user, sub_id):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    sub = _substitution(db, institution, sub_id, lock=True)
    if sub.status != "assigned":
        raise HTTPException(409, "Only assigned substitutions can be unassigned.")
    sub.substitute_member_id = None
    sub.status = "open"
    sub.assigned_by = user.id
    sub.assigned_at = None
    institution_svc.audit(db, institution.id, user, "staff.substitution_unassigned", f"#{sub.id}")
    institution_svc.save(db)
    return substitution_dict(db, sub)


# ------------------------------------------------------------ integration


def substitute_for_event(db, event_id):
    """(substitute_member_id, substitute_name) for an assigned substitution, else (None, None)."""
    row = (
        db.query(CampusSubstitution)
        .filter_by(event_id=event_id, status="assigned")
        .order_by(CampusSubstitution.id.desc())
        .first()
    )
    if row is None:
        return None, None
    return row.substitute_member_id, _member_name(db, row.substitute_member_id)


def substituted_event_ids(db, member_id):
    return [
        row[0]
        for row in db.query(CampusSubstitution.event_id).filter_by(substitute_member_id=member_id, status="assigned")
    ]


def open_substitutions_soon(db, institution_id, now, days=7):
    return (
        db.query(func.count(CampusSubstitution.id))
        .join(CampusEvent, CampusEvent.id == CampusSubstitution.event_id)
        .filter(
            CampusSubstitution.institution_id == institution_id,
            CampusSubstitution.status == "open",
            CampusEvent.starts_at >= now,
            CampusEvent.starts_at < now + timedelta(days=days),
        )
        .scalar()
        or 0
    )


# ------------------------------------------------------------------ report


def leave_report(db, institution_id, user, academic_year=None):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS)
    year = academic_year or institution.academic_year
    types = (
        db.query(CampusLeaveType)
        .filter_by(institution_id=institution.id, academic_year=year)
        .order_by(CampusLeaveType.code)
        .all()
    )
    staff = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(
            InstitutionMember.institution_id == institution.id,
            InstitutionMember.status == "active",
            InstitutionMember.role.in_(institution_svc.STAFF),
        )
        .order_by(User.display_name)
        .all()
    )
    hours = {}
    for sub, event in (
        db.query(CampusSubstitution, CampusEvent)
        .join(CampusEvent, CampusEvent.id == CampusSubstitution.event_id)
        .filter(CampusSubstitution.institution_id == institution.id, CampusSubstitution.status == "assigned")
    ):
        seconds = (institution_svc.utc(event.ends_at) - institution_svc.utc(event.starts_at)).total_seconds()
        hours[sub.substitute_member_id] = hours.get(sub.substitute_member_id, 0.0) + seconds / 3600
    rows = []
    for member, account in staff:
        balances_by_code = {}
        for leave_type in types:
            used = _used_days(db, member.id, leave_type.id, year)
            balances_by_code[leave_type.code] = {
                "quota": leave_type.annual_quota,
                "used": used,
                "remaining": max(0, leave_type.annual_quota - used),
            }
        rows.append(
            {
                "member_id": member.id,
                "name": account.display_name,
                "role": member.role,
                "department": member.department,
                "balances": balances_by_code,
                "substitution_hours": round(hours.get(member.id, 0.0), 2),
            }
        )
    return {"academic_year": year, "types": [type_dict(t) for t in types], "rows": rows}


def leave_report_csv(report):
    buffer = StringIO()
    writer = csv.writer(buffer)
    codes = [t["code"] for t in report["types"]]
    header = ["Name", "Role", "Department"]
    for code in codes:
        header += [f"{code} quota", f"{code} used", f"{code} remaining"]
    header.append("Substitution hours")
    writer.writerow(header)
    for row in report["rows"]:
        line = [row["name"], row["role"], row["department"]]
        for code in codes:
            balance = row["balances"].get(code, {"quota": 0, "used": 0, "remaining": 0})
            line += [balance["quota"], balance["used"], balance["remaining"]]
        line.append(row["substitution_hours"])
        writer.writerow(line)
    return buffer.getvalue()

