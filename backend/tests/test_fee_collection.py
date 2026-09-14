"""Fee collection: cash desk verification, receipts and invoices, online orders."""

from datetime import date
import hashlib
import hmac
import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from app.main import app
from app.models.campus_operations import ParentLinkRequest
from app.models.institution import InstitutionAudit, InstitutionMember
from app.models.tuition import TuitionPayment
from app.models.tuition_collection import TuitionOnlineOrder
from app.routers.tuition import router as tuition_router
from tests.test_tuition_finance import (  # noqa: F401  (fixture re-export)
    ROOT,
    create_assignment,
    create_published_plan,
    tuition_campus,
)


if not any(getattr(route, "path", "").endswith("/fees/summary") for route in app.routes):
    app.include_router(tuition_router, prefix=ROOT, tags=["Tuition fees"])
if not any(getattr(route, "path", "").endswith("/fees/cash") for route in app.routes):
    from app.routers.tuition_collection import router as collection_router

    app.include_router(collection_router, prefix=ROOT, tags=["Tuition collection"])


def _link_parent(db, campus):
    db.add(
        ParentLinkRequest(
            parent_user_id=campus.parent.id,
            student_user_id=campus.student.id,
            status="approved",
        )
    )
    db.commit()


def _owner_member(db, campus):
    return (
        db.query(InstitutionMember)
        .filter_by(institution_id=campus.institution_id, user_id=campus.owner.id)
        .one()
    )


def _pay(client, campus, assignment_id, key, **body):
    return client.post(
        f"{ROOT}/{campus.institution_id}/fees/assignments/{assignment_id}/payments",
        json=body,
        headers={"Idempotency-Key": key},
    )


class FakeClient:
    def __init__(self):
        self.created = []
        self.payments = {}

    class _Order:
        def __init__(self, outer):
            self.outer = outer

        def create(self, payload):
            self.outer.created.append(payload)
            return {"id": f"order_{len(self.outer.created)}", "amount": payload["amount"], "currency": "INR"}

        def payments(self, order_id):
            return {"items": [p for p in self.outer.payments.values() if p["order_id"] == order_id]}

    class _Payment:
        def __init__(self, outer):
            self.outer = outer

        def fetch(self, payment_id):
            return self.outer.payments[payment_id]

    @property
    def order(self):
        return FakeClient._Order(self)

    @property
    def payment(self):
        return FakeClient._Payment(self)


def _sign(order_id, payment_id, secret="secret"):
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


@pytest.fixture
def gateway(monkeypatch):
    from app.services import tuition_collection as tc

    fake = FakeClient()
    monkeypatch.setattr(tc, "_creds", lambda: ("rzp_test", "secret"))
    monkeypatch.setattr(tc, "_client", lambda: fake)
    return fake


# ------------------------------------------------------------------ Task 1


def test_migration_0043_round_trip(tmp_path):
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0043_fee_collection.py"
    spec = importlib.util.spec_from_file_location("m0043", path)
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)
    assert (migration.revision, migration.down_revision) == ("0043", "0042")

    engine = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    metadata = sa.MetaData()
    sa.Table("institutions", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("users", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("tuition_fee_assignments", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("tuition_installments", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table(
        "tuition_payments",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer()),
        sa.Column("method", sa.String(30)),
        sa.Column("recorded_by", sa.Integer()),
        sa.Column("paid_at", sa.DateTime()),
    )
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO tuition_payments (id, institution_id, method, recorded_by) "
                "VALUES (1, 1, 'cash', 7), (2, 1, 'upi', 7)"
            )
        )
        migration.op = Operations(MigrationContext.configure(conn))
        migration.upgrade()
        cols = {c["name"] for c in inspect(conn).get_columns("tuition_payments")}
        assert {"received_by", "verification_status", "verified_by", "verified_at", "verification_note"} <= cols
        rows = dict(conn.execute(sa.text("SELECT id, verification_status FROM tuition_payments")).all())
        assert rows == {1: "verified", 2: "not_required"}
        received = dict(conn.execute(sa.text("SELECT id, received_by FROM tuition_payments")).all())
        assert received == {1: 7, 2: None}
        assert {"tuition_invoices", "tuition_online_orders"} <= set(inspect(conn).get_table_names())
        migration.downgrade()
        assert "tuition_invoices" not in inspect(conn).get_table_names()
        cols = {c["name"] for c in inspect(conn).get_columns("tuition_payments")}
        assert "verification_status" not in cols and "received_by" not in cols


# ------------------------------------------------------------------ Task 2


def test_cash_requires_receiver_and_sets_pending(client, db, as_user, tuition_campus):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    aid = assignment["id"]

    missing = _pay(client, campus, aid, "cash-no-receiver", amount="100", method="cash")
    assert missing.status_code == 422, missing.text

    teacher_receiver = _pay(
        client, campus, aid, "cash-teacher", amount="100", method="cash", received_by_member_id=campus.teacher_member.id
    )
    assert teacher_receiver.status_code == 201, teacher_receiver.text
    payment = teacher_receiver.json()["payment"]
    assert payment["verification"]["status"] == "pending"
    assert payment["received_by"]["id"] == campus.teacher.id

    student_receiver = _pay(
        client, campus, aid, "cash-student", amount="50", method="cash", received_by_member_id=campus.student_member.id
    )
    assert student_receiver.status_code == 404

    card = _pay(client, campus, aid, "card-0001", amount="100", method="card")
    assert card.status_code == 201, card.text
    assert card.json()["payment"]["verification"]["status"] == "not_required"
    assert card.json()["payment"]["received_by"] is None

    # replay with the same key returns the same payment, receiver included
    replay = _pay(
        client, campus, aid, "cash-teacher", amount="100", method="cash", received_by_member_id=campus.teacher_member.id
    )
    assert replay.status_code == 201 and replay.json()["replayed"] is True
    assert replay.json()["payment"]["id"] == payment["id"]


# ------------------------------------------------------------------ Task 3


def test_verify_rules_and_cash_desk(client, db, as_user, make_user, tuition_campus):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    admin = make_user(role="instructor", email="fee-admin@example.org")
    db.add(InstitutionMember(institution_id=campus.institution_id, user_id=admin.id, role="admin", status="active", department=""))
    db.commit()

    paid = _pay(
        client, campus, assignment["id"], "cash-0001", amount="300", method="cash", received_by_member_id=_owner_member(db, campus).id
    ).json()["payment"]
    # the receiver cannot verify their own entry while another manager exists
    own = client.post(f"{fees}/payments/{paid['id']}/verify", json={"note": "counted"})
    assert own.status_code == 409, own.text
    as_user(campus.teacher)
    assert client.post(f"{fees}/payments/{paid['id']}/verify", json={}).status_code == 403
    as_user(admin)
    ok = client.post(f"{fees}/payments/{paid['id']}/verify", json={"note": "counted 300"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["verification"]["status"] == "verified"
    assert ok.json()["verification"]["verified_by"]["id"] == admin.id
    assert ok.json()["verification"]["note"] == "counted 300"
    assert client.post(f"{fees}/payments/{paid['id']}/verify", json={}).status_code == 409
    assert client.post(f"{fees}/payments/999999/verify", json={}).status_code == 404

    desk = client.get(f"{fees}/cash", params={"day": date.today().isoformat()})
    assert desk.status_code == 200, desk.text
    body = desk.json()
    assert body["verified_total"] == 300 and body["pending_total"] == 0 and body["pending_count"] == 0
    assert body["receivers"][0]["id"] == campus.owner.id and body["receivers"][0]["total"] == 300
    assert body["rows"][0]["verification"]["status"] == "verified"
    assert body["rows"][0]["receipt_number"].startswith("TF-")

    csv = client.get(f"{fees}/cash/csv", params={"day": date.today().isoformat()})
    assert csv.status_code == 200, csv.text
    assert "attachment" in csv.headers["content-disposition"]
    assert "Receipt,Student" in csv.text and "300.00" in csv.text

    as_user(campus.teacher)
    assert client.get(f"{fees}/cash", params={"day": date.today().isoformat()}).status_code == 403


def test_sole_manager_can_self_verify(client, db, as_user, tuition_campus):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    paid = _pay(
        client, campus, assignment["id"], "cheque-0001", amount="100", method="cheque", reference="CHQ 1",
        received_by_member_id=_owner_member(db, campus).id,
    ).json()["payment"]
    ok = client.post(f"{fees}/payments/{paid['id']}/verify", json={"note": "sole"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["verification"]["status"] == "verified"
    assert db.query(InstitutionAudit).filter(InstitutionAudit.detail.contains("self_verified_sole_manager")).count() == 1


def test_today_shows_cash_card(client, db, as_user, tuition_campus):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    _pay(
        client, campus, assignment["id"], "cash-today-1", amount="250", method="cash", received_by_member_id=_owner_member(db, campus).id
    )
    today = client.get(f"{ROOT}/{campus.institution_id}/today")
    assert today.status_code == 200, today.text
    card = next(a for a in today.json()["actions"] if a["id"] == "system-cash-verification")
    assert "1 cash payment" in card["title"] and "250" in card["detail"]


# ------------------------------------------------------------------ Task 4


def test_receipt_pdf_access(client, db, as_user, tuition_campus):
    campus = tuition_campus
    _link_parent(db, campus)
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    paid = _pay(
        client, campus, assignment["id"], "pdf-cash-1", amount="300", method="cash", received_by_member_id=_owner_member(db, campus).id
    ).json()["payment"]
    url = f"{fees}/receipts/{paid['receipt']['id']}/pdf"
    for person in (campus.owner, campus.student, campus.parent):
        as_user(person)
        response = client.get(url)
        assert response.status_code == 200, (person.user_email, response.text)
        assert response.content.startswith(b"%PDF")
        assert response.headers["content-type"].startswith("application/pdf")
    as_user(campus.stranger_parent)
    assert client.get(url).status_code == 404


def test_invoices(client, db, as_user, tuition_campus):
    campus = tuition_campus
    _link_parent(db, campus)
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    first = assignment["installments"][0]["id"]

    one = client.post(f"{fees}/assignments/{assignment['id']}/invoices", json={"installment_id": first})
    assert one.status_code == 201, one.text
    assert one.json()["amount"] == 1000 and one.json()["invoice_number"].startswith("TI-")
    assert one.json()["status"] == "open"

    as_user(campus.parent)
    whole = client.post(f"{fees}/assignments/{assignment['id']}/invoices", json={})
    assert whole.status_code == 201, whole.text
    assert whole.json()["amount"] == 3000 and len(whole.json()["lines"]) == 3
    pdf = client.get(f"{fees}/invoices/{whole.json()['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    listed = client.get(f"{fees}/assignments/{assignment['id']}/invoices")
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()["items"]] == [whole.json()["id"], one.json()["id"]]

    as_user(campus.owner)
    _pay(client, campus, assignment["id"], "invoice-pay-1", amount="1000", method="upi")
    again = client.post(f"{fees}/assignments/{assignment['id']}/invoices", json={"installment_id": first})
    assert again.status_code == 422, again.text
    assert client.get(f"{fees}/invoices/{one.json()['id']}").json()["status"] == "settled"
    assert client.get(f"{fees}/invoices/{whole.json()['id']}").json()["status"] == "open"

    as_user(campus.stranger_parent)
    assert client.get(f"{fees}/invoices/{one.json()['id']}").status_code == 404
    assert client.post(f"{fees}/assignments/{assignment['id']}/invoices", json={}).status_code == 404


# ------------------------------------------------------------------ Task 5


def test_online_order_503_when_unconfigured(client, db, as_user, tuition_campus, monkeypatch):
    from app.services import tuition_collection as tc

    monkeypatch.setattr(tc, "_creds", lambda: ("", ""))
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    assert client.get(f"{fees}/online/status").json() == {"ready": False}
    as_user(campus.student)
    response = client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={})
    assert response.status_code == 503, response.text
    assert "not set up" in response.json()["detail"]


def test_online_order_create_verify_replay(client, db, as_user, tuition_campus, gateway):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    first = assignment["installments"][0]
    assert client.get(f"{fees}/online/status").json() == {"ready": True}

    as_user(campus.student)
    too_much = client.post(
        f"{fees}/assignments/{assignment['id']}/online-orders", json={"installment_id": first["id"], "amount": "1500"}
    )
    assert too_much.status_code == 422, too_much.text
    created = client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={"installment_id": first["id"]})
    assert created.status_code == 201, created.text
    checkout = created.json()["checkout"]
    order = created.json()["order"]
    assert checkout["amount_paise"] == 100000 and checkout["key"] == "rzp_test" and checkout["order_id"] == "order_1"
    assert gateway.created[0]["notes"]["tuition_order_id"] == str(order["id"])

    gateway.payments["pay_1"] = {
        "id": "pay_1", "order_id": "order_1", "status": "captured", "amount": 100000, "currency": "INR", "amount_refunded": 0,
    }
    bad = client.post(
        f"{fees}/online-orders/{order['id']}/verify",
        json={"razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1", "razorpay_signature": "nope"},
    )
    assert bad.status_code == 400, bad.text
    good = {"razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1", "razorpay_signature": _sign("order_1", "pay_1")}
    ok = client.post(f"{fees}/online-orders/{order['id']}/verify", json=good)
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "paid"
    assert ok.json()["payment"]["method"] == "online" and ok.json()["payment"]["reference"] == "pay_1"
    assert ok.json()["payment"]["verification"]["status"] == "not_required"

    again = client.post(f"{fees}/online-orders/{order['id']}/verify", json=good)
    assert again.status_code == 200 and again.json()["payment"]["id"] == ok.json()["payment"]["id"]
    assert db.query(TuitionPayment).filter_by(method="online").count() == 1

    me = client.get(f"{fees}/me").json()
    assert me["assignments"][0]["installments"][0]["status"] == "paid"
    assert me["assignments"][0]["payments"][0]["receipt"]["receipt_number"].startswith("TF-")

    as_user(campus.stranger_parent)
    assert client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={}).status_code == 404
    assert client.post(f"{fees}/online-orders/{order['id']}/verify", json=good).status_code == 404


def test_webhook_capture_and_excess(client, db, as_user, tuition_campus, gateway):
    from app.models.webhook_event import WebhookEvent, WebhookEventStatus
    from app.services.webhook_processor import process_webhook_event

    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"

    as_user(campus.student)
    order = client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={}).json()["order"]
    assert order["amount"] == 3000
    as_user(campus.owner)
    _pay(client, campus, assignment["id"], "counter-first", amount="2500", method="upi")

    entity = {
        "id": "pay_w", "order_id": "order_1", "status": "captured", "amount": 300000, "currency": "INR",
        "amount_refunded": 0, "notes": {"tuition_order_id": str(order["id"])},
    }
    event = WebhookEvent(
        event_id="evt_tuition_1", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": entity}}}, signature_valid=True,
    )
    db.add(event)
    db.commit()
    process_webhook_event(db, event)
    db.commit()
    assert event.status == WebhookEventStatus.PROCESSED, event.last_error

    row = db.get(TuitionOnlineOrder, order["id"])
    db.refresh(row)
    assert row.status == "paid_excess" and float(row.excess_amount) == 2500
    assert row.gateway_payment_id == "pay_w" and row.payment_id is not None
    posted = db.get(TuitionPayment, row.payment_id)
    assert float(posted.amount) == 500 and posted.method == "online"

    today = client.get(f"{ROOT}/{campus.institution_id}/today").json()
    assert any(a["id"] == "system-online-excess" for a in today["actions"])
    desk = client.get(f"{fees}/cash", params={"day": date.today().isoformat()}).json()
    assert desk["excess_orders"][0]["excess_amount"] == 2500
    assert desk["excess_orders"][0]["gateway_payment_id"] == "pay_w"

    # replaying the same webhook is a no-op
    process_webhook_event(db, event)
    db.commit()
    assert db.query(TuitionPayment).filter_by(method="online").count() == 1
