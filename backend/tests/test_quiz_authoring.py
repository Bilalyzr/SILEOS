"""Quiz authoring — Tasks 1-2 of the Quiz & Assessment Engine fix wave
(spec docs/superpowers/specs/2026-09-03-quiz-engine-design.md, R4/F6 and R7/F9).

Task 1 covers persisting/reading the quiz feedback policy:
  - create_quiz / update_quiz read `feedbackMode` from the payload and
    persist it into `quiz_feedback_mode`.
  - get_quiz returns a top-level `feedbackMode`.
  - normalize_feedback_mode() defaults None/absent/legacy ("default") to
    "reveal_immediate" and passes through the three valid modes verbatim.

Task 2 covers server-side question payload validation (R7):
  - _validate_questions() raises HTTPException(422, {"code", "message",
    "index"}) on the first invalid question in a list.
  - create_quiz / update_quiz call it BEFORE any write — an invalid
    question anywhere in the payload means nothing persists/changes.
  - add_question_to_quiz validates the single question identically and
    422s on malformed `question_options` JSON instead of silently
    swallowing the error (audit A7).
"""
import json

import pytest

from app.routers.quizzes import normalize_feedback_mode, _validate_questions


# ----- factories (mirrors test_assessment_integrity.py's setup style) -------


def _make_approved_instructor(db, make_user, email="quiz_author@example.com"):
    """make_user(role="instructor") + an approved InstructorProfile, so
    auth_headers(email) can log in (login blocks unapproved instructors)."""
    from app.models.user import InstructorProfile

    instructor = make_user(role="instructor", email=email)
    db.add(InstructorProfile(user_id=instructor.id, is_approved=True))
    db.commit()
    return instructor


def _make_course(db, instructor, title="Quiz Authoring Course"):
    from app.models.course import Course

    course = Course(
        post_author=instructor.id,
        post_title=title,
        post_content="content",
        post_excerpt="excerpt",
        post_status="published",
        post_name=title.lower().replace(" ", "-"),
        course_thumbnail="",
        course_price=0,
        course_level="beginner",
        course_category="Meiporul",
        course_language="English",
        course_duration="10",
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture()
def instructor_client(client, db, make_user, auth_headers):
    """An approved instructor plus headers to act as them via `client`."""
    instructor = _make_approved_instructor(db, make_user)
    headers = auth_headers(instructor.user_email, instructor._test_password)

    class _InstructorClient:
        def post(self, url, **kwargs):
            kwargs.setdefault("headers", headers)
            return client.post(url, **kwargs)

        def put(self, url, **kwargs):
            kwargs.setdefault("headers", headers)
            return client.put(url, **kwargs)

        def get(self, url, **kwargs):
            kwargs.setdefault("headers", headers)
            return client.get(url, **kwargs)

    _InstructorClient.instructor = instructor
    return _InstructorClient()


@pytest.fixture()
def seeded_course(db, instructor_client):
    """A course owned by `instructor_client`'s instructor. Task 1's brief
    hardcodes /courses/1/quizzes — on the fresh per-test in-memory SQLite
    DB this is the first (and only) course, so its id is 1."""
    course = _make_course(db, instructor_client.instructor)
    assert course.id == 1
    return course


# ----- feedback policy: persist + read --------------------------------------


class TestFeedbackModePersistence:
    def test_create_quiz_persists_feedback_mode(self, instructor_client, seeded_course):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "T", "feedbackMode": "reveal_after_due",
            "questions": [{"type": "true_false", "question": "2+2=4",
                           "correctAnswer": "true", "points": 1}]})
        assert r.status_code in (200, 201), r.text
        q = instructor_client.get("/api/v1/courses/1/quizzes/%d" % r.json()["id"]).json()
        assert q["feedbackMode"] == "reveal_after_due"

    def test_create_quiz_defaults_feedback_mode_when_absent(self, instructor_client, seeded_course):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "No mode given",
            "questions": [{"type": "true_false", "question": "2+2=4",
                           "correctAnswer": "true", "points": 1}]})
        assert r.status_code in (200, 201), r.text
        q = instructor_client.get("/api/v1/courses/1/quizzes/%d" % r.json()["id"]).json()
        assert q["feedbackMode"] == "reveal_immediate"

    def test_update_quiz_persists_feedback_mode(self, instructor_client, seeded_course):
        create = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "T", "feedbackMode": "reveal_immediate",
            "questions": [{"type": "true_false", "question": "2+2=4",
                           "correctAnswer": "true", "points": 1}]})
        assert create.status_code in (200, 201), create.text
        quiz_id = create.json()["id"]

        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json={
            "title": "T", "feedbackMode": "reveal_never",
            "questions": [{"type": "true_false", "question": "2+2=4",
                           "correctAnswer": "true", "points": 1}]})
        assert r.status_code == 200, r.text

        q = instructor_client.get(f"/api/v1/courses/1/quizzes/{quiz_id}").json()
        assert q["feedbackMode"] == "reveal_never"

    def test_update_quiz_preserves_feedback_mode_when_absent(self, instructor_client, seeded_course):
        """A PUT that omits `feedbackMode` must PRESERVE the existing policy,
        not silently reset it to the default (absent-key bug class)."""
        create = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "T", "feedbackMode": "reveal_never",
            "questions": [{"type": "true_false", "question": "2+2=4",
                           "correctAnswer": "true", "points": 1}]})
        assert create.status_code in (200, 201), create.text
        quiz_id = create.json()["id"]

        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json={
            "title": "T",
            "questions": [{"type": "true_false", "question": "2+2=4",
                           "correctAnswer": "true", "points": 1}]})
        assert r.status_code == 200, r.text

        q = instructor_client.get(f"/api/v1/courses/1/quizzes/{quiz_id}").json()
        assert q["feedbackMode"] == "reveal_never"


# ----- normalize_feedback_mode() unit tests ----------------------------------


def test_feedback_mode_defaults_and_legacy():
    assert normalize_feedback_mode(None) == "reveal_immediate"
    assert normalize_feedback_mode("default") == "reveal_immediate"
    assert normalize_feedback_mode("reveal_never") == "reveal_never"


def test_feedback_mode_all_valid_values_pass_through():
    assert normalize_feedback_mode("reveal_immediate") == "reveal_immediate"
    assert normalize_feedback_mode("reveal_after_due") == "reveal_after_due"
    assert normalize_feedback_mode("reveal_never") == "reveal_never"


def test_feedback_mode_rejects_garbage():
    assert normalize_feedback_mode("bogus") == "reveal_immediate"
    assert normalize_feedback_mode(123) == "reveal_immediate"
    assert normalize_feedback_mode("") == "reveal_immediate"


# ----- _validate_questions() unit tests (spec R7) ----------------------------


def _q(**overrides):
    """A valid multiple_choice question, with overrides applied."""
    base = {
        "type": "multiple_choice",
        "question": "2+2=?",
        "options": ["3", "4", "5"],
        "correctAnswer": 1,
        "points": 1,
    }
    base.update(overrides)
    return base


class TestValidateQuestionsUnit:
    def test_valid_multiple_choice_passes(self):
        _validate_questions([_q()])  # no raise

    def test_bad_type_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(type="essay_wrong")])
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "invalid_type"
        assert exc.value.detail["index"] == 0

    def test_mcq_too_few_options(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(options=["only one"], correctAnswer=0)])
        assert exc.value.detail["code"] == "too_few_options"

    def test_mcq_empty_option_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(options=["4", "   ", "5"])])
        assert exc.value.detail["code"] == "empty_option"

    def test_mcq_correct_index_out_of_range(self):
        """The silent-unscorable case: correctAnswer beyond the option list."""
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(options=["a", "b", "c", "d"], correctAnswer=9)])
        assert exc.value.detail["code"] == "correct_index_out_of_range"

    def test_mcq_correct_answer_string_rejected_no_coercion(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(correctAnswer="1")])
        assert exc.value.detail["code"] == "correct_index_not_integer"

    def test_mcq_correct_answer_float_string_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(correctAnswer="1.9")])
        assert exc.value.detail["code"] == "correct_index_not_integer"

    def test_mcq_correct_answer_float_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(correctAnswer=1.9)])
        assert exc.value.detail["code"] == "correct_index_not_integer"

    def test_mcq_correct_answer_integer_valued_float_rejected(self):
        """1.0 must not silently pass as index 1 — no coercion allowed."""
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(correctAnswer=1.0)])
        assert exc.value.detail["code"] == "correct_index_not_integer"

    def test_mcq_correct_answer_bool_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(correctAnswer=True)])
        assert exc.value.detail["code"] == "correct_index_not_integer"

    def test_true_false_valid(self):
        _validate_questions([_q(type="true_false", options=[], correctAnswer="true")])
        _validate_questions([_q(type="true_false", options=[], correctAnswer="false")])

    def test_true_false_invalid_value_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(type="true_false", options=[], correctAnswer="maybe")])
        assert exc.value.detail["code"] == "true_false_invalid"

    def test_true_false_bool_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(type="true_false", options=[], correctAnswer=True)])
        assert exc.value.detail["code"] == "true_false_invalid"

    def test_fill_in_blank_valid(self):
        _validate_questions([_q(type="fill_in_blank", options=[], correctAnswer="Paris")])

    def test_fill_in_blank_empty_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(type="fill_in_blank", options=[], correctAnswer="   ")])
        assert exc.value.detail["code"] == "fill_in_blank_empty"

    def test_fill_in_blank_too_long_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(type="fill_in_blank", options=[], correctAnswer="x" * 201)])
        assert exc.value.detail["code"] == "fill_in_blank_too_long"

    def test_fill_in_blank_exactly_200_chars_ok(self):
        _validate_questions([_q(type="fill_in_blank", options=[], correctAnswer="x" * 200)])

    def test_short_answer_empty_correct_answer_ok(self):
        """R8: empty correctAnswer on short_answer becomes manual-graded —
        validation must allow it, not reject it."""
        _validate_questions([_q(type="short_answer", options=[], correctAnswer="")])
        _validate_questions([_q(type="short_answer", options=[])])

    def test_essay_with_zero_options_ok(self):
        _validate_questions([_q(type="essay", options=[])])

    def test_points_missing_rejected(self):
        q = _q()
        del q["points"]
        with pytest.raises(Exception) as exc:
            _validate_questions([q])
        assert exc.value.detail["code"] == "points_missing"

    def test_points_zero_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(points=0)])
        assert exc.value.detail["code"] == "points_out_of_range"

    def test_points_1001_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(points=1001)])
        assert exc.value.detail["code"] == "points_out_of_range"

    def test_points_boundary_1_ok(self):
        _validate_questions([_q(points=1)])

    def test_points_boundary_1000_ok(self):
        _validate_questions([_q(points=1000)])

    def test_points_float_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(points=1.5)])
        assert exc.value.detail["code"] == "points_out_of_range"

    def test_multi_select_valid(self):
        _validate_questions([_q(
            type="multi_select", options=["a", "b", "c"], correctAnswer=None,
            correctAnswers=[0, 2],
        )])

    def test_multi_select_empty_list_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(
                type="multi_select", options=["a", "b", "c"], correctAnswer=None,
                correctAnswers=[],
            )])
        assert exc.value.detail["code"] == "multi_select_invalid"

    def test_multi_select_out_of_range_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(
                type="multi_select", options=["a", "b", "c"], correctAnswer=None,
                correctAnswers=[0, 9],
            )])
        assert exc.value.detail["code"] == "multi_select_invalid"

    def test_multi_select_duplicate_indices_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(
                type="multi_select", options=["a", "b", "c"], correctAnswer=None,
                correctAnswers=[0, 0],
            )])
        assert exc.value.detail["code"] == "multi_select_invalid"

    def test_multi_select_non_integer_rejected(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(
                type="multi_select", options=["a", "b", "c"], correctAnswer=None,
                correctAnswers=["0"],
            )])
        assert exc.value.detail["code"] == "multi_select_invalid"

    def test_second_question_index_reported(self):
        with pytest.raises(Exception) as exc:
            _validate_questions([_q(), _q(correctAnswer=9)])
        assert exc.value.detail["index"] == 1


# ----- create_quiz / update_quiz enforce validation via the API -------------


class TestQuizValidationViaApi:
    def test_create_quiz_rejects_out_of_range_correct_answer(self, instructor_client, seeded_course):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Bad quiz",
            "questions": [{
                "type": "multiple_choice", "question": "Q1",
                "options": ["a", "b", "c", "d"], "correctAnswer": 9, "points": 1,
            }],
        })
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "correct_index_out_of_range"

    def test_create_quiz_rejects_coerced_string_index(self, instructor_client, seeded_course):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Bad quiz",
            "questions": [{
                "type": "multiple_choice", "question": "Q1",
                "options": ["a", "b"], "correctAnswer": "1.9", "points": 1,
            }],
        })
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "correct_index_not_integer"

    def test_create_quiz_rejects_points_zero(self, instructor_client, seeded_course):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Bad quiz",
            "questions": [{
                "type": "true_false", "question": "Q1",
                "correctAnswer": "true", "points": 0,
            }],
        })
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "points_out_of_range"

    def test_create_quiz_rejects_points_1001(self, instructor_client, seeded_course):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Bad quiz",
            "questions": [{
                "type": "true_false", "question": "Q1",
                "correctAnswer": "true", "points": 1001,
            }],
        })
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "points_out_of_range"

    def test_create_quiz_essay_zero_options_ok(self, instructor_client, seeded_course):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Essay quiz",
            "questions": [{
                "type": "essay", "question": "Discuss.", "points": 5,
            }],
        })
        assert r.status_code in (200, 201), r.text

    def test_create_quiz_one_bad_question_persists_nothing(self, instructor_client, db, seeded_course):
        """A payload with one bad question among good ones must persist
        NOTHING — no quiz row, no question rows."""
        from app.models.quiz import Quiz

        before_count = db.query(Quiz).filter(Quiz.post_parent == 1).count()

        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Mixed quiz",
            "questions": [
                {"type": "true_false", "question": "Good Q",
                 "correctAnswer": "true", "points": 1},
                {"type": "multiple_choice", "question": "Bad Q",
                 "options": ["a", "b"], "correctAnswer": 9, "points": 1},
            ],
        })
        assert r.status_code == 422, r.text

        after_count = db.query(Quiz).filter(Quiz.post_parent == 1).count()
        assert after_count == before_count

    def test_update_quiz_one_bad_question_changes_nothing(self, instructor_client, seeded_course):
        create = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Original title",
            "questions": [{
                "type": "true_false", "question": "Q1",
                "correctAnswer": "true", "points": 1,
            }],
        })
        assert create.status_code in (200, 201), create.text
        quiz_id = create.json()["id"]
        before = instructor_client.get(f"/api/v1/courses/1/quizzes/{quiz_id}").json()

        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json={
            "title": "Changed title should not persist",
            "questions": [
                {"type": "true_false", "question": "Q1 edited",
                 "correctAnswer": "true", "points": 1},
                {"type": "multiple_choice", "question": "Bad Q",
                 "options": ["a", "b"], "correctAnswer": 9, "points": 1},
            ],
        })
        assert r.status_code == 422, r.text

        after = instructor_client.get(f"/api/v1/courses/1/quizzes/{quiz_id}").json()
        assert after["title"] == before["title"] == "Original title"
        assert len(after["questions"]) == len(before["questions"]) == 1
        assert after["questions"][0]["question"] == "Q1"


# ----- add_question_to_quiz validates + handles malformed JSON --------------


class TestAddQuestionToQuiz:
    def _create_empty_quiz(self, instructor_client):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Quiz for add-question tests", "questions": [],
        })
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    def test_add_question_valid_mcq(self, instructor_client, seeded_course):
        quiz_id = self._create_empty_quiz(instructor_client)
        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Q1",
            "question_type": "multiple_choice",
            "question_mark": 2,
            "question_options": json.dumps({"options": ["a", "b"], "correct_answer": 1}),
        })
        assert r.status_code == 200, r.text

    def test_add_question_malformed_json_rejected_no_row_written(self, instructor_client, db, seeded_course):
        from app.models.quiz import QuizQuestion

        quiz_id = self._create_empty_quiz(instructor_client)
        before_count = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).count()

        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Q1",
            "question_type": "multiple_choice",
            "question_mark": 2,
            "question_options": "{not valid json",
        })
        assert r.status_code == 422, r.text

        after_count = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).count()
        assert after_count == before_count

    def test_add_question_out_of_range_correct_answer_rejected(self, instructor_client, seeded_course):
        quiz_id = self._create_empty_quiz(instructor_client)
        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Q1",
            "question_type": "multiple_choice",
            "question_mark": 1,
            "question_options": json.dumps({"options": ["a", "b"], "correct_answer": 9}),
        })
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "correct_index_out_of_range"

    def test_add_question_points_out_of_range_rejected(self, instructor_client, seeded_course):
        quiz_id = self._create_empty_quiz(instructor_client)
        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Q1",
            "question_type": "multiple_choice",
            "question_mark": 0,
            "question_options": json.dumps({"options": ["a", "b"], "correct_answer": 0}),
        })
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "points_out_of_range"

    # ----- controller add-on: per-type parity with create_quiz ---------------
    # add_question_to_quiz normalizes its flat payload into the same
    # canonical dict create_quiz/update_quiz use and writes through the
    # same _build_answer_rows helper — these prove that holds for every
    # type, not just multiple_choice/multi_select (already covered in
    # TestUnifiedQuestionWriter).

    def test_add_question_true_false_writes_answer_rows(self, instructor_client, db, seeded_course):
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        quiz_id = self._create_empty_quiz(instructor_client)
        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Is the sky blue?",
            "question_type": "true_false",
            "question_mark": 2,
            "correctAnswer": "false",
        })
        assert r.status_code == 200, r.text

        question = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).one()
        assert question.question_type == "true_false"
        rows = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).order_by(QuizQuestionAnswer.answer_order).all()
        assert [(r_.answer_title, r_.is_correct) for r_ in rows] == [
            ("True", False), ("False", True)
        ]

    def test_add_question_fill_in_blank_writes_answer_row(self, instructor_client, db, seeded_course):
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        quiz_id = self._create_empty_quiz(instructor_client)
        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Capital of France?",
            "question_type": "fill_in_blank",
            "question_mark": 3,
            "correctAnswer": "Paris",
        })
        assert r.status_code == 200, r.text

        question = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).one()
        rows = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).all()
        assert [(r_.answer_title, r_.is_correct) for r_ in rows] == [("Paris", True)]

    def test_add_question_short_answer_no_correct_answer_writes_no_rows(
        self, instructor_client, db, seeded_course
    ):
        """short_answer with an empty correctAnswer is manual-graded (R8) —
        no QuizQuestionAnswer row, matching create_quiz's behavior."""
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        quiz_id = self._create_empty_quiz(instructor_client)
        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Explain briefly",
            "question_type": "short_answer",
            "question_mark": 5,
        })
        assert r.status_code == 200, r.text

        question = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).one()
        assert question.question_type == "short_answer"
        assert db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).count() == 0

    def test_add_question_essay_writes_no_answer_rows(self, instructor_client, db, seeded_course):
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        quiz_id = self._create_empty_quiz(instructor_client)
        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Discuss at length",
            "question_type": "essay",
            "question_mark": 20,
        })
        assert r.status_code == 200, r.text

        question = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).one()
        assert question.question_type == "essay"
        assert db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).count() == 0


# =============================================================================
# Task 3 - transactional writes + question identity preservation (R5/R6, F7)
#
#   - ABSENT-KEY RULE (audit A1): a PUT without a "questions" key leaves
#     questions+answers completely untouched; "questions": [] present is an
#     explicit request to remove all.
#   - SINGLE TRANSACTION (R5): create_quiz/update_quiz commit exactly once,
#     at the end; any failure rolls back with nothing persisted/changed.
#   - IDENTITY PRESERVATION (R6): existing QuizQuestion rows are patched in
#     place matched by question_order position so quiz_attempt_answers
#     .question_id references survive edits; extra incoming questions insert
#     with new ids; dropping questions is a 409 when the quiz has attempts.
#   - B8/F8: JSON columns hold real dicts (no double-encoding), reads are
#     tolerant of legacy double-encoded values.
# =============================================================================


def _tf(question="2+2=4", correct="true", points=1, explanation=""):
    return {
        "type": "true_false",
        "question": question,
        "correctAnswer": correct,
        "points": points,
        "explanation": explanation,
    }


def _mc(question="Pick", options=None, correct=0, points=1, explanation=""):
    return {
        "type": "multiple_choice",
        "question": question,
        "options": options if options is not None else ["a", "b", "c"],
        "correctAnswer": correct,
        "points": points,
        "explanation": explanation,
    }


def _three_question_payload():
    return {
        "title": "Three-question quiz",
        "description": "desc",
        "timeLimit": 30,
        "questions": [
            _mc("Q1", ["alpha", "beta", "gamma"], 2, 3, "because gamma"),
            _tf("Q2", "false", 2, "because false"),
            {"type": "fill_in_blank", "question": "Q3",
             "correctAnswer": "answer3", "points": 4, "explanation": "e3"},
        ],
    }


def _create_three_question_quiz(instructor_client):
    r = instructor_client.post("/api/v1/courses/1/quizzes",
                               json=_three_question_payload())
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _snapshot(instructor_client, quiz_id):
    """Full owner-visible question view - ids, titles, options, correct
    answers, points, explanations."""
    r = instructor_client.get(f"/api/v1/courses/1/quizzes/{quiz_id}")
    assert r.status_code == 200, r.text
    return r.json()


def _seed_attempt(db, quiz_id, course_id, student_id, question_ids):
    """One submitted attempt with a QuizAttemptAnswer per question."""
    from app.models.quiz import QuizAttempt, QuizAttemptAnswer

    attempt = QuizAttempt(
        user_id=student_id,
        quiz_id=quiz_id,
        course_id=course_id,
        total_questions=len(question_ids),
        total_answered_questions=len(question_ids),
        total_marks=len(question_ids),
        earned_marks=len(question_ids),
        attempt_info={},
        attempt_status="attempt_ended",
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    for qid in question_ids:
        db.add(QuizAttemptAnswer(
            user_id=student_id,
            quiz_id=quiz_id,
            question_id=int(qid),
            quiz_attempt_id=attempt.attempt_id,
            given_answer="x",
            question_mark=1,
            achieved_mark=1,
            is_correct=True,
        ))
    db.commit()
    return attempt


# ----- A1: absent "questions" key leaves the question bank untouched --------


class TestAbsentQuestionsKey:
    def test_duration_only_put_preserves_questions(self, instructor_client, seeded_course):
        """THE regression test for audit A1: the curriculum tab's
        duration-only PUT {"timeLimit": 45} must not touch questions."""
        quiz_id = _create_three_question_quiz(instructor_client)
        before = _snapshot(instructor_client, quiz_id)
        assert len(before["questions"]) == 3

        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}",
                                  json={"timeLimit": 45})
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)
        assert after["timeLimit"] == 45
        # Byte-identical questions: ids, titles, options, correct answers,
        # points and explanations all survive.
        assert after["questions"] == before["questions"]

    def test_absent_questions_key_preserves_other_metadata_edits(
        self, instructor_client, seeded_course
    ):
        quiz_id = _create_three_question_quiz(instructor_client)
        before = _snapshot(instructor_client, quiz_id)

        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}",
                                  json={"title": "Renamed", "passingScore": 55})
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)
        assert after["title"] == "Renamed"
        assert after["passingScore"] == 55
        assert after["questions"] == before["questions"]

    def test_explicit_empty_list_deletes_all_when_no_attempts(
        self, instructor_client, db, seeded_course
    ):
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        quiz_id = _create_three_question_quiz(instructor_client)

        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}",
                                  json={"questions": []})
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)
        assert after["questions"] == []
        assert db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id).count() == 0
        # Answer rows go with them (no orphans).
        assert db.query(QuizQuestionAnswer).count() == 0


# ----- R6: identity preservation --------------------------------------------


class TestQuestionIdentityPreservation:
    def test_edit_preserves_question_ids(self, instructor_client, seeded_course):
        quiz_id = _create_three_question_quiz(instructor_client)
        before_ids = [q["id"] for q in _snapshot(instructor_client, quiz_id)["questions"]]

        payload = _three_question_payload()
        payload["questions"][0]["question"] = "Q1 edited"
        payload["questions"][0]["points"] = 7
        payload["questions"][0]["explanation"] = "new explanation"
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert [q["id"] for q in after] == before_ids
        assert after[0]["question"] == "Q1 edited"
        assert after[0]["points"] == 7.0
        assert after[0]["explanation"] == "new explanation"

    def test_edit_updates_options_and_correct_answer_in_place(
        self, instructor_client, seeded_course
    ):
        quiz_id = _create_three_question_quiz(instructor_client)
        before_ids = [q["id"] for q in _snapshot(instructor_client, quiz_id)["questions"]]

        payload = _three_question_payload()
        payload["questions"][0]["options"] = ["one", "two", "three", "four"]
        payload["questions"][0]["correctAnswer"] = 3
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert [q["id"] for q in after] == before_ids
        assert after[0]["options"] == ["one", "two", "three", "four"]
        assert after[0]["correctAnswer"] == 3

    def test_appended_question_gets_new_id(self, instructor_client, seeded_course):
        quiz_id = _create_three_question_quiz(instructor_client)
        before_ids = [q["id"] for q in _snapshot(instructor_client, quiz_id)["questions"]]

        payload = _three_question_payload()
        payload["questions"].append(_tf("Q4 appended", "true", 5))
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert len(after) == 4
        assert [q["id"] for q in after[:3]] == before_ids
        assert after[3]["id"] not in before_ids
        assert after[3]["question"] == "Q4 appended"

    def test_type_change_in_place_rewrites_answers(self, instructor_client, seeded_course):
        """Changing a question's type at the same position keeps its id and
        replaces its answer rows with the new type's."""
        quiz_id = _create_three_question_quiz(instructor_client)
        before_ids = [q["id"] for q in _snapshot(instructor_client, quiz_id)["questions"]]

        payload = _three_question_payload()
        payload["questions"][1] = _mc("Q2 now MC", ["p", "q"], 1, 2)
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert after[1]["id"] == before_ids[1]
        assert after[1]["type"] == "multiple_choice"
        assert after[1]["options"] == ["p", "q"]
        assert after[1]["correctAnswer"] == 1

    def test_shrink_allowed_when_no_attempts(self, instructor_client, seeded_course):
        quiz_id = _create_three_question_quiz(instructor_client)
        before_ids = [q["id"] for q in _snapshot(instructor_client, quiz_id)["questions"]]

        payload = _three_question_payload()
        payload["questions"] = payload["questions"][:2]
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert [q["id"] for q in after] == before_ids[:2]


# ----- R6: 409 when dropping a question from a quiz that has attempts -------


class TestDropQuestionWithAttempts:
    def _setup(self, instructor_client, db, make_user):
        quiz_id = _create_three_question_quiz(instructor_client)
        qids = [q["id"] for q in _snapshot(instructor_client, quiz_id)["questions"]]
        student = make_user(role="student", email="quiz_taker@example.com")
        _seed_attempt(db, quiz_id, 1, student.id, qids)
        return quiz_id, qids

    def test_shrink_with_attempts_returns_409(
        self, instructor_client, db, make_user, seeded_course
    ):
        quiz_id, qids = self._setup(instructor_client, db, make_user)

        payload = _three_question_payload()
        payload["questions"] = payload["questions"][:2]   # drop last question
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)

        assert r.status_code == 409, r.text
        detail = r.json()["detail"]
        assert detail["code"] == "question_has_attempts"
        assert detail["blocked_question_ids"] == [int(qids[2])]
        assert detail["removable_question_ids"] == []
        assert "message" in detail

    def test_explicit_empty_list_with_attempts_returns_409(
        self, instructor_client, db, make_user, seeded_course
    ):
        quiz_id, qids = self._setup(instructor_client, db, make_user)

        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}",
                                  json={"questions": []})
        assert r.status_code == 409, r.text
        detail = r.json()["detail"]
        assert detail["code"] == "question_has_attempts"
        assert detail["blocked_question_ids"] == [int(q) for q in qids]
        assert detail["removable_question_ids"] == []

    def test_409_writes_nothing(
        self, instructor_client, db, make_user, seeded_course
    ):
        quiz_id, _ = self._setup(instructor_client, db, make_user)
        before = _snapshot(instructor_client, quiz_id)

        payload = _three_question_payload()
        payload["title"] = "Should not persist"
        payload["questions"] = payload["questions"][:1]
        payload["questions"][0]["question"] = "Edited, should not persist"
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 409, r.text

        after = _snapshot(instructor_client, quiz_id)
        assert after["title"] == before["title"]
        assert after["questions"] == before["questions"]

    def test_quiz_with_attempts_can_still_add_and_modify(
        self, instructor_client, db, make_user, seeded_course
    ):
        """Binding: a quiz with >=1 attempt cannot DROP questions, but it
        can add and modify them."""
        quiz_id, qids = self._setup(instructor_client, db, make_user)

        payload = _three_question_payload()
        payload["questions"][0]["question"] = "Q1 edited with attempts present"
        payload["questions"].append(_tf("Q4 added with attempts present", "true", 1))
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert [q["id"] for q in after[:3]] == qids
        assert after[0]["question"] == "Q1 edited with attempts present"
        assert len(after) == 4

    def test_attempt_answers_still_resolve_after_edit(
        self, instructor_client, db, make_user, seeded_course
    ):
        """The whole point of R6: historical attempt answers must still
        join to a live question row after the quiz is edited."""
        from app.models.quiz import QuizAttemptAnswer, QuizQuestion

        quiz_id, qids = self._setup(instructor_client, db, make_user)

        payload = _three_question_payload()
        payload["questions"][0]["question"] = "Reworded prompt"
        payload["questions"][2]["correctAnswer"] = "different"
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 200, r.text

        rows = db.query(QuizAttemptAnswer).filter(
            QuizAttemptAnswer.quiz_id == quiz_id).all()
        assert len(rows) == 3
        for row in rows:
            question = db.query(QuizQuestion).filter(
                QuizQuestion.question_id == row.question_id).first()
            assert question is not None, "attempt answer orphaned by edit"
            assert question.quiz_id == quiz_id


# ----- R5: single transaction ------------------------------------------------


class TestSingleTransaction:
    def test_create_and_update_commit_exactly_once(self):
        """grep-proof: neither function body may contain more than one
        db.commit() call (and none inside a loop)."""
        import inspect
        from app.routers import quizzes as quizzes_module

        for fn in (quizzes_module.create_quiz, quizzes_module.update_quiz):
            source = inspect.getsource(fn)
            count = source.count("db.commit()")
            assert count == 1, (
                f"{fn.__name__} contains {count} db.commit() calls; R5 requires exactly 1"
            )

    def test_create_rolls_back_everything_on_mid_write_failure(
        self, instructor_client, db, monkeypatch, seeded_course
    ):
        """Fail on the Nth question write -> no quiz row, no question rows."""
        from app.models.quiz import Quiz, QuizQuestion

        before_quizzes = db.query(Quiz).count()
        before_questions = db.query(QuizQuestion).count()

        calls = {"n": 0}
        real_init = QuizQuestion.__init__

        def _boom(self, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected failure on 2nd question")
            return real_init(self, *args, **kwargs)

        monkeypatch.setattr(QuizQuestion, "__init__", _boom)

        with pytest.raises(RuntimeError):
            instructor_client.post("/api/v1/courses/1/quizzes",
                                   json=_three_question_payload())

        monkeypatch.undo()
        db.expire_all()
        assert db.query(Quiz).count() == before_quizzes
        assert db.query(QuizQuestion).count() == before_questions

    def test_update_rolls_back_everything_on_mid_write_failure(
        self, instructor_client, db, monkeypatch, seeded_course
    ):
        """Fail partway through an update -> original quiz state intact."""
        from app.models.quiz import QuizQuestionAnswer

        quiz_id = _create_three_question_quiz(instructor_client)
        before = _snapshot(instructor_client, quiz_id)

        # Inject on the model's __init__ rather than the module attribute:
        # `db.query(QuizQuestionAnswer)` also reads that attribute, and a
        # plain function there breaks SQLAlchemy's query construction.
        calls = {"n": 0}
        real_init = QuizQuestionAnswer.__init__

        def _boom(self, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected failure on 2nd answer row")
            return real_init(self, *args, **kwargs)

        monkeypatch.setattr(QuizQuestionAnswer, "__init__", _boom)

        payload = _three_question_payload()
        payload["title"] = "Should roll back"
        payload["questions"][0]["question"] = "Should roll back too"
        payload["questions"][0]["options"] = ["z1", "z2", "z3"]
        with pytest.raises(RuntimeError):
            instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)

        monkeypatch.undo()
        db.expire_all()
        after = _snapshot(instructor_client, quiz_id)
        assert after["title"] == before["title"]
        assert after["questions"] == before["questions"]

    def test_session_reusable_after_rollback_for_a_later_successful_request(
        self, instructor_client, db, monkeypatch, seeded_course
    ):
        """Controller add-on: a request that fails mid-write and rolls back
        must not leave the underlying connection/session wedged for the
        NEXT request. `client`'s DB dependency opens a fresh Session per
        request (see conftest.py's `_get_db`) against the same StaticPool
        connection — this proves that a crashed request's session.close()
        actually releases things cleanly, so an immediately-following
        request on the same shared connection succeeds normally rather
        than hitting a locked table / dangling transaction."""
        from app.models.quiz import QuizQuestion

        calls = {"n": 0}
        real_init = QuizQuestion.__init__

        def _boom_once(self, *args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected failure on 2nd question")
            return real_init(self, *args, **kwargs)

        monkeypatch.setattr(QuizQuestion, "__init__", _boom_once)
        with pytest.raises(RuntimeError):
            instructor_client.post("/api/v1/courses/1/quizzes", json=_three_question_payload())
        monkeypatch.undo()

        # Nothing from the failed request persisted...
        db.expire_all()
        assert db.query(QuizQuestion).count() == 0

        # ...and a fresh request on the same client/connection succeeds
        # cleanly, proving the session from the failed request didn't wedge
        # anything for this one.
        r = instructor_client.post(
            "/api/v1/courses/1/quizzes", json=_three_question_payload()
        )
        assert r.status_code in (200, 201), r.text
        quiz_id = r.json()["id"]

        db.expire_all()
        assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).count() == 3

        # And a plain read also works (separate request, separate session).
        after = _snapshot(instructor_client, quiz_id)
        assert len(after["questions"]) == 3


# ----- B8/F8: JSON columns hold real values, reads tolerate legacy -----------


class TestJsonColumnEncoding:
    def test_question_settings_stored_as_real_dict(
        self, instructor_client, db, seeded_course
    ):
        from app.models.quiz import QuizQuestion

        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Image quiz",
            "questions": [_mc("Q1", ["a", "b"], 0, 1)],
        })
        assert r.status_code in (200, 201), r.text
        quiz_id = r.json()["id"]

        question = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id).first()
        assert isinstance(question.question_settings, dict), (
            "question_settings must be a real dict, not a JSON-encoded string"
        )

    def test_image_url_survives_create_and_read(self, instructor_client, seeded_course):
        q = _mc("Q1", ["a", "b"], 0, 1)
        q["imageUrl"] = "https://cdn.example.com/pic.png"
        r = instructor_client.post("/api/v1/courses/1/quizzes",
                                   json={"title": "Image quiz", "questions": [q]})
        assert r.status_code in (200, 201), r.text
        quiz_id = r.json()["id"]

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert after[0]["imageUrl"] == "https://cdn.example.com/pic.png"

    def test_image_url_survives_update(self, instructor_client, seeded_course):
        quiz_id = _create_three_question_quiz(instructor_client)
        payload = _three_question_payload()
        payload["questions"][0]["imageUrl"] = "https://cdn.example.com/updated.png"
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json=payload)
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert after[0]["imageUrl"] == "https://cdn.example.com/updated.png"

    def test_get_quiz_reads_legacy_double_encoded_settings(
        self, instructor_client, db, seeded_course
    ):
        """Rows written by the old double-encoding code must still read."""
        from app.models.quiz import QuizQuestion

        quiz_id = _create_three_question_quiz(instructor_client)
        question = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id
        ).order_by(QuizQuestion.question_order).first()
        question.question_settings = json.dumps({"image_url": "legacy.png"})
        db.commit()

        after = _snapshot(instructor_client, quiz_id)["questions"]
        assert after[0]["imageUrl"] == "legacy.png"

    def test_get_quiz_attempt_reads_legacy_double_encoded_attempt_info(
        self, client, db, make_user, instructor_client, auth_headers, seeded_course
    ):
        """audit B8: the /attempt read path must go through the tolerant
        reader instead of a bare json.loads."""
        from app.models.quiz import QuizAttempt

        quiz_id = _create_three_question_quiz(instructor_client)
        student = make_user(role="student", email="legacy_reader@example.com")
        attempt = QuizAttempt(
            user_id=student.id, quiz_id=quiz_id, course_id=1,
            total_questions=3, total_answered_questions=3,
            total_marks=3, earned_marks=3,
            attempt_info=json.dumps({"1": "a"}),
            attempt_status="attempt_ended",
        )
        db.add(attempt)
        db.commit()

        headers = auth_headers(student.user_email, student._test_password)
        r = client.get(f"/api/v1/courses/1/quizzes/{quiz_id}/attempt", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["answers"] == {"1": "a"}

    def test_get_quiz_attempt_reads_real_dict_attempt_info(
        self, client, db, make_user, instructor_client, auth_headers, seeded_course
    ):
        """The same read must not 500 when attempt_info is a real dict."""
        from app.models.quiz import QuizAttempt

        quiz_id = _create_three_question_quiz(instructor_client)
        student = make_user(role="student", email="dict_reader@example.com")
        attempt = QuizAttempt(
            user_id=student.id, quiz_id=quiz_id, course_id=1,
            total_questions=3, total_answered_questions=3,
            total_marks=3, earned_marks=3,
            attempt_info={"1": "a"},
            attempt_status="attempt_ended",
        )
        db.add(attempt)
        db.commit()

        headers = auth_headers(student.user_email, student._test_password)
        r = client.get(f"/api/v1/courses/1/quizzes/{quiz_id}/attempt", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["answers"] == {"1": "a"}


# ----- unified question writer (one write path for all three endpoints) -----


class TestUnifiedQuestionWriter:
    def test_create_writes_fill_in_blank_answer_row(
        self, instructor_client, db, seeded_course
    ):
        """create_quiz used to skip fill_in_blank answer rows entirely (only
        update_quiz wrote them), so a fill_in_blank question created via POST
        was unscorable. The unified writer fixes that asymmetry."""
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "FIB quiz",
            "questions": [{"type": "fill_in_blank", "question": "Capital?",
                           "correctAnswer": "Paris", "points": 2}],
        })
        assert r.status_code in (200, 201), r.text
        quiz_id = r.json()["id"]

        question = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id).one()
        rows = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id).all()
        assert len(rows) == 1
        assert rows[0].answer_title == "Paris"
        assert rows[0].is_correct is True

    def test_create_and_update_write_identical_answer_rows(
        self, instructor_client, db, seeded_course
    ):
        """The same payload must produce the same answer rows whether it
        arrives via POST or PUT â€” one writer, one result."""
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        def _rows_for(quiz_id):
            out = []
            questions = db.query(QuizQuestion).filter(
                QuizQuestion.quiz_id == quiz_id
            ).order_by(QuizQuestion.question_order).all()
            for q in questions:
                answers = db.query(QuizQuestionAnswer).filter(
                    QuizQuestionAnswer.belongs_question_id == q.question_id
                ).order_by(QuizQuestionAnswer.answer_order).all()
                out.append([(a.belongs_question_type, a.answer_title,
                             a.is_correct, a.answer_order) for a in answers])
            return out

        created_id = _create_three_question_quiz(instructor_client)

        # An empty quiz brought to the same content by PUT.
        r = instructor_client.post("/api/v1/courses/1/quizzes",
                                   json={"title": "Empty", "questions": []})
        assert r.status_code in (200, 201), r.text
        updated_id = r.json()["id"]
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{updated_id}",
                                  json=_three_question_payload())
        assert r.status_code == 200, r.text

        db.expire_all()
        assert _rows_for(created_id) == _rows_for(updated_id)

    def test_add_question_endpoint_uses_shared_writer(
        self, instructor_client, db, seeded_course
    ):
        """POST /quizzes/{id}/questions writes through the same helper:
        question_settings lands as a real dict, not a raw string."""
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        r = instructor_client.post("/api/v1/courses/1/quizzes",
                                   json={"title": "Empty", "questions": []})
        quiz_id = r.json()["id"]

        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Q1",
            "question_type": "multiple_choice",
            "question_mark": 2,
            "question_options": json.dumps({"options": ["a", "b"], "correct_answer": 1}),
        })
        assert r.status_code == 200, r.text

        question = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id).one()
        assert isinstance(question.question_settings, dict)

        rows = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).order_by(QuizQuestionAnswer.answer_order).all()
        assert [(r_.answer_title, r_.is_correct) for r_ in rows] == [
            ("a", False), ("b", True)
        ]

    def test_add_question_commits_once(self):
        import inspect
        from app.routers import quizzes as quizzes_module

        source = inspect.getsource(quizzes_module.add_question_to_quiz)
        assert source.count("db.commit()") == 1

    def test_multi_select_create_writes_one_row_per_option(
        self, instructor_client, db, seeded_course
    ):
        """Task 4: multi_select now writes an answer row for every option,
        with is_correct=True on each index listed in correctAnswers — full
        parity with multiple_choice's per-option row writer."""
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Multi-select quiz",
            "questions": [{"type": "multi_select", "question": "Pick two",
                           "options": ["a", "b", "c"],
                           "correctAnswers": [0, 2], "points": 3}],
        })
        assert r.status_code in (200, 201), r.text
        quiz_id = r.json()["id"]

        question = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id).one()
        assert question.question_type == "multi_select"
        rows = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).order_by(QuizQuestionAnswer.answer_order).all()
        assert [(r_.answer_title, r_.is_correct) for r_ in rows] == [
            ("a", True), ("b", False), ("c", True)
        ]

    def test_multi_select_update_writes_answer_rows_in_place(
        self, instructor_client, db, seeded_course
    ):
        """PUT produces the same row shape as POST (unified writer parity),
        and patches the existing question row rather than recreating it."""
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        create = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Multi-select quiz",
            "questions": [{"type": "multi_select", "question": "Pick two",
                           "options": ["a", "b", "c"],
                           "correctAnswers": [0], "points": 3}],
        })
        assert create.status_code in (200, 201), create.text
        quiz_id = create.json()["id"]
        original_question_id = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id).one().question_id

        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}", json={
            "title": "Multi-select quiz",
            "questions": [{"type": "multi_select", "question": "Pick two",
                           "options": ["a", "b", "c"],
                           "correctAnswers": [1, 2], "points": 3}],
        })
        assert r.status_code == 200, r.text

        question = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id).one()
        assert question.question_id == original_question_id  # identity preserved (R6)
        rows = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).order_by(QuizQuestionAnswer.answer_order).all()
        assert [(r_.answer_title, r_.is_correct) for r_ in rows] == [
            ("a", False), ("b", True), ("c", True)
        ]

    def test_multi_select_add_question_endpoint_writes_answer_rows(
        self, instructor_client, db, seeded_course
    ):
        """POST /quizzes/{id}/questions (flat payload) normalizes correctly
        into the canonical dict and writes through the shared helper."""
        from app.models.quiz import QuizQuestion, QuizQuestionAnswer

        r = instructor_client.post("/api/v1/courses/1/quizzes",
                                   json={"title": "Empty", "questions": []})
        quiz_id = r.json()["id"]

        r = instructor_client.post(f"/api/v1/quizzes/{quiz_id}/questions", json={
            "question_title": "Pick two",
            "question_type": "multi_select",
            "question_mark": 3,
            "question_options": json.dumps({
                "options": ["a", "b", "c"], "correct_answers": [0, 2]
            }),
        })
        assert r.status_code == 200, r.text

        question = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id).one()
        rows = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == question.question_id
        ).order_by(QuizQuestionAnswer.answer_order).all()
        assert [(r_.answer_title, r_.is_correct) for r_ in rows] == [
            ("a", True), ("b", False), ("c", True)
        ]

    def test_multi_select_get_quiz_owner_sees_correct_answers_list(
        self, instructor_client, seeded_course
    ):
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Multi-select quiz",
            "questions": [{"type": "multi_select", "question": "Pick two",
                           "options": ["a", "b", "c"],
                           "correctAnswers": [0, 2], "points": 3}],
        })
        quiz_id = r.json()["id"]

        q = instructor_client.get(f"/api/v1/courses/1/quizzes/{quiz_id}").json()
        question = q["questions"][0]
        assert question["options"] == ["a", "b", "c"]
        assert question["correctAnswers"] == [0, 2]


# ----- open_ended is a first-class authoring type (manual-grade alias) -------


class TestOpenEndedAlias:
    def test_open_ended_passes_validation(self):
        _validate_questions([
            {"type": "open_ended", "question": "Discuss.", "points": 5}
        ])  # no raise

    def test_open_ended_quiz_round_trips_through_put(
        self, instructor_client, seeded_course
    ):
        """`open_ended` is a live MANUAL_GRADE_QUESTION_TYPES member, so such
        rows exist; the validator must not make them unsaveable."""
        r = instructor_client.post("/api/v1/courses/1/quizzes", json={
            "title": "Open ended quiz",
            "questions": [{"type": "open_ended", "question": "Explain.",
                           "points": 10, "explanation": "rubric"}],
        })
        assert r.status_code in (200, 201), r.text
        quiz_id = r.json()["id"]

        before = _snapshot(instructor_client, quiz_id)
        assert before["questions"][0]["type"] == "open_ended"

        payload = {"title": "Open ended quiz",
                   "questions": [{"type": "open_ended", "question": "Explain.",
                                  "points": 10, "explanation": "rubric"}]}
        r = instructor_client.put(f"/api/v1/courses/1/quizzes/{quiz_id}",
                                  json=payload)
        assert r.status_code == 200, r.text

        after = _snapshot(instructor_client, quiz_id)
        assert after["questions"][0]["id"] == before["questions"][0]["id"]
        assert after["questions"][0]["type"] == "open_ended"


def test_validation_errors_use_the_shared_422_helper():
    """Every 422 raised by the quiz authoring paths carries the same
    {code, message, index} shape via _validation_error()."""
    import inspect
    from app.routers import quizzes as quizzes_module

    source = inspect.getsource(quizzes_module.add_question_to_quiz)
    assert "HTTP_422_UNPROCESSABLE_ENTITY" not in source, (
        "add_question_to_quiz should raise via _validation_error(), not "
        "hand-rolled HTTPException(422, ...) blocks"
    )


def test_no_dead_option_helper_left_behind():
    """_non_empty_options() was defined but never called â€” deleted."""
    from app.routers import quizzes as quizzes_module

    assert not hasattr(quizzes_module, "_non_empty_options")
