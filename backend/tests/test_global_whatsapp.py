from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine

from app.models.campus_pilot import (
    CampusWhatsAppCampaign,
    CampusWhatsAppMessage,
    CampusWhatsAppWebhookEvent,
)
from app.models.institution import Institution, InstitutionMember
from app.models.whatsapp import (
    WhatsAppCampaign,
    WhatsAppContact,
    WhatsAppMessage,
    WhatsAppStatusReceipt,
)
from app.services import campus_whatsapp


ROOT = "/api/v1/whatsapp"


def _configure(monkeypatch):
    settings = campus_whatsapp.get_settings()
    values = {
        "WHATSAPP_PHONE_NUMBER_ID": "phone-id",
        "WHATSAPP_BUSINESS_ACCOUNT_ID": "business-id",
        "WHATSAPP_BUSINESS_PHONE": "+15550001111",
        "WHATSAPP_ACCESS_TOKEN": "test-access-secret",
        "WHATSAPP_APP_SECRET": "test-signing-secret",
        "WHATSAPP_VERIFY_TOKEN": "test-verify-secret",
        "WHATSAPP_API_VERSION": "v23.0",
        "WHATSAPP_APPROVED_TEMPLATES": "learning_update,campus_announcement",
    }
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)
    return values


def _signed(body, secret):
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _meta_payload(messages=None, statuses=None):
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


def test_account_whatsapp_consent_works_without_an_institution(
    client, as_user, make_user, db, monkeypatch
):
    values = _configure(monkeypatch)
    learner = make_user(role="student", email="global-learner@example.org")
    as_user(learner)

    initial = client.get(f"{ROOT}/status")
    assert initial.status_code == 200
    assert initial.json()["contact_status"] == "not_started"
    assert "test-access-secret" not in initial.text
    assert "test-signing-secret" not in initial.text

    pending = client.post(f"{ROOT}/opt-in", json={"phone": "+919876543210"})
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"
    contact = db.get(WhatsAppContact, learner.id)
    assert contact is not None
    assert contact.status == "pending"
    assert "JOIN" in pending.json()["click_to_chat_url"]

    payload = _meta_payload(
        messages=[
            {
                "id": "wamid.global-join",
                "from": "919876543210",
                "type": "text",
                "text": {"body": f"JOIN {contact.challenge}"},
            }
        ]
    )
    body = json.dumps(payload, separators=(",", ":")).encode()
    response = client.post(
        f"{ROOT}/webhook",
        content=body,
        headers={"x-hub-signature-256": _signed(body, values["WHATSAPP_APP_SECRET"])},
    )
    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(WhatsAppContact, learner.id).status == "confirmed"

    revoked = client.delete(f"{ROOT}/opt-in")
    assert revoked.status_code == 200
    assert revoked.json() == {"status": "revoked"}
    db.expire_all()
    assert db.get(WhatsAppContact, learner.id).status == "revoked"


def test_stop_revokes_the_phone_across_all_sashainfinity_accounts(
    client, make_user, db, monkeypatch
):
    values = _configure(monkeypatch)
    first = make_user(email="first-stop@example.org")
    second = make_user(role="parent", email="second-stop@example.org")
    creator = make_user(role="admin", email="stop-admin@example.org")
    for account in (first, second):
        db.add(
            WhatsAppContact(
                user_id=account.id,
                phone="+919999111122",
                status="confirmed",
                consent_at=datetime.now(timezone.utc),
            )
        )
    db.commit()
    campaign = WhatsAppCampaign(
        request_key="stop-cancel-001",
        template="learning_update",
        language="en",
        parameters=[],
        roles=["student", "parent"],
        header_image_url="",
        created_by=creator.id,
    )
    db.add(campaign)
    db.flush()
    db.add_all(
        [
            WhatsAppMessage(
                campaign_id=campaign.id,
                user_id=account.id,
                phone="+919999111122",
                status=state,
                callback_key=f"stop-cancel-{account.id}",
                attempts=1 if state == "retrying" else 0,
            )
            for account, state in ((first, "queued"), (second, "retrying"))
        ]
    )
    db.commit()

    payload = _meta_payload(
        messages=[
            {
                "id": "wamid.global-stop",
                "from": "919999111122",
                "type": "text",
                "text": {"body": "STOP"},
            }
        ]
    )
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"x-hub-signature-256": _signed(body, values["WHATSAPP_APP_SECRET"])}
    first_response = client.post(f"{ROOT}/webhook", content=body, headers=headers)
    assert first_response.status_code == 200, first_response.text
    second_response = client.post(f"{ROOT}/webhook", content=body, headers=headers)
    assert second_response.status_code == 200, second_response.text
    db.expire_all()
    assert {
        db.get(WhatsAppContact, first.id).status,
        db.get(WhatsAppContact, second.id).status,
    } == {"revoked"}
    assert {
        row.status
        for row in db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.campaign_id == campaign.id)
        .all()
    } == {"cancelled"}
    assert (
        db.query(CampusWhatsAppWebhookEvent)
        .filter_by(event_key="message:wamid.global-stop")
        .count()
        == 1
    )


def test_app_opt_out_cancels_undispatched_global_and_campus_messages(
    client, as_user, make_user, db
):
    account = make_user(email="opt-out-cancel@example.org")
    creator = make_user(role="admin", email="opt-out-cancel-admin@example.org")
    institution = Institution(
        name="Consent Boundary College",
        slug="consent-boundary-college",
        kind="college",
        academic_year="2026-27",
        timezone="Asia/Kolkata",
        description="",
        plan="starter",
    )
    db.add(institution)
    db.flush()
    member = InstitutionMember(
        institution_id=institution.id,
        user_id=account.id,
        role="student",
        department="Science",
        status="active",
    )
    db.add_all(
        [
            member,
            WhatsAppContact(
                user_id=account.id,
                phone="+919777777777",
                status="confirmed",
                consent_at=datetime.now(timezone.utc),
            ),
        ]
    )
    global_campaigns = [
        WhatsAppCampaign(
            request_key=f"optout-global-{suffix}",
            template="learning_update",
            language="en",
            parameters=[],
            roles=["student"],
            header_image_url="",
            created_by=creator.id,
        )
        for suffix in ("queued", "sending")
    ]
    campus_campaigns = [
        CampusWhatsAppCampaign(
            institution_id=institution.id,
            request_key=f"optout-campus-{suffix}",
            template="campus_announcement",
            language="en",
            parameters=[],
            batch_id=None,
            header_image_url="",
            created_by=creator.id,
        )
        for suffix in ("retrying", "sending")
    ]
    db.add_all(global_campaigns + campus_campaigns)
    db.flush()
    messages = [
        WhatsAppMessage(
            campaign_id=global_campaigns[0].id,
            user_id=account.id,
            phone="+919777777777",
            status="queued",
            callback_key="optout-global-queued",
            attempts=0,
        ),
        WhatsAppMessage(
            campaign_id=global_campaigns[1].id,
            user_id=account.id,
            phone="+919777777777",
            status="sending",
            callback_key="optout-global-sending",
            attempts=1,
        ),
        CampusWhatsAppMessage(
            campaign_id=campus_campaigns[0].id,
            member_id=member.id,
            phone="+919777777777",
            status="retrying",
            callback_key="optout-campus-retrying",
            attempts=1,
        ),
        CampusWhatsAppMessage(
            campaign_id=campus_campaigns[1].id,
            member_id=member.id,
            phone="+919777777777",
            status="sending",
            callback_key="optout-campus-sending",
            attempts=1,
        ),
    ]
    db.add_all(messages)
    db.commit()

    as_user(account)
    response = client.delete(f"{ROOT}/opt-in")
    assert response.status_code == 200
    db.expire_all()
    assert db.get(WhatsAppContact, account.id).status == "revoked"
    states = {row.callback_key: row.status for row in messages}
    assert states == {
        "optout-global-queued": "cancelled",
        "optout-global-sending": "sending",
        "optout-campus-retrying": "cancelled",
        "optout-campus-sending": "sending",
    }
    assert all(
        row.error == "Recipient opted out before dispatch."
        for row in messages
        if row.status == "cancelled"
    )


def test_admin_directory_and_campaigns_are_role_scoped_and_consent_safe(
    client, as_user, auth_headers, make_user, db, monkeypatch
):
    _configure(monkeypatch)
    admin = make_user(role="admin", email="communications-admin@example.org")
    learner = make_user(role="student", email="communications-learner@example.org")
    instructor = make_user(
        role="instructor", email="communications-instructor@example.org"
    )
    parent = make_user(role="parent", email="communications-parent@example.org")
    inactive = make_user(role="student", email="inactive-learner@example.org")
    inactive.is_active = False
    for account, phone, state in (
        (learner, "+919111111111", "confirmed"),
        (instructor, "+919222222222", "confirmed"),
        (parent, "+919333333333", "revoked"),
        (inactive, "+919444444444", "confirmed"),
    ):
        db.add(
            WhatsAppContact(
                user_id=account.id,
                phone=phone,
                status=state,
                consent_at=datetime.now(timezone.utc) if state == "confirmed" else None,
            )
        )
    db.commit()

    student_headers = auth_headers(learner.user_email, learner._test_password)
    denied = client.get(f"{ROOT}/admin/overview", headers=student_headers)
    assert denied.status_code == 403

    as_user(admin)
    overview = client.get(f"{ROOT}/admin/overview")
    assert overview.status_code == 200
    assert overview.json()["eligible_by_role"]["student"] == 1
    assert overview.json()["eligible_by_role"]["instructor"] == 1
    assert "parent" in overview.json()["eligible_by_role"]
    assert "superadmin" in overview.json()["eligible_by_role"]

    directory = client.get(
        f"{ROOT}/admin/contacts", params={"role": "student", "status": "confirmed"}
    )
    assert directory.status_code == 200
    row = next(
        item for item in directory.json()["items"] if item["user_id"] == learner.id
    )
    assert row["phone"].endswith("1111")
    assert row["phone"] != "+919111111111"

    monkeypatch.setattr(campus_whatsapp, "deliver_pending", lambda limit=100: None)
    command = {
        "request_key": "platform-learning-001",
        "template": "learning_update",
        "language": "en",
        "parameters": ["New recommendations are ready"],
        "roles": [
            "student",
            "instructor",
            "admin",
            "superadmin",
            "spoc",
            "parent",
            "company",
            "company_manager",
        ],
        "header_image_url": "https://cdn.example.org/sasha-banner.png",
    }
    created = client.post(f"{ROOT}/admin/campaigns", json=command)
    assert created.status_code == 201, created.text
    assert created.json()["recipient_count"] == 2
    repeated = client.post(f"{ROOT}/admin/campaigns", json=command)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == created.json()["id"]
    assert db.query(WhatsAppCampaign).count() == 1
    assert db.query(WhatsAppMessage).count() == 2

    message = db.query(WhatsAppMessage).filter_by(user_id=learner.id).one()
    db.get(WhatsAppContact, learner.id).status = "revoked"
    db.commit()

    @contextmanager
    def session():
        yield db

    def unexpected_provider_call(*_args, **_kwargs):
        raise AssertionError("Provider must not be called after consent is withdrawn")

    monkeypatch.setattr(campus_whatsapp, "SessionLocal", session)
    monkeypatch.setattr(campus_whatsapp.httpx, "post", unexpected_provider_call)
    campus_whatsapp.deliver_global(message.id)
    db.refresh(message)
    assert message.status == "cancelled"


def test_early_delivery_receipt_is_reconciled_after_provider_id_is_committed(
    client, make_user, db, monkeypatch
):
    values = _configure(monkeypatch)
    creator = make_user(role="admin", email="early-receipt-admin@example.org")
    recipient = make_user(email="early-receipt-user@example.org")
    campaign = WhatsAppCampaign(
        request_key="early-receipt-001",
        template="learning_update",
        language="en",
        parameters=[],
        roles=["student"],
        header_image_url="",
        created_by=creator.id,
    )
    db.add(campaign)
    db.flush()
    db.add(
        WhatsAppContact(
            user_id=recipient.id,
            phone="+919111222233",
            status="confirmed",
            consent_at=datetime.now(timezone.utc),
        )
    )
    message = WhatsAppMessage(
        campaign_id=campaign.id,
        user_id=recipient.id,
        phone="+919111222233",
        status="queued",
        callback_key="early-receipt-callback",
        attempts=0,
    )
    db.add(message)
    db.commit()

    payload = _meta_payload(
        statuses=[{"id": "wamid.early", "status": "read", "timestamp": "200"}]
    )
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"x-hub-signature-256": _signed(body, values["WHATSAPP_APP_SECRET"])}

    early = client.post(f"{ROOT}/webhook", content=body, headers=headers)
    assert early.status_code == 200
    assert db.query(CampusWhatsAppWebhookEvent).count() == 0
    assert db.query(WhatsAppStatusReceipt).count() == 1

    class ProviderResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"messages": [{"id": "wamid.early"}]}

    @contextmanager
    def session():
        yield db

    monkeypatch.setattr(campus_whatsapp, "SessionLocal", session)
    monkeypatch.setattr(
        campus_whatsapp.httpx, "post", lambda *_args, **_kwargs: ProviderResponse()
    )
    campus_whatsapp.deliver_global(message.id)
    db.refresh(message)
    assert message.status == "read"
    assert message.provider_id == "wamid.early"
    assert db.query(WhatsAppStatusReceipt).count() == 0
    assert db.query(CampusWhatsAppWebhookEvent).count() == 1

    duplicate = client.post(f"{ROOT}/webhook", content=body, headers=headers)
    assert duplicate.status_code == 200
    assert db.query(CampusWhatsAppWebhookEvent).count() == 1


def test_foreign_status_receipt_is_acknowledged_once_and_expires(
    client, db, monkeypatch
):
    values = _configure(monkeypatch)
    payload = _meta_payload(
        statuses=[{"id": "wamid.foreign", "status": "delivered", "timestamp": "300"}]
    )
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"x-hub-signature-256": _signed(body, values["WHATSAPP_APP_SECRET"])}

    assert (
        client.post(f"{ROOT}/webhook", content=body, headers=headers).status_code == 200
    )
    assert (
        client.post(f"{ROOT}/webhook", content=body, headers=headers).status_code == 200
    )
    receipt = db.query(WhatsAppStatusReceipt).one()
    assert receipt.provider_id == "wamid.foreign"

    result = campus_whatsapp.reconcile_status_receipts(db)
    db.refresh(receipt)
    assert result["deferred"] == 1
    assert receipt.attempts == 1

    receipt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    result = campus_whatsapp.reconcile_status_receipts(db)
    assert result["expired"] == 1
    assert db.query(WhatsAppStatusReceipt).count() == 0
    assert db.query(CampusWhatsAppWebhookEvent).count() == 0


def test_stale_sending_messages_are_reclaimed_but_fresh_claims_are_left_alone(
    make_user, db, monkeypatch
):
    _configure(monkeypatch)
    creator = make_user(role="admin", email="lease-admin@example.org")
    stale_user = make_user(email="stale-lease-user@example.org")
    fresh_user = make_user(email="fresh-lease-user@example.org")
    for account, phone in (
        (stale_user, "+919100000001"),
        (fresh_user, "+919100000002"),
    ):
        db.add(
            WhatsAppContact(
                user_id=account.id,
                phone=phone,
                status="confirmed",
                consent_at=datetime.now(timezone.utc),
            )
        )
    campaign = WhatsAppCampaign(
        request_key="sending-lease-001",
        template="learning_update",
        language="en",
        parameters=[],
        roles=["student"],
        header_image_url="",
        created_by=creator.id,
    )
    db.add(campaign)
    db.flush()
    stale = WhatsAppMessage(
        campaign_id=campaign.id,
        user_id=stale_user.id,
        phone="+919100000001",
        status="sending",
        callback_key="stale-lease-callback",
        attempts=1,
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    fresh = WhatsAppMessage(
        campaign_id=campaign.id,
        user_id=fresh_user.id,
        phone="+919100000002",
        status="sending",
        callback_key="fresh-lease-callback",
        attempts=1,
        updated_at=datetime.now(timezone.utc),
    )
    db.add_all([stale, fresh])
    db.commit()

    @contextmanager
    def session():
        yield db

    selected = []
    actual_deliver_global = campus_whatsapp.deliver_global
    monkeypatch.setattr(campus_whatsapp, "SessionLocal", session)
    monkeypatch.setattr(campus_whatsapp, "deliver_global", selected.append)
    campus_whatsapp.deliver_pending()
    assert selected == [stale.id]

    class ProviderResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"messages": [{"id": "wamid.reclaimed"}]}

    calls = []

    def provider_post(*args, **kwargs):
        calls.append((args, kwargs))
        return ProviderResponse()

    monkeypatch.setattr(campus_whatsapp.httpx, "post", provider_post)
    actual_deliver_global(stale.id)
    actual_deliver_global(fresh.id)
    db.refresh(stale)
    db.refresh(fresh)
    assert stale.status == "sent"
    assert stale.provider_id == "wamid.reclaimed"
    assert fresh.status == "sending"
    assert len(calls) == 1


def test_global_whatsapp_migration_consolidates_legacy_consent_and_round_trips():
    path = Path(__file__).parents[1] / "alembic/versions/0034_global_whatsapp.py"
    spec = importlib.util.spec_from_file_location("global_whatsapp_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    members = sa.Table(
        "institution_members",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
    )
    legacy = sa.Table(
        "campus_whatsapp_contacts",
        metadata,
        sa.Column("member_id", sa.Integer, primary_key=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("challenge", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("consent_at", sa.DateTime(timezone=True)),
    )
    sa.Table(
        "campus_whatsapp_messages",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
    )
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(users.insert(), [{"id": 1}, {"id": 2}, {"id": 3}])
        connection.execute(
            members.insert(),
            [
                {"id": 10, "user_id": 1},
                {"id": 11, "user_id": 1},
                {"id": 12, "user_id": 2},
            ],
        )
        connection.execute(
            legacy.insert(),
            [
                {
                    "member_id": 10,
                    "phone": "+911111111111",
                    "status": "confirmed",
                    "challenge": None,
                    "expires_at": None,
                    "consent_at": now,
                },
                {
                    "member_id": 11,
                    "phone": "+911111111111",
                    "status": "revoked",
                    "challenge": None,
                    "expires_at": None,
                    "consent_at": None,
                },
                {
                    "member_id": 12,
                    "phone": "+922222222222",
                    "status": "pending",
                    "challenge": "JOINME",
                    "expires_at": now,
                    "consent_at": None,
                },
            ],
        )
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()

        inspector = sa.inspect(connection)
        assert "whatsapp_status_receipts" in inspector.get_table_names()
        assert "ix_whatsapp_contacts_phone" in {
            row["name"] for row in inspector.get_indexes("whatsapp_contacts")
        }
        assert "ix_whatsapp_messages_delivery_due" in {
            row["name"] for row in inspector.get_indexes("whatsapp_messages")
        }
        assert "ix_whatsapp_status_receipts_provider_id" in {
            row["name"] for row in inspector.get_indexes("whatsapp_status_receipts")
        }
        assert "ix_whatsapp_status_receipts_due" in {
            row["name"] for row in inspector.get_indexes("whatsapp_status_receipts")
        }
        assert "ix_campus_whatsapp_messages_delivery_due" in {
            row["name"] for row in inspector.get_indexes("campus_whatsapp_messages")
        }

        contacts = sa.Table(
            "whatsapp_contacts", sa.MetaData(), autoload_with=connection
        )
        rows = {
            row.user_id: row
            for row in connection.execute(sa.select(contacts)).mappings()
        }
        assert rows[1].status == "revoked"
        assert rows[1].challenge is None
        assert rows[2].status == "pending"
        assert rows[2].challenge == "JOINME"

        campaigns = sa.Table(
            "whatsapp_campaigns", sa.MetaData(), autoload_with=connection
        )
        messages = sa.Table(
            "whatsapp_messages", sa.MetaData(), autoload_with=connection
        )
        connection.execute(
            contacts.insert().values(
                user_id=3,
                phone="+933333333333",
                status="confirmed",
                challenge=None,
                expires_at=None,
                consent_at=now,
            )
        )
        campaign_id = connection.execute(
            campaigns.insert()
            .values(
                request_key="fk-delete-001",
                template="learning_update",
                language="en",
                parameters=[],
                roles=["student"],
                header_image_url="",
                created_by=3,
            )
            .returning(campaigns.c.id)
        ).scalar_one()
        connection.execute(
            messages.insert().values(
                campaign_id=campaign_id,
                user_id=3,
                phone="+933333333333",
                status="queued",
                provider_id=None,
                error="",
                callback_key="fk-delete-callback",
                attempts=0,
                last_event_at=0,
            )
        )
        connection.execute(users.delete().where(users.c.id == 3))
        assert (
            connection.execute(
                sa.select(sa.func.count())
                .select_from(contacts)
                .where(contacts.c.user_id == 3)
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                sa.select(sa.func.count())
                .select_from(messages)
                .where(messages.c.user_id == 3)
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                sa.select(campaigns.c.created_by).where(campaigns.c.id == campaign_id)
            ).scalar_one()
            is None
        )

        connection.execute(
            contacts.update()
            .where(contacts.c.user_id == 2)
            .values(status="confirmed", challenge=None, expires_at=None, consent_at=now)
        )
        module.downgrade()
        restored = connection.execute(
            sa.select(legacy.c.status).where(legacy.c.member_id == 12)
        ).scalar_one()
        assert restored == "confirmed"
        inspector = sa.inspect(connection)
        assert "whatsapp_contacts" not in inspector.get_table_names()
        assert "whatsapp_status_receipts" not in inspector.get_table_names()
        assert "ix_campus_whatsapp_messages_delivery_due" not in {
            row["name"] for row in inspector.get_indexes("campus_whatsapp_messages")
        }
