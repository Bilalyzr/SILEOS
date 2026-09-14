"""
Pydantic schemas for the assessment-integrity endpoints added in
docs/superpowers/plans/2026-09-02-learning-experience.md Task 1.

The quizzes/assignments routers historically take raw `dict` request bodies
rather than declared Pydantic models (see app/routers/quizzes.py,
app/routers/assignments.py) and this task deliberately keeps that
convention for the endpoints it modifies, to avoid a wide blast-radius
schema migration outside its scope. These schemas exist for the NEW
instructor grading endpoints where a typed body meaningfully documents the
contract; they are optional annotations, not currently wired as
`response_model`/body-type on the routers (which still accept `dict`).
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class QuizAnswerGradeRequest(BaseModel):
    """Body for POST /quiz-attempts/{attempt_id}/answers/{answer_id}/grade"""
    achieved_mark: float = Field(..., ge=0, description="Points awarded for this manually-graded answer")
    feedback: Optional[str] = Field(None, description="Optional instructor feedback for this answer")


class QuizAttemptFinalizeResponse(BaseModel):
    attempt_id: int
    attempt_status: str
    total_marks: float
    earned_marks: float
    percentage: float
    passed: bool
    passing_grade: int


class RubricCriterion(BaseModel):
    """One row of Assignment.rubric (spec A1.12) — lightweight, no DB table."""
    criterion: str
    max_points: float = Field(..., ge=0)


class RubricScoreEntry(BaseModel):
    """One row of AssignmentSubmission.rubric_scores."""
    criterion: str
    points_awarded: float = Field(..., ge=0)


class AssignmentGradeRequest(BaseModel):
    """Body for POST /submissions/{submission_id}/grade"""
    grade: Optional[float] = None
    feedback: Optional[str] = None
    rubricScores: Optional[List[RubricScoreEntry]] = None
