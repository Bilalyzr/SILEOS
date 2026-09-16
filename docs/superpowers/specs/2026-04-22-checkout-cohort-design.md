# Unified Checkout with Cohort-Linked Coupons

**Date:** 2026-04-22
**Status:** Approved

## Overview

All course enrollments go through a unified checkout flow. Coupon codes serve dual purpose: discount application AND cohort assignment (SPOC referrals). Checkout form is conditional based on course price - free courses skip payment details.

## Requirements

1. All courses (free and paid) require checkout before enrollment
2. Free courses: simplified form (name, email, coupon only)
3. Paid courses: full payment form (card, billing, contact info)
4. Coupon codes are linked to specific cohorts - using a coupon auto-assigns user to that cohort
5. Both "Enroll Now" (direct checkout) and "Add to Cart" options on course detail
6. Coupon field available on both cart and checkout pages
7. Success page then auto-redirect to "My Courses"

## Architecture

### Backend Changes

#### Coupon Model Extension

Add `cohort_id` field to Coupon model:

```python
# app/models/coupon.py
class Coupon(Base):
    # ... existing fields ...
    cohort_id = Column(Integer, ForeignKey("cohorts.id"), nullable=True)
```

#### Orders Router Update

Modify `POST /api/v1/orders/` to:
- Handle single-course direct checkout
- When coupon applied, fetch `cohort_id` from coupon
- Create enrollments with `cohort_id` if coupon was used

#### New Endpoint

```
GET /api/v1/courses/{id}/checkout-info
Response: { price, salePrice, isFree, title, thumbnail }
```

### Frontend Changes

#### Course Detail Page

- Add "Enroll Now" button → navigates to `/checkout/{courseId}`
- Keep existing "Add to Cart" button

#### Checkout Page

Two modes based on total amount:

**Free Course Mode:**
- Full name input
- Email input
- Coupon code input
- "Confirm Enrollment" button
- No card/billing details

**Paid Course Mode:**
- Existing full payment form
- Contact info, card details, billing address
- Coupon field for discount

#### New Route

```
/checkout/:courseId - Direct checkout for single course
/checkout - Cart-based checkout (existing)
```

## Data Flow

```
User clicks "Enroll Now"
    ↓
Navigate to /checkout/{courseId}
    ↓
Fetch course price
    ↓
IF price == 0:
    Show simplified form (name, email, coupon)
ELSE:
    Show full payment form
    ↓
Submit → POST /api/v1/orders/
    ↓
Backend:
  - Validate coupon (if provided)
  - Get cohort_id from coupon
  - Create order + payment
  - Create enrollment(s) with cohort_id (if coupon used)
  - Record coupon usage
    ↓
Show success page
    ↓
Auto-redirect to /my-courses (3 seconds)
```

## Cohort Assignment Logic

```
Coupon applied?
  YES → coupon.cohort_id exists?
      YES → Create enrollment with cohort_id
      NO  → Create enrollment without cohort_id
  NO  → Create enrollment without cohort_id
```

## API Changes

### Modified Endpoints

**POST /api/v1/orders/**
- Accept `course_id` (single) OR `course_ids` (array)
- Include `cohort_id` in enrollment when coupon used
- Support ₹0 orders (free courses)

### New Schemas

```python
class DirectCheckoutRequest(BaseModel):
    course_id: int
    coupon_code: Optional[str]

# Existing OrderCreate still works for cart flow
```

## Database Schema Changes

### Coupon Table
```sql
ALTER TABLE coupons ADD COLUMN cohort_id INTEGER REFERENCES cohorts(id);
CREATE INDEX idx_coupon_cohort ON coupons(cohort_id);
```

### Enrollment Table
```sql
-- Ensure cohort_id exists (if not already present)
ALTER TABLE enrollments ADD COLUMN cohort_id INTEGER REFERENCES cohorts(id);
CREATE INDEX idx_enrollment_cohort ON enrollments(cohort_id);
```

## Testing Checklist

- [ ] Free course checkout without coupon
- [ ] Free course checkout with coupon (cohort assignment)
- [ ] Paid course checkout without coupon
- [ ] Paid course checkout with coupon (discount + cohort)
- [ ] Direct "Enroll Now" flow
- [ ] Cart-based checkout flow
- [ ] Coupon validation (expired, invalid, usage limits)
- [ ] Success page redirect
- [ ] Course appears in "My Courses" after enrollment

## Implementation Order

1. Database migration (cohort_id on coupons, enrollments)
2. Backend: Update Coupon model and schemas
3. Backend: Update orders router for cohort assignment
4. Backend: Add checkout-info endpoint
5. Frontend: Add checkout/:courseId route
6. Frontend: Conditional checkout form (free vs paid)
7. Frontend: Update course detail page with "Enroll Now"
8. Frontend: Success page with auto-redirect
9. Testing and bug fixes
