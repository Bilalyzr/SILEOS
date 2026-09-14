"""3D model library (Phase 2 — type-driven tools, owner 2026-09-04).

`ThreeDModel` is one instructor-uploaded GLB file. `file_path` is PRIVATE
(relative to backend/three_d/, never nginx-served) and streams only through
the authenticated /file endpoint — same doctrine as ebooks. Attachable to
lessons of MP (meiporul) and UP (utporul) courses only; enforced in the
courses.py content resolver.
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class ThreeDModel(Base):
    __tablename__ = "three_d_models"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)   # PRIVATE, relative path
    file_size_bytes = Column(Integer, default=0)
    format = Column(String(10), default="glb")        # glb only in Phase 2
    # Admin-shared library asset: visible in every instructor's picker and
    # attachable cross-owner (content libraries, 2026-09-05).
    tier_files = Column(JSON, nullable=True)   # {"T2": rel_path, "T3": rel_path} built by media_pipeline
    is_library = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
