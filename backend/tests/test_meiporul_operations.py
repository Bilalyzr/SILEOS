"""Meiporul lab deployment, fleet, safety, and support invariants."""

from app.models.platform_tenant import PlatformTenantMembership


ROOT = "/api/v1/meiporul/operations"


def _tenant(client, make_user, as_user, name="Immersive Academy"):
    owner = make_user(role="instructor")
    as_user(owner)
    response = client.post(
        "/api/v1/institutions",
        json={"name": name, "academic_year": "2026-2027"},
    )
    assert response.status_code == 201, response.text
    return owner, response.json()["tenant_id"]


def _site(client, tenant_id):
    response = client.post(
        f"{ROOT}/sites",
        json={
            "tenant_id": tenant_id,
            "code": "CHN-LAB-01",
            "name": "Chennai Immersive Lab",
            "room_count": 1,
            "headset_capacity": 30,
            "address": {"city": "Chennai", "state": "Tamil Nadu"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_go_live_requires_fleet_safety_network_and_milestones(
    client, db, make_user, as_user
):
    _, tenant_id = _tenant(client, make_user, as_user)
    admin = make_user(role="admin")
    as_user(admin)
    site = _site(client, tenant_id)
    assert len(site["milestones"]) == 5

    blocked = client.patch(
        f"{ROOT}/sites/{site['id']}",
        json={"status": "active", "reason": "Attempt initial go-live"},
    )
    assert blocked.status_code == 409

    ready_network = client.patch(
        f"{ROOT}/sites/{site['id']}",
        json={
            "status": "installing",
            "network_readiness": "ready",
            "reason": "Network acceptance complete",
        },
    )
    assert ready_network.status_code == 200
    device = client.post(
        f"{ROOT}/sites/{site['id']}/devices",
        json={
            "asset_tag": "VR-HEADSET-001",
            "serial_number": "SERIAL-001",
            "device_type": "headset",
            "vendor": "Meta",
            "model": "Quest",
        },
    ).json()
    for status in ("provisioning", "ready"):
        response = client.patch(
            f"{ROOT}/devices/{device['id']}",
            json={"status": status, "reason": f"Device moved to {status}"},
        )
        assert response.status_code == 200, response.text

    inspection = client.post(
        f"{ROOT}/sites/{site['id']}/inspections",
        json={
            "inspection_type": "pre_install",
            "status": "passed",
            "scheduled_for": "2026-09-13T09:00:00Z",
            "checklist": [{"key": "clearance", "passed": True}],
            "findings": "Room clearance and hygiene controls passed.",
        },
    )
    assert inspection.status_code == 201, inspection.text
    for milestone in inspection.json()["milestones"]:
        response = client.patch(
            f"{ROOT}/milestones/{milestone['id']}",
            json={
                "status": "completed",
                "evidence_urls": [f"https://evidence.example/{milestone['id']}"],
                "reason": "Field evidence reviewed",
            },
        )
        assert response.status_code == 200, response.text
    live = client.patch(
        f"{ROOT}/sites/{site['id']}",
        json={"status": "active", "reason": "All go-live controls passed"},
    )
    assert live.status_code == 200, live.text
    assert live.json()["status"] == "active"
    assert live.json()["safety_status"] == "passed"


def test_tenant_member_scope_and_ticket_resolution(client, db, make_user, as_user):
    owner, tenant_id = _tenant(client, make_user, as_user, "Tenant One")
    admin = make_user(role="admin")
    as_user(admin)
    site = _site(client, tenant_id)
    outsider = make_user(role="instructor")
    as_user(outsider)
    assert client.get(f"{ROOT}/sites/{site['id']}").status_code == 403

    db.add(
        PlatformTenantMembership(
            tenant_id=tenant_id,
            user_id=outsider.id,
            role="support",
            status="active",
            permissions=[],
        )
    )
    db.commit()
    opened = client.post(
        f"{ROOT}/sites/{site['id']}/tickets",
        json={
            "category": "hardware",
            "priority": "critical",
            "subject": "Headset display failure",
            "description": "The headset display remains black after a verified restart.",
        },
    )
    assert opened.status_code == 201, opened.text
    ticket = opened.json()["tickets"][0]
    assert ticket["reference"].startswith("MP-")
    missing_resolution = client.patch(
        f"{ROOT}/tickets/{ticket['id']}",
        json={"status": "resolved", "reason": "Attempted close"},
    )
    assert missing_resolution.status_code == 422
    resolved = client.patch(
        f"{ROOT}/tickets/{ticket['id']}",
        json={
            "status": "resolved",
            "resolution": "Display cable reseated and headset burn-in test passed.",
            "reason": "Repair verified by lab operator",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["tickets"][0]["status"] == "resolved"
