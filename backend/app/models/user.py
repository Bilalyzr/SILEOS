"""
User models - Premium SashaInfinity LMS user management system
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    """
    User model - Premium SashaInfinity LMS user management
    """
    __tablename__ = "users"

    # Core user fields
    id = Column(Integer, primary_key=True, index=True)
    user_login = Column(String(60), unique=True, index=True, nullable=False)
    user_pass = Column(String(255), nullable=False)
    user_nicename = Column(String(50), index=True, nullable=False)
    user_email = Column(String(100), unique=True, index=True, nullable=False)
    user_url = Column(String(100), default="")
    user_registered = Column(DateTime(timezone=True), server_default=func.now())
    user_activation_key = Column(String(255), default="")
    # Legacy WordPress-compatible mirror. Runtime authorization and active-user
    # reporting use is_active; keep new rows aligned for older integrations.
    user_status = Column(Integer, default=1, server_default="1")
    display_name = Column(String(250), nullable=False)

    # Additional fields for LMS functionality
    role = Column(String(50), default="student")  # student, instructor, admin, superadmin, spoc, company, company_manager
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)
    profile_completed = Column(Boolean, default=False)  # First-time profile completion
    last_login = Column(DateTime(timezone=True))

    # TOTP two-factor auth. `totp_secret` holds the base32 shared secret and is
    # written at enrolment; `totp_enabled` only flips true once the user has
    # proved they can generate a valid code, so a half-finished enrolment can
    # never lock anyone out. Enforced for admins at login (see routers/auth.py).
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    instructor_profile = relationship("InstructorProfile", back_populates="user", uselist=False)
    courses = relationship("Course", back_populates="instructor")
    enrollments = relationship("Enrollment", back_populates="student")
    quiz_attempts = relationship("QuizAttempt", back_populates="user")
    orders = relationship("Order", back_populates="user")
    earnings = relationship("Earning", back_populates="user")
    # Withdrawal now carries a second FK to users.id (processed_by, the admin
    # who actioned it) alongside user_id (the instructor being paid) — pin
    # this relationship to user_id so SQLAlchemy doesn't have to guess.
    withdrawals = relationship("Withdrawal", back_populates="user",
                               foreign_keys="Withdrawal.user_id")
    blog_posts = relationship("BlogPost", back_populates="author")
    coupons = relationship("Coupon", back_populates="creator")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.user_email})>"

class UserProfile(Base):
    """
    User profile - Replicated from wp_usermeta
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Profile information
    first_name = Column(String(255), default="")
    last_name = Column(String(255), default="")
    description = Column(Text, default="")
    phone = Column(String(20), default="")
    designation = Column(String(255), default="")

    # Address information
    address = Column(Text, default="")
    city = Column(String(100), default="")
    state = Column(String(100), default="")
    country = Column(String(100), default="")
    postal_code = Column(String(20), default="")

    # Profile image
    profile_photo = Column(String(255), default="")
    cover_photo = Column(String(255), default="")

    # Social links
    facebook = Column(String(255), default="")
    twitter = Column(String(255), default="")
    linkedin = Column(String(255), default="")
    website = Column(String(255), default="")

    # Settings
    show_email = Column(Boolean, default=False)
    receive_notifications = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id})>"

class InstructorProfile(Base):
    """
    Instructor specific profile data
    """
    __tablename__ = "instructor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Instructor specific fields
    instructor_rating = Column(String(10), default="0")
    instructor_bio = Column(Text, default="")
    instructor_designation = Column(String(255), default="")

    # Completion status
    profile_completion = Column(Integer, default=0)
    is_approved = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)

    # Earning settings
    earning_commission_type = Column(String(20), default="percentage")
    earning_commission_amount = Column(String(20), default="80")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="instructor_profile")

    def __repr__(self):
        return f"<InstructorProfile(user_id={self.user_id})>"

class AdminImpersonationLog(Base):
    """
    Audit log for admin 'View as Instructor' impersonation sessions.

    One row per impersonation start. `ended_at` is populated when:
      - The admin explicitly exits via POST /admin/impersonate/end, OR
      - The backend lazily notices the impersonation token has expired
        and closes out the most recent open row for that admin/target pair.

    We intentionally index on (admin_user_id) and (target_user_id) so
    the common "who impersonated whom / who has been impersonated" audit
    queries stay cheap as the table grows.
    """
    __tablename__ = "admin_impersonation_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=True)
    # Which role *started* this session. Nullable for back-fill of pre-existing
    # rows (treated as 'admin' on read). Lets the SuperAdmin audit feed
    # distinguish superadmin-initiated sessions from ordinary admin ones
    # without joining the users table.
    actor_role = Column(String(32), nullable=True, default="admin", index=True)

    def __repr__(self):
        return (
            f"<AdminImpersonationLog(id={self.id}, admin={self.admin_user_id}, "
            f"target={self.target_user_id}, started={self.started_at}, ended={self.ended_at})>"
        )


class UserRole(Base):
    """
    User roles - SashaInfinity LMS role system
    """
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), nullable=False)  # student, instructor, admin

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role={self.role})>"
