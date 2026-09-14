"""Business rules for institution integrations, privacy and roster exchange."""

from datetime import datetime, timedelta, timezone
import csv
import io
import re
import secrets
import zipfile

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.campus_control_plane import (
    CampusConsentReceipt,
    CampusDomain,
    CampusIntegration,
    CampusPrivacyRequest,
    CampusRetentionPolicy,
)
from app.models.course import Course
from app.models.institution import (
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionCourse,
    InstitutionMember,
)
from app.models.user import User
from app.services import institution_service


INTEGRATION_KINDS = {
    "google_workspace",
    "microsoft_entra",
    "saml",
    "oidc",
    "scim",
    "oneroster",
    "lti_1_3",
    "digilocker_nad",
}
DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


def _now():
    return datetime.now(timezone.utc)


def serialize_domain(row):
    return {
        "id": row.id,
        "hostname": row.hostname,
        "status": row.status,
        "is_primary": row.is_primary,
        "verification": {
            "record_type": "TXT",
            "record_name": f"_sashainfinity.{row.hostname}",
            "record_value": row.verification_token,
        },
        "verified_at": row.verified_at,
    }


def serialize_integration(row):
    return {
        "id": row.id,
        "kind": row.kind,
        "display_name": row.display_name,
        "status": row.status,
        "config": row.config or {},
        "has_secret_reference": bool(row.secret_reference),
        "last_sync_at": row.last_sync_at,
        "last_error": row.last_error,
        "updated_at": row.updated_at,
    }


def serialize_request(row):
    return {
        "id": row.id,
        "requester_user_id": row.requester_user_id,
        "subject_user_id": row.subject_user_id,
        "kind": row.kind,
        "status": row.status,
        "detail": row.detail,
        "resolution_note": row.resolution_note,
        "due_at": row.due_at,
        "resolved_at": row.resolved_at,
        "created_at": row.created_at,
    }


def overview(db, institution_id, user):
    institution_service.scope(db, institution_id, user, institution_service.MANAGERS)
    policy = db.get(CampusRetentionPolicy, institution_id)
    return {
        "domains": [
            serialize_domain(row)
            for row in db.query(CampusDomain)
            .filter_by(institution_id=institution_id)
            .order_by(CampusDomain.created_at.desc())
            .all()
        ],
        "integrations": [
            serialize_integration(row)
            for row in db.query(CampusIntegration)
            .filter_by(institution_id=institution_id)
            .order_by(CampusIntegration.kind)
            .all()
        ],
        "retention": {
            "inactive_account_days": policy.inactive_account_days if policy else 730,
            "learning_record_days": policy.learning_record_days if policy else 2555,
            "financial_record_days": policy.financial_record_days if policy else 2920,
            "application_record_days": policy.application_record_days if policy else 730,
            "legal_hold": policy.legal_hold if policy else False,
        },
        "privacy_requests": [
            serialize_request(row)
            for row in db.query(CampusPrivacyRequest)
            .filter_by(institution_id=institution_id)
            .order_by(CampusPrivacyRequest.created_at.desc())
            .limit(100)
            .all()
        ],
        "standards": [
            {"key": "oneroster", "version": "1.2", "capability": "CSV export"},
            {"key": "lti", "version": "1.3 Advantage", "capability": "Configuration"},
            {"key": "scim", "version": "2.0", "capability": "Configuration"},
        ],
    }


def add_domain(db, institution_id, user, hostname):
    institution_service.scope(
        db, institution_id, user, institution_service.MANAGERS, lock=True
    )
    value = hostname.strip().lower().rstrip(".")
    if value.startswith("www."):
        value = value[4:]
    if not DOMAIN_RE.fullmatch(value) or value.endswith("sashainfinity.com"):
        raise HTTPException(422, "Enter a valid custom hostname you control.")
    row = CampusDomain(
        institution_id=institution_id,
        hostname=value,
        verification_token=f"sasha-verify={secrets.token_urlsafe(32)}",
    )
    db.add(row)
    institution_service.audit(db, institution_id, user, "domain.added", value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That custom domain is already registered.") from None
    db.refresh(row)
    return row


def upsert_integration(db, institution_id, user, data):
    institution_service.scope(
        db, institution_id, user, institution_service.MANAGERS, lock=True
    )
    if data.kind not in INTEGRATION_KINDS:
        raise HTTPException(422, "Unsupported integration type.")
    row = (
        db.query(CampusIntegration)
        .filter_by(institution_id=institution_id, kind=data.kind)
        .first()
    )
    if not row:
        row = CampusIntegration(institution_id=institution_id, kind=data.kind)
        db.add(row)
    row.display_name = data.display_name.strip()
    row.status = data.status
    row.config = data.config
    row.secret_reference = data.secret_reference.strip()
    row.updated_by = user.id
    institution_service.audit(
        db, institution_id, user, "integration.updated", data.kind
    )
    institution_service.save(db)
    db.refresh(row)
    return row


def set_retention(db, institution_id, user, data):
    institution_service.scope(
        db, institution_id, user, institution_service.MANAGERS, lock=True
    )
    row = db.get(CampusRetentionPolicy, institution_id)
    if not row:
        row = CampusRetentionPolicy(institution_id=institution_id, updated_by=user.id)
        db.add(row)
    for field, value in data.model_dump().items():
        setattr(row, field, value)
    row.updated_by = user.id
    institution_service.audit(
        db, institution_id, user, "retention.updated", "Campus retention policy"
    )
    institution_service.save(db)
    return row


def create_privacy_request(db, institution_id, user, data):
    institution_service.scope(db, institution_id, user)
    subject_id = data.subject_user_id or user.id
    if subject_id != user.id:
        # Guardian and delegated requests require an already-approved link. The
        # existing parent API owns that proof; managers can record the request
        # after validating it through the campus workflow.
        _, actor = institution_service.scope(db, institution_id, user)
        if actor.role not in institution_service.MANAGERS:
            raise HTTPException(403, "You can submit a privacy request only for yourself.")
        if not db.query(InstitutionMember).filter_by(
            institution_id=institution_id, user_id=subject_id
        ).first():
            raise HTTPException(404, "Subject account not found in this institution.")
    duplicate = (
        db.query(CampusPrivacyRequest)
        .filter(
            CampusPrivacyRequest.institution_id == institution_id,
            CampusPrivacyRequest.subject_user_id == subject_id,
            CampusPrivacyRequest.kind == data.kind,
            CampusPrivacyRequest.status.in_(["submitted", "verifying", "processing"]),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(409, "A matching privacy request is already open.")
    row = CampusPrivacyRequest(
        institution_id=institution_id,
        requester_user_id=user.id,
        subject_user_id=subject_id,
        kind=data.kind,
        detail=data.detail.strip(),
        due_at=_now() + timedelta(days=30),
    )
    db.add(row)
    institution_service.audit(
        db, institution_id, user, "privacy.requested", data.kind
    )
    institution_service.save(db)
    db.refresh(row)
    return row


def update_privacy_request(db, institution_id, request_id, user, data):
    institution_service.scope(
        db, institution_id, user, institution_service.MANAGERS, lock=True
    )
    row = db.query(CampusPrivacyRequest).filter_by(
        id=request_id, institution_id=institution_id
    ).first()
    if not row:
        raise HTTPException(404, "Privacy request not found.")
    if row.status in {"completed", "rejected", "cancelled"}:
        raise HTTPException(409, "This privacy request is already closed.")
    row.status = data.status
    row.resolution_note = data.resolution_note.strip()
    if data.status in {"completed", "rejected", "cancelled"}:
        row.resolved_at = _now()
    institution_service.audit(
        db, institution_id, user, "privacy.updated", f"#{row.id}: {row.status}"
    )
    institution_service.save(db)
    db.refresh(row)
    return row


def set_consent(db, institution_id, user, data):
    institution_service.scope(db, institution_id, user)
    subject_id = data.subject_user_id or user.id
    if subject_id != user.id:
        _, actor = institution_service.scope(db, institution_id, user)
        if actor.role not in institution_service.MANAGERS:
            raise HTTPException(403, "You can record consent only for yourself.")
        if not db.query(InstitutionMember).filter_by(
            institution_id=institution_id, user_id=subject_id
        ).first():
            raise HTTPException(404, "Subject account not found in this institution.")
    row = db.query(CampusConsentReceipt).filter_by(
        institution_id=institution_id,
        subject_user_id=subject_id,
        purpose=data.purpose,
    ).first()
    if not row:
        row = CampusConsentReceipt(
            institution_id=institution_id,
            subject_user_id=subject_id,
            purpose=data.purpose,
        )
        db.add(row)
    now = _now()
    row.recorded_by_user_id = user.id
    row.notice_version = data.notice_version
    row.status = data.status
    row.evidence = {"method": data.method}
    row.granted_at = now if data.status == "granted" else row.granted_at
    row.revoked_at = now if data.status == "revoked" else None
    institution_service.audit(
        db, institution_id, user, "consent.updated", f"{data.purpose}: {data.status}"
    )
    institution_service.save(db)
    return row


def _csv_bytes(headers, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def oneroster_export(db, institution_id, user):
    institution, _ = institution_service.scope(
        db, institution_id, user, institution_service.STAFF
    )
    stamp = _now().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    members = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(InstitutionMember.institution_id == institution_id)
        .order_by(InstitutionMember.id)
        .all()
    )
    batches = db.query(InstitutionBatch).filter_by(institution_id=institution_id).all()
    memberships = (
        db.query(InstitutionBatchMember, InstitutionMember)
        .join(InstitutionMember, InstitutionMember.id == InstitutionBatchMember.member_id)
        .filter(InstitutionMember.institution_id == institution_id)
        .all()
    )
    courses = (
        db.query(InstitutionCourse, Course)
        .join(Course, Course.id == InstitutionCourse.course_id)
        .filter(InstitutionCourse.institution_id == institution_id)
        .all()
    )
    org_id = f"org-{institution_id}"
    files = {
        "orgs.csv": _csv_bytes(
            ["sourcedId", "status", "dateLastModified", "name", "type", "identifier", "parentSourcedId"],
            [{"sourcedId": org_id, "status": "active", "dateLastModified": stamp, "name": institution.name, "type": "school", "identifier": institution.slug, "parentSourcedId": ""}],
        ),
        "academicSessions.csv": _csv_bytes(
            ["sourcedId", "status", "dateLastModified", "title", "type", "startDate", "endDate", "parentSourcedId", "schoolYear"],
            [{"sourcedId": f"year-{institution_id}-{institution.academic_year}", "status": "active", "dateLastModified": stamp, "title": institution.academic_year, "type": "schoolYear", "startDate": "", "endDate": "", "parentSourcedId": "", "schoolYear": institution.academic_year}],
        ),
        "users.csv": _csv_bytes(
            ["sourcedId", "status", "dateLastModified", "enabledUser", "username", "givenName", "familyName", "identifier", "email", "phone", "roles", "orgs", "grades"],
            [{"sourcedId": f"user-{member.id}", "status": "active" if member.status == "active" else "tobedeleted", "dateLastModified": stamp, "enabledUser": str(member.status == "active").lower(), "username": account.user_login, "givenName": account.display_name, "familyName": "", "identifier": str(account.id), "email": account.user_email, "phone": getattr(account.profile, "phone", "") if account.profile else "", "roles": member.role, "orgs": org_id, "grades": member.department} for member, account in members],
        ),
        "courses.csv": _csv_bytes(
            ["sourcedId", "status", "dateLastModified", "schoolYearSourcedId", "title", "courseCode", "grades", "orgSourcedId", "subjects", "subjectCodes"],
            [{"sourcedId": f"course-{link.id}", "status": "active", "dateLastModified": stamp, "schoolYearSourcedId": f"year-{institution_id}-{institution.academic_year}", "title": course.post_title, "courseCode": str(course.id), "grades": "", "orgSourcedId": org_id, "subjects": "", "subjectCodes": ""} for link, course in courses],
        ),
        "classes.csv": _csv_bytes(
            ["sourcedId", "status", "dateLastModified", "title", "grades", "courseSourcedId", "classCode", "classType", "location", "schoolSourcedId", "termSourcedIds", "subjects", "subjectCodes", "periods"],
            [{"sourcedId": f"class-{batch.id}", "status": "active", "dateLastModified": stamp, "title": batch.name, "grades": batch.department, "courseSourcedId": "", "classCode": str(batch.id), "classType": "scheduled", "location": "", "schoolSourcedId": org_id, "termSourcedIds": f"year-{institution_id}-{institution.academic_year}", "subjects": "", "subjectCodes": "", "periods": ""} for batch in batches],
        ),
        "enrollments.csv": _csv_bytes(
            ["sourcedId", "status", "dateLastModified", "classSourcedId", "schoolSourcedId", "userSourcedId", "role", "primary", "beginDate", "endDate"],
            [{"sourcedId": f"enrollment-{link.id}", "status": "active", "dateLastModified": stamp, "classSourcedId": f"class-{link.batch_id}", "schoolSourcedId": org_id, "userSourcedId": f"user-{member.id}", "role": "student" if member.role == "student" else "teacher", "primary": "false", "beginDate": "", "endDate": ""} for link, member in memberships],
        ),
    }
    manifest = [
        {"propertyName": "manifest.version", "value": "1.0"},
        {"propertyName": "oneroster.version", "value": "1.2"},
        {"propertyName": "file.academicSessions", "value": "bulk"},
        {"propertyName": "file.classes", "value": "bulk"},
        {"propertyName": "file.courses", "value": "bulk"},
        {"propertyName": "file.enrollments", "value": "bulk"},
        {"propertyName": "file.orgs", "value": "bulk"},
        {"propertyName": "file.users", "value": "bulk"},
    ]
    files["manifest.csv"] = _csv_bytes(["propertyName", "value"], manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, body in files.items():
            archive.writestr(filename, body)
    institution_service.audit(
        db, institution_id, user, "oneroster.exported", f"{len(members)} users"
    )
    institution_service.save(db)
    return output.getvalue(), f"{institution.slug}-oneroster-1.2.zip"

