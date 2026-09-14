"""Operational health and private course transfer staging."""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeats"
    name = Column(String(64), primary_key=True)
    status = Column(String(24), nullable=False)
    detail = Column(JSON, nullable=False, default=dict)
    seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CourseTransfer(Base):
    __tablename__ = "course_transfers"
    id = Column(String(36), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(20), nullable=False)
    filename = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=False)
    manifest = Column(JSON, nullable=False)
    warnings = Column(JSON, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="preview")
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    staging_cleaned_at = Column(DateTime(timezone=True), nullable=True)
