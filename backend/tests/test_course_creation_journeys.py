"""Rank-9 E2E: course-creation module journeys against the SILEOS LMS dev API.

Runs the Proctor journey pattern (multi-step HTTP, statistical repeats for the
non-deterministic bits) against the live dev deployment. The suite exercises
the CREATE + UPDATE contract of /api/v1/courses — auth gates, validation,
slug handling, cross-tenant edit permissions — and cleans up after itself.

Env:
  SILEOS_BASE_URL   (default https://dev.sashainfinity.com)
  SILEOS_INSTRUCTOR_EMAIL / SILEOS_INSTRUCTOR_PASSWORD
  SILEOS_OTHER_INSTRUCTOR_EMAIL / _PASSWORD   (second instructor, for the
        cross-instructor 403 journey; falls back to the first)
  SILEOS_STUDENT_EMAIL / SILEOS_STUDENT_PASSWORD
"""

from __future__ import annotations

import os
import uuid

import pytest
import requests

pytestmark = [pytest.mark.l9, pytest.mark.nightly]

BASE = os.environ.get("SILEOS_BASE_URL", "https://dev.sashainfinity.com").rstrip("/")
TIMEOUT = 30
REPEATS = 5  # statistical gate: pass rate must be 5/5 on deterministic checks


def _login(email: str, password: str) -> dict:
    r = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def instructor_auth() -> dict:
    return _login(
        os.environ.get("SILEOS_INSTRUCTOR_EMAIL", "mock.priya@dev.sashainfinity.com"),
        os.environ.get("SILEOS_INSTRUCTOR_PASSWORD", "Mock#1234"),
    )


@pytest.fixture(scope="module")
def student_auth() -> dict:
    return _login(
        os.environ.get("SILEOS_STUDENT_EMAIL", "mock.aarav@dev.sashainfinity.com"),
        os.environ.get("SILEOS_STUDENT_PASSWORD", "Mock#1234"),
    )


@pytest.fixture(scope="module")
def other_instructor_auth(instructor_auth: dict) -> dict:
    email = os.environ.get("SILEOS_OTHER_INSTRUCTOR_EMAIL")
    if not email:
        return instructor_auth  # same-account mode: ownership journeys skip
    return _login(email, os.environ.get("SILEOS_OTHER_INSTRUCTOR_PASSWORD", "Mock#1234"))


def _payload(**over) -> dict:
    uid = uuid.uuid4().hex[:8]
    base = {
        "title": f"Proctor Journey {uid}",
        "description": "Temporary course created by the Proctor course-creation suite.",
        "category": "testing",
        "price": 999,
        "level": "beginner",
    }
    base.update(over)
    return base


@pytest.fixture()
def created_course(instructor_auth: dict):
    """Create a draft course for update journeys; delete it afterwards."""
    r = requests.post(f"{BASE}/api/v1/courses/", json=_payload(), headers=instructor_auth, timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    course = r.json()
    yield course
    requests.delete(f"{BASE}/api/v1/courses/{course['id']}", headers=instructor_auth, timeout=TIMEOUT)


# ------------------------------------------------------------------ auth gates
class TestAuthGates:
    def test_anonymous_create_rejected(self):
        r = requests.post(f"{BASE}/api/v1/courses/", json=_payload(), timeout=TIMEOUT)
        assert r.status_code == 401, f"anonymous create returned {r.status_code}"

    def test_student_create_forbidden(self, student_auth):
        r = requests.post(f"{BASE}/api/v1/courses/", json=_payload(), headers=student_auth, timeout=TIMEOUT)
        assert r.status_code == 403, f"student create returned {r.status_code}"


# ---------------------------------------------------------------- happy path
class TestCreateHappyPath:
    def test_instructor_create_defaults_to_draft(self, instructor_auth):
        r = requests.post(f"{BASE}/api/v1/courses/", json=_payload(), headers=instructor_auth, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body["status"] == "draft"
        assert body["slug"], "slug must be generated"
        requests.delete(f"{BASE}/api/v1/courses/{body['id']}", headers=instructor_auth, timeout=TIMEOUT)

    def test_create_deterministic_repeatability(self, instructor_auth):
        """Proctor statistical gate: the same valid payload family must land
        5/5 — one flaky 500 fails the journey."""
        passed = 0
        for _ in range(REPEATS):
            r = requests.post(f"{BASE}/api/v1/courses/", json=_payload(), headers=instructor_auth, timeout=TIMEOUT)
            if r.status_code in (200, 201):
                requests.delete(f"{BASE}/api/v1/courses/{r.json()['id']}", headers=instructor_auth, timeout=TIMEOUT)
                passed += 1
        assert passed == REPEATS, f"deterministic create passed {passed}/{REPEATS}"


# ------------------------------------------------------------------ validation
class TestValidation:
    def test_negative_price_rejected(self, instructor_auth):
        r = requests.post(f"{BASE}/api/v1/courses/", json=_payload(price=-5), headers=instructor_auth, timeout=TIMEOUT)
        assert r.status_code == 422, f"negative price create returned {r.status_code}"

    def test_negative_sale_price_rejected(self, instructor_auth):
        r = requests.post(
            f"{BASE}/api/v1/courses/", json=_payload(sale_price=-5), headers=instructor_auth, timeout=TIMEOUT
        )
        assert r.status_code == 422, f"negative sale_price create returned {r.status_code}: {r.text[:200]}"
        if r.status_code in (200, 201):
            requests.delete(f"{BASE}/api/v1/courses/{r.json()['id']}", headers=instructor_auth, timeout=TIMEOUT)

    def test_bad_level_rejected_on_create(self, instructor_auth):
        r = requests.post(f"{BASE}/api/v1/courses/", json=_payload(level="guru"), headers=instructor_auth, timeout=TIMEOUT)
        assert r.status_code == 422, f"bad level create returned {r.status_code}"

    def test_bad_slug_rejected(self, instructor_auth):
        r = requests.post(
            f"{BASE}/api/v1/courses/", json=_payload(slug="Not A Valid Slug!!"), headers=instructor_auth, timeout=TIMEOUT
        )
        assert r.status_code == 422, f"bad slug create returned {r.status_code}"

    def test_unknown_certificate_rejected(self, instructor_auth):
        r = requests.post(
            f"{BASE}/api/v1/courses/", json=_payload(certificate_id=99999999), headers=instructor_auth, timeout=TIMEOUT
        )
        assert r.status_code in (400, 403, 404, 422), f"unknown certificate returned {r.status_code}"


# --------------------------------------------------------------------- updates
class TestUpdateContract:
    def test_update_own_course_ok(self, instructor_auth, created_course):
        r = requests.put(
            f"{BASE}/api/v1/courses/{created_course['id']}",
            json={"price": 1234},
            headers=instructor_auth,
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text

    def test_update_negative_price_rejected(self, instructor_auth, created_course):
        r = requests.put(
            f"{BASE}/api/v1/courses/{created_course['id']}",
            json={"price": -99},
            headers=instructor_auth,
            timeout=TIMEOUT,
        )
        assert r.status_code == 422, f"negative price UPDATE returned {r.status_code} (stored={r.status_code==200})"

    def test_update_negative_sale_price_rejected(self, instructor_auth, created_course):
        r = requests.put(
            f"{BASE}/api/v1/courses/{created_course['id']}",
            json={"sale_price": -99},
            headers=instructor_auth,
            timeout=TIMEOUT,
        )
        assert r.status_code == 422, f"negative sale_price UPDATE returned {r.status_code}"

    def test_update_invalid_level_rejected(self, instructor_auth, created_course):
        r = requests.put(
            f"{BASE}/api/v1/courses/{created_course['id']}",
            json={"level": "wizard"},
            headers=instructor_auth,
            timeout=TIMEOUT,
        )
        assert r.status_code == 422, f"invalid level UPDATE returned {r.status_code}"

    def test_cross_instructor_update_forbidden(self, instructor_auth, other_instructor_auth, created_course):
        if other_instructor_auth is instructor_auth:
            pytest.skip("no second instructor configured")
        r = requests.put(
            f"{BASE}/api/v1/courses/{created_course['id']}",
            json={"price": 1},
            headers=other_instructor_auth,
            timeout=TIMEOUT,
        )
        assert r.status_code == 403, f"cross-instructor update returned {r.status_code}"


# ------------------------------------------------------------------- teardown
class TestTeardownContract:
    def test_instructor_can_delete_own_draft(self, instructor_auth):
        r = requests.post(f"{BASE}/api/v1/courses/", json=_payload(), headers=instructor_auth, timeout=TIMEOUT)
        assert r.status_code in (200, 201)
        cid = r.json()["id"]
        d = requests.delete(f"{BASE}/api/v1/courses/{cid}", headers=instructor_auth, timeout=TIMEOUT)
        assert d.status_code in (200, 204), f"delete returned {d.status_code}"
