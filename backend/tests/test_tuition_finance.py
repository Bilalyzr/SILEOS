from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from app.main import app
from app.models.campus_operations import ParentLinkRequest
from app.models.institution import InstitutionMember
from app.models.tuition import (
    TuitionAdjustment,
    TuitionFeeAssignment,
    TuitionLedgerEntry,
    TuitionPayment,
    TuitionReceipt,
)
from app.routers.tuition import router as tuition_router


ROOT = "/api/v1/institutions"

# Keep this vertical slice independently testable until the integration commit
# mounts the router in app/main.py.
if not any(
    getattr(route, "path", "").endswith("/fees/summary") for route in app.routes
):
    app.include_router(tuition_router, prefix=ROOT, tags=["Tuition fees"])


@pytest.fixture
def tuition_campus(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="tuition-owner@example.org")
    as_user(owner)
    institution_id = client.post(
        ROOT,
        json={"name": "Tuition Test College", "academic_year": "2026-27"},
    ).json()["id"]
    student = make_user(role="student", email="fee-student@example.org")
    other_student = make_user(role="student", email="fee-other@example.org")
    teacher = make_user(role="instructor", email="fee-teacher@example.org")
    parent = make_user(role="parent", email="fee-parent@example.org")
    stranger_parent = make_user(role="parent", email="fee-stranger-parent@example.org")
    members = []
    for person, role in (
        (student, "student"),
        (other_student, "student"),
        (teacher, "teacher"),
    ):
        member = InstitutionMember(
            institution_id=institution_id,
            user_id=person.id,
            role=role,
            status="active",
            department="",
        )
        db.add(member)
        db.flush()
        members.append(member)
    db.commit()
    return SimpleNamespace(
        owner=owner,
        student=student,
        other_student=other_student,
        teacher=teacher,
        parent=parent,
        stranger_parent=stranger_parent,
        institution_id=institution_id,
        student_member=members[0],
        other_member=members[1],
        teacher_member=members[2],
    )


def plan_payload(today=None):
    today = today or date.today()
    return {
        "name": "Annual tuition 2026",
        "academic_year": "2026-27",
        "currency": "inr",
        "description": "Academic and laboratory fees",
        "components": [
            {"code": "tuition", "name": "Tuition", "amount": "2000.00"},
            {"code": "LAB", "name": "Laboratory", "amount": "1000.00"},
        ],
        "installments": [
            {
                "name": "Opening installment",
                "due_on": str(today - timedelta(days=100)),
                "amount": "1000",
            },
            {
                "name": "Second installment",
                "due_on": str(today - timedelta(days=20)),
                "amount": "1000",
            },
            {
                "name": "Final installment",
                "due_on": str(today + timedelta(days=10)),
                "amount": "1000",
            },
        ],
    }


def create_published_plan(client, campus, today=None):
    root = f"{ROOT}/{campus.institution_id}/fees"
    response = client.post(root + "/plans", json=plan_payload(today))
    assert response.status_code == 201, response.text
    plan_id = response.json()["id"]
    published = client.post(f"{root}/plans/{plan_id}/publish")
    assert published.status_code == 200, published.text
    return plan_id


def create_assignment(client, campus, plan_id, member=None):
    member = member or campus.student_member
    response = client.post(
        f"{ROOT}/{campus.institution_id}/fees/assignments",
        json={
            "student_member_id": member.id,
            "plan_id": plan_id,
            "note": "2026 intake",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_plan_components_installments_publish_and_tenant_rbac(
    tuition_campus, client, as_user, make_user
):
    campus = tuition_campus
    root = f"{ROOT}/{campus.institution_id}/fees"
    invalid = plan_payload()
    invalid["installments"][2]["amount"] = "999.99"
    assert client.post(root + "/plans", json=invalid).status_code == 422

    plan_id = create_published_plan(client, campus)
    plan = client.get(root + "/plans").json()["items"][0]
    assert plan["id"] == plan_id
    assert plan["currency"] == "INR"
    assert plan["total_amount"] == 3000.0
    assert [row["code"] for row in plan["components"]] == ["TUITION", "LAB"]
    assert plan["status"] == "published"
    # Publishing is retry-safe.
    assert client.post(f"{root}/plans/{plan_id}/publish").status_code == 200

    as_user(campus.teacher)
    assert client.get(root + "/plans").status_code == 403
    assert client.post(root + "/plans", json=plan_payload()).status_code == 403
    platform_admin = make_user(
        role="admin", email="unscoped-platform-admin@example.org"
    )
    as_user(platform_admin)
    # Institution APIs intentionally have no platform-role bypass.
    assert client.get(root + "/summary").status_code == 404


def test_assignment_ledger_adjustment_payment_receipt_and_idempotency(
    tuition_campus, client, db
):
    campus = tuition_campus
    today = date.today()
    plan_id = create_published_plan(client, campus, today)
    account = create_assignment(client, campus, plan_id)
    assignment_id = account["id"]
    assert account["gross_amount"] == 3000.0
    assert account["balance"] == 3000.0
    assert len(account["installments"]) == 3
    assert db.query(TuitionLedgerEntry).filter_by(entry_type="charge").count() == 3

    adjust_url = (
        f"{ROOT}/{campus.institution_id}/fees/assignments/{assignment_id}/adjustments"
    )
    adjustment_body = {"kind": "discount", "amount": "200.00", "reason": "Merit award"}
    first_adjustment = client.post(
        adjust_url,
        json=adjustment_body,
        headers={"Idempotency-Key": "discount-2026-0001"},
    )
    assert first_adjustment.status_code == 201, first_adjustment.text
    assert first_adjustment.json()["replayed"] is False
    replay_adjustment = client.post(
        adjust_url,
        json=adjustment_body,
        headers={"Idempotency-Key": "discount-2026-0001"},
    )
    assert replay_adjustment.json()["replayed"] is True
    assert db.query(TuitionAdjustment).count() == 1

    payment_url = (
        f"{ROOT}/{campus.institution_id}/fees/assignments/{assignment_id}/payments"
    )
    payment_body = {
        "amount": "1200.00",
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "method": "upi",
        "reference": "UPI-12345",
        "note": "Front desk collection",
    }
    first = client.post(
        payment_url,
        json=payment_body,
        headers={"Idempotency-Key": "payment-2026-0001"},
    )
    assert first.status_code == 201, first.text
    assert first.json()["replayed"] is False
    assert first.json()["balance"] == 1600.0
    receipt = first.json()["payment"]["receipt"]
    assert receipt["receipt_number"].startswith(f"TF-{campus.institution_id}-")

    replay = client.post(
        payment_url,
        json=payment_body,
        headers={"Idempotency-Key": "payment-2026-0001"},
    )
    assert replay.status_code == 201
    assert replay.json()["replayed"] is True
    assert replay.json()["payment"]["id"] == first.json()["payment"]["id"]
    assert db.query(TuitionPayment).count() == 1
    assert db.query(TuitionReceipt).count() == 1
    assert (
        client.post(
            payment_url,
            json={**payment_body, "amount": "100.00"},
            headers={"Idempotency-Key": "payment-2026-0001"},
        ).status_code
        == 409
    )

    summary = client.get(root := f"{ROOT}/{campus.institution_id}/fees/summary").json()
    assert summary["totals"] == {
        "assessed": 3000.0,
        "discounts": 200.0,
        "waivers": 0.0,
        "paid": 1200.0,
        "outstanding": 1600.0,
        "overdue": 600.0,
        "due_today": 0.0,
        "due_next_30_days": 1000.0,
    }
    assert summary["aging"] == {
        "current": 1000.0,
        "days_1_30": 600.0,
        "days_31_60": 0.0,
        "days_61_90": 0.0,
        "days_91_plus": 0.0,
    }
    assert summary["accounts"] == {"total": 1, "with_balance": 1, "overdue": 1}
    aging = client.get(f"{ROOT}/{campus.institution_id}/fees/aging").json()
    assert aging["rows"][0]["student_user_id"] == campus.student.id
    assert aging["rows"][0]["oldest_due_on"] == str(today - timedelta(days=20))


def test_student_and_approved_parent_only_see_their_account_and_receipt(
    tuition_campus, client, as_user, db
):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    own_account = create_assignment(client, campus, plan_id)
    other_account = create_assignment(client, campus, plan_id, campus.other_member)
    payment = client.post(
        f"{ROOT}/{campus.institution_id}/fees/assignments/{own_account['id']}/payments",
        json={"amount": "50", "method": "upi", "reference": "CASH-1"},
        headers={"Idempotency-Key": "receipt-access-0001"},
    ).json()
    receipt_id = payment["payment"]["receipt"]["id"]

    as_user(campus.student)
    mine = client.get(f"{ROOT}/{campus.institution_id}/fees/me")
    assert mine.status_code == 200
    assert [row["id"] for row in mine.json()["assignments"]] == [own_account["id"]]
    assert (
        client.get(
            f"{ROOT}/{campus.institution_id}/fees/assignments/{other_account['id']}"
        ).status_code
        == 404
    )
    own_receipt = client.get(
        f"{ROOT}/{campus.institution_id}/fees/receipts/{receipt_id}"
    )
    assert own_receipt.status_code == 200
    assert own_receipt.headers["cache-control"] == "private, no-store"

    as_user(campus.parent)
    assert (
        client.get(
            f"{ROOT}/{campus.institution_id}/fees/me",
            params={"student_user_id": campus.student.id},
        ).status_code
        == 404
    )
    db.add(
        ParentLinkRequest(
            parent_user_id=campus.parent.id,
            student_user_id=campus.student.id,
            status="approved",
        )
    )
    db.commit()
    parent_view = client.get(
        f"{ROOT}/{campus.institution_id}/fees/me",
        params={"student_user_id": campus.student.id},
    )
    assert parent_view.status_code == 200
    assert parent_view.json()["student"]["user_id"] == campus.student.id
    assert (
        client.get(
            f"{ROOT}/{campus.institution_id}/fees/receipts/{receipt_id}"
        ).status_code
        == 200
    )
    assert client.get(f"{ROOT}/{campus.institution_id}/fees/summary").status_code == 404

    as_user(campus.stranger_parent)
    assert (
        client.get(
            f"{ROOT}/{campus.institution_id}/fees/me",
            params={"student_user_id": campus.student.id},
        ).status_code
        == 404
    )


def test_invalid_money_and_specific_installment_adjustments_are_atomic(
    tuition_campus, client, db
):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    account = create_assignment(client, campus, plan_id)
    assignment_id = account["id"]
    installment_id = account["installments"][0]["id"]
    root = f"{ROOT}/{campus.institution_id}/fees/assignments/{assignment_id}"

    assert (
        client.post(
            root + "/adjustments",
            json={
                "kind": "waiver",
                "amount": "1200",
                "reason": "Needs-based aid",
                "installment_id": installment_id,
            },
            headers={"Idempotency-Key": "waiver-too-large-0001"},
        ).status_code
        == 422
    )
    assert db.query(TuitionAdjustment).count() == 0
    assert (
        client.post(
            root + "/payments",
            json={"amount": "3000.01", "method": "cash"},
            headers={"Idempotency-Key": "overpayment-0000001"},
        ).status_code
        == 422
    )
    assert db.query(TuitionPayment).count() == 0
    assert db.query(TuitionFeeAssignment).count() == 1


def test_tuition_migration_builds_and_drops_all_tables(tmp_path):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0036_tuition_finance.py"
    )
    spec = importlib.util.spec_from_file_location(
        "tuition_migration_0036", migration_path
    )
    migration = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(migration)
    assert migration.revision == "0036"
    assert migration.down_revision == "0035"

    engine = create_engine(f"sqlite:///{tmp_path / 'tuition-migration.db'}")
    metadata = sa.MetaData()
    sa.Table("institutions", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("users", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table(
        "institution_members",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), sa.ForeignKey("institutions.id")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        tables = set(inspect(connection).get_table_names())
        assert {
            "tuition_fee_plans",
            "tuition_fee_components",
            "tuition_installment_templates",
            "tuition_fee_assignments",
            "tuition_installments",
            "tuition_payments",
            "tuition_adjustments",
            "tuition_ledger_entries",
            "tuition_receipts",
        }.issubset(tables)
        migration.downgrade()
        tables = set(inspect(connection).get_table_names())
        assert not any(name.startswith("tuition_") for name in tables)
