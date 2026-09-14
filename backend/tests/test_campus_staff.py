from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, inspect

from app.models.campus_pilot import CampusEvent
from app.models.campus_staff import CampusSubstitution
from app.models.institution import InstitutionAudit, InstitutionMember


ROOT = "/api/v1/institutions"
TODAY = date.today()
LEAVE_START = TODAY + timedelta(days=3)
LEAVE_END = TODAY + timedelta(days=4)


@pytest.fixture
def staff_campus(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="st-owner@example.org")
    as_user(owner)
    institution_id = client.post(
        ROOT, json={"name": "Staff College", "academic_year": "2026-27", "timezone": "Asia/Kolkata"}
    ).json()["id"]
    batch_id = client.post(
        f"{ROOT}/{institution_id}/batches", json={"name": "Grade 9", "academic_year": "2026-27"}
    ).json()["id"]
    people = {}
    for key, email in (("teacher", "st-teacher@example.org"), ("sub1", "st-sub1@example.org"), ("sub2", "st-sub2@example.org")):
        account = make_user(role="instructor", email=email)
        member = InstitutionMember(institution_id=institution_id, user_id=account.id, role="teacher", status="active", department="Science")
        db.add(member)
        db.flush()
        people[key] = SimpleNamespace(user=account, member=member)
    student = make_user(email="st-student@example.org")
    student_member = InstitutionMember(institution_id=institution_id, user_id=student.id, role="student", status="active", department="")
    db.add(student_member)
    db.flush()
    db.commit()
    client.post(f"{ROOT}/{institution_id}/batches/{batch_id}/members", json={"member_ids": [student_member.id]})
    owner_member = db.query(InstitutionMember).filter_by(institution_id=institution_id, user_id=owner.id).one()
    return SimpleNamespace(
        owner=owner,
        owner_member=owner_member,
        student=student,
        iid=institution_id,
        bid=batch_id,
        **people,
    )


def _event(db, campus, teacher_member_id, day, hour=9, title="Physics", room="Lab 1"):
    starts = datetime(day.year, day.month, day.day, hour, 0, tzinfo=timezone.utc)
    row = CampusEvent(
        institution_id=campus.iid,
        batch_id=campus.bid,
        teacher_id=teacher_member_id,
        title=title,
        kind="class",
        room=room,
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
        series=f"test-{title}-{day}-{hour}",
        created_by=campus.owner.id,
    )
    db.add(row)
    db.commit()
    return row


def _types(client, campus, quota=3):
    saved = client.put(
        f"{ROOT}/{campus.iid}/staff/leave/types",
        json={"academic_year": "2026-27", "types": [{"code": "cl", "name": "Casual leave", "annual_quota": quota}, {"code": "SL", "name": "Sick leave", "annual_quota": 5}]},
    )
    assert saved.status_code == 200, saved.text
    return {row["code"]: row["id"] for row in saved.json()["types"]}


def _apply(client, campus, type_id, starts=LEAVE_START, ends=LEAVE_END, note="Family event"):
    return client.post(
        f"{ROOT}/{campus.iid}/staff/leave",
        json={"type_id": type_id, "starts_on": str(starts), "ends_on": str(ends), "note": note},
    )


def test_leave_types_manager_only_and_code_normalised(staff_campus, client, as_user):
    campus = staff_campus
    types = _types(client, campus)
    assert set(types) == {"CL", "SL"}
    as_user(campus.teacher.user)
    assert client.put(f"{ROOT}/{campus.iid}/staff/leave/types", json={"academic_year": "2026-27", "types": []}).status_code == 403
    listed = client.get(f"{ROOT}/{campus.iid}/staff/leave/types").json()
    assert [t["code"] for t in listed["types"]] == ["CL", "SL"]
    as_user(campus.student)
    assert client.get(f"{ROOT}/{campus.iid}/staff/leave/types").status_code == 403


def test_apply_overlap_visibility_and_balances(staff_campus, client, as_user):
    campus = staff_campus
    types = _types(client, campus)
    as_user(campus.teacher.user)
    created = _apply(client, campus, types["CL"])
    assert created.status_code == 201, created.text
    assert created.json()["days"] == 2 and created.json()["status"] == "pending"
    assert _apply(client, campus, types["SL"], starts=LEAVE_END, ends=LEAVE_END + timedelta(days=1)).status_code == 409
    as_user(campus.sub1.user)
    assert client.get(f"{ROOT}/{campus.iid}/staff/leave").json() == []
    assert client.get(f"{ROOT}/{campus.iid}/staff/leave/balances", params={"member_id": campus.teacher.member.id}).status_code == 403
    as_user(campus.owner)
    assert len(client.get(f"{ROOT}/{campus.iid}/staff/leave").json()) == 1
    bal = client.get(f"{ROOT}/{campus.iid}/staff/leave/balances", params={"member_id": campus.teacher.member.id}).json()
    assert {b["code"]: (b["used"], b["remaining"]) for b in bal["balances"]} == {"CL": (0, 3), "SL": (0, 5)}
    as_user(campus.student)
    assert _apply(client, campus, types["CL"]).status_code == 403


def test_approve_creates_substitutions_only_in_range(staff_campus, client, as_user, db):
    campus = staff_campus
    types = _types(client, campus)
    inside = _event(db, campus, campus.teacher.member.id, LEAVE_START)
    inside_two = _event(db, campus, campus.teacher.member.id, LEAVE_END, hour=11, title="Chemistry")
    _event(db, campus, campus.teacher.member.id, LEAVE_END + timedelta(days=1), title="Outside")
    _event(db, campus, campus.sub1.member.id, LEAVE_START, title="Someone else")
    as_user(campus.teacher.user)
    leave_id = _apply(client, campus, types["CL"]).json()["id"]
    as_user(campus.owner)
    approved = client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["substitutions"] == {"total": 2, "open": 2, "assigned": 0}
    subs = {row.event_id for row in db.query(CampusSubstitution).filter_by(leave_id=leave_id)}
    assert subs == {inside.id, inside_two.id}
    bal = client.get(f"{ROOT}/{campus.iid}/staff/leave/balances", params={"member_id": campus.teacher.member.id}).json()
    assert next(b for b in bal["balances"] if b["code"] == "CL")["used"] == 2
    assert client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={}).status_code == 409
    as_user(campus.teacher.user)
    assert client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={}).status_code == 403


def test_quota_refusal_and_override(staff_campus, client, as_user):
    campus = staff_campus
    types = _types(client, campus, quota=1)
    as_user(campus.teacher.user)
    leave_id = _apply(client, campus, types["CL"]).json()["id"]
    as_user(campus.owner)
    refused = client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={})
    assert refused.status_code == 422 and "quota" in refused.json()["detail"]
    assert client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={"override": True}).status_code == 422
    ok = client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={"override": True, "note": "Bereavement"})
    assert ok.status_code == 200 and ok.json()["override"] is True and ok.json()["decision_note"] == "Bereavement"


def test_reject_and_cancel_release_substitutions(staff_campus, client, as_user, db):
    campus = staff_campus
    types = _types(client, campus)
    _event(db, campus, campus.teacher.member.id, LEAVE_START)
    as_user(campus.teacher.user)
    first = _apply(client, campus, types["CL"]).json()["id"]
    as_user(campus.owner)
    assert client.post(f"{ROOT}/{campus.iid}/staff/leave/{first}/reject", json={"note": ""}).status_code == 422
    rejected = client.post(f"{ROOT}/{campus.iid}/staff/leave/{first}/reject", json={"note": "Exam week"})
    assert rejected.json()["status"] == "rejected" and rejected.json()["decision_note"] == "Exam week"
    as_user(campus.teacher.user)
    second = _apply(client, campus, types["CL"]).json()["id"]
    as_user(campus.owner)
    client.post(f"{ROOT}/{campus.iid}/staff/leave/{second}/approve", json={})
    assert db.query(CampusSubstitution).filter_by(leave_id=second, status="open").count() == 1
    as_user(campus.teacher.user)
    cancelled = client.post(f"{ROOT}/{campus.iid}/staff/leave/{second}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert db.query(CampusSubstitution).filter_by(leave_id=second, status="released").count() == 1
    as_user(campus.sub1.user)
    assert client.post(f"{ROOT}/{campus.iid}/staff/leave/{second}/cancel").status_code == 404
    actions = {row.action for row in db.query(InstitutionAudit).filter_by(institution_id=campus.iid)}
    assert {"staff.leave_requested", "staff.leave_rejected", "staff.leave_approved", "staff.leave_cancelled"} <= actions


def test_candidates_assign_unassign_and_visibility(staff_campus, client, as_user, db):
    campus = staff_campus
    types = _types(client, campus)
    slot = _event(db, campus, campus.teacher.member.id, LEAVE_START, hour=9)
    _event(db, campus, campus.sub2.member.id, LEAVE_START, hour=9, title="Maths", room="Lab 2")  # sub2 busy
    as_user(campus.teacher.user)
    leave_id = _apply(client, campus, types["CL"]).json()["id"]
    as_user(campus.owner)
    client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={})
    subs = client.get(f"{ROOT}/{campus.iid}/staff/substitutions", params={"status": "open"}).json()
    assert len(subs) == 1 and subs[0]["event_id"] == slot.id and subs[0]["absent_member_id"] == campus.teacher.member.id
    sub_id = subs[0]["id"]
    names = {c["member_id"] for c in client.get(f"{ROOT}/{campus.iid}/staff/substitutions/{sub_id}/candidates").json()}
    assert campus.sub1.member.id in names
    assert campus.owner_member.id in names
    assert campus.sub2.member.id not in names and campus.teacher.member.id not in names
    assert client.post(f"{ROOT}/{campus.iid}/staff/substitutions/{sub_id}/assign", json={"substitute_member_id": campus.sub2.member.id}).status_code == 422
    assert client.post(f"{ROOT}/{campus.iid}/staff/substitutions/{sub_id}/assign", json={"substitute_member_id": campus.teacher.member.id}).status_code == 422
    assigned = client.post(f"{ROOT}/{campus.iid}/staff/substitutions/{sub_id}/assign", json={"substitute_member_id": campus.sub1.member.id, "note": "Thanks"})
    assert assigned.status_code == 200 and assigned.json()["status"] == "assigned"
    assert assigned.json()["substitute_member_id"] == campus.sub1.member.id
    # sub1 now busy for an overlapping second slot of the same leave.
    slot_two = _event(db, campus, campus.teacher.member.id, LEAVE_START, hour=9, title="Biology", room="Lab 3")
    db.add(CampusSubstitution(institution_id=campus.iid, leave_id=leave_id, event_id=slot_two.id, absent_member_id=campus.teacher.member.id, status="open"))
    db.commit()
    other = [s for s in client.get(f"{ROOT}/{campus.iid}/staff/substitutions", params={"status": "open"}).json() if s["event_id"] == slot_two.id][0]
    names_two = {c["member_id"] for c in client.get(f"{ROOT}/{campus.iid}/staff/substitutions/{other['id']}/candidates").json()}
    assert campus.sub1.member.id not in names_two
    # Timetable shows the substitute; the substitute's own view lists the slot.
    events = client.get(f"{ROOT}/{campus.iid}/pilot/events").json()
    shown = next(e for e in events if e["id"] == slot.id)
    assert shown["substitute_member_id"] == campus.sub1.member.id and shown["substitute_name"]
    as_user(campus.sub1.user)
    mine = client.get(f"{ROOT}/{campus.iid}/staff/substitutions").json()
    assert [s["id"] for s in mine] == [sub_id]
    assert client.get(f"{ROOT}/{campus.iid}/staff/substitutions/{sub_id}/candidates").status_code == 403
    as_user(campus.owner)
    released = client.post(f"{ROOT}/{campus.iid}/staff/substitutions/{sub_id}/unassign")
    assert released.json()["status"] == "open" and released.json()["substitute_member_id"] is None


def test_today_surfaces_uncovered_classes_and_covering_teacher(staff_campus, client, as_user, db):
    campus = staff_campus
    types = _types(client, campus)
    slot = _event(db, campus, campus.teacher.member.id, TODAY, hour=12)
    as_user(campus.teacher.user)
    leave_id = _apply(client, campus, types["CL"], starts=TODAY, ends=TODAY).json()["id"]
    as_user(campus.owner)
    client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={})
    today = client.get(f"{ROOT}/{campus.iid}/today").json()
    system = next((a for a in today["actions"] if a["id"] == "system-substitutions"), None)
    assert system is not None and system["href"].endswith("/staff")
    sub_id = client.get(f"{ROOT}/{campus.iid}/staff/substitutions", params={"status": "open"}).json()[0]["id"]
    client.post(f"{ROOT}/{campus.iid}/staff/substitutions/{sub_id}/assign", json={"substitute_member_id": campus.sub1.member.id})
    today = client.get(f"{ROOT}/{campus.iid}/today").json()
    assert all(a["id"] != "system-substitutions" for a in today["actions"])
    as_user(campus.sub1.user)
    schedule_ids = {item["id"] for item in client.get(f"{ROOT}/{campus.iid}/today").json()["schedule"]}
    assert slot.id in schedule_ids


def test_leave_report_json_and_csv(staff_campus, client, as_user, db):
    campus = staff_campus
    types = _types(client, campus)
    _event(db, campus, campus.teacher.member.id, LEAVE_START)
    as_user(campus.teacher.user)
    leave_id = _apply(client, campus, types["CL"]).json()["id"]
    as_user(campus.owner)
    client.post(f"{ROOT}/{campus.iid}/staff/leave/{leave_id}/approve", json={})
    sub_id = client.get(f"{ROOT}/{campus.iid}/staff/substitutions").json()[0]["id"]
    client.post(f"{ROOT}/{campus.iid}/staff/substitutions/{sub_id}/assign", json={"substitute_member_id": campus.sub1.member.id})
    report = client.get(f"{ROOT}/{campus.iid}/staff/leave/report").json()
    by_member = {row["member_id"]: row for row in report["rows"]}
    assert by_member[campus.teacher.member.id]["balances"]["CL"] == {"quota": 3, "used": 2, "remaining": 1}
    assert by_member[campus.sub1.member.id]["substitution_hours"] == 1.0
    csv_response = client.get(f"{ROOT}/{campus.iid}/staff/leave/report", params={"format": "csv"})
    assert csv_response.status_code == 200 and csv_response.headers["content-type"].startswith("text/csv")
    lines = csv_response.text.strip().splitlines()
    assert lines[0].startswith("Name,Role,Department,CL quota,CL used,CL remaining,SL quota")
    assert len(lines) == 1 + len(report["rows"])
    as_user(campus.teacher.user)
    assert client.get(f"{ROOT}/{campus.iid}/staff/leave/report").status_code == 403


def test_leave_report_csv_with_non_ascii_academic_year(staff_campus, client, as_user):
    campus = staff_campus
    year = "2026–2027"
    saved = client.put(
        f"{ROOT}/{campus.iid}/staff/leave/types",
        json={"academic_year": year, "types": [{"code": "CL", "name": "Casual leave", "annual_quota": 3}]},
    )
    assert saved.status_code == 200, saved.text
    response = client.get(f"{ROOT}/{campus.iid}/staff/leave/report", params={"academic_year": year, "format": "csv"})
    assert response.status_code == 200, response.text
    assert 'filename="leave-report-2026-2027.csv"' in response.headers["content-disposition"]
    assert "CL quota" in response.text


def test_campus_staff_migration_round_trip():
    versions = Path(__file__).parents[1] / "alembic/versions"
    spec = importlib.util.spec_from_file_location("m0040", versions / "0040_campus_staff_leave.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for name in ("institutions", "users", "institution_members", "campus_events"):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert {"campus_leave_types", "campus_leave_requests", "campus_substitutions"} <= set(inspect(connection).get_table_names())
        module.downgrade()
        assert not set(inspect(connection).get_table_names()) & {"campus_leave_types", "campus_leave_requests", "campus_substitutions"}
