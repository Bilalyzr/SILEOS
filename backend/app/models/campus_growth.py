"""Public institution acquisition records.

Leads deliberately live outside a tenant because they are created before a
school or college workspace exists. Access to them is restricted to platform
administrators by the router.
"""

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class CampusLead(Base):
    __tablename__ = "campus_leads"

    id = Column(Integer, primary_key=True)
    dedupe_key = Column(String(64), nullable=False)
    contact_name = Column(String(120), nullable=False)
    work_email = Column(String(254), nullable=False, index=True)
    phone = Column(String(20), nullable=False, default="")
    institution_name = Column(String(180), nullable=False)
    institution_kind = Column(String(20), nullable=False)
    learner_count = Column(String(24), nullable=False)
    interest = Column(String(30), nullable=False, default="demo")
    message = Column(Text, nullable=False, default="")
    source = Column(String(80), nullable=False, default="campus-page")
    attribution = Column(JSON, nullable=False, default=dict)
    status = Column(String(24), nullable=False, default="new", index=True)
    consent_at = Column(DateTime(timezone=True), nullable=False)
    assigned_to = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_campus_lead_dedupe"),)

