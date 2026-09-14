"""
A4 — POST /users/apply-instructor and POST /admin/instructors/create both
construct InstructorProfile with columns that don't exist on the model
(bio, expertise, experience, education, certifications, social_links, status)
and 500 on every call. Fix maps to the real columns
(instructor_bio, is_approved, ...) from models/user.py.

Fix round 1 — A4 fallout: making apply-instructor succeed made
GET /users/instructor-profile reachable for the first time
(users.py:350 -> UserService.format_instructor_profile_response,
user_service.py:56-79), and that formatter reads the SAME nonexistent
columns (.bio/.expertise/.experience/.education/.certifications/
.social_links/.status) -> AttributeError 500. Twin bug:
UserService.promote_to_instructor (user_service.py:193) sets
instructor_profile.status = "approved", an unmapped attribute that
silently never persists.
"""
from app.models.user import InstructorProfile


def test_apply_instructor_creates_persisted_profile(client, db, make_user, auth_headers):
    student = make_user(role="student")
    headers = auth_headers(student.user_email, student._test_password)

    payload = {
        "bio": "x" * 120,
        "expertise": ["Python", "FastAPI"],
        "experience": "5 years",
        "education": [{"degree": "BSc", "institution": "MIT"}],
        "certifications": [{"name": "AWS", "issuer": "Amazon"}],
        "social_links": {"twitter": "https://twitter.com/x"},
    }

    resp = client.post("/api/v1/users/apply-instructor", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text

    profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == student.id
    ).first()
    assert profile is not None
    assert profile.instructor_bio == payload["bio"]
    assert profile.is_approved is False


def test_admin_create_instructor_creates_persisted_profile(client, db, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)

    payload = {
        "email": "newinstructor@example.com",
        "username": "newinstructor",
        "password": "Test@1234",
        "display_name": "New Instructor",
        "bio": "Experienced educator in mathematics.",
    }

    resp = client.post("/api/v1/admin/instructors/create", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == payload["email"]

    from app.models.user import User
    user = db.query(User).filter(User.user_email == payload["email"]).first()
    assert user is not None
    assert user.role == "instructor"

    profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == user.id
    ).first()
    assert profile is not None
    assert profile.instructor_bio == payload["bio"]
    assert profile.is_approved is True


# ---------------- Fix round 1: A4 fallout ----------------

def test_apply_then_get_instructor_profile_returns_mapped_shape(client, db, make_user, auth_headers):
    """After apply-instructor, GET /users/instructor-profile must return
    200 with the real-column data mapped onto the stable response shape
    (fields with no backing column come back as sensible empties, not a
    500 from reading a nonexistent attribute)."""
    student = make_user(role="student")
    headers = auth_headers(student.user_email, student._test_password)

    payload = {
        "bio": "x" * 120,
        "expertise": ["Python", "FastAPI"],
        "experience": "5 years",
        "education": [{"degree": "BSc", "institution": "MIT"}],
        "certifications": [{"name": "AWS", "issuer": "Amazon"}],
        "social_links": {"twitter": "https://twitter.com/x"},
    }
    apply_resp = client.post("/api/v1/users/apply-instructor", json=payload, headers=headers)
    assert apply_resp.status_code == 200, apply_resp.text

    # require_instructor gates the GET; apply-instructor doesn't flip the
    # role, so promote the user directly for this test's purposes.
    student.role = "instructor"
    db.commit()

    get_resp = client.get("/api/v1/users/instructor-profile", headers=headers)
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()

    assert body["bio"] == payload["bio"]
    assert body["status"] == "pending"  # is_approved defaults False
    # Dropped fields (no backing column) come back as stable empties, not
    # missing keys or a 500.
    assert body["expertise"] == []
    assert body["experience"] == ""
    assert body["education"] == []
    assert body["certifications"] == []
    assert body["social_links"] == {}
    assert body["total_students"] == 0
    assert body["total_courses"] == 0


def test_admin_create_instructor_then_get_profile_is_readable(client, db, make_user, as_user, auth_headers):
    """Admin create-instructor -> the resulting profile must be readable
    via GET /users/instructor-profile (approved status this time)."""
    admin = make_user(role="admin")
    as_user(admin)

    payload = {
        "email": "readable@example.com",
        "username": "readableinstructor",
        "password": "Test@1234",
        "display_name": "Readable Instructor",
        "bio": "Bio text for a readable instructor profile.",
    }
    create_resp = client.post("/api/v1/admin/instructors/create", json=payload)
    assert create_resp.status_code == 200, create_resp.text

    from app.models.user import User
    from app.core.security import get_password_hash
    user = db.query(User).filter(User.user_email == payload["email"]).first()
    # Overwrite the placeholder hash with a known password for auth_headers.
    user.user_pass = get_password_hash("Test@1234")
    db.commit()

    headers = auth_headers(payload["email"], "Test@1234")
    get_resp = client.get("/api/v1/users/instructor-profile", headers=headers)
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body["bio"] == payload["bio"]
    assert body["status"] == "approved"


def test_promote_to_instructor_persists_is_approved(db, make_user):
    """UserService.promote_to_instructor's twin bug: it used to set
    instructor_profile.status = 'approved' (no such column, silently
    dropped). Must set is_approved=True and have it actually persist."""
    from app.services.user_service import UserService

    student = make_user(role="student")
    profile = InstructorProfile(user_id=student.id, is_approved=False)
    db.add(profile)
    db.commit()

    result = UserService.promote_to_instructor(db, student.id)
    assert result is True

    db.refresh(student)
    assert student.role == "instructor"

    db.refresh(profile)
    assert profile.is_approved is True


def test_promote_to_instructor_without_existing_profile_still_promotes_role(db, make_user):
    """No InstructorProfile row yet (e.g. instructor created without one) —
    promote_to_instructor must not crash; it just can't flip is_approved
    on a row that doesn't exist."""
    from app.services.user_service import UserService

    student = make_user(role="student")
    result = UserService.promote_to_instructor(db, student.id)
    assert result is True

    db.refresh(student)
    assert student.role == "instructor"
