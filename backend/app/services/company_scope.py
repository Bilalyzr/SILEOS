"""
Pure helpers shared across the company dashboard router. Stateless — they
take a Session and an authenticated User and return DB rows or raise.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.company import Company
from app.models.company_dashboard import CompanyManager
from app.models.internship import InternshipVoucher


def get_my_company(db: Session, user: User) -> Company:
    """Return the company the authenticated user belongs to."""
    if user.role == "company":
        c = db.query(Company).filter(Company.owner_user_id == user.id).first()
        if not c:
            raise HTTPException(status_code=404, detail="No company profile")
        return c
    if user.role == "company_manager":
        link = db.query(CompanyManager).filter(CompanyManager.user_id == user.id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Manager not linked to a company")
        c = db.query(Company).filter(Company.id == link.company_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Company not found")
        return c
    raise HTTPException(status_code=403, detail="Company role required")


def is_owner(user: User) -> bool:
    return user.role == "company"


def require_owner(user: User) -> None:
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Company owner only")


def assigned_voucher_query(db: Session, user: User):
    """Return a SQLAlchemy query yielding vouchers assigned to the caller's
    company. For managers, further restricts to vouchers whose
    reporting_manager_user_id is the manager.

    Includes vouchers with hired_by_company_id set (admin-assigned) OR
    naturally hired through the platform.
    """
    company = get_my_company(db, user)
    # Admin-assigned vouchers: hired_by_company_id is set regardless of status
    q = db.query(InternshipVoucher).filter(
        InternshipVoucher.hired_by_company_id == company.id
    )
    if user.role == "company_manager":
        q = q.filter(InternshipVoucher.reporting_manager_user_id == user.id)
    return q
