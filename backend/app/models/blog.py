"""
Blog Post Model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class BlogPost(Base):
    """Blog Post Model - SashaInfinity LMS blogging system"""
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)

    # Author information
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Post content
    title = Column(String(500), nullable=False)
    slug = Column(String(500), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    excerpt = Column(Text)

    # Featured image
    featured_image = Column(String(500))

    # Post metadata
    status = Column(String(20), default="DRAFT")  # DRAFT, PUBLISHED
    post_date = Column(DateTime, default=datetime.utcnow)
    post_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # SEO
    meta_title = Column(String(500))
    meta_description = Column(Text)

    # Categories and tags
    category = Column(String(100))
    tags = Column(String(500))  # Comma-separated tags

    # Related courses and internships (JSON array of IDs)
    related_course_ids = Column(String(500))  # JSON array: [1,2,3]
    related_internship_ids = Column(String(500))  # JSON array: [1,2,3]

    # Engagement metrics
    view_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = relationship("User", back_populates="blog_posts")
    comments = relationship("BlogComment", back_populates="blog_post", cascade="all, delete-orphan")


class BlogComment(Base):
    """Blog Comment Model"""
    __tablename__ = "blog_comments"

    id = Column(Integer, primary_key=True, index=True)
    blog_post_id = Column(Integer, ForeignKey("blog_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)
    status = Column(String(20), default="APPROVED")  # PENDING, APPROVED, SPAM

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    blog_post = relationship("BlogPost", back_populates="comments")
    user = relationship("User")
