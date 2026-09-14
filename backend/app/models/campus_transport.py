"""Campus transport: routes, stops, student assignments and daily boarding."""

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


class CampusTransportRoute(Base):
    __tablename__ = "campus_transport_routes"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    vehicle_number = Column(String(40), nullable=False, default="")
    driver_name = Column(String(120), nullable=False, default="")
    driver_phone = Column(String(20), nullable=False, default="")
    capacity = Column(Integer, nullable=False, default=40)
    fee_amount = Column(MONEY, nullable=True)
    currency = Column(String(3), nullable=False, default="INR")
    fee_plan_id = Column(Integer, ForeignKey("tuition_fee_plans.id"), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("institution_id", "name", name="uq_campus_transport_route"),)


class CampusTransportStop(Base):
    __tablename__ = "campus_transport_stops"
    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey("campus_transport_routes.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    name = Column(String(120), nullable=False)
    pickup_time = Column(String(5), nullable=False, default="")
    drop_time = Column(String(5), nullable=False, default="")
    landmark = Column(String(200), nullable=False, default="")
    __table_args__ = (UniqueConstraint("route_id", "sequence", name="uq_campus_transport_stop"),)


class CampusTransportAssignment(Base):
    __tablename__ = "campus_transport_assignments"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    route_id = Column(Integer, ForeignKey("campus_transport_routes.id"), nullable=False, index=True)
    stop_id = Column(Integer, ForeignKey("campus_transport_stops.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False)
    fee_assignment_id = Column(Integer, ForeignKey("tuition_fee_assignments.id"), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    started_on = Column(Date, nullable=False)
    ended_on = Column(Date, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_campus_transport_assignments_member_status", "member_id", "status"),)


class CampusTransportLog(Base):
    __tablename__ = "campus_transport_logs"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("campus_transport_routes.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False)
    day = Column(Date, nullable=False, index=True)
    boarded = Column(Boolean, nullable=False, default=False)
    dropped = Column(Boolean, nullable=False, default=False)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("route_id", "member_id", "day", name="uq_campus_transport_log"),)
