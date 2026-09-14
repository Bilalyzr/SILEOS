"""
Enrollment and progress models - Premium SashaInfinity LMS enrollment structure
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.types import Numeric as Decimal
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Enrollment(Base):
    """
    Course enrollments - Replicated from tutor_enrollments table
    """
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # Cohort tracking (for SPOC referral enrollments)
    cohort_id = Column(Integer, ForeignKey("cohorts.id"), nullable=True)

    # Membership-materialized enrollment tracking (memberships sub-project).
    # "membership" marks rows the membership system owns; NULL = purchase/legacy.
    enrollment_source = Column(String(20), nullable=True)
    # Indexed: suspend_membership_enrollments and every lapse-expiry pass
    # filter on membership_id.
    membership_id = Column(Integer, ForeignKey("memberships.id"), nullable=True,
                           index=True)

    # Enrollment details
    enrollment_date = Column(DateTime(timezone=True), server_default=func.now())
    enrollment_status = Column(String(50), default="enrolled")  # enrolled, completed, cancelled

    # Progress tracking
    course_progress_percentage = Column(Integer, default=0)
    completed_lessons = Column(Integer, default=0)
    total_lessons = Column(Integer, default=0)
    completed_quizzes = Column(Integer, default=0)
    total_quizzes = Column(Integer, default=0)

    # Completion details
    completion_date = Column(DateTime(timezone=True), nullable=True)
    completion_mode = Column(String(50), default="")
    completion_mode_text = Column(Text, default="")
    certificate_id = Column(String(100), nullable=True)  # ID of the issued certificate
    certificate_url = Column(String(500), nullable=True)  # URL to the certificate file

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    order = relationship("Order", back_populates="enrollments")
    cohort = relationship("Cohort", backref="enrollments")
    lesson_progress = relationship("LessonProgress", back_populates="enrollment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Enrollment(course_id={self.course_id}, user_id={self.user_id}, status={self.enrollment_status})>"

class LessonProgress(Base):
    """
    Lesson progress tracking - Replicated from tutor_lesson_progress table
    """
    __tablename__ = "lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)

    # Progress details
    progress_status = Column(String(50), default="started")  # started, completed
    completion_date = Column(DateTime(timezone=True), nullable=True)

    # Video progress
    video_current_time = Column(Integer, default=0)  # in seconds
    video_total_duration = Column(Integer, default=0)  # in seconds
    video_completion_percentage = Column(Integer, default=0)

    # Reading time
    reading_time = Column(Integer, default=0)  # in minutes

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    course = relationship("Course")
    lesson = relationship("Lesson", back_populates="progress")
    enrollment = relationship("Enrollment", back_populates="lesson_progress")

    def __repr__(self):
        return f"<LessonProgress(lesson_id={self.lesson_id}, user_id={self.user_id}, status={self.progress_status})>"

class StudentCourseActivity(Base):
    """
    Student course activities - Replicated from tutor_student_course_activities table
    """
    __tablename__ = "student_course_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=True)

    # Activity details
    activity_type = Column(String(50), nullable=False)  # lesson_completed, quiz_attempted, course_completed, etc.
    activity_value = Column(Text, default="")
    activity_status = Column(String(50), default="active")

    # Meta information
    activity_meta = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    course = relationship("Course")
    lesson = relationship("Lesson")
    quiz = relationship("Quiz")

    def __repr__(self):
        return f"<StudentCourseActivity(user_id={self.user_id}, type={self.activity_type})>"


class WatchSession(Base):
    """
    Granular video-watch session log (Issue 8: Student Activity).

    One row per contiguous watch segment — a play, a pause/resume pair, or a
    full play-to-end. Aggregated by the admin Student Activity endpoints to
    report time spent, number of sessions, last-active and the full
    viewing history (started / paused / resumed / completed).
    """
    __tablename__ = "watch_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)

    # 'started' | 'paused' | 'resumed' | 'completed' — the event that opened
    # or advanced this segment. Drives the Viewing History timeline.
    event = Column(String(20), nullable=False)

    # Watched seconds accumulated during THIS segment. Sum across a user's
    # rows in a course = total time spent.
    duration_seconds = Column(Integer, default=0)

    # Video position (seconds) at the moment of the event, for history.
    position_seconds = Column(Integer, default=0)

    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    course = relationship("Course")
    lesson = relationship("Lesson")

    def __repr__(self):
        return f"<WatchSession(user_id={self.user_id}, course_id={self.course_id}, event={self.event})>"


class CourseAnnouncement(Base):
    """
    Course announcements - Replicated from wp_posts where post_type='tutor_announcements'
    """
    __tablename__ = "course_announcements"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    post_author = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Content
    post_title = Column(Text, nullable=False)
    post_content = Column(Text, default="")
    post_excerpt = Column(Text, default="")
    post_status = Column(String(20), default="publish")

    # Timestamps
    post_date = Column(DateTime(timezone=True), server_default=func.now())
    post_modified = Column(DateTime(timezone=True), server_default=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course")
    author = relationship("User")

    def __repr__(self):
        return f"<CourseAnnouncement(id={self.id}, course_id={self.course_id}, title={self.post_title})>"

class WishlistItem(Base):
    """
    Course wishlist - Custom table for user wishlists
    """
    __tablename__ = "wishlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    course = relationship("Course")

    def __repr__(self):
        return f"<WishlistItem(user_id={self.user_id}, course_id={self.course_id})>"