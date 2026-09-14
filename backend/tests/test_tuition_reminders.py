from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, inspect

from app.models.campus_operations import ParentLinkRequest
from app.models.campus_pilot import CampusWhatsAppCampaign, CampusWhatsAppMessage
from app.models.institution import Institution, InstitutionMember
from app.models.tuition_reminders import TuitionReminder
from app.models.whatsapp import WhatsAppContact
from app.services import campus_worker
from app.services import tuition_reminders as svc


ROOT = "/api/v1/institutions"


@pytest.fixture
def fee_campus(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="rem-owner@example.org")
    as_user(owner)
    institution_id = client.post(
        ROOT, json={"name": "Reminder College", "academic_year": "2026-27"}
    ).json()["id"]
    student = make_user(role="student", email="rem-student@example.org")
    teacher = make_user(role="instructor", email="rem-teacher@example.org")
    parent = make_user(role="parent", email="rem-parent@example.org")
    stranger_parent = make_user(role="parent", email="rem-stranger@example.org")
    members = []
    for person, role in ((student, "student"), (teacher, "teacher")):
        member = InstitutionMember(
            institution_id=institution_id, user_id=person.id, role=role, status="active", department=""
        )
        db.add(member)
        db.flush()
        members.append(member)
    db.add(ParentLinkRequest(parent_user_id=parent.id, student_user_id=student.id, status="approved"))
    db.add(ParentLinkRequest(parent_user_id=stranger_parent.id, student_user_id=student.id, status="pending"))
    db.commit()
    return SimpleNamespace(
        owner=owner,
        student=student,
        teacher=teacher,
        parent=parent,
        stranger_parent=stranger_parent,
        iid=institution_id,
        student_member=members[0],
        teacher_member=members[1],
    )


def _plan_and_assignment(client, campus, today):
    root = f"{ROOT}/{campus.iid}/fees"
    plan = client.post(
        root + "/plans",
        json={
            "name": "Annual tuition",
            "academic_year": "2026-27",
            "currency": "inr",
            "description": "",
            "components": [{"code": "tuition", "name": "Tuition", "amount": "3000.00"}],
            "installments": [
                {"name": "Overdue two weeks", "due_on": str(today - timedelta(days=14)), "amount": "1000"},
                {"name": "Due today", "due_on": str(today), "amount": "1000"},
                {"name": "Due in a week", "due_on": str(today + timedelta(days=7)), "amount": "1000"},
            ],
        },
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]
    assert client.post(f"{root}/plans/{plan_id}/publish").status_code == 200
    assignment = client.post(
        f"{root}/assignments",
        json={"student_member_id": campus.student_member.id, "plan_id": plan_id, "note": ""},
    )
    assert assignment.status_code == 201, assignment.text
    return assignment.json()["id"]


def _enable(client, campus, **overrides):
    body = {
        "enabled": True,
        "days_before": [7, 1],
        "overdue_every_days": 7,
        "overdue_max": 3,
        "send_hour": 0,
        "channels": ["whatsapp", "email"],
        "whatsapp_template": "fee_reminder",
        "whatsapp_language": "en",
    }
    body.update(overrides)
    saved = client.put(f"{ROOT}/{campus.iid}/fees/reminders/policy", json=body)
    assert saved.status_code == 200, saved.text
    return saved.json()


def _rows(db, campus, **filters):
    return db.query(TuitionReminder).filter_by(institution_id=campus.iid, **filters).all()


def test_policy_defaults_validation_and_access(fee_campus, client, as_user):
    campus = fee_campus
    url = f"{ROOT}/{campus.iid}/fees/reminders/policy"
    defaults = client.get(url).json()
    assert defaults["enabled"] is False and defaults["days_before"] == [7, 1]
    assert client.put(url, json={"enabled": True, "days_before": [3, 3]}).status_code == 422
    assert client.put(url, json={"enabled": True, "days_before": [90]}).status_code == 422
    assert client.put(url, json={"enabled": True, "channels": []}).status_code == 422
    assert client.put(url, json={"enabled": True, "whatsapp_template": "bad name!"}).status_code == 422
    saved = _enable(client, campus, days_before=[1, 7, 3], send_hour=8)
    assert saved["days_before"] == [7, 3, 1] and saved["send_hour"] == 8
    assert client.get(url).json()["enabled"] is True
    as_user(campus.teacher)
    assert client.get(url).status_code == 403
    as_user(campus.student)
    assert client.get(url).status_code == 403
    as_user(campus.parent)
    assert client.get(url).status_code == 404


def test_staging_is_idempotent_and_records_reasons(fee_campus, client, db, monkeypatch):
    campus = fee_campus
    today = date.today()
    _plan_and_assignment(client, campus, today)
    _enable(client, campus)
    monkeypatch.setattr(svc, "whatsapp_ready", lambda: False)
    monkeypatch.setattr(svc, "mail_ready", lambda: False)
    first = client.post(f"{ROOT}/{campus.iid}/fees/reminders/run-now").json()
    # Three installments hit a stage today (before:7, due:0, overdue:2) for two
    # recipients (student + approved guardian); with nothing configured each
    # channel gets its own skipped row so the log explains both gaps.
    assert first["staged"] == 12 and first["skipped"] == 12 and first["sent"] == 0
    stages = {row.stage for row in _rows(db, campus)}
    assert stages == {"before:7", "due:0", "overdue:2"}
    recipients = {row.recipient_user_id for row in _rows(db, campus)}
    assert recipients == {campus.student.id, campus.parent.id}
    reasons = {row.skip_reason for row in _rows(db, campus)}
    assert reasons == {"whatsapp_not_configured", "email_not_configured"}
    second = client.post(f"{ROOT}/{campus.iid}/fees/reminders/run-now").json()
    assert second["staged"] == 0
    log = client.get(f"{ROOT}/{campus.iid}/fees/reminders", params={"status": "skipped"}).json()
    assert len(log["items"]) == 12 and log["next_after_id"] is None


def test_disabled_policy_and_send_hour_gate(fee_campus, client, db, monkeypatch):
    campus = fee_campus
    today = date.today()
    _plan_and_assignment(client, campus, today)
    monkeypatch.setattr(svc, "whatsapp_ready", lambda: False)
    monkeypatch.setattr(svc, "mail_ready", lambda: True)
    institution = db.get(Institution, campus.iid)
    policy = svc.TuitionReminderPolicy(institution_id=campus.iid, **svc.DEFAULT_POLICY)
    assert svc.stage_institution(db, institution, policy, today=today) == []
    policy.enabled = True
    policy.send_hour = 23
    monkeypatch.setattr(svc, "_local_now", lambda inst: datetime(2026, 9, 11, 8, 0, tzinfo=timezone.utc))
    assert svc.stage_institution(db, institution, policy, today=today) == []
    policy.send_hour = 8
    created = svc.stage_institution(db, institution, policy, today=today)
    assert len(created) == 6 and all(row.status == "queued" and row.channel == "email" for row in created)


def test_email_delivery_success_and_failure(fee_campus, client, db, monkeypatch):
    campus = fee_campus
    today = date.today()
    _plan_and_assignment(client, campus, today)
    _enable(client, campus, channels=["email"])
    monkeypatch.setattr(svc, "whatsapp_ready", lambda: False)
    monkeypatch.setattr(svc, "mail_ready", lambda: True)
    sent_to = []
    monkeypatch.setattr(
        svc.EmailService,
        "_send_smtp_email",
        staticmethod(lambda to, subject, text, html=None: sent_to.append((to, subject)) or True),
    )
    result = client.post(f"{ROOT}/{campus.iid}/fees/reminders/run-now").json()
    assert result == {"staged": 6, "sent": 6, "failed": 0, "skipped": 0}
    assert {to for to, _ in sent_to} == {"rem-student@example.org", "rem-parent@example.org"}
    assert any("Overdue" in subject for _, subject in sent_to)
    assert all(row.status == "sent" and row.sent_at for row in _rows(db, campus))
    # A failing SMTP call is recorded as failed, never as sent.
    monkeypatch.setattr(svc.EmailService, "_send_smtp_email", staticmethod(lambda *a, **k: False))
    manual = client.post(f"{ROOT}/{campus.iid}/fees/assignments/1/remind")
    assert manual.status_code == 201, manual.text
    assert {row["status"] for row in manual.json()} == {"failed"}
    assert client.post(f"{ROOT}/{campus.iid}/fees/assignments/1/remind").status_code == 409
    failed_id = manual.json()[0]["id"]
    monkeypatch.setattr(svc.EmailService, "_send_smtp_email", staticmethod(lambda *a, **k: True))
    retried = client.post(f"{ROOT}/{campus.iid}/fees/reminders/{failed_id}/retry")
    assert retried.status_code == 200 and retried.json()["status"] == "sent"
    assert client.post(f"{ROOT}/{campus.iid}/fees/reminders/{failed_id}/retry").status_code == 409


def test_whatsapp_path_creates_campaign_and_falls_back_without_consent(fee_campus, client, db, monkeypatch):
    campus = fee_campus
    today = date.today()
    _plan_and_assignment(client, campus, today)
    _enable(client, campus, days_before=[7], overdue_max=0)
    monkeypatch.setattr(svc, "whatsapp_ready", lambda: True)
    monkeypatch.setattr(svc, "mail_ready", lambda: True)
    monkeypatch.setattr(svc.campus_whatsapp, "approved_templates", lambda: ["fee_reminder"])
    monkeypatch.setattr(svc.EmailService, "_send_smtp_email", staticmethod(lambda *a, **k: True))
    db.add(WhatsAppContact(user_id=campus.student.id, phone="+919876500001", status="confirmed"))
    db.commit()
    result = client.post(f"{ROOT}/{campus.iid}/fees/reminders/run-now").json()
    # Two stages today (before:7, due:0) x two recipients.
    assert result["staged"] == 4 and result["failed"] == 0
    student_rows = _rows(db, campus, recipient_user_id=campus.student.id)
    assert {row.channel for row in student_rows} == {"whatsapp"}
    assert all(row.whatsapp_message_id for row in student_rows)
    campaigns = db.query(CampusWhatsAppCampaign).filter_by(institution_id=campus.iid).all()
    assert len(campaigns) == 2 and all(c.template == "fee_reminder" for c in campaigns)
    messages = db.query(CampusWhatsAppMessage).all()
    assert {m.member_id for m in messages} == {campus.student_member.id}
    assert all(m.phone == "+919876500001" and m.status == "queued" for m in messages)
    parent_rows = _rows(db, campus, recipient_user_id=campus.parent.id)
    assert {row.channel for row in parent_rows} == {"email"} and {row.status for row in parent_rows} == {"sent"}
    # The log mirrors the provider status of the WhatsApp message.
    messages[0].status = "delivered"
    db.commit()
    listed = client.get(f"{ROOT}/{campus.iid}/fees/reminders").json()["items"]
    mirrored = next(row for row in listed if row["id"] == student_rows[0].id or row["id"] == student_rows[1].id)
    assert mirrored["status"] in ("sent", "queued")
    assert any(row["status"] == "sent" and row["channel"] == "whatsapp" for row in listed)


def test_receipt_notice_queues_on_payment(fee_campus, client, db, monkeypatch):
    campus = fee_campus
    today = date.today()
    assignment_id = _plan_and_assignment(client, campus, today)
    _enable(client, campus, channels=["email"])
    monkeypatch.setattr(svc, "whatsapp_ready", lambda: False)
    monkeypatch.setattr(svc, "mail_ready", lambda: True)
    monkeypatch.setattr(svc.EmailService, "_send_smtp_email", staticmethod(lambda *a, **k: True))
    paid = client.post(
        f"{ROOT}/{campus.iid}/fees/assignments/{assignment_id}/payments",
        json={"amount": "500.00", "method": "upi", "reference": "", "note": ""},
        headers={"Idempotency-Key": "rem-pay-0001"},
    )
    assert paid.status_code == 201, paid.text
    receipts = _rows(db, campus, kind="receipt")
    assert {row.recipient_user_id for row in receipts} == {campus.student.id, campus.parent.id}
    assert all(row.status == "queued" and row.receipt_id for row in receipts)
    sent, failed = svc.deliver_pending(db, campus.iid)
    assert (sent, failed) == (2, 0)
    replay = client.post(
        f"{ROOT}/{campus.iid}/fees/assignments/{assignment_id}/payments",
        json={"amount": "500.00", "method": "upi", "reference": "", "note": ""},
        headers={"Idempotency-Key": "rem-pay-0001"},
    )
    assert replay.status_code in (200, 201)
    assert len(_rows(db, campus, kind="receipt")) == 2


def test_worker_tick_runs_reminders(fee_campus, client, db, monkeypatch, TestingSessionLocal):
    campus = fee_campus
    monkeypatch.setattr(svc, "SessionLocal", TestingSessionLocal)
    today = date.today()
    _plan_and_assignment(client, campus, today)
    _enable(client, campus, channels=["email"], send_hour=0)
    monkeypatch.setattr(svc, "whatsapp_ready", lambda: False)
    monkeypatch.setattr(svc, "mail_ready", lambda: True)
    monkeypatch.setattr(svc.EmailService, "_send_smtp_email", staticmethod(lambda *a, **k: True))
    monkeypatch.setattr(campus_worker, "deliver_pending", lambda: None)
    monkeypatch.setattr(campus_worker, "deliver_whatsapp_pending", lambda: None)
    monkeypatch.setattr(campus_worker, "reconcile", lambda db: None)
    assert campus_worker.tick() is True
    db.expire_all()
    rows = _rows(db, campus)
    assert len(rows) == 6 and {row.status for row in rows} == {"sent"}


def test_tuition_reminders_migration_round_trip():
    versions = Path(__file__).parents[1] / "alembic/versions"
    spec = importlib.util.spec_from_file_location("m0039", versions / "0039_tuition_reminders.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for name in (
            "institutions",
            "users",
            "tuition_fee_assignments",
            "tuition_installments",
            "tuition_receipts",
            "institution_members",
            "campus_whatsapp_messages",
        ):
            connection.exec_driver_sql(f"CREATE TABLE {name} (id INTEGER PRIMARY KEY)")
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        tables = set(inspect(connection).get_table_names())
        assert {"tuition_reminder_policies", "tuition_reminders"} <= tables
        module.downgrade()
        assert not set(inspect(connection).get_table_names()) & {"tuition_reminder_policies", "tuition_reminders"}
