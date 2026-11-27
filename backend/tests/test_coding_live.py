"""Phase 4 coverage: pushing coding challenges into live class sessions."""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.coding_assessment import CodingJudgeJob
from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassStatus
from tests.test_coding_analytics import _enrol, _publish
from tests.test_coding_assessments import INTERNAL, _course


LIVE = "/api/v1/live"


def _live_class(db, course, instructor, *, status=LiveClassStatus.LIVE):
    now = datetime.now(timezone.utc)
    live_class = LiveClass(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Practice lab",
        scheduled_start=now - timedelta(minutes=10),
        scheduled_end=now + timedelta(hours=1),
        room_name=f"room-{uuid.uuid4().hex[:16]}",
        status=status,
    )
    db.add(live_class)
    db.commit()
    db.refresh(live_class)
    return live_class


def _join(db, live_class, student):
    db.add(LiveClassAttendance(class_id=live_class.id, user_id=student.id))
    db.commit()


def _push(client, as_user, instructor, live_class, challenge_id, **extra):
    as_user(instructor)
    return client.post(
        f"{LIVE}/classes/{live_class.id}/coding-challenges",
        json={"challenge_id": challenge_id, "graded": extra.pop("graded", False), **extra},
    )


def _judge_correct(client, *, correct=True):
    from app.main import app
    from app.routers.coding_judge_internal import require_code_runner

    app.dependency_overrides[require_code_runner] = lambda: None
    claim = client.post(f"{INTERNAL}/jobs/claim", json={"judge_version": "runner-1.0"})
    assert claim.status_code == 200, claim.text
    job = claim.json()["job"]
    outputs = ["5\n", "42\n"]
    results = [
        {
            "test_case_id": case["id"],
            "status": "completed",
            "actual_output": outputs[index] if correct else "0\n",
            "execution_ms": 12,
            "memory_kb": 9000,
        }
        for index, case in enumerate(job["test_cases"])
    ]
    complete = client.post(
        f"{INTERNAL}/jobs/{job['job_id']}/complete",
        json={"lease_token": job["lease_token"], "results": results},
    )
    assert complete.status_code == 200, complete.text


def _published_challenge(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    slug = _publish(client, course, instructor, as_user)
    from app.models.coding_assessment import CodingChallenge

    challenge = db.query(CodingChallenge).filter_by(slug=slug).one()
    return instructor, course, challenge


def _submit_live(client, as_user, student, live_id, key, source="print(5)\n"):
    as_user(student)
    return client.post(
        f"{LIVE}/coding-challenges/{live_id}/submissions",
        json={"language": "python", "source_code": source, "idempotency_key": key},
    )


def test_push_requires_assigned_instructor_and_course_match(client, db, make_user, as_user):
    instructor, course, challenge = _published_challenge(client, db, make_user, as_user)
    live_class = _live_class(db, course, instructor)

    other = make_user(role="instructor")
    response = _push(client, as_user, other, live_class, challenge.id)
    assert response.status_code == 403, response.text

    response = _push(client, as_user, instructor, live_class, challenge.id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "open"
    assert body["model_solution"] is None or body["model_solution"] == ""

    foreign_instructor, foreign_course = _course(db, make_user)
    foreign_live = _live_class(db, foreign_course, foreign_instructor)
    response = _push(client, as_user, foreign_instructor, foreign_live, challenge.id)
    assert response.status_code == 422, response.text


def test_only_one_open_challenge_and_drafts_are_rejected(client, db, make_user, as_user):
    instructor, course, challenge = _published_challenge(client, db, make_user, as_user)
    live_class = _live_class(db, course, instructor)
    assert _push(client, as_user, instructor, live_class, challenge.id).status_code == 201
    assert _push(client, as_user, instructor, live_class, challenge.id).status_code == 409

    from app.models.coding_assessment import CodingChallenge

    draft = CodingChallenge(
        course_id=course.id,
        title="Draft only",
        slug=f"draft-{uuid.uuid4().hex[:8]}",
        problem_statement="Not published yet.",
        allowed_languages=["python"],
        starter_code={},
        status="draft",
        version=1,
        created_by=instructor.id,
    )
    db.add(draft)
    db.commit()
    as_user(instructor)
    other_class = _live_class(db, course, instructor)
    response = _push(client, as_user, instructor, other_class, draft.id)
    assert response.status_code == 422, response.text


def test_learners_need_to_join_and_solution_stays_hidden_until_reveal(
    client, db, make_user, as_user
):
    instructor, course, challenge = _published_challenge(client, db, make_user, as_user)
    live_class = _live_class(db, course, instructor)
    pushed = _push(
        client,
        as_user,
        instructor,
        live_class,
        challenge.id,
        model_solution="a, b = map(int, input().split())\nprint(a + b)\n",
    ).json()
    live_id = pushed["id"]

    student = make_user(role="student")
    _enrol(db, course, student)
    as_user(student)
    assert client.get(f"{LIVE}/coding-challenges/{live_id}").status_code == 403
    _join(db, live_class, student)
    view = client.get(f"{LIVE}/coding-challenges/{live_id}")
    assert view.status_code == 200, view.text
    assert view.json()["live"]["model_solution"] is None

    as_user(instructor)
    assert client.post(f"{LIVE}/coding-challenges/{live_id}/reveal").status_code == 409
    closed = client.post(f"{LIVE}/coding-challenges/{live_id}/close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    revealed = client.post(f"{LIVE}/coding-challenges/{live_id}/reveal")
    assert revealed.status_code == 200, revealed.text

    as_user(student)
    view = client.get(f"{LIVE}/coding-challenges/{live_id}").json()
    assert view["live"]["solution_revealed"] is True
    assert "print(a + b)" in view["live"]["model_solution"]


def test_submissions_link_to_the_session_and_board_respects_roles(
    client, db, make_user, as_user
):
    instructor, course, challenge = _published_challenge(client, db, make_user, as_user)
    live_class = _live_class(db, course, instructor)
    live_id = _push(client, as_user, instructor, live_class, challenge.id, graded=True).json()["id"]

    student = make_user(role="student")
    rival = make_user(role="student")
    for learner in (student, rival):
        _enrol(db, course, learner)
        _join(db, live_class, learner)

    not_joined = make_user(role="student")
    _enrol(db, course, not_joined)
    response = _submit_live(client, as_user, not_joined, live_id, "live-key-0001")
    assert response.status_code == 403, response.text

    response = _submit_live(client, as_user, student, live_id, "live-key-0002")
    assert response.status_code == 202, response.text
    assert response.json()["counts_for_grade"] is True

    _judge_correct(client)

    as_user(student)
    board = client.get(f"{LIVE}/coding-challenges/{live_id}/board").json()
    assert board["summary"]["learners_submitted"] == 1
    assert board["my_row"]["passed"] is True
    assert "rows" not in board

    as_user(instructor)
    board = client.get(f"{LIVE}/coding-challenges/{live_id}/board").json()
    assert [row["user_id"] for row in board["rows"]] == [student.id]
    assert board["rows"][0]["rank"] == 1

    as_user(rival)
    board = client.get(f"{LIVE}/coding-challenges/{live_id}/board").json()
    assert board["my_row"] is None
    assert board["summary"]["learners_submitted"] == 1


def test_closed_challenge_rejects_submissions_and_instructors_cannot_submit(
    client, db, make_user, as_user
):
    instructor, course, challenge = _published_challenge(client, db, make_user, as_user)
    live_class = _live_class(db, course, instructor)
    live_id = _push(client, as_user, instructor, live_class, challenge.id).json()["id"]

    student = make_user(role="student")
    _enrol(db, course, student)
    _join(db, live_class, student)

    as_user(instructor)
    response = client.post(
        f"{LIVE}/coding-challenges/{live_id}/submissions",
        json={"language": "python", "source_code": "print(5)\n", "idempotency_key": "staff-key-0001"},
    )
    assert response.status_code == 403

    client.post(f"{LIVE}/coding-challenges/{live_id}/close")
    response = _submit_live(client, as_user, student, live_id, "late-key-0001")
    assert response.status_code == 409, response.text
    assert db.query(CodingJudgeJob).count() == 0

    # A new challenge can be pushed once the previous one is closed.
    as_user(instructor)
    assert _push(client, as_user, instructor, live_class, challenge.id).status_code == 201
