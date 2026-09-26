"""
Course Management Router - SashaInfinity LMS API
Handles course CRUD operations, enrollment, and progress tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Body, Request, Response, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import json
import logging
import time

# Get logger for this module
logger = logging.getLogger(__name__)

from app.core.cache_headers import apply_public_cache
from app.core.database import get_db
from app.core.firebase_admin import send_course_event
from app.models.user import User, UserProfile
from app.models.course import Course, Lesson, CourseReview, CourseCategory
from app.core.course_types import DEFAULT_COURSE_TYPE, normalize_course_type
from app.models.quiz import Quiz
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.h5p import H5PContent
from app.models.game import Game
from app.models.enrollment import (
    Enrollment,
    LessonProgress,
    StudentCourseActivity,
    WatchSession,
    CourseAnnouncement,
    WishlistItem,
)
from app.models.quiz import QuizAttempt
from app.models.instructor_review import InstructorReview
from app.models.payment import OrderItem, Earning
from app.models.certificate import IssuedCertificate, CourseCertificate
from app.models.coupon import CouponCourseRestriction
from app.models.internship import InternshipVoucher
from app.models.cohort import Cohort
from pydantic import BaseModel, Field
from datetime import timezone
from sqlalchemy import or_
from app.services.auth_service import AuthService
from app.services.course_access import can_edit
from app.services.course_service import (
    CourseService,
    build_default_slug,
    ensure_slug,
    generate_unique_slug,
)
from app.routers.video import extract_video_id
from app.utils.email import send_enrollment_confirmation_email


async def send_enrollment_confirmation_email_safely(
    email: str, user_name: str, course_title: str, course_id: int
):
    """Background-task wrapper: log the outcome, never raise into the response."""
    try:
        await send_enrollment_confirmation_email(
            email=email,
            user_name=user_name,
            course_title=course_title,
            course_id=course_id,
        )
        logger.info(
            "Enrollment confirmation email sent to %s for course %s",
            email, course_title,
        )
    except Exception as email_err:
        logger.warning(
            "Failed to send enrollment confirmation email to %s: %s",
            email, email_err,
        )
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseListResponse,
    PaginatedCoursesResponse,
    LessonCreate,
    LessonUpdate,
    LessonResponse,
    EnrollmentResponse,
    CourseProgressResponse
)

router = APIRouter()
PUBLISHED_STATUSES = ["publish", "published", "PUBLISH", "PUBLISHED"]

# Course Management Endpoints

@router.get("/", response_model=PaginatedCoursesResponse)
async def get_courses(
    request: Request,
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    course_type: Optional[str] = None,
    level: Optional[str] = None,
    price_type: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "latest",
    status: Optional[str] = "publish",
    instructor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user)
):
    """
    Get list of courses with filtering and pagination
    """
    apply_public_cache(request, response, s_maxage=60, swr=600)
    query = db.query(Course).options(
        joinedload(Course.instructor).joinedload(User.profile),
        joinedload(Course.categories),
        joinedload(Course.lessons),
        joinedload(Course.quizzes)
    )

    # Apply filters
    if status:
        if status.lower() in ("publish", "published"):
            query = query.filter(Course.post_status.in_(PUBLISHED_STATUSES))
        else:
            query = query.filter(Course.post_status == status)

    if instructor_id:
        query = query.filter(Course.post_author == instructor_id)
    if course_type:
        # One of the three canonical types; unknown values match nothing
        # rather than silently listing everything.
        query = query.filter(Course.course_type == course_type.strip().lower())
    if category:
        # Both sides are normalised to a lowercase hyphenated slug so the home
        # CategoriesSection, the dedicated category pages (Meiporul/
        # Seyappaduporul/Utporul), and the catalog dropdown — which variously
        # query with "data analytics" or "data-analytics" — all match courses
        # whose course_category was saved capitalized/spaced by the instructor
        # form.
        query = query.filter(
            func.replace(func.lower(func.trim(Course.course_category)), " ", "-")
            == category.strip().lower().replace(" ", "-")
        )

    if level:
        query = query.filter(func.lower(Course.course_level) == level.strip().lower())

    if price_type:
        if price_type == "free":
            query = query.filter(Course.course_price == 0)
        elif price_type == "paid":
            query = query.filter(Course.course_price > 0)

    if search:
        # ilike, not contains(): contains() emits LIKE, which is case-sensitive
        # on Postgres and made search miss anything not typed in exact case.
        term = f"%{search.strip()}%"
        # v2.0 §3 emergent taxonomy: expand the term across its tag cluster so
        # 'trig' finds courses tagged trigonometry / Trigonometry / maths-trig.
        from sqlalchemy import or_
        conds = [Course.post_title.ilike(term), Course.post_content.ilike(term), Course.course_tags.ilike(term)]
        try:
            from app.services.tag_service import expand_query
            for t in expand_query(db, search)[:50]:
                conds.append(Course.course_tags.ilike(f'%"{t}"%'))
        except Exception:
            db.rollback()
        query = query.filter(or_(*conds))

    # Get total count for pagination
    total = query.count()

    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size  # Ceiling division

    # A deterministic ORDER BY is required before OFFSET/LIMIT: without one the
    # planner may return rows in a different order per query as the offset grows,
    # which duplicated some courses across pages and hid others entirely.
    # Course.id is the tiebreaker so every sort is total.
    sort_key = (sort or "latest").strip().lower()
    if sort_key == "popular":
        order_by = [Course.total_enrollments.desc().nulls_last(), Course.id.desc()]
    elif sort_key == "rating":
        order_by = [Course.average_rating.desc().nulls_last(), Course.id.desc()]
    elif sort_key == "price-low":
        order_by = [Course.course_price.asc().nulls_first(), Course.id.desc()]
    elif sort_key == "price-high":
        order_by = [Course.course_price.desc().nulls_last(), Course.id.desc()]
    else:  # "latest" and any unrecognised value
        order_by = [Course.created_at.desc().nulls_last(), Course.id.desc()]
    query = query.order_by(*order_by)

    # Apply pagination
    courses = query.offset(skip).limit(page_size).all()

    # Check enrollment status for authenticated users
    enrolled_course_ids = set()
    if current_user:
        enrollments = db.query(Enrollment).filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id.in_([c.id for c in courses])
        ).all()
        enrolled_course_ids = {e.course_id for e in enrollments if e.enrollment_status not in ['cancelled', 'suspended']}

    courses_data = [
        {
            "id": course.id,
            "slug": course.post_name or build_default_slug(course),
            "title": course.post_title,
            "description": (course.post_content or "")[:200] + "..." if len(course.post_content or "") > 200 else (course.post_content or ""),
            "featured_image": course.course_thumbnail or "",
            # Listings always show the real price (even to admins) so browse/detail
            # stay consistent. Admin free-access is applied at checkout, not here.
            "price": float(course.course_price) if course.course_price else 0,
            # align with pricing.is_on_sale() after merge
            "sale_price": float(course.course_sale_price) if course.course_sale_price and 0 < course.course_sale_price < (course.course_price or 0) else None,
            "level": course.course_level or "beginner",
            "category": course.course_category or "Course",
            "course_type": course.course_type or course.course_category or "",
            "instructor": {
                "id": course.instructor.id if course.instructor else 0,
                "name": course.instructor.display_name if course.instructor else "Unknown Instructor",
                "avatar": course.instructor.profile.profile_photo if course.instructor and course.instructor.profile else None
            },
            "stats": {
                "lessons": len(course.lessons),
                "quizzes": len(course.quizzes),
                "duration": sum([int(lesson.lesson_video_duration or 0) for lesson in course.lessons]),
                "students": course.total_enrollments or 0,
                "video_views": course.video_view_count or 0
            },
            "rating": course.average_rating or 0,
            "is_enrolled": course.id in enrolled_course_ids,
            "num_offline_workshops": course.num_offline_workshops or 0,
            "num_hours": course.num_hours or 0,
            "institution": course.institution or "",
            "created_at": course.created_at,
            "updated_at": course.updated_at
        }
        for course in courses
    ]

    return {
        "courses": courses_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.post("/{course_id}/lessons/{lesson_id}/view")
async def record_lesson_view(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """
    Record that a student opened/watched a lesson video in a course.

    Increments the course's `video_view_count` so the Admin -> Courses panel
    can report "how many times each course/video was viewed". Idempotent per
    request — the frontend calls this once when a video starts playing.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id, Lesson.post_parent == course_id
    ).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found in this course",
        )

    course.video_view_count = (course.video_view_count or 0) + 1
    db.commit()
    return {
        "success": True,
        "video_view_count": course.video_view_count,
    }


@router.get("/my-courses")
async def get_my_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get courses created by the current instructor with pagination
    """
    # Query courses where the current user is the author
    from app.services.course_access import collaborated_course_ids
    query = db.query(Course).filter(
        or_(Course.post_author == current_user.id, Course.id.in_(collaborated_course_ids(db, current_user.id)))
    ).order_by(Course.created_at.desc())

    # Get total count
    total = query.count()

    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size

    # Get paginated results
    courses = query.offset(skip).limit(page_size).all()

    return {
        "courses": [
            {
                "id": course.id,
                "slug": course.post_name or build_default_slug(course),
                "post_title": course.post_title,
                "post_excerpt": course.post_excerpt,
                "course_thumbnail": course.course_thumbnail,
                "course_price": float(course.course_price) if course.course_price else 0,
                "course_sale_price": float(course.course_sale_price) if course.course_sale_price else None,
                "course_level": course.course_level,
                "course_duration": course.course_duration,
                "course_category": course.course_category,
                "course_type": course.course_type or "",
                "post_status": course.post_status,
                "total_enrollments": course.total_enrollments or 0,
                "average_rating": float(course.average_rating) if course.average_rating else 0,
                "video_view_count": course.video_view_count or 0,
                "created_at": course.created_at.isoformat() if course.created_at else None,
                "updated_at": course.updated_at.isoformat() if course.updated_at else None
            }
            for course in courses
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/checkout-info")
async def get_course_checkout_info(
    course_id: int = Query(..., description="Course ID"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user)
):
    """
    Get checkout information for a course
    Returns course details needed for checkout page (price, is_enrolled, etc.)
    """
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check if user is enrolled
    is_enrolled = False
    if current_user:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == current_user.id
        ).first()
        is_enrolled = enrollment is not None and enrollment.enrollment_status not in ['cancelled', 'suspended']

    # Check if user has free access based on role (admin/super_admin)
    is_free_user = current_user and current_user.role in ['admin', 'super_admin']

    return {
        "course_id": course.id,
        "title": course.post_title,
        "thumbnail": course.course_thumbnail,
        "price": 0.0 if is_free_user else (float(course.course_price) if course.course_price else 0),
        # align with pricing.is_on_sale() after merge
        "sale_price": None if is_free_user else (float(course.course_sale_price) if course.course_sale_price and 0 < course.course_sale_price < (course.course_price or 0) else None),
        "is_free": is_free_user or course.course_price == 0,
        "level": course.course_level,
        "duration": course.course_duration,
        "is_enrolled": is_enrolled,
        "instructor": {
            "id": course.instructor.id if course.instructor else None,
            "name": course.instructor.display_name if course.instructor else "Unknown",
            "avatar": course.instructor.profile.profile_photo if course.instructor and course.instructor.profile else None
        } if course.instructor else None
    }

# NOTE: this literal route MUST stay above @router.get("/{course_ref}").
# FastAPI matches in registration order and course_ref is a str, so while
# /pending sat below it every request was answered by get_course(), which
# looked for a course whose slug is literally "pending" and returned 404.
@router.get("/pending", response_model=List[CourseListResponse])
async def get_pending_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get all pending courses awaiting admin approval (admin only)
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view pending courses"
        )

    courses = db.query(Course).options(
        joinedload(Course.instructor).joinedload(User.profile),
        joinedload(Course.lessons),
        joinedload(Course.quizzes)
    ).filter(Course.post_status == "pending").all()

    # Special user with free access to all courses (admin view, so no price override needed)
    return [
        {
            "id": course.id,
            "slug": course.post_name or build_default_slug(course),
            "title": course.post_title,
            "description": course.post_content[:200] + "..." if len(course.post_content) > 200 else course.post_content,
            "featured_image": course.course_thumbnail,
            "price": float(course.course_price) if course.course_price else 0,
            "level": course.course_level,
            "category": course.course_category,
            "course_type": course.course_type or course.course_category or "",
            "instructor": {
                "id": course.instructor.id,
                "name": course.instructor.display_name,
                "avatar": course.instructor.profile.profile_photo if course.instructor and course.instructor.profile else None
            },
            "stats": {
                "lessons": len(course.lessons),
                "quizzes": len(course.quizzes),
                "duration": sum([int(lesson.lesson_video_duration or 0) for lesson in course.lessons]),
                "students": course.total_enrollments or 0
            },
            "rating": course.average_rating or 0,
            "created_at": course.created_at,
            "updated_at": course.updated_at
        }
        for course in courses
    ]

# Lesson Management


@router.get('/slug-availability')
def course_slug_availability(slug: str, exclude_course_id: Optional[int] = None,
                             db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    from app.core.course_links import validate_course_slug
    from app.services.course_service import _slug_is_unique
    if user.role not in ('instructor', 'admin', 'superadmin'):
        raise HTTPException(403, 'Teaching-staff access required.')
    if exclude_course_id:
        course = db.get(Course, exclude_course_id)
        if not course or not can_edit(db, course, user):
            raise HTTPException(403, 'You cannot edit this course link.')
    try:
        normalized = validate_course_slug(slug)
        if not normalized: raise ValueError('Enter a course link to check.')
    except ValueError as exc:
        return {'available': False, 'slug': slug, 'message': str(exc)}
    available = _slug_is_unique(db, normalized, exclude_course_id)
    return {'available': available, 'slug': normalized, 'message': 'Available' if available else 'This course link is already in use.'}


@router.get("/{course_ref}", response_model=CourseResponse)
async def get_course(
    course_ref: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user)
):
    """
    Get detailed course information.

    `course_ref` accepts either a numeric id (legacy URLs `/courses/10`) or a
    slug (`/courses/python-for-beginners-10`). Numeric refs are looked up by
    id; non-numeric refs are looked up by `post_name`.
    """
    base_query = db.query(Course).options(
        joinedload(Course.instructor).joinedload(User.profile),
        joinedload(Course.quizzes),
        joinedload(Course.enrollments)
    )

    course = None
    # Try numeric id first (backward-compat with /courses/10)
    if course_ref.isdigit():
        try:
            course = base_query.filter(Course.id == int(course_ref)).first()
        except Exception:
            course = None

    # Fall back to slug lookup
    if not course:
        course = base_query.filter(func.lower(Course.post_name) == course_ref.lower()).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Back-compat: existing courses with empty post_name get one persisted
    # on first read. Best-effort — failure is swallowed inside ensure_slug.
    if not course.post_name:
        ensure_slug(db, course)

    course_id = course.id

    # Check access permissions for non-published courses
    # SashaInfinity LMS uses mixed published status values across import/admin paths.
    if course.post_status not in PUBLISHED_STATUSES:
        # Only allow access if user is admin or the course instructor
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This course is not yet published"
            )

        is_admin = current_user.role == "admin"
        is_instructor = current_user.id == course.post_author

        if not (is_admin or is_instructor):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This course is not yet published"
            )

    # Course.lessons already maps to Lesson.post_parent (the FK) and is ordered
    # by menu_order, so it resolves to exactly this query on access. The manual
    # re-assignment that used to live here wrote back into a
    # cascade="all, delete-orphan" collection — anything absent from the
    # assigned list would have been deleted on the next flush — and printed a
    # line per lesson on every course view. Both removed; the relationship is
    # loaded lazily below.

    # Check if user is enrolled
    is_enrolled = False
    enrollment = None
    if current_user:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == current_user.id
        ).first()
        is_enrolled = enrollment is not None and enrollment.enrollment_status not in ['cancelled', 'suspended']

    # Public-preview lock (2026-09-05): visitors and non-enrolled learners get
    # locked lessons stripped of media; owner/admin keep everything (editor).
    full_access = is_enrolled or bool(current_user and (current_user.role in ("admin", "superadmin") or current_user.id == course.post_author))
    return CourseService.format_course_response(course, is_enrolled, enrollment, db, full_access=full_access)

@router.get("/tools/resolved/{course_id}")
async def get_resolved_tools(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    """v2.0: effective tools = type profile defaults + course additions
    (the "Add more tools" escape hatch — defaults, not walls)."""
    from app.core.course_types import TOOL_AVAILABILITY, TYPE_CAPABILITIES
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    ctype = (course.course_type or "").lower()
    meta = TYPE_CAPABILITIES.get(ctype, {})
    defaults = list(meta.get("capabilities", []))
    additions = list(course.enabled_tools or [])
    resolved = sorted(set(defaults) | set(a for a in additions if isinstance(a, str)))
    return {
        "course_id": course_id,
        "type": ctype,
        "tools": [{"tool": t, "availability": TOOL_AVAILABILITY.get(t, "planned"),
                   "source": "default" if t in defaults else "added"} for t in resolved],
    }


@router.post("/tools/{course_id}")
async def add_tool(
    course_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    from app.core.course_types import COURSE_TYPES
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_edit(db, course, current_user):
        raise HTTPException(status_code=403, detail="Not your course")
    tool = (payload.get("tool") or "").strip()
    if not tool:
        raise HTTPException(status_code=422, detail="tool is required")
    enabled = list(course.enabled_tools or [])
    if tool not in enabled:
        enabled.append(tool)
        course.enabled_tools = enabled
        db.commit()
    return {"course_id": course_id, "enabled_tools": enabled}


@router.post("/", response_model=CourseResponse)
async def create_course(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Create a new course (instructor only)
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🎓 Creating course: {course_data.title} by user {current_user.id}")

    # Review finding M1. Deliberately OUTSIDE the try below — that block
    # converts every exception into a 500, which would mask the 422.
    _validate_certificate_id(db, current_user, course_data.certificate_id)
    if current_user.role not in ('instructor', 'admin', 'superadmin'):
        raise HTTPException(403, 'Teaching-staff access required.')
    from app.services.course_service import _slug_is_unique
    if course_data.slug and not _slug_is_unique(db, course_data.slug):
        raise HTTPException(409, 'This course link is already in use.')

    try:
        # Create course with proper field names. post_name is assigned a
        # temporary value here; after the INSERT we know the id and can
        # regenerate a unique `<slug>-<id>` form.
        # Respect an explicitly chosen status when valid; otherwise fall back to
        # the role default (admins publish immediately, instructors start as draft).
        _allowed_status = {"publish", "draft", "pending", "private"}
        _requested_status = (getattr(course_data, "status", None) or "").strip().lower()
        _post_status = _requested_status if _requested_status in _allowed_status else (
            "publish" if current_user.role == "admin" else "draft"
        )

        new_course = Course(
            post_title=course_data.title,
            post_content=course_data.content or course_data.description,
            post_excerpt=course_data.excerpt or course_data.description or "",
            post_status=_post_status,
            post_author=course_data.instructor_id if (current_user.role == 'admin' and course_data.instructor_id) else current_user.id,
            post_name="",  # set after flush, once we have an id
            course_target_audience=getattr(course_data, "target_audience", None) or "",
            course_thumbnail=course_data.thumbnail or "",
            course_intro_video=course_data.intro_video or "",
            course_price=course_data.price,
            course_sale_price=course_data.sale_price if course_data.sale_price is not None else 0,
            course_level=course_data.level,
            course_category=course_data.category or "",
            course_type=normalize_course_type(course_data.course_type) or DEFAULT_COURSE_TYPE,
            course_language=course_data.language or "English",
            course_duration=str(course_data.duration) if course_data.duration else "0",
            course_requirements=json.dumps(course_data.requirements) if course_data.requirements else "[]",
            course_benefits=json.dumps(course_data.benefits) if course_data.benefits else "[]",
            num_offline_workshops=course_data.num_offline_workshops if course_data.num_offline_workshops is not None else 0,
            # Matches the model default — an omitted value means "standard
            # 60 offline hours", not zero.
            num_hours=course_data.num_hours if course_data.num_hours is not None else 60,
            institution=course_data.institution or "",
            certificate_template=str(course_data.certificate_id) if course_data.certificate_id else ""
        )

        db.add(new_course)
        db.flush()  # assigns id without committing the tx
        # Generate the final unique slug using the just-assigned id.
        new_course.post_name = course_data.slug or generate_unique_slug(
            db, course_data.title, course_id=new_course.id
        )
        db.commit()
        db.refresh(new_course)

        logger.info(f"✅ Course created successfully: ID={new_course.id}, slug={new_course.post_name}, Status={new_course.post_status}")
        return CourseService.format_course_response(new_course, False, None)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'A course with this link was just saved. Choose another link.')
    except Exception as e:
        logger.error(f"❌ Failed to create course: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create course: {str(e)}"
        )

# Handle requests without trailing slash by delegating to the main function
@router.post("", response_model=CourseResponse)
async def create_course_no_slash(
    course_data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Create a new course (instructor only) - handles requests without trailing slash
    """
    logger.info(f"🎓 Creating course (no slash): {course_data.title} by user {current_user.id}")
    return await create_course(course_data, db, current_user)

@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Update course (instructor/admin only)
    """
    import logging
    logger = logging.getLogger(__name__)

    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check permissions
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this course"
        )

    logger.info(f"📝 Updating course {course_id}: {course_data.title}")

    # Review finding M1. Deliberately OUTSIDE the try below — that block
    # converts every exception into a 500, which would mask the 422.
    if "certificate_id" in course_data.dict(exclude_unset=True):
        _validate_certificate_id(db, current_user, course_data.certificate_id)
    from app.services.course_service import _slug_is_unique
    if course_data.slug and not _slug_is_unique(db, course_data.slug, course_id):
        raise HTTPException(409, 'This course link is already in use.')

    try:
        # Update course fields
        update_data = course_data.dict(exclude_unset=True)
        custom_slug = update_data.pop('slug', None)
        if custom_slug:
            course.post_name = custom_slug

        # Certificate template chosen by the instructor. Stored as a string id
        # in Course.certificate_template; "" clears it (falls back to default).
        # Pop it so the generic loop below doesn't try to write an int into the
        # varchar column (which Postgres rejects).
        if "certificate_id" in update_data:
            cid = update_data.pop("certificate_id")
            course.certificate_template = str(cid) if cid else ""
            logger.info(f"  Updated certificate_template: {course.certificate_template!r}")

        # Field mapping from schema to database model
        field_mapping = {
            "title": "post_title",
            "description": "post_excerpt",
            "content": "post_content",
            "excerpt": "post_excerpt",
            "thumbnail": "course_thumbnail",
            "intro_video": "course_intro_video",
            "price": "course_price",
            "sale_price": "course_sale_price",
            "level": "course_level",
            "category": "course_category",
            "duration": "course_duration",
            "language": "course_language",
            "status": "post_status",
            "sections_meta": "course_sections_meta",
            "course_type": "course_type",
            "num_offline_workshops": "num_offline_workshops",
            "num_hours": "num_hours",
            "institution": "institution"
        }

        title_changed = False
        old_title = course.post_title
        for field, value in update_data.items():
            if field in ["requirements", "benefits", "faq", "tags"] and value is not None:
                setattr(course, f"course_{field}", json.dumps(value))
                logger.info(f"  Updated {field}: {type(value)}")
            elif field in field_mapping:
                setattr(course, field_mapping[field], value)
                logger.info(f"  Updated {field} -> {field_mapping[field]}: {value}")
                if field == "title" and value != old_title:
                    title_changed = True
            elif hasattr(course, f"course_{field}"):
                setattr(course, f"course_{field}", value)
                logger.info(f"  Updated course_{field}: {value}")

        # Published URLs remain stable when titles change.
        if not course.post_name and course.post_title:
            try:
                new_slug = generate_unique_slug(
                    db, course.post_title, course_id=course.id
                )
                course.post_name = new_slug
                logger.info(f"  Regenerated slug → {new_slug}")
            except Exception as slug_err:
                logger.warning(f"  Slug regeneration failed, keeping old: {slug_err}")

        db.commit()
        db.refresh(course)

        logger.info(f"✅ Course {course_id} updated successfully. Status: {course.post_status}")
        send_course_event(course_id, "updated")
        return CourseService.format_course_response(course, False, None)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'A course with this link was just saved. Choose another link.')
    except Exception as e:
        logger.error(f"❌ Failed to update course {course_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update course: {str(e)}"
        )

@router.delete("/{course_id}")
async def delete_course(
    course_id: int,
    force: str = Query(None, alias="force"),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    try:
        # Convert force parameter to boolean - handle both string and boolean cases
        force_delete = False
        if force is not None:
            if isinstance(force, str):
                force_delete = force.lower() in ['true', '1', 'yes', 'on']
            elif isinstance(force, bool):
                force_delete = force
            else:
                force_delete = bool(force)

        """
        Delete course (instructor/admin only)

        Args:
            course_id: ID of the course to delete
            force: If True (admin only), delete course even with enrollments and notify students

        Returns:
            Success message with deletion details
        """
        from app.models.enrollment import Enrollment
        from app.services.email_service import EmailService

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"🗑️ DELETE course called: course_id={course_id}, force_raw={force}, force_delete={force_delete}, user_role={current_user.role}, user_id={current_user.id}")
        logger.info(f"🔍 Force parameter details: raw='{force}', parsed={force_delete}, type={type(force)}, exists={force is not None}")

        course = db.query(Course).filter(Course.id == course_id).first()

        if not course:
            logger.warning(f"Course not found: {course_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )

        # Check permissions
        if not can_edit(db, course, current_user):
            logger.warning(f"Unauthorized access attempt: user_id={current_user.id}, course_author={course.post_author}, role={current_user.role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this course"
            )

        # Check if there are any enrollments
        enrollments = db.query(Enrollment).filter(
            Enrollment.course_id == course_id
        ).all()

        enrollment_count = len(enrollments)
        logger.info(f"Course deletion check: enrollments={enrollment_count}, force_delete={force_delete}, user_role={current_user.role}")

        if enrollment_count > 0:
            # Only admins can force delete
            if not force_delete and current_user.role != 'admin':
                logger.warning(f"Cannot delete course with {enrollment_count} enrollments without force parameter")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete course with {enrollment_count} active enrollment(s). Please unenroll all students first or archive the course instead."
                )

            if current_user.role != "admin":
                logger.warning(f"Non-admin user attempting force delete: user_id={current_user.id}, role={current_user.role}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators can force delete courses with active enrollments"
                )

            # Admin force delete - notify all enrolled students
            notifications = []
            for enrollment in enrollments:
                student = db.query(User).filter(User.id == enrollment.user_id).first()
                if student:
                    notifications.append({
                        'student_email': student.user_email,
                        'student_name': student.display_name,
                        'course_title': course.post_title,
                        'course_id': course.id,
                        'deleted_by': current_user.display_name or 'Administrator'
                    })

            # Send bulk email notifications
            email_results = EmailService.send_bulk_course_deletion_notifications(notifications)

            # Delete all enrollments
            for enrollment in enrollments:
                db.delete(enrollment)

        # Delete related records before deleting the course
        from app.models.course import CourseReview, CourseCategoryRelation, CourseTagRelation

        # Delete course reviews
        db.query(CourseReview).filter(CourseReview.course_id == course_id).delete()
        # Delete course category relations
        db.query(CourseCategoryRelation).filter(CourseCategoryRelation.course_id == course_id).delete()
        # Delete course tag relations
        db.query(CourseTagRelation).filter(CourseTagRelation.course_id == course_id).delete()

        # Cascade-delete additional course-dependent rows (FK-safe ordering).
        db.query(StudentCourseActivity).filter(StudentCourseActivity.course_id == course_id).delete(synchronize_session=False)
        db.query(CourseAnnouncement).filter(CourseAnnouncement.course_id == course_id).delete(synchronize_session=False)
        db.query(WishlistItem).filter(WishlistItem.course_id == course_id).delete(synchronize_session=False)
        # QuizAttempt depends on Quiz — delete BEFORE Quiz.
        db.query(QuizAttempt).filter(QuizAttempt.course_id == course_id).delete(synchronize_session=False)
        db.query(InstructorReview).filter(InstructorReview.course_id == course_id).delete(synchronize_session=False)
        db.query(OrderItem).filter(OrderItem.course_id == course_id).delete(synchronize_session=False)
        db.query(Earning).filter(Earning.course_id == course_id).delete(synchronize_session=False)
        db.query(IssuedCertificate).filter(IssuedCertificate.course_id == course_id).delete(synchronize_session=False)
        db.query(CourseCertificate).filter(CourseCertificate.course_id == course_id).delete(synchronize_session=False)
        db.query(CouponCourseRestriction).filter(CouponCourseRestriction.course_id == course_id).delete(synchronize_session=False)
        # LessonProgress depends on Lesson — delete BEFORE Lesson.
        db.query(LessonProgress).filter(LessonProgress.course_id == course_id).delete(synchronize_session=False)
        # InternshipVoucher: clear redemption pointer; the buyer keeps the voucher.
        db.query(InternshipVoucher).filter(
            InternshipVoucher.redeemed_on_course_id == course_id
        ).update({"redeemed_on_course_id": None}, synchronize_session=False)
        # Cohort: keep the cohort row; just unlink it from this course.
        db.query(Cohort).filter(Cohort.course_id == course_id).update(
            {"course_id": None}, synchronize_session=False
        )

        # Delete related lessons
        db.query(Lesson).filter(Lesson.post_parent == course_id).delete()
        # Delete related quizzes
        db.query(Quiz).filter(Quiz.post_parent == course_id).delete()
        # Delete related assignments
        db.query(Assignment).filter(Assignment.course_id == course_id).delete()

        # Delete the course
        db.delete(course)
        db.commit()

        logger.info(f"Course deleted successfully: course_id={course_id}, enrollments_deleted={enrollment_count}, force_delete={force_delete}")
        send_course_event(course_id, "deleted")

        response_message = {
            "message": "Course deleted successfully",
            "course_id": course_id,
            "enrollments_deleted": enrollment_count,
            "force_deleted": enrollment_count > 0,
            "notifications_sent": len(notifications) if enrollment_count > 0 else 0
        }

        return response_message

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in course deletion: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete course: {str(e)}"
        )

@router.patch("/{course_id}/publish")
async def publish_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Submit course for publication
    - Instructors: Sets status to 'pending' (awaiting admin approval)
    - Admins: Sets status to 'published' (goes live immediately)
    """
    import logging
    logger = logging.getLogger(__name__)

    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check permissions
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to publish this course"
        )

    logger.info(f"🚀 Publishing course {course_id}: {course.post_title} by user {current_user.id} (role: {current_user.role})")

    try:
        # Set status based on role
        if current_user.role == "admin":
            course.post_status = "published"
            message = "Course published successfully"
            logger.info(f"  ✅ Admin published course directly")
        else:
            # Instructors submit for approval
            course.post_status = "pending"
            message = "Course submitted for admin approval"
            logger.info(f"  📝 Instructor submitted course for approval")

        db.commit()
        db.refresh(course)

        logger.info(f"✅ Course {course_id} status updated to: {course.post_status}")
        # Only ping clients when the course actually went live; 'pending' is not
        # publicly visible yet.
        if course.post_status == "published":
            send_course_event(course_id, "published")
        return {
            "message": message,
            "course_id": course.id,
            "status": course.post_status
        }
    except Exception as e:
        logger.error(f"❌ Failed to publish course {course_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish course: {str(e)}"
        )

# NOTE: a second @router.patch("/{course_id}/publish") handler used to live
# here, claiming to serve "requests without trailing slash". Both decorators
# registered the identical path, so FastAPI always matched the first one and
# this delegate was unreachable. Removed — publish_course above serves the
# route (there is no trailing-slash variant of it to handle).

@router.patch("/{course_id}/unpublish")
async def unpublish_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Unpublish a course (instructor/admin only)
    """
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check permissions
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to unpublish this course"
        )

    course.post_status = "draft"
    db.commit()
    db.refresh(course)
    send_course_event(course_id, "unpublished")

    return {
        "message": "Course unpublished successfully",
        "course_id": course.id,
        "status": course.post_status
    }

@router.patch("/{course_id}/approve")
async def approve_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Approve a pending course (admin only)
    Changes status from 'pending' to 'published'
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve courses"
        )

    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if course.post_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course status is '{course.post_status}', not 'pending'. Only pending courses can be approved."
        )

    course.post_status = "published"
    db.commit()
    db.refresh(course)
    send_course_event(course_id, "published")

    return {
        "message": "Course approved and published successfully",
        "course_id": course.id,
        "status": course.post_status
    }

@router.patch("/{course_id}/reject")
async def reject_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Reject a pending course (admin only)
    Changes status from 'pending' to 'draft'
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reject courses"
        )

    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if course.post_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course status is '{course.post_status}', not 'pending'. Only pending courses can be rejected."
        )

    course.post_status = "draft"
    db.commit()
    db.refresh(course)

    return {
        "message": "Course rejected and sent back to draft",
        "course_id": course.id,
        "status": course.post_status
    }

@router.get("/{course_id}/lessons", response_model=List[LessonResponse])
async def get_course_lessons(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user)
):
    """
    Get all lessons for a course
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check if user has access to course
    if course.post_status not in PUBLISHED_STATUSES:
        if not current_user or not can_edit(db, course, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Course not available"
            )

    lessons = db.query(Lesson).filter(
        Lesson.post_parent == course_id
    ).order_by(Lesson.menu_order).all()

    return [CourseService.format_lesson_response(lesson) for lesson in lessons]

async def _resolve_youtube_media(
    youtube_url: str,
    fallback_url: str,
    fallback_duration: int,
    timeout: float = 10.0,
) -> tuple[str, int]:
    """Resolve a YouTube URL to a direct media URL + duration, in-process.

    This used to be an HTTP request from the server back to its own
    /api/v1/extract/video with a 30s client timeout. That was doubly bad: the
    self-request occupied a second worker while the first one waited, and the
    extractor it reached spawns yt-dlp with a 90s timeout of its own. Saving a
    lesson could therefore hang for the full 30s, which is what made instructors
    click "Add Lecture" again — and every one of those clicks appended another
    row, because lesson creation has no dedupe. That is the duplicate-lesson
    mechanism.

    Calling the extractor directly removes the self-request, and the much
    shorter timeout keeps a slow or unavailable yt-dlp from blocking the save.
    Extraction is best-effort by design: the lesson always stores
    lesson_youtube_url, so playback can still resolve the stream later even
    when this returns the fallback.
    """
    from app.routers.video import cache as video_cache, extract as video_extract, get_video_id

    vid = get_video_id(youtube_url)
    if not vid:
        return fallback_url, fallback_duration

    # Share the extract router's cache so a URL already resolved for playback
    # doesn't pay for a second yt-dlp run here.
    key = f"{vid}:720"
    cached = video_cache.get(key)
    if cached and cached.get("expires", 0) > time.time():
        return cached.get("url") or fallback_url, cached.get("duration") or fallback_duration

    try:
        info = await asyncio.wait_for(video_extract(youtube_url, "720"), timeout=timeout)
    except Exception as exc:
        logger.warning("YouTube extraction skipped for %s: %s", youtube_url, exc)
        return fallback_url, fallback_duration

    video_cache[key] = {
        "videoId": vid,
        "title": info.get("title"),
        "url": info.get("url"),
        "duration": info.get("duration"),
        "quality": f"{info.get('height', 'unknown')}p",
        "thumbnail": info.get("thumbnail"),
        "author": info.get("uploader"),
        "expires": time.time() + 14400,
        "cached": False,
    }
    return info.get("url") or fallback_url, info.get("duration") or fallback_duration


def _validate_certificate_id(db: Session, current_user: User, certificate_id) -> None:
    """Review finding M1: a course may only point at a certificate template
    the caller is actually allowed to use.

    Three template flavours are legitimate, mirroring what the course editor's
    picker can offer (see certificates.py's /templates/list and
    certificate_designer.py's _visible_query):

      * a LEGACY row — non-empty `post_name` slug, one of the hand-authored
        designs, usable by anyone;
      * a GLOBAL row — `is_global = true`, published by an admin for everyone;
      * a DESIGNER row OWNED BY THE CALLER — an instructor's own
        elements_config template.

    Anything else (another instructor's private draft, or an id that does not
    resolve at all) is rejected with 422. Admins may reference any row.

    Without this an instructor could set certificate_id to a colleague's
    private template id — which the picker never offers, but the API happily
    accepted — and issue certificates against someone else's design.
    """
    if certificate_id in (None, "", 0):
        return

    try:
        cert_pk = int(certificate_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid certificate template id",
        )

    # Bound the value BEFORE it reaches the query. Python ints are unbounded,
    # but the id column is a 32-bit INTEGER: handing the driver something
    # larger raises OverflowError ("Python int too large to convert to SQLite
    # INTEGER"; psycopg2 raises its own equivalent), which escapes as an
    # uncaught 500 instead of the 422 this function exists to return. An
    # out-of-range id cannot match any row anyway, so it belongs on the same
    # "not found" path as any other unresolvable id.
    if not (1 <= cert_pk <= 2**31 - 1):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid certificate template id",
        )

    from app.models.certificate import Certificate

    template = db.query(Certificate).filter(Certificate.id == cert_pk).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Certificate template not found",
        )

    if current_user.role in ("admin", "superadmin"):
        return

    is_legacy = bool((template.post_name or "").strip())
    is_global = bool(template.is_global)
    is_own = template.post_author == current_user.id
    if is_legacy or is_global or is_own:
        return

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Not authorized to use this certificate template",
    )


def _resolve_lesson_content_fields(
    db: Session,
    current_user: User,
    *,
    requested_content_type: Optional[str],
    requested_h5p_content_id: Optional[int],
    requested_game_id: Optional[int],
    requested_geogebra_applet_id: Optional[int] = None,
    requested_three_d_model_id: Optional[int] = None,
    requested_virtual_lab_sim: Optional[str] = None,
    existing_content_type: str = "video",
    existing_h5p_content_id: Optional[int] = None,
    existing_game_id: Optional[int] = None,
    existing_geogebra_applet_id: Optional[int] = None,
    existing_three_d_model_id: Optional[int] = None,
    existing_virtual_lab_sim: Optional[str] = None,
    course: Optional["Course"] = None,
) -> tuple:
    """Validate + resolve the (lesson_content_type, h5p_content_id, game_id)
    triple for a lesson create/update — single source of truth for the
    atomic-pair contract ('pair or 400'). Extends the former
    _resolve_lesson_h5p_fields for 'game' (spec 2026-09-03 §3):

      - 'video'  -> clears BOTH FKs.
      - 'h5p'    -> requires a ready, caller-owned H5PContent; clears game_id.
      - 'game'   -> requires a PUBLISHED, caller-owned Game (admin any);
                    clears h5p_content_id. 404 unknown id, 400 unpublished,
                    403 cross-owner.

    `requested_*` are whatever the caller's payload supplied (None = field
    omitted, keep existing); `existing_*` are the lesson's current values
    (for a create, pass the same defaults the model would use: "video" /
    None / None).

    Returns the (content_type, h5p_content_id, game_id) tuple to persist.
    Raises HTTPException on any violation:
      - 400 if lesson_content_type isn't "video"/"h5p"/"game" (schema
        already constrains this, but re-checked here since this helper is
        the single source of truth for the cross-field rule below).
      - 400 if the effective type is "h5p"/"game" but no matching id
        resolves.
      - 404 if the id doesn't reference an existing row.
      - 400 if that row's status isn't "ready" (h5p) / "published" (game).
      - 403 unless the caller owns the row or is admin — cross-owner
        references are blocked; an instructor may only attach their own
        content, admins may attach any (ADJUDICATED policy).
    Also clears the unused FK(s) so a lesson never carries a dangling
    cross-type reference (flipping to video clears both; flipping between
    h5p and game clears whichever FK no longer applies).
    """
    effective_type = requested_content_type if requested_content_type is not None else existing_content_type
    if effective_type not in ("video", "h5p", "game", "geogebra", "three_d", "virtual_lab"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lesson_content_type must be one of ['game', 'geogebra', 'h5p', 'video', 'three_d', 'virtual_lab']",
        )

    if effective_type == "video":
        # Flipping back to video drops any H5P/game reference — never leave
        # a lesson with content_type="video" and a dangling FK.
        return "video", None, None, None, None

    if effective_type == "h5p":
        effective_h5p_id = (
            requested_h5p_content_id if requested_h5p_content_id is not None else existing_h5p_content_id
        )
        if effective_h5p_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="h5p_content_id is required when lesson_content_type is 'h5p'",
            )

        content = db.query(H5PContent).filter(H5PContent.id == effective_h5p_id).first()
        if not content:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="H5P content not found")
        if content.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"H5P content is not ready (status={content.status})",
            )
        if content.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only attach your own H5P content to a lesson",
            )

        return "h5p", effective_h5p_id, None, None, None

    if effective_type == "three_d":
        # Type-driven enablement: 3D models attach to MP (meiporul) and
        # UP (utporul) courses only — owner directive 2026-09-04.
        if course is not None and (course.course_type or "") not in ("meiporul", "utporul"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="3D model lessons are enabled on Meiporul (MP) and "
                       "Utporul (UP) courses only",
            )
        effective_model_id = requested_three_d_model_id if requested_three_d_model_id is not None else existing_three_d_model_id
        if effective_model_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="three_d_model_id is required when lesson_content_type is 'three_d'",
            )
        from app.models.three_d import ThreeDModel
        model = db.query(ThreeDModel).filter(ThreeDModel.id == effective_model_id).first()
        if not model:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="3D model not found")
        if (model.owner_id != current_user.id and current_user.role != "admin"
                and not bool(getattr(model, "is_library", False))):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="You can only attach your own 3D models or shared library models")
        return "three_d", None, None, None, effective_model_id

    if effective_type == "virtual_lab":
        from app.routers.virtual_labs import is_valid_lab_slug
        effective_sim = requested_virtual_lab_sim if requested_virtual_lab_sim is not None else existing_virtual_lab_sim
        if not effective_sim:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="virtual_lab_sim is required when lesson_content_type is 'virtual_lab'",
            )
        if not is_valid_lab_slug(db, effective_sim):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="unknown virtual lab simulation")
        return "virtual_lab", None, None, None, effective_sim

    if effective_type == "geogebra":
        applet = _resolve_geogebra_fields(
            db, current_user, course,
            requested_geogebra_applet_id, existing_geogebra_applet_id,
        )
        return "geogebra", None, None, applet.id, None

    # effective_type == "game"
    effective_game_id = requested_game_id if requested_game_id is not None else existing_game_id
    if effective_game_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="game_id is required when lesson_content_type is 'game'",
        )
    game = db.query(Game).filter(Game.id == effective_game_id).first()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    if game.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game must be published before it can be attached to a lesson",
        )
    # Marketplace rule (owner decision 2026-09-05): a published game that is
    # marketplace-listed may be attached by ANY instructor (attribution
    # preserved via owner_id); otherwise own-games/admin only.
    if (game.owner_id != current_user.id and current_user.role != "admin"
            and not bool(getattr(game, "is_listed", False))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only attach your own games or marketplace-listed games",
        )

    return "game", None, effective_game_id, None, None


def _resolve_geogebra_fields(db, current_user, course, requested_applet_id,
                             existing_applet_id):
    """Owner business rule (2026-09-04): GeoGebra interactives may be
    attached ONLY to lessons of FREE courses (effective price 0) — enforced
    here server-side, the UI merely mirrors it. Returns the applet row or
    raises 400/403/404/422."""
    from app.models.geogebra import GeoGebraApplet

    effective_price = course.course_price or 0
    if course.course_sale_price is not None and 0 < course.course_sale_price < effective_price:
        effective_price = course.course_sale_price
    if effective_price != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GeoGebra interactives are available for FREE courses only "
                   "(this course is priced) — owner rule 2026-09-04",
        )

    applet_id = requested_applet_id if requested_applet_id is not None else existing_applet_id
    if applet_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="geogebra_applet_id is required when lesson_content_type is 'geogebra'",
        )
    applet = db.query(GeoGebraApplet).filter(GeoGebraApplet.id == applet_id).first()
    if not applet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="GeoGebra applet not found")
    if applet.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only attach your own GeoGebra applets to a lesson",
        )
    return applet


@router.post("/{course_id}/lessons", response_model=LessonResponse)
async def create_lesson(
    course_id: int,
    lesson_data: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """
    Create a new lesson for a course with validation
    """
    # Validate course ID
    if course_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID"
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    # Check permissions
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add lessons to this course"
        )

    # Validate lesson data
    if not lesson_data.title or not lesson_data.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lesson title is required"
        )

    if len(lesson_data.title) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lesson title too long (max 500 characters)"
        )

    # Extract video URL if YouTube URL is provided
    extracted_video_url = lesson_data.video_url
    video_duration = lesson_data.video_duration or 0

    if lesson_data.youtube_url and extract_video_id(lesson_data.youtube_url):
        extracted_video_url, video_duration = await _resolve_youtube_media(
            lesson_data.youtube_url,
            extracted_video_url or "",
            video_duration,
        )

    # Next lesson order. This was `.count()`, which collides after any deletion:
    # with lessons at menu_order 1,2,3, deleting #2 leaves a count of 2, so the
    # next lesson is also created at 3. Two rows sharing a menu_order sort
    # non-deterministically, which is why the same lesson could appear twice in
    # the curriculum. Take the actual maximum instead.
    max_order = db.query(func.coalesce(func.max(Lesson.menu_order), 0)).filter(
        Lesson.post_parent == course_id
    ).scalar() or 0

    resolved_content_type, resolved_h5p_content_id, resolved_game_id, resolved_geogebra_id, resolved_extra = _resolve_lesson_content_fields(
        db,
        current_user,
        requested_content_type=lesson_data.lesson_content_type,
        requested_h5p_content_id=lesson_data.h5p_content_id,
        requested_game_id=lesson_data.game_id,
        requested_geogebra_applet_id=lesson_data.geogebra_applet_id,
        requested_three_d_model_id=getattr(lesson_data, "three_d_model_id", None),
        requested_virtual_lab_sim=getattr(lesson_data, "virtual_lab_sim", None),
        existing_content_type="video",
        course=course,
    )

    try:
        new_lesson = Lesson(
            post_title=lesson_data.title.strip(),
            post_content=lesson_data.content or "",
            post_author=current_user.id,
            post_parent=course_id,
            post_name=lesson_data.title.lower().replace(' ', '-')[:200],
            lesson_video_url=extracted_video_url or "",
            lesson_youtube_url=lesson_data.youtube_url or "",
            lesson_video_duration=str(video_duration),
            lesson_preview=lesson_data.is_preview,
            menu_order=max_order + 1,
            post_type="lesson",
            post_status="publish",
            lesson_content_type=resolved_content_type,
            h5p_content_id=resolved_h5p_content_id,
            game_id=resolved_game_id,
            geogebra_applet_id=resolved_geogebra_id,
            three_d_model_id=resolved_extra if resolved_content_type == "three_d" else None,
            virtual_lab_sim=resolved_extra if resolved_content_type == "virtual_lab" else None,
        )

        db.add(new_lesson)
        db.commit()
        db.refresh(new_lesson)

        return CourseService.format_lesson_response(new_lesson)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lesson: {str(e)}"
        )

@router.patch("/{course_id}/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    course_id: int,
    lesson_id: int,
    lesson_data: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Update a lesson for a course
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if not can_edit(db, course, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.post_parent == course_id
    ).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    # Update fields that were provided
    if lesson_data.title is not None:
        lesson.post_title = lesson_data.title
    if lesson_data.content is not None:
        lesson.post_content = lesson_data.content
    if lesson_data.video_url is not None:
        lesson.lesson_video_url = lesson_data.video_url
    if lesson_data.youtube_url is not None:
        lesson.lesson_youtube_url = lesson_data.youtube_url
    if lesson_data.video_duration is not None:
        lesson.lesson_video_duration = str(lesson_data.video_duration)
    if lesson_data.is_preview is not None:
        lesson.lesson_preview = lesson_data.is_preview
    if lesson_data.menu_order is not None:
        lesson.menu_order = lesson_data.menu_order
    if lesson_data.attachment_url is not None:
        lesson.lesson_attachment_url = lesson_data.attachment_url
    if lesson_data.order is not None:
        lesson.menu_order = lesson_data.order

    if (
        lesson_data.lesson_content_type is not None
        or lesson_data.h5p_content_id is not None
        or lesson_data.game_id is not None
        or lesson_data.geogebra_applet_id is not None
    ):
        resolved_content_type, resolved_h5p_content_id, resolved_game_id, resolved_geogebra_id, resolved_extra = _resolve_lesson_content_fields(
            db,
            current_user,
            requested_content_type=lesson_data.lesson_content_type,
            requested_h5p_content_id=lesson_data.h5p_content_id,
            requested_game_id=lesson_data.game_id,
            requested_geogebra_applet_id=lesson_data.geogebra_applet_id,
            requested_three_d_model_id=getattr(lesson_data, "three_d_model_id", None),
            requested_virtual_lab_sim=getattr(lesson_data, "virtual_lab_sim", None),
            existing_content_type=lesson.lesson_content_type or "video",
            existing_three_d_model_id=getattr(lesson, "three_d_model_id", None),
            existing_virtual_lab_sim=getattr(lesson, "virtual_lab_sim", None),
            course=course,
        )
        lesson.lesson_content_type = resolved_content_type
        lesson.h5p_content_id = resolved_h5p_content_id
        lesson.game_id = resolved_game_id
        lesson.geogebra_applet_id = resolved_geogebra_id
        lesson.three_d_model_id = resolved_extra if resolved_content_type == "three_d" else None
        lesson.virtual_lab_sim = resolved_extra if resolved_content_type == "virtual_lab" else None

    try:
        db.commit()
        db.refresh(lesson)
        return CourseService.format_lesson_response(lesson)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lesson: {str(e)}"
        )

@router.delete("/{course_id}/lessons/{lesson_id}")
async def delete_lesson(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Delete a lesson from a course.

    This endpoint was missing entirely — the course builder's delete button
    called it, got a 404/405 back and rolled the row into the UI again, so
    deleting a lecture never worked for lessons (quiz/assignment deletes had
    their own routes all along). Children that reference the lesson via
    foreign keys are removed first: progress rows, student activity rows and
    watch sessions.
    """
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.post_parent == course_id
    ).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    if not can_edit(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this lesson"
        )

    try:
        # FK children first — same order the whole-course delete uses.
        db.query(LessonProgress).filter(
            LessonProgress.lesson_id == lesson_id
        ).delete(synchronize_session=False)
        db.query(StudentCourseActivity).filter(
            StudentCourseActivity.lesson_id == lesson_id
        ).delete(synchronize_session=False)
        db.query(WatchSession).filter(
            WatchSession.lesson_id == lesson_id
        ).delete(synchronize_session=False)

        db.delete(lesson)
        db.commit()
        return {"message": "Lesson deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lesson: {str(e)}"
        )

@router.post("/{course_id}/lessons/{lesson_id}/complete")
async def mark_lesson_complete(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Mark a lesson as complete and update course progress
    """
    # Check if user is enrolled
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == current_user.id
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not enrolled in this course"
        )

    # Check if lesson/quiz/assignment exists and belongs to this course
    # Advanced courses may use quizzes or assignments as lesson equivalents
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.post_parent == course_id
    ).first()

    quiz = None
    assignment = None
    if not lesson:
        # Check if it's a quiz
        quiz = db.query(Quiz).filter(
            Quiz.id == lesson_id,
            Quiz.post_parent == course_id
        ).first()
    if not lesson and not quiz:
        # Check if it's an assignment
        assignment = db.query(Assignment).filter(
            Assignment.id == lesson_id,
            Assignment.course_id == course_id
        ).first()

    if not lesson and not quiz and not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson, quiz, or assignment not found in this course"
        )

    # Handle different content types (lessons, quizzes, assignments)
    # Each has its own progress tracking mechanism
    if lesson:
        # Use LessonProgress for actual lessons
        lesson_progress = db.query(LessonProgress).filter(
            LessonProgress.enrollment_id == enrollment.id,
            LessonProgress.lesson_id == lesson.id
        ).first()

        if lesson_progress:
            # Update existing progress
            if lesson_progress.progress_status != "completed":
                lesson_progress.progress_status = "completed"
                lesson_progress.completion_date = datetime.now(timezone.utc)
        else:
            # Create new lesson progress
            new_progress = LessonProgress(
                user_id=current_user.id,
                course_id=course_id,
                lesson_id=lesson.id,
                enrollment_id=enrollment.id,
                progress_status="completed",
                completion_date=datetime.now(timezone.utc)
            )
            db.add(new_progress)

    elif quiz:
        # Issue 3: a quiz content item can ONLY be marked complete if the
        # student has a real, passing attempt. Previously this branch
        # fabricated a passing QuizAttempt (earned_marks = passing grade),
        # which let students bypass the quiz entirely. Now we require an
        # existing ended attempt whose score meets quiz_passing_grade —
        # mirroring the pass logic in CourseService.calculate_course_progress.
        attempts = db.query(QuizAttempt).filter(
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.course_id == course_id,
            QuizAttempt.attempt_status == "attempt_ended",
        ).all()

        passing_grade = quiz.quiz_passing_grade or 0
        passing_attempt = next(
            (
                a for a in attempts
                if a.total_marks and a.total_marks > 0
                and (float(a.earned_marks) / float(a.total_marks)) * 100 >= passing_grade
            ),
            None,
        )

        if not passing_attempt:
            # Block completion until the required quiz is actually passed.
            if not attempts:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Please complete the quiz before marking it as complete.",
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"You must score at least {passing_grade}% on this quiz "
                    "before marking it as complete."
                ),
            )
        # A real passing attempt exists — nothing to write; the quiz is
        # already counted by calculate_course_progress below. Because this
        # branch never calls db.add()/mutates a QuizAttempt (it only reads
        # already-committed ones from the quiz's own submit/finalize
        # trigger points), it cannot hit the same missing-flush class of
        # bug as the `lesson` branch above — there is no pending write
        # here for the flush before calculate_course_progress to surface.

    elif assignment:
        # Use AssignmentSubmission for assignments
        # Issue (logic audit): this branch used to fabricate or
        # force-grade a submission with full marks, letting students
        # mark assignment lessons complete without any instructor
        # grading. Like the quiz branch above, completion requires a
        # real, instructor-graded submission — nothing is written here;
        # the graded submission is already counted by
        # calculate_course_progress below.
        submission = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.user_id == current_user.id,
            AssignmentSubmission.assignment_id == assignment.id
        ).first()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Submit the assignment first — it is graded by your instructor."
            )
        if submission.status != "graded":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Awaiting instructor grading."
            )
        # Same reasoning as the quiz branch above: nothing is written here
        # (the AssignmentSubmission was already committed by its own
        # grade-endpoint trigger point), so there is no pending write this
        # branch could hide from calculate_course_progress's read.

    # Issue 2/8: record a discrete activity row so the admin Statistics /
    # Student Activity panels can show completions and revisits. Idempotent
    # per (user, course, lesson) on the same day to avoid flooding.
    try:
        activity_type = (
            "quiz_passed" if quiz
            else "assignment_submitted" if assignment
            else "lesson_completed"
        )
        db.add(StudentCourseActivity(
            user_id=current_user.id,
            course_id=course_id,
            lesson_id=lesson.id if lesson else None,
            quiz_id=quiz.id if quiz else None,
            activity_type=activity_type,
            activity_value=str(lesson_id),
        ))
    except Exception as act_err:
        # Activity tracking must never break completion.
        logger.warning("Failed to record StudentCourseActivity: %s", act_err)

    # Get course and update enrollment progress
    course = db.query(Course).filter(Course.id == course_id).first()

    # Get actual total lessons from database (not from relationship which might be cached)
    total_lessons = db.query(Lesson).filter(Lesson.post_parent == course_id).count()
    enrollment.total_lessons = total_lessons

    # Flush pending writes from the branches above (new_progress /
    # lesson_progress.progress_status for the `lesson` branch;
    # StudentCourseActivity for all three) before calculate_course_progress
    # runs its own fresh SELECT over LessonProgress. This session is
    # autoflush=False (app/core/database.py + tests/conftest.py), so
    # without an explicit flush here that SELECT does NOT see the
    # just-added/just-mutated row — on a single-lesson course this made a
    # lesson's first-ever completion under-report completed_lessons/
    # course_progress_percentage/course_completed in THIS response (a
    # later re-query sees the correct committed state; only the
    # same-request read was stale). This flush is unrelated to the H1
    # transaction-ownership fix below — it makes THIS handler's own
    # pending writes visible to THIS handler's own next read, same
    # session, same transaction; it does not commit or touch any other
    # session/transaction boundary.
    db.flush()

    # Recalculate overall course progress (lessons, quizzes, assignments).
    # This call commits the LessonProgress/StudentCourseActivity writes made
    # above (calculate_course_progress's own db.commit()) — the gamification

    # SILEOS event spine: lesson completion as an xAPI statement
    # (best-effort, post-commit).
    from app.services.xapi_service import emit_statement
    emit_statement(
        actor_user_id=current_user.id,
        verb="completed",
        object_type="lesson",
        object_id=lesson_id,
        result={"progress_percentage": enrollment.course_progress_percentage},
        context={"course_id": course_id, "source": "mark_lesson_complete"},
    )
    # award below is sequenced strictly AFTER that commit (never before it)
    # so award()'s own flush/rollback (H1 review fix: award() owns none of
    # the caller's transaction boundary) can never touch this request's
    # still-uncommitted lesson-completion state.
    from app.services.course_service import CourseService
    progress_data = CourseService.calculate_course_progress(db, enrollment)

    # Gamification (spec D1): +10 XP for a real lesson completion only —
    # the quiz/assignment branches above are awarded from their own native
    # trigger points (quiz submit/finalize, assignment grade) so a lesson
    # equivalent doesn't get double-counted here. Best-effort: never fails
    # lesson completion. Own commit — see comment above for why this must
    # come after calculate_course_progress's commit, not before.
    if lesson:
        try:
            from app.services.gamification_service import award as _award_xp
            _award_xp(
                db, current_user.id, "lesson_completed",
                event_key=f"lesson:{lesson.id}:completed:user:{current_user.id}",
                course_id=course_id,
                meta={"lesson_id": lesson.id},
            )
            db.commit()
        except Exception as game_err:
            logger.warning("Gamification award failed for lesson complete: %s", game_err)
            try:
                db.rollback()
            except Exception:
                pass

    is_course_completed = progress_data.get('overall_progress', 0) >= 100

    # Certificate issuance is handled by CourseService.calculate_course_progress above.
    # We only need to send the email notification if a certificate exists.
    if is_course_completed and enrollment.completion_date:
        try:
            from app.models.certificate import IssuedCertificate
            from app.services.email_service import EmailService

            # Get existing certificate (already issued by calculate_course_progress)
            cert_row = db.query(IssuedCertificate).filter(
                IssuedCertificate.user_id == enrollment.user_id,
                IssuedCertificate.course_id == enrollment.course_id
            ).first()

            if cert_row:
                course = db.query(Course).filter(Course.id == course_id).first()
                completion_date_str = (
                    enrollment.completion_date.strftime('%B %d, %Y')
                    if enrollment.completion_date else datetime.utcnow().strftime('%B %d, %Y')
                )
                try:
                    EmailService.send_certificate_issued_notification(
                        student_email=current_user.user_email,
                        student_name=current_user.display_name,
                        course_title=course.post_title if course else cert_row.certificate_title,
                        course_id=course_id,
                        certificate_url=cert_row.certificate_download_url or "",
                        completion_date=completion_date_str
                    )
                except Exception as email_err:
                    logger.warning("[Certificate] email send failed: %s", email_err)
        except Exception as cert_err:
            logger.warning("[Certificate] Error in cert issuance hook: %s", cert_err)
    else:
        logger.debug(
            "[Certificate] Course %s not completed yet - Progress: %s%%",
            course_id,
            progress_data.get('overall_progress'),
        )

    # Note: calculate_course_progress() already commits, so no need to commit here

    # Return progress info and certificate status
    response = {
        "message": "Lesson marked as complete",
        "completed_lessons": enrollment.completed_lessons,
        "total_lessons": total_lessons,
        "progress_percentage": enrollment.course_progress_percentage,
        "course_completed": is_course_completed
    }

    # If course is completed, include certificate info
    if is_course_completed:
        response["certificate_available"] = True
        response["course_id"] = course_id

    return response

# NOTE: a second @router.patch("/{course_id}/lessons/{lesson_id}") handler
# used to live here (review finding M3). It was DEAD CODE — FastAPI dispatches
# to the FIRST matching route, so the handler registered above (~line 1300)
# always won and this one never executed. Worse, it was a reorder landmine:
# it carried a weaker guard set (no _resolve_lesson_content_fields validation of
# lesson_content_type/h5p_content_id), so merely moving it above its twin
# would have silently disabled H5P lesson-content validation on every lesson
# update. Deleted rather than merged: the surviving handler is a strict
# superset for the fields the API actually accepts.
#
# B10 (2026-09-04): a second @router.delete("/{course_id}/lessons/{lesson_id}")
# handler used to live here too — same class of hazard. FastAPI dispatched to
# the delete_lesson defined above (~line 1493), which also cleans up FK
# children (LessonProgress, StudentCourseActivity, WatchSession) before
# deleting; this dead twin skipped that cleanup entirely and returned 204
# instead of the live handler's 200 body. Deleted outright — strictly weaker,
# nothing to merge.

# Enrollment Management

@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_in_course(
    course_id: int,
    background_tasks: BackgroundTasks,
    payload: Optional[Dict[str, Any]] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Enroll the current user in a course.

    Body (optional):
        {"coupon_code": "..."} — unified checkout code. May be either a
        ReferralCode (cohort signup) or a discount Coupon. The backend
        detects which kind it is.

    Rules:
      * Paid courses: ALWAYS reject with 402 — even if a cohort referral
        or cohort-linked coupon matches. Paid courses go through the
        Razorpay create-order / verify flow. The cohort mapping is then
        applied post-verify, and the referral used_count is bumped at
        that point (not here).
      * Free courses: enroll immediately. If the code maps to a cohort
        (referral, or coupon with cohort_id), create CohortMembership
        idempotently and bump ReferralCode.used_count atomically.
    """
    from app.services.coupon_service import (
        CouponError,
        resolve_checkout_code,
        lock_referral_and_bump,
        lock_voucher_and_redeem,
    )
    from app.models.cohort import CohortMembership

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if course.post_status not in PUBLISHED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is not available for enrollment"
        )

    # Idempotent: if already enrolled, return the existing row.
    # IMPORTANT: do NOT consume any voucher in this branch — the user gets
    # their existing enrollment back, code untouched, explanatory message.
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == current_user.id
    ).first()

    if existing_enrollment:
        return {
            "id": existing_enrollment.id,
            "course_id": course_id,
            "student_id": current_user.id,
            "status": existing_enrollment.enrollment_status,
            "enrolled_at": existing_enrollment.enrollment_date,
            "progress": existing_enrollment.course_progress_percentage or 0,
            "message": "Already enrolled in this course — no code was consumed",
        }

    coupon_code: Optional[str] = None
    if payload and isinstance(payload, dict):
        coupon_code = (payload.get("coupon_code") or "").strip() or None

    # (Removed a hardcoded per-email free-access backdoor — everyone pays.)
    is_free_user = False
    is_paid = bool(course.course_price and float(course.course_price) > 0)

    # Resolve the checkout code (if any) uniformly. May be Voucher, Referral,
    # or Coupon — resolver decides kind. Invalid codes are a 400 regardless
    # of paid/free status so the user gets immediate feedback.
    resolved = None
    if coupon_code:
        try:
            resolved = resolve_checkout_code(
                db,
                code=coupon_code,
                user_id=current_user.id,
                course=course,
                for_paid=is_paid,
            )
        except CouponError as exc:
            raise HTTPException(status_code=400, detail=exc.message)

    is_voucher = bool(resolved and resolved.kind == "voucher")

    # A discount coupon that reduces the price to zero is, in effect, a full
    # comp — there is nothing to charge, and Razorpay rejects sub-₹1 orders, so
    # routing it through payment would either fail or (with the ₹1 floor) charge
    # the user for a "free" course. Treat a zero-final-amount coupon like a
    # voucher: enroll directly here and record its redemption below.
    is_full_discount_coupon = bool(
        resolved
        and resolved.kind == "coupon"
        and float(resolved.final_amount) <= 0
    )

    # CRITICAL: Paid courses always need payment unless using a voucher or a
    # coupon that brings the total to zero. Partial-discount coupons still go
    # through the Razorpay flow so the (non-zero) amount is actually charged.
    requires_payment = is_paid and not is_voucher and not is_full_discount_coupon
    if requires_payment:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": "Payment required for this course",
                "course_price": float(course.course_price),
                "requires_payment": True,
            }
        )

    # Determine cohort (if any) from resolved code. Voucher always carries a
    # cohort (the internship's 1:1 cohort); referral/coupon may or may not.
    cohort_to_assign = resolved.cohort if resolved else None
    referral_row = resolved.referral_row if resolved else None
    voucher_row = resolved.voucher_row if resolved else None

    if cohort_to_assign and resolved and resolved.max_students_reached:
        raise HTTPException(status_code=400, detail="Cohort full")

    try:
        total_lessons_count = db.query(Lesson).filter(Lesson.post_parent == course_id).count()

        new_enrollment = Enrollment(
            course_id=course_id,
            user_id=current_user.id,
            enrollment_status="enrolled",
            total_lessons=total_lessons_count,
            completed_lessons=0,
            cohort_id=cohort_to_assign.id if cohort_to_assign else None,
        )
        db.add(new_enrollment)

        # CohortMembership is the SPOC-visible roster — mirror the cohort_id
        # stamp on the enrollment with a membership row (idempotent).
        if cohort_to_assign:
            already_member = db.query(CohortMembership).filter(
                CohortMembership.cohort_id == cohort_to_assign.id,
                CohortMembership.user_id == current_user.id,
            ).first()
            if not already_member:
                db.add(CohortMembership(
                    cohort_id=cohort_to_assign.id,
                    user_id=current_user.id,
                ))

        # Voucher redemption: lock the row and flip status → redeemed in the
        # same transaction as the Enrollment insert. If two concurrent calls
        # race on the same voucher, one wins the lock and the other gets
        # CouponError → 400, which rolls back the losing enrollment.
        if voucher_row is not None:
            try:
                lock_voucher_and_redeem(db, voucher_row.id, course_id)
            except CouponError as exc:
                raise HTTPException(status_code=400, detail=exc.message)

        # Atomically bump ReferralCode.used_count under SELECT FOR UPDATE.
        # Re-checks max_uses under the lock so two parallel redemptions
        # on max_uses=1 can't both succeed.
        if referral_row is not None:
            try:
                lock_referral_and_bump(db, referral_row.id)
            except CouponError as exc:
                raise HTTPException(status_code=400, detail=exc.message)

        # Full-discount coupon (final_amount == 0): record the redemption here
        # since this enrollment bypasses the Razorpay /verify path that would
        # normally log it. Mirrors payments.verify so per-user-limit and usage
        # analytics stay accurate.
        if is_full_discount_coupon and resolved is not None:
            from app.models.coupon import CouponUsage
            db.add(CouponUsage(
                coupon_id=resolved.coupon.id,
                user_id=current_user.id,
                order_id=None,
                discount_amount=float(resolved.discount_amount),
            ))
            resolved.coupon.usage_count = (resolved.coupon.usage_count or 0) + 1

        # Update course enrollment count atomically
        db.query(Course).filter(Course.id == course_id).update(
            {Course.total_enrollments: (Course.total_enrollments or 0) + 1},
            synchronize_session=False,
        )
        db.commit()
        db.refresh(new_enrollment)

        # Send enrollment confirmation email AFTER responding — same rule as
        # registration: a slow SMTP hop must never hold the enroll response
        # (and its 20s timeout) hostage.
        background_tasks.add_task(
            send_enrollment_confirmation_email_safely,
            email=current_user.user_email,
            user_name=current_user.display_name or current_user.user_email,
            course_title=course.post_title,
            course_id=course_id,
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        # User already enrolled - return existing enrollment
        existing = db.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == current_user.id
        ).first()
        if existing:
            return {
                "id": existing.id,
                "course_id": course_id,
                "student_id": current_user.id,
                "status": existing.enrollment_status,
                "enrolled_at": existing.enrollment_date,
                "progress": 0,
                "is_free": not is_voucher,
                "is_voucher": is_voucher,
                "cohort_id": existing.cohort_id,
            }
        else:
            # If no existing enrollment found after IntegrityError, something is wrong
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create enrollment. Please try again."
            )
    except Exception as e:
        # Catch-all for any other errors
        db.rollback()
        logger.error(f"Unexpected error during enrollment for user {current_user.id} in course {course_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during enrollment. Please try again."
        )

    return {
        "id": new_enrollment.id,
        "course_id": course_id,
        "student_id": current_user.id,
        "status": new_enrollment.enrollment_status,
        "enrolled_at": new_enrollment.enrollment_date,
        "progress": 0,
        "is_free": not is_voucher,
        "is_voucher": is_voucher,
        "cohort_id": cohort_to_assign.id if cohort_to_assign else None,
    }

# NOTE: the mock `POST /{course_id}/purchase` endpoint was removed — it
# auto-enrolled any authenticated user in a paid course for free. Paid
# enrollment goes through the real Razorpay flow (/payments/create-order +
# /payments/verify); free/coupon enrollment goes through /enroll.

@router.get("/{course_id}/progress", response_model=CourseProgressResponse)
async def get_course_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Get user's progress in a course
    """
    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == current_user.id
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not enrolled in this course"
        )

    # Read-only: recompute the numbers WITHOUT persisting anything — no
    # tracker-column writes, no completion/regression transitions, and no
    # certificate issuance as a side effect of a GET.
    return CourseService.calculate_course_progress(db, enrollment, commit=False)


# ---------------------------------------------------------------------------
# Course Reviews
# ---------------------------------------------------------------------------

class CourseReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review_title: str = Field(default="", max_length=255)
    review_content: str = Field(default="")


def _recompute_course_rating(db: Session, course_id: int) -> None:
    """Recompute and persist Course.average_rating + total_reviews
    across only status='approved' reviews. Caller is responsible for commit.
    """
    from sqlalchemy import func as _sa_func
    row = (
        db.query(
            _sa_func.coalesce(_sa_func.avg(CourseReview.rating), 0),
            _sa_func.count(CourseReview.id),
        )
        .filter(
            CourseReview.course_id == course_id,
            CourseReview.status == "approved",
        )
        .one()
    )
    avg_rating = float(row[0] or 0)
    total = int(row[1] or 0)
    db.query(Course).filter(Course.id == course_id).update(
        {Course.average_rating: round(avg_rating, 2), Course.total_reviews: total},
        synchronize_session=False,
    )


@router.get("/{course_id}/reviews")
async def list_course_reviews(
    course_id: int,
    db: Session = Depends(get_db),
):
    """Public — list approved reviews for a course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    reviews = (
        db.query(CourseReview)
        .options(joinedload(CourseReview.user).joinedload(User.profile))
        .filter(
            CourseReview.course_id == course_id,
            CourseReview.status == "approved",
        )
        .order_by(CourseReview.created_at.desc())
        .all()
    )

    items = []
    for r in reviews:
        u = r.user
        avatar = ""
        if u and u.profile and u.profile.profile_photo:
            avatar = u.profile.profile_photo
        items.append({
            "id": r.id,
            "rating": r.rating,
            "review_title": r.review_title or "",
            "review_content": r.review_content or "",
            "created_at": r.created_at,
            "user": {
                "id": u.id if u else None,
                "name": u.display_name if u else "Anonymous",
                "avatar": avatar,
            },
        })

    total_reviews = len(items)
    avg_rating = (
        round(sum(r["rating"] for r in items) / total_reviews, 2)
        if total_reviews > 0 else 0
    )

    return {
        "reviews": items,
        "average_rating": avg_rating,
        "total_reviews": total_reviews,
    }


@router.post("/{course_id}/reviews")
async def create_course_review(
    course_id: int,
    payload: CourseReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Authenticated — submit a review. Must be enrolled. One review per user
    per course. New rows are `status='pending'` and require admin moderation.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrollment = db.query(Enrollment).filter(
        Enrollment.course_id == course_id,
        Enrollment.user_id == current_user.id,
    ).first()
    if not enrollment or enrollment.enrollment_status in ("cancelled", "suspended"):
        raise HTTPException(
            status_code=403,
            detail="You must be enrolled in this course to review it",
        )

    existing = db.query(CourseReview).filter(
        CourseReview.course_id == course_id,
        CourseReview.user_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this course")

    try:
        review = CourseReview(
            course_id=course_id,
            user_id=current_user.id,
            rating=payload.rating,
            review_title=payload.review_title or "",
            review_content=payload.review_content or "",
            status="pending",
            review_status="pending",
        )
        db.add(review)
        db.flush()
        # Pending reviews do not influence average_rating yet; recompute
        # anyway so the total_reviews counter stays consistent with the
        # approved-only definition.
        _recompute_course_rating(db, course_id)
        db.commit()
        db.refresh(review)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit review: {exc}")

    return {
        "id": review.id,
        "status": review.status,
        "message": "Review submitted — pending approval",
    }


# ==================== CATEGORIES ENDPOINTS ====================

@router.get("/categories", response_model=List[Dict[str, Any]])
def get_categories(db: Session = Depends(get_db)):
    """Get all course categories"""
    categories = db.query(CourseCategory).order_by(CourseCategory.term_order, CourseCategory.name).all()
    result = []
    for cat in categories:
        result.append({
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "parent_id": cat.parent_id,
        })
    return result


@router.get("/categories/{category_id}/courses")
def get_courses_by_category(
    category_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get courses by category"""
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get courses for this category
    query = db.query(Course).filter(
        Course.post_status == "published",
        Course.categories.any(CourseCategory.id == category_id)
    )

    total = query.count()
    courses = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "courses": [CourseService.serialize_course(c, db) for c in courses],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/{course_id}/lessons/{lesson_id}/preview")
async def get_lesson_public_preview(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user),
):
    """Public preview of ONE lesson (2026-09-05): works logged-out. Returns the
    full lesson payload (video / 3D / lab / game / H5P handles) only when the
    lesson is marked `lesson_preview`, or the caller is enrolled / the owner /
    admin. Every other lesson answers 403 with an enrol hint — the same rule
    the course payload applies when it strips locked lessons."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id, Lesson.post_parent == course_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    privileged = bool(current_user and (current_user.role in ("admin", "superadmin") or current_user.id == course.post_author))
    if course.post_status not in PUBLISHED_STATUSES and not privileged:
        raise HTTPException(status_code=403, detail="This course is not yet published")
    enrolled = False
    if current_user and not privileged:
        e = db.query(Enrollment).filter(Enrollment.course_id == course_id, Enrollment.user_id == current_user.id).first()
        enrolled = e is not None and e.enrollment_status not in ["cancelled", "suspended"]
    if not (lesson.lesson_preview or enrolled or privileged):
        raise HTTPException(status_code=403, detail="This lesson is locked — enrol to unlock it")
    data = CourseService.format_lesson_response(lesson)
    data["is_locked"] = False
    data["is_public_preview"] = bool(lesson.lesson_preview) and not (enrolled or privileged)
    if getattr(lesson, "h5p_content_id", None):
        from app.models.h5p import H5PContent
        row = db.query(H5PContent.public_id).filter(H5PContent.id == lesson.h5p_content_id).first()
        data["h5p_public_id"] = row[0] if row else None
    data["three_d_model_id"] = getattr(lesson, "three_d_model_id", None)
    data["virtual_lab_sim"] = getattr(lesson, "virtual_lab_sim", None)
    data["game_id"] = getattr(lesson, "game_id", None)
    data["geogebra_applet_id"] = getattr(lesson, "geogebra_applet_id", None)
    return data
