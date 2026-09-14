"""
Certificate models - Premium SashaInfinity LMS certificate structure
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.types import Numeric as Decimal
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Machine-readable invalidation reason written by
# CourseService.calculate_course_progress when recomputed progress falls
# below 100% (completion regression). CertificateService
# .issue_certificate_for_enrollment revives an invalidated certificate ONLY
# when this exact marker is present; any other reason (e.g. an admin
# revoke via /certificates/admin/{id}/revoke) is terminal.
COMPLETION_REGRESSED_INVALIDATION_REASON = "course_completion_regressed"

class Certificate(Base):
    """
    Certificate templates - Replicated from wp_posts where post_type='tutor_certificates'
    """
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    post_author = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Core fields (from wp_posts)
    post_date = Column(DateTime(timezone=True), server_default=func.now())
    post_content = Column(Text, default="")  # Certificate HTML content
    post_title = Column(Text, nullable=False)  # Certificate name
    post_excerpt = Column(Text, default="")
    post_status = Column(String(20), default="publish")
    post_name = Column(String(200), index=True, default="")
    post_modified = Column(DateTime(timezone=True), server_default=func.now())
    post_parent = Column(Integer, default=0)
    menu_order = Column(Integer, default=0)
    post_type = Column(String(20), default="tutor_certificates")

    # Certificate settings (from postmeta)
    certificate_orientation = Column(String(50), default="landscape")  # landscape, portrait
    certificate_size = Column(String(50), default="A4")  # A4, letter, custom
    certificate_width = Column(Integer, default=1400)  # pixels for custom size
    certificate_height = Column(Integer, default=1080)  # pixels for custom size

    # Template design
    background_image = Column(String(255), default="")
    background_color = Column(String(7), default="#ffffff")

    # Text styles
    title_font_size = Column(Integer, default=48)
    title_font_color = Column(String(7), default="#000000")
    title_font_family = Column(String(100), default="Arial")

    body_font_size = Column(Integer, default=24)
    body_font_color = Column(String(7), default="#000000")
    body_font_family = Column(String(100), default="Arial")

    # Certificate elements (positions and styles)
    elements_config = Column(JSON, default={})  # Store all element configurations

    # Enable/disable elements
    show_student_name = Column(Boolean, default=True)
    show_course_name = Column(Boolean, default=True)
    show_completion_date = Column(Boolean, default=True)
    show_certificate_id = Column(Boolean, default=True)
    show_instructor_signature = Column(Boolean, default=True)
    show_admin_signature = Column(Boolean, default=False)

    # QR Code settings
    enable_qr_code = Column(Boolean, default=False)
    qr_code_size = Column(Integer, default=100)
    qr_code_position = Column(String(50), default="bottom-right")

    # Instructor designer scoping (Task 6): a template an admin marks global
    # is readable (not editable) by every instructor, not just its author
    # (post_author). Own-template CRUD stays scoped by post_author regardless.
    is_global = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    author = relationship("User")
    issued_certificates = relationship("IssuedCertificate", back_populates="template")
    course_certificates = relationship("CourseCertificate", back_populates="certificate")

    def __repr__(self):
        return f"<Certificate(id={self.id}, title={self.post_title})>"

class CourseCertificate(Base):
    """
    Course-certificate assignments - Replicated from postmeta where meta_key='course_certificate'
    """
    __tablename__ = "course_certificates"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    certificate_id = Column(Integer, ForeignKey("certificates.id"), nullable=False)

    # Certificate criteria
    required_completion_percentage = Column(Integer, default=100)
    required_quiz_pass = Column(Boolean, default=False)
    required_assignment_pass = Column(Boolean, default=False)

    # Auto generation settings
    auto_generate = Column(Boolean, default=True)
    email_to_student = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    course = relationship("Course")
    certificate = relationship("Certificate", back_populates="course_certificates")

    def __repr__(self):
        return f"<CourseCertificate(course_id={self.course_id}, certificate_id={self.certificate_id})>"

class IssuedCertificate(Base):
    """
    Issued certificates - Replicated from tutor_generated_certificates table
    """
    __tablename__ = "issued_certificates"

    id = Column(Integer, primary_key=True, index=True)
    certificate_id = Column(Integer, ForeignKey("certificates.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Certificate details
    certificate_hash = Column(String(255), unique=True, nullable=False)  # Unique verification code
    secure_certificate_id = Column(String(100), unique=True, nullable=False)  # Formatted secure certificate ID
    certificate_title = Column(String(255), nullable=False)
    certificate_content = Column(Text, default="")  # Generated HTML content

    # Completion details
    completion_date = Column(DateTime(timezone=True), nullable=False)
    course_completion_percentage = Column(Decimal(5, 2), default=100.00)
    quiz_completion_percentage = Column(Decimal(5, 2), default=0.00)
    assignment_completion_percentage = Column(Decimal(5, 2), default=0.00)

    # Certificate file
    certificate_file_path = Column(String(500), default="")  # Path to generated PDF/image
    certificate_download_url = Column(String(500), default="")

    # Validation
    is_valid = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Certificate expiration date
    invalidated_date = Column(DateTime(timezone=True), nullable=True)
    invalidation_reason = Column(Text, default="")

    # Email tracking
    email_sent = Column(Boolean, default=False)
    email_sent_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    template = relationship("Certificate", back_populates="issued_certificates")
    course = relationship("Course")
    student = relationship("User")

    __table_args__ = (
        # Race-safe idempotency: one certificate per (user, course).
        # Concurrent 100%-completion triggers hitting different workers used to
        # produce duplicate rows; the unique index makes the second insert
        # fail fast with IntegrityError, and callers (issue_certificate_for_enrollment)
        # retry the lookup.
        UniqueConstraint("user_id", "course_id", name="uq_issued_certificate_user_course"),
        Index("ix_issued_cert_user_course", "user_id", "course_id"),
    )

    def __repr__(self):
        return f"<IssuedCertificate(id={self.id}, hash={self.certificate_hash}, user_id={self.user_id})>"

class CertificateVerification(Base):
    """
    Certificate verification logs
    """
    __tablename__ = "certificate_verifications"

    id = Column(Integer, primary_key=True, index=True)
    certificate_id = Column(Integer, ForeignKey("issued_certificates.id"), nullable=True)  # Nullable for failed verifications
    certificate_hash = Column(String(255), nullable=False)

    # Verification details
    verified_by_ip = Column(String(45), default="")
    verified_by_user_agent = Column(Text, default="")
    verification_result = Column(String(50), default="valid")  # valid, invalid, expired

    verified_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    certificate = relationship("IssuedCertificate")

    def __repr__(self):
        return f"<CertificateVerification(certificate_hash={self.certificate_hash}, result={self.verification_result})>"

class CertificateElementTemplate(Base):
    """
    Reusable certificate elements (signatures, logos, etc.)
    """
    __tablename__ = "certificate_element_templates"

    id = Column(Integer, primary_key=True, index=True)
    element_name = Column(String(255), nullable=False)
    element_type = Column(String(50), nullable=False)  # signature, logo, text, image

    # Element content
    element_content = Column(Text, default="")  # HTML/text content
    element_image_url = Column(String(500), default="")

    # Styling
    element_styles = Column(JSON, default={})  # CSS styles as JSON

    # Default positioning
    default_position_x = Column(Integer, default=0)
    default_position_y = Column(Integer, default=0)
    default_width = Column(Integer, default=100)
    default_height = Column(Integer, default=50)

    # Usage tracking
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User")

    def __repr__(self):
        return f"<CertificateElementTemplate(id={self.id}, name={self.element_name}, type={self.element_type})>"