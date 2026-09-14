"""Membership tiers and subscriptions (Razorpay Subscriptions).

State changes come exclusively from webhook handlers and the reconciliation
sweeper — see app/services/webhook_processor.py and reconciliation.py.
"""
import enum

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, text,
)
from sqlalchemy.types import Enum, Numeric
from sqlalchemy.sql import func

from app.core.database import Base


class MembershipStatus(enum.Enum):
    PENDING = "pending"        # subscription created, first charge not confirmed
    ACTIVE = "active"
    GRACE = "grace"            # renewal failed; access kept until grace_until
    SUSPENDED = "suspended"    # grace expired; membership enrollments suspended
    CANCELLED = "cancelled"    # user cancelled; access until current_period_end
    COMPLETED = "completed"    # total_count exhausted at gateway


class MembershipPlan(Base):
    __tablename__ = "membership_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, default="")
    all_access = Column(Boolean, nullable=False, default=False)
    period = Column(String(20), nullable=False)   # daily/weekly/monthly/yearly
    interval = Column(Integer, nullable=False, default=1)
    price = Column(Numeric(10, 2), nullable=False)  # INR per cycle
    grace_days = Column(Integer, nullable=False, default=7)
    razorpay_plan_id = Column(String(64), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())

    def __repr__(self):
        return f"<MembershipPlan(id={self.id}, name={self.name})>"


class MembershipPlanCourse(Base):
    """Curated tier coverage. Empty for all_access plans."""
    __tablename__ = "membership_plan_courses"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=False)
    razorpay_subscription_id = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(Enum(MembershipStatus), nullable=False,
                    default=MembershipStatus.PENDING)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    grace_until = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())

    # One blocking membership per user, enforced by the database rather than
    # by the /subscribe read-then-insert (which two concurrent requests can
    # both pass). The predicate matches BLOCKING_STATUSES in routers/memberships
    # and uses the stored Enum *names* (SQLAlchemy Enum persists names, not
    # values). Raw text keeps the IN-list identical on Postgres and SQLite.
    __table_args__ = (
        Index("uq_memberships_one_blocking_per_user", "user_id", unique=True,
              postgresql_where=text("status IN ('PENDING','ACTIVE','GRACE')"),
              sqlite_where=text("status IN ('PENDING','ACTIVE','GRACE')")),
    )

    def __repr__(self):
        return f"<Membership(id={self.id}, user={self.user_id}, status={self.status})>"
