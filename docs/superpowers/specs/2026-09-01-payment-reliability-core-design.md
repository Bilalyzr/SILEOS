# Payment Reliability Core — Design Spec

**Date:** 2026-09-01
**Status:** Approved by owner (chat), pending spec review
**Sub-project:** 1 of 5 (see "Roadmap context" at the end)

## Problem

SashaInfinity LMS is live and taking real Razorpay payments. Enrollment currently
depends entirely on the buyer's browser calling `POST /api/v1/payments/verify`
after checkout. The `/webhook` handler was removed in the 2026-04 cleanup, so:

- If the buyer pays and closes the tab / loses network before `/verify` fires,
  **Razorpay captures the money and the buyer never gets the course.**
- There is no reconciliation: orphaned captures are invisible until a support
  complaint arrives.
- The money-touching endpoints accept `request: dict` with manual `.get()`
  parsing — no schema validation at the boundary.

This sub-project also lays the foundation required by upcoming revenue products
(subscriptions, bundles, B2B invoicing): a durable, signature-verified,
idempotent webhook inbox that those products' events will flow through.

## Goals

1. Zero missed fulfillment: money captured at the gateway always results in
   enrollment (or an admin alert) without buyer action, within ~30 minutes worst
   case.
2. Database-enforced idempotency for gateway events: duplicate webhook
   deliveries, verify/webhook races, and replays can never double-enroll,
   double-order, or double-count revenue.
3. Typed request/response contracts (Pydantic) on all payment endpoints.
4. Operator visibility: failed/skipped events and unreconciled payments are
   queryable, and unfixable orphans email the admin.

## Non-goals

- Subscriptions, bundles, B2B invoicing (sub-projects 2–4; this design only
  ensures their events will be captured by the inbox as `skipped`).
- Edge caching / SWR (sub-project 5).
- Frontend Zod schemas (deferred; backend Pydantic is the enforced boundary).
- Auto-revoking course access on refund (refunds flag for admin review instead).
- A task-queue worker (Celery/arq). The inbox table is designed so one can be
  added later without rearchitecting; current volume does not justify the ops
  burden.

## Architecture

```
Razorpay ──webhook──▶ POST /api/v1/payments/webhook
                        │  verify X-Razorpay-Signature over RAW body, store event
                        ▼
                  webhook_events table (Postgres inbox, UNIQUE event_id)
                        │  process inline; sweeper retries failures
                        ▼
              fulfillment service  ◀──── POST /verify (browser path, behavior unchanged)
                        │  shared, idempotent (keyed on gateway_payment_id)
                        ▼
              Order + Payment + Enrollment  (existing tables, unchanged schema)

  reconciliation sweeper — asyncio task in FastAPI lifespan,
  Postgres-advisory-locked so multiple replicas cannot double-run it
```

All new code lives in the existing `backend/` FastAPI app. No new services or
containers.

## Components

### 1. `webhook_events` table (new model `app/models/webhook_event.py`)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `event_id` | varchar(255) **UNIQUE NOT NULL** | Razorpay event id (`x-razorpay-event-id` header, falling back to payload `id`). The unique constraint IS the idempotency mechanism — duplicate deliveries hit `ON CONFLICT DO NOTHING`. |
| `event_type` | varchar(100) | e.g. `payment.captured` |
| `payload` | JSON | raw event body |
| `signature_valid` | bool | invalid-signature events stored for forensics, never processed |
| `status` | enum: `received` / `processed` / `failed` / `skipped` | `skipped` = valid but unhandled type (future subscription events land here) |
| `attempts` | int default 0 | |
| `last_attempt_at` | timestamptz nullable | set on every processing attempt; drives retry backoff |
| `last_error` | text nullable | |
| `received_at` / `processed_at` | timestamptz | |

Migration: per repo convention (no Alembic) — SQLAlchemy model is source of
truth for `init_db()`, plus a manual SQL file
`backend/migrations/add_webhook_events_table.sql` for existing deployments.

### 2. Webhook endpoint — `POST /api/v1/payments/webhook`

- Unauthenticated (gateway-to-server), NOT behind JWT. Reads the **raw request
  body before any JSON parsing** — Razorpay signs the raw bytes.
- Verifies `X-Razorpay-Signature` = HMAC-SHA256(raw body, `RAZORPAY_WEBHOOK_SECRET`)
  with `hmac.compare_digest`.
- Invalid signature → store with `signature_valid=false`, return 400.
- Valid → insert (`ON CONFLICT DO NOTHING` on `event_id`; conflict → return 200
  immediately), then process inline. Processing failure marks the row `failed`
  (with `last_error`) but still returns 200 — the inbox + sweeper own retries,
  not Razorpay's redelivery.
- Handled event types:
  - `payment.captured` → extract order notes (`course_id`, `user_id`, coupon /
    cohort / referral fields) → call the fulfillment service. If `/verify`
    already ran, this is a no-op.
  - `payment.failed` → mark the matching local Order (if any) `FAILED`.
  - `refund.processed` → mark Payment `REFUNDED`; the linked enrollment is NOT
    revoked — refunded payments whose enrollment is still `enrolled` are
    surfaced in `/admin/payment-health` for a human decision (no schema change
    needed).
  - anything else → status `skipped`.
- New setting `RAZORPAY_WEBHOOK_SECRET` in `app/core/config.py` (+ `.env.example`).
  Missing/placeholder secret → endpoint returns 503 and logs, same pattern as
  `_razorpay_creds()`.

### 3. Fulfillment service — `app/services/fulfillment_service.py`

Extract the Order/OrderItem/Payment/Enrollment/CohortMembership/coupon-usage
write block currently inline in `/verify` (`payments.py` ~lines 362–482) into:

```
fulfill_course_purchase(db, *, user, course, razorpay_order_id,
                        razorpay_payment_id, order_notes, paid_amount,
                        base_price, coupon_discount, resolved_code) -> FulfillmentResult
```

- Idempotency key unchanged: existing Order joined on
  `Payment.gateway_payment_id` — whichever of `/verify` / webhook / sweeper runs
  first creates the rows; later callers no-op.
- `/verify` keeps ALL of its current defence-in-depth (HMAC on
  order_id|payment_id, notes-vs-user match, server-recomputed amount check)
  and then delegates the write to this service. Its external behavior is
  unchanged.
- The webhook path recomputes/validates amount from the event's order entity
  the same way `/verify` does (fetch order from Razorpay API when the event
  payload lacks notes).
- Referral `used_count` bump and CouponUsage stay new-enrollment-only (existing
  semantics preserved).

### 4. Reconciliation sweeper — `app/services/reconciliation.py`

Asyncio background task started in `main.py` lifespan; every cycle first takes
a Postgres advisory lock (`pg_try_advisory_lock`) and skips the cycle if
another replica holds it.

- **Every 5 min — inbox retry:** reprocess `failed` events with `attempts < 5`;
  backoff by requiring `now - last_attempt_at > 2^attempts` minutes
  (`last_attempt_at` timestamptz column, set on every processing attempt).
  After 5 attempts → stays `failed`, included in the daily admin alert.
- **Every 30 min — gateway diff:** fetch Razorpay orders created in the last
  24h with `status=paid`; for each, if no local `Payment` row matches the
  payment id → run fulfillment from the order's notes. If notes are unusable
  (missing/invalid user or course) → email admin via existing `email_service`
  with the payment id and amount.
- Sweeper failures are logged and never crash the app (task wraps each cycle in
  try/except).

### 5. Typed contracts — `app/schemas/payment.py` additions

- `CreateOrderRequest { course_id: int; code: str | None }` — replaces
  `request: dict` on `/create-order`.
- `VerifyPaymentRequest { razorpay_order_id, razorpay_payment_id,
  razorpay_signature, course_id: int }` — all required; Razorpay id fields
  pattern-validated (`order_…` / `pay_…`).
- Response models for both endpoints.
- Frontend request shape is unchanged (same field names) — no frontend work
  needed.

### 6. Admin observability — additions to `app/routers/admin.py`

- `GET /api/v1/admin/payment-health` → counts + recent rows of `failed` and
  `skipped` webhook events, plus unreconciled gateway payments found by the
  last sweep. Admin-role gated like existing admin endpoints.
- `/verify`'s "contact support / do not pay again" 500 message updated to say
  enrollment will complete automatically within a few minutes (now true).

## Error handling summary

| Failure | Outcome |
|---|---|
| Buyer closes tab after paying | webhook enrolls them (seconds) |
| Webhook delivery lost / endpoint down | 30-min gateway diff enrolls them |
| Processing bug on an event | inbox row `failed`, retried 5× with backoff, then admin alert |
| Duplicate webhook delivery | UNIQUE(event_id) → no-op |
| Webhook + /verify race | Payment.gateway_payment_id keying → single Order/Enrollment |
| Forged webhook | signature check fails → stored unprocessed, 400 |
| Order notes unusable | admin email with payment id + amount |

## Testing (new `backend/tests/`)

pytest is already declared in `requirements.txt`; no suite exists — this
creates it. Tests run against a throwaway SQLite/Postgres session with the
Razorpay client mocked.

1. Webhook signature: valid passes, invalid → 400 + stored unprocessed.
2. Idempotency: same `payment.captured` event delivered twice → exactly one
   Order, one Payment, one Enrollment.
3. Race: `/verify` then webhook (and reverse) → exactly one of each row.
4. Sweeper: a paid gateway order with no local Payment gets fulfilled; one with
   garbage notes triggers the admin-alert path.
5. Contracts: missing/malformed fields on `/create-order` and `/verify` → 422.
6. Refund event marks Payment REFUNDED and does not delete the Enrollment.

## Manual ops step (owner, not code)

In the Razorpay dashboard create a webhook →
`https://<domain>/api/v1/payments/webhook`, events `payment.captured`,
`payment.failed`, `refund.processed`; set a secret and put the same value in
`.env` as `RAZORPAY_WEBHOOK_SECRET`. Until this is done the system behaves
exactly as today (verify-only), with the sweeper's gateway diff already
providing the safety net.

## Roadmap context (later sub-projects, out of scope here)

2. Subscriptions/memberships — Razorpay Subscriptions; events arrive through
   this inbox (already captured as `skipped` until handlers exist).
3. Bundles / paid cohort seats — extends order flow + fulfillment service.
4. B2B / company invoicing — GST invoices, partial payments; reuses ledger
   discipline.
5. Edge caching (stale-while-revalidate) — public catalog/content paths only.
