"""Central admin control plane for tenants, domains, and vertical entitlements."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.platform_tenant import (
    EntitlementUpdate,
    TenantDomainCreate,
    TenantStatusUpdate,
)
from app.services.auth_service import AuthService
from app.services import platform_tenant_service as service


router = APIRouter()


@router.get("")
def list_tenants(
    status: Literal["trial", "active", "suspended", "archived"] | None = Query(
        default=None
    ),
    kind: Literal["platform", "institution", "franchise", "company", "creator"]
    | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(AuthService.require_admin),
):
    return service.list_tenants(db, status=status, kind=kind)


@router.get("/{tenant_id}")
def tenant_detail(
    tenant_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(AuthService.require_admin),
):
    return service.tenant_detail(db, tenant_id)


@router.patch("/{tenant_id}/status")
def update_status(
    tenant_id: int,
    command: TenantStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_admin),
):
    return service.update_status(
        db,
        tenant_id,
        status=command.status,
        reason=command.reason,
        actor_id=user.id,
    )


@router.put("/{tenant_id}/entitlements/{vertical}/{feature_key}")
def update_entitlement(
    tenant_id: int,
    vertical: str,
    feature_key: str,
    command: EntitlementUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_admin),
):
    return service.set_entitlement(
        db,
        tenant_id,
        vertical=vertical,
        feature_key=feature_key,
        enabled=command.enabled,
        quota=command.quota,
        effective_from=command.effective_from,
        effective_through=command.effective_through,
        reason=command.reason,
        actor_id=user.id,
    )


@router.post("/{tenant_id}/domains", status_code=201)
def create_domain(
    tenant_id: int,
    command: TenantDomainCreate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_admin),
):
    return service.add_domain(
        db,
        tenant_id,
        hostname=command.hostname,
        vertical=command.vertical,
        is_primary=command.is_primary,
        actor_id=user.id,
    )
