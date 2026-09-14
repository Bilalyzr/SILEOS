"""Evaluation-integrity regressions for graded content (logic audit).

The covered bug class:

* ``mark_lesson_complete`` fabricated assignment submissions with full
  marks — students could mark assignment lessons complete without an
  instructor ever grading anything;
* quiz progress counted ATTEMPTS instead of distinct passed quizzes, so
  one quiz passed twice reported 2/1 completed and 200% overall progress;
* ``submit_quiz`` never enforced ``quiz_max_attempts_allowed`` (only the
  start-attempt endpoint did);
* issued certificates left the quiz/assignment percentage columns at
  their 0 defaults and masked a stored 0% overall with ``or 100``;
* ``CouponUpdate`` accepted a 500% percentage discount that
  ``validate_and_compute`` would then apply in full.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pyotp
from pydantic import ValidationError

from app.core import totp
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.certificate import IssuedCertificate
from app.models.coupon import Coupon
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion, QuizQuestionAnswer
from app.schemas.coupon import CouponUpdate
from app.services.certificate_service import CertificateService
from app.services.coupon_service import validate_and_compute


# ----- factories -----------------------------------------------------------


def _make_course(db, instructor, title="Eval Course"):
    course = Course(
        post_author=instructor.id,
        post_title=title,
        post_content="Course content",
        post_excerpt="Course excerpt",
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


def _make_assignment(db, instructor, course, title="Essay", points=100):
    assignment = Assignment(
        course_id=course.id,
        created_by=instructor.id,
        title=title,
        total_points=points,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def _make_quiz(db, instructor, course, passing_grade=50, max_attempts=0, title="Quiz"):
    quiz = Quiz(
        post_author=instructor.id,
        post_parent=course.id,
        post_title=title,
        quiz_passing_grade=passing_grade,
        quiz_max_attempts_allowed=max_attempts,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def _add_mc_question(db, quiz, mark=10.0):
    """One multiple-choice question; answer index 0 is the correct one
    (submit_quiz grades multiple_choice by answer index)."""
    question = QuizQuestion(
        quiz_id=quiz.id,
        question_title="Pick one",
        question_type="multiple_choice",
        question_mark=mark,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    db.add_all([
        QuizQuestionAnswer(
            belongs_question_id=question.question_id,
            answer_title="Right",
            is_correct=True,
            answer_order=0,
        ),
        QuizQuestionAnswer(
            belongs_question_id=question.question_id,
            answer_title="Wrong",
            is_correct=False,
            answer_order=1,
        ),
    ])
    db.commit()
    return question


def _enroll(db, user, course):
    enrollment = Enrollment(user_id=user.id, course_id=course.id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def _make_coupon(db, owner, code, discount_type="percentage", discount_value="10"):
    coupon = Coupon(
        code=code,
        description="",
        discount_type=discount_type,
        discount_value=Decimal(discount_value),
        applicability="all_courses",
        usage_count=0,
        per_user_limit=1,
        minimum_purchase_amount=Decimal("0"),
        is_active=True,
        created_by=owner.id,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


def _no_certificate_pdf(monkeypatch):
    """Keep tests hermetic: completion paths best-effort generate a PDF and
    warm the render cache (a background thread running headless Chrome that
    writes cert_img_* files next to the tests' cwd). Both are stubbed out —
    the stray files otherwise flip the pre-existing webp-ratio tests in
    test_certificate_asset_delivery.py from SKIP to FAIL."""
    monkeypatch.setattr(CertificateService, "_generate_pdf", lambda data, path: None)
    monkeypatch.setattr(CertificateService, "warm_render_cache", lambda certificate: None)


def _admin_headers(client, db, admin):
    """Login headers for an admin. Admin logins are refused without 2FA,
    so enrol a TOTP secret and send the matching code."""
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


def _mark_complete(client, headers, course, content_id):
    return client.post(
        f"/api/v1/courses/{course.id}/lessons/{content_id}/complete",
        headers=headers,
    )


# ----- assignment gate -------------------------------------------------------


def test_assignment_complete_without_submission_is_403(client, db, make_user, auth_headers):
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor)
    assignment = _make_assignment(db, instructor, course)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")

    before = db.query(AssignmentSubmission).count()
    assert before == 0

    r = _mark_complete(client, headers, course, assignment.id)

    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "Submit the assignment first — it is graded by your instructor."
    # The endpoint must not fabricate a graded submission.
    assert db.query(AssignmentSubmission).count() == before


def test_assignment_complete_with_ungraded_submission_is_403(client, db, make_user, auth_headers):
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor)
    assignment = _make_assignment(db, instructor, course)
    _enroll(db, student, course)
    db.add(AssignmentSubmission(
        user_id=student.id,
        assignment_id=assignment.id,
        status="submitted",
        text_content="My essay",
        files=[],
    ))
    db.commit()
    headers = auth_headers("student@example.com")

    before = db.query(AssignmentSubmission).count()

    r = _mark_complete(client, headers, course, assignment.id)

    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "Awaiting instructor grading."

    db.expire_all()
    rows = db.query(AssignmentSubmission).all()
    assert len(rows) == before
    row = rows[0]
    assert row.status == "submitted"
    assert row.grade is None  # not force-graded to assignment.total_points
    assert row.graded_at is None
    assert row.text_content == "My essay"


def test_assignment_complete_with_graded_submission_is_noop(client, db, make_user, auth_headers, monkeypatch):
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor)
    assignment = _make_assignment(db, instructor, course, points=100)
    _enroll(db, student, course)
    # graded_by stays NULL — the gate keys on the submission status only.
    db.add(AssignmentSubmission(
        user_id=student.id,
        assignment_id=assignment.id,
        status="graded",
        grade=Decimal("85"),
        graded_by=None,
    ))
    db.commit()
    headers = auth_headers("student@example.com")

    before = db.query(AssignmentSubmission).count()

    r = _mark_complete(client, headers, course, assignment.id)

    assert r.status_code == 200, r.text
    assert r.json()["course_completed"] is True

    db.expire_all()
    rows = db.query(AssignmentSubmission).all()
    assert len(rows) == before  # no new row fabricated
    assert float(rows[0].grade) == 85.0  # instructor's grade untouched

    # Certificate issued by the progress recalc: percent columns populated.
    cert = db.query(IssuedCertificate).filter_by(
        user_id=student.id, course_id=course.id
    ).first()
    assert cert is not None
    assert cert.course_completion_percentage == 100
    assert cert.quiz_completion_percentage == 0  # course has no quizzes
    assert cert.assignment_completion_percentage == 100  # 1/1 graded


# ----- quiz progress math ----------------------------------------------------


def test_two_passing_attempts_on_one_quiz_count_as_one(client, db, make_user, auth_headers, monkeypatch):
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="Quiz Only Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50, max_attempts=0)
    question = _add_mc_question(db, quiz)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")
    payload = {"answers": {str(question.question_id): 0}}

    for _ in range(2):  # two passing attempts on the SAME quiz
        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json=payload,
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["passed"] is True

    db.expire_all()
    assert db.query(QuizAttempt).count() == 2  # both attempts stored
    enrollment = db.query(Enrollment).filter_by(
        user_id=student.id, course_id=course.id
    ).one()
    assert enrollment.completed_quizzes == 1  # but ONE distinct quiz passed
    assert enrollment.course_progress_percentage <= 100  # never above 100
    assert enrollment.course_progress_percentage == 100  # 1/1 => complete
    assert enrollment.completion_date is not None
    assert enrollment.enrollment_status == "completed"


# ----- quiz max attempts -----------------------------------------------------


def test_submit_quiz_beyond_max_attempts_is_403(client, db, make_user, auth_headers, monkeypatch):
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="Attempt Limit Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50, max_attempts=1)
    question = _add_mc_question(db, quiz)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")
    payload = {"answers": {str(question.question_id): 0}}
    url = f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit"

    r1 = client.post(url, json=payload, headers=headers)
    assert r1.status_code == 200, r1.text

    r2 = client.post(url, json=payload, headers=headers)
    assert r2.status_code == 403, r2.text
    assert r2.json()["detail"] == "Maximum attempts reached"

    assert db.query(QuizAttempt).count() == 1  # the blocked submit stored nothing


# ----- coupon discount validation ---------------------------------------------


def test_coupon_update_rejects_percentage_over_100():
    with pytest.raises(ValidationError):
        CouponUpdate(discount_type="percentage", discount_value=500)

    # In-range values and value-only payloads still validate.
    assert CouponUpdate(discount_type="percentage", discount_value=50).discount_value == 50
    assert CouponUpdate(discount_value=500).discount_value == 500


def test_validate_and_compute_clamps_percentage_discount(db, make_user):
    owner = make_user(role="admin", email="coupon-admin@example.com")
    student = make_user(role="student", email="coupon-student@example.com")
    # Legacy row: 150% — more than the whole price.
    _make_coupon(db, owner, "HUGE", discount_type="percentage", discount_value="150")

    result = validate_and_compute(
        db, code="HUGE", user_id=student.id, course_ids=[], total_amount=1000.0
    )

    assert result.discount_amount == 1000.0  # min(100, 150)% of 1000
    assert result.final_amount == 0.0


def test_update_coupon_passes_discount_type_through(client, db, make_user):
    admin = make_user(role="admin", email="coupon-admin@example.com")
    coupon = _make_coupon(db, admin, "SWITCH", discount_type="percentage", discount_value="10")
    headers = _admin_headers(client, db, admin)

    r = client.put(
        f"/api/v1/coupons/{coupon.id}",
        json={"discount_type": "fixed", "discount_value": 50},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["discount_type"] == "fixed"

    db.expire_all()
    row = db.query(Coupon).filter_by(id=coupon.id).one()
    assert row.discount_type == "fixed"
    assert float(row.discount_value) == 50.0

    # The new cross-validator fires through the API too.
    r2 = client.put(
        f"/api/v1/coupons/{coupon.id}",
        json={"discount_type": "percentage", "discount_value": 500},
        headers=headers,
    )
    assert r2.status_code == 422, r2.text


# ----- certificate percent columns --------------------------------------------


def test_certificate_percent_columns_and_null_progress_fallback(db, make_user, monkeypatch):
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="Cert Course")
    assignment = _make_assignment(db, instructor, course)
    db.add(AssignmentSubmission(
        user_id=student.id,
        assignment_id=assignment.id,
        status="graded",
        grade=Decimal("70"),
    ))
    enrollment = _enroll(db, student, course)
    enrollment.completion_date = datetime.now(timezone.utc)
    enrollment.course_progress_percentage = None  # tracker column never set
    db.commit()

    cert, newly_issued = CertificateService.issue_certificate_for_enrollment(db, enrollment)

    assert newly_issued is True
    assert cert is not None
    assert cert.course_completion_percentage == 100  # NULL falls back to 100
    assert cert.quiz_completion_percentage == 0  # no quizzes -> 0, not a crash
    assert cert.assignment_completion_percentage == 100  # 1/1 graded
