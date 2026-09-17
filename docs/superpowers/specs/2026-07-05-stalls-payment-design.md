# Stalls Payment Feature - Design Spec

**Date:** 2026-07-05
**Type:** New feature
**Scope:** Market vendor stall registration for one-time event

## Overview

Public-facing stall registration system for market vendor spaces. Users register at `/stalls-payment`, pay via Razorpay, receive invoice email. Admin panel manages registrations. Private API syncs data to edgyy.in.

## Requirements

### Public Page (`/stalls-payment`)
- **Form fields:** Name, Company/Shop Name, Number of stalls (min 1), Mobile number, Email
- **Pricing:** ₹2000 per stall
- **Coupon:** `SONA_STU_26` gives ₹1000 discount (NOT shown in UI - private distribution)
- **Limit:** 10 stalls total (one-time event, permanent after sold out)
- **Access:** Public (no login required)

### Admin Panel
- Sidebar item: "Stalls" in admin navigation
- List all paid registrations with details
- Export capability

### Email
- Invoice email sent after successful payment
- Contains: registration summary, invoice details, event info

### Edgyy Integration
- Private API endpoint: `/api/v1/stalls/edgyy/sync`
- Returns all paid stall registrations
- Auth: Bearer token (reuses existing `EDGYY_SECRET_TOKEN`)

## Architecture

### Backend Components

#### Model: `StallRegistration`
**File:** `backend/app/models/stall_registration.py`

```python
class StallStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"

class StallRegistration(Base):
    __tablename__ = "stall_registrations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    mobile = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)
    num_stalls = Column(Integer, nullable=False)

    # Pricing
    base_amount = Column(Decimal(13, 4), nullable=False)
    discount_amount = Column(Decimal(13, 4), default=0)
    final_amount = Column(Decimal(13, 4), nullable=False)
    coupon_code = Column(String(50), nullable=True)

    # Payment
    status = Column(Enum(StallStatus), default=StallStatus.PENDING)
    razorpay_order_id = Column(String(255), unique=True)
    razorpay_payment_id = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    paid_at = Column(DateTime, nullable=True)
```

#### Router: `stalls.py`
**File:** `backend/app/routers/stalls.py`

**Endpoints:**
- `GET /api/v1/stalls/availability` - Returns remaining stalls count
- `POST /api/v1/stalls/create-order` - Creates Razorpay order
- `POST /api/v1/stalls/verify` - Verifies payment, saves registration, sends email
- `GET /api/v1/stalls/edgyy/sync` - Private endpoint for edgyy.in (auth required)

#### Schema: `stall.py`
**File:** `backend/app/schemas/stall.py`

Request/response models matching the endpoints above.

#### Service: `stall_service.py`
**File:** `backend/app/services/stall_service.py`

**Functions:**
- `get_available_stalls()` - Returns remaining count (10 - paid_count)
- `validate_coupon(code)` - Validates `SONA_STU_26` coupon, returns discount
- `calculate_price(num_stalls, coupon_code)` - Computes final amount
- `create_stall_order()` - Validates form, creates Razorpay order
- `verify_stall_payment()` - Verifies signature, saves registration, triggers email
- `send_invoice_email()` - Sends invoice email

#### Admin Router Extension
**File:** `backend/app/routers/admin.py` (add to existing)

**Endpoints:**
- `GET /api/v1/admin/stalls` - List all registrations (paginated)
- `GET /api/v1/admin/stalls/{id}` - Single registration details

### Frontend Components

#### Page: `stalls-payment.tsx`
**File:** `frontend/src/pages/stalls-payment.tsx`

**Features:**
- Form with validation
- Real-time price display
- Hidden coupon input (no UI hint - only those who know can use)
- Razorpay checkout integration
- Loading/success/error states
- Sold out state (when 0 remaining)

#### Admin Page: `stalls.tsx`
**File:** `frontend/src/pages/admin/stalls.tsx`

**Features:**
- Table listing all registrations
- Columns: Name, Company, Stalls, Mobile, Email, Amount, Status, Date
- Status badges (pending/paid/failed)
- Export to CSV button

#### Navigation Update
**File:** `frontend/src/components/dashboard/nav-configs.ts`

Add to `ADMIN_NAV` array:
```typescript
{ kind: 'link', to: '/admin/stalls', label: 'Stalls', icon: Store }
```

#### App Router Update
**File:** `frontend/src/App.tsx`

Add route:
```typescript
<Route path="/stalls-payment" element={<StallsPaymentPage />} />
<Route path="/admin/stalls" element={<AdminLayout><AdminStalls /></AdminLayout>} />
```

### Email Template

**File:** `backend/app/services/email_service.py` (add new method)

**Method:** `send_stall_invoice_email()`

**Email contents:**
- **Subject:** "Stall Registration Confirmation - [Event Name]"
- **Plain text:** Registration details, invoice info, event details
- **HTML:** Styled invoice with event branding

### Configuration

**File:** `docker-compose.yml` (add to existing env)

```yaml
STALLS_TOTAL: "10"
STALLS_PRICE: "2000"
STALLS_COUPON_CODE: "SONA_STU_26"
STALLS_COUPON_DISCOUNT: "1000"
```

**Note:** `EDGYY_SECRET_TOKEN` already exists for payments proxy - reuse it.

## Data Flow

### Registration Flow

```
1. User visits /stalls-payment
2. Fills form (name, company, stalls, mobile, email)
3. (Optional) Enters coupon code
4. Frontend calls GET /api/v1/stalls/availability to check remaining
5. User submits form
6. Frontend calls POST /api/v1/stalls/create-order
   - Server validates form
   - Calculates price (num_stalls * 2000 - discount)
   - Creates Razorpay order
   - Returns order_id, key_id, amount
7. User completes Razorpay payment
8. Frontend calls POST /api/v1/stalls/verify
   - Server verifies signature
   - Saves StallRegistration with PAID status
   - Sends invoice email
   - Returns success
9. User sees confirmation page
```

### Edgyy Sync Flow

```
1. Edgyy server calls GET /api/v1/stalls/edgyy/sync
   - Header: Authorization: Bearer <EDGYY_SECRET_TOKEN>
2. Server validates token (reuses verify_edgyy_token)
3. Server returns all PAID registrations
4. Edgyy processes data for their system
```

## Security Considerations

1. **Amount validation:** Server computes price, ignores client values
2. **Signature verification:** HMAC-SHA256 on Razorpay callback
3. **Rate limiting:** 10 stalls total enforced server-side
4. **Edgyy auth:** Reuses existing `verify_edgyy_token` dependency
5. **Coupon privacy:** No UI mention, only validated server-side

## Testing Strategy

### Backend Tests
- Model validation
- Price calculation logic
- Coupon validation (valid, invalid, expired)
- Stall limit enforcement (10 max, 0 remaining)
- Razorpay signature verification
- Email sending (mock in tests)

### Frontend Tests
- Form validation
- Price display updates
- Sold out state
- Loading/error states
- Admin table rendering

### Integration Tests
- Full payment flow (test Razorpay key)
- Email delivery
- Edgyy auth + sync endpoint

## Success Criteria

- [ ] Public accessible at `/stalls-payment`
- [ ] Form collects all required fields
- [ ] Coupon `SONA_STU_26` gives ₹1000 discount
- [ ] 10 stall limit enforced
- [ ] Razorpay payment works end-to-end
- [ ] Invoice email sent after payment
- [ ] Admin can view all registrations
- [ ] Edgyy can fetch data via private API
- [ ] Sold out state shows when 0 remaining
