from datetime import date, datetime, timezone

from app.models.certificate import Certificate, IssuedCertificate
from app.models.cohort import Cohort
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.internship import Internship, InternshipAttendance, InternshipVoucher


def test_my_vouchers_returns_real_progress_certificate_and_attendance(
    client, db, make_user, as_user
):
    student = make_user(role="student")
    other_student = make_user(role="student")
    spoc = make_user(role="instructor")
    cohort = Cohort(spoc_user_id=spoc.id, name="Applied cohort", slug="applied-cohort")
    db.add(cohort)
    db.flush()
    internship = Internship(
        title="Applied AI Internship",
        slug="applied-ai-internship",
        price=2500,
        is_published=True,
        spoc_user_id=spoc.id,
        cohort_id=cohort.id,
    )
    course = Course(
        post_author=spoc.id,
        post_title="Applied AI practicum",
        post_status="publish",
        course_price_type="paid",
        course_price=2500,
    )
    db.add_all([internship, course])
    db.flush()
    voucher = InternshipVoucher(
        code="REAL-PROGRESS-1",
        internship_id=internship.id,
        buyer_user_id=student.id,
        amount_paid=2500,
        status="redeemed",
        engagement_status="completed",
        redeemed_on_course_id=course.id,
        redeemed_at=datetime.now(timezone.utc),
    )
    other_voucher = InternshipVoucher(
        code="OTHER-STUDENT-1",
        internship_id=internship.id,
        buyer_user_id=other_student.id,
        amount_paid=2500,
        status="issued",
    )
    enrollment = Enrollment(
        user_id=student.id,
        course_id=course.id,
        enrollment_status="completed",
        course_progress_percentage=100,
        completion_date=datetime.now(timezone.utc),
    )
    template = Certificate(post_author=spoc.id, post_title="Completion")
    db.add_all([voucher, other_voucher, enrollment, template])
    db.flush()
    issued = IssuedCertificate(
        certificate_id=template.id,
        course_id=course.id,
        user_id=student.id,
        certificate_hash="real-progress-certificate-hash",
        secure_certificate_id="SASHA-REAL-PROGRESS",
        certificate_title="Completion",
        completion_date=datetime.now(timezone.utc),
        is_valid=True,
    )
    db.add(issued)
    db.add_all(
        [
            InternshipAttendance(
                internship_id=internship.id,
                user_id=student.id,
                attended_at=date(2026, 9, 10),
                status="present",
            ),
            InternshipAttendance(
                internship_id=internship.id,
                user_id=student.id,
                attended_at=date(2026, 9, 11),
                status="late",
            ),
            InternshipAttendance(
                internship_id=internship.id,
                user_id=student.id,
                attended_at=date(2026, 9, 12),
                status="absent",
            ),
        ]
    )
    db.commit()
    db.refresh(issued)
    as_user(student)

    response = client.get("/api/v1/internships/my-vouchers")
    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    item = response.json()[0]
    assert item["internship_title"] == "Applied AI Internship"
    assert item["spoc_name"] == spoc.display_name
    assert item["course_progress"]["progress_percentage"] == 100
    assert item["course_progress"]["is_completed"] is True
    assert item["engagement_status"] == "completed"
    assert item["attendance_count"] == 2
    assert item["certificate_issued"] is True
    assert item["issued_certificate_id"] == issued.id
