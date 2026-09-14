"""Internship Request model - companies request new internships, admins approve/reject."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class InternshipRequest(Base):
    """A company's request for a new internship posting.

    Companies can request new internships to be created. Admins review and
    either approve (which creates the actual Internship row) or reject.
    """
    __tablename__ = "internship_requests"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    intern_count = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=False, default="")
    status = Column(String(20), nullable=False, default="pending")  # pending|approved|rejected|withdrawn
    rejection_reason = Column(Text, nullable=False, default="")
    approved_internship_id = Column(Integer, ForeignKey("internships.id"), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="internship_requests")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    approved_internship = relationship("Internship", foreign_keys=[approved_internship_id])
