import pytest
from sqlalchemy.exc import IntegrityError

from app.models.membership import (
    Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
)
from app.models.enrollment import Enrollment


def test_plan_membership_roundtrip(db, student_user):
    plan = MembershipPlan(
        name="Pro", all_access=True, period="monthly", interval=1,
        price=999.0, razorpay_plan_id="plan_X1",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    assert plan.grace_days == 7 and plan.is_active is True

    m = Membership(
        user_id=student_user.id, plan_id=plan.id,
        razorpay_subscription_id="sub_X1",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    assert m.status == MembershipStatus.PENDING


def test_subscription_id_unique(db, student_user):
    plan = MembershipPlan(name="P", all_access=True, period="monthly",
                          interval=1, price=1.0, razorpay_plan_id="plan_U")
    db.add(plan)
    db.commit()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_dup"))
    db.commit()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_dup"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_one_blocking_membership_per_user(db, student_user):
    """uq_memberships_one_blocking_per_user closes the /subscribe race: two
    concurrent inserts can't both leave a blocking row behind."""
    plan = MembershipPlan(name="P", all_access=True, period="monthly",
                          interval=1, price=1.0, razorpay_plan_id="plan_B")
    db.add(plan)
    db.commit()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_block1",
                      status=MembershipStatus.ACTIVE))
    db.commit()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_block2",
                      status=MembershipStatus.PENDING))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_non_blocking_statuses_are_not_unique_per_user(db, student_user):
    """The index is partial: terminal rows may pile up (cancel, resubscribe,
    cancel again) alongside one live membership."""
    plan = MembershipPlan(name="P", all_access=True, period="monthly",
                          interval=1, price=1.0, razorpay_plan_id="plan_NB")
    db.add(plan)
    db.commit()
    for i, status in enumerate([MembershipStatus.CANCELLED,
                                MembershipStatus.CANCELLED,
                                MembershipStatus.SUSPENDED,
                                MembershipStatus.ACTIVE]):
        db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                          razorpay_subscription_id=f"sub_nb{i}", status=status))
    db.commit()
    assert db.query(Membership).filter_by(user_id=student_user.id).count() == 4


def test_enrollment_source_columns(db, student_user, course):
    e = Enrollment(course_id=course.id, user_id=student_user.id,
                   enrollment_source="membership")
    db.add(e)
    db.commit()
    db.refresh(e)
    assert e.enrollment_source == "membership"
    assert e.membership_id is None
