"""Shared platform tenancy, entitlements, audit, and delivery outbox.

A platform tenant is the commercial/customer boundary.  It is deliberately
separate from a business vertical: one school, creator, or company may be
entitled to capabilities from Meiporul, Seyappaduporul, and Utporul at the
same time.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


TENANT_KINDS = ("platform", "institution", "franchise", "company", "creator")
TENANT_STATUSES = ("trial", "active", "suspended", "archived")
TENANT_ROLES = (
    "owner",
    "admin",
    "teacher",
    "instructor",
    "student",
    "learner",
    "finance",
    "operations",
    "support",
    "analyst",
)
MEMBERSHIP_STATUSES = ("invited", "active", "suspended", "removed")
DOMAIN_STATUSES = ("pending", "verified", "disabled")
OUTBOX_STATUSES = ("pending", "published", "failed")


def _choice_check(column: str, values: tuple[str, ...], name: str) -> CheckConstraint:
    quoted = ",".join(f"'{value}'" for value in values)
    return CheckConstraint(f"{column} IN ({quoted})", name=name)


class PlatformTenant(Base):
    __tablename__ = "platform_tenants"

    id = Column(Integer, primary_key=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(160), nullable=False)
    kind = Column(String(24), nullable=False, default="institution", index=True)
    status = Column(String(20), nullable=False, default="trial", index=True)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")
    data_region = Column(String(32), nullable=False, default="in")
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        _choice_check("kind", TENANT_KINDS, "ck_platform_tenant_kind"),
        _choice_check("status", TENANT_STATUSES, "ck_platform_tenant_status"),
    )


class PlatformTenantMembership(Base):
    __tablename__ = "platform_tenant_memberships"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(24), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    permissions = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_platform_tenant_member"),
        _choice_check("role", TENANT_ROLES, "ck_platform_tenant_member_role"),
        _choice_check(
            "status", MEMBERSHIP_STATUSES, "ck_platform_tenant_member_status"
        ),
        Index("ix_platform_tenant_member_scope", "tenant_id", "status", "role"),
    )


class PlatformTenantDomain(Base):
    __tablename__ = "platform_tenant_domains"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hostname = Column(String(253), nullable=False, unique=True)
    vertical = Column(String(30), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    is_primary = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "vertical IS NULL OR vertical IN ('meiporul','seyappaduporul','utporul')",
            name="ck_platform_tenant_domain_vertical",
        ),
        _choice_check("status", DOMAIN_STATUSES, "ck_platform_tenant_domain_status"),
        Index("ix_platform_tenant_domain_scope", "tenant_id", "vertical", "status"),
    )


class PlatformTenantEntitlement(Base):
    __tablename__ = "platform_tenant_entitlements"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vertical = Column(String(30), nullable=False)
    feature_key = Column(String(80), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    quota = Column(JSON, nullable=False, default=dict)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_through = Column(DateTime(timezone=True), nullable=True)
    updated_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "vertical",
            "feature_key",
            name="uq_platform_tenant_entitlement",
        ),
        CheckConstraint(
            "vertical IN ('meiporul','seyappaduporul','utporul')",
            name="ck_platform_tenant_entitlement_vertical",
        ),
        CheckConstraint(
            "effective_through IS NULL OR effective_from IS NULL "
            "OR effective_through > effective_from",
            name="ck_platform_tenant_entitlement_window",
        ),
        Index(
            "ix_platform_tenant_entitlement_lookup",
            "tenant_id",
            "vertical",
            "enabled",
        ),
    )


class PlatformAuditEvent(Base):
    __tablename__ = "platform_audit_events"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(80), nullable=False)
    target_id = Column(String(100), nullable=False, default="")
    reason = Column(String(500), nullable=False, default="")
    before_json = Column(JSON, nullable=True)
    after_json = Column(JSON, nullable=True)
    request_id = Column(String(80), nullable=False, default="", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_platform_audit_tenant_created", "tenant_id", "created_at", "id"),
    )


class PlatformOutboxEvent(Base):
    __tablename__ = "platform_outbox_events"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    topic = Column(String(120), nullable=False, index=True)
    aggregate_type = Column(String(80), nullable=False)
    aggregate_id = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    idempotency_key = Column(String(160), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        _choice_check("status", OUTBOX_STATUSES, "ck_platform_outbox_status"),
        CheckConstraint("attempts >= 0", name="ck_platform_outbox_attempts"),
        Index("ix_platform_outbox_delivery", "status", "available_at", "id"),
    )
