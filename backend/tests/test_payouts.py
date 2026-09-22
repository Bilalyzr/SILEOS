"""Contract tests for instructor withdrawals and the admin payout queue."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.course import Course
from app.models.payment import Order, OrderItem, OrderStatus, Withdrawal
from app.services.auth_service import AuthService
from app.services.payout_service import instructor_balance


@pytest.fixture
def act_as():
    """Exercise the real role guards without login approval/2FA setup noise."""
    from app.main import app

    def _set(user):
        app.dependency_overrides[AuthService.get_current_active_user] = lambda: user
        app.dependency_overrides[AuthService.require_instructor] = lambda: user
        app.dependency_overrides[AuthService.require_admin] = lambda: user
        return user

    yield _set
    app.dependency_overrides.pop(AuthService.get_current_active_user, None)
    app.dependency_overrides.pop(AuthService.require_instructor, None)
    app.dependency_overrides.pop(AuthService.require_admin, None)


def _sale(
    db,
    *,
    instructor,
    buyer,
    amount=1000,
    order_status=OrderStatus.COMPLETED,
    payment_method="razorpay",
):
    course = Course(
        post_author=instructor.id,
        post_title=f"Payout course {uuid4().hex[:8]}",
        post_status="publish",
        course_price_type="paid",
        course_price=amount,
    )
    db.add(course)
    db.flush()
    order = Order(
        user_id=buyer.id,
        order_key=f"payout-{uuid4().hex}",
        order_status=order_status,
        total_amount=amount,
        subtotal_amount=amount,
        payment_method=payment_method,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            course_id=course.id,
            order_item_name=course.post_title,
            subtotal=amount,
            total=amount,
        )
    )
    db.commit()
    return course, order


def test_balance_isolates_instructor_and_uses_real_completed_lines(db, make_user):
    instructor = make_user(role="instructor")
    other = make_user(role="instructor")
    buyer = make_user()
    _sale(db, instructor=instructor, buyer=buyer, amount=1250)
    _sale(db, instructor=other, buyer=buyer, amount=900)
    _sale(
        db,
        instructor=instructor,
        buyer=buyer,
        amount=700,
        payment_method="mock",
    )
    _sale(
        db,
        instructor=instructor,
        buyer=buyer,
        amount=600,
        order_status=OrderStatus.REFUNDED,
    )
    db.add_all(
        [
            Withdrawal(user_id=instructor.id, amount=200, status="pending"),
            Withdrawal(user_id=instructor.id, amount=100, status="approved"),
            Withdrawal(user_id=instructor.id, amount=50, status="paid"),
            Withdrawal(user_id=instructor.id, amount=75, status="rejected"),
        ]
    )
    db.commit()

    assert instructor_balance(db, instructor.id) == {
        "earned": 1250.0,
        "withdrawn_or_pending": 350.0,
        "available": 900.0,
    }
    assert instructor_balance(db, other.id)["earned"] == 900.0


def test_instructor_can_request_and_list_only_own_withdrawals(
    client, db, make_user, act_as
):
    instructor = make_user(role="instructor")
    other = make_user(role="instructor")
    buyer = make_user()
    _sale(db, instructor=instructor, buyer=buyer, amount=2000)
    db.add(Withdrawal(user_id=other.id, amount=500, status="pending"))
    db.commit()
    act_as(instructor)

    response = client.post(
        "/api/v1/instructor/withdrawals",
        json={"amount": 750, "method_data": {"type": "upi", "upi_id": "coach@upi"}},
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"
    assert response.json()["method_data"] == {"type": "upi", "upi_id": "coach@upi"}

    listing = client.get("/api/v1/instructor/withdrawals")
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert len(body["items"]) == 1
    assert body["balance"] == {
        "earned": 2000.0,
        "withdrawn_or_pending": 750.0,
        "available": 1250.0,
    }
    assert body["min_withdrawal_inr"] == 500


@pytest.mark.parametrize(
    "payload,expected_status",
    [
        ({"amount": 0, "method_data": {"type": "upi", "upi_id": "coach@upi"}}, 400),
        ({"amount": 499, "method_data": {"type": "upi", "upi_id": "coach@upi"}}, 400),
        ({"amount": 1001, "method_data": {"type": "upi", "upi_id": "coach@upi"}}, 400),
        ({"amount": 500, "method_data": {"type": "upi", "upi_id": "not-an-id"}}, 422),
        (
            {
                "amount": 500,
                "method_data": {
                    "type": "bank",
                    "account_holder": "Coach",
                    "account_number": "123",
                    "ifsc": "bad",
                },
            },
            422,
        ),
    ],
)
def test_request_rejects_invalid_amount_or_payment_method(
    client, db, make_user, act_as, payload, expected_status
):
    instructor = make_user(role="instructor")
    buyer = make_user()
    _sale(db, instructor=instructor, buyer=buyer, amount=1000)
    act_as(instructor)
    response = client.post(
        "/api/v1/instructor/withdrawals",
        json=payload,
    )
    assert response.status_code == expected_status, response.text


def test_bank_request_accepts_valid_strict_method(client, db, make_user, act_as):
    instructor = make_user(role="instructor")
    buyer = make_user()
    _sale(db, instructor=instructor, buyer=buyer, amount=1200)
    act_as(instructor)
    response = client.post(
        "/api/v1/instructor/withdrawals",
        json={
            "amount": 500,
            "method_data": {
                "type": "bank",
                "account_holder": "Course Coach",
                "account_number": "123456789012",
                "ifsc": "HDFC0001234",
                "bank_name": "HDFC",
            },
        },
    )
    assert response.status_code == 201, response.text


def test_admin_queue_enforces_transition_order_and_records_processing(
    client, db, make_user, act_as
):
    admin = make_user(role="admin")
    instructor = make_user(role="instructor")
    row = Withdrawal(
        user_id=instructor.id,
        amount=800,
        status="pending",
        method_data={"type": "upi", "upi_id": "teacher@upi"},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    act_as(admin)
    base = f"/api/v1/admin/withdrawals/{row.withdraw_id}"

    invalid = client.post(
        f"{base}/mark-paid", json={"paid_reference": "UTR-early"}
    )
    assert invalid.status_code == 409

    approved = client.post(f"{base}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["processed_by"] == admin.id
    assert approved.json()["processed_at"] is not None

    duplicate = client.post(f"{base}/approve")
    assert duplicate.status_code == 409
    paid = client.post(
        f"{base}/mark-paid", json={"paid_reference": "UTR-2026-0001"}
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["paid_reference"] == "UTR-2026-0001"


def test_admin_reject_releases_balance_and_queue_filters(
    client, db, make_user, act_as
):
    admin = make_user(role="admin")
    instructor = make_user(role="instructor")
    buyer = make_user()
    _sale(db, instructor=instructor, buyer=buyer, amount=1000)
    row = Withdrawal(user_id=instructor.id, amount=600, status="pending")
    db.add(row)
    db.commit()
    db.refresh(row)
    act_as(admin)

    rejected = client.post(
        f"/api/v1/admin/withdrawals/{row.withdraw_id}/reject",
        json={"reject_detail": "Bank details could not be verified"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert instructor_balance(db, instructor.id)["available"] == 1000.0

    queue = client.get("/api/v1/admin/withdrawals?status=rejected")
    assert queue.status_code == 200, queue.text
    assert [item["id"] for item in queue.json()] == [row.withdraw_id]
    assert client.get(
        "/api/v1/admin/withdrawals?status=unknown"
    ).status_code == 400


def test_withdrawal_endpoints_enforce_roles(make_user):
    student = make_user(role="student")
    instructor = make_user(role="instructor")
    with pytest.raises(HTTPException) as instructor_denied:
        AuthService.require_instructor(student)
    assert instructor_denied.value.status_code == 403
    with pytest.raises(HTTPException) as admin_denied:
        AuthService.require_admin(instructor)
    assert admin_denied.value.status_code == 403
