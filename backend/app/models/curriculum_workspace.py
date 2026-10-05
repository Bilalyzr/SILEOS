"""Curriculum references and explicit mappings to existing LMS courses."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class CurriculumChapter(Base):
    __tablename__ = 'curriculum_workspace_chapters'
    id = Column(Integer, primary_key=True)
    grade = Column(Integer, nullable=False)
    subject = Column(String(80), nullable=False)
    title = Column(String(200), nullable=False)
    edition = Column(String(40), nullable=False)
    source_url = Column(String(500), nullable=False)
    review_note = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint('grade', 'subject', 'title', 'edition', name='uq_curriculum_workspace_chapter'),)


class CurriculumCourseLink(Base):
    __tablename__ = 'curriculum_workspace_links'
    id = Column(Integer, primary_key=True)
    chapter_key = Column(String(180), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    reviewed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    review_note = Column(Text, nullable=False)
    revision = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint('chapter_key', 'course_id', name='uq_curriculum_workspace_link'),)
