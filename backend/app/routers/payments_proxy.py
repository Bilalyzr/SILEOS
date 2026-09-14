"""
Edgyy Payment Proxy Router - Server-to-server payment gateway proxy

Secure API layer allowing edgyy.in to use Sasha Infinity's Razorpay integration.
All requests authenticated with EDGYY_SECRET_TOKEN Bearer token.

Endpoints:
    POST /api/v1/payments/proxy/create-order - Create Razorpay order
    POST /api/v1/payments/proxy/verify - Verify payment signature
    POST /api/v1/payments/proxy/webhook - Razorpay webhook handler
    POST /api/v1/payments/proxy/create-session - Create hosted payment session
"""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

import httpx
import razorpay
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import get_db
from app.models.edgyy_payment import EdgyyPayment, EdgyyPaymentStatus, EdgyyPaymentSession, EdgyyPaymentSessionStatus
from app.schemas.edgyy_payment import (
    ProxyOrderRequest,
    ProxyOrderResponse,
    ProxyVerifyRequest,
    ProxyVerifyResponse,
    EdgyyWebhookCallback,
    CreateSessionRequest,
    CreateSessionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proxy", tags=["payments-proxy"])

settings = get_settings()


# Security: Token validation dependency
async def verify_edgyy_token(authorization: Optional[str] = Header(None)) -> None:
    """
    Verify EDGYY_SECRET_TOKEN from Authorization header.

    Expects: Authorization: Bearer <EDGYY_SECRET_TOKEN>
    Raises 401 if missing or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization format. Use: Bearer <token>",
        )

    token = authorization.split(" ", 1)[1].strip()
    expected_token = settings.EDGYY_SECRET_TOKEN

    if not expected_token:
        logger.error("EDGYY_SECRET_TOKEN not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment proxy not configured",
        )

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )


def _razorpay_client() -> razorpay.Client:
    """Get configured Razorpay client."""
    key_id = settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET

    if not key_id or not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured",
        )

    return razorpay.Client(auth=(key_id, key_secret))


def _razorpay_key_id() -> str:
    """Get Razorpay key ID for frontend checkout."""
    return settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID or ""


@router.post("/create-order", response_model=ProxyOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_proxy_order(
    request: ProxyOrderRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_edgyy_token),
):
    """
    Create a Razorpay order for Edgyy registration.

    Server-to-server endpoint. Validates EDGYY_SECRET_TOKEN, creates order
    via Razorpay API, stores mapping in database, returns order_id for checkout.

    Idempotent: Returns existing order if edgyy_registration_id already paid/created.
    """
    # Check for existing order (idempotency)
    existing = db.query(EdgyyPayment).filter(
        EdgyyPayment.edgyy_registration_id == request.edgyy_registration_id
    ).first()

    if existing:
        if existing.status == EdgyyPaymentStatus.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration {request.edgyy_registration_id} already paid",
            )
        # Return existing created order
        return ProxyOrderResponse(
            order_id=existing.razorpay_order_id,
            amount=int(float(existing.amount) * 100),  # Convert to paise
            currency=existing.currency,
            key_id=_razorpay_key_id(),
            edgyy_registration_id=existing.edgyy_registration_id,
        )

    # Create new Razorpay order
    amount_paise = int(float(request.amount) * 100)
    if amount_paise < 100:
        amount_paise = 100  # Razorpay minimum

    client = _razorpay_client()

    # Build notes with Edgyy context
    notes = {
        "edgyy_registration_id": request.edgyy_registration_id,
        "source": "edgyy.in",
        "currency": request.currency,
    }
    if request.edgyy_user_email:
        notes["edgyy_user_email"] = request.edgyy_user_email
    if request.edgyy_user_name:
        notes["edgyy_user_name"] = request.edgyy_user_name

    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": request.currency,
            "receipt": f"edgyy_{request.edgyy_registration_id}",
            "notes": notes,
        })
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create payment order: {str(e)}",
        )

    # Store mapping
    db_payment = EdgyyPayment(
        edgyy_registration_id=request.edgyy_registration_id,
        razorpay_order_id=order["id"],
        amount=request.amount,
        currency=request.currency,
        status=EdgyyPaymentStatus.CREATED,
        gateway_response={"order_creation": order},
    )
    db.add(db_payment)
    db.commit()

    logger.info(
        f"Created order {order['id']} for edgyy_registration_id {request.edgyy_registration_id}"
    )

    return ProxyOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=_razorpay_key_id(),
        edgyy_registration_id=request.edgyy_registration_id,
    )


@router.post("/verify", response_model=ProxyVerifyResponse)
async def verify_proxy_payment(
    request: ProxyVerifyRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_edgyy_token),
):
    """
    Verify Razorpay payment signature via HMAC-SHA256.

    Validates payment authenticity, updates database, triggers webhook to Edgyy.
    Returns success status for Edgyy to complete registration.

    Idempotent: Multiple calls with same payment_id succeed safely.
    """
    # Find our payment record. Orders from /create-order live in edgyy_payments;
    # orders from the hosted /create-session flow live in edgyy_payment_sessions.
    payment = db.query(EdgyyPayment).filter(
        EdgyyPayment.razorpay_order_id == request.razorpay_order_id,
        EdgyyPayment.edgyy_registration_id == request.edgyy_registration_id,
    ).first()
    paid_status = EdgyyPaymentStatus.PAID

    if not payment:
        payment = db.query(EdgyyPaymentSession).filter(
            EdgyyPaymentSession.razorpay_order_id == request.razorpay_order_id,
            EdgyyPaymentSession.edgyy_registration_id == request.edgyy_registration_id,
        ).first()
        paid_status = EdgyyPaymentSessionStatus.PAID

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found",
        )

    # Already paid - return success idempotently
    if payment.status == paid_status:
        return ProxyVerifyResponse(
            success=True,
            message="Payment already verified",
            edgyy_registration_id=payment.edgyy_registration_id,
            amount=payment.amount,
            paid_at=payment.paid_at,
        )

    # Verify HMAC signature
    key_secret = settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET
    msg = f"{request.razorpay_order_id}|{request.razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, request.razorpay_signature):
        logger.warning(f"Invalid signature for order {request.razorpay_order_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature",
        )

    # Fetch from Razorpay for double-verification
    client = _razorpay_client()
    try:
        rzp_order = client.order.fetch(request.razorpay_order_id)
        rzp_payment = client.payment.fetch(request.razorpay_payment_id)
    except Exception as e:
        logger.error(f"Razorpay fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to verify payment with gateway: {str(e)}",
        )

    # Verify amounts match
    expected_amount = int(float(payment.amount) * 100)
    if int(rzp_order.get("amount", 0)) != expected_amount:
        logger.error(f"Amount mismatch for order {request.razorpay_order_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount mismatch",
        )

    # Update payment record
    payment.status = paid_status
    payment.razorpay_payment_id = request.razorpay_payment_id
    payment.paid_at = datetime.utcnow()
    payment.gateway_response = {
        "order": rzp_order,
        "payment": rzp_payment,
    }
    db.commit()

    logger.info(
        f"Payment verified: {payment.edgyy_registration_id} -> {request.razorpay_payment_id}"
    )

    # Trigger webhook to Edgyy (async, non-blocking)
    _trigger_edgyy_webhook(payment)

    return ProxyVerifyResponse(
        success=True,
        message="Payment verified successfully",
        edgyy_registration_id=payment.edgyy_registration_id,
        amount=payment.amount,
        paid_at=payment.paid_at,
    )


def _trigger_edgyy_webhook(payment: EdgyyPayment) -> None:
    """
    Fire-and-forget webhook to Edgyy to complete registration.

    Runs in background. Logs errors but doesn't block response.
    """
    if not payment.razorpay_payment_id:
        logger.warning(f"No payment_id for {payment.edgyy_registration_id}, skipping webhook")
        return

    webhook_url = settings.EDGYY_WEBHOOK_URL
    if not webhook_url:
        logger.warning("EDGYY_WEBHOOK_URL not configured, skipping webhook")
        return

    payload = EdgyyWebhookCallback(
        razorpay_payment_id=payment.razorpay_payment_id,
        razorpay_order_id=payment.razorpay_order_id,
        edgyy_registration_id=payment.edgyy_registration_id,
        amount=float(payment.amount),
        currency=payment.currency,
        status="paid",
        paid_at=payment.paid_at or datetime.utcnow(),
    )

    def _send():
        try:
            headers = {"Content-Type": "application/json"}
            # Add auth header if secret configured
            if settings.EDGYY_WEBHOOK_SECRET:
                headers["X-Edgyy-Secret"] = settings.EDGYY_WEBHOOK_SECRET

            response = httpx.post(
                webhook_url,
                json=payload.model_dump(mode="json"),
                headers=headers,
                timeout=10.0,
            )
            if response.status_code == 200:
                logger.info(f"Webhook delivered to Edgyy: {payment.edgyy_registration_id}")
            else:
                logger.warning(
                    f"Webhook failed: {response.status_code} - {response.text[:200]}"
                )
        except Exception as e:
            logger.error(f"Webhook error: {e}")

    # In production, use Celery/BackgroundTasks. Here we just log.
    import threading
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Razorpay webhook endpoint for payment.captured events.

    Fail-safe backup for registrations where user closes browser after payment
    but before client-side verification completes.

    Verifies webhook signature, finds payment, delivers to Edgyy idempotently.
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify webhook signature
    webhook_signature = request.headers.get("x-razorpay-signature")
    if not webhook_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature",
        )

    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not webhook_secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook not configured",
        )

    expected_sig = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, webhook_signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse webhook payload
    import json
    try:
        payload = json.loads(body.decode())
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event = payload.get("event")
    if event != "payment.captured":
        return {"status": "ignored", "event": event}

    # Extract payment details
    payment_entity = payload.get("payload", {}).get("payment", {})
    razorpay_payment_id = payment_entity.get("id")
    razorpay_order_id = payment_entity.get("order_id")

    if not razorpay_order_id:
        logger.warning("Webhook missing order_id")
        return {"status": "error", "message": "Missing order_id"}

    # Find our payment record. Same two-table split as /verify: orders from
    # /create-order live in edgyy_payments, hosted /create-session orders in
    # edgyy_payment_sessions.
    payment = db.query(EdgyyPayment).filter(
        EdgyyPayment.razorpay_order_id == razorpay_order_id
    ).first()
    paid_status = EdgyyPaymentStatus.PAID

    if not payment:
        payment = db.query(EdgyyPaymentSession).filter(
            EdgyyPaymentSession.razorpay_order_id == razorpay_order_id
        ).first()
        paid_status = EdgyyPaymentSessionStatus.PAID

    if not payment:
        logger.warning(f"Webhook for unknown order: {razorpay_order_id}")
        return {"status": "error", "message": "Order not found"}

    # Idempotency check
    if payment.webhook_delivered:
        logger.info(f"Webhook already delivered for {payment.edgyy_registration_id}")
        return {"status": "already_delivered"}

    # Update payment if not already paid
    if payment.status != paid_status:
        payment.status = paid_status
        payment.razorpay_payment_id = razorpay_payment_id
        payment.paid_at = datetime.utcnow()
        payment.gateway_response = {"webhook": payload}
        db.commit()

    # Mark webhook as delivered
    payment.webhook_delivered = True
    payment.webhook_delivered_at = datetime.utcnow()
    db.commit()

    # Trigger webhook to Edgyy
    _trigger_edgyy_webhook(payment)

    logger.info(f"Webhook processed: {payment.edgyy_registration_id}")

    return {"status": "success", "edgyy_registration_id": payment.edgyy_registration_id}


@router.post("/create-session", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_edgyy_token),
):
    """
    Create a hosted payment session for Edgyy.

    Generates a session_id and returns a payment_url pointing to Sasha's
    hosted payment page. User completes payment on sashainfinity.com,
    then gets redirected back to Edgyy's return_url.
    """
    # Generate unique session ID
    session_id = f"sess_{secrets.token_urlsafe(40)}"

    # Create Razorpay order
    amount_paise = int(float(request.amount) * 100)
    if amount_paise < 100:
        amount_paise = 100

    client = _razorpay_client()

    notes = {
        "edgyy_registration_id": request.edgyy_registration_id,
        "session_id": session_id,
        "source": "edgyy.in",
    }

    try:
        order = client.order.create({
            "amount": amount_paise,
            "currency": request.currency,
            "receipt": f"edgyy_{request.edgyy_registration_id}",
            "notes": notes,
        })
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to create payment order: {str(e)}",
        )

    # Calculate expiry (15 minutes)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    # Store session
    session = EdgyyPaymentSession(
        session_id=session_id,
        edgyy_registration_id=request.edgyy_registration_id,
        edgyy_user_email=request.edgyy_user_email or "",
        edgyy_user_name=request.edgyy_user_name or "",
        return_url=request.return_url,
        razorpay_order_id=order["id"],
        amount=request.amount,
        currency=request.currency,
        status=EdgyyPaymentSessionStatus.PENDING,
        gateway_response={"order_creation": order},
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()

    logger.info(
        f"Created session {session_id} for edgyy_registration_id {request.edgyy_registration_id}"
    )

    # Build payment URL
    payment_url = f"{settings.FRONTEND_URL}/pay?session_id={session_id}"

    return CreateSessionResponse(
        session_id=session_id,
        payment_url=payment_url,
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
    )


@router.get("/health")
async def proxy_health():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "edgyy-payment-proxy",
        "razorpay_configured": bool(
            settings.RAZORPAY_KEY and settings.RAZORPAY_SECRET
        ),
        "edgyy_token_configured": bool(settings.EDGYY_SECRET_TOKEN),
    }


@router.post("/internal/verify-session")
async def verify_session_payment(
    request: dict,
    db: Session = Depends(get_db),
):
    """
    Internal endpoint called by hosted payment page after Razorpay success.
    Verifies signature, updates session, and returns redirect URL.
    """
    razorpay_order_id = request.get("razorpay_order_id")
    razorpay_payment_id = request.get("razorpay_payment_id")
    razorpay_signature = request.get("razorpay_signature")
    session_id = request.get("session_id")

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, session_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Find session
    session = db.query(EdgyyPaymentSession).filter(
        EdgyyPaymentSession.session_id == session_id,
        EdgyyPaymentSession.razorpay_order_id == razorpay_order_id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == EdgyyPaymentSessionStatus.PAID:
        # Already paid, return redirect URL
        return {
            "redirect_url": f"{session.return_url}?status=success&registration_id={session.edgyy_registration_id}&razorpay_payment_id={razorpay_payment_id}&razorpay_order_id={razorpay_order_id}&razorpay_signature={razorpay_signature}&session_id={session_id}"
        }

    # Verify HMAC signature
    key_secret = settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, razorpay_signature):
        logger.warning(f"Invalid signature for order {razorpay_order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Fetch from Razorpay for double-verification
    client = _razorpay_client()
    try:
        rzp_order = client.order.fetch(razorpay_order_id)
        rzp_payment = client.payment.fetch(razorpay_payment_id)
    except Exception as e:
        logger.error(f"Razorpay fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to verify payment with gateway: {str(e)}",
        )

    # Update session
    session.status = EdgyyPaymentSessionStatus.PAID
    session.razorpay_payment_id = razorpay_payment_id
    session.paid_at = datetime.utcnow()
    session.gateway_response = {
        "order": rzp_order,
        "payment": rzp_payment,
    }
    db.commit()

    logger.info(f"Session {session_id} payment verified successfully")

    # Build redirect URL
    redirect_url = f"{session.return_url}?status=success&registration_id={session.edgyy_registration_id}&razorpay_payment_id={razorpay_payment_id}&razorpay_order_id={razorpay_order_id}&razorpay_signature={razorpay_signature}&session_id={session_id}"

    return {"redirect_url": redirect_url}


@router.post("/internal/session-failed")
async def session_payment_failed(
    request: dict,
    db: Session = Depends(get_db),
):
    """
    Internal endpoint called when user dismisses or payment fails.
    Updates session status and returns redirect URL.
    """
    session_id = request.get("session_id")
    error = request.get("error", "Payment failed or cancelled")

    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    session = db.query(EdgyyPaymentSession).filter(
        EdgyyPaymentSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # This endpoint is unauthenticated (called by the browser on dismiss/failure).
    # Never let it flip an already-paid session to FAILED — that would let anyone
    # grief a completed payment by POSTing its session_id.
    if session.status == EdgyyPaymentSessionStatus.PAID:
        raise HTTPException(status_code=409, detail="Session already paid")

    # Update session as failed
    session.status = EdgyyPaymentSessionStatus.FAILED
    session.failure_reason = error
    db.commit()

    logger.info(f"Session {session_id} payment failed: {error}")

    # Build redirect URL
    redirect_url = f"{session.return_url}?status=failed&registration_id={session.edgyy_registration_id}&session_id={session_id}"

    return {"redirect_url": redirect_url}
