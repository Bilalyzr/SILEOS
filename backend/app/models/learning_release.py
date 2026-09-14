"""Versioned, idempotent lab evidence and offline synchronization receipts."""
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class LabInvestigationAttempt(Base):
    __tablename__='lab_investigation_attempts'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    lab_slug=Column(String(50),nullable=False,index=True)
    submission_id=Column(String(36),nullable=False)
    revision=Column(String(64),nullable=False)
    evidence=Column(JSON,nullable=False)
    feedback=Column(JSON,nullable=False)
    score=Column(Integer,nullable=False)
    max_score=Column(Integer,nullable=False)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(UniqueConstraint('user_id','submission_id',name='uq_lab_submission'),)


class OfflineSyncReceipt(Base):
    __tablename__='offline_sync_receipts'
    id=Column(Integer,primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    event_id=Column(String(36),nullable=False)
    lesson_id=Column(Integer,ForeignKey('lessons.id'),nullable=False)
    created_at=Column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(UniqueConstraint('user_id','event_id',name='uq_offline_event'),)
