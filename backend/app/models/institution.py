"""School/college administration. Existing LMS courses remain shared resources."""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from app.core.database import Base


class Institution(Base):
    __tablename__ = "institutions"
    id = Column(Integer, primary_key=True)
    # Commercial/customer boundary. An institution remains the campus-domain
    # aggregate while the tenant connects it to shared identity, entitlements,
    # domains, revenue, and platform-wide governance.
    tenant_id = Column(
        Integer, ForeignKey("platform_tenants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name = Column(String(160), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    kind = Column(String(20), nullable=False, default="school")
    academic_year = Column(String(32), nullable=False)
    timezone = Column(String(64), nullable=False, default="Asia/Kolkata")
    description = Column(Text, nullable=False, default="")
    plan = Column(String(20), nullable=False, default="starter")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InstitutionMember(Base):
    __tablename__ = "institution_members"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    department = Column(String(100), nullable=False, default="")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_institution_member"),
    )


class InstitutionInvite(Base):
    __tablename__ = "institution_invites"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    email = Column(String(254), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    department = Column(String(100), nullable=False, default="")
    status = Column(String(20), nullable=False, default="pending")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("institution_id", "email", name="uq_institution_invite"),
    )


class InstitutionBatch(Base):
    __tablename__ = "institution_batches"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False, default="")
    academic_year = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint(
            "institution_id", "name", "academic_year", name="uq_institution_batch"
        ),
    )


class InstitutionBatchMember(Base):
    __tablename__ = "institution_batch_members"
    id = Column(Integer, primary_key=True)
    batch_id = Column(
        Integer, ForeignKey("institution_batches.id"), nullable=False, index=True
    )
    member_id = Column(
        Integer, ForeignKey("institution_members.id"), nullable=False, index=True
    )
    __table_args__ = (
        UniqueConstraint("batch_id", "member_id", name="uq_institution_batch_member"),
    )


class InstitutionCourse(Base):
    __tablename__ = "institution_courses"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    connected_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("institution_id", "course_id", name="uq_institution_course"),
    )


class InstitutionAssignment(Base):
    __tablename__ = "institution_assignments"
    id = Column(Integer, primary_key=True)
    batch_id = Column(
        Integer, ForeignKey("institution_batches.id"), nullable=False, index=True
    )
    institution_course_id = Column(
        Integer, ForeignKey("institution_courses.id"), nullable=False
    )
    due_date = Column(String(10), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "institution_course_id", name="uq_institution_assignment"
        ),
    )


class InstitutionAudit(Base):
    __tablename__ = "institution_audit"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(60), nullable=False)
    detail = Column(String(250), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InstitutionPlanRequest(Base):
    __tablename__ = "institution_plan_requests"
    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer, ForeignKey("institutions.id"), nullable=False, index=True
    )
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    note = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
