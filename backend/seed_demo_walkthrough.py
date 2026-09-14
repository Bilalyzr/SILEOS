"""Extend visual_qa.db with login-capable demo users and live classes.

Throwaway demo data for the local walkthrough ONLY. Run from backend/:
  ./.venv/Scripts/python.exe seed_demo_walkthrough.py
Idempotent: safe to re-run.
"""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///./visual_qa.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("JWT_SECRET", "y" * 64)
os.environ.setdefault("VIDEO_SECRET", "visual-qa-secret-0123456789abcdef")
os.environ.setdefault("ENVIRONMENT", "development")

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app import models  # noqa: F401,E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.course import Course  # noqa: E402
from app.models.enrollment import Enrollment  # noqa: E402
from app.models.live_class import LiveClass, LiveClassStatus, RecordingStatus  # noqa: E402
from app.services.live_class_service import generate_room_name  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()
now = datetime.now(timezone.utc)

PASSWORD = "Demo@1234"
pw_hash = get_password_hash(PASSWORD)


def upsert_user(login, email, name, role):
    u = db.query(User).filter(User.user_email == email).first()
    if not u:
        u = db.query(User).filter(User.user_login == login).first()
    if not u:
        u = User(user_login=login, user_nicename=login.replace("_", "-"))
        db.add(u)
    u.user_email = email
    u.user_pass = pw_hash
    u.display_name = name
    u.role = role
    u.is_active = True
    u.is_verified = True
    db.flush()
    return u


admin = upsert_user("demo_admin", "admin@demo.local", "Sasha Admin", "admin")
instructor = db.query(User).filter(User.user_login == "qa_instructor").first()
if instructor:
    instructor.user_email = "priya@demo.local"
    instructor.user_pass = pw_hash
    instructor.role = "instructor"
    instructor.is_active = True
    instructor.is_verified = True
    db.flush()
else:
    instructor = upsert_user("qa_instructor", "priya@demo.local", "Priya Raman", "instructor")
student = upsert_user("demo_student", "arjun@demo.local", "Arjun Kumar", "student")

courses = db.query(Course).order_by(Course.id).all()
assert courses, "expected seeded courses in visual_qa.db"
first_course = courses[0]

# Enroll the student in the first two courses so dashboards have content.
for c in courses[:2]:
    exists = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == student.id, Enrollment.course_id == c.id)
        .first()
    )
    if not exists:
        db.add(
            Enrollment(
                user_id=student.id,
                course_id=c.id,
                enrollment_status="enrolled",
                enrollment_source="purchase",
            )
        )
db.flush()

# Live classes: one opening soon, one further out, one LIVE now, one ENDED.
if db.query(LiveClass).count() == 0:
    specs = [
        dict(
            title="React Hooks Deep Dive — Live Q&A",
            status=LiveClassStatus.SCHEDULED,
            start=now + timedelta(minutes=10),
            duration=60,
        ),
        dict(
            title="Deploying FastAPI to Production (Live Workshop)",
            status=LiveClassStatus.SCHEDULED,
            start=now + timedelta(days=2, hours=3),
            duration=90,
        ),
        dict(
            title="Pandas Crash Session — LIVE",
            status=LiveClassStatus.LIVE,
            start=now - timedelta(minutes=12),
            duration=60,
        ),
        dict(
            title="Kickoff: Course Orientation (recorded)",
            status=LiveClassStatus.ENDED,
            start=now - timedelta(days=1, hours=2),
            duration=45,
        ),
    ]
    for i, s in enumerate(specs):
        course = courses[0] if i != 2 else courses[1]
        lc = LiveClass(
            course_id=course.id,
            instructor_id=instructor.id,
            title=s["title"],
            description="Demo session seeded for the local walkthrough.",
            scheduled_start=s["start"],
            scheduled_end=s["start"] + timedelta(minutes=s["duration"]),
            timezone="Asia/Kolkata",
            room_name=generate_room_name(),
            status=s["status"],
        )
        if s["status"] == LiveClassStatus.LIVE:
            lc.started_at = s["start"]
        if s["status"] == LiveClassStatus.ENDED:
            lc.started_at = s["start"]
            lc.ended_at = s["start"] + timedelta(minutes=s["duration"])
            lc.recording_status = RecordingStatus.NONE
        db.add(lc)
    db.flush()

db.commit()
print("seeded. logins (password %s):" % PASSWORD)
for u in (admin, instructor, student):
    print(" ", u.role.ljust(10), u.user_email)
print("live classes:", db.query(LiveClass).count())
