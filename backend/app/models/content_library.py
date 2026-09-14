"""Content libraries (2026-09-05) — admin-curated catalogs that instructors
pull into a course curriculum.

VirtualLabCatalog — one virtual lab entry. Three providers:
  * 'phet'   — a PhET HTML5 sim (embed_url derived from the slug when blank);
  * 'embed'  — any https iframe-able lab the admin adds;
  * 'native' — a lab we ship and render ourselves (native_template + config,
               validated by app/schemas/lab_config.py; gradeable by parameters).
Built-in labs live as constants in app/routers/virtual_labs.py; DB rows add to
(or, on slug collision, override) them. lessons.virtual_lab_sim stores the slug,
which is why slug is capped at 50 chars.

VirtualLabResult — advisory score rows for native labs (same posture as
GameResult: client-graded, never gradebook truth, XP awarded best-effort).
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class VirtualLabCatalog(Base):
    __tablename__ = "virtual_lab_catalog"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    subject = Column(String(50), nullable=False, default="general")
    description = Column(Text, nullable=True)
    provider = Column(String(16), nullable=False, default="embed")   # phet | embed | native
    embed_url = Column(String(1000), nullable=True)
    native_template = Column(String(32), nullable=True)             # reaction_lab | identify_lab
    config = Column(JSON, nullable=True)                              # native only
    attribution = Column(String(300), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    is_published = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VirtualLabResult(Base):
    __tablename__ = "virtual_lab_results"

    id = Column(Integer, primary_key=True, index=True)
    lab_slug = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    duration_s = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
