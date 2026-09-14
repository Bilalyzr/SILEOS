"""Course bundles: one one-time price for a set of paid courses.

Fulfillment reads the course set from the ORDER NOTES SNAPSHOT taken at
purchase time — editing a bundle never changes what an already-paid buyer
receives.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.types import Numeric
from sqlalchemy.sql import func

from app.core.database import Base


class Bundle(Base):
    __tablename__ = "bundles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    slug = Column(String(255), unique=True, nullable=False, index=True)
    bundle_price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())

    def __repr__(self):
        return f"<Bundle(id={self.id}, slug={self.slug})>"


class BundleCourse(Base):
    __tablename__ = "bundle_courses"

    id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
