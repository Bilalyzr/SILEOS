"""Durable inbox for Razorpay webhook events.

The UNIQUE constraint on event_id IS the idempotency mechanism: duplicate
gateway deliveries insert-conflict into a no-op. Rows are never deleted —
they are the audit trail for the money pipeline.
"""
import enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.types import Enum
from sqlalchemy.sql import func

from app.core.database import Base


class WebhookEventStatus(enum.Enum):
    RECEIVED = "received"    # stored, not yet (successfully) processed
    PROCESSED = "processed"  # handler completed
    FAILED = "failed"        # handler raised; sweeper retries up to 5x
    SKIPPED = "skipped"      # valid signature, event type we don't handle yet


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, default="")
    payload = Column(JSON, nullable=False, default={})
    signature_valid = Column(Boolean, nullable=False, default=False)
    status = Column(
        Enum(WebhookEventStatus), nullable=False, default=WebhookEventStatus.RECEIVED
    )
    attempts = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, event_id={self.event_id}, type={self.event_type}, status={self.status})>"
