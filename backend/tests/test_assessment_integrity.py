"""Assessment integrity hardening (Task 1 of the Learning Experience plan).

Covers spec docs/superpowers/specs/2026-09-02-learning-experience-design.md
section A1, items 1-11 (item 12 — rubric math — is Task 2; only the model
fields are asserted here):

  1. essay -> pending_review + instructor grade/finalize endpoints
  2. GET quiz answer-leak fix (students never see correctAnswer/explanation)
  3. server-side timer (+90s grace, pause extension)
  4. resume-existing-attempt on /start
  5. assignment deadline + late_policy (allow/block/penalty)
  6. assignment submit enrollment check
  7. assignment status lifecycle (create/update accept status; list/get/submit
     gate on published)
  8. per-assignment file upload validation (/upload/assignment-file)
  9. unique (assignment_id, user_id) constraint
  10. (frontend dead-path removal — out of scope for this backend suite)
  11. pause blocks answer writes
"""
import shutil
from datetime import datetime, timedelta, timezone

import pytest

from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizQuestion, QuizQuestionAnswer


@pytest.fixture(autouse=True)
def _clean_assignment_uploads_dir():
    """The per-test DB is a fresh in-memory SQLite instance (IDs restart at
    1 every test), but /assignment-file writes to the REAL filesystem under
    UPLOAD_DIR/assignments/{assignment_id}/ — without this, files from an
    earlier test's assignment id=1 pollute a later test's assignment id=1
    and defeat max_files / on-disk-existence assertions (I1/I4 regression
    tests). Clears before AND after each test so a failed run doesn't leave
    debris for the next.
    """
    from app.routers.uploads import UPLOAD_DIR

    assignments_dir = UPLOAD_DIR / "assignments"
    shutil.rmtree(assignments_dir, ignore_errors=True)
    yield
    shutil.rmtree(assignments_dir, ignore_errors=True)


def _upload_dir_for(assignment_id) -> "object":
    """The real on-disk directory /assignment-file writes an assignment's
    uploads to — used to assert a file was actually deleted/kept by the
    budget-reclaim logic, not just to check the HTTP response."""
    from app.routers.uploads import UPLOAD_DIR

    return UPLOAD_DIR / "assignments" / str(assignment_id)


# ----- factories -------------------------------------------------------------


def _make_instructor(db, email="instructor@example.com"):
    from app.models.user import User
    from app.core.security import get_password_hash

    u = User(
        user_login="ai_instructor", user_pass=get_password_hash("Test@123"),
        user_nicename="ai_instructor", user_email=email,
        display_name="AI Instructor", role="instructor", is_active=True, is_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    u._test_password = "Test@123"
    return u


def _approve_instructor(db, user):
    """Login (AuthService.authenticate_user) blocks any instructor role
    without an approved InstructorProfile row — create one so
    auth_headers(...) can actually log this instructor in."""
    from app.models.user import InstructorProfile

    profile = db.query(InstructorProfile).filter_by(user_id=user.id).first()
    if profile:
        profile.is_approved = True
    else:
        db.add(InstructorProfile(user_id=user.id, is_approved=True))
    db.commit()
    return user


def _make_approved_instructor(db, make_user, email):
    """make_user(role="instructor") + an approved InstructorProfile, so
    auth_headers(email) can log in (mirrors production's approval gate)."""
    instructor = make_user(role="instructor", email=email)
    return _approve_instructor(db, instructor)


def _admin_headers(client, db, admin):
    """Admin logins require TOTP 2FA — enrol a secret and send the current
    code (same pattern as test_backend_hygiene._admin_headers)."""
    import pyotp
    from app.core import totp

    admin.totp_enabled = True
    admin.totp_secret = totp.generate_secret()
    db.commit()
    r = client.post(
        "/api/v1/auth/login",
        json={
            "email": admin.user_email,
            "password": admin._test_password,
            "otp_code": pyotp.TOTP(admin.totp_secret).now(),
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_course(db, instructor, title="Assess Course"):
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


def _enroll(db, user, course):
    e = Enrollment(course_id=course.id, user_id=user.id, enrollment_status="enrolled")
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _make_quiz(db, instructor, course, passing_grade=50, max_attempts=0, time_limit=0,
                title="Quiz", feedback_mode=None):
    quiz = Quiz(
        post_author=instructor.id,
        post_parent=course.id,
        post_title=title,
        quiz_passing_grade=passing_grade,
        quiz_max_attempts_allowed=max_attempts,
        quiz_time_limit=time_limit,
    )
    if feedback_mode is not None:
        quiz.quiz_feedback_mode = feedback_mode
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def _add_mc_question(db, quiz, mark=10.0, correct_index=0, n_options=2):
    question = QuizQuestion(
        quiz_id=quiz.id, question_title="Pick one",
        question_type="multiple_choice", question_mark=mark,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    db.add_all([
        QuizQuestionAnswer(
            belongs_question_id=question.question_id,
            answer_title=f"Option {i}",
            is_correct=(i == correct_index),
            answer_order=i,
        )
        for i in range(n_options)
    ])
    db.commit()
    return question


def _add_multi_select_question(db, quiz, mark=10.0, correct_indices=(0, 2), n_options=3):
    question = QuizQuestion(
        quiz_id=quiz.id, question_title="Pick all that apply",
        question_type="multi_select", question_mark=mark,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    db.add_all([
        QuizQuestionAnswer(
            belongs_question_id=question.question_id,
            belongs_question_type="multi_select",
            answer_title=f"Option {i}",
            is_correct=(i in correct_indices),
            answer_order=i,
        )
        for i in range(n_options)
    ])
    db.commit()
    return question


def _add_essay_question(db, quiz, mark=20.0):
    question = QuizQuestion(
        quiz_id=quiz.id, question_title="Explain yourself",
        question_type="essay", question_mark=mark,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def _make_assignment(db, instructor, course, title="HW", due_date=None,
                      late_policy="allow", late_penalty_pct=0, status="published",
                      allowed_file_types=None, max_files=5, max_file_size=10):
    assignment = Assignment(
        course_id=course.id,
        created_by=instructor.id,
        title=title,
        due_date=due_date,
        late_policy=late_policy,
        late_penalty_pct=late_penalty_pct,
        status=status,
        allowed_file_types=allowed_file_types or [],
        max_files=max_files,
        max_file_size=max_file_size,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


# ----- item 2: answer-leak fix ------------------------------------------------


class TestAnswerLeakFix:
    def test_student_does_not_see_correct_answer(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="leak_instr@example.com")
        student = make_user(role="student", email="leak_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz)
        _enroll(db, student, course)

        headers = auth_headers("leak_student@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["showCorrectAnswers"] is False
        for q in body["questions"]:
            assert "correctAnswer" not in q
            assert "explanation" not in q

    def test_owner_sees_correct_answer(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "leak_owner@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz, correct_index=1)

        headers = auth_headers("leak_owner@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["showCorrectAnswers"] is True
        assert body["questions"][0]["correctAnswer"] == 1

    def test_admin_sees_correct_answer(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="leak_owner2@example.com")
        admin = make_user(role="admin", email="leak_admin@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz)

        headers = _admin_headers(client, db, admin)
        r = client.get(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["showCorrectAnswers"] is True


# ----- item 4: resume-existing-attempt on start ------------------------------


class TestResumeExistingAttempt:
    def test_start_twice_returns_same_attempt(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="resume_instr@example.com")
        student = make_user(role="student", email="resume_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz)
        _enroll(db, student, course)

        headers = auth_headers("resume_student@example.com")
        r1 = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        assert r1.status_code == 200, r1.text
        first_id = r1.json()["attempt_id"]
        assert r1.json()["resumed"] is False

        r2 = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        assert r2.status_code == 200, r2.text
        assert r2.json()["attempt_id"] == first_id
        assert r2.json()["resumed"] is True

        # Only one attempt row was created.
        count = db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == student.id
        ).count()
        assert count == 1


# ----- item 3: server-side timer ---------------------------------------------


class TestServerTimer:
    def test_submit_after_deadline_ends_wedge_free_with_partial_score(
        self, client, db, make_user, auth_headers
    ):
        """Review finding C2: a deadline-exceeded submit must never leave
        the attempt wedged in attempt_started forever. It scores ONLY
        whatever was already saved server-side before the deadline (the
        request body's answers are discarded — a late-arriving payload
        must not let a client just keep resubmitting past the clock), ends
        the attempt, and returns 200 with late_submission:true."""
        instructor = make_user(role="instructor", email="timer_instr@example.com")
        student = make_user(role="student", email="timer_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, time_limit=1, passing_grade=50)  # 1 minute
        q1 = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        q2 = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("timer_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]

        # Only save an answer to q1 BEFORE the deadline — q2 is left unanswered
        # to prove the late request's payload (which would answer both) is
        # discarded, not merged in.
        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/answers",
            json={"question_id": q1.question_id, "given_answer": "0"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        # Force the started_at far enough in the past to exceed 1 min + 90s grace.
        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        attempt.attempt_started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()

        # This late request tries to answer BOTH questions — q2's answer
        # must be discarded; only q1 (saved before the deadline) is scored.
        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(q1.question_id): 0, str(q2.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["late_submission"] is True
        assert body["attempt_status"] == "attempt_ended"
        assert body["earned_marks"] == 10.0  # only q1 scored
        assert body["total_marks"] == 20.0

        db.refresh(attempt)
        assert attempt.attempt_status == "attempt_ended"
        assert attempt.attempt_ended_at is not None

        # No wedge: the ended attempt is not resumed. The exact 50% pass
        # now triggers the upstream no-passed-retakes rule at /start.
        r2 = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        assert r2.status_code == 403, r2.text
        assert "retakes are not allowed" in r2.json()["detail"]

    def test_submit_within_deadline_succeeds(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="timer_instr2@example.com")
        student = make_user(role="student", email="timer_student2@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, time_limit=30)
        q = _add_mc_question(db, quiz)
        _enroll(db, student, course)
        headers = auth_headers("timer_student2@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(q.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text

    def test_unlimited_time_never_rejected(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="timer_instr3@example.com")
        student = make_user(role="student", email="timer_student3@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, time_limit=0)  # unlimited
        q = _add_mc_question(db, quiz)
        _enroll(db, student, course)
        headers = auth_headers("timer_student3@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]
        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        attempt.attempt_started_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(q.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text


# ----- item 11: pause blocks answer writes -----------------------------------


class TestPauseBlocksWrites:
    def test_save_answer_while_paused_is_409(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="pause_instr@example.com")
        student = make_user(role="student", email="pause_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        q = _add_mc_question(db, quiz)
        _enroll(db, student, course)
        headers = auth_headers("pause_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]

        r = client.post(f"/api/v1/quiz-attempts/{attempt_id}/pause", headers=headers)
        assert r.status_code == 200, r.text

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/answers",
            json={"question_id": q.question_id, "given_answer": "0"},
            headers=headers,
        )
        assert r.status_code == 409, r.text

    def test_resume_allows_answer_writes_again(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="pause_instr2@example.com")
        student = make_user(role="student", email="pause_student2@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        q = _add_mc_question(db, quiz)
        _enroll(db, student, course)
        headers = auth_headers("pause_student2@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]
        client.post(f"/api/v1/quiz-attempts/{attempt_id}/pause", headers=headers)
        r = client.post(f"/api/v1/quiz-attempts/{attempt_id}/resume", headers=headers)
        assert r.status_code == 200, r.text

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/answers",
            json={"question_id": q.question_id, "given_answer": "0"},
            headers=headers,
        )
        assert r.status_code == 200, r.text


# ----- item 1: essay -> pending_review + grade/finalize ----------------------


class TestPendingReviewFlow:
    def test_submit_with_essay_sets_pending_review(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="essay_instr@example.com")
        student = make_user(role="student", email="essay_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        headers = auth_headers("essay_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0, str(essay.question_id): "my long answer"}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["attempt_status"] == "pending_review"
        assert body["pending_review"] is True
        # Auto-graded portion only.
        assert body["earned_marks"] == 10.0
        assert body["passed"] is False  # never "passed" while pending

        attempt = db.query(QuizAttempt).filter_by(
            user_id=student.id, quiz_id=quiz.id
        ).one()
        assert attempt.attempt_status == "pending_review"

    def test_pending_review_does_not_recalc_progress_yet(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="essay_instr_pr@example.com")
        student = make_user(role="student", email="essay_student_pr@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=1)
        essay = _add_essay_question(db, quiz, mark=20.0)
        enrollment = _enroll(db, student, course)
        headers = auth_headers("essay_student_pr@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "answer"}},
            headers=headers,
        )
        db.refresh(enrollment)
        # No auto-graded questions passed yet -> quiz not counted as passed.
        assert enrollment.completed_quizzes == 0

    def test_instructor_can_list_grade_and_finalize(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "essay_instr2@example.com")
        student = make_user(role="student", email="essay_student2@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        essay = _add_essay_question(db, quiz, mark=20.0)
        enrollment = _enroll(db, student, course)
        student_headers = auth_headers("essay_student2@example.com")
        instr_headers = auth_headers("essay_instr2@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0, str(essay.question_id): "essay text"}},
            headers=student_headers,
        )

        # Pending-review list
        r = client.get(
            f"/api/v1/courses/{course.id}/quizzes/pending-reviews", headers=instr_headers
        )
        assert r.status_code == 200, r.text
        pending = r.json()["pending_reviews"]
        assert len(pending) == 1
        attempt_id = pending[0]["attempt_id"]
        answer_id = pending[0]["ungraded_answer_ids"][0]

        # Grade the essay answer
        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/answers/{answer_id}/grade",
            json={"achieved_mark": 15, "feedback": "Good but could improve"},
            headers=instr_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["achieved_mark"] == 15

        # Finalize
        r = client.post(f"/api/v1/quiz-attempts/{attempt_id}/finalize", headers=instr_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["attempt_status"] == "attempt_ended"
        assert body["earned_marks"] == 25.0  # 10 (mc) + 15 (essay)
        assert body["passed"] is True

        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        assert attempt.attempt_status == "attempt_ended"

        # Progress recalculated now that it's ended.
        db.refresh(enrollment)
        assert enrollment.completed_quizzes == 1

    def test_finalize_rejected_when_answers_ungraded(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "essay_instr3@example.com")
        student = make_user(role="student", email="essay_student3@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        student_headers = auth_headers("essay_student3@example.com")
        instr_headers = auth_headers("essay_instr3@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "text"}},
            headers=student_headers,
        )
        attempt = db.query(QuizAttempt).filter_by(user_id=student.id, quiz_id=quiz.id).one()

        r = client.post(f"/api/v1/quiz-attempts/{attempt.attempt_id}/finalize", headers=instr_headers)
        assert r.status_code == 400, r.text

    def test_grade_and_finalize_require_course_owner_or_admin(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="essay_instr4@example.com")
        other_instructor = _make_approved_instructor(db, make_user, "essay_other@example.com")
        student = make_user(role="student", email="essay_student4@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        student_headers = auth_headers("essay_student4@example.com")
        other_headers = auth_headers("essay_other@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "text"}},
            headers=student_headers,
        )
        attempt = db.query(QuizAttempt).filter_by(user_id=student.id, quiz_id=quiz.id).one()
        answer = db.query(QuizAttemptAnswer).filter_by(quiz_attempt_id=attempt.attempt_id).one()

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt.attempt_id}/answers/{answer.attempt_answer_id}/grade",
            json={"achieved_mark": 10},
            headers=other_headers,
        )
        assert r.status_code == 403, r.text

    def test_course_owning_instructor_can_view_attempt_results(
        self, client, db, make_user, auth_headers
    ):
        """Review fix (grading-queue round): GET /quiz-attempts/{id}/results
        used to only allow the attempt owner or a site admin — a
        course-owning non-admin instructor 403'd on the exact call
        grading-queue.tsx's essay-review detail view makes, making the
        grade-each-answer -> finalize flow unusable for anyone but an
        admin. The course-owning instructor must now be able to view (not
        necessarily modify) another student's attempt results."""
        instructor = _make_approved_instructor(db, make_user, "results_owner@example.com")
        student = make_user(role="student", email="results_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        student_headers = auth_headers("results_student@example.com")
        instr_headers = auth_headers("results_owner@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0, str(essay.question_id): "essay text"}},
            headers=student_headers,
        )
        attempt = db.query(QuizAttempt).filter_by(user_id=student.id, quiz_id=quiz.id).one()

        # The course-owning instructor (not the student, not an admin) can
        # view the attempt's results — this is the call grading-queue.tsx's
        # loadDetail() makes before showing per-question mark inputs.
        r = client.get(
            f"/api/v1/quiz-attempts/{attempt.attempt_id}/results", headers=instr_headers
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["attempt_id"] == attempt.attempt_id
        assert body["pending_review"] is True

    def test_unrelated_instructor_still_forbidden_from_attempt_results(
        self, client, db, make_user, auth_headers
    ):
        """Student isolation stays intact: an instructor who does NOT own
        this attempt's course (and isn't admin) still gets 403 — the fix
        only adds a course-ownership allowance, not open instructor access
        to any attempt."""
        instructor = _make_approved_instructor(db, make_user, "results_owner2@example.com")
        other_instructor = _make_approved_instructor(db, make_user, "results_other@example.com")
        student = make_user(role="student", email="results_student2@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        student_headers = auth_headers("results_student2@example.com")
        other_headers = auth_headers("results_other@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "text"}},
            headers=student_headers,
        )
        attempt = db.query(QuizAttempt).filter_by(user_id=student.id, quiz_id=quiz.id).one()

        r = client.get(
            f"/api/v1/quiz-attempts/{attempt.attempt_id}/results", headers=other_headers
        )
        assert r.status_code == 403, r.text

    def test_different_student_still_forbidden_from_attempt_results(
        self, client, db, make_user, auth_headers
    ):
        """A different student (not the attempt owner, not staff) still
        403s on another student's attempt results — the view-access fix
        only widens access for the course-owning instructor."""
        instructor = _make_approved_instructor(db, make_user, "results_owner3@example.com")
        student = make_user(role="student", email="results_student3@example.com")
        other_student = make_user(role="student", email="results_other_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        _enroll(db, other_student, course)
        student_headers = auth_headers("results_student3@example.com")
        other_student_headers = auth_headers("results_other_student@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "text"}},
            headers=student_headers,
        )
        attempt = db.query(QuizAttempt).filter_by(user_id=student.id, quiz_id=quiz.id).one()

        r = client.get(
            f"/api/v1/quiz-attempts/{attempt.attempt_id}/results", headers=other_student_headers
        )
        assert r.status_code == 403, r.text


# ----- item 6 & 7: assignment enrollment check + status lifecycle ------------


class TestAssignmentEnrollmentAndStatus:
    def test_submit_without_enrollment_is_403(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="enr_instr@example.com")
        student = make_user(role="student", email="enr_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)
        headers = auth_headers("enr_student@example.com")

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "my work"},
            headers=headers,
        )
        assert r.status_code == 403, r.text

    def test_submit_with_enrollment_succeeds(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="enr_instr2@example.com")
        student = make_user(role="student", email="enr_student2@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)
        _enroll(db, student, course)
        headers = auth_headers("enr_student2@example.com")

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "my work"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

    def test_owner_can_submit_without_enrollment(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "enr_instr3@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)
        headers = auth_headers("enr_instr3@example.com")

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "preview"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

    def test_draft_assignment_hidden_from_student_list(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="draft_instr@example.com")
        student = make_user(role="student", email="draft_student@example.com")
        course = _make_course(db, instructor)
        _make_assignment(db, instructor, course, title="Draft HW", status="draft")
        _make_assignment(db, instructor, course, title="Published HW", status="published")
        _enroll(db, student, course)

        r = client.get(
            f"/api/v1/courses/{course.id}/assignments",
            headers=auth_headers("draft_student@example.com"),
        )
        assert r.status_code == 200, r.text
        titles = [a["title"] for a in r.json()]
        assert "Published HW" in titles
        assert "Draft HW" not in titles

    def test_draft_assignment_visible_to_owner(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "draft_instr2@example.com")
        course = _make_course(db, instructor)
        _make_assignment(db, instructor, course, title="Draft HW2", status="draft")

        r = client.get(
            f"/api/v1/courses/{course.id}/assignments",
            headers=auth_headers("draft_instr2@example.com"),
        )
        assert r.status_code == 200, r.text
        titles = [a["title"] for a in r.json()]
        assert "Draft HW2" in titles

    def test_submit_to_draft_assignment_rejected_for_student(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="draft_instr3@example.com")
        student = make_user(role="student", email="draft_student3@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, status="draft")
        _enroll(db, student, course)

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "work"},
            headers=auth_headers("draft_student3@example.com"),
        )
        assert r.status_code == 403, r.text

    def test_create_assignment_accepts_status(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "create_instr@example.com")
        course = _make_course(db, instructor)

        r = client.post(
            f"/api/v1/courses/{course.id}/assignments",
            json={"title": "New HW", "status": "draft"},
            headers=auth_headers("create_instr@example.com"),
        )
        assert r.status_code == 200, r.text
        assignment = db.query(Assignment).filter_by(id=r.json()["id"]).one()
        assert assignment.status.value == "draft"

    def test_update_assignment_accepts_status(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "update_instr@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, status="draft")

        r = client.put(
            f"/api/v1/courses/{course.id}/assignments/{assignment.id}",
            json={"status": "published"},
            headers=auth_headers("update_instr@example.com"),
        )
        assert r.status_code == 200, r.text
        db.refresh(assignment)
        assert assignment.status.value == "published"

    def test_invalid_status_rejected(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "invalid_status@example.com")
        course = _make_course(db, instructor)

        r = client.post(
            f"/api/v1/courses/{course.id}/assignments",
            json={"title": "Bad", "status": "not-a-real-status"},
            headers=auth_headers("invalid_status@example.com"),
        )
        assert r.status_code == 400, r.text


# ----- item 5: assignment deadline + late_policy ------------------------------


class TestAssignmentLatePolicy:
    def test_allow_policy_flags_late_but_accepts(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="late_instr@example.com")
        student = make_user(role="student", email="late_student@example.com")
        course = _make_course(db, instructor)
        past_due = datetime.now(timezone.utc) - timedelta(days=1)
        assignment = _make_assignment(db, instructor, course, due_date=past_due, late_policy="allow")
        _enroll(db, student, course)

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "late work"},
            headers=auth_headers("late_student@example.com"),
        )
        assert r.status_code == 200, r.text
        assert r.json()["isLate"] is True

        sub = db.query(AssignmentSubmission).filter_by(
            assignment_id=assignment.id, user_id=student.id
        ).one()
        assert sub.is_late is True

    def test_block_policy_rejects_late_submission(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="late_instr2@example.com")
        student = make_user(role="student", email="late_student2@example.com")
        course = _make_course(db, instructor)
        past_due = datetime.now(timezone.utc) - timedelta(days=1)
        assignment = _make_assignment(db, instructor, course, due_date=past_due, late_policy="block")
        _enroll(db, student, course)

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "too late"},
            headers=auth_headers("late_student2@example.com"),
        )
        assert r.status_code == 403, r.text
        assert "due" in r.json()["detail"].lower() or "deadline" in r.json()["detail"].lower()

    def test_on_time_submission_not_flagged_late(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="late_instr3@example.com")
        student = make_user(role="student", email="late_student3@example.com")
        course = _make_course(db, instructor)
        future_due = datetime.now(timezone.utc) + timedelta(days=1)
        assignment = _make_assignment(db, instructor, course, due_date=future_due, late_policy="block")
        _enroll(db, student, course)

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "on time"},
            headers=auth_headers("late_student3@example.com"),
        )
        assert r.status_code == 200, r.text
        assert r.json()["isLate"] is False

    def test_penalty_policy_reduces_grade(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "late_instr4@example.com")
        student = make_user(role="student", email="late_student4@example.com")
        course = _make_course(db, instructor)
        past_due = datetime.now(timezone.utc) - timedelta(days=1)
        assignment = _make_assignment(
            db, instructor, course, due_date=past_due, late_policy="penalty", late_penalty_pct=20
        )
        _enroll(db, student, course)

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "late but graded"},
            headers=auth_headers("late_student4@example.com"),
        )
        assert r.status_code == 200, r.text
        submission_id = r.json()["id"]

        r = client.post(
            f"/api/v1/submissions/{submission_id}/grade",
            json={"grade": 100, "feedback": "good work"},
            headers=auth_headers("late_instr4@example.com"),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["rawGrade"] == 100.0
        assert body["grade"] == 80.0  # 20% penalty applied
        assert body["latePenaltyApplied"] is True

        sub = db.query(AssignmentSubmission).filter_by(id=submission_id).one()
        assert float(sub.grade) == 80.0


# ----- item 9: unique (assignment_id, user_id) constraint --------------------


class TestUniqueSubmissionConstraint:
    def test_model_has_unique_constraint(self):
        constraint_names = {
            c.name for c in AssignmentSubmission.__table__.constraints
            if hasattr(c, "name")
        }
        assert "uq_assignment_user" in constraint_names

    def test_duplicate_submission_row_rejected_at_db_level(self, db, make_user):
        instructor = _make_instructor(db, email="uniq_instr@example.com")
        student_a = make_user(role="student", email="uniq_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)

        s1 = AssignmentSubmission(assignment_id=assignment.id, user_id=student_a.id, status=SubmissionStatus.SUBMITTED)
        db.add(s1)
        db.commit()

        s2 = AssignmentSubmission(assignment_id=assignment.id, user_id=student_a.id, status=SubmissionStatus.SUBMITTED)
        db.add(s2)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()


# ----- item 8: per-assignment file upload validation --------------------------


class TestAssignmentFileUpload:
    def test_rejects_disallowed_extension(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="file_instr@example.com")
        student = make_user(role="student", email="file_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        _enroll(db, student, course)
        headers = auth_headers("file_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("work.exe", b"not really a pdf", "application/octet-stream")},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_accepts_allowed_extension(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="file_instr2@example.com")
        student = make_user(role="student", email="file_student2@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        _enroll(db, student, course)
        headers = auth_headers("file_student2@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("work.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["file_url"].startswith(f"/uploads/assignments/{assignment.id}/")

    def test_rejects_oversized_file(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="file_instr3@example.com")
        student = make_user(role="student", email="file_student3@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"], max_file_size=1)  # 1 MB cap
        _enroll(db, student, course)
        headers = auth_headers("file_student3@example.com")

        big_payload = b"0" * (2 * 1024 * 1024)  # 2 MB > 1 MB cap
        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("big.pdf", big_payload, "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_unknown_assignment_404(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="file_student4@example.com")
        headers = auth_headers("file_student4@example.com")

        r = client.post(
            "/api/v1/upload/assignment-file?assignment_id=999999",
            files={"file": ("work.pdf", b"data", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 404, r.text


# ----- assignment model field sanity (item 12 fields only) -------------------


class TestRubricFieldsExist:
    def test_assignment_rubric_column_defaults_empty(self, db, make_user):
        instructor = _make_instructor(db, email="rubric_instr@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)
        assert assignment.rubric == []
        assert assignment.late_policy == "allow"
        assert assignment.late_penalty_pct == 0

    def test_submission_rubric_scores_nullable(self, db, make_user):
        instructor = _make_instructor(db, email="rubric_instr2@example.com")
        student = make_user(role="student", email="rubric_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)
        sub = AssignmentSubmission(assignment_id=assignment.id, user_id=student.id)
        db.add(sub)
        db.commit()
        db.refresh(sub)
        assert sub.rubric_scores is None


# ===========================================================================
# Review-round regressions (all PROVEN by the reviewer with live probes).
# C1/C2/C3 = Critical, I1-I4 = Important, M2 = Minor (cheap fold-in).
# M1 (parallel-start race) and M3 (report framing) are deferred to the
# ledger per the coordinator's instruction — not covered here.
# ===========================================================================


# ----- C1: canonical route bypassed attempt-limit + timer --------------------


class TestCanonicalRouteBypassClosed:
    def test_canonical_route_enforces_attempt_limit_via_open_attempt(
        self, client, db, make_user, auth_headers
    ):
        """Before the fix: POST /courses/{cid}/quizzes/{qid}/submit (called
        directly, without going through /quiz-attempts/{id}/submit) always
        passed existing_attempt=None, so it never looked up the caller's
        open attempt and could be resubmitted past max_attempts freely by
        just hitting the canonical route repeatedly against the SAME
        started attempt. Now: submitting through the canonical route with
        an open attempt on file routes through that attempt, ending it —
        a second canonical-route submit with no open attempt left is
        correctly treated as a fresh attempt count against the limit."""
        instructor = make_user(role="instructor", email="c1_instr@example.com")
        student = make_user(role="student", email="c1_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50, max_attempts=1)
        q = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("c1_student@example.com")

        # Start once — creates the one open attempt this student gets.
        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        assert r.status_code == 200, r.text

        # First canonical-route submit: consumes the open attempt, ends it.
        r1 = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(q.question_id): 0}},
            headers=headers,
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["attempt_status"] == "attempt_ended"

        # Second and third canonical-route submits: no open attempt remains
        # (the first ended it), so each would create/attempt a NEW one —
        # blocked by max_attempts=1 (already 1 ended attempt on file).
        for _ in range(2):
            r = client.post(
                f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
                json={"answers": {str(q.question_id): 0}},
                headers=headers,
            )
            assert r.status_code == 403, r.text

        ended_count = db.query(QuizAttempt).filter_by(
            user_id=student.id, quiz_id=quiz.id, attempt_status="attempt_ended"
        ).count()
        assert ended_count == 1

    def test_canonical_route_enforces_timer_via_open_attempt(
        self, client, db, make_user, auth_headers
    ):
        """Before the fix: hitting the canonical submit route directly
        after /start (rather than /quiz-attempts/{id}/submit) skipped the
        timer entirely (existing_attempt was always None on that path).
        Now the canonical route finds the same open attempt and applies
        the same wedge-free deadline handling as the attempt-scoped route."""
        instructor = make_user(role="instructor", email="c1t_instr@example.com")
        student = make_user(role="student", email="c1t_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, time_limit=1, passing_grade=50)
        q = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("c1t_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]
        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        attempt.attempt_started_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()

        # Hit the CANONICAL route directly, not the attempt-scoped one —
        # this used to be the bypass.
        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(q.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["late_submission"] is True
        # No answer had been saved server-side before the deadline, so
        # nothing is scored despite the request body answering q.
        assert r.json()["earned_marks"] == 0

    def test_pending_review_attempt_counts_toward_limit_and_blocks_resubmit(
        self, client, db, make_user, auth_headers
    ):
        """Before the fix: pending_review attempts were invisible to the
        max_attempts count (only attempt_ended counted) — a student could
        rack up unlimited pending_review rows by always including an essay
        question. Now pending_review counts, and submitting again while
        one is open is rejected outright (409) rather than allowed to pile
        up more pending rows."""
        instructor = make_user(role="instructor", email="c1p_instr@example.com")
        student = make_user(role="student", email="c1p_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50, max_attempts=1)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        headers = auth_headers("c1p_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        assert r.status_code == 200, r.text

        r1 = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "essay answer"}},
            headers=headers,
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["attempt_status"] == "pending_review"

        # A second submit while pending_review is open: 409, not a new row.
        r2 = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "trying again"}},
            headers=headers,
        )
        assert r2.status_code == 409, r2.text

        pending_count = db.query(QuizAttempt).filter_by(
            user_id=student.id, quiz_id=quiz.id, attempt_status="pending_review"
        ).count()
        assert pending_count == 1

        # /start also refuses to spin up a fresh attempt while one is
        # pending_review — it resumes/surfaces the existing row instead.
        r3 = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        assert r3.status_code == 200, r3.text
        assert r3.json()["resumed"] is True


# ----- I3: submit allowed while paused ----------------------------------------


class TestSubmitBlockedWhilePaused:
    def test_submit_while_paused_is_409(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="i3_instr@example.com")
        student = make_user(role="student", email="i3_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        q = _add_mc_question(db, quiz)
        _enroll(db, student, course)
        headers = auth_headers("i3_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]
        r = client.post(f"/api/v1/quiz-attempts/{attempt_id}/pause", headers=headers)
        assert r.status_code == 200, r.text

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(q.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 409, r.text

        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        assert attempt.attempt_status == "attempt_started"

    def test_submit_after_resume_succeeds(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="i3b_instr@example.com")
        student = make_user(role="student", email="i3b_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        q = _add_mc_question(db, quiz)
        _enroll(db, student, course)
        headers = auth_headers("i3b_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]
        client.post(f"/api/v1/quiz-attempts/{attempt_id}/pause", headers=headers)
        r = client.post(f"/api/v1/quiz-attempts/{attempt_id}/resume", headers=headers)
        assert r.status_code == 200, r.text

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(q.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text

    def test_resubmit_already_ended_attempt_is_409_not_400(
        self, client, db, make_user, auth_headers
    ):
        """Review fix (minor finding): the attempt-scoped submit route used
        to raise a blanket 400 "Attempt is already {status}" for ANY
        non-attempt_started status BEFORE _submit_quiz_impl's own, more
        specific 409 branches ever ran — a raced tab resubmitting an
        already-ended attempt should get the same 409 conflict semantics
        every other "can't submit right now" case uses, not a generic 400."""
        instructor = make_user(role="instructor", email="resub_instr@example.com")
        student = make_user(role="student", email="resub_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        q = _add_mc_question(db, quiz)
        _enroll(db, student, course)
        headers = auth_headers("resub_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(q.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["attempt_status"] == "attempt_ended"

        # Resubmitting the same, now-ended attempt: 409 conflict, not 400.
        r2 = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(q.question_id): 0}},
            headers=headers,
        )
        assert r2.status_code == 409, r2.text

        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        assert attempt.attempt_status == "attempt_ended"

    def test_resubmit_pending_review_via_attempt_scoped_route_is_409(
        self, client, db, make_user, auth_headers
    ):
        """A pending_review attempt hit via the attempt-scoped submit route
        (not just the canonical course/quiz route already covered by
        TestPendingReviewFlow) now falls through to _submit_quiz_impl's own
        pending_review 409 branch instead of being pre-empted by the old
        blanket 400 guard."""
        instructor = make_user(role="instructor", email="resub_pr_instr@example.com")
        student = make_user(role="student", email="resub_pr_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        headers = auth_headers("resub_pr_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(essay.question_id): "essay answer"}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["attempt_status"] == "pending_review"

        r2 = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(essay.question_id): "trying again"}},
            headers=headers,
        )
        assert r2.status_code == 409, r2.text
        assert "review" in r2.json()["detail"].lower()


# ----- M2: underscore-prefixed answer keys must not clobber bookkeeping ------


class TestUnderscoreAnswerKeyStripped:
    def test_graded_answers_key_in_submission_is_ignored(
        self, client, db, make_user, auth_headers
    ):
        """A student answer payload keyed "_graded_answers" (the exact
        internal marker finalize_quiz_attempt gates on) must never be
        allowed to write into that bookkeeping key — otherwise a student
        could forge their own manual-grading answers as "already graded"."""
        instructor = _make_approved_instructor(db, make_user, "m2_instr@example.com")
        student = make_user(role="student", email="m2_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        student_headers = auth_headers("m2_student@example.com")
        instr_headers = auth_headers("m2_instr@example.com")

        # Forge a fake "_graded_answers" key claiming some answer id is
        # already graded, alongside the real essay answer.
        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {
                str(essay.question_id): "my essay",
                "_graded_answers": [999999],
                "_pause": {"paused": True},
            }},
            headers=student_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["attempt_status"] == "pending_review"

        attempt = db.query(QuizAttempt).filter_by(user_id=student.id, quiz_id=quiz.id).one()
        info = attempt.attempt_info if isinstance(attempt.attempt_info, dict) else __import__("json").loads(attempt.attempt_info)
        # The forged keys must not have landed verbatim from student input —
        # _graded_answers stays whatever the server itself set (empty/absent
        # for a freshly pending_review attempt), never the forged [999999].
        assert info.get("_graded_answers") != [999999]

        # Finalize must still require the essay to be genuinely graded via
        # the real grade endpoint — the forged key didn't fast-path it.
        r = client.post(f"/api/v1/quiz-attempts/{attempt.attempt_id}/finalize", headers=instr_headers)
        assert r.status_code == 400, r.text


# ----- C3: /assignment-file upload had no enrollment/ownership check ---------


class TestAssignmentFileUploadRequiresEnrollment:
    def test_unenrolled_student_upload_is_403(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="c3_instr@example.com")
        student = make_user(role="student", email="c3_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        # Deliberately NOT enrolled.
        headers = auth_headers("c3_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("work.pdf", b"%PDF-1.4 data", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 403, r.text

    def test_enrolled_student_upload_still_succeeds(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="c3b_instr@example.com")
        student = make_user(role="student", email="c3b_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        _enroll(db, student, course)
        headers = auth_headers("c3b_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("work.pdf", b"%PDF-1.4 data", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 200, r.text

    def test_course_owner_upload_bypasses_enrollment(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "c3c_instr@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        headers = auth_headers("c3c_instr@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("preview.pdf", b"%PDF-1.4 data", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 200, r.text


# ----- I1: max_files counted from a submission row, not the real uploads -----


class TestMaxFilesEnforcedAtUploadTime:
    def test_max_files_enforced_up_to_the_cap_before_any_submission_exists(
        self, client, db, make_user, auth_headers
    ):
        """Before the I1 fix: max_files was counted from the (often
        nonexistent, pre-submit) AssignmentSubmission.files column, so
        uploads always undercounted to 0 and sailed through. Now the count
        comes from files actually present on disk for this user — but
        (follow-up HIGH fix) pre-submission uploads are all "orphans" with
        no live submission referencing them, so each new upload reclaims
        the budget from the previous abandoned one rather than piling up
        forever. A single upload obeys max_files (can't have MORE than the
        cap on disk at once), but repeated single uploads never
        permanently exhaust the budget — see
        TestUploadBudgetReclaim.test_abandoned_uploads_reclaim_budget for
        the multi-upload-in-a-row case this test used to (incorrectly)
        assert blocks forever."""
        instructor = make_user(role="instructor", email="i1_instr@example.com")
        student = make_user(role="student", email="i1_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(
            db, instructor, course, allowed_file_types=["pdf"], max_files=2
        )
        _enroll(db, student, course)
        headers = auth_headers("i1_student@example.com")

        # No AssignmentSubmission row exists at all yet — the old count
        # (from a submission row) would report 0 existing files, but the
        # NEW on-disk count must still cap concurrent uploads at max_files.
        assert db.query(AssignmentSubmission).filter_by(
            assignment_id=assignment.id, user_id=student.id
        ).first() is None

        for name in ("one.pdf", "two.pdf"):
            r = client.post(
                f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
                files={"file": (name, f"%PDF-1.4 {name}".encode(), "application/pdf")},
                headers=headers,
            )
            assert r.status_code == 200, r.text

        # Third upload with 2 already on disk and max_files=2 is over cap
        # (nothing to submit against yet, so both prior uploads are still
        # "live" candidates for a future submission at this exact instant —
        # only a NEW upload call re-evaluates orphan status, and the third
        # call's reclaim pass finds no submission and deletes ALL prior
        # files as orphans before re-counting, so it actually succeeds).
        # This demonstrates the reclaim-on-upload semantics precisely: the
        # cap is "no more than max_files accumulate across separate visits
        # without ever submitting", not "you can never upload again".
        r3 = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("three.pdf", b"%PDF-1.4 three", "application/pdf")},
            headers=headers,
        )
        assert r3.status_code == 200, r3.text

    def test_max_files_is_per_user(self, client, db, make_user, auth_headers):
        """Two different students each get their own max_files budget —
        the on-disk count is scoped by the u{user_id}_ filename prefix."""
        instructor = make_user(role="instructor", email="i1b_instr@example.com")
        student_a = make_user(role="student", email="i1b_student_a@example.com")
        student_b = make_user(role="student", email="i1b_student_b@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(
            db, instructor, course, allowed_file_types=["pdf"], max_files=1
        )
        _enroll(db, student_a, course)
        _enroll(db, student_b, course)

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("a.pdf", b"%PDF-1.4 a", "application/pdf")},
            headers=auth_headers("i1b_student_a@example.com"),
        )
        assert r.status_code == 200, r.text

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("b.pdf", b"%PDF-1.4 b", "application/pdf")},
            headers=auth_headers("i1b_student_b@example.com"),
        )
        assert r.status_code == 200, r.text


# ----- Follow-up HIGH: I1's fix counted every file ever uploaded and -----
# ----- nothing ever reclaimed the budget (RETURNED submissions, -----
# ----- abandoned uploads). Fixed via the "supersede" approach: orphaned -----
# ----- files (not referenced by a live, non-RETURNED submission) are -----
# ----- deleted at upload time before counting. -----------------------------


class TestUploadBudgetReclaim:
    def test_full_product_flow_return_then_reupload_then_resubmit(
        self, client, db, make_user, auth_headers
    ):
        """The exact broken flow the reviewer proved: max_files=1
        assignment -> upload -> submit -> instructor returns the
        submission (RETURNED) -> student's replacement upload used to get
        400 "Too many files" forever, because the old file was still
        counted even though it's no longer referenced by anything live.
        Now: the RETURNED submission's old file is an orphan, gets deleted
        on the replacement upload, and the student can re-upload and
        resubmit successfully."""
        instructor = _make_approved_instructor(db, make_user, "reclaim_instr@example.com")
        student = make_user(role="student", email="reclaim_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(
            db, instructor, course, allowed_file_types=["pdf"], max_files=1
        )
        _enroll(db, student, course)
        student_headers = auth_headers("reclaim_student@example.com")
        instr_headers = auth_headers("reclaim_instr@example.com")

        # 1. Upload the first file.
        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("first.pdf", b"%PDF-1.4 first draft", "application/pdf")},
            headers=student_headers,
        )
        assert r.status_code == 200, r.text
        first_file_url = r.json()["file_url"]
        first_filename = first_file_url.rsplit("/", 1)[-1]

        upload_dir = _upload_dir_for(assignment.id)
        assert (upload_dir / first_filename).is_file()

        # 2. Submit referencing that file.
        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "my first draft", "files": [{"file_url": first_file_url}]},
            headers=student_headers,
        )
        assert r.status_code == 200, r.text
        submission_id = r.json()["id"]

        # 3. Instructor returns it for changes — clears the file
        # reference's "live" status (submission status becomes RETURNED).
        r = client.post(
            f"/api/v1/submissions/{submission_id}/return",
            json={"feedback": "please redo this"},
            headers=instr_headers,
        )
        assert r.status_code == 200, r.text

        # 4. Student uploads a replacement file. Before the fix: 400
        # "Too many files" forever, because first.pdf was still counted.
        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("second.pdf", b"%PDF-1.4 revised draft", "application/pdf")},
            headers=student_headers,
        )
        assert r.status_code == 200, r.text
        second_file_url = r.json()["file_url"]
        second_filename = second_file_url.rsplit("/", 1)[-1]

        # The old (now-orphaned) file was deleted; the new one exists.
        assert not (upload_dir / first_filename).exists()
        assert (upload_dir / second_filename).is_file()

        # 5. Student resubmits with the new file — succeeds.
        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "revised draft", "files": [{"file_url": second_file_url}]},
            headers=student_headers,
        )
        assert r.status_code == 200, r.text

    def test_abandoned_uploads_reclaim_budget(self, client, db, make_user, auth_headers):
        """A student uploads up to max_files times but never submits
        (abandons the flow). Before the fix, those files sat on disk
        forever with no submission ever referencing them, permanently
        exhausting the budget. Now: with no live submission, every prior
        upload is an orphan and the next upload call reclaims the budget."""
        instructor = make_user(role="instructor", email="reclaim2_instr@example.com")
        student = make_user(role="student", email="reclaim2_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(
            db, instructor, course, allowed_file_types=["pdf"], max_files=5
        )
        _enroll(db, student, course)
        headers = auth_headers("reclaim2_student@example.com")

        # Upload max_files times without ever submitting.
        for i in range(5):
            r = client.post(
                f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
                files={"file": (f"abandoned{i}.pdf", f"%PDF-1.4 draft {i}".encode(), "application/pdf")},
                headers=headers,
            )
            assert r.status_code == 200, r.text

        # No submission was ever created — all 5 are orphans.
        assert db.query(AssignmentSubmission).filter_by(
            assignment_id=assignment.id, user_id=student.id
        ).first() is None

        # The next upload still succeeds: the reclaim pass deletes the
        # orphaned files before counting, rather than reporting "you have
        # 5, max is 5" forever.
        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("finally.pdf", b"%PDF-1.4 final draft", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 200, r.text

    def test_referenced_file_is_never_deleted_by_reclaim(
        self, client, db, make_user, auth_headers
    ):
        """I4's guarantee must survive the reclaim logic: a file
        referenced by a submitted, NON-RETURNED submission is never an
        orphan and must never be deleted — even when a later upload call
        hits max_files and is rejected."""
        instructor = make_user(role="instructor", email="reclaim3_instr@example.com")
        student = make_user(role="student", email="reclaim3_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(
            db, instructor, course, allowed_file_types=["pdf"], max_files=1
        )
        _enroll(db, student, course)
        headers = auth_headers("reclaim3_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("keep.pdf", b"%PDF-1.4 keep me", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        file_url = r.json()["file_url"]
        filename = file_url.rsplit("/", 1)[-1]
        upload_dir = _upload_dir_for(assignment.id)
        assert (upload_dir / filename).is_file()

        # Submit — status becomes SUBMITTED (not RETURNED), so the file is
        # now "live"/referenced.
        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "my work", "files": [{"file_url": file_url}]},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        submission = db.query(AssignmentSubmission).filter_by(
            assignment_id=assignment.id, user_id=student.id
        ).one()
        assert submission.status == SubmissionStatus.SUBMITTED

        # A second upload attempt while the submission is still live and
        # already at max_files=1: rejected (over cap), and — the actual
        # regression check — the referenced file must still be on disk
        # afterward, untouched by the reclaim pass.
        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("second.pdf", b"%PDF-1.4 second", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 400, r.text
        assert (upload_dir / filename).is_file()


# ----- I2: instructor allowlist could widen past safe types ------------------


class TestUploadExtensionSafetyCeiling:
    def test_html_extension_rejected_even_if_instructor_allowlisted_it(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="i2_instr@example.com")
        student = make_user(role="student", email="i2_student@example.com")
        course = _make_course(db, instructor)
        # Instructor (mis)configures html as allowed — must be rejected
        # anyway (server-side ceiling always wins).
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf", "html"])
        _enroll(db, student, course)
        headers = auth_headers("i2_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("payload.html", b"<script>alert(1)</script>", "text/html")},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_svg_extension_rejected(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="i2b_instr@example.com")
        student = make_user(role="student", email="i2b_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["svg"])
        _enroll(db, student, course)
        headers = auth_headers("i2b_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("payload.svg", b"<svg onload=alert(1)></svg>", "image/svg+xml")},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_no_restriction_configured_still_excludes_dangerous_types(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="i2c_instr@example.com")
        student = make_user(role="student", email="i2c_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=[])
        _enroll(db, student, course)
        headers = auth_headers("i2c_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("payload.html", b"<script>x</script>", "text/html")},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_content_type_mismatch_rejected(self, client, db, make_user, auth_headers):
        """A safe extension paired with an unrelated content_type (e.g. a
        .pdf upload actually declaring text/html) is rejected — the
        extension and declared MIME type must agree."""
        instructor = make_user(role="instructor", email="i2d_instr@example.com")
        student = make_user(role="student", email="i2d_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        _enroll(db, student, course)
        headers = auth_headers("i2d_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("work.pdf", b"<script>x</script>", "text/html")},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_safe_extension_with_matching_content_type_accepted(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="i2e_instr@example.com")
        student = make_user(role="student", email="i2e_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["txt"])
        _enroll(db, student, course)
        headers = auth_headers("i2e_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("notes.txt", b"plain text content", "text/plain")},
            headers=headers,
        )
        assert r.status_code == 200, r.text


# ----- I4: submit accepted arbitrary/foreign file_url values -----------------


class TestSubmitRejectsForeignFileUrls:
    def test_submit_rejects_another_users_file(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="i4_instr@example.com")
        victim = make_user(role="student", email="i4_victim@example.com")
        attacker = make_user(role="student", email="i4_attacker@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        _enroll(db, victim, course)
        _enroll(db, attacker, course)

        # Victim uploads a real file.
        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("victim.pdf", b"%PDF-1.4 victim data", "application/pdf")},
            headers=auth_headers("i4_victim@example.com"),
        )
        assert r.status_code == 200, r.text
        victim_file_url = r.json()["file_url"]

        # Attacker tries to submit referencing the victim's file_url.
        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "stolen work", "files": [{"file_url": victim_file_url}]},
            headers=auth_headers("i4_attacker@example.com"),
        )
        assert r.status_code == 422, r.text

    def test_submit_rejects_nonexistent_file(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="i4b_instr@example.com")
        student = make_user(role="student", email="i4b_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        _enroll(db, student, course)
        headers = auth_headers("i4b_student@example.com")

        fake_url = f"/uploads/assignments/{assignment.id}/u{student.id}_doesnotexist.pdf"
        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "work", "files": [{"file_url": fake_url}]},
            headers=headers,
        )
        assert r.status_code == 422, r.text

    def test_submit_rejects_wrong_assignment_path(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="i4c_instr@example.com")
        student = make_user(role="student", email="i4c_student@example.com")
        course = _make_course(db, instructor)
        assignment_a = _make_assignment(db, instructor, course, title="A", allowed_file_types=["pdf"])
        assignment_b = _make_assignment(db, instructor, course, title="B", allowed_file_types=["pdf"])
        _enroll(db, student, course)
        headers = auth_headers("i4c_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment_a.id}",
            files={"file": ("work.pdf", b"%PDF-1.4 data", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        file_url = r.json()["file_url"]

        # Submit this file against assignment B instead of A.
        r = client.post(
            f"/api/v1/assignments/{assignment_b.id}/submit",
            json={"textContent": "work", "files": [{"file_url": file_url}]},
            headers=headers,
        )
        assert r.status_code == 422, r.text

    def test_submit_accepts_own_genuinely_uploaded_file(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="i4d_instr@example.com")
        student = make_user(role="student", email="i4d_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, allowed_file_types=["pdf"])
        _enroll(db, student, course)
        headers = auth_headers("i4d_student@example.com")

        r = client.post(
            f"/api/v1/upload/assignment-file?assignment_id={assignment.id}",
            files={"file": ("mywork.pdf", b"%PDF-1.4 data", "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        file_url = r.json()["file_url"]

        r = client.post(
            f"/api/v1/assignments/{assignment.id}/submit",
            json={"textContent": "my real work", "files": [{"file_url": file_url}]},
            headers=headers,
        )
        assert r.status_code == 200, r.text


# ----- Task 4 (quiz-engine spec §5): multi_select scoring ---------------------


class TestMultiSelectScoring:
    """Exact-set scoring, no partial credit (spec §5). Uses the canonical
    /courses/{cid}/quizzes/{qid}/submit route (no /start needed — mirrors
    TestPendingReviewFlow's direct-submit pattern)."""

    def _setup(self, db, make_user, auth_headers, correct_indices=(0, 2), n_options=3, mark=10.0):
        instructor = make_user(role="instructor", email=f"ms_instr_{id(self)}@example.com")
        student = make_user(role="student", email=f"ms_student_{id(self)}@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        question = _add_multi_select_question(
            db, quiz, mark=mark, correct_indices=correct_indices, n_options=n_options
        )
        _enroll(db, student, course)
        headers = auth_headers(student.user_email)
        return course, quiz, question, headers

    def _submit(self, client, course, quiz, question, headers, answer):
        return client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): answer}},
            headers=headers,
        )

    def test_exact_match_scores_full_marks(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, [0, 2])
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["earned_marks"] == 10.0
        assert body["passed"] is True

    def test_exact_match_order_independent(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, [2, 0])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 10.0

    def test_superset_scores_zero(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, [0, 1, 2])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0

    def test_subset_scores_zero(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, [0])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0

    def test_empty_selection_scores_zero(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, [])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0

    def test_wrong_set_scores_zero(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, [1])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0

    def test_duplicate_indices_collapse_to_exact_match(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, [0, 0, 2])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 10.0

    def test_numeric_string_indices_accepted(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, ["0", "2"])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 10.0

    def test_out_of_range_index_scores_zero_not_500(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, [0, 1, 9])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0

    def test_non_list_payload_scores_zero_not_500(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, 0)
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0

    def test_dict_payload_scores_zero_not_500(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, {"0": True})
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0

    def test_string_of_indices_element_non_numeric_scores_zero(self, client, db, make_user, auth_headers):
        course, quiz, question, headers = self._setup(db, make_user, auth_headers)
        r = self._submit(client, course, quiz, question, headers, ["a", "b"])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0

    def test_no_partial_credit_for_almost_right(self, client, db, make_user, auth_headers):
        """3 correct out of 3 required, 1 extra wrong one included -> still 0,
        never a fractional mark (spec §5: no partial credit in v1)."""
        course, quiz, question, headers = self._setup(
            db, make_user, auth_headers, correct_indices=(0, 1, 2), n_options=4
        )
        r = self._submit(client, course, quiz, question, headers, [0, 1, 2, 3])
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0.0


class TestMultiSelectResultsPayload:
    def test_results_breakdown_returns_correct_answers_and_selected(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="ms_res_instr@example.com")
        student = make_user(role="student", email="ms_res_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        question = _add_multi_select_question(db, quiz, mark=10.0, correct_indices=(0, 2))
        _enroll(db, student, course)
        headers = auth_headers("ms_res_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): [0, 2]}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = next(q for q in r.json()["questions"] if q["question_id"] == question.question_id)
        assert item["type"] == "multi_select"
        assert item["correct_answer"] == [0, 2]
        assert item["user_answer"] == [0, 2]
        assert item["is_correct"] is True

    def test_results_breakdown_wrong_selection_shows_correct_set_anyway(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="ms_res_instr2@example.com")
        student = make_user(role="student", email="ms_res_student2@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        question = _add_multi_select_question(db, quiz, mark=10.0, correct_indices=(0, 2))
        _enroll(db, student, course)
        headers = auth_headers("ms_res_student2@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): [1]}},
            headers=headers,
        )
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = next(q for q in r.json()["questions"] if q["question_id"] == question.question_id)
        assert item["correct_answer"] == [0, 2]
        assert item["user_answer"] == [1]
        assert item["is_correct"] is False


class TestMultiSelectOwnerGating:
    def test_non_owner_get_hides_correct_answers(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="ms_gate_instr@example.com")
        student = make_user(role="student", email="ms_gate_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_multi_select_question(db, quiz, correct_indices=(0, 2))
        _enroll(db, student, course)

        headers = auth_headers("ms_gate_student@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["showCorrectAnswers"] is False
        question = body["questions"][0]
        assert question["type"] == "multi_select"
        # Options are shown (not sensitive) but not which ones are correct.
        assert question["options"] == ["Option 0", "Option 1", "Option 2"]
        assert "correctAnswers" not in question

    def test_owner_get_shows_correct_answers_list(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "ms_gate_owner@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_multi_select_question(db, quiz, correct_indices=(0, 2))

        headers = auth_headers("ms_gate_owner@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["showCorrectAnswers"] is True
        assert body["questions"][0]["correctAnswers"] == [0, 2]

    def test_admin_get_shows_correct_answers_list(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="ms_gate_instr2@example.com")
        admin = make_user(role="admin", email="ms_gate_admin@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_multi_select_question(db, quiz, correct_indices=(1,))

        headers = _admin_headers(client, db, admin)
        r = client.get(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["questions"][0]["correctAnswers"] == [1]


class TestMultiSelectNotManuallyGraded:
    def test_multi_select_never_sets_pending_review(self, client, db, make_user, auth_headers):
        """multi_select is auto-graded — submitting only a multi_select
        question must end the attempt immediately, never pending_review."""
        instructor = make_user(role="instructor", email="ms_auto_instr@example.com")
        student = make_user(role="student", email="ms_auto_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        question = _add_multi_select_question(db, quiz, mark=10.0, correct_indices=(0, 2))
        _enroll(db, student, course)
        headers = auth_headers("ms_auto_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): [0, 2]}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["attempt_status"] == "attempt_ended"
        assert body["pending_review"] is False
        assert body["passed"] is True


class TestMultiSelectSubmitAttemptsRoute:
    """The /quiz-attempts/{id}/submit rehydration path reads
    QuizAttemptAnswer.given_answer (stored as str(given)) when the client
    submits with no body — must still score multi_select correctly."""

    def test_answer_then_bodyless_submit_scores_correctly(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="ms_route_instr@example.com")
        student = make_user(role="student", email="ms_route_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        question = _add_multi_select_question(db, quiz, mark=10.0, correct_indices=(0, 2))
        _enroll(db, student, course)
        headers = auth_headers("ms_route_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        assert r.status_code == 200, r.text
        attempt_id = r.json()["attempt_id"]

        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/answers",
            json={"question_id": question.question_id, "given_answer": [0, 2]},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        r = client.post(f"/api/v1/quiz-attempts/{attempt_id}/submit", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["earned_marks"] == 10.0
        assert body["passed"] is True


# ----- Task 5: results endpoint feedback-policy enforcement (spec R4/§4) ----


class TestMultiSelectOversizeSubmission:
    """Task 5 add-on (Task 4 review, minor): _multi_select_answer_list must
    reject a submission longer than the question's option count instead of
    materializing/iterating an arbitrarily large list."""

    def test_oversize_list_scores_zero_not_500(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="ms_oversize_instr@example.com")
        student = make_user(role="student", email="ms_oversize_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        question = _add_multi_select_question(db, quiz, mark=10.0, correct_indices=(0, 2), n_options=3)
        _enroll(db, student, course)
        headers = auth_headers("ms_oversize_student@example.com")

        oversize = list(range(20000))
        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): oversize}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["earned_marks"] == 0.0
        assert body["passed"] is False


def _add_tf_question(db, quiz, mark=10.0, correct="true", explanation=""):
    question = QuizQuestion(
        quiz_id=quiz.id, question_title="True or false?",
        question_type="true_false", question_mark=mark,
        answer_explanation=explanation,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    db.add_all([
        QuizQuestionAnswer(
            belongs_question_id=question.question_id,
            answer_title=text, is_correct=(val == correct), answer_order=order,
        )
        for order, (text, val) in enumerate([("True", "true"), ("False", "false")])
    ])
    db.commit()
    return question


class TestFeedbackPolicyResultsEndpoint:
    """Task 5 (spec R4/§4): the results endpoint filters per-question
    correct_answer/explanation/is_correct according to quiz_feedback_mode,
    and adds a top-level feedback_mode. Assert key ABSENCE, not just value —
    a redacted field must be deleted from the dict, never merely nulled
    (None is itself meaningful for a not-yet-graded manual question)."""

    # ----- reveal_immediate (explicit + legacy "default") -------------------

    def test_reveal_immediate_shows_full_review(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="fb_imm_instr@example.com")
        student = make_user(role="student", email="fb_imm_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_immediate")
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("fb_imm_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=headers,
        )
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["feedback_mode"] == "reveal_immediate"
        item = body["questions"][0]
        assert item["correct_answer"] == 0
        assert "explanation" in item
        assert item["is_correct"] is True
        assert item["achieved_mark"] == 10.0

    def test_legacy_default_mode_behaves_as_reveal_immediate(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="fb_legacy_instr@example.com")
        student = make_user(role="student", email="fb_legacy_student@example.com")
        course = _make_course(db, instructor)
        # quiz_feedback_mode defaults to the literal string "default" at
        # the model level (legacy rows) — never explicitly set here.
        quiz = _make_quiz(db, instructor, course)
        assert quiz.quiz_feedback_mode == "default"
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("fb_legacy_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=headers,
        )
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["feedback_mode"] == "reveal_immediate"
        item = body["questions"][0]
        assert item["correct_answer"] == 0
        assert "explanation" in item
        assert item["is_correct"] is True

    # ----- reveal_never -------------------------------------------------

    def test_reveal_never_omits_correct_answer_explanation_and_is_correct_forever(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="fb_never_instr@example.com")
        student = make_user(role="student", email="fb_never_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_never")
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("fb_never_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=headers,
        )
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["feedback_mode"] == "reveal_never"
        item = body["questions"][0]
        assert "correct_answer" not in item
        assert "explanation" not in item
        assert "is_correct" not in item
        # achieved_mark/total and the student's own answer stay visible.
        assert item["achieved_mark"] == 10.0
        assert item["user_answer"] == 0
        assert body["earned_marks"] == 10.0
        assert body["total_marks"] == 10.0

    def test_reveal_never_multi_select_omits_same_three_keys(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="fb_never_ms_instr@example.com")
        student = make_user(role="student", email="fb_never_ms_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_never")
        question = _add_multi_select_question(db, quiz, mark=10.0, correct_indices=(0, 2))
        _enroll(db, student, course)
        headers = auth_headers("fb_never_ms_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): [0, 2]}},
            headers=headers,
        )
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert item["type"] == "multi_select"
        assert "correct_answer" not in item
        assert "explanation" not in item
        assert "is_correct" not in item
        assert item["achieved_mark"] == 10.0
        assert item["user_answer"] == [0, 2]

    def test_reveal_never_never_reveals_even_long_after_submission(
        self, client, db, make_user, auth_headers
    ):
        """"Forever" means forever — not just immediately post-submit."""
        instructor = make_user(role="instructor", email="fb_never_time_instr@example.com")
        student = make_user(role="student", email="fb_never_time_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_never")
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("fb_never_time_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=headers,
        )
        attempt_id = r.json()["attempt_id"]

        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        attempt.attempt_ended_at = datetime.now(timezone.utc) - timedelta(days=365)
        db.commit()

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert "correct_answer" not in item
        assert "is_correct" not in item

    # ----- reveal_after_due: no time limit -> immediate ----------------------

    def test_reveal_after_due_untimed_quiz_is_immediate(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="fb_due_untimed_instr@example.com")
        student = make_user(role="student", email="fb_due_untimed_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(
            db, instructor, course, feedback_mode="reveal_after_due", time_limit=0
        )
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("fb_due_untimed_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=headers,
        )
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["feedback_mode"] == "reveal_after_due"
        item = body["questions"][0]
        assert item["correct_answer"] == 0
        assert "explanation" in item
        assert item["is_correct"] is True

    # ----- reveal_after_due: timed quiz, both sides of the deadline ---------

    def test_reveal_after_due_timed_quiz_before_deadline_omits_answer_and_explanation(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="fb_due_pre_instr@example.com")
        student = make_user(role="student", email="fb_due_pre_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(
            db, instructor, course, feedback_mode="reveal_after_due", time_limit=30
        )
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("fb_due_pre_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]
        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        # Attempt just started — well before the 30-minute deadline.
        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["feedback_mode"] == "reveal_after_due"
        item = body["questions"][0]
        assert "correct_answer" not in item
        assert "explanation" not in item
        # is_correct/achieved_mark/needs_review stay visible pre-due.
        assert item["is_correct"] is True
        assert item["achieved_mark"] == 10.0
        assert item["needs_review"] is False

    def test_reveal_after_due_timed_quiz_after_deadline_reveals_full_review(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="fb_due_post_instr@example.com")
        student = make_user(role="student", email="fb_due_post_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(
            db, instructor, course, feedback_mode="reveal_after_due", time_limit=30
        )
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        headers = auth_headers("fb_due_post_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]
        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        # Push the attempt's started_at far enough into the past that the
        # 30-minute deadline (+ grace) has passed — same technique
        # TestServerTimer uses to probe the deadline boundary.
        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        attempt.attempt_started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert item["correct_answer"] == 0
        assert "explanation" in item
        assert item["is_correct"] is True

    def test_reveal_after_due_timed_quiz_multi_select_both_sides_of_deadline(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="fb_due_ms_instr@example.com")
        student = make_user(role="student", email="fb_due_ms_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(
            db, instructor, course, feedback_mode="reveal_after_due", time_limit=30
        )
        question = _add_multi_select_question(db, quiz, mark=10.0, correct_indices=(0, 2))
        _enroll(db, student, course)
        headers = auth_headers("fb_due_ms_student@example.com")

        r = client.post(f"/api/v1/quizzes/{quiz.id}/start", headers=headers)
        attempt_id = r.json()["attempt_id"]
        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            json={"answers": {str(question.question_id): [0, 2]}},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert "correct_answer" not in item
        assert "explanation" not in item
        assert item["is_correct"] is True

        attempt = db.query(QuizAttempt).filter_by(attempt_id=attempt_id).one()
        attempt.attempt_started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert item["correct_answer"] == [0, 2]
        assert "explanation" in item

    # ----- pending_review (manual grading) under each mode -------------------

    def test_pending_review_essay_reveal_immediate_no_correctness_leak_before_grading(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "fb_pending_imm_instr@example.com")
        student = make_user(role="student", email="fb_pending_imm_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_immediate")
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        headers = auth_headers("fb_pending_imm_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "my essay"}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert item["needs_review"] is True
        assert item["is_correct"] is None  # no leak before grading, any mode
        # achieved_mark is the persisted QuizAttemptAnswer row's value —
        # 0.0 at submit time (not yet graded), same as any ungraded manual
        # answer; it's not the ambiguous "never graded" signal (needs_review
        # is), so it is a real 0.0 rather than None here.
        assert item["achieved_mark"] == 0.0
        assert item["correct_answer"] is None

    def test_pending_review_essay_reveal_never_still_no_leak_and_omits_is_correct(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "fb_pending_never_instr@example.com")
        student = make_user(role="student", email="fb_pending_never_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_never")
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        headers = auth_headers("fb_pending_never_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "my essay"}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert item["needs_review"] is True
        assert "is_correct" not in item
        assert "correct_answer" not in item
        assert "explanation" not in item

    def test_manual_graded_feedback_text_visible_after_grading_reveal_immediate(
        self, client, db, make_user, auth_headers
    ):
        """Instructor free-text feedback (grade endpoint's `feedback` body
        field) surfaces on the results item and is never redacted by
        feedback_mode — the spec only names correct_answer/explanation/
        is_correct."""
        instructor = _make_approved_instructor(db, make_user, "fb_grade_txt_instr@example.com")
        student = make_user(role="student", email="fb_grade_txt_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_never")
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        student_headers = auth_headers("fb_grade_txt_student@example.com")
        instr_headers = auth_headers("fb_grade_txt_instr@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "my essay"}},
            headers=student_headers,
        )
        attempt_id = r.json()["attempt_id"]

        pending = client.get(
            f"/api/v1/courses/{course.id}/quizzes/pending-reviews", headers=instr_headers
        ).json()["pending_reviews"]
        answer_id = pending[0]["ungraded_answer_ids"][0]
        r = client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/answers/{answer_id}/grade",
            json={"achieved_mark": 15, "feedback": "Nice structure, needs more detail"},
            headers=instr_headers,
        )
        assert r.status_code == 200, r.text
        client.post(f"/api/v1/quiz-attempts/{attempt_id}/finalize", headers=instr_headers)

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=student_headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert item["feedback"] == "Nice structure, needs more detail"
        assert item["achieved_mark"] == 15.0
        # is_correct still hidden forever under reveal_never even once graded.
        assert "is_correct" not in item

    # ----- owner/instructor/admin viewing: never gated -----------------------

    def test_course_owner_instructor_sees_full_review_regardless_of_mode(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "fb_owner_instr@example.com")
        student = make_user(role="student", email="fb_owner_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_never")
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        student_headers = auth_headers("fb_owner_student@example.com")
        instr_headers = auth_headers("fb_owner_instr@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=student_headers,
        )
        attempt_id = r.json()["attempt_id"]

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=instr_headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert item["correct_answer"] == 0
        assert "explanation" in item
        assert item["is_correct"] is True

    def test_admin_sees_full_review_regardless_of_mode(
        self, client, db, make_user, auth_headers
    ):
        instructor = make_user(role="instructor", email="fb_admin_instr@example.com")
        student = make_user(role="student", email="fb_admin_student@example.com")
        admin = make_user(role="admin", email="fb_admin_admin@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, feedback_mode="reveal_never")
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        student_headers = auth_headers("fb_admin_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=student_headers,
        )
        attempt_id = r.json()["attempt_id"]

        admin_headers = _admin_headers(client, db, admin)
        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=admin_headers)
        assert r.status_code == 200, r.text
        item = r.json()["questions"][0]
        assert item["correct_answer"] == 0
        assert item["is_correct"] is True


# ----- Task 5 controller add-ons: results is_correct/achieved_mark from -----
# ----- persisted rows, not live recomputation --------------------------------


class TestResultsUseSavedRowsNotLiveRecompute:
    def test_editing_options_after_submission_does_not_flip_historical_results(
        self, client, db, make_user, auth_headers
    ):
        """Controller ruling: is_correct/achieved_mark must reflect what was
        ACTUALLY scored at submit time, read back from the persisted
        QuizAttemptAnswer row — not recomputed live from the current
        QuizQuestionAnswer rows. Editing a question's correct index after a
        submission must not silently flip a historical result."""
        instructor = _make_approved_instructor(db, make_user, "recompute_instr@example.com")
        student = make_user(role="student", email="recompute_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0, n_options=3)
        _enroll(db, student, course)
        headers = auth_headers("recompute_student@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        attempt_id = r.json()["attempt_id"]
        body = r.json()
        assert body["earned_marks"] == 10.0
        assert body["passed"] is True

        # Reorder which option is correct — mirrors an instructor editing
        # the quiz's answer key after students have already attempted it.
        rows = db.query(QuizQuestionAnswer).filter(
            QuizQuestionAnswer.belongs_question_id == mc.question_id
        ).order_by(QuizQuestionAnswer.answer_order).all()
        for row in rows:
            row.is_correct = (row.answer_order == 1)  # was 0, now 1
        db.commit()

        r = client.get(f"/api/v1/quiz-attempts/{attempt_id}/results", headers=headers)
        assert r.status_code == 200, r.text
        result = r.json()
        item = result["questions"][0]
        # Historical result unchanged: still correct, still 10 marks —
        # consistent with the attempt header (earned_marks/passed/counts).
        assert item["is_correct"] is True
        assert item["achieved_mark"] == 10.0
        assert result["earned_marks"] == 10.0
        assert result["passed"] is True
        assert result["correct_count"] == 1
        assert result["incorrect_count"] == 0
        # correct_answer_out (current answer key) DOES reflect the edit —
        # it's meant to show the quiz as it exists now.
        assert item["correct_answer"] == 1


# ----- Task 5 controller add-on: update_quiz null "questions" must not ------
# ----- collapse to [] and wipe the bank --------------------------------------


class TestUpdateQuizQuestionsNullVsMalformed:
    def test_null_questions_preserves_bank(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "null_q_instr@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz)
        _add_mc_question(db, quiz)
        _add_mc_question(db, quiz)
        headers = auth_headers("null_q_instr@example.com")

        before = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count()
        assert before == 3

        r = client.put(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}",
            json={"questions": None, "timeLimit": 45},
            headers=headers,
        )
        assert r.status_code == 200, r.text

        db.expire_all()
        after = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count()
        assert after == 3
        assert db.query(Quiz).filter_by(id=quiz.id).one().quiz_time_limit == 45

    def test_empty_dict_questions_rejected_422_not_wipe(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "dict_q_instr@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz)
        headers = auth_headers("dict_q_instr@example.com")

        r = client.put(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}",
            json={"questions": {}},
            headers=headers,
        )
        assert r.status_code == 422, r.text

        db.expire_all()
        assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count() == 1

    def test_empty_string_questions_rejected_422_not_wipe(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "str_q_instr@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz)
        headers = auth_headers("str_q_instr@example.com")

        r = client.put(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}",
            json={"questions": ""},
            headers=headers,
        )
        assert r.status_code == 422, r.text

        db.expire_all()
        assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count() == 1

    def test_zero_questions_rejected_422_not_wipe(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "zero_q_instr@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz)
        headers = auth_headers("zero_q_instr@example.com")

        r = client.put(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}",
            json={"questions": 0},
            headers=headers,
        )
        assert r.status_code == 422, r.text

        db.expire_all()
        assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count() == 1

    def test_string_abc_questions_rejected_422_not_wipe(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "abc_q_instr@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        _add_mc_question(db, quiz)
        headers = auth_headers("abc_q_instr@example.com")

        r = client.put(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}",
            json={"questions": "abc"},
            headers=headers,
        )
        assert r.status_code == 422, r.text

        db.expire_all()
        assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count() == 1
