"""Tuition fee reminders: one policy per institution, one ledger row per send.

The ledger row is the idempotency unit. A row exists per installment, stage,
recipient and channel, so a re-run can never send the same reminder twice.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.core.database import Base
from app.models.tuition import MONEY


REMINDER_KINDS = ("upcoming", "due", "overdue", "receipt", "manual")
REMINDER_CHANNELS = ("whatsapp", "email")
REMINDER_STATUSES = ("queued", "sent", "failed", "skipped")


class TuitionReminderPolicy(Base):
    __tablename__ = "tuition_reminder_policies"
    institution_id = Column(Integer, ForeignKey("institutions.id"), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False)
    days_before = Column(JSON, nullable=False, default=list)
    overdue_every_days = Column(Integer, nullable=False, default=7)
    overdue_max = Column(Integer, nullable=False, default=3)
    send_hour = Column(Integer, nullable=False, default=9)
    channels = Column(JSON, nullable=False, default=list)
    whatsapp_template = Column(String(120), nullable=False, default="")
    whatsapp_language = Column(String(20), nullable=False, default="en")
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TuitionReminder(Base):
    __tablename__ = "tuition_reminders"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    assignment_id = Column(
        Integer, ForeignKey("tuition_fee_assignments.id"), nullable=False, index=True
    )
    installment_id = Column(
        Integer, ForeignKey("tuition_installments.id"), nullable=True, index=True
    )
    receipt_id = Column(Integer, ForeignKey("tuition_receipts.id"), nullable=True)
    student_member_id = Column(
        Integer, ForeignKey("institution_members.id"), nullable=False, index=True
    )
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String(20), nullable=False)
    stage = Column(String(32), nullable=False)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    skip_reason = Column(String(120), nullable=False, default="")
    error = Column(String(250), nullable=False, default="")
    attempts = Column(Integer, nullable=False, default=0)
    amount = Column(MONEY, nullable=False)
    currency = Column(String(3), nullable=False)
    due_on = Column(DateTime(timezone=False), nullable=True)
    dedupe_key = Column(String(120), nullable=False)
    whatsapp_message_id = Column(
        Integer, ForeignKey("campus_whatsapp_messages.id"), nullable=True
    )
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint("institution_id", "dedupe_key", name="uq_tuition_reminder_dedupe"),
        Index("ix_tuition_reminders_status_created", "status", "created_at"),
    )
