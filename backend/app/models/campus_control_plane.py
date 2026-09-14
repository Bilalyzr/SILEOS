"""Tenant identity, integration and privacy control-plane records."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class CampusDomain(Base):
    __tablename__ = "campus_domains"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    hostname = Column(String(253), nullable=False, unique=True)
    verification_token = Column(String(80), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pending")
    is_primary = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampusIntegration(Base):
    __tablename__ = "campus_integrations"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    kind = Column(String(40), nullable=False)
    display_name = Column(String(120), nullable=False)
    status = Column(String(24), nullable=False, default="draft")
    config = Column(JSON, nullable=False, default=dict)
    secret_reference = Column(String(180), nullable=False, default="")
    last_sync_at = Column(DateTime(timezone=True))
    last_error = Column(String(500), nullable=False, default="")
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint("institution_id", "kind", name="uq_campus_integration_kind"),
    )


class CampusRetentionPolicy(Base):
    __tablename__ = "campus_retention_policies"

    institution_id = Column(Integer, ForeignKey("institutions.id"), primary_key=True)
    inactive_account_days = Column(Integer, nullable=False, default=730)
    learning_record_days = Column(Integer, nullable=False, default=2555)
    financial_record_days = Column(Integer, nullable=False, default=2920)
    application_record_days = Column(Integer, nullable=False, default=730)
    legal_hold = Column(Boolean, nullable=False, default=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CampusPrivacyRequest(Base):
    __tablename__ = "campus_privacy_requests"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    requester_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(24), nullable=False)
    status = Column(String(24), nullable=False, default="submitted", index=True)
    detail = Column(Text, nullable=False, default="")
    resolution_note = Column(Text, nullable=False, default="")
    due_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampusConsentReceipt(Base):
    __tablename__ = "campus_consent_receipts"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    subject_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    purpose = Column(String(80), nullable=False)
    notice_version = Column(String(40), nullable=False)
    status = Column(String(20), nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    granted_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "subject_user_id",
            "purpose",
            name="uq_campus_consent_purpose",
        ),
    )

