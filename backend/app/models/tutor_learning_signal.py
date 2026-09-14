"""Course-linked, privacy-bounded learning signals emitted by Sasha tutor.

Only a learner's question excerpt and deterministic diagnostic metadata are
stored.  General-learning conversations have no course id and are never
written here, so instructors cannot discover them through analytics.
"""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class TutorLearningSignal(Base):
    __tablename__ = "tutor_learning_signals"
    __table_args__ = (
        Index("ix_tutor_signal_course_created", "course_id", "created_at"),
        Index("ix_tutor_signal_learner_course_created", "user_id", "course_id", "created_at"),
        Index("ix_tutor_signal_course_concept", "course_id", "concept"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    session_key = Column(String(64), nullable=False, default="")
    prompt_excerpt = Column(Text, nullable=False, default="")
    concept = Column(String(80), nullable=False, default="General course support")
    struggle_score = Column(Float, nullable=False, default=0.0)
    severity = Column(String(16), nullable=False, default="developing")
    likely_gap = Column(String(32), nullable=False, default="concept_clarity")
    reasons = Column(JSON, nullable=False, default=list)
    repeat_count = Column(Integer, nullable=False, default=0)
    is_guarded = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
