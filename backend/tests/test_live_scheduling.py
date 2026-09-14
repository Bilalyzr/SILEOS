"""Scheduling CRUD router: create (one-off + weekly recurrence), role-aware
listing, detail, patch, soft-cancel, live-now, ICS export.

Covers: one-off create; recurrence 2 weekdays x 3 weeks -> 6 rows sharing one
schedule_id with distinct room names and correct local-time->UTC conversion
for Asia/Kolkata; non-owner instructor 403; student list scoping (enrolled
sees, stranger doesn't); patch-after-start 409; cancel event +
student-invisible after; ICS bytes assertions; live-now filtering.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.core.config import get_settings
from app.models.enrollment import Enrollment
from app.models.live_class import (
    LiveClass,
    LiveClassEvent,
    LiveClassSchedule,
    LiveClassStatus,
)


@pytest.fixture(autouse=True)
def _jitsi_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "JITSI_JWT_SECRET", "test-jitsi-secret-0123456789")
    monkeypatch.setattr(get_settings(), "JITSI_PUBLIC_URL", "https://live.example.test")


@pytest.fixture()
def as_user(client, as_user):
    """Like the shared `as_user` fixture, but also overrides
    `AuthService.require_instructor` (used by POST /classes).

    The shared conftest.py `as_user` only overrides
    `get_current_active_user`/`require_admin`. `require_instructor`'s own
    `Depends(get_current_active_user)` default is resolved at
    class-definition time against the *unbound staticmethod descriptor*, a
    different object from the plain function `AuthService.get_current_active_user`
    points to after class construction, so the shared override does not
    propagate to it (same quirk documented in test_company_billing_api.py's
    `as_company_user`). conftest.py is intentionally left untouched."""
    from app.services.auth_service import AuthService
    from app.main import app

    def _impl(user_obj):
        as_user(user_obj)
        app.dependency_overrides[AuthService.require_instructor] = lambda: user_obj
        return user_obj

    yield _impl
    app.dependency_overrides.pop(AuthService.require_instructor, None)


@pytest.fixture()
def instructor_user(db):
    from app.models.user import User

    u = User(
        user_login="sched_instructor", user_pass="x", user_nicename="sched_instructor",
        user_email="sched_instructor@example.com", display_name="Sched Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def other_instructor(db):
    from app.models.user import User

    u = User(
        user_login="sched_other_instructor", user_pass="x", user_nicename="sched_other_instructor",
        user_email="sched_other_instructor@example.com", display_name="Sched Other Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def admin_user(db):
    from app.models.user import User

    u = User(
        user_login="sched_admin", user_pass="x", user_nicename="sched_admin",
        user_email="sched_admin@example.com", display_name="Sched Admin",
        role="admin",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def live_course(db, instructor_user):
    from app.models.course import Course

    c = Course(post_author=instructor_user.id, post_title="Sched Course",
               course_price_type="free", course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _enroll(db, student, course):
    e = Enrollment(course_id=course.id, user_id=student.id, enrollment_status="enrolled")
    db.add(e)
    db.commit()
    return e


def _make_class(db, course, instructor, room_name, status=LiveClassStatus.SCHEDULED,
                 start_delta=timedelta(minutes=30), duration_minutes=60, **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Sched Test Class",
        scheduled_start=now + start_delta,
        scheduled_end=now + start_delta + timedelta(minutes=duration_minutes),
        room_name=room_name,
        status=status,
        settings={
            "lobby_enabled": True, "start_muted": True, "allow_chat": True,
            "allow_share": True, "record": False, "attendance_threshold_pct": 60,
        },
    )
    defaults.update(overrides)
    lc = LiveClass(**defaults)
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


# ---------------------------------------------------------------------------
# POST /classes — create
# ---------------------------------------------------------------------------

class TestCreate:
    def test_one_off_create(self, client, db, as_user, instructor_user, live_course):
        as_user(instructor_user)
        start = datetime.now(timezone.utc) + timedelta(days=1)
        r = client.post("/api/v1/live/classes", json={
            "course_id": live_course.id,
            "title": "One-off class",
            "scheduled_start": start.isoformat(),
            "duration_minutes": 60,
        })
        assert r.status_code == 201, r.text
        body = r.json()
        assert isinstance(body, list)
        assert len(body) == 1
        row = body[0]
        assert row["title"] == "One-off class"
        assert row["course_id"] == live_course.id
        assert row["instructor_id"] == instructor_user.id
        assert row["status"] == "scheduled"
        assert row["room_name"].startswith("si-")

        lc = db.query(LiveClass).filter_by(id=row["id"]).one()
        assert lc.schedule_id is not None
        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="class.created").all()
        assert len(events) == 1

    def test_non_owner_instructor_403(self, client, db, as_user, other_instructor, live_course):
        as_user(other_instructor)
        start = datetime.now(timezone.utc) + timedelta(days=1)
        r = client.post("/api/v1/live/classes", json={
            "course_id": live_course.id,
            "title": "Not mine",
            "scheduled_start": start.isoformat(),
            "duration_minutes": 60,
        })
        assert r.status_code == 403

    def test_admin_can_create_on_any_course(self, client, db, as_user, admin_user, live_course):
        as_user(admin_user)
        start = datetime.now(timezone.utc) + timedelta(days=1)
        r = client.post("/api/v1/live/classes", json={
            "course_id": live_course.id,
            "title": "Admin scheduled",
            "scheduled_start": start.isoformat(),
            "duration_minutes": 45,
        })
        assert r.status_code == 201, r.text

    def test_weekly_recurrence_two_days_three_weeks(self, client, db, as_user, instructor_user, live_course):
        """recurrence_weekly=["MO","WE"], weeks=3 -> 6 rows sharing one
        schedule_id, distinct room names, and each occurrence's UTC start
        derived from the SAME local wall-clock time via zoneinfo (DST-safe
        per-occurrence conversion, not a fixed offset)."""
        as_user(instructor_user)

        # First occurrence: a Monday, 2026-11-02, 19:00 local Asia/Kolkata.
        # IST is UTC+5:30 year-round (no DST) so this also cross-checks the
        # exact instant, but the conversion must go through zoneinfo per
        # occurrence, not a hardcoded +5:30 offset.
        first_start_local = datetime(2026, 11, 2, 19, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        assert first_start_local.strftime("%A") == "Monday"

        r = client.post("/api/v1/live/classes", json={
            "course_id": live_course.id,
            "title": "Weekly recurring class",
            "scheduled_start": first_start_local.isoformat(),
            "duration_minutes": 60,
            "timezone": "Asia/Kolkata",
            "recurrence_weekly": ["MO", "WE"],
            "weeks": 3,
        })
        assert r.status_code == 201, r.text
        rows = r.json()
        assert len(rows) == 6

        schedule_ids = {row["schedule_id"] for row in rows}
        assert len(schedule_ids) == 1
        assert None not in schedule_ids

        room_names = {row["room_name"] for row in rows}
        assert len(room_names) == 6

        # Every occurrence keeps the same local wall-clock time (19:00
        # Asia/Kolkata) and the same duration.
        for row in rows:
            start_utc = datetime.fromisoformat(row["scheduled_start"])
            end_utc = datetime.fromisoformat(row["scheduled_end"])
            assert (end_utc - start_utc) == timedelta(minutes=60)
            local = start_utc.astimezone(ZoneInfo("Asia/Kolkata"))
            assert local.hour == 19 and local.minute == 0

        # Known instant: 2026-11-02 19:00 Asia/Kolkata == 13:30 UTC.
        first_row = min(rows, key=lambda row: row["scheduled_start"])
        first_utc = datetime.fromisoformat(first_row["scheduled_start"])
        assert first_utc.astimezone(timezone.utc) == datetime(2026, 11, 2, 13, 30, tzinfo=timezone.utc)

        # Weekdays present are exactly Monday/Wednesday across 3 weeks.
        weekdays = sorted({datetime.fromisoformat(row["scheduled_start"]).astimezone(
            ZoneInfo("Asia/Kolkata")).strftime("%A") for row in rows})
        assert weekdays == ["Monday", "Wednesday"]

        # DB-level: one schedule row with the recurrence definition recorded.
        schedule = db.query(LiveClassSchedule).filter_by(id=first_row["schedule_id"]).one()
        assert schedule.weeks == 3
        assert schedule.recurrence_weekly == ["MO", "WE"]

        lc_count = db.query(LiveClass).filter_by(schedule_id=schedule.id).count()
        assert lc_count == 6

    def test_recurrence_never_generates_occurrence_before_scheduled_start(
        self, client, db, as_user, instructor_user, live_course,
    ):
        """Controller ruling (M3): occurrences must never be generated
        before the requested scheduled_start. scheduled_start on a Friday
        with recurrence_weekly=["MO"], weeks=3 must yield exactly 3 rows —
        the three following Mondays (Dec 7, 14, 21) — never a Monday that
        falls before the Friday anchor date."""
        as_user(instructor_user)

        friday_start_local = datetime(2026, 12, 4, 10, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        assert friday_start_local.strftime("%A") == "Friday"

        r = client.post("/api/v1/live/classes", json={
            "course_id": live_course.id,
            "title": "Friday-anchored Monday recurrence",
            "scheduled_start": friday_start_local.isoformat(),
            "duration_minutes": 60,
            "timezone": "Asia/Kolkata",
            "recurrence_weekly": ["MO"],
            "weeks": 3,
        })
        assert r.status_code == 201, r.text
        rows = r.json()
        assert len(rows) == 3

        dates_local = sorted(
            datetime.fromisoformat(row["scheduled_start"]).astimezone(ZoneInfo("Asia/Kolkata")).date()
            for row in rows
        )
        assert dates_local == [
            datetime(2026, 12, 7).date(),
            datetime(2026, 12, 14).date(),
            datetime(2026, 12, 21).date(),
        ]
        # None of the generated occurrences precede the requested anchor date.
        anchor_date = friday_start_local.date()
        assert all(d >= anchor_date for d in dates_local)

    def test_invalid_course_404(self, client, as_user, instructor_user):
        as_user(instructor_user)
        start = datetime.now(timezone.utc) + timedelta(days=1)
        r = client.post("/api/v1/live/classes", json={
            "course_id": 999999,
            "title": "Ghost course",
            "scheduled_start": start.isoformat(),
            "duration_minutes": 60,
        })
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /classes — list scoping
# ---------------------------------------------------------------------------

class TestList:
    def test_instructor_sees_only_own_classes(self, client, db, as_user, instructor_user,
                                                other_instructor, live_course):
        from app.models.course import Course
        other_course = Course(post_author=other_instructor.id, post_title="Other course",
                               course_price_type="free", course_price=0)
        db.add(other_course)
        db.commit()
        db.refresh(other_course)

        mine = _make_class(db, live_course, instructor_user, "si-list0001",
                            start_delta=timedelta(hours=1))
        _make_class(db, other_course, other_instructor, "si-list0002",
                    start_delta=timedelta(hours=1))

        as_user(instructor_user)
        r = client.get("/api/v1/live/classes", params={"scope": "upcoming"})
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["items"]]
        assert mine.id in ids
        assert len(ids) == 1

    def test_student_sees_enrolled_course_classes_only(self, client, db, as_user, student_user,
                                                          instructor_user, live_course):
        from app.models.course import Course
        stranger_course = Course(post_author=instructor_user.id, post_title="Stranger course",
                                  course_price_type="free", course_price=0)
        db.add(stranger_course)
        db.commit()
        db.refresh(stranger_course)

        _enroll(db, student_user, live_course)
        visible = _make_class(db, live_course, instructor_user, "si-list0003",
                               start_delta=timedelta(hours=1))
        hidden = _make_class(db, stranger_course, instructor_user, "si-list0004",
                              start_delta=timedelta(hours=1))

        as_user(student_user)
        r = client.get("/api/v1/live/classes", params={"scope": "upcoming"})
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["items"]]
        assert visible.id in ids
        assert hidden.id not in ids

    def test_admin_sees_all_classes(self, client, db, as_user, admin_user, instructor_user, live_course):
        _make_class(db, live_course, instructor_user, "si-list0005", start_delta=timedelta(hours=1))
        _make_class(db, live_course, instructor_user, "si-list0006", start_delta=timedelta(hours=2))

        as_user(admin_user)
        r = client.get("/api/v1/live/classes", params={"scope": "upcoming"})
        assert r.status_code == 200, r.text
        assert len(r.json()["items"]) >= 2

    def test_upcoming_ordered_ascending(self, client, db, as_user, instructor_user, live_course):
        later = _make_class(db, live_course, instructor_user, "si-list0007", start_delta=timedelta(hours=5))
        sooner = _make_class(db, live_course, instructor_user, "si-list0008", start_delta=timedelta(hours=1))

        as_user(instructor_user)
        r = client.get("/api/v1/live/classes", params={"scope": "upcoming"})
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["items"]]
        assert ids.index(sooner.id) < ids.index(later.id)

    def test_past_ordered_descending(self, client, db, as_user, instructor_user, live_course):
        older = _make_class(db, live_course, instructor_user, "si-list0009",
                             status=LiveClassStatus.ENDED, start_delta=timedelta(hours=-5),
                             ended_at=datetime.now(timezone.utc) - timedelta(hours=4))
        newer = _make_class(db, live_course, instructor_user, "si-list0010",
                             status=LiveClassStatus.ENDED, start_delta=timedelta(hours=-1),
                             ended_at=datetime.now(timezone.utc) - timedelta(minutes=30))

        as_user(instructor_user)
        r = client.get("/api/v1/live/classes", params={"scope": "past"})
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["items"]]
        assert ids.index(newer.id) < ids.index(older.id)

    def test_course_scope_permitted_only(self, client, db, as_user, student_user, instructor_user, live_course):
        _enroll(db, student_user, live_course)
        visible = _make_class(db, live_course, instructor_user, "si-list0011", start_delta=timedelta(hours=1))

        as_user(student_user)
        r = client.get("/api/v1/live/classes", params={"scope": f"course:{live_course.id}"})
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["items"]]
        assert visible.id in ids

    def test_course_scope_denied_for_stranger(self, client, db, as_user, student_user, instructor_user, live_course):
        _make_class(db, live_course, instructor_user, "si-list0012", start_delta=timedelta(hours=1))
        as_user(student_user)
        r = client.get("/api/v1/live/classes", params={"scope": f"course:{live_course.id}"})
        assert r.status_code == 403

    def test_course_scope_excludes_other_courses_for_student(self, client, db, as_user, student_user,
                                                                instructor_user, live_course):
        """Regression for C1: apply_scope_visibility's course: branch must
        actually filter to that course, not just permission-check and then
        return every class in the system. Student enrolled in course1 with
        a visible class there; a second course's class must never appear
        when scoped to course1."""
        from app.models.course import Course
        course2 = Course(post_author=instructor_user.id, post_title="Course 2",
                          course_price_type="free", course_price=0)
        db.add(course2)
        db.commit()
        db.refresh(course2)

        _enroll(db, student_user, live_course)
        _enroll(db, student_user, course2)
        visible = _make_class(db, live_course, instructor_user, "si-c1reg001", start_delta=timedelta(hours=1))
        other_course_class = _make_class(db, course2, instructor_user, "si-c1reg002", start_delta=timedelta(hours=1))

        as_user(student_user)
        r = client.get("/api/v1/live/classes", params={"scope": f"course:{live_course.id}"})
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["items"]]
        assert visible.id in ids
        assert other_course_class.id not in ids

    def test_course_scope_excludes_other_instructors_class_in_another_course(
        self, client, db, as_user, instructor_user, other_instructor, live_course,
    ):
        """Regression for C1: instructor A scoped to their own course must
        never see instructor B's class in a different course."""
        from app.models.course import Course
        course_b = Course(post_author=other_instructor.id, post_title="Instructor B course",
                           course_price_type="free", course_price=0)
        db.add(course_b)
        db.commit()
        db.refresh(course_b)

        own_class = _make_class(db, live_course, instructor_user, "si-c1reg003", start_delta=timedelta(hours=1))
        _make_class(db, course_b, other_instructor, "si-c1reg004", start_delta=timedelta(hours=1))

        as_user(instructor_user)
        r = client.get("/api/v1/live/classes", params={"scope": f"course:{live_course.id}"})
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["items"]]
        assert ids == [own_class.id]

    def test_course_scope_admin_gets_only_that_course(self, client, db, as_user, admin_user,
                                                         instructor_user, live_course):
        """Regression for C1: the admin early-return previously skipped the
        course filter entirely, so scope=course:X returned every class in
        the system for an admin instead of just X's."""
        from app.models.course import Course
        other_course = Course(post_author=instructor_user.id, post_title="Other admin-visible course",
                               course_price_type="free", course_price=0)
        db.add(other_course)
        db.commit()
        db.refresh(other_course)

        in_scope = _make_class(db, live_course, instructor_user, "si-c1reg005", start_delta=timedelta(hours=1))
        out_of_scope = _make_class(db, other_course, instructor_user, "si-c1reg006", start_delta=timedelta(hours=1))

        as_user(admin_user)
        r = client.get("/api/v1/live/classes", params={"scope": f"course:{live_course.id}"})
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["items"]]
        assert ids == [in_scope.id]
        assert out_of_scope.id not in ids

    def test_pagination_defaults_and_cap(self, client, db, as_user, instructor_user, live_course):
        for i in range(3):
            _make_class(db, live_course, instructor_user, f"si-pag000{i}", start_delta=timedelta(hours=i + 1))
        as_user(instructor_user)

        r = client.get("/api/v1/live/classes", params={"scope": "upcoming", "page_size": 2})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["items"]) == 2
        assert body["page"] == 1
        assert body["page_size"] == 2

        r2 = client.get("/api/v1/live/classes", params={"scope": "upcoming", "page_size": 1000})
        assert r2.status_code == 200, r2.text
        assert r2.json()["page_size"] == 100  # capped


# ---------------------------------------------------------------------------
# GET /classes/{id} — detail
# ---------------------------------------------------------------------------

class TestDetail:
    def test_detail_permitted_user(self, client, db, as_user, student_user, instructor_user, live_course):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-det00001", start_delta=timedelta(hours=1))
        as_user(student_user)

        r = client.get(f"/api/v1/live/classes/{lc.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == lc.id
        assert "server_ts" in body
        assert "join_opens_at" in body
        assert body["can_start"] is False

    def test_detail_denied_for_stranger(self, client, db, as_user, student_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-det00002", start_delta=timedelta(hours=1))
        as_user(student_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}")
        assert r.status_code == 403

    def test_detail_can_start_true_for_instructor_when_scheduled(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-det00003", start_delta=timedelta(hours=1))
        as_user(instructor_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}")
        assert r.status_code == 200, r.text
        assert r.json()["can_start"] is True

    def test_detail_404_for_missing(self, client, as_user, instructor_user):
        as_user(instructor_user)
        r = client.get("/api/v1/live/classes/999999")
        assert r.status_code == 404

    def test_start_response_matches_detail_response_scheduled_start(
        self, client, db, as_user, instructor_user, live_course,
    ):
        """Regression for I1: live_class_session.py's POST /start used to
        build its own LiveClassOut via a duplicate _to_out that emitted a
        naive scheduled_start (no re-attached UTC tzinfo), while
        live_classes.py's GET /classes/{id} used the shared, UTC-safe
        live_class_to_out — the same row's scheduled_start serialized
        differently (no trailing Z) between the two endpoints, a 5h30m
        countdown error on IST clients against SQLite. Both routers now
        share live_class_service.live_class_to_out, so the two responses
        must agree exactly."""
        lc = _make_class(db, live_course, instructor_user, "si-i1reg001", start_delta=timedelta(minutes=1))
        as_user(instructor_user)

        r_start = client.post(f"/api/v1/live/classes/{lc.id}/start")
        assert r_start.status_code == 200, r_start.text
        start_value = r_start.json()["scheduled_start"]
        assert start_value.endswith("Z") or "+00:00" in start_value

        r_detail = client.get(f"/api/v1/live/classes/{lc.id}")
        assert r_detail.status_code == 200, r_detail.text
        detail_value = r_detail.json()["scheduled_start"]

        assert start_value == detail_value


# ---------------------------------------------------------------------------
# PATCH /classes/{id}
# ---------------------------------------------------------------------------

class TestPatch:
    def test_patch_scheduled_class(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-pat00001", start_delta=timedelta(hours=1))
        as_user(instructor_user)

        r = client.patch(f"/api/v1/live/classes/{lc.id}", json={"title": "Updated title"})
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "Updated title"

    def test_patch_after_start_409(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-pat00002",
                          status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-5))
        as_user(instructor_user)

        r = client.patch(f"/api/v1/live/classes/{lc.id}", json={"title": "Too late"})
        assert r.status_code == 409

    def test_patch_non_owner_403(self, client, db, as_user, other_instructor, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-pat00003", start_delta=timedelta(hours=1))
        as_user(other_instructor)

        r = client.patch(f"/api/v1/live/classes/{lc.id}", json={"title": "Not mine"})
        assert r.status_code == 403

    def test_patch_updates_duration_recomputes_end(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-pat00004", start_delta=timedelta(hours=1),
                          duration_minutes=30)
        as_user(instructor_user)

        r = client.patch(f"/api/v1/live/classes/{lc.id}", json={"duration_minutes": 90})
        assert r.status_code == 200, r.text
        start = datetime.fromisoformat(r.json()["scheduled_start"])
        end = datetime.fromisoformat(r.json()["scheduled_end"])
        assert (end - start) == timedelta(minutes=90)

    def test_patch_settings_merges_provided_keys_preserving_others(
        self, client, db, as_user, instructor_user, live_course,
    ):
        """Regression for M4: PATCH settings must shallow-merge the
        provided keys over the existing settings dict, not replace it
        wholesale. Class starts with attendance_threshold_pct=90; patching
        only {"record": true} must leave the threshold untouched."""
        lc = _make_class(db, live_course, instructor_user, "si-pat00005", start_delta=timedelta(hours=1),
                          settings={
                              "lobby_enabled": True, "start_muted": True, "allow_chat": True,
                              "allow_share": True, "record": False, "attendance_threshold_pct": 90,
                          })
        as_user(instructor_user)

        r = client.patch(f"/api/v1/live/classes/{lc.id}", json={"settings": {"record": True}})
        assert r.status_code == 200, r.text
        settings = r.json()["settings"]
        assert settings["record"] is True
        assert settings["attendance_threshold_pct"] == 90
        assert settings["lobby_enabled"] is True
        assert settings["allow_chat"] is True
        assert settings["allow_share"] is True

        db.refresh(lc)
        assert lc.settings["attendance_threshold_pct"] == 90
        assert lc.settings["record"] is True


# ---------------------------------------------------------------------------
# DELETE /classes/{id} — soft cancel
# ---------------------------------------------------------------------------

class TestCancel:
    def test_cancel_scheduled_class(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-can00001", start_delta=timedelta(hours=1))
        as_user(instructor_user)

        r = client.delete(f"/api/v1/live/classes/{lc.id}")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "cancelled"

        db.refresh(lc)
        assert lc.status == LiveClassStatus.CANCELLED
        assert lc.deleted_at is not None

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="class.cancelled").all()
        assert len(events) == 1

    def test_cancel_ended_class_409(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-can00002",
                          status=LiveClassStatus.ENDED, start_delta=timedelta(hours=-2))
        as_user(instructor_user)

        r = client.delete(f"/api/v1/live/classes/{lc.id}")
        assert r.status_code == 409

    def test_cancel_twice_404s_on_second_call(self, client, db, as_user, instructor_user, live_course):
        """Regression for M2: the first DELETE soft-cancels (sets
        deleted_at); _get_class_or_404 filters deleted_at.is_(None), so a
        second DELETE on the same class must 404 — there is no reachable
        "already CANCELLED" branch to special-case as an idempotent no-op
        200."""
        lc = _make_class(db, live_course, instructor_user, "si-can00004", start_delta=timedelta(hours=1))
        as_user(instructor_user)

        r1 = client.delete(f"/api/v1/live/classes/{lc.id}")
        assert r1.status_code == 200, r1.text

        r2 = client.delete(f"/api/v1/live/classes/{lc.id}")
        assert r2.status_code == 404, r2.text

    def test_cancel_invisible_to_student_after(self, client, db, as_user, student_user, instructor_user, live_course):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-can00003", start_delta=timedelta(hours=1))
        as_user(instructor_user)
        r = client.delete(f"/api/v1/live/classes/{lc.id}")
        assert r.status_code == 200, r.text

        as_user(student_user)
        r2 = client.get(f"/api/v1/live/classes/{lc.id}")
        assert r2.status_code == 404

        r3 = client.get("/api/v1/live/classes", params={"scope": "upcoming"})
        assert r3.status_code == 200, r3.text
        ids = [row["id"] for row in r3.json()["items"]]
        assert lc.id not in ids


# ---------------------------------------------------------------------------
# GET /live-now
# ---------------------------------------------------------------------------

class TestLiveNow:
    def test_live_now_filters_status_and_visibility(self, client, db, as_user, student_user,
                                                       instructor_user, live_course):
        from app.models.course import Course
        stranger_course = Course(post_author=instructor_user.id, post_title="Stranger course 2",
                                  course_price_type="free", course_price=0)
        db.add(stranger_course)
        db.commit()
        db.refresh(stranger_course)

        _enroll(db, student_user, live_course)
        live_visible = _make_class(db, live_course, instructor_user, "si-live0001",
                                    status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-5))
        _make_class(db, live_course, instructor_user, "si-live0002",
                    status=LiveClassStatus.SCHEDULED, start_delta=timedelta(hours=1))
        _make_class(db, stranger_course, instructor_user, "si-live0003",
                    status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-3))

        as_user(student_user)
        r = client.get("/api/v1/live/live-now")
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["classes"]]
        assert ids == [live_visible.id]

    def test_live_now_admin_sees_all_live(self, client, db, as_user, admin_user, instructor_user, live_course):
        live1 = _make_class(db, live_course, instructor_user, "si-live0004",
                             status=LiveClassStatus.LIVE, start_delta=timedelta(minutes=-5))
        as_user(admin_user)
        r = client.get("/api/v1/live/live-now")
        assert r.status_code == 200, r.text
        ids = [row["id"] for row in r.json()["classes"]]
        assert live1.id in ids


# ---------------------------------------------------------------------------
# GET /classes/{id}/calendar.ics
# ---------------------------------------------------------------------------

class TestICS:
    def test_ics_bytes_and_headers(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-ics00001", start_delta=timedelta(hours=1))
        as_user(instructor_user)

        r = client.get(f"/api/v1/live/classes/{lc.id}/calendar.ics")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/calendar")

        text = r.text
        assert "BEGIN:VCALENDAR" in text
        assert "BEGIN:VEVENT" in text
        assert f"UID:liveclass-{lc.id}@sashainfinity.com" in text
        assert "DTSTART:" in text
        assert "DTEND:" in text
        # DTSTART must be UTC with a trailing Z, e.g. 20260101T120000Z
        import re
        m = re.search(r"DTSTART:(\d{8}T\d{6}Z)", text)
        assert m is not None
        assert "SUMMARY:" in text
        assert "DTSTAMP:" in text
        assert "PRODID:" in text
        assert "END:VEVENT" in text
        assert "END:VCALENDAR" in text

    def test_ics_escapes_special_characters(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-ics00002", start_delta=timedelta(hours=1),
                          title="Class, with; special\nchars", description="Line1\nLine2, semi;colon")
        as_user(instructor_user)

        r = client.get(f"/api/v1/live/classes/{lc.id}/calendar.ics")
        assert r.status_code == 200, r.text
        text = r.text
        assert "Class\\, with\\; special\\nchars" in text
        assert "Line1\\nLine2\\, semi\\;colon" in text
        # Raw unescaped newline must not appear inside the SUMMARY/DESCRIPTION values
        assert "special\nchars" not in text

    def test_ics_denied_for_stranger(self, client, db, as_user, student_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-ics00003", start_delta=timedelta(hours=1))
        as_user(student_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/calendar.ics")
        assert r.status_code == 403

    def test_ics_folds_long_lines_at_75_octets_and_unfolds_correctly(
        self, client, db, as_user, instructor_user, live_course,
    ):
        """Regression for I2: RFC 5545 Section 3.1 requires every physical
        content line to be at most 75 octets, folding longer logical lines
        onto CRLF + a single leading space per continuation. A 120-char
        title previously emitted a single >75-octet SUMMARY line."""
        long_title = "X" * 120
        lc = _make_class(db, live_course, instructor_user, "si-ics00004", start_delta=timedelta(hours=1),
                          title=long_title)
        as_user(instructor_user)

        r = client.get(f"/api/v1/live/classes/{lc.id}/calendar.ics")
        assert r.status_code == 200, r.text
        raw = r.text

        physical_lines = raw.split("\r\n")
        # Drop the single trailing empty element from the final \r\n.
        if physical_lines and physical_lines[-1] == "":
            physical_lines = physical_lines[:-1]

        for line in physical_lines:
            assert len(line.encode("utf-8")) <= 75, f"physical line exceeds 75 octets: {line!r}"

        # Unfold per RFC 5545 Section 3.1: a CRLF immediately followed by a
        # single space is removed, rejoining the continuation onto the
        # previous logical line.
        unfolded_lines: list[str] = []
        for line in physical_lines:
            if line.startswith(" ") and unfolded_lines:
                unfolded_lines[-1] += line[1:]
            else:
                unfolded_lines.append(line)

        summary_line = next(l for l in unfolded_lines if l.startswith("SUMMARY:"))
        assert summary_line == f"SUMMARY:{long_title}"

        # The folded SUMMARY logical line, as originally emitted, really
        # did span more than one physical line (the fold actually fired).
        summary_physical_count = 0
        counting = False
        for line in physical_lines:
            if line.startswith("SUMMARY:"):
                counting = True
                summary_physical_count = 1
                continue
            if counting:
                if line.startswith(" "):
                    summary_physical_count += 1
                else:
                    break
        assert summary_physical_count > 1
