"""
Admin Message Model - Messages from admin to students/interns
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class AdminMessage(Base):
    __tablename__ = "admin_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_type = Column(String(20), nullable=False)  # 'user' or 'company'
    recipient_id = Column(Integer, nullable=False)  # user_id or company_id
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Outcome of the email delivery attempt: 'sent', 'failed', or 'no_email'.
    # NULL on rows written before messages were emailed at all.
    email_status = Column(String(20), nullable=True)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
