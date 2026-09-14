from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
from PyPDF2 import PdfReader
import pytest
from sqlalchemy import create_engine, inspect

from app.models.campus_operations import (
    CampusAssessment,
    CampusAttendance,
    CampusBranding,
    CampusScore,
    CampusTerm,
)
from app.models.campus_pilot import (
    CampusEvent,
    CampusWhatsAppCampaign,
    CampusWhatsAppMessage,
    CampusWhatsAppWebhookEvent,
)
from app.models.institution import InstitutionMember
from app.models.whatsapp import WhatsAppContact
from app.services import campus_whatsapp


ROOT = "/api/v1/institutions"


@pytest.fixture
def pilot_campus(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="pilot-owner@example.org")
    teacher = make_user(role="instructor", email="pilot-teacher@example.org")
    student = make_user(email="pilot-student@example.org")
    other_student = make_user(email="pilot-other@example.org")
    as_user(owner)
    institution_id = client.post(
        ROOT,
        json={
            "name": "Sunrise College",
            "academic_year": "2026-27",
            "timezone": "Asia/Kolkata",
        },
    ).json()["id"]
    batch_id = client.post(
        f"{ROOT}/{institution_id}/batches",
        json={"name": "Science A", "academic_year": "2026-27"},
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
        json={"member_ids": [members[1].id]},
    )
    return SimpleNamespace(
        owner=owner,
        teacher=teacher,
        student=student,
        other_student=other_student,
        iid=institution_id,
        bid=batch_id,
        teacher_member=members[0],
        student_member=members[1],
        other_member=members[2],
    )


def test_onboarding_is_derived_and_dismissal_is_saved(pilot_campus, client, as_user):
    campus = pilot_campus
    root = f"{ROOT}/{campus.iid}/pilot/onboarding"
    result = client.get(root)
    assert result.status_code == 200
    body = result.json()
    assert body["total_steps"] == 8
    assert {step["key"] for step in body["steps"]} == {
        "profile",
        "branding",
        "batches",
        "staff",
        "students",
        "term",
        "timetable",
        "course",
    }
    assert body["completed_steps"] >= 4
    assert client.patch(root, json={"dismissed": True}).json()["dismissed"] is True
    as_user(campus.student)
    assert client.get(root).status_code == 403


def test_recurring_calendar_conflicts_and_batch_visibility(
    pilot_campus, client, as_user, db
):
    campus = pilot_campus
    root = f"{ROOT}/{campus.iid}/pilot/events"
    payload = {
        "title": "Physics lab",
        "kind": "class",
        "starts_at": "2030-01-07T09:00:00+05:30",
        "ends_at": "2030-01-07T10:00:00+05:30",
        "batch_id": campus.bid,
        "teacher_member_id": campus.teacher_member.id,
        "location": "Lab 1",
        "description": "Bring lab notebooks.",
        "recurrence": "weekly",
        "repeat_until": "2030-01-21",
    }
    created = client.post(root, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["created_count"] == 3
    assert db.query(CampusEvent).count() == 3
    conflict = {**payload, "title": "Chemistry lab", "recurrence": "none"}
    conflict.pop("repeat_until")
    assert client.post(root, json=conflict).status_code == 409
    as_user(campus.student)
    visible = client.get(
        root,
        params={
            "starts_after": "2030-01-01T00:00:00+00:00",
            "starts_before": "2030-02-01T00:00:00+00:00",
        },
    ).json()
    assert len(visible) == 3
    assert visible[0]["location"] == "Lab 1"
    as_user(campus.other_student)
    assert (
        client.get(
            root,
            params={
                "starts_after": "2030-01-01T00:00:00+00:00",
                "starts_before": "2030-02-01T00:00:00+00:00",
            },
        ).json()
        == []
    )


def test_announcements_reads_goals_and_notification_scope(
    pilot_campus, client, as_user
):
    campus = pilot_campus
    root = f"{ROOT}/{campus.iid}/pilot"
    campus_notice = client.post(
        root + "/announcements",
        json={"title": "Welcome week", "body": "Meet your mentors."},
    ).json()
    class_notice = client.post(
        root + "/announcements",
        json={
            "title": "Science lab",
            "body": "Bring your notebook.",
            "batch_id": campus.bid,
        },
    ).json()
    as_user(campus.student)
    assert {row["id"] for row in client.get(root + "/announcements").json()} == {
        campus_notice["id"],
        class_notice["id"],
    }
    read = client.post(root + f"/announcements/{class_notice['id']}/read").json()
    assert read["read_at"]
    assert (
        client.post(root + f"/announcements/{class_notice['id']}/read").status_code
        == 200
    )
    goal = client.post(
        root + "/goals",
        json={
            "title": "Finish the lab reflection",
            "target_date": (date.today() + timedelta(days=3)).isoformat(),
        },
    ).json()
    assert (
        client.patch(root + f"/goals/{goal['id']}", json={"progress": 60}).json()[
            "status"
        ]
        == "in_progress"
    )
    feed = client.get(root + "/notifications").json()
    assert any(item["id"] == f"goal:{goal['id']}" for item in feed)
    assert next(
        item for item in feed if item["id"] == f"announcement:{class_notice['id']}"
    )["read_at"]
    as_user(campus.other_student)
    ids = {item["id"] for item in client.get(root + "/notifications").json()}
    assert f"announcement:{class_notice['id']}" not in ids


def test_grading_policy_report_card_privacy_and_branded_pdf(
    pilot_campus, client, as_user, db
):
    campus = pilot_campus
    root = f"{ROOT}/{campus.iid}/pilot"
    term = CampusTerm(
        institution_id=campus.iid,
        name="Term 1",
        starts_on=date(2026, 7, 1),
        ends_on=date(2026, 12, 31),
    )
    db.add(term)
    db.flush()
    assessment = CampusAssessment(
        batch_id=campus.bid,
        term_id=term.id,
        title="Physics",
        max_score=100,
        due_on=date(2026, 9, 1),
        created_by=campus.owner.id,
    )
    db.add(assessment)
    db.flush()
    db.add_all(
        [
            CampusScore(
                assessment_id=assessment.id,
                member_id=campus.student_member.id,
                score=86,
                feedback="Strong reasoning.",
                graded_by=campus.owner.id,
            ),
            CampusAttendance(
                batch_id=campus.bid,
                member_id=campus.student_member.id,
                day=date(2026, 9, 1),
                status="present",
                recorded_by=campus.owner.id,
            ),
            CampusBranding(
                institution_id=campus.iid,
                title="Sunrise learning journey",
                subtitle="Curiosity belongs on every campus.",
            ),
        ]
    )
    db.commit()
    policy = {
        "bands": [
            {"label": "Distinction", "min_percent": 80},
            {"label": "Pass", "min_percent": 40},
            {"label": "Support", "min_percent": 0},
        ]
    }
    assert client.put(root + "/grading-policy", json=policy).status_code == 200
    report_url = root + f"/report-cards/{campus.student_member.id}"
    result = client.put(
        report_url + "/comment",
        json={"term_id": term.id, "overall_comment": "Excellent progress."},
    ).json()
    assert result["overall_percent"] == 86.0
    assert result["overall_grade"] == "Distinction"
    assert result["attendance_percent"] == 100.0
    pdf = client.get(report_url + ".pdf", params={"term_id": term.id})
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")
    text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages
    )
    assert "Sunrise learning journey" in text
    assert "Excellent progress" in text
    as_user(campus.student)
    assert client.get(report_url, params={"term_id": term.id}).status_code == 200
    as_user(campus.other_student)
    assert client.get(report_url, params={"term_id": term.id}).status_code == 404


def _signed(body, secret):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _meta_payload(*, messages=None, statuses=None):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messages": messages or [],
                            "statuses": statuses or [],
                        },
                    }
                ]
            }
        ],
    }


def test_whatsapp_opt_in_requires_a_signed_webhook(
    pilot_campus, client, as_user, db, monkeypatch
):
    campus = pilot_campus
    settings = campus_whatsapp.get_settings()
    monkeypatch.setattr(settings, "WHATSAPP_BUSINESS_PHONE", "")
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "")
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "")
    as_user(campus.student)
    result = client.post(
        f"{ROOT}/{campus.iid}/pilot/whatsapp/opt-in",
        json={"phone": "+919876543210"},
    )
    assert result.status_code == 503
    assert db.get(WhatsAppContact, campus.student.id) is None
    as_user(campus.owner)
    directory = client.get(f"{ROOT}/{campus.iid}/pilot/whatsapp/contacts").json()
    student = next(
        row for row in directory if row["member_id"] == campus.student_member.id
    )
    assert student["status"] == "not_started"
    assert student["phone"] is None


def test_whatsapp_requires_signed_inbound_consent_and_is_idempotent(
    pilot_campus, client, as_user, db, monkeypatch
):
    campus = pilot_campus
    settings = campus_whatsapp.get_settings()
    values = {
        "WHATSAPP_PHONE_NUMBER_ID": "phone-id",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "business-id",
        "WHATSAPP_BUSINESS_PHONE": "+919999999999",
        "WHATSAPP_ACCESS_TOKEN": "test-access-secret",
        "WHATSAPP_APP_SECRET": "test-app-secret",
        "WHATSAPP_VERIFY_TOKEN": "test-verify-secret",
        "WHATSAPP_API_VERSION": "v23.0",
        "WHATSAPP_APPROVED_TEMPLATES": "campus_announcement,assignment_due",
    }
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)

    verification = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-secret",
            "hub.challenge": "meta-challenge",
        },
    )
    assert verification.status_code == 200
    assert verification.text == "meta-challenge"
    assert (
        client.get(
            "/api/v1/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong"},
        ).status_code
        == 403
    )

    as_user(campus.student)
    root = f"{ROOT}/{campus.iid}/pilot/whatsapp"
    pending = client.post(root + "/opt-in", json={"phone": "+919876543210"})
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"
    contact = db.get(WhatsAppContact, campus.student.id)
    challenge = contact.challenge
    assert contact.consent_at is None
    status = client.get(root + "/status").json()
    assert status["configured"] is True
    assert status["opted_in"] is False
    assert status["join_url"].startswith("https://wa.me/")
    assert "test-access-secret" not in json.dumps(status)
    assert "test-app-secret" not in json.dumps(status)

    payload = _meta_payload(
        messages=[
            {
                "id": "wamid.optin-1",
                "from": "919876543210",
                "type": "text",
                "text": {"body": f"JOIN {challenge}"},
            }
        ]
    )
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"x-hub-signature-256": _signed(body, values["WHATSAPP_APP_SECRET"])}
    assert (
        client.post(
            "/api/v1/whatsapp/webhook",
            content=body,
            headers={"x-hub-signature-256": "sha256=invalid"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/whatsapp/webhook", content=body, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/whatsapp/webhook", content=body, headers=headers
        ).status_code
        == 200
    )
    db.expire_all()
    assert db.get(WhatsAppContact, campus.student.id).status == "confirmed"
    assert db.query(CampusWhatsAppWebhookEvent).count() == 1

    as_user(campus.owner)
    directory = client.get(root + "/contacts").json()
    student = next(
        row for row in directory if row["member_id"] == campus.student_member.id
    )
    assert student["phone"].endswith("3210")
    assert student["phone"] != "+919876543210"
    assert (
        client.post(
            root + "/campaigns",
            json={
                "request_key": "oversized-banner-1",
                "template": "campus_announcement",
                "language": "en",
                "parameters": [],
                "header_image_url": "https://example.org/" + "a" * 500,
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            root + "/campaigns",
            json={
                "request_key": "unsafe-template-1",
                "template": "unapproved",
                "language": "en",
                "parameters": [],
            },
        ).status_code
        == 422
    )
    monkeypatch.setattr(campus_whatsapp, "deliver_pending", lambda limit=100: None)
    command = {
        "request_key": "campus-welcome-001",
        "template": "campus_announcement",
        "language": "en",
        "parameters": ["Science students", "Lab starts Monday"],
    }
    campaign = client.post(root + "/campaigns", json=command)
    assert campaign.status_code == 201, campaign.text
    assert campaign.json()["recipient_count"] == 1
    assert campaign.json()["status"] == "queued"
    assert (
        client.post(root + "/campaigns", json=command).json()["id"]
        == campaign.json()["id"]
    )
    assert db.query(CampusWhatsAppCampaign).count() == 1
    assert db.query(CampusWhatsAppMessage).count() == 1


def test_whatsapp_delivery_does_not_resend_a_completed_message(
    pilot_campus, client, db, monkeypatch
):
    campus = pilot_campus
    settings = campus_whatsapp.get_settings()
    for name, value in {
        "WHATSAPP_PHONE_NUMBER_ID": "phone-id",
        "WHATSAPP_ACCESS_TOKEN": "token",
        "WHATSAPP_APP_SECRET": "signing-secret",
        "WHATSAPP_APPROVED_TEMPLATES": "campus_announcement",
    }.items():
        monkeypatch.setattr(settings, name, value)
    db.add(
        WhatsAppContact(
            user_id=campus.student.id,
            phone="+919876543210",
            status="confirmed",
            consent_at=datetime.now(timezone.utc),
        )
    )
    campaign = CampusWhatsAppCampaign(
        institution_id=campus.iid,
        request_key="direct-send-001",
        template="campus_announcement",
        language="en",
        parameters=["Hello"],
        batch_id=None,
        header_image_url="https://example.org/banner.png",
        created_by=campus.owner.id,
    )
    db.add(campaign)
    db.flush()
    message = CampusWhatsAppMessage(
        campaign_id=campaign.id,
        member_id=campus.student_member.id,
        phone="+919876543210",
        callback_key="callback-key-001",
        status="queued",
        attempts=0,
    )
    db.add(message)
    db.commit()

    @contextmanager
    def session():
        yield db

    class ProviderResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"messages": [{"id": "wamid.sent-1"}]}

    calls = []

    def provider_post(url, **kwargs):
        calls.append((url, kwargs))
        return ProviderResponse()

    monkeypatch.setattr(campus_whatsapp, "SessionLocal", session)
    monkeypatch.setattr(campus_whatsapp.httpx, "post", provider_post)
    campus_whatsapp.deliver(message.id)
    campus_whatsapp.deliver(message.id)
    db.refresh(message)
    assert message.status == "sent"
    assert message.provider_id == "wamid.sent-1"
    assert len(calls) == 1
    assert calls[0][1]["json"]["type"] == "template"

    status_payload = _meta_payload(
        statuses=[{"id": "wamid.sent-1", "status": "read", "timestamp": "200"}]
    )
    body = json.dumps(status_payload, separators=(",", ":")).encode()
    headers = {"x-hub-signature-256": _signed(body, "signing-secret")}
    assert (
        client.post(
            "/api/v1/whatsapp/webhook", content=body, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/whatsapp/webhook", content=body, headers=headers
        ).status_code
        == 200
    )
    db.expire_all()
    assert db.get(CampusWhatsAppMessage, message.id).status == "read"


def test_campus_pilot_migration_round_trip():
    path = Path(__file__).parents[1] / "alembic/versions/0033_campus_pilot.py"
    spec = importlib.util.spec_from_file_location("campus_pilot_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert len(inspect(connection).get_table_names()) == 11
        module.downgrade()
        assert inspect(connection).get_table_names() == []
