"""R7 payments polish: coupons on memberships through a Razorpay Offer id
(admin links it, subscribe passes offer_id, everything else is refused
honestly), and the offer-id validation.
"""
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def admin_headers(make_user):
    from app.core.security import create_access_token
    a = make_user(role="admin", email="pp-admin@example.com")
    return {"Authorization": f"Bearer {create_access_token({'sub': str(a.id)})}"}


@pytest.fixture
def student_headers(student_user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}


@pytest.fixture
def coupon(db, make_user):
    from app.models.coupon import Coupon
    creator = make_user(role="admin", email="pp-creator@example.com")
    c = Coupon(code="MEMBER10", description="10 off", discount_type="percentage", discount_value=10, applicability="all_courses",
               valid_from=datetime.now(timezone.utc) - timedelta(days=1), valid_until=datetime.now(timezone.utc) + timedelta(days=30),
               created_by=creator.id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def plan(db):
    from app.models.membership import MembershipPlan
    p = MembershipPlan(name="Gold", description="", all_access=True, period="monthly", interval=1, price=499, grace_days=7,
                       razorpay_plan_id="plan_test123", is_active=True)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


class _FakeSub:
    def __init__(self):
        self.calls = []

    def create(self, body):
        self.calls.append(body)
        return {"id": "sub_fake001"}


class _FakeClient:
    def __init__(self):
        self.subscription = _FakeSub()


def test_admin_links_offer_with_validation(client, db, coupon, admin_headers, student_headers):
    assert client.patch(f"/api/v1/coupons/{coupon.id}/membership-offer", headers=student_headers, json={"razorpay_offer_id": "offer_ABCDEFGH1234"}).status_code == 403
    r = client.patch(f"/api/v1/coupons/{coupon.id}/membership-offer", headers=admin_headers, json={"razorpay_offer_id": "not-an-offer"})
    assert r.status_code == 422
    r = client.patch(f"/api/v1/coupons/{coupon.id}/membership-offer", headers=admin_headers, json={"razorpay_offer_id": "offer_ABCDEFGH1234"})
    assert r.status_code == 200 and r.json()["razorpay_offer_id"] == "offer_ABCDEFGH1234"
    db.refresh(coupon)
    assert coupon.razorpay_offer_id == "offer_ABCDEFGH1234"
    r = client.patch(f"/api/v1/coupons/{coupon.id}/membership-offer", headers=admin_headers, json={"razorpay_offer_id": ""})
    assert r.json()["razorpay_offer_id"] is None


def test_subscribe_passes_offer_only_for_linked_coupons(client, db, coupon, plan, student_headers, monkeypatch):
    from app.routers import memberships
    fake = _FakeClient()
    monkeypatch.setattr(memberships, "_rzp_client", lambda: fake)
    monkeypatch.setattr(memberships, "_rzp_key_id", lambda: "rzp_test_key")
    # coupon without an offer -> refused, no gateway call
    r = client.post("/api/v1/memberships/subscribe", headers=student_headers, json={"plan_id": plan.id, "coupon_code": "member10"})
    assert r.status_code == 422 and "not valid for memberships" in r.json()["detail"] and fake.subscription.calls == []
    coupon.razorpay_offer_id = "offer_ABCDEFGH1234"
    db.commit()
    r = client.post("/api/v1/memberships/subscribe", headers=student_headers, json={"plan_id": plan.id, "coupon_code": "member10"})
    assert r.status_code == 200, r.text
    assert r.json()["subscription_id"] == "sub_fake001"
    body = fake.subscription.calls[-1]
    assert body["offer_id"] == "offer_ABCDEFGH1234" and body["notes"]["coupon"] == "MEMBER10" and body["plan_id"] == "plan_test123"
