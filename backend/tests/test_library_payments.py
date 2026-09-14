"""Digital Library payment extension (plan Task 5).

`ebook_id` joins the exactly-one-of create-order/verify contract and all
THREE convergent fulfillment paths (browser /verify, the webhook inbox's
payment.captured handler, and the reconciliation sweeper) land on one
idempotent `fulfill_ebook_purchase` keyed on `Payment.gateway_payment_id`
— the same shape bundles use.

Gateway is mocked exactly like tests/test_bundle_checkout.py: `FakeOrders`
records the payload create built and echoes it back on fetch, so /verify
sees the real checkout-time notes (including the `ebook_price_inr` rupee
snapshot that is authoritative for the amount check).
"""
import hashlib
import hmac

import pytest

from app.models.ebook import Ebook, EbookGrant
from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderItem, Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus

from tests.test_library import (_admin_headers, _grant,
                                _make_approved_instructor, _make_ebook)


@pytest.fixture
def ebooks_root(tmp_path, monkeypatch):
    """Throwaway storage root (copy of test_library.ebooks_root — fixtures are
    module-scoped by definition site, so it can't simply be imported)."""
    from app.services import library_storage
    root = tmp_path / "ebooks"
    monkeypatch.setattr(library_storage, "EBOOKS_ROOT", root)
    return root


# ----- gateway double ---------------------------------------------------------

class FakeOrders:
    """Copy of test_bundle_checkout.FakeOrders — records the created payload
    and echoes it back on fetch, so verify sees exactly what create built."""
    last_payload = None

    class order:
        @staticmethod
        def create(payload):
            FakeOrders.last_payload = payload
            return {"id": "order_TEST1", "amount": payload["amount"],
                    "currency": "INR", "notes": payload["notes"]}

        @staticmethod
        def fetch(order_id):
            return {"id": order_id,
                    "amount": FakeOrders.last_payload["amount"],
                    "amount_paid": FakeOrders.last_payload["amount"],
                    "currency": "INR",
                    "notes": FakeOrders.last_payload["notes"]}


@pytest.fixture(autouse=True)
def _reset_fake_orders():
    """FakeOrders.last_payload is class state — a leak between tests would let
    one test's notes verify another's order."""
    FakeOrders.last_payload = None
    yield
    FakeOrders.last_payload = None


def _patch_gateway(monkeypatch):
    import app.routers.payments as pay
    monkeypatch.setattr(pay, "_razorpay_client", lambda: FakeOrders)
    monkeypatch.setattr(pay, "_razorpay_creds", lambda: ("rzp_key", "secret"))


def _signed_verify_body(ebook_id, payment_id="pay_TEST1", order_id="order_TEST1"):
    sig = hmac.new(b"secret", f"{order_id}|{payment_id}".encode(),
                   hashlib.sha256).hexdigest()
    return {"razorpay_order_id": order_id, "razorpay_payment_id": payment_id,
            "razorpay_signature": sig, "ebook_id": ebook_id}


# ============================================================================
# create-order
# ============================================================================

class TestEbookCheckout:
    def test_exactly_one_of_rejects_pairs(self, client, as_user, student_user):
        """The schema-level exactly-one-of validator 422s at the FastAPI
        validation boundary (test_payment_contracts.py pins that shape for the
        existing three targets; ebook_id joins it unchanged)."""
        as_user(student_user)
        for body in ({"course_id": 1, "ebook_id": 1},
                     {"bundle_id": 1, "ebook_id": 1},
                     {"invoice_id": 1, "ebook_id": 1},
                     {"course_id": 1, "bundle_id": 1, "ebook_id": 1}):
            assert client.post("/api/v1/payments/create-order",
                               json=body).status_code == 422
        # ...and on /verify too.
        sig = hmac.new(b"secret", b"order_X|pay_X", hashlib.sha256).hexdigest()
        r = client.post("/api/v1/payments/verify", json={
            "razorpay_order_id": "order_X", "razorpay_payment_id": "pay_X",
            "razorpay_signature": sig, "course_id": 1, "ebook_id": 1})
        assert r.status_code == 422

    def test_order_uses_server_price_and_snapshot(self, client, db, make_user,
                                                  as_user, student_user,
                                                  monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-a@lib.com")
        ebook = _make_ebook(db, owner, price=500, discount=350,
                            status="published", file_path="1/x.pdf")
        as_user(student_user)
        r = client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        assert r.status_code == 200, r.text
        assert FakeOrders.last_payload["amount"] == 35000  # discount honored, paise
        notes = FakeOrders.last_payload["notes"]
        assert notes["ebook_id"] == str(ebook.id)
        assert notes["user_id"] == str(student_user.id)
        assert notes["ebook_price_inr"] == "350"           # rupee snapshot
        # audit fields — list/discount recorded alongside the charged price
        assert notes["ebook_list_price_inr"] == "500"
        assert notes["ebook_discount_inr"] == "150"

    def test_order_no_discount_charges_list_price(self, client, db, make_user,
                                                  as_user, student_user,
                                                  monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-a2@lib.com")
        ebook = _make_ebook(db, owner, price=499, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        r = client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        assert r.status_code == 200, r.text
        assert FakeOrders.last_payload["amount"] == 49900
        notes = FakeOrders.last_payload["notes"]
        assert notes["ebook_price_inr"] == "499"
        assert notes["ebook_discount_inr"] == "0"

    def test_coupon_rejected_on_ebooks(self, client, db, make_user, as_user,
                                       student_user, monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-b@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        r = client.post("/api/v1/payments/create-order",
                        json={"ebook_id": ebook.id, "coupon_code": "X"})
        assert r.status_code == 400
        assert "coupon" in r.json()["detail"].lower()

    def test_draft_and_missing_ebook_404(self, client, db, make_user, as_user,
                                         student_user, monkeypatch):
        """Drafts are indistinguishable from "doesn't exist" to a non-owner —
        same posture as the Task 4 store/download gates, so unpublished
        inventory can't be probed through the checkout endpoint."""
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-c@lib.com")
        draft = _make_ebook(db, owner, title="Draft One", price=500)
        as_user(student_user)
        assert client.post("/api/v1/payments/create-order",
                           json={"ebook_id": draft.id}).status_code == 404
        assert client.post("/api/v1/payments/create-order",
                           json={"ebook_id": 999999}).status_code == 404

    def test_free_ebook_400_with_claim_guidance(self, client, db, make_user,
                                                as_user, student_user,
                                                monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-d@lib.com")
        free = _make_ebook(db, owner, title="Free One", price=0,
                           status="published", file_path="1/y.pdf")
        # "free" is the EFFECTIVE price: a discount-to-zero ebook is free too.
        disc_free = _make_ebook(db, owner, title="Disc Free", price=500,
                                discount=0, status="published",
                                file_path="1/z.pdf")
        as_user(student_user)
        for eb in (free, disc_free):
            r = client.post("/api/v1/payments/create-order", json={"ebook_id": eb.id})
            assert r.status_code == 400, r.text
            assert "claim" in r.json()["detail"].lower()
        # nothing reached the gateway
        assert FakeOrders.last_payload is None

    def test_already_owned_409(self, client, db, make_user, as_user,
                               student_user, monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-e@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        _grant(db, ebook, student_user)
        as_user(student_user)
        r = client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        assert r.status_code == 409, r.text
        assert "own" in r.json()["detail"].lower()


# ============================================================================
# /verify
# ============================================================================

class TestEbookVerify:
    def test_verify_grants_and_writes_money_trail(self, client, db, make_user,
                                                  as_user, student_user,
                                                  monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "vf-a@lib.com")
        ebook = _make_ebook(db, owner, price=500, discount=350,
                            status="published", file_path="1/x.pdf")
        as_user(student_user)
        assert client.post("/api/v1/payments/create-order",
                           json={"ebook_id": ebook.id}).status_code == 200
        r = client.post("/api/v1/payments/verify", json=_signed_verify_body(ebook.id))
        assert r.status_code == 200, r.text
        assert r.json()["success"] is True
        assert r.json()["cohort_id"] is None

        grant = db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                               user_id=student_user.id).one()
        assert grant.source == "purchase"
        assert grant.order_id is not None
        order = db.query(Order).filter(Order.id == grant.order_id).one()
        assert order.ebook_id == ebook.id
        assert float(order.total_amount) == 350.0          # rupees, discount price
        assert float(order.subtotal_amount) == 500.0       # list price
        assert float(order.discount_amount) == 150.0
        item = db.query(OrderItem).filter(OrderItem.order_id == order.id).one()
        assert item.ebook_id == ebook.id and item.course_id is None
        assert item.order_item_type == "ebook_item"
        assert float(item.total) == 350.0                  # rupees, not paise
        assert float(item.subtotal) == 500.0
        payment = db.query(Payment).filter(
            Payment.gateway_payment_id == "pay_TEST1").one()
        assert payment.order_id == order.id
        assert float(payment.amount) == 350.0
        assert payment.gateway_order_id == "order_TEST1"
        # no enrollment side effects — ebooks never touch enrollments
        assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 0

    def test_verify_replay_is_idempotent(self, client, db, make_user, as_user,
                                         student_user, monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "vf-b@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        body = _signed_verify_body(ebook.id)
        assert client.post("/api/v1/payments/verify", json=body).status_code == 200
        assert client.post("/api/v1/payments/verify", json=body).status_code == 200
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1
        assert db.query(Order).filter(Order.ebook_id == ebook.id).count() == 1
        assert db.query(OrderItem).filter(OrderItem.ebook_id == ebook.id).count() == 1
        assert db.query(Payment).filter_by(gateway_payment_id="pay_TEST1").count() == 1

    def test_verify_uses_notes_snapshot_when_price_changes(self, client, db,
                                                           make_user, as_user,
                                                           student_user,
                                                           monkeypatch):
        """A price edit between checkout and verify must not orphan a real
        capture: the ebook_price_inr SNAPSHOT is authoritative, and the Order
        records the snapshot price — not the new live one."""
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "vf-c@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        ebook.price_inr = 900          # raised AFTER checkout
        db.commit()
        assert client.post("/api/v1/payments/verify",
                           json=_signed_verify_body(ebook.id)).status_code == 200
        order = db.query(Order).filter(Order.ebook_id == ebook.id).one()
        assert float(order.total_amount) == 500.0     # the snapshot, not 900
        assert float(order.subtotal_amount) == 500.0
        item = db.query(OrderItem).filter(OrderItem.ebook_id == ebook.id).one()
        assert float(item.total) == 500.0

    def test_verify_wrong_amount_400_no_grant(self, client, db, make_user,
                                              as_user, student_user, monkeypatch):
        """The gateway reports a smaller capture than the snapshot demands →
        strict-equality reject, and NOTHING is written (so the webhook and
        sweeper stay armed for the real capture)."""
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "vf-d@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        FakeOrders.last_payload["amount"] = 100        # tampered downward
        r = client.post("/api/v1/payments/verify", json=_signed_verify_body(ebook.id))
        assert r.status_code == 400, r.text
        assert db.query(EbookGrant).count() == 0
        assert db.query(Order).count() == 0
        assert db.query(Payment).count() == 0

    def test_verify_bad_signature_400(self, client, db, make_user, as_user,
                                      student_user, monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "vf-e@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        body = _signed_verify_body(ebook.id)
        body["razorpay_signature"] = "0" * 64
        assert client.post("/api/v1/payments/verify", json=body).status_code == 400
        assert db.query(EbookGrant).count() == 0

    def test_verify_wrong_ebook_400_wrong_user_403(self, client, db, make_user,
                                                   as_user, student_user,
                                                   auth_headers, monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "vf-f@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        other = _make_ebook(db, owner, title="Other Book", price=500,
                            status="published", file_path="1/y.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        # notes say ebook.id → verifying against `other` must 400
        assert client.post("/api/v1/payments/verify",
                           json=_signed_verify_body(other.id)).status_code == 400
        assert db.query(EbookGrant).count() == 0

    def test_verify_other_user_cannot_redeem_signed_order(self, client, db,
                                                          make_user, as_user,
                                                          student_user,
                                                          auth_headers,
                                                          monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "vf-g@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        # A different real user presenting the same signed order: the notes'
        # user_id no longer matches → 403, nothing granted.
        thief = make_user(role="student", email="pay-thief@lib.com")
        as_user(thief)
        r = client.post("/api/v1/payments/verify", json=_signed_verify_body(ebook.id))
        assert r.status_code == 403, r.text
        assert db.query(EbookGrant).count() == 0

    def test_verify_unpublished_between_checkout_and_verify_still_fulfills(
            self, client, db, make_user, as_user, student_user, monkeypatch):
        """The buyer already paid — an unpublish must never strand the capture,
        and the grant survives (spec §4: unpublish never touches grants)."""
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "vf-h@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        ebook.status = "draft"
        db.commit()
        assert client.post("/api/v1/payments/verify",
                           json=_signed_verify_body(ebook.id)).status_code == 200
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1

    def test_verify_deleted_ebook_writes_money_and_alerts_no_grant(
            self, client, db, make_user, as_user, student_user, monkeypatch):
        """Delete is 409-blocked once any grant exists, but a capture can race
        a pre-first-sale delete. The Order+Payment are still written (the
        capture stays reconcilable), a human is paged, and no grant appears."""
        from app.services.email_service import EmailService
        _patch_gateway(monkeypatch)
        alerts = []
        monkeypatch.setattr(EmailService, "send_payment_alert",
                            staticmethod(lambda subj, body: alerts.append(subj)))
        owner = _make_approved_instructor(db, make_user, "vf-i@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        ebook_id = ebook.id
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook_id})
        db.delete(ebook)
        db.commit()
        r = client.post("/api/v1/payments/verify", json=_signed_verify_body(ebook_id))
        assert r.status_code == 200, r.text
        assert db.query(Payment).filter_by(gateway_payment_id="pay_TEST1").count() == 1
        order = db.query(Order).one()
        assert float(order.total_amount) == 500.0
        assert db.query(EbookGrant).count() == 0
        assert alerts, "a human must be paged for an ungrantable capture"

    def test_buyer_can_download_end_to_end(self, client, db, make_user, as_user,
                                           student_user, monkeypatch,
                                           ebooks_root):
        """POST /verify → GET /download 200 with the real bytes."""
        blob = b"%PDF-1.4\nreal ebook bytes\n"
        target = ebooks_root / "1"
        target.mkdir(parents=True, exist_ok=True)
        (target / "book.pdf").write_bytes(blob)

        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "e2e@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/book.pdf")
        as_user(student_user)
        # before purchase: no grant → 403
        assert client.get(f"/api/v1/library/{ebook.id}/download").status_code == 403
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        assert client.post("/api/v1/payments/verify",
                           json=_signed_verify_body(ebook.id)).status_code == 200
        r = client.get(f"/api/v1/library/{ebook.id}/download")
        assert r.status_code == 200, r.text
        assert r.content == blob


# ============================================================================
# fulfill_ebook_purchase (the one convergence point)
# ============================================================================

class TestEbookFulfillment:
    def test_fulfill_is_idempotent_on_gateway_payment_id(self, db, make_user):
        from app.services.fulfillment_service import fulfill_ebook_purchase
        owner = _make_approved_instructor(db, make_user, "ff-a@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        for _ in range(2):  # duplicate gateway_payment_id → one grant, one order
            result = fulfill_ebook_purchase(
                db, user=student, ebook_id=ebook.id,
                razorpay_order_id="order_FF1", razorpay_payment_id="pay_FF1",
                paid_amount=500.0)
            db.commit()
        assert result.created_order is False               # second call was a replay
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1
        assert db.query(Payment).filter_by(gateway_payment_id="pay_FF1").count() == 1
        assert db.query(Order).count() == 1
        assert db.query(OrderItem).count() == 1

    def test_fulfill_never_touches_enrollments(self, db, make_user):
        from app.services.fulfillment_service import fulfill_ebook_purchase
        owner = _make_approved_instructor(db, make_user, "ff-e@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf", course_id=None)
        fulfill_ebook_purchase(db, user=student, ebook_id=ebook.id,
                               razorpay_order_id="order_FFE",
                               razorpay_payment_id="pay_FFE", paid_amount=500.0)
        db.commit()
        assert db.query(Enrollment).count() == 0

    def test_fulfill_missing_ebook_writes_money_and_alerts(self, db, make_user,
                                                           monkeypatch):
        from app.services import fulfillment_service
        from app.services.email_service import EmailService
        alerts = []
        monkeypatch.setattr(EmailService, "send_payment_alert",
                            staticmethod(lambda subj, body: alerts.append(subj)))
        student = make_user(role="student")
        result = fulfillment_service.fulfill_ebook_purchase(
            db, user=student, ebook_id=999999,
            razorpay_order_id="order_FF2", razorpay_payment_id="pay_FF2",
            paid_amount=350.0)
        db.commit()
        assert result.created_order is True                 # capture stays reconcilable
        assert db.query(Payment).filter_by(gateway_payment_id="pay_FF2").count() == 1
        assert db.query(EbookGrant).count() == 0            # nothing grantable
        assert db.query(OrderItem).count() == 0             # no line for a ghost product
        order = db.query(Order).one()
        assert order.ebook_id is None
        assert float(order.total_amount) == 350.0
        assert alerts                                        # human paged

    def test_fulfill_missing_ebook_replay_alerts_once_and_writes_once(
            self, db, make_user, monkeypatch):
        """A webhook/sweeper replay of an ungrantable capture must not page a
        human again or write a second money trail."""
        from app.services import fulfillment_service
        from app.services.email_service import EmailService
        alerts = []
        monkeypatch.setattr(EmailService, "send_payment_alert",
                            staticmethod(lambda subj, body: alerts.append(subj)))
        student = make_user(role="student")
        for _ in range(2):
            fulfillment_service.fulfill_ebook_purchase(
                db, user=student, ebook_id=999999,
                razorpay_order_id="order_FF2B", razorpay_payment_id="pay_FF2B",
                paid_amount=350.0)
            db.commit()
        assert db.query(Payment).filter_by(gateway_payment_id="pay_FF2B").count() == 1
        assert db.query(Order).count() == 1
        assert len(alerts) == 1

    def test_fulfill_stamps_order_id_on_prior_free_claim(self, db, make_user):
        """A free-claim row later purchased keeps ONE row, now tied to the
        money trail (grant_ebook stamps NULL order_id)."""
        from app.services.fulfillment_service import fulfill_ebook_purchase
        owner = _make_approved_instructor(db, make_user, "ff-b@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        _grant(db, ebook, student, order_id=None, source="purchase")
        fulfill_ebook_purchase(db, user=student, ebook_id=ebook.id,
                               razorpay_order_id="order_FF3",
                               razorpay_payment_id="pay_FF3", paid_amount=500.0)
        db.commit()
        grant = db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                               user_id=student.id).one()
        assert grant.order_id is not None

    def test_fulfill_never_rewrites_source_on_existing_grant(self, db, make_user):
        from app.services.fulfillment_service import fulfill_ebook_purchase
        owner = _make_approved_instructor(db, make_user, "ff-c@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        _grant(db, ebook, student, order_id=None, source="admin")
        fulfill_ebook_purchase(db, user=student, ebook_id=ebook.id,
                               razorpay_order_id="order_FF4",
                               razorpay_payment_id="pay_FF4", paid_amount=500.0)
        db.commit()
        grant = db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                               user_id=student.id).one()
        assert grant.source == "admin"      # never rewritten
        assert grant.order_id is not None   # but the money trail is stamped

    def test_fulfill_replay_self_heals_missing_grant(self, db, make_user):
        """A replay against an existing order re-creates a grant that was
        somehow lost — the grant is deliberately not gated on created_order
        (bundle posture)."""
        from app.services.fulfillment_service import fulfill_ebook_purchase
        owner = _make_approved_instructor(db, make_user, "ff-d@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        fulfill_ebook_purchase(db, user=student, ebook_id=ebook.id,
                               razorpay_order_id="order_FF5",
                               razorpay_payment_id="pay_FF5", paid_amount=500.0)
        db.commit()
        db.query(EbookGrant).delete()
        db.commit()
        result = fulfill_ebook_purchase(db, user=student, ebook_id=ebook.id,
                                        razorpay_order_id="order_FF5",
                                        razorpay_payment_id="pay_FF5",
                                        paid_amount=500.0)
        db.commit()
        assert result.created_order is False
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1
        assert db.query(Order).count() == 1

    def test_paid_amount_below_list_records_the_discount(self, db, make_user):
        from app.services.fulfillment_service import fulfill_ebook_purchase
        owner = _make_approved_instructor(db, make_user, "ff-f@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=500, discount=350,
                            status="published", file_path="1/x.pdf")
        fulfill_ebook_purchase(db, user=student, ebook_id=ebook.id,
                               razorpay_order_id="order_FF6",
                               razorpay_payment_id="pay_FF6", paid_amount=350.0,
                               list_price_inr=500)
        db.commit()
        order = db.query(Order).one()
        assert float(order.subtotal_amount) == 500.0
        assert float(order.discount_amount) == 150.0
        assert float(order.total_amount) == 350.0


# ============================================================================
# webhook + sweeper convergence — identical rows to /verify
# ============================================================================

def _captured_event(db, user, ebook_id, *, amount_paise=50000,
                    pay_id="pay_WEB1", event_id="evt_eb1",
                    snapshot="500", notes_extra=None):
    notes = {"ebook_id": str(ebook_id), "user_id": str(user.id),
             "ebook_price_inr": snapshot}
    notes.update(notes_extra or {})
    ev = WebhookEvent(
        event_id=event_id, event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": pay_id, "order_id": "order_WEB1", "amount": amount_paise,
            "currency": "INR", "notes": notes,
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()
    return ev


class FakeRzpClient:
    """Sweeper double — mirrors test_bundle_webhooks.FakeRzpClient."""
    def __init__(self, orders, payments_by_order):
        self._orders = orders
        self._pbo = payments_by_order
        self.order = self

    def all(self, opts):
        return {"items": self._orders}

    def payments(self, order_id):
        return {"items": self._pbo.get(order_id, [])}


class TestEbookWebhookAndSweeper:
    def test_webhook_fulfills_ebook(self, db, make_user, student_user):
        from app.services.webhook_processor import process_webhook_event
        owner = _make_approved_instructor(db, make_user, "wh-a@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        ev = _captured_event(db, student_user, ebook.id)
        process_webhook_event(db, ev)
        assert ev.status == WebhookEventStatus.PROCESSED, ev.last_error
        assert db.query(Payment).filter_by(gateway_payment_id="pay_WEB1").count() == 1
        grant = db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                               user_id=student_user.id).one()
        assert grant.source == "purchase" and grant.order_id is not None
        order = db.query(Order).filter(Order.ebook_id == ebook.id).one()
        assert float(order.total_amount) == 500.0
        item = db.query(OrderItem).filter(OrderItem.order_id == order.id).one()
        assert item.order_item_type == "ebook_item"
        assert item.course_id is None and item.ebook_id == ebook.id
        assert db.query(Enrollment).count() == 0

    def test_webhook_matches_verify_rows_exactly(self, client, db, make_user,
                                                 as_user, student_user,
                                                 monkeypatch):
        """Convergence: whichever path lands first, the rows are the same."""
        from app.services.webhook_processor import process_webhook_event
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "wh-b@lib.com")
        ebook = _make_ebook(db, owner, price=500, discount=350,
                            status="published", file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        client.post("/api/v1/payments/verify", json=_signed_verify_body(ebook.id))
        verify_order = db.query(Order).filter(Order.ebook_id == ebook.id).one()
        verify_shape = (float(verify_order.subtotal_amount),
                        float(verify_order.discount_amount),
                        float(verify_order.total_amount),
                        verify_order.payment_method)

        # Same capture arriving via the webhook is a no-op...
        ev = _captured_event(db, student_user, ebook.id, amount_paise=35000,
                             pay_id="pay_TEST1", event_id="evt_dup",
                             snapshot="350")
        process_webhook_event(db, ev)
        assert db.query(Order).filter(Order.ebook_id == ebook.id).count() == 1
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1

        # ...and a webhook-first capture for another buyer produces the same shape.
        buyer2 = make_user(role="student", email="wh-b2@lib.com")
        ev2 = _captured_event(db, buyer2, ebook.id, amount_paise=35000,
                              pay_id="pay_WEB2", event_id="evt_web2",
                              snapshot="350")
        process_webhook_event(db, ev2)
        assert ev2.status == WebhookEventStatus.PROCESSED, ev2.last_error
        web_order = db.query(Order).filter(Order.user_id == buyer2.id).one()
        assert (float(web_order.subtotal_amount), float(web_order.discount_amount),
                float(web_order.total_amount), web_order.payment_method) == verify_shape

    def test_webhook_duplicate_delivery_noop(self, db, make_user, student_user):
        from app.services.webhook_processor import process_webhook_event
        owner = _make_approved_instructor(db, make_user, "wh-c@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        process_webhook_event(db, _captured_event(db, student_user, ebook.id,
                                                  event_id="evt_c1"))
        process_webhook_event(db, _captured_event(db, student_user, ebook.id,
                                                  event_id="evt_c2"))
        assert db.query(Payment).count() == 1
        assert db.query(Order).count() == 1
        assert db.query(EbookGrant).count() == 1

    def test_webhook_bad_user_unrecoverable(self, db, make_user):
        from app.services.webhook_processor import process_webhook_event
        owner = _make_approved_instructor(db, make_user, "wh-d@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        ev = WebhookEvent(
            event_id="evt_baduser", event_type="payment.captured",
            payload={"payload": {"payment": {"entity": {
                "id": "pay_BADU", "order_id": "order_BADU", "amount": 50000,
                "currency": "INR",
                "notes": {"ebook_id": str(ebook.id), "user_id": "999999",
                          "ebook_price_inr": "500"},
            }}}}, signature_valid=True)
        db.add(ev)
        db.commit()
        process_webhook_event(db, ev)
        assert ev.status == WebhookEventStatus.FAILED
        assert ev.attempts == 5              # retries exhausted, not retried forever
        assert db.query(Payment).count() == 0

    def test_webhook_unusable_ebook_note_unrecoverable(self, db, make_user,
                                                       student_user):
        from app.services.webhook_processor import process_webhook_event
        ev = WebhookEvent(
            event_id="evt_badnote", event_type="payment.captured",
            payload={"payload": {"payment": {"entity": {
                "id": "pay_BADN", "order_id": "order_BADN", "amount": 50000,
                "currency": "INR",
                "notes": {"ebook_id": "not-an-int",
                          "user_id": str(student_user.id)},
            }}}}, signature_valid=True)
        db.add(ev)
        db.commit()
        process_webhook_event(db, ev)
        assert ev.status == WebhookEventStatus.FAILED
        assert db.query(Payment).count() == 0

    def test_webhook_notes_from_gateway_order_fallback(self, db, monkeypatch,
                                                       make_user, student_user):
        """Payment-entity notes can be empty while the ORDER carries them —
        the ebook branch must re-check the fallback's order notes too."""
        from app.services import webhook_processor as wp
        from app.services.webhook_processor import process_webhook_event

        owner = _make_approved_instructor(db, make_user, "wh-e@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")

        class _FakeOrderApi:
            def __init__(self, notes):
                self._notes = notes

            def fetch(self, order_id):
                return {"id": order_id, "notes": self._notes}

        class _FakeClient:
            def __init__(self, notes):
                self.order = _FakeOrderApi(notes)

        monkeypatch.setattr(wp, "_gateway_client", lambda: _FakeClient(
            {"ebook_id": str(ebook.id), "user_id": str(student_user.id),
             "ebook_price_inr": "500"}))

        ev = WebhookEvent(
            event_id="evt_eb_fallback", event_type="payment.captured",
            payload={"payload": {"payment": {"entity": {
                "id": "pay_EB_FALLBACK", "order_id": "order_EB_FALLBACK",
                "amount": 50000, "currency": "INR", "notes": {},
            }}}}, signature_valid=True)
        db.add(ev)
        db.commit()
        process_webhook_event(db, ev)
        assert ev.status == WebhookEventStatus.PROCESSED, ev.last_error
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1

    def test_sweeper_fulfills_orphan_ebook_capture(self, db, make_user,
                                                   student_user):
        from app.services.reconciliation import reconcile_gateway_orders
        owner = _make_approved_instructor(db, make_user, "sw-a@lib.com")
        ebook = _make_ebook(db, owner, price=500, discount=350,
                            status="published", file_path="1/x.pdf")
        client = FakeRzpClient(
            orders=[{"id": "order_GE1", "status": "paid", "amount": 35000,
                     "notes": {"ebook_id": str(ebook.id),
                               "user_id": str(student_user.id),
                               "ebook_price_inr": "350"}}],
            payments_by_order={"order_GE1": [
                {"id": "pay_GE1", "status": "captured", "amount": 35000,
                 "currency": "INR"}]})
        assert reconcile_gateway_orders(db, client) == 1
        grant = db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                               user_id=student_user.id).one()
        assert grant.order_id is not None
        order = db.query(Order).filter(Order.ebook_id == ebook.id).one()
        assert float(order.total_amount) == 350.0
        assert float(order.subtotal_amount) == 500.0
        item = db.query(OrderItem).filter(OrderItem.order_id == order.id).one()
        assert item.order_item_type == "ebook_item" and item.course_id is None
        assert db.query(Enrollment).count() == 0
        # second sweep is a no-op
        assert reconcile_gateway_orders(db, client) == 0
        assert db.query(Order).count() == 1

    def test_sweeper_alerts_on_unusable_ebook_notes(self, db, make_user,
                                                    monkeypatch):
        from app.services import reconciliation
        from app.services.reconciliation import reconcile_gateway_orders
        alerts = []
        monkeypatch.setattr(reconciliation.EmailService, "send_payment_alert",
                            staticmethod(lambda s, b: alerts.append(s)))
        client = FakeRzpClient(
            orders=[{"id": "order_GE2", "status": "paid", "amount": 35000,
                     "notes": {"ebook_id": "abc", "user_id": "1"}}],
            payments_by_order={"order_GE2": [
                {"id": "pay_GE2", "status": "captured", "amount": 35000,
                 "currency": "INR"}]})
        assert reconcile_gateway_orders(db, client) == 0
        assert alerts
        assert db.query(Payment).count() == 0

    def test_sweeper_alerts_when_user_missing(self, db, make_user, monkeypatch):
        from app.services import reconciliation
        from app.services.reconciliation import reconcile_gateway_orders
        alerts = []
        monkeypatch.setattr(reconciliation.EmailService, "send_payment_alert",
                            staticmethod(lambda s, b: alerts.append(s)))
        owner = _make_approved_instructor(db, make_user, "sw-c@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        client = FakeRzpClient(
            orders=[{"id": "order_GE3", "status": "paid", "amount": 50000,
                     "notes": {"ebook_id": str(ebook.id), "user_id": "999999",
                               "ebook_price_inr": "500"}}],
            payments_by_order={"order_GE3": [
                {"id": "pay_GE3", "status": "captured", "amount": 50000,
                 "currency": "INR"}]})
        assert reconcile_gateway_orders(db, client) == 0
        assert alerts
        assert db.query(EbookGrant).count() == 0


# ============================================================================
# revenue reporting: an ebook line must not read as "Course #None"
# ============================================================================

class TestAdminRevenueBreakdownWithEbooks:
    def test_course_breakdown_labels_ebook_lines(self, client, db, make_user,
                                                 auth_headers, student_user,
                                                 monkeypatch):
        """admin.py's course_breakdown loop keys on OrderItem.course_id, which
        is NULL for an ebook line — unfixed it renders 'Course #None'."""
        from app.services.fulfillment_service import fulfill_ebook_purchase

        owner = _make_approved_instructor(db, make_user, "rev-eb@lib.com")
        admin = make_user(role="admin", email="rev-admin@lib.com")
        ebook = _make_ebook(db, owner, title="Study Guide", price=500,
                            status="published", file_path="1/x.pdf")
        fulfill_ebook_purchase(db, user=student_user, ebook_id=ebook.id,
                               razorpay_order_id="order_REV1",
                               razorpay_payment_id="pay_REV1",
                               paid_amount=500.0)
        db.commit()

        headers = _admin_headers(client, db, admin)
        r = client.get("/api/v1/admin/revenue", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        titles = [str(t) for t in _iter_titles(body)]
        assert titles, body
        assert not any("Course #None" in t for t in titles), titles
        assert any("Study Guide" in t or "Ebook" in t for t in titles), titles


def _iter_titles(body):
    """Pull every course_title out of whatever shape /admin/revenue returns."""
    def walk(node):
        if isinstance(node, dict):
            if "course_title" in node:
                yield node["course_title"]
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)
    return list(walk(body))
