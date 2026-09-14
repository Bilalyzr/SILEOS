"""
Paid internship programs.

An `Internship` is an admin-created paid program tied to a SPOC user and a
dedicated `Cohort` (1:1). Students purchase access via Razorpay and receive
a single-use `InternshipVoucher` they can redeem at any course checkout
for a free enrollment.

The legacy `InternshipApplication` "apply-to-internship" flow has been
removed in favor of this voucher-based flow.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    Boolean,
    Index,
    UniqueConstraint,
)
from sqlalchemy.types import Numeric as Decimal
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Internship(Base):
    __tablename__ = "internships"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    cover_image = Column(String(500), default="")

    price = Column(Decimal(12, 2), nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)

    # SPOC user that oversees the cohort for this internship.
    spoc_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Dedicated 1:1 cohort auto-created for this internship. The cohort stays
    # alive even if the internship is deleted (history preservation) — so no
    # cascade from internship -> cohort.
    cohort_id = Column(Integer, ForeignKey("cohorts.id"), nullable=False, unique=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    spoc = relationship("User", foreign_keys=[spoc_user_id])
    cohort = relationship("Cohort", foreign_keys=[cohort_id])
    vouchers = relationship(
        "InternshipVoucher",
        back_populates="internship",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Internship(id={self.id}, slug={self.slug}, price={self.price})>"


class InternshipVoucher(Base):
    __tablename__ = "internship_vouchers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False, index=True)

    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False, index=True)
    buyer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    amount_paid = Column(Decimal(12, 2), nullable=False)
    razorpay_order_id = Column(String(255), default="")
    razorpay_payment_id = Column(String(255), default="")

    # 'issued' | 'redeemed'
    status = Column(String(20), default="issued", nullable=False)

    redeemed_on_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)

    # Admin override: manually-assigned hiring company. When set, takes
    # precedence over the auto-detected CompanyInterest.status='accepted' path
    # in the admin roster view.
    hired_by_company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    hired_by_override_at = Column(DateTime(timezone=True), nullable=True)
    hired_by_override_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Reporting manager assigned by the company. Optional. Set to a user
    # whose role is 'company' or 'company_manager' linked to the same
    # company that hired this voucher's owner.
    reporting_manager_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )

    # Company-private notes about this student's internship engagement.
    # Distinct from `status` (redemption tracking, 'issued'/'redeemed') —
    # companies never write to `status` directly.
    company_notes = Column(Text, default="")

    # Company-facing engagement status for this student's internship
    # placement. Distinct from `status` (voucher redemption tracking).
    # 'active' | 'completed' | 'closed'
    engagement_status = Column(String(20), default="active", nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    internship = relationship("Internship", back_populates="vouchers")
    buyer = relationship("User", foreign_keys=[buyer_user_id])
    redeemed_course = relationship("Course", foreign_keys=[redeemed_on_course_id])

    __table_args__ = (
        Index("ix_vouchers_buyer_status", "buyer_user_id", "status"),
    )

    def __repr__(self):
        return f"<InternshipVoucher(code={self.code}, status={self.status})>"


class InternshipAttendance(Base):
    """
    Admin-marked per-student attendance for an internship. Unique per
    (internship, user, date) — one record per day per student per internship.
    """
    __tablename__ = "internship_attendance"

    id = Column(Integer, primary_key=True, index=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    attended_at = Column(Date, nullable=False)
    status = Column(String(20), default="present", nullable=False)  # present|absent|late|excused
    notes = Column(Text, default="")

    # Hours worked on this day. Default 8 for present/late, 0 for absent/excused.
    hours_worked = Column(Decimal(4, 2), nullable=False, default=0)

    marked_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    internship = relationship("Internship", foreign_keys=[internship_id])
    user = relationship("User", foreign_keys=[user_id])
    marker = relationship("User", foreign_keys=[marked_by])

    __table_args__ = (
        UniqueConstraint(
            "internship_id", "user_id", "attended_at",
            name="uq_internship_attendance_internship_user_date",
        ),
        Index("ix_internship_attendance_internship_date", "internship_id", "attended_at"),
    )

    def __repr__(self):
        return f"<InternshipAttendance(internship_id={self.internship_id}, user_id={self.user_id}, date={self.attended_at}, status={self.status})>"
