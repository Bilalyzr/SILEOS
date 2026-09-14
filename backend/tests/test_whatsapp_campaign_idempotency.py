"""Race regressions for WhatsApp campaign request keys."""

from app.core.database import get_db
from app.main import app
from app.models.campus_pilot import CampusWhatsAppCampaign, CampusWhatsAppMessage
from app.models.institution import Institution, InstitutionMember
from app.models.whatsapp import WhatsAppCampaign, WhatsAppContact, WhatsAppMessage
from app.services import campus_whatsapp


def _configure(monkeypatch):
    settings = campus_whatsapp.get_settings()
    for name, value in {
        "WHATSAPP_PHONE_NUMBER_ID": "phone-id",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "business-id",
        "WHATSAPP_BUSINESS_PHONE": "+15550001111",
        "WHATSAPP_ACCESS_TOKEN": "test-access-token",
        "WHATSAPP_APP_SECRET": "test-app-secret",
        "WHATSAPP_VERIFY_TOKEN": "test-verify-token",
        "WHATSAPP_APPROVED_TEMPLATES": "learning_update,campus_announcement",
    }.items():
        monkeypatch.setattr(settings, name, value)


def _use_request_session(db):
    def dependency():
        yield db

    app.dependency_overrides[get_db] = dependency


def _hide_next_campaign_preflight(db, model, monkeypatch):
    """Make one preflight miss an already committed unique-key winner.

    The following savepoint flush then reproduces the integrity error raised
    when a concurrent request commits between the real preflight and insert.
    """

    real_query = db.query
    state = {"remaining": 0}

    class HiddenQuery:
        def __init__(self, query):
            self.query = query

        def filter_by(self, **kwargs):
            self.query = self.query.filter_by(**kwargs)
            return self

        def populate_existing(self):
            self.query = self.query.populate_existing()
            return self

        def first(self):
            return None

    def query(*entities, **kwargs):
        actual = real_query(*entities, **kwargs)
        if state["remaining"] and len(entities) == 1 and entities[0] is model:
            state["remaining"] -= 1
            return HiddenQuery(actual)
        return actual

    monkeypatch.setattr(db, "query", query)
    return state, real_query


def test_global_campaign_unique_race_reuses_winner_and_rejects_conflict(
    client, as_user, make_user, db, monkeypatch
):
    _configure(monkeypatch)
    _use_request_session(db)
    monkeypatch.setattr(campus_whatsapp, "deliver_pending", lambda limit=100: None)
    admin = make_user(role="admin", email="global-race-admin@example.org")
    recipient = make_user(email="global-race-recipient@example.org")
    db.add(
        WhatsAppContact(
            user_id=recipient.id,
            phone="+919111111111",
            status="confirmed",
        )
    )
    winner = WhatsAppCampaign(
        request_key="global-race-001",
        template="learning_update",
        language="en",
        parameters=["Hello"],
        roles=["student"],
        header_image_url="",
        created_by=admin.id,
    )
    db.add(winner)
    db.flush()
    db.add(
        WhatsAppMessage(
            campaign_id=winner.id,
            user_id=recipient.id,
            phone="+919111111111",
            status="queued",
            callback_key="global-race-message",
            attempts=0,
        )
    )
    db.commit()
    winner_id = winner.id
    state, real_query = _hide_next_campaign_preflight(db, WhatsAppCampaign, monkeypatch)
    as_user(admin)
    command = {
        "request_key": "global-race-001",
        "template": "learning_update",
        "language": "en",
        "parameters": ["Hello"],
        "roles": ["student"],
    }

    state["remaining"] = 1
    repeated = client.post("/api/v1/whatsapp/admin/campaigns", json=command)
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["id"] == winner_id
    assert real_query(WhatsAppCampaign).count() == 1
    assert real_query(WhatsAppMessage).count() == 1

    db.rollback()
    state["remaining"] = 1
    conflicting = client.post(
        "/api/v1/whatsapp/admin/campaigns",
        json={**command, "parameters": ["Different message"]},
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["detail"] == (
        "That request key belongs to another campaign."
    )
    assert real_query(WhatsAppCampaign).count() == 1
    assert real_query(WhatsAppMessage).count() == 1


def test_campus_campaign_unique_race_reuses_winner_and_rejects_conflict(
    client, as_user, make_user, db, monkeypatch
):
    _configure(monkeypatch)
    _use_request_session(db)
    monkeypatch.setattr(campus_whatsapp, "deliver_pending", lambda limit=100: None)
    owner = make_user(email="campus-race-owner@example.org")
    recipient = make_user(email="campus-race-recipient@example.org")
    institution = Institution(
        name="Race-safe College",
        slug="race-safe-college",
        kind="college",
        academic_year="2026-27",
        timezone="Asia/Kolkata",
        description="",
        plan="starter",
    )
    db.add(institution)
    db.flush()
    owner_member = InstitutionMember(
        institution_id=institution.id,
        user_id=owner.id,
        role="owner",
        department="",
        status="active",
    )
    recipient_member = InstitutionMember(
        institution_id=institution.id,
        user_id=recipient.id,
        role="student",
        department="Science",
        status="active",
    )
    db.add_all([owner_member, recipient_member])
    db.flush()
    db.add(
        WhatsAppContact(
            user_id=recipient.id,
            phone="+919222222222",
            status="confirmed",
        )
    )
    winner = CampusWhatsAppCampaign(
        institution_id=institution.id,
        request_key="campus-race-001",
        template="campus_announcement",
        language="en",
        parameters=["Hello campus"],
        batch_id=None,
        header_image_url="",
        created_by=owner.id,
    )
    db.add(winner)
    db.flush()
    db.add(
        CampusWhatsAppMessage(
            campaign_id=winner.id,
            member_id=recipient_member.id,
            phone="+919222222222",
            status="queued",
            callback_key="campus-race-message",
            attempts=0,
        )
    )
    db.commit()
    institution_id = institution.id
    winner_id = winner.id
    state, real_query = _hide_next_campaign_preflight(
        db, CampusWhatsAppCampaign, monkeypatch
    )
    as_user(owner)
    command = {
        "request_key": "campus-race-001",
        "template": "campus_announcement",
        "language": "en",
        "parameters": ["Hello campus"],
    }
    url = f"/api/v1/institutions/{institution_id}/pilot/whatsapp/campaigns"

    state["remaining"] = 1
    repeated = client.post(url, json=command)
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["id"] == winner_id
    assert real_query(CampusWhatsAppCampaign).count() == 1
    assert real_query(CampusWhatsAppMessage).count() == 1

    db.rollback()
    state["remaining"] = 1
    conflicting = client.post(
        url,
        json={**command, "parameters": ["Different campus message"]},
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["detail"] == (
        "That request key belongs to another campaign."
    )
    assert real_query(CampusWhatsAppCampaign).count() == 1
    assert real_query(CampusWhatsAppMessage).count() == 1
