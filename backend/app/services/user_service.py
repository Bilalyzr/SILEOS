"""
User Service - Business logic for user management
"""

import os
import uuid
from fastapi import UploadFile
from sqlalchemy.orm import Session
from typing import Dict, Any
import json

from app.models.user import User, UserProfile, InstructorProfile

class UserService:
    """User service class"""

    @staticmethod
    def format_user_profile_response(user: User, profile: UserProfile) -> Dict[str, Any]:
        """
        Format user profile data for API response
        """
        return {
            "id": user.id,
            "username": user.user_login,
            "email": user.user_email,
            "display_name": user.display_name,
            "role": user.role,
            "status": "active" if user.user_status == 0 else "inactive",
            "profile_completed": user.profile_completed,
            "first_name": profile.first_name or "",
            "last_name": profile.last_name or "",
            "phone": profile.phone or "",
            "description": profile.description or "",
            "designation": profile.designation or "",
            "address": profile.address or "",
            "city": profile.city or "",
            "state": profile.state or "",
            "country": profile.country or "",
            "postal_code": profile.postal_code or "",
            "profile_photo": profile.profile_photo or "",
            "cover_photo": profile.cover_photo or "",
            "facebook": profile.facebook or "",
            "twitter": profile.twitter or "",
            "linkedin": profile.linkedin or "",
            "website": profile.website or "",
            "joined_date": user.user_registered
        }

    @staticmethod
    def format_instructor_profile_response(user: User, instructor_profile: InstructorProfile, db: Session = None) -> Dict[str, Any]:
        """
        Format instructor profile data for API response.

        Fix round 1 (A4 fallout): this used to read .bio/.expertise/
        .experience/.education/.certifications/.social_links/.status —
        none of those columns exist on InstructorProfile
        (models/user.py:104-131) — AttributeError 500 on every call once
        apply-instructor started succeeding and made this endpoint
        reachable. Mapped to the real columns below; fields with no
        backing column return stable empties ([]/""/{}) so the response
        schema (InstructorProfileResponse) stays satisfied.

        PRODUCT GAP: InstructorApplicationRequest requires expertise/
        experience/education/certifications/social_links on submission,
        but InstructorProfile has no columns to store any of them — that
        data is accepted, then silently dropped (see users.py's
        apply_for_instructor). Needs a migration to add these columns;
        deliberately not added on this branch per ruling — flagged in
        the fix-wave report/ledger as a product gap instead.
        """
        try:
            rating = float(instructor_profile.instructor_rating) if instructor_profile.instructor_rating else None
        except (TypeError, ValueError):
            rating = None

        total_students = 0
        total_courses = 0
        if db is not None:
            from app.models.course import Course
            courses = db.query(Course).filter(Course.post_author == user.id).all()
            total_courses = len(courses)
            total_students = sum(c.total_enrollments or 0 for c in courses)

        return {
            "id": instructor_profile.id,
            "user_id": user.id,
            "bio": instructor_profile.instructor_bio or "",
            # No backing column (product gap — see docstring): stable empties.
            "expertise": [],
            "experience": "",
            "education": [],
            "certifications": [],
            "social_links": {},
            "status": "approved" if instructor_profile.is_approved else "pending",
            "rating": rating,
            "total_students": total_students,
            "total_courses": total_courses,
            "created_at": instructor_profile.created_at
        }

    @staticmethod
    async def save_avatar(file: UploadFile, user_id: int) -> str:
        """
        Save user avatar and return URL
        """
        # Write under the configured, absolute UPLOAD_DIR (default /app/uploads,
        # the bind-mounted dir nginx serves at /uploads/). Using a relative
        # "uploads/avatars" here resolved against the process CWD, so the file
        # could land outside the served directory and every avatar 404'd — the
        # rest of the app (course images, etc.) already uses settings.UPLOAD_DIR.
        from app.core.config import get_settings
        upload_dir = os.path.join(get_settings().UPLOAD_DIR, "avatars")
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"{user_id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)

        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Return URL path
        return f"/uploads/avatars/{filename}"

    @staticmethod
    def update_instructor_stats(db: Session, instructor_id: int):
        """
        Update instructor statistics (total courses, students, etc.)
        """
        from models.course import Course

        instructor_profile = db.query(InstructorProfile).filter(
            InstructorProfile.user_id == instructor_id
        ).first()

        if instructor_profile:
            courses = db.query(Course).filter(
                Course.post_author == instructor_id
            ).all()

            instructor_profile.total_courses = len(courses)
            instructor_profile.total_students = sum([c.total_enrollments or 0 for c in courses])

            db.commit()

    @staticmethod
    def calculate_instructor_rating(db: Session, instructor_id: int) -> float:
        """
        Calculate instructor's average rating based on course ratings
        """
        from models.course import Course

        courses = db.query(Course).filter(
            Course.instructor_id == instructor_id,
            Course.course_status == "published"
        ).all()

        if not courses:
            return 0.0

        total_rating = sum([c.course_rating or 0 for c in courses])
        return total_rating / len(courses)

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User:
        """
        Get user by email address
        """
        return db.query(User).filter(User.user_email == email).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User:
        """
        Get user by username
        """
        return db.query(User).filter(User.user_login == username).first()

    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        """
        Deactivate a user account
        """
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.user_status = "inactive"
            db.commit()
            return True
        return False

    @staticmethod
    def promote_to_instructor(db: Session, user_id: int) -> bool:
        """
        Promote a user to instructor role.

        Fix round 1 (A4 fallout): used to set instructor_profile.status =
        "approved" — no such column on InstructorProfile
        (models/user.py:104-131) — silently dropped, never persisted.
        The real approval flag is is_approved (Boolean).
        """
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.role == "student":
            user.role = "instructor"

            # Update instructor profile approval if a profile row exists
            instructor_profile = db.query(InstructorProfile).filter(
                InstructorProfile.user_id == user_id
            ).first()

            if instructor_profile:
                instructor_profile.is_approved = True

            db.commit()
            return True
        return False