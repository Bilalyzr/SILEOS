"""Practice blocks in lessons and learner drafts (coding platform Phase 2)."""

from app.main import app
from app.models.coding_assessment import CodingChallenge
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.services.auth_service import AuthService


ROOT = "/api/v1/utporul/coding"


def _course(db, make_user):
    instructor = make_user(role="instructor")
    course = Course(
        post_author=instructor.id,
        post_title="Lesson blocks course",
        post_status="published",
        course_type="utporul",
        course_price_type="free",
        course_price=0,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    lesson = Lesson(
        post_author=instructor.id,
        post_parent=course.id,
        post_title="Loops",
        post_status="publish",
        post_type="lesson",
        menu_order=1,
        lesson_content_type="video",
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return instructor, course, lesson


def _challenge(db, course, instructor, slug, status="published", languages=("python",), max_source=65536):
    row = CodingChallenge(
        course_id=course.id,
        created_by=instructor.id,
        slug=slug,
        title=f"Challenge {slug}",
        problem_statement="Read two integers and print their sum.",
        allowed_languages=list(languages),
        starter_code={},
        time_limit_ms=2000,
        memory_limit_mb=256,
        max_source_bytes=max_source,
        max_attempts=20,
        status=status,
        version=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _author(client, instructor):
    app.dependency_overrides[AuthService.require_instructor] = lambda: instructor
    app.dependency_overrides[AuthService.get_current_active_user] = lambda: instructor


def _blocks_url(course, lesson):
    return f"{ROOT}/courses/{course.id}/lessons/{lesson.id}/blocks"


def test_instructor_attaches_published_challenge_at_a_timestamp(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    challenge = _challenge(db, course, instructor, "sum-two")
    as_user(instructor)

    response = client.put(
        _blocks_url(course, lesson),
        json={"blocks": [{"challenge_slug": challenge.slug, "position_seconds": 90, "instructions": "Try a loop."}]},
    )
    assert response.status_code == 200, response.text
    block = response.json()[0]
    assert block["challenge_slug"] == "sum-two"
    assert block["position_seconds"] == 90
    assert block["instructions"] == "Try a loop."
    assert block["challenge_status"] == "published"


def test_block_without_timestamp_is_listed_after_the_lesson(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    challenge = _challenge(db, course, instructor, "after-lesson")
    as_user(instructor)
    response = client.put(
        _blocks_url(course, lesson),
        json={"blocks": [{"challenge_slug": challenge.slug, "position_seconds": None}]},
    )
    assert response.status_code == 200, response.text
    assert response.json()[0]["position_seconds"] is None


def test_enrolled_student_sees_only_published_blocks(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    live = _challenge(db, course, instructor, "live-one")
    _challenge(db, course, instructor, "draft-one", status="draft")
    as_user(instructor)
    client.put(
        _blocks_url(course, lesson),
        json={"blocks": [{"challenge_slug": live.slug, "position_seconds": 10}]},
    )

    student = make_user(role="student")
    db.add(Enrollment(course_id=course.id, user_id=student.id, enrollment_status="enrolled"))
    db.commit()
    as_user(student)
    response = client.get(_blocks_url(course, lesson))
    assert response.status_code == 200, response.text
    assert [b["challenge_slug"] for b in response.json()] == ["live-one"]
    assert "challenge_status" not in response.json()[0]


def test_non_enrolled_student_cannot_read_blocks(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    student = make_user(role="student")
    as_user(student)
    assert client.get(_blocks_url(course, lesson)).status_code == 403


def test_student_cannot_change_blocks(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    challenge = _challenge(db, course, instructor, "not-yours")
    student = make_user(role="student")
    db.add(Enrollment(course_id=course.id, user_id=student.id, enrollment_status="enrolled"))
    db.commit()
    as_user(student)
    response = client.put(
        _blocks_url(course, lesson),
        json={"blocks": [{"challenge_slug": challenge.slug, "position_seconds": 5}]},
    )
    assert response.status_code == 403


def test_draft_challenge_cannot_be_attached(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    _challenge(db, course, instructor, "still-draft", status="draft")
    as_user(instructor)
    response = client.put(
        _blocks_url(course, lesson),
        json={"blocks": [{"challenge_slug": "still-draft", "position_seconds": 5}]},
    )
    assert response.status_code == 422


def test_challenge_from_another_course_cannot_be_attached(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    other_instructor, other_course, _ = _course(db, make_user)
    foreign = _challenge(db, other_course, other_instructor, "foreign")
    as_user(instructor)
    response = client.put(
        _blocks_url(course, lesson),
        json={"blocks": [{"challenge_slug": foreign.slug, "position_seconds": 5}]},
    )
    assert response.status_code == 422


def test_same_challenge_twice_at_one_time_is_rejected(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    challenge = _challenge(db, course, instructor, "dupe")
    as_user(instructor)
    response = client.put(
        _blocks_url(course, lesson),
        json={"blocks": [
            {"challenge_slug": challenge.slug, "position_seconds": 30},
            {"challenge_slug": challenge.slug, "position_seconds": 30},
        ]},
    )
    assert response.status_code == 422


def test_negative_timestamp_is_rejected(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    challenge = _challenge(db, course, instructor, "neg")
    as_user(instructor)
    response = client.put(
        _blocks_url(course, lesson),
        json={"blocks": [{"challenge_slug": challenge.slug, "position_seconds": -1}]},
    )
    assert response.status_code == 422


def test_replacing_blocks_removes_the_old_ones(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    first = _challenge(db, course, instructor, "first")
    second = _challenge(db, course, instructor, "second")
    as_user(instructor)
    client.put(_blocks_url(course, lesson), json={"blocks": [{"challenge_slug": first.slug, "position_seconds": 1}]})
    response = client.put(_blocks_url(course, lesson), json={"blocks": [{"challenge_slug": second.slug, "position_seconds": 2}]})
    assert [b["challenge_slug"] for b in response.json()] == ["second"]


def test_draft_round_trip_is_private_to_the_learner(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    challenge = _challenge(db, course, instructor, "drafty", languages=("python", "c"))
    student = make_user(role="student")
    other = make_user(role="student")
    for learner in (student, other):
        db.add(Enrollment(course_id=course.id, user_id=learner.id, enrollment_status="enrolled"))
    db.commit()

    as_user(student)
    assert client.get(f"{ROOT}/challenges/drafty/draft", params={"language": "python"}).json() is None
    saved = client.put(f"{ROOT}/challenges/drafty/draft", json={"language": "python", "source_code": "print(1)"})
    assert saved.status_code == 200, saved.text
    loaded = client.get(f"{ROOT}/challenges/drafty/draft", params={"language": "python"}).json()
    assert loaded["source_code"] == "print(1)"

    client.put(f"{ROOT}/challenges/drafty/draft", json={"language": "python", "source_code": "print(2)"})
    assert client.get(f"{ROOT}/challenges/drafty/draft", params={"language": "python"}).json()["source_code"] == "print(2)"

    as_user(other)
    assert client.get(f"{ROOT}/challenges/drafty/draft", params={"language": "python"}).json() is None


def test_draft_rejects_unknown_language_and_oversize_source(client, db, make_user, as_user):
    instructor, course, lesson = _course(db, make_user)
    _challenge(db, course, instructor, "limits", languages=("python",), max_source=1024)
    student = make_user(role="student")
    db.add(Enrollment(course_id=course.id, user_id=student.id, enrollment_status="enrolled"))
    db.commit()
    as_user(student)
    bad_language = client.put(f"{ROOT}/challenges/limits/draft", json={"language": "c", "source_code": "x"})
    assert bad_language.status_code == 422
    too_big = client.put(f"{ROOT}/challenges/limits/draft", json={"language": "python", "source_code": "x" * 2000})
    assert too_big.status_code == 413
