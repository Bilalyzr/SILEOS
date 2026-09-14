"""Tenant-scoped campus pilot workflows shared by the API and exports."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_

from app.models.campus_operations import (
    CampusAssessment,
    CampusAttendance,
    CampusBranding,
    CampusScore,
    CampusTerm,
)
from app.models.campus_pilot import (
    CampusAnnouncement,
    CampusEvent,
    CampusGoal,
    CampusGradePolicy,
    CampusNoticeRead,
    CampusOnboardingState,
    CampusReportComment,
)
from app.models.institution import (
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionMember,
)
from app.models.user import User
from app.services import institution_service as institution_svc


DEFAULT_BANDS = [
    {"label": "A+", "min_percent": 90.0},
    {"label": "A", "min_percent": 80.0},
    {"label": "B", "min_percent": 70.0},
    {"label": "C", "min_percent": 60.0},
    {"label": "D", "min_percent": 50.0},
    {"label": "Needs support", "min_percent": 0.0},
]


def member_scope(db, institution_id, member_id, *, students_only=False):
    member = (
        db.query(InstitutionMember)
        .filter_by(id=member_id, institution_id=institution_id, status="active")
        .first()
    )
    if not member or (students_only and member.role != "student"):
        raise HTTPException(404, "Campus member not found.")
    return member


def batch_name(db, batch_id):
    if not batch_id:
        return None
    row = db.get(InstitutionBatch, batch_id)
    return row.name if row else None


def onboarding(db, institution, actor):
    from app.models.campus_operations import CampusLearningCourse

    state = db.get(CampusOnboardingState, institution.id)
    steps = [
        {
            "key": "profile",
            "label": "Confirm campus profile",
            "complete": bool(institution.name and institution.academic_year),
            "href": "settings",
        },
        {
            "key": "branding",
            "label": "Add a campus banner",
            "complete": db.get(CampusBranding, institution.id) is not None,
            "href": "settings",
        },
        {
            "key": "batches",
            "label": "Create the first class or batch",
            "complete": db.query(InstitutionBatch)
            .filter_by(institution_id=institution.id)
            .first()
            is not None,
            "href": "batches",
        },
        {
            "key": "staff",
            "label": "Add a teacher",
            "complete": db.query(InstitutionMember)
            .filter(
                InstitutionMember.institution_id == institution.id,
                InstitutionMember.status == "active",
                InstitutionMember.role.in_(("admin", "teacher")),
            )
            .first()
            is not None,
            "href": "people",
        },
        {
            "key": "students",
            "label": "Add learners",
            "complete": db.query(InstitutionMember)
            .filter_by(institution_id=institution.id, status="active", role="student")
            .first()
            is not None,
            "href": "people",
        },
        {
            "key": "term",
            "label": "Set the first academic term",
            "complete": db.query(CampusTerm)
            .filter_by(institution_id=institution.id)
            .first()
            is not None,
            "href": "academics",
        },
        {
            "key": "timetable",
            "label": "Schedule the first class",
            "complete": db.query(CampusEvent)
            .filter_by(institution_id=institution.id)
            .first()
            is not None,
            "href": "daily",
        },
        {
            "key": "course",
            "label": "Publish a campus course",
            "complete": db.query(CampusLearningCourse)
            .filter_by(institution_id=institution.id, published=True)
            .first()
            is not None,
            "href": "courses",
        },
    ]
    completed = sum(1 for step in steps if step["complete"])
    return {
        "dismissed": bool(state and state.dismissed),
        "progress": round(completed * 100 / len(steps)),
        "completed_steps": completed,
        "total_steps": len(steps),
        "steps": steps,
    }


def event_dict(db, row):
    from app.services.campus_staff import substitute_for_event

    substitute_id, substitute_name = substitute_for_event(db, row.id)
    return {
        "id": row.id,
        "series_id": row.series,
        "title": row.title,
        "kind": row.kind,
        "starts_at": institution_svc.utc(row.starts_at).isoformat(),
        "ends_at": institution_svc.utc(row.ends_at).isoformat(),
        "batch_id": row.batch_id,
        "batch_name": batch_name(db, row.batch_id),
        "teacher_member_id": row.teacher_id,
        "substitute_member_id": substitute_id,
        "substitute_name": substitute_name,
        "location": row.room,
        "description": row.description,
    }


def _conflicts(db, institution_id, starts_at, ends_at, batch_id, teacher_id, room):
    resources = []
    if batch_id:
        resources.append(CampusEvent.batch_id == batch_id)
    if teacher_id:
        resources.append(CampusEvent.teacher_id == teacher_id)
    if room.strip():
        resources.append(func.lower(CampusEvent.room) == room.strip().lower())
    if not resources:
        return []
    return (
        db.query(CampusEvent)
        .filter(
            CampusEvent.institution_id == institution_id,
            CampusEvent.starts_at < ends_at,
            CampusEvent.ends_at > starts_at,
            or_(*resources),
        )
        .all()
    )


def create_events(db, institution_id, user, data):
    _, actor = institution_svc.scope(
        db, institution_id, user, institution_svc.STAFF, lock=True
    )
    if data.batch_id:
        institution_svc.batch_scope(db, institution_id, data.batch_id)
    if data.teacher_member_id:
        teacher = member_scope(db, institution_id, data.teacher_member_id)
        if teacher.role not in institution_svc.STAFF:
            raise HTTPException(
                422, "The selected teacher must be an active staff member."
            )

    delta = {"none": None, "daily": timedelta(days=1), "weekly": timedelta(days=7)}[
        data.recurrence
    ]
    windows = [(data.starts_at, data.ends_at)]
    if delta:
        start, end = data.starts_at, data.ends_at
        while (start + delta).date() <= data.repeat_until:
            start, end = start + delta, end + delta
            windows.append((start, end))
    if len(windows) > 367:
        raise HTTPException(422, "A series can contain at most 367 events.")

    normalized = [
        (start.astimezone(timezone.utc), end.astimezone(timezone.utc))
        for start, end in windows
    ]
    for index, (start, end) in enumerate(normalized):
        conflicts = _conflicts(
            db,
            institution_id,
            start,
            end,
            data.batch_id,
            data.teacher_member_id,
            data.location,
        )
        for prior_start, prior_end in normalized[:index]:
            if start < prior_end and end > prior_start:
                raise HTTPException(
                    409,
                    "The recurring event overlaps another occurrence in this series.",
                )
        if conflicts:
            labels = ", ".join(sorted({row.title for row in conflicts})[:3])
            raise HTTPException(409, f"Timetable conflict with: {labels}.")

    series = uuid4().hex
    rows = []
    for start, end in normalized:
        row = CampusEvent(
            institution_id=institution_id,
            batch_id=data.batch_id,
            teacher_id=data.teacher_member_id,
            title=data.title.strip(),
            kind=data.kind,
            room=data.location.strip(),
            description=data.description.strip(),
            starts_at=start,
            ends_at=end,
            series=series,
            created_by=user.id,
        )
        db.add(row)
        rows.append(row)
    institution_svc.audit(
        db,
        institution_id,
        user,
        "calendar.series_created",
        f"{data.title}: {len(rows)} event(s)",
    )
    institution_svc.save(db)
    for row in rows:
        db.refresh(row)
    return {
        "series_id": series,
        "created_count": len(rows),
        "events": [event_dict(db, row) for row in rows],
    }


def announcement_dict(db, row, actor):
    read = (
        db.query(CampusNoticeRead)
        .filter_by(announcement_id=row.id, member_id=actor.id)
        .first()
    )
    return {
        "id": row.id,
        "title": row.title,
        "body": row.body,
        "audience": "batch" if row.batch_id else "institution",
        "batch_id": row.batch_id,
        "batch_name": batch_name(db, row.batch_id),
        "created_at": institution_svc.utc(row.created_at).isoformat(),
        "read_at": institution_svc.utc(read.read_at).isoformat() if read else None,
    }


def goal_dict(db, row):
    member = db.get(InstitutionMember, row.member_id)
    user = db.get(User, member.user_id) if member else None
    return {
        "id": row.id,
        "member_id": row.member_id,
        "student_name": user.display_name if user else "Learner",
        "title": row.title,
        "target_date": row.due_on.isoformat(),
        "progress": row.progress,
        "status": row.status,
    }


def grade_for(percent, bands):
    return next(
        (band["label"] for band in bands if percent >= float(band["min_percent"])),
        bands[-1]["label"],
    )


def report_card(db, institution, actor, member_id, term_id):
    member = member_scope(db, institution.id, member_id, students_only=True)
    if actor.role not in institution_svc.STAFF and actor.id != member.id:
        raise HTTPException(404, "Report card not found.")
    term = (
        db.query(CampusTerm)
        .filter_by(id=term_id, institution_id=institution.id)
        .first()
    )
    if not term:
        raise HTTPException(404, "Academic term not found.")
    batch_ids = [
        batch_id
        for batch_id, in db.query(InstitutionBatchMember.batch_id).filter_by(
            member_id=member.id
        )
    ]
    assessments = (
        db.query(CampusAssessment)
        .join(InstitutionBatch, InstitutionBatch.id == CampusAssessment.batch_id)
        .filter(
            InstitutionBatch.institution_id == institution.id,
            CampusAssessment.term_id == term.id,
            CampusAssessment.batch_id.in_(batch_ids),
        )
        .order_by(CampusAssessment.id)
        .all()
        if batch_ids
        else []
    )
    policy = db.get(CampusGradePolicy, institution.id)
    bands = policy.bands if policy else DEFAULT_BANDS
    rows = []
    total_score = 0.0
    total_max = 0.0
    for assessment in assessments:
        score = (
            db.query(CampusScore)
            .filter_by(assessment_id=assessment.id, member_id=member.id)
            .first()
        )
        percent = (score.score * 100 / assessment.max_score) if score else None
        rows.append(
            {
                "subject": assessment.title,
                "score": score.score if score else None,
                "max_score": assessment.max_score,
                "grade": grade_for(percent, bands)
                if percent is not None
                else "Pending",
                "comment": score.feedback if score else "",
            }
        )
        if score:
            total_score += score.score
            total_max += assessment.max_score
    # Published examinations for the term join the card as extra rows.
    from app.services import campus_exams as exam_svc

    for exam_row in exam_svc.report_card_rows(db, institution, member, term):
        percent = (
            exam_row["score"] * 100 / exam_row["max_score"]
            if exam_row["score"] is not None
            else None
        )
        rows.append(
            {
                "subject": exam_row["subject"],
                "score": exam_row["score"],
                "max_score": exam_row["max_score"],
                "grade": "Absent"
                if exam_row["absent"]
                else (grade_for(percent, bands) if percent is not None else "Pending"),
                "comment": exam_row["comment"],
            }
        )
        if exam_row["score"] is not None:
            total_score += exam_row["score"]
            total_max += exam_row["max_score"]
    comment = (
        db.query(CampusReportComment)
        .filter_by(member_id=member.id, term_id=term.id)
        .first()
    )
    attendance_rows = (
        db.query(CampusAttendance)
        .filter(
            CampusAttendance.member_id == member.id,
            CampusAttendance.batch_id.in_(batch_ids),
            CampusAttendance.day >= term.starts_on,
            CampusAttendance.day <= term.ends_on,
        )
        .all()
        if batch_ids
        else []
    )
    present = sum(1 for row in attendance_rows if row.status in ("present", "late"))
    student = db.get(User, member.user_id)
    overall_percent = round(total_score * 100 / total_max, 1) if total_max else None
    return {
        "member_id": member.id,
        "student_name": student.display_name,
        "institution_name": institution.name,
        "term_id": term.id,
        "term_name": term.name,
        "status": "complete"
        if rows and all(row["score"] is not None for row in rows)
        else "draft",
        "rows": rows,
        "overall_percent": overall_percent,
        "overall_grade": grade_for(overall_percent, bands)
        if overall_percent is not None
        else "Pending",
        "overall_comment": comment.comment if comment else "",
        "attendance_percent": round(present * 100 / len(attendance_rows), 1)
        if attendance_rows
        else None,
    }
