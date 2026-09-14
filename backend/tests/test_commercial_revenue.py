"""Commercial lifecycle and consolidated cross-vertical revenue coverage."""

from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.models.commercial import CommercialInvoice, RevenueLedgerEvent
from app.services.business_portfolio_service import portfolio


ROOT = "/api/v1/platform/commercial"


def _superadmin(client, make_user):
    from app.main import app
    from app.services.auth_service import AuthService

    user = make_user(role="superadmin")
    app.dependency_overrides[AuthService.require_admin] = lambda: user
    return user


def _tenant(client, make_user, as_user):
    owner = make_user(role="instructor")
    as_user(owner)
    response = client.post(
        "/api/v1/institutions",
        json={"name": "Immersive Academy", "academic_year": "2026-2027"},
    )
    assert response.status_code == 201, response.text
    return response.json()["tenant_id"]


def test_offer_rejects_stream_from_another_vertical(client, make_user):
    _superadmin(client, make_user)
    response = client.post(
        f"{ROOT}/offers",
        json={
            "sku": "MA1-BAD",
            "business_vertical": "meiporul",
            "revenue_stream": "tuition_fees",
            "name": "Wrongly classified offer",
            "billing_model": "one_time",
            "unit_amount": "1000.00",
        },
    )
    assert response.status_code == 422


def test_contract_invoice_capture_entitlement_and_partial_refunds(
    client, db, make_user, as_user
):
    tenant_id = _tenant(client, make_user, as_user)
    admin = _superadmin(client, make_user)
    offer_response = client.post(
        f"{ROOT}/offers",
        json={
            "sku": "MA1-LAB-40",
            "business_vertical": "meiporul",
            "revenue_stream": "lab_deployment",
            "name": "Forty headset immersive lab",
            "billing_model": "milestone",
            "unit_amount": "500000.00",
            "tax_code": "GST18",
            "entitlement_grants": [
                {
                    "vertical": "meiporul",
                    "feature_key": "device_fleet",
                    "quota": {"headsets": 40, "rooms": 1},
                }
            ],
        },
    )
    assert offer_response.status_code == 201, offer_response.text
    offer = offer_response.json()

    contract_response = client.post(
        f"{ROOT}/contracts",
        json={
            "tenant_id": tenant_id,
            "offer_id": offer["id"],
            "starts_on": "2026-09-13",
            "external_reference": "SIGNED-SOW-001",
        },
    )
    assert contract_response.status_code == 201, contract_response.text
    contract = contract_response.json()

    invoice_response = client.post(
        f"{ROOT}/invoices",
        json={
            "contract_id": contract["id"],
            "tax_amount": "90000.00",
            "due_on": "2026-09-30",
        },
    )
    assert invoice_response.status_code == 201, invoice_response.text
    invoice = invoice_response.json()
    assert invoice["invoice_number"] == "SI/2026-27/000001"
    assert invoice["total_amount"] == 590000.0

    paid_at = datetime(2026, 9, 13, 10, tzinfo=timezone.utc)
    payment_payload = {
        "source_event_key": "razorpay:pay_lab_001",
        "payment_reference": "pay_lab_001",
        "occurred_at": paid_at.isoformat(),
        "gateway_fee": "1180.00",
        "reason": "Razorpay capture verified",
    }
    payment_response = client.post(
        f"{ROOT}/invoices/{invoice['id']}/payments", json=payment_payload
    )
    assert payment_response.status_code == 201, payment_response.text
    capture = payment_response.json()
    assert capture["business_vertical"] == "meiporul"
    assert capture["revenue_stream"] == "lab_deployment"
    assert capture["net_amount"] == 498820.0
    # Gateway retries converge on the same immutable ledger event.
    duplicate = client.post(
        f"{ROOT}/invoices/{invoice['id']}/payments", json=payment_payload
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == capture["id"]
    assert db.query(RevenueLedgerEvent).filter_by(event_type="capture").count() == 1

    tenant_detail = client.get(f"/api/v1/platform/tenants/{tenant_id}").json()
    fleet = next(
        item
        for item in tenant_detail["entitlements"]
        if item["feature_key"] == "device_fleet"
    )
    assert fleet["enabled"] is True
    assert fleet["quota"]["headsets"] == 40

    for index, amount in enumerate(("100000.00", "490000.00"), start=1):
        response = client.post(
            f"{ROOT}/ledger/{capture['id']}/refunds",
            json={
                "source_event_key": f"razorpay:rfnd_lab_00{index}",
                "refund_reference": f"rfnd_lab_00{index}",
                "amount": amount,
                "occurred_at": (paid_at + timedelta(days=index)).isoformat(),
                "reason": "Approved deployment refund",
            },
        )
        assert response.status_code == 201, response.text
    assert db.get(CommercialInvoice, invoice["id"]).status == "refunded"

    excessive = client.post(
        f"{ROOT}/ledger/{capture['id']}/refunds",
        json={
            "source_event_key": "razorpay:rfnd_lab_too_much",
            "refund_reference": "rfnd_lab_too_much",
            "amount": "1.00",
            "occurred_at": (paid_at + timedelta(days=3)).isoformat(),
            "reason": "Must be rejected",
        },
    )
    assert excessive.status_code == 409

    report = portfolio(db, date(2026, 9, 1), date(2026, 9, 30))
    meiporul = next(row for row in report["verticals"] if row["key"] == "meiporul")
    inr = next(row for row in meiporul["revenue"]["currencies"] if row["currency"] == "INR")
    assert inr == {
        "currency": "INR",
        "captured": 590000.0,
        "refunded": 590000.0,
        "net_cash": 0.0,
    }


def test_invoice_sequence_is_fiscal_year_scoped(client, make_user, as_user):
    tenant_id = _tenant(client, make_user, as_user)
    _superadmin(client, make_user)
    offer = client.post(
        f"{ROOT}/offers",
        json={
            "sku": "MA2-SAAS-ANNUAL",
            "business_vertical": "seyappaduporul",
            "revenue_stream": "institution_operations",
            "name": "Campus OS annual plan",
            "billing_model": "subscription",
            "unit_amount": "120000.00",
        },
    ).json()
    contract = client.post(
        f"{ROOT}/contracts",
        json={
            "tenant_id": tenant_id,
            "offer_id": offer["id"],
            "billing_interval": "annual",
            "starts_on": "2026-03-01",
        },
    ).json()
    first = client.post(
        f"{ROOT}/invoices",
        json={"contract_id": contract["id"], "due_on": "2026-03-20"},
    ).json()
    second = client.post(
        f"{ROOT}/invoices",
        json={"contract_id": contract["id"], "due_on": "2026-04-20"},
    ).json()
    assert first["invoice_number"] == "SI/2025-26/000001"
    assert second["invoice_number"] == "SI/2026-27/000001"


def test_commercial_migration_round_trip(tmp_path):
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0045_commercial_revenue_ledger.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0045", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert (migration.revision, migration.down_revision) == ("0045", "0044")

    engine = create_engine(f"sqlite:///{tmp_path / 'commercial.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text("CREATE TABLE platform_tenants (id INTEGER PRIMARY KEY)")
        )
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        expected = {
            "commercial_invoice_counters",
            "commercial_offers",
            "commercial_contracts",
            "commercial_invoices",
            "revenue_ledger_events",
        }
        assert expected.issubset(set(inspect(connection).get_table_names()))
        migration.downgrade()
        assert expected.isdisjoint(set(inspect(connection).get_table_names()))
