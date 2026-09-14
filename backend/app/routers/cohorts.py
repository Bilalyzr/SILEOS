"""
Cohorts router — SS1 (mounted at /api/v1/cohorts).

Endpoints:
  Admin:
    POST|GET|PUT|DELETE /admin/colleges[/id]
    POST|GET|PUT|DELETE /admin/cohorts[/id]
  SPOC:
    GET  /spoc/my-cohorts
    GET  /spoc/cohorts/{id}/roster
    GET  /spoc/cohorts/{id}/task-stats
    POST|GET|PUT|DELETE /spoc/cohorts/{id}/sessions[/id]
    POST /spoc/sessions/{id}/attendance
    POST /spoc/students/{user_id}/internship-eligible
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, date, time, timezone
from typing import List, Optional

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import and_, func as sa_func
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.user import User
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment, LessonProgress
from app.models.quiz import QuizAttempt
from app.models.assignment import AssignmentSubmission
from app.models.cohort import (
    College,
    Cohort,
    ReferralCode,
    CohortMembership,
    Session as CohortSession,
    SessionAttendance,
)
from app.models.coupon import Coupon
from app.services.auth_service import AuthService
from app.schemas.cohort import (
    CollegeCreate, CollegeUpdate, CollegeOut,
    CohortCreate, CohortUpdate, CohortOut, ReferralCodeOut,
    RosterRow, TaskStatsRow,
    SessionCreate, SessionUpdate, SessionOut,
    BulkAttendanceRequest, AttendanceOut,
    EligibilityToggleRequest, EligibilityToggleOut,
)


router = APIRouter()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    value = (value or "").lower().strip()
    slug = _SLUG_RE.sub("-", value).strip("-")
    return slug or f"item-{secrets.token_hex(3)}"


def _generate_referral_code(cohort_slug: str) -> str:
    prefix = (cohort_slug or "cohort").split("-")[0][:12] or "cohort"
    rand = secrets.token_hex(2).upper()  # 4-char random
    return f"{prefix.upper()}-{rand}"


def _unique_slug(db: DBSession, model, base: str) -> str:
    slug = base
    n = 1
    while db.query(model).filter(model.slug == slug).first() is not None:
        n += 1
        slug = f"{base}-{n}"
    return slug


def _validate_scheduled_at(value: datetime) -> datetime:
    """Reject scheduled_at more than 30 minutes in the past. Naive datetimes
    are treated as UTC. Returns the (possibly tz-attached) value."""
    if value is None:
        return value
    dt = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if dt < now - timedelta(minutes=30):
        raise HTTPException(
            status_code=400,
            detail="scheduled_at cannot be more than 30 minutes in the past",
        )
    return dt


def _ensure_spoc_owns_cohort(db: DBSession, cohort_id: int, user: User) -> Cohort:
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    if cohort.spoc_user_id != user.id:
        raise HTTPException(status_code=403, detail="This cohort does not belong to you")
    return cohort


# ==================================================================
# Admin — Colleges
# ==================================================================

@router.post("/admin/colleges", response_model=CollegeOut)
def admin_create_college(
    payload: CollegeCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    slug = payload.slug or _slugify(payload.name)
    slug = _unique_slug(db, College, slug)
    try:
        college = College(
            name=payload.name,
            slug=slug,
            city=payload.city or "",
            state=payload.state or "",
            contact_name=payload.contact_name or "",
            contact_email=payload.contact_email or "",
            created_by=current_user.id,
        )
        db.add(college)
        db.commit()
        db.refresh(college)
        return college
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create college: {e}")


@router.get("/admin/colleges", response_model=List[CollegeOut])
def admin_list_colleges(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    return db.query(College).order_by(College.created_at.desc()).all()


@router.get("/admin/colleges/{college_id}", response_model=CollegeOut)
def admin_get_college(
    college_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return college


@router.put("/admin/colleges/{college_id}", response_model=CollegeOut)
def admin_update_college(
    college_id: int,
    payload: CollegeUpdate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    try:
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(college, k, v)
        db.commit()
        db.refresh(college)
        return college
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update: {e}")


@router.delete("/admin/colleges/{college_id}")
def admin_delete_college(
    college_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    try:
        db.delete(college)
        db.commit()
        return {"message": "College deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete: {e}")


# Public endpoint for colleges (for dropdown in course edit)
@router.get("/colleges", response_model=List[CollegeOut])
def public_list_colleges(
    db: DBSession = Depends(get_db),
):
    """Public endpoint to list all colleges for institution dropdown"""
    return db.query(College).order_by(College.name.asc()).all()


# ==================================================================
# Admin — Cohorts
# ==================================================================

@router.post("/admin/cohorts", response_model=CohortOut)
def admin_create_cohort(
    payload: CohortCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    # Validate FKs
    if not db.query(College).filter(College.id == payload.college_id).first():
        raise HTTPException(status_code=400, detail="College not found")
    if not db.query(Course).filter(Course.id == payload.course_id).first():
        raise HTTPException(status_code=400, detail="Course not found")
    spoc = db.query(User).filter(User.id == payload.spoc_user_id).first()
    if not spoc:
        raise HTTPException(status_code=400, detail="SPOC user not found")

    slug_base = payload.slug or _slugify(payload.name)
    slug = _unique_slug(db, Cohort, slug_base)

    try:
        cohort = Cohort(
            college_id=payload.college_id,
            course_id=payload.course_id,
            spoc_user_id=payload.spoc_user_id,
            name=payload.name,
            slug=slug,
            max_students=payload.max_students,
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            is_active=payload.is_active,
        )
        db.add(cohort)
        db.flush()  # get id

        # Generate unique referral code
        for _ in range(10):
            candidate = _generate_referral_code(cohort.slug)
            if not db.query(ReferralCode).filter(ReferralCode.code == candidate).first():
                break
        else:
            candidate = f"{cohort.slug.upper()}-{secrets.token_hex(3).upper()}"

        code = ReferralCode(
            cohort_id=cohort.id,
            code=candidate,
            max_uses=payload.referral_max_uses,
            used_count=0,
            expires_at=payload.referral_expires_at,
        )
        db.add(code)
        db.commit()
        db.refresh(cohort)
        return cohort
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create cohort: {e}")


@router.get("/admin/cohorts", response_model=List[CohortOut])
def admin_list_cohorts(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    return db.query(Cohort).order_by(Cohort.created_at.desc()).all()


@router.get("/admin/cohorts/{cohort_id}", response_model=CohortOut)
def admin_get_cohort(
    cohort_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return cohort


@router.put("/admin/cohorts/{cohort_id}", response_model=CohortOut)
def admin_update_cohort(
    cohort_id: int,
    payload: CohortUpdate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    try:
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(cohort, k, v)
        db.commit()
        db.refresh(cohort)
        return cohort
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update cohort: {e}")


@router.delete("/admin/cohorts/{cohort_id}")
def admin_delete_cohort(
    cohort_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    try:
        # Cascade cleanup BEFORE deleting the cohort:
        # 1) Detach enrollments (keep course access, drop cohort tag)
        db.query(Enrollment).filter(Enrollment.cohort_id == cohort_id).update(
            {Enrollment.cohort_id: None}, synchronize_session=False
        )

        # 2) Revoke cohort-scoped SPOC eligibility. Leave auto_certificate rows alone.
        try:
            from app.models.candidate import CandidateEligibility
            db.query(CandidateEligibility).filter(
                CandidateEligibility.cohort_id == cohort_id,
                CandidateEligibility.source == "spoc_approved",
            ).update(
                {CandidateEligibility.cohort_id: None, CandidateEligibility.eligible: False},
                synchronize_session=False,
            )
        except ImportError:
            # SS2 not deployed; nothing to revoke
            pass

        # 3) Detach (don't delete) coupons tied to this cohort — they remain as
        # plain discounts.
        db.query(Coupon).filter(Coupon.cohort_id == cohort_id).update(
            {Coupon.cohort_id: None}, synchronize_session=False
        )

        db.flush()
        db.delete(cohort)
        db.commit()
        return {"message": "Cohort deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete cohort: {e}")


# ------------------------------------------------------------------
# Admin — regenerate referral code
# ------------------------------------------------------------------

@router.post("/admin/cohorts/{cohort_id}/referral-code/regenerate", response_model=ReferralCodeOut)
def admin_regenerate_referral_code(
    cohort_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Issue a fresh referral code for a cohort. Invalidates the old one —
    any in-flight links using it stop working immediately."""
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    try:
        existing = db.query(ReferralCode).filter(ReferralCode.cohort_id == cohort_id).first()

        # Generate a unique new code
        new_code = None
        for _ in range(10):
            candidate = _generate_referral_code(cohort.slug)
            collision = db.query(ReferralCode).filter(ReferralCode.code == candidate).first()
            if not collision or (existing and collision.id == existing.id):
                new_code = candidate
                break
        if not new_code:
            new_code = f"{cohort.slug.upper()}-{secrets.token_hex(3).upper()}"

        if existing:
            db.delete(existing)
            db.flush()
            rc = ReferralCode(
                cohort_id=cohort_id,
                code=new_code,
                max_uses=existing.max_uses or 100,
                used_count=0,
                expires_at=existing.expires_at,
            )
        else:
            rc = ReferralCode(
                cohort_id=cohort_id,
                code=new_code,
                max_uses=100,
                used_count=0,
                expires_at=None,
            )
        db.add(rc)
        db.commit()
        db.refresh(rc)
        return rc
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to regenerate code: {e}")


# ------------------------------------------------------------------
# Admin — manual cohort membership management
# ------------------------------------------------------------------

@router.get("/admin/cohorts/{cohort_id}/members")
def admin_list_cohort_members(
    cohort_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """List the students in a cohort (admin view)."""
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    rows = (
        db.query(CohortMembership, User)
        .join(User, User.id == CohortMembership.user_id)
        .filter(CohortMembership.cohort_id == cohort_id)
        .order_by(CohortMembership.joined_at.desc())
        .all()
    )
    return [
        {
            "membership_id": m.id,
            "user_id": u.id,
            "email": u.user_email,
            "display_name": u.display_name,
            "joined_at": m.joined_at,
        }
        for (m, u) in rows
    ]


@router.post("/admin/cohorts/{cohort_id}/members", status_code=201)
def admin_add_cohort_member(
    cohort_id: int,
    payload: dict,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """
    Admin manually adds a student to a cohort. Body: {email} OR {user_id}.

    Side effects:
      - creates CohortMembership (idempotent)
      - creates an Enrollment in the cohort's course (idempotent);
        existing enrollments are stamped with cohort_id if currently null.
    """
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    email = (payload.get("email") or "").strip().lower()
    uid = payload.get("user_id")
    user = None
    if uid:
        user = db.query(User).filter(User.id == int(uid)).first()
    elif email:
        user = db.query(User).filter(sa_func.lower(User.user_email) == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Ask them to register first.")

    try:
        # Membership (idempotent)
        membership = db.query(CohortMembership).filter(
            CohortMembership.cohort_id == cohort_id,
            CohortMembership.user_id == user.id,
        ).first()
        if not membership:
            membership = CohortMembership(cohort_id=cohort_id, user_id=user.id)
            db.add(membership)
            db.flush()

        # Enrollment in the cohort's course (idempotent). Stamp cohort_id on
        # existing enrollments so the SPOC can see them under this cohort.
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == cohort.course_id,
            Enrollment.user_id == user.id,
        ).first()
        if not enrollment:
            total_lessons = db.query(Lesson).filter(Lesson.post_parent == cohort.course_id).count()
            enrollment = Enrollment(
                course_id=cohort.course_id,
                user_id=user.id,
                enrollment_status="enrolled",
                total_lessons=total_lessons,
                completed_lessons=0,
                cohort_id=cohort_id,
            )
            db.add(enrollment)
            # Atomic enrollment-count bump (same pattern as /courses/{id}/enroll)
            db.query(Course).filter(Course.id == cohort.course_id).update(
                {Course.total_enrollments: (Course.total_enrollments or 0) + 1},
                synchronize_session=False,
            )
        elif getattr(enrollment, "cohort_id", None) is None:
            enrollment.cohort_id = cohort_id

        db.commit()
        db.refresh(membership)
        return {
            "membership_id": membership.id,
            "user_id": user.id,
            "email": user.user_email,
            "display_name": user.display_name,
            "joined_at": membership.joined_at,
            "enrollment_id": enrollment.id,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to add member: {e}")


@router.delete("/admin/cohorts/{cohort_id}/members/{user_id}")
def admin_remove_cohort_member(
    cohort_id: int,
    user_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Remove a student from a cohort (clears cohort_id on enrollment, deletes membership).
    Does NOT delete the enrollment itself — student keeps course access."""
    membership = db.query(CohortMembership).filter(
        CohortMembership.cohort_id == cohort_id,
        CohortMembership.user_id == user_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this cohort")
    try:
        # 1) Null cohort_id on the matching enrollment (keep enrollment alive)
        enrollment = db.query(Enrollment).filter(
            Enrollment.cohort_id == cohort_id,
            Enrollment.user_id == user_id,
        ).first()
        if enrollment:
            enrollment.cohort_id = None

        # 2) Revoke cohort-scoped SPOC eligibility for this user, if any.
        # Leave auto_certificate-earned rows alone.
        try:
            from app.models.candidate import CandidateEligibility
            elig = db.query(CandidateEligibility).filter(
                CandidateEligibility.user_id == user_id,
                CandidateEligibility.cohort_id == cohort_id,
                CandidateEligibility.source == "spoc_approved",
            ).first()
            if elig:
                elig.cohort_id = None
                elig.eligible = False
        except ImportError:
            pass

        db.delete(membership)
        db.commit()
        return {"message": "Member removed from cohort"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to remove member: {e}")


# ==================================================================
# SPOC
# ==================================================================

@router.get("/spoc/my-cohorts", response_model=List[CohortOut])
def spoc_my_cohorts(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    return (
        db.query(Cohort)
        .filter(Cohort.spoc_user_id == current_user.id)
        .order_by(Cohort.created_at.desc())
        .all()
    )


@router.get("/spoc/cohorts/{cohort_id}/roster", response_model=List[RosterRow])
def spoc_roster(
    cohort_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    _ensure_spoc_owns_cohort(db, cohort_id, current_user)

    memberships = (
        db.query(CohortMembership, User)
        .join(User, User.id == CohortMembership.user_id)
        .filter(CohortMembership.cohort_id == cohort_id)
        .all()
    )

    if not memberships:
        return []

    user_ids = [u.id for _, u in memberships]

    # Activity today: any LessonProgress.updated_at or QuizAttempt.attempt_started_at today
    today = date.today()
    day_start = datetime.combine(today, time.min)
    day_end = datetime.combine(today, time.max)

    active_lesson_user_ids = {
        uid for (uid,) in db.query(LessonProgress.user_id)
        .filter(
            LessonProgress.user_id.in_(user_ids),
            LessonProgress.updated_at >= day_start,
            LessonProgress.updated_at <= day_end,
        )
        .distinct()
        .all()
    }
    active_quiz_user_ids = {
        uid for (uid,) in db.query(QuizAttempt.user_id)
        .filter(
            QuizAttempt.user_id.in_(user_ids),
            QuizAttempt.attempt_started_at >= day_start,
            QuizAttempt.attempt_started_at <= day_end,
        )
        .distinct()
        .all()
    }
    active_today = active_lesson_user_ids | active_quiz_user_ids

    rows: List[RosterRow] = []
    for membership, user in memberships:
        rows.append(RosterRow(
            user_id=user.id,
            display_name=user.display_name or user.user_login,
            email=user.user_email,
            joined_at=membership.joined_at,
            active_today=user.id in active_today,
        ))
    return rows


@router.get("/spoc/cohorts/{cohort_id}/task-stats", response_model=List[TaskStatsRow])
def spoc_task_stats(
    cohort_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    cohort = _ensure_spoc_owns_cohort(db, cohort_id, current_user)

    memberships = (
        db.query(CohortMembership, User)
        .join(User, User.id == CohortMembership.user_id)
        .filter(CohortMembership.cohort_id == cohort_id)
        .all()
    )
    if not memberships:
        return []
    user_ids = [u.id for _, u in memberships]

    # Lessons completed (scoped to cohort course via LessonProgress.course_id)
    lesson_counts = dict(
        db.query(LessonProgress.user_id, sa_func.count(LessonProgress.id))
        .filter(
            LessonProgress.user_id.in_(user_ids),
            LessonProgress.course_id == cohort.course_id,
            LessonProgress.progress_status == "completed",
        )
        .group_by(LessonProgress.user_id)
        .all()
    )

    quiz_counts = dict(
        db.query(QuizAttempt.user_id, sa_func.count(QuizAttempt.attempt_id))
        .filter(
            QuizAttempt.user_id.in_(user_ids),
            QuizAttempt.course_id == cohort.course_id,
        )
        .group_by(QuizAttempt.user_id)
        .all()
    )

    assignment_counts = dict(
        db.query(AssignmentSubmission.user_id, sa_func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.user_id.in_(user_ids))
        .group_by(AssignmentSubmission.user_id)
        .all()
    )

    rows: List[TaskStatsRow] = []
    for _, user in memberships:
        rows.append(TaskStatsRow(
            user_id=user.id,
            display_name=user.display_name or user.user_login,
            completed_lessons=int(lesson_counts.get(user.id, 0)),
            quiz_attempts=int(quiz_counts.get(user.id, 0)),
            assignment_submissions=int(assignment_counts.get(user.id, 0)),
        ))
    return rows


# ------- Sessions CRUD -------

@router.post("/spoc/cohorts/{cohort_id}/sessions", response_model=SessionOut)
def spoc_create_session(
    cohort_id: int,
    payload: SessionCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    _ensure_spoc_owns_cohort(db, cohort_id, current_user)
    scheduled_at = _validate_scheduled_at(payload.scheduled_at)
    try:
        sess = CohortSession(
            cohort_id=cohort_id,
            scheduled_at=scheduled_at,
            duration_minutes=payload.duration_minutes,
            topic=payload.topic,
            session_type=payload.session_type,
            created_by=current_user.id,
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)
        return sess
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create session: {e}")


@router.get("/spoc/cohorts/{cohort_id}/sessions", response_model=List[SessionOut])
def spoc_list_sessions(
    cohort_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    _ensure_spoc_owns_cohort(db, cohort_id, current_user)
    return (
        db.query(CohortSession)
        .filter(CohortSession.cohort_id == cohort_id)
        .order_by(CohortSession.scheduled_at.desc())
        .all()
    )


@router.get("/spoc/cohorts/{cohort_id}/sessions/{session_id}", response_model=SessionOut)
def spoc_get_session(
    cohort_id: int,
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    _ensure_spoc_owns_cohort(db, cohort_id, current_user)
    sess = db.query(CohortSession).filter(
        CohortSession.id == session_id, CohortSession.cohort_id == cohort_id
    ).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return sess


@router.put("/spoc/cohorts/{cohort_id}/sessions/{session_id}", response_model=SessionOut)
def spoc_update_session(
    cohort_id: int,
    session_id: int,
    payload: SessionUpdate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    _ensure_spoc_owns_cohort(db, cohort_id, current_user)
    sess = db.query(CohortSession).filter(
        CohortSession.id == session_id, CohortSession.cohort_id == cohort_id
    ).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        data = payload.model_dump(exclude_unset=True)
        if "scheduled_at" in data and data["scheduled_at"] is not None:
            data["scheduled_at"] = _validate_scheduled_at(data["scheduled_at"])
        for k, v in data.items():
            setattr(sess, k, v)
        db.commit()
        db.refresh(sess)
        return sess
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update session: {e}")


@router.delete("/spoc/cohorts/{cohort_id}/sessions/{session_id}")
def spoc_delete_session(
    cohort_id: int,
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    _ensure_spoc_owns_cohort(db, cohort_id, current_user)
    sess = db.query(CohortSession).filter(
        CohortSession.id == session_id, CohortSession.cohort_id == cohort_id
    ).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        db.delete(sess)
        db.commit()
        return {"message": "Session deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete session: {e}")


# ------- Bulk attendance -------

@router.post("/spoc/sessions/{session_id}/attendance")
def spoc_bulk_mark_attendance(
    session_id: int,
    payload: BulkAttendanceRequest,
    response: Response,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    sess = db.query(CohortSession).filter(CohortSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    _ensure_spoc_owns_cohort(db, sess.cohort_id, current_user)

    # Restrict entries to cohort members
    member_ids = {
        uid for (uid,) in db.query(CohortMembership.user_id)
        .filter(CohortMembership.cohort_id == sess.cohort_id)
        .all()
    }

    results: List[SessionAttendance] = []
    skipped: List[dict] = []
    try:
        for entry in payload.entries:
            if entry.user_id not in member_ids:
                skipped.append({"user_id": entry.user_id, "reason": "not_a_member"})
                continue
            row = db.query(SessionAttendance).filter(
                SessionAttendance.session_id == session_id,
                SessionAttendance.user_id == entry.user_id,
            ).first()
            if row:
                row.status = entry.status
                row.notes = entry.notes or ""
                row.marked_by = current_user.id
                row.marked_at = datetime.now(timezone.utc)
            else:
                row = SessionAttendance(
                    session_id=session_id,
                    user_id=entry.user_id,
                    status=entry.status,
                    notes=entry.notes or "",
                    marked_by=current_user.id,
                )
                db.add(row)
            results.append(row)
        db.commit()
        for r in results:
            db.refresh(r)

        marked = [
            AttendanceOut.model_validate(r, from_attributes=True).model_dump()
            for r in results
        ]
        if skipped:
            response.status_code = status.HTTP_207_MULTI_STATUS
        return {"marked": marked, "skipped": skipped}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to save attendance: {e}")


# ------- SS2 handoff: SPOC greenlight -------

@router.post("/spoc/students/{user_id}/internship-eligible", response_model=EligibilityToggleOut)
def spoc_set_eligibility(
    user_id: int,
    payload: EligibilityToggleRequest,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc),
):
    # Verify the target user belongs to at least one cohort owned by this SPOC
    membership_cohort = (
        db.query(CohortMembership, Cohort)
        .join(Cohort, Cohort.id == CohortMembership.cohort_id)
        .filter(
            CohortMembership.user_id == user_id,
            Cohort.spoc_user_id == current_user.id,
        )
        .first()
    )
    if not membership_cohort:
        raise HTTPException(
            status_code=403,
            detail="Target student is not in any cohort owned by you",
        )
    _, cohort = membership_cohort

    # Deferred import — SS2 model may not have landed yet
    try:
        from app.models.candidate import CandidateEligibility
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Candidate eligibility module not available (SS2 not deployed)",
        )

    try:
        row = db.query(CandidateEligibility).filter(
            CandidateEligibility.user_id == user_id
        ).first()
        if row:
            # Preserve `source='auto_certificate'` on updates — the SPOC
            # action confirms eligibility but does not overwrite how it
            # was originally earned. Only upgrade source on brand-new
            # rows (handled in the else branch).
            if row.source != "auto_certificate":
                row.source = "spoc_approved"
            row.eligible = payload.eligible
            row.reason = payload.reason or ""
            row.decided_by = current_user.id
            row.decided_at = datetime.now(timezone.utc)
            row.cohort_id = cohort.id
        else:
            row = CandidateEligibility(
                user_id=user_id,
                source="spoc_approved",
                eligible=payload.eligible,
                reason=payload.reason or "",
                decided_by=current_user.id,
                cohort_id=cohort.id,
            )
            db.add(row)
        db.commit()
        db.refresh(row)
        return EligibilityToggleOut(
            user_id=row.user_id,
            eligible=row.eligible,
            source=row.source,
            cohort_id=row.cohort_id,
            decided_by=row.decided_by,
            reason=row.reason or "",
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to save eligibility: {e}")


# ==================================================================
# R10 — Institution features: class-wise mastery (SPOC + admin)
# ==================================================================

def _cohort_mastery_payload(db: DBSession, cohort: Cohort) -> dict:
    """Aggregate the learner-scoped mastery graph over a cohort's members:
    per-concept class average + how many sit below 50%, per-student overall
    + weakest concept + at-risk flag. Derived at read time, never stored."""
    from collections import defaultdict
    from app.models.mastery import LearnerMastery
    from app.models.sileos_pack import StudentRiskFlag
    members = [uid for (uid,) in db.query(CohortMembership.user_id).filter(CohortMembership.cohort_id == cohort.id).all()]
    if not members:
        return {"cohort_id": cohort.id, "members": 0, "concepts": [], "students": [], "class_average": None}
    names = {u.id: u.display_name for u in db.query(User).filter(User.id.in_(members)).all()}
    rows = db.query(LearnerMastery).filter(LearnerMastery.user_id.in_(members), LearnerMastery.evidence_count >= 1).all()
    by_concept = defaultdict(list)
    by_student = defaultdict(list)
    for r in rows:
        by_concept[r.concept].append(r.estimate)
        by_student[r.user_id].append((r.concept, r.estimate))
    concepts = sorted(({"concept": c, "average": round(sum(v) / len(v), 1), "learners": len(v), "below_50": sum(1 for x in v if x < 50)}
                       for c, v in by_concept.items()), key=lambda x: (x["average"], -x["learners"]))
    risk = {}
    if cohort.course_id:
        for f in db.query(StudentRiskFlag).filter(StudentRiskFlag.course_id == cohort.course_id, StudentRiskFlag.user_id.in_(members)).all():
            risk[f.user_id] = {"severity": f.severity, "reasons": f.reasons}
    students = []
    for uid in members:
        ests = by_student.get(uid, [])
        weakest = min(ests, key=lambda t: t[1]) if ests else None
        students.append({"user_id": uid, "name": names.get(uid, f"#{uid}"),
                         "average": round(sum(e for _, e in ests) / len(ests), 1) if ests else None,
                         "concepts": len(ests), "weakest": weakest[0] if weakest else None,
                         "weakest_estimate": round(weakest[1], 1) if weakest else None, "risk": risk.get(uid)})
    students.sort(key=lambda x: (x["average"] is None, x["average"] if x["average"] is not None else 0))
    averages = [x["average"] for x in students if x["average"] is not None]
    return {"cohort_id": cohort.id, "cohort_name": cohort.name, "course_id": cohort.course_id, "members": len(members),
            "class_average": round(sum(averages) / len(averages), 1) if averages else None,
            "concepts": concepts[:40], "students": students}


@router.get("/spoc/cohorts/{cohort_id}/mastery")
async def spoc_cohort_mastery(cohort_id: int, db: DBSession = Depends(get_db),
                              current_user: User = Depends(AuthService.get_current_active_user)):
    cohort = db.query(Cohort).filter(Cohort.id == cohort_id).first()
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    if current_user.role not in ("admin", "superadmin"):
        allowed = cohort.spoc_user_id == current_user.id
        if not allowed and cohort.course_id:
            from app.services.course_access import can_edit
            course = db.query(Course).filter(Course.id == cohort.course_id).first()
            allowed = can_edit(db, course, current_user)
        if not allowed:
            raise HTTPException(status_code=403, detail="This cohort does not belong to you")
    return _cohort_mastery_payload(db, cohort)


@router.get("/admin/colleges/{college_id}/mastery")
async def college_mastery(college_id: int, db: DBSession = Depends(get_db),
                          current_user: User = Depends(AuthService.require_admin)):
    """School dashboard: one row per cohort with class average and at-risk count."""
    cohorts = db.query(Cohort).filter(Cohort.college_id == college_id).order_by(Cohort.name.asc()).all()
    out = []
    for c in cohorts:
        pl = _cohort_mastery_payload(db, c)
        out.append({"cohort_id": c.id, "cohort_name": c.name, "course_id": c.course_id, "members": pl["members"],
                    "class_average": pl["class_average"], "at_risk": sum(1 for s in pl["students"] if s["risk"]),
                    "weakest_concept": pl["concepts"][0]["concept"] if pl["concepts"] else None})
    return {"college_id": college_id, "cohorts": out}
