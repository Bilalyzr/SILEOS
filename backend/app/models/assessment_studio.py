"""Course-scoped publication and audit metadata over reusable bank questions."""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func
from app.core.database import Base


class StudioQuestion(Base):
    __tablename__ = "studio_questions"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    bank_question_id = Column(Integer, ForeignKey("bank_questions.id"), nullable=False, unique=True)
    concept = Column(String(80), nullable=False, index=True)
    purpose = Column(String(20), nullable=False, default="practice")
    status = Column(String(20), nullable=False, default="draft")
    version = Column(Integer, nullable=False, default=1)
    published_snapshot = Column(JSON, nullable=True)
    history = Column(JSON, nullable=False, default=list)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
