"""Encrypted AI provider credentials managed by platform administrators.

The browser only ever receives ``key_hint``. The credential ciphertext is
decrypted for the duration of one server-side provider request and is never
written to logs or API responses.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class AiProviderCredential(Base):
    __tablename__ = "ai_provider_credentials"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False)
    provider = Column(String(24), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    key_ciphertext = Column(Text, nullable=False)
    key_fingerprint = Column(String(64), nullable=False)
    key_hint = Column(String(16), nullable=False)
    priority = Column(Integer, nullable=False, default=100, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    health_status = Column(String(20), nullable=False, default="untested", index=True)
    failure_count = Column(Integer, nullable=False, default=0)
    last_error = Column(String(300), nullable=False, default="")
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("provider", "key_fingerprint", name="uq_ai_provider_key_fingerprint"),
    )
