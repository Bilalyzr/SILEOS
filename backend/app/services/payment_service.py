"""
Payment Service - Business logic for payment processing
"""

import razorpay
import hmac
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.payment import Payment
from app.models.enrollment import Enrollment

settings = get_settings()

class PaymentService:
    """Payment service class"""

    def __init__(self):
        key = settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID
        secret = settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET
        self.razorpay_client = razorpay.Client(
            auth=(key, secret)
        )

    @staticmethod
    async def create_payment_intent(amount: int, currency: str, metadata: Dict[str, str]) -> Dict[str, Any]:
        """
        Create a real Razorpay order. Fails closed when credentials are absent.
        """
        try:
            payment_service = PaymentService()
            order = await asyncio.to_thread(
                payment_service.razorpay_client.order.create,
                {
                    "amount": int(amount),
                    "currency": currency.upper(),
                    "receipt": f"intent_{datetime.utcnow():%Y%m%d%H%M%S%f}"[:40],
                    "notes": metadata,
                },
            )
            return {
                "id": order["id"],
                "client_secret": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "status": order["status"],
                "is_mock": False,
            }

        except Exception as e:
            raise Exception(f"Failed to create payment intent: {str(e)}")

    @staticmethod
    async def verify_payment(payment_intent_id: str) -> Dict[str, Any]:
        """
        Read an order's status from Razorpay. This does not replace the
        signature-and-amount verification in the payment router.
        """
        try:
            if not payment_intent_id.startswith("order_"):
                return {"status": "failed", "error": "Invalid Razorpay order id"}
            payment_service = PaymentService()
            order = await asyncio.to_thread(
                payment_service.razorpay_client.order.fetch,
                payment_intent_id,
            )
            return {
                "status": "succeeded" if order.get("status") == "paid" else order.get("status", "pending"),
                "order_id": payment_intent_id,
                "amount": order.get("amount"),
                "amount_paid": order.get("amount_paid"),
                "currency": order.get("currency"),
                "is_mock": False,
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def verify_webhook_signature(payload: bytes, headers: Dict[str, str]) -> bool:
        """
        Verify Razorpay webhook signature
        """
        try:
            webhook_signature = headers.get("x-razorpay-signature")
            if not webhook_signature:
                return False

            expected_signature = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
                payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(webhook_signature, expected_signature)

        except Exception:
            return False

    @staticmethod
    def is_refund_eligible(payment: Payment, enrollment: Enrollment) -> bool:
        """
        Check if payment is eligible for refund
        """
        # Check if payment was made within last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        if payment.created_at < thirty_days_ago:
            return False

        # Check if course progress is less than 30%
        if enrollment and enrollment.course_progress_percentage and enrollment.course_progress_percentage > 30:
            return False

        return True

    @staticmethod
    async def process_refund(payment_id: str, amount: int, reason: str) -> Dict[str, Any]:
        """
        Process refund with Razorpay
        """
        try:
            payment_service = PaymentService()

            refund_data = {
                "amount": amount,
                "notes": {
                    "reason": reason,
                    "processed_at": datetime.utcnow().isoformat()
                }
            }

            refund = payment_service.razorpay_client.payment.refund(payment_id, refund_data)

            return {
                "status": "processed",
                "refund_id": refund["id"],
                "amount": refund["amount"],
                "currency": refund["currency"]
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    @staticmethod
    def get_payment_methods() -> Dict[str, Any]:
        """
        Get available payment methods
        """
        return {
            "methods": [
                {
                    "type": "card",
                    "name": "Credit/Debit Card",
                    "supported_networks": ["visa", "mastercard", "amex", "rupay"]
                },
                {
                    "type": "netbanking",
                    "name": "Net Banking",
                    "supported_banks": ["sbi", "hdfc", "icici", "axis", "kotak"]
                },
                {
                    "type": "wallet",
                    "name": "Digital Wallets",
                    "supported_wallets": ["paytm", "phonepe", "googlepay", "amazonpay"]
                },
                {
                    "type": "upi",
                    "name": "UPI",
                    "supported_apps": ["gpay", "phonepe", "paytm", "bhim"]
                }
            ]
        }

    @staticmethod
    def calculate_platform_fee(amount: float) -> float:
        """
        Calculate platform fee (commission)
        """
        # Platform takes 5% commission
        return amount * 0.05

    @staticmethod
    def calculate_instructor_earning(amount: float) -> float:
        """
        Calculate instructor earnings after platform fee
        """
        platform_fee = PaymentService.calculate_platform_fee(amount)
        return amount - platform_fee

    @staticmethod
    def format_currency(amount: float, currency: str = "INR") -> str:
        """
        Format currency amount for display
        """
        if currency == "INR":
            return f"₹{amount:,.2f}"
        elif currency == "USD":
            return f"${amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
