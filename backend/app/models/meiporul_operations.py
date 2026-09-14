"""Meiporul field operations: immersive sites, fleet, safety, and support."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class ImmersiveLabSite(Base):
    __tablename__ = "immersive_lab_sites"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("platform_tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("commercial_contracts.id", ondelete="SET NULL"), nullable=True)
    code = Column(String(40), nullable=False)
    name = Column(String(160), nullable=False)
    status = Column(String(20), nullable=False, default="planned", index=True)
    address = Column(JSON, nullable=False, default=dict)
    room_count = Column(Integer, nullable=False, default=1)
    headset_capacity = Column(Integer, nullable=False, default=0)
    network_readiness = Column(String(20), nullable=False, default="unknown")
    safety_status = Column(String(20), nullable=False, default="pending")
    go_live_on = Column(Date, nullable=True)
    notes = Column(Text, nullable=False, default="")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_immersive_site_tenant_code"),
        CheckConstraint("status IN ('planned','installing','active','paused','retired')", name="ck_immersive_site_status"),
        CheckConstraint("network_readiness IN ('unknown','failed','conditional','ready')", name="ck_immersive_site_network"),
        CheckConstraint("safety_status IN ('pending','failed','conditional','passed')", name="ck_immersive_site_safety"),
        CheckConstraint("room_count > 0", name="ck_immersive_site_rooms"),
        CheckConstraint("headset_capacity >= 0", name="ck_immersive_site_capacity"),
        Index("ix_immersive_site_tenant_status", "tenant_id", "status"),
    )


class ImmersiveDevice(Base):
    __tablename__ = "immersive_devices"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("platform_tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("immersive_lab_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_tag = Column(String(80), nullable=False)
    serial_number = Column(String(160), nullable=False, default="")
    device_type = Column(String(24), nullable=False)
    vendor = Column(String(100), nullable=False, default="")
    model = Column(String(100), nullable=False, default="")
    os_version = Column(String(80), nullable=False, default="")
    firmware_version = Column(String(80), nullable=False, default="")
    status = Column(String(24), nullable=False, default="inventory", index=True)
    assigned_room = Column(String(80), nullable=False, default="")
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    commissioned_on = Column(Date, nullable=True)
    warranty_through = Column(Date, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "asset_tag", name="uq_immersive_device_asset_tag"),
        CheckConstraint("device_type IN ('headset','controller','workstation','router','haptic','other')", name="ck_immersive_device_type"),
        CheckConstraint("status IN ('inventory','provisioning','ready','deployed','maintenance','quarantined','retired')", name="ck_immersive_device_status"),
        Index("ix_immersive_device_site_status", "site_id", "status"),
    )


class ImmersiveSafetyInspection(Base):
    __tablename__ = "immersive_safety_inspections"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("platform_tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("immersive_lab_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_type = Column(String(24), nullable=False)
    status = Column(String(20), nullable=False, default="scheduled", index=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    checklist = Column(JSON, nullable=False, default=list)
    findings = Column(Text, nullable=False, default="")
    corrective_actions = Column(Text, nullable=False, default="")
    next_due_on = Column(Date, nullable=True)
    inspector_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("inspection_type IN ('pre_install','routine','incident','post_repair')", name="ck_immersive_inspection_type"),
        CheckConstraint("status IN ('scheduled','passed','failed','conditional')", name="ck_immersive_inspection_status"),
        Index("ix_immersive_inspection_site_schedule", "site_id", "scheduled_for"),
    )


class ImmersiveDeploymentMilestone(Base):
    __tablename__ = "immersive_deployment_milestones"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("platform_tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("immersive_lab_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    title = Column(String(160), nullable=False)
    status = Column(String(24), nullable=False, default="not_started", index=True)
    due_on = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    evidence_urls = Column(JSON, nullable=False, default=list)
    notes = Column(Text, nullable=False, default="")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("site_id", "sequence", name="uq_immersive_milestone_sequence"),
        CheckConstraint("sequence > 0", name="ck_immersive_milestone_sequence"),
        CheckConstraint("status IN ('not_started','in_progress','blocked','completed','skipped')", name="ck_immersive_milestone_status"),
        Index("ix_immersive_milestone_site_status", "site_id", "status"),
    )


class ImmersiveServiceTicket(Base):
    __tablename__ = "immersive_service_tickets"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("platform_tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("immersive_lab_sites.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("immersive_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("commercial_contracts.id", ondelete="SET NULL"), nullable=True)
    reference = Column(String(40), nullable=False, unique=True, index=True)
    category = Column(String(24), nullable=False)
    priority = Column(String(12), nullable=False, default="normal", index=True)
    status = Column(String(24), nullable=False, default="open", index=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    resolution = Column(Text, nullable=False, default="")
    sla_due_at = Column(DateTime(timezone=True), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("category IN ('hardware','software','network','content','safety','training','other')", name="ck_immersive_ticket_category"),
        CheckConstraint("priority IN ('low','normal','high','critical')", name="ck_immersive_ticket_priority"),
        CheckConstraint("status IN ('open','triaged','in_progress','waiting_customer','resolved','closed')", name="ck_immersive_ticket_status"),
        Index("ix_immersive_ticket_tenant_status", "tenant_id", "status"),
        Index("ix_immersive_ticket_sla", "status", "sla_due_at"),
    )
