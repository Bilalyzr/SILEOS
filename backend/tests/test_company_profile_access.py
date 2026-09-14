"""Authorization and tenant-scoping coverage for ``GET /companies/me``."""
from datetime import datetime, timezone

from app.models.company_dashboard import CompanyManager


def test_company_manager_can_read_linked_company_profile(
    client,
    db,
    make_user,
    make_company,
    auth_headers,
):
    owner = make_user(role="company")
    company = make_company(owner=owner)
    manager = make_user(role="company_manager")
    db.add(
        CompanyManager(
            company_id=company.id,
            user_id=manager.id,
            invited_by=owner.id,
            accepted_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    response = client.get(
        "/api/v1/companies/me",
        headers=auth_headers(manager.user_email, manager._test_password),
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == company.id
    assert response.json()["owner_user_id"] == owner.id


def test_unlinked_company_manager_cannot_read_any_company_profile(
    client,
    make_user,
    auth_headers,
):
    manager = make_user(role="company_manager")

    response = client.get(
        "/api/v1/companies/me",
        headers=auth_headers(manager.user_email, manager._test_password),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Endpoint not found"
