"""Durable invitation delivery. Retrying an SMTP send can deliver a duplicate email."""
from html import escape
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.campus_operations import CampusMailJob
from app.models.institution import InstitutionInvite, Institution
from app.services.institution_service import utc
from app.services.email_service import EmailService


def mail_configured():
    s = get_settings()
    return bool(s.SMTP_HOST and s.SMTP_USER and s.SMTP_PASSWORD and s.EMAIL_FROM)


def deliver(job_id):
    with SessionLocal() as db:
        job = db.query(CampusMailJob).filter_by(id=job_id).with_for_update().first()
        if not job or job.status != "queued":
            return
        invite = db.get(InstitutionInvite, job.invite_id)
        if (
            not invite
            or invite.status != "pending"
            or utc(invite.expires_at) <= datetime.now(timezone.utc)
        ):
            job.status = "cancelled"
            db.commit()
            return
        inst = db.get(Institution, invite.institution_id)
        job.attempts += 1
        url = get_settings().FRONTEND_URL.rstrip("/") + "/institutions"
        text = f"You have been invited to {inst.name} as {invite.role}. Sign in or create an account using this email, verify it, and accept your invitation at {url}. This invitation expires after seven days."
        html = f'<div style="background:linear-gradient(120deg,#fff8ed,#ffd5aa);padding:36px;font-family:Arial;color:#5b3016;border-radius:20px"><p>SASHAINFINITY · CAMPUS</p><h1>Your campus is waiting.</h1><p>{escape(text)}</p><a href="{escape(url,quote=True)}" style="display:inline-block;background:#ffb879;color:#50250e;padding:14px 22px;border-radius:12px">Open invitations</a></div>'
        # Keep the row locked during SMTP to serialize retries. Never claim sent
        # when the provider is missing or the service returned a failure.
        ok = mail_configured() and EmailService._send_smtp_email(
            invite.email, "Your campus invitation · SashaInfinity", text, html
        )
        job.status = "sent" if ok else "failed"
        job.last_error = (
            ""
            if ok
            else "Email delivery failed. Check the SMTP service before retrying."
        )
        db.commit()


def deliver_pending():
    with SessionLocal() as db:
        ids = [
            i for i, in db.query(CampusMailJob.id).filter_by(status="queued").limit(100)
        ]
    for job_id in ids:
        deliver(job_id)
