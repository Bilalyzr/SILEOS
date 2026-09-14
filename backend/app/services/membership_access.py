"""Grant / suspend the Enrollment rows a membership materializes.

Ownership rules (spec):
- grant never overwrites an existing (user, course) row of ANY source;
- suspend touches only rows with enrollment_source == "membership" AND
  order_id IS NULL (a later purchase stamps order_id and permanently
  exempts the row);
- suspension preserves all progress; re-grant flips status back to enrolled.
Callers own commit/rollback.
"""
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.membership import Membership, MembershipPlan, MembershipPlanCourse


# Same set routers/courses.py uses for public listing. An all_access tier
# means "every paid course a member could browse", so unpublished drafts
# must not be silently handed out.
PUBLISHED_STATUSES = ["publish", "published", "PUBLISH", "PUBLISHED"]


def covered_course_ids(db: Session, plan: MembershipPlan) -> set[int]:
    if plan.all_access:
        rows = (db.query(Course.id)
                .filter(Course.course_price_type == "paid",
                        Course.post_status.in_(PUBLISHED_STATUSES)).all())
    else:
        rows = (db.query(MembershipPlanCourse.course_id)
                .filter(MembershipPlanCourse.plan_id == plan.id).all())
    return {r[0] for r in rows}


def grant_membership_enrollments(db: Session, membership: Membership) -> int:
    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == membership.plan_id).one()
    covered = covered_course_ids(db, plan)
    if not covered:
        return 0
    existing = {
        e.course_id: e
        for e in db.query(Enrollment).filter(
            Enrollment.user_id == membership.user_id,
            Enrollment.course_id.in_(covered),
        ).all()
    }
    changed = 0
    for course_id in covered:
        row = existing.get(course_id)
        if row is None:
            db.add(Enrollment(
                course_id=course_id,
                user_id=membership.user_id,
                enrollment_status="enrolled",
                enrollment_source="membership",
                membership_id=membership.id,
            ))
            changed += 1
        elif (row.enrollment_source == "membership"
              and row.enrollment_status == "suspended"):
            row.enrollment_status = "enrolled"
            row.membership_id = membership.id
            changed += 1
        elif (row.enrollment_source == "membership"
              and row.enrollment_status == "enrolled"
              and row.membership_id != membership.id):
            # cancel -> resubscribe: the row is still owned by the OLD
            # membership, so that membership's later lapse-expiry pass would
            # suspend an actively paying member. Re-point ownership to the
            # membership that is granting now.
            row.membership_id = membership.id
            changed += 1
        # any other existing row (purchase, cohort, completed...) is not ours
    return changed


def suspend_membership_enrollments(db: Session, membership: Membership) -> int:
    rows = db.query(Enrollment).filter(
        Enrollment.membership_id == membership.id,
        Enrollment.enrollment_source == "membership",
        Enrollment.order_id.is_(None),
        Enrollment.enrollment_status == "enrolled",
    ).all()
    for row in rows:
        row.enrollment_status = "suspended"
    return len(rows)
