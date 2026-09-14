"""
User Management Router - SashaInfinity LMS API
Handles user profiles, instructor applications, and user data management
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
import logging
import re

from app.core.database import get_db
from app.models.user import User, UserProfile, InstructorProfile
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderItem, OrderStatus
from app.services.auth_service import AuthService
from app.services.course_service import CourseService
from app.services.user_service import UserService
from app.schemas.user import (
    UserProfileUpdate,
    UserProfileResponse,
    InstructorApplicationRequest,
    InstructorProfileResponse,
    UserStatsResponse
)

router = APIRouter()

@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information
    """
    print(f"[DEBUG] get_user_profile: current_user.id={current_user.id}, email={current_user.user_email}, display_name={current_user.display_name}")
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    print(f"[DEBUG] profile query result: user_id={profile.user_id if profile else None}, first_name={profile.first_name if profile else None}")

    if not profile:
        # Create default profile if not exists
        profile = UserProfile(
            user_id=current_user.id,
            first_name="",
            last_name="",
            phone="",
            description="",
            profile_photo=""
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return UserService.format_user_profile_response(current_user, profile)

@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile
    """
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    # Update profile fields
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "social_links" and value:
            profile.social_links = value
        elif hasattr(profile, field):
            setattr(profile, field, value)

    # Update user display name if first/last name provided
    if profile_data.first_name and profile_data.last_name:
        current_user.display_name = f"{profile_data.first_name} {profile_data.last_name}"

    # Mark profile as completed if mandatory fields are filled
    # Mandatory fields: first_name, last_name, phone
    if (profile.first_name and profile.last_name and profile.phone):
        current_user.profile_completed = True
        print(f"✅ Profile completed for user: {current_user.user_email}")

    db.commit()
    db.refresh(profile)

    return UserService.format_user_profile_response(current_user, profile)

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload user avatar image. Accepts all image formats up to 15MB.
    """
    # Read file content to check size
    file_content = await file.read()
    await file.seek(0)  # Reset file pointer

    # Validate file size (15MB = 15 * 1024 * 1024 bytes)
    max_size = 15 * 1024 * 1024
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size must be less than 15MB. Uploaded file: {len(file_content) / (1024*1024):.2f}MB"
        )

    # Validate file type (accept all image types)
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    # Save file and get URL
    avatar_url = await UserService.save_avatar(file, current_user.id)

    # Update user profile
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    profile.profile_photo = avatar_url
    db.commit()
    db.refresh(profile)

    return {"avatar_url": avatar_url}


@router.delete("/avatar")
async def remove_avatar(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove user avatar (set profile_photo to empty string)
    """
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()

    if profile:
        # Store old URL for potential cleanup
        old_avatar = profile.profile_photo
        profile.profile_photo = ""
        db.commit()

        # Optionally delete the old file
        if old_avatar:
            import os
            file_path = old_avatar.lstrip('/')
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to delete avatar file {file_path}: {e}")

    return {"message": "Avatar removed successfully"}

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user statistics (enrolled courses, completed courses, etc.)
    """
    logging.info(f"[USERS_STATS] user_id={current_user.id}, role={current_user.role}")

    if current_user.role == "student":
        enrollments = db.query(Enrollment).filter(
            Enrollment.user_id == current_user.id
        ).all()

        enrolled_courses = len(enrollments)
        completed_courses = len([e for e in enrollments if e.completion_date])
        in_progress_courses = enrolled_courses - completed_courses

        return {
            "role": current_user.role,
            "enrolled_courses": enrolled_courses,
            "completed_courses": completed_courses,
            "in_progress_courses": in_progress_courses,
            "certificates_earned": completed_courses
        }

    elif current_user.role == "instructor":
        courses = db.query(Course).filter(
            Course.post_author == current_user.id
        ).all()

        total_students = sum([c.total_enrollments or 0 for c in courses])
        # Support both uppercase and lowercase status values
        published_courses = len([c for c in courses if c.post_status in ["publish", "PUBLISH", "published", "PUBLISHED"]])

        # Real money received for this instructor's courses: the per-course line
        # total on COMPLETED orders, which is net of any coupon discount.
        # Previously this was list_price × enrollment_count, which ignored
        # coupons, sale prices and free/comped enrollments alike.
        course_ids = [c.id for c in courses]
        total_revenue = 0.0
        if course_ids:
            total_revenue = float(
                db.query(func.sum(OrderItem.total))
                .join(Order, OrderItem.order_id == Order.id)
                .filter(
                    OrderItem.course_id.in_(course_ids),
                    Order.order_status == OrderStatus.COMPLETED,
                )
                .scalar() or 0
            )

        return {
            "role": current_user.role,
            "total_courses": len(courses),
            "published_courses": published_courses,
            "draft_courses": len(courses) - published_courses,
            "total_students": total_students,
            "total_revenue": total_revenue
        }

    elif current_user.role == "spoc":
        from app.models.internship import Internship, InternshipVoucher

        # Count internships where this user is the SPOC
        my_internships = db.query(Internship).filter(Internship.spoc_user_id == current_user.id).count()

        # Get internship IDs for this SPOC
        internship_ids = [i[0] for i in db.query(Internship.id).filter(Internship.spoc_user_id == current_user.id).all()]

        # Count vouchers for this SPOC's internships
        vouchers_redeemed = 0
        pending_interns = 0

        if internship_ids:
            vouchers_redeemed = db.query(InternshipVoucher).filter(
                InternshipVoucher.internship_id.in_(internship_ids),
                InternshipVoucher.status == 'redeemed'
            ).count()

            pending_interns = db.query(InternshipVoucher).filter(
                InternshipVoucher.internship_id.in_(internship_ids),
                InternshipVoucher.status == 'issued'
            ).count()

        result = {
            "role": current_user.role,
            "my_internships": my_internships,
            "vouchers_redeemed": vouchers_redeemed,
            "pending_interns": pending_interns
        }
        logging.info(f"[USERS_STATS] SPOC user_id={current_user.id}, result={result}")
        return result

    else:  # admin
        total_users = db.query(User).count()
        total_courses = db.query(Course).count()
        total_enrollments = db.query(Enrollment).count()

        return {
            "role": current_user.role,
            "total_users": total_users,
            "total_courses": total_courses,
            "total_enrollments": total_enrollments,
            "active_users": db.query(User).filter(User.is_active.is_(True)).count()
        }

# Instructor Application Endpoints

@router.post("/apply-instructor")
async def apply_for_instructor(
    application: InstructorApplicationRequest,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Apply to become an instructor
    """
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only students can apply to become instructors"
        )

    # Check if already applied
    existing_profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == current_user.id
    ).first()

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instructor application already submitted"
        )

    # Create instructor profile
    # NOTE: InstructorProfile (models/user.py:104-132) only has instructor_bio /
    # instructor_designation / is_approved / is_blocked / earning_* columns —
    # expertise/experience/education/certifications/social_links have no
    # backing columns and are intentionally dropped (not persisted).
    instructor_profile = InstructorProfile(
        user_id=current_user.id,
        instructor_bio=application.bio,
        is_approved=False,
    )

    db.add(instructor_profile)
    db.commit()

    return {"message": "Instructor application submitted successfully. We will review your application and get back to you."}

@router.get("/instructor-profile", response_model=InstructorProfileResponse)
async def get_instructor_profile(
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db)
):
    """
    Get instructor profile information
    """
    instructor_profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == current_user.id
    ).first()

    if not instructor_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor profile not found"
        )

    return UserService.format_instructor_profile_response(current_user, instructor_profile, db)

@router.get("/my-courses")
async def get_my_courses(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get courses based on user role (enrolled courses for students, created courses for instructors)
    """
    if current_user.role == "student":
        enrollments = db.query(Enrollment).options(
            joinedload(Enrollment.course).joinedload(Course.instructor).joinedload(User.profile),
            joinedload(Enrollment.course).joinedload(Course.lessons),
            joinedload(Enrollment.course).joinedload(Course.quizzes),
            joinedload(Enrollment.course).joinedload(Course.assignments),
        ).filter(Enrollment.user_id == current_user.id).all()

        results = []
        for enrollment in enrollments:
            course = enrollment.course
            if not course:
                continue

            results.append(
                CourseService.format_course_response(
                    course,
                    is_enrolled=True,
                    enrollment=enrollment,
                    db=db,
                )
            )
        return results

    elif current_user.role in ["instructor", "admin"]:
        courses = db.query(Course).options(
            joinedload(Course.instructor).joinedload(User.profile),
            joinedload(Course.lessons),
            joinedload(Course.quizzes),
            joinedload(Course.assignments),
        ).filter(Course.post_author == current_user.id).all()

        return [
            CourseService.format_course_response(course, is_enrolled=True, db=db)
            for course in courses
        ]

    return []


@router.get("/instructors/top")
async def get_top_instructors(
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    Get top instructors based on course count and ratings (public endpoint)
    """
    from sqlalchemy import func
    from app.models.instructor_review import InstructorReview

    # Get instructors with their course counts and average ratings
    instructors_query = db.query(
        User.id,
        User.display_name,
        User.user_email,
        UserProfile.profile_photo,
        UserProfile.description,
        UserProfile.designation,
        InstructorProfile.instructor_bio,
        InstructorProfile.instructor_designation,
        func.count(func.distinct(Course.id)).label('course_count'),
        func.coalesce(func.avg(InstructorReview.rating), 0).label('avg_rating')
    ).join(
        UserProfile, User.id == UserProfile.user_id, isouter=True
    ).join(
        InstructorProfile, User.id == InstructorProfile.user_id, isouter=True
    ).join(
        Course, User.id == Course.post_author, isouter=True
    ).join(
        InstructorReview, User.id == InstructorReview.instructor_id, isouter=True
    ).filter(
        User.role == "instructor"
    ).group_by(
        User.id,
        User.display_name,
        User.user_email,
        UserProfile.profile_photo,
        UserProfile.description,
        UserProfile.designation,
        InstructorProfile.instructor_bio,
        InstructorProfile.instructor_designation
    ).having(
        func.count(func.distinct(Course.id)) > 0  # only instructors who actually have courses
    ).order_by(
        func.count(func.distinct(Course.id)).desc(),
        func.avg(InstructorReview.rating).desc()
    ).limit(limit).all()

    return [
        {
            "id": instructor.id,
            "name": instructor.display_name,
            "email": instructor.user_email,
            "profile_photo": instructor.profile_photo or "https://ui-avatars.com/api/?name=" + instructor.display_name.replace(" ", "+"),
            "description": instructor.description or instructor.instructor_bio or "Experienced instructor",
            "expertise": instructor.instructor_designation or instructor.designation or "Instructor",
            "course_count": instructor.course_count,
            "rating": round(float(instructor.avg_rating), 1) if instructor.avg_rating else 0.0
        }
        for instructor in instructors_query
    ]
def _slugify(name: str) -> str:
    """Match the frontend slugify: lowercase, non-alphanumerics -> hyphen."""
    s = (name or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"^-+|-+$", "", s)


@router.get("/instructors/{instructor_ref}")
async def get_instructor_by_id(
    instructor_ref: str,
    db: Session = Depends(get_db)
):
    """Get public instructor profile by numeric id or name-slug, with real stats."""
    from app.models.course import Course

    if instructor_ref.isdigit():
        user = db.query(User).filter(User.id == int(instructor_ref)).first()
    else:
        # Resolve a name-slug (e.g. "saran-thiyagu") to the instructor. On a
        # slug collision the lowest id wins.
        candidates = (
            db.query(User)
            .filter(User.role.in_(["instructor", "admin"]))
            .order_by(User.id)
            .all()
        )
        user = next((u for u in candidates if _slugify(u.display_name) == instructor_ref), None)

    if not user:
        raise HTTPException(status_code=404, detail="Instructor not found")

    instructor_id = user.id

    # Get both user profile and instructor profile
    user_profile = db.query(UserProfile).filter(
        UserProfile.user_id == instructor_id
    ).first()

    instructor_profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == instructor_id
    ).first()

    # Real stats from DB
    courses = db.query(Course).filter(Course.post_author == instructor_id).all()
    total_courses = len(courses)
    total_students = sum([c.total_enrollments or 0 for c in courses])

    return {
        "id": user.id,
        "display_name": user.display_name,
        "user_email": user.user_email,
        "profile": {
            "profile_photo": user_profile.profile_photo if user_profile else None,
            "bio": instructor_profile.instructor_bio if instructor_profile else (user_profile.description if user_profile else ""),
            "expertise": "[]",
            "experience": instructor_profile.instructor_designation if instructor_profile else (user_profile.designation if user_profile else ""),
            "rating": float(instructor_profile.instructor_rating or 0) if instructor_profile else 0.0,
            "social_links": {
                "website": user_profile.website if user_profile else "",
                "facebook": user_profile.facebook if user_profile else "",
                "twitter": user_profile.twitter if user_profile else "",
                "linkedin": user_profile.linkedin if user_profile else ""
            }
        },
        "total_courses": total_courses,
        "total_students": total_students,
        "total_reviews": 0,
        "average_rating": float(instructor_profile.instructor_rating or 0) if instructor_profile else 0.0
    }


@router.get("/public/{username}")
async def get_public_profile(
    username: str,
    db: Session = Depends(get_db)
):
    """
    Public, READ-ONLY profile lookup by username (user_login).

    Unauthenticated and intentionally separate from the protected `/profile`
    route, so a shared link like /u/<username> opens for anyone. Returns only
    public-safe fields — private contact details (phone, address, postal code,
    and email unless the user opted in via show_email) are never exposed.
    """
    user = db.query(User).filter(User.user_login.ilike(username)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = db.query(UserProfile).filter(
        UserProfile.user_id == user.id
    ).first()
    instructor_profile = db.query(InstructorProfile).filter(
        InstructorProfile.user_id == user.id
    ).first()

    # Public stats: teaching metrics for instructors/admins, enrolled count for
    # learners. Wrapped defensively so a stats hiccup never 500s the page.
    stats = {}
    try:
        if user.role in ("instructor", "admin"):
            courses = db.query(Course).filter(Course.post_author == user.id).all()
            stats = {
                "courses": len(courses),
                "students": sum([c.total_enrollments or 0 for c in courses]),
                "rating": float(instructor_profile.instructor_rating or 0) if instructor_profile else 0.0,
            }
        else:
            stats = {
                "courses": db.query(Enrollment).filter(
                    Enrollment.user_id == user.id
                ).count(),
            }
    except Exception:
        stats = {}

    location = ", ".join(
        p for p in [
            (profile.city if profile else "") or "",
            (profile.country if profile else "") or "",
        ] if p
    )

    return {
        "username": user.user_login,
        "display_name": user.display_name,
        "role": user.role,
        "profile_photo": (profile.profile_photo if profile else "") or "",
        "cover_photo": (profile.cover_photo if profile else "") or "",
        "designation": (profile.designation if profile else "")
            or (instructor_profile.instructor_designation if instructor_profile else ""),
        "bio": (profile.description if profile else "")
            or (instructor_profile.instructor_bio if instructor_profile else ""),
        "location": location,
        # Email only if the user explicitly opted to show it.
        "email": user.user_email if (profile and profile.show_email) else "",
        "joined_date": user.user_registered,
        "social_links": {
            "website": (profile.website if profile else "") or "",
            "facebook": (profile.facebook if profile else "") or "",
            "twitter": (profile.twitter if profile else "") or "",
            "linkedin": (profile.linkedin if profile else "") or "",
        },
        "stats": stats,
    }
