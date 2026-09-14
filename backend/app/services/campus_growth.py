"""Public campus acquisition and plan catalogue services."""

from datetime import datetime, timezone
import hashlib

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.campus_growth import CampusLead


PLAN_CATALOG = (
    {
        "key": "starter",
        "name": "Starter",
        "description": "Launch one connected school or college workspace.",
        "price_label": "Talk to us",
        "featured": False,
        "features": [
            "100 active members",
            "Courses, batches and attendance",
            "Assessments and report cards",
            "Account-wide WhatsApp preferences",
        ],
    },
    {
        "key": "campus",
        "name": "Campus",
        "description": "Run admissions, learning and student finance together.",
        "price_label": "Custom annual plan",
        "featured": True,
        "features": [
            "1,000 active members",
            "Admissions and fee operations",
            "Role-aware action centre",
            "Priority onboarding and migration",
        ],
    },
    {
        "key": "enterprise",
        "name": "Enterprise",
        "description": "Govern multiple campuses with identity and data controls.",
        "price_label": "Custom agreement",
        "featured": False,
        "features": [
            "10,000 active members",
            "SSO, roster sync and custom domains",
            "Compliance and retention controls",
            "Dedicated success and support",
        ],
    },
)


def _lead_key(email: str, institution_name: str, now: datetime) -> str:
    normalized = f"{email.strip().lower()}|{institution_name.strip().lower()}|{now.date()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def create_lead(db, data):
    """Create at most one lead per contact/institution/day.

    Returning the existing row is intentional: public form retries stay
    idempotent while the response never reveals whether an email already
    exists elsewhere in the database.
    """

    if data.website:
        # Honeypot submissions receive the same benign result as real ones.
        return None
    now = datetime.now(timezone.utc)
    key = _lead_key(str(data.work_email), data.institution_name, now)
    existing = db.query(CampusLead).filter_by(dedupe_key=key).first()
    if existing:
        return existing
    row = CampusLead(
        dedupe_key=key,
        contact_name=data.contact_name.strip(),
        work_email=str(data.work_email).strip().lower(),
        phone=data.phone.strip(),
        institution_name=data.institution_name.strip(),
        institution_kind=data.institution_kind,
        learner_count=data.learner_count,
        interest=data.interest,
        message=data.message.strip(),
        source=data.source.strip() or "campus-page",
        attribution={
            key: value
            for key, value in (data.attribution or {}).items()
            if key in {"utm_source", "utm_medium", "utm_campaign", "referrer"}
            and isinstance(value, str)
        },
        consent_at=now,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.query(CampusLead).filter_by(dedupe_key=key).first()
    db.refresh(row)
    return row


def serialize(row: CampusLead) -> dict:
    return {
        "id": row.id,
        "contact_name": row.contact_name,
        "work_email": row.work_email,
        "phone": row.phone,
        "institution_name": row.institution_name,
        "institution_kind": row.institution_kind,
        "learner_count": row.learner_count,
        "interest": row.interest,
        "message": row.message,
        "source": row.source,
        "status": row.status,
        "created_at": row.created_at,
    }


def update_status(db, lead_id: int, status: str):
    row = db.query(CampusLead).filter_by(id=lead_id).first()
    if not row:
        raise HTTPException(404, "Campus enquiry not found.")
    row.status = status
    db.commit()
    db.refresh(row)
    return row

