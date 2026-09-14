from datetime import datetime, timedelta, timezone

from app.models.membership import (
    Membership, MembershipPlan, MembershipStatus,
)


def _plan(db, active=True):
    p = MembershipPlan(name="Pro", all_access=True, period="monthly",
                       interval=1, price=999.0, razorpay_plan_id="plan_API",
                       is_active=active)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _plan2(db):
    """A second, different tier."""
    p = MembershipPlan(name="Lite", all_access=True, period="monthly",
                       interval=1, price=99.0, razorpay_plan_id="plan_API2")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


class FakeRzp:
    created: list = []
    cancelled = None

    class subscription:
        @staticmethod
        def create(payload):
            assert payload["total_count"] == 100
            FakeRzp.created.append(payload)
            return {"id": f"sub_API{len(FakeRzp.created)}", "status": "created"}

        @staticmethod
        def cancel(sub_id, payload=None):
            FakeRzp.cancelled = (sub_id, payload)
            return {"id": sub_id, "status": "cancelled"}


def _patch_client(monkeypatch):
    FakeRzp.created = []
    FakeRzp.cancelled = None
    import app.routers.memberships as mod
    monkeypatch.setattr(mod, "_rzp_client", lambda: FakeRzp)
    monkeypatch.setattr(mod, "_rzp_key_id", lambda: "rzp_test_key")


def test_plans_lists_only_active(client, db):
    _plan(db)
    _plan_inactive = MembershipPlan(name="Old", all_access=True,
                                    period="monthly", interval=1, price=1.0,
                                    razorpay_plan_id="plan_OLD", is_active=False)
    db.add(_plan_inactive)
    db.commit()
    r = client.get("/api/v1/memberships/plans")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Pro" in names and "Old" not in names


def test_subscribe_creates_pending_membership(client, db, as_user, student_user, monkeypatch):
    plan = _plan(db)
    _patch_client(monkeypatch)
    as_user(student_user)
    r = client.post("/api/v1/memberships/subscribe", json={"plan_id": plan.id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["subscription_id"] == "sub_API1"
    m = db.query(Membership).filter_by(user_id=student_user.id).one()
    assert m.status == MembershipStatus.PENDING


def test_subscribe_conflict_when_already_member(client, db, as_user, student_user, monkeypatch):
    plan = _plan(db)
    _patch_client(monkeypatch)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_EXIST",
                      status=MembershipStatus.ACTIVE))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/memberships/subscribe", json={"plan_id": plan.id})
    assert r.status_code == 409


def test_me_and_cancel(client, db, as_user, student_user, monkeypatch):
    plan = _plan(db)
    _patch_client(monkeypatch)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_ME",
                      status=MembershipStatus.ACTIVE,
                      current_period_end=datetime.now(timezone.utc) + timedelta(days=9)))
    db.commit()
    as_user(student_user)
    r = client.get("/api/v1/memberships/me")
    assert r.status_code == 200 and r.json()["status"] == "active"
    r = client.post("/api/v1/memberships/cancel")
    assert r.status_code == 200
    assert FakeRzp.cancelled[0] == "sub_ME"
    assert FakeRzp.cancelled[1] == {"cancel_at_cycle_end": 1}
    m = db.query(Membership).filter_by(razorpay_subscription_id="sub_ME").one()
    assert m.cancel_at_period_end is True


def test_me_without_membership_404(client, as_user, student_user):
    as_user(student_user)
    assert client.get("/api/v1/memberships/me").status_code == 404


# ----- C1: an abandoned checkout must not block resubscribe forever -----

def test_subscribe_with_pending_same_plan_resumes_checkout(
        client, db, as_user, student_user, monkeypatch):
    """The user dismissed the Razorpay modal; hitting Subscribe again on the
    same tier hands back the SAME subscription id and creates no second row."""
    plan = _plan(db)
    _patch_client(monkeypatch)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_ABANDONED",
                      status=MembershipStatus.PENDING))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/memberships/subscribe", json={"plan_id": plan.id})
    assert r.status_code == 200, r.text
    assert r.json()["subscription_id"] == "sub_ABANDONED"
    assert FakeRzp.created == []          # no second gateway subscription
    assert db.query(Membership).filter_by(user_id=student_user.id).count() == 1


def test_subscribe_with_pending_different_plan_replaces_it(
        client, db, as_user, student_user, monkeypatch):
    plan = _plan(db)
    other = _plan2(db)
    _patch_client(monkeypatch)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_ABANDONED2",
                      status=MembershipStatus.PENDING))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/memberships/subscribe", json={"plan_id": other.id})
    assert r.status_code == 200, r.text
    assert r.json()["subscription_id"] == "sub_API1"   # a fresh subscription
    old = db.query(Membership).filter_by(
        razorpay_subscription_id="sub_ABANDONED2").one()
    assert old.status == MembershipStatus.CANCELLED    # discarded locally
    assert FakeRzp.cancelled is None                   # ...with no gateway call
    new = db.query(Membership).filter_by(
        razorpay_subscription_id="sub_API1").one()
    assert new.status == MembershipStatus.PENDING and new.plan_id == other.id


def test_subscribe_still_409s_on_grace(client, db, as_user, student_user,
                                       monkeypatch):
    plan = _plan(db)
    _patch_client(monkeypatch)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_GRACE",
                      status=MembershipStatus.GRACE))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/memberships/subscribe", json={"plan_id": plan.id})
    assert r.status_code == 409


# ----- I3: deterministic /cancel target -----

def _drop_blocking_index(db):
    """Legacy rows predating uq_memberships_one_blocking_per_user: a user can
    still hold both a stale PENDING and a live ACTIVE membership in a database
    that existed before the index was added (the migration is IF NOT EXISTS and
    instructs ops to de-duplicate). Selection must stay deterministic there."""
    from sqlalchemy import text
    db.execute(text("DROP INDEX IF EXISTS uq_memberships_one_blocking_per_user"))
    db.commit()


def test_cancel_prefers_active_over_pending(client, db, as_user, student_user,
                                            monkeypatch):
    plan = _plan(db)
    other = _plan2(db)
    _patch_client(monkeypatch)
    _drop_blocking_index(db)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_LIVE",
                      status=MembershipStatus.ACTIVE))
    db.add(Membership(user_id=student_user.id, plan_id=other.id,
                      razorpay_subscription_id="sub_STALE_PENDING",
                      status=MembershipStatus.PENDING))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/memberships/cancel")
    assert r.status_code == 200, r.text
    assert FakeRzp.cancelled[0] == "sub_LIVE"   # the ACTIVE one, not the PENDING
    live = db.query(Membership).filter_by(
        razorpay_subscription_id="sub_LIVE").one()
    assert live.cancel_at_period_end is True


def test_cancel_pending_only_skips_gateway(client, db, as_user, student_user,
                                           monkeypatch):
    plan = _plan(db)
    _patch_client(monkeypatch)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_ONLY_PENDING",
                      status=MembershipStatus.PENDING))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/memberships/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["message"] == "Pending membership discarded"
    assert FakeRzp.cancelled is None   # Razorpay rejects cancelling `created`
    m = db.query(Membership).filter_by(
        razorpay_subscription_id="sub_ONLY_PENDING").one()
    assert m.status == MembershipStatus.CANCELLED


def test_me_prefers_active_over_pending(client, db, as_user, student_user,
                                        monkeypatch):
    plan = _plan(db)
    other = _plan2(db)
    _patch_client(monkeypatch)
    _drop_blocking_index(db)
    db.add(Membership(user_id=student_user.id, plan_id=other.id,
                      razorpay_subscription_id="sub_ME_PENDING",
                      status=MembershipStatus.PENDING))
    db.commit()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_ME_ACTIVE",
                      status=MembershipStatus.ACTIVE))
    db.commit()
    as_user(student_user)
    r = client.get("/api/v1/memberships/me")
    assert r.status_code == 200
    assert r.json()["status"] == "active" and r.json()["plan_id"] == plan.id
