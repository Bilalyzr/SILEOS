"""Commands for Utporul coding challenge authoring and judge delivery."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Language = Literal["python", "javascript", "typescript", "java", "cpp", "c"]


class Command(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class TestCaseIn(Command):
    visibility: Literal["sample", "hidden"] = "hidden"
    input_text: str = Field(default="", max_length=100_000)
    expected_output: str = Field(max_length=100_000)
    comparison: Literal["exact", "trimmed", "tokens"] = "trimmed"
    weight: float = Field(default=1, gt=0, le=1000)


class ChallengeCreate(Command):
    title: str = Field(min_length=3, max_length=200)
    problem_statement: str = Field(min_length=10, max_length=30_000)
    input_format: str = Field(default="", max_length=5000)
    output_format: str = Field(default="", max_length=5000)
    constraints_text: str = Field(default="", max_length=5000)
    allowed_languages: list[Language] = Field(min_length=1, max_length=6)
    starter_code: dict[Language, str] = Field(default_factory=dict)
    time_limit_ms: int = Field(default=2000, ge=100, le=15000)
    memory_limit_mb: int = Field(default=256, ge=16, le=1024)
    max_source_bytes: int = Field(default=65536, ge=100, le=262144)
    max_attempts: int = Field(default=20, ge=1, le=500)
    test_cases: list[TestCaseIn] = Field(min_length=1, max_length=100)

    @field_validator("allowed_languages")
    @classmethod
    def unique_languages(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("allowed_languages must be unique")
        return value

    @field_validator("starter_code")
    @classmethod
    def starter_size(cls, value):
        if any(len(code.encode("utf-8")) > 100_000 for code in value.values()):
            raise ValueError("starter code is too large")
        return value


class ChallengeUpdate(ChallengeCreate):
    version: int = Field(gt=0)


class ChallengeAction(Command):
    action: Literal["publish", "retire"]
    version: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=500)


class SubmissionCreate(Command):
    language: Language
    source_code: str = Field(min_length=1, max_length=262144)
    idempotency_key: str = Field(min_length=8, max_length=100)


class JudgeClaim(Command):
    judge_version: str = Field(min_length=2, max_length=40)


class JudgeCaseResult(Command):
    test_case_id: int = Field(gt=0)
    status: Literal[
        "completed",
        "time_limit",
        "memory_limit",
        "runtime_error",
        "compile_error",
        "internal_error",
    ]
    actual_output: str = Field(default="", max_length=100_000)
    stderr: str = Field(default="", max_length=20_000)
    execution_ms: int = Field(default=0, ge=0, le=120_000)
    memory_kb: int = Field(default=0, ge=0, le=2_097_152)


class JudgeComplete(Command):
    lease_token: str = Field(min_length=16, max_length=80)
    results: list[JudgeCaseResult] = Field(min_length=1, max_length=100)


class JudgeFail(Command):
    lease_token: str = Field(min_length=16, max_length=80)
    error: str = Field(min_length=3, max_length=2000)
    retryable: bool = True
