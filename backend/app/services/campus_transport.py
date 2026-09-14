"""Campus transport: routes, stops, assignments, boarding, and the fee link.

A route with a fee owns one published tuition plan; assigning a student
assigns that plan, so the existing ledger, reminders and receipts apply.
"""

import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func

from app.models.campus_operations import ParentLinkRequest
from app.models.campus_transport import (
    CampusTransportAssignment,
    CampusTransportLog,
    CampusTransportRoute,
    CampusTransportStop,
)
from app.models.institution import InstitutionMember
from app.models.tuition import TuitionFeePlan
from app.models.user import User
from app.schemas.tuition import FeeAssignmentCreate, FeePlanCreate
from app.services import institution_service as institution_svc
from app.services import tuition_service


# ---------------------------------------------------------------- helpers


def _zone(institution):
    try:
        return ZoneInfo(institution.timezone)
    except Exception:
        return timezone.utc


def _today(institution):
    return datetime.now(_zone(institution)).date()


def _route(db, institution, route_id, *, lock=False):
    query = db.query(CampusTransportRoute).filter_by(id=route_id, institution_id=institution.id)
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Route not found.")
    return row


def _member_name(db, member_id):
    row = (
        db.query(User.display_name)
        .join(InstitutionMember, InstitutionMember.user_id == User.id)
        .filter(InstitutionMember.id == member_id)
        .first()
    )
    return row[0] if row else None


def _active_count(db, route_id):
    return (
        db.query(func.count(CampusTransportAssignment.id))
        .filter_by(route_id=route_id, status="active")
        .scalar()
        or 0
    )


def _learner_member(db, institution, user, student_user_id=None):
    if user.role == "parent":
        if not student_user_id:
            raise HTTPException(422, "Choose an approved student account.")
        approved = (
            db.query(ParentLinkRequest)
            .filter_by(parent_user_id=user.id, student_user_id=student_user_id, status="approved")
            .first()
        )
        if not approved:
            raise HTTPException(404, "Approved student account not found.")
        target = student_user_id
    else:
        if student_user_id and student_user_id != user.id:
            raise HTTPException(404, "Student account not found.")
        target = user.id
    member = (
        db.query(InstitutionMember)
        .filter_by(institution_id=institution.id, user_id=target, role="student", status="active")
        .first()
    )
    if not member:
        raise HTTPException(404, "Active student account not found in this institution.")
    return member


# --------------------------------------------------------------- fee plan


def _ensure_fee_plan(db, institution, user, name, amount, currency, code, label):
    """Create and publish a single-installment plan for a transport or hostel fee."""
    if amount is None or tuition_service.money(amount) <= tuition_service.ZERO:
        return None
    plan_name = f"{label} · {name}"[:160]
    due_on = _today(institution) + timedelta(days=30)
    data = FeePlanCreate(
        name=plan_name,
        academic_year=institution.academic_year,
        currency=currency.upper(),
        description=f"{label} fee for {name}",
        components=[{"code": code, "name": f"{label} fee", "amount": str(tuition_service.money(amount))}],
        installments=[{"name": f"{label} fee", "due_on": due_on, "amount": str(tuition_service.money(amount))}],
    )
    existing = (
        db.query(TuitionFeePlan)
        .filter_by(institution_id=institution.id, name=plan_name, academic_year=institution.academic_year)
        .first()
    )
    if existing:
        if existing.status != "published":
            tuition_service.publish_plan(db, institution.id, existing.id, user)
        return existing.id
    created = tuition_service.create_plan(db, institution.id, user, data)
    tuition_service.publish_plan(db, institution.id, created["id"], user)
    return created["id"]


def _assign_fee(db, institution, user, member, plan_id, note):
    if not plan_id:
        return None
    result = tuition_service.assign_plan(
        db, institution.id, user, FeeAssignmentCreate(student_member_id=member.id, plan_id=plan_id, note=note)
    )
    return result["id"]


# ----------------------------------------------------------------- routes


def stop_dict(row):
    return {
        "id": row.id,
        "sequence": row.sequence,
        "name": row.name,
        "pickup_time": row.pickup_time,
        "drop_time": row.drop_time,
        "landmark": row.landmark,
    }


def route_dict(db, row):
    stops = db.query(CampusTransportStop).filter_by(route_id=row.id).order_by(CampusTransportStop.sequence).all()
    return {
        "id": row.id,
        "name": row.name,
        "vehicle_number": row.vehicle_number,
        "driver_name": row.driver_name,
        "driver_phone": row.driver_phone,
        "capacity": row.capacity,
        "occupied": int(_active_count(db, row.id)),
        "fee_amount": tuition_service.number(row.fee_amount) if row.fee_amount is not None else None,
        "currency": row.currency,
        "fee_plan_id": row.fee_plan_id,
        "active": bool(row.active),
        "stops": [stop_dict(s) for s in stops],
    }


def list_routes(db, institution_id, user):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    rows = (
        db.query(CampusTransportRoute)
        .filter_by(institution_id=institution.id)
        .order_by(CampusTransportRoute.active.desc(), CampusTransportRoute.name)
        .all()
    )
    return [route_dict(db, row) for row in rows]


def _replace_stops(db, route, stops):
    existing = {s.id: s for s in db.query(CampusTransportStop).filter_by(route_id=route.id)}
    in_use = {
        sid
        for sid, in db.query(CampusTransportAssignment.stop_id).filter_by(route_id=route.id, status="active")
    }
    by_name = {s.name.strip().lower(): s for s in existing.values()}
    keep = set()
    for sequence, item in enumerate(stops, 1):
        row = by_name.get(item.name.strip().lower())
        if row is None:
            row = CampusTransportStop(route_id=route.id, name=item.name.strip())
            db.add(row)
        row.sequence = sequence + 1000  # park sequences to avoid unique clashes mid-update
        row.pickup_time = item.pickup_time
        row.drop_time = item.drop_time
        row.landmark = item.landmark.strip()
        db.flush()
        keep.add(row.id)
    for sid, row in existing.items():
        if sid not in keep:
            if sid in in_use:
                raise HTTPException(409, f"Stop '{row.name}' has students assigned and cannot be removed.")
            db.delete(row)
    db.flush()
    for sequence, row in enumerate(
        sorted(
            (r for r in db.query(CampusTransportStop).filter_by(route_id=route.id)),
            key=lambda r: r.sequence,
        ),
        1,
    ):
        row.sequence = sequence
    db.flush()


def create_route(db, institution_id, user, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    if db.query(CampusTransportRoute).filter_by(institution_id=institution.id, name=data.name.strip()).first():
        raise HTTPException(409, "A route with this name already exists.")
    row = CampusTransportRoute(
        institution_id=institution.id,
        name=data.name.strip(),
        vehicle_number=data.vehicle_number.strip(),
        driver_name=data.driver_name.strip(),
        driver_phone=data.driver_phone.strip(),
        capacity=data.capacity,
        fee_amount=tuition_service.money(data.fee_amount) if data.fee_amount is not None else None,
        currency=data.currency.upper(),
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    _replace_stops(db, row, data.stops)
    row.fee_plan_id = _ensure_fee_plan(db, institution, user, row.name, row.fee_amount, row.currency, "TRANSPORT", "Transport")
    institution_svc.audit(db, institution.id, user, "transport.route_created", f"{row.name} ({len(data.stops)} stops)")
    institution_svc.save(db)
    return route_dict(db, row)


def update_route(db, institution_id, user, route_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    row = _route(db, institution, route_id, lock=True)
    changes = data.model_dump(exclude_unset=True)
    stops = changes.pop("stops", None)
    for key, value in changes.items():
        setattr(row, key, value.strip() if isinstance(value, str) else value)
    if row.capacity < _active_count(db, row.id):
        raise HTTPException(422, "Capacity cannot be lower than the students already assigned.")
    if stops is not None:
        _replace_stops(db, row, data.stops)
    institution_svc.audit(db, institution.id, user, "transport.route_updated", row.name)
    institution_svc.save(db)
    return route_dict(db, row)


# ------------------------------------------------------------ assignments


def assignment_dict(db, row, log=None):
    stop = db.get(CampusTransportStop, row.stop_id)
    return {
        "id": row.id,
        "route_id": row.route_id,
        "stop_id": row.stop_id,
        "stop_name": stop.name if stop else None,
        "member_id": row.member_id,
        "student_name": _member_name(db, row.member_id),
        "fee_assignment_id": row.fee_assignment_id,
        "status": row.status,
        "started_on": row.started_on.isoformat(),
        "ended_on": row.ended_on.isoformat() if row.ended_on else None,
        "boarded": bool(log.boarded) if log else None,
        "dropped": bool(log.dropped) if log else None,
    }


def assign_student(db, institution_id, user, route_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    route = _route(db, institution, route_id, lock=True)
    if not route.active:
        raise HTTPException(409, "This route is inactive.")
    stop = db.query(CampusTransportStop).filter_by(id=data.stop_id, route_id=route.id).first()
    if not stop:
        raise HTTPException(404, "Stop not found on this route.")
    member, _account = tuition_service._student(db, institution.id, data.member_id)
    if db.query(CampusTransportAssignment).filter_by(member_id=member.id, status="active").first():
        raise HTTPException(409, "This student already has an active transport assignment.")
    if _active_count(db, route.id) >= route.capacity:
        raise HTTPException(409, "This route is full.")
    row = CampusTransportAssignment(
        institution_id=institution.id,
        route_id=route.id,
        stop_id=stop.id,
        member_id=member.id,
        status="active",
        started_on=_today(institution),
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    row.fee_assignment_id = _assign_fee(db, institution, user, member, route.fee_plan_id, f"Transport · {route.name}")
    institution_svc.audit(db, institution.id, user, "transport.student_assigned", f"member {member.id} → {route.name} / {stop.name}")
    institution_svc.save(db)
    return assignment_dict(db, row)


def end_assignment(db, institution_id, user, assignment_id):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    row = db.query(CampusTransportAssignment).filter_by(id=assignment_id, institution_id=institution.id).with_for_update().first()
    if not row:
        raise HTTPException(404, "Transport assignment not found.")
    if row.status != "active":
        raise HTTPException(409, "This assignment has already ended.")
    row.status = "ended"
    row.ended_on = _today(institution)
    institution_svc.audit(db, institution.id, user, "transport.student_removed", f"assignment #{row.id}")
    institution_svc.save(db)
    return assignment_dict(db, row)


# ---------------------------------------------------------------- boarding


def roster(db, institution_id, user, route_id, day=None):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    route = _route(db, institution, route_id)
    day = day or _today(institution)
    rows = (
        db.query(CampusTransportAssignment)
        .filter_by(route_id=route.id, status="active")
        .all()
    )
    logs = {
        log.member_id: log
        for log in db.query(CampusTransportLog).filter_by(route_id=route.id, day=day)
    }
    stops = {s.id: s for s in db.query(CampusTransportStop).filter_by(route_id=route.id)}
    items = [assignment_dict(db, row, logs.get(row.member_id)) for row in rows]
    items.sort(key=lambda item: (stops[item["stop_id"]].sequence if item["stop_id"] in stops else 0, item["student_name"] or ""))
    return {"route": route_dict(db, route), "day": day.isoformat(), "students": items}


def put_boarding(db, institution_id, user, route_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF, lock=True)
    route = _route(db, institution, route_id)
    if data.day > _today(institution):
        raise HTTPException(422, "Boarding cannot be recorded for a future day.")
    active = {
        row.member_id
        for row in db.query(CampusTransportAssignment).filter_by(route_id=route.id, status="active")
    }
    for entry in data.entries:
        if entry.member_id not in active:
            raise HTTPException(422, "Every student must be actively assigned to this route.")
    existing = {
        log.member_id: log
        for log in db.query(CampusTransportLog).filter(
            CampusTransportLog.route_id == route.id,
            CampusTransportLog.day == data.day,
            CampusTransportLog.member_id.in_([e.member_id for e in data.entries]),
        )
    }
    for entry in data.entries:
        log = existing.get(entry.member_id)
        if log is None:
            log = CampusTransportLog(institution_id=institution.id, route_id=route.id, member_id=entry.member_id, day=data.day)
            db.add(log)
        log.boarded = entry.boarded
        log.dropped = entry.dropped
        log.recorded_by = user.id
    institution_svc.audit(db, institution.id, user, "transport.boarding_recorded", f"{route.name} {data.day}: {len(data.entries)} row(s)")
    institution_svc.save(db)
    return roster(db, institution_id, user, route_id, data.day)


# --------------------------------------------------------------------- me


def me(db, institution_id, user, student_user_id=None):
    if user.role == "parent":
        from app.models.institution import Institution

        institution = db.get(Institution, institution_id)
        if not institution:
            raise HTTPException(404, "Institution not found.")
    else:
        institution, _ = institution_svc.scope(db, institution_id, user)
    member = _learner_member(db, institution, user, student_user_id)
    row = db.query(CampusTransportAssignment).filter_by(member_id=member.id, status="active").first()
    if not row:
        return {"assigned": False, "route": None, "stop": None, "today": None}
    route = db.get(CampusTransportRoute, row.route_id)
    stop = db.get(CampusTransportStop, row.stop_id)
    today = _today(institution)
    log = db.query(CampusTransportLog).filter_by(route_id=route.id, member_id=member.id, day=today).first()
    return {
        "assigned": True,
        "route": {
            "id": route.id,
            "name": route.name,
            "vehicle_number": route.vehicle_number,
            "driver_name": route.driver_name,
            "driver_phone": route.driver_phone,
        },
        "stop": stop_dict(stop) if stop else None,
        "today": {"day": today.isoformat(), "boarded": bool(log.boarded), "dropped": bool(log.dropped)} if log else None,
    }


# ------------------------------------------------------------ integration


def routes_without_boarding_today(db, institution, today):
    routes = db.query(CampusTransportRoute).filter_by(institution_id=institution.id, active=True).all()
    missing = 0
    for route in routes:
        if not _active_count(db, route.id):
            continue
        if not db.query(CampusTransportLog).filter_by(route_id=route.id, day=today).first():
            missing += 1
    return missing


# ------------------------------------------------------------------ report


def roster_csv(db, institution_id, user, route_id):
    data = roster(db, institution_id, user, route_id)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Route", "Stop", "Student", "Started on", "Boarded today", "Dropped today"])
    for item in data["students"]:
        writer.writerow(
            [
                data["route"]["name"],
                item["stop_name"] or "",
                item["student_name"] or "",
                item["started_on"],
                "" if item["boarded"] is None else ("yes" if item["boarded"] else "no"),
                "" if item["dropped"] is None else ("yes" if item["dropped"] else "no"),
            ]
        )
    return buffer.getvalue(), data["route"]["name"]
