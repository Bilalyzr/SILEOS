"""Course studio settings (v2.0 §4 — WP6): the per-course knobs the type
studios expose — Parent View Configurator (§4.2), Reward System Designer
(§4.2 / §10), and the opening-face dismissal. Stored as JSON so a new type
profile stays data, not code (§2.3). Defaults come from the course type via
app/services/studio_service.defaults_for_type().
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func

from app.core.database import Base


class CourseStudioSettings(Base):
    __tablename__ = "course_studio_settings"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, unique=True, index=True)
    parent_view = Column(JSON, nullable=False, default=dict)    # {attendance, completion, scores, time_spent, teacher_notes, class_reports}
    rewards = Column(JSON, nullable=False, default=dict)        # {points: {event_type: pts}, badges: [...], streak_freeze_days_per_month, leaderboard_opt_out}
    face_dismissed = Column(Boolean, nullable=False, default=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
