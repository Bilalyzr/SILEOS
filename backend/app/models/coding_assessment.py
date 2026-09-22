"""Utporul coding challenges, hidden tests, submissions, and judge queue."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


class CodingChallenge(Base):
    __tablename__ = "coding_challenges"

    id = Column(Integer, primary_key=True)
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id = Column(
        Integer,
        ForeignKey("platform_tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slug = Column(String(120), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    problem_statement = Column(Text, nullable=False)
    input_format = Column(Text, nullable=False, default="")
    output_format = Column(Text, nullable=False, default="")
    constraints_text = Column(Text, nullable=False, default="")
    allowed_languages = Column(JSON, nullable=False, default=list)
    starter_code = Column(JSON, nullable=False, default=dict)
    time_limit_ms = Column(Integer, nullable=False, default=2000)
    memory_limit_mb = Column(Integer, nullable=False, default=256)
    max_source_bytes = Column(Integer, nullable=False, default=65536)
    max_attempts = Column(Integer, nullable=False, default=20)
    status = Column(String(20), nullable=False, default="draft", index=True)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','published','retired')",
            name="ck_coding_challenge_status",
        ),
        CheckConstraint(
            "time_limit_ms BETWEEN 100 AND 15000",
            name="ck_coding_challenge_time_limit",
        ),
        CheckConstraint(
            "memory_limit_mb BETWEEN 16 AND 1024",
            name="ck_coding_challenge_memory_limit",
        ),
        CheckConstraint(
            "max_source_bytes BETWEEN 100 AND 262144",
            name="ck_coding_challenge_source_limit",
        ),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 500",
            name="ck_coding_challenge_attempts",
        ),
        CheckConstraint("version > 0", name="ck_coding_challenge_version"),
        Index("ix_coding_challenge_course_status", "course_id", "status"),
    )


class CodingTestCase(Base):
    __tablename__ = "coding_test_cases"

    id = Column(Integer, primary_key=True)
    challenge_id = Column(
        Integer,
        ForeignKey("coding_challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal = Column(Integer, nullable=False)
    visibility = Column(String(12), nullable=False, default="hidden")
    input_text = Column(Text, nullable=False, default="")
    expected_output = Column(Text, nullable=False)
    comparison = Column(String(20), nullable=False, default="trimmed")
    weight = Column(Numeric(7, 3), nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("challenge_id", "ordinal", name="uq_coding_test_case_order"),
        CheckConstraint("ordinal > 0", name="ck_coding_test_case_ordinal"),
        CheckConstraint(
            "visibility IN ('sample','hidden')",
            name="ck_coding_test_case_visibility",
        ),
        CheckConstraint(
            "comparison IN ('exact','trimmed','tokens')",
            name="ck_coding_test_case_comparison",
        ),
        CheckConstraint("weight > 0", name="ck_coding_test_case_weight"),
    )


class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id = Column(Integer, primary_key=True)
    challenge_id = Column(
        Integer,
        ForeignKey("coding_challenges.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    language = Column(String(30), nullable=False)
    source_code = Column(Text, nullable=False)
    source_sha256 = Column(String(64), nullable=False)
    idempotency_key = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="queued", index=True)
    score = Column(Numeric(7, 3), nullable=False, default=0)
    passed_cases = Column(Integer, nullable=False, default=0)
    total_cases = Column(Integer, nullable=False, default=0)
    error_code = Column(String(40), nullable=False, default="")
    attempt_number = Column(Integer, nullable=False)
    judge_version = Column(String(40), nullable=False, default="")
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_coding_submission_idempotency"),
        UniqueConstraint(
            "challenge_id", "user_id", "attempt_number", name="uq_coding_submission_attempt"
        ),
        CheckConstraint(
            "status IN ('queued','running','passed','failed','error','cancelled')",
            name="ck_coding_submission_status",
        ),
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_coding_submission_score"),
        CheckConstraint("attempt_number > 0", name="ck_coding_submission_attempt_number"),
        Index(
            "ix_coding_submission_user_challenge",
            "user_id",
            "challenge_id",
            "submitted_at",
        ),
    )


class CodingCaseResult(Base):
    __tablename__ = "coding_case_results"

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer,
        ForeignKey("coding_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id = Column(
        Integer,
        ForeignKey("coding_test_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(String(24), nullable=False)
    actual_output = Column(Text, nullable=False, default="")
    stderr = Column(Text, nullable=False, default="")
    execution_ms = Column(Integer, nullable=False, default=0)
    memory_kb = Column(Integer, nullable=False, default=0)
    score_awarded = Column(Numeric(7, 3), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("submission_id", "test_case_id", name="uq_coding_case_result"),
        CheckConstraint(
            "status IN ('passed','wrong_answer','time_limit','memory_limit','runtime_error','compile_error','internal_error')",
            name="ck_coding_case_result_status",
        ),
        CheckConstraint("execution_ms >= 0", name="ck_coding_case_result_time"),
        CheckConstraint("memory_kb >= 0", name="ck_coding_case_result_memory"),
        CheckConstraint("score_awarded >= 0", name="ck_coding_case_result_score"),
    )


class CodingJudgeJob(Base):
    __tablename__ = "coding_judge_jobs"

    id = Column(Integer, primary_key=True)
    submission_id = Column(
        Integer,
        ForeignKey("coding_submissions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status = Column(String(20), nullable=False, default="queued", index=True)
    priority = Column(Integer, nullable=False, default=100)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    lease_token = Column(String(80), nullable=False, default="")
    lease_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_error = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','leased','completed','failed','cancelled')",
            name="ck_coding_judge_job_status",
        ),
        CheckConstraint("priority BETWEEN 0 AND 1000", name="ck_coding_judge_job_priority"),
        CheckConstraint("attempts >= 0", name="ck_coding_judge_job_attempts"),
        Index("ix_coding_judge_claim", "status", "available_at", "priority", "id"),
    )
