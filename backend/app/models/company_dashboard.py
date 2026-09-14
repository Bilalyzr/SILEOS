"""
Company-dashboard v2 models.

Owns:
  - CompanyManager — sub-users belonging to a Company. role on User is
    'company_manager'. Owner of the Company is the User row referenced by
    Company.owner_user_id (role='company') and is NOT inserted here.
  - DailyWorkLog — student's daily work-done entry for an internship.
  - InternshipAnnouncement — company-posted announcement, optionally
    internship-scoped.
  - InternshipPerformanceReview — end-of-internship review submitted by a
    company about a student.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    UniqueConstraint, Index, Date, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CompanyManager(Base):
    __tablename__ = "company_managers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     unique=True, nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", foreign_keys=[company_id])
    user = relationship("User", foreign_keys=[user_id])


class DailyWorkLog(Base):
    __tablename__ = "daily_work_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    internship_id = Column(Integer, ForeignKey("internships.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    log_date = Column(Date, nullable=False)
    content = Column(Text, nullable=False, default="")
    attachment_url = Column(String(500), nullable=False, default="")
    review_status = Column(String(20), nullable=False, default="pending")  # pending|approved|flagged
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_comment = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("student_user_id", "log_date", name="uq_work_log_student_date"),
        Index("ix_work_logs_internship_date", "internship_id", "log_date"),
    )

    student = relationship("User", foreign_keys=[student_user_id])
    internship = relationship("Internship", foreign_keys=[internship_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class InternshipAnnouncement(Base):
    __tablename__ = "internship_announcements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    internship_id = Column(Integer, ForeignKey("internships.id", ondelete="SET NULL"),
                           nullable=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", foreign_keys=[company_id])
    internship = relationship("Internship", foreign_keys=[internship_id])


class InternshipPerformanceReview(Base):
    __tablename__ = "internship_performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    internship_id = Column(Integer, ForeignKey("internships.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=False, default="")
    hire_recommendation = Column(String(10), nullable=False, default="maybe")  # yes|maybe|no
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "student_user_id", "internship_id",
                         name="uq_review_company_student_internship"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
    )

    company = relationship("Company", foreign_keys=[company_id])
    student = relationship("User", foreign_keys=[student_user_id])
    internship = relationship("Internship", foreign_keys=[internship_id])
