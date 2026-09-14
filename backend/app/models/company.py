"""
Company + CompanyInterest models — SS3.

Owned by the SS3 implementer.

Tables:
  - companies: one row per company account. Linked 1:1 to a User with role='company'.
  - company_interests: a company expressing interest in a specific candidate user.
    Unique per (company_id, candidate_user_id) — enforced at DB level.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Company(Base):
    """
    Company profile. One User(role='company') owns one Company.

    approval_source:
        - 'self_serve'   — company filled signup form, awaiting admin approval.
        - 'admin_invite' — admin created + pre-approved, company completes setup via email link.

    is_approved gates all browse / interest endpoints in companies.py.
    """
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True
    )

    name = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, index=True, nullable=False)
    website = Column(String(255), default="")
    industry = Column(String(100), default="")
    team_size = Column(String(50), default="")  # e.g. '1-10', '11-50', '51-200', '200+'
    description = Column(Text, default="")
    logo_url = Column(String(500), default="")

    contact_email = Column(String(150), nullable=False, index=True)
    contact_phone = Column(String(30), default="")

    # Billing columns (company invoicing)
    gstin = Column(String(20), default="")  # Goods and Services Tax Identification Number
    legal_name = Column(String(255), default="")  # Legal entity name for invoices
    billing_address = Column(Text, default="")  # Full billing address
    state_code = Column(String(2), default="")  # 2-digit numeric GST state code (e.g. '29', '33', '07')

    is_approved = Column(Boolean, default=False, nullable=False, index=True)
    approval_source = Column(String(20), default="self_serve", nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    interests = relationship(
        "CompanyInterest", back_populates="company", cascade="all, delete-orphan"
    )
    internship_requests = relationship(
        "InternshipRequest", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Company(id={self.id}, name={self.name!r}, approved={self.is_approved})>"


class CompanyInterest(Base):
    """
    A company's expressed interest in a specific candidate user.

    status transitions:
        interested -> accepted | declined | withdrawn
        (accepted/declined written by candidate; withdrawn written by company)

    On `accepted`, the router surfaces candidate email + phone to the company.
    """
    __tablename__ = "company_interests"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    candidate_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    status = Column(String(20), default="interested", nullable=False, index=True)
    company_message = Column(Text, default="")

    responded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "candidate_user_id", name="uq_company_candidate_interest"
        ),
        Index("ix_company_interests_candidate_status", "candidate_user_id", "status"),
    )

    # Relationships
    company = relationship("Company", back_populates="interests")
    candidate = relationship("User", foreign_keys=[candidate_user_id])

    def __repr__(self):
        return (
            f"<CompanyInterest(id={self.id}, company_id={self.company_id}, "
            f"candidate_user_id={self.candidate_user_id}, status={self.status})>"
        )
