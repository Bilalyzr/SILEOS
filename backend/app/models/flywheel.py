"""Flywheel extras (v2.0 §10 — WP8): peer "teach it back" v1.

A learner explains a concept in their own words; peers mark it helpful or
not. Explanations are learner-scoped evidence of understanding (a small
mastery signal) and a social reinforcement loop — never graded truth.
Everything else in WP8 (next-class agenda, insight cards, DigiLocker
adapter) is derived or stateless and needs no table.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class TeachBack(Base):
    __tablename__ = "teach_backs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    concept = Column(String(80), nullable=False, index=True)
    text = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="visible")   # visible | hidden (instructor moderation)
    helpful_count = Column(Integer, nullable=False, default=0)
    not_helpful_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TeachBackRating(Base):
    __tablename__ = "teach_back_ratings"
    __table_args__ = (UniqueConstraint("teach_back_id", "rater_id", name="uq_teach_back_rating"),)

    id = Column(Integer, primary_key=True, index=True)
    teach_back_id = Column(Integer, ForeignKey("teach_backs.id", ondelete="CASCADE"), nullable=False, index=True)
    rater_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    helpful = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
