"""
Contract tests for the Pydantic request models on the money endpoints.

/create-order and /verify used to take `request: dict`, so malformed
payloads reached application code and produced 400/404 instead of a
clean 422 at the FastAPI validation boundary. These tests pin that
422 behavior.
"""


def test_create_order_rejects_missing_course_id(client, as_user, student_user):
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"coupon_code": "X"})
    assert r.status_code == 422


def test_create_order_rejects_non_int_course_id(client, as_user, student_user):
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"course_id": "abc"})
    assert r.status_code == 422


def test_verify_rejects_missing_fields(client, as_user, student_user):
    as_user(student_user)
    r = client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": "order_x", "course_id": 1},
    )
    assert r.status_code == 422


def test_verify_rejects_malformed_gateway_ids(client, as_user, student_user):
    as_user(student_user)
    r = client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": "not-an-order-id",
            "razorpay_payment_id": "pay_ok123",
            "razorpay_signature": "ab" * 32,
            "course_id": 1,
        },
    )
    assert r.status_code == 422
