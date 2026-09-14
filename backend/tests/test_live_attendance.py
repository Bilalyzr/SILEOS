"""Attendance router: GET rows/summary, CSV export, threshold recompute.

Covers: CSV shape + export event logged, recompute flips present rows and
409s on a non-ENDED class.
"""
import csv
import io
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassEvent, LiveClassStatus


@pytest.fixture()
def instructor_user(db):
    from app.models.user import User

    u = User(
        user_login="att_instructor", user_pass="x", user_nicename="att_instructor",
        user_email="att_instructor@example.com", display_name="Att Instructor",
        role="instructor",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def live_course(db, instructor_user):
    from app.models.course import Course

    c = Course(post_author=instructor_user.id, post_title="Att Course",
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


def _make_class(db, course, instructor, room_name, status=LiveClassStatus.ENDED,
                 duration_minutes=100, **overrides):
    now = datetime.now(timezone.utc)
    defaults = dict(
        course_id=course.id,
        instructor_id=instructor.id,
        title="Attendance Test Class",
        scheduled_start=now - timedelta(minutes=duration_minutes),
        scheduled_end=now,
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


class TestAttendanceList:
    def test_get_attendance_rows_shape(self, client, db, as_user, instructor_user, live_course, student_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-att00001")
        db.add(LiveClassAttendance(
            class_id=lc.id, user_id=student_user.id,
            first_joined_at=datetime.now(timezone.utc), accumulated_seconds=3660, present=True,
        ))
        db.commit()

        as_user(instructor_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/attendance")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_participants"] == 1
        assert body["present_count"] == 1
        row = body["rows"][0]
        assert row["email"] == student_user.user_email
        assert row["accumulated_minutes"] == 61
        assert row["present"] is True

    def test_non_staff_403(self, client, db, as_user, student_user, live_course, instructor_user):
        lc = _make_class(db, live_course, instructor_user, "si-att00002")
        as_user(student_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/attendance")
        assert r.status_code == 403


class TestAttendanceCsvExport:
    def test_csv_shape_and_export_event_logged(self, client, db, as_user, instructor_user, live_course, student_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-att00003")
        joined = datetime.now(timezone.utc)
        db.add(LiveClassAttendance(
            class_id=lc.id, user_id=student_user.id,
            first_joined_at=joined, accumulated_seconds=3660, present=True,
        ))
        db.commit()

        as_user(instructor_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/attendance/export.csv")
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers["content-type"]
        assert "attachment" in r.headers.get("content-disposition", "")

        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        assert rows[0] == ["name", "email", "first_join", "total_minutes", "present"]
        assert len(rows) == 2
        data_row = rows[1]
        assert data_row[1] == student_user.user_email
        assert data_row[3] == "61"
        assert data_row[4] == "True"

        events = db.query(LiveClassEvent).filter_by(class_id=lc.id, event="attendance.exported").all()
        assert len(events) == 1

    def test_csv_export_non_staff_403(self, client, db, as_user, student_user, live_course, instructor_user):
        lc = _make_class(db, live_course, instructor_user, "si-att00004")
        as_user(student_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/attendance/export.csv")
        assert r.status_code == 403

    def test_csv_export_neutralizes_formula_injection(self, db, client, as_user, instructor_user, live_course):
        """A display_name starting with '=' (or +/-/@) is a live formula-
        injection vector in Excel/Sheets on open — must come out
        single-quote-prefixed so it renders as literal text instead."""
        from app.models.user import User

        malicious = User(
            user_login="att_evil", user_pass="x", user_nicename="att_evil",
            user_email="=cmd|'/c calc'!A1@example.com",
            display_name="=cmd|'/c calc'!A1",
        )
        db.add(malicious)
        db.commit()
        db.refresh(malicious)
        _enroll(db, malicious, live_course)

        lc = _make_class(db, live_course, instructor_user, "si-att00008")
        db.add(LiveClassAttendance(
            class_id=lc.id, user_id=malicious.id,
            first_joined_at=datetime.now(timezone.utc), accumulated_seconds=600, present=True,
        ))
        db.commit()

        as_user(instructor_user)
        r = client.get(f"/api/v1/live/classes/{lc.id}/attendance/export.csv")
        assert r.status_code == 200, r.text

        reader = csv.reader(io.StringIO(r.text))
        rows = list(reader)
        data_row = rows[1]
        assert data_row[0] == "'=cmd|'/c calc'!A1"
        assert data_row[1] == "'=cmd|'/c calc'!A1@example.com"


class TestAttendanceRecompute:
    def test_recompute_flips_present_rows(self, client, db, as_user, instructor_user, live_course, student_user):
        _enroll(db, student_user, live_course)
        lc = _make_class(db, live_course, instructor_user, "si-att00005", duration_minutes=100)
        # 3000s of 6000s scheduled = 50%. At threshold 60 -> absent; recompute
        # to threshold 40 -> present.
        db.add(LiveClassAttendance(class_id=lc.id, user_id=student_user.id, accumulated_seconds=3000, present=False))
        db.commit()

        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/attendance/recompute", json={"threshold_pct": 40})
        assert r.status_code == 200, r.text

        att = db.query(LiveClassAttendance).filter_by(class_id=lc.id, user_id=student_user.id).one()
        assert att.present is True

        db.expire(lc)
        assert lc.settings["attendance_threshold_pct"] == 40

    def test_recompute_409_on_non_ended_class(self, client, db, as_user, instructor_user, live_course):
        lc = _make_class(db, live_course, instructor_user, "si-att00006", status=LiveClassStatus.SCHEDULED,
                          scheduled_start=datetime.now(timezone.utc) + timedelta(minutes=30),
                          scheduled_end=datetime.now(timezone.utc) + timedelta(minutes=130))
        as_user(instructor_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/attendance/recompute", json={"threshold_pct": 40})
        assert r.status_code == 409

    def test_recompute_non_staff_403(self, client, db, as_user, student_user, live_course, instructor_user):
        lc = _make_class(db, live_course, instructor_user, "si-att00007")
        as_user(student_user)
        r = client.post(f"/api/v1/live/classes/{lc.id}/attendance/recompute", json={"threshold_pct": 40})
        assert r.status_code == 403
