"""Emergent tag taxonomy (v2.0 §3, §12 `tag_clusters` — WP4).

A cluster is DERIVED from the free-text tags instructors typed (see
app/services/tag_service.py). `member_tags` are the raw tags; `label` is an
optional admin display name; `centroid` is reserved for embedding-based
clustering once an LLM key is configured (unused today).
"""
from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class TagCluster(Base):
    __tablename__ = "tag_clusters"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(120), nullable=True)
    member_tags = Column(JSON, nullable=False, default=list)
    size = Column(Integer, nullable=False, default=0)
    centroid = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
