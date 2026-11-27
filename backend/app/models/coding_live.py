"""Phase 4: coding challenges pushed into a live class session.

A push is one row in `live_coding_challenges`. Each student submission made
through the live endpoint gets one `live_coding_submissions` link row, so the
results board can be built from the judge's own submission records without
copying any source code or verdicts.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class LiveCodingChallenge(Base):
    __tablename__ = "live_coding_challenges"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(
        Integer, ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    challenge_id = Column(
        Integer, ForeignKey("coding_challenges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pushed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(12), nullable=False, default="open", index=True)  # open | closed
    graded = Column(Boolean, nullable=False, default=False)
    instructions = Column(Text, nullable=False, default="")
    # Shown to learners only after `solution_revealed_at` is set.
    model_solution = Column(Text, nullable=False, default="")
    solution_revealed_at = Column(DateTime(timezone=True), nullable=True)
    pushed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_live_coding_challenges_class_status", "class_id", "status"),)

    def __repr__(self):
        return f"<LiveCodingChallenge(id={self.id}, class_id={self.class_id}, status={self.status})>"


class LiveCodingSubmission(Base):
    __tablename__ = "live_coding_submissions"

    id = Column(Integer, primary_key=True, index=True)
    live_id = Column(
        Integer, ForeignKey("live_coding_challenges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submission_id = Column(
        Integer, ForeignKey("coding_submissions.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    counts_for_grade = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_live_coding_submissions_submission"),
    )

    def __repr__(self):
        return f"<LiveCodingSubmission(live_id={self.live_id}, submission_id={self.submission_id})>"
