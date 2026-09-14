"""Parent portal: every approved child's campus signals in one read.

Pure aggregation over existing services under the same guardian rules
(approved parent_link_requests). Each block degrades to None on failure so
one broken signal never hides the rest.
"""

from datetime import datetime, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import or_

from app.models.campus_operations import CampusAttendance, ParentLinkRequest
from app.models.campus_pilot import CampusAnnouncement
from app.models.institution import Institution, InstitutionBatch, InstitutionBatchMember, InstitutionMember
from app.models.user import User
from app.services import campus_exams, campus_hostel, campus_transport, institution_service as institution_svc, tuition_service


log = logging.getLogger(__name__)
ATTENDANCE_WINDOW_DAYS = 30
LOW_ATTENDANCE_PERCENT = 75
MIN_ATTENDANCE_DAYS = 5


def _zone(institution):
    try:
        return ZoneInfo(institution.timezone)
    except Exception:
        return timezone.utc


def _safe(label, fn):
    try:
        return fn()
    except HTTPException:
        return None
    except Exception:
        log.warning("Parent portal block %s failed", label, exc_info=True)
        return None


def _children(db, parent):
    ids = [
        sid
        for sid, in db.query(ParentLinkRequest.student_user_id).filter_by(parent_user_id=parent.id, status="approved")
    ]
    if not ids:
        return []
    return db.query(User).filter(User.id.in_(ids), User.is_active.is_(True)).order_by(User.display_name).all()


def _attendance(db, member, batch_ids, today):
    if not batch_ids:
        return None
    since = today - timedelta(days=ATTENDANCE_WINDOW_DAYS)
    rows = (
        db.query(CampusAttendance)
        .filter(
            CampusAttendance.member_id == member.id,
            CampusAttendance.batch_id.in_(batch_ids),
            CampusAttendance.day > since,
            CampusAttendance.day <= today,
        )
        .all()
    )
    if not rows:
        return None
    present = sum(1 for row in rows if row.status in ("present", "late"))
    return {"present": present, "total": len(rows), "percent": round(present * 100 / len(rows), 1)}


def _fees(db, institution, parent, student):
    accounts = tuition_service.self_accounts(db, institution.id, parent, student.id)["assignments"]
    currency = accounts[0]["currency"] if accounts else "INR"
    outstanding = sum(a["balance"] for a in accounts)
    overdue = 0.0
    next_due = None
    for account in accounts:
        for row in account["installments"]:
            if row["balance"] <= 0:
                continue
            if row["status"] == "overdue":
                overdue += row["balance"]
            candidate = {
                "name": f"{account['plan']['name']} · {row['name']}",
                "due_on": row["due_on"].isoformat(),
                "balance": row["balance"],
                "assignment_id": account["id"],
                "installment_id": row["id"],
            }
            if next_due is None or candidate["due_on"] < next_due["due_on"]:
                next_due = candidate
    return {
        "currency": currency,
        "outstanding": round(outstanding, 2),
        "overdue": round(overdue, 2),
        "next_due": next_due,
        "accounts": len(accounts),
        # The account the parent can act on (pay or print) from the portal tile.
        "assignment_id": next_due["assignment_id"] if next_due else None,
    }


def _exams(db, institution, parent, student):
    listed = campus_exams.list_exams(db, institution.id, parent, None, student.id)
    out = []
    for exam in listed:
        if exam["status"] != "published":
            continue
        result = _safe("exam-result", lambda: campus_exams.my_results(db, institution.id, parent, exam["id"], student.id))
        if result is None:
            continue
        out.append(
            {
                "id": exam["id"],
                "name": exam["name"],
                "status": exam["status"],
                "published_at": exam["published_at"],
                "total": result["total"],
                "max_total": result["max_total"],
                "percent": result["percent"],
                "passed": result["passed"],
                "rank": result["rank"],
                "students": result["students"],
            }
        )
        if len(out) == 3:
            break
    return out


def _hostel(db, institution, parent, student):
    me = campus_hostel.me(db, institution.id, parent, student.id)
    allocation = me["allocation"]
    pending = next((p for p in me["passes"] if p["status"] == "pending"), None)
    approved = next((p for p in me["passes"] if p["status"] == "approved"), None)
    return {
        "resident": me["resident"],
        "block": allocation["block_name"] if allocation else None,
        "room": allocation["room_number"] if allocation else None,
        "pending_pass": pending,
        "approved_pass": approved,
    }


def _notices(db, institution, batch_ids):
    query = db.query(CampusAnnouncement).filter(CampusAnnouncement.institution_id == institution.id)
    if batch_ids:
        query = query.filter(or_(CampusAnnouncement.batch_id.is_(None), CampusAnnouncement.batch_id.in_(batch_ids)))
    else:
        query = query.filter(CampusAnnouncement.batch_id.is_(None))
    rows = query.order_by(CampusAnnouncement.created_at.desc(), CampusAnnouncement.id.desc()).limit(3).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "body": row.body[:240],
            "created_at": institution_svc.utc(row.created_at).isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def _alerts(block, now):
    alerts = []
    fees = block.get("fees")
    if fees and fees["overdue"] > 0:
        alerts.append({"kind": "fees_overdue", "message": f"{fees['currency']} {fees['overdue']:,.2f} is overdue."})
    attendance = block.get("attendance")
    if attendance and attendance["total"] >= MIN_ATTENDANCE_DAYS and attendance["percent"] < LOW_ATTENDANCE_PERCENT:
        alerts.append({"kind": "attendance_low", "message": f"Attendance is {attendance['percent']}% over the last {ATTENDANCE_WINDOW_DAYS} days."})
    transport = block.get("transport")
    if transport and transport.get("assigned") and transport.get("today") and not transport["today"]["boarded"]:
        alerts.append({"kind": "transport_not_boarded", "message": "Not marked as boarded today."})
    hostel = block.get("hostel")
    if hostel and hostel.get("pending_pass"):
        alerts.append({"kind": "hostel_pass_pending", "message": "An out-pass is waiting for the warden's decision."})
    for exam in block.get("exams") or []:
        if exam.get("published_at"):
            published = datetime.fromisoformat(exam["published_at"])
            if now - published <= timedelta(days=7):
                alerts.append({"kind": "results_published", "message": f"Results for {exam['name']} were published."})
                break
    return alerts


def _institution_block(db, parent, student, member, now):
    institution = db.get(Institution, member.institution_id)
    zone = _zone(institution)
    today = now.astimezone(zone).date()
    batch_rows = (
        db.query(InstitutionBatch)
        .join(InstitutionBatchMember, InstitutionBatchMember.batch_id == InstitutionBatch.id)
        .filter(InstitutionBatchMember.member_id == member.id)
        .all()
    )
    batch_ids = [b.id for b in batch_rows]
    block = {
        "institution": {"id": institution.id, "name": institution.name, "academic_year": institution.academic_year, "timezone": institution.timezone},
        "member_id": member.id,
        "batches": [b.name for b in batch_rows],
        "attendance": _safe("attendance", lambda: _attendance(db, member, batch_ids, today)),
        "fees": _safe("fees", lambda: _fees(db, institution, parent, student)),
        "exams": _safe("exams", lambda: _exams(db, institution, parent, student)) or [],
        "transport": _safe("transport", lambda: campus_transport.me(db, institution.id, parent, student.id)),
        "hostel": _safe("hostel", lambda: _hostel(db, institution, parent, student)),
        "notices": _safe("notices", lambda: _notices(db, institution, batch_ids)) or [],
    }
    block["alerts"] = _alerts(block, now)
    return block


def overview(db, parent):
    if parent.role != "parent":
        raise HTTPException(403, "Parent access only")
    now = datetime.now(timezone.utc)
    children = []
    for student in _children(db, parent):
        memberships = (
            db.query(InstitutionMember)
            .filter_by(user_id=student.id, role="student", status="active")
            .order_by(InstitutionMember.id)
            .all()
        )
        children.append(
            {
                "student": {"id": student.id, "name": student.display_name, "email": student.user_email},
                "institutions": [_institution_block(db, parent, student, member, now) for member in memberships],
            }
        )
    pending = db.query(ParentLinkRequest).filter_by(parent_user_id=parent.id, status="pending").count()
    return {"children": children, "pending_requests": pending, "generated_at": now.isoformat()}

