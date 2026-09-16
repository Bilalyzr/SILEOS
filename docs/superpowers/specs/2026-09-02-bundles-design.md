# Bundles & Paid Cohort Seats — Design Spec

**Date:** 2026-09-02
**Status:** Approved by owner (chat, standing "go with your recommendation")
**Sub-project:** 3 of 5. Builds on sub-projects 1–2. Implemented on branch
`bundles` (forked from `memberships`) in worktree `.worktrees/bundles`.

## Product scope (owner-approved recommendation)

- **Bundles:** admin-defined sets of paid courses sold at one one-time bundle
  price. Public listing + detail pages; purchase grants an enrollment per
  course. Live alongside single-course purchases and memberships.
- **Paid cohort seats:** a cohort may carry its own `seat_price`; checking
  out with that cohort charges the seat price instead of the course price.
  Referral-code cohorts without a seat price behave exactly as today.
- **Out of scope:** coupons on bundles, bundles-of-bundles, automated seat
  refunds, vouchers (already exist), any membership/bundle cross-rules
  beyond the existing never-overwrite invariant.

## Architectural approach

Extend the existing hardened order flow — no new payment machinery. Every
purchase (course, bundle, seat-priced cohort) flows: `create-order`
(server-side price) → Razorpay → `/verify` AND webhook AND reconciliation
sweeper → idempotent fulfillment keyed on `gateway_payment_id`.

## Data model

### `bundles`
| Column | Notes |
|---|---|
| id, name, description | |
| `bundle_price` numeric(10,2) NOT NULL | INR |
| `is_active` bool default true | inactive → hidden from public pages, not purchasable |
| `slug` varchar(255) unique | public URL |
| created_at / updated_at | |

### `bundle_courses`
(bundle_id indexed, course_id). A bundle must contain ≥ 2 courses
(validated at create/update; existing purchases unaffected by later edits —
fulfillment reads the bundle's course set at purchase time from order
notes, see below).

### `cohorts.seat_price`
New nullable numeric(10,2). NULL = no seat pricing (today's behavior).

### `enrollments.enrollment_source`
Reused (added in sub-project 2): bundle grants tag rows
`enrollment_source="bundle"`. No new columns.

Migration: SQL file `backend/migrations/add_bundles_tables.sql` + models as
init_db() source of truth (repo convention).

## Purchase flow

### create-order (extended)
`CreateOrderRequest` gains optional `bundle_id: int` — exactly one of
`course_id` / `bundle_id` must be present (422 otherwise).

- **Bundle:** price = `bundle.bundle_price` (server-side; bundle must be
  active). Order notes carry `bundle_id`, `user_id`, and
  `bundle_course_ids` (comma-separated snapshot of the course set at
  purchase time — fulfillment uses the snapshot so a later bundle edit
  cannot change what an already-paid buyer receives). Coupons rejected on
  bundle orders (400) per non-goals.
- **Cohort seat:** when the existing cohort path runs and
  `cohort.seat_price` is not NULL, `expected_price = seat_price` (before
  coupon logic; coupons don't apply to seat-priced cohorts — 400 if
  attempted). Capacity check unchanged.

### /verify (extended)
Accepts the same request shape plus optional `bundle_id` (mutually
exclusive with course_id, mirroring create-order). Keeps the full
defence-in-depth of the course path: HMAC check, order notes matched
against current_user.id and the requested bundle_id, amount recomputed
server-side from the bundle row / seat price. Delegates to the fulfillment
service.

### Fulfillment service (extended)
New `fulfill_bundle_purchase(db, *, user, bundle_id, course_ids, razorpay_order_id,
razorpay_payment_id, paid_amount, currency) -> FulfillmentResult`:
- Same idempotency key: existing Order joined on
  `Payment.gateway_payment_id` → no-op replay.
- One Order (COMPLETED, total = paid_amount, `bundle_id` set) + **one
  OrderItem per course** (order_item_type="bundle_item", per-item subtotal
  = course list price; per-item total = paid_amount × (item list price ÷
  combined list price) rounded to 2 dp, with the LAST item absorbing the
  rounding remainder so item totals sum exactly to paid_amount) + one
  Payment (payment_method="razorpay_bundle").
- One enrollment per course via the same never-overwrite rule: existing
  row of any source → left alone; else create with
  `enrollment_source="bundle"` (order_id set — bundle enrollments are
  PURCHASES: never suspended by anything). `total_enrollments` bumped only
  for newly created rows.
- Course-purchase fulfillment (`fulfill_course_purchase`) unchanged; the
  cohort-seat path uses it as today (it's still a course purchase, just at
  seat price).

### Webhook + sweeper (extended)
`payment.captured` handler and the gateway-diff sweeper recognize
`bundle_id` in notes (checked after the subscription_id branch, before the
course-notes branch) and call `fulfill_bundle_purchase` using the
`bundle_course_ids` snapshot from notes. Unusable bundle notes →
UnrecoverableEvent/admin alert (same pattern as courses).

## API

Public:
- `GET /api/v1/bundles` — active bundles: id, slug, name, description,
  bundle_price, courses (id, title, price), combined_price (sum of list
  prices, for the savings display).
- `GET /api/v1/bundles/{slug}` — one bundle, same shape, plus
  `owned_course_ids` for the authenticated viewer (so the UI can show
  overlap honestly before purchase).

Admin (`/api/v1/admin/bundles`): CRUD (create validates ≥2 existing paid
courses; update can change name/description/price/courses/is_active —
edits never affect past purchases), list with per-bundle sales count. To
make that count clean, `orders` gains a nullable `bundle_id` FK column
(set by bundle fulfillment; NULL for all other orders) — sales count =
COUNT of completed Orders with that bundle_id.

Cohort admin: seat_price field added to the existing cohort admin
endpoints/UI.

## Frontend

- `/bundles` listing + `/bundles/{slug}` detail (price vs combined price,
  included courses, owned-course overlap note, Buy via the existing
  Razorpay checkout pattern with `bundle_id`).
- Admin → Bundles management page (mirror the memberships admin page
  patterns): table + create/edit form with course multi-select and the
  sales count.
- Cohort admin form gains seat price input.
- Checkout/course-detail purchase paths: unchanged for courses.

## Testing

Same harness: bundle fulfillment grants N enrollments idempotently;
replay/verify-webhook race → one Order; already-owned course in bundle →
row untouched, others granted; bundle notes snapshot honored over current
bundle contents; seat_price overrides course price in create-order AND
verify amount checks; coupons rejected on bundles and seat-priced cohorts;
inactive bundle not purchasable; admin CRUD validation (≥2 courses, paid
courses only); sweeper fulfills orphaned bundle capture.

## Ops at launch

Run `backend/migrations/add_bundles_tables.sql` on production Postgres.
No new Razorpay configuration (bundle/seat payments are ordinary one-time
payments on the existing webhook).
