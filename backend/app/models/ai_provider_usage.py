"""Append-only AI provider usage and failover attempt log."""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.sql import func

from app.core.database import Base


class AiProviderUsageEvent(Base):
    __tablename__ = "ai_provider_usage_events"

    id = Column(Integer, primary_key=True, index=True)
    credential_id = Column(
        Integer,
        ForeignKey("ai_provider_credentials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider = Column(String(24), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    feature = Column(String(80), nullable=False, index=True)
    success = Column(Integer, nullable=False, default=0)  # 1 if success else 0
    latency_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_ai_provider_usage_provider_feature", "provider", "feature", "created_at"),
        Index("ix_ai_provider_usage_success_created", "success", "created_at"),
    )
