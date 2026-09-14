"""Tenant-scoped admissions and learner lifecycle records.

Admissions intentionally links to institution memberships rather than the
platform role on ``users``.  An applicant may exist before a SashaInfinity
account does; conversion creates or reuses an institution student membership
only after an authorized manager performs the explicit conversion step.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


PROGRAM_STATUSES = ("draft", "active", "archived")
INTAKE_STATUSES = ("draft", "open", "closed", "archived")
APPLICATION_STAGES = (
    "draft",
    "submitted",
    "screening",
    "documents",
    "assessment",
    "interview",
    "decision",
    "waitlisted",
    "offered",
    "admitted",
    "rejected",
    "withdrawn",
    "enrolled",
)
OFFER_STATUSES = (
    "none",
    "draft",
    "issued",
    "accepted",
    "declined",
    "expired",
    "revoked",
)
DOCUMENT_STATUSES = ("pending", "submitted", "verified", "rejected", "waived")
TASK_STATUSES = ("open", "in_progress", "completed", "cancelled")
LEARNER_STATUSES = (
    "enrolled",
    "active",
    "on_leave",
    "completed",
    "withdrawn",
    "transferred",
)


def _allowed(column: str, values: tuple[str, ...], name: str) -> CheckConstraint:
    quoted = ", ".join(f"'{value}'" for value in values)
    return CheckConstraint(f"{column} IN ({quoted})", name=name)


class AdmissionProgram(Base):
    __tablename__ = "admission_programs"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(160), nullable=False)
    code = Column(String(24), nullable=False)
    level = Column(String(30), nullable=False, default="other")
    department = Column(String(100), nullable=False, default="")
    duration_months = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_admission_program_code"),
        _allowed("status", PROGRAM_STATUSES, "ck_admission_program_status"),
        CheckConstraint("duration_months > 0", name="ck_admission_program_duration"),
    )


class AdmissionIntake(Base):
    __tablename__ = "admission_intakes"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = Column(
        Integer,
        ForeignKey("admission_programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    batch_id = Column(
        Integer,
        ForeignKey("institution_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    name = Column(String(120), nullable=False)
    academic_year = Column(String(32), nullable=False)
    starts_on = Column(Date, nullable=False)
    closes_on = Column(Date, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "program_id",
            "name",
            "academic_year",
            name="uq_admission_intake",
        ),
        _allowed("status", INTAKE_STATUSES, "ck_admission_intake_status"),
        CheckConstraint("capacity > 0", name="ck_admission_intake_capacity"),
        CheckConstraint("closes_on <= starts_on", name="ck_admission_intake_dates"),
    )


class AdmissionApplication(Base):
    __tablename__ = "admission_applications"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = Column(
        Integer,
        ForeignKey("admission_programs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    intake_id = Column(
        Integer,
        ForeignKey("admission_intakes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    application_number = Column(String(32), nullable=False)
    full_name = Column(String(160), nullable=False)
    email = Column(String(254), nullable=False, index=True)
    phone = Column(String(20), nullable=False, default="")
    date_of_birth = Column(Date, nullable=True)
    address = Column(String(1000), nullable=False, default="")
    prior_institution = Column(String(160), nullable=False, default="")
    source = Column(String(60), nullable=False, default="manual")
    stage = Column(String(20), nullable=False, default="submitted", index=True)
    offer_status = Column(String(20), nullable=False, default="none", index=True)
    offer_expires_on = Column(Date, nullable=True)
    offer_conditions = Column(String(4000), nullable=False, default="")
    tuition_amount = Column(Numeric(12, 2), nullable=True)
    offer_currency = Column(String(3), nullable=False, default="INR")
    offer_issued_at = Column(DateTime(timezone=True), nullable=True)
    offer_responded_at = Column(DateTime(timezone=True), nullable=True)
    owner_member_id = Column(
        Integer,
        ForeignKey("institution_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    enrollment_member_id = Column(
        Integer,
        ForeignKey("institution_members.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    invitation_id = Column(
        Integer,
        ForeignKey("institution_invites.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "application_number",
            name="uq_admission_application_number",
        ),
        Index(
            "ix_admission_applications_pipeline",
            "institution_id",
            "intake_id",
            "stage",
            "id",
        ),
        _allowed("stage", APPLICATION_STAGES, "ck_admission_application_stage"),
        _allowed("offer_status", OFFER_STATUSES, "ck_admission_offer_status"),
        CheckConstraint("version > 0", name="ck_admission_application_version"),
        CheckConstraint(
            "tuition_amount IS NULL OR tuition_amount >= 0", name="ck_admission_tuition"
        ),
    )


class AdmissionDocument(Base):
    __tablename__ = "admission_documents"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer,
        ForeignKey("admission_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind = Column(String(40), nullable=False)
    label = Column(String(120), nullable=False)
    required = Column(Boolean, nullable=False, default=True)
    status = Column(String(20), nullable=False, default="pending")
    due_on = Column(Date, nullable=True)
    rejection_reason = Column(String(500), nullable=False, default="")
    verified_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("application_id", "label", name="uq_admission_document_label"),
        _allowed("status", DOCUMENT_STATUSES, "ck_admission_document_status"),
    )


class AdmissionNote(Base):
    __tablename__ = "admission_notes"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer,
        ForeignKey("admission_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body = Column(String(4000), nullable=False)
    author_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AdmissionTask(Base):
    __tablename__ = "admission_tasks"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer,
        ForeignKey("admission_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    due_on = Column(Date, nullable=True, index=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    assignee_member_id = Column(
        Integer,
        ForeignKey("institution_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_admission_tasks_due", "status", "due_on", "id"),
        _allowed("status", TASK_STATUSES, "ck_admission_task_status"),
    )


class AdmissionStageHistory(Base):
    __tablename__ = "admission_stage_history"

    id = Column(Integer, primary_key=True)
    application_id = Column(
        Integer,
        ForeignKey("admission_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_stage = Column(String(20), nullable=True)
    to_stage = Column(String(20), nullable=False)
    reason = Column(String(1000), nullable=False, default="")
    actor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CampusLearnerProfile(Base):
    __tablename__ = "campus_learner_profiles"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id = Column(
        Integer,
        ForeignKey("institution_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    application_id = Column(
        Integer,
        ForeignKey("admission_applications.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    program_id = Column(
        Integer,
        ForeignKey("admission_programs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    intake_id = Column(
        Integer,
        ForeignKey("admission_intakes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    admission_number = Column(String(32), nullable=False)
    status = Column(String(20), nullable=False, default="enrolled", index=True)
    joined_on = Column(Date, nullable=False)
    expected_completion_on = Column(Date, nullable=True)
    completed_on = Column(Date, nullable=True)
    exit_reason = Column(String(1000), nullable=False, default="")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id", "member_id", name="uq_campus_learner_member"
        ),
        UniqueConstraint(
            "institution_id", "admission_number", name="uq_campus_admission_number"
        ),
        Index(
            "ix_campus_learner_intake_status",
            "institution_id",
            "intake_id",
            "status",
            "id",
        ),
        _allowed("status", LEARNER_STATUSES, "ck_campus_learner_status"),
        CheckConstraint("version > 0", name="ck_campus_learner_version"),
    )


class CampusLearnerLifecycleHistory(Base):
    __tablename__ = "campus_learner_lifecycle_history"

    id = Column(Integer, primary_key=True)
    learner_profile_id = Column(
        Integer,
        ForeignKey("campus_learner_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    reason = Column(String(1000), nullable=False, default="")
    effective_on = Column(Date, nullable=False)
    actor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
