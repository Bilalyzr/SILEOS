"""Backend correctness & hygiene regressions (logic audit, task 3 + follow-ups).

Covered bug classes:

* ``submit_quiz`` crashed with a 500 when a multiple-choice answer arrived
  as a non-numeric string (``str < int`` TypeError) instead of scoring the
  question wrong — and truncated fractional indices (``1.9`` -> option 1)
  instead of scoring them wrong;
* ``POST /coupons/validate`` compared ``count >= coupon.per_user_limit``
  with a NULL limit (TypeError -> 500) and re-implemented the discount
  math, so validate could disagree with the apply/checkout path;
* coupon updates accepted an unknown ``discount_type`` and let a
  percentage coupon absorb an out-of-range ``discount_value`` when the
  payload omitted the type (stored-type cross-check -> 422);
* ``GET /courses/{id}/progress`` recomputed progress through the same
  service used by write paths, so a read could flip enrollment status,
  rewrite tracker columns, and even auto-issue a certificate;
* certificate revival after a completion regression also resurrected
  ADMIN-revoked certificates — revival is now gated on the regression
  marker only, so an admin revoke is terminal;
* bulk admin force-complete skipped the progress recalc, so a below-100%
  student could be marked completed (and mailed) with no basis.
"""

from decimal import Decimal
from datetime import datetime, timezone

import pytest
import pyotp

from app.core import totp
from app.models.assignment import Assignment
from app.models.coupon import Coupon, CouponUsage
from app.models.course import Course
from app.models.certificate import (
    COMPLETION_REGRESSED_INVALIDATION_REASON,
    IssuedCertificate,
)
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion, QuizQuestionAnswer
from app.services.certificate_service import CertificateService
from app.services.coupon_service import CouponError, validate_and_compute


# ----- factories -----------------------------------------------------------


def _make_course(db, instructor, title="Hygiene Course"):
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


def _add_mc_question(db, quiz, mark=10.0, n_options=2, correct_index=0):
    """One multiple-choice question. Answer ordering defines the option
    index the client sends; `correct_index` picks which option is correct
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
            answer_title=f"Option {i}",
            is_correct=(i == correct_index),
            answer_order=i,
        )
        for i in range(n_options)
    ])
    db.commit()
    return question


def _enroll(db, user, course):
    enrollment = Enrollment(user_id=user.id, course_id=course.id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def _make_coupon(db, owner, code, discount_type="percentage", discount_value="10",
                 per_user_limit=1):
    coupon = Coupon(
        code=code,
        description="",
        discount_type=discount_type,
        discount_value=Decimal(discount_value),
        applicability="all_courses",
        usage_count=0,
        per_user_limit=per_user_limit,
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
    warm the render cache (a background thread running headless Chrome).
    Both are stubbed out (same rationale as test_evaluation_gates)."""
    monkeypatch.setattr(CertificateService, "_generate_pdf", lambda data, path: None)
    monkeypatch.setattr(CertificateService, "warm_render_cache", lambda certificate: None)


def _admin_headers(client, db, admin):
    """Login headers for an admin. Admin logins are refused without 2FA,
    so enrol a TOTP secret and send the matching code (same pattern as
    test_evaluation_gates)."""
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


# ----- item 2: string answers to multiple-choice questions -------------------


def test_non_numeric_string_answer_is_scored_wrong_not_500(
    client, db, make_user, auth_headers
):
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="String Answer Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50)
    question = _add_mc_question(db, quiz, mark=10.0)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")

    # A client sending the answer as an arbitrary string used to hit
    # `user_answer < len(all_answers)` -> TypeError -> 500.
    r = client.post(
        f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
        json={"answers": {str(question.question_id): "elephant"}},
        headers=headers,
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["earned_marks"] == 0  # scored wrong, not crashed
    assert body["total_marks"] == 10
    assert body["passed"] is False

    # The attempt still persisted with the raw answer.
    attempt = db.query(QuizAttempt).filter_by(
        user_id=student.id, quiz_id=quiz.id
    ).one()
    assert attempt.attempt_status == "attempt_ended"
    assert attempt.earned_marks == 0


def test_numeric_string_answer_index_is_cast_and_scored(
    client, db, make_user, auth_headers, monkeypatch
):
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="Numeric String Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50)
    question = _add_mc_question(db, quiz, mark=10.0)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")

    # The index arriving as a JSON string ("0") is cast and graded normally.
    r = client.post(
        f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
        json={"answers": {str(question.question_id): "0"}},
        headers=headers,
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["earned_marks"] == 10
    assert body["passed"] is True


# ----- item 4: coupon validate parity ----------------------------------------


def test_validate_with_null_per_user_limit_returns_200(client, db, make_user, auth_headers):
    owner = make_user(role="admin", email="coupon-admin@example.com")
    student = make_user(role="student", email="coupon-null@example.com")
    # Legacy row: per_user_limit never backfilled -> NULL.
    _make_coupon(db, owner, "NULLLIM", per_user_limit=None)
    headers = auth_headers("coupon-null@example.com")

    r = client.post(
        "/api/v1/coupons/validate",
        json={"code": "NULLLIM", "course_ids": [], "total_amount": 1000.0},
        headers=headers,
    )

    # NULL limit means "once" (service rule) — not a TypeError 500.
    assert r.status_code == 200, r.text
    assert r.json()["valid"] is True


def test_validate_endpoint_matches_apply_math(client, db, make_user, auth_headers):
    owner = make_user(role="admin", email="coupon-admin@example.com")
    student = make_user(role="student", email="coupon-parity@example.com")
    coupon = _make_coupon(db, owner, "PARITY15", discount_value="15")
    headers = auth_headers("coupon-parity@example.com")

    r = client.post(
        "/api/v1/coupons/validate",
        json={"code": "PARITY15", "course_ids": [], "total_amount": 2000.0},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    api = r.json()
    assert api["valid"] is True

    # The apply path (validate_and_compute) must promise the exact same
    # numbers the validate endpoint showed the user.
    result = validate_and_compute(
        db, code="PARITY15", user_id=student.id, course_ids=[], total_amount=2000.0
    )
    assert api["discount_amount"] == pytest.approx(result.discount_amount)
    assert api["final_amount"] == pytest.approx(result.final_amount)

    # Parity on rejection too: burn the (NULL-ish) per-user limit, then both
    # paths must refuse the coupon — validate with valid=False, apply by
    # raising CouponError.
    db.add(CouponUsage(
        coupon_id=coupon.id,
        user_id=student.id,
        discount_amount=Decimal("0"),
    ))
    db.commit()

    r2 = client.post(
        "/api/v1/coupons/validate",
        json={"code": "PARITY15", "course_ids": [], "total_amount": 2000.0},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["valid"] is False

    with pytest.raises(CouponError):
        validate_and_compute(
            db, code="PARITY15", user_id=student.id, course_ids=[], total_amount=2000.0
        )


# ----- item 6: GET /progress is read-only ------------------------------------


def test_get_course_progress_writes_nothing(client, db, make_user, auth_headers):
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="Readonly Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50)
    _enroll(db, student, course)

    # A real passing attempt exists, but the enrollment row is stale:
    # trackers zeroed, status still 'enrolled'. A GET must report the
    # recomputed 100% WITHOUT fixing up the row or issuing a certificate.
    db.add(QuizAttempt(
        user_id=student.id,
        quiz_id=quiz.id,
        course_id=course.id,
        total_questions=1,
        total_answered_questions=1,
        total_marks=10,
        earned_marks=10,
        attempt_info="{}",
        attempt_status="attempt_ended",
    ))
    db.commit()

    headers = auth_headers("student@example.com")
    r = client.get(f"/api/v1/courses/{course.id}/progress", headers=headers)

    assert r.status_code == 200, r.text
    assert r.json()["overall_progress"] == 100.0
    assert r.json()["certificate_earned"] is True

    db.expire_all()
    enrollment = db.query(Enrollment).filter_by(
        user_id=student.id, course_id=course.id
    ).one()
    assert enrollment.enrollment_status == "enrolled"  # not flipped
    assert enrollment.completion_date is None  # not set
    assert not enrollment.course_progress_percentage  # tracker untouched
    # A read must never auto-issue a certificate.
    assert db.query(IssuedCertificate).filter_by(
        user_id=student.id, course_id=course.id
    ).count() == 0


# ----- item 7: invalidated certificates revive on re-completion ---------------


def _submit_quiz_ok(client, headers, course, quiz, question):
    """Submit a passing attempt (answer index 0 is the correct one)."""
    r = client.post(
        f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
        json={"answers": {str(question.question_id): "0"}},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["passed"] is True
    return r


def _enrollment_of(db, student, course):
    db.expire_all()
    return db.query(Enrollment).filter_by(
        user_id=student.id, course_id=course.id
    ).one()


def _cert_of(db, student, course):
    db.expire_all()
    return db.query(IssuedCertificate).filter_by(
        user_id=student.id, course_id=course.id
    ).one()


def test_invalidated_certificate_revives_on_re_completion(
    client, db, make_user, auth_headers, monkeypatch
):
    """Full journey: complete -> regression invalidates the cert and unlinks
    it -> legitimate re-completion must REVIVE the same certificate row and
    re-stamp the enrollment instead of early-returning "already issued"."""
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="Revival Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50, title="Quiz")
    question = _add_mc_question(db, quiz, mark=10.0)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")

    # 1) Completing the only quiz pushes the enrollment to 100% and
    #    auto-issues a valid certificate.
    _submit_quiz_ok(client, headers, course, quiz, question)

    cert = _cert_of(db, student, course)
    enrollment = _enrollment_of(db, student, course)
    assert cert.is_valid is True
    assert enrollment.completion_date is not None
    assert enrollment.certificate_id == str(cert.id)
    assert enrollment.certificate_url == cert.certificate_download_url

    # 2) Instructor adds content (a second quiz). The next write-path
    #    recalc (any quiz submit) sees 1/2 quizzes done, regresses the
    #    completion, invalidates the certificate, and unlinks it.
    quiz2 = _make_quiz(db, instructor, course, passing_grade=50, title="Quiz 2")
    question2 = _add_mc_question(db, quiz2, mark=10.0)
    _submit_quiz_ok(client, headers, course, quiz, question)  # re-submit = recalc

    cert = _cert_of(db, student, course)
    enrollment = _enrollment_of(db, student, course)
    assert cert.is_valid is False
    # Audit trail is the machine-readable regression marker (not free
    # text) — the revival branch keys off exactly this value.
    assert cert.invalidation_reason == COMPLETION_REGRESSED_INVALIDATION_REASON
    assert cert.invalidated_date is not None
    assert enrollment.completion_date is None
    assert enrollment.certificate_id is None
    assert enrollment.certificate_url is None

    # 3) Re-complete by passing the new quiz. The auto-issue call inside
    #    the recalc must revive the existing certificate.
    _submit_quiz_ok(client, headers, course, quiz2, question2)

    revived = _cert_of(db, student, course)
    enrollment = _enrollment_of(db, student, course)
    assert revived.id == cert.id  # same row revived, not a duplicate
    assert revived.is_valid is True
    assert not revived.invalidation_reason  # cleared
    assert revived.invalidated_date is None
    assert enrollment.completion_date is not None
    assert enrollment.certificate_id == str(revived.id)
    assert enrollment.certificate_url == revived.certificate_download_url
    # Still exactly one certificate per (user, course).
    assert db.query(IssuedCertificate).filter_by(
        user_id=student.id, course_id=course.id
    ).count() == 1


def test_invalidated_certificate_not_revived_when_enrollment_not_qualifying(
    client, db, make_user, auth_headers, monkeypatch
):
    """The revive branch only fires when the enrollment qualifies for
    issuance. A regressed enrollment (completion_date None) — or one whose
    assignments are not all approved — must keep the certificate invalid."""
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="No Revival Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50, title="Quiz")
    question = _add_mc_question(db, quiz, mark=10.0)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")

    # Complete, then regress via added content (same journey as above).
    _submit_quiz_ok(client, headers, course, quiz, question)
    quiz2 = _make_quiz(db, instructor, course, passing_grade=50, title="Quiz 2")
    _add_mc_question(db, quiz2, mark=10.0)
    _submit_quiz_ok(client, headers, course, quiz, question)

    cert = _cert_of(db, student, course)
    enrollment = _enrollment_of(db, student, course)
    assert cert.is_valid is False
    assert enrollment.completion_date is None

    # Case 1: completion regressed — no completion_date, so no revival.
    row, newly = CertificateService.issue_certificate_for_enrollment(db, enrollment)
    assert row is not None and row.id == cert.id
    assert newly is False
    assert row.is_valid is False  # stays invalid
    assert row.invalidation_reason == COMPLETION_REGRESSED_INVALIDATION_REASON
    assert row.invalidated_date is not None
    assert enrollment.certificate_id is None  # not re-stamped

    # Case 2: completion_date manually restored, but the (new) assignment
    # has no approved GRADED submission — the assignment gate must block
    # the revival exactly like it blocks fresh issuance.
    db.add(Assignment(
        course_id=course.id,
        created_by=instructor.id,
        title="Essay",
        total_points=100,
    ))
    enrollment.completion_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(enrollment)

    row, newly = CertificateService.issue_certificate_for_enrollment(db, enrollment)
    assert row is not None and row.id == cert.id
    assert newly is False
    assert row.is_valid is False
    assert enrollment.certificate_id is None


def test_admin_revoked_certificate_is_terminal_not_revived(
    client, db, make_user, auth_headers, monkeypatch
):
    """An ADMIN revoke (free-text reason) must survive every issuance hook:
    even when the enrollment still fully qualifies (completion_date set,
    all assignments approved), issue_certificate_for_enrollment returns
    (existing, False) and the cert stays invalid. Only the regression
    marker (previous test) may be revived."""
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    admin = make_user(role="admin", email="admin@example.com")
    course = _make_course(db, instructor, title="Admin Revoke Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50, title="Quiz")
    question = _add_mc_question(db, quiz, mark=10.0)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")
    admin_headers = _admin_headers(client, db, admin)

    # Complete -> valid certificate issued and stamped on the enrollment.
    _submit_quiz_ok(client, headers, course, quiz, question)
    cert = _cert_of(db, student, course)
    enrollment = _enrollment_of(db, student, course)
    assert cert.is_valid is True

    # Admin revokes with a deliberate, human reason.
    r = client.post(
        f"/api/v1/certificates/admin/{cert.id}/revoke",
        json={"reason": "Issued in error by support"},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_valid"] is False

    cert = _cert_of(db, student, course)
    enrollment = _enrollment_of(db, student, course)
    assert cert.is_valid is False
    assert cert.invalidation_reason == "Issued in error by support"
    assert cert.invalidated_date is not None
    assert enrollment.certificate_id is None  # unlinked

    # The enrollment still QUALIFIES for issuance (completion_date is set —
    # revoke does not regress it — and the course has no assignments), yet
    # the direct issuance call must refuse to revive the admin revoke.
    assert enrollment.completion_date is not None
    row, newly = CertificateService.issue_certificate_for_enrollment(db, enrollment)
    assert row is not None and row.id == cert.id
    assert newly is False
    assert row.is_valid is False  # stays revoked
    assert row.invalidation_reason == "Issued in error by support"  # untouched
    assert enrollment.certificate_id is None

    # And the automatic write path (quiz re-submit -> recalc -> issue hook)
    # must not resurrect it either.
    _submit_quiz_ok(client, headers, course, quiz, question)
    cert = _cert_of(db, student, course)
    enrollment = _enrollment_of(db, student, course)
    assert cert.is_valid is False
    assert cert.invalidation_reason == "Issued in error by support"
    assert enrollment.certificate_id is None
    # Still exactly one certificate row — no duplicate re-issue either.
    assert db.query(IssuedCertificate).filter_by(
        user_id=student.id, course_id=course.id
    ).count() == 1


# ----- item 2: bulk admin force-complete respects the recalc ------------------


def _seed_ended_attempt(db, user, course, quiz, mark=10.0):
    """Insert a passing ended attempt directly (migration/import style —
    no write-path recalc has ever run for this enrollment)."""
    db.add(QuizAttempt(
        user_id=user.id,
        quiz_id=quiz.id,
        course_id=course.id,
        total_questions=1,
        total_answered_questions=1,
        total_marks=mark,
        earned_marks=mark,
        attempt_info="{}",
        attempt_status="attempt_ended",
    ))
    db.commit()


def test_bulk_force_complete_respects_recalc(
    client, db, make_user, auth_headers, monkeypatch
):
    """Bulk `completed` must run the progress recalc like the single
    endpoint: a below-100% student is reverted to enrolled (no completion
    date, no certificate, NO completion email), while a student the recalc
    confirms keeps the completion and gets the notification."""
    _no_certificate_pdf(monkeypatch)
    from app.services.email_service import EmailService

    completions_mailed = []
    # Method may not exist on EmailService at all (pre-existing gap) —
    # install a recorder either way so we observe the call attempt.
    monkeypatch.setattr(
        EmailService,
        "send_enrollment_completion_notification",
        lambda **kw: completions_mailed.append(kw),
        raising=False,
    )

    instructor = make_user(role="instructor", email="instructor@example.com")
    admin = make_user(role="admin", email="admin@example.com")
    course = _make_course(db, instructor, title="Bulk Force Course")
    quiz1 = _make_quiz(db, instructor, course, passing_grade=50, title="Quiz 1")
    quiz2 = _make_quiz(db, instructor, course, passing_grade=50, title="Quiz 2")

    # halfway: one of two quizzes passed. completer: both passed.
    halfway = make_user(role="student", email="halfway@example.com")
    completer = make_user(role="student", email="completer@example.com")
    enrollment_halfway = _enroll(db, halfway, course)
    enrollment_completer = _enroll(db, completer, course)
    _seed_ended_attempt(db, halfway, course, quiz1)
    _seed_ended_attempt(db, completer, course, quiz1)
    _seed_ended_attempt(db, completer, course, quiz2)

    admin_headers = _admin_headers(client, db, admin)
    r = client.put(
        "/api/v1/admin/enrollments/bulk-update?new_status=completed",
        json=[enrollment_halfway.id, enrollment_completer.id],
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enrollments_updated"] == 2
    assert body["notifications_sent"] == 1  # only the confirmed completion

    # Below-100% student: the recalc reverted the force-complete.
    db.expire_all()
    halfway_row = db.query(Enrollment).filter_by(
        user_id=halfway.id, course_id=course.id
    ).one()
    assert halfway_row.enrollment_status == "enrolled"
    assert halfway_row.completion_date is None
    assert halfway_row.certificate_id is None
    assert halfway_row.course_progress_percentage == 50
    assert db.query(IssuedCertificate).filter_by(
        user_id=halfway.id, course_id=course.id
    ).count() == 0

    # Genuine completer: recalc confirmed, certificate auto-issued.
    completer_row = db.query(Enrollment).filter_by(
        user_id=completer.id, course_id=course.id
    ).one()
    assert completer_row.enrollment_status == "completed"
    assert completer_row.completion_date is not None
    completer_cert = db.query(IssuedCertificate).filter_by(
        user_id=completer.id, course_id=course.id
    ).one()
    assert completer_cert.is_valid is True
    assert completer_row.certificate_id == str(completer_cert.id)

    # Exactly one completion email, addressed to the confirmed student.
    assert len(completions_mailed) == 1
    assert completions_mailed[0]["student_email"] == "completer@example.com"


# ----- items 4+5: coupon update validation -------------------------------------


def test_coupon_update_rejects_unknown_discount_type(client, db, make_user):
    owner = make_user(role="admin", email="coupon-admin@example.com")
    coupon = _make_coupon(db, owner, "ENUMUPD", discount_value="10")
    headers = _admin_headers(client, db, owner)

    r = client.put(
        f"/api/v1/coupons/{coupon.id}",
        json={"discount_type": "banana"},
        headers=headers,
    )
    assert r.status_code == 422, r.text
    assert "Discount type" in r.text

    # The enum still accepts the legal values.
    r2 = client.put(
        f"/api/v1/coupons/{coupon.id}",
        json={"discount_type": "fixed"},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["discount_type"] == "fixed"


def test_coupon_update_value_checked_against_stored_percentage_type(
    client, db, make_user
):
    owner = make_user(role="admin", email="coupon-admin@example.com")
    pct = _make_coupon(db, owner, "PCTSTORED", discount_type="percentage",
                       discount_value="10")
    headers = _admin_headers(client, db, owner)

    # discount_value alone (no discount_type in the payload): the schema
    # cannot range-check it, so the STORED type must — 422, not a silent
    # out-of-range percentage (or a downstream 500) later.
    r = client.put(
        f"/api/v1/coupons/{pct.id}",
        json={"discount_value": 150},
        headers=headers,
    )
    assert r.status_code == 422, r.text

    db.expire_all()
    stored = db.query(Coupon).filter(Coupon.id == pct.id).one()
    assert stored.discount_value == Decimal("10")  # unchanged

    # Legal values still land.
    r2 = client.put(
        f"/api/v1/coupons/{pct.id}",
        json={"discount_value": 25},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["discount_value"] == 25

    # A fixed-type coupon may take amounts above 100 — the bound is
    # percentage-specific.
    fixed = _make_coupon(db, owner, "FIXEDSTORED", discount_type="fixed",
                         discount_value="50")
    r3 = client.put(
        f"/api/v1/coupons/{fixed.id}",
        json={"discount_value": 150},
        headers=headers,
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["discount_value"] == 150


# ----- item 7: fractional multiple-choice answers score wrong ------------------


def test_fractional_answer_index_scores_wrong_not_truncated(
    client, db, make_user, auth_headers, monkeypatch
):
    """The correct option sits at index 1, so a truncating cast of 1.9 to
    1 would mark it CORRECT. Both encodings — JSON float 1.9 and string
    "1.9" — must score wrong; whole indices in any encoding stay right."""
    _no_certificate_pdf(monkeypatch)
    instructor = make_user(role="instructor", email="instructor@example.com")
    student = make_user(role="student", email="student@example.com")
    course = _make_course(db, instructor, title="Fractional Course")
    quiz = _make_quiz(db, instructor, course, passing_grade=50)
    question = _add_mc_question(db, quiz, mark=10.0, n_options=3, correct_index=1)
    _enroll(db, student, course)
    headers = auth_headers("student@example.com")

    for payload in (1.9, "1.9", "1.0e0", 2.7):
        r = client.post(
            f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
            json={"answers": {str(question.question_id): payload}},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["earned_marks"] == 0, payload
        assert r.json()["passed"] is False, payload

    # Whole integers — JSON int, integer-valued float, numeric string —
    # still select their option and can score correct.
    r = client.post(
        f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
        json={"answers": {str(question.question_id): 1}},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["earned_marks"] == 10
    assert r.json()["passed"] is True

    r = client.post(
        f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
        json={"answers": {str(question.question_id): "1"}},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["earned_marks"] == 10

    r = client.post(
        f"/api/v1/courses/{course.id}/quizzes/{quiz.id}/submit",
        json={"answers": {str(question.question_id): 1.0}},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["earned_marks"] == 10
