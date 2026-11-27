"""Phase 3 coverage: performance scoring, instructor metrics, CSV export, learner progress."""

from datetime import datetime, timedelta, timezone

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.services.coding_analytics_service import ranking_key
from tests.test_coding_assessments import INTERNAL, ROOT, _author, _course, _definition


CORRECT_OUTPUTS = ["5\n", "42\n"]
WRONG = "0\n"


def _publish(client, course, instructor, as_user):
    as_user(instructor)
    _author(client, instructor)
    created = client.post(f"{ROOT}/courses/{course.id}/challenges", json=_definition())
    assert created.status_code == 201, created.text
    challenge = created.json()
    published = client.post(
        f"{ROOT}/challenges/{challenge['id']}/action",
        json={"action": "publish", "version": challenge["version"], "reason": "Reviewed"},
    )
    assert published.status_code == 200, published.text
    return published.json()["slug"]


def _enrol(db, course, student):
    db.add(Enrollment(course_id=course.id, user_id=student.id, enrollment_status="enrolled"))
    db.commit()


def _submit_and_judge(client, as_user, student, slug, key, *, correct, execution_ms, memory_kb):
    as_user(student)
    queued = client.post(
        f"{ROOT}/challenges/{slug}/submissions",
        json={
            "language": "python",
            "source_code": "print(1)\n",
            "idempotency_key": key,
        },
    )
    assert queued.status_code == 202, queued.text
    from app.main import app
    from app.routers.coding_judge_internal import require_code_runner

    app.dependency_overrides[require_code_runner] = lambda: None
    claim = client.post(f"{INTERNAL}/jobs/claim", json={"judge_version": "runner-1.0"})
    assert claim.status_code == 200, claim.text
    job = claim.json()["job"]
    results = []
    # The _definition() fixture has one sample case (answer 5) and one hidden case (answer 42).
    for index, case in enumerate(job["test_cases"]):
        output = CORRECT_OUTPUTS[index] if correct else WRONG
        results.append(
            {
                "test_case_id": case["id"],
                "status": "completed",
                "actual_output": output,
                "execution_ms": execution_ms,
                "memory_kb": memory_kb,
            }
        )
    complete = client.post(
        f"{INTERNAL}/jobs/{job['job_id']}/complete",
        json={"lease_token": job["lease_token"], "results": results},
    )
    assert complete.status_code == 200, complete.text
    return queued.json()["id"]


def _three_learners(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    slug = _publish(client, course, instructor, as_user)
    fast = make_user(role="student")
    slow = make_user(role="student")
    wrong = make_user(role="student")
    for student in (fast, slow, wrong):
        _enrol(db, course, student)
    fast.display_name = "Fast Learner"
    slow.display_name = "=HYPERLINK(\"x\")"
    wrong.display_name = "Wrong Learner"
    db.commit()
    _submit_and_judge(client, as_user, fast, slug, "analytics-fast-0001", correct=True, execution_ms=10, memory_kb=9000)
    _submit_and_judge(client, as_user, slow, slug, "analytics-slow-0001", correct=True, execution_ms=50, memory_kb=9000)
    _submit_and_judge(client, as_user, wrong, slug, "analytics-wrong-0001", correct=False, execution_ms=5, memory_kb=8000)
    return instructor, course, slug, fast, slow, wrong


def test_ranking_key_prefers_score_then_speed_then_memory_then_time():
    now = datetime(2026, 11, 27, tzinfo=timezone.utc)
    later = now + timedelta(minutes=1)
    assert ranking_key(100, 900, 9000, later) < ranking_key(50, 1, 1, now)
    assert ranking_key(100, 10, 9000, later) < ranking_key(100, 50, 1, now)
    assert ranking_key(100, 10, 1000, later) < ranking_key(100, 10, 9000, now)
    assert ranking_key(100, 10, 1000, now) < ranking_key(100, 10, 1000, later)


def test_instructor_metrics_pass_rate_ranking_and_failing_cases(client, db, make_user, as_user):
    instructor, course, slug, fast, slow, wrong = _three_learners(client, db, make_user, as_user)
    as_user(instructor)
    response = client.get(f"{ROOT}/courses/{course.id}/metrics")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["challenges"]) == 1
    challenge = body["challenges"][0]
    assert challenge["slug"] == slug
    assert challenge["learners_attempted"] == 3
    assert challenge["learners_passed"] == 2
    assert challenge["pass_rate"] == 0.667
    assert challenge["total_submissions"] == 3
    assert challenge["median_minutes_to_first_pass"] is not None

    ranks = [(row["user_id"], row["rank"], row["passed"]) for row in challenge["leaderboard"]]
    assert ranks[0] == (fast.id, 1, True)
    assert ranks[1] == (slow.id, 2, True)
    assert ranks[2] == (wrong.id, 3, False)
    assert challenge["leaderboard"][0]["total_ms"] == 20
    assert challenge["leaderboard"][0]["peak_memory_kb"] == 9000

    failing = challenge["failing_cases"]
    assert [case["ordinal"] for case in failing] == [1, 2]
    assert all(case["failed"] == 1 for case in failing)
    assert failing[0]["failure_breakdown"] == {"wrong_answer": 1}
    # Hidden inputs and expected outputs never appear in metrics.
    assert "input_text" not in str(body)
    assert "expected_output" not in str(body)


def test_metrics_csv_is_sanitised_and_ordered(client, db, make_user, as_user):
    instructor, course, slug, fast, slow, wrong = _three_learners(client, db, make_user, as_user)
    as_user(instructor)
    response = client.get(f"{ROOT}/courses/{course.id}/metrics.csv")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("challenge_slug,challenge_title,rank,learner_id,learner_name")
    assert len(lines) == 4
    assert "'=HYPERLINK" in response.text
    assert ",Fast Learner," in lines[1]


def test_metrics_are_forbidden_to_students(client, db, make_user, as_user):
    instructor, course, *_ = _three_learners(client, db, make_user, as_user)
    outsider = make_user(role="student")
    as_user(outsider)
    assert client.get(f"{ROOT}/courses/{course.id}/metrics").status_code == 403
    assert client.get(f"{ROOT}/courses/{course.id}/metrics.csv").status_code == 403


def test_learner_progress_shows_own_scores_only(client, db, make_user, as_user):
    instructor, course, slug, fast, slow, wrong = _three_learners(client, db, make_user, as_user)
    as_user(wrong)
    response = client.get(f"{ROOT}/learner/progress")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == {
        "challenges_total": 1,
        "challenges_attempted": 1,
        "challenges_passed": 0,
    }
    row = body["challenges"][0]
    assert row["slug"] == slug
    assert row["attempts"] == 1
    assert row["passed"] is False
    assert row["first_passed_at"] is None
    assert len(body["history"]) == 1
    assert body["history"][0]["status"] == "failed"

    as_user(fast)
    body = client.get(f"{ROOT}/learner/progress").json()
    assert body["summary"]["challenges_passed"] == 1
    assert body["challenges"][0]["best_score"] == 100.0
    assert body["challenges"][0]["best_total_ms"] == 20
    assert all(item["status"] in {"passed", "failed", "error"} for item in body["history"])
