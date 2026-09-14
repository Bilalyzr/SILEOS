"""Campus hostel: blocks, rooms, allocations, out-passes and visitors."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
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


ROOM_TYPES = ("single", "double", "triple", "dormitory")
PASS_STATUSES = ("pending", "approved", "rejected", "returned")


class CampusHostelBlock(Base):
    __tablename__ = "campus_hostel_blocks"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    warden_member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=True)
    gender = Column(String(10), nullable=False, default="any")
    fee_amount = Column(MONEY, nullable=True)
    currency = Column(String(3), nullable=False, default="INR")
    fee_plan_id = Column(Integer, ForeignKey("tuition_fee_plans.id"), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("institution_id", "name", name="uq_campus_hostel_block"),)


class CampusHostelRoom(Base):
    __tablename__ = "campus_hostel_rooms"
    id = Column(Integer, primary_key=True)
    block_id = Column(Integer, ForeignKey("campus_hostel_blocks.id"), nullable=False, index=True)
    number = Column(String(20), nullable=False)
    floor = Column(String(20), nullable=False, default="")
    room_type = Column(String(20), nullable=False, default="double")
    capacity = Column(Integer, nullable=False, default=2)
    active = Column(Boolean, nullable=False, default=True)
    __table_args__ = (UniqueConstraint("block_id", "number", name="uq_campus_hostel_room"),)


class CampusHostelAllocation(Base):
    __tablename__ = "campus_hostel_allocations"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("campus_hostel_rooms.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False)
    fee_assignment_id = Column(Integer, ForeignKey("tuition_fee_assignments.id"), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    checked_in_on = Column(Date, nullable=False)
    checked_out_on = Column(Date, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_campus_hostel_allocations_member_status", "member_id", "status"),)


class CampusHostelPass(Base):
    __tablename__ = "campus_hostel_passes"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False, index=True)
    kind = Column(String(20), nullable=False, default="outpass")
    reason = Column(String(500), nullable=False, default="")
    leaves_at = Column(DateTime(timezone=True), nullable=False)
    returns_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(String(500), nullable=False, default="")
    returned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampusHostelVisitor(Base):
    __tablename__ = "campus_hostel_visitors"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False, index=True)
    visitor_name = Column(String(120), nullable=False)
    relation = Column(String(60), nullable=False, default="")
    phone = Column(String(20), nullable=False, default="")
    checked_in_at = Column(DateTime(timezone=True), nullable=False, index=True)
    checked_out_at = Column(DateTime(timezone=True), nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
