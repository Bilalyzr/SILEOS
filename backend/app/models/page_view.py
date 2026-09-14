"""
PageView model - tracks frontend page/route views for analytics.
Written by the /api/v1/analytics/track endpoint (frontend beacon) and
queried by the various analytics endpoints.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class PageView(Base):
    __tablename__ = "page_views"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(500), nullable=False, index=True)
    referrer = Column(String(500), default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    ip_hash = Column(String(64), nullable=True, index=True)
    user_agent = Column(String(500), default="")
    country = Column(String(8), default="")
    duration_ms = Column(Integer, default=0)

    entity_type = Column(String(32), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_page_views_created_path", "created_at", "path"),
        Index("ix_page_views_entity", "entity_type", "entity_id"),
    )
