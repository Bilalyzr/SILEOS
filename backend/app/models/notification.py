from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)          # submission_received | cert_issued | submission_returned
    title = Column(String(255), nullable=False)
    message = Column(Text, default="")
    link = Column(String(255), nullable=True)          # frontend path, e.g. /admin/approvals
    related_id = Column(Integer, nullable=True)         # e.g. submission id
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_notifications_user_unread", "user_id", "is_read"),)

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type})>"
