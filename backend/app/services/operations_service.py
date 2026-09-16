"""Administrative operations based on stored evidence; never inferred service health."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import shutil
from sqlalchemy import func, case, text
from app.core import listing
from app.models.course import Course
from app.models.user import User, InstructorProfile
from app.models.enrollment import Enrollment
from app.models.payment import Order, Payment, PaymentStatus
from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
from app.models.learning_planner import LearningIntervention, LearningPlanTask
from app.models.recording_lesson import RecordingLesson
from app.models.membership import Membership, MembershipPlan, MembershipStatus
from app.models.operations import ServiceHeartbeat


def now():
    return datetime.now(timezone.utc)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def value(v):
    return v.value if hasattr(v, "value") else v


def pulse(db, name, status="ok", detail=None):
    row = db.get(ServiceHeartbeat, name)
    if row is None:
        row = ServiceHeartbeat(name=name); db.add(row)
    row.status, row.detail, row.seen_at = status, detail or {}, now()
    db.commit()


def heartbeat(name, status="ok", detail=None):
    from app.core.database import SessionLocal
    try:
        with SessionLocal() as db:
            pulse(db, name, status, detail)
    except Exception:
        # Monitoring cannot fail the operation it describes.
        import logging
        logging.getLogger(__name__).warning("Could not record service heartbeat: %s", name)


def listing_query(db, dataset, q="", status=""):
    if dataset == "courses":
        model = Course; query = db.query(model); cols = [model.post_title, model.course_category]
        sorts = {"name": model.post_title, "created": model.created_at, "status": model.post_status, "id": model.id}
        if status: query = query.filter(model.post_status == status)
        serialize = lambda r: {"id": r.id, "name": r.post_title, "detail": r.course_category, "status": r.post_status, "created": r.created_at, "amount": float(r.course_price or 0), "href": f"/instructor/courses/{r.id}/edit"}
    elif dataset in ("students", "instructors"):
        model = User; query = db.query(model).filter(model.role == dataset[:-1]); cols = [model.display_name, model.user_email]
        sorts = {"name": model.display_name, "created": model.created_at, "status": model.is_active, "id": model.id}
        if status:
            if status not in ("active", "inactive"): raise ValueError("Choose active or inactive.")
            query = query.filter(model.is_active == (status == "active"))
        serialize = lambda r: {"id": r.id, "name": r.display_name, "detail": r.user_email, "status": "active" if r.is_active else "inactive", "created": r.created_at, "amount": None, "href": "/admin/manage"}
    elif dataset == "orders":
        model = Order; query = db.query(model); cols = [model.id, model.order_status]
        sorts = {"name": model.id, "created": model.created_at, "status": model.order_status, "id": model.id}
        if status:
            from app.models.payment import OrderStatus
            query = query.filter(model.order_status == OrderStatus(status))
        serialize = lambda r: {"id": r.id, "name": f"Order #{r.id}", "detail": f"Customer #{r.user_id}", "status": value(r.order_status), "created": r.created_at, "amount": float(r.total_amount or 0), "href": "/admin/orders"}
    elif dataset == "enrollments":
        model = Enrollment; query = db.query(model).join(Course, Course.id == model.course_id).join(User, User.id == model.user_id); cols = [Course.post_title, User.user_email, User.display_name]
        sorts = {"name": Course.post_title, "created": model.created_at, "status": model.enrollment_status, "id": model.id}
        if status: query = query.filter(model.enrollment_status == status)
        def serialize(r):
            return {"id": r.id, "name": db.get(Course, r.course_id).post_title, "detail": db.get(User, r.user_id).user_email, "status": r.enrollment_status, "created": r.created_at, "amount": None, "href": "/admin/enrollments"}
    else:
        raise ValueError("Unknown admin dataset.")
    return listing.filtered(query, q, cols), sorts, model.id, serialize


def queues(db):
    buckets = []
    def add(key, label, query, describe, href, clock):
        count = query.count()
        items = [{"id": r.id, "title": describe(r), "href": href(r), "age_hours": round(max(0, (now() - utc(clock(r))).total_seconds() / 3600), 1) if clock(r) else None} for r in query.limit(20).all()]
        buckets.append({"key": key, "label": label, "count": count, "items": items})
    add("courses", "Courses awaiting approval", db.query(Course).filter(Course.post_status == "pending").order_by(Course.created_at), lambda r: r.post_title, lambda r: "/admin/approvals", lambda r: r.created_at)
    add("instructors", "Instructor applications", db.query(InstructorProfile).filter(InstructorProfile.is_approved.is_(False), InstructorProfile.is_blocked.is_(False)).order_by(InstructorProfile.created_at), lambda r: db.get(User, r.user_id).display_name, lambda r: "/admin/approvals", lambda r: r.created_at)
    add("grading", "Assignments ungraded for 48 hours", db.query(AssignmentSubmission).filter(AssignmentSubmission.status == SubmissionStatus.SUBMITTED, AssignmentSubmission.graded_at.is_(None), AssignmentSubmission.submitted_at < now() - timedelta(hours=48)).order_by(AssignmentSubmission.submitted_at), lambda r: db.get(Assignment, r.assignment_id).title, lambda r: f"/instructor/courses/{db.get(Assignment, r.assignment_id).course_id}/grading-queue", lambda r: r.submitted_at)
    add("interventions", "Learners needing instructor support", db.query(LearningIntervention).filter(LearningIntervention.status == "needs_instructor").order_by(LearningIntervention.updated_at), lambda r: r.concept, lambda r: "/instructor/interventions", lambda r: r.updated_at)
    add("recordings", "Failed recording jobs", db.query(RecordingLesson).filter(RecordingLesson.status == "failed").order_by(RecordingLesson.updated_at), lambda r: r.title, lambda r: f"/instructor/recording-lessons?class_id={r.class_id}", lambda r: r.updated_at)
    return buckets


def outcomes(db):
    counts = db.query(Enrollment.course_id, func.count(Enrollment.id), func.sum(case((Enrollment.enrollment_status == "completed", 1), else_=0)), func.avg(Enrollment.course_progress_percentage)).filter(Enrollment.enrollment_status.in_(["enrolled", "completed"])).group_by(Enrollment.course_id).all()
    courses = [{"course_id": cid, "title": db.get(Course, cid).post_title, "learners": total, "completed": int(completed or 0), "completion_rate": round(100 * (completed or 0) / total, 1), "mean_progress": round(float(progress or 0), 1)} for cid, total, completed, progress in counts]
    weak = db.query(LearningIntervention.concept, func.count(LearningIntervention.id)).filter(LearningIntervention.status.notin_(["resolved", "dismissed"])).group_by(LearningIntervention.concept).order_by(func.count(LearningIntervention.id).desc()).limit(20).all()
    paired = []
    # Compare verified practice/follow-up pairs per intervention; no score means unknown.
    verified = {}
    for task in db.query(LearningPlanTask).filter(LearningPlanTask.status == 'done', LearningPlanTask.kind.in_(['practice', 'followup']), LearningPlanTask.intervention_id.isnot(None), LearningPlanTask.completed_at.isnot(None)).order_by(LearningPlanTask.completed_at, LearningPlanTask.id):
        evidence = task.outcome or {}
        if evidence.get('enough_evidence') is not True or not isinstance(evidence.get('score'), (int, float)): continue
        pair = verified.setdefault(task.intervention_id, {})
        pair[task.kind] = (task.completed_at, evidence['score'])
    for pair in verified.values():
        if 'practice' in pair and 'followup' in pair and pair['followup'][0] > pair['practice'][0]:
            paired.append(pair['followup'][1] - pair['practice'][1])
    return {"courses": courses, "struggling_concepts": [{"concept": c, "open_interventions": n} for c, n in weak], "paired_interventions": len(paired), "mean_delayed_change": round(sum(paired) / len(paired), 1) if paired else None}


def revenue(db, start, end):
    after = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    before = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    captured = db.query(Payment.currency, func.sum(Payment.amount)).filter(Payment.payment_status.in_([PaymentStatus.COMPLETED, PaymentStatus.REFUNDED]), Payment.payment_date >= after, Payment.payment_date < before).group_by(Payment.currency).all()
    refunds = dict(db.query(Payment.currency, func.sum(Payment.amount)).filter(Payment.payment_status == PaymentStatus.REFUNDED, Payment.refund_processed_at >= after, Payment.refund_processed_at < before).group_by(Payment.currency).all())
    gross = dict(captured)
    currencies = [{"currency": currency or "INR", "captured": float(gross.get(currency) or 0), "refunded": float(refunds.get(currency) or 0), "net_cash": float((gross.get(currency) or 0) - (refunds.get(currency) or 0))} for currency in sorted(set(gross) | set(refunds))]
    mrr = Decimal("0")
    for plan, membership in db.query(MembershipPlan, Membership).join(Membership, Membership.plan_id == MembershipPlan.id).filter(Membership.status == MembershipStatus.ACTIVE):
        if not membership.current_period_end or utc(membership.current_period_end) <= now(): continue
        months = {"daily": Decimal(12) / 365, "weekly": Decimal(12) / 52, "monthly": Decimal(1), "yearly": Decimal(12)}.get(plan.period)
        if months and plan.interval > 0: mrr += plan.price / (months * plan.interval)
    return {"from": str(start), "to": str(end), "currencies": currencies, "estimated_active_mrr_inr": float(round(mrr, 2)), "failed_payments": db.query(Payment).filter(Payment.payment_status == PaymentStatus.FAILED, Payment.payment_date >= after, Payment.payment_date < before).count(), "refunds_needing_attention": db.query(Payment).filter(Payment.refund_status.in_(["failed", "requested"])).count(), "refunds_missing_timestamp": db.query(Payment).filter(Payment.payment_status == PaymentStatus.REFUNDED, Payment.refund_processed_at.is_(None)).count(), "note": "UTC date window. Refunds use processing date; missing refund timestamps are reported separately. MRR is an estimate of current active subscriptions, not collected cash."}


def health(db):
    from app.services.transcription_provider import configuration
    from app.core.config import get_settings
    db.execute(text("SELECT 1"))
    try:
        disk = shutil.disk_usage(Path(get_settings().UPLOAD_DIR).resolve())
        storage = {"status": "ok", "free_bytes": disk.free, "total_bytes": disk.total,
                   "free_percent": round(100 * disk.free / disk.total, 1)}
    except OSError:
        # A missing/unmounted upload volume must not take down the entire
        # operations dashboard or report another disk's capacity as healthy.
        storage = {"status": "unavailable", "free_bytes": None, "total_bytes": None,
                   "free_percent": None}
    rows = {r.name: r for r in db.query(ServiceHeartbeat)}
    services = []
    for name, window in (("recording_worker", 120), ("payment_reconciliation", 900)):
        row = rows.get(name); age = (now() - utc(row.seen_at)).total_seconds() if row else None
        allowed = 3720 if row and row.status == "processing" and name == "recording_worker" else window
        services.append({"name": name, "status": "unknown" if row is None else "stale" if age > allowed else row.status, "last_seen": row.seen_at if row else None, "age_seconds": round(age) if age is not None else None})
    return {"database": "ok", "transcription": configuration(), "services": services, "storage": storage, "recording_jobs": {status: count for status, count in db.query(RecordingLesson.status, func.count(RecordingLesson.id)).group_by(RecordingLesson.status)}, "note": "Unknown means no worker heartbeat has been recorded. Storage measures the upload filesystem; unavailable means the configured volume could not be read."}
