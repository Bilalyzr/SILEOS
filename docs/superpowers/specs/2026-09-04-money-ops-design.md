# Money Operations — Design Spec

**Date:** 2026-09-04 · **Branch:** `money-ops` (worktree `.worktrees/money-ops`, off `revenue-platform` @ 83f176f)
**Source findings:** audit Part 2 A-H1 (no refunds), I-H2 (no payouts), C-H3 (no seat revoke), §0 (no admin subscription cancel; delete-vs-archive for memberships/bundles). All four operator rulings below were given by the owner's delegate on 2026-09-03.
**Review tier:** STRONGEST (opus) on every task — this branch moves or revokes money and access.

## 0. Rulings (binding)
- R1 **Archive, not delete.** Membership plans and bundles get `is_active=false` as the primary verb (already exists for plans; add for bundles if missing). Hard delete is allowed ONLY when the plan has zero memberships ever / the bundle has zero orders ever; otherwise 409 with a message naming the count. Admin gets a **cancel-subscription** action.
- R2 **Refunds are admin-initiated, full-amount only** (partial = out of scope). Money moves via the Razorpay refund API; state converges through the existing webhook.
- R3 **Payouts move no money in-product.** Instructors request a withdrawal against their available balance; admin approves/rejects/marks-paid with a bank reference. Actual transfer is manual (NEFT/UPI) — the product is the ledger.
- R4 Seat revoke returns the seat to the pool and revokes ONLY the access that seat granted.

## 1. Refunds (A-H1)
**Existing plumbing (reuse, don't rebuild):** `PaymentService.process_refund(payment_id, amount, reason)` (payment_service.py:111 — calls `razorpay_client.payment.refund`); `schemas/payment.RefundRequest` (reason ≥10 chars); webhook `refund.processed` → `_handle_refund_processed` (webhook_processor.py:443) sets `Payment.payment_status=REFUNDED` and deliberately does NOT revoke enrollment; `/admin/payment-health` surfaces "refunded with active enrollment"; `PaymentStatus.REFUNDED` + `OrderStatus.REFUNDED` enums exist but nothing sets `OrderStatus.REFUNDED`.

**New:** `POST /api/v1/admin/orders/{order_id}/refund` body `{reason}` (require_admin):
1. Load Order + its Payment(s) with `gateway_payment_id` and status paid/captured. 409 if already REFUNDED or a refund is in flight; 400 if the order has no captured gateway payment (offline/company-invoice orders are out of scope → 400 with guidance).
2. Amount = the captured amount recorded on the Payment (full refund, paise). Never from the request.
3. Persist intent FIRST (Payment `refund_status='requested'`, `refund_reason`, `refund_requested_by`, `refund_requested_at` — add columns via **migration 0006** if absent; store `gateway_refund_id` when returned) then call `process_refund`. On gateway failure: mark `refund_status='failed'` with the error, return 502, leave access intact.
4. On gateway success: `Payment.payment_status=REFUNDED`, `Order.status=REFUNDED`, `gateway_refund_id` stored, and **revoke exactly the enrollments this order granted**: `Enrollment.order_id == order.id` (course orders: one row; bundle orders: all rows) → `enrollment_status="cancelled"`. NEVER touch rows with a different `order_id`, membership rows, or company rows. Emit the existing email path if a refund template exists (else skip; no new templates).
5. Idempotent convergence: `_handle_refund_processed` now ALSO performs step 4's order/enrollment updates **when the refund was admin-initiated** (payment carries `refund_status in ('requested','processed')`); externally-initiated refunds (dashboard refunds with no intent row) keep today's behavior (mark REFUNDED, leave access for human decision via payment-health). Both paths idempotent (re-running changes nothing).
6. Every refund writes an admin audit entry if the repo has an admin audit/activity log model; otherwise `logger.info` with order/payment/actor ids (plan-writer verifies which).

**UI:** admin orders page (`admin.py:2725` list) gains an order status column with REFUNDED, a "Refund" action → reason modal (≥10 chars) → confirmation naming amount + affected courses → toast with refund id; refunded rows show the reason on hover/expand. **Student "My Orders"** page at `/my-orders` (nav under profile/settings) reads `GET /orders/me` (orders.py:325) — read-only list with status (incl. Refunded), amount, date, items — closing product gap D1 cheaply.

## 2. Admin cancel-subscription + archive rules (§0, R1)
- Extract `cancel_membership_subscription(db, membership, *, immediate: bool, actor_id: int) -> None` from `memberships.py:167-195` and use it from BOTH the self-service `/cancel` (immediate=False, unchanged behavior) and the new **`POST /api/v1/admin/memberships/{membership_id}/cancel`** body `{immediate: bool, reason}` (require_admin). `immediate=false` → Razorpay `cancel_at_cycle_end=1` + `cancel_at_period_end=True` (today's semantics). `immediate=true` → Razorpay cancel now (`cancel_at_cycle_end=0`), `status=CANCELLED`, and `membership_access.suspend(...)` (the existing lapse logic) so materialized enrollments suspend immediately. PENDING rows discard locally as today. Gateway failure → 502, nothing changed locally.
- Plans: `DELETE /admin/memberships/plans/{id}` → 409 `{"count": n}` when any Membership row references it; else hard delete. Bundles: add `is_active` toggle if absent (check model) and `DELETE /admin/bundles/{id}` → 409 when any Order references it; else hard delete. UI: Deactivate is the prominent action; Delete appears only when the server says it's allowed (button disabled with the count otherwise).

## 3. Seat revoke (C-H3, R4)
`DELETE /api/v1/company-billing/seat-pools/{pool_id}/assignments/{user_id}` (require_company_or_manager, own pool via `_get_own_pool_or_404`): in ONE transaction — delete the `CompanySeatAssignment` (404 if none); atomic `used_seats = used_seats - 1` guarded `used_seats > 0`; revoke enrollments where `Enrollment.user_id==user AND enrollment_source=="company" AND order_id==pool.order_id AND course_id in pool's course list` → `enrollment_status="cancelled"` (rows the user obtained any other way — purchase, membership, another pool — are untouched; the assign path's rescue semantics mean such rows never carried this pool's order_id). Response lists revoked vs untouched course ids. UI: "Revoke seat" on the assignments table with confirm.

## 4. Instructor payouts (I-H2, R3)
- **Balance authority:** one helper `instructor_balance(db, user_id) -> {earned, withdrawn_or_pending, available}` whose `earned` uses the SAME formula the instructor dashboard already shows (`dashboard.py:775-795`, earnings by order line) — the plan-writer must confirm whether `Earning` rows are written anywhere; if not, the order-line formula is the authority and `Earning` stays unused (do not start populating it now). `available = earned − Σ withdrawals with status in ('pending','approved','paid')`.
- `Withdrawal` model exists (payment.py:217-239: amount, method_data JSON, status pending|approved|rejected|paid, reject_detail). No migration needed unless an admin-reference field is required → add `paid_reference` + `processed_by` + `processed_at` via migration 0006 (same revision as refunds columns).
- Instructor: `POST /api/v1/instructor/withdrawals` `{amount, method_data{type: 'bank'|'upi', ...}}` → 400 if amount ≤0, > available, or below a `MIN_WITHDRAWAL_INR` setting (default 500); `GET /api/v1/instructor/withdrawals` (own, with balance summary). Admin: `GET /api/v1/admin/withdrawals?status=`, `POST /admin/withdrawals/{id}/approve`, `/reject {reject_detail}`, `/mark-paid {paid_reference}`; transitions pending→approved→paid, pending→rejected; anything else 409. `method_data` is stored as given but rendered as text only (never HTML) and NEVER logged.
- UI: instructor "Payouts" page (balance cards, request form with method fields, history table) + nav entry in `components/dashboard/nav-configs.ts`; admin "Payouts" queue page with the three actions.

## 5. Cross-cutting rules
- Routes declared WITHOUT trailing slash; new prefixes added to `frontend/src/api/axios.ts` `noSlashEndpoints` (`/admin/withdrawals`, `/instructor/withdrawals`, `/my-orders` if any new prefix).
- Money amounts: rupees in DB (Numeric), paise only at the Razorpay boundary (`max(int(round(x*100)),100)` convention).
- Every mutating endpoint: one transaction, persist-intent-before-gateway-call, idempotent re-runs, explicit 409s.
- Never touch `backend/app/routers/payments_proxy.py` or `backend/tests/test_proxy_webhook_migration.py`.
- Tests are binding per feature: refund happy path + already-refunded 409 + gateway failure leaves access + bundle order revokes all its rows and nothing else + webhook convergence idempotent both admin-initiated and external; admin cancel both modes + gateway failure + pending discard; plan/bundle delete 409-vs-allowed; seat revoke matrix (pool-granted revoked, purchased row untouched, used_seats decrement floor, other company's pool 404); payouts balance math, min/over-balance 400s, state machine 409s, authz (student 403, other instructor's rows invisible).

## Follow-ups surfaced during the sale-price fix (not in this spec's tasks; track for the payment-hardening pass)
- Webhook (`webhook_processor.py`) and sweeper (`reconciliation.py`) fulfillment paths do not independently re-verify the captured amount against the expected price the way `/verify` does, and do not apply the seat-price cohort override when deriving discounts. Pre-existing; both paths key on `gateway_payment_id` idempotency, so the exposure is mis-recorded discount/subtotal fields rather than wrong access. Candidate for a shared `expected_amount_for_order(db, order_notes, course)` helper used by all three paths.

## Out of scope
Partial refunds, automatic bank transfers, refund of membership charges (use cancel), company-invoice refunds, GDPR account deletion, comment moderation, admin password reset (fix-wave), cart checkout.
