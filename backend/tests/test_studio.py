"""WP6 — Studio faces (v2.0 §4): per-type defaults (opening face, parent
view), settings validation, Reward System Designer hooks (points override,
custom course badges, leaderboard opt-out, streak freezes), the Parent View
Configurator filtering the guardian digest, and the SP schedule builder
(term view + clone week).
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassStatus


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="studio-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def student_headers(student_user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}


def _course(db, instructor, course_type="seyappaduporul"):
    from app.models.course import Course
    c = Course(post_title="Studio course", post_content="d", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=0, course_type=course_type)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_defaults_per_type_and_settings_validation(client, db, headers, instructor, student_headers):
    sp = _course(db, instructor, "seyappaduporul")
    mp = _course(db, instructor, "meiporul")
    up = _course(db, instructor, "utporul")
    faces = {c.id: client.get(f"/api/v1/studio/courses/{c.id}/settings", headers=headers).json()["opening_face"]
             for c in (sp, mp, up)}
    assert faces == {sp.id: "schedule", mp.id: "asset_library", up.id: "outcome"}
    sp_settings = client.get(f"/api/v1/studio/courses/{sp.id}/settings", headers=headers).json()
    assert sp_settings["parent_view"]["attendance"] and sp_settings["parent_view"]["completion"]
    assert not sp_settings["parent_view"]["scores"]
    assert sp_settings["rewards"]["streak_freeze_days_per_month"] == 1

    # not the owner
    assert client.get(f"/api/v1/studio/courses/{sp.id}/settings", headers=student_headers).status_code == 403
    # validation
    bad = client.put(f"/api/v1/studio/courses/{sp.id}/settings", headers=headers,
                     json={"rewards": {"points": {"not_an_event": 5}}})
    assert bad.status_code == 422
    bad = client.put(f"/api/v1/studio/courses/{sp.id}/settings", headers=headers,
                     json={"parent_view": {"salary": True}})
    assert bad.status_code == 422
    ok = client.put(f"/api/v1/studio/courses/{sp.id}/settings", headers=headers, json={
        "parent_view": {"scores": True},
        "rewards": {"points": {"lesson_completed": 40},
                    "badges": [{"name": "Lab Rat", "rule": "labs_completed", "threshold": 2, "points": 30}],
                    "streak_freeze_days_per_month": 2, "leaderboard_opt_out": True},
        "face_dismissed": True,
    })
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["parent_view"]["scores"] is True and body["parent_view"]["attendance"] is True
    assert body["rewards"]["points"] == {"lesson_completed": 40}
    assert body["rewards"]["badges"][0]["slug"] == "lab-rat"
    assert body["face_dismissed"] is True


def test_points_override_and_custom_badge(client, db, headers, instructor, student_user, student_headers):
    from app.services import gamification_service as game
    from app.models.gamification import XpEvent
    c = _course(db, instructor)
    client.put(f"/api/v1/studio/courses/{c.id}/settings", headers=headers, json={
        "rewards": {"points": {"lab_completed": 7},
                    "badges": [{"name": "Lab Rat", "rule": "labs_completed", "threshold": 2, "points": 30}]}})
    ev = game.award(db, student_user.id, "lab_completed", f"lab:a:completed:user:{student_user.id}", course_id=c.id)
    db.commit()
    assert ev.points == 7  # override applied
    other = game.award(db, student_user.id, "lab_completed", f"lab:b:completed:user:{student_user.id}")
    db.commit()
    assert other.points == game.DEFAULT_POINTS["lab_completed"]  # no course -> default
    assert db.query(XpEvent).filter(XpEvent.event_type == "course_badge").count() == 0
    game.award(db, student_user.id, "lab_completed", f"lab:c:completed:user:{student_user.id}", course_id=c.id)
    db.commit()
    badge = db.query(XpEvent).filter(XpEvent.event_type == "course_badge").one()
    assert badge.meta["slug"] == "lab-rat" and badge.points == 30
    # idempotent on a further award
    game.award(db, student_user.id, "lab_completed", f"lab:d:completed:user:{student_user.id}", course_id=c.id)
    db.commit()
    assert db.query(XpEvent).filter(XpEvent.event_type == "course_badge").count() == 1
    me = client.get(f"/api/v1/studio/courses/{c.id}/rewards/me", headers=student_headers).json()
    assert me["badges"][0]["earned"] is True and me["badges"][0]["progress"] == 2
    assert me["points_in_course"] == 7 * 3 + 30


def test_leaderboard_opt_out(client, db, headers, instructor, student_user, student_headers):
    from app.services import gamification_service as game
    c = _course(db, instructor)
    game.award(db, student_user.id, "lesson_completed", f"lesson:1:completed:user:{student_user.id}", course_id=c.id)
    db.commit()
    r = client.get(f"/api/v1/gamification/leaderboard?scope=course:{c.id}", headers=student_headers)
    assert r.status_code == 200 and len(r.json()["entries"]) == 1
    client.put(f"/api/v1/studio/courses/{c.id}/settings", headers=headers, json={"rewards": {"leaderboard_opt_out": True}})
    r = client.get(f"/api/v1/gamification/leaderboard?scope=course:{c.id}", headers=student_headers)
    assert r.status_code == 200 and r.json()["entries"] == [] and r.json()["opted_out"] is True


def test_streak_freeze_covers_missed_days_within_allowance(client, db, headers, instructor, student_user):
    from app.services import gamification_service as game
    from app.models.gamification import UserGameStats
    c = _course(db, instructor)
    db.add(Enrollment(user_id=student_user.id, course_id=c.id, enrollment_status="enrolled"))
    db.commit()
    client.put(f"/api/v1/studio/courses/{c.id}/settings", headers=headers,
               json={"rewards": {"streak_freeze_days_per_month": 2}})
    stats = UserGameStats(user_id=student_user.id, total_xp=0, current_streak=3, longest_streak=3,
                          last_active_date=date(2026, 9, 1))
    db.add(stats)
    db.commit()
    game.touch_streak(db, stats, on_date=date(2026, 9, 3))   # 1 missed day -> frozen
    assert stats.current_streak == 4 and stats.streak_freezes_used == 1
    game.touch_streak(db, stats, on_date=date(2026, 9, 6))   # 2 more missed -> exceeds allowance -> reset
    assert stats.current_streak == 1
    # no allowance at all -> plain reset
    client.put(f"/api/v1/studio/courses/{c.id}/settings", headers=headers,
               json={"rewards": {"streak_freeze_days_per_month": 0}})
    stats.current_streak = 5
    game.touch_streak(db, stats, on_date=date(2026, 9, 8))
    assert stats.current_streak == 1


def test_parent_digest_honours_parent_view(client, db, headers, instructor, student_user, make_user):
    from app.services.auth_service import AuthService
    from app.main import app
    c = _course(db, instructor, "seyappaduporul")
    db.add(Enrollment(user_id=student_user.id, course_id=c.id, enrollment_status="enrolled", course_progress_percentage=42))
    db.commit()
    from app.routers.parents import ParentStudent
    ParentStudent.__table__.create(bind=db.get_bind(), checkfirst=True)  # table lives in the router module
    parent = make_user(role="parent", email="studio-parent@example.com")
    db.add(ParentStudent(parent_user_id=parent.id, student_user_id=student_user.id))
    db.commit()
    app.dependency_overrides[AuthService.get_current_user] = lambda: parent
    try:
        d = client.get("/api/v1/parents/digest").json()
        course = d["digests"][0]["courses"][0]
        assert course["progress"] == 42 and "attendance" in course and "recent_scores" not in course
        client.put(f"/api/v1/studio/courses/{c.id}/settings", headers=headers,
                   json={"parent_view": {"completion": False, "scores": True}})
        d = client.get("/api/v1/parents/digest").json()
        course = d["digests"][0]["courses"][0]
        assert "progress" not in course and "recent_scores" in course and "risk" in course
    finally:
        app.dependency_overrides.pop(AuthService.get_current_user, None)


def test_schedule_term_view_and_clone_week(client, db, headers, instructor):
    c = _course(db, instructor)
    monday = date(2026, 9, 7)
    for i, day in enumerate((0, 2)):
        start = datetime.combine(monday + timedelta(days=day), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=10)
        db.add(LiveClass(course_id=c.id, instructor_id=instructor.id, title=f"Week class {i}", scheduled_start=start,
                         scheduled_end=start + timedelta(hours=1), room_name=f"studio-room-{i}",
                         status=LiveClassStatus.SCHEDULED, settings={}, purpose="lecture"))
    db.commit()
    r = client.get(f"/api/v1/studio/courses/{c.id}/schedule", headers=headers)
    assert r.status_code == 200
    assert r.json()["live_classes"] == 2 and len(r.json()["weeks"]) == 1
    bad = client.post(f"/api/v1/studio/courses/{c.id}/schedule/clone-week", headers=headers,
                      json={"from_week_start": "2026-09-14", "to_week_start": "2026-09-21"})
    assert bad.status_code == 422  # empty source week
    ok = client.post(f"/api/v1/studio/courses/{c.id}/schedule/clone-week", headers=headers,
                     json={"from_week_start": "2026-09-07", "to_week_start": "2026-09-14"})
    assert ok.status_code == 200, ok.text
    assert len(ok.json()["created"]) == 2 and ok.json()["schedule"]["live_classes"] == 4
    weeks = ok.json()["schedule"]["weeks"]
    assert [w["week_start"] for w in weeks] == ["2026-09-07", "2026-09-14"]
    cloned = db.query(LiveClass).filter(LiveClass.id.in_(ok.json()["created"])).all()
    assert all(cl.purpose == "lecture" and cl.status == LiveClassStatus.SCHEDULED for cl in cloned)
    assert len({cl.room_name for cl in cloned} | {"studio-room-0", "studio-room-1"}) == 4
