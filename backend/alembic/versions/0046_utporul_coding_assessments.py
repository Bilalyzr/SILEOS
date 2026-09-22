"""Utporul coding challenges and isolated judge queue.

Revision ID: 0046
Revises: 0045
"""

from alembic import op
import sqlalchemy as sa

from app.core.migration_operations import idempotent_create_operations


revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None
op = idempotent_create_operations(op)


def upgrade():
    op.create_table(
        "coding_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column("input_format", sa.Text(), nullable=False, server_default=""),
        sa.Column("output_format", sa.Text(), nullable=False, server_default=""),
        sa.Column("constraints_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("allowed_languages", sa.JSON(), nullable=False),
        sa.Column("starter_code", sa.JSON(), nullable=False),
        sa.Column("time_limit_ms", sa.Integer(), nullable=False, server_default="2000"),
        sa.Column("memory_limit_mb", sa.Integer(), nullable=False, server_default="256"),
        sa.Column("max_source_bytes", sa.Integer(), nullable=False, server_default="65536"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('draft','published','retired')", name="ck_coding_challenge_status"),
        sa.CheckConstraint("time_limit_ms BETWEEN 100 AND 15000", name="ck_coding_challenge_time_limit"),
        sa.CheckConstraint("memory_limit_mb BETWEEN 16 AND 1024", name="ck_coding_challenge_memory_limit"),
        sa.CheckConstraint("max_source_bytes BETWEEN 100 AND 262144", name="ck_coding_challenge_source_limit"),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 500", name="ck_coding_challenge_attempts"),
        sa.CheckConstraint("version > 0", name="ck_coding_challenge_version"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_coding_challenges_course_id", "coding_challenges", ["course_id"])
    op.create_index("ix_coding_challenges_tenant_id", "coding_challenges", ["tenant_id"])
    op.create_index("ix_coding_challenges_slug", "coding_challenges", ["slug"], unique=True)
    op.create_index("ix_coding_challenges_status", "coding_challenges", ["status"])
    op.create_index("ix_coding_challenge_course_status", "coding_challenges", ["course_id", "status"])

    op.create_table(
        "coding_test_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("visibility", sa.String(12), nullable=False, server_default="hidden"),
        sa.Column("input_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("comparison", sa.String(20), nullable=False, server_default="trimmed"),
        sa.Column("weight", sa.Numeric(7, 3), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("ordinal > 0", name="ck_coding_test_case_ordinal"),
        sa.CheckConstraint("visibility IN ('sample','hidden')", name="ck_coding_test_case_visibility"),
        sa.CheckConstraint("comparison IN ('exact','trimmed','tokens')", name="ck_coding_test_case_comparison"),
        sa.CheckConstraint("weight > 0", name="ck_coding_test_case_weight"),
        sa.ForeignKeyConstraint(["challenge_id"], ["coding_challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge_id", "ordinal", name="uq_coding_test_case_order"),
    )
    op.create_index("ix_coding_test_cases_challenge_id", "coding_test_cases", ["challenge_id"])

    op.create_table(
        "coding_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(30), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("score", sa.Numeric(7, 3), nullable=False, server_default="0"),
        sa.Column("passed_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(40), nullable=False, server_default=""),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("judge_version", sa.String(40), nullable=False, server_default=""),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued','running','passed','failed','error','cancelled')", name="ck_coding_submission_status"),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_coding_submission_score"),
        sa.CheckConstraint("attempt_number > 0", name="ck_coding_submission_attempt_number"),
        sa.ForeignKeyConstraint(["challenge_id"], ["coding_challenges.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_coding_submission_idempotency"),
        sa.UniqueConstraint("challenge_id", "user_id", "attempt_number", name="uq_coding_submission_attempt"),
    )
    op.create_index("ix_coding_submissions_challenge_id", "coding_submissions", ["challenge_id"])
    op.create_index("ix_coding_submissions_user_id", "coding_submissions", ["user_id"])
    op.create_index("ix_coding_submissions_status", "coding_submissions", ["status"])
    op.create_index("ix_coding_submission_user_challenge", "coding_submissions", ["user_id", "challenge_id", "submitted_at"])

    op.create_table(
        "coding_case_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("test_case_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("actual_output", sa.Text(), nullable=False, server_default=""),
        sa.Column("stderr", sa.Text(), nullable=False, server_default=""),
        sa.Column("execution_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("memory_kb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_awarded", sa.Numeric(7, 3), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('passed','wrong_answer','time_limit','memory_limit','runtime_error','compile_error','internal_error')", name="ck_coding_case_result_status"),
        sa.CheckConstraint("execution_ms >= 0", name="ck_coding_case_result_time"),
        sa.CheckConstraint("memory_kb >= 0", name="ck_coding_case_result_memory"),
        sa.CheckConstraint("score_awarded >= 0", name="ck_coding_case_result_score"),
        sa.ForeignKeyConstraint(["submission_id"], ["coding_submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["coding_test_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", "test_case_id", name="uq_coding_case_result"),
    )
    op.create_index("ix_coding_case_results_submission_id", "coding_case_results", ["submission_id"])

    op.create_table(
        "coding_judge_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("lease_token", sa.String(80), nullable=False, server_default=""),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('queued','leased','completed','failed','cancelled')", name="ck_coding_judge_job_status"),
        sa.CheckConstraint("priority BETWEEN 0 AND 1000", name="ck_coding_judge_job_priority"),
        sa.CheckConstraint("attempts >= 0", name="ck_coding_judge_job_attempts"),
        sa.ForeignKeyConstraint(["submission_id"], ["coding_submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id"),
    )
    op.create_index("ix_coding_judge_jobs_status", "coding_judge_jobs", ["status"])
    op.create_index("ix_coding_judge_jobs_available_at", "coding_judge_jobs", ["available_at"])
    op.create_index("ix_coding_judge_jobs_lease_expires_at", "coding_judge_jobs", ["lease_expires_at"])
    op.create_index("ix_coding_judge_claim", "coding_judge_jobs", ["status", "available_at", "priority", "id"])


def downgrade():
    bind = op.get_bind()
    for table_name in (
        "coding_judge_jobs",
        "coding_case_results",
        "coding_submissions",
        "coding_test_cases",
        "coding_challenges",
    ):
        if sa.inspect(bind).has_table(table_name):
            op.drop_table(table_name)
