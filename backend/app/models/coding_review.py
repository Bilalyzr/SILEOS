"""Phase 5 (part A): line-anchored review comments and the instructor review queue.

Submissions are immutable (source is fixed at submit time), so a comment's
line number stays valid for the life of the row. No stale-anchor handling is
needed.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class CodingReviewComment(Base):
    __tablename__ = "coding_review_comments"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(
        Integer, ForeignKey("coding_submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    line = Column(Integer, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(12), nullable=False, default="open")  # open | resolved
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_coding_review_comments_submission_line", "submission_id", "line"),)

    def __repr__(self):
        return f"<CodingReviewComment(id={self.id}, submission_id={self.submission_id}, line={self.line})>"


class CodingReviewRequest(Base):
    """A learner asks for a review of one final submission. One request per submission."""

    __tablename__ = "coding_review_requests"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(
        Integer,
        ForeignKey("coding_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed = Column(Boolean, nullable=False, default=False, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<CodingReviewRequest(submission_id={self.submission_id}, reviewed={self.reviewed})>"
