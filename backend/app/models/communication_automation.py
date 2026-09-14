"""Preferences, lifecycle rules and durable institution communication outbox."""

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
    Time,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class CommunicationProfile(Base):
    __tablename__ = "communication_profiles"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")
    quiet_start = Column(Time, nullable=True)
    quiet_end = Column(Time, nullable=True)
    digest_cadence = Column(String(16), nullable=False, default="instant")
    digest_time = Column(Time, nullable=False)
    digest_weekday = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "digest_cadence IN ('instant','daily','weekly')",
            name="ck_communication_profile_digest",
        ),
        CheckConstraint(
            "digest_weekday >= 0 AND digest_weekday <= 6",
            name="ck_communication_profile_weekday",
        ),
        CheckConstraint(
            "(quiet_start IS NULL AND quiet_end IS NULL) OR "
            "(quiet_start IS NOT NULL AND quiet_end IS NOT NULL AND quiet_start <> quiet_end)",
            name="ck_communication_profile_quiet_pair",
        ),
    )


class CommunicationTopicPreference(Base):
    __tablename__ = "communication_topic_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic = Column(String(64), nullable=False)
    in_app_enabled = Column(Boolean, nullable=False, default=True)
    email_enabled = Column(Boolean, nullable=False, default=False)
    push_enabled = Column(Boolean, nullable=False, default=False)
    whatsapp_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_communication_user_topic"),
    )


class InstitutionAutomationRule(Base):
    __tablename__ = "institution_automation_rules"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(160), nullable=False)
    topic = Column(String(64), nullable=False)
    event_trigger = Column(String(80), nullable=False)
    audience_roles = Column(JSON, nullable=False)
    batch_id = Column(
        Integer,
        ForeignKey("institution_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    channels = Column(JSON, nullable=False)
    title_template = Column(String(200), nullable=False)
    body_template = Column(Text, nullable=False)
    action_url_template = Column(String(500), nullable=False, default="")
    whatsapp_template = Column(String(120), nullable=False, default="")
    whatsapp_parameters = Column(JSON, nullable=False)
    whatsapp_header_image_url = Column(String(500), nullable=False, default="")
    approval_policy = Column(String(24), nullable=False, default="manager_required")
    status = Column(String(20), nullable=False, default="draft")
    schedule_mode = Column(String(20), nullable=False, default="immediate")
    schedule_timezone = Column(String(64), nullable=False)
    schedule_time = Column(Time, nullable=False)
    schedule_weekday = Column(Integer, nullable=False, default=0)
    run_recipient_cap = Column(Integer, nullable=False, default=500)
    daily_message_cap = Column(Integer, nullable=False, default=2000)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    paused_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id", "name", name="uq_institution_automation_name"
        ),
        CheckConstraint(
            "status IN ('draft','approved','paused')",
            name="ck_institution_automation_status",
        ),
        CheckConstraint(
            "approval_policy IN ('manager_required','owner_required')",
            name="ck_institution_automation_approval",
        ),
        CheckConstraint(
            "schedule_mode IN ('immediate','daily','weekly')",
            name="ck_institution_automation_schedule",
        ),
        CheckConstraint(
            "schedule_weekday >= 0 AND schedule_weekday <= 6",
            name="ck_institution_automation_weekday",
        ),
        CheckConstraint(
            "run_recipient_cap >= 1 AND run_recipient_cap <= 2000",
            name="ck_institution_automation_run_cap",
        ),
        CheckConstraint(
            "daily_message_cap >= 1 AND daily_message_cap <= 10000",
            name="ck_institution_automation_daily_cap",
        ),
        Index(
            "ix_institution_automation_status_trigger",
            "institution_id",
            "status",
            "event_trigger",
        ),
    )


class AutomationDispatch(Base):
    __tablename__ = "automation_dispatches"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        Integer,
        ForeignKey("institution_automation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    event_payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    recipient_count = Column(Integer, nullable=False, default=0)
    outbox_count = Column(Integer, nullable=False, default=0)
    suppressed_count = Column(Integer, nullable=False, default=0)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("rule_id", "event_key", name="uq_automation_dispatch_event"),
        CheckConstraint(
            "status IN ('queued','partial','completed','cancelled')",
            name="ck_automation_dispatch_status",
        ),
        Index(
            "ix_automation_dispatch_due", "status", "scheduled_for", "id"
        ),
    )


class CommunicationOutbox(Base):
    __tablename__ = "communication_outbox"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        Integer,
        ForeignKey("institution_automation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dispatch_id = Column(
        Integer,
        ForeignKey("automation_dispatches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_member_id = Column(
        Integer,
        ForeignKey("institution_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    topic = Column(String(64), nullable=False)
    channel = Column(String(20), nullable=False)
    idempotency_key = Column(String(64), nullable=False, unique=True)
    status = Column(String(24), nullable=False, default="pending")
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    message_payload = Column(JSON, nullable=False)
    reason = Column(String(240), nullable=False, default="")
    attempts = Column(Integer, nullable=False, default=0)
    provider_kind = Column(String(30), nullable=False, default="")
    provider_message_id = Column(
        Integer,
        ForeignKey("campus_whatsapp_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    notification_id = Column(
        Integer, ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "dispatch_id",
            "recipient_user_id",
            "channel",
            name="uq_communication_outbox_recipient_channel",
        ),
        CheckConstraint(
            "channel IN ('in_app','email','push','whatsapp')",
            name="ck_communication_outbox_channel",
        ),
        CheckConstraint(
            "status IN ('pending','awaiting_adapter','suppressed','handed_off',"
            "'delivered','failed','cancelled')",
            name="ck_communication_outbox_status",
        ),
        Index(
            "ix_communication_outbox_due", "status", "scheduled_for", "id"
        ),
        Index(
            "ix_communication_outbox_user_topic",
            "recipient_user_id",
            "topic",
            "created_at",
        ),
    )
