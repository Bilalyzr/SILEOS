"""Staff leave and substitution.

Balances are derived from approved requests; nothing stores a running total.
"""

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


LEAVE_STATUSES = ("pending", "approved", "rejected", "cancelled")
SUBSTITUTION_STATUSES = ("open", "assigned", "released")


class CampusLeaveType(Base):
    __tablename__ = "campus_leave_types"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    academic_year = Column(String(32), nullable=False)
    code = Column(String(20), nullable=False)
    name = Column(String(80), nullable=False)
    annual_quota = Column(Integer, nullable=False, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("institution_id", "academic_year", "code", name="uq_campus_leave_type"),
    )


class CampusLeaveRequest(Base):
    __tablename__ = "campus_leave_requests"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False, index=True)
    type_id = Column(Integer, ForeignKey("campus_leave_types.id"), nullable=False)
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=False)
    days = Column(Integer, nullable=False)
    note = Column(String(500), nullable=False, default="")
    status = Column(String(20), nullable=False, default="pending")
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(String(500), nullable=False, default="")
    override = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        Index("ix_campus_leave_requests_institution_status", "institution_id", "status"),
    )


class CampusSubstitution(Base):
    __tablename__ = "campus_substitutions"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    leave_id = Column(Integer, ForeignKey("campus_leave_requests.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("campus_events.id"), nullable=False, index=True)
    absent_member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False)
    substitute_member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(String(500), nullable=False, default="")
    __table_args__ = (
        UniqueConstraint("leave_id", "event_id", name="uq_campus_substitution"),
    )
