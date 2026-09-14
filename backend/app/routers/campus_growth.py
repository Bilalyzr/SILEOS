"""Public school and college acquisition endpoints."""

from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campus_growth import CampusLead
from app.services import campus_growth as service
from app.services.auth_service import AuthService


router = APIRouter()


class CampusLeadCreate(BaseModel):
    contact_name: str = Field(min_length=2, max_length=120)
    work_email: EmailStr
    phone: str = Field(default="", max_length=20, pattern=r"^[+0-9 ()-]*$")
    institution_name: str = Field(min_length=2, max_length=180)
    institution_kind: Literal["school", "college", "university", "training"]
    learner_count: Literal["under-100", "100-499", "500-1999", "2000-plus"]
    interest: Literal["demo", "trial", "quote"] = "demo"
    message: str = Field(default="", max_length=2000)
    source: str = Field(default="campus-page", max_length=80)
    attribution: dict[str, str] = Field(default_factory=dict)
    consent: bool
    website: str = Field(default="", max_length=200)

    @field_validator("consent")
    @classmethod
    def consent_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent is required so we can respond to this enquiry.")
        return value


class LeadStatusUpdate(BaseModel):
    status: Literal["new", "contacted", "qualified", "won", "closed"]


@router.get("/plans")
def plans():
    return {"plans": service.PLAN_CATALOG}


@router.post("/leads", status_code=status.HTTP_202_ACCEPTED)
def create_lead(data: CampusLeadCreate, db: Session = Depends(get_db)):
    row = service.create_lead(db, data)
    return {
        "accepted": True,
        "reference": f"CAMPUS-{row.id:06d}" if row else "CAMPUS-RECEIVED",
        "message": "Thanks. Our campus team will contact you shortly.",
    }


@router.get("/leads")
def list_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin=Depends(AuthService.require_admin),
):
    query = db.query(CampusLead)
    if status_filter:
        query = query.filter(CampusLead.status == status_filter)
    total = query.count()
    rows = query.order_by(CampusLead.created_at.desc(), CampusLead.id.desc()).offset(offset).limit(limit).all()
    return {"items": [service.serialize(row) for row in rows], "total": total}


@router.patch("/leads/{lead_id}")
def set_lead_status(
    lead_id: int,
    data: LeadStatusUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(AuthService.require_admin),
):
    return service.serialize(service.update_status(db, lead_id, data.status))

