"""Live-class permanent records (v2.0 §7.3 / §7.4 — WP5).

ClassReport — generated automatically when a class ENDS and kept forever:
"media expires, knowledge does not". Attendance with join/leave/duration,
the event/question log, poll results, engagement, the instructor's notes,
transcript + AI key topics when they exist (Engine A), and whether the
recording still exists. Survives recording deletion and class cancellation.

RecordingAudit — every retention action on a recording (soft delete,
restore, extend, hard delete by the sweeper, expiry warnings) with actor,
reason and timestamp (§7.4 "every deletion is audit-logged").
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class ClassReport(Base):
    __tablename__ = "class_reports"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("live_classes.id"), nullable=False, unique=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    purpose = Column(String(24), nullable=True)
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_s = Column(Integer, nullable=False, default=0)
    attendance = Column(JSON, nullable=False, default=list)      # [{user_id, name, joined_at, left_at, duration_s, present}]
    event_log = Column(JSON, nullable=False, default=list)       # [{t, user_id, event, payload}]
    poll_results = Column(JSON, nullable=False, default=list)    # [{question, options, tallies, total}]
    engagement = Column(JSON, nullable=False, default=dict)      # {enrolled, joined, present, avg_duration_s, poll_votes, present_pct}
    instructor_notes = Column(Text, nullable=False, default="")
    transcript = Column(Text, nullable=True)                     # Engine A (WP7) fills these
    ai_topics = Column(JSON, nullable=True)
    processing_status = Column(String(16), nullable=False, default="pending")   # pending | processed
    shared_with_guardians = Column(Boolean, nullable=False, default=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RecordingAudit(Base):
    __tablename__ = "recording_audit"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("live_classes.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)      # null = sweeper
    action = Column(String(24), nullable=False)   # soft_delete | restore | extend | hard_delete | expiry_warning
    reason = Column(String(300), nullable=True)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
