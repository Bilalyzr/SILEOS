"""Phase 6: per-learner pacing, judge queue backpressure, queue monitoring, and a burst test."""

import time

from app.models.coding_assessment import CodingJudgeJob
from app.services import coding_assessment_service as coding_service
from app.services.coding_ops import judge_health
from tests.test_coding_analytics import _enrol, _publish, _submit_and_judge
from tests.test_coding_assessments import _course


ROOT = "/api/v1/utporul/coding"


def _published(client, db, make_user, as_user, max_attempts=20):
    from app.models.coding_assessment import CodingChallenge

    instructor, course = _course(db, make_user)
    slug = _publish(client, course, instructor, as_user)
    # The shared fixture allows 3 attempts; these tests need room to submit more.
    challenge = db.query(CodingChallenge).filter_by(slug=slug).one()
    challenge.max_attempts = max_attempts
    db.commit()
    return course, slug


def _submit(client, as_user, student, slug, key):
    as_user(student)
    return client.post(
        f"{ROOT}/challenges/{slug}/submissions",
        json={"language": "python", "source_code": "print(5)\n", "idempotency_key": key},
    )


def test_learner_is_paced_to_six_submissions_a_minute(client, db, make_user, as_user):
    course, slug = _published(client, db, make_user, as_user)
    student = make_user(role="student")
    _enrol(db, course, student)
    for index in range(coding_service.SUBMITS_PER_MINUTE):
        response = _submit(client, as_user, student, slug, f"pace-key-{index:04d}")
        assert response.status_code == 202, response.text
    blocked = _submit(client, as_user, student, slug, "pace-key-9999")
    assert blocked.status_code == 429, blocked.text
    assert blocked.headers["Retry-After"] == str(coding_service.RETRY_AFTER_SECONDS)

    # Retrying an existing key is not a new submission, so it still succeeds.
    replay = _submit(client, as_user, student, slug, "pace-key-0000")
    assert replay.status_code == 202, replay.text


def test_full_judge_queue_returns_503_with_retry_hint(client, db, make_user, as_user, monkeypatch):
    course, slug = _published(client, db, make_user, as_user)
    monkeypatch.setattr(coding_service, "QUEUE_CAPACITY", 2)
    first = make_user(role="student")
    second = make_user(role="student")
    third = make_user(role="student")
    for learner in (first, second, third):
        _enrol(db, course, learner)
    assert _submit(client, as_user, first, slug, "queue-key-0001").status_code == 202
    assert _submit(client, as_user, second, slug, "queue-key-0002").status_code == 202
    full = _submit(client, as_user, third, slug, "queue-key-0003")
    assert full.status_code == 503, full.text
    assert full.headers["Retry-After"] == str(coding_service.RETRY_AFTER_SECONDS)
    assert db.query(CodingJudgeJob).count() == 2


def test_one_hundred_learners_submitting_together(client, db, make_user, as_user):
    course, slug = _published(client, db, make_user, as_user)
    learners = []
    for _ in range(100):
        learner = make_user(role="student")
        _enrol(db, course, learner)
        learners.append(learner)

    started = time.perf_counter()
    statuses = [
        _submit(client, as_user, learner, slug, f"burst-key-{index:04d}").status_code
        for index, learner in enumerate(learners)
    ]
    elapsed = time.perf_counter() - started

    assert statuses.count(202) == 100, statuses
    assert judge_health(db)["queue_queued"] == 100
    # Generous bound for the in-process test client on a shared CI runner.
    assert elapsed < 120, f"100 submissions took {elapsed:.1f}s"


def test_judge_health_reports_depth_latency_and_errors(client, db, make_user, as_user):
    empty = judge_health(db)
    assert empty["queue_queued"] == 0
    assert empty["completed_last_hour"] == 0
    assert empty["error_ratio_last_hour"] == 0.0

    course, slug = _published(client, db, make_user, as_user)
    student = make_user(role="student")
    _enrol(db, course, student)
    _submit_and_judge(client, as_user, student, slug, "health-key-0001", correct=True, execution_ms=10, memory_kb=9000)

    health = judge_health(db)
    assert health["completed_last_hour"] == 1
    assert health["queue_queued"] == 0
    assert health["error_ratio_last_hour"] == 0.0
    assert health["judge_latency_p95_seconds"] >= 0.0
