"""Personal goals, scheduled work, and evidence-backed interventions."""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class LearningGoal(Base):
    __tablename__ = "learning_goals"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_learning_goal_user_course"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    target_date = Column(Date, nullable=False)
    daily_minutes = Column(Integer, nullable=False, default=30)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LearningIntervention(Base):
    __tablename__ = "learning_interventions"
    __table_args__ = (UniqueConstraint("goal_id", "concept", name="uq_intervention_goal_concept"),)
    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey("learning_goals.id"), nullable=False, index=True)
    concept = Column(String(80), nullable=False)
    status = Column(String(24), nullable=False, default="suggested")
    reason = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    baseline_score = Column(Float, nullable=True)
    latest_score = Column(Float, nullable=True)
    followup_score = Column(Float, nullable=True)
    instructor_note = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LearningPlanTask(Base):
    __tablename__ = "learning_plan_tasks"
    __table_args__ = (UniqueConstraint("goal_id", "task_key", name="uq_plan_task_goal_key"),)
    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey("learning_goals.id"), nullable=False, index=True)
    task_key = Column(String(120), nullable=False)
    kind = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    concept = Column(String(80), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    intervention_id = Column(Integer, ForeignKey("learning_interventions.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("adaptive_sessions.id"), nullable=True, unique=True)
    minutes = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    not_before = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    outcome = Column(JSON, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
