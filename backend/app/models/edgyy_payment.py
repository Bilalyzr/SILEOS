"""
Edgyy Payment Proxy Model - Tracks payments from edgyy.in platform
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.types import Numeric as Decimal, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class EdgyyPaymentStatus(enum.Enum):
    """Edgyy payment proxy status enumeration"""
    CREATED = "created"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class EdgyyPayment(Base):
    """
    Edgyy Payment Proxy - Tracks payments initiated from edgyy.in
    Maps edgyy_registration_id to Razorpay order/payment details
    """
    __tablename__ = "edgyy_payments"

    id = Column(Integer, primary_key=True, index=True)

    # Edgyy identifiers
    edgyy_registration_id = Column(String(255), unique=True, nullable=False, index=True)

    # Razorpay details
    razorpay_order_id = Column(String(255), unique=True, nullable=False, index=True)
    razorpay_payment_id = Column(String(255), default="")

    # Payment details
    amount = Column(Decimal(13, 4), nullable=False)
    currency = Column(String(3), default="INR")
    status = Column(Enum(EdgyyPaymentStatus), default=EdgyyPaymentStatus.CREATED)

    # Gateway response
    gateway_response = Column(JSON, default={})
    failure_reason = Column(Text, default="")

    # Webhook tracking
    webhook_delivered = Column(Boolean, default=False)
    webhook_delivered_at = Column(DateTime(timezone=True), nullable=True)
    webhook_retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<EdgyyPayment(id={self.id}, reg_id={self.edgyy_registration_id}, status={self.status}, amount={self.amount})>"


class EdgyyPaymentSessionStatus(enum.Enum):
    """Edgyy payment session status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"


class EdgyyPaymentSession(Base):
    """
    Edgyy Payment Session - Hosted payment page sessions
    Stores session data for redirect-based payment flow
    """
    __tablename__ = "edgyy_payment_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Session identifier
    session_id = Column(String(64), unique=True, nullable=False, index=True)

    # Edgyy identifiers
    edgyy_registration_id = Column(String(255), nullable=False, index=True)
    edgyy_user_email = Column(String(255), default="")
    edgyy_user_name = Column(String(255), default="")

    # Return URL for callback
    return_url = Column(String(1024), nullable=False)

    # Razorpay details
    razorpay_order_id = Column(String(255), unique=True, nullable=False, index=True)
    razorpay_payment_id = Column(String(255), default="")

    # Payment details
    amount = Column(Decimal(13, 4), nullable=False)
    currency = Column(String(3), default="INR")
    status = Column(Enum(EdgyyPaymentSessionStatus), default=EdgyyPaymentSessionStatus.PENDING)

    # Gateway response
    gateway_response = Column(JSON, default={})
    failure_reason = Column(Text, default="")

    # Webhook tracking
    webhook_delivered = Column(Boolean, default=False)
    webhook_delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<EdgyyPaymentSession(id={self.id}, session_id={self.session_id}, status={self.status})>"
