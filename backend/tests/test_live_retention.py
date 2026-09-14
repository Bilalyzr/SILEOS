"""WP5 — live-class classification, permanent class reports, recording
retention (soft delete + 30-day restore, extend within the ceiling, expiry
warnings, sweeper purge that never touches the report) and the deletion audit.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassStatus


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="ret-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def admin_headers(make_user):
    from app.core.security import create_access_token
    a = make_user(role="admin", email="ret-admin@example.com")
    return {"Authorization": f"Bearer {create_access_token({'sub': str(a.id)})}"}


@pytest.fixture
def student_headers(student_user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}


@pytest.fixture
def course(db, instructor):
    from app.models.course import Course
    c = Course(post_author=instructor.id, post_title="Retention course", course_price_type="free", course_price=0,
               course_type="seyappaduporul")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _class(db, course, instructor, room, **over):
    now = datetime.now(timezone.utc)
    fields = dict(course_id=course.id, instructor_id=instructor.id, title="Ret class",
                  scheduled_start=now - timedelta(hours=2), scheduled_end=now - timedelta(hours=1), room_name=room,
                  status=LiveClassStatus.LIVE, started_at=now - timedelta(hours=2),
                  settings={"record": True, "attendance_threshold_pct": 60, "retention_days": 30})
    fields.update(over)
    lc = LiveClass(**fields)
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return lc


def test_classification_validated_on_create(client, db, headers, course):
    start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    r = client.post("/api/v1/live/classes", json={"course_id": course.id, "title": "Doubt hour", "scheduled_start": start,
                    "duration_minutes": 45, "settings": {"purpose": "doubt_clearing", "mode": "one_to_one",
                                                          "audience": "selected", "recording_policy": "never", "retention_days": 10}},
                    headers=headers)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    lc = body[0] if isinstance(body, list) else body.get("classes", [body])[0] if isinstance(body, dict) and "classes" in body else body
    assert lc["purpose"] == "doubt_clearing" and lc["mode"] == "one_to_one" and lc["audience"] == "selected"
    assert lc["recording_policy"] == "never" and lc["lifecycle"] == "scheduled"
    r = client.post("/api/v1/live/classes", json={"course_id": course.id, "title": "Bad", "scheduled_start": start,
                    "duration_minutes": 45, "settings": {"purpose": "party"}}, headers=headers)
    assert r.status_code == 422


def test_end_class_generates_permanent_report_and_retention(client, db, headers, course, instructor, student_user, student_headers):
    db.add(Enrollment(course_id=course.id, user_id=student_user.id, enrollment_status="enrolled"))
    lc = _class(db, course, instructor, "ret-room-1", purpose="lecture")
    db.add(LiveClassAttendance(class_id=lc.id, user_id=student_user.id, first_joined_at=lc.started_at,
                               last_heartbeat_at=lc.started_at + timedelta(minutes=50), accumulated_seconds=3000))
    db.commit()
    r = client.post(f"/api/v1/live/classes/{lc.id}/end", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["lifecycle"] == "ended" and r.json()["retention_until"] is not None
    db.refresh(lc)
    assert (lc.retention_until - lc.ended_at).days == 30          # per-class retention_days honoured

    rep = client.get(f"/api/v1/live/classes/{lc.id}/report", headers=headers).json()
    assert rep["purpose"] == "lecture" and rep["engagement"]["enrolled"] == 1 and rep["engagement"]["present"] == 1
    assert rep["attendance"][0]["user_id"] == student_user.id and rep["attendance"][0]["duration_s"] == 3000
    assert rep["recording"]["retention_until"] is not None and rep["lifecycle"] == "ended"
    # learner sees only their own row, guardians only when shared
    mine = client.get(f"/api/v1/live/classes/{lc.id}/report", headers=student_headers).json()
    assert len(mine["attendance"]) == 1 and mine["event_log"] == []
    r = client.put(f"/api/v1/live/classes/{lc.id}/report/notes", json={"instructor_notes": "Covered Newton's laws."}, headers=headers)
    assert r.status_code == 200
    assert client.put(f"/api/v1/live/classes/{lc.id}/report/notes", json={"instructor_notes": "x"}, headers=student_headers).status_code == 403
    r = client.get(f"/api/v1/live/classes/{lc.id}/report.pdf", headers=headers)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert client.get(f"/api/v1/live/classes/{lc.id}/report.pdf", headers=student_headers).status_code == 403


def test_soft_delete_restore_extend_and_audit(client, db, headers, admin_headers, student_headers, course, instructor):
    lc = _class(db, course, instructor, "ret-room-2", status=LiveClassStatus.ENDED, ended_at=datetime.now(timezone.utc) - timedelta(hours=1),
                recording_video_id="bunny-abc", retention_until=datetime.now(timezone.utc) + timedelta(days=30))
    # students cannot delete; instructor soft-deletes with a reason
    assert client.delete(f"/api/v1/live/classes/{lc.id}/recording", headers=student_headers).status_code == 403
    r = client.delete(f"/api/v1/live/classes/{lc.id}/recording?reason=term%20over", headers=headers)
    assert r.status_code == 200 and r.json()["restorable_days"] == 30
    db.refresh(lc)
    assert lc.recording_video_id == "bunny-abc" and lc.recording_deleted_at is not None    # media kept during grace
    assert client.get(f"/api/v1/live/classes/{lc.id}/recording-playback", headers=headers).status_code == 404
    assert client.delete(f"/api/v1/live/classes/{lc.id}/recording", headers=headers).status_code == 409
    # restore within the window
    r = client.post(f"/api/v1/live/classes/{lc.id}/recording/restore", headers=headers)
    assert r.status_code == 200
    db.refresh(lc)
    assert lc.recording_deleted_at is None
    # extend, capped at the tenant ceiling (365 days after the class)
    r = client.post(f"/api/v1/live/classes/{lc.id}/recording/extend", json={"days": 400}, headers=headers)
    assert r.status_code == 200
    db.refresh(lc)
    assert (lc.retention_until - lc.ended_at).days <= 365
    assert client.post(f"/api/v1/live/classes/{lc.id}/recording/extend", json={"days": 10}, headers=headers).status_code == 409
    # audit trail: admin only
    assert client.get("/api/v1/live/recordings/audit", headers=headers).status_code == 403
    audit = client.get(f"/api/v1/live/recordings/audit?class_id={lc.id}", headers=admin_headers).json()["audit"]
    assert [a["action"] for a in audit] == ["extend", "restore", "soft_delete"]
    assert audit[-1]["reason"] == "term over"


def test_sweeper_warns_then_purges_but_keeps_the_report(client, db, headers, course, instructor, student_user):
    from app.models.live_class import LiveClassEvent
    from app.models.live_class_report import ClassReport
    from app.services import class_report_service as crs
    now = datetime.now(timezone.utc)
    lc = _class(db, course, instructor, "ret-room-3", status=LiveClassStatus.ENDED, ended_at=now - timedelta(days=10),
                recording_video_id="bunny-xyz", retention_until=now + timedelta(days=2))
    crs.generate_report(db, lc)
    db.commit()
    stats = crs.retention_pass(db, now)
    assert stats == {"warned": 1, "purged": 0}
    assert db.query(LiveClassEvent).filter(LiveClassEvent.class_id == lc.id, LiveClassEvent.event == "recording.expiry_warning_3d").count() == 1
    assert crs.retention_pass(db, now) == {"warned": 0, "purged": 0}     # idempotent
    exp = client.get("/api/v1/live/recordings/expiring?within_days=14", headers=headers).json()["classes"]
    assert [c["class_id"] for c in exp] == [lc.id]
    # past retention → purged; report survives; lifecycle = deleted
    stats = crs.retention_pass(db, now + timedelta(days=3))
    assert stats["purged"] == 1
    db.refresh(lc)
    assert lc.recording_video_id is None
    rep = db.query(ClassReport).filter(ClassReport.class_id == lc.id).first()
    assert rep is not None and rep.engagement is not None
    assert crs.lifecycle(lc, rep) == "deleted"
    assert client.get(f"/api/v1/live/classes/{lc.id}/report", headers=headers).json()["recording"]["exists"] is False
    # soft-deleted recordings purge 30 days after deletion
    lc2 = _class(db, course, instructor, "ret-room-4", status=LiveClassStatus.ENDED, ended_at=now - timedelta(days=1),
                 recording_video_id="bunny-2", retention_until=now + timedelta(days=300), recording_deleted_at=now - timedelta(days=31))
    assert crs.retention_pass(db, now)["purged"] == 1
    db.refresh(lc2)
    assert lc2.recording_video_id is None


def test_manifest_lists_course_recordings(client, db, headers, course, instructor):
    now = datetime.now(timezone.utc)
    _class(db, course, instructor, "ret-room-5", status=LiveClassStatus.ENDED, ended_at=now, recording_video_id="v1",
           retention_until=now + timedelta(days=5))
    _class(db, course, instructor, "ret-room-6", status=LiveClassStatus.ENDED, ended_at=now, recording_video_id="v2",
           retention_until=now + timedelta(days=5), recording_deleted_at=now)
    r = client.get(f"/api/v1/live/courses/{course.id}/recordings/manifest", headers=headers)
    assert r.status_code == 200
    recs = r.json()["recordings"]
    assert [x["recording_video_id"] for x in recs] == ["v1"] and recs[0]["download_endpoint"].endswith("/recording-download")
