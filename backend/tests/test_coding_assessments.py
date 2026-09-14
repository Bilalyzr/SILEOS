"""Utporul challenge authoring, learner privacy, and judge lease coverage."""

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.coding_assessment import CodingJudgeJob, CodingSubmission


ROOT = "/api/v1/utporul/coding"
INTERNAL = "/api/v1/internal/coding"


def _course(db, make_user):
    instructor = make_user(role="instructor")
    course = Course(
        post_author=instructor.id,
        post_title="Production Python",
        post_status="published",
        course_type="utporul",
        course_price_type="free",
        course_price=0,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return instructor, course


def _author(client, instructor):
    from app.main import app
    from app.services.auth_service import AuthService

    app.dependency_overrides[AuthService.require_instructor] = lambda: instructor


def _definition(hidden=True):
    cases = [
        {
            "visibility": "sample",
            "input_text": "2 3\n",
            "expected_output": "5\n",
            "comparison": "trimmed",
            "weight": 1,
        }
    ]
    if hidden:
        cases.append(
            {
                "visibility": "hidden",
                "input_text": "40 2\n",
                "expected_output": "42\n",
                "comparison": "tokens",
                "weight": 1,
            }
        )
    return {
        "title": "Add two integers",
        "problem_statement": "Read two integers and print their exact sum.",
        "input_format": "Two space-separated integers.",
        "output_format": "One integer.",
        "constraints_text": "-10^9 <= n <= 10^9",
        "allowed_languages": ["python", "javascript"],
        "starter_code": {"python": "a, b = map(int, input().split())\n"},
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "max_attempts": 3,
        "test_cases": cases,
    }


def test_publish_requires_hidden_case(client, db, make_user):
    instructor, course = _course(db, make_user)
    _author(client, instructor)
    created = client.post(
        f"{ROOT}/courses/{course.id}/challenges", json=_definition(hidden=False)
    )
    assert created.status_code == 201, created.text
    response = client.post(
        f"{ROOT}/challenges/{created.json()['id']}/action",
        json={
            "action": "publish",
            "version": created.json()["version"],
            "reason": "Reviewed by instructor",
        },
    )
    assert response.status_code == 422


def test_end_to_end_submission_hides_answers_and_uses_judge_lease(
    client, db, make_user, as_user
):
    instructor, course = _course(db, make_user)
    _author(client, instructor)
    created = client.post(
        f"{ROOT}/courses/{course.id}/challenges", json=_definition()
    )
    assert created.status_code == 201, created.text
    challenge = created.json()
    published = client.post(
        f"{ROOT}/challenges/{challenge['id']}/action",
        json={
            "action": "publish",
            "version": challenge["version"],
            "reason": "All hidden tests reviewed",
        },
    )
    assert published.status_code == 200, published.text
    slug = published.json()["slug"]

    student = make_user(role="student")
    as_user(student)
    assert client.get(f"{ROOT}/challenges/{slug}").status_code == 403
    db.add(
        Enrollment(
            course_id=course.id,
            user_id=student.id,
            enrollment_status="enrolled",
        )
    )
    db.commit()
    learner = client.get(f"{ROOT}/challenges/{slug}")
    assert learner.status_code == 200, learner.text
    assert len(learner.json()["sample_cases"]) == 1
    assert learner.json()["sample_cases"] == [
        {
            "ordinal": 1,
            "input_text": "2 3",
            "expected_output": "5",
            "comparison": "trimmed",
        }
    ]

    payload = {
        "language": "python",
        "source_code": "a, b = map(int, input().split())\nprint(a + b)\n",
        "idempotency_key": "editor-run-0001",
    }
    queued = client.post(f"{ROOT}/challenges/{slug}/submissions", json=payload)
    assert queued.status_code == 202, queued.text
    submission_id = queued.json()["id"]
    duplicate = client.post(f"{ROOT}/challenges/{slug}/submissions", json=payload)
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == submission_id
    assert db.query(CodingSubmission).count() == 1
    assert db.query(CodingJudgeJob).count() == 1

    from app.main import app
    from app.routers.coding_judge_internal import require_code_runner

    app.dependency_overrides[require_code_runner] = lambda: None
    claim = client.post(
        f"{INTERNAL}/jobs/claim", json={"judge_version": "runner-1.0"}
    )
    assert claim.status_code == 200, claim.text
    job = claim.json()["job"]
    assert job["limits"]["network"] == "disabled"
    assert all("expected_output" not in case for case in job["test_cases"])

    case_ids = [case["id"] for case in job["test_cases"]]
    invalid = client.post(
        f"{INTERNAL}/jobs/{job['job_id']}/complete",
        json={
            "lease_token": "invalid-lease-token-value",
            "results": [
                {
                    "test_case_id": case_id,
                    "status": "completed",
                    "actual_output": "5\n",
                }
                for case_id in case_ids
            ],
        },
    )
    assert invalid.status_code == 409

    complete = client.post(
        f"{INTERNAL}/jobs/{job['job_id']}/complete",
        json={
            "lease_token": job["lease_token"],
            "results": [
                {
                    "test_case_id": case_ids[0],
                    "status": "completed",
                    "actual_output": "5\n",
                    "execution_ms": 12,
                    "memory_kb": 9000,
                },
                {
                    "test_case_id": case_ids[1],
                    "status": "completed",
                    "actual_output": "41\n",
                    "execution_ms": 13,
                    "memory_kb": 9100,
                },
            ],
        },
    )
    assert complete.status_code == 200, complete.text
    assert complete.json() == {
        "submission_id": submission_id,
        "status": "failed",
        "score": 50.0,
    }

    result = client.get(f"{ROOT}/submissions/{submission_id}").json()
    assert result["status"] == "failed"
    hidden = next(row for row in result["results"] if row["visibility"] == "hidden")
    assert hidden["test_case_id"] is None
    assert hidden["actual_output"] == ""
    assert hidden["stderr"] == ""


def test_submission_limits_language_source_and_attempts(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    _author(client, instructor)
    definition = _definition()
    definition["max_attempts"] = 1
    created = client.post(f"{ROOT}/courses/{course.id}/challenges", json=definition).json()
    published = client.post(
        f"{ROOT}/challenges/{created['id']}/action",
        json={"action": "publish", "version": 1, "reason": "Review complete"},
    ).json()
    student = make_user()
    db.add(Enrollment(course_id=course.id, user_id=student.id, enrollment_status="enrolled"))
    db.commit()
    as_user(student)
    discovered = client.get(f"{ROOT}/learner/challenges")
    assert discovered.status_code == 200, discovered.text
    assert discovered.json()[0]["slug"] == published["slug"]
    assert discovered.json()[0]["attempts_used"] == 0
    rejected = client.post(
        f"{ROOT}/challenges/{published['slug']}/submissions",
        json={"language": "java", "source_code": "class Main {}", "idempotency_key": "attempt-java-1"},
    )
    assert rejected.status_code == 422
    accepted = client.post(
        f"{ROOT}/challenges/{published['slug']}/submissions",
        json={"language": "python", "source_code": "print(5)", "idempotency_key": "attempt-python-1"},
    )
    assert accepted.status_code == 202
    limited = client.post(
        f"{ROOT}/challenges/{published['slug']}/submissions",
        json={"language": "python", "source_code": "print(5)", "idempotency_key": "attempt-python-2"},
    )
    assert limited.status_code == 409


def test_rejects_non_utporul_course_and_requeues_transient_judge_failure(
    client, db, make_user
):
    instructor, course = _course(db, make_user)
    _author(client, instructor)
    course.course_type = "meiporul"
    db.commit()
    rejected = client.post(
        f"{ROOT}/courses/{course.id}/challenges", json=_definition()
    )
    assert rejected.status_code == 422

    course.course_type = "utporul"
    db.commit()
    challenge = client.post(
        f"{ROOT}/courses/{course.id}/challenges", json=_definition()
    ).json()
    published = client.post(
        f"{ROOT}/challenges/{challenge['id']}/action",
        json={"action": "publish", "version": 1, "reason": "Review complete"},
    ).json()
    student = make_user()
    db.add(Enrollment(course_id=course.id, user_id=student.id, enrollment_status="enrolled"))
    db.commit()

    from app.main import app
    from app.routers.coding_judge_internal import require_code_runner
    from app.services.auth_service import AuthService

    app.dependency_overrides[AuthService.get_current_active_user] = lambda: student
    queued = client.post(
        f"{ROOT}/challenges/{published['slug']}/submissions",
        json={
            "language": "python",
            "source_code": "print(5)",
            "idempotency_key": "retryable-run-1",
        },
    ).json()
    app.dependency_overrides[require_code_runner] = lambda: None
    claim = client.post(
        f"{INTERNAL}/jobs/claim", json={"judge_version": "runner-1.0"}
    ).json()["job"]
    failed = client.post(
        f"{INTERNAL}/jobs/{claim['job_id']}/fail",
        json={
            "lease_token": claim["lease_token"],
            "error": "Judge node is temporarily unavailable",
            "retryable": True,
        },
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "queued"
    submission = db.get(CodingSubmission, queued["id"])
    db.refresh(submission)
    assert submission.status == "queued"
