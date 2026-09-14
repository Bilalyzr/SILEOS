"""Tenant-safe Meiporul deployment, fleet, safety, and AMC workflows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.models.meiporul_operations import ImmersiveDeploymentMilestone, ImmersiveDevice, ImmersiveLabSite, ImmersiveSafetyInspection, ImmersiveServiceTicket
from app.models.platform_tenant import PlatformTenantMembership
from app.services import platform_tenant_service as tenant_service


ADMIN_ROLES = {"admin", "superadmin"}
MEMBER_ROLES = {"owner", "admin", "operations", "support"}
DEFAULT_MILESTONES = (
    "Site survey approved",
    "Network and electrical readiness",
    "Hardware installed and provisioned",
    "Instructor and operator training",
    "Safety sign-off and go-live",
)
DEVICE_TRANSITIONS = {
    "inventory": {"provisioning", "retired"},
    "provisioning": {"ready", "maintenance", "quarantined"},
    "ready": {"deployed", "maintenance", "quarantined", "retired"},
    "deployed": {"ready", "maintenance", "quarantined", "retired"},
    "maintenance": {"ready", "deployed", "quarantined", "retired"},
    "quarantined": {"maintenance", "retired"},
    "retired": set(),
}


def _now():
    return datetime.now(timezone.utc)


def _commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This Meiporul operations record already exists.") from None


def _tenant_ids(db, user) -> list[int] | None:
    if user.role in ADMIN_ROLES:
        return None
    return [
        tenant_id for (tenant_id,) in db.query(PlatformTenantMembership.tenant_id)
        .filter(
            PlatformTenantMembership.user_id == user.id,
            PlatformTenantMembership.status == "active",
            PlatformTenantMembership.role.in_(MEMBER_ROLES),
        ).all()
    ]


def _require_tenant(db, tenant_id: int, user):
    tenant = tenant_service.get_tenant(db, tenant_id)
    permitted = _tenant_ids(db, user)
    if permitted is not None and tenant_id not in permitted:
        raise HTTPException(403, "You cannot manage this tenant's immersive operations.")
    if tenant.status not in {"trial", "active"}:
        raise HTTPException(409, "This tenant is not operational.")
    return tenant


def _site(db, site_id: int, user, *, lock: bool = False) -> ImmersiveLabSite:
    query = db.query(ImmersiveLabSite).filter_by(id=site_id)
    site = query.with_for_update().first() if lock else query.first()
    if site is None:
        raise HTTPException(404, "Immersive lab site not found.")
    _require_tenant(db, site.tenant_id, user)
    return site


def _device_dict(row: ImmersiveDevice) -> dict:
    return {
        "id": row.id, "tenant_id": row.tenant_id, "site_id": row.site_id,
        "asset_tag": row.asset_tag, "serial_number": row.serial_number,
        "device_type": row.device_type, "vendor": row.vendor, "model": row.model,
        "os_version": row.os_version, "firmware_version": row.firmware_version,
        "status": row.status, "assigned_room": row.assigned_room,
        "last_seen_at": row.last_seen_at, "commissioned_on": row.commissioned_on,
        "warranty_through": row.warranty_through, "metadata": row.metadata_json,
    }


def _site_dict(db, row: ImmersiveLabSite, *, detail: bool = False) -> dict:
    devices = db.query(ImmersiveDevice).filter_by(site_id=row.id)
    tickets = db.query(ImmersiveServiceTicket).filter_by(site_id=row.id)
    payload = {
        "id": row.id, "tenant_id": row.tenant_id, "institution_id": row.institution_id,
        "contract_id": row.contract_id, "code": row.code, "name": row.name,
        "status": row.status, "address": row.address, "room_count": row.room_count,
        "headset_capacity": row.headset_capacity, "network_readiness": row.network_readiness,
        "safety_status": row.safety_status, "go_live_on": row.go_live_on,
        "notes": row.notes, "created_at": row.created_at, "updated_at": row.updated_at,
        "counts": {
            "devices": devices.count(),
            "deployed_devices": devices.filter(ImmersiveDevice.status == "deployed").count(),
            "open_tickets": tickets.filter(ImmersiveServiceTicket.status.notin_(("resolved", "closed"))).count(),
        },
    }
    if detail:
        payload["devices"] = [_device_dict(device) for device in devices.order_by(ImmersiveDevice.asset_tag).all()]
        payload["inspections"] = [
            {"id": item.id, "inspection_type": item.inspection_type, "status": item.status,
             "scheduled_for": item.scheduled_for, "completed_at": item.completed_at,
             "checklist": item.checklist, "findings": item.findings,
             "corrective_actions": item.corrective_actions, "next_due_on": item.next_due_on,
             "inspector_id": item.inspector_id}
            for item in db.query(ImmersiveSafetyInspection).filter_by(site_id=row.id).order_by(ImmersiveSafetyInspection.scheduled_for.desc()).all()
        ]
        payload["milestones"] = [
            {"id": item.id, "sequence": item.sequence, "title": item.title, "status": item.status,
             "due_on": item.due_on, "completed_at": item.completed_at,
             "owner_user_id": item.owner_user_id, "evidence_urls": item.evidence_urls,
             "notes": item.notes}
            for item in db.query(ImmersiveDeploymentMilestone).filter_by(site_id=row.id).order_by(ImmersiveDeploymentMilestone.sequence).all()
        ]
        payload["tickets"] = [
            {"id": item.id, "reference": item.reference, "device_id": item.device_id,
             "category": item.category, "priority": item.priority, "status": item.status,
             "subject": item.subject, "description": item.description, "resolution": item.resolution,
             "sla_due_at": item.sla_due_at, "assignee_id": item.assignee_id,
             "resolved_at": item.resolved_at, "created_at": item.created_at}
            for item in tickets.order_by(ImmersiveServiceTicket.id.desc()).all()
        ]
    return payload


def list_sites(db, user, tenant_id: int | None = None) -> list[dict]:
    query = db.query(ImmersiveLabSite)
    permitted = _tenant_ids(db, user)
    if permitted is not None:
        query = query.filter(ImmersiveLabSite.tenant_id.in_(permitted or [-1]))
    if tenant_id:
        _require_tenant(db, tenant_id, user)
        query = query.filter(ImmersiveLabSite.tenant_id == tenant_id)
    return [_site_dict(db, row) for row in query.order_by(ImmersiveLabSite.id.desc()).limit(500).all()]


def get_site(db, site_id: int, user) -> dict:
    return _site_dict(db, _site(db, site_id, user), detail=True)


def create_site(db, command, user) -> dict:
    _require_tenant(db, command.tenant_id, user)
    site = ImmersiveLabSite(
        **command.model_dump(exclude={"code"}),
        code=command.code.upper(),
        created_by=user.id,
    )
    db.add(site); db.flush()
    for sequence, title in enumerate(DEFAULT_MILESTONES, start=1):
        db.add(ImmersiveDeploymentMilestone(tenant_id=site.tenant_id, site_id=site.id, sequence=sequence, title=title, created_by=user.id))
    tenant_service.audit(db, tenant_id=site.tenant_id, actor_id=user.id, action="meiporul.site_created", target_type="immersive_lab_site", target_id=site.id, after={"code": site.code, "status": site.status})
    tenant_service.enqueue(db, tenant_id=site.tenant_id, topic="meiporul.site.created", aggregate_type="immersive_lab_site", aggregate_id=site.id, payload={"site_id": site.id, "tenant_id": site.tenant_id}, idempotency_key=f"meiporul:site:{site.id}:created:v1")
    _commit(db)
    return _site_dict(db, site, detail=True)


def update_site(db, site_id: int, command, user) -> dict:
    site = _site(db, site_id, user, lock=True)
    before = {"status": site.status, "network_readiness": site.network_readiness, "safety_status": site.safety_status}
    values = command.model_dump(exclude={"reason"}, exclude_none=True)
    target_status = values.pop("status", None)
    for key, value in values.items(): setattr(site, key, value)
    if target_status == "active" and site.status != "active":
        if site.network_readiness != "ready" or site.safety_status != "passed":
            raise HTTPException(409, "Go-live requires ready network and passed safety inspection.")
        ready_headsets = db.query(ImmersiveDevice).filter(ImmersiveDevice.site_id == site.id, ImmersiveDevice.device_type == "headset", ImmersiveDevice.status.in_(("ready", "deployed"))).count()
        unfinished = db.query(ImmersiveDeploymentMilestone).filter(ImmersiveDeploymentMilestone.site_id == site.id, ImmersiveDeploymentMilestone.status.notin_(("completed", "skipped"))).count()
        if ready_headsets == 0 or unfinished:
            raise HTTPException(409, "Go-live requires a ready headset and every deployment milestone completed or skipped.")
    if target_status: site.status = target_status
    tenant_service.audit(db, tenant_id=site.tenant_id, actor_id=user.id, action="meiporul.site_updated", target_type="immersive_lab_site", target_id=site.id, reason=command.reason, before=before, after={"status": site.status, "network_readiness": site.network_readiness, "safety_status": site.safety_status})
    _commit(db)
    return _site_dict(db, site, detail=True)


def add_device(db, site_id: int, command, user) -> dict:
    site = _site(db, site_id, user)
    values = command.model_dump(exclude={"metadata"})
    device = ImmersiveDevice(tenant_id=site.tenant_id, site_id=site.id, metadata_json=command.metadata, created_by=user.id, **values)
    db.add(device)
    tenant_service.audit(db, tenant_id=site.tenant_id, actor_id=user.id, action="meiporul.device_added", target_type="immersive_device", target_id=command.asset_tag, after={"site_id": site.id, "status": command.status})
    _commit(db)
    return _device_dict(device)


def update_device(db, device_id: int, command, user) -> dict:
    device = db.query(ImmersiveDevice).filter_by(id=device_id).with_for_update().first()
    if device is None: raise HTTPException(404, "Immersive device not found.")
    _require_tenant(db, device.tenant_id, user)
    values = command.model_dump(exclude={"reason", "metadata"}, exclude_none=True)
    target = values.pop("status", None)
    if target and target != device.status and target not in DEVICE_TRANSITIONS[device.status]:
        raise HTTPException(409, f"Device cannot move from {device.status} to {target}.")
    before = {"status": device.status, "assigned_room": device.assigned_room}
    for key, value in values.items(): setattr(device, key, value)
    if command.metadata is not None: device.metadata_json = command.metadata
    if target: device.status = target
    tenant_service.audit(db, tenant_id=device.tenant_id, actor_id=user.id, action="meiporul.device_updated", target_type="immersive_device", target_id=device.id, reason=command.reason, before=before, after={"status": device.status, "assigned_room": device.assigned_room})
    _commit(db)
    return _device_dict(device)


def add_inspection(db, site_id: int, command, user) -> dict:
    site = _site(db, site_id, user, lock=True)
    values = command.model_dump()
    if command.status != "scheduled" and command.completed_at is None: values["completed_at"] = _now()
    row = ImmersiveSafetyInspection(tenant_id=site.tenant_id, site_id=site.id, created_by=user.id, **values)
    db.add(row)
    if command.status in {"passed", "failed", "conditional"}: site.safety_status = command.status
    tenant_service.audit(db, tenant_id=site.tenant_id, actor_id=user.id, action="meiporul.inspection_recorded", target_type="immersive_safety_inspection", target_id=site.id, after={"type": command.inspection_type, "status": command.status})
    _commit(db)
    return _site_dict(db, site, detail=True)


def add_milestone(db, site_id: int, command, user) -> dict:
    site = _site(db, site_id, user, lock=True)
    sequence = (db.query(func.max(ImmersiveDeploymentMilestone.sequence)).filter_by(site_id=site.id).scalar() or 0) + 1
    db.add(ImmersiveDeploymentMilestone(tenant_id=site.tenant_id, site_id=site.id, sequence=sequence, created_by=user.id, **command.model_dump()))
    _commit(db)
    return _site_dict(db, site, detail=True)


def update_milestone(db, milestone_id: int, command, user) -> dict:
    row = db.query(ImmersiveDeploymentMilestone).filter_by(id=milestone_id).with_for_update().first()
    if row is None: raise HTTPException(404, "Deployment milestone not found.")
    site = _site(db, row.site_id, user)
    row.status = command.status; row.evidence_urls = command.evidence_urls; row.notes = command.notes
    row.completed_at = _now() if command.status == "completed" else None
    tenant_service.audit(db, tenant_id=row.tenant_id, actor_id=user.id, action="meiporul.milestone_updated", target_type="immersive_deployment_milestone", target_id=row.id, reason=command.reason, after={"status": row.status})
    _commit(db)
    return _site_dict(db, site, detail=True)


def create_ticket(db, site_id: int, command, user) -> dict:
    site = _site(db, site_id, user)
    if command.device_id:
        device = db.get(ImmersiveDevice, command.device_id)
        if device is None or device.site_id != site.id: raise HTTPException(422, "Device does not belong to this site.")
    hours = {"low": 72, "normal": 48, "high": 24, "critical": 4}[command.priority]
    row = ImmersiveServiceTicket(tenant_id=site.tenant_id, site_id=site.id, reference=f"MP-{_now():%Y%m%d}-{secrets.token_hex(3).upper()}", status="open", sla_due_at=_now() + timedelta(hours=hours), created_by=user.id, **command.model_dump())
    db.add(row); db.flush()
    tenant_service.audit(db, tenant_id=site.tenant_id, actor_id=user.id, action="meiporul.ticket_opened", target_type="immersive_service_ticket", target_id=row.id, after={"reference": row.reference, "priority": row.priority})
    tenant_service.enqueue(db, tenant_id=site.tenant_id, topic="meiporul.ticket.opened", aggregate_type="immersive_service_ticket", aggregate_id=row.id, payload={"ticket_id": row.id, "site_id": site.id, "priority": row.priority}, idempotency_key=f"meiporul:ticket:{row.id}:opened:v1")
    _commit(db)
    return _site_dict(db, site, detail=True)


def update_ticket(db, ticket_id: int, command, user) -> dict:
    row = db.query(ImmersiveServiceTicket).filter_by(id=ticket_id).with_for_update().first()
    if row is None: raise HTTPException(404, "Service ticket not found.")
    site = _site(db, row.site_id, user)
    if command.status in {"resolved", "closed"} and len(command.resolution.strip()) < 3:
        raise HTTPException(422, "A resolution is required before resolving a ticket.")
    row.status = command.status; row.assignee_id = command.assignee_id; row.resolution = command.resolution
    if command.status == "resolved": row.resolved_at = _now()
    if command.status == "closed":
        row.resolved_at = row.resolved_at or _now(); row.closed_at = _now()
    tenant_service.audit(db, tenant_id=row.tenant_id, actor_id=user.id, action="meiporul.ticket_updated", target_type="immersive_service_ticket", target_id=row.id, reason=command.reason, after={"status": row.status})
    _commit(db)
    return _site_dict(db, site, detail=True)
