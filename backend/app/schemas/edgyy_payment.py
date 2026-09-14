"""
Edgyy Payment Proxy Schemas - Request/Response models
"""
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime


class ProxyOrderRequest(BaseModel):
    """Request from Edgyy to create a Razorpay order"""
    amount: Decimal = Field(..., gt=0, description="Amount in INR")
    currency: str = Field(default="INR", description="Currency code")
    edgyy_registration_id: str = Field(..., min_length=1, description="Unique registration ID from Edgyy")
    edgyy_user_email: Optional[str] = Field(None, description="User email for tracking")
    edgyy_user_name: Optional[str] = Field(None, description="User name for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 500,
                "currency": "INR",
                "edgyy_registration_id": "REG_98765",
                "edgyy_user_email": "user@example.com",
                "edgyy_user_name": "John Doe"
            }
        }


class ProxyOrderResponse(BaseModel):
    """Response to Edgyy with Razorpay order details"""
    order_id: str = Field(..., description="Razorpay order ID")
    amount: int = Field(..., description="Amount in paise")
    currency: str = Field(..., description="Currency code")
    key_id: str = Field(..., description="Razorpay key ID for checkout")
    edgyy_registration_id: str = Field(..., description="Echoed back for verification")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "order_abc123xyz",
                "amount": 50000,
                "currency": "INR",
                "key_id": "rzp_live_abc123",
                "edgyy_registration_id": "REG_98765"
            }
        }


class ProxyVerifyRequest(BaseModel):
    """Request from Edgyy to verify payment"""
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="HMAC signature for verification")
    edgyy_registration_id: str = Field(..., description="Original registration ID")

    class Config:
        json_schema_extra = {
            "example": {
                "razorpay_order_id": "order_abc123xyz",
                "razorpay_payment_id": "pay_abc123xyz",
                "razorpay_signature": "9a4b8c7d...",
                "edgyy_registration_id": "REG_98765"
            }
        }


class ProxyVerifyResponse(BaseModel):
    """Response to Edgyy after verification"""
    success: bool = Field(..., description="Payment verification status")
    message: str = Field(..., description="Human-readable status message")
    edgyy_registration_id: str = Field(..., description="Original registration ID")
    amount: Optional[Decimal] = Field(None, description="Paid amount")
    paid_at: Optional[datetime] = Field(None, description="Payment timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Payment verified successfully",
                "edgyy_registration_id": "REG_98765",
                "amount": 500,
                "paid_at": "2026-07-02T10:30:00Z"
            }
        }


class WebhookPaymentCaptured(BaseModel):
    """Razorpay payment.captured webhook payload"""
    event: str = Field(..., description="Event type, e.g., payment.captured")
    payload: Dict[str, Any] = Field(..., description="Webhook payload containing payment entity")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "id": "pay_abc123",
                        "order_id": "order_abc123",
                        "amount": 50000,
                        "currency": "INR",
                        "status": "captured",
                        "notes": {
                            "edgyy_registration_id": "REG_98765"
                        }
                    }
                }
            }
        }


class EdgyyWebhookCallback(BaseModel):
    """Payload for callback to Edgyy webhook receiver"""
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    edgyy_registration_id: str = Field(..., description="Original registration ID")
    amount: Decimal = Field(..., description="Paid amount in INR")
    currency: str = Field(default="INR", description="Currency code")
    status: str = Field(..., description="Payment status")
    paid_at: datetime = Field(..., description="Payment timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "razorpay_payment_id": "pay_abc123",
                "razorpay_order_id": "order_abc123",
                "edgyy_registration_id": "REG_98765",
                "amount": 500,
                "currency": "INR",
                "status": "paid",
                "paid_at": "2026-07-02T10:30:00Z"
            }
        }


class CreateSessionRequest(BaseModel):
    """Request from Edgyy to create a hosted payment session"""
    amount: Decimal = Field(..., gt=0, description="Amount in INR")
    currency: str = Field(default="INR", description="Currency code")
    edgyy_registration_id: str = Field(..., min_length=1, description="Unique registration ID from Edgyy")
    edgyy_user_email: Optional[str] = Field(None, description="User email for tracking")
    edgyy_user_name: Optional[str] = Field(None, description="User name for tracking")
    return_url: str = Field(..., min_length=1, description="URL to redirect after payment")

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 250,
                "currency": "INR",
                "edgyy_registration_id": "REG_abc123",
                "edgyy_user_email": "user@example.com",
                "edgyy_user_name": "John Doe",
                "return_url": "https://edgyy.in/payment-callback"
            }
        }


class CreateSessionResponse(BaseModel):
    """Response with hosted payment page URL"""
    session_id: str = Field(..., description="Unique session identifier")
    payment_url: str = Field(..., description="Hosted payment page URL")
    order_id: str = Field(..., description="Razorpay order ID")
    amount: int = Field(..., description="Amount in paise")
    currency: str = Field(..., description="Currency code")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123xyz",
                "payment_url": "https://sashainfinity.com/pay?session_id=sess_abc123xyz",
                "order_id": "order_razorpay123",
                "amount": 25000,
                "currency": "INR"
            }
        }
