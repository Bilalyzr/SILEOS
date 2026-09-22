"""Tenant provisioning, policy, control-plane authorization, and migration coverage."""

import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from app.models.institution import Institution
from app.models.platform_tenant import (
    PlatformAuditEvent,
    PlatformOutboxEvent,
    PlatformTenant,
    PlatformTenantEntitlement,
    PlatformTenantMembership,
)
from app.services.platform_tenant_service import is_entitled


INSTITUTIONS = "/api/v1/institutions"
TENANTS = "/api/v1/platform/tenants"


def _create_campus(client, as_user, owner):
    as_user(owner)
    response = client.post(
        INSTITUTIONS,
        json={
            "name": "Sasha Future School",
            "kind": "school",
            "academic_year": "2026-2027",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_institution_provisions_shared_tenant_entitlements_and_outbox(
    client, db, as_user, make_user
):
    owner = make_user(role="instructor")
    payload = _create_campus(client, as_user, owner)

    institution = db.get(Institution, payload["id"])
    assert payload["tenant_id"] == institution.tenant_id
    tenant = db.get(PlatformTenant, institution.tenant_id)
    assert (tenant.kind, tenant.status, tenant.created_by) == (
        "institution",
        "trial",
        owner.id,
    )
    membership = (
        db.query(PlatformTenantMembership)
        .filter_by(tenant_id=tenant.id, user_id=owner.id)
        .one()
    )
    assert (membership.role, membership.status) == ("owner", "active")
    assert {
        (row.vertical, row.feature_key)
        for row in db.query(PlatformTenantEntitlement)
        .filter_by(tenant_id=tenant.id)
        .all()
    } == {
        ("meiporul", "immersive_catalog"),
        ("seyappaduporul", "campus_operations"),
        ("utporul", "course_authoring"),
    }
    assert (
        db.query(PlatformAuditEvent)
        .filter_by(tenant_id=tenant.id, action="tenant.provisioned")
        .count()
        == 1
    )
    assert (
        db.query(PlatformOutboxEvent)
        .filter_by(tenant_id=tenant.id, topic="platform.tenant.provisioned")
        .count()
        == 1
    )


def test_institution_invitation_and_suspension_sync_tenant_membership(
    client, db, as_user, make_user
):
    owner = make_user(role="instructor", email="owner@future.edu")
    payload = _create_campus(client, as_user, owner)
    invited = make_user(email="teacher@future.edu")
    invitation = client.post(
        f"{INSTITUTIONS}/{payload['id']}/invitations",
        json={"email": invited.user_email, "role": "teacher"},
    ).json()

    as_user(invited)
    accepted = client.post(
        f"{INSTITUTIONS}/invitations/{invitation['id']}/accept"
    )
    assert accepted.status_code == 200, accepted.text
    membership = (
        db.query(PlatformTenantMembership)
        .filter_by(tenant_id=payload["tenant_id"], user_id=invited.id)
        .one()
    )
    assert (membership.role, membership.status) == ("teacher", "active")

    as_user(owner)
    campus_member = next(
        row
        for row in client.get(f"{INSTITUTIONS}/{payload['id']}").json()["members"]
        if row["user_id"] == invited.id
    )
    updated = client.patch(
        f"{INSTITUTIONS}/{payload['id']}/members/{campus_member['id']}",
        json={"role": "student", "status": "suspended"},
    )
    assert updated.status_code == 200, updated.text
    db.refresh(membership)
    assert (membership.role, membership.status) == ("student", "suspended")


def test_only_superadmin_can_control_tenants_and_changes_are_audited(
    client, db, as_user, make_user
):
    owner = make_user(role="instructor")
    payload = _create_campus(client, as_user, owner)

    # Tenant control is intentionally stricter than ordinary admin screens.
    from app.main import app
    from app.services.auth_service import AuthService

    admin = make_user(role="admin")
    with pytest.raises(HTTPException) as denied:
        AuthService.require_superadmin(admin)
    assert denied.value.status_code == 403

    superadmin = make_user(role="superadmin")
    app.dependency_overrides[AuthService.require_admin] = lambda: superadmin
    listing = client.get(TENANTS)
    assert listing.status_code == 200, listing.text
    assert any(row["id"] == payload["tenant_id"] for row in listing.json())

    changed = client.put(
        f"{TENANTS}/{payload['tenant_id']}/entitlements/meiporul/device_fleet",
        json={
            "enabled": True,
            "quota": {"headsets": 40, "rooms": 2},
            "reason": "Signed immersive lab contract",
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["quota"]["headsets"] == 40
    assert is_entitled(db, payload["tenant_id"], "meiporul", "device_fleet")

    suspended = client.patch(
        f"{TENANTS}/{payload['tenant_id']}/status",
        json={"status": "suspended", "reason": "Contract temporarily paused"},
    )
    assert suspended.status_code == 200, suspended.text
    assert not is_entitled(db, payload["tenant_id"], "meiporul", "device_fleet")
    assert (
        db.query(PlatformAuditEvent)
        .filter_by(
            tenant_id=payload["tenant_id"], action="tenant.entitlement_changed"
        )
        .count()
        == 1
    )
    app.dependency_overrides.pop(AuthService.require_admin, None)


def test_platform_tenant_migration_backfills_existing_institution(tmp_path):
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0044_platform_tenant_kernel.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0044", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert (migration.revision, migration.down_revision) == ("0044", "0043")

    engine = create_engine(f"sqlite:///{tmp_path / 'platform-kernel.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, user_email VARCHAR(254))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE institutions ("
                "id INTEGER PRIMARY KEY, slug VARCHAR(100) NOT NULL UNIQUE, "
                "name VARCHAR(160) NOT NULL, timezone VARCHAR(64) NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE institution_members ("
                "id INTEGER PRIMARY KEY, institution_id INTEGER NOT NULL, "
                "user_id INTEGER NOT NULL, role VARCHAR(20) NOT NULL, "
                "status VARCHAR(20) NOT NULL)"
            )
        )
        connection.execute(text("INSERT INTO users VALUES (1, 'owner@example.com')"))
        connection.execute(
            text(
                "INSERT INTO institutions VALUES "
                "(7, 'legacy-school', 'Legacy School', 'Asia/Kolkata')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO institution_members VALUES (1, 7, 1, 'owner', 'active')"
            )
        )
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        tables = set(inspect(connection).get_table_names())
        assert {
            "platform_tenants",
            "platform_tenant_memberships",
            "platform_tenant_domains",
            "platform_tenant_entitlements",
            "platform_audit_events",
            "platform_outbox_events",
        }.issubset(tables)
        tenant_id = connection.execute(
            text("SELECT tenant_id FROM institutions WHERE id = 7")
        ).scalar_one()
        assert tenant_id is not None
        assert connection.execute(
            text(
                "SELECT count(*) FROM platform_tenant_memberships "
                "WHERE tenant_id = :tenant_id AND user_id = 1"
            ),
            {"tenant_id": tenant_id},
        ).scalar_one() == 1
        assert connection.execute(
            text(
                "SELECT count(*) FROM platform_tenant_entitlements "
                "WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        ).scalar_one() == 3

        migration.downgrade()
        assert "tenant_id" not in {
            column["name"] for column in inspect(connection).get_columns("institutions")
        }
