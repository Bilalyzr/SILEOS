"""Tuition fee reminders and receipt notices.

Doctrine: never claim a send that did not happen. A reminder row is created
for every (installment, stage, recipient, channel) once, and its status tells
the truth: sent, failed with an error, or skipped with a reason.
"""

from datetime import datetime, timezone
from html import escape
import logging
import secrets
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.campus_operations import ParentLinkRequest
from app.models.campus_pilot import CampusWhatsAppCampaign, CampusWhatsAppMessage
from app.models.institution import Institution, InstitutionMember
from app.models.tuition import (
    TuitionFeeAssignment,
    TuitionFeePlan,
    TuitionInstallment,
    TuitionReceipt,
)
from app.models.tuition_reminders import TuitionReminder, TuitionReminderPolicy
from app.models.user import User
from app.models.whatsapp import WhatsAppContact
from app.services import campus_mail
from app.services import campus_whatsapp
from app.services import institution_service as institution_svc
from app.services import tuition_service
from app.services.email_service import EmailService


log = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
DEFAULT_POLICY = {
    "enabled": False,
    "days_before": [7, 1],
    "overdue_every_days": 7,
    "overdue_max": 3,
    "send_hour": 9,
    "channels": ["whatsapp", "email"],
    "whatsapp_template": "",
    "whatsapp_language": "en",
}


# ----------------------------------------------------------------- policy


def _manager(db, institution_id, user, *, lock=False):
    return institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=lock)


def _policy_row(db, institution_id):
    return db.get(TuitionReminderPolicy, institution_id)


def policy_dict(row, institution_id):
    if row is None:
        return {"institution_id": institution_id, **DEFAULT_POLICY, "updated_at": None}
    return {
        "institution_id": institution_id,
        "enabled": bool(row.enabled),
        "days_before": list(row.days_before or []),
        "overdue_every_days": row.overdue_every_days,
        "overdue_max": row.overdue_max,
        "send_hour": row.send_hour,
        "channels": list(row.channels or []),
        "whatsapp_template": row.whatsapp_template,
        "whatsapp_language": row.whatsapp_language,
        "updated_at": institution_svc.utc(row.updated_at).isoformat() if row.updated_at else None,
    }


def get_policy(db, institution_id, user):
    _manager(db, institution_id, user)
    return policy_dict(_policy_row(db, institution_id), institution_id)


def save_policy(db, institution_id, user, data):
    institution, _ = _manager(db, institution_id, user, lock=True)
    row = _policy_row(db, institution.id)
    if row is None:
        row = TuitionReminderPolicy(institution_id=institution.id)
        db.add(row)
    row.enabled = data.enabled
    row.days_before = list(data.days_before)
    row.overdue_every_days = data.overdue_every_days
    row.overdue_max = data.overdue_max
    row.send_hour = data.send_hour
    row.channels = list(data.channels)
    row.whatsapp_template = data.whatsapp_template
    row.whatsapp_language = data.whatsapp_language.strip() or "en"
    row.updated_by = user.id
    institution_svc.audit(
        db,
        institution.id,
        user,
        "tuition.reminder_policy_saved",
        f"enabled={data.enabled} channels={','.join(data.channels)}",
    )
    institution_svc.save(db)
    return policy_dict(row, institution.id)


# ------------------------------------------------------------- readiness


def whatsapp_ready():
    """True when the Meta Cloud API credentials are all present."""
    return bool(campus_whatsapp.configuration_status()["configured"])


def mail_ready():
    return bool(campus_mail.mail_configured())


def _template_ok(policy):
    return bool(policy.whatsapp_template) and policy.whatsapp_template in campus_whatsapp.approved_templates()


# ------------------------------------------------------------ recipients


def recipients_for(db, institution, student_member):
    """The student plus every guardian with an approved link, as delivery targets."""
    student_user = db.get(User, student_member.user_id)
    users = [student_user] if student_user and student_user.is_active else []
    guardian_ids = [
        pid
        for pid, in db.query(ParentLinkRequest.parent_user_id).filter_by(
            student_user_id=student_member.user_id, status="approved"
        )
    ]
    if guardian_ids:
        users.extend(
            db.query(User).filter(User.id.in_(guardian_ids), User.is_active.is_(True)).all()
        )
    out = []
    for account in users:
        member = (
            db.query(InstitutionMember)
            .filter_by(institution_id=institution.id, user_id=account.id, status="active")
            .first()
        )
        contact = db.get(WhatsAppContact, account.id)
        out.append(
            {
                "user": account,
                "member": member,
                "contact": contact if contact and contact.status == "confirmed" else None,
            }
        )
    return out


def channel_plan(policy, recipient, *, whatsapp_ok, mail_ok):
    """Return [(channel, skip_reason)] for one recipient under the policy.

    WhatsApp is preferred when consented and configured; email is the
    fallback. A recipient with no usable channel gets one skipped row so the
    log explains why nothing was sent.
    """
    plans = []
    channels = list(policy.channels or [])
    if "whatsapp" in channels:
        if not whatsapp_ok:
            plans.append(("whatsapp", "whatsapp_not_configured"))
        elif recipient["member"] is None:
            plans.append(("whatsapp", "not_a_member"))
        elif recipient["contact"] is None:
            plans.append(("whatsapp", "no_consent"))
        else:
            return [("whatsapp", None)]
    if "email" in channels:
        if not mail_ok:
            plans.append(("email", "email_not_configured"))
        elif not recipient["user"].user_email:
            plans.append(("email", "no_email"))
        else:
            return [("email", None)]
    return plans or [("email", "no_channel")]


# ---------------------------------------------------------------- staging


def _local_now(institution):
    try:
        zone = ZoneInfo(institution.timezone)
    except Exception:
        zone = timezone.utc
    return datetime.now(zone)


def _stage_for(installment_row, today, policy):
    """Map one outstanding installment to today's stage, or None."""
    due_on = installment_row["due_on"]
    delta = (due_on - today).days
    if delta > 0:
        return (f"before:{delta}", "upcoming") if delta in (policy.days_before or []) else None
    if delta == 0:
        return ("due:0", "due")
    overdue_days = -delta
    every = max(1, policy.overdue_every_days)
    k = overdue_days // every
    if 1 <= k <= policy.overdue_max:
        return (f"overdue:{k}", "overdue")
    return None


def _insert(db, values):
    """Insert one reminder row; return it, or None when the dedupe key exists."""
    row = TuitionReminder(**values)
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        return None
    return row


def _stage_rows(db, institution, policy, assignment, student_member, *, installment_row, stage, kind, actor_id, whatsapp_ok, mail_ok, dedupe_prefix=""):
    created = []
    for recipient in recipients_for(db, institution, student_member):
        for channel, skip in channel_plan(policy, recipient, whatsapp_ok=whatsapp_ok, mail_ok=mail_ok):
            key = f"{dedupe_prefix}{installment_row['id']}:{stage}:{recipient['user'].id}:{channel}"
            row = _insert(
                db,
                {
                    "institution_id": institution.id,
                    "assignment_id": assignment.id,
                    "installment_id": installment_row["id"],
                    "student_member_id": student_member.id,
                    "recipient_user_id": recipient["user"].id,
                    "kind": kind,
                    "stage": stage,
                    "channel": channel,
                    "status": "skipped" if skip else "queued",
                    "skip_reason": skip or "",
                    "amount": tuition_service.money(installment_row["balance"]),
                    "currency": assignment.currency,
                    "due_on": datetime.combine(installment_row["due_on"], datetime.min.time()),
                    "dedupe_key": key,
                    "created_by": actor_id,
                },
            )
            if row is not None:
                created.append(row)
    return created


def stage_institution(db, institution, policy, *, today=None, force=False, actor_id=None):
    """Create today's reminder rows for every outstanding installment. Idempotent."""
    if not policy.enabled and not force:
        return []
    now_local = _local_now(institution)
    today = today or now_local.date()
    if not force and now_local.hour < policy.send_hour:
        return []
    whatsapp_ok = whatsapp_ready() and _template_ok(policy)
    mail_ok = mail_ready()
    created = []
    assignments = (
        db.query(TuitionFeeAssignment)
        .filter(
            TuitionFeeAssignment.institution_id == institution.id,
            TuitionFeeAssignment.status == "active",
        )
        .order_by(TuitionFeeAssignment.id)
        .all()
    )
    for assignment in assignments:
        student_member = db.get(InstitutionMember, assignment.student_member_id)
        if not student_member or student_member.status != "active":
            continue
        snapshot = tuition_service._snapshot_for(db, assignment, today)
        for installment_row in snapshot["installments"]:
            if installment_row["balance"] <= 0:
                continue
            staged = _stage_for(installment_row, today, policy)
            if not staged:
                continue
            stage, kind = staged
            created.extend(
                _stage_rows(
                    db,
                    institution,
                    policy,
                    assignment,
                    student_member,
                    installment_row=installment_row,
                    stage=stage,
                    kind=kind,
                    actor_id=actor_id,
                    whatsapp_ok=whatsapp_ok,
                    mail_ok=mail_ok,
                )
            )
    db.commit()
    return created


def queue_receipt(db, institution, assignment, payment, receipt, actor_id):
    """Queue receipt notices after a payment commit. Never raises."""
    try:
        policy = _policy_row(db, institution.id)
        if policy is None or not policy.enabled:
            return []
        student_member = db.get(InstitutionMember, assignment.student_member_id)
        whatsapp_ok = whatsapp_ready() and _template_ok(policy)
        mail_ok = mail_ready()
        created = []
        for recipient in recipients_for(db, institution, student_member):
            for channel, skip in channel_plan(policy, recipient, whatsapp_ok=whatsapp_ok, mail_ok=mail_ok):
                row = _insert(
                    db,
                    {
                        "institution_id": institution.id,
                        "assignment_id": assignment.id,
                        "installment_id": None,
                        "receipt_id": receipt.id,
                        "student_member_id": student_member.id,
                        "recipient_user_id": recipient["user"].id,
                        "kind": "receipt",
                        "stage": "receipt",
                        "channel": channel,
                        "status": "skipped" if skip else "queued",
                        "skip_reason": skip or "",
                        "amount": tuition_service.money(payment.amount),
                        "currency": payment.currency,
                        "due_on": None,
                        "dedupe_key": f"receipt:{receipt.id}:{recipient['user'].id}:{channel}",
                        "created_by": actor_id,
                    },
                )
                if row is not None:
                    created.append(row)
        db.commit()
        return created
    except Exception:
        db.rollback()
        log.warning("Receipt notice could not be queued", exc_info=True)
        return []


# --------------------------------------------------------------- messages


def _context(db, reminder):
    institution = db.get(Institution, reminder.institution_id)
    assignment = db.get(TuitionFeeAssignment, reminder.assignment_id)
    plan = db.get(TuitionFeePlan, assignment.plan_id) if assignment else None
    student_member = db.get(InstitutionMember, reminder.student_member_id)
    student = db.get(User, student_member.user_id) if student_member else None
    installment = db.get(TuitionInstallment, reminder.installment_id) if reminder.installment_id else None
    receipt = db.get(TuitionReceipt, reminder.receipt_id) if reminder.receipt_id else None
    return {
        "institution": institution.name if institution else "",
        "student": (student.display_name if student else None) or "Student",
        "plan": plan.name if plan else "Tuition fees",
        "installment": installment.name if installment else "",
        "amount": f"{reminder.currency.upper()} {tuition_service.money(reminder.amount):,.2f}",
        "due_on": reminder.due_on.date().isoformat() if reminder.due_on else "",
        "receipt_number": receipt.receipt_number if receipt else "",
        "balance_after": f"{reminder.currency.upper()} {tuition_service.money(receipt.balance_after):,.2f}" if receipt else "",
        "pay_url": _pay_url(db, institution, reminder),
    }


def _pay_url(db, institution, reminder):
    """Where the recipient can pay online, or "" when the gateway is not set up."""
    from app.core.config import get_settings
    from app.services.tuition_collection import online_ready

    if not institution or not online_ready():
        return ""
    base = get_settings().FRONTEND_URL.rstrip("/")
    recipient = db.get(User, reminder.recipient_user_id)
    if recipient and recipient.role == "parent":
        return f"{base}/parent"
    return f"{base}/institutions/{institution.id}/finance"


def message_text(kind, ctx):
    return _base_text(kind, ctx) + (f" Pay online: {ctx['pay_url']}" if kind != "receipt" and ctx.get("pay_url") else "")


def _base_text(kind, ctx):
    if kind == "receipt":
        return (
            f"Payment received. {ctx['institution']} has recorded {ctx['amount']} for {ctx['student']} "
            f"({ctx['plan']}). Receipt {ctx['receipt_number']}. Balance after payment: {ctx['balance_after']}."
        )
    if kind == "upcoming":
        return (
            f"Fee reminder from {ctx['institution']}: {ctx['amount']} for {ctx['student']} "
            f"({ctx['plan']} - {ctx['installment']}) is due on {ctx['due_on']}."
        )
    if kind == "due":
        return (
            f"Fee due today at {ctx['institution']}: {ctx['amount']} for {ctx['student']} "
            f"({ctx['plan']} - {ctx['installment']})."
        )
    if kind == "overdue":
        return (
            f"Overdue fee at {ctx['institution']}: {ctx['amount']} for {ctx['student']} "
            f"({ctx['plan']} - {ctx['installment']}) was due on {ctx['due_on']}. Please pay at the earliest."
        )
    return (
        f"Fee reminder from {ctx['institution']}: {ctx['amount']} is outstanding for {ctx['student']} "
        f"({ctx['plan']} - {ctx['installment']}), due {ctx['due_on']}."
    )


def _subject(kind, ctx):
    return {
        "receipt": f"Payment receipt {ctx['receipt_number']} - {ctx['institution']}",
        "upcoming": f"Fee due {ctx['due_on']} - {ctx['institution']}",
        "due": f"Fee due today - {ctx['institution']}",
        "overdue": f"Overdue fee - {ctx['institution']}",
    }.get(kind, f"Fee reminder - {ctx['institution']}")


# ---------------------------------------------------------------- delivery


def deliver_email(db, reminder):
    ctx = _context(db, reminder)
    recipient = db.get(User, reminder.recipient_user_id)
    text = message_text(reminder.kind, ctx)
    html = (
        '<div style="background:linear-gradient(120deg,#fff8ed,#ffd5aa);padding:36px;font-family:Arial;'
        'color:#5b3016;border-radius:20px"><p>SASHAINFINITY · CAMPUS</p>'
        f"<h1>{escape(ctx['institution'])}</h1><p>{escape(text)}</p></div>"
    )
    reminder.attempts += 1
    ok = bool(
        recipient
        and recipient.user_email
        and mail_ready()
        and EmailService._send_smtp_email(recipient.user_email, _subject(reminder.kind, ctx), text, html)
    )
    if ok:
        reminder.status = "sent"
        reminder.error = ""
        reminder.sent_at = datetime.now(timezone.utc)
    else:
        reminder.status = "failed"
        reminder.error = "Email delivery failed. Check the SMTP service before retrying."


def _campaign_actor(db, reminder):
    if reminder.created_by:
        return reminder.created_by
    owner = (
        db.query(InstitutionMember)
        .filter_by(institution_id=reminder.institution_id, role="owner", status="active")
        .order_by(InstitutionMember.id)
        .first()
    )
    return owner.user_id if owner else reminder.recipient_user_id


def deliver_whatsapp(db, reminder):
    """Hand the reminder to the existing WhatsApp pipeline as a one-recipient campaign."""
    policy = _policy_row(db, reminder.institution_id)
    member = (
        db.query(InstitutionMember)
        .filter_by(institution_id=reminder.institution_id, user_id=reminder.recipient_user_id, status="active")
        .first()
    )
    contact = db.get(WhatsAppContact, reminder.recipient_user_id)
    reminder.attempts += 1
    if not (policy and whatsapp_ready() and _template_ok(policy) and member and contact and contact.status == "confirmed"):
        reminder.status = "failed"
        reminder.error = "WhatsApp is not ready for this recipient (configuration, template or consent)."
        return
    ctx = _context(db, reminder)
    campaign = CampusWhatsAppCampaign(
        institution_id=reminder.institution_id,
        request_key=f"reminder:{reminder.id}",
        template=policy.whatsapp_template,
        language=policy.whatsapp_language or "en",
        parameters=[ctx["student"], ctx["amount"], ctx["due_on"] or ctx["receipt_number"], ctx["institution"]],
        batch_id=None,
        created_by=_campaign_actor(db, reminder),
    )
    db.add(campaign)
    db.flush()
    message = CampusWhatsAppMessage(
        campaign_id=campaign.id,
        member_id=member.id,
        phone=contact.phone,
        status="queued",
        callback_key=secrets.token_hex(16),
    )
    db.add(message)
    db.flush()
    reminder.whatsapp_message_id = message.id
    reminder.status = "queued"
    reminder.error = ""


def deliver_pending(db, institution_id=None, limit=200):
    query = db.query(TuitionReminder).filter(
        TuitionReminder.status == "queued", TuitionReminder.whatsapp_message_id.is_(None)
    )
    if institution_id is not None:
        query = query.filter(TuitionReminder.institution_id == institution_id)
    rows = query.order_by(TuitionReminder.id).limit(limit).all()
    sent = failed = 0
    for reminder in rows:
        try:
            if reminder.channel == "email":
                deliver_email(db, reminder)
            else:
                deliver_whatsapp(db, reminder)
            db.commit()
        except Exception:
            db.rollback()
            log.warning("Reminder %s delivery raised", reminder.id, exc_info=True)
            reminder = db.get(TuitionReminder, reminder.id)
            if reminder is not None:
                reminder.attempts += 1
                reminder.status = "failed"
                reminder.error = "Delivery raised an unexpected error."
                db.commit()
        if reminder is not None and reminder.status == "sent":
            sent += 1
        elif reminder is not None and reminder.status == "failed":
            failed += 1
    return sent, failed


def run_institution(db, institution, *, force=False, actor_id=None, today=None):
    policy = _policy_row(db, institution.id)
    if policy is None:
        policy = TuitionReminderPolicy(institution_id=institution.id, **DEFAULT_POLICY)
    created = stage_institution(db, institution, policy, today=today, force=force, actor_id=actor_id)
    sent, failed = deliver_pending(db, institution.id)
    skipped = sum(1 for row in created if row.status == "skipped")
    return {"staged": len(created), "sent": sent, "failed": failed, "skipped": skipped}


def run_all(limit_per_institution=500):
    """Worker entry point: stage and deliver for every institution with reminders on."""
    with SessionLocal() as db:
        ids = [
            iid
            for iid, in db.query(TuitionReminderPolicy.institution_id).filter(
                TuitionReminderPolicy.enabled.is_(True)
            )
        ]
        for iid in ids:
            institution = db.get(Institution, iid)
            if institution is None:
                continue
            try:
                run_institution(db, institution)
            except Exception:
                db.rollback()
                log.warning("Reminder run failed for institution %s", iid, exc_info=True)


# ------------------------------------------------------------- endpoints


def run_now(db, institution_id, user):
    institution, _ = _manager(db, institution_id, user)
    result = run_institution(db, institution, force=True, actor_id=user.id)
    institution_svc.audit(db, institution.id, user, "tuition.reminders_run", str(result))
    db.commit()
    return result


def _whatsapp_status(db, reminder):
    if reminder.whatsapp_message_id is None:
        return reminder.status, reminder.error
    message = db.get(CampusWhatsAppMessage, reminder.whatsapp_message_id)
    if message is None:
        return reminder.status, reminder.error
    if message.status in ("sent", "delivered", "read"):
        return "sent", ""
    if message.status == "failed":
        return "failed", message.error or "WhatsApp delivery failed."
    return "queued", ""


def reminder_dict(db, row):
    status, error = _whatsapp_status(db, row)
    recipient = db.get(User, row.recipient_user_id)
    student_member = db.get(InstitutionMember, row.student_member_id)
    student = db.get(User, student_member.user_id) if student_member else None
    return {
        "id": row.id,
        "assignment_id": row.assignment_id,
        "installment_id": row.installment_id,
        "receipt_id": row.receipt_id,
        "student_member_id": row.student_member_id,
        "student_name": (student.display_name if student else None) or "Student",
        "recipient_user_id": row.recipient_user_id,
        "recipient_name": (recipient.display_name if recipient else None) or "",
        "recipient_role": recipient.role if recipient else "",
        "kind": row.kind,
        "stage": row.stage,
        "channel": row.channel,
        "status": status,
        "skip_reason": row.skip_reason,
        "error": error,
        "attempts": row.attempts,
        "amount": tuition_service.number(row.amount),
        "currency": row.currency,
        "due_on": row.due_on.date().isoformat() if row.due_on else None,
        "created_at": institution_svc.utc(row.created_at).isoformat() if row.created_at else None,
        "sent_at": institution_svc.utc(row.sent_at).isoformat() if row.sent_at else None,
    }


def list_reminders(db, institution_id, user, *, status=None, after_id=None, limit=50):
    institution, _ = _manager(db, institution_id, user)
    query = db.query(TuitionReminder).filter_by(institution_id=institution.id)
    if status:
        query = query.filter(TuitionReminder.status == status)
    if after_id:
        query = query.filter(TuitionReminder.id < after_id)
    rows = query.order_by(TuitionReminder.id.desc()).limit(limit + 1).all()
    more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [reminder_dict(db, row) for row in rows],
        "next_after_id": rows[-1].id if more and rows else None,
    }


def retry(db, institution_id, user, reminder_id):
    institution, _ = _manager(db, institution_id, user, lock=True)
    row = db.query(TuitionReminder).filter_by(id=reminder_id, institution_id=institution.id).first()
    if row is None:
        raise HTTPException(404, "Reminder not found.")
    if row.status != "failed":
        raise HTTPException(409, "Only failed reminders can be retried.")
    if row.attempts >= MAX_ATTEMPTS:
        raise HTTPException(409, "This reminder reached the retry limit.")
    row.status = "queued"
    row.whatsapp_message_id = None
    db.commit()
    if row.channel == "email":
        deliver_email(db, row)
    else:
        deliver_whatsapp(db, row)
    db.commit()
    return reminder_dict(db, row)


def remind_assignment(db, institution_id, user, assignment_id):
    """Manager-triggered reminder for the earliest unpaid installment, sent now."""
    institution, _ = _manager(db, institution_id, user, lock=True)
    assignment = tuition_service._assignment(db, institution.id, assignment_id)
    if assignment.status == "cancelled":
        raise HTTPException(409, "A cancelled tuition fee account cannot receive reminders.")
    student_member = db.get(InstitutionMember, assignment.student_member_id)
    snapshot = tuition_service._snapshot_for(db, assignment)
    target = next((row for row in snapshot["installments"] if row["balance"] > 0), None)
    if target is None:
        raise HTTPException(422, "This account has no outstanding installment.")
    policy = _policy_row(db, institution.id) or TuitionReminderPolicy(institution_id=institution.id, **DEFAULT_POLICY)
    today = _local_now(institution).date()
    created = _stage_rows(
        db,
        institution,
        policy,
        assignment,
        student_member,
        installment_row=target,
        stage=f"manual:{today.isoformat()}",
        kind="manual",
        actor_id=user.id,
        whatsapp_ok=whatsapp_ready() and _template_ok(policy),
        mail_ok=mail_ready(),
        dedupe_prefix="manual:",
    )
    if not created:
        raise HTTPException(409, "A reminder for this installment was already sent today.")
    institution_svc.audit(db, institution.id, user, "tuition.reminder_sent", f"Account #{assignment.id}")
    db.commit()
    ids = [row.id for row in created]
    deliver_pending(db, institution.id)
    return [reminder_dict(db, db.get(TuitionReminder, rid)) for rid in ids]
