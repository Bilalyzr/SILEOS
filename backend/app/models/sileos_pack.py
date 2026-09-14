"""SILEOS feature pack models (docs/SILEOS_FEATURES.md, 2026-09-04).

Backend-only integration of selected SILEOS blueprint capabilities into the
existing Sasha LMS data model. No existing UI consumes these yet — every
surface here is API-first (the instructor/admin UI can be wired later
without schema changes).

- `QuestionBank` / `BankQuestion` — reusable, tagged, difficulty-rated
  question pools (blueprint §3.4 "question banks with tagging, difficulty
  calibration, item analysis"). Questions are COPIES: pulling one into a
  quiz snapshots it, so editing a bank question never rewrites live quizzes
  (the quiz-engine spec's delete+recreate lesson, inverted).
- `CoursePrerequisite` — course A requires course B at ≥N% progress
  (blueprint §3.2 prerequisites / adaptive release; learner-facing gating
  exposed via /unlock-status — not enforced on existing enroll flows yet).
- `LearningPath` — an ordered list of courses (blueprint §3.2 learning
  paths, lite): `course_ids` is a JSON array kept in list order, so reorder
  is one UPDATE and paths of tens of courses don't need a join table.
- `XapiStatement` — the event spine (blueprint §3.5, xAPI-lite): every
  meaningful learner action lands here as actor-verb-object. Postgres-only
  by design — the blueprint's ClickHouse mirror is deliberately NOT built
  until statement volume demands it.
- `AiJob` — audit trail for AI generation calls (blueprint §15 guardrails:
  model + input + output logged; output is always a DRAFT a human approves
  before use — never auto-applied to live content).
- `StudentRiskFlag` — materialized at-risk snapshot per (course, student),
  persisted so dashboards can sort/filter and flag history stays auditable.
"""
from sqlalchemy import (JSON, Column, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

QUESTION_DIFFICULTIES = ("easy", "medium", "hard")
QUESTION_BANK_TYPES = (
    "multiple_choice", "true_false", "fill_in_blanks", "short_answer",
)


class QuestionBank(Base):
    """A reusable question pool owned by one instructor."""
    __tablename__ = "question_banks"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    questions = relationship(
        "BankQuestion", back_populates="bank",
        cascade="all, delete-orphan", lazy="selectin",
    )


class BankQuestion(Base):
    """One bank question. `options`/`correct_answer` are JSON so every
    question type fits one row shape (same convention as QuizQuestion
    question_settings). `source_quiz_question_id` records the origin when
    imported from a live quiz — provenance only, NOT a live FK."""
    __tablename__ = "bank_questions"

    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("question_banks.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    question_title = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)
    question_mark = Column(Float, default=1.0)
    options = Column(JSON, default=list)          # list[str] for choice types
    correct_answer = Column(JSON, default=None)   # index / "true"/"false" / text
    answer_explanation = Column(Text, default="")
    difficulty = Column(String(16), default="medium")  # easy | medium | hard
    tags = Column(JSON, default=list)             # list[str], blueprint §3.4 tagging
    source_quiz_question_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bank = relationship("QuestionBank", back_populates="questions")


class CoursePrerequisite(Base):
    """Course A (`course_id`) requires course B (`requires_course_id`) at
    `min_progress_percentage`. UNIQUE pair — one rule per required course."""
    __tablename__ = "course_prerequisites"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    requires_course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    min_progress_percentage = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("course_id", "requires_course_id",
                         name="uq_course_prereq_pair"),
    )


class LearningPath(Base):
    """An ordered sequence of courses owned by its author."""
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    course_ids = Column(JSON, default=list)  # ordered
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())


class XapiStatement(Base):
    """One learner event, actor-verb-object (xAPI-lite). `verb` uses the ADL
    verb registry short form ("completed", "attempted", "watched"...).
    `object_type` ∈ lesson | course | quiz | h5p | game; `object_ref` is the
    platform-absolute IRI built by the emitter service."""
    __tablename__ = "xapi_statements"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    verb = Column(String(64), nullable=False, index=True)
    object_type = Column(String(32), nullable=False)
    object_id = Column(String(64), nullable=False, default="")
    object_ref = Column(String(500), default="")
    result = Column(JSON, default=dict)
    context = Column(JSON, default=dict)  # course_id, ip, ua...
    stored_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_xapi_actor_time", "actor_user_id", "stored_at"),
    )


class AiJob(Base):
    """One AI generation call: input, output, status, model — the audit
    trail blueprint §15 requires. Nothing here mutates live content."""
    __tablename__ = "ai_jobs"

    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # generate_questions | ...
    status = Column(String(20), default="pending", index=True)  # pending|done|failed
    model = Column(String(100), default="")
    input_json = Column(JSON, default=dict)
    output_json = Column(JSON, default=dict)
    error = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)


class StudentRiskFlag(Base):
    """Materialized at-risk snapshot per (course, student) — recomputed by
    the at-risk endpoint; UNIQUE pair makes recompute idempotent."""
    __tablename__ = "student_risk_flags"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    risk_score = Column(Integer, default=0)  # 0-100, higher = more at risk
    severity = Column(String(16), default="low")  # low | medium | high
    reasons = Column(JSON, default=list)  # list[str] — human-readable, explainable
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_risk_course_student"),
    )
