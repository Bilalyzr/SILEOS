# Memberships (Subscriptions) — Design Spec

**Date:** 2026-09-01
**Status:** Approved by owner (chat: "go as per your recommendation")
**Sub-project:** 2 of 5. Builds on sub-project 1 (Payment Reliability Core,
branch `payment-reliability-core`). Implemented on a branch off that branch,
in an isolated worktree (a concurrent session holds uncommitted changes in
the main checkout).

## Product decisions (owner-confirmed)

- **Tiers.** Multiple membership tiers. A tier is either **all-access**
  (every paid course) or **curated** (an admin-picked course set).
- **Billing interval is admin-configurable per tier** (daily / weekly /
  monthly / yearly × interval count, i.e. whatever Razorpay Plans support).
- **Grace period on failed renewal:** when Razorpay halts a subscription
  after retries fail, the member keeps access for a grace window
  (default 7 days, admin-configurable per tier) before suspension.
- **Cancel = at period end** (`cancel_at_cycle_end`), access until the paid
  period expires.
- **No free trial at launch** (Razorpay plan config can add one later).
- Individual course purchases continue unchanged alongside memberships.

## Core architectural decision: materialized enrollments

Course access in this codebase is checked via `Enrollment` rows in many
scattered places (course detail, video gating, progress, quizzes,
certificates, dashboards — `enrollment_status not in ['cancelled',
'suspended']`). Therefore membership access is granted by **creating real
Enrollment rows** (`enrollment_source = "membership"`) for every covered
course when a membership activates, and flipping exactly those rows to
`suspended` when it lapses past grace. Consequences:

- Every existing access check, progress tracker, certificate flow, and
  dashboard works for members with zero changes.
- Suspension preserves progress; re-subscribing re-activates the same rows.
- A sync pass (riding the existing reconciliation loop) grants
  newly-published courses to active members of covering tiers.
- A membership enrollment never overwrites a purchased one: if a row for
  (user, course) already exists, granting leaves it alone. Suspension on
  lapse touches only rows with `enrollment_source = "membership"` AND
  `order_id IS NULL` — a member who later *buys* a covered course gets
  `order_id` stamped on the row by the purchase flow, which permanently
  exempts it from membership suspension.

## Data model

### `membership_plans`
| Column | Notes |
|---|---|
| id, name, description | |
| `all_access` bool | true = every paid course |
| `period` varchar | daily/weekly/monthly/yearly (Razorpay plan period) |
| `interval` int | every N periods |
| `price` numeric(10,2) | INR, per billing cycle |
| `grace_days` int default 7 | |
| `razorpay_plan_id` varchar unique | created via API when the tier is created/priced |
| `is_active` bool | inactive tiers hidden from the pricing page; existing members unaffected |
| created_at / updated_at | |

### `membership_plan_courses`
(plan_id, course_id) rows for curated tiers; empty for all-access tiers.

### `memberships`
| Column | Notes |
|---|---|
| id, user_id FK, plan_id FK | |
| `razorpay_subscription_id` varchar unique | idempotency key for webhook handlers |
| `status` enum | `pending` → `active` → (`grace` → `suspended`) / `cancelled`; `completed` when total_count exhausts |
| `current_period_end` timestamptz | from subscription entity `current_end` |
| `grace_until` timestamptz nullable | set on halt |
| `cancel_at_period_end` bool | set when user cancels |
| created_at / updated_at | |

### `enrollments.enrollment_source`
New nullable varchar(20) column; `"membership"` marks rows this system owns.
NULL/absent = legacy/purchase rows (never touched by membership logic).
Plus `enrollments.membership_id` nullable FK for precise ownership.

Migrations: SQL file per repo convention + models as init_db() source of truth.

## State machine (webhook-driven, via the sub-project-1 inbox)

Razorpay events land in `webhook_events` (already captured as `skipped`
today); new handlers in `webhook_processor.py`:

| Event | Transition |
|---|---|
| `subscription.activated` | pending → active; set current_period_end; **grant enrollments** |
| `subscription.charged` | extend current_period_end; if grace/suspended → active; re-grant/reactivate enrollments |
| `subscription.halted` | active → grace; `grace_until = now + plan.grace_days` (access kept) |
| `subscription.cancelled` | → cancelled; access until current_period_end (sweeper suspends after) |
| `subscription.completed` | → completed; treated like cancelled-at-period-end |
| `subscription.pending` | recorded only (Razorpay is retrying; no state change — grace starts at halted) |

All handlers are idempotent (keyed on razorpay_subscription_id + the event's
effect being state-absorbing). Unknown membership for a subscription id →
UnrecoverableEvent → admin alert (same pattern as sub-project 1).

Sweeper additions (existing reconciliation loop, same cadence):
- **Grace/period expiry pass:** memberships in `grace` past `grace_until`,
  or `cancelled`/`completed` past `current_period_end` → suspend their
  membership enrollments, mark membership `suspended` (grace case).
- **Catalog sync pass:** for each active membership, grant enrollments for
  covered courses added since last pass (cheap set difference).

## API

Public/member (`/api/v1/memberships`):
- `GET /plans` — active tiers with price, period, covered-course count.
- `POST /subscribe` `{plan_id}` — creates Razorpay Subscription
  (`customer_notify=1`, `total_count=100` cycles — Razorpay requires a
  finite count; 100 cycles is effectively open-ended and `subscription.
  completed` handles the horizon), creates local `pending` membership; returns `{subscription_id, key}` for
  Razorpay Checkout. One active/pending/grace membership per user at a time
  (409 otherwise).
- `GET /me` — current membership: plan, status, period end, grace info.
- `POST /cancel` — `cancel_at_cycle_end=1` at Razorpay; marks
  cancel_at_period_end locally.

Admin (`/api/v1/admin/memberships`):
- Plan CRUD (create also creates the Razorpay Plan; price/period changes
  create a NEW Razorpay plan id — Razorpay plans are immutable — existing
  subscribers stay on the old plan id until they resubscribe).
- `GET /` — member list with status filters.
- `/admin/payment-health` gains a memberships section: counts by status,
  memberships in grace, recent subscription events that failed processing.

Frontend (existing stack/patterns, minimal):
- **Pricing page** (`/membership`) listing active tiers → subscribe →
  Razorpay Checkout with `subscription_id` (same integration pattern as
  course purchase checkout).
- **My-membership card** on the student dashboard: plan, renewal date,
  status (incl. grace warning), cancel button with confirm.
- Covered courses need no special UI: materialized enrollments make
  `is_enrolled` true, so existing course cards/pages already render the
  enrolled state for members. No cosmetic label work in this sub-project.

## Verification & payments hygiene

- `/subscribe` requires auth; plan must be active. Amounts and periods are
  never client-supplied — the Razorpay subscription is created server-side
  from the plan row.
- Subscription webhooks arrive through the signature-verified inbox; the
  frontend callback (`razorpay_payment_id` etc. after checkout) is treated
  as UX-only — **state changes come from webhooks/sweeper exclusively**,
  eliminating the client-dependency bug class sub-project 1 fixed for
  one-time purchases.
- The `payment.captured` events that accompany subscription charges carry a
  `subscription_id` and no course notes: the captured-payment handler must
  detect this and defer to the subscription handlers (not raise
  UnrecoverableEvent). Charges are recorded as Order+Payment rows
  (`payment_method="razorpay_subscription"`) for revenue reporting, keyed
  on gateway_payment_id exactly like course purchases.

## Testing

Same harness (backend/tests, SQLite, fixtures from sub-project 1):
lifecycle transitions per event type incl. idempotent re-delivery; grant on
activate (all-access + curated); purchased-enrollment never touched by
suspend; grace flow (halted → charged recovers; halted → expiry suspends);
catalog sync grants new course; one-membership-per-user constraint;
plan CRUD contracts; subscription-charge Payment rows unique on gateway id.
Razorpay client mocked throughout.

## Non-goals

- Trials, proration, plan up/downgrade mid-cycle (resubscribe covers it),
  seat/team memberships (that's B2B, sub-project 4), coupon codes on
  subscriptions, dunning emails beyond Razorpay's own notifications
  (`customer_notify=1`), member-only pricing page CMS.

## Ops (owner, at launch)

Add the subscription events to the existing Razorpay webhook
(`subscription.activated`, `.charged`, `.halted`, `.cancelled`,
`.completed`, `.pending`); run the two SQL migrations; create the first
tiers in the admin UI.
