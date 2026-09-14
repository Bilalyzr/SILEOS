"""Institution boundaries, invitations, academic lifecycle, and truthful billing."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.models.institution import (
    InstitutionMember,
    InstitutionInvite,
    Institution,
    InstitutionAudit,
)
from app.models.course import Course
from app.models.enrollment import Enrollment

ROOT = "/api/v1/institutions"


@pytest.fixture
def campus(client, as_user, make_user):
    owner = make_user(role="instructor", email="owner@college.edu")
    as_user(owner)
    response = client.post(
        ROOT,
        json={
            "name": "Greenwood College",
            "kind": "college",
            "academic_year": "2026–2027",
        },
    )
    assert response.status_code == 201, response.text
    return owner, response.json()["id"]


def member(db, make_user, institution_id, role="student"):
    user = make_user()
    row = InstitutionMember(
        institution_id=institution_id,
        user_id=user.id,
        role=role,
        status="active",
        department="Science",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return user, row


def test_owner_is_not_platform_admin_and_settings_cannot_change_plan(
    campus, db, client
):
    owner, institution_id = campus
    assert owner.role == "instructor"
    assert client.get(ROOT).json()[0]["role"] == "owner"
    payload = {"name": "College", "academic_year": "2026", "plan": "enterprise"}
    assert client.patch(f"{ROOT}/{institution_id}", json=payload).status_code == 422
    assert db.get(Institution, institution_id).plan == "starter"


def test_other_institutions_and_platform_admin_have_no_implicit_access(
    campus, client, as_user, make_user
):
    _, institution_id = campus
    for role in ("student", "admin", "superadmin"):
        as_user(make_user(role=role))
        assert client.get(f"{ROOT}/{institution_id}").status_code == 404
        assert client.get(f"{ROOT}/{institution_id}/report.csv").status_code == 404
        assert client.get(ROOT).json() == []


def test_invitation_requires_matching_verified_account_and_single_use(
    campus, client, db, as_user, make_user
):
    owner, institution_id = campus
    invited = make_user(email="new@college.edu")
    result = client.post(
        f"{ROOT}/{institution_id}/invitations",
        json={"email": "NEW@college.edu", "role": "teacher"},
    )
    assert result.status_code == 201, result.text
    invitation_id = result.json()["id"]
    assert result.json()["delivery"] == "account_inbox"
    as_user(make_user(email="stranger@college.edu"))
    assert client.post(f"{ROOT}/invitations/{invitation_id}/accept").status_code == 404
    as_user(invited)
    inbox = client.get(f"{ROOT}/invitations").json()
    assert len(inbox) == 1
    assert datetime.fromisoformat(inbox[0]["expires_at"]).utcoffset() == timedelta(0)
    invited.is_verified = False
    db.commit()
    assert client.post(f"{ROOT}/invitations/{invitation_id}/accept").status_code == 403
    invited.is_verified = True
    db.commit()
    assert client.post(f"{ROOT}/invitations/{invitation_id}/accept").status_code == 200
    assert client.post(f"{ROOT}/invitations/{invitation_id}/accept").status_code == 409
    assert (
        invited.role == "student"
    )  # Institution teacher does not change platform role.


def test_expired_and_revoked_invites_cannot_join(
    campus, client, db, as_user, make_user
):
    owner, institution_id = campus
    for revoked in (False, True):
        u = make_user()
        as_user(owner)
        result = client.post(
            f"{ROOT}/{institution_id}/invitations", json={"email": u.user_email}
        )
        invitation_id = result.json()["id"]
        if revoked:
            assert (
                client.delete(
                    f"{ROOT}/{institution_id}/invitations/{invitation_id}"
                ).status_code
                == 200
            )
        else:
            db.get(InstitutionInvite, invitation_id).expires_at = datetime.now(
                timezone.utc
            ) - timedelta(days=1)
            db.commit()
        as_user(u)
        assert (
            client.post(f"{ROOT}/invitations/{invitation_id}/accept").status_code == 409
        )


def test_admin_cannot_promote_self_or_modify_owner(
    campus, client, db, as_user, make_user
):
    owner, institution_id = campus
    admin, row = member(db, make_user, institution_id, "admin")
    as_user(admin)
    owner_member = (
        db.query(InstitutionMember)
        .filter_by(user_id=owner.id, institution_id=institution_id)
        .one()
    )
    for target in (row.id, owner_member.id):
        assert (
            client.patch(
                f"{ROOT}/{institution_id}/members/{target}", json={"role": "student"}
            ).status_code
            == 403
        )
    assert (
        client.post(
            f"{ROOT}/{institution_id}/invitations",
            json={"email": "admin2@college.edu", "role": "admin"},
        ).status_code
        == 403
    )


def test_suspended_member_loses_institution_access(
    campus, client, db, as_user, make_user
):
    owner, institution_id = campus
    u, row = member(db, make_user, institution_id)
    assert (
        client.patch(
            f"{ROOT}/{institution_id}/members/{row.id}",
            json={"role": "student", "status": "suspended"},
        ).status_code
        == 200
    )
    as_user(u)
    assert client.get(f"{ROOT}/{institution_id}").status_code == 404
    assert u.is_active


def test_batch_rejects_cross_institution_and_nonstudent_ids_atomically(
    campus, client, db, make_user
):
    _, institution_id = campus
    _, valid = member(db, make_user, institution_id)
    _, teacher = member(db, make_user, institution_id, "teacher")
    batch_id = client.post(
        f"{ROOT}/{institution_id}/batches",
        json={"name": "Physics A", "academic_year": "2026"},
    ).json()["id"]
    for ids in ([valid.id, 999999], [teacher.id]):
        assert (
            client.post(
                f"{ROOT}/{institution_id}/batches/{batch_id}/members",
                json={"member_ids": ids},
            ).status_code
            == 422
        )
    assert (
        client.get(f"{ROOT}/{institution_id}").json()["batches"][0]["student_count"]
        == 0
    )
    for _ in range(2):
        assert (
            client.post(
                f"{ROOT}/{institution_id}/batches/{batch_id}/members",
                json={"member_ids": [valid.id, valid.id]},
            ).status_code
            == 200
        )
    assert (
        client.get(f"{ROOT}/{institution_id}").json()["batches"][0]["student_count"]
        == 1
    )


def test_assignment_reports_are_scoped_and_do_not_unlock_paid_courses(
    campus, client, db, as_user, make_user
):
    owner, institution_id = campus
    student, m = member(db, make_user, institution_id)
    outsider = make_user()
    course = Course(
        post_author=owner.id,
        post_title="=Physics",
        post_status="published",
        course_price_type="paid",
        course_price=500,
    )
    db.add(course)
    db.commit()
    assert (
        client.post(
            f"{ROOT}/{institution_id}/courses", json={"course_id": course.id}
        ).status_code
        == 201
    )
    linked = client.get(f"{ROOT}/{institution_id}").json()["courses"][0]["id"]
    batch = client.post(
        f"{ROOT}/{institution_id}/batches",
        json={"name": "Grade 11", "academic_year": "2026"},
    ).json()["id"]
    client.post(
        f"{ROOT}/{institution_id}/batches/{batch}/members", json={"member_ids": [m.id]}
    )
    assert (
        client.post(
            f"{ROOT}/{institution_id}/batches/{batch}/assignments",
            json={"institution_course_id": linked},
        ).status_code
        == 200
    )
    report = client.get(f"{ROOT}/{institution_id}").json()["report"]
    assert len(report) == 1 and report[0]["has_access"] is False
    assert db.query(Enrollment).filter_by(user_id=student.id).count() == 0
    db.add(
        Enrollment(
            user_id=student.id,
            course_id=course.id,
            enrollment_status="enrolled",
            course_progress_percentage=45,
        )
    )
    db.add(
        Enrollment(
            user_id=outsider.id,
            course_id=course.id,
            enrollment_status="enrolled",
            course_progress_percentage=99,
        )
    )
    db.commit()
    report = client.get(f"{ROOT}/{institution_id}").json()["report"]
    assert len(report) == 1 and report[0]["progress"] == 45
    exported = client.get(f"{ROOT}/{institution_id}/report.csv")
    assert "'=Physics" in exported.text
    as_user(student)
    data = client.get(f"{ROOT}/{institution_id}").json()
    assert (
        len(data["members"]) == 1
        and not data["invites"]
        and not data["activity"]
        and data["usage"] is None
    )
    assert len(data["report"]) == 1
    assert client.get(f"{ROOT}/{institution_id}/report.csv").status_code == 403


def test_student_cannot_mutate_academics_or_billing(
    campus, client, db, as_user, make_user
):
    _, institution_id = campus
    u, _ = member(db, make_user, institution_id)
    as_user(u)
    assert (
        client.post(
            f"{ROOT}/{institution_id}/batches",
            json={"name": "Class A", "academic_year": "2026"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"{ROOT}/{institution_id}/plan-requests", json={"plan": "enterprise"}
        ).status_code
        == 403
    )
    assert client.get(f"{ROOT}/{institution_id}/available-courses").status_code == 403


def test_plan_request_is_durable_idempotent_pending_not_activation(campus, client, db):
    _, institution_id = campus
    assert (
        client.post(
            f"{ROOT}/{institution_id}/plan-requests",
            json={"plan": "campus", "note": "500 students"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"{ROOT}/{institution_id}/plan-requests", json={"plan": "enterprise"}
        ).status_code
        == 409
    )
    data = client.get(f"{ROOT}/{institution_id}").json()
    assert data["institution"]["plan"] == "starter"
    assert data["plan_requests"][0]["status"] == "pending"
    assert (
        db.query(InstitutionAudit)
        .filter_by(institution_id=institution_id, action="plan.requested")
        .count()
        == 1
    )


def test_plan_capacity_counts_pending_invitations(campus, client, monkeypatch):
    from app.services import institution_service as svc

    _, institution_id = campus
    monkeypatch.setitem(
        svc.LIMITS, "starter", {"members": 2, "batches": 1, "courses": 1}
    )
    assert (
        client.post(
            f"{ROOT}/{institution_id}/invitations", json={"email": "first@college.edu"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"{ROOT}/{institution_id}/invitations", json={"email": "second@college.edu"}
        ).status_code
        == 409
    )


def test_unrelated_course_cannot_be_connected(campus, client, db, make_user):
    _, institution_id = campus
    other = make_user(role="instructor")
    course = Course(
        post_author=other.id,
        post_title="Other college private course",
        post_status="draft",
    )
    db.add(course)
    db.commit()
    assert (
        client.post(
            f"{ROOT}/{institution_id}/courses", json={"course_id": course.id}
        ).status_code
        == 404
    )
    assert not client.get(f"{ROOT}/{institution_id}/available-courses").json()


def test_timezone_and_blank_names_are_validated(client, as_user, make_user):
    as_user(make_user())
    for payload in (
        {"name": "  ", "academic_year": "2026"},
        {"name": "College", "academic_year": "2026", "timezone": "Not/AZone"},
    ):
        assert client.post(ROOT, json=payload).status_code == 422


def test_migration_upgrade_downgrade_roundtrip():
    path = Path(__file__).parents[1] / "alembic/versions/0030_institutions.py"
    spec = importlib.util.spec_from_file_location("institution_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert "institution_members" in inspect(connection).get_table_names()
        migration.downgrade()
        assert not inspect(connection).get_table_names()
        migration.upgrade()
        assert len(inspect(connection).get_table_names()) == 9


def test_platform_review_requires_admin_and_preserves_plan(
    campus, client, db, as_user, make_user
):
    owner, institution_id = campus
    client.post(f"{ROOT}/{institution_id}/plan-requests", json={"plan": "campus"})
    assert client.get(f"{ROOT}/platform/plan-requests").status_code == 403
    as_user(make_user(role="admin"))
    queue = client.get(f"{ROOT}/platform/plan-requests").json()
    assert queue[0]["institution_id"] == institution_id
    request_id = queue[0]["id"]
    assert (
        client.patch(
            f"{ROOT}/platform/plan-requests/{request_id}",
            json={"status": "reviewed", "note": "Requirements checked"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"{ROOT}/platform/plan-requests/{request_id}",
            json={"status": "declined", "note": "Second review"},
        ).status_code
        == 409
    )
    assert db.get(Institution, institution_id).plan == "starter"
    as_user(owner)
    assert (
        client.get(f"{ROOT}/{institution_id}").json()["plan_requests"][0]["status"]
        == "reviewed"
    )
