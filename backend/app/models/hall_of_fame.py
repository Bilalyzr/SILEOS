"""
Wall of Fame member model.

Each row is one staff profile shown on the public /hall-of-fame page.
Managed by admins/superadmins via /api/v1/hall-of-fame/* endpoints.
Replaces the hardcoded HALL_OF_FAME array that lived in the frontend.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class HallOfFameMember(Base):
    __tablename__ = "hall_of_fame_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    role = Column(String(200), nullable=False, default="")
    company = Column(String(200), nullable=False, default="")
    # URL to the uploaded photo (string, like BlogPost.featured_image).
    # NULL when no photo is set - the frontend renders an initials avatar.
    photo = Column(String(500), nullable=True)
    tenure = Column(String(100), nullable=False, default="")
    location = Column(String(200), nullable=True)
    linkedin = Column(String(500), nullable=True)
    blurb = Column(Text, nullable=True)
    highlight = Column(String(100), nullable=True)
    # Manual ordering on the public page (lower = appears first).
    sort_order = Column(Integer, nullable=False, default=0, index=True)
    # Draft toggle - unpublished members are hidden from the public list
    # but still visible/editable in the admin UI.
    is_published = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<HallOfFameMember(id={self.id}, name={self.name}, order={self.sort_order})>"
