"""Account-wide WhatsApp self-service and platform-admin communications."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.whatsapp import WhatsAppCampaign, WhatsAppContact, WhatsAppMessage
from app.schemas.whatsapp import (
    WHATSAPP_AUDIENCE_ROLES,
    WhatsAppCampaignCreate,
    WhatsAppOptIn,
)
from app.services import campus_whatsapp as whatsapp_svc
from app.services import whatsapp_campaigns as campaign_svc
from app.services.auth_service import AuthService
from app.services.institution_service import utc


router = APIRouter()
Current = Depends(AuthService.get_current_active_user)
Admin = Depends(AuthService.require_admin)


def _campaign_dict(db, row):
    counts = {
        "queued": 0,
        "sent": 0,
        "delivered": 0,
        "read": 0,
        "failed": 0,
        "cancelled": 0,
    }
    for status, count in (
        db.query(WhatsAppMessage.status, func.count())
        .filter_by(campaign_id=row.id)
        .group_by(WhatsAppMessage.status)
    ):
        target = "queued" if status in ("queued", "retrying", "sending") else status
        counts[target] = counts.get(target, 0) + count
    total = sum(counts.values())
    unsuccessful = counts["failed"] + counts["cancelled"]
    if counts["queued"]:
        aggregate = "queued"
    elif total and unsuccessful == total:
        aggregate = "failed"
    elif unsuccessful:
        aggregate = "partial"
    elif total and counts["read"] == total:
        aggregate = "read"
    elif total and counts["read"] + counts["delivered"] == total:
        aggregate = "delivered"
    else:
        aggregate = "sent"
    return {
        "id": row.id,
        "request_key": row.request_key,
        "template": row.template,
        "language": row.language,
        "parameters": row.parameters,
        "roles": row.roles,
        "header_image_url": row.header_image_url or None,
        "created_at": utc(row.created_at).isoformat(),
        "status": aggregate,
        "recipient_count": total,
        **counts,
    }


def _masked_phone(phone):
    if not phone:
        return None
    return "+" + "*" * max(4, len(phone) - 5) + phone[-4:]


def _same_campaign(row, data, header_url, roles):
    return (
        row.template == data.template
        and row.language == data.language
        and row.parameters == data.parameters
        and sorted(row.roles or []) == roles
        and row.header_image_url == header_url
    )


def _existing_campaign(db, data, header_url, roles):
    row = (
        db.query(WhatsAppCampaign)
        .filter_by(request_key=data.request_key)
        .populate_existing()
        .first()
    )
    if row and not _same_campaign(row, data, header_url, roles):
        raise HTTPException(409, "That request key belongs to another campaign.")
    return row


def _claim_campaign(db, campaign, data, header_url, roles):
    """Insert behind a savepoint, or reload the concurrent request winner."""

    # Keep a successful savepoint open through recipient expansion. Besides
    # preserving the unique-key recovery boundary, this gives SQLite a real
    # transaction before its first write; the route's final commit/rollback
    # then covers both the campaign and all message batches.
    savepoint = db.begin_nested()
    try:
        db.add(campaign)
        db.flush()
        return campaign, True
    except IntegrityError:
        savepoint.rollback()
        # The savepoint keeps the outer request transaction usable after the
        # unique-key loser. Under PostgreSQL the insert waits for the winner's
        # commit; SQLite raises immediately for an already committed winner.
        db.expire_all()
        existing = _existing_campaign(db, data, header_url, roles)
        if existing:
            return existing, False
        raise HTTPException(
            409, "That campaign request is already being processed."
        ) from None


@router.get("/status")
def whatsapp_status(db: Session = Depends(get_db), user=Current):
    result = whatsapp_svc.configuration_status()
    result.update(whatsapp_svc.contact_status(db.get(WhatsAppContact, user.id)))
    return result


@router.post("/opt-in")
def whatsapp_opt_in(
    data: WhatsAppOptIn,
    db: Session = Depends(get_db),
    user=Current,
):
    result = whatsapp_svc.begin_opt_in(db, user.id, data.phone)
    if result is None:
        raise HTTPException(
            503,
            "WhatsApp opt-in is unavailable until the business phone and signed webhook are configured.",
        )
    return result


@router.delete("/opt-in")
def whatsapp_opt_out(db: Session = Depends(get_db), user=Current):
    return whatsapp_svc.revoke_opt_in(db, user.id)


@router.get("/admin/overview")
def whatsapp_admin_overview(db: Session = Depends(get_db), _admin=Admin):
    result = whatsapp_svc.configuration_status()
    total_users = (
        db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar()
    )
    consent_counts = {status: 0 for status in ("pending", "confirmed", "revoked")}
    for status, count in (
        db.query(WhatsAppContact.status, func.count())
        .join(User, User.id == WhatsAppContact.user_id)
        .filter(User.is_active.is_(True))
        .group_by(WhatsAppContact.status)
    ):
        if status in consent_counts:
            consent_counts[status] = count
    consent_counts["not_started"] = max(0, total_users - sum(consent_counts.values()))
    consent_counts["total_users"] = total_users

    eligible_by_role = {role: 0 for role in WHATSAPP_AUDIENCE_ROLES}
    for role, count in (
        db.query(User.role, func.count())
        .join(WhatsAppContact, WhatsAppContact.user_id == User.id)
        .filter(User.is_active.is_(True), WhatsAppContact.status == "confirmed")
        .group_by(User.role)
    ):
        if role in eligible_by_role:
            eligible_by_role[role] = count
    result.update(
        {"consent_counts": consent_counts, "eligible_by_role": eligible_by_role}
    )
    return result


@router.get("/admin/contacts")
def whatsapp_admin_contacts(
    status: str | None = Query(default=None),
    role: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin=Admin,
):
    allowed_statuses = {"not_started", "pending", "confirmed", "revoked"}
    if status is not None and status not in allowed_statuses:
        raise HTTPException(422, "Select a valid consent status.")
    if role is not None and role not in WHATSAPP_AUDIENCE_ROLES:
        raise HTTPException(422, "Select a valid account role.")
    query = db.query(User, WhatsAppContact).outerjoin(
        WhatsAppContact, WhatsAppContact.user_id == User.id
    )
    if status == "not_started":
        query = query.filter(WhatsAppContact.user_id.is_(None))
    elif status:
        query = query.filter(WhatsAppContact.status == status)
    if role:
        query = query.filter(User.role == role)
    term = (search or "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.filter(
            or_(
                User.display_name.ilike(pattern),
                User.user_email.ilike(pattern),
                User.user_login.ilike(pattern),
            )
        )
    total = query.count()
    rows = query.order_by(User.display_name, User.id).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                "user_id": account.id,
                "name": account.display_name,
                "email": account.user_email,
                "role": account.role,
                "is_active": account.is_active,
                "phone": _masked_phone(contact.phone) if contact else None,
                "status": contact.status if contact else "not_started",
                "consent_at": utc(contact.consent_at).isoformat()
                if contact and contact.consent_at
                else None,
            }
            for account, contact in rows
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/admin/campaigns")
def whatsapp_admin_campaigns(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin=Admin,
):
    return [
        _campaign_dict(db, row)
        for row in db.query(WhatsAppCampaign)
        .order_by(WhatsAppCampaign.id.desc())
        .limit(limit)
    ]


@router.post("/admin/campaigns", status_code=201)
def whatsapp_admin_campaign_create(
    data: WhatsAppCampaignCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    admin=Admin,
):
    status = whatsapp_svc.configuration_status()
    if not status["configured"]:
        raise HTTPException(503, "WhatsApp Cloud API is not fully configured.")
    if data.template not in status["approved_templates"]:
        raise HTTPException(422, "Select an approved WhatsApp template.")
    header_url = str(data.header_image_url) if data.header_image_url else ""
    roles = sorted(data.roles)
    existing = _existing_campaign(db, data, header_url, roles)
    if existing:
        return _campaign_dict(db, existing)

    campaign = WhatsAppCampaign(
        request_key=data.request_key,
        template=data.template,
        language=data.language,
        parameters=data.parameters,
        roles=roles,
        header_image_url=header_url,
        created_by=admin.id,
    )
    campaign, created = _claim_campaign(db, campaign, data, header_url, roles)
    if not created:
        return _campaign_dict(db, campaign)
    try:
        recipient_count = campaign_svc.enqueue_global_recipients(
            db,
            campaign_id=campaign.id,
            roles=roles,
        )
        if not recipient_count:
            raise HTTPException(
                422, "No active, opted-in recipients match this audience."
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(campaign)
    background.add_task(whatsapp_svc.deliver_pending)
    return _campaign_dict(db, campaign)
