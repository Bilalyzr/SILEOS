"""
Quiz Management Router - SashaInfinity LMS API
Handles quiz CRUD operations, questions, and attempts
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import json
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer, QuizAttempt, QuizAttemptAnswer
from app.models.course import Course
from app.services.auth_service import AuthService
from app.services.course_access import can_edit
from app.services.gamification_service import QUIZ_BONUS_THRESHOLD_PCT

router = APIRouter()
logger = logging.getLogger(__name__)

# Question types graded by an instructor rather than automatically (spec
# A1.1 — pending_review flow). Referenced by submit scoring, the pending-
# review list/grade/finalize endpoints, and the results breakdown.
MANUAL_GRADE_QUESTION_TYPES = ("essay", "open_ended")

# Feedback policy (spec R4). `quiz_feedback_mode` on the Quiz model is
# persisted verbatim when it's one of these; anything else (None/absent,
# or a legacy value like "default") normalizes to "reveal_immediate".
FEEDBACK_MODES = ("reveal_immediate", "reveal_after_due", "reveal_never")


def normalize_feedback_mode(value) -> str:
    return value if value in FEEDBACK_MODES else "reveal_immediate"


def _multi_select_answer_list(user_answer, max_len: Optional[int] = None):
    """Normalize a multi_select answer payload to a list, or None if it
    isn't one. Accepts a real JSON/Python list (the normal submit body
    shape), and also a JSON-array-shaped string — the per-answer save
    endpoint (`POST /quiz-attempts/{id}/answers`) stores `given_answer` as
    `str(given_answer)`, and the no-body `/submit` rehydration path reads
    that column straight back into the answers map, so a list submitted
    via that route arrives here as e.g. "[0, 2]" rather than a real list.
    Anything else (plain non-numeric strings, dicts, None) returns None so
    the caller scores the question wrong instead of crashing.

    `max_len` (the question's option count, when the caller has it) caps
    the accepted list length: a submission longer than the number of
    options can never be a valid index set anyway (even ignoring
    duplicates/out-of-range values), so an oversized payload — e.g. a
    20,000-element list — is rejected here (treated as invalid, same as
    any other malformed payload: scores 0, never raises) instead of being
    materialized and iterated downstream.
    """
    if isinstance(user_answer, list):
        parsed = user_answer
    elif isinstance(user_answer, str):
        try:
            parsed = json.loads(user_answer)
        except (TypeError, ValueError):
            return None
        if not isinstance(parsed, list):
            return None
    else:
        return None
    if max_len is not None and len(parsed) > max_len:
        return None
    return parsed


def _mc_answer_index(user_answer) -> int:
    """Cast a multiple-choice answer payload to an option index.

    Accepts whole integers however the client encoded them: JSON int,
    integer-valued float, or a numeric string like "2". Everything else
    returns -1 so the question scores WRONG rather than crashing the
    submit — non-numeric strings, and fractional numerics like 1.9 (JSON
    float or "1.9" string) which must never be silently truncated down
    to the integer below (int(1.9) == 1 would "select" option 1).
    """
    if isinstance(user_answer, bool):
        return -1
    if isinstance(user_answer, int):
        return user_answer
    if isinstance(user_answer, float):
        return int(user_answer) if user_answer.is_integer() else -1
    try:
        return int(str(user_answer).strip())
    except (TypeError, ValueError):
        return -1


# Question types accepted at authoring time (spec R7). `multi_select` is
# validated here already (full type support — persistence + scoring —
# lands in Task 4).
#
# `open_ended` is a legacy alias of `essay`: it is a live
# MANUAL_GRADE_QUESTION_TYPES member that the scoring, pending-review and
# results paths all handle, so rows with that type exist. Omitting it here
# made the validator reject any PUT that round-tripped such a question,
# i.e. an existing open_ended quiz could not be saved at all. It validates
# exactly like `essay` (no answer required).
QUESTION_TYPES = (
    "multiple_choice",
    "true_false",
    "short_answer",
    "essay",
    "open_ended",
    "fill_in_blank",
    "multi_select",
)


def _validation_error(code: str, message: str, index: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": code, "message": message, "index": index},
    )


def _is_strict_int(value) -> bool:
    """True only for an actual integer index — no coercion. Rejects bool
    (Python's bool is an int subclass), float (even integer-valued, e.g.
    1.0), and numeric strings (e.g. "1") so a payload like `"1"` or `1.9`
    can never silently pass as an in-range option index."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_questions(questions: list) -> None:
    """Server-side authoring validation (spec R7). Raises HTTPException(422)
    with a stable machine `code`, human `message`, and the 0-based `index`
    of the offending question on the FIRST rule violated. Callers must run
    this before performing ANY write — nothing may persist if any question
    in the payload is invalid.
    """
    if not isinstance(questions, list):
        raise _validation_error(
            "invalid_type", "questions must be a list", 0
        )

    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            raise _validation_error(
                "invalid_type", "question must be an object", index
            )

        q_type = question.get("type")
        if q_type not in QUESTION_TYPES:
            raise _validation_error(
                "invalid_type",
                f"question type must be one of {QUESTION_TYPES}",
                index,
            )

        # points: integer 1..1000 for ALL types.
        points = question.get("points")
        if points is None:
            raise _validation_error(
                "points_missing", "points is required", index
            )
        if not _is_strict_int(points) or not (1 <= points <= 1000):
            raise _validation_error(
                "points_out_of_range", "points must be an integer between 1 and 1000", index
            )

        if q_type in ("multiple_choice", "multi_select"):
            raw_options = question.get("options")
            if not isinstance(raw_options, list):
                raise _validation_error(
                    "too_few_options", "options must be a list of at least 2 entries", index
                )
            trimmed = []
            for option in raw_options:
                text = option.strip() if isinstance(option, str) else ""
                if not text:
                    raise _validation_error(
                        "empty_option", "options must not be empty", index
                    )
                trimmed.append(text)
            if len(trimmed) < 2:
                raise _validation_error(
                    "too_few_options", "at least 2 non-empty options are required", index
                )

            if q_type == "multiple_choice":
                correct_answer = question.get("correctAnswer")
                if not _is_strict_int(correct_answer):
                    raise _validation_error(
                        "correct_index_not_integer",
                        "correctAnswer must be an integer option index",
                        index,
                    )
                if not (0 <= correct_answer < len(trimmed)):
                    raise _validation_error(
                        "correct_index_out_of_range",
                        "correctAnswer must be a valid option index",
                        index,
                    )
            else:  # multi_select
                correct_answers = question.get("correctAnswers")
                if (
                    not isinstance(correct_answers, list)
                    or len(correct_answers) < 1
                    or not all(_is_strict_int(a) for a in correct_answers)
                    or not all(0 <= a < len(trimmed) for a in correct_answers)
                    or len(set(correct_answers)) != len(correct_answers)
                ):
                    raise _validation_error(
                        "multi_select_invalid",
                        "correctAnswers must be a list of at least 1 distinct, in-range option index",
                        index,
                    )

        elif q_type == "true_false":
            correct_answer = question.get("correctAnswer")
            if correct_answer not in ("true", "false"):
                raise _validation_error(
                    "true_false_invalid",
                    'correctAnswer must be "true" or "false"',
                    index,
                )

        elif q_type == "fill_in_blank":
            correct_answer = question.get("correctAnswer")
            text = correct_answer.strip() if isinstance(correct_answer, str) else ""
            if not text:
                raise _validation_error(
                    "fill_in_blank_empty", "correctAnswer must not be empty", index
                )
            if len(text) > 200:
                raise _validation_error(
                    "fill_in_blank_too_long", "correctAnswer must be 200 characters or fewer", index
                )

        # short_answer: correctAnswer optional (empty -> manual grade, R8).
        # essay: no answer required.


# -----------------------------------------------------------------------------
# Quiz question write helpers (spec R5/R6, audit A1/A6/B8)
# -----------------------------------------------------------------------------


def _json_column_dict(raw) -> dict:
    """Tolerant reader for a JSON column that may hold a real dict (what we
    write now) or a legacy double-encoded JSON string (what the old
    `json.dumps(...)`-into-a-JSON-column writers left behind — audit B8/F8).
    Anything unreadable degrades to `{}` rather than raising.

    Returns a SHALLOW COPY when `raw` is already a dict — never the live
    object backing the SQLAlchemy JSON column. Callers mutate the dict
    they get back and then reassign it to the column (`attempt.attempt_info
    = info`); if this returned the same object already sitting on the
    attribute, that reassignment would be a same-identity no-op that
    SQLAlchemy's change tracking can silently drop, leaving the mutation
    uncommitted (a real regression this fixed: pause/resume's `_pause`
    write wasn't taking effect).
    """
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _question_settings_payload(q_data: dict) -> dict:
    """The `question_settings` value for a question payload — a REAL dict,
    never a JSON string (F8: double-encoding silently lost `image_url` on
    read through the old bare-except path)."""
    return {"image_url": q_data.get("imageUrl", "")}


def _apply_question_fields(question: QuizQuestion, q_data: dict, order: int) -> None:
    """Patch an existing (or freshly constructed) question row from a
    validated payload entry. Never touches `question_id` — identity is
    preserved so `quiz_attempt_answers.question_id` references survive
    (spec R6)."""
    question.question_title = q_data.get("question", "")
    question.question_type = q_data.get("type", "multiple_choice")
    question.question_mark = q_data.get("points", 1)
    question.question_order = order
    question.answer_explanation = q_data.get("explanation", "")
    question.question_settings = _question_settings_payload(q_data)


def _build_answer_rows(question_id: int, q_data: dict) -> list:
    """The QuizQuestionAnswer rows for one validated question payload.

    Answer rows carry no external references (`quiz_attempt_answers` points
    at `question_id`, never `answer_id` — verified against models/quiz.py),
    so replacing them wholesale on an in-place question patch is safe.
    """
    q_type = q_data.get("type")
    rows = []

    if q_type == "multiple_choice" and q_data.get("options"):
        for opt_idx, option_text in enumerate(q_data["options"]):
            rows.append(QuizQuestionAnswer(
                belongs_question_id=question_id,
                belongs_question_type="multiple_choice",
                answer_title=option_text,
                is_correct=(opt_idx == q_data.get("correctAnswer")),
                answer_order=opt_idx,
            ))

    elif q_type == "multi_select" and q_data.get("options"):
        correct_set = set(q_data.get("correctAnswers") or [])
        for opt_idx, option_text in enumerate(q_data["options"]):
            rows.append(QuizQuestionAnswer(
                belongs_question_id=question_id,
                belongs_question_type="multi_select",
                answer_title=option_text,
                is_correct=(opt_idx in correct_set),
                answer_order=opt_idx,
            ))

    elif q_type == "true_false":
        correct_answer = q_data.get("correctAnswer", "true")
        for opt_text, opt_val in [("True", "true"), ("False", "false")]:
            rows.append(QuizQuestionAnswer(
                belongs_question_id=question_id,
                belongs_question_type="true_false",
                answer_title=opt_text,
                is_correct=(opt_val == correct_answer),
                answer_order=0 if opt_val == "true" else 1,
            ))

    elif q_type == "fill_in_blank":
        correct_answer = str(q_data.get("correctAnswer", "")).strip()
        if correct_answer:
            rows.append(QuizQuestionAnswer(
                belongs_question_id=question_id,
                belongs_question_type="fill_in_blank",
                answer_title=correct_answer,
                is_correct=True,
                answer_order=0,
            ))

    return rows



def _not_retired():
    """R8: retired questions (NULL on legacy rows) never enter new attempts."""
    from sqlalchemy import or_
    return or_(QuizQuestion.is_retired.is_(None), QuizQuestion.is_retired.is_(False))


def _parse_window(value, field_name="date/time"):
    """ISO string / '' / None -> aware datetime or None (422 on garbage).

    A *close* time in the past is rejected: a quiz that already closed can
    never be attempted, and silently saving one publishes a dead window.
    Open times may be in the past (a quiz that is already open is valid)."""
    if value in (None, "", 0):
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid {field_name}: {value!r}")
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if field_name == "quiz_available_until":
        if dt < datetime.now(dt.tzinfo) - timedelta(minutes=5):
            raise HTTPException(
                status_code=422,
                detail="Close time cannot be in the past.",
            )
    return dt


def _iso(dt):
    return dt.isoformat() if dt else None

@router.get("/quizzes/{quiz_id}")
async def get_quiz_basic(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get basic quiz info (just course_id for navigation)
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    return {
        "id": quiz.id,
        "course_id": quiz.post_parent,
        "title": quiz.post_title
    }


@router.post("/courses/{course_id}/quizzes")
async def create_quiz(
    course_id: int,
    quiz_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Create a new quiz for a course
    """
    # Verify course exists and user has permission
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add quizzes to this course"
        )

    # Validate ALL questions before any write (spec R7) — nothing persists
    # if any question in the payload is invalid.
    _validate_questions(quiz_data.get("questions", []))

    # Scored interactive modules (H5P/Game) — validated before write:
    # must exist and belong to the caller (or admin). Their results
    # (h5p_results / game_results) feed the cumulative grade.
    # ScorableItem contract (v2.0 §5): every module normalised with derived
    # max_score + universal fields; graded items above T4 block publication.
    from app.schemas.scorable import assert_publishable, normalize_scorable_items
    validated_modules = normalize_scorable_items(db, quiz_data.get("interactive_modules"), current_user)
    assert_publishable(validated_modules)

    # Create quiz
    new_quiz = Quiz(
        post_author=current_user.id,
        post_title=quiz_data.get("title", "Untitled Quiz"),
        post_content=quiz_data.get("description", ""),
        post_excerpt=quiz_data.get("description", "")[:200],
        post_status="publish",
        post_parent=course_id,
        quiz_time_limit=quiz_data.get("timeLimit", 0),
        quiz_passing_grade=quiz_data.get("passingScore", 70),
        quiz_max_attempts_allowed=quiz_data.get("maxAttempts", 0),
        quiz_questions_order=quiz_data.get("randomizeQuestions", False) and "rand" or "asc",
        quiz_max_questions_for_take=int(quiz_data.get("maxQuestionsForTake") or 0),
        quiz_available_from=_parse_window(quiz_data.get("availableFrom")),
        quiz_available_until=_parse_window(quiz_data.get("availableUntil"), field_name="quiz_available_until"),
        quiz_feedback_mode=normalize_feedback_mode(quiz_data.get("feedbackMode")),
        interactive_modules=validated_modules,
    )

    # Single transaction (spec R5): the quiz row, every question and every
    # answer are written under ONE commit at the end. A failure anywhere —
    # including partway through the question loop — rolls the whole thing
    # back, so a create can never leave a published quiz with 0..k
    # questions (audit A6).
    questions_data = quiz_data.get("questions", [])
    try:
        db.add(new_quiz)
        db.flush()  # assigns new_quiz.id without committing

        for idx, q_data in enumerate(questions_data):
            question = QuizQuestion(quiz_id=new_quiz.id)
            _apply_question_fields(question, q_data, idx)
            db.add(question)
            db.flush()  # assigns question.question_id without committing

            for answer in _build_answer_rows(question.question_id, q_data):
                db.add(answer)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "id": new_quiz.id,
        "interactive_modules": new_quiz.interactive_modules or [],
        "message": "Quiz created successfully"
    }


@router.post("/quizzes/{quiz_id}/questions")
async def add_question_to_quiz(
    quiz_id: int,
    question_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Add a question to an existing quiz
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    # Verify permission
    course = db.query(Course).filter(Course.id == quiz.post_parent).first()
    if course and not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this quiz"
        )

    # Parse question_options BEFORE any write — malformed JSON must 422,
    # not silently persist an unscorable question (audit A7).
    q_type = question_data.get("question_type", "multiple_choice")
    options_str = question_data.get("question_options", "")
    options = []
    correct_answer = 0
    correct_answers = None
    if options_str:
        try:
            options_data = json.loads(options_str)
        except json.JSONDecodeError:
            raise _validation_error(
                "invalid_type", "question_options must be valid JSON", 0
            )
        if not isinstance(options_data, dict):
            raise _validation_error(
                "invalid_type", "question_options must be a JSON object", 0
            )
        options = options_data.get("options", [])
        correct_answer = options_data.get("correct_answer", 0)
        correct_answers = options_data.get("correct_answers")

    # Normalize this endpoint's flat payload into the same canonical
    # question dict create_quiz/update_quiz use, so validation AND the write
    # go through one shared path (no third divergent question writer).
    canonical = {
        "type": q_type,
        "question": question_data.get("question_title", ""),
        "points": question_data.get("question_mark", 1),
        "explanation": question_data.get("answer_explanation", ""),
        "imageUrl": _json_column_dict(
            question_data.get("question_settings")
        ).get("image_url", ""),
        "options": options,
        "correctAnswer": correct_answer,
        "correctAnswers": correct_answers,
    }
    if q_type == "true_false":
        canonical["correctAnswer"] = question_data.get("correctAnswer", correct_answer)
    elif q_type == "fill_in_blank":
        canonical["correctAnswer"] = question_data.get("correctAnswer", "")

    # Validate identically to create_quiz/update_quiz (spec R7) — nothing
    # persists if it's invalid.
    _validate_questions([canonical])

    # Single transaction (spec R5), same as create/update.
    try:
        question = QuizQuestion(quiz_id=quiz_id)
        _apply_question_fields(
            question, canonical, question_data.get("question_order", 0)
        )
        db.add(question)
        db.flush()  # assigns question_id without committing

        for answer in _build_answer_rows(question.question_id, canonical):
            db.add(answer)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "id": question.question_id,
        "message": "Question added successfully"
    }


# NOTE: this literal-path route MUST be registered before
# `/courses/{course_id}/quizzes/{quiz_id}` below — FastAPI raises a 422 on
# `quiz_id: int` failing to parse "pending-reviews" rather than falling
# through to a later route, so registration order decides the match.
@router.get("/courses/{course_id}/quizzes/pending-reviews")
async def list_pending_review_attempts(
    course_id: int,
    quiz_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """
    List quiz attempts in `pending_review` for this course (optionally
    narrowed to one quiz). Course-owner/admin only.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view grading for this course"
        )

    query = db.query(QuizAttempt).filter(
        QuizAttempt.course_id == course_id,
        QuizAttempt.attempt_status == "pending_review",
    )
    if quiz_id is not None:
        query = query.filter(QuizAttempt.quiz_id == quiz_id)
    attempts = query.order_by(QuizAttempt.attempt_started_at.asc()).all()

    result = []
    for attempt in attempts:
        quiz_row = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
        student = db.query(User).filter(User.id == attempt.user_id).first()
        manual_answers = db.query(QuizAttemptAnswer).join(
            QuizQuestion, QuizAttemptAnswer.question_id == QuizQuestion.question_id
        ).filter(
            QuizAttemptAnswer.quiz_attempt_id == attempt.attempt_id,
            QuizQuestion.question_type.in_(MANUAL_GRADE_QUESTION_TYPES),
        ).all()
        graded_ids = set((_attempt_info_dict(attempt).get("_graded_answers")) or [])
        pending_answer_ids = [
            a.attempt_answer_id for a in manual_answers
            if a.attempt_answer_id not in graded_ids
        ]
        result.append({
            "attempt_id": attempt.attempt_id,
            "quiz_id": attempt.quiz_id,
            "quiz_title": quiz_row.post_title if quiz_row else None,
            "course_id": course_id,
            "user_id": attempt.user_id,
            "student_name": student.display_name if student else "Unknown",
            "student_email": student.user_email if student else None,
            "attempt_started_at": attempt.attempt_started_at.isoformat() if attempt.attempt_started_at else None,
            "manual_answer_count": len(manual_answers),
            "manual_answer_ids": [a.attempt_answer_id for a in manual_answers],
            "ungraded_answer_ids": pending_answer_ids,
        })

    return {"pending_reviews": result, "count": len(result)}


@router.get("/courses/{course_id}/quizzes/{quiz_id}")
async def get_quiz(
    course_id: int,
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get quiz details with questions. `correctAnswer`/`explanation` are only
    included for the course owner or an admin — students get sanitized
    questions (they fetch correct answers post-submit via the results
    endpoint, which already gates on submission status).
    """
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        Quiz.post_parent == course_id
    ).first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    can_see_answers = current_user.role == "admin" or (
        course is not None and course.post_author == current_user.id
    )

    # Get questions with answers. Tiebreak on question_id so ordering is
    # deterministic when multiple questions share the same question_order
    # (matches update_quiz's ordering, which existing_questions[idx] relies
    # on for R6 identity-preserving PATCH-in-place).
    questions = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id,
        _not_retired(),
    ).order_by(QuizQuestion.question_order, QuizQuestion.question_id).all()

    questions_data = []
    for question in questions:
        answers = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).order_by(QuizQuestionAnswer.answer_order).all()

        question_dict = {
            "id": str(question.question_id),
            "type": question.question_type,
            "question": question.question_title,
            "points": float(question.question_mark),
        }
        if can_see_answers:
            question_dict["explanation"] = question.answer_explanation

        # Parse settings — tolerant of both the real dict we write now and
        # legacy double-encoded JSON strings (audit B8/F8; the old bare
        # `except` here silently dropped image_url on every read).
        question_dict["imageUrl"] = _json_column_dict(
            question.question_settings
        ).get("image_url", "")

        # Add options for multiple choice (option text itself is not
        # sensitive — only which one is correct is gated)
        if question.question_type == "multiple_choice":
            question_dict["options"] = [ans.answer_title for ans in answers]
            if can_see_answers:
                for idx, ans in enumerate(answers):
                    if ans.is_correct:
                        question_dict["correctAnswer"] = idx
                        break

        # Add options for multi_select (option text itself is not sensitive
        # — only which ones are correct is gated, same posture as MCQ)
        elif question.question_type == "multi_select":
            question_dict["options"] = [ans.answer_title for ans in answers]
            if can_see_answers:
                question_dict["correctAnswers"] = [
                    idx for idx, ans in enumerate(answers) if ans.is_correct
                ]

        # Add correct answer for true/false
        elif question.question_type == "true_false":
            if can_see_answers:
                for ans in answers:
                    if ans.is_correct:
                        question_dict["correctAnswer"] = ans.answer_title.lower()
                        break

        # Add correct answer for fill_in_blank, short_answer, essay
        elif question.question_type in ("fill_in_blank", "short_answer", "essay"):
            if can_see_answers:
                for ans in answers:
                    if ans.is_correct:
                        question_dict["correctAnswer"] = ans.answer_title
                        break

        questions_data.append(question_dict)

    return {
        "id": quiz.id,
        "title": quiz.post_title,
        "description": quiz.post_content,
        "timeLimit": quiz.quiz_time_limit,
        "passingScore": quiz.quiz_passing_grade,
        "maxAttempts": quiz.quiz_max_attempts_allowed,
        "randomizeQuestions": quiz.quiz_questions_order == "rand",
        "maxQuestionsForTake": int(quiz.quiz_max_questions_for_take or 0),
        "availableFrom": _iso(quiz.quiz_available_from),
        "availableUntil": _iso(quiz.quiz_available_until),
        "showCorrectAnswers": can_see_answers,
        "feedbackMode": normalize_feedback_mode(quiz.quiz_feedback_mode),
        "interactive_modules": (quiz.interactive_modules or []),

        "questions": questions_data
    }


@router.put("/courses/{course_id}/quizzes/{quiz_id}")
async def update_quiz(
    course_id: int,
    quiz_id: int,
    quiz_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Update an existing quiz
    """
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        Quiz.post_parent == course_id
    ).first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    # Check permission
    course = db.query(Course).filter(Course.id == course_id).first()
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this quiz"
        )

    # ABSENT-KEY RULE (audit A1): "questions" missing from the payload means
    # "don't touch the question bank" — only quiz metadata is updated. The
    # curriculum tab's duration-only PUT ({"timeLimit": 45}) used to fall
    # through to `.get("questions", [])` -> [] and silently delete every
    # question. An explicitly-present "questions": [] is still an explicit
    # request to remove them all (subject to the attempts check below).
    #
    # `None` is ALSO treated as absent/untouched (a client sending
    # {"questions": null} alongside other metadata fields must not wipe the
    # bank either — same bug class). Any other present-but-non-list value
    # ({}, "", 0, "abc", ...) is a genuine malformed payload and must 422
    # via _validate_questions rather than being silently coerced to [] and
    # then deleting every question (review finding — probed: 3 questions ->
    # 0 with {"questions": null} before this fix).
    questions_provided = "questions" in quiz_data and quiz_data.get("questions") is not None
    questions_data = quiz_data.get("questions") if questions_provided else []

    # Validate ALL questions before any write (spec R7) — nothing changes
    # if any question in the payload is invalid. This also catches a
    # present-but-non-list "questions" value (e.g. {}, "", 0, "abc") with a
    # clean 422 instead of silently wiping the bank.
    if questions_provided:
        _validate_questions(questions_data)

    # Existing questions in position order — the identity anchor for R6.
    existing_questions = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id
    ).order_by(QuizQuestion.question_order, QuizQuestion.question_id).all()

    # Questions beyond the incoming count would be DELETED. That is only
    # allowed while the quiz has zero attempts — otherwise the delete would
    # orphan `quiz_attempt_answers.question_id` rows (spec R6). Refuse the
    # whole request with 409 and write NOTHING; the check runs before any
    # mutation so `quiz` is still clean when we raise.
    if questions_provided and len(questions_data) < len(existing_questions):
        doomed = existing_questions[len(questions_data):]
        has_attempts = db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz_id
        ).count() > 0
        if has_attempts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "question_has_attempts",
                    "message": (
                        "This quiz has student attempts, so its questions cannot be "
                        "removed — removing them would orphan recorded answers. You "
                        "can still edit existing questions and add new ones."
                    ),
                    "blocked_question_ids": [q.question_id for q in doomed],
                    "removable_question_ids": [],
                },
            )

    # Single transaction (spec R5): metadata, question patches, inserts and
    # deletes all land under ONE commit at the end; any failure rolls the
    # whole edit back (audit A6 — the old per-question commit could leave a
    # gutted quiz behind).
    try:
        # Update quiz settings
        quiz.post_title = quiz_data.get("title", quiz.post_title)
        quiz.post_content = quiz_data.get("description", quiz.post_content)
        quiz.quiz_time_limit = quiz_data.get("timeLimit", quiz.quiz_time_limit)
        quiz.quiz_passing_grade = quiz_data.get("passingScore", quiz.quiz_passing_grade)
        quiz.quiz_max_attempts_allowed = quiz_data.get("maxAttempts", quiz.quiz_max_attempts_allowed)
        quiz.quiz_questions_order = "rand" if quiz_data.get("randomizeQuestions", False) else "asc"
        if "maxQuestionsForTake" in quiz_data:
            quiz.quiz_max_questions_for_take = int(quiz_data.get("maxQuestionsForTake") or 0)
        if "availableFrom" in quiz_data:
            quiz.quiz_available_from = _parse_window(quiz_data.get("availableFrom"))
        if "availableUntil" in quiz_data:
            quiz.quiz_available_until = _parse_window(quiz_data.get("availableUntil"), field_name="quiz_available_until")
        # Preserve-on-absent: only touch the feedback policy when the caller
        # actually sent `feedbackMode`. A PUT that omits the key must not
        # silently reset an existing policy back to the default (same
        # absent-key bug class as the question-wipe issue).
        if "feedbackMode" in quiz_data:
            quiz.quiz_feedback_mode = normalize_feedback_mode(quiz_data["feedbackMode"])
        if "interactive_modules" in quiz_data:
            from app.schemas.scorable import assert_publishable, normalize_scorable_items
            validated_modules = normalize_scorable_items(db, quiz_data.get("interactive_modules"), current_user)
            assert_publishable(validated_modules)
            quiz.interactive_modules = validated_modules

        # Apply the question set when provided (R6: identity preserved —
        # in-place patch for existing positions, insert beyond, delete the
        # tail; the 409 attempts-guard above already vetted any deletion).
        if questions_provided:
            for idx, q_data in enumerate(questions_data):
                if idx < len(existing_questions):
                    # PATCH IN PLACE (R6): the row keeps its question_id, so
                    # historical quiz_attempt_answers still resolve. Answer
                    # rows are replaced wholesale — nothing references
                    # answer_id (verified against models/quiz.py).
                    question = existing_questions[idx]
                    _apply_question_fields(question, q_data, idx)
                    db.query(QuizQuestionAnswer).filter(
                        QuizQuestionAnswer.belongs_question_id == question.question_id
                    ).delete(synchronize_session=False)
                    question_id = question.question_id
                else:
                    # INSERT: incoming questions beyond the existing count
                    # get brand-new ids.
                    question = QuizQuestion(quiz_id=quiz.id)
                    _apply_question_fields(question, q_data, idx)
                    db.add(question)
                    db.flush()  # assigns question_id without committing
                    question_id = question.question_id

                for answer in _build_answer_rows(question_id, q_data):
                    db.add(answer)

            # DELETE the tail: existing questions beyond the incoming count
            # (only reachable when the 409 guard above allowed it).
            for doomed_q in existing_questions[len(questions_data):]:
                db.delete(doomed_q)

        db.commit()
        db.refresh(quiz)
    except Exception:
        db.rollback()
        raise

    return {
        "interactive_modules": quiz.interactive_modules or [],
        "id": quiz.id,
        "message": "Quiz updated successfully"
    }


@router.delete("/courses/{course_id}/quizzes/{quiz_id}")
async def delete_quiz(
    course_id: int,
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Delete a quiz
    """
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        Quiz.post_parent == course_id
    ).first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    # Check permission
    course = db.query(Course).filter(Course.id == course_id).first()
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this quiz"
        )

    # Delete quiz attempts first (foreign key constraint)
    from app.models.quiz import QuizAttempt, QuizAttemptAnswer
    attempts = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id).all()
    for attempt in attempts:
        db.query(QuizAttemptAnswer).filter(QuizAttemptAnswer.quiz_attempt_id == attempt.attempt_id).delete()
        db.delete(attempt)

    # Delete questions and answers
    questions = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id,
        _not_retired(),
    ).all()

    for question in questions:
        db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).delete()
        db.delete(question)

    db.delete(quiz)
    db.commit()

    return {"message": "Quiz deleted successfully"}


async def _submit_quiz_impl(
    course_id: int,
    quiz_id: int,
    submission_data: dict,
    db: Session,
    current_user: User,
    existing_attempt: QuizAttempt = None,
):
    """
    Submit quiz answers and record attempt. Plain (non-route) function —
    see `submit_quiz` and `submit_quiz_attempt` below for the two routes
    that call it, so `existing_attempt` never becomes a FastAPI request
    parameter (Pydantic can't build a request-body field for a SQLAlchemy
    model).

    `existing_attempt` is set only when called from `submit_quiz_attempt`
    (the attempt-scoped path) with a real, previously `/start`-ed
    QuizAttempt row: in that case the server-side timer/pause checks apply
    and THAT row is updated in place (rather than creating a second,
    orphaned attempt row). When called from the canonical route directly
    (no prior /start — the path used by older/simpler clients and existing
    tests), there is no known start time to check a deadline against, so
    the timer is skipped and a fresh already-ended attempt is created,
    matching the long-standing behaviour.
    """
    from app.models.enrollment import Enrollment

    # Check if user is enrolled OR is the course author/admin
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == current_user.id
    ).first()

    # Allow course author and admins to take quizzes without enrollment
    course_check = db.query(Course).filter(Course.id == course_id).first()
    is_owner_or_admin = course_check and (
        course_check.post_author == current_user.id or
        current_user.role == "admin"
    )

    if not enrollment and not is_owner_or_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enrolled in this course"
        )

    # Get quiz
    quiz = db.query(Quiz).filter(
        Quiz.id == quiz_id,
        Quiz.post_parent == course_id
    ).first()

    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    # Route the canonical (no-attempt_id-in-URL) call through the caller's
    # own OPEN attempt when one exists (review finding C1): without this,
    # a client could always hit this route directly to bypass the
    # attempt-scoped timer/limit/pause checks entirely — submit_quiz_attempt
    # is not the only path into this scoring logic, so the guards have to
    # live here regardless of which route found the attempt. "Open" means
    # attempt_started OR pending_review; a fresh row is only ever created
    # when the caller truly has no open attempt (preserves the legacy
    # submit-without-/start tests, which never create one).
    if existing_attempt is None:
        existing_attempt = db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.course_id == course_id,
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.attempt_status.in_(["attempt_started", "pending_review"]),
        ).order_by(QuizAttempt.attempt_started_at.desc()).first()

    # A pending_review attempt is awaiting instructor grading — it cannot
    # be resubmitted over (review finding C1). Finalizing it is the
    # instructor's /finalize endpoint, not another submit.
    if existing_attempt is not None and existing_attempt.attempt_status == "pending_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This attempt is awaiting instructor review and cannot be resubmitted"
        )

    # Enforce quiz_max_attempts_allowed exactly like start_quiz_attempt:
    # count prior ended-or-pending attempts for this user+quiz+course
    # (review finding C1 — pending_review must count too, or a student
    # could rack up unlimited pending_review rows past max_attempts by
    # always including a manual question); 0 = unlimited. An
    # existing_attempt being finalized doesn't count against itself.
    if quiz.quiz_max_attempts_allowed and quiz.quiz_max_attempts_allowed > 0:
        prior_count_query = db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.course_id == course_id,
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.attempt_status.in_(["attempt_ended", "pending_review"]),
        )
        if existing_attempt is not None:
            prior_count_query = prior_count_query.filter(
                QuizAttempt.attempt_id != existing_attempt.attempt_id
            )
        if prior_count_query.count() >= quiz.quiz_max_attempts_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Maximum attempts reached"
            )

    # Pause must be explicitly resumed before submitting (review finding
    # I3) — otherwise pausing indefinitely extends the deadline (pause time
    # is added to the timer budget) into unlimited free thinking time with
    # the clock visibly stopped client-side.
    if existing_attempt is not None:
        info_for_pause = _attempt_info_dict(existing_attempt)
        if _is_paused(info_for_pause):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attempt is paused — resume before submitting"
            )

    # Server-side timer (spec A1.3): only enforceable when we know a real
    # start time — i.e. there's an open attempt (found above, or passed in
    # by submit_quiz_attempt) being finalized. quiz_time_limit == 0 means
    # unlimited (never rejected). A client-side call to the canonical route
    # made directly (truly no open attempt anywhere) still has no known
    # start time and can't be timed — matches long-standing behaviour for
    # the legacy submit-without-/start tests.
    is_late_submission = False
    if existing_attempt is not None and quiz.quiz_time_limit and quiz.quiz_time_limit > 0:
        started_at = _as_utc(existing_attempt.attempt_started_at)
        info_for_timer = _attempt_info_dict(existing_attempt)
        pause_seconds = _accumulated_pause_seconds(info_for_timer)
        deadline = started_at + timedelta(minutes=quiz.quiz_time_limit) \
            + timedelta(seconds=SUBMIT_GRACE_SECONDS + pause_seconds)
        now = datetime.now(timezone.utc)
        if now > deadline:
            # Review finding C2: a hard 409 here left the attempt wedged
            # forever in attempt_started (/start would just keep resuming
            # the same expired attempt — no way out). Instead, score and
            # end the attempt using ONLY whatever answers were already
            # saved server-side before the deadline (attempt_info /
            # quiz_attempt_answers as they stand right now) — the
            # late-arriving submission body's answers are discarded, not
            # merged in, since accepting them would let a client simply
            # keep the late request's payload and defeat the timer. The
            # response is 200 with late_submission:true and whatever score
            # those already-saved answers earn.
            is_late_submission = True
            submission_data = {"answers": {
                k: v for k, v in info_for_timer.items() if not str(k).startswith("_")
            }}

    # Get questions and validate answers
    questions = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id,
        _not_retired(),
    ).all()
    # Roadmap item 5: an attempt that drew a random subset is graded on that subset only
    _subset = None
    if existing_attempt is not None:
        _subset = (_attempt_info_dict(existing_attempt) or {}).get("_question_ids")
    if _subset:
        _allowed = {int(x) for x in _subset}
        questions = [q for q in questions if q.question_id in _allowed]

    total_marks = 0
    earned_marks = 0
    # Review finding M2: strip any client-submitted answer key that starts
    # with "_" at the source — those names are reserved for internal
    # attempt_info bookkeeping (_pause, _graded_answers, _manual_feedback)
    # and must never be settable by a student's answer payload.
    raw_answers_data = submission_data.get("answers", {}) or {}
    answers_data = {
        k: v for k, v in raw_answers_data.items() if not str(k).startswith("_")
    }
    has_manual_question = False
    per_question_results = {}  # question_id(str) -> {is_correct, achieved_mark, needs_review}

    for question in questions:
        q_mark = float(question.question_mark)
        total_marks += q_mark

        user_answer = answers_data.get(str(question.question_id))

        if question.question_type in MANUAL_GRADE_QUESTION_TYPES:
            has_manual_question = True
            per_question_results[str(question.question_id)] = {
                "is_correct": False,
                "achieved_mark": 0.0,
                "needs_review": True,
            }
            continue

        if user_answer is None:
            continue

        # Get correct answer
        correct_answers = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id,
            QuizQuestionAnswer.is_correct == True
        ).all()

        # Full answer set (ordered) — shared by multiple_choice (index
        # lookup) and multi_select (set-equality scoring).
        all_answers = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).order_by(QuizQuestionAnswer.answer_order).all()

        is_correct = False
        if question.question_type == "multiple_choice":
            # user_answer is the option index, but clients may send it as a
            # string or as an arbitrary non-numeric payload. Only whole
            # integers select an option (see _mc_answer_index); anything
            # else — including a fractional numeric like 1.9 — must score
            # the question wrong, not blow up the submit with a 500 and
            # not be truncated to the option at the integer below.
            answer_index = _mc_answer_index(user_answer)
            if 0 <= answer_index < len(all_answers) and all_answers[answer_index].is_correct:
                is_correct = True
        elif question.question_type == "multi_select":
            # user_answer must be a list of option indices (ints or numeric
            # strings, per _mc_answer_index); a non-list payload, or any
            # element that doesn't resolve to a valid index, scores wrong
            # rather than crashing. Duplicates collapse via set(); v1 has
            # NO partial credit (spec §5) — full marks iff the submitted
            # set equals the correct set exactly, else 0.
            picked = _multi_select_answer_list(user_answer, max_len=len(all_answers))
            if picked is not None:
                picked_indices = {_mc_answer_index(a) for a in picked}
                if all(0 <= i < len(all_answers) for i in picked_indices):
                    correct_set = {
                        idx for idx, a in enumerate(all_answers) if a.is_correct
                    }
                    is_correct = picked_indices == correct_set
        elif question.question_type == "true_false":
            # user_answer is "true" or "false"
            for ans in correct_answers:
                if ans.answer_title.lower() == str(user_answer).lower():
                    is_correct = True
                    break

        elif question.question_type in ("fill_in_blank", "short_answer"):
            for ans in correct_answers:
                if str(ans.answer_title).strip().lower() == str(user_answer).strip().lower():
                    is_correct = True
                    break

        achieved = q_mark if is_correct else 0.0
        if is_correct:
            earned_marks += q_mark
        per_question_results[str(question.question_id)] = {
            "is_correct": is_correct,
            "achieved_mark": achieved,
            "needs_review": False,
        }

    # Calculate percentage (auto-graded portion only when pending_review —
    # the percentage/passed verdict is provisional until finalize).
    percentage = (earned_marks / total_marks * 100) if total_marks > 0 else 0
    final_status = "pending_review" if has_manual_question else "attempt_ended"
    now_ts = datetime.now(timezone.utc)

    if existing_attempt is not None:
        # Finalize the real started attempt in place instead of creating an
        # orphaned duplicate row.
        attempt = existing_attempt
        attempt.total_questions = len(questions)
        attempt.total_answered_questions = len([k for k in answers_data if not str(k).startswith("_")])
        attempt.total_marks = total_marks
        attempt.earned_marks = earned_marks
        info = _attempt_info_dict(attempt)
        # Preserve internal bookkeeping keys (e.g. _pause, _graded_answers)
        # already stored; merge in the submitted answers. `answers_data` was
        # already stripped of underscore-prefixed keys above (review
        # finding M2), so this can never clobber a bookkeeping key.
        info.update(answers_data)
        attempt.attempt_info = info
        attempt.attempt_status = final_status
        attempt.attempt_ended_at = now_ts if final_status == "attempt_ended" else None
    else:
        # Direct-call path (no prior /start): create a fresh, already-ended
        # (or pending_review) attempt row — matches long-standing behaviour.
        attempt = QuizAttempt(
            user_id=current_user.id,
            quiz_id=quiz_id,
            course_id=course_id,
            total_questions=len(questions),
            total_answered_questions=len(answers_data),
            total_marks=total_marks,
            earned_marks=earned_marks,
            attempt_info=answers_data,
            attempt_status=final_status,
            attempt_started_at=now_ts,
            attempt_ended_at=now_ts if final_status == "attempt_ended" else None,
        )
        db.add(attempt)

    try:
        db.commit()
        db.refresh(attempt)
    except Exception:
        db.rollback()
        raise

    # Persist per-question scoring onto quiz_attempt_answers so the
    # pending-review / grading endpoints have somewhere to read/write
    # achieved_mark and is_correct. Upsert per question.
    for qid_str, result in per_question_results.items():
        qid_int = int(qid_str)
        row = db.query(QuizAttemptAnswer).filter(
            QuizAttemptAnswer.quiz_attempt_id == attempt.attempt_id,
            QuizAttemptAnswer.question_id == qid_int,
        ).first()
        given = answers_data.get(qid_str, "")
        if row:
            row.given_answer = str(given)
            row.is_correct = result["is_correct"]
            row.achieved_mark = result["achieved_mark"]
        else:
            question_row = next((q for q in questions if q.question_id == qid_int), None)
            row = QuizAttemptAnswer(
                user_id=current_user.id,
                quiz_id=quiz_id,
                question_id=qid_int,
                quiz_attempt_id=attempt.attempt_id,
                given_answer=str(given),
                question_mark=question_row.question_mark if question_row else 0,
                achieved_mark=result["achieved_mark"],
                is_correct=result["is_correct"],
            )
            db.add(row)
    if per_question_results:
        db.commit()

    # Recalculate course progress after scoring: a passed quiz may push the
    # enrollment to 100% and must trigger cert issuance like mark-lesson-complete
    # and grade-assignment do. Skip for owners/admins who aren't really enrolled,
    # and skip while pending_review — passed_distinct_quizzes only counts
    # attempt_ended attempts, so nothing to recalc until finalize.
    if enrollment is not None and final_status == "attempt_ended":
        try:
            from app.services.course_service import CourseService
            CourseService.calculate_course_progress(db, enrollment)
        except Exception:
            # Don't fail the quiz submit because the downstream bookkeeping
            # hit a snag — the attempt is saved.
            try:
                db.rollback()
            except Exception:
                pass

    passed = (final_status == "attempt_ended") and percentage >= quiz.quiz_passing_grade

    # Gamification (spec D1): +20 for a passed quiz, +10 bonus at >= 90%.
    # Only for a genuinely finalized attempt (attempt_ended) — pending_review
    # attempts award nothing until finalize_quiz_attempt flips them.
    # Idempotent on attempt_id, so re-submitting the same ended attempt (if
    # that were ever possible) can't double-award.
    if passed:
        try:
            from app.services.gamification_service import award as _award_xp
            # Review finding M4: the event_key is keyed on (quiz, user), NOT
            # on the attempt. A per-attempt key let a student farm unbounded
            # XP by re-taking the same quiz (every fresh attempt_id minted a
            # new, un-awarded key). Keying on the quiz makes a pass award XP
            # ONCE EVER, matching lesson/course completion semantics.
            _award_xp(
                db, current_user.id, "quiz_passed",
                event_key=f"quiz:{quiz_id}:passed:user:{current_user.id}",
                course_id=course_id,
                meta={"quiz_id": quiz_id, "attempt_id": attempt.attempt_id, "percentage": round(percentage, 2)},
            )
            if percentage >= QUIZ_BONUS_THRESHOLD_PCT:
                _award_xp(
                    db, current_user.id, "quiz_passed_bonus",
                    event_key=f"quiz:{quiz_id}:bonus:user:{current_user.id}",
                    course_id=course_id,
                    meta={"quiz_id": quiz_id, "attempt_id": attempt.attempt_id, "percentage": round(percentage, 2)},
                )
            # award() only flushes (H1 review fix) — everything ahead of this
            # point (the attempt row, per-question scoring, and any progress
            # recalc) is already committed above, so this commit covers only
            # the gamification rows and nothing else can be lost if it fails.
            db.commit()
        except Exception as game_err:
            logger.warning("Gamification award failed for quiz submit: %s", game_err)
            try:
                db.rollback()
            except Exception:
                pass

    # Mastery graph (v2.0 §9.5) — best-effort, after the attempt's own commit.
    from app.services.mastery_service import safe_record_evidence
    safe_record_evidence(db, user_id=current_user.id, kind="quiz", ref_id=quiz_id, score=float(earned_marks or 0),
                         max_score=float(total_marks or 0), course_id=course_id)
    from app.services.learning_planner_service import refresh_after_assessment
    refresh_after_assessment(db, current_user.id, course_id)

    return {
        "attempt_id": attempt.attempt_id,
        "total_marks": total_marks,
        "earned_marks": earned_marks,
        "percentage": round(percentage, 2),
        "passed": passed,
        "passing_grade": quiz.quiz_passing_grade,
        "attempt_status": final_status,
        "pending_review": has_manual_question,
        # Review finding C2: true when this submit was server-forced by the
        # deadline (only already-saved answers were scored — any answers in
        # this request's body, if it was a live client call, were
        # discarded). 200, never a wedge.
        "late_submission": is_late_submission,
        "weak_concepts": _weak_concepts_for_view(db, attempt, quiz, current_user),
    }


@router.post("/courses/{course_id}/quizzes/{quiz_id}/submit")
async def submit_quiz(
    course_id: int,
    quiz_id: int,
    submission_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    """
    Submit quiz answers and record attempt (canonical route — see
    _submit_quiz_impl for the actual logic).
    """
    return await _submit_quiz_impl(
        course_id=course_id,
        quiz_id=quiz_id,
        submission_data=submission_data,
        db=db,
        current_user=current_user,
    )


@router.get("/courses/{course_id}/quizzes/{quiz_id}/attempt")
async def get_quiz_attempt(
    course_id: int,
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get the most recent quiz attempt for the current user
    """
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.course_id == course_id,
        QuizAttempt.attempt_status == "attempt_ended"
    ).order_by(QuizAttempt.attempt_ended_at.desc()).first()

    if not attempt:
        return None

    # Get quiz for passing grade
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()

    return {
        "attempt_id": attempt.attempt_id,
        "total_marks": float(attempt.total_marks),
        "earned_marks": float(attempt.earned_marks),
        "percentage": round((float(attempt.earned_marks) / float(attempt.total_marks) * 100) if attempt.total_marks > 0 else 0, 2),
        "passed": (float(attempt.earned_marks) / float(attempt.total_marks) * 100) >= quiz.quiz_passing_grade if attempt.total_marks > 0 else False,
        "passing_grade": quiz.quiz_passing_grade,
        # audit B8: go through the tolerant reader — a bare json.loads here
        # 500s the moment attempt_info holds a real dict rather than a
        # double-encoded string.
        "answers": _attempt_info_dict(attempt)
    }


@router.get("/courses/{course_id}/quizzes/{quiz_id}/attempts-count")
async def get_quiz_attempts_count(
    course_id: int,
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get the number of attempts used and remaining for the current user
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    attempts_used = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.course_id == course_id,
        QuizAttempt.attempt_status == "attempt_ended"
    ).count()

    max_attempts = quiz.quiz_max_attempts_allowed or 0  # 0 means unlimited
    remaining = max_attempts - attempts_used if max_attempts > 0 else 999

    return {
        "attempts_used": attempts_used,
        "max_attempts": max_attempts,
        "remaining": remaining,
        "unlimited": max_attempts == 0
    }


# -----------------------------------------------------------------------------
# Quiz player lifecycle endpoints (start / save-answer / pause / resume / results)
# -----------------------------------------------------------------------------

def _attempt_info_dict(attempt: QuizAttempt) -> dict:
    """Safely read attempt_info as a dict (may be JSON-encoded string or dict)."""
    return _json_column_dict(attempt.attempt_info)


def _authorize_attempt(attempt: QuizAttempt, current_user: User) -> None:
    """Raise 403 unless the attempt belongs to the caller or caller is admin.

    Used by every write-ish/self-service attempt endpoint (attempt detail,
    save-answer, pause, resume, the attempt-scoped submit route) — kept
    narrow to the attempt owner intentionally, since widening it would let
    a course-owning instructor pause/resume/write answers on a student's
    still-in-progress attempt, which is out of scope for grading access.
    """
    if attempt.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this quiz attempt"
        )


def _authorize_attempt_view(db: Session, attempt: QuizAttempt, current_user: User) -> None:
    """Raise 403 unless the caller may VIEW this attempt's results: the
    attempt owner, an admin, or the instructor who owns the attempt's
    course (grading-queue review round finding — a course-owning
    non-admin instructor was 403ing on GET /quiz-attempts/{id}/results,
    the exact call grading-queue.tsx's essay-review detail view makes,
    making the grade-each-answer -> finalize flow unusable for anyone but
    an admin). Deliberately separate from `_authorize_attempt` (used by
    write/self-service endpoints) — read access for grading purposes
    should not imply write access to a student's live attempt.

    A different student, or an instructor who does NOT own this course,
    still gets 403 — this only adds one specific, read-only allowance.
    """
    if attempt.user_id == current_user.id or current_user.role == "admin":
        return
    course = db.query(Course).filter(Course.id == attempt.course_id).first()
    if course is not None and course.post_author == current_user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have access to this quiz attempt"
    )


# Server-side timer grace window (spec A1.3): submit is rejected once now is
# past attempt_started_at + quiz_time_limit + this grace + accumulated pause
# duration. Covers network/client jitter around auto-submit.
SUBMIT_GRACE_SECONDS = 90

# Pause duration is capped at 24h total so a forgotten/never-resumed pause
# can't extend the deadline indefinitely (spec A1.11).
MAX_PAUSE_SECONDS = 24 * 60 * 60


def _as_utc(dt: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip even for DateTime(timezone=True)
    columns — the stored value is still UTC wall-clock time. Re-attach UTC
    so arithmetic/comparison against an aware `now` doesn't raise or apply
    the host's local offset. Mirrors live_class_service._as_utc."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _is_paused(info: dict) -> bool:
    """True if attempt_info['_pause'] currently marks the attempt paused."""
    pause = info.get("_pause")
    if not isinstance(pause, dict):
        return False
    return bool(pause.get("paused"))


def _accumulated_pause_seconds(info: dict) -> float:
    """Total paused duration for this attempt, in seconds, capped at
    MAX_PAUSE_SECONDS. Adds any already-accumulated total plus, if currently
    paused, the time elapsed since the current pause began."""
    pause = info.get("_pause")
    if not isinstance(pause, dict):
        return 0.0

    total = float(pause.get("accumulated_seconds") or 0)

    if pause.get("paused") and pause.get("paused_at"):
        try:
            paused_at = datetime.fromisoformat(str(pause["paused_at"]))
        except (TypeError, ValueError):
            paused_at = None
        if paused_at is not None:
            paused_at = _as_utc(paused_at)
            now = datetime.now(timezone.utc)
            if now > paused_at:
                total += (now - paused_at).total_seconds()

    return min(total, MAX_PAUSE_SECONDS)


@router.post("/quizzes/{quiz_id}/start")
async def start_quiz_attempt(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Create a new QuizAttempt for the current user. Requires enrollment in the
    owning course (course author and admin bypass enrollment).
    """
    from app.models.enrollment import Enrollment

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    course_id = quiz.post_parent
    course = db.query(Course).filter(Course.id == course_id).first()
    is_owner_or_admin = course is not None and (
        course.post_author == current_user.id or current_user.role == "admin"
    )

    if not is_owner_or_admin:
        # R8: timed window
        _now = datetime.now(timezone.utc)
        _from, _until = _parse_window(quiz.quiz_available_from), _parse_window(quiz.quiz_available_until)
        if _from and _now < _from:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"This quiz opens at {_from.isoformat()}")
        if _until and _now > _until:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This quiz is closed")
    if not is_owner_or_admin:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == current_user.id
        ).first()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in the course to start this quiz"
            )

    # Resume-existing-attempt: if the user already has an OPEN attempt
    # (attempt_started, or pending_review — review finding C1: a
    # pending_review attempt is awaiting instructor grading, not startable
    # over) for this quiz, return THAT attempt instead of creating a new
    # one — prevents orphaned rows and double-counting toward max_attempts
    # on a merely-abandoned-tab retry. A pending_review "resume" doesn't
    # mean the student can keep answering it (submit_quiz's own guard
    # rejects that); it just surfaces the existing row instead of 500ing
    # or silently creating a duplicate.
    existing_attempt = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.attempt_status.in_(["attempt_started", "pending_review"]),
    ).order_by(QuizAttempt.attempt_started_at.desc()).first()
    if existing_attempt:
        return {
            "attempt_id": existing_attempt.attempt_id,
            "quiz_id": quiz_id,
            "course_id": course_id,
            "total_questions": existing_attempt.total_questions,
            "time_limit": quiz.quiz_time_limit,  # minutes; 0 = unlimited
            "attempt_started_at": existing_attempt.attempt_started_at.isoformat() if existing_attempt.attempt_started_at else None,
            "attempt_status": existing_attempt.attempt_status,
            "resumed": True,
            "question_ids": (existing_attempt.attempt_info or {}).get("_question_ids"),
        }

    # Enforce max_attempts (0 = unlimited). Review finding C1: pending_review
    # attempts count too — otherwise a student could accumulate unlimited
    # pending_review rows (each awaiting instructor grading) past
    # max_attempts by always including a manually-graded question.
    if quiz.quiz_max_attempts_allowed and quiz.quiz_max_attempts_allowed > 0:
        prior_count = db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.attempt_status.in_(["attempt_ended", "pending_review"]),
        ).count()
        if prior_count >= quiz.quiz_max_attempts_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Maximum attempts reached for this quiz"
            )

    total_questions = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == quiz_id,
        _not_retired(),
    ).count()

    # Roadmap item 5: draw N questions per attempt when the quiz asks for it.
    attempt_info = {}
    limit = int(quiz.quiz_max_questions_for_take or 0)
    if 0 < limit < total_questions:
        import random as _random
        ids = [qid for (qid,) in db.query(QuizQuestion.question_id).filter(QuizQuestion.quiz_id == quiz_id, _not_retired()).all()]
        _random.shuffle(ids)
        attempt_info["_question_ids"] = ids[:limit]
        total_questions = limit
    started_at = datetime.now(timezone.utc)
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        course_id=course_id,
        total_questions=total_questions,
        total_answered_questions=0,
        total_marks=0,
        earned_marks=0,
        attempt_info=attempt_info,
        attempt_status="attempt_started",
        attempt_started_at=started_at,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": attempt.attempt_id,
        "quiz_id": quiz_id,
        "course_id": course_id,
        "total_questions": total_questions,
        "time_limit": quiz.quiz_time_limit,  # minutes; 0 = unlimited
        "attempt_started_at": started_at.isoformat(),
        "attempt_status": attempt.attempt_status,
        "resumed": False,
        "question_ids": attempt_info.get("_question_ids"),
    }


@router.get("/quiz-attempts/{attempt_id}")
async def get_quiz_attempt_by_id(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Return an in-progress or ended attempt. If the attempt has not been
    submitted, correct-answer / explanation data is omitted to prevent leakage.
    """
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    _authorize_attempt(attempt, current_user)

    saved_answers = _attempt_info_dict(attempt)
    # Return per-question saved answers via quiz_attempt_answers if present,
    # falling back to attempt_info blob.
    per_answers = db.query(QuizAttemptAnswer).filter(
        QuizAttemptAnswer.quiz_attempt_id == attempt_id
    ).all()
    if per_answers:
        saved_answers = {str(a.question_id): a.given_answer for a in per_answers}

    return {
        "attempt_id": attempt.attempt_id,
        "quiz_id": attempt.quiz_id,
        "course_id": attempt.course_id,
        "user_id": attempt.user_id,
        "attempt_status": attempt.attempt_status,
        "total_questions": attempt.total_questions,
        "total_answered_questions": attempt.total_answered_questions,
        "attempt_started_at": attempt.attempt_started_at.isoformat() if attempt.attempt_started_at else None,
        "attempt_ended_at": attempt.attempt_ended_at.isoformat() if attempt.attempt_ended_at else None,
        "answers": saved_answers,
    }


@router.post("/quiz-attempts/{attempt_id}/answers")
async def save_attempt_answer(
    attempt_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Upsert a single answer for (attempt_id, question_id). Frontend sends:
        { "question_id": <int>, "given_answer": <str> }
    """
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    _authorize_attempt(attempt, current_user)

    if attempt.attempt_status != "attempt_started":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify a submitted attempt"
        )

    info = _attempt_info_dict(attempt)
    if _is_paused(info):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attempt is paused — resume before saving answers"
        )

    question_id = payload.get("question_id")
    given_answer = payload.get("given_answer", "")
    if question_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question_id is required"
        )

    question = db.query(QuizQuestion).filter(
        QuizQuestion.question_id == question_id,
        QuizQuestion.quiz_id == attempt.quiz_id,
    ).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found in this quiz"
        )

    # Upsert into quiz_attempt_answers
    row = db.query(QuizAttemptAnswer).filter(
        QuizAttemptAnswer.quiz_attempt_id == attempt_id,
        QuizAttemptAnswer.question_id == question_id,
    ).first()

    if row:
        row.given_answer = str(given_answer)
    else:
        row = QuizAttemptAnswer(
            user_id=current_user.id,
            quiz_id=attempt.quiz_id,
            question_id=question_id,
            quiz_attempt_id=attempt_id,
            given_answer=str(given_answer),
            question_mark=question.question_mark,
            achieved_mark=0,
            is_correct=False,
        )
        db.add(row)

    # Mirror into attempt_info blob so /submit scoring (which reads attempt_info)
    # stays consistent with per-row storage. Reuse `info` fetched above (pause
    # check) rather than re-reading, and preserve internal keys like _pause.
    info[str(question_id)] = given_answer
    attempt.attempt_info = info
    attempt.total_answered_questions = len([k for k in info if not str(k).startswith("_")])

    db.commit()

    return {
        "attempt_id": attempt_id,
        "question_id": question_id,
        "saved": True,
    }


@router.post("/quiz-attempts/{attempt_id}/pause")
async def pause_quiz_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Mark an attempt as paused. The QuizAttempt model has no dedicated pause
    column, so we stash the pause state inside `attempt_info["_pause"]` as a
    best-effort record without requiring a schema migration. Save-answer
    writes are refused while paused (spec A1.11); the server-side submit
    deadline is extended by the accumulated pause duration, capped at 24h.
    """
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    _authorize_attempt(attempt, current_user)

    if attempt.attempt_status == "attempt_ended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pause a submitted attempt"
        )

    info = _attempt_info_dict(attempt)
    if not _is_paused(info):
        prior_pause = info.get("_pause") if isinstance(info.get("_pause"), dict) else {}
        info["_pause"] = {
            "paused": True,
            "paused_at": datetime.now(timezone.utc).isoformat(),
            "accumulated_seconds": float(prior_pause.get("accumulated_seconds") or 0),
        }
        attempt.attempt_info = info
        db.commit()

    return {"attempt_id": attempt_id, "paused": True, "note": "pause-state stored in attempt_info"}


@router.post("/quiz-attempts/{attempt_id}/resume")
async def resume_quiz_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Clear the pause flag stashed inside attempt_info, folding the elapsed
    pause duration into the running accumulated total (capped at 24h). No
    schema changes.
    """
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    _authorize_attempt(attempt, current_user)

    if attempt.attempt_status == "attempt_ended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resume a submitted attempt"
        )

    info = _attempt_info_dict(attempt)
    if "_pause" in info:
        accumulated = _accumulated_pause_seconds(info)
        info["_pause"] = {
            "paused": False,
            "resumed_at": datetime.now(timezone.utc).isoformat(),
            "accumulated_seconds": accumulated,
        }
        attempt.attempt_info = info
        db.commit()

    return {"attempt_id": attempt_id, "paused": False, "note": "pause-state cleared in attempt_info"}


def _quiz_due_passed(quiz: Quiz, attempt: QuizAttempt) -> bool:
    """True once the quiz's "due point" (spec R4/§4) has passed for this
    attempt, for `reveal_after_due` gating.

    - No time limit (`quiz_time_limit` falsy/0): there is no due point to
      wait for — treat as immediate (always "passed").
    - Timed quiz: due = the attempt's own deadline, using the EXACT same
      formula the server-side submit timer uses (attempt_started_at +
      quiz_time_limit minutes + SUBMIT_GRACE_SECONDS + accumulated pause
      seconds) — see submit_quiz_attempt — so "past due" here means the
      same instant the timer itself would have cut the attempt off.
    """
    if quiz is None or not quiz.quiz_time_limit or quiz.quiz_time_limit <= 0:
        return True
    if attempt.attempt_started_at is None:
        # No known start time to measure from — can't be "past due" yet.
        return False
    started_at = _as_utc(attempt.attempt_started_at)
    info = _attempt_info_dict(attempt)
    pause_seconds = _accumulated_pause_seconds(info)
    deadline = started_at + timedelta(minutes=quiz.quiz_time_limit) \
        + timedelta(seconds=SUBMIT_GRACE_SECONDS + pause_seconds)
    return datetime.now(timezone.utc) > deadline


def _weak_concepts_for_view(db: Session, attempt, quiz, user) -> list:
    from app.services.learning_signals_service import weak_attempt_concepts
    if attempt.user_id == user.id and user.role != "admin" and normalize_feedback_mode(quiz.quiz_feedback_mode if quiz else None) == "reveal_never":
        return []
    return weak_attempt_concepts(db, attempt)


def _redact_review_item(item: dict, mode: str, due_passed: bool) -> dict:
    """Apply the feedback policy (spec R4/§4) to one already-built review
    item, IN PLACE, and return it. Must run identically for every question
    type/state (auto-graded, manual pending_review, manual graded) — the
    set of keys present/absent is what callers assert on, not just values,
    so a redacted key is deleted outright rather than set to None (None is
    still a meaningful, distinguishable value for `is_correct` on a
    not-yet-graded manual question).

    - reveal_immediate: no redaction — today's full review.
    - reveal_after_due: while NOT yet past due, omit `correct_answer` and
      `explanation` but KEEP `is_correct`/`achieved_mark`/`feedback`(instructor
      text)/`needs_review`. Once past due, behaves like reveal_immediate.
    - reveal_never: ALWAYS omit `correct_answer`, `explanation` AND
      `is_correct` (spec §4: "omits all three forever") — `achieved_mark`
      and everything else stays, so a student still sees their score.
    """
    if mode == "reveal_never":
        item.pop("correct_answer", None)
        item.pop("explanation", None)
        item.pop("is_correct", None)
    elif mode == "reveal_after_due" and not due_passed:
        item.pop("correct_answer", None)
        item.pop("explanation", None)
    return item


@router.get("/quiz-attempts/{attempt_id}/results")
async def get_quiz_attempt_results(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Return a submitted attempt with score and per-question correct/incorrect
    breakdown. For unsubmitted attempts, omit correct-answer leakage.

    `pending_review` is treated as submitted-but-partial: auto-graded
    questions reveal their correct answer/explanation same as a fully ended
    attempt, but manually-graded questions (essay/open_ended) never reveal
    a correct_answer (there isn't a single one) and are flagged
    `needs_review: true` with `is_correct: null` until an instructor grades
    them and finalizes the attempt.

    Feedback policy (spec R4/§4): the quiz's `quiz_feedback_mode` further
    redacts each question's `correct_answer`/`explanation`/`is_correct` —
    see `_redact_review_item`. Applied to EVERY question type/state
    consistently. The response's top-level `feedback_mode` tells the UI
    which policy was applied and why fields may be missing. This gating
    applies ONLY to the attempt's own student viewing their own results —
    an admin or the course-owning instructor sees the unredacted review
    regardless of mode (they already have full access to the answer key).

    View access: the attempt owner, an admin, or the instructor who owns
    the attempt's course (needed for the grading-queue essay-review detail
    view — see _authorize_attempt_view). A different student, or an
    instructor who doesn't own this course, still gets 403.
    """
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    _authorize_attempt_view(db, attempt, current_user)

    quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
    questions = db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id == attempt.quiz_id
    ).order_by(QuizQuestion.question_order, QuizQuestion.question_id).all()

    answers_blob = _attempt_info_dict(attempt)
    # Strip internal keys like _pause from the user-visible map
    user_answers = {k: v for k, v in answers_blob.items() if not str(k).startswith("_")}

    is_ended = attempt.attempt_status == "attempt_ended"
    is_pending_review = attempt.attempt_status == "pending_review"
    is_submitted = is_ended or is_pending_review
    total_marks = float(attempt.total_marks or 0)
    earned_marks = float(attempt.earned_marks or 0)
    percentage = round((earned_marks / total_marks * 100) if total_marks > 0 else 0, 2)
    passing_grade = quiz.quiz_passing_grade if quiz else 0
    # A pending_review attempt's percentage/pass verdict is provisional
    # (auto-graded portion only) — never report "passed" until finalize.
    passed = is_ended and percentage >= passing_grade

    # Feedback policy (spec R4/§4). Gating applies only to the attempt's
    # own student viewing their own results — an admin or the course-owning
    # instructor already has full access to the answer key regardless of
    # mode (see _authorize_attempt_view: those are the only two ways a
    # non-owner reaches this endpoint at all).
    feedback_mode = normalize_feedback_mode(quiz.quiz_feedback_mode if quiz else None)
    is_attempt_owner_viewing = attempt.user_id == current_user.id
    apply_feedback_gating = is_attempt_owner_viewing and current_user.role != "admin"
    due_passed = _quiz_due_passed(quiz, attempt)

    # Per-question achieved_mark/is_correct already persisted at submit time
    # (see submit_quiz) — read those back instead of recomputing, so a
    # manually-graded question's later instructor score is reflected here.
    saved_rows = {
        a.question_id: a
        for a in db.query(QuizAttemptAnswer).filter(
            QuizAttemptAnswer.quiz_attempt_id == attempt_id
        ).all()
    }

    # Instructor free-text feedback left via POST .../answers/{id}/grade —
    # stored in attempt_info._manual_feedback keyed by attempt_answer_id
    # (see grade_quiz_attempt_answer). Never redacted by feedback_mode —
    # the spec only names correct_answer/explanation/is_correct.
    manual_feedback_map = _attempt_info_dict(attempt).get("_manual_feedback", {})
    if not isinstance(manual_feedback_map, dict):
        manual_feedback_map = {}

    breakdown = []
    for q in questions:
        user_answer = user_answers.get(str(q.question_id))
        item = {
            "question_id": q.question_id,
            "question": q.question_title,
            "type": q.question_type,
            "points": float(q.question_mark or 0),
            "user_answer": user_answer,
        }
        is_manual = q.question_type in MANUAL_GRADE_QUESTION_TYPES

        if is_submitted and is_manual:
            saved = saved_rows.get(q.question_id)
            # A manual question only stops needing review once the attempt
            # is finalized (attempt_ended) — see finalize_quiz_attempt.
            item["needs_review"] = not is_ended
            item["is_correct"] = None if not is_ended else bool(saved and saved.is_correct)
            item["achieved_mark"] = float(saved.achieved_mark) if saved else None
            item["correct_answer"] = None  # no single correct answer for manual types
            # Exposes the QuizAttemptAnswer PK so an instructor-facing client
            # (grading queue) can call POST .../answers/{answer_id}/grade
            # directly from this breakdown without a separate lookup — the
            # grade endpoint takes attempt_answer_id, not question_id.
            item["attempt_answer_id"] = saved.attempt_answer_id if saved else None
            item["explanation"] = q.answer_explanation or ""
            item["feedback"] = (
                manual_feedback_map.get(str(saved.attempt_answer_id)) if saved else None
            )
            item = _redact_review_item(item, feedback_mode, due_passed) \
                if apply_feedback_gating else item

        elif is_submitted:
            # Reveal correct answer + explanation for auto-graded questions
            # once the attempt has at least been submitted (attempt_ended
            # OR pending_review — the auto portion is already final).
            all_answers = db.query(QuizQuestionAnswer).filter(
                QuizQuestionAnswer.belongs_question_id == q.question_id
            ).order_by(QuizQuestionAnswer.answer_order).all()
            correct = [a for a in all_answers if a.is_correct]

            # correct_answer_out (the CURRENT correct answer text/index) is
            # always computed live from QuizQuestionAnswer — it's meant to
            # reflect the quiz as it exists now, and manual grading has no
            # equivalent concept for auto-graded types.
            is_correct = False
            correct_answer_out = None
            if q.question_type == "multiple_choice":
                for idx, a in enumerate(all_answers):
                    if a.is_correct:
                        correct_answer_out = idx
                        break
                try:
                    if user_answer is not None and int(user_answer) == correct_answer_out:
                        is_correct = True
                except (TypeError, ValueError):
                    pass
            elif q.question_type == "multi_select":
                correct_answer_out = [
                    idx for idx, a in enumerate(all_answers) if a.is_correct
                ]
                picked = _multi_select_answer_list(user_answer, max_len=len(all_answers))
                if picked is not None:
                    picked_indices = {_mc_answer_index(a) for a in picked}
                    if all(0 <= i < len(all_answers) for i in picked_indices):
                        is_correct = picked_indices == set(correct_answer_out)
            elif q.question_type == "true_false":
                correct_answer_out = (correct[0].answer_title.lower() if correct else None)
                if user_answer is not None and str(user_answer).lower() == str(correct_answer_out):
                    is_correct = True
            elif q.question_type in ("fill_in_blank", "short_answer"):
                correct_answer_out = correct[0].answer_title if correct else None
                if user_answer is not None and correct_answer_out is not None and \
                        str(user_answer).strip().lower() == str(correct_answer_out).strip().lower():
                    is_correct = True

            # Prefer the PERSISTED per-question result from submit time
            # (review finding — controller ruling): recomputing live from
            # the current QuizQuestionAnswer rows means an instructor
            # editing options/correct-answer AFTER a submission silently
            # flips a historical is_correct/achieved_mark, while the
            # attempt header (total_marks/earned_marks/passed/counts) still
            # reflects what was actually scored at submit time — the
            # per-question breakdown would then contradict its own header.
            # Live recomputation stays as a fallback ONLY for attempts with
            # no saved row (shouldn't happen post-Task-1, but defends
            # against pre-existing data).
            saved = saved_rows.get(q.question_id)
            if saved is not None:
                is_correct = bool(saved.is_correct)
                achieved_mark = float(saved.achieved_mark or 0)
            else:
                achieved_mark = float(q.question_mark or 0) if is_correct else 0.0

            item["is_correct"] = is_correct
            item["achieved_mark"] = achieved_mark
            item["correct_answer"] = correct_answer_out
            item["explanation"] = q.answer_explanation or ""
            item["needs_review"] = False
            if apply_feedback_gating:
                item = _redact_review_item(item, feedback_mode, due_passed)

        breakdown.append(item)

    # correct_count/incorrect_count reflect whatever is_correct the caller
    # actually sees — under reveal_never (student view) is_correct is
    # deleted from every item's dict, so .get() naturally returns neither
    # True nor False and both counts land at 0 for that viewer, same as an
    # unsubmitted attempt. This is intentional: reveal_never withholds
    # right/wrong signal entirely, and a count derived from data the
    # response doesn't otherwise expose would leak it back out.
    correct_count = sum(1 for b in breakdown if b.get("is_correct") is True) if is_submitted else 0
    incorrect_count = (
        len([b for b in breakdown if b.get("is_correct") is False]) if is_submitted else 0
    )

    return {
        "attempt_id": attempt.attempt_id,
        "quiz_id": attempt.quiz_id,
        "course_id": attempt.course_id,
        "attempt_status": attempt.attempt_status,
        "submitted": is_submitted,
        "pending_review": is_pending_review,
        "total_marks": total_marks,
        "earned_marks": earned_marks,
        "percentage": percentage,
        "passing_grade": passing_grade,
        "passed": passed,
        "total_questions": len(questions),
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "attempt_started_at": attempt.attempt_started_at.isoformat() if attempt.attempt_started_at else None,
        "attempt_ended_at": attempt.attempt_ended_at.isoformat() if attempt.attempt_ended_at else None,
        "feedback_mode": feedback_mode,
        "questions": breakdown,
        "weak_concepts": _weak_concepts_for_view(db, attempt, quiz, current_user),
    }


# -----------------------------------------------------------------------------
# Instructor manual-grading endpoints (spec A1.1 — pending_review flow)
# -----------------------------------------------------------------------------

def _require_quiz_course_owner_or_admin(db: Session, quiz: Quiz, current_user: User) -> None:
    """Raise 403 unless caller owns the quiz's course or is admin — same
    guard shape used by the other instructor-only quiz endpoints."""
    course = db.query(Course).filter(Course.id == quiz.post_parent).first()
    if not course or not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage grading for this quiz"
        )


@router.post("/quiz-attempts/{attempt_id}/answers/{answer_id}/grade")
async def grade_quiz_attempt_answer(
    attempt_id: int,
    answer_id: int,
    grade_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """
    Grade one manually-graded answer within a pending_review attempt.
    Body: {"achieved_mark": <number>, "feedback": <str, optional>}
    """
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    _require_quiz_course_owner_or_admin(db, quiz, current_user)

    answer = db.query(QuizAttemptAnswer).filter(
        QuizAttemptAnswer.attempt_answer_id == answer_id,
        QuizAttemptAnswer.quiz_attempt_id == attempt_id,
    ).first()
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found on this attempt")

    achieved_mark = grade_data.get("achieved_mark")
    if achieved_mark is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="achieved_mark is required")
    try:
        achieved_mark = float(achieved_mark)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="achieved_mark must be numeric")

    max_mark = float(answer.question_mark or 0)
    if achieved_mark < 0 or (max_mark > 0 and achieved_mark > max_mark):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"achieved_mark must be between 0 and {max_mark}"
        )

    answer.achieved_mark = achieved_mark
    answer.is_correct = achieved_mark >= max_mark and max_mark > 0

    # QuizAttemptAnswer has no dedicated "graded" flag or feedback column.
    # achieved_mark==0 is a legitimate score, indistinguishable at rest from
    # "never graded" — so we record graded-ness (and optional feedback text)
    # explicitly in the attempt's attempt_info blob, keyed by answer id.
    # finalize_quiz_attempt reads `_graded_answers` as the completeness gate.
    info = _attempt_info_dict(attempt)
    graded_ids = info.get("_graded_answers", [])
    if not isinstance(graded_ids, list):
        graded_ids = []
    if answer_id not in graded_ids:
        graded_ids.append(answer_id)
    info["_graded_answers"] = graded_ids

    feedback = grade_data.get("feedback")
    if feedback is not None:
        feedback_map = info.get("_manual_feedback", {})
        if not isinstance(feedback_map, dict):
            feedback_map = {}
        feedback_map[str(answer_id)] = feedback
        info["_manual_feedback"] = feedback_map

    attempt.attempt_info = info
    db.commit()

    return {
        "attempt_id": attempt_id,
        "answer_id": answer_id,
        "achieved_mark": achieved_mark,
        "is_correct": answer.is_correct,
        "graded": True,
    }


@router.post("/quiz-attempts/{attempt_id}/finalize")
async def finalize_quiz_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """
    Finalize a pending_review attempt: requires every manually-graded
    answer to have been graded (achieved_mark set), recomputes
    earned_marks from all per-answer achieved_mark rows, flips the attempt
    to attempt_ended, and triggers progress recalc for enrolled users.
    """
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    _require_quiz_course_owner_or_admin(db, quiz, current_user)

    if attempt.attempt_status != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Attempt is not pending review (status: {attempt.attempt_status})"
        )

    manual_answers = db.query(QuizAttemptAnswer).join(
        QuizQuestion, QuizAttemptAnswer.question_id == QuizQuestion.question_id
    ).filter(
        QuizAttemptAnswer.quiz_attempt_id == attempt_id,
        QuizQuestion.question_type.in_(MANUAL_GRADE_QUESTION_TYPES),
    ).all()

    # A manual answer counts as graded once the grade endpoint has recorded
    # its id in attempt_info["_graded_answers"] — an explicit marker rather
    # than inferring from achieved_mark (0 is a legitimate score, not a
    # "not yet graded" sentinel).
    info = _attempt_info_dict(attempt)
    graded_ids = set(info.get("_graded_answers") or [])

    ungraded = [a for a in manual_answers if a.attempt_answer_id not in graded_ids]
    if ungraded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{len(ungraded)} manually-graded answer(s) still ungraded "
                f"(answer_ids={[a.attempt_answer_id for a in ungraded]}). "
                "Grade every essay/open-ended answer before finalizing."
            )
        )

    # Recompute earned_marks from every persisted per-answer achieved_mark
    # (auto-graded questions already have theirs from submit_quiz).
    all_answers = db.query(QuizAttemptAnswer).filter(
        QuizAttemptAnswer.quiz_attempt_id == attempt_id
    ).all()
    earned_marks = sum(float(a.achieved_mark or 0) for a in all_answers)

    attempt.earned_marks = earned_marks
    attempt.attempt_status = "attempt_ended"
    attempt.attempt_ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(attempt)

    # Progress recalc for enrolled users (mirrors submit_quiz) — best-effort,
    # never fails the finalize.
    from app.models.enrollment import Enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == attempt.course_id,
        Enrollment.user_id == attempt.user_id,
    ).first()
    if enrollment is not None:
        try:
            from app.services.course_service import CourseService
            CourseService.calculate_course_progress(db, enrollment)
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    total_marks = float(attempt.total_marks or 0)
    percentage = round((earned_marks / total_marks * 100) if total_marks > 0 else 0, 2)
    passed = percentage >= quiz.quiz_passing_grade

    # Gamification (spec D1): the pending_review path only reaches a real
    # verdict here at finalize — mirrors the direct-pass award in
    # _submit_quiz_impl, same idempotent event_key shape.
    if passed:
        try:
            from app.services.gamification_service import award as _award_xp
            # Review finding M4: keyed on (quiz, user), not on the attempt —
            # see the matching comment in _submit_quiz_impl. Both sites must
            # use the SAME key shape so a pass that arrives via review
            # finalization and one that arrives directly converge to a single
            # award rather than stacking.
            _award_xp(
                db, attempt.user_id, "quiz_passed",
                event_key=f"quiz:{attempt.quiz_id}:passed:user:{attempt.user_id}",
                course_id=attempt.course_id,
                meta={"quiz_id": attempt.quiz_id, "attempt_id": attempt.attempt_id, "percentage": percentage},
            )
            if percentage >= QUIZ_BONUS_THRESHOLD_PCT:
                _award_xp(
                    db, attempt.user_id, "quiz_passed_bonus",
                    event_key=f"quiz:{attempt.quiz_id}:bonus:user:{attempt.user_id}",
                    course_id=attempt.course_id,
                    meta={"quiz_id": attempt.quiz_id, "attempt_id": attempt.attempt_id, "percentage": percentage},
                )
            # award() only flushes (H1 review fix) — the attempt's own
            # finalize state and any progress recalc are already committed
            # above, so this commit covers only the gamification rows.
            db.commit()
        except Exception as game_err:
            logger.warning("Gamification award failed for quiz finalize: %s", game_err)
            try:
                db.rollback()
            except Exception:
                pass

    from app.services.mastery_service import safe_record_evidence
    safe_record_evidence(db, user_id=attempt.user_id, kind="quiz", ref_id=attempt.quiz_id, score=float(earned_marks or 0),
                         max_score=float(total_marks or 0), course_id=attempt.course_id)
    from app.services.learning_planner_service import refresh_after_assessment
    refresh_after_assessment(db, attempt.user_id, attempt.course_id)

    return {
        "attempt_id": attempt.attempt_id,
        "attempt_status": attempt.attempt_status,
        "total_marks": total_marks,
        "earned_marks": earned_marks,
        "percentage": percentage,
        "passed": passed,
        "passing_grade": quiz.quiz_passing_grade,
        "weak_concepts": _weak_concepts_for_view(db, attempt, quiz, current_user),
    }


# Legacy path aliases — frontend uses /quizzes/{attempt_id}/pause|resume in some spots.
# Keep them as thin wrappers so the contract is stable regardless of which path is called.
@router.post("/quizzes/{attempt_id}/pause")
async def pause_quiz_attempt_legacy(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    return await pause_quiz_attempt(attempt_id, db, current_user)


@router.post("/quizzes/{attempt_id}/resume")
async def resume_quiz_attempt_legacy(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    return await resume_quiz_attempt(attempt_id, db, current_user)


@router.get("/quizzes/{attempt_id}/results")
async def get_quiz_results_legacy(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    return await get_quiz_attempt_results(attempt_id, db, current_user)


@router.post("/quiz-attempts/{attempt_id}/submit")
async def submit_quiz_attempt(
    attempt_id: int,
    submission_data: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """
    Submit a quiz attempt — thin wrapper that routes to the canonical
    `/courses/{course_id}/quizzes/{quiz_id}/submit` scoring logic. The
    frontend uses this attempt-scoped path; the canonical one requires
    course_id + quiz_id in the URL, which the attempt row already carries.

    Body (optional): {"answers": {question_id: given_answer, ...}} — if
    omitted, previously saved per-answer rows / attempt_info are used.
    """
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    _authorize_attempt(attempt, current_user)

    # Review finding (fix round): this used to reject ANY non-attempt_started
    # status with a flat 400, which pre-empted _submit_quiz_impl's own,
    # more specific 409 branches below (pending_review, paused) — a raced
    # tab hitting this route on a pending_review attempt saw a generic 400
    # instead of the "awaiting instructor review" 409 the canonical route
    # gives. Only `attempt_ended` is guarded here (still 409, not a wedge):
    # _submit_quiz_impl only re-derives existing_attempt when it's None, and
    # its own re-derivation query never matches attempt_ended, so an ended
    # attempt passed straight through would otherwise fall through every
    # guard below and get re-scored. `pending_review` and `attempt_started`
    # continue on to _submit_quiz_impl, which already codes those cases
    # correctly (409 pending-review / 409 paused / 200 normal submit).
    if attempt.attempt_status == "attempt_ended":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This attempt has already been submitted"
        )

    if submission_data is None:
        submission_data = {}
    # If the client didn't send answers inline, rehydrate from per-answer rows
    # so the canonical /submit scoring path can work uniformly.
    if not submission_data.get("answers"):
        rows = db.query(QuizAttemptAnswer).filter(
            QuizAttemptAnswer.quiz_attempt_id == attempt_id
        ).all()
        submission_data["answers"] = {
            str(r.question_id): r.given_answer for r in rows
        }

    return await _submit_quiz_impl(
        course_id=attempt.course_id,
        quiz_id=attempt.quiz_id,
        submission_data=submission_data,
        db=db,
        current_user=current_user,
        existing_attempt=attempt,
    )


INTEGRITY_EVENTS = ("tab_hidden", "tab_visible", "fullscreen_exit", "copy", "paste", "window_blur")


@router.post("/quiz-attempts/{attempt_id}/integrity")
async def record_integrity_event(
    attempt_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """R8 proctoring-lite: the taker's browser reports focus/tab/clipboard
    events; counts live in attempt_info['integrity'] and are shown to the
    instructor. Advisory — never changes a score."""
    event = str(payload.get("event") or "")
    if event not in INTEGRITY_EVENTS:
        raise HTTPException(status_code=422, detail=f"event must be one of {list(INTEGRITY_EVENTS)}")
    attempt = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == attempt_id).first()
    if not attempt or attempt.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if attempt.attempt_ended_at is not None:
        return {"recorded": False, "reason": "attempt already submitted"}
    info = dict(attempt.attempt_info or {})
    integ = dict(info.get("integrity") or {})
    integ[event] = int(integ.get(event) or 0) + 1
    integ["last_event_at"] = datetime.now(timezone.utc).isoformat()
    info["integrity"] = integ
    attempt.attempt_info = info
    db.commit()
    return {"recorded": True, "integrity": integ}


@router.get("/courses/{course_id}/quizzes/{quiz_id}/integrity")
async def quiz_integrity_summary(
    course_id: int,
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Instructor view: per-attempt integrity counters for one quiz."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or not can_edit(db, course, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your course")
    rows = (db.query(QuizAttempt, User).join(User, User.id == QuizAttempt.user_id)
            .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.course_id == course_id)
            .order_by(QuizAttempt.attempt_id.desc()).limit(300).all())
    out = []
    for a, u in rows:
        integ = (a.attempt_info or {}).get("integrity") or {}
        flags = []
        if int(integ.get("tab_hidden") or 0) >= 3:
            flags.append(f"left the tab {integ.get('tab_hidden')} times")
        if int(integ.get("paste") or 0) >= 1:
            flags.append(f"pasted text {integ.get('paste')}x")
        if int(integ.get("fullscreen_exit") or 0) >= 2:
            flags.append("exited full screen repeatedly")
        out.append({"attempt_id": a.attempt_id, "user_id": u.id, "name": u.display_name, "status": a.attempt_status,
                    "earned": float(a.earned_marks or 0), "total": float(a.total_marks or 0),
                    "integrity": integ, "flags": flags, "started_at": _iso(a.attempt_started_at), "ended_at": _iso(a.attempt_ended_at)})
    return {"quiz_id": quiz_id, "attempts": out, "flagged": sum(1 for r in out if r["flags"])}
