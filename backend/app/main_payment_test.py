"""
Payment Test FastAPI Application - Testing payment service
"""

from fastapi import FastAPI, Request, HTTPException
from app.core.cors import setup_cors
from fastapi.responses import JSONResponse
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    print("Payment Test Backend Started Successfully!")
    yield
    print("Shutting down Payment Test Backend...")

# Create FastAPI application
app = FastAPI(
    title="SashaInfinity LMS Payment Test API",
    description="Premium SashaInfinity LMS - Payment Test Backend API",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# CORS Middleware (centralized)
setup_cors(app)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sashainfinity-lms-payment-test",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# Root Endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SashaInfinity LMS Payment Test Backend API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled",
        "payment_testing": True,
        "status": "running"
    }

# Test payment configuration
@app.get("/api/test-payment-config")
async def test_payment_config():
    """Test payment configuration"""
    try:
        return {
            "payment_config": "loaded",
            "razorpay_key_id": settings.RAZORPAY_KEY_ID or "not configured",
            "razorpay_key_secret": "configured" if settings.RAZORPAY_KEY_SECRET else "not configured",
            "webhook_secret": "configured" if settings.RAZORPAY_WEBHOOK_SECRET else "not configured",
            "razorpay_configured": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
            "test_mode": not bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
        }
    except Exception as e:
        return {
            "payment_config": "error",
            "error": str(e)
        }

# Test payment service imports and methods
@app.get("/api/test-payment-service")
async def test_payment_service():
    """Test payment service methods"""
    try:
        from services.payment_service import PaymentService

        # Test utility methods that don't require API calls
        platform_fee = PaymentService.calculate_platform_fee(1000.0)
        instructor_earning = PaymentService.calculate_instructor_earning(1000.0)
        formatted_currency = PaymentService.format_currency(1000.0, "INR")
        payment_methods = PaymentService.get_payment_methods()

        return {
            "payment_service": "loaded",
            "methods_tested": {
                "platform_fee_calculation": f"₹50.00 (5% of ₹1000)",
                "instructor_earning_calculation": f"₹950.00 (after 5% platform fee)",
                "currency_formatting": formatted_currency,
                "payment_methods_count": len(payment_methods["methods"]),
                "available_methods": [method["name"] for method in payment_methods["methods"]]
            },
            "calculations": {
                "platform_fee": platform_fee,
                "instructor_earning": instructor_earning
            }
        }
    except Exception as e:
        return {
            "payment_service": "error",
            "error": str(e)
        }

# Test payment flow simulation (without actual API calls)
@app.post("/api/test-payment-flow")
async def test_payment_flow():
    """Simulate payment flow without API calls"""
    try:
        from services.payment_service import PaymentService

        # Simulate order creation (would create with Razorpay in production)
        mock_order = {
            "id": "order_mock_123456789",
            "client_secret": "order_mock_123456789",
            "amount": 50000,  # ₹500 in paise
            "currency": "INR",
            "status": "created"
        }

        # Calculate fees
        amount_rupees = mock_order["amount"] / 100
        platform_fee = PaymentService.calculate_platform_fee(amount_rupees)
        instructor_earning = PaymentService.calculate_instructor_earning(amount_rupees)

        return {
            "payment_flow": "simulated",
            "mock_order": mock_order,
            "breakdown": {
                "course_price": f"₹{amount_rupees:.2f}",
                "platform_fee": f"₹{platform_fee:.2f}",
                "instructor_earning": f"₹{instructor_earning:.2f}",
                "currency": "INR"
            },
            "flow_steps": [
                "1. Create payment order",
                "2. Customer pays via Razorpay",
                "3. Webhook verifies payment",
                "4. Enroll student in course",
                "5. Send confirmation email",
                "6. Update instructor earnings"
            ],
            "note": "This is a simulation. Production requires valid Razorpay credentials."
        }
    except Exception as e:
        return {
            "payment_flow": "error",
            "error": str(e)
        }

# Test webhook signature verification (with mock data)
@app.post("/api/test-webhook-verification")
async def test_webhook_verification():
    """Test webhook signature verification logic"""
    try:
        from services.payment_service import PaymentService
        import hmac
        import hashlib

        # Mock webhook data
        mock_payload = b'{"event":"payment.captured","payload":{"order":{"id":"order_123"}}}'

        # If webhook secret is configured, test real verification
        if settings.RAZORPAY_WEBHOOK_SECRET:
            # Create a valid signature for testing
            expected_signature = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
                mock_payload,
                hashlib.sha256
            ).hexdigest()

            mock_headers = {"x-razorpay-signature": expected_signature}
            is_valid = PaymentService.verify_webhook_signature(mock_payload, mock_headers)

            return {
                "webhook_verification": "tested",
                "signature_valid": is_valid,
                "webhook_secret_configured": True
            }
        else:
            # Test with invalid signature
            mock_headers = {"x-razorpay-signature": "invalid_signature"}
            is_valid = PaymentService.verify_webhook_signature(mock_payload, mock_headers)

            return {
                "webhook_verification": "tested",
                "signature_valid": is_valid,
                "webhook_secret_configured": False,
                "note": "Webhook secret not configured - tested with invalid signature"
            }

    except Exception as e:
        return {
            "webhook_verification": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(
        "main_payment_test:app",
        host="0.0.0.0",
        port=8006,
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="info"
    )