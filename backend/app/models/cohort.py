"""
College, Cohort, ReferralCode, CohortMembership, Session,
SessionAttendance — SS1.

Owned by the SS1 implementer.
Integration: SPOC greenlight writes into candidate.CandidateEligibility
(SS2 model). Do not duplicate eligibility data here.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Date, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    city = Column(String(100), default="")
    state = Column(String(100), default="")
    contact_name = Column(String(255), default="")
    contact_email = Column(String(255), default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", foreign_keys=[created_by])
    cohorts = relationship("Cohort", back_populates="college", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<College(id={self.id}, name={self.name})>"


class Cohort(Base):
    __tablename__ = "cohorts"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    spoc_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), default="")
    max_students = Column(Integer, default=0)
    # Paid cohort seats: when set, checkout with this cohort charges this
    # price instead of the course price. NULL = no seat pricing.
    seat_price = Column(Numeric(10, 2), nullable=True)
    starts_on = Column(Date, nullable=True)
    ends_on = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    college = relationship("College", back_populates="cohorts")
    course = relationship("Course", foreign_keys=[course_id])
    spoc = relationship("User", foreign_keys=[spoc_user_id])
    referral_code = relationship("ReferralCode", back_populates="cohort", uselist=False, cascade="all, delete-orphan")
    memberships = relationship("CohortMembership", back_populates="cohort", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="cohort", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cohort(id={self.id}, name={self.name})>"


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True, index=True)
    cohort_id = Column(Integer, ForeignKey("cohorts.id"), nullable=False, unique=True)
    code = Column(String(64), unique=True, index=True, nullable=False)
    max_uses = Column(Integer, default=0, nullable=False)
    used_count = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cohort = relationship("Cohort", back_populates="referral_code")

    def __repr__(self):
        return f"<ReferralCode(code={self.code}, used={self.used_count}/{self.max_uses})>"


class CohortMembership(Base):
    __tablename__ = "cohort_memberships"

    id = Column(Integer, primary_key=True, index=True)
    cohort_id = Column(Integer, ForeignKey("cohorts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    cohort = relationship("Cohort", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("cohort_id", "user_id", name="uq_cohort_membership_cohort_user"),
    )

    def __repr__(self):
        return f"<CohortMembership(cohort_id={self.cohort_id}, user_id={self.user_id})>"


class Session(Base):
    __tablename__ = "cohort_sessions"

    id = Column(Integer, primary_key=True, index=True)
    cohort_id = Column(Integer, ForeignKey("cohorts.id"), nullable=False, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=60, nullable=False)
    topic = Column(String(500), default="")
    session_type = Column(String(32), default="lecture")  # lecture|lab|evaluation|other
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cohort = relationship("Cohort", back_populates="sessions")
    creator = relationship("User", foreign_keys=[created_by])
    attendance = relationship("SessionAttendance", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(id={self.id}, cohort_id={self.cohort_id}, topic={self.topic})>"


class SessionAttendance(Base):
    __tablename__ = "session_attendance"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("cohort_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="absent")  # present|absent|late|excused
    notes = Column(Text, default="")
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    marked_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    session = relationship("Session", back_populates="attendance")
    user = relationship("User", foreign_keys=[user_id])
    marker = relationship("User", foreign_keys=[marked_by])

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_attendance_session_user"),
    )

    def __repr__(self):
        return f"<SessionAttendance(session_id={self.session_id}, user_id={self.user_id}, status={self.status})>"
