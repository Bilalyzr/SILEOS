"""Bounded recipient expansion for WhatsApp campaigns.

The caller owns the request transaction. These helpers deliberately neither
commit nor roll it back, so the campaign claim, every message row, and the
campus audit record succeed or fail together.
"""

import secrets
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models.campus_pilot import CampusWhatsAppMessage
from app.models.institution import InstitutionBatchMember, InstitutionMember
from app.models.user import User
from app.models.whatsapp import WhatsAppContact, WhatsAppMessage


RECIPIENT_PAGE_SIZE = 500


def _message_values(*, campaign_id, recipient_key, rows, queued_at):
    return [
        {
            "campaign_id": campaign_id,
            recipient_key: recipient_id,
            "phone": phone,
            "status": "queued",
            "error": "",
            "callback_key": secrets.token_urlsafe(24),
            "attempts": 0,
            "next_attempt_at": queued_at,
            "last_event_at": 0,
            "updated_at": queued_at,
        }
        for recipient_id, phone in rows
    ]


def enqueue_global_recipients(db, *, campaign_id, roles):
    """Expand an account-role audience with bounded Core selects/inserts."""

    users = User.__table__
    contacts = WhatsAppContact.__table__
    messages = WhatsAppMessage.__table__
    audience = contacts.join(users, users.c.id == contacts.c.user_id)
    predicates = (
        users.c.is_active.is_(True),
        users.c.role.in_(roles),
        contacts.c.status == "confirmed",
    )

    # Fix the high-water mark before paging so accounts created during this
    # request cannot make the expansion unbounded.
    upper_id = db.execute(
        select(func.max(users.c.id)).select_from(audience).where(*predicates)
    ).scalar_one()
    if upper_id is None:
        return 0

    inserted = 0
    last_id = None
    queued_at = datetime.now(timezone.utc)
    while True:
        page_predicates = [*predicates, users.c.id <= upper_id]
        if last_id is not None:
            page_predicates.append(users.c.id > last_id)
        rows = db.execute(
            select(users.c.id, contacts.c.phone)
            .select_from(audience)
            .where(*page_predicates)
            .order_by(users.c.id)
            .limit(RECIPIENT_PAGE_SIZE)
        ).fetchall()
        if not rows:
            break

        values = _message_values(
            campaign_id=campaign_id,
            recipient_key="user_id",
            rows=rows,
            queued_at=queued_at,
        )
        db.execute(messages.insert(), values)
        inserted += len(values)
        last_id = rows[-1][0]

    return inserted


def enqueue_campus_recipients(
    db,
    *,
    campaign_id,
    institution_id,
    batch_id=None,
):
    """Expand an institution or batch audience in fixed-size keyset pages."""

    users = User.__table__
    contacts = WhatsAppContact.__table__
    members = InstitutionMember.__table__
    batch_members = InstitutionBatchMember.__table__
    messages = CampusWhatsAppMessage.__table__
    audience = members.join(contacts, contacts.c.user_id == members.c.user_id).join(
        users, users.c.id == members.c.user_id
    )
    predicates = [
        members.c.institution_id == institution_id,
        members.c.status == "active",
        users.c.is_active.is_(True),
        contacts.c.status == "confirmed",
    ]
    if batch_id is not None:
        audience = audience.join(
            batch_members, batch_members.c.member_id == members.c.id
        )
        predicates.append(batch_members.c.batch_id == batch_id)

    upper_id = db.execute(
        select(func.max(members.c.id)).select_from(audience).where(*predicates)
    ).scalar_one()
    if upper_id is None:
        return 0

    inserted = 0
    last_id = None
    queued_at = datetime.now(timezone.utc)
    while True:
        page_predicates = [*predicates, members.c.id <= upper_id]
        if last_id is not None:
            page_predicates.append(members.c.id > last_id)
        rows = db.execute(
            select(members.c.id, contacts.c.phone)
            .select_from(audience)
            .where(*page_predicates)
            .order_by(members.c.id)
            .limit(RECIPIENT_PAGE_SIZE)
        ).fetchall()
        if not rows:
            break

        values = _message_values(
            campaign_id=campaign_id,
            recipient_key="member_id",
            rows=rows,
            queued_at=queued_at,
        )
        db.execute(messages.insert(), values)
        inserted += len(values)
        last_id = rows[-1][0]

    return inserted
