from datetime import datetime, timedelta, timezone
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
from PyPDF2 import PdfReader
import pytest
from sqlalchemy import create_engine, inspect

from app.models.campus_exams import CampusExam, CampusExamPaper, CampusHallTicket
from app.models.campus_operations import ParentLinkRequest
from app.models.campus_pilot import CampusEvent
from app.models.institution import InstitutionAudit, InstitutionMember


ROOT = "/api/v1/institutions"
START = datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def exam_campus(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="exam-owner@example.org")
    teacher = make_user(role="instructor", email="exam-teacher@example.org")
    student = make_user(email="exam-student@example.org")
    other_student = make_user(email="exam-other@example.org")
    parent = make_user(role="parent", email="exam-parent@example.org")
    stranger = make_user(role="instructor", email="exam-stranger@example.org")
    as_user(owner)
    institution_id = client.post(
        ROOT,
        json={
            "name": "Greenwood College",
            "academic_year": "2026-27",
            "timezone": "Asia/Kolkata",
        },
    ).json()["id"]
    batch_id = client.post(
        f"{ROOT}/{institution_id}/batches",
        json={"name": "Grade 10 A", "academic_year": "2026-27"},
    ).json()["id"]
    term_id = client.post(
        f"{ROOT}/{institution_id}/terms",
        json={"name": "Term 1", "starts_on": "2026-06-01", "ends_on": "2026-12-20"},
    ).json()["id"]
    members = []
    for account, role in (
        (teacher, "teacher"),
        (student, "student"),
        (other_student, "student"),
    ):
        member = InstitutionMember(
            institution_id=institution_id,
            user_id=account.id,
            role=role,
            status="active",
            department="Science",
        )
        db.add(member)
        db.flush()
        members.append(member)
    db.commit()
    client.post(
        f"{ROOT}/{institution_id}/batches/{batch_id}/members",
        json={"member_ids": [members[1].id, members[2].id]},
    )
    as_user(stranger)
    other_institution_id = client.post(
        ROOT,
        json={"name": "Elsewhere School", "academic_year": "2026-27"},
    ).json()["id"]
    as_user(owner)
    return SimpleNamespace(
        owner=owner,
        teacher=teacher,
        student=student,
        other_student=other_student,
        parent=parent,
        stranger=stranger,
        iid=institution_id,
        other_iid=other_institution_id,
        bid=batch_id,
        term_id=term_id,
        teacher_member=members[0],
        student_member=members[1],
        other_member=members[2],
    )


def _exam(client, campus, name="Mid-term"):
    return client.post(
        f"{ROOT}/{campus.iid}/exams",
        json={"term_id": campus.term_id, "name": name, "kind": "midterm"},
    )


def _paper(client, campus, exam_id, subject="Physics", start=START, room="Hall A"):
    return client.post(
        f"{ROOT}/{campus.iid}/exams/{exam_id}/papers",
        json={
            "batch_id": campus.bid,
            "subject": subject,
            "max_marks": 100,
            "pass_marks": 35,
            "starts_at": start.isoformat(),
            "duration_minutes": 120,
            "room": room,
        },
    )


def test_teacher_creates_exam_and_duplicate_name_conflicts(exam_campus, client, as_user):
    campus = exam_campus
    as_user(campus.teacher)
    created = _exam(client, campus)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["papers"] == []
    assert _exam(client, campus).status_code == 409
    as_user(campus.student)
    assert _exam(client, campus).status_code == 403
    as_user(campus.stranger)
    assert _exam(client, campus).status_code == 404


def test_paper_schedules_timetable_event_and_rejects_conflicts(
    exam_campus, client, as_user, db
):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    created = _paper(client, campus, exam_id)
    assert created.status_code == 201, created.text
    paper = created.json()
    assert paper["ends_at"].startswith("2026-10-05T11:00")
    event = db.get(CampusEvent, paper["event_id"])
    assert event.kind == "exam" and event.batch_id == campus.bid
    assert db.get(CampusExam, exam_id).status == "scheduled"
    # Same batch, overlapping time: conflict.
    clash = _paper(client, campus, exam_id, subject="Chemistry", start=START + timedelta(hours=1))
    assert clash.status_code == 409
    assert "conflict" in clash.json()["detail"].lower()
    # Different day, same room: fine.
    ok = _paper(client, campus, exam_id, subject="Chemistry", start=START + timedelta(days=1))
    assert ok.status_code == 201
    listed = client.get(f"{ROOT}/{campus.iid}/exams", params={"term_id": campus.term_id}).json()
    assert len(listed[0]["papers"]) == 2


def test_paper_delete_blocked_when_marks_exist(exam_campus, client, as_user, db):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    paper_id = _paper(client, campus, exam_id).json()["id"]
    marks = client.put(
        f"{ROOT}/{campus.iid}/exams/{exam_id}/papers/{paper_id}/marks",
        json={"entries": [{"member_id": campus.student_member.id, "marks": 80}]},
    )
    assert marks.status_code == 200, marks.text
    assert client.delete(f"{ROOT}/{campus.iid}/exams/{exam_id}/papers/{paper_id}").status_code == 409
    empty = _paper(client, campus, exam_id, subject="Biology", start=START + timedelta(days=2)).json()
    assert client.delete(f"{ROOT}/{campus.iid}/exams/{exam_id}/papers/{empty['id']}").status_code == 204
    assert db.get(CampusEvent, empty["event_id"]) is None


def test_publish_requires_papers_and_manager(exam_campus, client, as_user, db):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    assert client.post(f"{ROOT}/{campus.iid}/exams/{exam_id}/publish").status_code == 422
    _paper(client, campus, exam_id)
    as_user(campus.teacher)
    assert client.post(f"{ROOT}/{campus.iid}/exams/{exam_id}/publish").status_code == 403
    as_user(campus.owner)
    published = client.post(f"{ROOT}/{campus.iid}/exams/{exam_id}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_at"]
    unpublished = client.post(f"{ROOT}/{campus.iid}/exams/{exam_id}/unpublish")
    assert unpublished.json()["status"] == "scheduled"
    actions = {
        row.action for row in db.query(InstitutionAudit).filter_by(institution_id=campus.iid)
    }
    assert {"exam.published", "exam.unpublished"} <= actions


def test_marks_validation_upsert_and_lock(exam_campus, client, as_user):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    paper_id = _paper(client, campus, exam_id).json()["id"]
    url = f"{ROOT}/{campus.iid}/exams/{exam_id}/papers/{paper_id}/marks"
    roster = client.get(url).json()
    assert {row["member_id"] for row in roster} == {
        campus.student_member.id,
        campus.other_member.id,
    }
    assert all(row["marks"] is None for row in roster)
    too_high = client.put(url, json={"entries": [{"member_id": campus.student_member.id, "marks": 120}]})
    assert too_high.status_code == 422
    outsider = client.put(url, json={"entries": [{"member_id": campus.teacher_member.id, "marks": 10}]})
    assert outsider.status_code == 422
    first = client.put(
        url,
        json={
            "entries": [
                {"member_id": campus.student_member.id, "marks": 70, "remarks": "Good"},
                {"member_id": campus.other_member.id, "absent": True, "marks": 50},
            ]
        },
    )
    assert first.status_code == 200
    by_member = {row["member_id"]: row for row in first.json()}
    assert by_member[campus.student_member.id]["marks"] == 70
    assert by_member[campus.other_member.id]["absent"] is True
    assert by_member[campus.other_member.id]["marks"] is None
    second = client.put(url, json={"entries": [{"member_id": campus.student_member.id, "marks": 88}]})
    assert {row["member_id"]: row["marks"] for row in second.json()}[campus.student_member.id] == 88
    client.post(f"{ROOT}/{campus.iid}/exams/{exam_id}/publish")
    assert client.put(url, json={"entries": [{"member_id": campus.student_member.id, "marks": 1}]}).status_code == 409


def test_results_rank_and_visibility(exam_campus, client, as_user, db):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    physics = _paper(client, campus, exam_id).json()["id"]
    chemistry = _paper(client, campus, exam_id, subject="Chemistry", start=START + timedelta(days=1)).json()["id"]
    base = f"{ROOT}/{campus.iid}/exams/{exam_id}"
    client.put(
        f"{base}/papers/{physics}/marks",
        json={
            "entries": [
                {"member_id": campus.student_member.id, "marks": 80},
                {"member_id": campus.other_member.id, "marks": 50},
            ]
        },
    )
    client.put(
        f"{base}/papers/{chemistry}/marks",
        json={
            "entries": [
                {"member_id": campus.student_member.id, "marks": 70},
                {"member_id": campus.other_member.id, "absent": True},
            ]
        },
    )
    results = client.get(f"{base}/results", params={"batch_id": campus.bid}).json()
    rows = {row["member_id"]: row for row in results["rows"]}
    top = rows[campus.student_member.id]
    assert top["total"] == 150 and top["max_total"] == 200 and top["percent"] == 75.0
    assert top["rank"] == 1 and top["passed"] is True
    low = rows[campus.other_member.id]
    assert low["total"] == 50 and low["rank"] == 2 and low["passed"] is False
    # Not published: students see nothing yet.
    as_user(campus.student)
    assert client.get(f"{base}/results/me").status_code == 404
    assert client.get(f"{base}/results", params={"batch_id": campus.bid}).status_code == 403
    as_user(campus.owner)
    client.post(f"{base}/publish")
    as_user(campus.student)
    mine = client.get(f"{base}/results/me")
    assert mine.status_code == 200
    assert mine.json()["total"] == 150 and mine.json()["rank"] == 1
    # Parent without approval: 404. With approval: sees the child's results.
    as_user(campus.parent)
    assert client.get(f"{base}/results/me", params={"student_user_id": campus.student.id}).status_code == 404
    db.add(
        ParentLinkRequest(
            parent_user_id=campus.parent.id,
            student_user_id=campus.student.id,
            status="approved",
        )
    )
    db.commit()
    approved = client.get(f"{base}/results/me", params={"student_user_id": campus.student.id})
    assert approved.status_code == 200 and approved.json()["total"] == 150
    # Students only see scheduled or published exams in the list.
    as_user(campus.owner)
    _exam(client, campus, name="Draft only")
    as_user(campus.student)
    names = {row["name"] for row in client.get(f"{ROOT}/{campus.iid}/exams").json()}
    assert names == {"Mid-term"}


def test_hall_tickets_idempotent_and_pdf_access(exam_campus, client, as_user, db):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    _paper(client, campus, exam_id)
    base = f"{ROOT}/{campus.iid}/exams/{exam_id}/hall-tickets"
    first = client.get(base).json()
    assert {row["member_id"] for row in first} == {campus.student_member.id, campus.other_member.id}
    second = client.get(base).json()
    assert {row["token"] for row in first} == {row["token"] for row in second}
    assert db.query(CampusHallTicket).filter_by(exam_id=exam_id).count() == 2
    as_user(campus.student)
    own = client.get(f"{base}/{campus.student_member.id}/pdf")
    assert own.status_code == 200
    assert own.headers["content-type"] == "application/pdf"
    assert own.content.startswith(b"%PDF")
    text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(own.content)).pages)
    assert "Physics" in text and "Hall A" in text
    assert client.get(f"{base}/{campus.other_member.id}/pdf").status_code == 404
    assert client.get(base).status_code == 403
    # "me" resolves the caller's own membership; staff must name a student.
    mine = client.get(f"{base}/me/pdf")
    assert mine.status_code == 200 and mine.content.startswith(b"%PDF")
    as_user(campus.owner)
    assert client.get(f"{base}/me/pdf").status_code == 404
    # Guardians reach the child's ticket only through an approved link.
    as_user(campus.parent)
    assert client.get(f"{base}/me/pdf", params={"student_user_id": campus.student.id}).status_code == 404
    db.add(ParentLinkRequest(parent_user_id=campus.parent.id, student_user_id=campus.student.id, status="approved"))
    db.commit()
    guardian = client.get(f"{base}/me/pdf", params={"student_user_id": campus.student.id})
    assert guardian.status_code == 200 and guardian.content.startswith(b"%PDF")


def test_marksheet_pdf_after_publish(exam_campus, client, as_user):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    paper_id = _paper(client, campus, exam_id).json()["id"]
    base = f"{ROOT}/{campus.iid}/exams/{exam_id}"
    client.put(
        f"{base}/papers/{paper_id}/marks",
        json={"entries": [{"member_id": campus.student_member.id, "marks": 91.5}]},
    )
    staff = client.get(f"{base}/results/{campus.student_member.id}/marksheet.pdf")
    assert staff.status_code == 200 and staff.content.startswith(b"%PDF")
    as_user(campus.student)
    assert client.get(f"{base}/results/{campus.student_member.id}/marksheet.pdf").status_code == 404
    as_user(campus.owner)
    client.post(f"{base}/publish")
    as_user(campus.student)
    mine = client.get(f"{base}/results/{campus.student_member.id}/marksheet.pdf")
    assert mine.status_code == 200
    text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(mine.content)).pages)
    assert "Physics" in text and "91.5" in text
    assert client.get(f"{base}/results/{campus.other_member.id}/marksheet.pdf").status_code == 404


def test_report_card_includes_published_exam_rows(exam_campus, client, as_user):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    paper_id = _paper(client, campus, exam_id).json()["id"]
    base = f"{ROOT}/{campus.iid}/exams/{exam_id}"
    client.put(
        f"{base}/papers/{paper_id}/marks",
        json={"entries": [{"member_id": campus.student_member.id, "marks": 60}]},
    )
    card_url = f"{ROOT}/{campus.iid}/pilot/report-cards/{campus.student_member.id}"
    before = client.get(card_url, params={"term_id": campus.term_id}).json()
    assert all("Mid-term" not in row["subject"] for row in before["rows"])
    client.post(f"{base}/publish")
    after = client.get(card_url, params={"term_id": campus.term_id}).json()
    exam_rows = [row for row in after["rows"] if row["subject"] == "Mid-term · Physics"]
    assert len(exam_rows) == 1
    assert exam_rows[0]["score"] == 60 and exam_rows[0]["max_score"] == 100
    assert after["overall_percent"] == 60.0


def test_cross_institution_exam_access_is_hidden(exam_campus, client, as_user):
    campus = exam_campus
    exam_id = _exam(client, campus).json()["id"]
    as_user(campus.stranger)
    assert client.get(f"{ROOT}/{campus.iid}/exams/{exam_id}/hall-tickets").status_code == 404
    assert client.get(f"{ROOT}/{campus.other_iid}/exams/{exam_id}/results", params={"batch_id": campus.bid}).status_code == 404


def test_campus_exams_migration_round_trip():
    versions = Path(__file__).parents[1] / "alembic/versions"

    def load(name):
        spec = importlib.util.spec_from_file_location(name, versions / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        op = Operations(MigrationContext.configure(connection))
        # Parent tables the new foreign keys reference.
        for name in ("institutions", "users", "campus_terms", "institution_batches", "institution_members", "campus_events"):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
        module = load("0038_campus_exams")
        module.op = op
        module.upgrade()
        tables = set(inspect(connection).get_table_names())
        assert {"campus_exams", "campus_exam_papers", "campus_exam_marks", "campus_hall_tickets"} <= tables
        module.downgrade()
        remaining = set(inspect(connection).get_table_names())
        assert not remaining & {"campus_exams", "campus_exam_papers", "campus_exam_marks", "campus_hall_tickets"}
