"""Assignable work items for the role-aware campus Today view."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class CampusActionItem(Base):
    __tablename__ = "campus_action_items"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    kind = Column(String(30), nullable=False, default="task")
    title = Column(String(180), nullable=False)
    detail = Column(Text, nullable=False, default="")
    priority = Column(String(16), nullable=False, default="normal", index=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    assigned_member_id = Column(Integer, ForeignKey("institution_members.id"), index=True)
    due_at = Column(DateTime(timezone=True), index=True)
    action_url = Column(String(500), nullable=False, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    snoozed_until = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

