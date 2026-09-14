"""Account-wide WhatsApp consent and platform communication records."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class WhatsAppContact(Base):
    """One WhatsApp consent state for one SashaInfinity account."""

    __tablename__ = "whatsapp_contacts"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    phone = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    challenge = Column(String(64), nullable=True, unique=True)
    expires_at = Column(DateTime(timezone=True))
    consent_at = Column(DateTime(timezone=True))
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WhatsAppCampaign(Base):
    """A platform-admin campaign aimed at explicitly selected account roles."""

    __tablename__ = "whatsapp_campaigns"

    id = Column(Integer, primary_key=True)
    request_key = Column(String(64), nullable=False, unique=True)
    template = Column(String(120), nullable=False)
    language = Column(String(20), nullable=False)
    parameters = Column(JSON, nullable=False)
    roles = Column(JSON, nullable=False)
    header_image_url = Column(String(500), nullable=False, default="")
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WhatsAppMessage(Base):
    """Durable delivery state for one account in a platform campaign."""

    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(
        Integer,
        ForeignKey("whatsapp_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    phone = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    provider_id = Column(String(250), unique=True)
    error = Column(String(200), nullable=False, default="")
    callback_key = Column(String(64), nullable=False, unique=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), server_default=func.now())
    last_event_at = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # A retry of the same campaign command cannot enqueue the same user twice.
        # The named constraint also makes migration diagnostics unambiguous.
        UniqueConstraint("campaign_id", "user_id", name="uq_whatsapp_message"),
        Index(
            "ix_whatsapp_messages_delivery_due",
            "status",
            "next_attempt_at",
            "id",
        ),
    )


class WhatsAppStatusReceipt(Base):
    """A signed provider status waiting for its outbound message to be visible.

    Meta can deliver a webhook concurrently with the send response. Keeping the
    unmatched receipt here avoids losing that state without asking Meta to retry
    permanently unknown message identifiers forever.
    """

    __tablename__ = "whatsapp_status_receipts"

    id = Column(Integer, primary_key=True)
    event_key = Column(String(250), nullable=False, unique=True)
    provider_id = Column(String(250), nullable=False)
    status = Column(String(20), nullable=False)
    event_at = Column(Integer, nullable=False, default=0)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_whatsapp_status_receipts_provider_id", "provider_id"),
        Index(
            "ix_whatsapp_status_receipts_due",
            "next_attempt_at",
            "expires_at",
            "id",
        ),
    )
