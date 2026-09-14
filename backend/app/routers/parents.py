"""Parent/guardian layer (v2.0 §4.2 SP studio + owner decision 2026-09-05).

Model: a parent is a user with role='parent', linked to students via
parent_students (verified by the parent knowing the student's email —
upgraded to OTP/email verification when the notification stack lands).
Digest: weekly per-student summary (attendance, grades, at-risk flags) —
the same numbers the student sees, nothing more (no financials, no other
students). WhatsApp delivery is an adapter stub: honest 503 without
MSG91_API_KEY, digest preview always available in the parent dashboard.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.database import Base, get_db
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter()


class ParentStudent(Base):
    __tablename__ = "parent_students"
    id = Column(Integer, primary_key=True, index=True)
    parent_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    linked_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("parent_user_id", "student_user_id", name="uq_parent_student"),
    )


def _linked_students(db: Session, parent: User):
    # ParentStudent is the durable, approved grant. ParentLinkRequest is the
    # pending/approval workflow that creates it; requiring both rows here
    # silently revoked every guardian link created before that workflow was
    # introduced. It also made access depend on disposable request history.
    return (db.query(User)
            .join(ParentStudent, ParentStudent.student_user_id == User.id)
            .filter(ParentStudent.parent_user_id == parent.id)
            .all())


def _require_parent(current_user: User) -> None:
    if current_user.role not in ("parent", "admin"):
        raise HTTPException(status_code=403, detail="Parent access only")


@router.post("/children")
def link_child(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_active_user),
):
    """Link a child by their account email (parent must know it)."""
    _require_parent(current_user)
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="email is required")
    student = db.query(User).filter(
        User.user_email == email, User.role == "student").first()
    if not student:
        return {"status": "pending", "already": False}
    if not current_user.is_verified:
        raise HTTPException(403, "Verify your email before requesting guardian access.")
    from app.models.campus_operations import ParentLinkRequest
    request = db.query(ParentLinkRequest).filter_by(parent_user_id=current_user.id, student_user_id=student.id).first()
    if request:
        return {"status": request.status, "already": request.status == "approved"}
    db.add(ParentLinkRequest(parent_user_id=current_user.id, student_user_id=student.id))
    db.commit()
    return {"status": "pending", "already": False}



@router.get("/children")
def list_children(
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_active_user),
):
    _require_parent(current_user)
    kids = _linked_students(db, current_user)
    return {"children": [
        {"id": k.id, "name": k.display_name, "email": k.user_email}
        for k in kids
    ]}


def _attendance_summary(db: Session, student_id: int, course_id: int) -> dict:
    from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassStatus
    ended = db.query(LiveClass.id).filter(LiveClass.course_id == course_id, LiveClass.status == LiveClassStatus.ENDED).all()
    ids = [i for (i,) in ended]
    present = 0
    if ids:
        present = db.query(LiveClassAttendance).filter(LiveClassAttendance.user_id == student_id,
                                                       LiveClassAttendance.class_id.in_(ids),
                                                       LiveClassAttendance.present.is_(True)).count()
    return {"classes_held": len(ids), "attended": present}


def _recent_scores(db: Session, student_id: int, course_id: int, since) -> list:
    from app.models.quiz import QuizAttempt
    rows = (db.query(QuizAttempt).filter(QuizAttempt.user_id == student_id, QuizAttempt.course_id == course_id,
                                         QuizAttempt.attempt_ended_at.isnot(None))
            .order_by(QuizAttempt.attempt_id.desc()).limit(5).all())
    return [{"quiz_id": a.quiz_id, "score": float(a.earned_marks or 0), "max": float(a.total_marks or 0)} for a in rows]


def _shared_reports(db: Session, course_id: int) -> list:
    from app.models.live_class_report import ClassReport
    rows = (db.query(ClassReport).filter(ClassReport.course_id == course_id, ClassReport.shared_with_guardians.is_(True))
            .order_by(ClassReport.id.desc()).limit(5).all())
    return [{"class_id": r.class_id, "title": r.title, "ended_at": r.ended_at.isoformat() if r.ended_at else None} for r in rows]


def _build_digest(db: Session, student: User) -> dict:
    """One student's weekly digest: enrollment progress, recent grades,
    at-risk flags. Same data the student sees — no financials."""
    from app.models.enrollment import Enrollment
    from app.models.sileos_pack import StudentRiskFlag

    since = datetime.now(timezone.utc) - timedelta(days=7)
    courses = []
    for e in (db.query(Enrollment)
              .filter(Enrollment.user_id == student.id,
                      Enrollment.enrollment_status.in_(["enrolled", "completed"]))
              .limit(20).all()):
        flag = (db.query(StudentRiskFlag)
                .filter(StudentRiskFlag.user_id == student.id,
                        StudentRiskFlag.course_id == e.course_id).first())
        # v2.0 §4 (WP6): per-course Parent View Configurator decides what a
        # guardian sees. Defaults come from the course type (SP: attendance +
        # completion only).
        from app.services import studio_service
        pv = studio_service.parent_view(db, e.course_id)
        entry = {
            "course_id": e.course_id,
            "status": e.enrollment_status,
            "visible": [k for k, v in pv.items() if v],
        }
        if pv.get("completion"):
            entry["progress"] = int(e.course_progress_percentage or 0)
        if pv.get("attendance"):
            entry["attendance"] = _attendance_summary(db, student.id, e.course_id)
        if pv.get("scores"):
            entry["risk"] = {"severity": flag.severity, "reasons": flag.reasons} if flag else None
            entry["recent_scores"] = _recent_scores(db, student.id, e.course_id, since)
        if pv.get("class_reports"):
            entry["shared_reports"] = _shared_reports(db, e.course_id)
        courses.append(entry)
    return {
        "student": {"id": student.id, "name": student.display_name},
        "week_of": since.date().isoformat(),
        "courses": courses,
    }


@router.get("/digest")
def my_children_digest(
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_active_user),
):
    """Digests for every linked child — powers the parent dashboard."""
    _require_parent(current_user)
    kids = _linked_students(db, current_user)
    return {"digests": [_build_digest(db, k) for k in kids]}


@router.post("/digest/whatsapp")
def send_whatsapp_digest(
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_active_user),
):
    """Queue WhatsApp delivery of the digest. Honest 503 without
    MSG91_API_KEY — preview in the dashboard works regardless."""
    import os
    if not os.environ.get("MSG91_API_KEY", "").strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp delivery is not configured: set MSG91_API_KEY "
                   "on the backend. The digest itself is always available "
                   "in the parent dashboard.",
        )
    _require_parent(current_user)
    kids = _linked_students(db, current_user)
    raise HTTPException(503, "WhatsApp delivery is not installed. Your approved learning summaries remain available here.")


@router.get("/access-requests")
def access_requests(db: Session = Depends(get_db), current_user=Depends(AuthService.get_current_active_user)):
    from app.models.campus_operations import ParentLinkRequest
    return [{"id": r.id, "parent_name": u.display_name, "parent_email": u.user_email, "status": r.status}
            for r,u in db.query(ParentLinkRequest,User).join(User,User.id==ParentLinkRequest.parent_user_id)
            .filter(ParentLinkRequest.student_user_id==current_user.id).all()]


from app.schemas.campus_operations import LinkDecision

@router.patch("/access-requests/{request_id}")
def decide_access(request_id:int, data:LinkDecision, db:Session=Depends(get_db), current_user=Depends(AuthService.get_current_active_user)):
    from app.models.campus_operations import ParentLinkRequest
    if not current_user.is_verified:raise HTTPException(403,"Verify your email before approving guardian access.")
    # Lock the student to serialize both duplicate approvals and revocation.
    db.query(User).filter_by(id=current_user.id).with_for_update().one()
    row=db.query(ParentLinkRequest).filter_by(id=request_id,student_user_id=current_user.id).first()
    if not row:raise HTTPException(404,"Request not found.")
    row.status=data.status
    link=db.query(ParentStudent).filter_by(parent_user_id=row.parent_user_id,student_user_id=current_user.id).first()
    if data.status=="approved" and not link:db.add(ParentStudent(parent_user_id=row.parent_user_id,student_user_id=current_user.id))
    if data.status!="approved" and link:db.delete(link)
    db.commit()
    return {"status":row.status}
