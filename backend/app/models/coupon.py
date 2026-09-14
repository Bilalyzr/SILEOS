"""
Coupon model for discount codes
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.types import Numeric as Decimal
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class DiscountType(enum.Enum):
    """Discount type enum"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"

class CouponApplicability(enum.Enum):
    """Coupon applicability enum"""
    ALL_COURSES = "all_courses"
    SPECIFIC_COURSES = "specific_courses"

# PostgreSQL enum types
discount_type_enum = ENUM('percentage', 'fixed', name='discount_type', create_type=True)
coupon_applicability_enum = ENUM('all_courses', 'specific_courses', name='coupon_applicability', create_type=True)

class Coupon(Base):
    """
    Coupon model for managing discount codes
    """
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, default="")

    # Discount details
    discount_type = Column(discount_type_enum, nullable=False)  # percentage or fixed
    discount_value = Column(Decimal(10, 2), nullable=False)  # percentage (0-100) or fixed amount

    # Applicability
    applicability = Column(coupon_applicability_enum, nullable=False, default='all_courses')
    # R7: a Razorpay Offer id (offer_XXXX, created in the Razorpay dashboard) makes this
    # coupon usable on MEMBERSHIP subscriptions — the gateway applies the discount.
    razorpay_offer_id = Column(String(64), nullable=True)

    # Usage limits
    usage_limit = Column(Integer, nullable=True)  # NULL means unlimited
    # NOT NULL: a bulk seed once inserted NULLs, and CouponListResponse
    # (usage_count: int) turned one NULL row into a 400 for the whole list.
    usage_count = Column(Integer, default=0, nullable=False)
    per_user_limit = Column(Integer, default=1)  # How many times one user can use it

    # Minimum purchase
    minimum_purchase_amount = Column(Decimal(10, 2), default=0)

    # Validity
    valid_from = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)  # NULL means no expiry

    # Status
    is_active = Column(Boolean, default=True)

    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Cohort association (SPOC referral tracking)
    cohort_id = Column(Integer, ForeignKey("cohorts.id"), nullable=True)

    # Relationships
    creator = relationship("User", back_populates="coupons")
    cohort = relationship("Cohort", backref="coupons")
    course_restrictions = relationship("CouponCourseRestriction", back_populates="coupon", cascade="all, delete-orphan")
    usage_records = relationship("CouponUsage", back_populates="coupon", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Coupon(code={self.code}, discount={self.discount_value}{self.discount_type.value})>"

class CouponCourseRestriction(Base):
    """
    Many-to-many relationship between coupons and courses
    Used when coupon is applicable only to specific courses
    """
    __tablename__ = "coupon_course_restrictions"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    coupon = relationship("Coupon", back_populates="course_restrictions")
    course = relationship("Course")

    def __repr__(self):
        return f"<CouponCourseRestriction(coupon_id={self.coupon_id}, course_id={self.course_id})>"

class CouponUsage(Base):
    """
    Track coupon usage by users
    """
    __tablename__ = "coupon_usage"

    id = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # NULL if not yet ordered

    discount_amount = Column(Decimal(10, 2), nullable=False)
    used_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    coupon = relationship("Coupon", back_populates="usage_records")
    user = relationship("User")
    order = relationship("Order", foreign_keys=[order_id])

    def __repr__(self):
        return f"<CouponUsage(coupon_id={self.coupon_id}, user_id={self.user_id}, discount={self.discount_amount})>"
