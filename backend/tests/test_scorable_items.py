"""WP1 — ScorableItem contract (v2.0 §5): normalisation with derived
max_score, the four universal fields, practice-only, the tier-floor
publication rule, the derived registry endpoint, and cumulative grading that
honours weights, buckets (games_h5p vs three_d_tasks) and live participation.
"""
from datetime import datetime, timedelta, timezone

import pytest

QUIZ_RUSH = {"items": [
    {"prompt": "2+2?", "options": ["3", "4"], "answer_index": 1},
    {"prompt": "3+3?", "options": ["6", "7"], "answer_index": 0},
], "settings": {"seconds_per_question": 20, "shuffle": False}}


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="scor-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def other_instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="scor-other@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def other_headers(client, other_instructor, auth_headers):
    return auth_headers(other_instructor.user_email)


def _course(db, instructor, course_type="utporul"):
    from app.models.course import Course
    c = Course(post_title="Scorable course", post_content="d", post_excerpt="p",
               post_status="publish", post_author=instructor.id, course_price=0,
               course_type=course_type)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _game(client, headers, title="Rush", publish=True, listed=False):
    r = client.post("/api/v1/games", json={"title": title, "template": "quiz_rush", "config": QUIZ_RUSH}, headers=headers)
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    if publish:
        assert client.post(f"/api/v1/games/{gid}/publish", headers=headers).status_code == 200
    if listed:
        assert client.post(f"/api/v1/games/{gid}/list", json={"listed": True}, headers=headers).status_code == 200
    return gid


def _quiz(client, headers, course_id, modules, expect=200):
    r = client.post(f"/api/v1/courses/{course_id}/quizzes",
                    json={"title": "Container quiz", "questions": [], "interactive_modules": modules},
                    headers=headers)
    assert r.status_code == expect, r.text
    return r


def test_old_shape_normalises_with_defaults(client, db, instructor, headers):
    course = _course(db, instructor)
    gid = _game(client, headers)
    r = _quiz(client, headers, course.id, [{"kind": "game", "id": gid}])
    qid = r.json()["id"]
    got = client.get(f"/api/v1/courses/{course.id}/quizzes/{qid}", headers=headers).json()["interactive_modules"]
    assert got == [{"kind": "game", "id": gid, "title": "Rush", "max_score": 20, "weight": 1.0,
                    "attempts_allowed": 0, "grading_mode": "auto", "practice_only": False, "tier_floor": "T4"}]


def test_client_cannot_set_max_score_and_fields_validate(client, db, instructor, headers):
    course = _course(db, instructor)
    gid = _game(client, headers)
    r = _quiz(client, headers, course.id, [{"kind": "game", "id": gid, "max_score": 999, "weight": 2.5,
                                            "attempts_allowed": 3, "practice_only": True}])
    item = r.json()["interactive_modules"][0]
    assert item["max_score"] == 20 and item["weight"] == 2.5 and item["attempts_allowed"] == 3 and item["practice_only"] is True
    _quiz(client, headers, course.id, [{"kind": "game", "id": gid, "weight": -1}], expect=422)
    _quiz(client, headers, course.id, [{"kind": "game", "id": gid, "grading_mode": "magic"}], expect=422)
    _quiz(client, headers, course.id, [{"kind": "game", "id": gid, "tier_floor": "T9"}], expect=422)
    _quiz(client, headers, course.id, [{"kind": "game", "id": gid}, {"kind": "game", "id": gid}], expect=422)


def test_tier_floor_above_t4_blocks_unless_practice(client, db, instructor, headers):
    course = _course(db, instructor)
    gid = _game(client, headers)
    r = _quiz(client, headers, course.id, [{"kind": "game", "id": gid, "tier_floor": "T2"}], expect=422)
    assert "T4" in r.json()["detail"]
    _quiz(client, headers, course.id, [{"kind": "game", "id": gid, "tier_floor": "T2", "practice_only": True}])
    # update path enforces the same rule
    qid = _quiz(client, headers, course.id, [{"kind": "game", "id": gid}]).json()["id"]
    r = client.put(f"/api/v1/courses/{course.id}/quizzes/{qid}",
                   json={"interactive_modules": [{"kind": "game", "id": gid, "tier_floor": "T1"}]}, headers=headers)
    assert r.status_code == 422


@pytest.mark.usefixtures("authored_native_labs")
def test_lab_kind_native_only(client, db, instructor, headers):
    course = _course(db, instructor)
    r = _quiz(client, headers, course.id, [{"kind": "lab", "id": "fixture-reaction-lab"}])
    item = r.json()["interactive_modules"][0]
    assert item["max_score"] == 100 and item["title"].startswith("Reaction Lab")
    _quiz(client, headers, course.id, [{"kind": "lab", "id": "projectile-motion"}], expect=422)  # embed, no score
    _quiz(client, headers, course.id, [{"kind": "lab", "id": "no-such-lab"}], expect=422)
    _quiz(client, headers, course.id, [{"kind": "three_d_task", "id": 999999}], expect=404)  # WP2 router: unknown task


def test_marketplace_game_allowed_private_game_403(client, db, instructor, headers, other_headers):
    course = _course(db, instructor)
    listed = _game(client, other_headers, title="Shared", listed=True)
    private = _game(client, other_headers, title="Private")
    _quiz(client, headers, course.id, [{"kind": "game", "id": listed}])
    _quiz(client, headers, course.id, [{"kind": "game", "id": private}], expect=403)


@pytest.mark.usefixtures("authored_native_labs")
def test_registry_lists_insertable_items(client, db, instructor, headers, other_headers):
    mine = _game(client, headers, title="Mine")
    shared = _game(client, other_headers, title="Shared", listed=True)
    _game(client, other_headers, title="Hidden")
    r = client.get("/api/v1/scorable-items", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    games = {i["id"]: i for i in items if i["kind"] == "game"}
    assert games[mine]["source"] == "mine" and games[shared]["source"] == "marketplace"
    assert len(games) == 2
    labs = {i["id"]: i for i in items if i["kind"] == "lab"}
    assert labs["fixture-cell-identify"]["max_score"] == 110 and labs["fixture-cell-identify"]["bucket"] == "three_d_tasks"
    assert all(i["tier_floor"] == "T4" for i in items)
    assert r.json()["gradeable_floor"] == "T4"


@pytest.mark.usefixtures("authored_native_labs")
def test_cumulative_honours_weights_buckets_practice_and_live(client, db, instructor, headers, student_user):
    from app.models.enrollment import Enrollment
    from app.models.game import GameResult
    from app.models.content_library import VirtualLabResult
    from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassStatus

    course = _course(db, instructor, course_type="utporul")   # 40/15/15/20/10
    gid = _game(client, headers)
    _quiz(client, headers, course.id, [
        {"kind": "game", "id": gid, "weight": 3},
        {"kind": "lab", "id": "fixture-reaction-lab", "weight": 1},
    ])
    db.add(Enrollment(course_id=course.id, user_id=student_user.id, enrollment_status="enrolled"))
    db.add(GameResult(game_id=gid, user_id=student_user.id, score=16, max_score=20, duration_s=30))   # 80%
    db.add(GameResult(game_id=gid, user_id=student_user.id, score=10, max_score=20, duration_s=30))   # best wins
    db.add(VirtualLabResult(lab_slug="fixture-reaction-lab", user_id=student_user.id, score=50, max_score=100))  # 50%
    db.commit()

    # cumulative-grade depends on AuthService.get_current_user (not the *_active* variant
    # that as_user overrides), so mint a real bearer for the student.
    from app.core.security import create_access_token
    sh = {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}
    r = client.get(f"/api/v1/analytics/courses/{course.id}/students/{student_user.id}/cumulative-grade", headers=sh)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["breakdown"]["interactive_modules"]["average"] == 80.0
    assert body["breakdown"]["three_d_tasks"]["average"] == 50.0
    assert body["breakdown"]["live_participation"]["average"] is None
    # only games_h5p (15) and three_d_tasks (15) have data → (80*15 + 50*15) / 30
    assert body["cumulative_grade"] == 65.0
    assert body["weights"]["quizzes"] == 40

    # mark the lab practice-only → it drops out of the grade
    from app.models.quiz import Quiz
    quiz = db.query(Quiz).filter(Quiz.post_parent == course.id).first()
    r = client.put(f"/api/v1/courses/{course.id}/quizzes/{quiz.id}", json={"interactive_modules": [
        {"kind": "game", "id": gid, "weight": 3},
        {"kind": "lab", "id": "fixture-reaction-lab", "weight": 1, "practice_only": True},
    ]}, headers=headers)
    assert r.status_code == 200, r.text
    body = client.get(f"/api/v1/analytics/courses/{course.id}/students/{student_user.id}/cumulative-grade", headers=sh).json()
    assert body["breakdown"]["three_d_tasks"]["average"] is None
    assert body["breakdown"]["interactive_modules"]["practice_only"] == 1
    assert body["cumulative_grade"] == 80.0

    # live participation: 2 ended classes, present in 1 → 50%, weight 10
    now = datetime.now(timezone.utc)
    classes = []
    for i in range(2):
        lc = LiveClass(course_id=course.id, instructor_id=instructor.id, title=f"C{i}",
                       scheduled_start=now - timedelta(hours=3), scheduled_end=now - timedelta(hours=2),
                       room_name=f"scor-room-{i}", status=LiveClassStatus.ENDED, settings={})
        db.add(lc)
        classes.append(lc)
    db.commit()
    db.add(LiveClassAttendance(class_id=classes[0].id, user_id=student_user.id, accumulated_seconds=3600, present=True))
    db.add(LiveClassAttendance(class_id=classes[1].id, user_id=student_user.id, accumulated_seconds=10, present=False))
    db.commit()
    body = client.get(f"/api/v1/analytics/courses/{course.id}/students/{student_user.id}/cumulative-grade", headers=sh).json()
    assert body["breakdown"]["live_participation"] == {"average": 50.0, "classes_ended": 2, "weight": "10%"}
    # (80*15 + 50*10) / 25 = 68
    assert body["cumulative_grade"] == 68.0
