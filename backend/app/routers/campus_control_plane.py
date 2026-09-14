"""Institution identity, standards and privacy control plane."""

from typing import Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import campus_control_plane as service
from app.services import institution_service
from app.services.auth_service import AuthService


router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


class DomainCreate(BaseModel):
    hostname: str = Field(min_length=4, max_length=253)


class IntegrationUpsert(BaseModel):
    kind: Literal[
        "google_workspace",
        "microsoft_entra",
        "saml",
        "oidc",
        "scim",
        "oneroster",
        "lti_1_3",
        "digilocker_nad",
    ]
    display_name: str = Field(min_length=2, max_length=120)
    status: Literal["draft", "ready", "active", "paused"] = "draft"
    config: dict = Field(default_factory=dict)
    secret_reference: str = Field(default="", max_length=180)


class RetentionUpdate(BaseModel):
    inactive_account_days: int = Field(ge=30, le=3650)
    learning_record_days: int = Field(ge=30, le=7300)
    financial_record_days: int = Field(ge=365, le=7300)
    application_record_days: int = Field(ge=30, le=3650)
    legal_hold: bool = False


class PrivacyRequestCreate(BaseModel):
    subject_user_id: int | None = None
    kind: Literal["access", "export", "correction", "erasure", "restriction"]
    detail: str = Field(default="", max_length=4000)


class PrivacyRequestUpdate(BaseModel):
    status: Literal["verifying", "processing", "completed", "rejected", "cancelled"]
    resolution_note: str = Field(default="", max_length=4000)


class ConsentUpdate(BaseModel):
    subject_user_id: int | None = None
    purpose: str = Field(min_length=2, max_length=80)
    notice_version: str = Field(min_length=1, max_length=40)
    status: Literal["granted", "revoked"]
    method: Literal["self_service", "guardian", "paper_record", "admin_verified"]


@router.get("/{institution_id}/control-plane")
def overview(institution_id: int, db: Session = Depends(get_db), user=Current):
    return service.overview(db, institution_id, user)


@router.post("/{institution_id}/control-plane/domains", status_code=status.HTTP_201_CREATED)
def add_domain(
    institution_id: int,
    data: DomainCreate,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.serialize_domain(
        service.add_domain(db, institution_id, user, data.hostname)
    )


@router.put("/{institution_id}/control-plane/integrations/{kind}")
def save_integration(
    institution_id: int,
    kind: str,
    data: IntegrationUpsert,
    db: Session = Depends(get_db),
    user=Current,
):
    if kind != data.kind:
        from fastapi import HTTPException

        raise HTTPException(422, "Integration path and payload must match.")
    return service.serialize_integration(
        service.upsert_integration(db, institution_id, user, data)
    )


@router.put("/{institution_id}/control-plane/retention")
def save_retention(
    institution_id: int,
    data: RetentionUpdate,
    db: Session = Depends(get_db),
    user=Current,
):
    row = service.set_retention(db, institution_id, user, data)
    return {
        "inactive_account_days": row.inactive_account_days,
        "learning_record_days": row.learning_record_days,
        "financial_record_days": row.financial_record_days,
        "application_record_days": row.application_record_days,
        "legal_hold": row.legal_hold,
    }


@router.post("/{institution_id}/privacy/requests", status_code=status.HTTP_201_CREATED)
def create_privacy_request(
    institution_id: int,
    data: PrivacyRequestCreate,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.serialize_request(
        service.create_privacy_request(db, institution_id, user, data)
    )


@router.get("/{institution_id}/privacy/requests")
def list_privacy_requests(
    institution_id: int,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_service.scope(db, institution_id, user)
    from app.models.campus_control_plane import CampusPrivacyRequest

    query = db.query(CampusPrivacyRequest).filter_by(institution_id=institution_id)
    if actor.role not in institution_service.MANAGERS:
        query = query.filter(CampusPrivacyRequest.requester_user_id == user.id)
    return {
        "items": [
            service.serialize_request(row)
            for row in query.order_by(CampusPrivacyRequest.created_at.desc()).limit(100).all()
        ]
    }


@router.patch("/{institution_id}/privacy/requests/{request_id}")
def update_privacy_request(
    institution_id: int,
    request_id: int,
    data: PrivacyRequestUpdate,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.serialize_request(
        service.update_privacy_request(db, institution_id, request_id, user, data)
    )


@router.put("/{institution_id}/privacy/consent")
def update_consent(
    institution_id: int,
    data: ConsentUpdate,
    db: Session = Depends(get_db),
    user=Current,
):
    row = service.set_consent(db, institution_id, user, data)
    return {
        "id": row.id,
        "subject_user_id": row.subject_user_id,
        "purpose": row.purpose,
        "notice_version": row.notice_version,
        "status": row.status,
        "granted_at": row.granted_at,
        "revoked_at": row.revoked_at,
    }


@router.get("/{institution_id}/integrations/oneroster/export")
def export_oneroster(
    institution_id: int,
    db: Session = Depends(get_db),
    user=Current,
):
    body, filename = service.oneroster_export(db, institution_id, user)
    return Response(
        body,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )

