"""Validated commands for Meiporul field operations."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Command(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class SiteCreate(Command):
    tenant_id: int = Field(gt=0)
    institution_id: int | None = Field(default=None, gt=0)
    contract_id: int | None = Field(default=None, gt=0)
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=3, max_length=160)
    address: dict = Field(default_factory=dict)
    room_count: int = Field(default=1, gt=0, le=100)
    headset_capacity: int = Field(default=0, ge=0, le=10_000)
    go_live_on: date | None = None
    notes: str = Field(default="", max_length=10_000)


class SiteUpdate(Command):
    status: Literal["planned", "installing", "active", "paused", "retired"] | None = None
    name: str | None = Field(default=None, min_length=3, max_length=160)
    address: dict | None = None
    room_count: int | None = Field(default=None, gt=0, le=100)
    headset_capacity: int | None = Field(default=None, ge=0, le=10_000)
    network_readiness: Literal["unknown", "failed", "conditional", "ready"] | None = None
    go_live_on: date | None = None
    notes: str | None = Field(default=None, max_length=10_000)
    reason: str = Field(min_length=3, max_length=500)


class DeviceCreate(Command):
    asset_tag: str = Field(min_length=2, max_length=80)
    serial_number: str = Field(default="", max_length=160)
    device_type: Literal["headset", "controller", "workstation", "router", "haptic", "other"]
    vendor: str = Field(default="", max_length=100)
    model: str = Field(default="", max_length=100)
    os_version: str = Field(default="", max_length=80)
    firmware_version: str = Field(default="", max_length=80)
    status: Literal["inventory", "provisioning", "ready", "deployed", "maintenance", "quarantined", "retired"] = "inventory"
    assigned_room: str = Field(default="", max_length=80)
    commissioned_on: date | None = None
    warranty_through: date | None = None
    metadata: dict = Field(default_factory=dict)


class DeviceUpdate(Command):
    status: Literal["inventory", "provisioning", "ready", "deployed", "maintenance", "quarantined", "retired"] | None = None
    assigned_room: str | None = Field(default=None, max_length=80)
    os_version: str | None = Field(default=None, max_length=80)
    firmware_version: str | None = Field(default=None, max_length=80)
    last_seen_at: datetime | None = None
    warranty_through: date | None = None
    metadata: dict | None = None
    reason: str = Field(min_length=3, max_length=500)


class InspectionCreate(Command):
    inspection_type: Literal["pre_install", "routine", "incident", "post_repair"]
    status: Literal["scheduled", "passed", "failed", "conditional"] = "scheduled"
    scheduled_for: datetime
    completed_at: datetime | None = None
    checklist: list[dict] = Field(default_factory=list, max_length=200)
    findings: str = Field(default="", max_length=20_000)
    corrective_actions: str = Field(default="", max_length=20_000)
    next_due_on: date | None = None
    inspector_id: int | None = Field(default=None, gt=0)


class MilestoneCreate(Command):
    title: str = Field(min_length=3, max_length=160)
    due_on: date | None = None
    owner_user_id: int | None = Field(default=None, gt=0)
    notes: str = Field(default="", max_length=10_000)


class MilestoneUpdate(Command):
    status: Literal["not_started", "in_progress", "blocked", "completed", "skipped"]
    evidence_urls: list[str] = Field(default_factory=list, max_length=50)
    notes: str = Field(default="", max_length=10_000)
    reason: str = Field(min_length=3, max_length=500)


class TicketCreate(Command):
    device_id: int | None = Field(default=None, gt=0)
    contract_id: int | None = Field(default=None, gt=0)
    category: Literal["hardware", "software", "network", "content", "safety", "training", "other"]
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=30_000)


class TicketUpdate(Command):
    status: Literal["open", "triaged", "in_progress", "waiting_customer", "resolved", "closed"]
    assignee_id: int | None = Field(default=None, gt=0)
    resolution: str = Field(default="", max_length=30_000)
    reason: str = Field(min_length=3, max_length=500)
