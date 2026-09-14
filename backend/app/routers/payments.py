"""
Payment Router - SashaInfinity LMS

Handles Razorpay order creation and payment verification.

/create-order and /verify accept EXACTLY ONE target — `course_id`,
`bundle_id`, `invoice_id` or `ebook_id` (enforced by the
`_exactly_one_target` model validator in schemas/payment.py; 422 otherwise).
Each target has its own branch function below and its own idempotent
fulfillment write, all keyed on `Payment.gateway_payment_id`. Coupons apply
to courses only — bundles, invoices and ebooks reject them with a 400.

Hardened against client-supplied amount tampering: the server always computes
the amount from the course's server-side price — via
`app.services.pricing.effective_course_price`, which charges
`course.course_sale_price` when it is a valid sale (`0 < sale < price`) and
`course.course_price` otherwise — and verifies it against the captured
order on the Razorpay side before granting enrollment. Order notes carry
both `list_price` and `sale_price` for audit visibility only; /verify always
RECOMPUTES the expected amount from the DB via the pricing authority rather
than trusting the notes.

Paid courses NEVER bypass Razorpay. A ReferralCode applied at checkout just
maps the user to the cohort AFTER successful Razorpay verify — it does not
reduce the order amount. A discount Coupon reduces the order amount on the
server before the Razorpay order is created.

Removed in 2026-04 cleanup (these handlers referenced non-existent model
columns — `Payment.student_id`, `Payment.status`, an unimported `Transaction`
class — and would 500 on every call; none were called by the frontend):
    - /create-payment-intent, /confirm-payment
    - /transactions, /earnings
    - /refund
Re-add them only after wiring them to the real Payment / Order schema.
/webhook (below) is the durable-inbox endpoint; the older /proxy/webhook in
payments_proxy.py is Edgyy-scoped and being migrated separately.
"""

import hashlib
import hmac
import json
import logging
import uuid

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.course import Course
from app.models.coupon import Coupon
from app.models.enrollment import Enrollment
from app.models.cohort import Cohort
from app.models.user import User
from app.models.webhook_event import WebhookEvent
from app.schemas.payment import (
    CreateOrderRequest,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.coupon_service import (
    CouponError,
    resolve_checkout_code,
    validate_and_compute,
)
from app.services.fulfillment_service import (
    fulfill_bundle_purchase,
    fulfill_cart_purchase,
    fulfill_course_purchase,
)
from app.services.cart_checkout import (
    CartSnapshotError,
    build_cart_snapshot,
    canonical_course_ids,
    parse_cart_notes,
)
from app.services.pricing import effective_course_price, resolve_expected_purchase
from app.services.webhook_processor import process_webhook_event
from app.services.invoice_service import settle_invoice

logger = logging.getLogger(__name__)

router = APIRouter()


def _clean_cred(value: str) -> str:
    """Drop unfilled `.env` placeholders like `<new_key_id>` so they cannot
    shadow a real credential in the fallback chain below."""
    value = (value or "").strip()
    if value.startswith("<") and value.endswith(">"):
        return ""
    return value


def _razorpay_creds() -> tuple[str, str]:
    """Resolve Razorpay credentials. Accepts either env var pair for
    backwards compatibility (RAZORPAY_KEY/SECRET is canonical; the older
    RAZORPAY_KEY_ID/SECRET pair is honored as a fallback)."""
    settings = get_settings()
    key_id = _clean_cred(settings.RAZORPAY_KEY) or _clean_cred(settings.RAZORPAY_KEY_ID)
    key_secret = _clean_cred(settings.RAZORPAY_SECRET) or _clean_cred(
        settings.RAZORPAY_KEY_SECRET
    )
    return key_id, key_secret


def _razorpay_client() -> razorpay.Client:
    key_id, key_secret = _razorpay_creds()
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured",
        )
    return razorpay.Client(auth=(key_id, key_secret))


async def _create_cart_order(request, db, current_user):
    """Create one immutable Razorpay order for up to ten courses."""
    try:
        requested_ids = canonical_course_ids(request.course_ids or [])
    except CartSnapshotError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    courses = db.query(Course).filter(Course.id.in_(requested_ids)).all()
    by_id = {course.id: course for course in courses}
    missing = [course_id for course_id in requested_ids if course_id not in by_id]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Courses not found: {', '.join(map(str, missing))}",
        )
    unavailable = [
        course.id for course in courses
        if course.post_status not in ("publish", "published")
    ]
    if unavailable:
        raise HTTPException(
            status_code=400,
            detail=f"Courses are not available for enrollment: {', '.join(map(str, unavailable))}",
        )

    owned = {
        row.course_id for row in db.query(Enrollment).filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id.in_(requested_ids),
            Enrollment.enrollment_status == "enrolled",
        ).all()
    }
    if owned:
        raise HTTPException(
            status_code=409,
            detail=("Remove already-owned courses before checkout: "
                    + ", ".join(map(str, sorted(owned)))),
        )

    line_prices = {
        course_id: int(round(float(effective_course_price(by_id[course_id])) * 100))
        for course_id in requested_ids
    }
    subtotal = sum(line_prices.values()) / 100.0
    if subtotal <= 0:
        raise HTTPException(
            status_code=400,
            detail="Free carts do not require a payment order — complete the free order.",
        )

    coupon = None
    discount_paise = 0
    if request.coupon_code:
        try:
            result = validate_and_compute(
                db,
                code=str(request.coupon_code).strip(),
                user_id=current_user.id,
                course_ids=requested_ids,
                total_amount=subtotal,
            )
        except CouponError as exc:
            raise HTTPException(status_code=400, detail=exc.message)
        coupon = result.coupon
        discount_paise = int(round(float(result.discount_amount) * 100))

    try:
        snapshot = build_cart_snapshot(
            line_prices,
            discount_paise=discount_paise,
            coupon_id=coupon.id if coupon else None,
            coupon_code=coupon.code if coupon else None,
        )
    except CartSnapshotError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    notes = snapshot.to_notes(user_id=current_user.id)
    client = _razorpay_client()
    try:
        order = client.order.create({
            "amount": snapshot.total_paise,
            "currency": "INR",
            "receipt": f"cart_{current_user.id}_{uuid.uuid4().hex[:12]}",
            "notes": notes,
        })
    except razorpay.errors.BadRequestError as exc:
        logger.exception(
            "Razorpay rejected cart order (user=%s courses=%s)",
            current_user.id, requested_ids,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway rejected the order: {exc}",
        )
    except Exception:
        logger.exception(
            "Razorpay cart order failed (user=%s courses=%s)",
            current_user.id, requested_ids,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the payment gateway. Please try again in a moment.",
        )

    key_id, _ = _razorpay_creds()
    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order.get("currency") or "INR",
        "key_id": key_id,
        "course_ids": requested_ids,
    }


async def _create_bundle_order(request, db, current_user):
    """Create a Razorpay order for a bundle purchase. Server-computed price
    (Bundle.bundle_price) — coupons are not accepted on bundles. Notes carry
    the course-set snapshot so /verify (and the webhook/sweeper) grant
    exactly the courses that were priced at checkout, even if the bundle's
    contents change later."""
    from app.models.bundle import Bundle, BundleCourse

    if request.coupon_code:
        raise HTTPException(status_code=400,
                            detail="Coupons cannot be applied to bundles")
    bundle = db.query(Bundle).filter(Bundle.id == request.bundle_id,
                                     Bundle.is_active.is_(True)).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    course_ids = [r[0] for r in db.query(BundleCourse.course_id)
                  .filter(BundleCourse.bundle_id == bundle.id).all()]
    if not course_ids:
        raise HTTPException(status_code=400, detail="Bundle has no courses")
    owned = {e.course_id for e in db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id.in_(course_ids),
        Enrollment.enrollment_status == "enrolled").all()}
    if owned == set(course_ids):
        raise HTTPException(status_code=400,
                            detail="You already own every course in this bundle")

    amount_paise = max(int(round(float(bundle.bundle_price) * 100)), 100)
    notes = {
        "bundle_id": str(bundle.id),
        "user_id": str(current_user.id),
        "bundle_course_ids": ",".join(str(c) for c in course_ids),
    }
    client = _razorpay_client()
    try:
        order = client.order.create({
            "amount": amount_paise, "currency": "INR",
            "receipt": f"bundle_{bundle.id}_user_{current_user.id}",
            "notes": notes,
        })
    except Exception:
        logger.exception("Razorpay bundle order failed (user=%s bundle=%s)",
                         current_user.id, bundle.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Could not reach the payment gateway.")
    key_id, _ = _razorpay_creds()
    return {"order_id": order["id"], "amount": order["amount"],
            "currency": order["currency"], "key_id": key_id}


def _company_authorized_for_invoice(db: Session, invoice, user: User) -> bool:
    """True if `user` is the owning company's owner OR a linked
    CompanyManager of that company (mirrors the CompanyManager resolution
    pattern in app/routers/company_dashboard.py / app/services/company_scope.py,
    but scoped to the invoice's company rather than 'my company')."""
    from app.models.company import Company
    from app.models.company_dashboard import CompanyManager

    company = db.query(Company).filter(Company.id == invoice.company_id).first()
    if not company:
        return False
    if company.owner_user_id == user.id:
        return True
    link = db.query(CompanyManager).filter(
        CompanyManager.user_id == user.id,
        CompanyManager.company_id == company.id,
    ).first()
    return link is not None


def create_invoice_order_payload(db: Session, invoice, user: User) -> dict:
    """Build the Razorpay order payload for an invoice payment: the auth
    check (owner or linked CompanyManager of the invoice's company; 403
    otherwise), the ISSUED-status check (409 otherwise), and order creation.
    Returns {order_id, amount, currency, key_id}.

    Shared by POST /create-order (invoice_id branch) and Task 5's
    /invoices/{id}/pay so order creation logic lives in exactly one place.
    """
    from app.models.company_invoice import InvoiceStatus

    if not _company_authorized_for_invoice(db, invoice, user):
        raise HTTPException(status_code=403, detail="Not authorized for this invoice")

    if invoice.status != InvoiceStatus.ISSUED:
        raise HTTPException(
            status_code=409,
            detail=f"Invoice is {invoice.status.value}, not issued — cannot pay",
        )

    amount_paise = max(int(round(float(invoice.total) * 100)), 100)
    notes = {
        "invoice_id": str(invoice.id),
        "user_id": str(user.id),
    }
    client = _razorpay_client()
    try:
        order = client.order.create({
            "amount": amount_paise, "currency": "INR",
            "receipt": f"invoice_{invoice.id}_user_{user.id}",
            "notes": notes,
        })
    except Exception:
        logger.exception("Razorpay invoice order failed (user=%s invoice=%s)",
                         user.id, invoice.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Could not reach the payment gateway.")
    key_id, _ = _razorpay_creds()
    return {"order_id": order["id"], "amount": order["amount"],
            "currency": order["currency"], "key_id": key_id}


async def _create_invoice_order(request, db, current_user):
    """Create a Razorpay order for a company invoice payment. Coupons are
    not accepted on invoices."""
    from app.models.company_invoice import CompanyInvoice

    if request.coupon_code:
        raise HTTPException(status_code=400,
                            detail="Coupons cannot be applied to invoices")
    invoice = db.query(CompanyInvoice).filter(
        CompanyInvoice.id == request.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return create_invoice_order_payload(db, invoice, current_user)


async def _create_ebook_order(request, db, current_user):
    """Create a Razorpay order for an ebook purchase (spec §2). Server-computed
    price from the Ebook row (discount honored) — coupons are REJECTED on
    ebooks at launch, mirroring bundles. Notes carry an ebook_id + rupee-price
    snapshot so /verify (and the webhook/sweeper) fulfill the exact deal that
    was priced at checkout even if the ebook's price changes later."""
    from app.models.ebook import Ebook, EbookGrant, effective_price_inr

    if request.coupon_code:
        raise HTTPException(status_code=400,
                            detail="Coupons cannot be applied to ebooks")
    ebook = db.query(Ebook).filter(Ebook.id == request.ebook_id).first()
    # Drafts are indistinguishable from "doesn't exist" to a buyer, matching
    # the store/download gates in routers/library.py — a 400 here would turn
    # checkout into an unpublished-inventory probe.
    if not ebook or ebook.status != "published":
        raise HTTPException(status_code=404, detail="Ebook not found")

    already = db.query(EbookGrant).filter(
        EbookGrant.ebook_id == ebook.id,
        EbookGrant.user_id == current_user.id).first()
    if already:
        # 409, not 400: the request is well-formed, it conflicts with state
        # the caller already holds (and UNIQUE(ebook_id, user_id) means a
        # second grant could never exist anyway).
        raise HTTPException(status_code=409, detail="You already own this ebook")

    list_price_inr = int(ebook.price_inr or 0)
    price_inr = effective_price_inr(ebook)
    if price_inr <= 0:
        # "Free" is the EFFECTIVE price, so a discount-to-zero ebook lands
        # here too. Razorpay rejects zero-amount orders and the ₹1 clamp
        # would silently charge for a free product.
        raise HTTPException(
            status_code=400,
            detail=(f"Free ebooks do not require a payment order — use "
                    f"POST /library/{ebook.id}/claim instead."))

    amount_paise = max(int(round(float(price_inr) * 100)), 100)
    notes = {
        "ebook_id": str(ebook.id),
        "user_id": str(current_user.id),
        # Checkout-time snapshot (whole rupees). AUTHORITATIVE for the
        # /verify amount check and for the Order's money columns — unlike
        # the course path, which recomputes from the DB, an ebook's price
        # has no sale/coupon machinery behind it, so the snapshot is the
        # only record of the deal the buyer accepted.
        "ebook_price_inr": str(price_inr),
        # Audit-only breakdown of that snapshot.
        "ebook_list_price_inr": str(list_price_inr),
        "ebook_discount_inr": str(max(0, list_price_inr - int(price_inr))),
    }
    client = _razorpay_client()
    try:
        order = client.order.create({
            "amount": amount_paise, "currency": "INR",
            "receipt": f"ebook_{ebook.id}_user_{current_user.id}",
            "notes": notes,
        })
    except Exception:
        logger.exception("Razorpay ebook order failed (user=%s ebook=%s)",
                         current_user.id, ebook.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Could not reach the payment gateway.")
    key_id, _ = _razorpay_creds()
    return {"order_id": order["id"], "amount": order["amount"],
            "currency": order["currency"], "key_id": key_id}


@router.post("/create-order")
async def create_razorpay_order(
    request: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """
    Create a Razorpay order for a course purchase (or, via the branch
    functions above, a bundle / company invoice / ebook — exactly one of
    course_id, bundle_id, invoice_id, ebook_id).

    The amount is computed from the course price on the server. Any `amount`
    value sent by the client is ignored. Notes carry course_id, user_id,
    optional coupon_code / discount_amount, and optional cohort_id /
    referral_code_id so /verify can stamp enrollment with the cohort and
    atomically bump referral usage exactly once.

    A ReferralCode by itself never reduces the order amount — the user
    still pays the full course price and the cohort mapping is applied
    on successful verify. A discount Coupon reduces the amount here.
    """
    if request.course_ids is not None:
        return await _create_cart_order(request, db, current_user)

    if request.bundle_id is not None:
        return await _create_bundle_order(request, db, current_user)

    if request.invoice_id is not None:
        return await _create_invoice_order(request, db, current_user)

    if request.ebook_id is not None:
        return await _create_ebook_order(request, db, current_user)

    course_pk = request.course_id

    course = db.query(Course).filter(Course.id == course_pk).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if getattr(course, "post_status", None) not in ("publish", "published"):
        raise HTTPException(status_code=400, detail="Course is not available for enrollment")

    already = db.query(Enrollment).filter(
        Enrollment.course_id == course.id,
        Enrollment.user_id == current_user.id,
        Enrollment.enrollment_status == "enrolled",
    ).first()
    if already:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")

    if not course.course_price or float(course.course_price) <= 0:
        raise HTTPException(
            status_code=400,
            detail="Free courses do not require a payment order — enroll directly.",
        )

    base_price = float(effective_course_price(course))
    final_price = base_price
    notes: dict[str, str] = {
        "course_id": str(course.id),
        "user_id": str(current_user.id),
        # Informational only — /verify always recomputes from the DB via
        # the pricing authority and never trusts these notes for amount.
        "list_price": f"{float(course.course_price or 0):.2f}",
        "sale_price": f"{float(course.course_sale_price or 0):.2f}",
    }

    # Unified checkout-code resolver — may be a ReferralCode OR a Coupon.
    resolved = None
    coupon_code = request.coupon_code
    if coupon_code:
        try:
            resolved = resolve_checkout_code(
                db,
                code=str(coupon_code).strip(),
                user_id=current_user.id,
                course=course,
                for_paid=True,
            )
        except CouponError as exc:
            raise HTTPException(status_code=400, detail=exc.message)

        if resolved.kind is None:
            raise HTTPException(status_code=400, detail="Invalid code")

        # Reject up front if the mapped cohort is already at capacity
        # (saves the user from paying then being rejected post-verify).
        if resolved.cohort and resolved.max_students_reached:
            raise HTTPException(status_code=400, detail="Cohort full")

        if resolved.kind == "voucher":
            # Vouchers are a 100% discount; Razorpay rejects zero-amount
            # orders. Frontend must route voucher codes to /enroll instead.
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Voucher detected — use /courses/{course.id}/enroll "
                    "instead of creating a Razorpay order"
                ),
            )

        if resolved.kind == "coupon":
            # Discount applies to the Razorpay amount.
            final_price = float(resolved.final_amount)
            notes["coupon_code"] = resolved.coupon.code
            notes["coupon_id"] = str(resolved.coupon.id)
            notes["discount_amount"] = f"{float(resolved.discount_amount):.2f}"
            if resolved.cohort:
                notes["cohort_id"] = str(resolved.cohort.id)
        elif resolved.kind == "referral":
            # Referral does NOT reduce the amount. Stash the cohort and
            # the referral code row id so /verify can apply the mapping
            # and bump used_count atomically.
            notes["cohort_id"] = str(resolved.cohort.id)
            notes["referral_code_id"] = str(resolved.referral_row.id)
            notes["referral_code"] = resolved.referral_row.code

        seat_cohort = resolved.cohort if resolved else None
        if seat_cohort is not None and seat_cohort.seat_price is not None:
            if resolved.kind == "coupon":
                raise HTTPException(
                    status_code=400,
                    detail="Coupons cannot be applied to seat-priced cohorts")
            # Referral into a seat-priced cohort charges the seat price.
            final_price = float(seat_cohort.seat_price)
            notes["seat_price"] = f"{final_price:.2f}"

    amount_paise = int(round(final_price * 100))
    if amount_paise < 100:
        amount_paise = 100  # Razorpay minimum

    client = _razorpay_client()
    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"course_{course.id}_user_{current_user.id}",
            "notes": notes,
        })
    except razorpay.errors.BadRequestError as exc:
        # Wrong/mismatched key pair (test key + live secret is the classic one),
        # a deactivated account, or a rejected amount. Unhandled, this surfaced
        # to the student as a bare "Internal Server Error" with nothing logged.
        logger.exception(
            "Razorpay rejected order creation (user_id=%s course_id=%s amount_paise=%s)",
            current_user.id, course.id, amount_paise,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway rejected the order: {exc}",
        )
    except Exception:
        logger.exception(
            "Razorpay order creation failed (user_id=%s course_id=%s amount_paise=%s)",
            current_user.id, course.id, amount_paise,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the payment gateway. Please try again in a moment.",
        )

    key_id, _ = _razorpay_creds()
    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": key_id,
    }


async def _verify_cart_payment(request, db, current_user):
    """Verify and fulfill a paid cart from its immutable order snapshot."""
    razorpay_order_id = request.razorpay_order_id
    razorpay_payment_id = request.razorpay_payment_id

    _, key_secret = _razorpay_creds()
    if not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=("Payment gateway not configured — payment captured but not "
                    "verified. Contact support."),
        )
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_signature = hmac.new(
        key_secret.encode(), message, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, request.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    try:
        requested_ids = canonical_course_ids(request.course_ids or [])
    except CartSnapshotError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    client = _razorpay_client()
    try:
        order = client.order.fetch(razorpay_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Order not found at gateway")

    notes = order.get("notes") or {}
    try:
        snapshot = parse_cart_notes(notes)
    except CartSnapshotError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Order has an invalid cart snapshot: {exc}",
        )
    if snapshot.course_ids != requested_ids:
        raise HTTPException(status_code=400, detail="Order does not match this cart")
    if str(notes.get("user_id")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Order does not belong to this user")
    if (
        int(order.get("amount", 0)) != snapshot.total_paise
        or int(order.get("amount_paid", 0)) < snapshot.total_paise
    ):
        raise HTTPException(status_code=400, detail="Order amount does not match this cart")

    coupon = None
    if snapshot.coupon_id is not None:
        coupon = db.query(Coupon).filter(Coupon.id == snapshot.coupon_id).first()
        if coupon is None or coupon.code.upper() != snapshot.coupon_code:
            # The gateway has already captured the immutable discounted amount.
            # A coupon deleted/renamed between checkout and callback must not
            # strand a paid learner. Fulfil from the signed price snapshot and
            # alert operations; there is simply no coupon row left to consume.
            EmailService.send_payment_alert(
                "cart coupon changed after capture",
                f"user_id={current_user.id} payment_id={razorpay_payment_id} "
                f"order_id={razorpay_order_id} coupon_id={snapshot.coupon_id} "
                f"snapshot_code={snapshot.coupon_code}. "
                "Fulfilling the captured cart without a coupon usage row.",
            )
            coupon = None

    try:
        fulfill_cart_purchase(
            db,
            user=current_user,
            line_prices_paise=snapshot.line_prices_paise,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            paid_amount=snapshot.total_paise / 100.0,
            coupon_discount=snapshot.discount_paise / 100.0,
            currency=order.get("currency") or "INR",
            coupon=coupon,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Payment verified but cart fulfillment failed "
            "(user=%s courses=%s payment=%s order=%s)",
            current_user.id, requested_ids, razorpay_payment_id, razorpay_order_id,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Your payment was received. Course access will complete "
                "automatically within a few minutes — do not pay again. "
                f"Contact support with payment ID {razorpay_payment_id} if needed."
            ),
        )

    return {
        "success": True,
        "message": "Payment verified — all cart courses unlocked",
        "cohort_id": None,
    }


async def _verify_bundle_payment(request, db, current_user):
    """Verify a Razorpay payment for a bundle order and enroll the user in
    every course in the bundle's checkout-time snapshot. Mirrors the course
    /verify flow: HMAC signature check, order/user/target match against
    notes, server-recomputed amount check, then the idempotent fulfillment
    write."""
    from app.models.bundle import Bundle

    razorpay_order_id = request.razorpay_order_id
    razorpay_payment_id = request.razorpay_payment_id
    razorpay_signature = request.razorpay_signature

    _, key_secret = _razorpay_creds()
    if not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured — payment captured but not verified. Contact support.",
        )
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # No is_active filter: a bundle deactivated between checkout and verify
    # must still fulfill — the buyer already paid for the snapshot.
    bundle = db.query(Bundle).filter(Bundle.id == request.bundle_id).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    client = _razorpay_client()
    try:
        order = client.order.fetch(razorpay_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Order not found at gateway")

    notes = order.get("notes") or {}
    if str(notes.get("bundle_id")) != str(bundle.id):
        raise HTTPException(status_code=400, detail="Order does not match bundle")
    if str(notes.get("user_id")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Order does not belong to this user")

    expected_price = float(bundle.bundle_price)
    expected_amount = int(round(expected_price * 100))
    if expected_amount < 100:
        expected_amount = 100  # Razorpay minimum; matches /create-order clamp
    if int(order.get("amount", 0)) != expected_amount or int(order.get("amount_paid", 0)) < expected_amount:
        raise HTTPException(status_code=400, detail="Order amount does not match bundle price")

    course_ids_note = notes.get("bundle_course_ids") or ""
    try:
        course_ids = [int(c) for c in course_ids_note.split(",") if c.strip()]
    except ValueError:
        course_ids = []
    if not course_ids:
        # Refuse to fulfil an empty/corrupt snapshot. Bailing BEFORE the
        # fulfillment write means no Payment row exists, so the webhook and
        # the reconciliation sweeper — which parse the notes themselves and
        # can escalate — are still armed for this capture. Writing an empty
        # Order here would disarm them.
        logger.error(
            "bundle verify: unusable bundle_course_ids note %r "
            "(user_id=%s bundle_id=%s razorpay_payment_id=%s)",
            course_ids_note, current_user.id, bundle.id, razorpay_payment_id,
        )
        raise HTTPException(
            status_code=400,
            detail=("Order is missing its course list — contact support; "
                    "do not pay again"),
        )

    paid_amount = expected_amount / 100.0

    try:
        result = fulfill_bundle_purchase(
            db,
            user=current_user,
            bundle_id=bundle.id,
            course_ids=course_ids,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            paid_amount=paid_amount,
            currency=order.get("currency") or "INR",
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Payment verified at gateway but enrollment write failed "
            "(user_id=%s bundle_id=%s razorpay_payment_id=%s razorpay_order_id=%s)",
            current_user.id, bundle.id, razorpay_payment_id, razorpay_order_id,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Your payment was received. Enrollment will complete "
                "automatically within a few minutes — do not pay again. "
                f"If it does not appear, contact support quoting payment ID "
                f"{razorpay_payment_id}."
            ),
        )

    return {
        "success": True,
        "message": "Payment verified — all bundle courses unlocked",
        "cohort_id": None,
    }


async def _verify_invoice_payment(request, db, current_user):
    """Verify a Razorpay payment for a company invoice and settle it.
    Mirrors the bundle /verify flow: HMAC signature check, order/user/target
    match against notes, server-recomputed amount check (from the invoice
    row itself, not the notes), then the idempotent settle_invoice write.

    Already-PAID invoices (settle_invoice returns False, e.g. a replayed
    verify after the webhook already settled it) still respond success —
    this is an idempotent status check for the caller, not a failure. A
    settle_invoice False on an invoice that is NOT PAID is the opposite:
    money was captured for something unsettleable (cancelled), so it alerts
    and 409s rather than reporting a success that never happened."""
    from app.models.company_invoice import CompanyInvoice, InvoiceStatus

    razorpay_order_id = request.razorpay_order_id
    razorpay_payment_id = request.razorpay_payment_id
    razorpay_signature = request.razorpay_signature

    _, key_secret = _razorpay_creds()
    if not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured — payment captured but not verified. Contact support.",
        )
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    invoice = db.query(CompanyInvoice).filter(
        CompanyInvoice.id == request.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not _company_authorized_for_invoice(db, invoice, current_user):
        raise HTTPException(status_code=403, detail="Not authorized for this invoice")

    client = _razorpay_client()
    try:
        order = client.order.fetch(razorpay_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Order not found at gateway")

    notes = order.get("notes") or {}
    if str(notes.get("invoice_id")) != str(invoice.id):
        raise HTTPException(status_code=400, detail="Order does not match invoice")
    if str(notes.get("user_id")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Order does not belong to this user")

    expected_amount = max(int(round(float(invoice.total) * 100)), 100)
    if int(order.get("amount", 0)) != expected_amount or int(order.get("amount_paid", 0)) < expected_amount:
        raise HTTPException(status_code=400, detail="Order amount does not match invoice total")

    try:
        settled = settle_invoice(
            db, invoice, via="razorpay", reference=razorpay_payment_id,
            gateway_payment_id=razorpay_payment_id,
            gateway_order_id=razorpay_order_id,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Payment verified at gateway but invoice settlement failed "
            "(user_id=%s invoice_id=%s razorpay_payment_id=%s razorpay_order_id=%s)",
            current_user.id, invoice.id, razorpay_payment_id, razorpay_order_id,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Your payment was received. The invoice will be marked paid "
                "automatically within a few minutes — do not pay again. "
                f"If it does not update, contact support quoting payment ID "
                f"{razorpay_payment_id}."
            ),
        )

    if not settled and invoice.status != InvoiceStatus.PAID:
        # Money was captured at the gateway but the invoice can't be settled
        # (cancelled, or otherwise not ISSUED). Reporting success here would
        # tell the payer their invoice is paid while nothing was booked.
        # Mirrors webhook_processor's unsettleable-invoice handling: alert,
        # persist nothing, and tell the caller not to pay again.
        EmailService.send_payment_alert(
            f"captured payment for unsettleable invoice {invoice.id} (verify)",
            f"invoice_number={invoice.invoice_number} status={invoice.status.value} "
            f"payment_id={razorpay_payment_id} order_id={razorpay_order_id} "
            f"amount={invoice.total} INR user_id={current_user.id}. "
            "Not settled — investigate manually.",
        )
        db.commit()
        raise HTTPException(
            status_code=409,
            detail=(
                "Payment received but the invoice can no longer be settled "
                "(it may have been cancelled). Do not pay again — contact "
                f"support quoting payment ID {razorpay_payment_id}."
            ),
        )

    return {
        "success": True,
        "message": "Invoice paid — seats activated",
        "cohort_id": None,
    }


async def _verify_ebook_payment(request, db, current_user):
    """Verify a Razorpay payment for an ebook and grant it. Mirrors the
    bundle /verify flow: HMAC signature check, order/user/target match
    against notes, amount check against the checkout-time PRICE SNAPSHOT
    (a price edit between checkout and verify must not orphan the capture),
    then the idempotent fulfillment write.

    Deliberately does NOT 404 a deleted ebook: `fulfill_ebook_purchase`
    writes the Order+Payment and pages a human instead, so a capture that
    raced a pre-first-sale delete stays reconcilable (plan: "ebook deleted
    before fulfillment"). Bailing with a 404 here would leave real money
    with no local record."""
    from app.models.ebook import Ebook, snapshot_prices_from_notes
    from app.services.fulfillment_service import fulfill_ebook_purchase

    razorpay_order_id = request.razorpay_order_id
    razorpay_payment_id = request.razorpay_payment_id
    razorpay_signature = request.razorpay_signature

    _, key_secret = _razorpay_creds()
    if not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured — payment captured but not verified. Contact support.",
        )
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # No published filter: an ebook unpublished between checkout and verify
    # must still fulfill — the buyer already paid (same posture as bundles).
    # A DELETED ebook is handled by fulfillment, not rejected here.
    ebook_id = int(request.ebook_id)
    ebook = db.query(Ebook).filter(Ebook.id == ebook_id).first()

    client = _razorpay_client()
    try:
        order = client.order.fetch(razorpay_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Order not found at gateway")

    notes = order.get("notes") or {}
    if str(notes.get("ebook_id")) != str(ebook_id):
        raise HTTPException(status_code=400, detail="Order does not match ebook")
    if str(notes.get("user_id")) != str(current_user.id):
        raise HTTPException(status_code=403,
                            detail="Order does not belong to this user")

    snapshot_inr, list_inr = snapshot_prices_from_notes(notes, ebook)
    if not snapshot_inr or snapshot_inr <= 0:
        # No snapshot AND no live row to fall back on: refuse to price the
        # capture. Bailing BEFORE the fulfillment write means no Payment row
        # exists, so the webhook and the sweeper — which can fetch the order
        # notes themselves and escalate — stay armed (bundle I1 posture).
        logger.error(
            "ebook verify: unusable price snapshot %r "
            "(user_id=%s ebook_id=%s razorpay_payment_id=%s)",
            notes.get("ebook_price_inr"), current_user.id, ebook_id,
            razorpay_payment_id,
        )
        raise HTTPException(
            status_code=400,
            detail=("Order is missing its price snapshot — contact support; "
                    "do not pay again"),
        )

    expected_amount = max(int(round(float(snapshot_inr) * 100)), 100)
    if int(order.get("amount", 0)) != expected_amount \
            or int(order.get("amount_paid", 0)) < expected_amount:
        raise HTTPException(status_code=400,
                            detail="Order amount does not match ebook price")

    paid_amount = expected_amount / 100.0
    try:
        fulfill_ebook_purchase(
            db,
            user=current_user,
            ebook_id=ebook_id,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            paid_amount=paid_amount,
            list_price_inr=list_inr,
            currency=order.get("currency") or "INR",
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Payment verified at gateway but ebook grant write failed "
            "(user_id=%s ebook_id=%s razorpay_payment_id=%s razorpay_order_id=%s)",
            current_user.id, ebook_id, razorpay_payment_id, razorpay_order_id,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Your payment was received. Library access will complete "
                "automatically within a few minutes — do not pay again. "
                f"If it does not appear, contact support quoting payment ID "
                f"{razorpay_payment_id}."
            ),
        )

    return {
        "success": True,
        "message": "Payment verified — ebook added to your library",
        "cohort_id": None,
    }


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_razorpay_payment(
    request: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """
    Verify a Razorpay payment and enroll the user.

    Defence in depth:
      1. HMAC signature on (order_id|payment_id) is validated with constant-time compare.
      2. The Razorpay order is fetched and its `notes` are matched against
         current_user.id and the requested course_id, so a signed order from
         one user cannot be redeemed by another.
      3. The captured amount must equal the server-recomputed price, blocking
         price tampering even if the client sent a forged course id.

    Cohort mapping: if the order notes carry a cohort_id, the Enrollment
    is stamped with cohort_id and a CohortMembership row is created
    idempotently. If a referral_code_id is present, used_count is bumped
    atomically under SELECT FOR UPDATE here (once and only once per
    successful verify).

    Money trail: a COMPLETED Order + OrderItem + Payment are written for the
    amount actually captured (post-coupon), with the coupon discount recorded
    on Order.discount_amount and the list price on Order.subtotal_amount. This
    is what purchase history, /admin/orders and revenue read; without it they
    fall back to course.course_price and report the pre-discount price.
    """
    if request.course_ids is not None:
        return await _verify_cart_payment(request, db, current_user)

    if request.bundle_id is not None:
        return await _verify_bundle_payment(request, db, current_user)

    if request.invoice_id is not None:
        return await _verify_invoice_payment(request, db, current_user)

    if request.ebook_id is not None:
        return await _verify_ebook_payment(request, db, current_user)

    razorpay_order_id = request.razorpay_order_id
    razorpay_payment_id = request.razorpay_payment_id
    razorpay_signature = request.razorpay_signature
    course_id = request.course_id

    _, key_secret = _razorpay_creds()
    if not key_secret:
        # Without this guard `key_secret.encode()` raises AttributeError and
        # FastAPI turns it into an opaque 500 — after the card was charged.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured — payment captured but not verified. Contact support.",
        )
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    course = db.query(Course).filter(Course.id == int(course_id)).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    client = _razorpay_client()
    try:
        order = client.order.fetch(razorpay_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Order not found at gateway")

    notes = order.get("notes") or {}
    if str(notes.get("course_id")) != str(course.id):
        raise HTTPException(status_code=400, detail="Order does not match course")
    if str(notes.get("user_id")) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Order does not belong to this user")

    # Re-resolve the code from notes (if any) — ONLY for the user-facing
    # error path (invalid/expired code, or a hand-crafted voucher note).
    # /verify is the one path with a human waiting on the response, so it
    # keeps its own explicit validation here; the actual expected price and
    # cohort mapping come from the shared `resolve_expected_purchase`
    # helper below, so /verify, the webhook handler and the sweeper all
    # agree field-for-field on the same purchase (this replaces this
    # function's own previous cohort_id/referral_code_id note handling,
    # which — unlike `resolve_checkout_code` — never checked
    # `cohort.course_id == course.id`, allowing a stale/forged cohort_id
    # from a different course's cheaper seat cohort to under-charge and
    # mis-map a purchase).
    note_code = notes.get("coupon_code") or notes.get("referral_code")
    if note_code:
        try:
            precheck = resolve_checkout_code(
                db,
                code=str(note_code),
                user_id=current_user.id,
                course=course,
                for_paid=True,
            )
        except CouponError as exc:
            raise HTTPException(status_code=400, detail=f"Code no longer valid: {exc.message}")

        if precheck.kind == "voucher":
            # Should never happen — /create-order rejects vouchers. Guard
            # defensively so a hand-crafted order with a voucher note can't
            # bypass voucher redemption accounting.
            raise HTTPException(
                status_code=400,
                detail="Voucher orders are not processed via /verify; use /courses/{id}/enroll",
            )

    expected = resolve_expected_purchase(
        db, course, notes, user_id=current_user.id,
    )
    expected_price = expected.expected_price
    cohort_to_assign: Cohort | None = expected.cohort
    referral_code_id_note = expected.referral_code_id

    expected_amount = int(round(expected_price * 100))
    if expected_amount < 100:
        expected_amount = 100  # Razorpay minimum; matches /create-order clamp
    if int(order.get("amount", 0)) != expected_amount or int(order.get("amount_paid", 0)) < expected_amount:
        raise HTTPException(status_code=400, detail="Order amount does not match course price")

    # The amount actually captured, in rupees — this is `expected_price` after
    # the Razorpay ₹1 minimum clamp, so it is exactly what the user was charged.
    paid_amount = expected_amount / 100.0
    coupon_discount = float(expected.coupon_discount) if expected.is_coupon else 0.0

    try:
        try:
            result = fulfill_course_purchase(
                db,
                user=current_user,
                course=course,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                paid_amount=paid_amount,
                # subtotal_price (from the shared helper), not expected_price:
                # expected_price is what was actually charged (net of a
                # coupon's discount), so using it as the pre-discount
                # subtotal would make subtotal - discount double-subtract
                # the coupon. subtotal_price is the seat price / effective
                # course price the buyer was offered BEFORE any coupon
                # discount — see ExpectedPurchase's docstring.
                base_price=expected.subtotal_price,
                coupon_discount=coupon_discount,
                currency=order.get("currency") or "INR",
                cohort=cohort_to_assign,
                referral_code_id=referral_code_id_note,
                coupon=expected.coupon,
            )
        except CouponError as exc:
            # The seat was sold under us between create-order and
            # verify. Payment already captured — surface a clear
            # error; operator will refund / reassign manually.
            raise HTTPException(
                status_code=409,
                detail=f"Referral code exhausted after payment: {exc.message}",
            )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        # The gateway has already captured the money; only our bookkeeping
        # failed. Log the full traceback for reconciliation and return an
        # actionable message instead of a bare "Internal Server Error", which
        # tells the student nothing and loses the payment id.
        logger.exception(
            "Payment verified at gateway but enrollment write failed "
            "(user_id=%s course_id=%s razorpay_payment_id=%s razorpay_order_id=%s)",
            current_user.id, course.id, razorpay_payment_id, razorpay_order_id,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Your payment was received. Enrollment will complete "
                "automatically within a few minutes — do not pay again. "
                f"If it does not appear, contact support quoting payment ID "
                f"{razorpay_payment_id}."
            ),
        )

    return {
        "success": True,
        "message": "Payment verified and enrolled successfully",
        "cohort_id": result.cohort_id,
    }


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Razorpay server-to-server webhook. Unauthenticated by design —
    authenticity comes from the HMAC signature over the RAW body."""
    raw_body = await request.body()

    settings = get_settings()
    secret = _clean_cred(settings.RAZORPAY_WEBHOOK_SECRET)
    if not secret:
        logger.error("webhook received but RAZORPAY_WEBHOOK_SECRET unset")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    provided_sig = request.headers.get("X-Razorpay-Signature", "")
    expected_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    signature_valid = hmac.compare_digest(expected_sig, provided_sig)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Malformed body")

    event_id = request.headers.get("X-Razorpay-Event-Id") or payload.get("id") or ""
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event id")

    event = WebhookEvent(
        event_id=str(event_id),
        event_type=str(payload.get("event") or ""),
        payload=payload,
        signature_valid=signature_valid,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # duplicate delivery — UNIQUE(event_id)
        existing = db.query(WebhookEvent).filter(
            WebhookEvent.event_id == str(event_id)
        ).first()
        # A forged delivery that lands FIRST would otherwise permanently
        # occupy the event_id, so the genuine delivery of the same event
        # could never be processed. Let a valid signature upgrade the
        # poisoned row (attempts kept) and then process it.
        if existing is not None and not existing.signature_valid and signature_valid:
            existing.payload = payload
            existing.signature_valid = True
            existing.event_type = str(payload.get("event") or "")
            # status is left as-is (a forged row is never PROCESSED) and
            # attempts are kept, so the retry budget is unchanged.
            db.commit()
            process_webhook_event(db, existing)
            return {"status": "ok"}
        return {"status": "ok"}  # genuine duplicate: ack and stop

    if not signature_valid:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Inline fast path. On failure the row stays FAILED and the sweeper
    # retries — always ack so Razorpay doesn't redeliver what we hold.
    process_webhook_event(db, event)
    return {"status": "ok"}
