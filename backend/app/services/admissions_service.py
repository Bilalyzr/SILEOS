"""Business rules for tenant-scoped admissions and learner lifecycle.

Every public function receives the authenticated user and re-checks active
institution membership.  Applicant PII is limited to institution owners and
administrators; the platform administrator role is not an implicit bypass.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from html import escape
from io import BytesIO
import secrets

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.admissions import (
    AdmissionApplication,
    AdmissionDocument,
    AdmissionIntake,
    AdmissionNote,
    AdmissionProgram,
    AdmissionStageHistory,
    AdmissionTask,
    CampusLearnerLifecycleHistory,
    CampusLearnerProfile,
)
from app.models.campus_operations import CampusBranding
from app.models.institution import (
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionInvite,
    InstitutionMember,
)
from app.models.user import User
from app.schemas.institution import InviteCreate
from app.services import institution_service as institution_svc


ACTIVE_APPLICATION_STAGES = {
    "draft",
    "submitted",
    "screening",
    "documents",
    "assessment",
    "interview",
    "decision",
    "waitlisted",
    "offered",
    "admitted",
}
STAGE_TRANSITIONS = {
    "draft": {"submitted", "withdrawn"},
    "submitted": {"screening", "documents", "withdrawn"},
    "screening": {
        "documents",
        "assessment",
        "interview",
        "decision",
        "waitlisted",
        "rejected",
        "withdrawn",
    },
    "documents": {
        "screening",
        "assessment",
        "interview",
        "decision",
        "waitlisted",
        "rejected",
        "withdrawn",
    },
    "assessment": {"interview", "decision", "waitlisted", "rejected", "withdrawn"},
    "interview": {"decision", "waitlisted", "rejected", "withdrawn"},
    "decision": {"offered", "admitted", "waitlisted", "rejected", "withdrawn"},
    "waitlisted": {"screening", "decision", "offered", "rejected", "withdrawn"},
    "offered": {"admitted", "waitlisted", "rejected", "withdrawn"},
    "admitted": {"enrolled", "withdrawn"},
    "rejected": {"screening"},
    "withdrawn": {"screening"},
    "enrolled": set(),
}
OFFER_TRANSITIONS = {
    "none": {"draft", "issued"},
    "draft": {"none", "issued", "revoked"},
    "issued": {"accepted", "declined", "expired", "revoked"},
    "accepted": {"revoked"},
    "declined": {"draft", "issued"},
    "expired": {"draft", "issued"},
    "revoked": {"draft", "issued"},
}
DOCUMENT_TRANSITIONS = {
    "pending": {"submitted", "waived"},
    "submitted": {"verified", "rejected", "waived"},
    "verified": {"rejected"},
    "rejected": {"submitted", "waived"},
    "waived": {"pending"},
}
TASK_TRANSITIONS = {
    "open": {"in_progress", "completed", "cancelled"},
    "in_progress": {"open", "completed", "cancelled"},
    "completed": {"open"},
    "cancelled": {"open"},
}
LEARNER_TRANSITIONS = {
    "enrolled": {"active", "on_leave", "withdrawn", "transferred"},
    "active": {"on_leave", "completed", "withdrawn", "transferred"},
    "on_leave": {"active", "withdrawn", "transferred"},
    "completed": set(),
    "withdrawn": set(),
    "transferred": set(),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _commit(
    db: Session, conflict: str = "This admissions record already exists."
) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, conflict) from None


def _manager_scope(db: Session, institution_id: int, user, *, lock: bool = False):
    return institution_svc.scope(
        db, institution_id, user, institution_svc.MANAGERS, lock=lock
    )


def _program(db: Session, institution_id: int, program_id: int, *, lock: bool = False):
    query = db.query(AdmissionProgram).filter_by(
        id=program_id, institution_id=institution_id
    )
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Program not found.")
    return row


def _intake(db: Session, institution_id: int, intake_id: int, *, lock: bool = False):
    query = db.query(AdmissionIntake).filter_by(
        id=intake_id, institution_id=institution_id
    )
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Intake not found.")
    return row


def _application(
    db: Session, institution_id: int, application_id: int, *, lock: bool = False
):
    query = db.query(AdmissionApplication).filter_by(
        id=application_id, institution_id=institution_id
    )
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Application not found.")
    return row


def _active_member(
    db: Session,
    institution_id: int,
    member_id: int,
    *,
    roles: tuple[str, ...] | None = None,
):
    row = (
        db.query(InstitutionMember)
        .filter_by(id=member_id, institution_id=institution_id, status="active")
        .first()
    )
    if not row or (roles and row.role not in roles):
        raise HTTPException(422, "Choose an eligible member from this institution.")
    return row


def _assert_version(row, expected: int) -> None:
    if row.version != expected:
        raise HTTPException(
            409,
            "This record changed after you opened it. Refresh before trying again.",
        )


def _record_stage(
    db: Session, application, actor, old: str | None, new: str, reason: str
):
    db.add(
        AdmissionStageHistory(
            application_id=application.id,
            from_stage=old,
            to_stage=new,
            reason=reason,
            actor_id=actor.id,
        )
    )


def _set_stage(db: Session, application, actor, new: str, reason: str = "") -> None:
    old = application.stage
    if old == new:
        return
    allowed = STAGE_TRANSITIONS.get(old, set())
    if new not in allowed:
        raise HTTPException(409, f"An application cannot move from {old} to {new}.")
    if new in {"rejected", "withdrawn", "waitlisted"} and not reason:
        raise HTTPException(422, f"Add a reason before marking this application {new}.")
    if old in {"rejected", "withdrawn"} and not reason:
        raise HTTPException(422, "Add a reason before reopening this application.")
    application.stage = new
    _record_stage(db, application, actor, old, new, reason)


def _program_dict(row: AdmissionProgram) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "code": row.code,
        "level": row.level,
        "department": row.department,
        "duration_months": row.duration_months,
        "status": row.status,
        "created_at": institution_svc.utc(row.created_at),
    }


def create_program(db: Session, institution_id: int, user, data) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = AdmissionProgram(
        institution_id=institution_id, created_by=user.id, **data.model_dump()
    )
    db.add(row)
    institution_svc.audit(
        db, institution_id, user, "admissions.program_created", data.code
    )
    _commit(db, "A program with this code already exists.")
    db.refresh(row)
    return _program_dict(row)


def list_programs(db: Session, institution_id: int, user) -> list[dict]:
    _manager_scope(db, institution_id, user)
    return [
        _program_dict(row)
        for row in db.query(AdmissionProgram)
        .filter_by(institution_id=institution_id)
        .order_by(AdmissionProgram.name, AdmissionProgram.id)
        .all()
    ]


def update_program(
    db: Session, institution_id: int, program_id: int, user, data
) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = _program(db, institution_id, program_id, lock=True)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("status") == "archived":
        open_intakes = (
            db.query(AdmissionIntake)
            .filter(
                AdmissionIntake.program_id == row.id,
                AdmissionIntake.status.in_(("draft", "open")),
            )
            .count()
        )
        if open_intakes:
            raise HTTPException(
                409, "Close or archive this program's active intakes first."
            )
    for key, value in changes.items():
        setattr(row, key, value)
    institution_svc.audit(
        db, institution_id, user, "admissions.program_updated", row.code
    )
    _commit(db, "A program with this code already exists.")
    db.refresh(row)
    return _program_dict(row)


def _intake_counts(db: Session, intake_ids: list[int]):
    if not intake_ids:
        return {}, {}
    applications = dict(
        db.query(AdmissionApplication.intake_id, func.count(AdmissionApplication.id))
        .filter(AdmissionApplication.intake_id.in_(intake_ids))
        .group_by(AdmissionApplication.intake_id)
        .all()
    )
    enrolled = dict(
        db.query(CampusLearnerProfile.intake_id, func.count(CampusLearnerProfile.id))
        .filter(
            CampusLearnerProfile.intake_id.in_(intake_ids),
            CampusLearnerProfile.status.notin_(("withdrawn", "transferred")),
        )
        .group_by(CampusLearnerProfile.intake_id)
        .all()
    )
    return applications, enrolled


def _intake_dict(
    row: AdmissionIntake, program_name: str, application_count: int, enrolled: int
):
    return {
        "id": row.id,
        "program_id": row.program_id,
        "program_name": program_name,
        "batch_id": row.batch_id,
        "name": row.name,
        "academic_year": row.academic_year,
        "starts_on": row.starts_on,
        "closes_on": row.closes_on,
        "capacity": row.capacity,
        "status": row.status,
        "applications": application_count,
        "enrolled": enrolled,
        "available": max(0, row.capacity - enrolled),
    }


def _serialize_intakes(db: Session, rows) -> list[dict]:
    intake_ids = [row.id for row, _ in rows]
    applications, enrolled = _intake_counts(db, intake_ids)
    return [
        _intake_dict(
            row,
            program.name,
            applications.get(row.id, 0),
            enrolled.get(row.id, 0),
        )
        for row, program in rows
    ]


def create_intake(db: Session, institution_id: int, user, data) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    program = _program(db, institution_id, data.program_id)
    if data.status == "open" and program.status != "active":
        raise HTTPException(409, "Activate the program before opening an intake.")
    if data.batch_id:
        institution_svc.batch_scope(db, institution_id, data.batch_id)
    row = AdmissionIntake(
        institution_id=institution_id, created_by=user.id, **data.model_dump()
    )
    db.add(row)
    institution_svc.audit(
        db, institution_id, user, "admissions.intake_created", data.name
    )
    _commit(db, "This program already has an intake with that name and academic year.")
    db.refresh(row)
    return _serialize_intakes(db, [(row, program)])[0]


def list_intakes(db: Session, institution_id: int, user) -> list[dict]:
    _manager_scope(db, institution_id, user)
    rows = (
        db.query(AdmissionIntake, AdmissionProgram)
        .join(AdmissionProgram, AdmissionProgram.id == AdmissionIntake.program_id)
        .filter(AdmissionIntake.institution_id == institution_id)
        .order_by(AdmissionIntake.starts_on.desc(), AdmissionIntake.id.desc())
        .all()
    )
    return _serialize_intakes(db, rows)


def update_intake(db: Session, institution_id: int, intake_id: int, user, data) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = _intake(db, institution_id, intake_id, lock=True)
    changes = data.model_dump(exclude_unset=True)
    starts_on = changes.get("starts_on", row.starts_on)
    closes_on = changes.get("closes_on", row.closes_on)
    if closes_on > starts_on:
        raise HTTPException(
            422, "Applications must close on or before the intake start date."
        )
    if changes.get("batch_id"):
        institution_svc.batch_scope(db, institution_id, changes["batch_id"])
    program = _program(db, institution_id, row.program_id)
    if changes.get("status") == "open" and program.status != "active":
        raise HTTPException(409, "Activate the program before opening an intake.")
    enrolled = (
        db.query(CampusLearnerProfile)
        .filter(
            CampusLearnerProfile.intake_id == row.id,
            CampusLearnerProfile.status.notin_(("withdrawn", "transferred")),
        )
        .count()
    )
    if changes.get("capacity", row.capacity) < enrolled:
        raise HTTPException(
            409, "Capacity cannot be lower than the current learner count."
        )
    for key, value in changes.items():
        setattr(row, key, value)
    institution_svc.audit(
        db, institution_id, user, "admissions.intake_updated", row.name
    )
    _commit(db, "This program already has an intake with that name and academic year.")
    db.refresh(row)
    return _serialize_intakes(db, [(row, program)])[0]


def _new_reference(prefix: str) -> str:
    return f"{prefix}-{date.today().year}-{secrets.token_hex(4).upper()}"


def _application_list_item(row, program_name: str, intake_name: str) -> dict:
    return {
        "id": row.id,
        "application_number": row.application_number,
        "full_name": row.full_name,
        "email": row.email,
        "phone": row.phone,
        "program_id": row.program_id,
        "program_name": program_name,
        "intake_id": row.intake_id,
        "intake_name": intake_name,
        "stage": row.stage,
        "offer_status": row.offer_status,
        "source": row.source,
        "owner_member_id": row.owner_member_id,
        "enrollment_member_id": row.enrollment_member_id,
        "submitted_at": institution_svc.utc(row.submitted_at),
        "updated_at": institution_svc.utc(row.updated_at),
        "version": row.version,
    }


def create_application(db: Session, institution_id: int, user, data) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    program = _program(db, institution_id, data.program_id)
    intake = _intake(db, institution_id, data.intake_id, lock=True)
    if intake.program_id != program.id:
        raise HTTPException(422, "The intake does not belong to the selected program.")
    if intake.status not in ("draft", "open"):
        raise HTTPException(409, "This intake is not accepting applications.")
    email = str(data.email).lower()
    duplicate = (
        db.query(AdmissionApplication)
        .filter(
            AdmissionApplication.institution_id == institution_id,
            AdmissionApplication.intake_id == intake.id,
            func.lower(AdmissionApplication.email) == email,
            AdmissionApplication.stage.in_(ACTIVE_APPLICATION_STAGES),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            409, "This applicant already has an active application for the intake."
        )
    values = data.model_dump()
    values["email"] = email
    row = AdmissionApplication(
        institution_id=institution_id,
        application_number=_new_reference("APP"),
        created_by=user.id,
        stage="submitted",
        offer_status="none",
        version=1,
        **values,
    )
    db.add(row)
    db.flush()
    _record_stage(db, row, user, None, "submitted", "Application created")
    institution_svc.audit(
        db,
        institution_id,
        user,
        "admissions.application_created",
        row.application_number,
    )
    _commit(db, "An application with this reference already exists. Try again.")
    return _application_detail(db, row)


def list_applications(
    db: Session,
    institution_id: int,
    user,
    *,
    search: str = "",
    stage: str | None = None,
    offer_status: str | None = None,
    intake_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    _manager_scope(db, institution_id, user)
    query = (
        db.query(AdmissionApplication, AdmissionProgram, AdmissionIntake)
        .join(AdmissionProgram, AdmissionProgram.id == AdmissionApplication.program_id)
        .join(AdmissionIntake, AdmissionIntake.id == AdmissionApplication.intake_id)
        .filter(AdmissionApplication.institution_id == institution_id)
    )
    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(AdmissionApplication.full_name).like(pattern),
                func.lower(AdmissionApplication.email).like(pattern),
                func.lower(AdmissionApplication.application_number).like(pattern),
            )
        )
    if stage:
        query = query.filter(AdmissionApplication.stage == stage)
    if offer_status:
        query = query.filter(AdmissionApplication.offer_status == offer_status)
    if intake_id:
        _intake(db, institution_id, intake_id)
        query = query.filter(AdmissionApplication.intake_id == intake_id)
    total = query.count()
    rows = (
        query.order_by(
            AdmissionApplication.updated_at.desc(), AdmissionApplication.id.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [
            _application_list_item(row, program.name, intake.name)
            for row, program, intake in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def update_application(
    db: Session, institution_id: int, application_id: int, user, data
) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = _application(db, institution_id, application_id, lock=True)
    if row.stage == "enrolled":
        raise HTTPException(409, "Edit the learner profile after enrollment.")
    changes = data.model_dump(exclude_unset=True)
    expected_version = changes.pop("expected_version")
    _assert_version(row, expected_version)
    if "owner_member_id" in changes and changes["owner_member_id"] is not None:
        _active_member(
            db,
            institution_id,
            changes["owner_member_id"],
            roles=institution_svc.MANAGERS,
        )
    if "email" in changes and changes["email"] is not None:
        changes["email"] = str(changes["email"]).lower()
    for key, value in changes.items():
        setattr(row, key, value)
    row.version += 1
    institution_svc.audit(
        db,
        institution_id,
        user,
        "admissions.application_updated",
        row.application_number,
    )
    _commit(db)
    return _application_detail(db, row)


def transition_stage(
    db: Session, institution_id: int, application_id: int, user, data
) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = _application(db, institution_id, application_id, lock=True)
    if row.stage == data.stage:
        return _application_detail(db, row)
    _assert_version(row, data.expected_version)
    _set_stage(db, row, user, data.stage, data.reason)
    row.version += 1
    institution_svc.audit(
        db,
        institution_id,
        user,
        "admissions.stage_changed",
        f"{row.application_number}: {row.stage}",
    )
    _commit(db)
    return _application_detail(db, row)


def add_document(
    db: Session, institution_id: int, application_id: int, user, data
) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = _application(db, institution_id, application_id, lock=True)
    document = AdmissionDocument(application_id=row.id, **data.model_dump())
    db.add(document)
    row.updated_at = _now()
    institution_svc.audit(
        db, institution_id, user, "admissions.document_added", row.application_number
    )
    _commit(db, "This checklist already contains a document with that label.")
    return _application_detail(db, row)


def update_document(
    db: Session, institution_id: int, application_id: int, document_id: int, user, data
) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = _application(db, institution_id, application_id, lock=True)
    document = (
        db.query(AdmissionDocument)
        .filter_by(id=document_id, application_id=row.id)
        .with_for_update()
        .first()
    )
    if not document:
        raise HTTPException(404, "Checklist document not found.")
    if document.status == data.status:
        return _application_detail(db, row)
    if data.status not in DOCUMENT_TRANSITIONS.get(document.status, set()):
        raise HTTPException(
            409, f"A document cannot move from {document.status} to {data.status}."
        )
    document.status = data.status
    document.rejection_reason = data.rejection_reason
    if data.status in ("verified", "waived"):
        document.verified_by = user.id
        document.verified_at = _now()
    else:
        document.verified_by = None
        document.verified_at = None
    row.updated_at = _now()
    institution_svc.audit(
        db, institution_id, user, "admissions.document_updated", row.application_number
    )
    _commit(db)
    return _application_detail(db, row)


def add_note(db: Session, institution_id: int, application_id: int, user, data) -> dict:
    _manager_scope(db, institution_id, user)
    row = _application(db, institution_id, application_id)
    db.add(AdmissionNote(application_id=row.id, body=data.body, author_id=user.id))
    row.updated_at = _now()
    institution_svc.audit(
        db, institution_id, user, "admissions.note_added", row.application_number
    )
    _commit(db)
    return _application_detail(db, row)


def _validate_assignee(db: Session, institution_id: int, member_id: int | None) -> None:
    if member_id is not None:
        _active_member(db, institution_id, member_id, roles=institution_svc.MANAGERS)


def add_task(db: Session, institution_id: int, application_id: int, user, data) -> dict:
    _manager_scope(db, institution_id, user)
    row = _application(db, institution_id, application_id)
    _validate_assignee(db, institution_id, data.assignee_member_id)
    db.add(
        AdmissionTask(application_id=row.id, created_by=user.id, **data.model_dump())
    )
    row.updated_at = _now()
    institution_svc.audit(
        db, institution_id, user, "admissions.task_added", row.application_number
    )
    _commit(db)
    return _application_detail(db, row)


def update_task(
    db: Session, institution_id: int, application_id: int, task_id: int, user, data
) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = _application(db, institution_id, application_id, lock=True)
    task = (
        db.query(AdmissionTask)
        .filter_by(id=task_id, application_id=row.id)
        .with_for_update()
        .first()
    )
    if not task:
        raise HTTPException(404, "Admissions task not found.")
    changes = data.model_dump(exclude_unset=True)
    old_status = task.status
    if old_status != data.status and data.status not in TASK_TRANSITIONS.get(
        old_status, set()
    ):
        raise HTTPException(
            409, f"A task cannot move from {old_status} to {data.status}."
        )
    _validate_assignee(db, institution_id, changes.get("assignee_member_id"))
    for key, value in changes.items():
        setattr(task, key, value)
    if old_status != task.status:
        task.completed_at = _now() if task.status == "completed" else None
    row.updated_at = _now()
    institution_svc.audit(
        db, institution_id, user, "admissions.task_updated", row.application_number
    )
    _commit(db)
    return _application_detail(db, row)


def update_offer(
    db: Session, institution_id: int, application_id: int, user, data
) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    row = _application(db, institution_id, application_id, lock=True)
    if row.offer_status == data.status:
        return _application_detail(db, row)
    _assert_version(row, data.expected_version)
    if data.status not in OFFER_TRANSITIONS.get(row.offer_status, set()):
        raise HTTPException(
            409, f"An offer cannot move from {row.offer_status} to {data.status}."
        )
    if data.status == "issued" and row.stage not in {
        "decision",
        "waitlisted",
        "offered",
        "admitted",
    }:
        raise HTTPException(
            409, "Move the application to decision before issuing an offer."
        )
    old_offer = row.offer_status
    row.offer_status = data.status
    if data.status in ("draft", "issued"):
        row.offer_expires_on = data.expires_on
        row.offer_conditions = data.conditions
        row.tuition_amount = data.tuition_amount
        row.offer_currency = data.currency
    if data.status == "issued":
        row.offer_issued_at = _now()
        row.offer_responded_at = None
        if row.stage in ("decision", "waitlisted"):
            _set_stage(db, row, user, "offered", data.reason or "Offer issued")
    elif data.status in ("accepted", "declined"):
        row.offer_responded_at = _now()
        if data.status == "accepted" and row.stage == "offered":
            _set_stage(db, row, user, "admitted", data.reason or "Offer accepted")
    elif data.status == "revoked" and row.stage == "admitted":
        if not data.reason:
            raise HTTPException(422, "Add a reason when revoking an accepted offer.")
        old_stage = row.stage
        row.stage = "decision"
        _record_stage(db, row, user, old_stage, row.stage, data.reason)
    elif data.status == "none":
        row.offer_expires_on = None
        row.offer_conditions = ""
        row.tuition_amount = None
        row.offer_issued_at = None
        row.offer_responded_at = None
    row.version += 1
    institution_svc.audit(
        db,
        institution_id,
        user,
        "admissions.offer_updated",
        f"{row.application_number}: {old_offer} to {row.offer_status}",
    )
    _commit(db)
    return _application_detail(db, row)


def _add_months(value: date, months: int) -> date:
    target = value.month - 1 + months
    year = value.year + target // 12
    month = target % 12 + 1
    month_days = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(value.day, month_days))


def _matching_student_member(
    db: Session, institution_id: int, row, member_id: int | None
):
    if member_id:
        member = _active_member(db, institution_id, member_id, roles=("student",))
        account = db.get(User, member.user_id)
        if not account or account.user_email.lower() != row.email.lower():
            raise HTTPException(
                422, "The selected student's email does not match the applicant."
            )
        return member
    account = (
        db.query(User)
        .filter(
            func.lower(User.user_email) == row.email.lower(), User.is_active.is_(True)
        )
        .first()
    )
    if not account or not account.is_verified:
        return None
    member = (
        db.query(InstitutionMember)
        .filter_by(institution_id=institution_id, user_id=account.id)
        .first()
    )
    if member:
        if member.status != "active" or member.role != "student":
            raise HTTPException(
                409, "The matching account is not an active institution student."
            )
        return member
    return account


def _pending_invitation(db: Session, institution_id: int, email: str):
    now = _now()
    return (
        db.query(InstitutionInvite)
        .filter(
            InstitutionInvite.institution_id == institution_id,
            func.lower(InstitutionInvite.email) == email.lower(),
            InstitutionInvite.status == "pending",
            InstitutionInvite.expires_at > now,
        )
        .first()
    )


def convert_application(
    db: Session, institution_id: int, application_id: int, user, data
) -> dict:
    institution, _ = _manager_scope(db, institution_id, user, lock=True)
    row = _application(db, institution_id, application_id, lock=True)
    existing_profile = (
        db.query(CampusLearnerProfile).filter_by(application_id=row.id).first()
    )
    if row.stage == "enrolled" and existing_profile:
        return {
            "outcome": "enrolled",
            "application": _application_detail(db, row),
            "learner_profile": _learner_dict(
                db, existing_profile, include_history=True
            ),
            "invitation_id": None,
        }
    if row.invitation_id:
        existing_invitation = db.get(InstitutionInvite, row.invitation_id)
        if (
            existing_invitation
            and existing_invitation.status == "pending"
            and institution_svc.utc(existing_invitation.expires_at) > _now()
            and _matching_student_member(db, institution_id, row, data.member_id)
            is None
        ):
            return {
                "outcome": "invited",
                "application": _application_detail(db, row),
                "learner_profile": None,
                "invitation_id": existing_invitation.id,
            }
    _assert_version(row, data.expected_version)
    if row.stage != "admitted" and row.offer_status != "accepted":
        raise HTTPException(
            409, "Admit the applicant or record an accepted offer first."
        )
    if row.offer_status not in ("none", "accepted"):
        raise HTTPException(
            409, "Only an accepted offer can be converted to enrollment."
        )
    missing = (
        db.query(AdmissionDocument)
        .filter(
            AdmissionDocument.application_id == row.id,
            AdmissionDocument.required.is_(True),
            AdmissionDocument.status.notin_(("verified", "waived")),
        )
        .count()
    )
    if missing:
        raise HTTPException(
            409, "Verify or waive every required document before enrollment."
        )
    intake = _intake(db, institution_id, row.intake_id, lock=True)
    enrolled = (
        db.query(CampusLearnerProfile)
        .filter(
            CampusLearnerProfile.intake_id == intake.id,
            CampusLearnerProfile.status.notin_(("withdrawn", "transferred")),
        )
        .count()
    )
    if enrolled >= intake.capacity:
        raise HTTPException(409, "This intake has reached capacity.")
    resolved = _matching_student_member(db, institution_id, row, data.member_id)
    if resolved is None:
        invitation = _pending_invitation(db, institution_id, row.email)
        if invitation is None:
            result = institution_svc.invite(
                db,
                institution_id,
                user,
                InviteCreate(email=row.email, role="student", department="Admissions"),
                commit=False,
            )
            invitation_id = result["id"]
        else:
            invitation_id = invitation.id
        row.invitation_id = invitation_id
        row.version += 1
        institution_svc.audit(
            db,
            institution_id,
            user,
            "admissions.conversion_invited",
            row.application_number,
        )
        _commit(db)
        return {
            "outcome": "invited",
            "application": _application_detail(db, row),
            "learner_profile": None,
            "invitation_id": invitation_id,
        }
    if isinstance(resolved, User):
        institution_svc.capacity(db, institution, "members")
        program = _program(db, institution_id, row.program_id)
        member = InstitutionMember(
            institution_id=institution_id,
            user_id=resolved.id,
            role="student",
            department=program.department,
            status="active",
        )
        db.add(member)
        db.flush()
        invitation = _pending_invitation(db, institution_id, row.email)
        if invitation:
            invitation.status = "accepted"
    else:
        member = resolved
    existing_member_profile = (
        db.query(CampusLearnerProfile)
        .filter_by(institution_id=institution_id, member_id=member.id)
        .first()
    )
    if existing_member_profile:
        raise HTTPException(
            409, "This student already has a learner lifecycle profile."
        )
    batch_id = data.batch_id or intake.batch_id
    if batch_id:
        institution_svc.batch_scope(db, institution_id, batch_id)
        existing_batch_member = (
            db.query(InstitutionBatchMember)
            .filter_by(batch_id=batch_id, member_id=member.id)
            .first()
        )
        if not existing_batch_member:
            db.add(InstitutionBatchMember(batch_id=batch_id, member_id=member.id))
    joined_on = data.joined_on or date.today()
    admission_number = (data.admission_number or _new_reference("STU")).upper()
    program = _program(db, institution_id, row.program_id)
    profile = CampusLearnerProfile(
        institution_id=institution_id,
        member_id=member.id,
        application_id=row.id,
        program_id=row.program_id,
        intake_id=row.intake_id,
        admission_number=admission_number,
        status="enrolled",
        joined_on=joined_on,
        expected_completion_on=_add_months(joined_on, program.duration_months),
        version=1,
    )
    db.add(profile)
    db.flush()
    db.add(
        CampusLearnerLifecycleHistory(
            learner_profile_id=profile.id,
            from_status=None,
            to_status="enrolled",
            reason="Admission application converted",
            effective_on=joined_on,
            actor_id=user.id,
        )
    )
    old_stage = row.stage
    row.stage = "enrolled"
    row.enrollment_member_id = member.id
    row.invitation_id = None
    row.version += 1
    _record_stage(db, row, user, old_stage, "enrolled", "Converted to learner")
    institution_svc.audit(
        db,
        institution_id,
        user,
        "admissions.application_converted",
        row.application_number,
    )
    _commit(db, "The admission or learner record already exists.")
    return {
        "outcome": "enrolled",
        "application": _application_detail(db, row),
        "learner_profile": _learner_dict(db, profile, include_history=True),
        "invitation_id": None,
    }


def _learner_dict(
    db: Session, profile, *, include_history: bool = False, related=None
) -> dict:
    if related is None:
        related = (
            db.query(InstitutionMember, User, AdmissionProgram, AdmissionIntake)
            .join(User, User.id == InstitutionMember.user_id)
            .join(AdmissionProgram, AdmissionProgram.id == profile.program_id)
            .join(AdmissionIntake, AdmissionIntake.id == profile.intake_id)
            .filter(InstitutionMember.id == profile.member_id)
            .one()
        )
    member, account, program, intake = related
    result = {
        "id": profile.id,
        "member_id": profile.member_id,
        "learner_name": account.display_name or "Student",
        "learner_email": account.user_email,
        "application_id": profile.application_id,
        "program_id": profile.program_id,
        "program_name": program.name,
        "intake_id": profile.intake_id,
        "intake_name": intake.name,
        "admission_number": profile.admission_number,
        "status": profile.status,
        "joined_on": profile.joined_on,
        "expected_completion_on": profile.expected_completion_on,
        "completed_on": profile.completed_on,
        "exit_reason": profile.exit_reason,
        "version": profile.version,
        "history": [],
    }
    if include_history:
        rows = (
            db.query(CampusLearnerLifecycleHistory, User)
            .outerjoin(User, User.id == CampusLearnerLifecycleHistory.actor_id)
            .filter(CampusLearnerLifecycleHistory.learner_profile_id == profile.id)
            .order_by(CampusLearnerLifecycleHistory.id.desc())
            .all()
        )
        result["history"] = [
            {
                "id": history.id,
                "from_status": history.from_status,
                "to_status": history.to_status,
                "reason": history.reason,
                "effective_on": history.effective_on,
                "actor_id": history.actor_id,
                "actor_name": actor.display_name if actor else "Former staff member",
                "created_at": institution_svc.utc(history.created_at),
            }
            for history, actor in rows
        ]
    return result


def list_learners(db: Session, institution_id: int, user) -> list[dict]:
    _manager_scope(db, institution_id, user)
    rows = (
        db.query(
            CampusLearnerProfile,
            InstitutionMember,
            User,
            AdmissionProgram,
            AdmissionIntake,
        )
        .join(
            InstitutionMember,
            InstitutionMember.id == CampusLearnerProfile.member_id,
        )
        .join(User, User.id == InstitutionMember.user_id)
        .join(AdmissionProgram, AdmissionProgram.id == CampusLearnerProfile.program_id)
        .join(AdmissionIntake, AdmissionIntake.id == CampusLearnerProfile.intake_id)
        .filter(CampusLearnerProfile.institution_id == institution_id)
        .order_by(CampusLearnerProfile.id.desc())
        .limit(500)
        .all()
    )
    return [
        _learner_dict(db, profile, related=(member, account, program, intake))
        for profile, member, account, program, intake in rows
    ]


def get_learner(db: Session, institution_id: int, member_id: int, user) -> dict:
    _, actor = institution_svc.scope(db, institution_id, user)
    if actor.role not in institution_svc.MANAGERS and actor.id != member_id:
        raise HTTPException(404, "Learner profile not found.")
    profile = (
        db.query(CampusLearnerProfile)
        .filter_by(institution_id=institution_id, member_id=member_id)
        .first()
    )
    if not profile:
        raise HTTPException(404, "Learner profile not found.")
    return _learner_dict(db, profile, include_history=True)


def transition_learner(
    db: Session, institution_id: int, member_id: int, user, data
) -> dict:
    _manager_scope(db, institution_id, user, lock=True)
    profile = (
        db.query(CampusLearnerProfile)
        .filter_by(institution_id=institution_id, member_id=member_id)
        .with_for_update()
        .first()
    )
    if not profile:
        raise HTTPException(404, "Learner profile not found.")
    if profile.status == data.status:
        return _learner_dict(db, profile, include_history=True)
    _assert_version(profile, data.expected_version)
    if data.status not in LEARNER_TRANSITIONS.get(profile.status, set()):
        raise HTTPException(
            409, f"A learner cannot move from {profile.status} to {data.status}."
        )
    if data.status in ("on_leave", "withdrawn", "transferred") and not data.reason:
        raise HTTPException(422, "Add a reason for this lifecycle change.")
    effective_on = data.effective_on or date.today()
    old = profile.status
    profile.status = data.status
    profile.version += 1
    profile.completed_on = effective_on if data.status == "completed" else None
    profile.exit_reason = (
        data.reason if data.status in ("withdrawn", "transferred") else ""
    )
    db.add(
        CampusLearnerLifecycleHistory(
            learner_profile_id=profile.id,
            from_status=old,
            to_status=data.status,
            reason=data.reason,
            effective_on=effective_on,
            actor_id=user.id,
        )
    )
    institution_svc.audit(
        db,
        institution_id,
        user,
        "admissions.learner_status_changed",
        f"{profile.admission_number}: {data.status}",
    )
    _commit(db)
    return _learner_dict(db, profile, include_history=True)


def _application_detail(db: Session, row: AdmissionApplication) -> dict:
    program = db.get(AdmissionProgram, row.program_id)
    intake = db.get(AdmissionIntake, row.intake_id)
    result = _application_list_item(row, program.name, intake.name)
    documents = (
        db.query(AdmissionDocument)
        .filter_by(application_id=row.id)
        .order_by(AdmissionDocument.required.desc(), AdmissionDocument.id)
        .all()
    )
    result.update(
        {
            "date_of_birth": row.date_of_birth,
            "address": row.address,
            "prior_institution": row.prior_institution,
            "offer_expires_on": row.offer_expires_on,
            "offer_conditions": row.offer_conditions,
            "tuition_amount": row.tuition_amount,
            "offer_currency": row.offer_currency,
            "invitation_id": row.invitation_id,
            "documents": [
                {
                    "id": document.id,
                    "kind": document.kind,
                    "label": document.label,
                    "required": document.required,
                    "status": document.status,
                    "due_on": document.due_on,
                    "rejection_reason": document.rejection_reason,
                    "verified_at": institution_svc.utc(document.verified_at)
                    if document.verified_at
                    else None,
                }
                for document in documents
            ],
        }
    )
    notes = (
        db.query(AdmissionNote, User)
        .outerjoin(User, User.id == AdmissionNote.author_id)
        .filter(AdmissionNote.application_id == row.id)
        .order_by(AdmissionNote.id.desc())
        .all()
    )
    result["notes"] = [
        {
            "id": note.id,
            "body": note.body,
            "author_id": note.author_id,
            "author_name": author.display_name if author else "Former staff member",
            "created_at": institution_svc.utc(note.created_at),
        }
        for note, author in notes
    ]
    tasks = (
        db.query(AdmissionTask, InstitutionMember, User)
        .outerjoin(
            InstitutionMember, InstitutionMember.id == AdmissionTask.assignee_member_id
        )
        .outerjoin(User, User.id == InstitutionMember.user_id)
        .filter(AdmissionTask.application_id == row.id)
        .order_by(AdmissionTask.status, AdmissionTask.due_on, AdmissionTask.id)
        .all()
    )
    result["tasks"] = [
        {
            "id": task.id,
            "title": task.title,
            "due_on": task.due_on,
            "status": task.status,
            "assignee_member_id": task.assignee_member_id,
            "assignee_name": assignee.display_name if assignee else "",
            "completed_at": institution_svc.utc(task.completed_at)
            if task.completed_at
            else None,
            "created_at": institution_svc.utc(task.created_at),
        }
        for task, _, assignee in tasks
    ]
    history = (
        db.query(AdmissionStageHistory, User)
        .outerjoin(User, User.id == AdmissionStageHistory.actor_id)
        .filter(AdmissionStageHistory.application_id == row.id)
        .order_by(AdmissionStageHistory.id.desc())
        .all()
    )
    result["history"] = [
        {
            "id": item.id,
            "from_stage": item.from_stage,
            "to_stage": item.to_stage,
            "reason": item.reason,
            "actor_id": item.actor_id,
            "actor_name": actor.display_name if actor else "Former staff member",
            "created_at": institution_svc.utc(item.created_at),
        }
        for item, actor in history
    ]
    profile = db.query(CampusLearnerProfile).filter_by(application_id=row.id).first()
    result["learner_profile"] = (
        _learner_dict(db, profile, include_history=True) if profile else None
    )
    return result


def get_application(
    db: Session, institution_id: int, application_id: int, user
) -> dict:
    _manager_scope(db, institution_id, user)
    return _application_detail(db, _application(db, institution_id, application_id))


def admissions_summary(db: Session, institution_id: int, user) -> dict:
    _manager_scope(db, institution_id, user)
    base = db.query(AdmissionApplication).filter_by(institution_id=institution_id)
    total = base.count()
    stage_rows = (
        db.query(AdmissionApplication.stage, func.count(AdmissionApplication.id))
        .filter_by(institution_id=institution_id)
        .group_by(AdmissionApplication.stage)
        .order_by(AdmissionApplication.stage)
        .all()
    )
    stage_counts = {stage: count for stage, count in stage_rows}
    offer_rows = (
        db.query(AdmissionApplication.offer_status, func.count(AdmissionApplication.id))
        .filter_by(institution_id=institution_id)
        .group_by(AdmissionApplication.offer_status)
        .order_by(AdmissionApplication.offer_status)
        .all()
    )
    today = date.today()
    week = today + timedelta(days=7)
    task_base = (
        db.query(AdmissionTask)
        .join(
            AdmissionApplication,
            AdmissionApplication.id == AdmissionTask.application_id,
        )
        .filter(
            AdmissionApplication.institution_id == institution_id,
            AdmissionTask.status.in_(("open", "in_progress")),
        )
    )
    rows = (
        db.query(AdmissionIntake, AdmissionProgram)
        .join(AdmissionProgram, AdmissionProgram.id == AdmissionIntake.program_id)
        .filter(
            AdmissionIntake.institution_id == institution_id,
            AdmissionIntake.status.in_(("draft", "open")),
        )
        .order_by(AdmissionIntake.starts_on, AdmissionIntake.id)
        .limit(20)
        .all()
    )
    recent = (
        db.query(AdmissionApplication, AdmissionProgram, AdmissionIntake)
        .join(AdmissionProgram, AdmissionProgram.id == AdmissionApplication.program_id)
        .join(AdmissionIntake, AdmissionIntake.id == AdmissionApplication.intake_id)
        .filter(AdmissionApplication.institution_id == institution_id)
        .order_by(
            AdmissionApplication.updated_at.desc(), AdmissionApplication.id.desc()
        )
        .limit(5)
        .all()
    )
    return {
        "counts": {
            "total": total,
            "active": sum(
                stage_counts.get(stage, 0) for stage in ACTIVE_APPLICATION_STAGES
            ),
            "offered": stage_counts.get("offered", 0),
            "admitted": stage_counts.get("admitted", 0),
            "enrolled": stage_counts.get("enrolled", 0),
            "rejected": stage_counts.get("rejected", 0),
            "withdrawn": stage_counts.get("withdrawn", 0),
        },
        "stage_counts": [
            {"stage": stage, "count": count} for stage, count in stage_rows
        ],
        "offer_counts": [
            {"status": status, "count": count} for status, count in offer_rows
        ],
        "tasks": {
            "open": task_base.count(),
            "overdue": task_base.filter(AdmissionTask.due_on < today).count(),
            "due_soon": task_base.filter(
                AdmissionTask.due_on >= today, AdmissionTask.due_on <= week
            ).count(),
        },
        "intakes": _serialize_intakes(db, rows),
        "recent_applications": [
            _application_list_item(application, program.name, intake.name)
            for application, program, intake in recent
        ],
    }


def build_offer_pdf(
    db: Session, institution_id: int, application_id: int, user
) -> bytes:
    institution, _ = _manager_scope(db, institution_id, user)
    row = _application(db, institution_id, application_id)
    if row.offer_status not in ("issued", "accepted", "declined", "expired", "revoked"):
        raise HTTPException(409, "Issue the offer before downloading its letter.")
    program = _program(db, institution_id, row.program_id)
    intake = _intake(db, institution_id, row.intake_id)
    branding = db.get(CampusBranding, institution_id)

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    orange = colors.HexColor("#F97316")
    pale = colors.HexColor("#FFF1E7")
    ink = colors.HexColor("#512B18")
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=32 * mm,
        bottomMargin=22 * mm,
        title=f"Offer {row.application_number}",
        author=institution.name,
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "AdmissionOfferHeading",
        parent=styles["Title"],
        textColor=ink,
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=26,
    )
    body = ParagraphStyle(
        "AdmissionOfferBody", parent=styles["BodyText"], textColor=ink, leading=16
    )
    title = branding.title if branding else institution.name
    subtitle = branding.subtitle if branding else "Admissions"
    money = "—"
    if row.tuition_amount is not None:
        money = f"{row.offer_currency} {Decimal(row.tuition_amount):,.2f}"
    story = [
        Paragraph(escape(title), heading),
        Paragraph(escape(subtitle), body),
        Spacer(1, 10 * mm),
        Paragraph(f"Dear {escape(row.full_name)},", body),
        Spacer(1, 5 * mm),
        Paragraph(
            "We are pleased to confirm your offer of admission, subject to the conditions below.",
            body,
        ),
        Spacer(1, 6 * mm),
        Table(
            [
                ["Application", row.application_number],
                ["Program", program.name],
                ["Intake", f"{intake.name} · {intake.academic_year}"],
                ["Offer status", row.offer_status.title()],
                [
                    "Respond by",
                    row.offer_expires_on.isoformat()
                    if row.offer_expires_on
                    else "No date set",
                ],
                ["Tuition", money],
            ],
            colWidths=[42 * mm, 115 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), pale),
                    ("TEXTCOLOR", (0, 0), (-1, -1), ink),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FFD0AE")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        ),
        Spacer(1, 7 * mm),
        Paragraph("Conditions", styles["Heading3"]),
        Paragraph(escape(row.offer_conditions or "No additional conditions."), body),
    ]

    def decorate(canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(pale)
        canvas.rect(0, height - 24 * mm, width, 24 * mm, fill=1, stroke=0)
        canvas.setFillColor(orange)
        canvas.rect(0, height - 5 * mm, width, 5 * mm, fill=1, stroke=0)
        canvas.setFillColor(ink)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            22 * mm, 11 * mm, "Generated securely by SashaInfinity Campus"
        )
        canvas.drawRightString(width - 22 * mm, 11 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return stream.getvalue()
