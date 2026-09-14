"""AI layer completion (v2.0 §9 — WP7): the two things the engines need to
persist that are NOT AiJob audit rows.

* TutorEscalation — Engine C hands a learner to the instructor WITH context
  (question, recent turns, weak concepts). Instructor replies in-app.
* ContentErrorReport — learner-reported errors on a quiz question / lesson /
  bank question → instructor inbox (§9.4 safeguard 3). Resolution is a human
  act; nothing auto-edits content.

Auto-flagging by item statistics (§9.4 safeguard 2) is DERIVED at read time
in `ai_layer_service.flagged_items()` — never stored.
"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class TutorEscalation(Base):
    __tablename__ = "tutor_escalations"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    context = Column(JSON, nullable=False, default=dict)     # {history: [...], lesson_id, weak_concepts: [...]}
    status = Column(String(16), nullable=False, default="open", index=True)   # open | answered
    instructor_reply = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    answered_at = Column(DateTime(timezone=True), nullable=True)


class ContentErrorReport(Base):
    __tablename__ = "content_error_reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(20), nullable=False)                 # quiz_question | lesson | bank_question | other
    ref_id = Column(Integer, nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="open", index=True)   # open | resolved | dismissed
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
