"""
Admin Messages Router - Send messages from admin to students
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.user import User
from app.models.admin_message import AdminMessage
from app.models.company import Company
from app.models.internship import InternshipVoucher
from app.services.auth_service import AuthService
from app.services.email_service import EmailService

router = APIRouter()


def _sender_name(user: User) -> str:
    return getattr(user, "display_name", None) or "SashaInfinity Team"


def _recipient_name(user: User) -> str:
    email = getattr(user, "user_email", "") or ""
    return getattr(user, "display_name", None) or (email.split("@")[0] if email else "there")


class MessageCreate(BaseModel):
    recipient_type: Literal["user", "company"]
    recipient_id: int
    subject: str
    body: str


class BulkMessageCreate(BaseModel):
    recipient_type: Literal["user", "company"]
    recipient_ids: List[int]  # List of user_ids OR company_ids
    subject: str
    body: str


class MessageResponse(BaseModel):
    id: int
    recipient_type: str
    recipient_id: int
    recipient_name: str  # Derived from user or company
    subject: str
    body: str
    sent_at: datetime
    read_at: Optional[datetime]
    email_status: Optional[str] = None


@router.get("/sent", response_model=List[MessageResponse])
async def get_sent_messages(
    current_user: User = Depends(AuthService.require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
):
    """Get all messages sent by admin"""
    messages = db.query(AdminMessage).filter(
        AdminMessage.sender_id == current_user.id
    ).order_by(AdminMessage.sent_at.desc()).offset(skip).limit(limit).all()

    result = []
    for msg in messages:
        recipient_name = ""
        if msg.recipient_type == "user":
            user = db.query(User).filter(User.id == msg.recipient_id).first()
            recipient_name = user.display_name or user.user_email if user else "Unknown"
        else:
            company = db.query(Company).filter(Company.id == msg.recipient_id).first()
            recipient_name = company.name if company else "Unknown Company"

        result.append(MessageResponse(
            id=msg.id,
            recipient_type=msg.recipient_type,
            recipient_id=msg.recipient_id,
            recipient_name=recipient_name,
            subject=msg.subject,
            body=msg.body,
            sent_at=msg.sent_at,
            read_at=msg.read_at,
            email_status=msg.email_status
        ))
    return result


@router.post("/", status_code=201)
async def send_message(
    payload: MessageCreate,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Send single message to user or company (stored in-app and emailed)"""
    # Validate recipient
    to_email = ""
    to_name = ""
    if payload.recipient_type == "user":
        user = db.query(User).filter(User.id == payload.recipient_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        to_email = user.user_email or ""
        to_name = _recipient_name(user)
    else:
        company = db.query(Company).filter(Company.id == payload.recipient_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        to_email = company.contact_email or ""
        to_name = getattr(company, "name", "") or ""

    message = AdminMessage(
        sender_id=current_user.id,
        recipient_type=payload.recipient_type,
        recipient_id=payload.recipient_id,
        subject=payload.subject,
        body=payload.body,
    )

    # Deliver by email as well — the in-app row alone was why admins saw the
    # message under "Recently sent" while the student never received anything.
    if to_email:
        delivered = EmailService.send_admin_message_email(
            to_email=to_email,
            recipient_name=to_name,
            subject=payload.subject,
            body=payload.body,
            sender_name=_sender_name(current_user),
        )
        message.email_status = "sent" if delivered else "failed"
    else:
        message.email_status = "no_email"

    db.add(message)
    db.commit()

    return {"status": "sent", "id": message.id, "email_status": message.email_status}


@router.post("/bulk", status_code=201)
async def send_bulk_message(
    payload: BulkMessageCreate,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """
    Send bulk message to multiple users or all interns in a company.

    Each recipient gets an in-app message row *and* an email. Previously only
    the row was written, so the admin saw the message under "Recently sent"
    while nothing reached the student's inbox.
    """
    failed = []

    # Resolve the recipient users first, deduplicated — a student holding two
    # vouchers at the same company should not be mailed the same notice twice.
    target_users: dict[int, User] = {}

    if payload.recipient_type == "user":
        for user_id in payload.recipient_ids:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                failed.append({"id": user_id, "reason": "User not found"})
                continue
            target_users[user.id] = user

    else:  # company → every intern hired by that company
        for company_id in payload.recipient_ids:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                failed.append({"id": company_id, "reason": "Company not found"})
                continue

            vouchers = db.query(InternshipVoucher).filter(
                InternshipVoucher.hired_by_company_id == company_id
            ).all()

            buyer_ids = {v.buyer_user_id for v in vouchers if v.buyer_user_id}
            if not buyer_ids:
                continue
            for user in db.query(User).filter(User.id.in_(buyer_ids)).all():
                target_users[user.id] = user

    if not target_users:
        return {
            "status": "sent",
            "sent_count": 0,
            "failed_count": len(failed),
            "email_sent_count": 0,
            "email_failed_count": 0,
            "failed": failed,
        }

    # One SMTP connection for the whole batch.
    recipients = [
        (u.user_email or "", _recipient_name(u))
        for u in target_users.values()
    ]
    email_results = EmailService.send_admin_message_emails(
        recipients=recipients,
        subject=payload.subject,
        body=payload.body,
        sender_name=_sender_name(current_user),
    )

    email_sent = 0
    email_failed = 0
    for user_id, user in target_users.items():
        email = user.user_email or ""
        if not email:
            status = "no_email"
            email_failed += 1
        elif email_results.get(email):
            status = "sent"
            email_sent += 1
        else:
            status = "failed"
            email_failed += 1

        db.add(AdminMessage(
            sender_id=current_user.id,
            recipient_type="user",  # Messages always go to individual users
            recipient_id=user_id,
            subject=payload.subject,
            body=payload.body,
            email_status=status,
        ))

    db.commit()

    return {
        "status": "sent",
        "sent_count": len(target_users),
        "failed_count": len(failed),
        # Delivery is reported separately: the in-app message always lands, the
        # email may not (bad address, SMTP down).
        "email_sent_count": email_sent,
        "email_failed_count": email_failed,
        "failed": failed,
    }


@router.get("/recipients/company")
async def get_companies_for_bulk_send(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Get list of companies with intern count for bulk sending"""
    companies = db.query(Company).filter(
        Company.is_approved == True
    ).all()

    result = []
    for company in companies:
        # Count interns assigned to this company
        intern_count = db.query(InternshipVoucher).filter(
            InternshipVoucher.hired_by_company_id == company.id
        ).count()

        if intern_count > 0:
            result.append({
                "id": company.id,
                "name": company.name,
                "industry": company.industry,
                "intern_count": intern_count
            })

    return result


@router.get("/recipients/students")
async def get_students_for_bulk_send(
    current_user: User = Depends(AuthService.require_admin),
    internship_id: Optional[int] = None,
    company_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get list of students for bulk sending, optionally filtered"""
    query = db.query(User).filter(User.role == "student")

    # Filter by internship
    if internship_id:
        voucher_user_ids = db.query(InternshipVoucher.buyer_user_id).filter(
            InternshipVoucher.internship_id == internship_id
        ).all()
        user_ids = [v[0] for v in voucher_user_ids]
        query = query.filter(User.id.in_(user_ids))

    # Filter by company assignment
    if company_id:
        voucher_user_ids = db.query(InternshipVoucher.buyer_user_id).filter(
            InternshipVoucher.hired_by_company_id == company_id
        ).all()
        user_ids = [v[0] for v in voucher_user_ids]
        query = query.filter(User.id.in_(user_ids))

    if search:
        query = query.filter(
            User.user_email.contains(search) | User.display_name.contains(search)
        )

    students = query.limit(500).all()

    return [
        {
            "id": s.id,
            "email": s.user_email,
            "name": s.display_name or s.user_email.split("@")[0]
        }
        for s in students
    ]


@router.get("/my-messages")
async def get_my_admin_messages(
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
):
    """Get admin messages sent to the current user"""
    messages = db.query(AdminMessage).filter(
        AdminMessage.recipient_type == "user",
        AdminMessage.recipient_id == current_user.id
    ).order_by(AdminMessage.sent_at.desc()).all()

    # Mark as read
    unread = [m for m in messages if m.read_at is None]
    for msg in unread:
        msg.read_at = datetime.now(timezone.utc)
    if unread:
        db.commit()

    result = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        result.append({
            "id": msg.id,
            "sender_name": sender.display_name if sender else "Admin",
            "subject": msg.subject,
            "body": msg.body,
            "sent_at": msg.sent_at,
            "read_at": msg.read_at
        })
    return result
