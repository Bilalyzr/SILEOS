from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class LabNotebook(Base):
    __tablename__ = 'lab_notebooks'
    __table_args__ = (UniqueConstraint('user_id', 'lab_slug', name='uq_lab_notebook_user_slug'),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    lab_slug = Column(String(50), nullable=False)
    prediction = Column(Text, nullable=False, default='')
    observation = Column(Text, nullable=False, default='')
    conclusion = Column(Text, nullable=False, default='')
    trials = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
