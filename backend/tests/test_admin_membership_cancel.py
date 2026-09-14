"""Admin cancel-subscription + shared helper
(docs/superpowers/specs/2026-09-04-money-ops-design.md §2).

Gateway mocked exactly like tests/test_membership_api.py (FakeRzp at
app.routers.memberships._rzp_client).
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enrollment import Enrollment
from app.models.membership import Membership, MembershipPlan, MembershipStatus


class FakeRzp:
    cancelled: list = []
    fail = False

    class subscription:
        @staticmethod
        def cancel(sub_id, payload=None):
            if FakeRzp.fail:
                raise RuntimeError("gateway down")
            FakeRzp.cancelled.append((sub_id, payload))
            return {"id": sub_id, "status": "cancelled"}


@pytest.fixture()
def rzp(monkeypatch):
    FakeRzp.cancelled = []
    FakeRzp.fail = False
    import app.routers.memberships as mod
    monkeypatch.setattr(mod, "_rzp_client", lambda: FakeRzp)
    return FakeRzp


def _plan(db):
    p = MembershipPlan(name="Pro", all_access=True, period="monthly", interval=1,
                       price=999.0, razorpay_plan_id="plan_ADM")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _membership(db, user, plan, status=MembershipStatus.ACTIVE, sub_id="sub_ADM"):
    m = Membership(user_id=user.id, plan_id=plan.id, razorpay_subscription_id=sub_id,
                   status=status,
                   current_period_end=datetime.now(timezone.utc) + timedelta(days=9))
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _membership_row(db, user, course, m, order_id=None):
    e = Enrollment(user_id=user.id, course_id=course.id, enrollment_status="enrolled",
                   enrollment_source="membership", membership_id=m.id, order_id=order_id)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


BODY_END = {"immediate": False, "reason": "Chargeback received"}
BODY_NOW = {"immediate": True, "reason": "Fraudulent account"}


def test_admin_cancel_at_period_end(client, db, rzp, as_user, student_user, course):
    plan = _plan(db)
    m = _membership(db, student_user, plan)
    row = _membership_row(db, student_user, course, m)
    as_user(student_user)  # require_admin overridden by fixture
    r = client.post(f"/api/v1/admin/memberships/{m.id}/cancel", json=BODY_END)
    assert r.status_code == 200, r.text
    assert rzp.cancelled == [("sub_ADM", {"cancel_at_cycle_end": 1})]
    db.refresh(m)
    db.refresh(row)
    assert m.status == MembershipStatus.ACTIVE            # access until period end
    assert m.cancel_at_period_end is True
    assert row.enrollment_status == "enrolled"
    assert r.json()["cancel_at_period_end"] is True


def test_admin_cancel_immediate_suspends_materialized_rows(client, db, rzp, as_user,
                                                           student_user, course):
    plan = _plan(db)
    m = _membership(db, student_user, plan)
    row = _membership_row(db, student_user, course, m)
    # a purchased row (order_id set) must NEVER be suspended by a cancel
    from app.models.payment import Order, OrderStatus
    o = Order(user_id=student_user.id, order_key="RZP_KEEP", order_status=OrderStatus.COMPLETED,
              total_amount=100)
    db.add(o)
    db.flush()
    from tests.test_refunds import _second_course
    c2 = _second_course(db, title="Bought")
    bought = Enrollment(user_id=student_user.id, course_id=c2.id, enrollment_status="enrolled",
                        enrollment_source="membership", membership_id=m.id, order_id=o.id)
    db.add(bought)
    db.commit()

    as_user(student_user)
    r = client.post(f"/api/v1/admin/memberships/{m.id}/cancel", json=BODY_NOW)
    assert r.status_code == 200, r.text
    assert rzp.cancelled == [("sub_ADM", {"cancel_at_cycle_end": 0})]
    db.refresh(m)
    db.refresh(row)
    db.refresh(bought)
    assert m.status == MembershipStatus.CANCELLED
    assert row.enrollment_status == "suspended"
    assert bought.enrollment_status == "enrolled"        # order_id exempts it
    assert r.json()["status"] == "cancelled"


def test_admin_cancel_gateway_failure_502_changes_nothing(client, db, rzp, as_user,
                                                          student_user, course):
    rzp.fail = True
    plan = _plan(db)
    m = _membership(db, student_user, plan)
    row = _membership_row(db, student_user, course, m)
    as_user(student_user)
    r = client.post(f"/api/v1/admin/memberships/{m.id}/cancel", json=BODY_NOW)
    assert r.status_code == 502
    db.refresh(m)
    db.refresh(row)
    assert m.status == MembershipStatus.ACTIVE
    assert m.cancel_at_period_end is False
    assert row.enrollment_status == "enrolled"


def test_admin_cancel_pending_discards_locally_without_gateway(client, db, rzp, as_user,
                                                               student_user):
    plan = _plan(db)
    m = _membership(db, student_user, plan, status=MembershipStatus.PENDING)
    as_user(student_user)
    r = client.post(f"/api/v1/admin/memberships/{m.id}/cancel", json=BODY_END)
    assert r.status_code == 200, r.text
    assert rzp.cancelled == []
    db.refresh(m)
    assert m.status == MembershipStatus.CANCELLED


def test_admin_cancel_period_end_rerun_is_idempotent(client, db, rzp, as_user, student_user):
    plan = _plan(db)
    m = _membership(db, student_user, plan)
    as_user(student_user)
    assert client.post(f"/api/v1/admin/memberships/{m.id}/cancel",
                       json=BODY_END).status_code == 200
    r = client.post(f"/api/v1/admin/memberships/{m.id}/cancel", json=BODY_END)
    assert r.status_code == 200
    assert len(rzp.cancelled) == 1                        # no second gateway call
    assert r.json()["cancel_at_period_end"] is True


def test_admin_cancel_immediate_rerun_on_cancelled_is_idempotent(client, db, rzp, as_user,
                                                                 student_user, course):
    """An immediate cancel that already landed re-runs as a 200 no-op: the
    membership is already CANCELLED and Razorpay must not be called again."""
    plan = _plan(db)
    m = _membership(db, student_user, plan)
    row = _membership_row(db, student_user, course, m)
    as_user(student_user)
    assert client.post(f"/api/v1/admin/memberships/{m.id}/cancel",
                       json=BODY_NOW).status_code == 200
    r = client.post(f"/api/v1/admin/memberships/{m.id}/cancel", json=BODY_NOW)
    assert r.status_code == 200, r.text
    assert len(rzp.cancelled) == 1                        # no second gateway call
    db.refresh(m)
    db.refresh(row)
    assert m.status == MembershipStatus.CANCELLED
    assert row.enrollment_status == "suspended"
    assert r.json()["status"] == "cancelled"


def test_admin_cancel_unknown_404_and_reason_required(client, db, rzp, as_user, student_user):
    plan = _plan(db)
    m = _membership(db, student_user, plan)
    as_user(student_user)
    assert client.post("/api/v1/admin/memberships/999999/cancel",
                       json=BODY_END).status_code == 404
    assert client.post(f"/api/v1/admin/memberships/{m.id}/cancel",
                       json={"immediate": True, "reason": ""}).status_code == 422


def test_admin_cancel_requires_admin(client, db, rzp, make_user, auth_headers,
                                     student_user, course):
    """A logged-in student cannot cancel someone's membership."""
    plan = _plan(db)
    m = _membership(db, student_user, plan)
    row = _membership_row(db, student_user, course, m)
    stu = make_user(role="student")
    r = client.post(f"/api/v1/admin/memberships/{m.id}/cancel", json=BODY_NOW,
                    headers=auth_headers(stu.user_email, stu._test_password))
    assert r.status_code == 403
    assert rzp.cancelled == []
    db.refresh(m)
    db.refresh(row)
    assert m.status == MembershipStatus.ACTIVE
    assert row.enrollment_status == "enrolled"


def test_self_service_cancel_still_uses_period_end_semantics(client, db, rzp, as_user,
                                                            student_user):
    """Regression guard for the extraction — mirrors
    tests/test_membership_api.py::test_me_and_cancel."""
    plan = _plan(db)
    m = _membership(db, student_user, plan)
    as_user(student_user)
    r = client.post("/api/v1/memberships/cancel")
    assert r.status_code == 200
    assert rzp.cancelled == [("sub_ADM", {"cancel_at_cycle_end": 1})]
    db.refresh(m)
    assert m.cancel_at_period_end is True and m.status == MembershipStatus.ACTIVE


def test_self_service_cancel_pending_discards_without_gateway(client, db, rzp, as_user,
                                                              student_user):
    """Regression guard: the PENDING discard branch keeps its own message."""
    plan = _plan(db)
    m = _membership(db, student_user, plan, status=MembershipStatus.PENDING)
    as_user(student_user)
    r = client.post("/api/v1/memberships/cancel")
    assert r.status_code == 200
    assert r.json()["message"] == "Pending membership discarded"
    assert rzp.cancelled == []
    db.refresh(m)
    assert m.status == MembershipStatus.CANCELLED
