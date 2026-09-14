"""Harness sanity: tables create, app answers, auth override works."""


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_db_fixture_creates_rows(db, student_user, course):
    assert student_user.id is not None
    assert course.id is not None
