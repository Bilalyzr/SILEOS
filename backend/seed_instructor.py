"""
Seed a pre-approved Instructor login for local development.

Creates (or updates) a User(role='instructor', is_verified=True) plus an
InstructorProfile(is_approved=True) so the user can log in immediately.

Run:
    docker-compose exec backend python seed_instructor.py
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, InstructorProfile


EMAIL = "instructor@example.com"
PASSWORD = "Instructor@123"
LOGIN = "demo_instructor"
DISPLAY_NAME = "Demo Instructor"


def main() -> None:
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.user_email == EMAIL).first()
        if user:
            user.role = "instructor"
            user.user_pass = get_password_hash(PASSWORD)
            user.is_active = True
            user.is_verified = True
            user.display_name = DISPLAY_NAME
            print(f"Updated existing user id={user.id}")
        else:
            user = User(
                user_login=LOGIN,
                user_pass=get_password_hash(PASSWORD),
                user_nicename=LOGIN,
                user_email=EMAIL,
                display_name=DISPLAY_NAME,
                role="instructor",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.flush()
            print(f"Created user id={user.id}")

        profile = (
            db.query(InstructorProfile)
            .filter(InstructorProfile.user_id == user.id)
            .first()
        )
        if profile:
            profile.is_approved = True
            profile.is_blocked = False
            profile.instructor_bio = "Senior backend engineer · 8 years teaching FastAPI / Postgres / cloud infra."
            profile.instructor_designation = "Senior Instructor"
            profile.instructor_rating = "4.8"
            profile.profile_completion = 100
            print(f"Updated existing instructor profile id={profile.id}")
        else:
            profile = InstructorProfile(
                user_id=user.id,
                instructor_bio="Senior backend engineer · 8 years teaching FastAPI / Postgres / cloud infra.",
                instructor_designation="Senior Instructor",
                instructor_rating="4.8",
                profile_completion=100,
                is_approved=True,
                is_blocked=False,
            )
            db.add(profile)
            print(f"Created instructor profile")

        db.commit()

        print("\n=== Instructor Login Ready ===")
        print(f"  URL:      http://localhost:3100/login")
        print(f"  Email:    {EMAIL}")
        print(f"  Password: {PASSWORD}")
        print(f"  Redirect: /instructor/dashboard")
    except Exception as e:
        db.rollback()
        print(f"FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
