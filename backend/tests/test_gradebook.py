"""Manual grading queue, rubrics, gradebook + CSV (Task 2 of the Learning
Experience plan).

Covers docs/superpowers/specs/2026-09-02-learning-experience-design.md
section A1 item 12 (rubric grading math) + A2 (gradebook):

  - GET /courses/{id}/grading-queue: merged quiz-essay + assignment queue,
    sorted oldest-first.
  - Rubric-scored grading on POST /submissions/{id}/grade: criterion-match
    validation, over-max rejection, explicit-grade override, sum math with
    late penalty applied after.
  - Rubric shape validation on assignment create/update.
  - GET /courses/{id}/gradebook matrix: graded/pending/missing/late
    statuses.
  - GET /courses/{id}/gradebook.csv shape.
  - Guards: student 403, other instructor 403.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizQuestion, QuizQuestionAnswer


# ----- factories (mirrors test_assessment_integrity.py) -----------------------


def _make_instructor(db, email="instructor@example.com"):
    from app.models.user import User
    from app.core.security import get_password_hash

    u = User(
        user_login="gb_instructor", user_pass=get_password_hash("Test@123"),
        user_nicename="gb_instructor", user_email=email,
        display_name="GB Instructor", role="instructor", is_active=True, is_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    u._test_password = "Test@123"
    return u


def _approve_instructor(db, user):
    from app.models.user import InstructorProfile

    profile = db.query(InstructorProfile).filter_by(user_id=user.id).first()
    if profile:
        profile.is_approved = True
    else:
        db.add(InstructorProfile(user_id=user.id, is_approved=True))
    db.commit()
    return user


def _make_approved_instructor(db, make_user, email):
    instructor = make_user(role="instructor", email=email)
    return _approve_instructor(db, instructor)


def _admin_headers(client, db, admin):
    """Admin logins require TOTP 2FA — enrol a secret and send the current
    code (mirrors test_assessment_integrity._admin_headers)."""
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


def _make_course(db, instructor, title="Gradebook Course"):
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


def _make_quiz(db, instructor, course, passing_grade=50, title="Quiz"):
    quiz = Quiz(
        post_author=instructor.id,
        post_parent=course.id,
        post_title=title,
        quiz_passing_grade=passing_grade,
    )
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
                      total_points=100, rubric=None):
    assignment = Assignment(
        course_id=course.id,
        created_by=instructor.id,
        title=title,
        due_date=due_date,
        late_policy=late_policy,
        late_penalty_pct=late_penalty_pct,
        status=status,
        total_points=total_points,
        rubric=rubric or [],
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def _submit_assignment_direct(db, assignment, student, is_late=False, submitted_at=None):
    """Create a submission row directly (bypassing the HTTP endpoint) so
    tests can control submitted_at ordering precisely for queue-sort
    assertions."""
    sub = AssignmentSubmission(
        assignment_id=assignment.id,
        user_id=student.id,
        text_content="my work",
        files=[],
        status=SubmissionStatus.SUBMITTED,
        is_late=is_late,
        submitted_at=submitted_at or datetime.now(timezone.utc),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


# ----- grading-queue merge + sort ---------------------------------------------


class TestGradingQueue:
    def test_merges_quiz_essay_and_assignment_entries_sorted_oldest_first(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "queue_instr@example.com")
        student = make_user(role="student", email="queue_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        essay = _add_essay_question(db, quiz, mark=20.0)
        assignment = _make_assignment(db, instructor, course, title="Essay HW")
        _enroll(db, student, course)
        student_headers = auth_headers("queue_student@example.com")
        instr_headers = auth_headers("queue_instr@example.com")

        # Assignment submitted first (older).
        _submit_assignment_direct(
            db, assignment, student,
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        # Quiz essay submitted second (newer) via the real endpoint.
        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "my essay"}},
            headers=student_headers,
        )

        r = client.get(f"/api/v1/courses/{course.id}/grading-queue", headers=instr_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["count"] == 2
        queue = body["queue"]
        assert [e["type"] for e in queue] == ["assignment", "quiz_essay"]
        assert queue[0]["assignment_id"] == assignment.id
        assert queue[1]["quiz_id"] == quiz.id
        assert len(queue[1]["ungraded_answer_ids"]) == 1

    def test_graded_submission_and_finalized_attempt_excluded(
        self, client, db, make_user, auth_headers
    ):
        instructor = _make_approved_instructor(db, make_user, "queue_instr2@example.com")
        student = make_user(role="student", email="queue_student2@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)
        _enroll(db, student, course)
        instr_headers = auth_headers("queue_instr2@example.com")

        sub = _submit_assignment_direct(db, assignment, student)
        sub.status = SubmissionStatus.GRADED
        sub.grade = 90
        db.commit()

        r = client.get(f"/api/v1/courses/{course.id}/grading-queue", headers=instr_headers)
        assert r.status_code == 200, r.text
        assert r.json()["count"] == 0

    def test_queue_requires_course_owner_or_admin(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="queue_instr3@example.com")
        other_instructor = _make_approved_instructor(db, make_user, "queue_other@example.com")
        student = make_user(role="student", email="queue_student3@example.com")
        course = _make_course(db, instructor)
        _enroll(db, student, course)
        other_headers = auth_headers("queue_other@example.com")
        student_headers = auth_headers("queue_student3@example.com")

        r = client.get(f"/api/v1/courses/{course.id}/grading-queue", headers=other_headers)
        assert r.status_code == 403, r.text

        r = client.get(f"/api/v1/courses/{course.id}/grading-queue", headers=student_headers)
        assert r.status_code == 403, r.text


# ----- rubric validation on assignment create/update --------------------------


class TestRubricShapeValidation:
    def test_create_rejects_non_list_rubric(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "rub_instr1@example.com")
        course = _make_course(db, instructor)
        headers = auth_headers("rub_instr1@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/assignments",
            json={"title": "HW", "rubric": "not a list"},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_create_rejects_too_many_criteria(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "rub_instr2@example.com")
        course = _make_course(db, instructor)
        headers = auth_headers("rub_instr2@example.com")

        rubric = [{"criterion": f"C{i}", "max_points": 5} for i in range(21)]
        r = client.post(
            f"/api/v1/courses/{course.id}/assignments",
            json={"title": "HW", "rubric": rubric},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_create_rejects_non_positive_max_points(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "rub_instr3@example.com")
        course = _make_course(db, instructor)
        headers = auth_headers("rub_instr3@example.com")

        r = client.post(
            f"/api/v1/courses/{course.id}/assignments",
            json={"title": "HW", "rubric": [{"criterion": "Clarity", "max_points": 0}]},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_create_accepts_valid_rubric(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "rub_instr4@example.com")
        course = _make_course(db, instructor)
        headers = auth_headers("rub_instr4@example.com")

        rubric = [
            {"criterion": "Clarity", "max_points": 10},
            {"criterion": "Correctness", "max_points": 20},
        ]
        r = client.post(
            f"/api/v1/courses/{course.id}/assignments",
            json={"title": "HW", "rubric": rubric},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assignment_id = r.json()["id"]
        assignment = db.query(Assignment).filter_by(id=assignment_id).one()
        assert len(assignment.rubric) == 2

    def test_update_rejects_duplicate_criteria(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "rub_instr5@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)
        headers = auth_headers("rub_instr5@example.com")

        r = client.put(
            f"/api/v1/courses/{course.id}/assignments/{assignment.id}",
            json={"rubric": [
                {"criterion": "Clarity", "max_points": 10},
                {"criterion": "Clarity", "max_points": 5},
            ]},
            headers=headers,
        )
        assert r.status_code == 400, r.text


# ----- rubric-scored grading ---------------------------------------------------


class TestRubricScoredGrading:
    def _setup(self, db, make_user, auth_headers, email_suffix, **assignment_kwargs):
        instructor = _make_approved_instructor(db, make_user, f"grade_instr{email_suffix}@example.com")
        student = make_user(role="student", email=f"grade_student{email_suffix}@example.com")
        course = _make_course(db, instructor)
        rubric = [
            {"criterion": "Clarity", "max_points": 10},
            {"criterion": "Correctness", "max_points": 20},
        ]
        assignment = _make_assignment(db, instructor, course, rubric=rubric, **assignment_kwargs)
        _enroll(db, student, course)
        submission = _submit_assignment_direct(db, assignment, student)
        instr_headers = auth_headers(f"grade_instr{email_suffix}@example.com")
        return instructor, student, course, assignment, submission, instr_headers

    def test_rubric_sum_becomes_grade(self, client, db, make_user, auth_headers):
        _, _, _, _, submission, headers = self._setup(db, make_user, auth_headers, "1")

        r = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={"rubricScores": [
                {"criterion": "Clarity", "points": 8},
                {"criterion": "Correctness", "points": 15},
            ]},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["grade"] == 23.0
        assert body["rawGrade"] == 23.0

        db.refresh(submission)
        assert float(submission.grade) == 23.0
        assert submission.rubric_scores == [
            {"criterion": "Clarity", "points": 8.0},
            {"criterion": "Correctness", "points": 15.0},
        ]

    def test_mismatched_criterion_rejected(self, client, db, make_user, auth_headers):
        _, _, _, _, submission, headers = self._setup(db, make_user, auth_headers, "2")

        r = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={"rubricScores": [
                {"criterion": "Clarity", "points": 8},
                {"criterion": "Effort", "points": 5},
            ]},
            headers=headers,
        )
        assert r.status_code == 400, r.text
        assert "Unknown rubric criterion" in r.text

    def test_missing_criterion_rejected(self, client, db, make_user, auth_headers):
        _, _, _, _, submission, headers = self._setup(db, make_user, auth_headers, "2b")

        r = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={"rubricScores": [{"criterion": "Clarity", "points": 8}]},
            headers=headers,
        )
        assert r.status_code == 400, r.text
        assert "missing criteria" in r.text

    def test_over_max_points_rejected(self, client, db, make_user, auth_headers):
        _, _, _, _, submission, headers = self._setup(db, make_user, auth_headers, "3")

        r = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={"rubricScores": [
                {"criterion": "Clarity", "points": 999},
                {"criterion": "Correctness", "points": 15},
            ]},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_explicit_grade_overrides_rubric_sum(self, client, db, make_user, auth_headers):
        _, _, _, _, submission, headers = self._setup(db, make_user, auth_headers, "4")

        r = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={
                "grade": 99,
                "rubricScores": [
                    {"criterion": "Clarity", "points": 8},
                    {"criterion": "Correctness", "points": 15},
                ],
            },
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["rawGrade"] == 99.0
        assert body["grade"] == 99.0

        db.refresh(submission)
        assert float(submission.grade) == 99.0
        # rubric_scores still stored even though grade came from the
        # explicit field.
        assert submission.rubric_scores is not None

    def test_rubric_sum_with_late_penalty_applied_after(self, client, db, make_user, auth_headers):
        _, _, _, assignment, submission, headers = self._setup(
            db, make_user, auth_headers, "5",
            late_policy="penalty", late_penalty_pct=20,
        )
        submission.is_late = True
        db.commit()

        r = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={"rubricScores": [
                {"criterion": "Clarity", "points": 10},
                {"criterion": "Correctness", "points": 20},
            ]},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Sum = 30, penalty 20% -> 24.0
        assert body["rawGrade"] == 30.0
        assert body["grade"] == 24.0
        assert body["latePenaltyApplied"] is True

    def test_grade_without_rubric_when_assignment_has_no_rubric(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "grade_instr6@example.com")
        student = make_user(role="student", email="grade_student6@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course)  # no rubric
        _enroll(db, student, course)
        submission = _submit_assignment_direct(db, assignment, student)
        headers = auth_headers("grade_instr6@example.com")

        r = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={"rubricScores": [{"criterion": "Clarity", "points": 5}]},
            headers=headers,
        )
        assert r.status_code == 400, r.text

    def test_plain_grade_still_works_without_rubric_scores(self, client, db, make_user, auth_headers):
        _, _, _, _, submission, headers = self._setup(db, make_user, auth_headers, "7")

        r = client.post(
            f"/api/v1/submissions/{submission.id}/grade",
            json={"grade": 88, "feedback": "Nice"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["grade"] == 88.0


# ----- gradebook matrix --------------------------------------------------------


class TestGradebookMatrix:
    def test_statuses_graded_pending_missing_late(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "matrix_instr@example.com")
        s_graded = make_user(role="student", email="matrix_graded@example.com")
        s_pending = make_user(role="student", email="matrix_pending@example.com")
        s_missing = make_user(role="student", email="matrix_missing@example.com")
        s_late = make_user(role="student", email="matrix_late@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, total_points=50)

        for s in (s_graded, s_pending, s_missing, s_late):
            _enroll(db, s, course)

        graded_sub = _submit_assignment_direct(db, assignment, s_graded)
        graded_sub.status = SubmissionStatus.GRADED
        graded_sub.grade = 45
        db.commit()

        _submit_assignment_direct(db, assignment, s_pending)
        # s_missing never submits.
        _submit_assignment_direct(db, assignment, s_late, is_late=True)

        instr_headers = auth_headers("matrix_instr@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=instr_headers)
        assert r.status_code == 200, r.text
        body = r.json()

        assert len(body["items"]) == 1
        item_key = f"assignment:{assignment.id}"
        by_student = {row["student"]["id"]: row["cells"][item_key] for row in body["rows"]}

        assert by_student[s_graded.id]["status"] == "graded"
        assert by_student[s_graded.id]["score"] == 45.0
        assert by_student[s_pending.id]["status"] == "pending"
        assert by_student[s_missing.id]["status"] == "missing"
        assert by_student[s_late.id]["status"] == "late"
        assert by_student[s_late.id]["is_late"] is True

    def test_quiz_column_reflects_best_ended_attempt(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "matrix_instr2@example.com")
        student = make_user(role="student", email="matrix_quiz_student@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course, passing_grade=50)
        mc = _add_mc_question(db, quiz, mark=10.0, correct_index=0)
        _enroll(db, student, course)
        student_headers = auth_headers("matrix_quiz_student@example.com")
        instr_headers = auth_headers("matrix_instr2@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(mc.question_id): 0}},
            headers=student_headers,
        )

        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=instr_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        item_key = f"quiz:{quiz.id}"
        row = next(row for row in body["rows"] if row["student"]["id"] == student.id)
        assert row["cells"][item_key]["status"] == "graded"
        assert row["cells"][item_key]["score"] == 10.0
        assert row["cells"][item_key]["max"] == 10.0

    def test_quiz_pending_review_shows_pending_status(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "matrix_instr3@example.com")
        student = make_user(role="student", email="matrix_quiz_student2@example.com")
        course = _make_course(db, instructor)
        quiz = _make_quiz(db, instructor, course)
        essay = _add_essay_question(db, quiz, mark=20.0)
        _enroll(db, student, course)
        student_headers = auth_headers("matrix_quiz_student2@example.com")
        instr_headers = auth_headers("matrix_instr3@example.com")

        client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(essay.question_id): "text"}},
            headers=student_headers,
        )

        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=instr_headers)
        body = r.json()
        item_key = f"quiz:{quiz.id}"
        row = next(row for row in body["rows"] if row["student"]["id"] == student.id)
        assert row["cells"][item_key]["status"] == "pending"

    def test_draft_assignment_excluded_from_gradebook(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "matrix_instr4@example.com")
        course = _make_course(db, instructor)
        _make_assignment(db, instructor, course, status="draft")
        instr_headers = auth_headers("matrix_instr4@example.com")

        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=instr_headers)
        assert r.status_code == 200, r.text
        assert r.json()["items"] == []

    def test_gradebook_requires_course_owner_or_admin(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="matrix_instr5@example.com")
        other_instructor = _make_approved_instructor(db, make_user, "matrix_other@example.com")
        student = make_user(role="student", email="matrix_student5@example.com")
        course = _make_course(db, instructor)
        _enroll(db, student, course)
        other_headers = auth_headers("matrix_other@example.com")
        student_headers = auth_headers("matrix_student5@example.com")

        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=other_headers)
        assert r.status_code == 403, r.text

        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=student_headers)
        assert r.status_code == 403, r.text

    def test_admin_can_view_gradebook(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "matrix_instr6@example.com")
        admin = make_user(role="admin", email="matrix_admin@example.com")
        course = _make_course(db, instructor)
        admin_headers = _admin_headers(client, db, admin)

        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=admin_headers)
        assert r.status_code == 200, r.text

    def test_cancelled_enrollment_excluded_from_matrix(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "matrix_instr7@example.com")
        active_student = make_user(role="student", email="matrix_active@example.com")
        cancelled_student = make_user(role="student", email="matrix_cancelled@example.com")
        course = _make_course(db, instructor)
        _enroll(db, active_student, course)
        cancelled_enrollment = _enroll(db, cancelled_student, course)
        cancelled_enrollment.enrollment_status = "cancelled"
        db.commit()

        instr_headers = auth_headers("matrix_instr7@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=instr_headers)
        assert r.status_code == 200, r.text
        body = r.json()

        student_ids = {row["student"]["id"] for row in body["rows"]}
        assert active_student.id in student_ids
        assert cancelled_student.id not in student_ids

    def test_completed_enrollment_still_included_in_matrix(self, client, db, make_user, auth_headers):
        """A student who finished the course flips enrollment_status to
        "completed" (course_service.calculate_course_progress) — this must
        NOT be treated the same as "cancelled"; the gradebook still needs
        to show their grades."""
        instructor = _make_approved_instructor(db, make_user, "matrix_instr8@example.com")
        completed_student = make_user(role="student", email="matrix_completed@example.com")
        course = _make_course(db, instructor)
        completed_enrollment = _enroll(db, completed_student, course)
        completed_enrollment.enrollment_status = "completed"
        db.commit()

        instr_headers = auth_headers("matrix_instr8@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=instr_headers)
        assert r.status_code == 200, r.text
        student_ids = {row["student"]["id"] for row in r.json()["rows"]}
        assert completed_student.id in student_ids

    def test_suspended_enrollment_still_included_in_matrix(self, client, db, make_user, auth_headers):
        """A lapsed-membership student flips enrollment_status to
        "suspended" (membership_access.suspend_membership_enrollments) —
        this is a grace-period state the member typically reactivates from,
        NOT a removal like "cancelled". ADJUDICATED: the gradebook must
        still show their row so grading continuity survives the lapse."""
        instructor = _make_approved_instructor(db, make_user, "matrix_instr9@example.com")
        suspended_student = make_user(role="student", email="matrix_suspended@example.com")
        course = _make_course(db, instructor)
        suspended_enrollment = _enroll(db, suspended_student, course)
        suspended_enrollment.enrollment_status = "suspended"
        db.commit()

        instr_headers = auth_headers("matrix_instr9@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/gradebook", headers=instr_headers)
        assert r.status_code == 200, r.text
        student_ids = {row["student"]["id"] for row in r.json()["rows"]}
        assert suspended_student.id in student_ids


# ----- CSV export ---------------------------------------------------------------


class TestGradebookCsv:
    def test_csv_shape(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "csv_instr@example.com")
        student = make_user(role="student", email="csv_student@example.com")
        course = _make_course(db, instructor)
        assignment = _make_assignment(db, instructor, course, title="Essay 1", total_points=50)
        _enroll(db, student, course)
        sub = _submit_assignment_direct(db, assignment, student)
        sub.status = SubmissionStatus.GRADED
        sub.grade = 42
        db.commit()

        instr_headers = auth_headers("csv_instr@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/gradebook.csv", headers=instr_headers)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/csv")
        assert "gradebook-course" in r.headers["content-disposition"]

        lines = r.text.strip().splitlines()
        header = lines[0].split(",")
        assert header[0] == "Student"
        assert header[1] == "Email"
        assert "Essay 1" in header
        assert any("42.0/50" in line for line in lines[1:])

    def test_csv_requires_course_owner_or_admin(self, client, db, make_user, auth_headers):
        instructor = make_user(role="instructor", email="csv_instr2@example.com")
        other_instructor = _make_approved_instructor(db, make_user, "csv_other@example.com")
        course = _make_course(db, instructor)
        other_headers = auth_headers("csv_other@example.com")

        r = client.get(f"/api/v1/courses/{course.id}/gradebook.csv", headers=other_headers)
        assert r.status_code == 403, r.text

    def test_cancelled_enrollment_excluded_from_csv(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "csv_instr3@example.com")
        cancelled_student = make_user(role="student", email="csv_cancelled@example.com")
        course = _make_course(db, instructor)
        cancelled_enrollment = _enroll(db, cancelled_student, course)
        cancelled_enrollment.enrollment_status = "cancelled"
        db.commit()

        instr_headers = auth_headers("csv_instr3@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/gradebook.csv", headers=instr_headers)
        assert r.status_code == 200, r.text
        assert cancelled_student.user_email not in r.text

    def test_csv_neutralizes_formula_injection_in_display_name(self, client, db, make_user, auth_headers):
        """Same CSV-formula-injection hole as live_class_attendance's export
        (review finding, proven live): a display_name starting with '='
        must come out single-quote-prefixed so Excel/Sheets render it as
        literal text instead of executing it on open."""
        instructor = _make_approved_instructor(db, make_user, "csv_instr4@example.com")
        course = _make_course(db, instructor)

        from app.models.user import User
        from app.core.security import get_password_hash

        malicious = User(
            user_login="csv_evil", user_pass=get_password_hash("Test@123"),
            user_nicename="csv_evil", user_email="csv_evil@example.com",
            display_name="=cmd|'/c calc'!A1", role="student",
            is_active=True, is_verified=True,
        )
        db.add(malicious)
        db.commit()
        db.refresh(malicious)
        _enroll(db, malicious, course)

        instr_headers = auth_headers("csv_instr4@example.com")
        r = client.get(f"/api/v1/courses/{course.id}/gradebook.csv", headers=instr_headers)
        assert r.status_code == 200, r.text

        import csv as csv_module
        import io as io_module

        reader = csv_module.reader(io_module.StringIO(r.text))
        rows = list(reader)
        data_row = next(row for row in rows[1:] if row and row[1] == malicious.user_email)
        assert data_row[0] == "'=cmd|'/c calc'!A1"
