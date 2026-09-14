"""Role-aware daily campus summary and assignable action items."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import func

from app.models.campus_action_center import CampusActionItem
from app.models.campus_operations import CampusAssessment, CampusAttendance, CampusScore
from app.models.campus_pilot import (
    CampusAnnouncement,
    CampusEvent,
    CampusGoal,
    CampusNoticeRead,
    CampusWhatsAppCampaign,
    CampusWhatsAppMessage,
)
from app.models.institution import (
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionMember,
)
from app.services import institution_service


def _utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _zone(name):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Kolkata")


def _local_window(institution):
    zone = _zone(institution.timezone)
    now = datetime.now(timezone.utc)
    local_now = now.astimezone(zone)
    start = datetime.combine(local_now.date(), time.min, zone).astimezone(timezone.utc)
    end = start + timedelta(days=1)
    return now, local_now, start, end


def _member_batch_ids(db, member_id):
    return [
        row[0]
        for row in db.query(InstitutionBatchMember.batch_id)
        .filter_by(member_id=member_id)
        .all()
    ]


def _action(row):
    return {
        "id": f"task-{row.id}",
        "kind": row.kind,
        "title": row.title,
        "detail": row.detail,
        "priority": row.priority,
        "status": row.status,
        "due_at": _utc(row.due_at),
        "href": row.action_url or None,
        "cta_label": "Open" if row.action_url else None,
        "owner_name": None,
    }


def _system_action(key, kind, title, detail, priority, href, cta_label="Review"):
    return {
        "id": key,
        "kind": kind,
        "title": title,
        "detail": detail,
        "priority": priority,
        "status": "open",
        "due_at": None,
        "href": href,
        "cta_label": cta_label,
        "owner_name": None,
    }


def today(db, institution_id, user):
    institution, actor = institution_service.scope(db, institution_id, user)
    now, local_now, day_start, day_end = _local_window(institution)
    manager = actor.role in institution_service.MANAGERS
    staff = actor.role in institution_service.STAFF
    batch_ids = _member_batch_ids(db, actor.id)
    base = f"/institutions/{institution_id}"

    event_query = db.query(CampusEvent).filter(
        CampusEvent.institution_id == institution_id,
        CampusEvent.starts_at >= day_start,
        CampusEvent.starts_at < day_end,
    )
    if not staff:
        event_query = event_query.filter(
            (CampusEvent.batch_id.is_(None)) | (CampusEvent.batch_id.in_(batch_ids))
        )
    elif actor.role == "teacher":
        from app.services.campus_staff import substituted_event_ids

        covering = substituted_event_ids(db, actor.id)
        event_query = event_query.filter(
            (CampusEvent.teacher_id == actor.id)
            | (CampusEvent.batch_id.is_(None))
            | (CampusEvent.batch_id.in_(batch_ids))
            | (CampusEvent.id.in_(covering) if covering else False)
        )
    events = event_query.order_by(CampusEvent.starts_at).limit(20).all()

    notice_query = db.query(CampusAnnouncement).filter(
        CampusAnnouncement.institution_id == institution_id
    )
    if not staff:
        notice_query = notice_query.filter(
            (CampusAnnouncement.batch_id.is_(None))
            | (CampusAnnouncement.batch_id.in_(batch_ids))
        )
    announcements = notice_query.order_by(CampusAnnouncement.created_at.desc()).limit(8).all()
    read_ids = {
        row[0]
        for row in db.query(CampusNoticeRead.announcement_id)
        .filter(
            CampusNoticeRead.member_id == actor.id,
            CampusNoticeRead.announcement_id.in_([item.id for item in announcements] or [-1]),
        )
        .all()
    }
    unread = [item for item in announcements if item.id not in read_ids]

    task_query = db.query(CampusActionItem).filter(
        CampusActionItem.institution_id == institution_id,
        CampusActionItem.status.in_(["open", "snoozed"]),
    )
    if manager:
        pass
    elif staff:
        task_query = task_query.filter(
            (CampusActionItem.assigned_member_id.is_(None))
            | (CampusActionItem.assigned_member_id == actor.id)
        )
    else:
        task_query = task_query.filter(CampusActionItem.assigned_member_id == actor.id)
    tasks = [
        row
        for row in task_query.order_by(
            CampusActionItem.due_at.is_(None), CampusActionItem.due_at, CampusActionItem.id
        ).limit(20).all()
        if row.status != "snoozed" or not row.snoozed_until or _utc(row.snoozed_until) <= now
    ]
    actions = [_action(row) for row in tasks]
    admissions_data = None
    fee_data = None

    active_students = db.query(InstitutionMember).filter_by(
        institution_id=institution_id, role="student", status="active"
    ).count()
    today_attendance = (
        db.query(CampusAttendance)
        .join(InstitutionBatch, InstitutionBatch.id == CampusAttendance.batch_id)
        .filter(
            InstitutionBatch.institution_id == institution_id,
            CampusAttendance.day == local_now.date(),
        )
    )
    attendance_total = today_attendance.count()
    present_count = today_attendance.filter(
        CampusAttendance.status.in_(["present", "late", "excused"])
    ).count()
    attendance_percent = (
        round(present_count * 100 / attendance_total) if attendance_total else 0
    )

    if staff:
        from app.services.campus_hostel import pending_pass_count

        waiting_passes = pending_pass_count(db, institution_id)
        if waiting_passes:
            actions.append(
                _system_action(
                    "system-hostel-passes",
                    "hostel",
                    f"{waiting_passes} hostel pass{'es' if waiting_passes != 1 else ''} waiting for a decision",
                    "Residents are waiting to leave campus. Approve or reject their out-passes.",
                    "high",
                    base + "/hostel",
                    "Review passes",
                )
            )
        assessments = (
            db.query(CampusAssessment, InstitutionBatch)
            .join(InstitutionBatch, InstitutionBatch.id == CampusAssessment.batch_id)
            .filter(InstitutionBatch.institution_id == institution_id)
            .all()
        )
        ungraded = 0
        for assessment, batch in assessments:
            learner_count = db.query(InstitutionBatchMember).join(
                InstitutionMember,
                InstitutionMember.id == InstitutionBatchMember.member_id,
            ).filter(
                InstitutionBatchMember.batch_id == batch.id,
                InstitutionMember.role == "student",
                InstitutionMember.status == "active",
            ).count()
            scored = db.query(CampusScore).filter_by(assessment_id=assessment.id).count()
            ungraded += max(0, learner_count - scored)
        if ungraded:
            actions.append(
                _system_action(
                    "system-ungraded",
                    "grading",
                    f"{ungraded} assessment result{'s' if ungraded != 1 else ''} need attention",
                    "Complete grading so learners and families see current progress.",
                    "high",
                    base + "/academics",
                    "Open grading",
                )
            )
        batch_count = db.query(InstitutionBatch).filter_by(
            institution_id=institution_id
        ).count()
        batches_recorded = today_attendance.with_entities(
            func.count(func.distinct(CampusAttendance.batch_id))
        ).scalar() or 0
        if batch_count and batches_recorded < batch_count:
            actions.append(
                _system_action(
                    "system-attendance",
                    "attendance",
                    "Today’s attendance is incomplete",
                    f"{batch_count - batches_recorded} batch{'es' if batch_count - batches_recorded != 1 else ''} still need a register.",
                    "high",
                    base + "/academics",
                    "Take attendance",
                )
            )
        failed_messages = (
            db.query(CampusWhatsAppMessage)
            .join(
                CampusWhatsAppCampaign,
                CampusWhatsAppCampaign.id == CampusWhatsAppMessage.campaign_id,
            )
            .filter(
                CampusWhatsAppCampaign.institution_id == institution_id,
                CampusWhatsAppMessage.status == "failed",
            )
            .count()
        )
        if manager and failed_messages:
            actions.append(
                _system_action(
                    "system-whatsapp",
                    "communication",
                    f"{failed_messages} WhatsApp deliver{'ies' if failed_messages != 1 else 'y'} need review",
                    "Resolve invalid numbers or provider errors before the next campaign.",
                    "normal",
                    base + "/daily?view=whatsapp",
                    "Review delivery",
                )
            )
        if manager:
            from app.services.campus_staff import open_substitutions_soon

            uncovered = open_substitutions_soon(db, institution_id, day_start)
            from app.services.campus_transport import routes_without_boarding_today

            unrecorded_routes = routes_without_boarding_today(db, institution, local_now.date())
            from app.services.tuition_collection import excess_order_count, pending_cash

            cash_count, cash_total = pending_cash(db, institution_id)
            if cash_count:
                actions.append(
                    _system_action(
                        "system-cash-verification",
                        "finance",
                        f"{cash_count} cash payment{'s' if cash_count != 1 else ''} waiting for verification",
                        f"{cash_total:,.2f} received at the counter has not been counted by a second person yet.",
                        "high",
                        base + "/finance?panel=cash",
                        "Open cash desk",
                    )
                )
            excess = excess_order_count(db, institution_id)
            if excess:
                actions.append(
                    _system_action(
                        "system-online-excess",
                        "finance",
                        f"{excess} online payment{'s' if excess != 1 else ''} need a refund",
                        "A gateway payment arrived after the balance was already settled at the counter.",
                        "high",
                        base + "/finance?panel=cash",
                        "Review",
                    )
                )
            if unrecorded_routes:
                actions.append(
                    _system_action(
                        "system-transport",
                        "transport",
                        f"Boarding not recorded for {unrecorded_routes} route{'s' if unrecorded_routes != 1 else ''}",
                        "Mark who boarded and was dropped so families can see today's status.",
                        "normal",
                        base + "/transport",
                        "Record boarding",
                    )
                )
            if uncovered:
                actions.append(
                    _system_action(
                        "system-substitutions",
                        "staff",
                        f"{uncovered} class{'es' if uncovered != 1 else ''} need a substitute this week",
                        "A teacher is on approved leave. Assign a free colleague so the class is covered.",
                        "high",
                        base + "/staff",
                        "Assign substitutes",
                    )
                )
            from app.services import admissions_service, tuition_service

            admissions_data = admissions_service.admissions_summary(
                db, institution_id, user
            )
            if admissions_data["tasks"]["overdue"]:
                overdue_tasks = admissions_data["tasks"]["overdue"]
                actions.append(
                    _system_action(
                        "system-admissions-tasks",
                        "admissions",
                        f"{overdue_tasks} overdue admission task{'s' if overdue_tasks != 1 else ''}",
                        "Review applicant follow-ups and keep decisions moving.",
                        "urgent",
                        base + "/admissions",
                        "Open admissions",
                    )
                )
            try:
                fee_data = tuition_service.summary(db, institution_id, user)
            except HTTPException as error:
                if error.status_code != 409:
                    raise
            if fee_data and fee_data["accounts"]["overdue"]:
                overdue_accounts = fee_data["accounts"]["overdue"]
                currency = fee_data["currency"] or "INR"
                overdue_amount = fee_data["totals"]["overdue"]
                actions.append(
                    _system_action(
                        "system-fee-dues",
                        "finance",
                        f"{overdue_accounts} student account{'s' if overdue_accounts != 1 else ''} overdue",
                        f"{currency} {overdue_amount:,.2f} needs collection follow-up.",
                        "high",
                        base + "/finance",
                        "Review dues",
                    )
                )
    else:
        goals = db.query(CampusGoal).filter(
            CampusGoal.member_id == actor.id,
            CampusGoal.completed.is_(False),
        ).order_by(CampusGoal.due_on).all()
        for goal in goals[:3]:
            priority = "high" if goal.due_on <= local_now.date() else "normal"
            actions.append(
                _system_action(
                    f"goal-{goal.id}",
                    "goal",
                    goal.title,
                    f"{goal.progress}% complete · due {goal.due_on.isoformat()}",
                    priority,
                    base + "/daily?view=goals",
                    "Continue goal",
                )
            )
        if unread:
            actions.append(
                _system_action(
                    "system-notices",
                    "announcement",
                    f"{len(unread)} unread campus update{'s' if len(unread) != 1 else ''}",
                    "Catch up on messages shared with your class.",
                    "normal",
                    base + "/daily?view=announcements",
                    "Read updates",
                )
            )

    if manager:
        metrics = [
            {"key": "students", "label": "Active students", "value": str(active_students), "detail": "Across this institution", "tone": "orange"},
            {"key": "attendance", "label": "Attendance today", "value": f"{attendance_percent}%" if attendance_total else "—", "detail": f"{attendance_total} records captured", "tone": "green" if attendance_percent >= 85 else "amber"},
            {"key": "actions", "label": "Open actions", "value": str(len(actions)), "detail": "Items needing follow-up", "tone": "amber" if actions else "green"},
            {"key": "notices", "label": "Recent notices", "value": str(len(announcements)), "detail": "Latest campus communication", "tone": "blue"},
        ]
        if admissions_data is not None:
            metrics[2] = {
                "key": "admissions",
                "label": "Active applicants",
                "value": str(admissions_data["counts"]["active"]),
                "detail": f"{admissions_data['counts']['enrolled']} enrolled",
                "tone": "orange",
            }
        if fee_data is not None:
            metrics[3] = {
                "key": "fees",
                "label": "Fee collection",
                "value": f"{fee_data['currency'] or 'INR'} {fee_data['totals']['paid']:,.0f}",
                "detail": f"{fee_data['accounts']['overdue']} overdue accounts",
                "tone": "green" if not fee_data["accounts"]["overdue"] else "amber",
            }
        headline = "Your campus priorities are ready."
    elif staff:
        metrics = [
            {"key": "classes", "label": "Today’s schedule", "value": str(len(events)), "detail": "Classes and campus events", "tone": "orange"},
            {"key": "attendance", "label": "Attendance recorded", "value": str(attendance_total), "detail": "Learner records today", "tone": "green"},
            {"key": "actions", "label": "Teaching actions", "value": str(len(actions)), "detail": "Grading and follow-ups", "tone": "amber"},
            {"key": "notices", "label": "Updates", "value": str(len(announcements)), "detail": "Campus announcements", "tone": "blue"},
        ]
        headline = "Everything for today’s teaching, in one view."
    else:
        my_attendance = today_attendance.filter(CampusAttendance.member_id == actor.id).first()
        open_goals = db.query(CampusGoal).filter_by(member_id=actor.id, completed=False).count()
        metrics = [
            {"key": "classes", "label": "Today’s schedule", "value": str(len(events)), "detail": "Classes and events", "tone": "orange"},
            {"key": "attendance", "label": "Attendance", "value": my_attendance.status.title() if my_attendance else "Pending", "detail": "Today’s register", "tone": "green" if my_attendance and my_attendance.status == "present" else "amber"},
            {"key": "goals", "label": "Active goals", "value": str(open_goals), "detail": "Your current priorities", "tone": "blue"},
            {"key": "updates", "label": "Unread updates", "value": str(len(unread)), "detail": "From your campus", "tone": "amber" if unread else "green"},
        ]
        headline = "Here’s your clearest path through today."

    hour = local_now.hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    return {
        "role": actor.role,
        "generated_at": now,
        "greeting": greeting,
        "headline": headline,
        "metrics": metrics,
        "actions": actions[:30],
        "schedule": [
            {
                "id": item.id,
                "title": item.title,
                "kind": item.kind,
                "starts_at": _utc(item.starts_at),
                "ends_at": _utc(item.ends_at),
                "location": item.room,
                "href": base + "/daily?view=timetable",
            }
            for item in events
        ],
        "notices": [
            {
                "id": item.id,
                "title": item.title,
                "detail": item.body[:240],
                "tone": "new" if item.id in {row.id for row in unread} else "read",
                "href": base + "/daily?view=announcements",
            }
            for item in announcements[:5]
        ],
    }


def create_action(db, institution_id, user, data):
    institution_service.scope(db, institution_id, user, institution_service.STAFF)
    if data.assigned_member_id is not None:
        assignee = db.query(InstitutionMember).filter_by(
            id=data.assigned_member_id,
            institution_id=institution_id,
            status="active",
        ).first()
        if not assignee:
            raise HTTPException(404, "Assignee not found in this institution.")
    row = CampusActionItem(
        institution_id=institution_id,
        kind=data.kind,
        title=data.title.strip(),
        detail=data.detail.strip(),
        priority=data.priority,
        assigned_member_id=data.assigned_member_id,
        due_at=data.due_at,
        action_url=data.href.strip(),
        created_by=user.id,
    )
    db.add(row)
    institution_service.audit(db, institution_id, user, "action.created", row.title)
    institution_service.save(db)
    db.refresh(row)
    return _action(row)


def update_action(db, institution_id, action_id, user, status):
    institution_service.scope(db, institution_id, user)
    if not action_id.startswith("task-") or not action_id[5:].isdigit():
        raise HTTPException(409, "Open the linked workflow to complete this action.")
    row = db.query(CampusActionItem).filter_by(
        id=int(action_id[5:]), institution_id=institution_id
    ).first()
    if not row:
        raise HTTPException(404, "Action not found.")
    _, actor = institution_service.scope(db, institution_id, user)
    can_manage = actor.role in institution_service.STAFF
    if not can_manage and row.assigned_member_id != actor.id:
        raise HTTPException(404, "Action not found.")
    row.status = status
    now = datetime.now(timezone.utc)
    row.completed_at = now if status == "done" else None
    row.snoozed_until = now + timedelta(days=1) if status == "snoozed" else None
    institution_service.audit(db, institution_id, user, "action.updated", f"#{row.id}: {status}")
    institution_service.save(db)
    db.refresh(row)
    return _action(row)
