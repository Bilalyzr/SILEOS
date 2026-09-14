"""Student-facing endpoints for daily-work-done + announcements."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.internship import InternshipVoucher
from app.models.company_dashboard import DailyWorkLog, InternshipAnnouncement
from app.services.auth_service import AuthService

router = APIRouter()


def _require_student(user: User = Depends(AuthService.get_current_user)) -> User:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Students only")
    return user


class WorkLogCreate(BaseModel):
    internship_id: int
    log_date: date
    content: str
    attachment_url: Optional[str] = ""


class WorkLogOut(BaseModel):
    id: int
    internship_id: int
    log_date: date
    content: str
    attachment_url: str
    review_status: str
    reviewer_comment: str


class AnnouncementOut(BaseModel):
    id: int
    title: str
    body: str
    internship_id: Optional[int]
    created_at: str


@router.post("/work-logs", response_model=WorkLogOut, status_code=201)
def create_log(
    body: WorkLogCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    # student must have a redeemed voucher on that internship
    v = db.query(InternshipVoucher).filter(
        InternshipVoucher.buyer_user_id == user.id,
        InternshipVoucher.internship_id == body.internship_id,
        InternshipVoucher.status == "redeemed",
    ).first()
    if not v:
        raise HTTPException(
            status_code=403,
            detail="Not enrolled in that internship"
        )
    existing = db.query(DailyWorkLog).filter(
        DailyWorkLog.student_user_id == user.id,
        DailyWorkLog.log_date == body.log_date,
    ).first()
    if existing:
        existing.content = body.content
        existing.attachment_url = body.attachment_url or ""
        log = existing
    else:
        log = DailyWorkLog(
            student_user_id=user.id,
            internship_id=body.internship_id,
            log_date=body.log_date,
            content=body.content,
            attachment_url=body.attachment_url or "",
        )
        db.add(log)
    db.commit()
    db.refresh(log)
    return WorkLogOut(
        id=log.id,
        internship_id=log.internship_id,
        log_date=log.log_date,
        content=log.content,
        attachment_url=log.attachment_url,
        review_status=log.review_status,
        reviewer_comment=log.reviewer_comment,
    )


@router.get("/work-logs")
def list_my_logs(
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    rows = db.query(DailyWorkLog).filter(
        DailyWorkLog.student_user_id == user.id
    ).order_by(DailyWorkLog.log_date.desc()).all()
    return {"items": [
        WorkLogOut(
            id=r.id,
            internship_id=r.internship_id,
            log_date=r.log_date,
            content=r.content,
            attachment_url=r.attachment_url,
            review_status=r.review_status,
            reviewer_comment=r.reviewer_comment,
        ) for r in rows
    ]}


@router.get("/announcements")
def list_my_announcements(
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    # Announcements where student belongs to that company's cohort.
    vouchers = db.query(InternshipVoucher).filter(
        InternshipVoucher.buyer_user_id == user.id,
        InternshipVoucher.status == "redeemed",
    ).all()
    company_ids = {
        v.hired_by_company_id for v in vouchers
        if v.hired_by_company_id
    }
    if not company_ids:
        return {"items": []}
    rows = db.query(InternshipAnnouncement).filter(
        InternshipAnnouncement.company_id.in_(company_ids),
        InternshipAnnouncement.deleted_at == None,
    ).order_by(InternshipAnnouncement.created_at.desc()).all()
    return {"items": [
        AnnouncementOut(
            id=a.id,
            title=a.title,
            body=a.body,
            internship_id=a.internship_id,
            created_at=a.created_at.isoformat(),
        ) for a in rows
    ]}
