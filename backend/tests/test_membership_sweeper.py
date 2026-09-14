from datetime import datetime, timedelta, timezone

from app.models.enrollment import Enrollment
from app.models.membership import (
    Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
)
from app.models.user import User
from app.services.membership_access import grant_membership_enrollments
from app.services.reconciliation import (
    expire_lapsed_memberships, sync_membership_catalog,
)


def _second_user(db, tag="two"):
    """A minimal second User row, bypassing password hashing (irrelevant
    here and broken in this environment's bcrypt/passlib pairing)."""
    u = User(
        user_login=f"user_{tag}",
        user_pass="x",
        user_nicename=f"user_{tag}",
        user_email=f"user_{tag}@example.com",
        display_name=f"User {tag}",
        role="student",
        is_active=True,
        is_verified=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _setup(db, user, course, status, **kw):
    plan = MembershipPlan(name="T", all_access=False, period="monthly",
                          interval=1, price=9.0, razorpay_plan_id="plan_S")
    db.add(plan)
    db.flush()
    db.add(MembershipPlanCourse(plan_id=plan.id, course_id=course.id))
    m = Membership(user_id=user.id, plan_id=plan.id,
                   razorpay_subscription_id="sub_S1", status=status, **kw)
    db.add(m)
    db.commit()
    db.refresh(m)
    grant_membership_enrollments(db, m)
    db.commit()
    return plan, m


def test_grace_expiry_suspends(db, student_user, course):
    _, m = _setup(db, student_user, course, MembershipStatus.GRACE,
                  grace_until=datetime.now(timezone.utc) - timedelta(days=1))
    assert expire_lapsed_memberships(db) == 1
    db.refresh(m)
    assert m.status == MembershipStatus.SUSPENDED
    assert db.query(Enrollment).filter_by(
        user_id=student_user.id).one().enrollment_status == "suspended"
    assert expire_lapsed_memberships(db) == 0  # idempotent


def test_grace_not_yet_expired_untouched(db, student_user, course):
    _, m = _setup(db, student_user, course, MembershipStatus.GRACE,
                  grace_until=datetime.now(timezone.utc) + timedelta(days=3))
    assert expire_lapsed_memberships(db) == 0
    db.refresh(m)
    assert m.status == MembershipStatus.GRACE


def test_cancelled_past_period_end_suspends_access(db, student_user, course):
    _, m = _setup(db, student_user, course, MembershipStatus.CANCELLED,
                  current_period_end=datetime.now(timezone.utc) - timedelta(days=1))
    assert expire_lapsed_memberships(db) == 1
    assert db.query(Enrollment).filter_by(
        user_id=student_user.id).one().enrollment_status == "suspended"


def test_catalog_sync_grants_new_course(db, student_user, course):
    course.post_status = "publish"  # all_access covers published paid courses
    db.commit()
    plan = MembershipPlan(name="All", all_access=True, period="monthly",
                          interval=1, price=9.0, razorpay_plan_id="plan_AA")
    db.add(plan)
    db.flush()
    m = Membership(user_id=student_user.id, plan_id=plan.id,
                   razorpay_subscription_id="sub_AA",
                   status=MembershipStatus.ACTIVE)
    db.add(m)
    db.commit()
    assert sync_membership_catalog(db) >= 1  # grants the existing paid course
    assert db.query(Enrollment).filter_by(user_id=student_user.id,
                                          course_id=course.id).count() == 1
    assert sync_membership_catalog(db) == 0  # then converges


def _pending(db, user, course, sub_id, age_hours):
    """A PENDING membership created `age_hours` ago."""
    plan = MembershipPlan(name="P", all_access=False, period="monthly",
                          interval=1, price=9.0,
                          razorpay_plan_id=f"plan_{sub_id}")
    db.add(plan)
    db.flush()
    db.add(MembershipPlanCourse(plan_id=plan.id, course_id=course.id))
    m = Membership(user_id=user.id, plan_id=plan.id,
                   razorpay_subscription_id=sub_id,
                   status=MembershipStatus.PENDING)
    db.add(m)
    db.commit()
    db.refresh(m)
    # server_default=now(); rewrite created_at to age the row.
    m.created_at = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    db.commit()
    db.refresh(m)
    return m


def test_stale_pending_is_cancelled(db, student_user, course):
    """An abandoned checkout (49h old) is discarded so the user can subscribe
    again; it never granted enrollments, so none are touched."""
    m = _pending(db, student_user, course, "sub_STALE", age_hours=49)
    assert expire_lapsed_memberships(db) == 1
    db.refresh(m)
    assert m.status == MembershipStatus.CANCELLED
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 0
    assert expire_lapsed_memberships(db) == 0  # idempotent


def test_fresh_pending_survives(db, student_user, course):
    """A checkout started an hour ago may still be confirmed by a webhook."""
    m = _pending(db, student_user, course, "sub_FRESH", age_hours=1)
    assert expire_lapsed_memberships(db) == 0
    db.refresh(m)
    assert m.status == MembershipStatus.PENDING


def test_cancel_resubscribe_keeps_access(db, student_user, course):
    """I1: after cancel -> resubscribe, the old membership's lapse-expiry pass
    must not suspend the new membership's access."""
    plan = MembershipPlan(name="T", all_access=False, period="monthly",
                          interval=1, price=9.0, razorpay_plan_id="plan_CR")
    db.add(plan)
    db.flush()
    db.add(MembershipPlanCourse(plan_id=plan.id, course_id=course.id))
    m1 = Membership(user_id=student_user.id, plan_id=plan.id,
                    razorpay_subscription_id="sub_CR1",
                    status=MembershipStatus.ACTIVE)
    db.add(m1)
    db.commit()
    db.refresh(m1)
    grant_membership_enrollments(db, m1)
    db.commit()

    # user cancels; the paid period has since elapsed
    m1.status = MembershipStatus.CANCELLED
    m1.current_period_end = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()

    # ...and immediately resubscribes
    m2 = Membership(user_id=student_user.id, plan_id=plan.id,
                    razorpay_subscription_id="sub_CR2",
                    status=MembershipStatus.ACTIVE)
    db.add(m2)
    db.commit()
    db.refresh(m2)
    # re-granting under m2 must take ownership of the row m1 still holds
    assert grant_membership_enrollments(db, m2) == 1
    db.commit()
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    assert row.membership_id == m2.id

    expire_lapsed_memberships(db)   # m1's pass: nothing left of its own
    db.refresh(row)
    assert row.enrollment_status == "enrolled"
    assert row.membership_id == m2.id
    db.refresh(m2)
    assert m2.status == MembershipStatus.ACTIVE


def test_expire_isolates_per_membership_failure(db, student_user, course,
                                                  monkeypatch):
    """One membership raising during suspend must not block the rest of
    the pass (regression for the missing fault isolation)."""
    import app.services.reconciliation as reconciliation

    other_user = _second_user(db)
    _, bad = _setup(db, student_user, course, MembershipStatus.GRACE,
                    grace_until=datetime.now(timezone.utc) - timedelta(days=1))
    good_plan = MembershipPlan(name="T2", all_access=False, period="monthly",
                               interval=1, price=9.0, razorpay_plan_id="plan_S2")
    db.add(good_plan)
    db.flush()
    db.add(MembershipPlanCourse(plan_id=good_plan.id, course_id=course.id))
    good = Membership(user_id=other_user.id, plan_id=good_plan.id,
                      razorpay_subscription_id="sub_S2",
                      status=MembershipStatus.GRACE,
                      grace_until=datetime.now(timezone.utc) - timedelta(days=1))
    db.add(good)
    db.commit()
    db.refresh(good)
    grant_membership_enrollments(db, good)
    db.commit()

    real_suspend = reconciliation.suspend_membership_enrollments

    def flaky_suspend(db, membership):
        if membership.id == bad.id:
            raise RuntimeError("boom")
        return real_suspend(db, membership)

    monkeypatch.setattr(reconciliation, "suspend_membership_enrollments", flaky_suspend)

    count = expire_lapsed_memberships(db)

    assert count == 1
    db.refresh(good)
    assert good.status == MembershipStatus.SUSPENDED
    assert db.query(Enrollment).filter_by(
        user_id=other_user.id).one().enrollment_status == "suspended"
