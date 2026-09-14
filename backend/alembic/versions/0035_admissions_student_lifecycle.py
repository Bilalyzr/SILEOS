"""Add tenant admissions and student lifecycle records.

Revision ID: 0035
Revises: 0034
"""

from alembic import op
import sqlalchemy as sa
from app.core.migration_operations import idempotent_create_operations

op = idempotent_create_operations(op)


revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admission_programs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("code", sa.String(24), nullable=False),
        sa.Column("level", sa.String(30), nullable=False),
        sa.Column("department", sa.String(100), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("duration_months > 0", name="ck_admission_program_duration"),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_admission_program_status",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "code", name="uq_admission_program_code"),
    )
    op.create_index(
        "ix_admission_programs_institution_id", "admission_programs", ["institution_id"]
    )

    op.create_table(
        "admission_intakes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("academic_year", sa.String(32), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("closes_on", sa.Date(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("capacity > 0", name="ck_admission_intake_capacity"),
        sa.CheckConstraint("closes_on <= starts_on", name="ck_admission_intake_dates"),
        sa.CheckConstraint(
            "status IN ('draft', 'open', 'closed', 'archived')",
            name="ck_admission_intake_status",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], ["admission_programs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["institution_batches.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id",
            "program_id",
            "name",
            "academic_year",
            name="uq_admission_intake",
        ),
    )
    op.create_index(
        "ix_admission_intakes_institution_id", "admission_intakes", ["institution_id"]
    )
    op.create_index(
        "ix_admission_intakes_program_id", "admission_intakes", ["program_id"]
    )

    op.create_table(
        "admission_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("intake_id", sa.Integer(), nullable=False),
        sa.Column("application_number", sa.String(32), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("address", sa.String(1000), nullable=False),
        sa.Column("prior_institution", sa.String(160), nullable=False),
        sa.Column("source", sa.String(60), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("offer_status", sa.String(20), nullable=False),
        sa.Column("offer_expires_on", sa.Date(), nullable=True),
        sa.Column("offer_conditions", sa.String(4000), nullable=False),
        sa.Column("tuition_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("offer_currency", sa.String(3), nullable=False),
        sa.Column("offer_issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offer_responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_member_id", sa.Integer(), nullable=True),
        sa.Column("enrollment_member_id", sa.Integer(), nullable=True),
        sa.Column("invitation_id", sa.Integer(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("version > 0", name="ck_admission_application_version"),
        sa.CheckConstraint(
            "tuition_amount IS NULL OR tuition_amount >= 0", name="ck_admission_tuition"
        ),
        sa.CheckConstraint(
            "stage IN ('draft', 'submitted', 'screening', 'documents', 'assessment', "
            "'interview', 'decision', 'waitlisted', 'offered', 'admitted', 'rejected', "
            "'withdrawn', 'enrolled')",
            name="ck_admission_application_stage",
        ),
        sa.CheckConstraint(
            "offer_status IN ('none', 'draft', 'issued', 'accepted', 'declined', 'expired', 'revoked')",
            name="ck_admission_offer_status",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], ["admission_programs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["intake_id"], ["admission_intakes.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["owner_member_id"], ["institution_members.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_member_id"], ["institution_members.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["invitation_id"], ["institution_invites.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id",
            "application_number",
            name="uq_admission_application_number",
        ),
        sa.UniqueConstraint("enrollment_member_id"),
    )
    op.create_index(
        "ix_admission_applications_institution_id",
        "admission_applications",
        ["institution_id"],
    )
    op.create_index(
        "ix_admission_applications_program_id", "admission_applications", ["program_id"]
    )
    op.create_index(
        "ix_admission_applications_intake_id", "admission_applications", ["intake_id"]
    )
    op.create_index(
        "ix_admission_applications_email", "admission_applications", ["email"]
    )
    op.create_index(
        "ix_admission_applications_stage", "admission_applications", ["stage"]
    )
    op.create_index(
        "ix_admission_applications_offer_status",
        "admission_applications",
        ["offer_status"],
    )
    op.create_index(
        "ix_admission_applications_pipeline",
        "admission_applications",
        ["institution_id", "intake_id", "stage", "id"],
    )

    op.create_table(
        "admission_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=False),
        sa.Column("verified_by", sa.Integer(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'submitted', 'verified', 'rejected', 'waived')",
            name="ck_admission_document_status",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["admission_applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id", "label", name="uq_admission_document_label"
        ),
    )
    op.create_index(
        "ix_admission_documents_application_id",
        "admission_documents",
        ["application_id"],
    )

    op.create_table(
        "admission_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(4000), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["admission_applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admission_notes_application_id", "admission_notes", ["application_id"]
    )

    op.create_table(
        "admission_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("assignee_member_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'cancelled')",
            name="ck_admission_task_status",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["admission_applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["assignee_member_id"], ["institution_members.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admission_tasks_application_id", "admission_tasks", ["application_id"]
    )
    op.create_index("ix_admission_tasks_due_on", "admission_tasks", ["due_on"])
    op.create_index("ix_admission_tasks_status", "admission_tasks", ["status"])
    op.create_index(
        "ix_admission_tasks_due", "admission_tasks", ["status", "due_on", "id"]
    )

    op.create_table(
        "admission_stage_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("from_stage", sa.String(20), nullable=True),
        sa.Column("to_stage", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["admission_applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admission_stage_history_application_id",
        "admission_stage_history",
        ["application_id"],
    )

    op.create_table(
        "campus_learner_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=True),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("intake_id", sa.Integer(), nullable=False),
        sa.Column("admission_number", sa.String(32), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("joined_on", sa.Date(), nullable=False),
        sa.Column("expected_completion_on", sa.Date(), nullable=True),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column("exit_reason", sa.String(1000), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("version > 0", name="ck_campus_learner_version"),
        sa.CheckConstraint(
            "status IN ('enrolled', 'active', 'on_leave', 'completed', 'withdrawn', 'transferred')",
            name="ck_campus_learner_status",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["member_id"], ["institution_members.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["admission_applications.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], ["admission_programs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["intake_id"], ["admission_intakes.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id"),
        sa.UniqueConstraint(
            "institution_id", "member_id", name="uq_campus_learner_member"
        ),
        sa.UniqueConstraint(
            "institution_id", "admission_number", name="uq_campus_admission_number"
        ),
    )
    op.create_index(
        "ix_campus_learner_profiles_institution_id",
        "campus_learner_profiles",
        ["institution_id"],
    )
    op.create_index(
        "ix_campus_learner_profiles_intake_id", "campus_learner_profiles", ["intake_id"]
    )
    op.create_index(
        "ix_campus_learner_profiles_status", "campus_learner_profiles", ["status"]
    )
    op.create_index(
        "ix_campus_learner_intake_status",
        "campus_learner_profiles",
        ["institution_id", "intake_id", "status", "id"],
    )

    op.create_table(
        "campus_learner_lifecycle_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_profile_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["learner_profile_id"], ["campus_learner_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_campus_learner_lifecycle_history_profile",
        "campus_learner_lifecycle_history",
        ["learner_profile_id"],
    )


def downgrade():
    op.drop_index(
        "ix_campus_learner_lifecycle_history_profile",
        table_name="campus_learner_lifecycle_history",
    )
    op.drop_table("campus_learner_lifecycle_history")
    op.drop_index(
        "ix_campus_learner_intake_status", table_name="campus_learner_profiles"
    )
    op.drop_index(
        "ix_campus_learner_profiles_status", table_name="campus_learner_profiles"
    )
    op.drop_index(
        "ix_campus_learner_profiles_intake_id", table_name="campus_learner_profiles"
    )
    op.drop_index(
        "ix_campus_learner_profiles_institution_id",
        table_name="campus_learner_profiles",
    )
    op.drop_table("campus_learner_profiles")
    op.drop_index(
        "ix_admission_stage_history_application_id",
        table_name="admission_stage_history",
    )
    op.drop_table("admission_stage_history")
    op.drop_index("ix_admission_tasks_due", table_name="admission_tasks")
    op.drop_index("ix_admission_tasks_status", table_name="admission_tasks")
    op.drop_index("ix_admission_tasks_due_on", table_name="admission_tasks")
    op.drop_index("ix_admission_tasks_application_id", table_name="admission_tasks")
    op.drop_table("admission_tasks")
    op.drop_index("ix_admission_notes_application_id", table_name="admission_notes")
    op.drop_table("admission_notes")
    op.drop_index(
        "ix_admission_documents_application_id", table_name="admission_documents"
    )
    op.drop_table("admission_documents")
    op.drop_index(
        "ix_admission_applications_pipeline", table_name="admission_applications"
    )
    op.drop_index(
        "ix_admission_applications_offer_status", table_name="admission_applications"
    )
    op.drop_index(
        "ix_admission_applications_stage", table_name="admission_applications"
    )
    op.drop_index(
        "ix_admission_applications_email", table_name="admission_applications"
    )
    op.drop_index(
        "ix_admission_applications_intake_id", table_name="admission_applications"
    )
    op.drop_index(
        "ix_admission_applications_program_id", table_name="admission_applications"
    )
    op.drop_index(
        "ix_admission_applications_institution_id", table_name="admission_applications"
    )
    op.drop_table("admission_applications")
    op.drop_index("ix_admission_intakes_program_id", table_name="admission_intakes")
    op.drop_index("ix_admission_intakes_institution_id", table_name="admission_intakes")
    op.drop_table("admission_intakes")
    op.drop_index(
        "ix_admission_programs_institution_id", table_name="admission_programs"
    )
    op.drop_table("admission_programs")
