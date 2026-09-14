"""Focused admissions, conversion, tenant isolation, and migration coverage."""

from datetime import date, timedelta
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect

from app.core.database import get_db
from app.models.admissions import (
    AdmissionApplication,
    AdmissionDocument,
    AdmissionStageHistory,
    CampusLearnerLifecycleHistory,
    CampusLearnerProfile,
)
from app.models.institution import (
    Institution,
    InstitutionBatch,
    InstitutionInvite,
    InstitutionMember,
)
from app.routers import admissions
from app.services.auth_service import AuthService


ROOT = "/api/v1/institutions"


@pytest.fixture
def admissions_client(TestingSessionLocal):
    app = FastAPI()
    app.include_router(admissions.router, prefix=ROOT)
    actor = {"user": None}

    def session_override():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def current_user():
        return actor["user"]

    app.dependency_overrides[get_db] = session_override
    app.dependency_overrides[AuthService.get_current_active_user] = current_user
    with TestClient(app) as client:
        yield client, lambda user: actor.__setitem__("user", user)


def make_campus(db, make_user, *, name="Admissions College"):
    owner = make_user(role="instructor")
    institution = Institution(
        name=name,
        slug=f"campus-{owner.id}",
        kind="college",
        academic_year="2026-2027",
        timezone="Asia/Kolkata",
        plan="starter",
    )
    db.add(institution)
    db.flush()
    member = InstitutionMember(
        institution_id=institution.id,
        user_id=owner.id,
        role="owner",
        status="active",
        department="Admissions",
    )
    db.add(member)
    db.commit()
    return owner, institution, member


def create_program_and_intake(client, institution_id):
    program = client.post(
        f"{ROOT}/{institution_id}/admissions/programs",
        json={
            "name": "Bachelor of Computer Applications",
            "code": "bca",
            "level": "undergraduate",
            "department": "Computing",
            "duration_months": 36,
            "status": "active",
        },
    )
    assert program.status_code == 201, program.text
    program = program.json()
    intake = client.post(
        f"{ROOT}/{institution_id}/admissions/intakes",
        json={
            "program_id": program["id"],
            "name": "July intake",
            "academic_year": "2027-2028",
            "starts_on": (date.today() + timedelta(days=90)).isoformat(),
            "closes_on": (date.today() + timedelta(days=60)).isoformat(),
            "capacity": 2,
            "status": "open",
        },
    )
    assert intake.status_code == 201, intake.text
    return program, intake.json()


def create_application(client, institution_id, program_id, intake_id, email):
    response = client.post(
        f"{ROOT}/{institution_id}/admissions/applications",
        json={
            "full_name": "Asha Rao",
            "email": email,
            "phone": "+919876543210",
            "program_id": program_id,
            "intake_id": intake_id,
            "date_of_birth": "2007-04-12",
            "address": "Chennai",
            "prior_institution": "Greenwood School",
            "source": "open-day",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def move_stage(client, institution_id, application, stage, reason=""):
    response = client.patch(
        f"{ROOT}/{institution_id}/admissions/applications/{application['id']}/stage",
        json={
            "stage": stage,
            "reason": reason,
            "expected_version": application["version"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_complete_application_offer_conversion_and_lifecycle(
    admissions_client, db, make_user
):
    client, as_actor = admissions_client
    owner, institution, _ = make_campus(db, make_user)
    as_actor(owner)
    program, intake = create_program_and_intake(client, institution.id)
    applicant_account = make_user(email="asha@example.edu")
    application = create_application(
        client,
        institution.id,
        program["id"],
        intake["id"],
        applicant_account.user_email,
    )
    assert application["stage"] == "submitted"
    assert application["version"] == 1
    assert application["application_number"].startswith("APP-")

    checklist = client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/documents",
        json={"kind": "marksheet", "label": "Grade 12 marksheet", "required": True},
    )
    assert checklist.status_code == 201
    document_id = checklist.json()["documents"][0]["id"]
    for document_status in ("submitted", "verified"):
        checklist = client.patch(
            f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/documents/{document_id}",
            json={"status": document_status, "rejection_reason": ""},
        )
        assert checklist.status_code == 200, checklist.text

    application = move_stage(client, institution.id, application, "screening")
    application = move_stage(client, institution.id, application, "decision")
    offer = client.put(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/offer",
        json={
            "status": "issued",
            "expires_on": (date.today() + timedelta(days=14)).isoformat(),
            "conditions": "Submit original documents at orientation.",
            "tuition_amount": "75000.00",
            "currency": "INR",
            "expected_version": application["version"],
        },
    )
    assert offer.status_code == 200, offer.text
    application = offer.json()
    assert application["stage"] == "offered"
    assert application["offer_status"] == "issued"

    accepted = client.put(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/offer",
        json={
            "status": "accepted",
            "expected_version": application["version"],
        },
    )
    assert accepted.status_code == 200, accepted.text
    application = accepted.json()
    assert application["stage"] == "admitted"
    assert application["tuition_amount"] == "75000.00"

    converted = client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/convert",
        json={
            "expected_version": application["version"],
            "admission_number": "BCA/2027/001",
        },
    )
    assert converted.status_code == 200, converted.text
    converted = converted.json()
    assert converted["outcome"] == "enrolled"
    assert converted["application"]["stage"] == "enrolled"
    profile = converted["learner_profile"]
    assert profile["learner_email"] == applicant_account.user_email
    assert profile["admission_number"] == "BCA/2027/001"
    assert profile["history"][0]["to_status"] == "enrolled"

    activated = client.patch(
        f"{ROOT}/{institution.id}/admissions/learners/{profile['member_id']}/lifecycle",
        json={"status": "active", "expected_version": profile["version"]},
    )
    assert activated.status_code == 200, activated.text
    active_profile = activated.json()
    completed = client.patch(
        f"{ROOT}/{institution.id}/admissions/learners/{profile['member_id']}/lifecycle",
        json={"status": "completed", "expected_version": active_profile["version"]},
    )
    assert completed.status_code == 200
    assert completed.json()["completed_on"] == date.today().isoformat()
    assert db.query(CampusLearnerProfile).count() == 1
    assert db.query(CampusLearnerLifecycleHistory).count() == 3
    assert db.query(AdmissionStageHistory).count() == 6


def test_unverified_applicant_gets_reusable_invitation(
    admissions_client, db, make_user
):
    client, as_actor = admissions_client
    owner, institution, _ = make_campus(db, make_user)
    as_actor(owner)
    program, intake = create_program_and_intake(client, institution.id)
    application = create_application(
        client, institution.id, program["id"], intake["id"], "new.student@example.edu"
    )
    application = move_stage(client, institution.id, application, "screening")
    application = move_stage(client, institution.id, application, "decision")
    application = move_stage(client, institution.id, application, "admitted")
    result = client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/convert",
        json={"expected_version": application["version"]},
    )
    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload["outcome"] == "invited"
    assert payload["invitation_id"]
    assert (
        db.query(InstitutionInvite).filter_by(email="new.student@example.edu").count()
        == 1
    )
    assert db.query(CampusLearnerProfile).count() == 0

    # A client retry can safely use its original version without issuing a
    # second invitation or failing optimistic locking.
    retried = client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/convert",
        json={"expected_version": application["version"]},
    )
    assert retried.status_code == 200, retried.text
    assert retried.json()["invitation_id"] == payload["invitation_id"]
    assert (
        db.query(InstitutionInvite).filter_by(email="new.student@example.edu").count()
        == 1
    )


def test_required_documents_and_capacity_block_conversion(
    admissions_client, db, make_user
):
    client, as_actor = admissions_client
    owner, institution, _ = make_campus(db, make_user)
    as_actor(owner)
    program, intake = create_program_and_intake(client, institution.id)
    first = make_user(email="first@example.edu")
    application = create_application(
        client, institution.id, program["id"], intake["id"], first.user_email
    )
    application = move_stage(client, institution.id, application, "screening")
    application = move_stage(client, institution.id, application, "decision")
    application = move_stage(client, institution.id, application, "admitted")
    client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/documents",
        json={"kind": "identity", "label": "Identity proof", "required": True},
    )
    blocked = client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/convert",
        json={"expected_version": application["version"]},
    )
    assert blocked.status_code == 409
    assert "required document" in blocked.json()["detail"]

    # Capacity is checked against converted profiles, not application volume.
    document = db.query(AdmissionDocument).one()
    document.status = "waived"
    document.verified_by = owner.id
    db.commit()
    assert (
        client.patch(
            f"{ROOT}/{institution.id}/admissions/intakes/{intake['id']}",
            json={"capacity": 1},
        ).status_code
        == 200
    )
    enrolled = client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/convert",
        json={"expected_version": application["version"]},
    )
    assert enrolled.status_code == 200, enrolled.text

    second = make_user(email="second@example.edu")
    application2 = create_application(
        client, institution.id, program["id"], intake["id"], second.user_email
    )
    application2 = move_stage(client, institution.id, application2, "screening")
    application2 = move_stage(client, institution.id, application2, "decision")
    application2 = move_stage(client, institution.id, application2, "admitted")
    full = client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application2['id']}/convert",
        json={"expected_version": application2["version"]},
    )
    assert full.status_code == 409
    assert "capacity" in full.json()["detail"].lower()


def test_metrics_tasks_filters_and_offer_pdf(admissions_client, db, make_user):
    client, as_actor = admissions_client
    owner, institution, owner_member = make_campus(db, make_user)
    as_actor(owner)
    program, intake = create_program_and_intake(client, institution.id)
    application = create_application(
        client, institution.id, program["id"], intake["id"], "metrics@example.edu"
    )
    task = client.post(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/tasks",
        json={
            "title": "Review transcript",
            "due_on": (date.today() - timedelta(days=1)).isoformat(),
            "assignee_member_id": owner_member.id,
        },
    )
    assert task.status_code == 201, task.text
    assert (
        client.post(
            f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/notes",
            json={"body": "Strong academic record."},
        ).status_code
        == 201
    )
    summary = client.get(f"{ROOT}/{institution.id}/admissions/summary")
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["counts"]["total"] == 1
    assert payload["counts"]["active"] == 1
    assert payload["tasks"] == {"open": 1, "overdue": 1, "due_soon": 0}
    assert payload["intakes"][0]["applications"] == 1
    listing = client.get(
        f"{ROOT}/{institution.id}/admissions/applications",
        params={"search": "METRICS@", "stage": "submitted", "limit": 1},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    application = move_stage(client, institution.id, application, "screening")
    application = move_stage(client, institution.id, application, "decision")
    issued = client.put(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/offer",
        json={"status": "issued", "expected_version": application["version"]},
    )
    assert issued.status_code == 200
    pdf = client.get(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/offer.pdf"
    )
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["cache-control"] == "private, no-store"


def test_optimistic_locking_transition_rules_and_idempotent_retry(
    admissions_client, db, make_user
):
    client, as_actor = admissions_client
    owner, institution, _ = make_campus(db, make_user)
    as_actor(owner)
    program, intake = create_program_and_intake(client, institution.id)
    application = create_application(
        client, institution.id, program["id"], intake["id"], "locking@example.edu"
    )
    invalid = client.patch(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/stage",
        json={"stage": "enrolled", "expected_version": application["version"]},
    )
    assert invalid.status_code == 409
    application = move_stage(client, institution.id, application, "screening")
    stale = client.patch(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/stage",
        json={"stage": "decision", "expected_version": 1},
    )
    assert stale.status_code == 409
    retry = client.patch(
        f"{ROOT}/{institution.id}/admissions/applications/{application['id']}/stage",
        json={"stage": "screening", "expected_version": 1},
    )
    assert retry.status_code == 200
    assert retry.json()["version"] == application["version"]


def test_applicant_pii_has_no_platform_or_cross_tenant_bypass(
    admissions_client, db, make_user
):
    client, as_actor = admissions_client
    owner, institution, _ = make_campus(db, make_user, name="Campus One")
    as_actor(owner)
    program, intake = create_program_and_intake(client, institution.id)
    create_application(
        client, institution.id, program["id"], intake["id"], "private@example.edu"
    )
    other_owner, other, _ = make_campus(db, make_user, name="Campus Two")
    as_actor(other_owner)
    assert client.get(f"{ROOT}/{institution.id}/admissions/summary").status_code == 404
    assert (
        client.get(f"{ROOT}/{institution.id}/admissions/applications").status_code
        == 404
    )
    as_actor(make_user(role="superadmin"))
    assert (
        client.get(f"{ROOT}/{institution.id}/admissions/applications").status_code
        == 404
    )
    student = make_user(email="member@example.edu")
    db.add(
        InstitutionMember(
            institution_id=institution.id,
            user_id=student.id,
            role="student",
            status="active",
            department="",
        )
    )
    db.commit()
    as_actor(student)
    assert (
        client.get(f"{ROOT}/{institution.id}/admissions/applications").status_code
        == 403
    )


def test_program_intake_validation_and_archival_guards(
    admissions_client, db, make_user
):
    client, as_actor = admissions_client
    owner, institution, _ = make_campus(db, make_user)
    as_actor(owner)
    program, intake = create_program_and_intake(client, institution.id)
    duplicate = client.post(
        f"{ROOT}/{institution.id}/admissions/programs",
        json={
            "name": "Duplicate",
            "code": "BCA",
            "duration_months": 12,
            "status": "active",
        },
    )
    assert duplicate.status_code == 409
    archived = client.patch(
        f"{ROOT}/{institution.id}/admissions/programs/{program['id']}",
        json={"status": "archived"},
    )
    assert archived.status_code == 409
    bad_dates = client.patch(
        f"{ROOT}/{institution.id}/admissions/intakes/{intake['id']}",
        json={"closes_on": (date.today() + timedelta(days=200)).isoformat()},
    )
    assert bad_dates.status_code == 422


def test_admissions_migration_upgrade_downgrade_roundtrip():
    path = (
        Path(__file__).parents[1]
        / "alembic/versions/0035_admissions_student_lifecycle.py"
    )
    spec = importlib.util.spec_from_file_location("admissions_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    metadata = MetaData()
    Table("users", metadata, Column("id", Integer, primary_key=True))
    Table("institutions", metadata, Column("id", Integer, primary_key=True))
    Table(
        "institution_members",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("institution_id", Integer),
    )
    Table("institution_invites", metadata, Column("id", Integer, primary_key=True))
    Table("institution_batches", metadata, Column("id", Integer, primary_key=True))
    metadata.create_all(engine)
    expected = {
        "admission_programs",
        "admission_intakes",
        "admission_applications",
        "admission_documents",
        "admission_notes",
        "admission_tasks",
        "admission_stage_history",
        "campus_learner_profiles",
        "campus_learner_lifecycle_history",
    }
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert expected <= set(inspect(connection).get_table_names())
        migration.downgrade()
        assert not expected & set(inspect(connection).get_table_names())
        migration.upgrade()
        assert expected <= set(inspect(connection).get_table_names())
