from datetime import datetime, timedelta, timezone

from app.models.enrollment import Enrollment
from app.models.membership import (
    Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
)
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.webhook_processor import process_webhook_event


def _plan(db, course_ids):
    plan = MembershipPlan(name="T", all_access=False, period="monthly",
                          interval=1, price=999.0, razorpay_plan_id="plan_W")
    db.add(plan)
    db.flush()
    for cid in course_ids:
        db.add(MembershipPlanCourse(plan_id=plan.id, course_id=cid))
    db.commit()
    return plan


def _membership(db, user, plan, **kw):
    m = Membership(user_id=user.id, plan_id=plan.id,
                   razorpay_subscription_id="sub_W1", **kw)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _sub_event(db, event_type, sub_id="sub_W1", event_id=None, current_end=None,
               payment=None):
    entity = {"id": sub_id, "status": event_type.split(".")[1]}
    if current_end is not None:
        entity["current_end"] = current_end
    payload = {"entity": "event", "event": event_type,
               "payload": {"subscription": {"entity": entity}}}
    if payment:
        payload["payload"]["payment"] = {"entity": payment}
    ev = WebhookEvent(event_id=event_id or f"evt_{event_type}_{sub_id}",
                      event_type=event_type, payload=payload,
                      signature_valid=True)
    db.add(ev)
    db.commit()
    return ev


def test_activated_grants_and_sets_period(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan)
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    ev = _sub_event(db, "subscription.activated", current_end=end)
    process_webhook_event(db, ev)
    db.refresh(m)
    assert ev.status == WebhookEventStatus.PROCESSED
    assert m.status == MembershipStatus.ACTIVE
    assert m.current_period_end is not None
    assert db.query(Enrollment).filter_by(user_id=student_user.id,
                                          course_id=course.id).count() == 1


def test_charged_recovers_from_grace(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan, status=MembershipStatus.GRACE,
                    grace_until=datetime.now(timezone.utc))
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    ev = _sub_event(db, "subscription.charged", current_end=end,
                    payment={"id": "pay_SUB1", "amount": 99900,
                             "currency": "INR", "subscription_id": "sub_W1"})
    process_webhook_event(db, ev)
    db.refresh(m)
    assert m.status == MembershipStatus.ACTIVE
    assert m.grace_until is None


def test_charged_records_payment_row_idempotently(db, student_user, course):
    plan = _plan(db, [course.id])
    _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    pay = {"id": "pay_SUB2", "amount": 99900, "currency": "INR",
           "subscription_id": "sub_W1"}
    process_webhook_event(db, _sub_event(db, "subscription.charged",
                                         event_id="evt_c1", current_end=end,
                                         payment=pay))
    process_webhook_event(db, _sub_event(db, "subscription.charged",
                                         event_id="evt_c2", current_end=end,
                                         payment=pay))
    assert db.query(Payment).filter_by(gateway_payment_id="pay_SUB2").count() == 1


def test_halted_starts_grace_keeps_access(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    from app.services.membership_access import grant_membership_enrollments
    grant_membership_enrollments(db, m)
    db.commit()
    process_webhook_event(db, _sub_event(db, "subscription.halted"))
    db.refresh(m)
    assert m.status == MembershipStatus.GRACE
    assert m.grace_until is not None
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    assert row.enrollment_status == "enrolled"  # access kept during grace


def test_halted_honours_zero_grace_days(db, student_user, course):
    """grace_days=0 means no grace at all — `or 7` used to silently grant a
    week of free access on a tier that deliberately has none."""
    plan = MembershipPlan(name="NoGrace", all_access=False, period="monthly",
                          interval=1, price=999.0, razorpay_plan_id="plan_NG",
                          grace_days=0)
    db.add(plan)
    db.flush()
    db.add(MembershipPlanCourse(plan_id=plan.id, course_id=course.id))
    db.commit()
    m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    process_webhook_event(db, _sub_event(db, "subscription.halted"))
    db.refresh(m)
    assert m.status == MembershipStatus.GRACE
    grace_until = m.grace_until
    if grace_until.tzinfo is None:
        grace_until = grace_until.replace(tzinfo=timezone.utc)
    delta = abs((grace_until - datetime.now(timezone.utc)).total_seconds())
    assert delta < 60, f"grace_until should be ~now, got {m.grace_until}"


def test_halted_uses_configured_grace_days(db, student_user, course):
    plan = MembershipPlan(name="ThreeDay", all_access=False, period="monthly",
                          interval=1, price=999.0, razorpay_plan_id="plan_3D",
                          grace_days=3)
    db.add(plan)
    db.flush()
    db.add(MembershipPlanCourse(plan_id=plan.id, course_id=course.id))
    db.commit()
    m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    process_webhook_event(db, _sub_event(db, "subscription.halted"))
    db.refresh(m)
    grace_until = m.grace_until
    if grace_until.tzinfo is None:
        grace_until = grace_until.replace(tzinfo=timezone.utc)
    days = (grace_until - datetime.now(timezone.utc)).total_seconds() / 86400
    assert 2.9 < days < 3.1


def test_cancelled_marks_cancelled_keeps_access(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE,
                    current_period_end=datetime.now(timezone.utc) + timedelta(days=10))
    process_webhook_event(db, _sub_event(db, "subscription.cancelled"))
    db.refresh(m)
    assert m.status == MembershipStatus.CANCELLED


def test_unknown_subscription_id_is_unrecoverable(db):
    ev = _sub_event(db, "subscription.activated", sub_id="sub_GHOST",
                    event_id="evt_ghost")
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.FAILED
    assert ev.attempts == 5  # unrecoverable exhausts retries


def test_captured_with_subscription_id_not_unrecoverable(db, student_user, course):
    plan = _plan(db, [course.id])
    _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    ev = WebhookEvent(
        event_id="evt_subcap", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_SUB3", "amount": 99900, "currency": "INR",
            "subscription_id": "sub_W1", "notes": {},
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Payment).filter_by(gateway_payment_id="pay_SUB3").count() == 1


def test_pending_does_not_change_current_period_end(db, student_user, course):
    plan = _plan(db, [course.id])
    original_end = datetime.now(timezone.utc) + timedelta(days=5)
    m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE,
                    current_period_end=original_end)
    future_end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    process_webhook_event(db, _sub_event(db, "subscription.pending",
                                         current_end=future_end))
    db.refresh(m)
    assert m.status == MembershipStatus.ACTIVE
    # current_period_end must be untouched — pending is "recorded only".
    # SQLite drops tzinfo on round-trip, so compare naive UTC values.
    stored_end = m.current_period_end
    if stored_end.tzinfo is None:
        stored_end = stored_end.replace(tzinfo=timezone.utc)
    assert abs((stored_end - original_end).total_seconds()) < 1


def test_charged_after_cancelled_stays_cancelled_but_records_payment(
        db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    from app.services.membership_access import (
        grant_membership_enrollments, suspend_membership_enrollments,
    )
    grant_membership_enrollments(db, m)
    db.commit()
    m.status = MembershipStatus.CANCELLED
    suspend_membership_enrollments(db, m)
    db.commit()

    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    pay = {"id": "pay_SUB_LATE", "amount": 99900, "currency": "INR",
           "subscription_id": "sub_W1"}
    process_webhook_event(db, _sub_event(db, "subscription.charged",
                                         current_end=end, payment=pay))
    db.refresh(m)
    assert m.status == MembershipStatus.CANCELLED
    row = db.query(Enrollment).filter_by(user_id=student_user.id,
                                         course_id=course.id).one()
    assert row.enrollment_status == "suspended"  # not re-granted
    assert db.query(Payment).filter_by(
        gateway_payment_id="pay_SUB_LATE").count() == 1  # revenue still recorded


def test_activated_after_completed_stays_completed(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan, status=MembershipStatus.COMPLETED)
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    process_webhook_event(db, _sub_event(db, "subscription.activated",
                                         current_end=end))
    db.refresh(m)
    assert m.status == MembershipStatus.COMPLETED
