from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, inspect

from app.models.campus_operations import ParentLinkRequest
from app.models.institution import InstitutionMember
from app.models.tuition import TuitionFeeAssignment, TuitionFeePlan


ROOT = "/api/v1/institutions"


@pytest.fixture
def hostel_campus(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="hostel-owner@example.org")
    as_user(owner)
    institution_id = client.post(
        ROOT, json={"name": "Hostel College", "academic_year": "2026-27", "timezone": "Asia/Kolkata"}
    ).json()["id"]
    warden = make_user(role="instructor", email="hostel-warden@example.org")
    students = [make_user(email=f"hostel-student-{n}@example.org") for n in range(3)]
    parent = make_user(role="parent", email="hostel-parent@example.org")
    members = {}
    for account, role in [(warden, "teacher")] + [(s, "student") for s in students]:
        member = InstitutionMember(institution_id=institution_id, user_id=account.id, role=role, status="active", department="")
        db.add(member)
        db.flush()
        members[account.id] = member
    db.add(ParentLinkRequest(parent_user_id=parent.id, student_user_id=students[0].id, status="approved"))
    db.commit()
    return SimpleNamespace(
        owner=owner,
        warden=warden,
        students=students,
        parent=parent,
        iid=institution_id,
        warden_member=members[warden.id],
        student_members=[members[s.id] for s in students],
    )


def _block(client, campus, name="Block A", fee="24000.00", warden=True):
    return client.post(
        f"{ROOT}/{campus.iid}/hostel/blocks",
        json={
            "name": name,
            "warden_member_id": campus.warden_member.id if warden else None,
            "gender": "any",
            "fee_amount": fee,
            "currency": "INR",
            "rooms": [
                {"number": "101", "floor": "1", "room_type": "double", "capacity": 2},
                {"number": "102", "floor": "1", "room_type": "single", "capacity": 1},
            ],
        },
    )


def _leave(hours_from_now=24, length=6):
    start = datetime.now(timezone.utc) + timedelta(hours=hours_from_now)
    return start.isoformat(), (start + timedelta(hours=length)).isoformat()


def test_block_rooms_fee_plan_and_roles(hostel_campus, client, as_user, db):
    campus = hostel_campus
    created = _block(client, campus)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["capacity"] == 3 and body["occupied"] == 0 and body["warden_name"]
    assert db.get(TuitionFeePlan, body["fee_plan_id"]).name == "Hostel · Block A"
    assert _block(client, campus).status_code == 409
    bad_warden = client.post(f"{ROOT}/{campus.iid}/hostel/blocks", json={"name": "B", "warden_member_id": campus.student_members[0].id})
    assert bad_warden.status_code == 422
    as_user(campus.warden)
    assert _block(client, campus, name="Warden block").status_code == 403
    assert client.get(f"{ROOT}/{campus.iid}/hostel/blocks").status_code == 200
    as_user(campus.students[0])
    assert client.get(f"{ROOT}/{campus.iid}/hostel/blocks").status_code == 403


def test_allocate_capacity_fee_rooms_and_checkout(hostel_campus, client, as_user, db):
    campus = hostel_campus
    block = _block(client, campus).json()
    rooms = {r["number"]: r["id"] for r in block["rooms"]}
    base = f"{ROOT}/{campus.iid}/hostel"
    first = client.post(f"{base}/rooms/{rooms['101']}/allocations", json={"member_id": campus.student_members[0].id})
    assert first.status_code == 201, first.text
    assert first.json()["room_number"] == "101" and first.json()["block_name"] == "Block A"
    fee = db.get(TuitionFeeAssignment, first.json()["fee_assignment_id"])
    assert float(fee.gross_amount) == 24000.0
    assert client.post(f"{base}/rooms/{rooms['102']}/allocations", json={"member_id": campus.student_members[0].id}).status_code == 409
    assert client.post(f"{base}/rooms/{rooms['101']}/allocations", json={"member_id": campus.student_members[1].id}).status_code == 201
    full = client.post(f"{base}/rooms/{rooms['101']}/allocations", json={"member_id": campus.student_members[2].id})
    assert full.status_code == 409 and "full" in full.json()["detail"]
    occ = client.get(f"{base}/occupancy").json()
    assert occ["occupied"] == 2 and occ["capacity"] == 3 and len(occ["allocations"]) == 2
    # Rooms with residents cannot be removed or shrunk below occupancy.
    assert client.put(f"{base}/blocks/{block['id']}/rooms", json={"rooms": [{"number": "102"}]}).status_code == 409
    assert client.put(f"{base}/blocks/{block['id']}/rooms", json={"rooms": [{"number": "101", "capacity": 1}, {"number": "102"}]}).status_code == 422
    grown = client.put(f"{base}/blocks/{block['id']}/rooms", json={"rooms": [{"number": "101", "capacity": 3}, {"number": "102", "room_type": "single", "capacity": 1}, {"number": "201", "floor": "2", "room_type": "dormitory", "capacity": 6}]})
    assert grown.status_code == 200 and grown.json()["capacity"] == 10
    out = client.post(f"{base}/allocations/{first.json()['id']}/checkout")
    assert out.json()["status"] == "ended" and out.json()["checked_out_on"]
    assert client.post(f"{base}/allocations/{first.json()['id']}/checkout").status_code == 409
    csv_response = client.get(f"{base}/occupancy.csv")
    assert csv_response.status_code == 200 and csv_response.text.startswith("Block,Room,Floor,Type,Capacity,Occupied,Student,Checked in")
    as_user(campus.warden)
    assert client.post(f"{base}/rooms/{rooms['102']}/allocations", json={"member_id": campus.student_members[2].id}).status_code == 403


def test_passes_lifecycle_visibility_and_today(hostel_campus, client, as_user):
    campus = hostel_campus
    block = _block(client, campus).json()
    base = f"{ROOT}/{campus.iid}/hostel"
    room = block["rooms"][0]["id"]
    client.post(f"{base}/rooms/{room}/allocations", json={"member_id": campus.student_members[0].id})
    leaves, returns = _leave()
    # A non-resident cannot request; a resident can, without overlaps.
    as_user(campus.students[1])
    assert client.post(f"{base}/passes", json={"reason": "Family visit", "leaves_at": leaves, "returns_at": returns}).status_code == 409
    as_user(campus.students[0])
    created = client.post(f"{base}/passes", json={"reason": "Family visit", "leaves_at": leaves, "returns_at": returns})
    assert created.status_code == 201, created.text
    assert client.post(f"{base}/passes", json={"reason": "Again", "leaves_at": leaves, "returns_at": returns}).status_code == 409
    assert client.post(f"{base}/passes", json={"reason": "Bad", "leaves_at": returns, "returns_at": leaves}).status_code == 422
    pass_id = created.json()["id"]
    assert [p["id"] for p in client.get(f"{base}/passes").json()] == [pass_id]
    assert client.post(f"{base}/passes/{pass_id}/approve", json={}).status_code == 403
    # Staff see the pending pass on Today and decide it.
    as_user(campus.warden)
    today = client.get(f"{ROOT}/{campus.iid}/today").json()
    assert any(a["id"] == "system-hostel-passes" and "1 hostel pass " in a["title"] for a in today["actions"])
    assert client.post(f"{base}/passes/{pass_id}/reject", json={}).status_code == 422
    approved = client.post(f"{base}/passes/{pass_id}/approve", json={"note": "Back by 9"})
    assert approved.json()["status"] == "approved" and approved.json()["decision_note"] == "Back by 9"
    assert client.post(f"{base}/passes/{pass_id}/approve", json={}).status_code == 409
    today = client.get(f"{ROOT}/{campus.iid}/today").json()
    assert all(a["id"] != "system-hostel-passes" for a in today["actions"])
    returned = client.post(f"{base}/passes/{pass_id}/return")
    assert returned.json()["status"] == "returned" and returned.json()["returned_at"]
    # Guardian sees the child's room and passes only with approval.
    as_user(campus.parent)
    assert client.get(f"{base}/me", params={"student_user_id": campus.students[1].id}).status_code == 404
    mine = client.get(f"{base}/me", params={"student_user_id": campus.students[0].id}).json()
    assert mine["resident"] is True and mine["allocation"]["room_number"] == "101" and mine["passes"][0]["status"] == "returned"
    as_user(campus.students[2])
    assert client.get(f"{base}/me").json()["resident"] is False


def test_visitor_register(hostel_campus, client, as_user):
    campus = hostel_campus
    block = _block(client, campus).json()
    base = f"{ROOT}/{campus.iid}/hostel"
    client.post(f"{base}/rooms/{block['rooms'][0]['id']}/allocations", json={"member_id": campus.student_members[0].id})
    as_user(campus.warden)
    assert client.post(f"{base}/visitors", json={"member_id": campus.student_members[2].id, "visitor_name": "Uncle"}).status_code == 409
    logged = client.post(f"{base}/visitors", json={"member_id": campus.student_members[0].id, "visitor_name": "Meera", "relation": "Mother", "phone": "+919000000002"})
    assert logged.status_code == 201 and logged.json()["checked_out_at"] is None
    listed = client.get(f"{base}/visitors").json()
    assert len(listed) == 1 and listed[0]["student_name"]
    out = client.post(f"{base}/visitors/{logged.json()['id']}/checkout")
    assert out.json()["checked_out_at"]
    assert client.post(f"{base}/visitors/{logged.json()['id']}/checkout").status_code == 409
    as_user(campus.students[0])
    assert client.get(f"{base}/visitors").status_code == 403


def test_campus_hostel_migration_round_trip():
    versions = Path(__file__).parents[1] / "alembic/versions"
    spec = importlib.util.spec_from_file_location("m0042", versions / "0042_campus_hostel.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for name in ("institutions", "users", "institution_members", "tuition_fee_plans", "tuition_fee_assignments"):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        wanted = {"campus_hostel_blocks", "campus_hostel_rooms", "campus_hostel_allocations", "campus_hostel_passes", "campus_hostel_visitors"}
        assert wanted <= set(inspect(connection).get_table_names())
        module.downgrade()
        assert not set(inspect(connection).get_table_names()) & wanted
