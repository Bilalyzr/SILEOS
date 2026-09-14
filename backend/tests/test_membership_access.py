from app.models.enrollment import Enrollment
from app.models.membership import (
    Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
)
from app.services.membership_access import (
    covered_course_ids, grant_membership_enrollments,
    suspend_membership_enrollments,
)


def _plan(db, all_access=True, course_ids=()):
    plan = MembershipPlan(name="T", all_access=all_access, period="monthly",
                          interval=1, price=999.0,
                          razorpay_plan_id=f"plan_{all_access}_{len(course_ids)}")
    db.add(plan)
    db.flush()
    for cid in course_ids:
        db.add(MembershipPlanCourse(plan_id=plan.id, course_id=cid))
    db.commit()
    db.refresh(plan)
    return plan


def _membership(db, user, plan):
    m = Membership(user_id=user.id, plan_id=plan.id,
                   razorpay_subscription_id=f"sub_{plan.id}_{user.id}")
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _publish(db, *courses):
    """The Course fixture defaults to post_status='draft'; all_access coverage
    is restricted to published courses."""
    for c in courses:
        c.post_status = "publish"
    db.commit()


def test_all_access_covers_paid_courses_only(db, course, free_course):
    _publish(db, course, free_course)
    plan = _plan(db, all_access=True)
    ids = covered_course_ids(db, plan)
    assert course.id in ids
    assert free_course.id not in ids


def test_all_access_excludes_unpublished_paid_course(db, course):
    """A draft paid course must not be handed to all-access members before
    it is published."""
    course.post_status = "draft"
    db.commit()
    plan = _plan(db, all_access=True)
    assert course.id not in covered_course_ids(db, plan)
    _publish(db, course)
    assert course.id in covered_course_ids(db, plan)


def test_curated_plan_still_covers_unpublished_course(db, course):
    """Curated tiers are unchanged: an admin explicitly picked those rows."""
    course.post_status = "draft"
    db.commit()
    plan = _plan(db, all_access=False, course_ids=[course.id])
    assert covered_course_ids(db, plan) == {course.id}


def test_curated_covers_exact_set(db, course):
    plan = _plan(db, all_access=False, course_ids=[course.id])
    assert covered_course_ids(db, plan) == {course.id}


def test_grant_creates_membership_rows(db, student_user, course):
    plan = _plan(db, all_access=False, course_ids=[course.id])
    m = _membership(db, student_user, plan)
    n = grant_membership_enrollments(db, m)
    db.commit()
    assert n == 1
    row = db.query(Enrollment).filter_by(user_id=student_user.id,
                                         course_id=course.id).one()
    assert row.enrollment_source == "membership"
    assert row.membership_id == m.id
    assert row.enrollment_status == "enrolled"
    # idempotent
    assert grant_membership_enrollments(db, m) == 0


def test_grant_never_touches_existing_purchase_row(db, student_user, course):
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="enrolled"))
    db.commit()
    plan = _plan(db, all_access=False, course_ids=[course.id])
    m = _membership(db, student_user, plan)
    assert grant_membership_enrollments(db, m) == 0
    row = db.query(Enrollment).filter_by(user_id=student_user.id,
                                         course_id=course.id).one()
    assert row.enrollment_source is None


def test_suspend_only_membership_rows_without_order(db, student_user, course, order_row):
    plan = _plan(db, all_access=False, course_ids=[course.id])
    m = _membership(db, student_user, plan)
    grant_membership_enrollments(db, m)
    db.commit()
    # Simulate the member later BUYING the course: purchase flow stamps order_id.
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    row.order_id = order_row.id
    db.commit()
    assert suspend_membership_enrollments(db, m) == 0  # exempt: has order
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    assert row.enrollment_status == "enrolled"


def test_suspend_and_regrant_cycle(db, student_user, course):
    plan = _plan(db, all_access=False, course_ids=[course.id])
    m = _membership(db, student_user, plan)
    grant_membership_enrollments(db, m)
    db.commit()
    assert suspend_membership_enrollments(db, m) == 1
    db.commit()
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    assert row.enrollment_status == "suspended"
    # progress-preserving reactivation on re-grant
    assert grant_membership_enrollments(db, m) == 1
    db.commit()
    db.refresh(row)
    assert row.enrollment_status == "enrolled"
