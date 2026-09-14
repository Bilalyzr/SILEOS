"""Learning-signals engine (2026-09-06): the raw behaviour a learner leaves
behind while learning, and the two things derived from it that must persist.

  LearningSignal      — append-only: rewinds, replays, skips, pauses, early
                        quits, notes, hesitation and answer changes on questions.
                        Position-stamped so they cluster by 10-second segment.
  LessonConceptMarker — instructor-placed "from 3:20 this is about X" markers
                        that turn segments into concepts.
  AdaptiveSession     — a personalised practice set built from the learner's
                        struggle profile + mastery; graded server-side; feeds
                        the mastery graph as evidence. Never enters the gradebook.
Struggle profiles and heat-maps are DERIVED at read time.
"""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class LearningSignal(Base):
    __tablename__ = "learning_signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True, index=True)
    quiz_id = Column(Integer, nullable=True, index=True)
    question_id = Column(Integer, nullable=True, index=True)
    kind = Column(String(32), nullable=False, index=True)
    position_s = Column(Integer, nullable=True)      # media time where it happened
    segment = Column(Integer, nullable=True)         # position_s // 10
    value = Column(Float, nullable=True)             # seconds jumped / hesitated, change count, pct watched…
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LessonConceptMarker(Base):
    __tablename__ = "lesson_concept_markers"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)
    time_s = Column(Integer, nullable=False)
    concept = Column(String(80), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AdaptiveSession(Base):
    __tablename__ = "adaptive_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    question_ids = Column(JSON, nullable=False, default=list)
    plan = Column(JSON, nullable=True)               # {concepts: [...], why: [...], difficulty: ...}
    answers = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)            # per question {correct, concept}
    score = Column(Integer, nullable=True)
    max_score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
