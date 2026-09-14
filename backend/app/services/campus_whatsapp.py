"""Meta WhatsApp Cloud API adapter with explicit consent and durable retries."""

import hashlib
import hmac
import logging
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.campus_pilot import (
    CampusWhatsAppCampaign,
    CampusWhatsAppMessage,
    CampusWhatsAppWebhookEvent,
)
from app.models.institution import InstitutionBatchMember, InstitutionMember
from app.models.user import User
from app.models.whatsapp import (
    WhatsAppCampaign,
    WhatsAppContact,
    WhatsAppMessage,
    WhatsAppStatusReceipt,
)
from app.services.institution_service import utc


log = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
SENDING_LEASE = timedelta(minutes=5)
STATUS_RECEIPT_RETENTION = timedelta(days=7)
STATUS_RECEIPT_MAX_BACKOFF = timedelta(hours=6)
STATUS_RECEIPT_BATCH = 200
DELIVERY_CONCURRENCY = 4
_DELIVERY_TICK_LOCK = threading.Lock()


def approved_templates():
    raw = get_settings().WHATSAPP_APPROVED_TEMPLATES
    return sorted(
        {
            item.strip()
            for item in raw.split(",")
            if item.strip() and item.strip().replace("_", "a").isalnum()
        }
    )


def configuration_status():
    settings = get_settings()
    values = {
        "WHATSAPP_PHONE_NUMBER_ID": settings.WHATSAPP_PHONE_NUMBER_ID,
        "WHATSAPP_BUSINESS_ACCOUNT_ID": settings.WHATSAPP_BUSINESS_ACCOUNT_ID,
        "WHATSAPP_BUSINESS_PHONE": settings.WHATSAPP_BUSINESS_PHONE,
        "WHATSAPP_ACCESS_TOKEN": settings.WHATSAPP_ACCESS_TOKEN,
        "WHATSAPP_APP_SECRET": settings.WHATSAPP_APP_SECRET,
        "WHATSAPP_VERIFY_TOKEN": settings.WHATSAPP_VERIFY_TOKEN,
    }
    missing = [name for name, value in values.items() if not value]
    return {
        "configured": not missing,
        "api_version": settings.WHATSAPP_API_VERSION,
        "phone_number_configured": bool(settings.WHATSAPP_PHONE_NUMBER_ID),
        "business_account_configured": bool(settings.WHATSAPP_BUSINESS_ACCOUNT_ID),
        "business_phone_configured": bool(settings.WHATSAPP_BUSINESS_PHONE),
        "webhook_ready": bool(
            settings.WHATSAPP_APP_SECRET and settings.WHATSAPP_VERIFY_TOKEN
        ),
        "approved_templates": approved_templates(),
        "missing_fields": missing,
        "missing_settings": missing,
        "display_phone_number": settings.WHATSAPP_BUSINESS_PHONE or None,
    }


def click_to_chat(challenge):
    number = "".join(
        ch for ch in get_settings().WHATSAPP_BUSINESS_PHONE if ch.isdigit()
    )
    if not number:
        return None
    return f"https://wa.me/{number}?text={quote('JOIN ' + challenge)}"


def contact_status(contact):
    """Return the public account-level consent fields without server secrets."""

    return {
        "opted_in": bool(contact and contact.status == "confirmed"),
        "contact_status": contact.status if contact else "not_started",
        "phone": contact.phone if contact else None,
        "consent_at": utc(contact.consent_at).isoformat()
        if contact and contact.consent_at
        else None,
        "join_url": click_to_chat(contact.challenge)
        if contact and contact.status == "pending" and contact.challenge
        else None,
        "join_expires_at": utc(contact.expires_at).isoformat()
        if contact and contact.expires_at
        else None,
    }


def begin_opt_in(db, user_id, phone):
    """Start signed inbound verification for one SashaInfinity account."""

    configuration = configuration_status()
    if (
        not configuration["business_phone_configured"]
        or not configuration["webhook_ready"]
    ):
        return None
    row = db.query(WhatsAppContact).filter_by(user_id=user_id).with_for_update().first()
    if row and row.status == "confirmed" and row.phone == phone:
        return {
            "status": "confirmed",
            "click_to_chat_url": None,
            "expires_at": None,
            "consent_at": utc(row.consent_at).isoformat() if row.consent_at else None,
        }
    challenge = secrets.token_urlsafe(9)
    if not row:
        row = WhatsAppContact(user_id=user_id)
        db.add(row)
    row.phone = phone
    row.status = "pending"
    row.challenge = challenge
    row.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    row.consent_at = None
    db.commit()
    return {
        "status": "pending",
        "click_to_chat_url": click_to_chat(challenge),
        "expires_at": utc(row.expires_at).isoformat(),
        "consent_at": None,
    }


def _cancel_undispatched_for_users(db, user_ids):
    """Cancel work that has not crossed the outbound dispatch boundary.

    A `sending` row has already been claimed by a worker and is treated as in
    flight: WhatsApp cannot recall it reliably. Queued and retrying rows are
    cancelled in the same transaction as consent withdrawal, so a later worker
    cannot claim them after the opt-out commits.
    """

    user_ids = tuple(sorted(set(user_ids)))
    if not user_ids:
        return {"global": 0, "campus": 0}
    now = datetime.now(timezone.utc)
    values = {
        "status": "cancelled",
        "error": "Recipient opted out before dispatch.",
        "updated_at": now,
    }
    global_count = (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.user_id.in_(user_ids),
            WhatsAppMessage.status.in_(("queued", "retrying")),
        )
        .update(values, synchronize_session=False)
    )
    member_ids = select(InstitutionMember.id).where(
        InstitutionMember.user_id.in_(user_ids)
    )
    campus_count = (
        db.query(CampusWhatsAppMessage)
        .filter(
            CampusWhatsAppMessage.member_id.in_(member_ids),
            CampusWhatsAppMessage.status.in_(("queued", "retrying")),
        )
        .update(values, synchronize_session=False)
    )
    return {"global": global_count, "campus": campus_count}


def revoke_opt_in(db, user_id):
    """Withdraw consent and cancel every message not already in flight."""

    row = db.query(WhatsAppContact).filter_by(user_id=user_id).with_for_update().first()
    if row:
        row.status = "revoked"
        row.challenge = None
        row.expires_at = None
    _cancel_undispatched_for_users(db, [user_id])
    db.commit()
    return {"status": "revoked"}


def verify_signature(body, signature):
    secret = get_settings().WHATSAPP_APP_SECRET
    if not secret or not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[7:])


def _template_payload(campaign, message):
    components = []
    if campaign.header_image_url:
        components.append(
            {
                "type": "header",
                "parameters": [
                    {"type": "image", "image": {"link": campaign.header_image_url}}
                ],
            }
        )
    if campaign.parameters:
        components.append(
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": value} for value in campaign.parameters
                ],
            }
        )
    template = {
        "name": campaign.template,
        "language": {"code": campaign.language},
    }
    if components:
        template["components"] = components
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.phone.lstrip("+"),
        "type": "template",
        "template": template,
    }


def _send_template(db, settings, campaign, message, warning):
    """Make one provider attempt and persist its retry-safe result."""

    try:
        response = httpx.post(
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json=_template_payload(campaign, message),
            timeout=15,
        )
        response.raise_for_status()
        provider_id = response.json().get("messages", [{}])[0].get("id")
        if not provider_id:
            raise ValueError("Provider response did not include a message id.")
        message.provider_id = provider_id
        message.status = "sent"
        message.error = ""
    except Exception:
        # Provider bodies can contain request data; keep the durable error generic.
        log.warning(warning, exc_info=False)
        if message.attempts >= MAX_ATTEMPTS:
            message.status = "failed"
            message.error = "Delivery failed after the retry limit."
        else:
            message.status = "retrying"
            message.error = "Temporary delivery failure; retry scheduled."
            message.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                minutes=2**message.attempts
            )
    db.commit()
    if message.provider_id:
        # A signed delivery receipt can reach our webhook before the provider
        # response above is committed. Resolve that durable inbox entry as soon
        # as the provider id becomes visible; the maintenance worker is the
        # fallback for the opposite transaction ordering.
        try:
            reconcile_status_receipts(db, provider_id=message.provider_id)
        except Exception:
            db.rollback()
            log.warning("WhatsApp status receipt reconciliation failed", exc_info=False)


def deliver(message_id):
    settings = get_settings()
    with SessionLocal() as db:
        message = (
            db.query(CampusWhatsAppMessage)
            .filter_by(id=message_id)
            .with_for_update()
            .first()
        )
        now = datetime.now(timezone.utc)
        stale_sending = bool(
            message
            and message.status == "sending"
            and (
                not message.updated_at or utc(message.updated_at) <= now - SENDING_LEASE
            )
        )
        if not message or (
            message.status not in ("queued", "retrying") and not stale_sending
        ):
            return
        if (
            not stale_sending
            and message.next_attempt_at
            and utc(message.next_attempt_at) > now
        ):
            return
        campaign = db.get(CampusWhatsAppCampaign, message.campaign_id)
        member = db.get(InstitutionMember, message.member_id)
        account = db.get(User, member.user_id) if member else None
        contact = db.get(WhatsAppContact, member.user_id) if member else None
        in_batch = True
        if campaign and campaign.batch_id and member:
            in_batch = bool(
                db.query(InstitutionBatchMember.id)
                .filter_by(batch_id=campaign.batch_id, member_id=member.id)
                .first()
            )
        if (
            not campaign
            or not member
            or not account
            or not account.is_active
            or member.status != "active"
            or member.institution_id != campaign.institution_id
            or not in_batch
            or not contact
            or contact.status != "confirmed"
            or contact.phone != message.phone
        ):
            message.status = "cancelled"
            message.error = "Recipient is no longer eligible or opted in."
            db.commit()
            return
        if campaign.template not in approved_templates():
            message.status = "cancelled"
            message.error = "Template is no longer approved."
            db.commit()
            return

        message.attempts += 1
        message.status = "sending"
        db.commit()
        _send_template(
            db, settings, campaign, message, "WhatsApp message delivery failed"
        )


def deliver_global(message_id):
    """Deliver one platform campaign message after rechecking its audience."""

    settings = get_settings()
    with SessionLocal() as db:
        message = (
            db.query(WhatsAppMessage).filter_by(id=message_id).with_for_update().first()
        )
        now = datetime.now(timezone.utc)
        stale_sending = bool(
            message
            and message.status == "sending"
            and (
                not message.updated_at or utc(message.updated_at) <= now - SENDING_LEASE
            )
        )
        if not message or (
            message.status not in ("queued", "retrying") and not stale_sending
        ):
            return
        if (
            not stale_sending
            and message.next_attempt_at
            and utc(message.next_attempt_at) > now
        ):
            return
        campaign = db.get(WhatsAppCampaign, message.campaign_id)
        account = db.get(User, message.user_id)
        contact = db.get(WhatsAppContact, message.user_id)
        if (
            not campaign
            or not account
            or not account.is_active
            or account.role not in (campaign.roles or [])
            or not contact
            or contact.status != "confirmed"
            or contact.phone != message.phone
        ):
            message.status = "cancelled"
            message.error = "Recipient is no longer eligible or opted in."
            db.commit()
            return
        if campaign.template not in approved_templates():
            message.status = "cancelled"
            message.error = "Template is no longer approved."
            db.commit()
            return

        message.attempts += 1
        message.status = "sending"
        db.commit()
        _send_template(
            db,
            settings,
            campaign,
            message,
            "WhatsApp platform message delivery failed",
        )


def _due_message_ids(db, model, now, stale_before, limit):
    return [
        message_id
        for message_id, in db.query(model.id)
        .filter(
            or_(
                and_(
                    model.status.in_(("queued", "retrying")),
                    model.next_attempt_at <= now,
                ),
                and_(
                    model.status == "sending",
                    or_(
                        model.updated_at.is_(None),
                        model.updated_at <= stale_before,
                    ),
                ),
            )
        )
        .order_by(model.id)
        .limit(limit)
    ]


def _interleave_delivery_jobs(campus_ids, global_ids, limit):
    jobs = []
    for index in range(max(len(campus_ids), len(global_ids))):
        if index < len(campus_ids):
            jobs.append(("campus", campus_ids[index]))
        if index < len(global_ids):
            jobs.append(("global", global_ids[index]))
    return jobs[:limit]


def _session_uses_sqlite(db):
    try:
        bind = db.get_bind()
    except (AttributeError, TypeError):
        bind = getattr(db, "bind", None)
    return getattr(getattr(bind, "dialect", None), "name", None) == "sqlite"


def deliver_pending(limit=100, max_workers=DELIVERY_CONCURRENCY):
    """Run one bounded delivery tick without overlapping another local tick."""

    if not _DELIVERY_TICK_LOCK.acquire(blocking=False):
        log.debug("Skipping overlapping WhatsApp delivery tick")
        return

    try:
        limit = max(0, int(limit))
        now = datetime.now(timezone.utc)
        stale_before = now - SENDING_LEASE
        with SessionLocal() as db:
            reconcile_status_receipts(
                db, limit=min(STATUS_RECEIPT_BATCH, max(limit, 1) * 2)
            )
            campus_ids = _due_message_ids(
                db, CampusWhatsAppMessage, now, stale_before, limit
            )
            global_ids = _due_message_ids(db, WhatsAppMessage, now, stale_before, limit)
            use_single_worker = _session_uses_sqlite(db)

        jobs = _interleave_delivery_jobs(campus_ids, global_ids, limit)
        if not jobs:
            return

        requested_workers = (
            DELIVERY_CONCURRENCY if max_workers is None else int(max_workers)
        )
        worker_count = min(
            len(jobs),
            DELIVERY_CONCURRENCY,
            max(1, requested_workers),
        )
        if use_single_worker:
            worker_count = 1

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(
                    deliver if queue == "campus" else deliver_global,
                    message_id,
                ): (queue, message_id)
                for queue, message_id in jobs
            }
            for future in as_completed(futures):
                queue, message_id = futures[future]
                try:
                    future.result()
                except Exception:
                    log.exception(
                        "WhatsApp %s delivery job failed for message %s",
                        queue,
                        message_id,
                    )
    finally:
        _DELIVERY_TICK_LOCK.release()


def _claim_webhook_event(db, event_key, event_type):
    if db.query(CampusWhatsAppWebhookEvent).filter_by(event_key=event_key).first():
        return False
    try:
        with db.begin_nested():
            db.add(
                CampusWhatsAppWebhookEvent(
                    event_key=event_key[:250], event_type=event_type
                )
            )
            db.flush()
        return True
    except IntegrityError:
        return False


def _status_event_key(provider_id, value, timestamp):
    raw = f"status:{provider_id}:{value}:{timestamp}"
    if len(raw) <= 250:
        return raw
    return f"status:sha256:{hashlib.sha256(raw.encode()).hexdigest()}"


def _status_message(db, provider_id):
    message = db.query(CampusWhatsAppMessage).filter_by(provider_id=provider_id).first()
    if not message:
        message = db.query(WhatsAppMessage).filter_by(provider_id=provider_id).first()
    return message


def _apply_status(message, value, timestamp):
    if timestamp < message.last_event_at:
        return
    rank = {
        "queued": 0,
        "retrying": 0,
        "sending": 0,
        "sent": 1,
        "delivered": 2,
        "read": 3,
    }
    if value == "failed":
        if message.status not in ("delivered", "read"):
            message.status = "failed"
            message.error = "The provider reported that delivery failed."
    elif rank.get(value, 0) >= rank.get(message.status, 0):
        message.status = value
        message.error = ""
    message.last_event_at = timestamp


def _store_status_receipt(db, event_key, provider_id, value, timestamp):
    if db.query(WhatsAppStatusReceipt).filter_by(event_key=event_key).first():
        return
    now = datetime.now(timezone.utc)
    try:
        with db.begin_nested():
            db.add(
                WhatsAppStatusReceipt(
                    event_key=event_key,
                    provider_id=provider_id,
                    status=value,
                    event_at=timestamp,
                    attempts=0,
                    next_attempt_at=now,
                    expires_at=now + STATUS_RECEIPT_RETENTION,
                )
            )
            db.flush()
    except IntegrityError:
        # A concurrent delivery of the same signed webhook stored it first.
        pass


def _receipt_backoff(attempts):
    seconds = min(
        int(STATUS_RECEIPT_MAX_BACKOFF.total_seconds()),
        30 * (2 ** min(attempts, 10)),
    )
    return timedelta(seconds=seconds)


def reconcile_status_receipts(db, provider_id=None, limit=STATUS_RECEIPT_BATCH):
    """Resolve early provider receipts and age out permanently foreign ids.

    Provider-specific reconciliation ignores backoff and runs immediately
    after a successful send commits its provider id. The periodic path retries
    unmatched rows with bounded exponential backoff for seven days, then
    removes them. Webhook callers are always acknowledged and never need to
    retry an id that does not belong to this deployment.
    """

    now = datetime.now(timezone.utc)
    expired = (
        db.query(WhatsAppStatusReceipt)
        .filter(WhatsAppStatusReceipt.expires_at <= now)
        .delete(synchronize_session=False)
    )
    query = db.query(WhatsAppStatusReceipt).filter(
        WhatsAppStatusReceipt.expires_at > now
    )
    if provider_id:
        query = query.filter(WhatsAppStatusReceipt.provider_id == provider_id)
    else:
        query = query.filter(WhatsAppStatusReceipt.next_attempt_at <= now)
    receipts = (
        query.order_by(WhatsAppStatusReceipt.event_at, WhatsAppStatusReceipt.id)
        .limit(max(1, limit))
        .all()
    )
    resolved = 0
    for receipt in receipts:
        message = _status_message(db, receipt.provider_id)
        if not message:
            receipt.attempts += 1
            receipt.next_attempt_at = now + _receipt_backoff(receipt.attempts)
            continue
        if _claim_webhook_event(db, receipt.event_key, "status"):
            _apply_status(message, receipt.status, receipt.event_at)
        db.delete(receipt)
        resolved += 1
    db.commit()
    return {
        "resolved": resolved,
        "deferred": len(receipts) - resolved,
        "expired": expired,
    }


def _process_inbound(db, message):
    message_id = str(message.get("id", ""))
    phone = "+" + "".join(ch for ch in str(message.get("from", "")) if ch.isdigit())
    text = str(message.get("text", {}).get("body", "")).strip()
    if (
        not message_id
        or not phone
        or not _claim_webhook_event(db, f"message:{message_id}", "message")
    ):
        return
    upper = text.upper()
    if upper == "STOP":
        contacts = (
            db.query(WhatsAppContact).filter_by(phone=phone).with_for_update().all()
        )
        for contact in contacts:
            contact.status = "revoked"
            contact.challenge = None
            contact.expires_at = None
        _cancel_undispatched_for_users(db, [contact.user_id for contact in contacts])
        return
    if not upper.startswith("JOIN "):
        return
    challenge = text[5:].strip()
    contact = (
        db.query(WhatsAppContact)
        .filter_by(phone=phone, challenge=challenge, status="pending")
        .first()
    )
    if (
        not contact
        or not contact.expires_at
        or utc(contact.expires_at) <= datetime.now(timezone.utc)
    ):
        return
    contact.status = "confirmed"
    contact.consent_at = datetime.now(timezone.utc)
    contact.challenge = None
    contact.expires_at = None


def _process_status(db, status):
    provider_id = str(status.get("id", ""))
    value = str(status.get("status", "")).lower()
    try:
        timestamp = int(status.get("timestamp", 0) or 0)
    except (TypeError, ValueError):
        return
    if (
        value not in ("sent", "delivered", "read", "failed")
        or not provider_id
        or len(provider_id) > 250
    ):
        return
    key = _status_event_key(provider_id, value, timestamp)
    if db.query(CampusWhatsAppWebhookEvent).filter_by(event_key=key).first():
        return
    message = _status_message(db, provider_id)
    if not message:
        _store_status_receipt(db, key, provider_id, value, timestamp)
        return
    if not _claim_webhook_event(db, key, "status"):
        return
    _apply_status(message, value, timestamp)
    db.query(WhatsAppStatusReceipt).filter_by(event_key=key).delete(
        synchronize_session=False
    )


def process_webhook(db, payload):
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                _process_inbound(db, message)
            for status in value.get("statuses", []):
                _process_status(db, status)
    db.commit()
