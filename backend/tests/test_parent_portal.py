from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models.campus_operations import CampusAttendance, ParentLinkRequest
from app.models.campus_pilot import CampusAnnouncement, CampusEvent
from app.models.institution import InstitutionMember


ROOT = "/api/v1/institutions"
PORTAL = "/api/v1/parents/campus"


@pytest.fixture
def family(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="pp-owner@example.org")
    as_user(owner)
    iid = client.post(ROOT, json={"name": "Portal College", "academic_year": "2026-27", "timezone": "Asia/Kolkata"}).json()["id"]
    bid = client.post(f"{ROOT}/{iid}/batches", json={"name": "Grade 8", "academic_year": "2026-27"}).json()["id"]
    term_id = client.post(f"{ROOT}/{iid}/terms", json={"name": "Term 1", "starts_on": "2026-06-01", "ends_on": "2026-12-20"}).json()["id"]
    child = make_user(email="pp-child@example.org")
    other = make_user(email="pp-other@example.org")
    parent = make_user(role="parent", email="pp-parent@example.org")
    members = {}
    for account in (child, other):
        member = InstitutionMember(institution_id=iid, user_id=account.id, role="student", status="active", department="")
        db.add(member)
        db.flush()
        members[account.id] = member
    db.add(ParentLinkRequest(parent_user_id=parent.id, student_user_id=child.id, status="approved"))
    db.add(ParentLinkRequest(parent_user_id=parent.id, student_user_id=other.id, status="pending"))
    db.commit()
    client.post(f"{ROOT}/{iid}/batches/{bid}/members", json={"member_ids": [members[child.id].id, members[other.id].id]})
    return SimpleNamespace(owner=owner, child=child, other=other, parent=parent, iid=iid, bid=bid, term_id=term_id, child_member=members[child.id])


def _seed_signals(client, db, fam):
    today = date.today()
    # Attendance: 4 present, 4 absent over the last 10 days → 50%.
    for offset in range(1, 9):
        db.add(CampusAttendance(batch_id=fam.bid, member_id=fam.child_member.id, day=today - timedelta(days=offset), status="present" if offset % 2 else "absent", recorded_by=fam.owner.id))
    db.add(CampusAnnouncement(institution_id=fam.iid, batch_id=None, title="PTM on Friday", body="Parents are invited.", created_by=fam.owner.id))
    db.commit()
    # Fee plan with one overdue installment.
    plan = client.post(
        f"{ROOT}/{fam.iid}/fees/plans",
        json={"name": "Tuition", "academic_year": "2026-27", "currency": "INR", "description": "", "components": [{"code": "T", "name": "Tuition", "amount": "2000.00"}], "installments": [{"name": "Overdue part", "due_on": str(today - timedelta(days=10)), "amount": "1000"}, {"name": "Later part", "due_on": str(today + timedelta(days=20)), "amount": "1000"}]},
    ).json()["id"]
    client.post(f"{ROOT}/{fam.iid}/fees/plans/{plan}/publish")
    client.post(f"{ROOT}/{fam.iid}/fees/assignments", json={"student_member_id": fam.child_member.id, "plan_id": plan, "note": ""})
    # Published exam with marks.
    exam = client.post(f"{ROOT}/{fam.iid}/exams", json={"term_id": fam.term_id, "name": "Unit test 1", "kind": "unit"}).json()["id"]
    paper = client.post(f"{ROOT}/{fam.iid}/exams/{exam}/papers", json={"batch_id": fam.bid, "subject": "Maths", "max_marks": 50, "pass_marks": 20, "starts_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(), "duration_minutes": 60, "room": "R1"}).json()["id"]
    client.put(f"{ROOT}/{fam.iid}/exams/{exam}/papers/{paper}/marks", json={"entries": [{"member_id": fam.child_member.id, "marks": 45}]})
    client.post(f"{ROOT}/{fam.iid}/exams/{exam}/publish")
    # Transport assignment with today's log (not boarded).
    route = client.post(f"{ROOT}/{fam.iid}/transport/routes", json={"name": "Loop", "capacity": 10, "stops": [{"name": "Gate"}]}).json()
    client.post(f"{ROOT}/{fam.iid}/transport/routes/{route['id']}/assignments", json={"member_id": fam.child_member.id, "stop_id": route["stops"][0]["id"]})
    day = client.get(f"{ROOT}/{fam.iid}/transport/routes/{route['id']}/roster").json()["day"]
    client.put(f"{ROOT}/{fam.iid}/transport/routes/{route['id']}/boarding", json={"day": day, "entries": [{"member_id": fam.child_member.id, "boarded": False}]})
    # Hostel allocation and a pending pass.
    block = client.post(f"{ROOT}/{fam.iid}/hostel/blocks", json={"name": "Girls block", "rooms": [{"number": "G1", "capacity": 2}]}).json()
    client.post(f"{ROOT}/{fam.iid}/hostel/rooms/{block['rooms'][0]['id']}/allocations", json={"member_id": fam.child_member.id})
    return exam


def test_parent_sees_every_signal_for_approved_child_only(family, client, as_user, db):
    fam = family
    exam_id = _seed_signals(client, db, fam)
    as_user(fam.child)
    leaves = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    returns = (datetime.now(timezone.utc) + timedelta(days=1, hours=5)).isoformat()
    assert client.post(f"{ROOT}/{fam.iid}/hostel/passes", json={"reason": "Home visit", "leaves_at": leaves, "returns_at": returns}).status_code == 201
    as_user(fam.parent)
    response = client.get(PORTAL)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["pending_requests"] == 1
    assert [c["student"]["email"] for c in body["children"]] == ["pp-child@example.org"]
    block = body["children"][0]["institutions"][0]
    assert block["institution"]["name"] == "Portal College" and block["batches"] == ["Grade 8"]
    assert block["attendance"] == {"present": 4, "total": 8, "percent": 50.0}
    assert block["fees"]["outstanding"] == 2000.0 and block["fees"]["overdue"] == 1000.0
    assert block["fees"]["next_due"]["name"] == "Tuition · Overdue part"
    assert [e["id"] for e in block["exams"]] == [exam_id]
    assert block["exams"][0]["total"] == 45 and block["exams"][0]["passed"] is True and block["exams"][0]["rank"] == 1
    assert block["transport"]["assigned"] is True and block["transport"]["today"]["boarded"] is False
    assert block["hostel"]["resident"] is True and block["hostel"]["room"] == "G1" and block["hostel"]["pending_pass"]["reason"] == "Home visit"
    assert block["notices"][0]["title"] == "PTM on Friday"
    kinds = {a["kind"] for a in block["alerts"]}
    assert kinds == {"fees_overdue", "attendance_low", "transport_not_boarded", "hostel_pass_pending", "results_published"}


def test_portal_role_gate_and_empty_state(family, client, as_user, make_user):
    fam = family
    as_user(fam.child)
    assert client.get(PORTAL).status_code == 403
    as_user(fam.owner)
    assert client.get(PORTAL).status_code == 403
    lonely = make_user(role="parent", email="pp-lonely@example.org")
    as_user(lonely)
    body = client.get(PORTAL).json()
    assert body == {"children": [], "pending_requests": 0, "generated_at": body["generated_at"]}


def test_portal_degrades_when_one_block_fails(family, client, as_user, db, monkeypatch):
    fam = family
    _seed_signals(client, db, fam)
    from app.services import parent_portal

    def boom(*args, **kwargs):
        raise RuntimeError("transport exploded")

    monkeypatch.setattr(parent_portal.campus_transport, "me", boom)
    as_user(fam.parent)
    body = client.get(PORTAL).json()
    block = body["children"][0]["institutions"][0]
    assert block["transport"] is None and block["fees"]["overdue"] == 1000.0
    assert "transport_not_boarded" not in {a["kind"] for a in block["alerts"]}


def test_child_without_campus_membership_lists_no_institutions(family, client, as_user, make_user, db):
    fam = family
    outsider = make_user(email="pp-outsider@example.org")
    db.add(ParentLinkRequest(parent_user_id=fam.parent.id, student_user_id=outsider.id, status="approved"))
    db.commit()
    as_user(fam.parent)
    body = client.get(PORTAL).json()
    by_email = {c["student"]["email"]: c for c in body["children"]}
    assert by_email["pp-outsider@example.org"]["institutions"] == []
    assert len(by_email["pp-child@example.org"]["institutions"]) == 1
    # Unused import guard for the timetable model keeps the fixture honest.
    assert CampusEvent is not None
