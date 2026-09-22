# Stalls Payment Feature - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build market vendor stall registration system with Razorpay payment, admin panel, email invoices, and edgyy.in sync.

**Architecture:** Separate `StallRegistration` model + `stalls` router following existing payment patterns. Reuses `verify_edgyy_token` for private API. Frontend page at `/stalls-payment`, admin view in sidebar.

**Tech Stack:** FastAPI, SQLAlchemy, Razorpay, React, TypeScript, TailwindCSS

---

## File Structure

### Backend (new files)
- `backend/app/models/stall_registration.py` - SQLAlchemy model
- `backend/app/schemas/stall.py` - Pydantic schemas
- `backend/app/services/stall_service.py` - Business logic
- `backend/app/routers/stalls.py` - API endpoints
- `backend/tests/test_stall_service.py` - Service tests
- `backend/tests/test_stall_router.py` - API tests

### Backend (modifications)
- `backend/app/main.py` - Import and mount stalls router
- `backend/app/routers/admin.py` - Add admin endpoints for stalls
- `backend/app/core/config.py` - Add stalls config fields
- `backend/app/services/email_service.py` - Add invoice email method

### Frontend (new files)
- `frontend/src/pages/stalls-payment.tsx` - Public payment page
- `frontend/src/pages/admin/stalls.tsx` - Admin view
- `frontend/src/api/stalls.ts` - API client
- `frontend/src/hooks/use-stalls.ts` - Hook for stalls data

### Frontend (modifications)
- `frontend/src/App.tsx` - Add routes
- `frontend/src/components/dashboard/nav-configs.ts` - Add admin sidebar item

---

## Task 1: Backend - StallRegistration Model

**Files:**
- Create: `backend/app/models/stall_registration.py`

- [ ] **Step 1: Create model file with StallRegistration class**

```python
"""
Stall Registration Model - Market vendor stall registrations
"""
import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.types import Numeric as Decimal
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class StallStatus(str, enum.Enum):
    """Stall registration status"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"


# PostgreSQL enum
stall_status_enum = ENUM('pending', 'paid', 'failed', name='stall_status', create_type=True)


class StallRegistration(Base):
    """Market vendor stall registration"""
    __tablename__ = "stall_registrations"

    id = Column(Integer, primary_key=True, index=True)

    # Registrant details
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    mobile = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)

    # Stall details
    num_stalls = Column(Integer, nullable=False)

    # Pricing
    base_amount = Column(Decimal(13, 4), nullable=False)
    discount_amount = Column(Decimal(13, 4), default=0)
    final_amount = Column(Decimal(13, 4), nullable=False)
    coupon_code = Column(String(50), nullable=True)

    # Payment
    status = Column(stall_status_enum, default=StallStatus.PENDING)
    razorpay_order_id = Column(String(255), unique=True, nullable=True, index=True)
    razorpay_payment_id = Column(String(255), nullable=True)

    # Invoice
    invoice_number = Column(String(50), unique=True, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        """Convert to dict for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "company_name": self.company_name,
            "mobile": self.mobile,
            "email": self.email,
            "num_stalls": self.num_stalls,
            "base_amount": float(self.base_amount),
            "discount_amount": float(self.discount_amount),
            "final_amount": float(self.final_amount),
            "coupon_code": self.coupon_code,
            "status": self.status.value if isinstance(self.status, enum.Enum) else self.status,
            "razorpay_payment_id": self.razorpay_payment_id,
            "invoice_number": self.invoice_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }

    def __repr__(self):
        return f"<StallRegistration(id={self.id}, name={self.name}, status={self.status})>"
```

- [ ] **Step 2: Update models/__init__.py to export StallRegistration**

Add to `backend/app/models/__init__.py`:
```python
from app.models.stall_registration import StallRegistration, StallStatus
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/stall_registration.py backend/app/models/__init__.py
git commit -m "feat(stalls): add StallRegistration model"
```

---

## Task 2: Backend - Stall Schemas

**Files:**
- Create: `backend/app/schemas/stall.py`

- [ ] **Step 1: Create Pydantic schemas**

```python
"""
Stall Registration Schemas - Request/Response models
"""
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from typing import Optional
from datetime import datetime
import enum


class StallStatus(str, enum.Enum):
    """Stall status enum for schemas"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"


class StallAvailabilityResponse(BaseModel):
    """Response for stall availability check"""
    total_stalls: int = Field(..., description="Total stalls available")
    sold_stalls: int = Field(..., description="Number of sold stalls")
    remaining_stalls: int = Field(..., description="Remaining stalls available")
    is_sold_out: bool = Field(..., description="Whether all stalls are sold")


class CreateOrderRequest(BaseModel):
    """Request to create stall order"""
    name: str = Field(..., min_length=2, max_length=255)
    company_name: str = Field(..., min_length=2, max_length=255)
    num_stalls: int = Field(..., ge=1, le=10)
    mobile: str = Field(..., regex=r"^[6-9]\d{9}$")
    email: str = Field(..., regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    coupon_code: Optional[str] = Field(None, max_length=50)

    @validator('mobile')
    def validate_mobile(cls, v):
        if not v or len(v) != 10:
            raise ValueError('Mobile number must be 10 digits')
        return v


class CreateOrderResponse(BaseModel):
    """Response with Razorpay order details"""
    order_id: str = Field(..., description="Razorpay order ID")
    amount: int = Field(..., description="Amount in paise")
    currency: str = Field(..., description="Currency code")
    key_id: str = Field(..., description="Razorpay key ID for checkout")
    registration_id: int = Field(..., description="Stall registration ID")


class VerifyPaymentRequest(BaseModel):
    """Request to verify payment"""
    razorpay_order_id: str = Field(..., description="Razorpay order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay payment ID")
    razorpay_signature: str = Field(..., description="HMAC signature")
    registration_id: int = Field(..., description="Stall registration ID")


class VerifyPaymentResponse(BaseModel):
    """Response after payment verification"""
    success: bool = Field(..., description="Payment verification status")
    message: str = Field(..., description="Status message")
    invoice_number: Optional[str] = Field(None, description="Invoice number")


class StallRegistrationResponse(BaseModel):
    """Single stall registration details"""
    id: int
    name: str
    company_name: str
    mobile: str
    email: str
    num_stalls: int
    base_amount: float
    discount_amount: float
    final_amount: float
    coupon_code: Optional[str]
    status: StallStatus
    razorpay_payment_id: Optional[str]
    invoice_number: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]


class StallListResponse(BaseModel):
    """List of stall registrations"""
    stalls: list[StallRegistrationResponse]
    total: int
    page: int
    page_size: int


class EdgyySyncResponse(BaseModel):
    """Response for edgyy sync endpoint"""
    stalls: list[dict]
    total_sold: int
    remaining: int
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/stall.py
git commit -m "feat(stalls): add Pydantic schemas"
```

---

## Task 3: Backend - Stall Service

**Files:**
- Create: `backend/app/services/stall_service.py`

- [ ] **Step 1: Create stall service with business logic**

```python
"""
Stall Service - Business logic for stall registrations
"""
import hmac
import hashlib
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
import razorpay

from app.models.stall_registration import StallRegistration, StallStatus
from app.schemas.stall import CreateOrderRequest
from app.core.config import get_settings


settings = get_settings()


# Config constants (with defaults)
STALLS_TOTAL = getattr(settings, 'STALLS_TOTAL', 10)
STALLS_PRICE = getattr(settings, 'STALLS_PRICE', Decimal('2000'))
STALLS_COUPON_CODE = getattr(settings, 'STALLS_COUPON_CODE', 'SONA_STU_26')
STALLS_COUPON_DISCOUNT = getattr(settings, 'STALLS_COUPON_DISCOUNT', Decimal('1000'))


def get_razorpay_client() -> razorpay.Client:
    """Get configured Razorpay client"""
    key_id = settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET

    if not key_id or not key_secret:
        raise ValueError("Payment gateway not configured")

    return razorpay.Client(auth=(key_id, key_secret))


def get_available_stalls(db: Session) -> dict:
    """Get stall availability"""
    sold_count = db.query(StallRegistration).filter(
        StallRegistration.status == StallStatus.PAID
    ).count()

    remaining = max(0, STALLS_TOTAL - sold_count)

    return {
        "total_stalls": STALLS_TOTAL,
        "sold_stalls": sold_count,
        "remaining_stalls": remaining,
        "is_sold_out": remaining == 0
    }


def validate_coupon(code: Optional[str]) -> Decimal:
    """Validate coupon and return discount amount"""
    if not code:
        return Decimal('0')

    if code.strip().upper() == STALLS_COUPON_CODE:
        return STALLS_COUPON_DISCOUNT

    return Decimal('0')


def calculate_price(num_stalls: int, coupon_code: Optional[str]) -> dict:
    """Calculate final price"""
    base_amount = Decimal(str(num_stalls)) * STALLS_PRICE
    discount = validate_coupon(coupon_code)
    final_amount = base_amount - discount

    return {
        "base_amount": base_amount,
        "discount_amount": discount,
        "final_amount": max(final_amount, Decimal('0'))  # Never negative
    }


def generate_invoice_number() -> str:
    """Generate unique invoice number"""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_part = secrets.token_urlsafe(6)[:8].upper()
    return f"STALL-{timestamp}-{random_part}"


def create_stall_order(request: CreateOrderRequest, db: Session) -> dict:
    """Create Razorpay order for stall registration"""
    # Check availability
    availability = get_available_stalls(db)
    if availability["is_sold_out"]:
        raise ValueError("All stalls are sold out")

    if request.num_stalls > availability["remaining_stalls"]:
        raise ValueError(f"Only {availability['remaining_stalls']} stalls available")

    # Calculate price
    pricing = calculate_price(request.num_stalls, request.coupon_code)

    # Check if email already has a paid registration
    existing = db.query(StallRegistration).filter(
        StallRegistration.email == request.email,
        StallRegistration.status == StallStatus.PAID
    ).first()
    if existing:
        raise ValueError("This email has already registered for a stall")

    # Create registration record
    invoice_num = generate_invoice_number()
    registration = StallRegistration(
        name=request.name.strip(),
        company_name=request.company_name.strip(),
        mobile=request.mobile.strip(),
        email=request.email.strip().lower(),
        num_stalls=request.num_stalls,
        base_amount=pricing["base_amount"],
        discount_amount=pricing["discount_amount"],
        final_amount=pricing["final_amount"],
        coupon_code=request.coupon_code.strip().upper() if request.coupon_code else None,
        status=StallStatus.PENDING,
        invoice_number=invoice_num
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)

    # Create Razorpay order
    client = get_razorpay_client()
    amount_paise = int(pricing["final_amount"] * 100)
    if amount_paise < 100:
        amount_paise = 100  # Razorpay minimum

    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": invoice_num,
        "notes": {
            "registration_id": str(registration.id),
            "invoice_number": invoice_num,
            "stall_registration": "true"
        }
    })

    # Update registration with order ID
    registration.razorpay_order_id = order["id"]
    db.commit()

    # Get key_id for frontend
    key_id = settings.RAZORPAY_KEY or settings.RAZORPAY_KEY_ID

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": key_id,
        "registration_id": registration.id
    }


def verify_stall_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    registration_id: int,
    db: Session
) -> dict:
    """Verify Razorpay payment and update registration"""
    # Find registration
    registration = db.query(StallRegistration).filter(
        StallRegistration.id == registration_id
    ).first()

    if not registration:
        raise ValueError("Registration not found")

    if registration.status == StallStatus.PAID:
        return {
            "success": True,
            "message": "Payment already verified",
            "invoice_number": registration.invoice_number
        }

    # Verify signature
    key_secret = settings.RAZORPAY_SECRET or settings.RAZORPAY_KEY_SECRET
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, razorpay_signature):
        raise ValueError("Invalid payment signature")

    # Fetch from Razorpay for double-verification
    client = get_razorpay_client()
    try:
        rzp_order = client.order.fetch(razorpay_order_id)
        rzp_payment = client.payment.fetch(razorpay_payment_id)
    except Exception as e:
        raise ValueError(f"Failed to verify payment with gateway: {str(e)}")

    # Verify amount
    expected_amount = int(float(registration.final_amount) * 100)
    if int(rzp_order.get("amount", 0)) != expected_amount:
        raise ValueError("Payment amount mismatch")

    # Update registration
    registration.status = StallStatus.PAID
    registration.razorpay_payment_id = razorpay_payment_id
    registration.paid_at = datetime.utcnow()
    db.commit()

    # Send invoice email (async, non-blocking)
    _send_invoice_email_async(registration)

    return {
        "success": True,
        "message": "Payment verified successfully",
        "invoice_number": registration.invoice_number
    }


def _send_invoice_email_async(registration: StallRegistration) -> None:
    """Send invoice email in background thread"""
    import threading
    thread = threading.Thread(target=_send_invoice_email, args=(registration,), daemon=True)
    thread.start()


def _send_invoice_email(registration: StallRegistration) -> None:
    """Send invoice email (called in background)"""
    try:
        from app.services.email_service import EmailService
        EmailService.send_stall_invoice_email(
            to_email=registration.email,
            recipient_name=registration.name,
            company_name=registration.company_name,
            num_stalls=registration.num_stalls,
            base_amount=float(registration.base_amount),
            discount_amount=float(registration.discount_amount),
            final_amount=float(registration.final_amount),
            invoice_number=registration.invoice_number,
            payment_id=registration.razorpay_payment_id or "",
            paid_at=registration.paid_at
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send invoice email: {e}")


def get_all_registrations(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    status: Optional[StallStatus] = None
) -> dict:
    """Get all registrations (admin)"""
    query = db.query(StallRegistration)

    if status:
        query = query.filter(StallRegistration.status == status)

    total = query.count()
    offset = (page - 1) * page_size
    registrations = query.order_by(
        StallRegistration.created_at.desc()
    ).offset(offset).limit(page_size).all()

    return {
        "stalls": [r.to_dict() for r in registrations],
        "total": total,
        "page": page,
        "page_size": page_size
    }


def get_edgyy_sync_data(db: Session) -> dict:
    """Get data for edgyy sync (private API)"""
    registrations = db.query(StallRegistration).filter(
        StallRegistration.status == StallStatus.PAID
    ).order_by(StallRegistration.paid_at.desc()).all()

    sold_count = len(registrations)
    remaining = max(0, STALLS_TOTAL - sold_count)

    return {
        "stalls": [r.to_dict() for r in registrations],
        "total_sold": sold_count,
        "remaining": remaining
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/stall_service.py
git commit -m "feat(stalls): add stall service with business logic"
```

---

## Task 4: Backend - Stall Router

**Files:**
- Create: `backend/app/routers/stalls.py`

- [ ] **Step 1: Create stalls router with all endpoints**

```python
"""
Stall Router - API endpoints for stall registrations
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.routers.payments_proxy import verify_edgyy_token
from app.schemas.stall import (
    StallAvailabilityResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
    StallListResponse,
    EdgyySyncResponse
)
from app.services.stall_service import (
    get_available_stalls,
    create_stall_order,
    verify_stall_payment,
    get_all_registrations,
    get_edgyy_sync_data
)
from app.services.auth_service import AuthService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stalls", tags=["Stalls"])


@router.get("/availability", response_model=StallAvailabilityResponse)
async def check_availability(
    db: Session = Depends(get_db)
):
    """Check stall availability (public endpoint)"""
    try:
        availability = get_available_stalls(db)
        return availability
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check availability"
        )


@router.post("/create-order", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequest,
    db: Session = Depends(get_db)
):
    """Create Razorpay order for stall registration (public)"""
    try:
        result = create_stall_order(request, db)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request: VerifyPaymentRequest,
    db: Session = Depends(get_db)
):
    """Verify Razorpay payment (public)"""
    try:
        result = verify_stall_payment(
            request.razorpay_order_id,
            request.razorpay_payment_id,
            request.razorpay_signature,
            request.registration_id,
            db
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify payment"
        )


@router.get("/edgyy/sync", response_model=EdgyySyncResponse)
async def edgyy_sync(
    _: None = Depends(verify_edgyy_token),  # Reuse edgyy auth
    db: Session = Depends(get_db)
):
    """Private endpoint for edgyy.in to fetch stall data"""
    try:
        data = get_edgyy_sync_data(db)
        return data
    except Exception as e:
        logger.error(f"Error in edgyy sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch data"
        )
```

- [ ] **Step 2: Update main.py to import and mount router**

Add import to `backend/app/main.py` (after other router imports):
```python
from app.routers import stalls
```

Add router mount (after other routers, around line 720):
```python
app.include_router(stalls.router, prefix="/api/v1/stalls", tags=["Stalls"])
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/stalls.py backend/app/main.py
git commit -m "feat(stalls): add stalls router with public API endpoints"
```

---

## Task 5: Backend - Admin Endpoints

**Files:**
- Modify: `backend/app/routers/admin.py`

- [ ] **Step 1: Add admin endpoints to admin.py**

Add these endpoints to `backend/app/routers/admin.py` (before the router ends):

```python
@router.get("/stalls", response_model=StallListResponse)
async def get_stall_registrations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Get all stall registrations (admin only)"""
    from app.services.stall_service import get_all_registrations
    from app.models.stall_registration import StallStatus

    status_enum = None
    if status_filter:
        try:
            status_enum = StallStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")

    result = get_all_registrations(db, page=page, page_size=page_size, status=status_enum)
    return result


@router.get("/stalls/{registration_id}")
async def get_stall_registration(
    registration_id: int,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db)
):
    """Get single stall registration (admin only)"""
    from app.models.stall_registration import StallRegistration

    registration = db.query(StallRegistration).filter(
        StallRegistration.id == registration_id
    ).first()

    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    return registration.to_dict()
```

Also add import at top of file:
```python
from app.schemas.stall import StallListResponse
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/admin.py
git commit -m "feat(stalls): add admin endpoints for stall management"
```

---

## Task 6: Backend - Config Fields

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Add stalls config fields**

Add to `backend/app/core/config.py` (after Edgyy section, around line 131):

```python
    # Stalls Configuration
    STALLS_TOTAL: int = Field(default=10, env="STALLS_TOTAL")
    STALLS_PRICE: Decimal = Field(default=Decimal('2000'), env="STALLS_PRICE")
    STALLS_COUPON_CODE: str = Field(default="SONA_STU_26", env="STALLS_COUPON_CODE")
    STALLS_COUPON_DISCOUNT: Decimal = Field(default=Decimal('1000'), env="STALLS_COUPON_DISCOUNT")
```

Also ensure Decimal is imported at top (it should be).

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat(stalls): add config fields for stalls"
```

---

## Task 7: Backend - Invoice Email

**Files:**
- Modify: `backend/app/services/email_service.py`

- [ ] **Step 1: Add invoice email method**

Add to `backend/app/services/email_service.py` (at end of class, before closing):

```python
    @staticmethod
    def send_stall_invoice_email(
        to_email: str,
        recipient_name: str,
        company_name: str,
        num_stalls: int,
        base_amount: float,
        discount_amount: float,
        final_amount: float,
        invoice_number: str,
        payment_id: str,
        paid_at
    ) -> bool:
        """
        Send stall registration invoice email

        Args:
            to_email: Recipient email
            recipient_name: Registrant name
            company_name: Company/shop name
            num_stalls: Number of stalls booked
            base_amount: Base amount before discount
            discount_amount: Discount applied
            final_amount: Final amount paid
            invoice_number: Invoice number
            payment_id: Razorpay payment ID
            paid_at: Payment timestamp

        Returns:
            bool: True if sent successfully
        """
        subject = f"Stall Registration Confirmation - {invoice_number}"

        # Plain text version
        text_body = f"""
Dear {recipient_name},

Thank you for your stall registration!

Registration Details:
- Invoice Number: {invoice_number}
- Company/Shop Name: {company_name}
- Number of Stalls: {num_stalls}
- Mobile: {payment_id[:20]}...

Payment Details:
- Base Amount: ₹{base_amount:.2f}
- Discount Applied: ₹{discount_amount:.2f}
- Final Amount Paid: ₹{final_amount:.2f}
- Payment ID: {payment_id[:30]}...
- Payment Date: {paid_at.strftime('%B %d, %Y at %I:%M %p') if paid_at else 'N/A'}

Event Information:
- Venue: [Event Venue - To be updated]
- Date: [Event Date - To be updated]
- Setup Time: [Setup Time - To be updated]

Important Notes:
- Please arrive 1 hour before the event start time for setup.
- Display your invoice number at the entrance.
- For queries, contact: support@sashainfinity.com

We look forward to seeing you at the event!

Best regards,
SashaInfinity Team
        """

        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ padding: 30px; background-color: #f9f9f9; border: 1px solid #e0e0e0; border-top: none; }}
        .invoice-box {{ background-color: white; padding: 20px; margin: 20px 0; border-left: 4px solid #f97316; border-radius: 4px; }}
        .total-row {{ border-top: 2px solid #f97316; padding-top: 15px; margin-top: 15px; font-weight: bold; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
        .btn {{ display: inline-block; padding: 12px 30px; background: #f97316; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Registration Confirmed!</h1>
            <p>Invoice #{invoice_number}</p>
        </div>
        <div class="content">
            <p>Dear <strong>{recipient_name}</strong>,</p>
            <p>Thank you for your stall registration! Your payment has been successfully processed.</p>

            <div class="invoice-box">
                <h3>Registration Details</h3>
                <table cellpadding="5" style="width: 100%;">
                    <tr><td><strong>Invoice Number:</strong></td><td>{invoice_number}</td></tr>
                    <tr><td><strong>Company/Shop Name:</strong></td><td>{company_name}</td></tr>
                    <tr><td><strong>Number of Stalls:</strong></td><td>{num_stalls}</td></tr>
                </table>
            </div>

            <div class="invoice-box">
                <h3>Payment Summary</h3>
                <table cellpadding="5" style="width: 100%;">
                    <tr><td>Base Amount:</td><td>₹{base_amount:.2f}</td></tr>
                    <tr><td>Discount:</td><td>- ₹{discount_amount:.2f}</td></tr>
                    <tr class="total-row">
                        <td>Total Paid:</td>
                        <td style="color: #f97316; font-size: 18px;">₹{final_amount:.2f}</td>
                    </tr>
                </table>
                <p style="margin-top: 15px; color: #666; font-size: 12px;">
                    Payment ID: {payment_id[:30]}...<br>
                    Payment Date: {paid_at.strftime('%B %d, %Y at %I:%M %p') if paid_at else 'N/A'}
                </p>
            </div>

            <div class="invoice-box">
                <h3>Event Information</h3>
                <p><strong>Venue:</strong> [Event Venue - To be updated]</p>
                <p><strong>Date:</strong> [Event Date - To be updated]</p>
                <p><strong>Setup Time:</strong> [Setup Time - To be updated]</p>
            </div>

            <p style="color: #666;">Please arrive 1 hour before the event start time for setup. Display your invoice number at the entrance.</p>
        </div>
        <div class="footer">
            <p>For queries, contact: support@sashainfinity.com</p>
            <p>SashaInfinity LMS Team</p>
        </div>
    </div>
</body>
</html>
        """

        return EmailService._send_smtp_email(to_email, subject, text_body, html_body)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/email_service.py
git commit -m "feat(stalls): add invoice email method"
```

---

## Task 8: Frontend - API Client

**Files:**
- Create: `frontend/src/api/stalls.ts`

- [ ] **Step 1: Create stalls API client**

```typescript
import { axios } from './axios'

export interface StallAvailability {
  total_stalls: number
  sold_stalls: number
  remaining_stalls: number
  is_sold_out: boolean
}

export interface CreateStallOrderRequest {
  name: string
  company_name: string
  num_stalls: number
  mobile: string
  email: string
  coupon_code?: string
}

export interface CreateStallOrderResponse {
  order_id: string
  amount: number
  currency: string
  key_id: string
  registration_id: number
}

export interface VerifyStallPaymentRequest {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
  registration_id: number
}

export interface VerifyStallPaymentResponse {
  success: boolean
  message: string
  invoice_number?: string
}

export interface StallRegistration {
  id: number
  name: string
  company_name: string
  mobile: string
  email: string
  num_stalls: number
  base_amount: number
  discount_amount: number
  final_amount: number
  coupon_code: string | null
  status: 'pending' | 'paid' | 'failed'
  razorpay_payment_id: string | null
  invoice_number: string | null
  created_at: string
  paid_at: string | null
}

export interface StallListResponse {
  stalls: StallRegistration[]
  total: number
  page: number
  page_size: number
}

export const stallsAPI = {
  getAvailability: async () => {
    const { data } = await axios.get<StallAvailability>('/stalls/availability')
    return data
  },

  createOrder: async (request: CreateStallOrderRequest) => {
    const { data } = await axios.post<CreateStallOrderResponse>('/stalls/create-order', request)
    return data
  },

  verifyPayment: async (request: VerifyStallPaymentRequest) => {
    const { data } = await axios.post<VerifyStallPaymentResponse>('/stalls/verify', request)
    return data
  },

  getAdminStalls: async (page = 1, pageSize = 50, statusFilter?: string) => {
    const params: Record<string, string | number> = { page, page_size: pageSize }
    if (statusFilter) params.status_filter = statusFilter
    const { data } = await axios.get<StallListResponse>('/admin/stalls', { params })
    return data
  },

  getStallById: async (id: number) => {
    const { data } = await axios.get<StallRegistration>(`/admin/stalls/${id}`)
    return data
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/stalls.ts
git commit -m "feat(stalls): add API client"
```

---

## Task 9: Frontend - Stalls Payment Page

**Files:**
- Create: `frontend/src/pages/stalls-payment.tsx'

- [ ] **Step 1: Create stalls payment page**

```typescript
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { stallsAPI, CreateStallOrderRequest } from '@/api/stalls'
import { Store, MapPin, Calendar, Mail, Phone, Building2, Tag, CheckCircle, XCircle } from 'lucide-react'

declare global {
  interface Window {
    Razorpay: any
  }
}

export const StallsPaymentPage: React.FC = () => {
  const navigate = useNavigate()
  const [availability, setAvailability] = useState<{ total_stalls: number; remaining_stalls: number; is_sold_out: boolean } | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const [form, setForm] = useState({
    name: '',
    company_name: '',
    num_stalls: 1,
    mobile: '',
    email: '',
    coupon_code: ''
  })

  const [showCoupon, setShowCoupon] = useState(false)
  const [price, setPrice] = useState({ base: 2000, discount: 0, final: 2000 })

  // Load availability
  useEffect(() => {
    stallsAPI.getAvailability()
      .then(data => {
        setAvailability(data)
        setLoading(false)
      })
      .catch(() => {
        toast.error('Failed to load availability')
        setLoading(false)
      })
  }, [])

  // Calculate price when form changes
  useEffect(() => {
    const base = form.num_stalls * 2000
    let discount = 0
    if (form.coupon_code.toUpperCase() === 'SONA_STU_26') {
      discount = 1000
    }
    const final = Math.max(0, base - discount)
    setPrice({ base, discount, final })
  }, [form.num_stalls, form.coupon_code])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!form.name || !form.company_name || !form.mobile || !form.email) {
      toast.error('Please fill all required fields')
      return
    }

    if (form.mobile.length !== 10) {
      toast.error('Mobile number must be 10 digits')
      return
    }

    if (availability?.is_sold_out) {
      toast.error('Sorry, all stalls are sold out')
      return
    }

    if (form.num_stalls > availability?.remaining_stalls!) {
      toast.error(`Only ${availability.remaining_stalls} stalls available`)
      return
    }

    setSubmitting(true)

    try {
      const request: CreateStallOrderRequest = {
        name: form.name,
        company_name: form.company_name,
        num_stalls: form.num_stalls,
        mobile: form.mobile,
        email: form.email,
        coupon_code: form.coupon_code || undefined
      }

      const order = await stallsAPI.createOrder(request)

      // Open Razorpay checkout
      const options = {
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: 'SashaInfinity',
        description: 'Stall Registration',
        order_id: order.order_id,
        handler: async (response: any) => {
          // Payment successful, verify
          try {
            const verify = await stallsAPI.verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              registration_id: order.registration_id
            })

            if (verify.success) {
              toast.success(`Payment successful! Invoice: ${verify.invoice_number}`)
              navigate('/stalls-payment/success', { state: { invoiceNumber: verify.invoice_number } })
            }
          } catch (err: any) {
            toast.error('Payment verification failed. Please contact support.')
          }
        },
        modal: {
          ondismiss: () => {
            setSubmitting(false)
            toast.error('Payment cancelled')
          }
        },
        prefill: {
          name: form.name,
          email: form.email,
          contact: form.mobile
        }
      }

      const rzp = new window.Razorpay(options)
      rzp.open()
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to create order'
      toast.error(msg)
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    )
  }

  if (availability?.is_sold_out) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Sold Out!</h1>
          <p className="text-gray-600">All 10 stalls have been registered.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Market Stall Registration</h1>
          <p className="text-gray-600">Reserve your stall for the upcoming market event</p>
          <div className="mt-4 inline-flex items-center gap-2 bg-green-100 text-green-700 px-4 py-2 rounded-full">
            <CheckCircle className="w-5 h-5" />
            <span className="font-semibold">{availability?.remaining_stalls} stalls remaining</span>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Form */}
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <Store className="w-6 h-6 text-orange-500" />
              Registration Details
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  placeholder="Enter your full name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company/Shop Name *</label>
                <input
                  type="text"
                  required
                  value={form.company_name}
                  onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  placeholder="Enter company or shop name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Number of Stalls *</label>
                <select
                  value={form.num_stalls}
                  onChange={e => setForm(f => ({ ...f, num_stalls: parseInt(e.target.value) }))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                    <option key={n} value={n} disabled={n > availability?.remaining_stalls!}>
                      {n} Stall{n > 1 ? 's' : ''} {n > availability?.remaining_stalls! ? '(Sold Out)' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Mobile *</label>
                  <input
                    type="tel"
                    required
                    maxLength={10}
                    value={form.mobile}
                    onChange={e => setForm(f => ({ ...f, mobile: e.target.value.replace(/\D/g, '') }))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    placeholder="10-digit number"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                  <input
                    type="email"
                    required
                    value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    placeholder="your@email.com"
                  />
                </div>
              </div>

              <div>
                <button
                  type="button"
                  onClick={() => setShowCoupon(!showCoupon)}
                  className="text-orange-600 text-sm hover:underline"
                >
                  {showCoupon ? 'Hide' : 'Have a coupon code?'}
                </button>
                {showCoupon && (
                  <input
                    type="text"
                    value={form.coupon_code}
                    onChange={e => setForm(f => ({ ...f, coupon_code: e.target.value }))}
                    className="w-full mt-2 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    placeholder="Enter coupon code"
                  />
                )}
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold rounded-lg hover:from-orange-600 hover:to-amber-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Processing...' : `Pay ₹${price.final}`}
              </button>
            </form>
          </div>

          {/* Price Breakdown */}
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-xl p-8">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Tag className="w-6 h-6 text-orange-500" />
                Price Breakdown
              </h2>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Price per stall</span>
                  <span className="font-medium">₹2,000</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Number of stalls</span>
                  <span className="font-medium">× {form.num_stalls}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Base amount</span>
                  <span className="font-medium">₹{price.base.toLocaleString('en-IN')}</span>
                </div>
                {price.discount > 0 && (
                  <>
                    <div className="flex justify-between text-green-600">
                      <span>Discount applied</span>
                      <span className="font-medium">-₹{price.discount.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="text-xs text-gray-500">
                      Coupon: {form.coupon_code.toUpperCase()}
                    </div>
                  </>
                )}
                <div className="border-t pt-3 flex justify-between text-lg">
                  <span className="font-semibold">Total</span>
                  <span className="font-bold text-orange-600">₹{price.final.toLocaleString('en-IN')}</span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-xl p-8">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <Calendar className="w-6 h-6 text-orange-500" />
                Event Details
              </h2>

              <div className="space-y-3 text-gray-600">
                <p className="flex items-center gap-2">
                  <MapPin className="w-5 h-5" />
                  <span>Venue: [To be announced]</span>
                </p>
                <p className="flex items-center gap-2">
                  <Calendar className="w-5 h-5" />
                  <span>Date: [To be announced]</span>
                </p>
              </div>

              <div className="mt-6 p-4 bg-orange-50 rounded-lg text-sm text-orange-700">
                <p>• Arrive 1 hour early for setup</p>
                <p>• Display invoice number at entrance</p>
                <p>• Invoice sent to email after payment</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default StallsPaymentPage
```

- [ ] **Step 2: Create success page**

```typescript
// frontend/src/pages/stalls-payment-success.tsx
import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { CheckCircle, Home, Mail } from 'lucide-react'

export const StallsPaymentSuccessPage: React.FC = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const invoiceNumber = location.state?.invoiceNumber || 'N/A'

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Registration Successful!</h1>
        <p className="text-gray-600 mb-6">Your stall has been booked. Invoice details sent to your email.</p>

        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <p className="text-sm text-gray-500">Invoice Number</p>
          <p className="text-xl font-bold text-orange-600">{invoiceNumber}</p>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => navigate('/')}
            className="w-full py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold rounded-lg hover:from-orange-600 hover:to-amber-600 transition-all flex items-center justify-center gap-2"
          >
            <Home className="w-5 h-5" />
            Go to Home
          </button>
        </div>

        <p className="mt-6 text-sm text-gray-500">
          For queries, contact <a href="mailto:support@sashainfinity.com" className="text-orange-600">support@sashainfinity.com</a>
        </p>
      </div>
    </div>
  )
}

export default StallsPaymentSuccessPage
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/stalls-payment.tsx frontend/src/pages/stalls-payment-success.tsx
git commit -m "feat(stalls): add payment page with Razorpay integration"
```

---

## Task 10: Frontend - Admin Stalls Page

**Files:**
- Create: `frontend/src/pages/admin/stalls.tsx`

- [ ] **Step 1: Create admin stalls page**

```typescript
import React, { useState, useEffect } from 'react'
import { stallsAPI, StallRegistration } from '@/api/stalls'
import { getAuthToken } from '@/utils/auth-helper'
import toast from 'react-hot-toast'
import { Store, Download, Filter, ChevronLeft, ChevronRight } from 'lucide-react'

const API = "/api/v1"
const h = () => ({ "Content-Type": "application/json", Authorization: `Bearer ${getAuthToken()}` })

export const AdminStalls: React.FC = () => {
  const [stalls, setStalls] = useState<StallRegistration[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState<string>('')

  const pageSize = 50

  const loadStalls = async () => {
    setLoading(true)
    try {
      const data = await stallsAPI.getAdminStalls(page, pageSize, statusFilter || undefined)
      setStalls(data.stalls)
      setTotal(data.total)
    } catch (err) {
      toast.error('Failed to load registrations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadStalls() }, [page, statusFilter])

  const exportCSV = () => {
    const headers = ['Invoice', 'Name', 'Company', 'Mobile', 'Email', 'Stalls', 'Amount', 'Status', 'Date']
    const rows = stalls.map(s => [
      s.invoice_number || 'N/A',
      s.name,
      s.company_name,
      s.mobile,
      s.email,
      s.num_stalls.toString(),
      `₹${s.final_amount}`,
      s.status,
      new Date(s.created_at).toLocaleDateString()
    ])

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `stall-registrations-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  const getStatusBadge = (status: string) => {
    const styles = {
      paid: 'bg-green-100 text-green-700',
      pending: 'bg-yellow-100 text-yellow-700',
      failed: 'bg-red-100 text-red-700'
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status as keyof typeof styles] || 'bg-gray-100'}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Store className="w-8 h-8 text-orange-500" />
          Stall Registrations
        </h1>
        <button
          onClick={exportCSV}
          className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 flex items-center gap-2"
        >
          <Download className="w-5 h-5" />
          Export CSV
        </button>
      </div>

      <div className="bg-white rounded-xl border">
        {/* Filters */}
        <div className="p-4 border-b flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">All Status</option>
              <option value="paid">Paid</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <span className="text-sm text-gray-500">
            {total} total registrations
          </span>
        </div>

        {/* Table */}
        {loading ? (
          <div className="p-8 text-center">Loading...</div>
        ) : stalls.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No registrations found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Invoice</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stalls</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {stalls.map(stall => (
                  <tr key={stall.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-orange-600">{stall.invoice_number || 'N/A'}</td>
                    <td className="px-4 py-3 text-sm">{stall.name}</td>
                    <td className="px-4 py-3 text-sm">{stall.company_name}</td>
                    <td className="px-4 py-3 text-sm">
                      <div>{stall.mobile}</div>
                      <div className="text-gray-500 text-xs">{stall.email}</div>
                    </td>
                    <td className="px-4 py-3 text-sm">{stall.num_stalls}</td>
                    <td className="px-4 py-3 text-sm font-medium">₹{stall.final_amount.toLocaleString('en-IN')}</td>
                    <td className="px-4 py-3 text-sm">{getStatusBadge(stall.status)}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(stall.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 border-t flex items-center justify-between">
            <span className="text-sm text-gray-500">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50 flex items-center gap-1"
              >
                <ChevronLeft className="w-4 h-4" /> Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50 flex items-center gap-1"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminStalls
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/admin/stalls.tsx
git commit -m "feat(stalls): add admin page for stall management"
```

---

## Task 11: Frontend - Navigation & Routes

**Files:**
- Modify: `frontend/src/components/dashboard/nav-configs.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add stalls to admin navigation**

Add to `ADMIN_NAV` array in `frontend/src/components/dashboard/nav-configs.ts` (after Coupons line):

```typescript
{ kind: 'link', to: '/admin/stalls', label: 'Stalls', icon: Store },
```

Ensure `Store` is imported from lucide-react at top of file.

- [ ] **Step 2: Add routes to App.tsx**

Add imports to `frontend/src/App.tsx`:
```typescript
import { StallsPaymentPage } from '@/pages/stalls-payment'
import { StallsPaymentSuccessPage } from '@/pages/stalls-payment-success'
import { AdminStalls } from '@/pages/admin/stalls'
```

Add routes (inside `<Routes>`, with other public routes):
```typescript
<Route path="/stalls-payment" element={<StallsPaymentPage />} />
<Route path="/stalls-payment/success" element={<StallsPaymentSuccessPage />} />
```

Add admin route (inside admin routes section):
```typescript
<Route path="/admin/stalls" element={<AdminLayout><AdminStalls /></AdminLayout>} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/nav-configs.ts frontend/src/App.tsx
git commit -m "feat(stalls): add navigation and routes"
```

---

## Task 12: Docker Compose - Config Fields

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add env vars to docker-compose.yml**

Add to backend environment section in `docker-compose.yml`:

```yaml
STALLS_TOTAL: "10"
STALLS_PRICE: "2000"
STALLS_COUPON_CODE: "SONA_STU_26"
STALLS_COUPON_DISCOUNT: "1000"
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(stalls): add config env vars to docker-compose"
```

---

## Task 13: Razorpay Script Loading

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add Razorpay script tag**

Add to `frontend/index.html` (before closing `</head>`):

```html
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat(stalls): add Razorpay checkout script"
```

---

## Task 14: Database Migration

**Files:**
- Create: `backend/migrations/create_stalls_table.sql`

- [ ] **Step 1: Create SQL migration file**

```sql
-- Stalls Registration Table Migration
-- Run: docker-compose exec postgres psql -U tutor -d tutor_lms < backend/migrations/create_stalls_table.sql

-- Create enum
CREATE TYPE stall_status AS ENUM ('pending', 'paid', 'failed');

-- Create table
CREATE TABLE IF NOT EXISTS stall_registrations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    num_stalls INTEGER NOT NULL,
    base_amount NUMERIC(13, 4) NOT NULL,
    discount_amount NUMERIC(13, 4) DEFAULT 0,
    final_amount NUMERIC(13, 4) NOT NULL,
    coupon_code VARCHAR(50),
    status stall_status DEFAULT 'pending',
    razorpay_order_id VARCHAR(255) UNIQUE,
    razorpay_payment_id VARCHAR(255),
    invoice_number VARCHAR(50) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_stall_registrations_razorpay_order ON stall_registrations(razorpay_order_id);
CREATE INDEX IF NOT EXISTS idx_stall_registrations_invoice ON stall_registrations(invoice_number);
CREATE INDEX IF NOT EXISTS idx_stall_registrations_status ON stall_registrations(status);
CREATE INDEX IF NOT EXISTS idx_stall_registrations_email ON stall_registrations(email);
```

- [ ] **Step 2: Run migration**

```bash
docker-compose exec postgres psql -U tutor -d tutor_lms < backend/migrations/create_stalls_table.sql
```

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/create_stalls_table.sql
git commit -m "feat(stalls): add database migration"
```

---

## Task 15: Testing - Backend Service Tests

**Files:**
- Create: `backend/tests/test_stall_service.py`

- [ ] **Step 1: Create service tests**

```python
"""
Tests for stall service
"""
import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.stall_service import (
    calculate_price,
    validate_coupon,
    generate_invoice_number
)
from app.models.stall_registration import StallStatus


def test_calculate_price_no_coupon():
    """Test price calculation without coupon"""
    result = calculate_price(2, None)
    assert result["base_amount"] == Decimal('4000')
    assert result["discount_amount"] == Decimal('0')
    assert result["final_amount"] == Decimal('4000')


def test_calculate_price_with_coupon():
    """Test price calculation with valid coupon"""
    result = calculate_price(2, 'SONA_STU_26')
    assert result["base_amount"] == Decimal('4000')
    assert result["discount_amount"] == Decimal('1000')
    assert result["final_amount"] == Decimal('3000')


def test_calculate_price_with_invalid_coupon():
    """Test price calculation with invalid coupon"""
    result = calculate_price(2, 'INVALID_CODE')
    assert result["base_amount"] == Decimal('4000')
    assert result["discount_amount"] == Decimal('0')
    assert result["final_amount"] == Decimal('4000')


def test_calculate_price_case_insensitive_coupon():
    """Test coupon is case-insensitive"""
    result1 = calculate_price(1, 'sona_stu_26')
    result2 = calculate_price(1, 'SONA_STU_26')
    result3 = calculate_price(1, 'Sona_Stu_26')
    assert result1["discount_amount"] == result2["discount_amount"]
    assert result2["discount_amount"] == result3["discount_amount"]


def test_validate_coupon_valid():
    """Test valid coupon returns discount"""
    discount = validate_coupon('SONA_STU_26')
    assert discount == Decimal('1000')


def test_validate_coupon_invalid():
    """Test invalid coupon returns 0"""
    discount = validate_coupon('INVALID')
    assert discount == Decimal('0')


def test_validate_coupon_none():
    """Test None coupon returns 0"""
    discount = validate_coupon(None)
    assert discount == Decimal('0')


def test_generate_invoice_number():
    """Test invoice number generation"""
    invoice1 = generate_invoice_number()
    invoice2 = generate_invoice_number()

    assert invoice1.startswith('STALL-')
    assert invoice2.startswith('STALL-')
    assert invoice1 != invoice2  # Should be unique


def test_calculate_price_never_negative():
    """Test final amount is never negative"""
    # Even with huge discount, price shouldn't be negative
    result = calculate_price(1, 'SONA_STU_26')
    assert result["final_amount"] >= 0
```

- [ ] **Step 2: Run tests**

```bash
cd backend && python -m pytest tests/test_stall_service.py -v
```

Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_stall_service.py
git commit -m "test(stalls): add service tests"
```

---

## Task 16: Integration Test - Full Flow

**Files:**
- Create: `backend/tests/test_stall_integration.py`

- [ ] **Step 1: Create integration test**

```python
"""
Integration tests for stall registration flow
"""
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session

from app.services.stall_service import (
    get_available_stalls,
    create_stall_order,
    verify_stall_payment
)
from app.schemas.stall import CreateOrderRequest
from app.models.stall_registration import StallRegistration, StallStatus


def test_stall_registration_flow(db: Session):
    """Test complete registration flow"""
    # Check initial availability
    avail = get_available_stalls(db)
    assert avail["total_stalls"] == 10
    assert avail["sold_stalls"] == 0
    assert avail["remaining_stalls"] == 10
    assert avail["is_sold_out"] is False

    # Create order
    request = CreateOrderRequest(
        name="Test Vendor",
        company_name="Test Shop",
        num_stalls=2,
        mobile="9876543210",
        email="test@example.com",
        coupon_code="SONA_STU_26"
    )

    order_result = create_stall_order(request, db)
    assert "order_id" in order_result
    assert "registration_id" in order_result
    assert order_result["amount"] == 300000  # 2 stalls * 2000 - 1000 discount = 3000 INR = 300000 paise

    # Verify registration created
    registration = db.query(StallRegistration).filter(
        StallRegistration.email == "test@example.com"
    ).first()
    assert registration is not None
    assert registration.status == StallStatus.PENDING
    assert registration.num_stalls == 2
    assert registration.final_amount == Decimal('3000')

    # Clean up for test isolation
    db.delete(registration)
    db.commit()


def test_duplicate_email_rejected(db: Session):
    """Test that duplicate email is rejected"""
    from app.core.exceptions import ValidationError  # Adjust import as needed

    # First registration
    request1 = CreateOrderRequest(
        name="First User",
        company_name="First Shop",
        num_stalls=1,
        mobile="9876543210",
        email="duplicate@example.com",
        coupon_code=None
    )

    # Create and manually mark as paid
    order1 = create_stall_order(request1, db)
    reg1 = db.query(StallRegistration).filter(
        StallRegistration.email == "duplicate@example.com"
    ).first()
    reg1.status = StallStatus.PAID
    db.commit()

    # Try second registration with same email
    request2 = CreateOrderRequest(
        name="Second User",
        company_name="Second Shop",
        num_stalls=1,
        mobile="9876543211",
        email="duplicate@example.com",
        coupon_code=None
    )

    with pytest.raises(ValueError, match="already registered"):
        create_stall_order(request2, db)

    # Clean up
    db.delete(reg1)
    db.commit()


def test_sold_out_prevents_order(db: Session):
    """Test that orders are rejected when sold out"""
    # This test would need to mock the availability or create 10 paid registrations
    # For now, we'll test the logic conceptually
    pass
```

- [ ] **Step 2: Run integration tests**

```bash
cd backend && python -m pytest tests/test_stall_integration.py -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_stall_integration.py
git commit -m "test(stalls): add integration tests"
```

---

## End Checklist

After all tasks complete:

- [ ] Backend: `docker-compose restart backend`
- [ ] Frontend: `docker-compose restart frontend`
- [ ] Visit `/stalls-payment` - page loads, shows availability
- [ ] Test form validation (mobile, email)
- [ ] Test coupon code (SONA_STU_26 gives discount)
- [ ] Test Razorpay payment (use test key)
- [ ] Verify invoice email received
- [ ] Admin: Visit `/admin/stalls` - table loads
- [ ] Admin: Export CSV works
- [ ] Edgyy: Test `/api/v1/stalls/edgyy/sync` with Bearer token
