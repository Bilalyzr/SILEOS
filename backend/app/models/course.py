"""
Course models - Premium SashaInfinity LMS course management system
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Index, text
from sqlalchemy.types import Numeric as Decimal
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Course(Base):
    """
    Course model - Replicated from wp_posts where post_type='courses'
    """
    __tablename__ = "courses"

    # Core fields (from wp_posts)
    id = Column(Integer, primary_key=True, index=True)
    post_author = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_date = Column(DateTime(timezone=True), server_default=func.now())
    post_date_gmt = Column(DateTime(timezone=True), server_default=func.now())
    post_content = Column(Text, default="")
    post_title = Column(Text, nullable=False)
    post_excerpt = Column(Text, default="")
    post_status = Column(String(20), default="draft")  # draft, pending, published, private
    comment_status = Column(String(20), default="open")
    ping_status = Column(String(20), default="open")
    post_password = Column(String(255), default="")
    post_name = Column(String(200), index=True, default="")
    __table_args__ = (Index('uq_courses_public_slug', func.lower(post_name), unique=True,
                           sqlite_where=text("post_name <> ''"), postgresql_where=text("post_name <> ''")),)
    to_ping = Column(Text, default="")
    pinged = Column(Text, default="")
    post_modified = Column(DateTime(timezone=True), server_default=func.now())
    post_modified_gmt = Column(DateTime(timezone=True), server_default=func.now())
    post_content_filtered = Column(Text, default="")
    post_parent = Column(Integer, default=0)
    guid = Column(String(255), default="")
    menu_order = Column(Integer, default=0)
    post_type = Column(String(20), default="courses")
    post_mime_type = Column(String(100), default="")
    comment_count = Column(Integer, default=0)

    # Course specific fields (from postmeta)
    course_price_type = Column(String(20), default="free")  # free, paid
    course_price = Column(Decimal(10, 2), default=0)
    course_sale_price = Column(Decimal(10, 2), default=0)
    course_duration = Column(String(255), default="")
    course_level = Column(String(50), default="beginner")  # beginner, intermediate, advanced
    course_category = Column(String(100), default="")  # Simple category field
    course_language = Column(String(50), default="English")
    course_benefits = Column(Text, default="")
    course_requirements = Column(Text, default="")
    course_target_audience = Column(Text, default="")
    course_material_includes = Column(Text, default="")
    course_tags = Column(Text, default="")  # Simple tags field (JSON string)

    # Offline workshop and institution fields
    num_offline_workshops = Column(Integer, default=0)
    # Offline contact hours. Defaults to 60 (was 0) so a course created without
    # an explicit value carries the standard programme length rather than
    # displaying "0 hours" on the course page.
    num_hours = Column(Integer, default=60)
    institution = Column(String(255), default="")

    # Media
    course_thumbnail = Column(String(255), default="")
    course_cover_image = Column(String(255), default="")
    course_intro_video = Column(String(255), default="")

    # Settings
    course_retakes_allowed = Column(Boolean, default=True)
    course_auto_start_next_lesson = Column(Boolean, default=False)
    course_content_drip_type = Column(String(50), default="none")

    # Certificate settings
    certificate_template = Column(String(255), default="")
    course_sections_meta = Column(Text, default="")
    course_type = Column(String(50), default="")
    enabled_tools = Column(JSON, default=list)
    is_template = Column(Boolean, default=False)   # R6: start-from-template catalogue
    certificate_design = Column(JSON, default={})

    # Analytics
    total_enrollments = Column(Integer, default=0)
    average_rating = Column(Decimal(3, 2), default=0)
    total_reviews = Column(Integer, default=0)
    # Total times any lesson video in this course has been viewed
    # (incremented per watch session, see routers/progress.py & courses.py).
    video_view_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    instructor = relationship("User", back_populates="courses")
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan", order_by="Lesson.menu_order")
    quizzes = relationship("Quiz", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", passive_deletes="all")
    reviews = relationship("CourseReview", back_populates="course")
    categories = relationship("CourseCategory", secondary="course_category_relations", back_populates="courses")
    tags = relationship("CourseTag", secondary="course_tag_relations", back_populates="courses")

    def __repr__(self):
        return f"<Course(id={self.id}, title={self.post_title})>"

class Lesson(Base):
    """
    Lesson model - Replicated from wp_posts where post_type='lesson'
    """
    __tablename__ = "lessons"

    # Core fields (from wp_posts)
    id = Column(Integer, primary_key=True, index=True)
    post_author = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_date = Column(DateTime(timezone=True), server_default=func.now())
    post_content = Column(Text, default="")
    post_title = Column(Text, nullable=False)
    post_excerpt = Column(Text, default="")
    post_status = Column(String(20), default="publish")
    post_name = Column(String(200), index=True, default="")
    post_modified = Column(DateTime(timezone=True), server_default=func.now())
    post_parent = Column(Integer, ForeignKey("courses.id"), nullable=False)
    menu_order = Column(Integer, default=0)
    post_type = Column(String(20), default="lesson")

    # Lesson specific fields
    lesson_video_source = Column(String(50), default="html5")
    lesson_video_url = Column(String(255), default="")
    lesson_youtube_url = Column(String(255), default="")
    lesson_video_duration = Column(String(50), default="")
    lesson_video_poster = Column(String(255), default="")

    # H5P interactive-content support (plan Task 4, spec B5). "video" is the
    # pre-existing default player behaviour; "h5p" branches the frontend
    # player to the sandboxed H5P iframe (see H5PLesson.tsx) and requires
    # h5p_content_id to point at a ready app.models.h5p.H5PContent row.
    lesson_content_type = Column(String(20), default="video")
    h5p_content_id = Column(Integer, ForeignKey("h5p_contents.id"), nullable=True)

    # Learning-game lesson support (spec 2026-09-03-learning-games §2/§3).
    # "game" branches the frontend player to GamePlayer.tsx and requires
    # game_id to point at a published app.models.game.Game row owned by the
    # lesson author (admin any) — validated by courses.py's
    # _resolve_lesson_content_fields, the same atomic-pair helper that
    # guards h5p_content_id.
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    # geogebra_applet_id to point at a GeoGebraApplet row — attachable
    # ONLY to lessons of FREE courses (enforced in the content resolver).
    geogebra_applet_id = Column(Integer, ForeignKey("geogebra_applets.id"), nullable=True)
    # Phase 2: 3D GLB model (MP/UP courses only) and PhET virtual lab slug.
    three_d_model_id = Column(Integer, ForeignKey("three_d_models.id"), nullable=True)
    virtual_lab_sim = Column(String(50), nullable=True)

    # Content settings
    lesson_attachments = Column(Text, default="")
    lesson_preview = Column(Boolean, default=False)
    lesson_attachment_url = Column(Text, default='')

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="lessons")
    progress = relationship("LessonProgress", back_populates="lesson")

    def __repr__(self):
        return f"<Lesson(id={self.id}, title={self.post_title})>"

class CourseCategory(Base):
    """
    Course categories
    """
    __tablename__ = "course_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(200), nullable=False, unique=True)
    description = Column(Text, default="")
    parent_id = Column(Integer, ForeignKey("course_categories.id"), nullable=True)
    term_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    courses = relationship("Course", secondary="course_category_relations", back_populates="categories")
    parent = relationship("CourseCategory", remote_side=[id])

    def __repr__(self):
        return f"<CourseCategory(id={self.id}, name={self.name})>"

class CourseTag(Base):
    """
    Course tags
    """
    __tablename__ = "course_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    slug = Column(String(200), nullable=False, unique=True)
    description = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    courses = relationship("Course", secondary="course_tag_relations", back_populates="tags")

    def __repr__(self):
        return f"<CourseTag(id={self.id}, name={self.name})>"

class CourseReview(Base):
    """
    Course reviews and ratings
    """
    __tablename__ = "course_reviews"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_title = Column(String(255), default="")
    review_content = Column(Text, default="")
    review_status = Column(String(20), default="approved")  # legacy column, kept for backward compat
    # New moderation column (migration: course_review_status_2026_04_23.sql).
    # New rows default to 'pending' — existing rows were backfilled to
    # 'approved' by the migration so legacy reviews stay visible.
    status = Column(String(20), nullable=False, default="pending")
    admin_notes = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="reviews")
    user = relationship("User")

    def __repr__(self):
        return f"<CourseReview(course_id={self.course_id}, user_id={self.user_id}, rating={self.rating})>"

# Association tables
class CourseCategoryRelation(Base):
    """Association table for course-category many-to-many relationship"""
    __tablename__ = "course_category_relations"

    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    category_id = Column(Integer, ForeignKey("course_categories.id"), primary_key=True)

class CourseTagRelation(Base):
    """Association table for course-tag many-to-many relationship"""
    __tablename__ = "course_tag_relations"

    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("course_tags.id"), primary_key=True)
