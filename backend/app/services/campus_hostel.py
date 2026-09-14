"""Campus hostel: blocks, rooms, allocations, out-passes, visitors, fee link."""

import csv
from datetime import datetime, timezone
from io import StringIO

from fastapi import HTTPException
from sqlalchemy import func

from app.models.campus_hostel import (
    CampusHostelAllocation,
    CampusHostelBlock,
    CampusHostelPass,
    CampusHostelRoom,
    CampusHostelVisitor,
)
from app.models.institution import Institution, InstitutionMember
from app.services import institution_service as institution_svc
from app.services import tuition_service
from app.services.campus_transport import _assign_fee, _ensure_fee_plan, _learner_member, _member_name, _today


# ---------------------------------------------------------------- helpers


def _block(db, institution, block_id, *, lock=False):
    query = db.query(CampusHostelBlock).filter_by(id=block_id, institution_id=institution.id)
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Hostel block not found.")
    return row


def _room(db, institution, room_id):
    row = (
        db.query(CampusHostelRoom)
        .join(CampusHostelBlock, CampusHostelBlock.id == CampusHostelRoom.block_id)
        .filter(CampusHostelRoom.id == room_id, CampusHostelBlock.institution_id == institution.id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Room not found.")
    return row


def _occupancy(db, room_id):
    return db.query(func.count(CampusHostelAllocation.id)).filter_by(room_id=room_id, status="active").scalar() or 0


def _reader(db, institution_id, user):
    if user.role == "parent":
        institution = db.get(Institution, institution_id)
        if not institution:
            raise HTTPException(404, "Institution not found.")
        return institution, None
    return institution_svc.scope(db, institution_id, user)


# ---------------------------------------------------------- blocks, rooms


def room_dict(db, row):
    return {
        "id": row.id,
        "block_id": row.block_id,
        "number": row.number,
        "floor": row.floor,
        "room_type": row.room_type,
        "capacity": row.capacity,
        "occupied": int(_occupancy(db, row.id)),
        "active": bool(row.active),
    }


def block_dict(db, row):
    rooms = db.query(CampusHostelRoom).filter_by(block_id=row.id).order_by(CampusHostelRoom.floor, CampusHostelRoom.number).all()
    room_rows = [room_dict(db, r) for r in rooms]
    return {
        "id": row.id,
        "name": row.name,
        "warden_member_id": row.warden_member_id,
        "warden_name": _member_name(db, row.warden_member_id) if row.warden_member_id else None,
        "gender": row.gender,
        "fee_amount": tuition_service.number(row.fee_amount) if row.fee_amount is not None else None,
        "currency": row.currency,
        "fee_plan_id": row.fee_plan_id,
        "active": bool(row.active),
        "capacity": sum(r["capacity"] for r in room_rows if r["active"]),
        "occupied": sum(r["occupied"] for r in room_rows),
        "rooms": room_rows,
    }


def list_blocks(db, institution_id, user):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    rows = db.query(CampusHostelBlock).filter_by(institution_id=institution.id).order_by(CampusHostelBlock.active.desc(), CampusHostelBlock.name).all()
    return [block_dict(db, row) for row in rows]


def _replace_rooms(db, block, rooms):
    existing = {r.number.strip().lower(): r for r in db.query(CampusHostelRoom).filter_by(block_id=block.id)}
    keep = set()
    for item in rooms:
        key = item.number.strip().lower()
        row = existing.get(key)
        if row is None:
            row = CampusHostelRoom(block_id=block.id, number=item.number.strip())
            db.add(row)
        row.floor = item.floor.strip()
        row.room_type = item.room_type
        row.capacity = item.capacity
        row.active = item.active
        db.flush()
        if row.capacity < _occupancy(db, row.id):
            raise HTTPException(422, f"Room {row.number} already houses more students than the new capacity.")
        keep.add(row.id)
    for row in existing.values():
        if row.id not in keep:
            if _occupancy(db, row.id):
                raise HTTPException(409, f"Room {row.number} has students allocated and cannot be removed.")
            db.delete(row)
    db.flush()


def create_block(db, institution_id, user, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    if db.query(CampusHostelBlock).filter_by(institution_id=institution.id, name=data.name.strip()).first():
        raise HTTPException(409, "A block with this name already exists.")
    if data.warden_member_id:
        warden = db.query(InstitutionMember).filter_by(id=data.warden_member_id, institution_id=institution.id, status="active").first()
        if not warden or warden.role not in institution_svc.STAFF:
            raise HTTPException(422, "The warden must be an active staff member.")
    row = CampusHostelBlock(
        institution_id=institution.id,
        name=data.name.strip(),
        warden_member_id=data.warden_member_id,
        gender=data.gender,
        fee_amount=tuition_service.money(data.fee_amount) if data.fee_amount is not None else None,
        currency=data.currency.upper(),
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    _replace_rooms(db, row, data.rooms)
    row.fee_plan_id = _ensure_fee_plan(db, institution, user, row.name, row.fee_amount, row.currency, "HOSTEL", "Hostel")
    institution_svc.audit(db, institution.id, user, "hostel.block_created", f"{row.name} ({len(data.rooms)} rooms)")
    institution_svc.save(db)
    return block_dict(db, row)


def update_block(db, institution_id, user, block_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    row = _block(db, institution, block_id, lock=True)
    changes = data.model_dump(exclude_unset=True)
    if "warden_member_id" in changes and changes["warden_member_id"]:
        warden = db.query(InstitutionMember).filter_by(id=changes["warden_member_id"], institution_id=institution.id, status="active").first()
        if not warden or warden.role not in institution_svc.STAFF:
            raise HTTPException(422, "The warden must be an active staff member.")
    for key, value in changes.items():
        setattr(row, key, value.strip() if isinstance(value, str) else value)
    institution_svc.audit(db, institution.id, user, "hostel.block_updated", row.name)
    institution_svc.save(db)
    return block_dict(db, row)


def put_rooms(db, institution_id, user, block_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    row = _block(db, institution, block_id, lock=True)
    _replace_rooms(db, row, data.rooms)
    institution_svc.audit(db, institution.id, user, "hostel.rooms_saved", f"{row.name}: {len(data.rooms)} room(s)")
    institution_svc.save(db)
    return block_dict(db, row)


# ------------------------------------------------------------ allocations


def allocation_dict(db, row):
    room = db.get(CampusHostelRoom, row.room_id)
    block = db.get(CampusHostelBlock, room.block_id) if room else None
    return {
        "id": row.id,
        "room_id": row.room_id,
        "room_number": room.number if room else None,
        "block_id": block.id if block else None,
        "block_name": block.name if block else None,
        "member_id": row.member_id,
        "student_name": _member_name(db, row.member_id),
        "fee_assignment_id": row.fee_assignment_id,
        "status": row.status,
        "checked_in_on": row.checked_in_on.isoformat(),
        "checked_out_on": row.checked_out_on.isoformat() if row.checked_out_on else None,
    }


def allocate(db, institution_id, user, room_id, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    room = _room(db, institution, room_id)
    block = db.get(CampusHostelBlock, room.block_id)
    if not room.active or not block.active:
        raise HTTPException(409, "This room is not available.")
    member, _account = tuition_service._student(db, institution.id, data.member_id)
    if db.query(CampusHostelAllocation).filter_by(member_id=member.id, status="active").first():
        raise HTTPException(409, "This student already has a hostel room.")
    if _occupancy(db, room.id) >= room.capacity:
        raise HTTPException(409, "This room is full.")
    row = CampusHostelAllocation(
        institution_id=institution.id,
        room_id=room.id,
        member_id=member.id,
        status="active",
        checked_in_on=_today(institution),
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    row.fee_assignment_id = _assign_fee(db, institution, user, member, block.fee_plan_id, f"Hostel · {block.name}")
    institution_svc.audit(db, institution.id, user, "hostel.allocated", f"member {member.id} → {block.name} / {room.number}")
    institution_svc.save(db)
    return allocation_dict(db, row)


def checkout(db, institution_id, user, allocation_id):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    row = db.query(CampusHostelAllocation).filter_by(id=allocation_id, institution_id=institution.id).with_for_update().first()
    if not row:
        raise HTTPException(404, "Allocation not found.")
    if row.status != "active":
        raise HTTPException(409, "This allocation has already ended.")
    row.status = "ended"
    row.checked_out_on = _today(institution)
    institution_svc.audit(db, institution.id, user, "hostel.checked_out", f"allocation #{row.id}")
    institution_svc.save(db)
    return allocation_dict(db, row)


def occupancy(db, institution_id, user):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    blocks = list_blocks(db, institution_id, user)
    allocations = (
        db.query(CampusHostelAllocation)
        .filter_by(institution_id=institution.id, status="active")
        .order_by(CampusHostelAllocation.room_id, CampusHostelAllocation.id)
        .all()
    )
    return {
        "blocks": blocks,
        "allocations": [allocation_dict(db, row) for row in allocations],
        "capacity": sum(b["capacity"] for b in blocks if b["active"]),
        "occupied": sum(b["occupied"] for b in blocks),
    }


# ----------------------------------------------------------------- passes


def pass_dict(db, row):
    return {
        "id": row.id,
        "member_id": row.member_id,
        "student_name": _member_name(db, row.member_id),
        "kind": row.kind,
        "reason": row.reason,
        "leaves_at": institution_svc.utc(row.leaves_at).isoformat(),
        "returns_at": institution_svc.utc(row.returns_at).isoformat(),
        "status": row.status,
        "decided_by": row.decided_by,
        "decided_at": institution_svc.utc(row.decided_at).isoformat() if row.decided_at else None,
        "decision_note": row.decision_note,
        "returned_at": institution_svc.utc(row.returned_at).isoformat() if row.returned_at else None,
        "created_at": institution_svc.utc(row.created_at).isoformat() if row.created_at else None,
    }


def list_passes(db, institution_id, user, status=None, student_user_id=None, limit=200):
    institution, member = _reader(db, institution_id, user)
    query = db.query(CampusHostelPass).filter_by(institution_id=institution.id)
    if member is None or member.role not in institution_svc.STAFF:
        learner = member if member is not None and member.role == "student" else _learner_member(db, institution, user, student_user_id)
        query = query.filter(CampusHostelPass.member_id == learner.id)
    if status:
        query = query.filter(CampusHostelPass.status == status)
    rows = query.order_by(CampusHostelPass.leaves_at.desc(), CampusHostelPass.id.desc()).limit(limit).all()
    return [pass_dict(db, row) for row in rows]


def create_pass(db, institution_id, user, data):
    institution, member = institution_svc.scope(db, institution_id, user, lock=True)
    if member.role != "student":
        raise HTTPException(403, "Only hostel residents request passes.")
    if not db.query(CampusHostelAllocation).filter_by(member_id=member.id, status="active").first():
        raise HTTPException(409, "You are not allocated to a hostel room.")
    overlap = (
        db.query(CampusHostelPass)
        .filter(
            CampusHostelPass.member_id == member.id,
            CampusHostelPass.status.in_(("pending", "approved")),
            CampusHostelPass.leaves_at < data.returns_at.astimezone(timezone.utc),
            CampusHostelPass.returns_at > data.leaves_at.astimezone(timezone.utc),
        )
        .first()
    )
    if overlap:
        raise HTTPException(409, "You already have a pending or approved pass for that time.")
    row = CampusHostelPass(
        institution_id=institution.id,
        member_id=member.id,
        kind=data.kind,
        reason=data.reason.strip(),
        leaves_at=data.leaves_at.astimezone(timezone.utc),
        returns_at=data.returns_at.astimezone(timezone.utc),
        status="pending",
    )
    db.add(row)
    institution_svc.audit(db, institution.id, user, "hostel.pass_requested", f"{data.kind} {data.leaves_at.isoformat()}")
    institution_svc.save(db)
    db.refresh(row)
    return pass_dict(db, row)


def _pass(db, institution, pass_id):
    row = db.query(CampusHostelPass).filter_by(id=pass_id, institution_id=institution.id).with_for_update().first()
    if not row:
        raise HTTPException(404, "Pass not found.")
    return row


def decide_pass(db, institution_id, user, pass_id, approve, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF, lock=True)
    row = _pass(db, institution, pass_id)
    if row.status != "pending":
        raise HTTPException(409, "Only pending passes can be decided.")
    if not approve and not data.note.strip():
        raise HTTPException(422, "A rejection needs a reason.")
    row.status = "approved" if approve else "rejected"
    row.decided_by = user.id
    row.decided_at = datetime.now(timezone.utc)
    row.decision_note = data.note.strip()
    institution_svc.audit(db, institution.id, user, f"hostel.pass_{row.status}", f"#{row.id}")
    institution_svc.save(db)
    return pass_dict(db, row)


def mark_returned(db, institution_id, user, pass_id):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF, lock=True)
    row = _pass(db, institution, pass_id)
    if row.status != "approved":
        raise HTTPException(409, "Only approved passes can be marked returned.")
    row.status = "returned"
    row.returned_at = datetime.now(timezone.utc)
    institution_svc.audit(db, institution.id, user, "hostel.pass_returned", f"#{row.id}")
    institution_svc.save(db)
    return pass_dict(db, row)


# --------------------------------------------------------------- visitors


def visitor_dict(db, row):
    return {
        "id": row.id,
        "member_id": row.member_id,
        "student_name": _member_name(db, row.member_id),
        "visitor_name": row.visitor_name,
        "relation": row.relation,
        "phone": row.phone,
        "checked_in_at": institution_svc.utc(row.checked_in_at).isoformat(),
        "checked_out_at": institution_svc.utc(row.checked_out_at).isoformat() if row.checked_out_at else None,
    }


def list_visitors(db, institution_id, user, day=None, limit=300):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF)
    query = db.query(CampusHostelVisitor).filter_by(institution_id=institution.id)
    if day:
        from app.services.campus_staff import _range_bounds, _zone

        start, end = _range_bounds(day, day, _zone(institution))
        query = query.filter(CampusHostelVisitor.checked_in_at >= start, CampusHostelVisitor.checked_in_at < end)
    rows = query.order_by(CampusHostelVisitor.checked_in_at.desc()).limit(limit).all()
    return [visitor_dict(db, row) for row in rows]


def log_visitor(db, institution_id, user, data):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF, lock=True)
    member, _account = tuition_service._student(db, institution.id, data.member_id)
    if not db.query(CampusHostelAllocation).filter_by(member_id=member.id, status="active").first():
        raise HTTPException(409, "That student is not a hostel resident.")
    row = CampusHostelVisitor(
        institution_id=institution.id,
        member_id=member.id,
        visitor_name=data.visitor_name.strip(),
        relation=data.relation.strip(),
        phone=data.phone.strip(),
        checked_in_at=datetime.now(timezone.utc),
        recorded_by=user.id,
    )
    db.add(row)
    institution_svc.save(db)
    db.refresh(row)
    return visitor_dict(db, row)


def visitor_checkout(db, institution_id, user, visitor_id):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.STAFF, lock=True)
    row = db.query(CampusHostelVisitor).filter_by(id=visitor_id, institution_id=institution.id).with_for_update().first()
    if not row:
        raise HTTPException(404, "Visitor entry not found.")
    if row.checked_out_at:
        raise HTTPException(409, "This visitor has already checked out.")
    row.checked_out_at = datetime.now(timezone.utc)
    institution_svc.save(db)
    return visitor_dict(db, row)


# --------------------------------------------------------------------- me


def me(db, institution_id, user, student_user_id=None):
    institution, member = _reader(db, institution_id, user)
    learner = member if member is not None and member.role == "student" else _learner_member(db, institution, user, student_user_id)
    row = db.query(CampusHostelAllocation).filter_by(member_id=learner.id, status="active").first()
    passes = list_passes(db, institution_id, user, student_user_id=student_user_id, limit=20)
    if not row:
        return {"resident": False, "allocation": None, "passes": passes}
    return {"resident": True, "allocation": allocation_dict(db, row), "passes": passes}


def pending_pass_count(db, institution_id):
    return db.query(func.count(CampusHostelPass.id)).filter_by(institution_id=institution_id, status="pending").scalar() or 0


# ------------------------------------------------------------------ report


def occupancy_csv(db, institution_id, user):
    data = occupancy(db, institution_id, user)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Block", "Room", "Floor", "Type", "Capacity", "Occupied", "Student", "Checked in"])
    by_room = {}
    for row in data["allocations"]:
        by_room.setdefault(row["room_id"], []).append(row)
    for block in data["blocks"]:
        for room in block["rooms"]:
            residents = by_room.get(room["id"], [])
            if not residents:
                writer.writerow([block["name"], room["number"], room["floor"], room["room_type"], room["capacity"], room["occupied"], "", ""])
            for resident in residents:
                writer.writerow([block["name"], room["number"], room["floor"], room["room_type"], room["capacity"], room["occupied"], resident["student_name"], resident["checked_in_on"]])
    return buffer.getvalue()
