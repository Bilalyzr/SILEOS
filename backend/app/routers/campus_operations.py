"""Academic operations scoped to active institution membership on every request."""
import csv
import io
from datetime import date
from pathlib import Path
from urllib.parse import quote
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from fastapi.responses import Response
from pydantic import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session, defer
from app.core.database import get_db
from app.models.user import User
from app.models.institution import (
    InstitutionMember,
    InstitutionInvite,
    InstitutionBatch,
    InstitutionBatchMember,
)
from app.models.campus_operations import (
    CampusTerm,
    CampusAttendance,
    CampusAssessment,
    CampusScore,
    CampusResource,
    CampusBranding,
    CampusMailJob,
)
from app.schemas.campus_operations import (
    BulkInvite,
    TermCreate,
    AttendanceSave,
    AssessmentCreate,
    AssessmentEdit,
    ScoresSave,
    BrandingSave,
)
from app.schemas.institution import InviteCreate
from app.services.auth_service import AuthService
from app.services import institution_service as svc

router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


def batch_scope(db, institution_id, batch_id, user, write=False):
    inst, actor = svc.scope(
        db, institution_id, user, svc.STAFF if write else None, lock=write
    )
    batch = (
        db.query(InstitutionBatch)
        .filter_by(id=batch_id, institution_id=institution_id)
        .first()
    )
    if not batch:
        raise HTTPException(404, "Batch not found.")
    if (
        actor.role not in svc.STAFF
        and not db.query(InstitutionBatchMember)
        .filter_by(batch_id=batch_id, member_id=actor.id)
        .first()
    ):
        raise HTTPException(404, "Batch not found.")
    return inst, actor, batch


def batch_students(db, batch_id):
    return (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .join(
            InstitutionBatchMember,
            InstitutionBatchMember.member_id == InstitutionMember.id,
        )
        .filter(
            InstitutionBatchMember.batch_id == batch_id,
            InstitutionMember.status == "active",
            InstitutionMember.role == "student",
        )
        .all()
    )


@router.post("/{institution_id}/people/import")
def bulk_invites(
    institution_id: int, data: BulkInvite, db: Session = Depends(get_db), user=Current
):
    inst, actor = svc.scope(db, institution_id, user, svc.MANAGERS, lock=data.commit)
    svc.verified(user)
    reader = csv.DictReader(io.StringIO(data.csv.lstrip("\ufeff")))
    if (
        not reader.fieldnames
        or set(reader.fieldnames) - {"email", "role", "department"}
        or "email" not in reader.fieldnames
    ):
        raise HTTPException(422, "Use CSV headers email,role,department.")
    result = []
    valid = []
    seen = set()
    for n, row in enumerate(reader, 2):
        if n > 501:
            raise HTTPException(422, "Import up to 500 rows at a time.")
        try:
            item = InviteCreate(
                email=row.get("email") or "",
                role=row.get("role") or "student",
                department=row.get("department") or "",
            )
            email = str(item.email).lower()
            if email in seen:
                raise ValueError("Duplicate email in this file.")
            seen.add(email)
            if item.role == "admin" and actor.role != "owner":
                raise ValueError("Only owners can invite administrators.")
            existing = (
                db.query(InstitutionMember)
                .join(User, User.id == InstitutionMember.user_id)
                .filter(
                    InstitutionMember.institution_id == institution_id,
                    svc.func.lower(User.user_email) == email,
                )
                .first()
            )
            invitation = (
                db.query(InstitutionInvite)
                .filter_by(institution_id=institution_id, email=email, status="pending")
                .first()
            )
            if existing or (
                invitation
                and svc.utc(invitation.expires_at) > svc.datetime.now(svc.timezone.utc)
            ):
                result.append(
                    {
                        "row": n,
                        "email": email,
                        "status": "skipped",
                        "message": "Already a member or already invited.",
                    }
                )
                continue
            valid.append(item)
            result.append(
                {
                    "row": n,
                    "email": email,
                    "status": "ready",
                    "message": "Invitation will be created.",
                }
            )
        except (ValidationError, ValueError):
            result.append(
                {
                    "row": n,
                    "email": str(row.get("email") or "")[:254],
                    "status": "error",
                    "message": "Invalid email, role, department or duplicate row.",
                }
            )
    errors = sum(r["status"] == "error" for r in result)
    usage = svc.usage(db, inst)
    remaining = max(
        0, usage["limits"]["members"] - usage["members"] - usage["reserved_seats"]
    )
    if len(valid) > remaining:
        errors += 1
    if data.commit and errors:
        raise HTTPException(
            422, "Fix invalid rows and check available seats before importing."
        )
    if data.commit:
        try:
            for item in valid:
                svc.invite(db, institution_id, user, item, commit=False)
            svc.audit(
                db,
                institution_id,
                user,
                "members.imported",
                f"{len(valid)} invitations created",
            )
            svc.save(db)
        except Exception:
            db.rollback()
            raise
    if data.commit:
        for item in result:
            if item["status"] == "ready":
                item["status"] = "created"
                item["message"] = "Invitation created."
    return {
        "rows": result,
        "ready": len(valid),
        "errors": errors,
        "available_seats": remaining,
        "created": len(valid) if data.commit else 0,
        "committed": data.commit,
    }


@router.post("/{institution_id}/invitations/{invite_id}/send-email", status_code=202)
def send_invitation(
    institution_id: int,
    invite_id: int,
    tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    svc.verified(user)
    row = (
        db.query(InstitutionInvite)
        .filter_by(id=invite_id, institution_id=institution_id, status="pending")
        .first()
    )
    if not row or svc.utc(row.expires_at) <= svc.datetime.now(svc.timezone.utc):
        raise HTTPException(404, "Active invitation not found.")
    if row.role == "admin" and actor.role != "owner":
        raise HTTPException(403, "Only owners can send administrator invitations.")
    from app.services.campus_mail import mail_configured, deliver

    if not mail_configured():
        raise HTTPException(
            503,
            "Email delivery is not configured. The account inbox invitation remains available.",
        )
    job = db.query(CampusMailJob).filter_by(invite_id=invite_id).first()
    if job and job.status in ("queued", "sending", "sent"):
        return {"status": job.status}
    if job:
        if job.attempts >= 5:
            raise HTTPException(
                409, "Delivery retry limit reached. Check the mail service."
            )
        job.status = "queued"
    else:
        job = CampusMailJob(invite_id=invite_id)
        db.add(job)
    svc.audit(db, institution_id, user, "invitation.email_queued", row.email)
    svc.save(db)
    tasks.add_task(deliver, job.id)
    return {"status": "queued"}


@router.get("/{institution_id}/academics")
def academics(
    institution_id: int,
    batch_id: int | None = None,
    day: date | None = None,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = svc.scope(db, institution_id, user)
    terms = (
        db.query(CampusTerm)
        .filter_by(institution_id=institution_id)
        .order_by(CampusTerm.starts_on.desc())
        .all()
    )
    output = {
        "terms": [
            {"id": t.id, "name": t.name, "starts_on": t.starts_on, "ends_on": t.ends_on}
            for t in terms
        ],
        "students": [],
        "attendance": [],
        "assessments": [],
    }
    if not batch_id:
        return output
    batch_scope(db, institution_id, batch_id, user)
    students = batch_students(db, batch_id)
    if actor.role not in svc.STAFF:
        students = [(m, u) for m, u in students if m.id == actor.id]
    ids = [m.id for m, u in students]
    output["students"] = [
        {"id": m.id, "name": u.display_name or u.user_email, "email": u.user_email}
        for m, u in students
    ]
    output["attendance"] = [
        {"member_id": a.member_id, "status": a.status, "day": a.day}
        for a in db.query(CampusAttendance).filter(
            CampusAttendance.batch_id == batch_id,
            CampusAttendance.day == (day or date.today()),
            CampusAttendance.member_id.in_(ids),
        )
    ]
    assessments = (
        db.query(CampusAssessment)
        .filter_by(batch_id=batch_id)
        .order_by(CampusAssessment.id.desc())
        .limit(100)
        .all()
    )
    for a in assessments:
        output["assessments"].append(
            {
                "id": a.id,
                "title": a.title,
                "term_id": a.term_id,
                "max_score": a.max_score,
                "due_on": a.due_on,
                "scores": [
                    {"member_id": s.member_id, "score": s.score, "feedback": s.feedback}
                    for s in db.query(CampusScore).filter(
                        CampusScore.assessment_id == a.id,
                        CampusScore.member_id.in_(ids),
                    )
                ],
            }
        )
    return output


@router.post("/{institution_id}/terms", status_code=201)
def term(
    institution_id: int, data: TermCreate, db: Session = Depends(get_db), user=Current
):
    svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    if db.query(CampusTerm).filter_by(institution_id=institution_id).count() >= 100:
        raise HTTPException(409, "Term limit reached.")
    row = CampusTerm(institution_id=institution_id, **data.model_dump())
    db.add(row)
    svc.audit(db, institution_id, user, "term.created", data.name)
    svc.save(db)
    return {"id": row.id}


@router.put("/{institution_id}/attendance")
def attendance(
    institution_id: int,
    data: AttendanceSave,
    db: Session = Depends(get_db),
    user=Current,
):
    _, _, batch = batch_scope(db, institution_id, data.batch_id, user, write=True)
    if data.day > date.today():
        raise HTTPException(422, "Attendance cannot be recorded in the future.")
    ids = {m.id for m, u in batch_students(db, batch.id)}
    supplied = [e.member_id for e in data.entries]
    if len(set(supplied)) != len(supplied) or not set(supplied) <= ids:
        raise HTTPException(
            422, "Choose active students in this batch only, once each."
        )
    for e in data.entries:
        row = (
            db.query(CampusAttendance)
            .filter_by(batch_id=batch.id, member_id=e.member_id, day=data.day)
            .first()
        )
        if not row:
            row = CampusAttendance(
                batch_id=batch.id, member_id=e.member_id, day=data.day
            )
            db.add(row)
        row.status = e.status
        row.recorded_by = user.id
    svc.audit(
        db, institution_id, user, "attendance.saved", f"{batch.name} · {data.day}"
    )
    svc.save(db)
    return {"saved": len(data.entries)}


@router.post("/{institution_id}/assessments", status_code=201)
def assessment(
    institution_id: int,
    data: AssessmentCreate,
    db: Session = Depends(get_db),
    user=Current,
):
    batch_scope(db, institution_id, data.batch_id, user, write=True)
    if (
        data.term_id
        and not db.query(CampusTerm)
        .filter_by(id=data.term_id, institution_id=institution_id)
        .first()
    ):
        raise HTTPException(404, "Term not found.")
    if db.query(CampusAssessment).filter_by(batch_id=data.batch_id).count() >= 100:
        raise HTTPException(409, "Assessment limit reached for this batch.")
    row = CampusAssessment(**data.model_dump(), created_by=user.id)
    db.add(row)
    svc.audit(db, institution_id, user, "assessment.created", data.title)
    svc.save(db)
    return {"id": row.id}


@router.put("/{institution_id}/assessments/{assessment_id}/scores")
def scores(
    institution_id: int,
    assessment_id: int,
    data: ScoresSave,
    db: Session = Depends(get_db),
    user=Current,
):
    svc.scope(db, institution_id, user, svc.STAFF, lock=True)
    a = (
        db.query(CampusAssessment)
        .join(InstitutionBatch, InstitutionBatch.id == CampusAssessment.batch_id)
        .filter(
            CampusAssessment.id == assessment_id,
            InstitutionBatch.institution_id == institution_id,
        )
        .first()
    )
    if not a:
        raise HTTPException(404, "Assessment not found.")
    ids = {m.id for m, u in batch_students(db, a.batch_id)}
    supplied = [e.member_id for e in data.entries]
    if (
        len(set(supplied)) != len(supplied)
        or not set(supplied) <= ids
        or any(e.score > a.max_score for e in data.entries)
    ):
        raise HTTPException(422, "Check batch membership and maximum scores.")
    for e in data.entries:
        row = (
            db.query(CampusScore)
            .filter_by(assessment_id=a.id, member_id=e.member_id)
            .first()
        )
        if not row:
            row = CampusScore(assessment_id=a.id, member_id=e.member_id)
            db.add(row)
        row.score = e.score
        row.feedback = e.feedback
        row.graded_by = user.id
    svc.audit(db, institution_id, user, "scores.saved", a.title)
    svc.save(db)
    return {"saved": len(data.entries)}


def _scoped_assessment(db, institution_id, assessment_id, user):
    """Assessment within this institution, with staff write scope applied."""
    svc.scope(db, institution_id, user, svc.STAFF, lock=True)
    a = (
        db.query(CampusAssessment)
        .join(InstitutionBatch, InstitutionBatch.id == CampusAssessment.batch_id)
        .filter(
            CampusAssessment.id == assessment_id,
            InstitutionBatch.institution_id == institution_id,
        )
        .first()
    )
    if not a:
        raise HTTPException(404, "Assessment not found.")
    return a


@router.put("/{institution_id}/assessments/{assessment_id}")
def edit_assessment(
    institution_id: int,
    assessment_id: int,
    data: AssessmentEdit,
    db: Session = Depends(get_db),
    user=Current,
):
    """Edit an assessment's title/max score/due date/term. Assessments used
    to be create-only; the only "edit" was overwriting scores."""
    a = _scoped_assessment(db, institution_id, assessment_id, user)
    if (
        data.term_id is not None
        and not db.query(CampusTerm)
        .filter_by(id=data.term_id, institution_id=institution_id)
        .first()
    ):
        raise HTTPException(404, "Term not found.")
    before = a.title
    if data.title is not None:
        a.title = data.title
    if data.max_score is not None:
        if db.query(CampusScore).filter(
            CampusScore.assessment_id == a.id, CampusScore.score > data.max_score
        ).first():
            raise HTTPException(
                422, "A recorded score exceeds the new maximum. Adjust scores first."
            )
        a.max_score = data.max_score
    if data.due_on is not None:
        a.due_on = data.due_on
    if data.term_id is not None:
        a.term_id = data.term_id
    svc.audit(db, institution_id, user, "assessment.edited", f"{before} → {a.title}")
    svc.save(db)
    return {"id": a.id}


@router.delete("/{institution_id}/assessments/{assessment_id}")
def delete_assessment(
    institution_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    user=Current,
):
    """Delete an assessment with its scores. Score rows are removed first —
    the FK has no ondelete cascade and orphaned scores would linger."""
    a = _scoped_assessment(db, institution_id, assessment_id, user)
    db.query(CampusScore).filter(CampusScore.assessment_id == a.id).delete()
    title = a.title
    db.delete(a)
    svc.audit(db, institution_id, user, "assessment.deleted", title)
    svc.save(db)
    return {"deleted": assessment_id}


def resource_scope(db, institution_id, user):
    _, actor = svc.scope(db, institution_id, user)
    q = db.query(CampusResource).filter_by(institution_id=institution_id)
    if actor.role not in svc.STAFF:
        batches = [
            b
            for b, in db.query(InstitutionBatchMember.batch_id).filter_by(
                member_id=actor.id
            )
        ]
        q = q.filter(
            (CampusResource.batch_id.is_(None)) | CampusResource.batch_id.in_(batches)
        )
    return q


@router.get("/{institution_id}/resources")
def resources(institution_id: int, db: Session = Depends(get_db), user=Current):
    return [
        {
            "id": r.id,
            "title": r.title,
            "filename": r.filename,
            "batch_id": r.batch_id,
            "created_at": svc.utc(r.created_at),
        }
        for r in resource_scope(db, institution_id, user)
        .options(defer(CampusResource.content))
        .order_by(CampusResource.id.desc())
        .limit(100)
    ]


@router.post("/{institution_id}/resources", status_code=201)
async def upload_resource(
    institution_id: int,
    title: str = Form(..., min_length=2, max_length=160),
    batch_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Current,
):
    svc.scope(db, institution_id, user, svc.STAFF, lock=True)
    if batch_id:
        batch_scope(db, institution_id, batch_id, user, write=True)
    if db.query(CampusResource).filter_by(institution_id=institution_id).count() >= 100:
        raise HTTPException(409, "The workspace supports up to 100 resources.")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024 or not content:
        raise HTTPException(422, "Choose a non-empty file under 5 MB.")
    ext = Path(file.filename or "").suffix.lower()
    types = {".pdf": "application/pdf", ".txt": "text/plain", ".csv": "text/csv"}
    if ext not in types or (ext == ".pdf" and not content.startswith(b"%PDF-")):
        raise HTTPException(422, "Choose a PDF, plain-text or CSV resource.")
    if ext != ".pdf":
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(422, "Text resources must use UTF-8.") from None
    filename = "resource" + ext
    row = CampusResource(
        institution_id=institution_id,
        batch_id=batch_id,
        title=title,
        filename=filename,
        mime_type=types[ext],
        content=content,
        uploaded_by=user.id,
    )
    db.add(row)
    svc.audit(db, institution_id, user, "resource.uploaded", title)
    svc.save(db)
    return {"id": row.id}


@router.get("/{institution_id}/resources/{resource_id}/download")
def download_resource(
    institution_id: int, resource_id: int, db: Session = Depends(get_db), user=Current
):
    r = (
        resource_scope(db, institution_id, user)
        .filter(CampusResource.id == resource_id)
        .first()
    )
    if not r:
        raise HTTPException(404, "Resource not found.")
    return Response(
        r.content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(r.filename)}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{institution_id}/resources/{resource_id}")
def remove_resource(
    institution_id: int, resource_id: int, db: Session = Depends(get_db), user=Current
):
    svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    row = (
        db.query(CampusResource)
        .filter_by(id=resource_id, institution_id=institution_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Resource not found.")
    from app.models.campus_operations import CampusLesson

    if db.query(CampusLesson).filter_by(resource_id=resource_id).first():
        raise HTTPException(
            409, "Remove this resource from its course lessons before deleting it."
        )
    svc.audit(db, institution_id, user, "resource.removed", row.title)
    db.delete(row)
    svc.save(db)
    return {"deleted": True}


@router.get("/{institution_id}/branding")
def branding(institution_id: int, db: Session = Depends(get_db), user=Current):
    svc.scope(db, institution_id, user)
    row = db.get(CampusBranding, institution_id)
    return {
        "title": row.title if row else "Your campus. Every possibility.",
        "subtitle": row.subtitle if row else "Learn, connect and grow together.",
        "has_image": bool(row and row.image),
    }


@router.put("/{institution_id}/branding")
def save_branding(
    institution_id: int, data: BrandingSave, db: Session = Depends(get_db), user=Current
):
    svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    row = db.get(CampusBranding, institution_id)
    if not row:
        row = CampusBranding(institution_id=institution_id)
        db.add(row)
    row.title = data.title
    row.subtitle = data.subtitle
    svc.audit(db, institution_id, user, "branding.updated", data.title)
    svc.save(db)
    return {"saved": True}


@router.put("/{institution_id}/branding/image")
async def banner_image(
    institution_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Current,
):
    svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(422, "Choose an image under 5 MB.")
    try:
        image = Image.open(io.BytesIO(content))
        if (
            image.format not in ("PNG", "JPEG", "WEBP")
            or image.width * image.height > 20_000_000
        ):
            raise ValueError()
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1600, 900))
        out = io.BytesIO()
        image.save(out, format="PNG")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(
            422, "Choose a valid PNG, JPEG or WebP under 20 megapixels."
        ) from None
    row = db.get(CampusBranding, institution_id)
    if not row:
        row = CampusBranding(institution_id=institution_id)
        db.add(row)
    row.image = out.getvalue()
    svc.audit(db, institution_id, user, "branding.image_updated", "Campus banner")
    svc.save(db)
    return {"saved": True}


@router.get("/{institution_id}/branding/image")
def get_banner_image(institution_id: int, db: Session = Depends(get_db), user=Current):
    svc.scope(db, institution_id, user)
    row = db.get(CampusBranding, institution_id)
    if not row or not row.image:
        raise HTTPException(404, "No banner image.")
    return Response(
        row.image,
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{institution_id}/branding/image")
def delete_banner_image(
    institution_id: int, db: Session = Depends(get_db), user=Current
):
    svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    row = db.get(CampusBranding, institution_id)
    if row:
        row.image = None
    svc.audit(db, institution_id, user, "branding.image_removed", "Campus banner")
    svc.save(db)
    return {"deleted": True}
