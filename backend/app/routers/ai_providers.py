"""Admin API for the encrypted Sasha AI provider credential pool."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_provider import AiProviderCredential
from app.models.ai_provider_usage import AiProviderUsageEvent
from app.models.platform_tenant import PlatformAuditEvent
from app.models.user import User
from app.services.ai_provider_vault import (
    DEFAULT_MODELS, encrypt_api_key, has_configured_provider,
    key_fingerprint, key_hint, test_credential,
)
from app.services.auth_service import AuthService


router = APIRouter()


class ProviderCreate(BaseModel):
    label: str = Field(min_length=2, max_length=100)
    provider: Literal["glm", "gemini"]
    api_key: str = Field(min_length=8, max_length=500)
    model: str | None = Field(default=None, min_length=2, max_length=100)
    priority: int = Field(default=100, ge=1, le=9999)
    is_active: bool = True

    @field_validator("label", "api_key", "model")
    @classmethod
    def trim_strings(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProviderUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=100)
    api_key: str | None = Field(default=None, min_length=8, max_length=500)
    model: str | None = Field(default=None, min_length=2, max_length=100)
    priority: int | None = Field(default=None, ge=1, le=9999)
    is_active: bool | None = None

    @field_validator("label", "api_key", "model")
    @classmethod
    def trim_strings(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProviderOut(BaseModel):
    id: int
    label: str
    provider: str
    model: str
    key_hint: str
    priority: int
    is_active: bool
    health_status: str
    failure_count: int
    last_error: str
    last_used_at: datetime | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UsageAggregate(BaseModel):
    scope: str
    provider: str
    model: str
    feature: str | None
    attempts: int
    success: int
    failure: int
    success_rate: float
    avg_latency_ms: float | None
    last_used_at: datetime | None


class RecentFailure(BaseModel):
    id: int
    credential_id: int | None
    provider: str
    model: str
    feature: str
    error: str
    created_at: datetime


class UsageReport(BaseModel):
    period_days: int
    total_attempts: int
    total_success: int
    total_failures: int
    success_rate: float
    by_provider: list[UsageAggregate]
    by_feature: list[UsageAggregate]
    recent_failures: list[RecentFailure]


class ProviderHealth(BaseModel):
    configured: bool
    active_credentials: int
    healthy_credentials: int
    configured_credentials: int
    providers: list[str]


def _row(db: Session, credential_id: int) -> AiProviderCredential:
    row = db.query(AiProviderCredential).filter(AiProviderCredential.id == credential_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="AI provider credential not found")
    return row


def _snapshot(row: AiProviderCredential) -> dict:
    return {
        "label": row.label,
        "provider": row.provider,
        "model": row.model,
        "key_hint": row.key_hint,
        "priority": row.priority,
        "is_active": row.is_active,
        "health_status": row.health_status,
    }


def _provider_status(db: Session) -> ProviderHealth:
    rows = db.query(AiProviderCredential).filter(AiProviderCredential.is_active.is_(True)).all()
    providers = sorted({row.provider for row in rows})
    return ProviderHealth(
        configured=bool(has_configured_provider()),
        active_credentials=len(rows),
        healthy_credentials=sum(1 for row in rows if row.health_status == "healthy"),
        configured_credentials=sum(1 for row in rows if row.is_active),
        providers=providers,
    )


def _aggregate_usage(events: list[AiProviderUsageEvent], by_feature: bool) -> list[UsageAggregate]:
    buckets: dict[tuple[str, str], dict[str, object]] = {}
    for event in events:
        feature = event.feature if by_feature else ""
        key = (event.provider, feature)
        bucket = buckets.get(key)
        if bucket is None:
            bucket = {
                "provider": event.provider,
                "model": event.model,
                "feature": event.feature if by_feature else None,
                "scope": event.provider if not by_feature else feature,
                "attempts": 0,
                "success": 0,
                "failure": 0,
                "latency_sum": 0,
                "latency_count": 0,
                "last_used_at": None,
            }
            buckets[key] = bucket
        bucket["attempts"] = int(bucket["attempts"]) + 1
        if event.success:
            bucket["success"] = int(bucket["success"]) + 1
        else:
            bucket["failure"] = int(bucket["failure"]) + 1
        if event.latency_ms is not None:
            bucket["latency_sum"] = float(bucket["latency_sum"]) + event.latency_ms
            bucket["latency_count"] = int(bucket["latency_count"]) + 1
        if event.created_at is not None:
            existing = bucket["last_used_at"]
            if existing is None or event.created_at > existing:
                bucket["last_used_at"] = event.created_at

    output: list[UsageAggregate] = []
    for bucket in buckets.values():
        attempts = int(bucket["attempts"])
        success = int(bucket["success"])
        failures = int(bucket["failure"])
        latency_count = int(bucket["latency_count"])
        avg_latency = (
            round(float(bucket["latency_sum"]) / latency_count, 1)
            if latency_count
            else None
        )
        success_rate = round((success / attempts) * 100, 2) if attempts else 0.0
        output.append(UsageAggregate(
            scope=str(bucket["scope"]),
            provider=str(bucket["provider"]),
            model=str(bucket["model"]),
            feature=(
                None if bucket["feature"] is None else str(bucket["feature"])
            ),
            attempts=attempts,
            success=success,
            failure=failures,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            last_used_at=bucket["last_used_at"],
        ))
    return sorted(output, key=lambda item: item.attempts, reverse=True)


def _audit(db: Session, actor_id: int, action: str, row: AiProviderCredential, *, before=None, after=None) -> None:
    db.add(PlatformAuditEvent(
        actor_id=actor_id,
        action=action,
        target_type="ai_provider_credential",
        target_id=str(row.id or ""),
        reason="Administrator managed Sasha AI provider routing",
        before_json=before,
        after_json=after,
    ))


@router.get("/providers/status")
def provider_status(
    db: Session = Depends(get_db),
    _: User = Depends(AuthService.get_current_active_user),
):
    try:
        return _provider_status(db)
    except SQLAlchemyError:
        db.rollback()
        return {
            "configured": has_configured_provider(),
            "active_credentials": 0,
            "healthy_credentials": 0,
            "configured_credentials": 0,
            "providers": [],
        }


@router.get("/providers/usage", response_model=UsageReport)
def provider_usage(
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
    days: int = 7,
):
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be greater than 0")
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        events = (
            db.query(AiProviderUsageEvent)
            .filter(AiProviderUsageEvent.created_at >= since)
            .order_by(AiProviderUsageEvent.created_at.desc())
            .all()
        )
        total_attempts = len(events)
        total_success = sum(1 for event in events if event.success)
        total_failures = total_attempts - total_success
        recent_failures = [
            RecentFailure(
                id=event.id,
                credential_id=event.credential_id,
                provider=event.provider,
                model=event.model,
                feature=event.feature,
                error=event.error,
                created_at=event.created_at,
            )
            for event in (
                db.query(AiProviderUsageEvent)
                .filter(AiProviderUsageEvent.created_at >= since, AiProviderUsageEvent.success == 0)
                .order_by(AiProviderUsageEvent.created_at.desc())
                .limit(10)
                .all()
            )
        ]
    except SQLAlchemyError:
        db.rollback()
        return UsageReport(
            period_days=days,
            total_attempts=0,
            total_success=0,
            total_failures=0,
            success_rate=0.0,
            by_provider=[],
            by_feature=[],
            recent_failures=[],
        )

    success_rate = round((total_success / total_attempts) * 100, 2) if total_attempts else 0.0
    return UsageReport(
        period_days=days,
        total_attempts=total_attempts,
        total_success=total_success,
        total_failures=total_failures,
        success_rate=success_rate,
        by_provider=_aggregate_usage(events, by_feature=False),
        by_feature=_aggregate_usage(events, by_feature=True),
        recent_failures=recent_failures,
    )


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(db: Session = Depends(get_db), _: User = Depends(AuthService.require_admin)):
    return db.query(AiProviderCredential).order_by(AiProviderCredential.priority, AiProviderCredential.id).all()


@router.post("/providers", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def create_provider(
    payload: ProviderCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    row = AiProviderCredential(
        label=payload.label,
        provider=payload.provider,
        model=payload.model or DEFAULT_MODELS[payload.provider],
        key_ciphertext=encrypt_api_key(payload.api_key),
        key_fingerprint=key_fingerprint(payload.api_key),
        key_hint=key_hint(payload.api_key),
        priority=payload.priority,
        is_active=payload.is_active,
        created_by=admin.id,
        updated_by=admin.id,
    )
    db.add(row)
    try:
        db.flush()
        _audit(db, admin.id, "ai_provider.created", row, after=_snapshot(row))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This API key is already registered for that provider") from exc
    db.refresh(row)
    return row


@router.patch("/providers/{credential_id}", response_model=ProviderOut)
def update_provider(
    credential_id: int,
    payload: ProviderUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    row = _row(db, credential_id)
    before = _snapshot(row)
    changes = payload.model_dump(exclude_unset=True)
    api_key = changes.pop("api_key", None)
    for field, value in changes.items():
        setattr(row, field, value)
    if api_key:
        row.key_ciphertext = encrypt_api_key(api_key)
        row.key_fingerprint = key_fingerprint(api_key)
        row.key_hint = key_hint(api_key)
        row.health_status = "untested"
        row.failure_count = 0
        row.last_error = ""
    row.updated_by = admin.id
    try:
        db.flush()
        _audit(db, admin.id, "ai_provider.updated", row, before=before, after=_snapshot(row))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This API key is already registered for that provider") from exc
    db.refresh(row)
    return row


@router.post("/providers/{credential_id}/test", response_model=ProviderOut)
def test_provider(
    credential_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    row = _row(db, credential_id)
    test_credential(db, row)
    _audit(db, admin.id, "ai_provider.tested", row, after=_snapshot(row))
    db.commit()
    db.refresh(row)
    return row


@router.delete("/providers/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(
    credential_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    row = _row(db, credential_id)
    _audit(db, admin.id, "ai_provider.deleted", row, before=_snapshot(row))
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
