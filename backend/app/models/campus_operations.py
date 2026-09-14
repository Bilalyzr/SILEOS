"""Institution-owned academic data and private files; no public upload paths."""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    LargeBinary,
    Float,
    Boolean,
)
from sqlalchemy.sql import func
from app.core.database import Base


class CampusTerm(Base):
    __tablename__ = "campus_terms"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=False)
    __table_args__ = (
        UniqueConstraint("institution_id", "name", name="uq_campus_term"),
    )


class CampusAttendance(Base):
    __tablename__ = "campus_attendance"
    id = Column(Integer, primary_key=True)
    batch_id = Column(
        Integer, ForeignKey("institution_batches.id"), nullable=False, index=True
    )
    member_id = Column(
        Integer, ForeignKey("institution_members.id"), nullable=False, index=True
    )
    day = Column(Date, nullable=False)
    status = Column(String(16), nullable=False)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("batch_id", "member_id", "day", name="uq_campus_attendance"),
    )


class CampusAssessment(Base):
    __tablename__ = "campus_assessments"
    id = Column(Integer, primary_key=True)
    batch_id = Column(
        Integer, ForeignKey("institution_batches.id"), nullable=False, index=True
    )
    term_id = Column(Integer, ForeignKey("campus_terms.id"), nullable=True)
    title = Column(String(160), nullable=False)
    max_score = Column(Float, nullable=False)
    due_on = Column(Date, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)


class CampusScore(Base):
    __tablename__ = "campus_scores"
    id = Column(Integer, primary_key=True)
    assessment_id = Column(
        Integer, ForeignKey("campus_assessments.id"), nullable=False, index=True
    )
    member_id = Column(Integer, ForeignKey("institution_members.id"), nullable=False)
    score = Column(Float, nullable=False)
    feedback = Column(String(1000), nullable=False, default="")
    graded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("assessment_id", "member_id", name="uq_campus_score"),
    )


class CampusResource(Base):
    __tablename__ = "campus_resources"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    batch_id = Column(Integer, ForeignKey("institution_batches.id"), nullable=True)
    title = Column(String(160), nullable=False)
    filename = Column(String(160), nullable=False)
    mime_type = Column(String(100), nullable=False)
    content = Column(LargeBinary, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampusBranding(Base):
    __tablename__ = "campus_branding"
    institution_id = Column(Integer, ForeignKey("institutions.id"), primary_key=True)
    title = Column(
        String(160), nullable=False, default="Your campus. Every possibility."
    )
    subtitle = Column(
        String(320), nullable=False, default="Learn, connect and grow together."
    )
    image = Column(LargeBinary, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CampusMailJob(Base):
    __tablename__ = "campus_mail_jobs"
    id = Column(Integer, primary_key=True)
    invite_id = Column(
        Integer, ForeignKey("institution_invites.id"), nullable=False, unique=True
    )
    status = Column(String(20), nullable=False, default="queued")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(String(250), nullable=False, default="")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ParentLinkRequest(Base):
    __tablename__ = "parent_link_requests"
    id = Column(Integer, primary_key=True)
    parent_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint(
            "parent_user_id", "student_user_id", name="uq_parent_link_request"
        ),
    )


class CampusSubscription(Base):
    __tablename__ = "campus_subscriptions"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    plan = Column(String(20), nullable=False)
    gateway_plan_id = Column(String(80), nullable=False)
    gateway_subscription_id = Column(String(80), nullable=True, unique=True)
    status = Column(String(30), nullable=False, default="creating")
    paid_through = Column(DateTime(timezone=True), nullable=True)
    checkout_url = Column(String(500), nullable=False, default="")
    last_event_at = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampusLearningCourse(Base):
    __tablename__ = "campus_learning_courses"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    batch_id = Column(Integer, ForeignKey("institution_batches.id"), nullable=True)
    title = Column(String(160), nullable=False)
    summary = Column(String(1000), nullable=False, default="")
    published = Column(Boolean, nullable=False, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampusLesson(Base):
    __tablename__ = "campus_lessons"
    id = Column(Integer, primary_key=True)
    course_id = Column(
        Integer, ForeignKey("campus_learning_courses.id"), nullable=False, index=True
    )
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=False)
    resource_id = Column(Integer, ForeignKey("campus_resources.id"), nullable=True)
    position = Column(Integer, nullable=False)
    __table_args__ = (
        UniqueConstraint("course_id", "position", name="uq_campus_lesson_position"),
    )


class CampusLessonProgress(Base):
    __tablename__ = "campus_lesson_progress"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(
        Integer, ForeignKey("campus_lessons.id"), nullable=False, index=True
    )
    member_id = Column(
        Integer, ForeignKey("institution_members.id"), nullable=False, index=True
    )
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("lesson_id", "member_id", name="uq_campus_lesson_progress"),
    )
