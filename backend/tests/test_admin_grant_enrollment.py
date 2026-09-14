"""A-H4: admin grant course enrollment — Batch 2 platform fix wave.

POST /admin/enrollments {user_id, course_id} grants via
fulfillment_service.grant_purchased_course rescue semantics with
source="admin", order_id NULL. 409 if already enrolled.
"""
from app.models.enrollment import Enrollment


class TestAdminGrantEnrollment:
    def test_admin_grants_enrollment(self, client, db, make_user, as_user, course):
        admin = make_user(role="admin", email="admin_grant1@example.com")
        student = make_user(role="student", email="grant_student1@example.com")
        as_user(admin)

        r = client.post("/api/v1/admin/enrollments", json={
            "user_id": student.id, "course_id": course.id,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user_id"] == student.id
        assert body["course_id"] == course.id

        row = db.query(Enrollment).filter(
            Enrollment.user_id == student.id, Enrollment.course_id == course.id,
        ).first()
        assert row is not None
        assert row.enrollment_status == "enrolled"
        assert row.enrollment_source == "admin"
        assert row.order_id is None

    def test_duplicate_enrollment_409(self, client, db, make_user, as_user, course):
        admin = make_user(role="admin", email="admin_grant2@example.com")
        student = make_user(role="student", email="grant_student2@example.com")
        as_user(admin)

        r1 = client.post("/api/v1/admin/enrollments", json={
            "user_id": student.id, "course_id": course.id,
        })
        assert r1.status_code == 200, r1.text

        r2 = client.post("/api/v1/admin/enrollments", json={
            "user_id": student.id, "course_id": course.id,
        })
        assert r2.status_code == 409

    def test_rescues_suspended_enrollment(self, client, db, make_user, as_user, course):
        admin = make_user(role="admin", email="admin_grant3@example.com")
        student = make_user(role="student", email="grant_student3@example.com")

        row = Enrollment(
            course_id=course.id, user_id=student.id,
            enrollment_status="suspended", enrollment_source="membership",
            order_id=None,
        )
        db.add(row)
        db.commit()

        as_user(admin)
        r = client.post("/api/v1/admin/enrollments", json={
            "user_id": student.id, "course_id": course.id,
        })
        assert r.status_code == 200, r.text

        db.refresh(row)
        assert row.enrollment_status == "enrolled"
        # Rescue must NOT rewrite the original source.
        assert row.enrollment_source == "membership"

    def test_non_admin_forbidden(self, client, db, make_user, auth_headers, course):
        student = make_user(role="student", email="notadmin_grant@example.com")
        target = make_user(role="student", email="grant_target@example.com")
        headers = auth_headers(student.user_email, student._test_password)

        r = client.post("/api/v1/admin/enrollments", json={
            "user_id": target.id, "course_id": course.id,
        }, headers=headers)
        assert r.status_code == 403

    def test_404_for_unknown_course(self, client, db, make_user, as_user):
        admin = make_user(role="admin", email="admin_grant4@example.com")
        student = make_user(role="student", email="grant_student4@example.com")
        as_user(admin)

        r = client.post("/api/v1/admin/enrollments", json={
            "user_id": student.id, "course_id": 999999,
        })
        assert r.status_code == 404

    def test_404_for_unknown_user(self, client, db, make_user, as_user, course):
        admin = make_user(role="admin", email="admin_grant5@example.com")
        as_user(admin)

        r = client.post("/api/v1/admin/enrollments", json={
            "user_id": 999999, "course_id": course.id,
        })
        assert r.status_code == 404
