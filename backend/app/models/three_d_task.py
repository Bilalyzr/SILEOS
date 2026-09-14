"""3D match-and-verify assessment (v2.0 §6, WP2 2026-09-05).

ThreeDTask — one authored task on a 3D model: task_type ∈ match | identify |
verify | assemble | measure | manipulate | sequence, with a PARAMETER-BASED
config (anchors as normalised bounding-box coordinates, parameter ranges,
slot mappings, step orders — never gestures) validated by
app/schemas/three_d_task_config.py. `concepts` is a free-text list the task
declares for the mastery graph (WP3). `tier_floor` defaults to T4 because
every type has a T4 interface (static render + selection / numeric entry)
earning identical marks.

ThreeDTaskAttempt — server-graded attempt (§6.2: state and parameters) plus
the evidence trail (§6.3: rotations, resets, parameter explorations,
hesitations, wrong selections) and the confidence signal derived from it
("clean" vs "trial and error") that instructors see beside the score.
"""
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class ThreeDTask(Base):
    __tablename__ = "three_d_tasks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("three_d_models.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    task_type = Column(String(16), nullable=False)
    config = Column(JSON, nullable=False)
    concepts = Column(JSON, nullable=False, default=list)
    tier_floor = Column(String(2), nullable=False, default="T4")
    status = Column(String(16), nullable=False, default="draft")   # draft | published
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ThreeDTaskAttempt(Base):
    __tablename__ = "three_d_task_attempts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("three_d_tasks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    mode = Column(String(2), nullable=False, default="T1")        # tier the learner used
    answers = Column(JSON, nullable=False, default=dict)
    evidence = Column(JSON, nullable=False, default=list)
    confidence = Column(String(16), nullable=False, default="unknown")  # clean | mixed | trial_and_error | unknown
    confidence_detail = Column(JSON, nullable=False, default=dict)
    duration_s = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
