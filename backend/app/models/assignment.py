"""
Assignment models for course assignments
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.types import Numeric as Decimal
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# Status enums for validation
class AssignmentStatus(str, enum.Enum):
    """Valid assignment statuses"""
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class LatePolicy(str, enum.Enum):
    """How submit_assignment treats a submission made after due_date."""
    ALLOW = "allow"        # accept, flag is_late=True, no grade impact
    BLOCK = "block"        # reject with 403 once due_date has passed
    PENALTY = "penalty"    # accept, flag is_late=True, grading applies late_penalty_pct


class SubmissionStatus(str, enum.Enum):
    """Valid submission statuses"""
    SUBMITTED = "submitted"
    GRADED = "graded"
    RETURNED = "returned"


class Assignment(Base):
    """
    Assignment model - Similar to Quiz structure
    """
    __tablename__ = "assignments"

    # Core fields
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    instructions = Column(Text, default="")

    # Assignment settings
    due_date = Column(DateTime(timezone=True), nullable=True)
    total_points = Column(Integer, default=100)
    allowed_file_types = Column(JSON, default=[])  # List of allowed file extensions
    max_file_size = Column(Integer, default=10)  # in MB
    max_files = Column(Integer, default=5)
    submission_type = Column(String(50), default="both")  # text, file, both
    attachments = Column(JSON, default=[])  # Instructor reference files

    # Late-submission handling (spec A1.5). late_policy is stored as a plain
    # String(10) rather than SQLEnum(LatePolicy) so existing rows / raw-dict
    # payloads default cleanly to "allow" without an enum migration dance;
    # routers validate against LatePolicy's values.
    late_policy = Column(String(10), default="allow", nullable=False)
    late_penalty_pct = Column(Integer, default=0, nullable=False)

    # Lightweight rubric (spec A1.12): list of {criterion, max_points}.
    # Grading math (summing rubric_scores) is Task 2 — only the field lands
    # here.
    rubric = Column(JSON, default=[])

    # Display settings
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.PUBLISHED, nullable=False)
    order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="assignments")
    creator = relationship("User", foreign_keys=[created_by])
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Assignment(id={self.id}, title={self.title})>"


class AssignmentSubmission(Base):
    """
    Student submissions for assignments
    """
    __tablename__ = "assignment_submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Submission content
    text_content = Column(Text, default="")
    files = Column(JSON, default=[])  # List of uploaded file URLs

    # True when submitted_at is after the assignment's due_date at the time
    # of submission. Set once at submit time and never recomputed later.
    is_late = Column(Boolean, default=False, nullable=False)

    # Grading
    grade = Column(Decimal(9, 2), nullable=True)
    feedback = Column(Text, default="")
    status = Column(SQLEnum(SubmissionStatus), default=SubmissionStatus.SUBMITTED, nullable=False)

    # Per-criterion scores when the assignment carries a rubric:
    # [{criterion, points_awarded}, ...]. Optional; grade remains the
    # overridable source of truth (spec A1.12). Summing math is Task 2.
    rubric_scores = Column(JSON, nullable=True)

    # Who approved/graded this submission. Instructors are the primary graders;
    # an admin may step in as a fallback when the instructor hasn't acted. These
    # give the approvals flow an audit trail of who signed off.
    graded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    graded_by_role = Column(String(20), nullable=True)  # "instructor" | "admin"

    # Timestamps
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    graded_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("assignment_id", "user_id", name="uq_assignment_user"),
    )

    def __repr__(self):
        return f"<AssignmentSubmission(id={self.id}, user_id={self.user_id}, status={self.status})>"
