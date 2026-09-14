"""
Company dashboard v2 — operational dashboard for companies.

Mounted at /api/v1/companies/me (and /api/v1/companies for setup-token flows).
"""
import secrets as _secrets
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response
from jose import JWTError, jwt
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    ALGORITHM, create_access_token, get_password_hash,
)
from app.models.user import User
from app.models.company import Company
from app.models.company_dashboard import CompanyManager, DailyWorkLog
from app.models.internship import InternshipAttendance, Internship, InternshipVoucher
from app.models.internship_request import InternshipRequest
from app.models.candidate import CandidateProfile
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.schemas.company_dashboard import (
    ManagerInviteRequest, ManagerResponse, ManagerCompleteSetupRequest,
    OverviewResponse,
    StudentListItem, StudentListResponse, StudentPatchRequest,
    CompanyInternshipItem, CompanyInternshipListResponse,
    AttendanceEntry, AttendanceGridResponse, AttendanceUpsertRequest,
    WorkLogItem, WorkLogListResponse, WorkLogReviewRequest,
    AnnouncementCreateRequest, AnnouncementItem, AnnouncementListResponse,
    PerformanceReviewCreateRequest, PerformanceReviewItem,
    InternshipRequestCreate, InternshipRequestItem, InternshipRequestListResponse,
)
from app.services.auth_service import AuthService
from app.services.company_scope import get_my_company, require_owner, assigned_voucher_query
from app.services.email_service import EmailService
from app.services.attendance_report import build_rows, render_csv, render_pdf

router = APIRouter()
settings = get_settings()

MANAGER_SETUP_TOKEN_TTL_DAYS = 7

# Company-facing engagement status for a student's internship placement.
# Kept separate from InternshipVoucher.status ('issued'/'redeemed', which
# drives coupon/redemption logic elsewhere and must never be written by
# this endpoint).
ALLOWED_ENGAGEMENT_STATUSES = {"active", "completed", "closed"}


# ---------------- Helpers ----------------

def _mint_manager_setup_token(email: str, manager_link_id: int) -> str:
    payload = {
        "sub": email,
        "manager_link_id": manager_link_id,
        "type": "manager_setup",
        "exp": datetime.now(timezone.utc) + timedelta(days=MANAGER_SETUP_TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _verify_manager_setup_token(token: str) -> tuple[str, int]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if payload.get("type") != "manager_setup":
        raise HTTPException(status_code=400, detail="Wrong token type")
    return payload["sub"], int(payload["manager_link_id"])


# ---------------- Manager endpoints ----------------

@router.post("/me/managers", response_model=ManagerResponse, status_code=201)
def invite_manager(
    body: ManagerInviteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    company = get_my_company(db, user)

    # Find or create the user
    target = db.query(User).filter(User.user_email == body.email).first()
    if target is None:
        login = body.email.split("@")[0][:50] or "manager"
        base_login = login
        n = 2
        while db.query(User).filter(User.user_login == login).first() is not None:
            login = f"{base_login}{n}"[:60]
            n += 1
        target = User(
            user_login=login,
            user_pass=get_password_hash(_secrets.token_urlsafe(32)),
            user_nicename=login,
            user_email=body.email,
            display_name=body.name,
            role="company_manager",
            is_active=True,
            is_verified=False,
        )
        db.add(target)
        db.flush()
    else:
        if target.role not in ("company_manager",):
            raise HTTPException(
                status_code=400,
                detail=f"User already exists with role={target.role}",
            )

    # Don't double-link
    existing = db.query(CompanyManager).filter(CompanyManager.user_id == target.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already a manager")

    link = CompanyManager(
        company_id=company.id,
        user_id=target.id,
        invited_by=user.id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    token = _mint_manager_setup_token(target.user_email, link.id)
    try:
        EmailService.send_manager_setup_link_email(target.user_email, token)
    except Exception:
        pass  # email failures shouldn't roll back the invite

    return ManagerResponse(
        id=link.id,
        user_id=target.id,
        email=target.user_email,
        name=target.display_name,
        accepted_at=link.accepted_at,
        invited_at=link.invited_at,
        setup_token=token,
    )


@router.get("/me/managers", response_model=List[ManagerResponse])
def list_managers(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = get_my_company(db, user)
    rows = (
        db.query(CompanyManager, User)
        .join(User, User.id == CompanyManager.user_id)
        .filter(CompanyManager.company_id == company.id)
        .order_by(CompanyManager.invited_at.desc())
        .all()
    )
    return [
        ManagerResponse(
            id=link.id,
            user_id=u.id,
            email=u.user_email,
            name=u.display_name,
            accepted_at=link.accepted_at,
            invited_at=link.invited_at,
        )
        for link, u in rows
    ]


@router.delete("/me/managers/{manager_id}", status_code=204)
def revoke_manager(
    manager_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    company = get_my_company(db, user)
    link = db.query(CompanyManager).filter(
        CompanyManager.id == manager_id,
        CompanyManager.company_id == company.id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Manager not found")
    db.delete(link)
    db.commit()
    return


@router.post("/managers/complete-setup")
def complete_manager_setup(
    body: ManagerCompleteSetupRequest,
    db: Session = Depends(get_db),
):
    email, link_id = _verify_manager_setup_token(body.token)
    link = db.query(CompanyManager).filter(CompanyManager.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Invite not found")
    user = db.query(User).filter(User.id == link.user_id).first()
    if not user or user.user_email != email:
        raise HTTPException(status_code=404, detail="User not found")

    user.user_pass = get_password_hash(body.password)
    user.is_verified = True
    link.accepted_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok"}


# ---------------- Overview endpoint ----------------

@router.get("/me/overview", response_model=OverviewResponse)
def overview(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    vouchers = assigned_voucher_query(db, user).all()
    student_ids = [v.buyer_user_id for v in vouchers]
    internship_ids = list({v.internship_id for v in vouchers})

    today = date.today()
    week_ago = today - timedelta(days=6)

    today_rows = (
        db.query(InternshipAttendance)
        .filter(
            InternshipAttendance.user_id.in_(student_ids or [-1]),
            InternshipAttendance.internship_id.in_(internship_ids or [-1]),
            InternshipAttendance.attended_at == today,
        )
        .all()
    )
    by_status = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    for r in today_rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    not_marked = len(student_ids) - sum(by_status.values())

    week_rows = (
        db.query(InternshipAttendance.status, sa_func.count())
        .filter(
            InternshipAttendance.user_id.in_(student_ids or [-1]),
            InternshipAttendance.internship_id.in_(internship_ids or [-1]),
            InternshipAttendance.attended_at >= week_ago,
        )
        .group_by(InternshipAttendance.status)
        .all()
    )
    week_total = sum(c for _, c in week_rows)
    week_present = sum(c for s, c in week_rows if s in ("present", "late"))
    week_pct = (week_present / week_total * 100) if week_total else 0.0

    pending_reviews = (
        db.query(sa_func.count(DailyWorkLog.id))
        .filter(
            DailyWorkLog.student_user_id.in_(student_ids or [-1]),
            DailyWorkLog.review_status == "pending",
        )
        .scalar()
        or 0
    )

    activity = []  # placeholder — can be extended later

    return OverviewResponse(
        active_interns=len(student_ids),
        active_internships=len(internship_ids),
        week_attendance_pct=round(week_pct, 1),
        pending_work_log_reviews=pending_reviews,
        today_present=by_status.get("present", 0),
        today_absent=by_status.get("absent", 0),
        today_late=by_status.get("late", 0),
        today_excused=by_status.get("excused", 0),
        today_not_marked=max(not_marked, 0),
        activity=activity,
    )


# ---------------- Students endpoints ----------------

def _calculate_student_progress(user_id: int, db: Session) -> float:
    """
    Calculate student's course progress percentage.
    Returns the average progress across all enrolled courses.
    If no enrollments exist, returns 0.0.
    """
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user_id
    ).all()
    if not enrollments:
        return 0.0
    # Average of course_progress_percentage across all enrollments
    total_progress = sum(e.course_progress_percentage or 0 for e in enrollments)
    return round(total_progress / len(enrollments), 1)


def _calculate_student_attendance(user_id: int, internship_id: int, db: Session) -> float:
    """
    Calculate student's attendance percentage for an internship.
    Returns the percentage of days marked as 'present' or 'late' out of all
    days where attendance has been marked.
    """
    attendance_records = db.query(InternshipAttendance).filter(
        InternshipAttendance.user_id == user_id,
        InternshipAttendance.internship_id == internship_id,
    ).all()
    if not attendance_records:
        return 0.0
    present_days = sum(1 for a in attendance_records if a.status in ('present', 'late'))
    return round(present_days / len(attendance_records) * 100, 1)


@router.get("/me/students", response_model=StudentListResponse)
def list_students(
    internship_id: Optional[int] = None,
    manager_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    q = assigned_voucher_query(db, user)
    if internship_id is not None:
        q = q.filter(InternshipVoucher.internship_id == internship_id)
    if manager_id is not None:
        q = q.filter(InternshipVoucher.reporting_manager_user_id == manager_id)
    vouchers = q.all()

    # Bulk fetch ancillaries
    user_ids = {v.buyer_user_id for v in vouchers}
    intern_ids = {v.internship_id for v in vouchers}
    mgr_ids = {v.reporting_manager_user_id for v in vouchers if v.reporting_manager_user_id}
    students = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids or [-1])).all()}
    interns = {i.id: i for i in db.query(Internship).filter(Internship.id.in_(intern_ids or [-1])).all()}
    mgrs = {u.id: u for u in db.query(User).filter(User.id.in_(mgr_ids or [-1])).all()} if mgr_ids else {}
    # Fetch candidate profiles for resume and links
    candidates = {c.user_id: c for c in db.query(CandidateProfile).filter(CandidateProfile.user_id.in_(user_ids or [-1])).all()}

    items = []
    for v in vouchers:
        s = students.get(v.buyer_user_id)
        i = interns.get(v.internship_id)
        if not s or not i:
            continue
        if search and search.lower() not in (s.display_name + s.user_email).lower():
            continue
        cand = candidates.get(s.id)
        # Calculate progress and attendance percentages
        progress_pct = _calculate_student_progress(s.id, db)
        attendance_pct = _calculate_student_attendance(s.id, i.id, db)
        items.append(StudentListItem(
            user_id=s.id,
            voucher_id=v.id,
            name=s.display_name,
            email=s.user_email,
            internship_id=i.id,
            internship_title=i.title,
            progress_pct=progress_pct,
            attendance_pct=attendance_pct,
            reporting_manager_user_id=v.reporting_manager_user_id,
            reporting_manager_name=mgrs[v.reporting_manager_user_id].display_name
                if v.reporting_manager_user_id else None,
            cert_status="none",
            notes=v.company_notes or "",
            internship_status=v.engagement_status or "active",
            resume_url=cand.resume_url if cand else None,
            linkedin_url=cand.linkedin_url if cand else None,
            github_url=cand.github_url if cand else None,
            portfolio_url=cand.portfolio_url if cand else None,
        ))
    return StudentListResponse(items=items, total=len(items))


@router.get("/me/students/{user_id}", response_model=StudentListItem)
def get_student(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    v = assigned_voucher_query(db, user).filter(
        InternshipVoucher.buyer_user_id == user_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Student not found")
    s = db.query(User).filter(User.id == user_id).first()
    i = db.query(Internship).filter(Internship.id == v.internship_id).first()
    mgr = (db.query(User).filter(User.id == v.reporting_manager_user_id).first()
           if v.reporting_manager_user_id else None)
    cand = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    # Calculate progress and attendance percentages
    progress_pct = _calculate_student_progress(s.id, db)
    attendance_pct = _calculate_student_attendance(s.id, i.id, db)
    return StudentListItem(
        user_id=s.id, voucher_id=v.id, name=s.display_name, email=s.user_email,
        internship_id=i.id, internship_title=i.title,
        progress_pct=progress_pct, attendance_pct=attendance_pct,
        reporting_manager_user_id=v.reporting_manager_user_id,
        reporting_manager_name=mgr.display_name if mgr else None,
        cert_status="none", notes=v.company_notes or "",
        internship_status=v.engagement_status or "active",
        resume_url=cand.resume_url if cand else None,
        linkedin_url=cand.linkedin_url if cand else None,
        github_url=cand.github_url if cand else None,
        portfolio_url=cand.portfolio_url if cand else None,
    )


@router.patch("/me/students/{user_id}", response_model=StudentListItem)
def patch_student(
    user_id: int,
    body: StudentPatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    v = assigned_voucher_query(db, user).filter(
        InternshipVoucher.buyer_user_id == user_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Student not found")
    if body.reporting_manager_user_id is not None:
        # Validate the manager belongs to this company
        company = get_my_company(db, user)
        ok = db.query(CompanyManager).filter(
            CompanyManager.company_id == company.id,
            CompanyManager.user_id == body.reporting_manager_user_id,
        ).first()
        if not ok and body.reporting_manager_user_id != company.owner_user_id:
            raise HTTPException(status_code=400, detail="Manager not in this company")
        v.reporting_manager_user_id = body.reporting_manager_user_id
    if body.notes is not None:
        v.company_notes = body.notes
    if body.internship_status is not None:
        if body.internship_status not in ALLOWED_ENGAGEMENT_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Invalid internship_status "
                    f"{body.internship_status!r}. Must be one of: "
                    f"{sorted(ALLOWED_ENGAGEMENT_STATUSES)}"
                ),
            )
        v.engagement_status = body.internship_status
    db.commit(); db.refresh(v)

    # Fetch and return updated student data (duplicate logic from get_student)
    s = db.query(User).filter(User.id == user_id).first()
    i = db.query(Internship).filter(Internship.id == v.internship_id).first()
    mgr = (db.query(User).filter(User.id == v.reporting_manager_user_id).first()
           if v.reporting_manager_user_id else None)
    cand = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    # Calculate progress and attendance percentages
    progress_pct = _calculate_student_progress(s.id, db)
    attendance_pct = _calculate_student_attendance(s.id, i.id, db)
    return StudentListItem(
        user_id=s.id, voucher_id=v.id, name=s.display_name, email=s.user_email,
        internship_id=i.id, internship_title=i.title,
        progress_pct=progress_pct, attendance_pct=attendance_pct,
        reporting_manager_user_id=v.reporting_manager_user_id,
        reporting_manager_name=mgr.display_name if mgr else None,
        cert_status="none", notes=v.company_notes or "",
        internship_status=v.engagement_status or "active",
        resume_url=cand.resume_url if cand else None,
        linkedin_url=cand.linkedin_url if cand else None,
        github_url=cand.github_url if cand else None,
        portfolio_url=cand.portfolio_url if cand else None,
    )


# ---------------- Internships endpoints ----------------

@router.get("/me/internships", response_model=CompanyInternshipListResponse)
def list_company_internships(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    vouchers = assigned_voucher_query(db, user).all()
    by_iid: dict[int, list] = {}
    for v in vouchers:
        by_iid.setdefault(v.internship_id, []).append(v)

    interns = (db.query(Internship)
               .filter(Internship.id.in_(by_iid.keys() or [-1]))
               .all())
    spocs = {u.id: u for u in db.query(User).filter(
        User.id.in_({i.spoc_user_id for i in interns} or [-1])
    ).all()}

    items = []
    for i in interns:
        # Calculate average progress for students in this internship
        student_ids = [v.buyer_user_id for v in by_iid[i.id]]
        if student_ids:
            progress_values = [_calculate_student_progress(sid, db) for sid in student_ids]
            avg_progress_pct = round(sum(progress_values) / len(progress_values), 1) if progress_values else 0.0
        else:
            avg_progress_pct = 0.0
        items.append(CompanyInternshipItem(
            id=i.id, title=i.title, slug=i.slug, cover_image=i.cover_image or "",
            student_count=len(by_iid[i.id]),
            avg_progress_pct=avg_progress_pct,
            spoc_name=spocs.get(i.spoc_user_id).display_name if spocs.get(i.spoc_user_id) else None,
        ))
    return CompanyInternshipListResponse(items=items)


@router.get("/me/internships/{internship_id}", response_model=CompanyInternshipItem)
def get_company_internship(
    internship_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    vouchers = assigned_voucher_query(db, user).filter(
        InternshipVoucher.internship_id == internship_id
    ).all()
    if not vouchers:
        raise HTTPException(status_code=404, detail="Internship not in your scope")
    i = db.query(Internship).filter(Internship.id == internship_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Internship not found")
    spoc = db.query(User).filter(User.id == i.spoc_user_id).first()
    # Calculate average progress for students in this internship
    student_ids = [v.buyer_user_id for v in vouchers]
    if student_ids:
        progress_values = [_calculate_student_progress(sid, db) for sid in student_ids]
        avg_progress_pct = round(sum(progress_values) / len(progress_values), 1) if progress_values else 0.0
    else:
        avg_progress_pct = 0.0
    return CompanyInternshipItem(
        id=i.id, title=i.title, slug=i.slug, cover_image=i.cover_image or "",
        student_count=len(vouchers), avg_progress_pct=avg_progress_pct,
        spoc_name=spoc.display_name if spoc else None,
    )


# ---------------- Attendance endpoints ----------------

@router.get("/me/attendance", response_model=AttendanceGridResponse)
def get_attendance_grid(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    vouchers = assigned_voucher_query(db, user).all()
    student_ids = [v.buyer_user_id for v in vouchers]
    internship_ids = [v.internship_id for v in vouchers]

    if not from_date:
        from_date = date.today() - timedelta(days=13)
    if not to_date:
        to_date = date.today()

    attendance = (
        db.query(InternshipAttendance)
        .filter(
            InternshipAttendance.user_id.in_(student_ids or [-1]),
            InternshipAttendance.internship_id.in_(internship_ids or [-1]),
            InternshipAttendance.attended_at >= from_date,
            InternshipAttendance.attended_at <= to_date,
        )
        .all()
    )

    students_map = {u.id: u for u in db.query(User).filter(User.id.in_(student_ids or [-1])).all()}
    students_data = []
    for v in vouchers:
        s = students_map.get(v.buyer_user_id)
        if s:
            entries = [
                {
                    "id": a.id,
                    "date": a.attended_at.isoformat(),
                    "status": a.status,
                    "hours_worked": float(a.hours_worked) if a.hours_worked else 0.0,
                    "notes": a.notes or "",
                }
                for a in attendance
                if a.user_id == s.id
            ]
            students_data.append({
                "user_id": s.id,
                "name": s.display_name,
                "email": s.user_email,
                "voucher_id": v.id,
                "entries": entries,
            })

    dates = [(from_date + timedelta(days=i)) for i in range((to_date - from_date).days + 1)]

    return AttendanceGridResponse(students=students_data, dates=dates)


@router.post("/me/attendance")
def upsert_attendance(
    body: AttendanceUpsertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    # Get scoped student IDs to validate
    vouchers = assigned_voucher_query(db, user).all()
    scoped_student_ids = {v.buyer_user_id: v.internship_id for v in vouchers}

    for entry in body.entries:
        if entry.student_user_id not in scoped_student_ids:
            raise HTTPException(status_code=404, detail="Student not in your scope")
        if entry.internship_id != scoped_student_ids[entry.student_user_id]:
            raise HTTPException(status_code=400, detail="Internship mismatch for student")

    for entry in body.entries:
        existing = db.query(InternshipAttendance).filter(
            InternshipAttendance.user_id == entry.student_user_id,
            InternshipAttendance.internship_id == entry.internship_id,
            InternshipAttendance.attended_at == entry.date,
        ).first()

        if existing:
            existing.status = entry.status
            existing.hours_worked = entry.hours_worked
            existing.notes = entry.notes
        else:
            new_att = InternshipAttendance(
                user_id=entry.student_user_id,
                internship_id=entry.internship_id,
                attended_at=entry.date,
                status=entry.status,
                hours_worked=entry.hours_worked,
                notes=entry.notes,
            )
            db.add(new_att)

    db.commit()
    return {"status": "ok"}


# ---------------- Work Logs endpoints ----------------

@router.get("/me/work-logs", response_model=WorkLogListResponse)
def list_work_logs(
    student_id: Optional[int] = Query(None),
    internship_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.models.company_dashboard import DailyWorkLog
    vouchers = assigned_voucher_query(db, user).all()
    student_ids = [v.buyer_user_id for v in vouchers]
    internship_ids = [v.internship_id for v in vouchers]

    q = db.query(DailyWorkLog).filter(
        DailyWorkLog.student_user_id.in_(student_ids or [-1]),
        DailyWorkLog.internship_id.in_(internship_ids or [-1]),
    )
    if student_id:
        q = q.filter(DailyWorkLog.student_user_id == student_id)
    if internship_id:
        q = q.filter(DailyWorkLog.internship_id == internship_id)
    if status:
        q = q.filter(DailyWorkLog.review_status == status)

    logs = q.order_by(DailyWorkLog.log_date.desc()).all()

    # Fetch related data
    user_ids = {l.student_user_id for l in logs}
    intern_ids = {l.internship_id for l in logs}
    reviewer_ids = {l.reviewed_by for l in logs if l.reviewed_by}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(list(user_ids | reviewer_ids) or [-1])).all()}
    interns = {i.id: i for i in db.query(Internship).filter(Internship.id.in_(intern_ids or [-1])).all()}

    items = []
    for l in logs:
        student = users.get(l.student_user_id)
        intern = interns.get(l.internship_id)
        reviewer = users.get(l.reviewed_by) if l.reviewed_by else None
        if student and intern:
            items.append(WorkLogItem(
                id=l.id,
                student_user_id=l.student_user_id,
                student_name=student.display_name,
                internship_id=l.internship_id,
                internship_title=intern.title,
                log_date=l.log_date,
                content=l.content,
                attachment_url=l.attachment_url,
                review_status=l.review_status,
                reviewed_by_name=reviewer.display_name if reviewer else None,
                reviewer_comment=l.reviewer_comment,
            ))
    return WorkLogListResponse(items=items, total=len(items))


@router.post("/me/work-logs/{log_id}/review")
def review_work_log(
    log_id: int,
    body: WorkLogReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.models.company_dashboard import DailyWorkLog
    vouchers = assigned_voucher_query(db, user).all()
    student_ids = {v.buyer_user_id for v in vouchers}

    log = db.query(DailyWorkLog).filter(DailyWorkLog.id == log_id).first()
    if not log or log.student_user_id not in student_ids:
        raise HTTPException(status_code=404, detail="Work log not found")

    log.review_status = body.status
    log.reviewed_by = user.id
    log.reviewer_comment = body.comment
    db.commit()
    return {"status": "ok"}


# ---------------- Announcements endpoints ----------------

@router.get("/me/announcements", response_model=AnnouncementListResponse)
def list_announcements(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.models.company_dashboard import InternshipAnnouncement
    company = get_my_company(db, user)

    anns = db.query(InternshipAnnouncement).filter(
        InternshipAnnouncement.company_id == company.id,
        InternshipAnnouncement.deleted_at == None,
    ).order_by(InternshipAnnouncement.created_at.desc()).all()

    # Fetch related data
    intern_ids = {a.internship_id for a in anns if a.internship_id}
    creator_ids = {a.created_by for a in anns if a.created_by}
    interns = {i.id: i for i in db.query(Internship).filter(Internship.id.in_(list(intern_ids) or [-1])).all()}
    creators = {u.id: u for u in db.query(User).filter(User.id.in_(list(creator_ids) or [-1])).all()}

    items = []
    for a in anns:
        intern = interns.get(a.internship_id) if a.internship_id else None
        creator = creators.get(a.created_by) if a.created_by else None
        items.append(AnnouncementItem(
            id=a.id,
            title=a.title,
            body=a.body,
            internship_id=a.internship_id,
            internship_title=intern.title if intern else None,
            created_at=a.created_at,
            created_by_name=creator.display_name if creator else None,
        ))
    return AnnouncementListResponse(items=items)


@router.post("/me/announcements", response_model=AnnouncementItem, status_code=201)
def create_announcement(
    body: AnnouncementCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.models.company_dashboard import InternshipAnnouncement
    require_owner(user)
    company = get_my_company(db, user)

    # Validate internship belongs to company's scope
    if body.internship_id:
        vouchers = assigned_voucher_query(db, user).filter(
            InternshipVoucher.internship_id == body.internship_id
        ).first()
        if not vouchers:
            raise HTTPException(status_code=400, detail="Internship not in your scope")

    ann = InternshipAnnouncement(
        company_id=company.id,
        internship_id=body.internship_id,
        title=body.title,
        body=body.body,
        created_by=user.id,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)

    intern = db.query(Internship).filter(Internship.id == ann.internship_id).first() if ann.internship_id else None
    return AnnouncementItem(
        id=ann.id,
        title=ann.title,
        body=ann.body,
        internship_id=ann.internship_id,
        internship_title=intern.title if intern else None,
        created_at=ann.created_at,
        created_by_name=user.display_name,
    )


@router.delete("/me/announcements/{announcement_id}", status_code=204)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.models.company_dashboard import InternshipAnnouncement
    require_owner(user)
    company = get_my_company(db, user)

    ann = db.query(InternshipAnnouncement).filter(
        InternshipAnnouncement.id == announcement_id,
        InternshipAnnouncement.company_id == company.id,
    ).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")

    ann.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return


# ---------------- Performance Reviews endpoints ----------------

@router.get("/me/reviews", response_model=List[PerformanceReviewItem])
def list_performance_reviews(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.models.company_dashboard import InternshipPerformanceReview
    company = get_my_company(db, user)

    reviews = db.query(InternshipPerformanceReview).filter(
        InternshipPerformanceReview.company_id == company.id,
    ).order_by(InternshipPerformanceReview.submitted_at.desc()).all()

    # Fetch related data
    student_ids = {r.student_user_id for r in reviews}
    intern_ids = {r.internship_id for r in reviews}
    students = {u.id: u for u in db.query(User).filter(User.id.in_(list(student_ids) or [-1])).all()}
    interns = {i.id: i for i in db.query(Internship).filter(Internship.id.in_(list(intern_ids) or [-1])).all()}

    items = []
    for r in reviews:
        student = students.get(r.student_user_id)
        intern = interns.get(r.internship_id)
        if student and intern:
            items.append(PerformanceReviewItem(
                id=r.id,
                company_id=r.company_id,
                student_user_id=r.student_user_id,
                student_name=student.display_name,
                internship_id=r.internship_id,
                internship_title=intern.title,
                rating=r.rating,
                feedback=r.feedback,
                hire_recommendation=r.hire_recommendation,
                submitted_at=r.submitted_at,
            ))
    return items


@router.post("/me/reviews", response_model=PerformanceReviewItem, status_code=201)
def create_performance_review(
    body: PerformanceReviewCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.models.company_dashboard import InternshipPerformanceReview
    require_owner(user)
    company = get_my_company(db, user)

    # Validate student is in company's scope
    voucher = assigned_voucher_query(db, user).filter(
        InternshipVoucher.buyer_user_id == body.student_user_id,
        InternshipVoucher.internship_id == body.internship_id,
    ).first()
    if not voucher:
        raise HTTPException(status_code=404, detail="Student not in your scope")

    # Check for existing review
    existing = db.query(InternshipPerformanceReview).filter(
        InternshipPerformanceReview.company_id == company.id,
        InternshipPerformanceReview.student_user_id == body.student_user_id,
        InternshipPerformanceReview.internship_id == body.internship_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Review already exists")

    review = InternshipPerformanceReview(
        company_id=company.id,
        student_user_id=body.student_user_id,
        internship_id=body.internship_id,
        rating=body.rating,
        feedback=body.feedback,
        hire_recommendation=body.hire_recommendation,
        submitted_by=user.id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    student = db.query(User).filter(User.id == review.student_user_id).first()
    intern = db.query(Internship).filter(Internship.id == review.internship_id).first()
    return PerformanceReviewItem(
        id=review.id,
        company_id=review.company_id,
        student_user_id=review.student_user_id,
        student_name=student.display_name if student else "",
        internship_id=review.internship_id,
        internship_title=intern.title if intern else "",
        rating=review.rating,
        feedback=review.feedback,
        hire_recommendation=review.hire_recommendation,
        submitted_at=review.submitted_at,
    )


# ---------------- Attendance Reports endpoint ----------------

@router.get("/me/reports/attendance")
def company_attendance_report(
    from_date: date,
    to_date: date,
    internship_id: Optional[list[int]] = Query(None),
    student_id: Optional[list[int]] = Query(None),
    manager_id: Optional[list[int]] = Query(None),
    format: str = Query("json"),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    voucher_ids = [v.id for v in assigned_voucher_query(db, user).all()]
    rows = build_rows(
        db,
        voucher_ids=voucher_ids,
        from_date=from_date,
        to_date=to_date,
        student_ids=student_id,
        internship_ids=internship_id,
        manager_ids=manager_id,
    )
    if format == "csv":
        return Response(
            content=render_csv(rows),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="attendance-{from_date}-{to_date}.csv"'},
        )
    if format == "pdf":
        return Response(
            content=render_pdf(rows, title=f"Attendance report {from_date} to {to_date}"),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="attendance-{from_date}-{to_date}.pdf"'},
        )
    return {"rows": [r.__dict__ for r in rows]}


# ---------------- Internship Requests endpoints ----------------

@router.post("/me/internship-requests", response_model=InternshipRequestItem, status_code=201)
def create_internship_request(
    body: InternshipRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    company = get_my_company(db, user)

    req = InternshipRequest(
        company_id=company.id,
        requested_by=user.id,
        title=body.title,
        start_date=body.start_date,
        end_date=body.end_date,
        intern_count=body.intern_count,
        description=body.description,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return InternshipRequestItem(
        id=req.id,
        company_id=req.company_id,
        company_name=company.name,
        requested_by=req.requested_by,
        requester_name=user.display_name,
        title=req.title,
        start_date=req.start_date,
        end_date=req.end_date,
        intern_count=req.intern_count,
        description=req.description,
        status=req.status,
        rejection_reason=req.rejection_reason,
        approved_internship_id=req.approved_internship_id,
        reviewed_by=req.reviewed_by,
        reviewer_name=None,
        reviewed_at=req.reviewed_at,
        created_at=req.created_at,
    )


@router.get("/me/internship-requests", response_model=InternshipRequestListResponse)
def list_internship_requests(
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = get_my_company(db, user)

    q = db.query(InternshipRequest).filter(InternshipRequest.company_id == company.id)
    if status_filter:
        q = q.filter(InternshipRequest.status == status_filter)

    requests = q.order_by(InternshipRequest.created_at.desc()).all()

    # Fetch related data
    requester_ids = {r.requested_by for r in requests}
    reviewer_ids = {r.reviewed_by for r in requests if r.reviewed_by}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(list(requester_ids | reviewer_ids) or [-1])).all()}

    items = []
    for r in requests:
        requester = users.get(r.requested_by)
        reviewer = users.get(r.reviewed_by) if r.reviewed_by else None
        items.append(InternshipRequestItem(
            id=r.id,
            company_id=r.company_id,
            company_name=company.name,
            requested_by=r.requested_by,
            requester_name=requester.display_name if requester else "",
            title=r.title,
            start_date=r.start_date,
            end_date=r.end_date,
            intern_count=r.intern_count,
            description=r.description,
            status=r.status,
            rejection_reason=r.rejection_reason,
            approved_internship_id=r.approved_internship_id,
            reviewed_by=r.reviewed_by,
            reviewer_name=reviewer.display_name if reviewer else None,
            reviewed_at=r.reviewed_at,
            created_at=r.created_at,
        ))
    return InternshipRequestListResponse(items=items)


@router.delete("/me/internship-requests/{request_id}", status_code=204)
def withdraw_internship_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    company = get_my_company(db, user)

    req = db.query(InternshipRequest).filter(
        InternshipRequest.id == request_id,
        InternshipRequest.company_id == company.id,
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Can only withdraw pending requests")

    req.status = "withdrawn"
    db.commit()
    return
