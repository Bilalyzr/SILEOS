"""Bounded WhatsApp campaign expansion and request-transaction regressions."""

from fastapi import BackgroundTasks
import pytest
from sqlalchemy import func, select

from app.models.campus_pilot import CampusWhatsAppCampaign, CampusWhatsAppMessage
from app.models.institution import (
    Institution,
    InstitutionAudit,
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionMember,
)
from app.models.user import User
from app.models.whatsapp import WhatsAppCampaign, WhatsAppContact, WhatsAppMessage
from app.routers import whatsapp as whatsapp_router
from app.schemas.whatsapp import WhatsAppCampaignCreate
from app.services import campus_whatsapp, whatsapp_campaigns


RECIPIENTS = 1_205


def _configure_whatsapp(monkeypatch):
    settings = campus_whatsapp.get_settings()
    values = {
        "WHATSAPP_PHONE_NUMBER_ID": "phone-id",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "business-id",
        "WHATSAPP_BUSINESS_PHONE": "+15550001111",
        "WHATSAPP_ACCESS_TOKEN": "access-token",
        "WHATSAPP_APP_SECRET": "app-secret",
        "WHATSAPP_VERIFY_TOKEN": "verify-token",
        "WHATSAPP_APPROVED_TEMPLATES": "learning_update,campus_announcement",
    }
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)


def _seed_users_and_contacts(db, count, *, first_id=1):
    ids = range(first_id, first_id + count)
    db.execute(
        User.__table__.insert(),
        [
            {
                "id": user_id,
                "user_login": f"bulk-user-{user_id}",
                "user_pass": "unused",
                "user_nicename": f"bulk-user-{user_id}",
                "user_email": f"bulk-user-{user_id}@example.org",
                "display_name": f"Bulk User {user_id}",
                "role": "student",
                "is_active": True,
                "is_verified": True,
            }
            for user_id in ids
        ],
    )
    ids = range(first_id, first_id + count)
    db.execute(
        WhatsAppContact.__table__.insert(),
        [
            {
                "user_id": user_id,
                "phone": f"+1555{user_id:08d}",
                "status": "confirmed",
            }
            for user_id in ids
        ],
    )


def _track_insert_batches(monkeypatch, db, table_name, *, fail_on_batch=None):
    original_execute = db.execute
    batch_sizes = []

    def tracked_execute(statement, params=None, *args, **kwargs):
        table = getattr(statement, "table", None)
        if getattr(statement, "is_insert", False) and table.name == table_name:
            batch_sizes.append(len(params))
            if fail_on_batch == len(batch_sizes):
                raise RuntimeError("synthetic batch insert failure")
        return original_execute(statement, params, *args, **kwargs)

    monkeypatch.setattr(db, "execute", tracked_execute)
    return original_execute, batch_sizes


def _forbid_orm_queries(*_args, **_kwargs):
    raise AssertionError("recipient expansion must not hydrate ORM entities")


def test_global_expansion_inserts_1205_recipients_in_bounded_core_batches(
    db, monkeypatch
):
    _seed_users_and_contacts(db, RECIPIENTS)
    campaign_id = db.execute(
        WhatsAppCampaign.__table__.insert().values(
            request_key="global-scale-1205",
            template="learning_update",
            language="en",
            parameters=[],
            roles=["student"],
            header_image_url="",
        )
    ).inserted_primary_key[0]
    original_execute, batch_sizes = _track_insert_batches(
        monkeypatch, db, WhatsAppMessage.__tablename__
    )
    monkeypatch.setattr(db, "query", _forbid_orm_queries)

    inserted = whatsapp_campaigns.enqueue_global_recipients(
        db, campaign_id=campaign_id, roles=["student"]
    )

    assert inserted == RECIPIENTS
    assert batch_sizes == [500, 500, 205]
    assert (
        original_execute(
            select(func.count()).select_from(WhatsAppMessage.__table__)
        ).scalar_one()
        == RECIPIENTS
    )


def test_campus_expansion_inserts_1205_recipients_in_bounded_core_batches(
    db, monkeypatch
):
    _seed_users_and_contacts(db, RECIPIENTS)
    db.execute(
        Institution.__table__.insert().values(
            id=1,
            name="Scale Campus",
            slug="scale-campus",
            academic_year="2026-27",
        )
    )
    db.execute(
        InstitutionMember.__table__.insert(),
        [
            {
                "id": member_id,
                "institution_id": 1,
                "user_id": member_id,
                "role": "student",
                "status": "active",
            }
            for member_id in range(1, RECIPIENTS + 1)
        ],
    )
    db.execute(
        InstitutionBatch.__table__.insert().values(
            id=1,
            institution_id=1,
            name="Scale Batch",
            academic_year="2026-27",
        )
    )
    db.execute(
        InstitutionBatchMember.__table__.insert(),
        [
            {"batch_id": 1, "member_id": member_id}
            for member_id in range(1, RECIPIENTS + 1)
        ],
    )
    campaign_id = db.execute(
        CampusWhatsAppCampaign.__table__.insert().values(
            institution_id=1,
            request_key="campus-scale-1205",
            template="campus_announcement",
            language="en",
            parameters=[],
            batch_id=1,
            header_image_url="",
            created_by=1,
        )
    ).inserted_primary_key[0]
    original_execute, batch_sizes = _track_insert_batches(
        monkeypatch, db, CampusWhatsAppMessage.__tablename__
    )
    monkeypatch.setattr(db, "query", _forbid_orm_queries)

    inserted = whatsapp_campaigns.enqueue_campus_recipients(
        db,
        campaign_id=campaign_id,
        institution_id=1,
        batch_id=1,
    )

    assert inserted == RECIPIENTS
    assert batch_sizes == [500, 500, 205]
    assert (
        original_execute(
            select(func.count()).select_from(CampusWhatsAppMessage.__table__)
        ).scalar_one()
        == RECIPIENTS
    )


def test_global_zero_audience_rolls_back_campaign(
    client, as_user, make_user, db, monkeypatch
):
    _configure_whatsapp(monkeypatch)
    admin = make_user(role="admin", email="zero-audience-admin@example.org")
    as_user(admin)

    response = client.post(
        "/api/v1/whatsapp/admin/campaigns",
        json={
            "request_key": "zero-audience-global",
            "template": "learning_update",
            "parameters": [],
            "roles": ["student"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "No active, opted-in recipients match this audience."
    )
    db.expire_all()
    assert (
        db.query(WhatsAppCampaign).filter_by(request_key="zero-audience-global").count()
        == 0
    )
    assert db.query(WhatsAppMessage).count() == 0


def test_campus_zero_audience_rolls_back_campaign_and_audit(
    client, as_user, make_user, db, monkeypatch
):
    _configure_whatsapp(monkeypatch)
    owner = make_user(role="instructor", email="zero-campus-owner@example.org")
    institution = Institution(
        name="Zero Audience Campus",
        slug="zero-audience-campus",
        kind="college",
        academic_year="2026-27",
        timezone="Asia/Kolkata",
        description="",
        plan="starter",
    )
    db.add(institution)
    db.flush()
    db.add(
        InstitutionMember(
            institution_id=institution.id,
            user_id=owner.id,
            role="owner",
            department="",
            status="active",
        )
    )
    db.commit()
    institution_id = institution.id
    as_user(owner)

    response = client.post(
        f"/api/v1/institutions/{institution_id}/pilot/whatsapp/campaigns",
        json={
            "request_key": "zero-audience-campus",
            "template": "campus_announcement",
            "parameters": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "No active, opted-in recipients match this audience."
    )
    db.expire_all()
    assert (
        db.query(CampusWhatsAppCampaign)
        .filter_by(
            institution_id=institution_id,
            request_key="zero-audience-campus",
        )
        .count()
        == 0
    )
    assert db.query(CampusWhatsAppMessage).count() == 0
    assert (
        db.query(InstitutionAudit)
        .filter_by(
            institution_id=institution_id,
            action="whatsapp.campaign_created",
        )
        .count()
        == 0
    )


def test_mid_batch_failure_rolls_back_campaign_and_first_batch(
    db, make_user, monkeypatch
):
    _configure_whatsapp(monkeypatch)
    admin = make_user(role="admin", email="batch-failure-admin@example.org")
    _seed_users_and_contacts(db, 501, first_id=10_000)
    db.commit()
    _original_execute, batch_sizes = _track_insert_batches(
        monkeypatch,
        db,
        WhatsAppMessage.__tablename__,
        fail_on_batch=2,
    )
    command = WhatsAppCampaignCreate(
        request_key="mid-batch-failure",
        template="learning_update",
        parameters=[],
        roles=["student"],
    )

    with pytest.raises(RuntimeError, match="synthetic batch insert failure"):
        whatsapp_router.whatsapp_admin_campaign_create(
            command,
            BackgroundTasks(),
            db,
            admin,
        )

    assert batch_sizes == [500, 1]
    assert (
        db.query(WhatsAppCampaign).filter_by(request_key="mid-batch-failure").count()
        == 0
    )
    assert db.query(WhatsAppMessage).count() == 0
