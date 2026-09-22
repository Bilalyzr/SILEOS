"""Scoped school administration; assignments never bypass LMS purchase/access rules."""
from datetime import datetime, timedelta, timezone
import re
import secrets
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.models.institution import (
    Institution,
    InstitutionMember,
    InstitutionInvite,
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionCourse,
    InstitutionAssignment,
    InstitutionAudit,
    InstitutionPlanRequest,
)
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.services.course_access import can_edit, collaborated_course_ids

MANAGERS = ("owner", "admin")
STAFF = ("owner", "admin", "teacher")
# Pilot limits are enforced under the institution row lock. Paid activation is a separate workflow.
LIMITS = {
    "starter": {"members": 100, "batches": 10, "courses": 20},
    "campus": {"members": 1000, "batches": 100, "courses": 200},
    "enterprise": {"members": 10000, "batches": 1000, "courses": 2000},
}

# Platform administrators (admin/superadmin) operate on EVERY institution —
# without this they see zero campuses (list_mine is membership-scoped) and
# every campus tool 404s for them, which is how "Bring your campus together",
# fee-plan assignment and the trust/integrations tab all broke for QA.
PLATFORM_ADMIN_ROLES = ("admin", "superadmin")


class _PlatformAdminMember:
    """Stand-in InstitutionMember for a platform admin without membership.

    Grants manager-level ("admin") powers. Owner-only gates (e.g. inviting
    administrators) still apply — a platform admin is not the campus owner.
    """

    id = None
    role = "admin"
    status = "active"

    def __init__(self, institution_id, user_id):
        self.institution_id = institution_id
        self.user_id = user_id


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def verified(user):
    if not user.is_verified:
        raise HTTPException(
            403, "Verify your email before managing institution access."
        )


def scope(db, institution_id, user, roles=None, lock=False):
    member = (
        db.query(InstitutionMember)
        .filter_by(institution_id=institution_id, user_id=user.id, status="active")
        .first()
    )
    if not member and getattr(user, "role", None) in PLATFORM_ADMIN_ROLES:
        member = _PlatformAdminMember(institution_id, user.id)
    if not member:
        raise HTTPException(404, "Institution not found.")
    q = db.query(Institution).filter_by(id=institution_id)
    institution = q.with_for_update().one() if lock else q.one()
    if lock and member.id is not None:
        # An access change may have committed while this command waited for the
        # institution lock. Re-read membership before authorizing the mutation.
        # (Skipped for the platform-admin stand-in, which is not a DB row.)
        db.refresh(member)
        if member.status != "active":
            raise HTTPException(404, "Institution not found.")
    if roles and member.role not in roles:
        raise HTTPException(403, "Your institution role cannot perform this action.")
    from app.services.campus_billing import effective_plan

    institution.plan = effective_plan(db, institution_id)
    return institution, member


def audit(db, institution_id, user, action, detail):
    db.add(
        InstitutionAudit(
            institution_id=institution_id,
            actor_id=user.id,
            action=action,
            detail=detail[:250],
        )
    )


def save(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "This record already exists. Refresh and try again."
        ) from None


def usage(db, inst):
    from app.models.campus_operations import CampusLearningCourse

    now = datetime.now(timezone.utc)
    members = (
        db.query(InstitutionMember)
        .filter_by(institution_id=inst.id, status="active")
        .count()
    )
    invites = (
        db.query(InstitutionInvite)
        .filter(
            InstitutionInvite.institution_id == inst.id,
            InstitutionInvite.status == "pending",
            InstitutionInvite.expires_at > now,
        )
        .count()
    )
    return {
        "members": members,
        "reserved_seats": invites,
        "batches": db.query(InstitutionBatch).filter_by(institution_id=inst.id).count(),
        "courses": db.query(InstitutionCourse).filter_by(institution_id=inst.id).count()
        + db.query(CampusLearningCourse).filter_by(institution_id=inst.id).count(),
        "limits": LIMITS.get(inst.plan, LIMITS["starter"]),
    }


def capacity(db, inst, resource):
    u = usage(db, inst)
    total = u[resource] + (u["reserved_seats"] if resource == "members" else 0)
    if total >= u["limits"][resource]:
        raise HTTPException(409, f"The current plan's {resource} limit is reached.")


def serialize(inst, role):
    return {
        "id": inst.id,
        "name": inst.name,
        "slug": inst.slug,
        "kind": inst.kind,
        "academic_year": inst.academic_year,
        "timezone": inst.timezone,
        "description": inst.description,
        "plan": inst.plan,
        "role": role,
    }


def create(db, user, data):
    verified(user)
    # Lock the account to serialize workspace creation for one owner.
    db.query(User).filter_by(id=user.id).with_for_update().one()
    if (
        db.query(InstitutionMember).filter_by(user_id=user.id, role="owner").count()
        >= 5
    ):
        raise HTTPException(409, "An account can own up to five institutions.")
    slug = re.sub(r"[^a-z0-9]+", "-", data.name.lower()).strip("-")[:70] or "campus"
    inst = Institution(
        **data.model_dump(), slug=f"{slug}-{secrets.token_hex(4)}", plan="starter"
    )
    db.add(inst)
    db.flush()
    db.add(
        InstitutionMember(
            institution_id=inst.id,
            user_id=user.id,
            role="owner",
            status="active",
            department="",
        )
    )
    audit(db, inst.id, user, "institution.created", inst.name)
    save(db)
    return serialize(inst, "owner")


def list_mine(db, user):
    # Platform admins see every campus (they manage/support all of them);
    # everyone else sees only their active memberships.
    if getattr(user, "role", None) in PLATFORM_ADMIN_ROLES:
        return [
            serialize(i, "admin")
            for i in db.query(Institution).order_by(Institution.name).all()
        ]
    return [
        serialize(i, m.role)
        for i, m in db.query(Institution, InstitutionMember)
        .join(InstitutionMember, InstitutionMember.institution_id == Institution.id)
        .filter(
            InstitutionMember.user_id == user.id, InstitutionMember.status == "active"
        )
        .order_by(Institution.name)
        .all()
    ]


def invite(db, institution_id, user, data, commit=True):
    verified(user)
    inst, member = scope(db, institution_id, user, MANAGERS, lock=True)
    if data.role == "admin" and member.role != "owner":
        raise HTTPException(
            403, "Only the institution owner can invite an administrator."
        )
    email = str(data.email).lower()
    existing_member = (
        db.query(InstitutionMember)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(
            InstitutionMember.institution_id == institution_id,
            func.lower(User.user_email) == email,
        )
        .first()
    )
    if existing_member:
        raise HTTPException(
            409, "This account is already a member. Manage its access in People."
        )
    row = (
        db.query(InstitutionInvite)
        .filter_by(institution_id=institution_id, email=email)
        .first()
    )
    if (
        row
        and row.status == "pending"
        and utc(row.expires_at) > datetime.now(timezone.utc)
    ):
        raise HTTPException(409, "An active invitation already exists for this email.")
    capacity(db, inst, "members")
    if not row:
        row = InstitutionInvite(institution_id=institution_id, email=email)
        db.add(row)
    row.role, row.department, row.status = data.role, data.department, "pending"
    row.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    audit(db, institution_id, user, "member.invited", f"{email} · {data.role}")
    if commit:
        save(db)
    else:
        db.flush()
    return {"id": row.id, "status": "pending", "delivery": "account_inbox"}


def pending_invites(db, user):
    verified(user)
    return [
        {
            "id": r.id,
            "institution_name": i.name,
            "role": r.role,
            "expires_at": utc(r.expires_at),
        }
        for r, i in db.query(InstitutionInvite, Institution)
        .join(Institution, Institution.id == InstitutionInvite.institution_id)
        .filter(
            func.lower(InstitutionInvite.email) == user.user_email.lower(),
            InstitutionInvite.status == "pending",
            InstitutionInvite.expires_at > datetime.now(timezone.utc),
        )
        .all()
    ]


def accept_invite(db, invite_id, user):
    verified(user)
    invite = db.query(InstitutionInvite).filter_by(id=invite_id).first()
    if not invite or invite.email != user.user_email.lower():
        raise HTTPException(404, "Invitation not found.")
    inst = (
        db.query(Institution)
        .filter_by(id=invite.institution_id)
        .with_for_update()
        .one()
    )
    db.refresh(invite)
    if invite.status != "pending" or utc(invite.expires_at) <= datetime.now(
        timezone.utc
    ):
        raise HTTPException(409, "This invitation is no longer active.")
    existing = (
        db.query(InstitutionMember)
        .filter_by(institution_id=inst.id, user_id=user.id)
        .first()
    )
    if existing:
        raise HTTPException(409, "You already belong to this institution.")
    if (
        usage(db, inst)["members"]
        >= LIMITS.get(inst.plan, LIMITS["starter"])["members"]
    ):
        raise HTTPException(409, "The institution has no available seats.")
    db.add(
        InstitutionMember(
            institution_id=inst.id,
            user_id=user.id,
            role=invite.role,
            department=invite.department,
            status="active",
        )
    )
    invite.status = "accepted"
    audit(db, inst.id, user, "member.joined", user.display_name or "Member joined")
    save(db)
    return serialize(inst, invite.role)


def update_member(db, institution_id, member_id, user, data):
    inst, actor = scope(db, institution_id, user, MANAGERS, lock=True)
    member = (
        db.query(InstitutionMember)
        .filter_by(id=member_id, institution_id=institution_id)
        .first()
    )
    if not member:
        raise HTTPException(404, "Member not found.")
    if member.role == "owner" or member.user_id == user.id:
        raise HTTPException(403, "Owner and self access cannot be changed here.")
    if actor.role != "owner" and (member.role == "admin" or data.role == "admin"):
        raise HTTPException(403, "Only the owner can manage administrators.")
    if member.status != "active" and data.status == "active":
        capacity(db, inst, "members")
    for key, value in data.model_dump().items():
        setattr(member, key, value)
    audit(
        db,
        institution_id,
        user,
        "member.updated",
        f"Member #{member.id}: {member.role}, {member.status}",
    )
    save(db)


def create_batch(db, institution_id, user, data):
    inst, _ = scope(db, institution_id, user, MANAGERS, lock=True)
    capacity(db, inst, "batches")
    row = InstitutionBatch(institution_id=institution_id, **data.model_dump())
    db.add(row)
    audit(db, institution_id, user, "batch.created", data.name)
    save(db)
    return {"id": row.id}


def batch_scope(db, institution_id, batch_id):
    row = (
        db.query(InstitutionBatch)
        .filter_by(id=batch_id, institution_id=institution_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Batch not found.")
    return row


def add_batch_members(db, institution_id, batch_id, user, ids):
    scope(db, institution_id, user, MANAGERS, lock=True)
    batch = batch_scope(db, institution_id, batch_id)
    ids = set(ids)
    members = (
        db.query(InstitutionMember)
        .filter(
            InstitutionMember.id.in_(ids),
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.role == "student",
            InstitutionMember.status == "active",
        )
        .all()
    )
    if len(members) != len(ids):
        raise HTTPException(422, "Choose active students from this institution only.")
    existing = {
        r.member_id
        for r in db.query(InstitutionBatchMember).filter_by(batch_id=batch_id).all()
    }
    for member_id in ids - existing:
        db.add(InstitutionBatchMember(batch_id=batch_id, member_id=member_id))
    audit(
        db,
        institution_id,
        user,
        "batch.members_added",
        f"{batch.name}: {len(ids - existing)} students",
    )
    save(db)


def available_courses(db, institution_id, user):
    scope(db, institution_id, user, STAFF)
    # No global catalog enumeration: offer the actor's own or collaborated courses.
    ids = collaborated_course_ids(db, user.id)
    return [
        {"id": c.id, "title": c.post_title, "status": c.post_status}
        for c in db.query(Course)
        .filter((Course.post_author == user.id) | Course.id.in_(ids))
        .order_by(Course.post_title)
        .limit(200)
        .all()
    ]


def connect_course(db, institution_id, user, course_id):
    inst, _ = scope(db, institution_id, user, STAFF, lock=True)
    course = db.query(Course).filter_by(id=course_id).first()
    if not course or not can_edit(db, course, user):
        raise HTTPException(404, "Editable course not found.")
    if (
        db.query(InstitutionCourse)
        .filter_by(institution_id=institution_id, course_id=course_id)
        .first()
    ):
        raise HTTPException(409, "This course is already connected.")
    capacity(db, inst, "courses")
    row = InstitutionCourse(
        institution_id=institution_id, course_id=course_id, connected_by=user.id
    )
    db.add(row)
    audit(db, institution_id, user, "course.connected", course.post_title)
    save(db)


def assign_course(db, institution_id, batch_id, user, data):
    scope(db, institution_id, user, MANAGERS, lock=True)
    batch = batch_scope(db, institution_id, batch_id)
    linked = (
        db.query(InstitutionCourse)
        .filter_by(id=data.institution_course_id, institution_id=institution_id)
        .first()
    )
    if not linked:
        raise HTTPException(404, "Connected course not found.")
    course = db.query(Course).filter_by(id=linked.course_id).one()
    # Course creation stores "publish" while the publish endpoint stores
    # "published" (see PUBLISHED_STATUSES in routers/courses.py) — accept both
    # spellings, or every freshly created "published" course is rejected here.
    if course.post_status not in ("publish", "published", "PUBLISH", "PUBLISHED"):
        raise HTTPException(409, "Publish this course before assigning it to a batch.")
    row = (
        db.query(InstitutionAssignment)
        .filter_by(batch_id=batch_id, institution_course_id=linked.id)
        .first()
    )
    if not row:
        row = InstitutionAssignment(batch_id=batch_id, institution_course_id=linked.id)
        db.add(row)
    row.due_date = data.due_date.isoformat() if data.due_date else None
    audit(
        db,
        institution_id,
        user,
        "course.assigned",
        f"{course.post_title} → {batch.name}",
    )
    save(db)


def report_rows(db, institution_id, user):
    _, actor = scope(db, institution_id, user)
    q = (
        db.query(
            InstitutionBatch,
            InstitutionMember,
            User,
            InstitutionCourse,
            Course,
            InstitutionAssignment,
        )
        .join(
            InstitutionBatchMember,
            InstitutionBatchMember.batch_id == InstitutionBatch.id,
        )
        .join(
            InstitutionMember, InstitutionMember.id == InstitutionBatchMember.member_id
        )
        .join(User, User.id == InstitutionMember.user_id)
        .join(
            InstitutionAssignment, InstitutionAssignment.batch_id == InstitutionBatch.id
        )
        .join(
            InstitutionCourse,
            InstitutionCourse.id == InstitutionAssignment.institution_course_id,
        )
        .join(Course, Course.id == InstitutionCourse.course_id)
        .filter(
            InstitutionBatch.institution_id == institution_id,
            InstitutionMember.institution_id == institution_id,
            InstitutionCourse.institution_id == institution_id,
            InstitutionMember.status == "active",
            InstitutionMember.role == "student",
        )
    )
    if actor.role not in STAFF:
        q = q.filter(InstitutionMember.user_id == user.id)
    rows = q.order_by(InstitutionBatch.name, User.display_name, Course.post_title).all()
    user_ids = {r[2].id for r in rows}
    course_ids = {r[4].id for r in rows}
    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id.in_(user_ids),
            Enrollment.course_id.in_(course_ids),
            Enrollment.enrollment_status.in_(("enrolled", "active", "completed")),
        )
        .all()
        if rows
        else []
    )
    progress = {}
    for e in enrollments:
        key = (e.user_id, e.course_id)
        progress[key] = max(progress.get(key, 0), e.course_progress_percentage or 0)
    return [
        {
            "batch_id": b.id,
            "batch": b.name,
            "student": u.display_name or "Student",
            "user_id": u.id,
            "course_id": c.id,
            "course": c.post_title,
            "due_date": a.due_date,
            "progress": min(100, max(0, progress.get((u.id, c.id), 0))),
            "has_access": (u.id, c.id) in progress,
        }
        for b, m, u, ic, c, a in rows
    ]


def overview(db, institution_id, user):
    inst, actor = scope(db, institution_id, user)
    staff, manager = actor.role in STAFF, actor.role in MANAGERS
    members_q = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(InstitutionMember.institution_id == institution_id)
    )
    if not staff:
        members_q = members_q.filter(InstitutionMember.user_id == user.id)
    members = [
        {
            "id": m.id,
            "user_id": u.id,
            "name": u.display_name or "Member",
            "email": u.user_email if manager or u.id == user.id else "",
            "role": m.role,
            "department": m.department,
            "status": m.status,
        }
        for m, u in members_q.order_by(User.display_name).all()
    ]
    bq = db.query(InstitutionBatch).filter_by(institution_id=institution_id)
    if not staff:
        bq = bq.join(
            InstitutionBatchMember,
            InstitutionBatchMember.batch_id == InstitutionBatch.id,
        ).filter(InstitutionBatchMember.member_id == actor.id)
    batches = []
    for b in bq.order_by(InstitutionBatch.name).all():
        member_ids = [
            r.member_id
            for r in db.query(InstitutionBatchMember)
            .join(
                InstitutionMember,
                InstitutionMember.id == InstitutionBatchMember.member_id,
            )
            .filter(
                InstitutionBatchMember.batch_id == b.id,
                InstitutionMember.status == "active",
                InstitutionMember.role == "student",
            )
            .all()
        ]
        assignments = [
            {
                "id": a.id,
                "institution_course_id": a.institution_course_id,
                "due_date": a.due_date,
            }
            for a in db.query(InstitutionAssignment).filter_by(batch_id=b.id).all()
        ]
        batches.append(
            {
                "id": b.id,
                "name": b.name,
                "department": b.department,
                "academic_year": b.academic_year,
                "student_count": len(member_ids),
                "member_ids": member_ids if staff else [actor.id],
                "assignments": assignments,
            }
        )
    cq = (
        db.query(InstitutionCourse, Course)
        .join(Course, Course.id == InstitutionCourse.course_id)
        .filter(InstitutionCourse.institution_id == institution_id)
    )
    if not staff:
        assigned = {
            a["institution_course_id"] for b in batches for a in b["assignments"]
        }
        cq = cq.filter(InstitutionCourse.id.in_(assigned))
    courses = [
        {
            "id": ic.id,
            "course_id": c.id,
            "title": c.post_title,
            "status": c.post_status,
            "can_edit": can_edit(db, c, user),
        }
        for ic, c in cq.order_by(Course.post_title).all()
    ]
    invites = (
        [
            {
                "id": i.id,
                "email": i.email,
                "role": i.role,
                "status": "expired"
                if i.status == "pending"
                and utc(i.expires_at) <= datetime.now(timezone.utc)
                else i.status,
                "expires_at": utc(i.expires_at),
            }
            for i in db.query(InstitutionInvite)
            .filter_by(institution_id=institution_id)
            .order_by(InstitutionInvite.id.desc())
            .limit(100)
        ]
        if manager
        else []
    )
    events = (
        [
            {
                "id": a.id,
                "action": a.action,
                "detail": a.detail,
                "created_at": utc(a.created_at),
            }
            for a in db.query(InstitutionAudit)
            .filter_by(institution_id=institution_id)
            .order_by(InstitutionAudit.id.desc())
            .limit(50)
        ]
        if manager
        else []
    )
    requests = (
        [
            {
                "id": r.id,
                "plan": r.plan,
                "status": r.status,
                "created_at": utc(r.created_at),
            }
            for r in db.query(InstitutionPlanRequest)
            .filter_by(institution_id=institution_id)
            .order_by(InstitutionPlanRequest.id.desc())
            .limit(20)
        ]
        if manager
        else []
    )
    return {
        "institution": serialize(inst, actor.role),
        "members": members,
        "batches": batches,
        "courses": courses,
        "invites": invites,
        "activity": events,
        "usage": usage(db, inst) if staff else None,
        "plan_requests": requests,
        "report": report_rows(db, institution_id, user),
    }


def request_plan(db, institution_id, user, data):
    scope(db, institution_id, user, ("owner",), lock=True)
    pending = (
        db.query(InstitutionPlanRequest)
        .filter_by(institution_id=institution_id, status="pending")
        .first()
    )
    if pending:
        raise HTTPException(409, "A plan request is already pending review.")
    db.add(
        InstitutionPlanRequest(
            institution_id=institution_id,
            requested_by=user.id,
            **data.model_dump(),
            status="pending",
        )
    )
    audit(db, institution_id, user, "plan.requested", data.plan)
    save(db)
