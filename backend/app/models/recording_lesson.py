"""Private, durable recording workbench; publication uses the normal Lesson gate."""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class RecordingLesson(Base):
    __tablename__ = "recording_lessons"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("live_classes.id"), nullable=False, unique=True)
    source_path = Column(Text, nullable=False, default="")
    status = Column(String(24), nullable=False, default="queued", index=True)
    language = Column(String(12), nullable=False, default="auto")
    version = Column(Integer, nullable=False, default=1)
    attempts = Column(Integer, nullable=False, default=0)
    error = Column(String(500), nullable=True)
    title = Column(String(200), nullable=False, default="")
    notes = Column(Text, nullable=False, default="")
    segments = Column(JSON, nullable=False, default=list)
    chapters = Column(JSON, nullable=False, default=list)
    concepts = Column(JSON, nullable=False, default=list)
    question_ids = Column(JSON, nullable=False, default=list)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True, unique=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
