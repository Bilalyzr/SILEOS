"""Business-vertical-neutral tenant control-plane operations."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.core.business_verticals import VERTICAL_KEYS, normalize_vertical
from app.models.institution import Institution
from app.models.platform_tenant import (
    PlatformAuditEvent,
    PlatformOutboxEvent,
    PlatformTenant,
    PlatformTenantDomain,
    PlatformTenantEntitlement,
    PlatformTenantMembership,
)


DEFAULT_INSTITUTION_ENTITLEMENTS = {
    "meiporul": ("immersive_catalog", {"private_assets": 0, "device_rooms": 0}),
    "seyappaduporul": ("campus_operations", {"campuses": 1}),
    "utporul": ("course_authoring", {"published_courses": 20}),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _slug(value: str, *, fallback: str = "tenant") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (cleaned or fallback)[:100]


def serialize_tenant(tenant: PlatformTenant, *, counts: dict[str, int] | None = None) -> dict:
    payload = {
        "id": tenant.id,
        "slug": tenant.slug,
        "name": tenant.name,
        "kind": tenant.kind,
        "status": tenant.status,
        "timezone": tenant.timezone,
        "data_region": tenant.data_region,
        "created_by": tenant.created_by,
        "created_at": tenant.created_at,
        "updated_at": tenant.updated_at,
    }
    if counts is not None:
        payload["counts"] = counts
    return payload


def audit(
    db,
    *,
    tenant_id: int | None,
    actor_id: int | None,
    action: str,
    target_type: str,
    target_id: str | int = "",
    reason: str = "",
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str = "",
) -> PlatformAuditEvent:
    event = PlatformAuditEvent(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        reason=reason[:500],
        before_json=before,
        after_json=after,
        request_id=request_id[:80],
    )
    db.add(event)
    return event


def enqueue(
    db,
    *,
    tenant_id: int | None,
    topic: str,
    aggregate_type: str,
    aggregate_id: str | int,
    payload: dict[str, Any],
    idempotency_key: str,
) -> PlatformOutboxEvent:
    event = PlatformOutboxEvent(
        tenant_id=tenant_id,
        topic=topic,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=payload,
        idempotency_key=idempotency_key,
        status="pending",
        available_at=_utcnow(),
    )
    db.add(event)
    return event


def provision_institution(db, institution: Institution, owner) -> PlatformTenant:
    """Create the platform boundary atomically with a new institution."""
    if institution.tenant_id:
        tenant = db.get(PlatformTenant, institution.tenant_id)
        if tenant:
            sync_institution_member(
                db,
                institution=institution,
                user_id=owner.id,
                role="owner",
                status="active",
            )
            return tenant

    # Institution ids are included so tenant slugs remain stable and collision
    # free even when two customers choose the same public name.
    candidate = _slug(f"inst-{institution.id}-{institution.slug}")
    tenant = PlatformTenant(
        slug=candidate,
        name=institution.name,
        kind="institution",
        status="trial",
        timezone=institution.timezone,
        data_region="in",
        created_by=owner.id,
    )
    db.add(tenant)
    db.flush()
    institution.tenant_id = tenant.id

    db.add(
        PlatformTenantMembership(
            tenant_id=tenant.id,
            user_id=owner.id,
            role="owner",
            status="active",
            permissions=[],
        )
    )
    for vertical, (feature_key, quota) in DEFAULT_INSTITUTION_ENTITLEMENTS.items():
        db.add(
            PlatformTenantEntitlement(
                tenant_id=tenant.id,
                vertical=vertical,
                feature_key=feature_key,
                enabled=True,
                quota=quota,
                updated_by=owner.id,
                effective_from=_utcnow(),
            )
        )

    audit(
        db,
        tenant_id=tenant.id,
        actor_id=owner.id,
        action="tenant.provisioned",
        target_type="platform_tenant",
        target_id=tenant.id,
        reason="Institution workspace created",
        after={"kind": tenant.kind, "status": tenant.status},
    )
    enqueue(
        db,
        tenant_id=tenant.id,
        topic="platform.tenant.provisioned",
        aggregate_type="platform_tenant",
        aggregate_id=tenant.id,
        payload={
            "tenant_id": tenant.id,
            "institution_id": institution.id,
            "verticals": list(VERTICAL_KEYS),
        },
        idempotency_key=f"tenant:{tenant.id}:provisioned:v1",
    )
    return tenant


def sync_institution_member(
    db,
    *,
    institution: Institution,
    user_id: int,
    role: str,
    status: str,
) -> PlatformTenantMembership | None:
    """Mirror campus membership into the platform boundary in the same transaction."""
    if not institution.tenant_id:
        return None
    membership = (
        db.query(PlatformTenantMembership)
        .filter_by(tenant_id=institution.tenant_id, user_id=user_id)
        .first()
    )
    tenant_status = "active" if status == "active" else "suspended"
    if membership is None:
        membership = PlatformTenantMembership(
            tenant_id=institution.tenant_id,
            user_id=user_id,
            role=role,
            status=tenant_status,
            permissions=[],
        )
        db.add(membership)
    else:
        membership.role = role
        membership.status = tenant_status
    return membership


def get_tenant(db, tenant_id: int, *, lock: bool = False) -> PlatformTenant:
    query = db.query(PlatformTenant).filter_by(id=tenant_id)
    tenant = query.with_for_update().first() if lock else query.first()
    if tenant is None:
        raise HTTPException(404, "Tenant not found.")
    return tenant


def list_tenants(db, *, status: str | None = None, kind: str | None = None) -> list[dict]:
    query = db.query(PlatformTenant)
    if status:
        query = query.filter(PlatformTenant.status == status)
    if kind:
        query = query.filter(PlatformTenant.kind == kind)
    tenants = query.order_by(PlatformTenant.id.desc()).limit(500).all()
    result = []
    for tenant in tenants:
        counts = {
            "members": db.query(PlatformTenantMembership)
            .filter_by(tenant_id=tenant.id, status="active")
            .count(),
            "domains": db.query(PlatformTenantDomain)
            .filter_by(tenant_id=tenant.id, status="verified")
            .count(),
            "entitlements": db.query(PlatformTenantEntitlement)
            .filter_by(tenant_id=tenant.id, enabled=True)
            .count(),
        }
        result.append(serialize_tenant(tenant, counts=counts))
    return result


def tenant_detail(db, tenant_id: int) -> dict:
    tenant = get_tenant(db, tenant_id)
    payload = serialize_tenant(tenant)
    payload["members"] = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "role": row.role,
            "status": row.status,
            "permissions": row.permissions,
        }
        for row in db.query(PlatformTenantMembership)
        .filter_by(tenant_id=tenant_id)
        .order_by(PlatformTenantMembership.id)
        .all()
    ]
    payload["domains"] = [
        {
            "id": row.id,
            "hostname": row.hostname,
            "vertical": row.vertical,
            "status": row.status,
            "is_primary": row.is_primary,
            "verified_at": row.verified_at,
        }
        for row in db.query(PlatformTenantDomain)
        .filter_by(tenant_id=tenant_id)
        .order_by(PlatformTenantDomain.hostname)
        .all()
    ]
    payload["entitlements"] = [
        {
            "id": row.id,
            "vertical": row.vertical,
            "feature_key": row.feature_key,
            "enabled": row.enabled,
            "quota": row.quota,
            "effective_from": row.effective_from,
            "effective_through": row.effective_through,
        }
        for row in db.query(PlatformTenantEntitlement)
        .filter_by(tenant_id=tenant_id)
        .order_by(
            PlatformTenantEntitlement.vertical,
            PlatformTenantEntitlement.feature_key,
        )
        .all()
    ]
    return payload


def update_status(db, tenant_id: int, *, status: str, reason: str, actor_id: int) -> dict:
    tenant = get_tenant(db, tenant_id, lock=True)
    if tenant.kind == "platform" and status in {"suspended", "archived"}:
        raise HTTPException(409, "The platform tenant cannot be suspended or archived.")
    before = {"status": tenant.status}
    tenant.status = status
    audit(
        db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        action="tenant.status_changed",
        target_type="platform_tenant",
        target_id=tenant.id,
        reason=reason,
        before=before,
        after={"status": status},
    )
    enqueue(
        db,
        tenant_id=tenant.id,
        topic="platform.tenant.status_changed",
        aggregate_type="platform_tenant",
        aggregate_id=tenant.id,
        payload={"tenant_id": tenant.id, "status": status, "reason": reason},
        idempotency_key=f"tenant:{tenant.id}:status:{status}:{int(_utcnow().timestamp() * 1_000_000)}",
    )
    _commit(db)
    return serialize_tenant(tenant)


def set_entitlement(
    db,
    tenant_id: int,
    *,
    vertical: str,
    feature_key: str,
    enabled: bool,
    quota: dict,
    effective_from: datetime | None,
    effective_through: datetime | None,
    reason: str,
    actor_id: int,
) -> dict:
    tenant = get_tenant(db, tenant_id, lock=True)
    canonical = normalize_vertical(vertical)
    if canonical is None:
        raise HTTPException(422, "Unknown business vertical.")
    row = (
        db.query(PlatformTenantEntitlement)
        .filter_by(tenant_id=tenant_id, vertical=canonical, feature_key=feature_key)
        .first()
    )
    before = None
    if row is None:
        row = PlatformTenantEntitlement(
            tenant_id=tenant.id,
            vertical=canonical,
            feature_key=feature_key,
        )
        db.add(row)
    else:
        before = {"enabled": row.enabled, "quota": row.quota}
    row.enabled = enabled
    row.quota = quota
    row.effective_from = effective_from
    row.effective_through = effective_through
    row.updated_by = actor_id
    audit(
        db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        action="tenant.entitlement_changed",
        target_type="platform_tenant_entitlement",
        target_id=f"{canonical}:{feature_key}",
        reason=reason,
        before=before,
        after={"enabled": enabled, "quota": quota},
    )
    enqueue(
        db,
        tenant_id=tenant.id,
        topic="platform.tenant.entitlement_changed",
        aggregate_type="platform_tenant_entitlement",
        aggregate_id=f"{tenant.id}:{canonical}:{feature_key}",
        payload={
            "tenant_id": tenant.id,
            "vertical": canonical,
            "feature_key": feature_key,
            "enabled": enabled,
            "quota": quota,
        },
        idempotency_key=(
            f"tenant:{tenant.id}:entitlement:{canonical}:{feature_key}:"
            f"{int(_utcnow().timestamp() * 1_000_000)}"
        ),
    )
    _commit(db)
    return {
        "tenant_id": tenant.id,
        "vertical": row.vertical,
        "feature_key": row.feature_key,
        "enabled": row.enabled,
        "quota": row.quota,
    }


def add_domain(
    db,
    tenant_id: int,
    *,
    hostname: str,
    vertical: str | None,
    is_primary: bool,
    actor_id: int,
) -> dict:
    tenant = get_tenant(db, tenant_id, lock=True)
    host = hostname.strip().lower().rstrip(".")
    if not host or "/" in host or ":" in host or " " in host or "." not in host:
        raise HTTPException(422, "Enter a hostname without a scheme, port, or path.")
    canonical = normalize_vertical(vertical) if vertical else None
    if vertical and canonical is None:
        raise HTTPException(422, "Unknown business vertical.")
    if is_primary:
        db.query(PlatformTenantDomain).filter_by(
            tenant_id=tenant.id, vertical=canonical, is_primary=True
        ).update({"is_primary": False}, synchronize_session=False)
    row = PlatformTenantDomain(
        tenant_id=tenant.id,
        hostname=host,
        vertical=canonical,
        status="pending",
        is_primary=is_primary,
    )
    db.add(row)
    audit(
        db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        action="tenant.domain_requested",
        target_type="platform_tenant_domain",
        target_id=host,
        after={"vertical": canonical, "is_primary": is_primary},
    )
    _commit(db)
    return {
        "id": row.id,
        "hostname": row.hostname,
        "vertical": row.vertical,
        "status": row.status,
        "is_primary": row.is_primary,
    }


def is_entitled(db, tenant_id: int, vertical: str, feature_key: str) -> bool:
    """Single policy primitive for feature gates in all three verticals."""
    canonical = normalize_vertical(vertical)
    if canonical is None:
        return False
    from app.services.growth_fulfillment import feature_access
    if feature_access(db, tenant_id, canonical, feature_key):
        return True
    now = _utcnow()
    return (
        db.query(PlatformTenantEntitlement)
        .join(PlatformTenant, PlatformTenant.id == PlatformTenantEntitlement.tenant_id)
        .filter(
            PlatformTenant.id == tenant_id,
            PlatformTenant.status.in_(("trial", "active")),
            PlatformTenantEntitlement.vertical == canonical,
            PlatformTenantEntitlement.feature_key == feature_key,
            PlatformTenantEntitlement.enabled.is_(True),
            (PlatformTenantEntitlement.effective_from.is_(None))
            | (PlatformTenantEntitlement.effective_from <= now),
            (PlatformTenantEntitlement.effective_through.is_(None))
            | (PlatformTenantEntitlement.effective_through > now),
        )
        .first()
        is not None
    )


def resolve_verified_domain(db, hostname: str) -> PlatformTenantDomain | None:
    host = hostname.strip().lower().split(":", 1)[0].rstrip(".")
    return (
        db.query(PlatformTenantDomain)
        .join(PlatformTenant, PlatformTenant.id == PlatformTenantDomain.tenant_id)
        .filter(
            func.lower(PlatformTenantDomain.hostname) == host,
            PlatformTenantDomain.status == "verified",
            PlatformTenant.status.in_(("trial", "active")),
        )
        .first()
    )


def _commit(db) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This tenant setting already exists.") from None
