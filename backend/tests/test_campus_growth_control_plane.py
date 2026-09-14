import io
import zipfile

from app.models.campus_growth import CampusLead
from app.models.institution import (
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionMember,
)


ROOT = "/api/v1/institutions"


def make_institution(client, as_user, user, name="Northstar College"):
    as_user(user)
    response = client.post(
        ROOT,
        json={"name": name, "kind": "college", "academic_year": "2026-27"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_public_campus_lead_is_consented_idempotent_and_private(
    client, db, as_user, make_user
):
    plans = client.get("/api/v1/campus-growth/plans")
    assert plans.status_code == 200
    assert [plan["key"] for plan in plans.json()["plans"]] == [
        "starter",
        "campus",
        "enterprise",
    ]
    payload = {
        "contact_name": "Asha Raman",
        "work_email": "asha@example.edu",
        "phone": "+91 98765 43210",
        "institution_name": "Example School",
        "institution_kind": "school",
        "learner_count": "500-1999",
        "interest": "demo",
        "message": "Admissions and fees",
        "source": "campus-page",
        "attribution": {"utm_source": "search", "unsafe": "removed"},
        "consent": True,
        "website": "",
    }
    first = client.post("/api/v1/campus-growth/leads", json=payload)
    second = client.post("/api/v1/campus-growth/leads", json=payload)
    assert first.status_code == second.status_code == 202
    assert first.json()["reference"] == second.json()["reference"]
    assert "work_email" not in first.json()
    assert db.query(CampusLead).count() == 1
    assert db.query(CampusLead).one().attribution == {"utm_source": "search"}
    rejected = client.post(
        "/api/v1/campus-growth/leads", json={**payload, "consent": False}
    )
    assert rejected.status_code == 422

    admin = make_user(role="admin")
    as_user(admin)
    listed = client.get("/api/v1/campus-growth/leads")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["work_email"] == "asha@example.edu"


def test_control_plane_scoping_secret_redaction_and_privacy_workflow(
    client, db, as_user, make_user
):
    owner = make_user(role="instructor")
    outsider = make_user(role="instructor")
    institution_id = make_institution(client, as_user, owner)
    root = f"{ROOT}/{institution_id}"

    domain = client.post(
        root + "/control-plane/domains", json={"hostname": "learn.example.edu"}
    )
    assert domain.status_code == 201, domain.text
    assert domain.json()["verification"]["record_type"] == "TXT"
    assert domain.json()["status"] == "pending"

    integration = client.put(
        root + "/control-plane/integrations/oidc",
        json={
            "kind": "oidc",
            "display_name": "Example Identity",
            "status": "ready",
            "config": {"issuer": "https://id.example.edu"},
            "secret_reference": "vault://campus/example-oidc",
        },
    )
    assert integration.status_code == 200, integration.text
    assert integration.json()["has_secret_reference"] is True
    assert "secret_reference" not in integration.json()

    request = client.post(
        root + "/privacy/requests",
        json={"kind": "export", "detail": "A copy of my campus records"},
    )
    assert request.status_code == 201
    assert request.json()["status"] == "submitted"

    as_user(outsider)
    assert client.get(root + "/control-plane").status_code == 404
    assert client.get(root + "/privacy/requests").status_code == 404


def test_oneroster_export_contains_only_the_selected_institution(
    client, db, as_user, make_user
):
    owner = make_user(role="instructor")
    student = make_user(email="learner@example.edu")
    outsider = make_user(email="outside@example.edu")
    institution_id = make_institution(client, as_user, owner)
    member = InstitutionMember(
        institution_id=institution_id,
        user_id=student.id,
        role="student",
        status="active",
        department="Grade 8",
    )
    batch = InstitutionBatch(
        institution_id=institution_id,
        name="Grade 8 A",
        department="Grade 8",
        academic_year="2026-27",
    )
    db.add_all([member, batch])
    db.flush()
    db.add(InstitutionBatchMember(batch_id=batch.id, member_id=member.id))
    db.commit()
    response = client.get(
        f"{ROOT}/{institution_id}/integrations/oneroster/export"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert {
            "manifest.csv",
            "orgs.csv",
            "users.csv",
            "classes.csv",
            "courses.csv",
            "enrollments.csv",
            "academicSessions.csv",
        } <= set(archive.namelist())
        users = archive.read("users.csv").decode("utf-8-sig")
        assert "learner@example.edu" in users
        assert "outside@example.edu" not in users


def test_every_response_gets_a_safe_request_id(client):
    response = client.get(
        "/api/v1/campus-growth/plans", headers={"X-Request-ID": "test-request-123"}
    )
    assert response.headers["X-Request-ID"] == "test-request-123"
    generated = client.get(
        "/api/v1/campus-growth/plans", headers={"X-Request-ID": "bad id"}
    )
    assert len(generated.headers["X-Request-ID"]) == 32

