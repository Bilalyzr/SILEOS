"""Membership-scoped institution APIs. No platform-role bypass."""
import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.services import institution_service as svc
from app.schemas.institution import (
    InstitutionCreate,
    InviteCreate,
    MemberUpdate,
    BatchCreate,
    BatchMembers,
    CourseConnect,
    AssignmentCreate,
    PlanRequestCreate,
    PlanRequestReview,
)
from app.models.institution import (
    InstitutionInvite,
    InstitutionBatchMember,
    InstitutionPlanRequest,
    Institution,
)
from app.models.user import User

router = APIRouter()
CurrentUser = Depends(AuthService.get_current_active_user)


@router.get("/platform/plan-requests")
def platform_requests(db: Session = Depends(get_db), user=CurrentUser):
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "Platform administrator access required.")
    return [
        {
            "id": r.id,
            "institution": inst.name,
            "institution_id": inst.id,
            "plan": r.plan,
            "status": r.status,
            "note": r.note,
            "contact_email": owner.user_email,
            "created_at": svc.utc(r.created_at),
        }
        for r, inst, owner in db.query(InstitutionPlanRequest, Institution, User)
        .join(Institution, Institution.id == InstitutionPlanRequest.institution_id)
        .join(User, User.id == InstitutionPlanRequest.requested_by)
        .order_by(InstitutionPlanRequest.id.desc())
        .limit(200)
        .all()
    ]


@router.patch("/platform/plan-requests/{request_id}")
def review_request(
    request_id: int,
    data: PlanRequestReview,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "Platform administrator access required.")
    row = (
        db.query(InstitutionPlanRequest)
        .filter_by(id=request_id)
        .with_for_update()
        .first()
    )
    if not row:
        raise HTTPException(404, "Request not found.")
    if row.status != "pending":
        raise HTTPException(409, "This request has already been reviewed.")
    row.status = data.status
    svc.audit(
        db,
        row.institution_id,
        user,
        "plan.request_reviewed",
        f"{data.status}: {data.note}",
    )
    svc.save(db)
    return {"status": row.status}


@router.get("")
def mine(db: Session = Depends(get_db), user=CurrentUser):
    return svc.list_mine(db, user)


@router.post("", status_code=201)
def create(data: InstitutionCreate, db: Session = Depends(get_db), user=CurrentUser):
    return svc.create(db, user, data)


@router.get("/invitations")
def invitations(db: Session = Depends(get_db), user=CurrentUser):
    return svc.pending_invites(db, user)


@router.post("/invitations/{invite_id}/accept")
def accept(invite_id: int, db: Session = Depends(get_db), user=CurrentUser):
    return svc.accept_invite(db, invite_id, user)


@router.get("/{institution_id}")
def overview(institution_id: int, db: Session = Depends(get_db), user=CurrentUser):
    return svc.overview(db, institution_id, user)


@router.patch("/{institution_id}")
def update(
    institution_id: int,
    data: InstitutionCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    inst, member = svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    for key, value in data.model_dump().items():
        setattr(inst, key, value)
    svc.audit(db, institution_id, user, "institution.updated", inst.name)
    svc.save(db)
    return svc.serialize(inst, member.role)


@router.post("/{institution_id}/invitations", status_code=201)
def invite(
    institution_id: int,
    data: InviteCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return svc.invite(db, institution_id, user, data)


@router.delete("/{institution_id}/invitations/{invite_id}")
def revoke_invite(
    institution_id: int, invite_id: int, db: Session = Depends(get_db), user=CurrentUser
):
    _, actor = svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    row = (
        db.query(InstitutionInvite)
        .filter_by(id=invite_id, institution_id=institution_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Invitation not found.")
    if row.role == "admin" and actor.role != "owner":
        raise HTTPException(
            403, "Only the owner can revoke an administrator invitation."
        )
    if row.status != "pending":
        raise HTTPException(409, "This invitation is no longer pending.")
    row.status = "revoked"
    svc.audit(db, institution_id, user, "invitation.revoked", row.email)
    svc.save(db)
    return {"status": "revoked"}


@router.patch("/{institution_id}/members/{member_id}")
def member_update(
    institution_id: int,
    member_id: int,
    data: MemberUpdate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    svc.update_member(db, institution_id, member_id, user, data)
    return {"status": "updated"}


@router.post("/{institution_id}/batches", status_code=201)
def batch_create(
    institution_id: int,
    data: BatchCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return svc.create_batch(db, institution_id, user, data)


@router.post("/{institution_id}/batches/{batch_id}/members")
def batch_members(
    institution_id: int,
    batch_id: int,
    data: BatchMembers,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    svc.add_batch_members(db, institution_id, batch_id, user, data.member_ids)
    return {"status": "updated"}


@router.delete("/{institution_id}/batches/{batch_id}/members/{member_id}")
def remove_batch_member(
    institution_id: int,
    batch_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    svc.scope(db, institution_id, user, svc.MANAGERS, lock=True)
    batch = svc.batch_scope(db, institution_id, batch_id)
    row = (
        db.query(InstitutionBatchMember)
        .filter_by(batch_id=batch_id, member_id=member_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Batch member not found.")
    db.delete(row)
    svc.audit(
        db,
        institution_id,
        user,
        "batch.member_removed",
        f"{batch.name}: member #{member_id}",
    )
    svc.save(db)
    return {"status": "removed"}


@router.get("/{institution_id}/available-courses")
def available(institution_id: int, db: Session = Depends(get_db), user=CurrentUser):
    return svc.available_courses(db, institution_id, user)


@router.post("/{institution_id}/courses", status_code=201)
def connect(
    institution_id: int,
    data: CourseConnect,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    svc.connect_course(db, institution_id, user, data.course_id)
    return {"status": "connected"}


@router.post("/{institution_id}/batches/{batch_id}/assignments")
def assign(
    institution_id: int,
    batch_id: int,
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    svc.assign_course(db, institution_id, batch_id, user, data)
    return {"status": "assigned"}


@router.get("/{institution_id}/report.csv")
def export_report(institution_id: int, db: Session = Depends(get_db), user=CurrentUser):
    svc.scope(db, institution_id, user, svc.STAFF)
    rows = svc.report_rows(db, institution_id, user)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        ["Batch", "Student", "Course", "Progress (%)", "Enrollment", "Due date"]
    )

    def safe(value):
        value = str(value or "")
        return (
            "'" + value
            if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
            else value
        )

    for row in rows:
        writer.writerow(
            [
                safe(row["batch"]),
                safe(row["student"]),
                safe(row["course"]),
                row["progress"],
                "Enrolled" if row["has_access"] else "Enrollment needed",
                row["due_date"] or "",
            ]
        )
    return Response(
        "\ufeff" + output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="institution-{institution_id}-progress.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{institution_id}/plan-requests", status_code=201)
def request_plan(
    institution_id: int,
    data: PlanRequestCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    svc.request_plan(db, institution_id, user, data)
    return {
        "status": "pending",
        "detail": "Request saved for review. Your current plan has not changed.",
    }
