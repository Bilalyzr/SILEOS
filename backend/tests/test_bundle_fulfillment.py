"""
Tests for `fulfill_bundle_purchase` in app.services.fulfillment_service.

NOTE: the task brief's test helper imports `_make_user` from
`tests.conftest`, but no such helper exists there (conftest only exposes
the `make_user` fixture factory, not a standalone importable function).
So `_second_course` below inlines a local user-factory instead of
importing `_make_user`.
"""
from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderItem, Payment


from app.services.fulfillment_service import fulfill_bundle_purchase


def _make_user(db, login):
    """Local inline user-factory (replaces the brief's `tests.conftest._make_user`,
    which does not exist in this repo's conftest)."""
    from app.models.user import User
    u = User(
        user_login=login,
        user_pass="x",
        user_nicename=login,
        user_email=f"{login}@example.com",
        display_name=login,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _second_course(db, price=300.0, title="Course B"):
    from app.models.course import Course
    author = _make_user(db, f"instr_{title.replace(' ', '_')}")
    c = Course(post_author=author.id, post_title=title,
               course_price_type="paid", course_price=price,
               post_status="publish")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _fulfill(db, user, ids, pay_id="pay_BF1", amount=700.0):
    return fulfill_bundle_purchase(
        db, user=user, bundle_id=1, course_ids=ids,
        razorpay_order_id="order_BF1", razorpay_payment_id=pay_id,
        paid_amount=amount)


def test_grants_all_courses_and_money_trail(db, student_user, course):
    c2 = _second_course(db)  # course=500, c2=300, combined 800, paid 700
    res = _fulfill(db, student_user, [course.id, c2.id])
    db.commit()
    assert res.created_order and res.is_new_enrollment
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 2
    order = db.query(Order).one()
    assert float(order.total_amount) == 700.0
    assert order.bundle_id == 1
    items = db.query(OrderItem).filter_by(order_id=order.id).all()
    assert len(items) == 2
    assert abs(sum(float(i.total) for i in items) - 700.0) < 0.001
    rows = db.query(Enrollment).all()
    assert all(r.enrollment_source == "bundle" and r.order_id == order.id
               for r in rows)


def test_replay_is_noop(db, student_user, course):
    c2 = _second_course(db)
    _fulfill(db, student_user, [course.id, c2.id])
    db.commit()
    res2 = _fulfill(db, student_user, [course.id, c2.id])
    db.commit()
    assert not res2.created_order
    assert db.query(Order).count() == 1
    assert db.query(Enrollment).count() == 2


def test_owned_course_untouched_others_granted(db, student_user, course):
    c2 = _second_course(db)
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="enrolled"))
    db.commit()
    res = _fulfill(db, student_user, [course.id, c2.id])
    db.commit()
    owned = db.query(Enrollment).filter_by(course_id=course.id).one()
    assert owned.enrollment_source is None       # source never rewritten
    assert owned.enrollment_status == "enrolled"  # already enrolled: unchanged
    # An enrolled row with a NULL order_id still gets stamped — harmless and
    # correct: the buyer really did pay for it, and the stamp only ever adds
    # protection from membership suspension.
    assert owned.order_id == res.order_id
    granted = db.query(Enrollment).filter_by(course_id=c2.id).one()
    assert granted.enrollment_source == "bundle"


def test_suspended_membership_row_rescued_by_bundle(db, student_user, course):
    """C1: a lapsed membership row (suspended, order_id NULL) is what the
    create-order guard lets the user pay for — fulfillment must rescue it,
    not skip it, or they pay and stay locked out."""
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="suspended",
                      enrollment_source="membership"))
    db.commit()

    res = _fulfill(db, student_user, [course.id])
    db.commit()

    row = db.query(Enrollment).filter_by(course_id=course.id).one()
    assert row.enrollment_status == "enrolled"
    assert row.order_id == res.order_id       # purchase-exempt from now on
    assert row.enrollment_source == "membership"  # source never rewritten
    assert res.is_new_enrollment              # access genuinely changed


def test_rescued_membership_row_survives_lapse_sweeper(db, student_user, course):
    """The load-bearing half of C1: once the bundle purchase stamps order_id,
    a later membership lapse-expiry pass must NOT re-suspend the row."""
    from datetime import datetime, timedelta, timezone

    from app.models.membership import (
        Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
    )
    from app.services.membership_access import (
        grant_membership_enrollments, suspend_membership_enrollments,
    )
    from app.services.reconciliation import expire_lapsed_memberships

    plan = MembershipPlan(name="T", all_access=False, period="monthly",
                          interval=1, price=9.0, razorpay_plan_id="plan_RESCUE")
    db.add(plan)
    db.flush()
    db.add(MembershipPlanCourse(plan_id=plan.id, course_id=course.id))
    m = Membership(user_id=student_user.id, plan_id=plan.id,
                   razorpay_subscription_id="sub_RESCUE",
                   status=MembershipStatus.GRACE,
                   grace_until=datetime.now(timezone.utc) - timedelta(days=1))
    db.add(m)
    db.commit()
    db.refresh(m)
    grant_membership_enrollments(db, m)
    db.commit()

    # membership lapses -> row suspended
    assert suspend_membership_enrollments(db, m) == 1
    db.commit()
    row = db.query(Enrollment).filter_by(course_id=course.id).one()
    assert row.enrollment_status == "suspended"

    # ...user buys a bundle containing that course
    _fulfill(db, student_user, [course.id])
    db.commit()
    db.refresh(row)
    assert row.enrollment_status == "enrolled"
    assert row.order_id is not None

    # a later lapse-expiry pass must leave it alone (order_id exempts it)
    expire_lapsed_memberships(db)
    assert suspend_membership_enrollments(db, m) == 0
    db.commit()
    db.refresh(row)
    assert row.enrollment_status == "enrolled"


def test_rescue_does_not_double_bump_total_enrollments(db, student_user, course):
    """A rescued row already counted toward total_enrollments."""
    from app.models.course import Course

    course.total_enrollments = 1
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="suspended",
                      enrollment_source="membership"))
    db.commit()

    _fulfill(db, student_user, [course.id])
    db.commit()

    assert db.query(Course).filter_by(id=course.id).one().total_enrollments == 1
    assert db.query(Enrollment).filter_by(course_id=course.id).count() == 1


def test_all_courses_missing_alerts_and_keeps_money_trail(db, student_user,
                                                          monkeypatch):
    """Related upgrade 1: when the whole snapshot is unresolvable the capture
    is still recorded (money moved) but an operational alert is raised."""
    import app.services.email_service as email_mod

    captured = []
    monkeypatch.setattr(
        email_mod.EmailService, "send_payment_alert",
        staticmethod(lambda subject, body: captured.append((subject, body)) or True),
    )

    res = _fulfill(db, student_user, [999998, 999999])
    db.commit()

    assert captured and "no resolvable courses" in captured[0][0]
    assert res.created_order and not res.is_new_enrollment
    assert db.query(Order).count() == 1
    assert db.query(Payment).count() == 1
    assert db.query(OrderItem).count() == 0
    assert db.query(Enrollment).count() == 0


def test_missing_course_skipped(db, student_user, course):
    res = _fulfill(db, student_user, [course.id, 999999])
    db.commit()
    assert db.query(Enrollment).count() == 1
    assert db.query(OrderItem).count() == 1


def test_duplicate_course_id_deduped(db, student_user, course):
    """course_ids with a duplicate (e.g. parsed from an order-notes string,
    or a bundle with no unique (bundle_id, course_id) constraint) must not
    produce duplicate OrderItems/Enrollments or double-bump total_enrollments."""
    from app.models.course import Course

    c2 = _second_course(db)  # course=500, c2=300
    _fulfill(db, student_user, [course.id, course.id, c2.id])
    db.commit()

    items = db.query(OrderItem).all()
    assert len(items) == 2
    assert abs(sum(float(i.total) for i in items) - 700.0) < 0.001

    enrollments = db.query(Enrollment).all()
    assert len(enrollments) == 2
    assert {e.course_id for e in enrollments} == {course.id, c2.id}

    refreshed = db.query(Course).filter_by(id=course.id).one()
    assert refreshed.total_enrollments == 1
