"""Formal campus examinations: schedule, hall tickets, marks and publication.

Results are derived from papers and marks at read time. Nothing stores totals.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from app.core.database import Base


EXAM_KINDS = ("unit", "midterm", "final", "practical", "other")
EXAM_STATUSES = ("draft", "scheduled", "published")


class CampusExam(Base):
    __tablename__ = "campus_exams"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    term_id = Column(Integer, ForeignKey("campus_terms.id"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    kind = Column(String(20), nullable=False, default="other")
    status = Column(String(20), nullable=False, default="draft")
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint("institution_id", "term_id", "name", name="uq_campus_exam"),
    )


class CampusExamPaper(Base):
    __tablename__ = "campus_exam_papers"
    id = Column(Integer, primary_key=True)
    exam_id = Column(
        Integer, ForeignKey("campus_exams.id"), nullable=False, index=True
    )
    batch_id = Column(
        Integer, ForeignKey("institution_batches.id"), nullable=False, index=True
    )
    subject = Column(String(120), nullable=False)
    max_marks = Column(Float, nullable=False)
    pass_marks = Column(Float, nullable=False, default=0.0)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    room = Column(String(80), nullable=False, default="")
    event_id = Column(Integer, ForeignKey("campus_events.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("exam_id", "batch_id", "subject", name="uq_campus_exam_paper"),
    )


class CampusExamMark(Base):
    __tablename__ = "campus_exam_marks"
    id = Column(Integer, primary_key=True)
    paper_id = Column(
        Integer, ForeignKey("campus_exam_papers.id"), nullable=False, index=True
    )
    member_id = Column(
        Integer, ForeignKey("institution_members.id"), nullable=False, index=True
    )
    marks = Column(Float, nullable=True)
    absent = Column(Boolean, nullable=False, default=False)
    remarks = Column(String(500), nullable=False, default="")
    graded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (
        UniqueConstraint("paper_id", "member_id", name="uq_campus_exam_mark"),
    )


class CampusHallTicket(Base):
    __tablename__ = "campus_hall_tickets"
    id = Column(Integer, primary_key=True)
    exam_id = Column(
        Integer, ForeignKey("campus_exams.id"), nullable=False, index=True
    )
    member_id = Column(
        Integer, ForeignKey("institution_members.id"), nullable=False, index=True
    )
    roll_number = Column(String(40), nullable=False)
    token = Column(String(32), nullable=False, unique=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    issued_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("exam_id", "member_id", name="uq_campus_hall_ticket"),
    )
