from datetime import date, timedelta
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
def bus_campus(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="bus-owner@example.org")
    as_user(owner)
    institution_id = client.post(
        ROOT, json={"name": "Bus College", "academic_year": "2026-27", "timezone": "Asia/Kolkata"}
    ).json()["id"]
    teacher = make_user(role="instructor", email="bus-teacher@example.org")
    students = [make_user(email=f"bus-student-{n}@example.org") for n in range(3)]
    parent = make_user(role="parent", email="bus-parent@example.org")
    members = {}
    for account, role in [(teacher, "teacher")] + [(s, "student") for s in students]:
        member = InstitutionMember(institution_id=institution_id, user_id=account.id, role=role, status="active", department="")
        db.add(member)
        db.flush()
        members[account.id] = member
    db.add(ParentLinkRequest(parent_user_id=parent.id, student_user_id=students[0].id, status="approved"))
    db.commit()
    return SimpleNamespace(
        owner=owner,
        teacher=teacher,
        students=students,
        parent=parent,
        iid=institution_id,
        teacher_member=members[teacher.id],
        student_members=[members[s.id] for s in students],
    )


def _route(client, campus, name="North loop", capacity=2, fee="1500.00"):
    return client.post(
        f"{ROOT}/{campus.iid}/transport/routes",
        json={
            "name": name,
            "vehicle_number": "TN 01 AB 1234",
            "driver_name": "Kumar",
            "driver_phone": "+919000000001",
            "capacity": capacity,
            "fee_amount": fee,
            "currency": "inr",
            "stops": [
                {"name": "Anna Nagar", "pickup_time": "07:10", "drop_time": "16:20", "landmark": "Tower park"},
                {"name": "Kilpauk", "pickup_time": "07:25", "drop_time": "16:05"},
            ],
        },
    )


def test_route_create_publishes_fee_plan_and_gates_roles(bus_campus, client, as_user, db):
    campus = bus_campus
    created = _route(client, campus)
    assert created.status_code == 201, created.text
    body = created.json()
    assert [s["sequence"] for s in body["stops"]] == [1, 2]
    assert body["occupied"] == 0 and body["currency"] == "INR" and body["fee_amount"] == 1500.0
    plan = db.get(TuitionFeePlan, body["fee_plan_id"])
    assert plan.status == "published" and plan.name == "Transport · North loop"
    assert _route(client, campus).status_code == 409
    assert client.post(f"{ROOT}/{campus.iid}/transport/routes", json={"name": "Bad", "stops": [{"name": "X", "pickup_time": "7:5"}]}).status_code == 422
    as_user(campus.teacher)
    assert _route(client, campus, name="Teacher route").status_code == 403
    assert client.get(f"{ROOT}/{campus.iid}/transport/routes").status_code == 200
    as_user(campus.students[0])
    assert client.get(f"{ROOT}/{campus.iid}/transport/routes").status_code == 403


def test_assign_capacity_duplicates_fee_and_end(bus_campus, client, as_user, db):
    campus = bus_campus
    route = _route(client, campus).json()
    stop = route["stops"][0]["id"]
    base = f"{ROOT}/{campus.iid}/transport"
    first = client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": campus.student_members[0].id, "stop_id": stop})
    assert first.status_code == 201, first.text
    assert first.json()["stop_name"] == "Anna Nagar" and first.json()["fee_assignment_id"]
    fee = db.get(TuitionFeeAssignment, first.json()["fee_assignment_id"])
    assert fee.student_member_id == campus.student_members[0].id and float(fee.gross_amount) == 1500.0
    # Same student twice → 409; teacher member → 404 (not a student); wrong stop → 404.
    assert client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": campus.student_members[0].id, "stop_id": stop}).status_code == 409
    assert client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": campus.teacher_member.id, "stop_id": stop}).status_code == 404
    assert client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": campus.student_members[1].id, "stop_id": 9999}).status_code == 404
    second = client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": campus.student_members[1].id, "stop_id": route["stops"][1]["id"]})
    assert second.status_code == 201
    full = client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": campus.student_members[2].id, "stop_id": stop})
    assert full.status_code == 409 and "full" in full.json()["detail"]
    listed = client.get(f"{base}/routes").json()[0]
    assert listed["occupied"] == 2
    # Capacity cannot drop below occupancy; a stop in use cannot be removed.
    assert client.patch(f"{base}/routes/{route['id']}", json={"capacity": 1}).status_code == 422
    assert client.patch(f"{base}/routes/{route['id']}", json={"stops": [{"name": "Anna Nagar"}]}).status_code == 409
    renamed = client.patch(f"{base}/routes/{route['id']}", json={"stops": [{"name": "Kilpauk", "pickup_time": "07:30"}, {"name": "Anna Nagar"}, {"name": "Egmore"}]})
    assert renamed.status_code == 200 and [s["name"] for s in renamed.json()["stops"]] == ["Kilpauk", "Anna Nagar", "Egmore"]
    ended = client.post(f"{base}/assignments/{second.json()['id']}/end")
    assert ended.json()["status"] == "ended" and ended.json()["ended_on"]
    assert client.post(f"{base}/assignments/{second.json()['id']}/end").status_code == 409
    assert client.get(f"{base}/routes").json()[0]["occupied"] == 1
    as_user(campus.teacher)
    assert client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": campus.student_members[2].id, "stop_id": stop}).status_code == 403


def test_boarding_roster_upsert_future_and_learner_views(bus_campus, client, as_user):
    campus = bus_campus
    route = _route(client, campus, capacity=5).json()
    base = f"{ROOT}/{campus.iid}/transport"
    for member, stop in zip(campus.student_members[:2], route["stops"]):
        assert client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": member.id, "stop_id": stop["id"]}).status_code == 201
    as_user(campus.teacher)
    today = client.get(f"{base}/routes/{route['id']}/roster").json()
    assert len(today["students"]) == 2 and all(s["boarded"] is None for s in today["students"])
    day = today["day"]
    tomorrow = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    assert client.put(f"{base}/routes/{route['id']}/boarding", json={"day": tomorrow, "entries": [{"member_id": campus.student_members[0].id, "boarded": True}]}).status_code == 422
    assert client.put(f"{base}/routes/{route['id']}/boarding", json={"day": day, "entries": [{"member_id": campus.student_members[2].id, "boarded": True}]}).status_code == 422
    saved = client.put(
        f"{base}/routes/{route['id']}/boarding",
        json={"day": day, "entries": [{"member_id": campus.student_members[0].id, "boarded": True}, {"member_id": campus.student_members[1].id, "boarded": False}]},
    )
    assert saved.status_code == 200, saved.text
    flags = {s["member_id"]: (s["boarded"], s["dropped"]) for s in saved.json()["students"]}
    assert flags[campus.student_members[0].id] == (True, False) and flags[campus.student_members[1].id] == (False, False)
    again = client.put(f"{base}/routes/{route['id']}/boarding", json={"day": day, "entries": [{"member_id": campus.student_members[0].id, "boarded": True, "dropped": True}]})
    assert {s["member_id"]: s["dropped"] for s in again.json()["students"]}[campus.student_members[0].id] is True
    csv_response = client.get(f"{base}/routes/{route['id']}/roster.csv")
    assert csv_response.status_code == 200 and csv_response.text.startswith("Route,Stop,Student,Started on,Boarded today,Dropped today")
    assert 'filename="transport-North-loop.csv"' in csv_response.headers["content-disposition"]
    as_user(campus.students[0])
    mine = client.get(f"{base}/me").json()
    assert mine["assigned"] is True and mine["stop"]["name"] == "Anna Nagar" and mine["today"] == {"day": day, "boarded": True, "dropped": True}
    assert client.get(f"{base}/routes/{route['id']}/roster").status_code == 403
    as_user(campus.students[2])
    assert client.get(f"{base}/me").json()["assigned"] is False
    as_user(campus.parent)
    assert client.get(f"{base}/me", params={"student_user_id": campus.students[1].id}).status_code == 404
    guardian = client.get(f"{base}/me", params={"student_user_id": campus.students[0].id}).json()
    assert guardian["route"]["driver_phone"] == "+919000000001"


def test_today_flags_routes_without_boarding(bus_campus, client, as_user):
    campus = bus_campus
    route = _route(client, campus, capacity=5).json()
    base = f"{ROOT}/{campus.iid}/transport"
    today = client.get(f"{ROOT}/{campus.iid}/today").json()
    assert all(a["id"] != "system-transport" for a in today["actions"])
    client.post(f"{base}/routes/{route['id']}/assignments", json={"member_id": campus.student_members[0].id, "stop_id": route["stops"][0]["id"]})
    today = client.get(f"{ROOT}/{campus.iid}/today").json()
    flagged = next(a for a in today["actions"] if a["id"] == "system-transport")
    assert flagged["href"].endswith("/transport") and "1 route" in flagged["title"]
    day = client.get(f"{base}/routes/{route['id']}/roster").json()["day"]
    client.put(f"{base}/routes/{route['id']}/boarding", json={"day": day, "entries": [{"member_id": campus.student_members[0].id, "boarded": True}]})
    today = client.get(f"{ROOT}/{campus.iid}/today").json()
    assert all(a["id"] != "system-transport" for a in today["actions"])


def test_campus_transport_migration_round_trip():
    versions = Path(__file__).parents[1] / "alembic/versions"
    spec = importlib.util.spec_from_file_location("m0041", versions / "0041_campus_transport.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for name in ("institutions", "users", "institution_members", "tuition_fee_plans", "tuition_fee_assignments"):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        wanted = {"campus_transport_routes", "campus_transport_stops", "campus_transport_assignments", "campus_transport_logs"}
        assert wanted <= set(inspect(connection).get_table_names())
        module.downgrade()
        assert not set(inspect(connection).get_table_names()) & wanted
