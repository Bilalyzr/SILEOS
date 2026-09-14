"""Daily campus pilot APIs and the public Meta webhook endpoint."""

import json
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.campus_operations import CampusAttendance, CampusBranding, CampusTerm
from app.models.campus_pilot import (
    CampusAnnouncement,
    CampusEvent,
    CampusGoal,
    CampusGradePolicy,
    CampusNoticeRead,
    CampusOnboardingState,
    CampusReportComment,
    CampusWhatsAppCampaign,
    CampusWhatsAppMessage,
)
from app.models.institution import (
    InstitutionAssignment,
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionCourse,
    InstitutionMember,
)
from app.models.course import Course
from app.models.user import User
from app.models.whatsapp import WhatsAppContact
from app.schemas.campus_pilot import (
    AnnouncementCreate,
    EventCreate,
    GoalCreate,
    GoalUpdate,
    GradePolicySave,
    OnboardingUpdate,
    ReportCommentSave,
    WhatsAppCampaignCreate,
    WhatsAppOptIn,
)
from app.services import campus_pilot as pilot_svc
from app.services import campus_whatsapp as whatsapp_svc
from app.services import institution_service as institution_svc
from app.services import whatsapp_campaigns as campaign_svc
from app.services.auth_service import AuthService
from app.services.campus_report_pdf import build_report_card_pdf


router = APIRouter()
webhook_router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


def _masked_phone(phone):
    if not phone:
        return None
    return "+" + "*" * max(4, len(phone) - 5) + phone[-4:]


def _latest_term_id(db, institution_id, term_id):
    if term_id:
        return term_id
    row = (
        db.query(CampusTerm)
        .filter_by(institution_id=institution_id)
        .order_by(CampusTerm.ends_on.desc(), CampusTerm.id.desc())
        .first()
    )
    if not row:
        raise HTTPException(404, "Create an academic term before viewing report cards.")
    return row.id


def _campaign_dict(db, row):
    counts = {
        "queued": 0,
        "sent": 0,
        "delivered": 0,
        "read": 0,
        "failed": 0,
        "cancelled": 0,
    }
    for status, count in (
        db.query(CampusWhatsAppMessage.status, func.count())
        .filter_by(campaign_id=row.id)
        .group_by(CampusWhatsAppMessage.status)
    ):
        target = "queued" if status in ("queued", "retrying", "sending") else status
        counts[target] = counts.get(target, 0) + count
    total = sum(counts.values())
    unsuccessful = counts["failed"] + counts["cancelled"]
    if counts["queued"]:
        aggregate = "queued"
    elif total and unsuccessful == total:
        aggregate = "failed"
    elif unsuccessful:
        aggregate = "partial"
    elif total and counts["read"] == total:
        aggregate = "read"
    elif total and counts["read"] + counts["delivered"] == total:
        aggregate = "delivered"
    else:
        aggregate = "sent"
    return {
        "id": row.id,
        "request_key": row.request_key,
        "template": row.template,
        "language": row.language,
        "parameters": row.parameters,
        "batch_id": row.batch_id,
        "header_image_url": row.header_image_url or None,
        "created_at": institution_svc.utc(row.created_at).isoformat(),
        "status": aggregate,
        "recipient_count": total,
        **counts,
    }


def _same_whatsapp_campaign(row, data, header_url):
    return (
        row.template == data.template
        and row.language == data.language
        and row.parameters == data.parameters
        and row.batch_id == data.batch_id
        and row.header_image_url == header_url
    )


def _existing_whatsapp_campaign(db, institution_id, data, header_url):
    row = (
        db.query(CampusWhatsAppCampaign)
        .filter_by(institution_id=institution_id, request_key=data.request_key)
        .populate_existing()
        .first()
    )
    if row and not _same_whatsapp_campaign(row, data, header_url):
        raise HTTPException(409, "That request key belongs to another campaign.")
    return row


def _claim_whatsapp_campaign(db, campaign, institution_id, data, header_url):
    """Insert behind a savepoint, or reload the concurrent request winner."""

    # Leave the successful savepoint open until the request commits or rolls
    # back, so the campaign, audit, and every recipient batch stay atomic even
    # with SQLite's legacy transaction mode.
    savepoint = db.begin_nested()
    try:
        db.add(campaign)
        db.flush()
        return campaign, True
    except IntegrityError:
        savepoint.rollback()
        db.expire_all()
        existing = _existing_whatsapp_campaign(db, institution_id, data, header_url)
        if existing:
            return existing, False
        raise HTTPException(
            409, "That campaign request is already being processed."
        ) from None


@router.get("/{institution_id}/pilot/onboarding")
def onboarding(institution_id: int, db: Session = Depends(get_db), user=Current):
    institution, actor = institution_svc.scope(
        db, institution_id, user, institution_svc.MANAGERS
    )
    return pilot_svc.onboarding(db, institution, actor)


@router.patch("/{institution_id}/pilot/onboarding")
def onboarding_update(
    institution_id: int,
    data: OnboardingUpdate,
    db: Session = Depends(get_db),
    user=Current,
):
    institution, actor = institution_svc.scope(
        db, institution_id, user, institution_svc.MANAGERS, lock=True
    )
    row = db.get(CampusOnboardingState, institution_id)
    if not row:
        row = CampusOnboardingState(institution_id=institution_id, updated_by=user.id)
        db.add(row)
    row.dismissed = data.dismissed
    row.updated_by = user.id
    institution_svc.save(db)
    return pilot_svc.onboarding(db, institution, actor)


@router.get("/{institution_id}/pilot/events")
def events(
    institution_id: int,
    starts_after: datetime | None = Query(default=None),
    starts_before: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_svc.scope(db, institution_id, user)
    start = starts_after or datetime.now(timezone.utc) - timedelta(days=30)
    end = starts_before or datetime.now(timezone.utc) + timedelta(days=180)
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise HTTPException(422, "Calendar filters require a valid offset-aware range.")
    query = db.query(CampusEvent).filter(
        CampusEvent.institution_id == institution_id,
        CampusEvent.starts_at < end.astimezone(timezone.utc),
        CampusEvent.ends_at > start.astimezone(timezone.utc),
    )
    if actor.role not in institution_svc.STAFF:
        batch_ids = db.query(InstitutionBatchMember.batch_id).filter_by(
            member_id=actor.id
        )
        query = query.filter(
            or_(CampusEvent.batch_id.is_(None), CampusEvent.batch_id.in_(batch_ids))
        )
    return [
        pilot_svc.event_dict(db, row)
        for row in query.order_by(CampusEvent.starts_at, CampusEvent.id).limit(2000)
    ]


@router.post("/{institution_id}/pilot/events", status_code=201)
def event_create(
    institution_id: int,
    data: EventCreate,
    db: Session = Depends(get_db),
    user=Current,
):
    return pilot_svc.create_events(db, institution_id, user, data)


@router.delete("/{institution_id}/pilot/events/{event_id}")
def event_delete(
    institution_id: int,
    event_id: int,
    series: bool = False,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_svc.scope(
        db, institution_id, user, institution_svc.STAFF, lock=True
    )
    row = (
        db.query(CampusEvent)
        .filter_by(id=event_id, institution_id=institution_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Calendar event not found.")
    if actor.role not in institution_svc.MANAGERS and row.created_by != user.id:
        raise HTTPException(
            403, "Only the author or a campus manager can remove this event."
        )
    query = db.query(CampusEvent).filter_by(institution_id=institution_id)
    targets = query.filter_by(series=row.series).all() if series else [row]
    for target in targets:
        db.delete(target)
    institution_svc.audit(
        db,
        institution_id,
        user,
        "calendar.event_removed",
        f"{row.title}: {len(targets)}",
    )
    institution_svc.save(db)
    return {"status": "removed", "removed_count": len(targets)}


def _visible_announcements(db, institution_id, actor):
    query = db.query(CampusAnnouncement).filter_by(institution_id=institution_id)
    if actor.role not in institution_svc.STAFF:
        batch_ids = db.query(InstitutionBatchMember.batch_id).filter_by(
            member_id=actor.id
        )
        query = query.filter(
            or_(
                CampusAnnouncement.batch_id.is_(None),
                CampusAnnouncement.batch_id.in_(batch_ids),
            )
        )
    return query


@router.get("/{institution_id}/pilot/announcements")
def announcements(institution_id: int, db: Session = Depends(get_db), user=Current):
    _, actor = institution_svc.scope(db, institution_id, user)
    return [
        pilot_svc.announcement_dict(db, row, actor)
        for row in _visible_announcements(db, institution_id, actor)
        .order_by(CampusAnnouncement.id.desc())
        .limit(500)
    ]


@router.post("/{institution_id}/pilot/announcements", status_code=201)
def announcement_create(
    institution_id: int,
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_svc.scope(
        db, institution_id, user, institution_svc.STAFF, lock=True
    )
    if data.batch_id:
        institution_svc.batch_scope(db, institution_id, data.batch_id)
    row = CampusAnnouncement(
        institution_id=institution_id,
        batch_id=data.batch_id,
        title=data.title.strip(),
        body=data.body.strip(),
        created_by=user.id,
    )
    db.add(row)
    institution_svc.audit(db, institution_id, user, "announcement.created", data.title)
    institution_svc.save(db)
    db.refresh(row)
    return pilot_svc.announcement_dict(db, row, actor)


@router.post("/{institution_id}/pilot/announcements/{announcement_id}/read")
def announcement_read(
    institution_id: int,
    announcement_id: int,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_svc.scope(db, institution_id, user)
    row = (
        _visible_announcements(db, institution_id, actor)
        .filter_by(id=announcement_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Announcement not found.")
    marker = (
        db.query(CampusNoticeRead)
        .filter_by(announcement_id=row.id, member_id=actor.id)
        .first()
    )
    if not marker:
        db.add(CampusNoticeRead(announcement_id=row.id, member_id=actor.id))
        institution_svc.save(db)
    return pilot_svc.announcement_dict(db, row, actor)


@router.get("/{institution_id}/pilot/notifications")
def notification_feed(institution_id: int, db: Session = Depends(get_db), user=Current):
    """A bounded personal feed derived from authoritative campus records."""
    institution, actor = institution_svc.scope(db, institution_id, user)
    now = datetime.now(timezone.utc)
    try:
        today = now.astimezone(ZoneInfo(institution.timezone)).date()
    except ZoneInfoNotFoundError:
        today = now.date()
    horizon = today + timedelta(days=14)
    batch_ids = [
        batch_id
        for batch_id, in db.query(InstitutionBatchMember.batch_id).filter_by(
            member_id=actor.id
        )
    ]
    items = []

    event_query = db.query(CampusEvent).filter(
        CampusEvent.institution_id == institution_id,
        CampusEvent.starts_at >= now,
        CampusEvent.starts_at <= now + timedelta(days=14),
    )
    if actor.role not in institution_svc.STAFF:
        event_query = event_query.filter(
            or_(CampusEvent.batch_id.is_(None), CampusEvent.batch_id.in_(batch_ids))
        )
    for event in event_query.order_by(CampusEvent.starts_at).limit(30):
        items.append(
            {
                "id": f"event:{event.id}",
                "type": "event",
                "title": event.title,
                "detail": f"{event.kind.title()} · {event.room or 'Campus'}",
                "starts_at": institution_svc.utc(event.starts_at).isoformat(),
                "due_on": None,
                "severity": "important" if event.kind == "exam" else "info",
                "href": "daily",
                "read_at": None,
            }
        )

    assignment_query = (
        db.query(InstitutionAssignment, Course)
        .join(InstitutionBatch, InstitutionBatch.id == InstitutionAssignment.batch_id)
        .join(
            InstitutionCourse,
            InstitutionCourse.id == InstitutionAssignment.institution_course_id,
        )
        .join(Course, Course.id == InstitutionCourse.course_id)
        .filter(
            InstitutionBatch.institution_id == institution_id,
            InstitutionCourse.institution_id == institution_id,
            InstitutionAssignment.due_date.is_not(None),
            InstitutionAssignment.due_date >= today.isoformat(),
            InstitutionAssignment.due_date <= horizon.isoformat(),
        )
    )
    if actor.role not in institution_svc.STAFF:
        assignment_query = assignment_query.filter(
            InstitutionAssignment.batch_id.in_(batch_ids)
        )
    for assignment, course in assignment_query.limit(30):
        items.append(
            {
                "id": f"assignment:{assignment.id}",
                "type": "assignment",
                "title": course.post_title,
                "detail": "Course assignment due soon",
                "starts_at": None,
                "due_on": assignment.due_date,
                "severity": "important",
                "href": "courses",
                "read_at": None,
            }
        )

    attendance_query = (
        db.query(CampusAttendance)
        .join(InstitutionBatch, InstitutionBatch.id == CampusAttendance.batch_id)
        .filter(
            InstitutionBatch.institution_id == institution_id,
            CampusAttendance.day == today,
            CampusAttendance.status.in_(("absent", "late")),
        )
    )
    if actor.role not in institution_svc.STAFF:
        attendance_query = attendance_query.filter(
            CampusAttendance.member_id == actor.id
        )
    attendance_count = attendance_query.count()
    if attendance_count:
        items.append(
            {
                "id": f"attendance:{today.isoformat()}",
                "type": "attendance",
                "title": "Attendance needs attention",
                "detail": (
                    f"{attendance_count} learners are absent or late today."
                    if actor.role in institution_svc.STAFF
                    else "Your attendance was marked absent or late today."
                ),
                "starts_at": None,
                "due_on": today.isoformat(),
                "severity": "alert",
                "href": "academics",
                "read_at": None,
            }
        )

    goal_query = (
        db.query(CampusGoal)
        .join(InstitutionMember, InstitutionMember.id == CampusGoal.member_id)
        .filter(
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.status == "active",
            CampusGoal.status != "completed",
            CampusGoal.due_on >= today,
            CampusGoal.due_on <= horizon,
        )
    )
    if actor.role not in institution_svc.STAFF:
        goal_query = goal_query.filter(CampusGoal.member_id == actor.id)
    for goal in goal_query.order_by(CampusGoal.due_on).limit(30):
        items.append(
            {
                "id": f"goal:{goal.id}",
                "type": "goal",
                "title": goal.title,
                "detail": f"Learning goal · {goal.progress}% complete",
                "starts_at": None,
                "due_on": goal.due_on.isoformat(),
                "severity": "info",
                "href": "daily",
                "read_at": None,
            }
        )

    for announcement in (
        _visible_announcements(db, institution_id, actor)
        .order_by(CampusAnnouncement.id.desc())
        .limit(20)
    ):
        notice = pilot_svc.announcement_dict(db, announcement, actor)
        items.append(
            {
                "id": f"announcement:{announcement.id}",
                "type": "announcement",
                "title": announcement.title,
                "detail": announcement.body[:180],
                "starts_at": notice["created_at"],
                "due_on": None,
                "severity": "info",
                "href": "daily",
                "read_at": notice["read_at"],
            }
        )

    def order_key(item):
        return item["starts_at"] or item["due_on"] or "9999-12-31"

    return sorted(items, key=order_key)[:100]


@router.get("/{institution_id}/pilot/goals")
def goals(
    institution_id: int,
    member_id: int | None = None,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_svc.scope(db, institution_id, user)
    if member_id and member_id != actor.id:
        if actor.role not in institution_svc.STAFF:
            raise HTTPException(404, "Learner goals not found.")
        pilot_svc.member_scope(db, institution_id, member_id, students_only=True)
    query = db.query(CampusGoal).join(
        InstitutionMember, InstitutionMember.id == CampusGoal.member_id
    )
    if actor.role in institution_svc.STAFF:
        query = query.filter(
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.status == "active",
            InstitutionMember.role == "student",
        )
        if member_id:
            query = query.filter(CampusGoal.member_id == member_id)
    else:
        query = query.filter(CampusGoal.member_id == actor.id)
    rows = query.order_by(CampusGoal.due_on, CampusGoal.id).limit(500).all()
    return [{**pilot_svc.goal_dict(db, row), "can_edit": True} for row in rows]


@router.post("/{institution_id}/pilot/goals", status_code=201)
def goal_create(
    institution_id: int,
    data: GoalCreate,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_svc.scope(db, institution_id, user, lock=True)
    member_id = data.member_id or actor.id
    if member_id != actor.id and actor.role not in institution_svc.STAFF:
        raise HTTPException(404, "Learner not found.")
    target = pilot_svc.member_scope(db, institution_id, member_id)
    if target.role != "student":
        raise HTTPException(422, "Goals can only be assigned to active learners.")
    row = CampusGoal(
        member_id=target.id,
        title=data.title.strip(),
        due_on=data.target_date,
        progress=0,
        status="planned",
        completed=False,
        created_by=user.id,
    )
    db.add(row)
    institution_svc.save(db)
    db.refresh(row)
    return pilot_svc.goal_dict(db, row)


@router.patch("/{institution_id}/pilot/goals/{goal_id}")
def goal_update(
    institution_id: int,
    goal_id: int,
    data: GoalUpdate,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_svc.scope(db, institution_id, user, lock=True)
    row = (
        db.query(CampusGoal)
        .join(InstitutionMember, InstitutionMember.id == CampusGoal.member_id)
        .filter(
            CampusGoal.id == goal_id,
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.status == "active",
        )
        .first()
    )
    if not row or (
        actor.role not in institution_svc.STAFF and row.member_id != actor.id
    ):
        raise HTTPException(404, "Learner goal not found.")
    changes = data.model_dump(exclude_unset=True)
    if "title" in changes:
        row.title = changes["title"].strip()
    if "target_date" in changes:
        row.due_on = changes["target_date"]
    if "status" in changes:
        row.status = changes["status"]
        if row.status == "completed":
            row.progress = 100
    if "progress" in changes:
        row.progress = changes["progress"]
        row.status = (
            "completed"
            if row.progress == 100
            else "in_progress"
            if row.progress
            else "planned"
        )
    row.completed = row.status == "completed"
    institution_svc.save(db)
    return pilot_svc.goal_dict(db, row)


@router.get("/{institution_id}/pilot/grading-policy")
def grading_policy(institution_id: int, db: Session = Depends(get_db), user=Current):
    institution_svc.scope(db, institution_id, user)
    row = db.get(CampusGradePolicy, institution_id)
    return {
        "bands": row.bands if row else pilot_svc.DEFAULT_BANDS,
        "customized": bool(row),
    }


@router.put("/{institution_id}/pilot/grading-policy")
def grading_policy_save(
    institution_id: int,
    data: GradePolicySave,
    db: Session = Depends(get_db),
    user=Current,
):
    institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    row = db.get(CampusGradePolicy, institution_id)
    if not row:
        row = CampusGradePolicy(institution_id=institution_id)
        db.add(row)
    row.bands = [band.model_dump() for band in data.bands]
    institution_svc.audit(
        db, institution_id, user, "grading.policy_updated", "Grade bands"
    )
    institution_svc.save(db)
    return {"bands": row.bands, "customized": True}


@router.get("/{institution_id}/pilot/report-cards/{member_id:int}")
def report_card(
    institution_id: int,
    member_id: int,
    term_id: int | None = None,
    db: Session = Depends(get_db),
    user=Current,
):
    institution, actor = institution_svc.scope(db, institution_id, user)
    return pilot_svc.report_card(
        db, institution, actor, member_id, _latest_term_id(db, institution_id, term_id)
    )


@router.put("/{institution_id}/pilot/report-cards/{member_id:int}/comment")
def report_comment(
    institution_id: int,
    member_id: int,
    data: ReportCommentSave,
    db: Session = Depends(get_db),
    user=Current,
):
    institution, actor = institution_svc.scope(
        db, institution_id, user, institution_svc.STAFF, lock=True
    )
    pilot_svc.report_card(db, institution, actor, member_id, data.term_id)
    row = (
        db.query(CampusReportComment)
        .filter_by(member_id=member_id, term_id=data.term_id)
        .first()
    )
    if not row:
        row = CampusReportComment(member_id=member_id, term_id=data.term_id)
        db.add(row)
    row.comment = data.overall_comment.strip()
    row.updated_by = user.id
    institution_svc.save(db)
    return pilot_svc.report_card(db, institution, actor, member_id, data.term_id)


@router.get("/{institution_id}/pilot/report-cards/{member_id:int}.pdf")
def report_card_pdf(
    institution_id: int,
    member_id: int,
    term_id: int | None = None,
    db: Session = Depends(get_db),
    user=Current,
):
    institution, actor = institution_svc.scope(db, institution_id, user)
    report = pilot_svc.report_card(
        db, institution, actor, member_id, _latest_term_id(db, institution_id, term_id)
    )
    content = build_report_card_pdf(report, db.get(CampusBranding, institution_id))
    filename = f"campus-report-{member_id}-{report['term_id']}.pdf"
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{institution_id}/pilot/whatsapp/status")
def whatsapp_status(institution_id: int, db: Session = Depends(get_db), user=Current):
    _, actor = institution_svc.scope(db, institution_id, user)
    result = whatsapp_svc.configuration_status()
    contact = db.get(WhatsAppContact, actor.user_id)
    result.update(whatsapp_svc.contact_status(contact))
    return result


@router.post("/{institution_id}/pilot/whatsapp/opt-in")
def whatsapp_opt_in(
    institution_id: int,
    data: WhatsAppOptIn,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = institution_svc.scope(db, institution_id, user, lock=True)
    result = whatsapp_svc.begin_opt_in(db, actor.user_id, data.phone)
    if result is None:
        raise HTTPException(
            503,
            "WhatsApp opt-in is unavailable until the business phone and signed webhook are configured.",
        )
    return result


@router.delete("/{institution_id}/pilot/whatsapp/opt-in")
def whatsapp_opt_out(institution_id: int, db: Session = Depends(get_db), user=Current):
    _, actor = institution_svc.scope(db, institution_id, user, lock=True)
    return whatsapp_svc.revoke_opt_in(db, actor.user_id)


@router.get("/{institution_id}/pilot/whatsapp/contacts")
def whatsapp_contacts(institution_id: int, db: Session = Depends(get_db), user=Current):
    institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS)
    rows = (
        db.query(InstitutionMember, User, WhatsAppContact)
        .join(User, User.id == InstitutionMember.user_id)
        .outerjoin(
            WhatsAppContact,
            WhatsAppContact.user_id == InstitutionMember.user_id,
        )
        .filter(InstitutionMember.institution_id == institution_id)
        .order_by(User.display_name)
        .all()
    )
    return [
        {
            "member_id": member.id,
            "name": account.display_name,
            "phone": _masked_phone(contact.phone) if contact else None,
            "status": contact.status if contact else "not_started",
            "member_status": member.status,
            "consent_at": institution_svc.utc(contact.consent_at).isoformat()
            if contact and contact.consent_at
            else None,
        }
        for member, account, contact in rows
    ]


@router.get("/{institution_id}/pilot/whatsapp/campaigns")
def whatsapp_campaigns(
    institution_id: int, db: Session = Depends(get_db), user=Current
):
    institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS)
    return [
        _campaign_dict(db, row)
        for row in db.query(CampusWhatsAppCampaign)
        .filter_by(institution_id=institution_id)
        .order_by(CampusWhatsAppCampaign.id.desc())
        .limit(200)
    ]


@router.post("/{institution_id}/pilot/whatsapp/campaigns", status_code=201)
def whatsapp_campaign_create(
    institution_id: int,
    data: WhatsAppCampaignCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Current,
):
    institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    status = whatsapp_svc.configuration_status()
    if not status["configured"]:
        raise HTTPException(503, "WhatsApp Cloud API is not fully configured.")
    if data.template not in status["approved_templates"]:
        raise HTTPException(422, "Select an approved WhatsApp template.")
    if data.batch_id:
        institution_svc.batch_scope(db, institution_id, data.batch_id)
    header_url = str(data.header_image_url) if data.header_image_url else ""
    existing = _existing_whatsapp_campaign(db, institution_id, data, header_url)
    if existing:
        return _campaign_dict(db, existing)

    campaign = CampusWhatsAppCampaign(
        institution_id=institution_id,
        request_key=data.request_key,
        template=data.template,
        language=data.language,
        parameters=data.parameters,
        batch_id=data.batch_id,
        header_image_url=header_url,
        created_by=user.id,
    )
    campaign, created = _claim_whatsapp_campaign(
        db, campaign, institution_id, data, header_url
    )
    if not created:
        return _campaign_dict(db, campaign)
    try:
        recipient_count = campaign_svc.enqueue_campus_recipients(
            db,
            campaign_id=campaign.id,
            institution_id=institution_id,
            batch_id=data.batch_id,
        )
        if not recipient_count:
            raise HTTPException(
                422, "No active, opted-in recipients match this audience."
            )
        institution_svc.audit(
            db,
            institution_id,
            user,
            "whatsapp.campaign_created",
            f"{data.template}: {recipient_count} recipient(s)",
        )
        institution_svc.save(db)
    except Exception:
        db.rollback()
        raise
    db.refresh(campaign)
    background.add_task(whatsapp_svc.deliver_pending)
    return _campaign_dict(db, campaign)


@webhook_router.get("/webhook")
def whatsapp_webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    if (
        hub_mode != "subscribe"
        or not get_settings().WHATSAPP_VERIFY_TOKEN
        or not secrets.compare_digest(
            hub_verify_token or "", get_settings().WHATSAPP_VERIFY_TOKEN
        )
    ):
        raise HTTPException(403, "Webhook verification failed.")
    return Response(hub_challenge or "", media_type="text/plain")


@webhook_router.post("/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    if len(body) > 1_000_000:
        raise HTTPException(413, "Webhook payload is too large.")
    if not whatsapp_svc.verify_signature(
        body, request.headers.get("x-hub-signature-256", "")
    ):
        raise HTTPException(401, "Invalid webhook signature.")
    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        raise HTTPException(400, "Invalid webhook payload.") from None
    if (
        not isinstance(payload, dict)
        or payload.get("object") != "whatsapp_business_account"
    ):
        raise HTTPException(400, "Unsupported webhook payload.")
    whatsapp_svc.process_webhook(db, payload)
    return {"status": "accepted"}
