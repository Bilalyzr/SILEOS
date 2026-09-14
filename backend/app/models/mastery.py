"""Learner mastery graph (v2.0 §8.3, §9.5, §10.1 — WP3 2026-09-05).

LEARNER-SCOPED, never course-scoped: what a student proves in an MP 3D task
informs the SP tutor and the UP exam generator (§10.1, the moat). Every
scorable thing DECLARES concepts through `concept_links`; every graded event
writes `mastery_evidence` rows (one per concept) with a source weight
(supervised quiz > assignment > clean 3D path > lab > H5P > game > fumbling
path); `learner_mastery` holds the derived estimate + confidence per
(learner, concept). `concept_prerequisites` is instructor-declared;
`course_outcomes` carries the UP "Outcome definition" (§4.3) whose target
concepts drive the coverage-gap report.

Concepts are free text, normalised (lowercase, single spaces, ≤80 chars) —
no taxonomy, matching §3.
"""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class ConceptLink(Base):
    __tablename__ = "concept_links"
    __table_args__ = (UniqueConstraint("kind", "ref_id", "concept", name="uq_concept_link"),)

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(24), nullable=False, index=True)      # quiz | question | game | h5p | lab | three_d_task | lesson | assignment | course
    ref_id = Column(String(64), nullable=False, index=True)
    concept = Column(String(80), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"
    __table_args__ = (UniqueConstraint("concept", "requires", name="uq_concept_prereq"),)

    id = Column(Integer, primary_key=True, index=True)
    concept = Column(String(80), nullable=False, index=True)
    requires = Column(String(80), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MasteryEvidence(Base):
    __tablename__ = "mastery_evidence"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    concept = Column(String(80), nullable=False, index=True)
    source_kind = Column(String(24), nullable=False)
    source_ref = Column(String(64), nullable=False)
    score_pct = Column(Float, nullable=False)              # 0..100
    weight = Column(Float, nullable=False, default=1.0)    # evidence weight by source (§9.5)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    detail = Column(JSON, nullable=True)                   # e.g. {"confidence": "clean"}
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LearnerMastery(Base):
    __tablename__ = "learner_mastery"
    __table_args__ = (UniqueConstraint("user_id", "concept", name="uq_learner_concept"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    concept = Column(String(80), nullable=False, index=True)
    estimate = Column(Float, nullable=False, default=0.0)      # 0..100
    confidence = Column(Float, nullable=False, default=0.0)    # 0..1
    evidence_count = Column(Integer, nullable=False, default=0)
    last_evidence_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CourseOutcome(Base):
    __tablename__ = "course_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, unique=True, index=True)
    outcome_text = Column(Text, nullable=False, default="")
    target_concepts = Column(JSON, nullable=False, default=list)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
