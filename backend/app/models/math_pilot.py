"""Course-scoped, versioned mathematics pilot; no public learner records."""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, UniqueConstraint
from app.core.database import Base


class MathPilotPolicy(Base):
    __tablename__ = 'math_pilot_policies'
    course_id = Column(Integer, ForeignKey('courses.id'), primary_key=True)
    version = Column(String(64), nullable=False)
    reviewed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    review_note = Column(String(2000), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=False)


class MathPilotSession(Base):
    __tablename__ = 'math_pilot_sessions'
    __table_args__ = (UniqueConstraint('user_id', 'course_id', 'version', name='uq_math_pilot_learner'),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    version = Column(String(64), nullable=False)
    stage = Column(String(24), nullable=False)
    sequence = Column(Integer, nullable=False, default=0)
    hypothesis = Column(String(40), nullable=True)
    intervention = Column(String(40), nullable=True)
    transfer_score = Column(Integer, nullable=True)
    retention_score = Column(Integer, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MathPilotEvent(Base):
    __tablename__ = 'math_pilot_events'
    __table_args__ = (UniqueConstraint('session_id', 'sequence', name='uq_math_pilot_sequence'),
                     UniqueConstraint('session_id', 'key', name='uq_math_pilot_request'))
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('math_pilot_sessions.id'), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    key = Column(String(36), nullable=False)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(24), nullable=False)
    payload = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
