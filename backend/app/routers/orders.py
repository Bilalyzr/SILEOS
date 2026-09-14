"""
Orders Router - Simple checkout endpoint for cart functionality
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.payment import Payment, Order, OrderItem, OrderStatus, PaymentStatus
from app.models.coupon import CouponUsage
from app.services.auth_service import AuthService
from app.services.coupon_service import (
    CouponError,
    validate_and_compute,
)
from app.services.pricing import effective_course_price
from app.core.business_verticals import revenue_metadata
from pydantic import BaseModel

router = APIRouter()

class OrderCreate(BaseModel):
    course_ids: List[int]
    coupon_code: str = None

class OrderItemResponse(BaseModel):
    course_id: int
    price_at_purchase: float

class OrderResponse(BaseModel):
    id: int
    total_amount: float
    discount_amount: float = 0
    status: str
    created_at: datetime
    items: List[OrderItemResponse]
    coupon_code: str = None

    class Config:
        from_attributes = True

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create order and enroll student in courses (mock payment)
    """
    if not order_data.course_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No courses selected"
        )

    total_amount = 0
    order_items = []

    # Process each course
    for course_id in order_data.course_ids:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course with ID {course_id} not found"
            )
        if course.post_status not in ("publish", "published"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course with ID {course_id} is not published",
            )

        # Check if already enrolled
        existing_enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == current_user.id
        ).first()

        if existing_enrollment:
            continue  # Skip if already enrolled

        # Add to total. Routed through the shared pricing authority
        # (app.services.pricing) so this matches the direct Razorpay
        # checkout path exactly. NOTE: this is a stricter rule than the
        # previous inline check here, which accepted `sale_price >= price`
        # (so a sale price entered above list price incorrectly won). The
        # authority requires `0 < sale_price < price` — see
        # tests/test_sale_price_pricing.py for the pinned behavior change.
        price = float(effective_course_price(course))
        total_amount += price

        order_items.append({
            "course_id": course.id,
            "price_at_purchase": price
        })

    if not order_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in all selected courses"
        )

    # Cart-level codes are Coupons only. Referral/voucher codes map one learner
    # to one course/cohort and therefore belong to the direct course checkout.
    coupon = None
    discount_amount = 0

    if order_data.coupon_code:
        try:
            result = validate_and_compute(
                db,
                code=order_data.coupon_code,
                user_id=current_user.id,
                course_ids=[item["course_id"] for item in order_items],
                total_amount=total_amount,
            )
        except CouponError as exc:
            raise HTTPException(status_code=400, detail=exc.message)
        coupon = result.coupon
        discount_amount = float(result.discount_amount)

    final_amount = total_amount - discount_amount

    # This endpoint completes the order without ever contacting a payment
    # gateway (payment_method="mock" below). That is only acceptable when
    # nothing is actually owed — otherwise it hands out paid courses for free
    # while writing COMPLETED Order/Payment rows that reported revenue then
    # counted as money received.
    #
    # Paid carts must go through Razorpay. There is no multi-course gateway
    # flow yet, so reject them here rather than enroll for free; the
    # single-course path (/payments/create-order -> /payments/verify) works.
    if float(final_amount) > 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "Cart checkout cannot process paid orders yet. "
                "Please purchase these courses individually from the course page."
            ),
        )

    # Allocate the order-level discount across the line items, pro-rata by list
    # price, so the OrderItem totals sum to Order.total_amount. Per-course
    # revenue reporting reads these line totals; leaving them at list price made
    # every coupon order reconcile to more than the customer actually paid. The
    # last line absorbs any rounding remainder so the sum is exact.
    line_totals: list[float] = []
    allocated = 0.0
    for idx, item in enumerate(order_items):
        if idx == len(order_items) - 1:
            line_total = float(final_amount) - allocated
        else:
            share = (
                float(item["price_at_purchase"]) / float(total_amount)
                if total_amount
                else 0.0
            )
            line_total = round(float(final_amount) * share, 2)
            allocated += line_total
        line_totals.append(max(line_total, 0.0))

    # Create order
    order_key = f"ORDER_{uuid.uuid4().hex[:12].upper()}"
    order = Order(
        user_id=current_user.id,
        order_key=order_key,
        total_amount=final_amount,
        subtotal_amount=total_amount,
        discount_amount=discount_amount,
        order_status=OrderStatus.COMPLETED,  # Mock payment - instant completion
        payment_method="mock",
        payment_method_title="Mock Payment",
        transaction_id=f"MOCK_{uuid.uuid4().hex[:12].upper()}",
        date_paid=datetime.now(),
        date_completed=datetime.now()
    )

    db.add(order)
    db.flush()  # Get order ID

    # Create order items
    for idx, item in enumerate(order_items):
        course = db.query(Course).filter(Course.id == item["course_id"]).first()
        order_item = OrderItem(
            order_id=order.id,
            course_id=item["course_id"],
            order_item_name=course.post_title if course else f"Course {item['course_id']}",
            order_item_type="line_item",
            quantity=1,
            subtotal=float(item["price_at_purchase"]),  # list price
            total=line_totals[idx],                     # after coupon discount
            product_data=revenue_metadata(course.course_type) if course else {},
        )
        db.add(order_item)

    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        order_id=order.id,
        payment_method="mock",
        gateway_transaction_id=f"MOCK_TXN_{uuid.uuid4().hex[:12].upper()}",
        gateway_payment_id=f"MOCK_PAY_{uuid.uuid4().hex[:12].upper()}",
        gateway_order_id=order_key,
        amount=float(final_amount),
        currency="INR",
        payment_status=PaymentStatus.COMPLETED,
        processed_date=datetime.now()
    )

    db.add(payment)

    # Record coupon usage if coupon was applied
    if coupon:
        coupon_usage = CouponUsage(
            coupon_id=coupon.id,
            user_id=current_user.id,
            order_id=order.id,
            discount_amount=discount_amount
        )
        db.add(coupon_usage)

        # Increment coupon usage count
        coupon.usage_count = (coupon.usage_count or 0) + 1

    # Enroll student in all courses. Cohort/referral assignment is purposely
    # reserved for the single-course checkout where it is unambiguous.
    for item in order_items:
        enrollment = Enrollment(
            course_id=item["course_id"],
            user_id=current_user.id,
            order_id=order.id,
            enrollment_status="enrolled",
            cohort_id=None,
        )
        db.add(enrollment)

        # Update course enrollment count
        course = db.query(Course).filter(Course.id == item["course_id"]).first()
        if course:
            course.total_enrollments = (course.total_enrollments or 0) + 1

    db.commit()
    db.refresh(order)

    # Send order confirmation email with invoice
    try:
        from app.services.email_service import EmailService

        # Prepare order items for email
        email_items = []
        for item in order_items:
            course = db.query(Course).filter(Course.id == item["course_id"]).first()
            email_items.append({
                "title": course.post_title if course else f"Course {item['course_id']}",
                "price": float(item["price_at_purchase"])
            })

        # Send email
        EmailService.send_order_confirmation(
            customer_email=current_user.email,
            customer_name=current_user.display_name or current_user.email,
            order_id=order.id,
            order_items=email_items,
            total_amount=float(final_amount),
            transaction_id=order.transaction_id
        )
    except Exception as e:
        # Log error but don't fail the order
        print(f"Failed to send order confirmation email: {e}")

    return {
        "id": order.id,
        "total_amount": final_amount,
        "discount_amount": discount_amount,
        "status": "completed",
        "created_at": order.created_at,
        "items": order_items,
        "coupon_code": order_data.coupon_code if coupon else None
    }

@router.get("/me")
async def get_my_orders(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db)
):
    """The caller's own orders as explicit dicts (spec §1 UI — student
    "My Orders").

    Previously this returned raw ORM rows, which serialized every column on
    Order — billing_*, transaction_id, ip_address and friends. The shape below
    is a closed allow-list: never billing columns, never the admin's refund
    reason. `refunded_at` is the only refund detail a student sees.
    """
    orders = (db.query(Order)
              .options(joinedload(Order.order_items), joinedload(Order.payments))
              .filter(Order.user_id == current_user.id)
              .order_by(Order.created_at.desc()).all())
    out = []
    for o in orders:
        status = o.order_status.value if hasattr(o.order_status, "value") else str(o.order_status or "")
        refunded_at = None
        for p in o.payments:
            if p.refund_processed_at is not None:
                refunded_at = p.refund_processed_at
                break
        out.append({
            "id": o.id,
            "order_key": o.order_key,
            "status": status,
            "total_amount": float(o.total_amount or 0),
            "discount_amount": float(o.discount_amount or 0),
            "currency": o.currency or "INR",
            "payment_method": o.payment_method or "",
            "created_at": o.created_at,
            "refunded_at": refunded_at,
            "items": [
                {"course_id": it.course_id, "title": it.order_item_name, "total": float(it.total or 0)}
                for it in o.order_items
            ],
        })
    return out
