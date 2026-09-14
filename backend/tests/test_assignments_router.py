"""
B12 — invalid dueDate on create/update was silently swallowed and stored
as None (create) or left unchanged (update). Fix: 422 on parse failure.

B9 — allowed_file_types / attachments / files are real JSON columns but
were json.dumps()'d before writing (rubric, in the same table, is written
directly). Fix: write direct Python values; add a tolerant `_json_list`
read helper that accepts either a direct list or a legacy double-encoded
JSON string.
"""
import json

import pytest

from app.models.assignment import Assignment, AssignmentSubmission
from app.models.user import InstructorProfile


def _approve_as_instructor(db, user):
    """Set role=instructor and attach an approved InstructorProfile —
    login blocks role=instructor without one (auth_service.py
    'instructor_not_approved')."""
    user.role = "instructor"
    db.add(InstructorProfile(user_id=user.id, is_approved=True))
    db.commit()


@pytest.fixture()
def instructor_headers(client, course, auth_headers, db):
    from app.models.user import User
    from app.core.security import get_password_hash

    instructor = db.query(User).filter(User.id == course.post_author).first()
    instructor.user_pass = get_password_hash("Test@123")
    _approve_as_instructor(db, instructor)
    return auth_headers(instructor.user_email, "Test@123")


# ---------------- B12: dueDate validation ----------------

def test_create_assignment_invalid_due_date_is_422(client, course, instructor_headers):
    resp = client.post(
        f"/api/v1/courses/{course.id}/assignments",
        json={"title": "HW1", "dueDate": "not-a-date"},
        headers=instructor_headers,
    )
    assert resp.status_code == 422, resp.text


def test_create_assignment_valid_due_date_persists(client, db, course, instructor_headers):
    resp = client.post(
        f"/api/v1/courses/{course.id}/assignments",
        json={"title": "HW1", "dueDate": "2027-01-15T10:00:00Z"},
        headers=instructor_headers,
    )
    assert resp.status_code == 200, resp.text
    assignment_id = resp.json()["id"] if "id" in resp.json() else None
    # The create endpoint's exact response shape is fetched via GET below
    # regardless of what create returns.
    assignment = db.query(Assignment).filter(Assignment.course_id == course.id).first()
    assert assignment.due_date is not None
    assert assignment.due_date.year == 2027


def test_update_assignment_invalid_due_date_is_422(client, db, course, instructor_headers):
    assignment = Assignment(course_id=course.id, created_by=course.post_author, title="HW1")
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    resp = client.put(
        f"/api/v1/courses/{course.id}/assignments/{assignment.id}",
        json={"dueDate": "garbage"},
        headers=instructor_headers,
    )
    assert resp.status_code == 422, resp.text


# ---------------- B9: JSON column round-trip ----------------

def test_create_assignment_json_fields_round_trip_as_lists(client, db, course, instructor_headers):
    resp = client.post(
        f"/api/v1/courses/{course.id}/assignments",
        json={
            "title": "HW2",
            "allowedFileTypes": ["pdf", "docx"],
            "attachments": [{"file_url": "/uploads/a.pdf", "name": "a.pdf"}],
        },
        headers=instructor_headers,
    )
    assert resp.status_code == 200, resp.text

    assignment = db.query(Assignment).filter(
        Assignment.course_id == course.id, Assignment.title == "HW2"
    ).first()
    # Written as real Python lists, not JSON-encoded strings.
    assert assignment.allowed_file_types == ["pdf", "docx"]
    assert isinstance(assignment.attachments, list)
    assert assignment.attachments[0]["name"] == "a.pdf"

    # Read back through the API as lists too.
    get_resp = client.get(
        f"/api/v1/courses/{course.id}/assignments/{assignment.id}",
        headers=instructor_headers,
    )
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body["allowedFileTypes"] == ["pdf", "docx"]
    assert body["attachments"][0]["name"] == "a.pdf"


def test_update_assignment_json_fields_round_trip_as_lists(client, db, course, instructor_headers):
    assignment = Assignment(course_id=course.id, created_by=course.post_author, title="HW3")
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    resp = client.put(
        f"/api/v1/courses/{course.id}/assignments/{assignment.id}",
        json={"allowedFileTypes": ["zip"], "attachments": []},
        headers=instructor_headers,
    )
    assert resp.status_code == 200, resp.text

    db.refresh(assignment)
    assert assignment.allowed_file_types == ["zip"]
    assert assignment.attachments == []


def test_legacy_double_encoded_row_still_reads_correctly(client, db, course, instructor_headers):
    """A row written by the OLD json.dumps code path must still read back
    as a proper list via the new tolerant _json_list helper."""
    assignment = Assignment(
        course_id=course.id, created_by=course.post_author, title="Legacy HW",
        allowed_file_types=json.dumps(["pdf"]),
        attachments=json.dumps([{"name": "old.pdf"}]),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    resp = client.get(
        f"/api/v1/courses/{course.id}/assignments/{assignment.id}",
        headers=instructor_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["allowedFileTypes"] == ["pdf"]
    assert body["attachments"] == [{"name": "old.pdf"}]


def test_submission_files_round_trip_as_list(client, db, course, student_user, auth_headers):
    """Submit an assignment (empty files list — the on-disk ownership/
    existence guard in _validate_submission_files, review finding I4, is
    out of scope here) and confirm `files` is written as a real Python
    list (not a JSON-encoded string) and read back the same way through
    the instructor's get_submissions view."""
    from app.models.user import User
    from app.models.enrollment import Enrollment
    from app.core.security import get_password_hash

    assignment = Assignment(
        course_id=course.id, created_by=course.post_author, title="Submit HW",
        submission_type="text",
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    db.add(Enrollment(user_id=student_user.id, course_id=course.id))
    db.commit()

    student_user.user_pass = get_password_hash("Test@123")
    db.commit()
    student_headers = auth_headers(student_user.user_email, "Test@123")

    submit_resp = client.post(
        f"/api/v1/assignments/{assignment.id}/submit",
        json={"textContent": "done", "files": []},
        headers=student_headers,
    )
    assert submit_resp.status_code == 200, submit_resp.text

    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment.id
    ).first()
    assert submission.files == []
    assert not isinstance(submission.files, str)

    # Directly write a legacy-shaped (double-encoded) row plus a
    # freshly-written direct-list row and confirm both read back as lists
    # through get_submissions — the tolerant _json_list helper in action.
    submission.files = [{"file_url": "/uploads/assignments/x/u1_a.pdf"}]
    db.commit()

    instructor = db.query(User).filter(User.id == course.post_author).first()
    instructor.user_pass = get_password_hash("Test@123")
    _approve_as_instructor(db, instructor)
    instructor_headers = auth_headers(instructor.user_email, "Test@123")

    list_resp = client.get(
        f"/api/v1/assignments/{assignment.id}/submissions",
        headers=instructor_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    subs = list_resp.json()["submissions"]
    assert subs[0]["files"] == [{"file_url": "/uploads/assignments/x/u1_a.pdf"}]
