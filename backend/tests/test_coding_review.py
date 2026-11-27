"""Phase 5 (part A): line-anchored review comments, review requests and the queue."""

from tests.test_coding_analytics import _enrol, _publish, _submit_and_judge
from tests.test_coding_assessments import _course


ROOT = "/api/v1/utporul/coding"


def _judged_submission(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    slug = _publish(client, course, instructor, as_user)
    student = make_user(role="student")
    _enrol(db, course, student)
    submission_id = _submit_and_judge(
        client,
        as_user,
        student,
        slug,
        "review-key-0001",
        correct=True,
        execution_ms=10,
        memory_kb=9000,
    )
    return instructor, course, student, submission_id


def test_owner_and_staff_comment_and_outsiders_cannot_see(client, db, make_user, as_user):
    instructor, course, student, sub_id = _judged_submission(client, db, make_user, as_user)

    as_user(student)
    own = client.post(f"{ROOT}/submissions/{sub_id}/comments", json={"line": 1, "body": "Is this input safe?"})
    assert own.status_code == 201, own.text
    assert own.json()["author_is_staff"] is False

    too_far = client.post(f"{ROOT}/submissions/{sub_id}/comments", json={"line": 5, "body": "Nope"})
    assert too_far.status_code == 422

    as_user(instructor)
    reply = client.post(f"{ROOT}/submissions/{sub_id}/comments", json={"line": 1, "body": "Good question."})
    assert reply.status_code == 201, reply.text
    assert reply.json()["author_is_staff"] is True

    listed = client.get(f"{ROOT}/submissions/{sub_id}/comments").json()
    assert [c["body"] for c in listed] == ["Is this input safe?", "Good question."]

    outsider = make_user(role="student")
    _enrol(db, course, outsider)
    as_user(outsider)
    assert client.get(f"{ROOT}/submissions/{sub_id}/comments").status_code == 404
    assert (
        client.post(f"{ROOT}/submissions/{sub_id}/comments", json={"line": 1, "body": "Peeking"}).status_code
        == 404
    )


def test_review_request_flow_and_queue(client, db, make_user, as_user):
    instructor, course, student, sub_id = _judged_submission(client, db, make_user, as_user)

    as_user(instructor)
    assert client.post(f"{ROOT}/submissions/{sub_id}/review-request").status_code == 403

    as_user(student)
    first = client.post(f"{ROOT}/submissions/{sub_id}/review-request")
    assert first.status_code == 201, first.text
    again = client.post(f"{ROOT}/submissions/{sub_id}/review-request")
    assert again.status_code == 201
    client.post(f"{ROOT}/submissions/{sub_id}/comments", json={"line": 1, "body": "Please check edge cases."})

    outsider = make_user(role="student")
    _enrol(db, course, outsider)
    as_user(outsider)
    assert client.get(f"{ROOT}/courses/{course.id}/review-queue").status_code == 403

    as_user(instructor)
    queue = client.get(f"{ROOT}/courses/{course.id}/review-queue")
    assert queue.status_code == 200, queue.text
    body = queue.json()
    assert body["count"] == 1
    item = body["items"][0]
    assert item["submission_id"] == sub_id
    assert item["open_comments"] == 1

    comment_id = client.get(f"{ROOT}/submissions/{sub_id}/comments").json()[0]["id"]
    as_user(student)
    assert client.post(f"{ROOT}/comments/{comment_id}/resolve").status_code == 403

    as_user(instructor)
    resolved = client.post(f"{ROOT}/comments/{comment_id}/resolve")
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert client.get(f"{ROOT}/courses/{course.id}/review-queue").json()["items"][0]["open_comments"] == 0

    done = client.post(f"{ROOT}/submissions/{sub_id}/review-done")
    assert done.status_code == 200, done.text
    assert client.get(f"{ROOT}/courses/{course.id}/review-queue").json()["count"] == 0


def test_review_done_needs_a_request_and_editor(client, db, make_user, as_user):
    instructor, course, student, sub_id = _judged_submission(client, db, make_user, as_user)
    as_user(instructor)
    assert client.post(f"{ROOT}/submissions/{sub_id}/review-done").status_code == 404

    as_user(student)
    client.post(f"{ROOT}/submissions/{sub_id}/review-request")
    assert client.post(f"{ROOT}/submissions/{sub_id}/review-done").status_code == 403
