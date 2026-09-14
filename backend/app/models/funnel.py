"""Conversion funnel events (roadmap R1, 2026-09-05).

One append-only row per meaningful visitor action on the way to an
enrolment: course_view, preview_open, checkout_start. Enrolments themselves
are NOT duplicated here — they are derived from the enrollments table so
the funnel can never disagree with the money. Anonymous visitors are keyed
by a browser session id; logged-in users also carry user_id.
"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class FunnelEvent(Base):
    __tablename__ = "funnel_events"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(24), nullable=False, index=True)            # course_view | preview_open | checkout_start
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    meta = Column(JSON, nullable=True)                                # {lesson_id, source, …}
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
