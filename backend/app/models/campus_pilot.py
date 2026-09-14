"""Daily campus operations and explicit, verified WhatsApp subscriptions."""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
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


class CampusOnboardingState(Base):
    __tablename__ = "campus_onboarding_states"
    institution_id = Column(Integer, ForeignKey("institutions.id"), primary_key=True)
    dismissed = Column(Boolean, nullable=False, default=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CampusEvent(Base):
    __tablename__ = "campus_events"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    batch_id = Column(Integer, ForeignKey("institution_batches.id"))
    teacher_id = Column(Integer, ForeignKey("institution_members.id"))
    title = Column(String(160), nullable=False)
    kind = Column(String(20), nullable=False)
    room = Column(String(80), nullable=False, default="")
    description = Column(String(1000), nullable=False, default="")
    starts_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    series = Column(String(40), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)


class CampusAnnouncement(Base):
    __tablename__ = "campus_announcements"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    batch_id = Column(Integer, ForeignKey("institution_batches.id"))
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampusNoticeRead(Base):
    __tablename__ = "campus_notice_reads"
    id = Column(Integer, primary_key=True)
    announcement_id = Column(
        Integer, ForeignKey("campus_announcements.id"), nullable=False
    )
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False)
    read_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("announcement_id", "member_id", name="uq_campus_notice_read"),
    )


class CampusGoal(Base):
    __tablename__ = "campus_goals"
    id = Column(Integer, primary_key=True)
    member_id = Column(
        Integer, ForeignKey("institution_members.id"), nullable=False, index=True
    )
    title = Column(String(160), nullable=False)
    due_on = Column(Date, nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="planned")
    completed = Column(Boolean, nullable=False, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)


class CampusGradePolicy(Base):
    __tablename__ = "campus_grade_policies"
    institution_id = Column(Integer, ForeignKey("institutions.id"), primary_key=True)
    bands = Column(JSON, nullable=False)


class CampusReportComment(Base):
    __tablename__ = "campus_report_comments"
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False)
    term_id = Column(Integer, ForeignKey("campus_terms.id"), nullable=False)
    comment = Column(String(2000), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint("member_id", "term_id", name="uq_campus_report_comment"),
    )


class CampusWhatsAppContact(Base):
    __tablename__ = "campus_whatsapp_contacts"
    member_id = Column(Integer, ForeignKey("institution_members.id"), primary_key=True)
    phone = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    challenge = Column(String(64), nullable=True, unique=True)
    expires_at = Column(DateTime(timezone=True))
    consent_at = Column(DateTime(timezone=True))


class CampusWhatsAppCampaign(Base):
    __tablename__ = "campus_whatsapp_campaigns"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    request_key = Column(String(64), nullable=False)
    template = Column(String(120), nullable=False)
    language = Column(String(20), nullable=False)
    parameters = Column(JSON, nullable=False)
    batch_id = Column(Integer, ForeignKey("institution_batches.id"), nullable=True)
    header_image_url = Column(String(500), nullable=False, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("institution_id", "request_key", name="uq_campus_wa_campaign"),
    )


class CampusWhatsAppMessage(Base):
    __tablename__ = "campus_whatsapp_messages"
    id = Column(Integer, primary_key=True)
    campaign_id = Column(
        Integer, ForeignKey("campus_whatsapp_campaigns.id"), nullable=False, index=True
    )
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False)
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
        UniqueConstraint("campaign_id", "member_id", name="uq_campus_wa_message"),
        Index(
            "ix_campus_whatsapp_messages_delivery_due",
            "status",
            "next_attempt_at",
            "id",
        ),
    )


class CampusWhatsAppWebhookEvent(Base):
    __tablename__ = "campus_whatsapp_webhook_events"
    id = Column(Integer, primary_key=True)
    event_key = Column(String(250), nullable=False, unique=True)
    event_type = Column(String(30), nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
