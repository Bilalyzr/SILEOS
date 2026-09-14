from app.models.membership import Membership, MembershipPlan, MembershipStatus


class FakeRzpAdmin:
    class plan:
        @staticmethod
        def create(payload):
            assert payload["period"] == "monthly"
            assert payload["item"]["amount"] == 99900  # paise
            return {"id": "plan_NEW1"}


def _patch(monkeypatch):
    import app.routers.memberships as mod
    monkeypatch.setattr(mod, "_rzp_client", lambda: FakeRzpAdmin)


def test_admin_creates_plan_with_razorpay(client, db, as_user, student_user, monkeypatch, course):
    _patch(monkeypatch)
    as_user(student_user)  # require_admin overridden by fixture
    r = client.post("/api/v1/admin/memberships/plans", json={
        "name": "Pro", "period": "monthly", "price": 999.0,
        "all_access": False, "course_ids": [course.id],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["razorpay_plan_id"] == "plan_NEW1"
    assert body["covered_courses"] == 1
    assert body["course_ids"] == [course.id]


def test_admin_plan_validation(client, as_user, student_user):
    as_user(student_user)
    r = client.post("/api/v1/admin/memberships/plans", json={
        "name": "Bad", "period": "hourly", "price": 10.0})
    assert r.status_code == 422


def test_admin_lists_members_and_health(client, db, as_user, student_user):
    plan = MembershipPlan(name="P", all_access=True, period="monthly",
                          interval=1, price=1.0, razorpay_plan_id="plan_H")
    db.add(plan)
    db.flush()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_H",
                      status=MembershipStatus.GRACE))
    db.commit()
    as_user(student_user)
    r = client.get("/api/v1/admin/memberships")
    assert r.status_code == 200 and r.json()[0]["status"] == "grace"
    r = client.get("/api/v1/admin/payment-health")
    assert r.status_code == 200
    assert r.json()["memberships"]["in_grace"] == 1
