# Fee collection: cash desk, invoices and receipts, cash verification, online payment

Date: 2026-09-12. Status: pending owner approval. Migration: 0043.

## Goal

Let a campus collect fees three ways and prove every rupee:

1. **At the counter** (cash, cheque, UPI shown on a phone, bank transfer) with a
   printable numbered receipt and a second person confirming the cash was received.
2. **Demand invoice** before payment, printable, for one installment or the whole balance.
3. **Online through Razorpay** from the student or parent fee page, posted through the
   same ledger path as counter payments so receipts, reminders and reports behave the same.

"Offline" in this build means "paid without the gateway". The app still needs a
connection; the counter prints receipts and invoices from the browser.

## Decisions (owner, 12 Sep 2026)

- Offline = counter payments, not a no-internet mode.
- Receiver confirmation = cashier records, a second owner/admin verifies after counting.
- Invoice = demand invoice before payment plus receipt after each payment, both PDF.
- Razorpay online payment ships in the same build.

## What exists today

- `tuition_payments` already carries `method` (cash, bank_transfer, card, upi, cheque,
  online), `reference`, `recorded_by`, and a numbered `tuition_receipts` row per payment.
- `record_payment` is idempotent, balance-guarded, allocates credit through
  `_allocate_credit`, audits, and queues receipt notices via `tuition_reminders.queue_receipt`.
- No PDF for receipts. No invoice concept. `recorded_by` is stored but never shown.
- Razorpay client, HMAC verify, `/api/v1/payments/webhook` and `webhook_processor`
  exist for course purchases. Exam papers show the per-row `gateway_order_id` pattern
  (`exam_papers.py` create, verify, reconcile; `exam_paper_service.fulfill_capture`).
- `Institution` has name, academic year, timezone. No address or GST fields.

## Data (migration 0043, reversible)

### `tuition_payments` new columns

| column | type | rule |
|---|---|---|
| `received_by` | FK users, nullable | Who physically took the money. Required for cash and cheque. Null for online. |
| `verification_status` | string(20) | `not_required` (card, upi, bank_transfer, online) or `pending` / `verified` (cash, cheque). Check constraint. |
| `verified_by` | FK users, nullable | Set on verify. |
| `verified_at` | datetime tz, nullable | Set on verify. |
| `verification_note` | string(300), default "" | Optional counting note. |

Index `ix_tuition_payment_verification` on (`institution_id`, `verification_status`, `paid_at`).
Existing rows backfill: `received_by = recorded_by`, status `verified` for cash/cheque
(history is treated as already counted) and `not_required` otherwise.

### `tuition_invoices` (demand invoices)

institution_id, assignment_id, installment_id (nullable = whole balance), invoice_number
(`TI-{institution}-{year}-{seq:06d}`, unique), amount, currency, due_on, lines_json
(snapshot of installment name, due, amount due, credited, balance), issued_by, issued_at.
An invoice is a snapshot of what was owed when it was issued. It never changes the ledger.
Status is derived at read time from the current balance (`open` or `settled`).

### `tuition_online_orders`

institution_id, assignment_id, installment_id (nullable), payer_user_id, gateway_order_id
(unique), gateway_payment_id (nullable, unique), payment_id (FK tuition_payments, nullable),
amount, amount_paise, currency, status (`created`, `paid`, `paid_excess`, `failed`),
excess_amount (default 0), created_at, paid_at.

## Behaviour

### Counter payment and receiver

- `TuitionPaymentCreate` gains `received_by_member_id: int | None`. For cash and cheque it
  is required and must be an active owner, admin or teacher of the institution. Other
  methods ignore it.
- `record_payment` sets `verification_status` by method. Receipt output and receipt PDF
  show "Received by {name}" and the verification stamp.

### Cash verification

- `POST /{iid}/fees/payments/{payment_id}/verify` body `{note}`. Owner or admin only.
- The verifier must not be the receiver. If the institution has exactly one active
  owner/admin and that person is the receiver, self-verification is allowed and the
  audit records `self_verified_sole_manager`. This keeps one-person offices unblocked
  while still leaving a trail.
- Verifying a non-pending payment returns 409. Reversed payments cannot be verified.
- `GET /{iid}/fees/cash?day=YYYY-MM-DD` returns the local-day cash desk: every cash and
  cheque payment that day, per-receiver totals, pending and verified totals, and any
  online orders in `paid_excess`. `GET .../cash/csv` exports the same.
- Today (manager branch): `system-cash-verification` card when any cash or cheque
  payment is pending, showing count and total, linking to `?view=finance&panel=cash`.
  `system-online-excess` card when any order is `paid_excess`.

### Documents

- `GET /{iid}/fees/receipts/{receipt_id}/pdf`: A4 receipt via reportlab in
  `campus_report_pdf.build_fee_receipt_pdf`. Fields: campus name, academic year, receipt
  number, student, plan, installment allocations, amount in figures, method, reference,
  paid at (campus timezone), received by, verification stamp, balance after. Same access
  rule as `receipt_detail` (manager, the student, approved parent).
- `POST /{iid}/fees/assignments/{aid}/invoices` body `{installment_id | null}` creates a
  demand invoice. Managers, the student and approved parents may create one for that
  account. 422 when the chosen installment or the account has no balance.
- `GET /{iid}/fees/invoices/{id}` and `GET .../invoices/{id}/pdf`: same access rule.
  `GET /{iid}/fees/assignments/{aid}/invoices` lists them for the account.
- The PDF header uses institution name and academic year only. There are no address or
  GST fields on the institution today, so the PDF leaves a "Registered details" line blank.
  Adding those fields is a separate change.

### Online payment (Razorpay)

- `POST /{iid}/fees/assignments/{aid}/online-orders` body `{installment_id | null, amount | null}`.
  Payer must be the student, an approved parent, or a manager. Amount defaults to the
  installment balance (or whole balance); must be > 0 and at most that balance. Returns 503
  "Online payment is not set up for this campus yet" when Razorpay keys are missing, and
  503 "Checkout could not start" when the gateway call fails. Creates the Razorpay order
  with `receipt = tf-{order id}` and notes `{tuition_order_id, institution_id}`. Response:
  `{order: {...}, checkout: {key, order_id, amount_paise, currency, name, description, prefill: {name, email}}}`.
- `POST /{iid}/fees/online-orders/{id}/verify` body `{razorpay_order_id, razorpay_payment_id, razorpay_signature}`:
  HMAC over `order|payment` with the key secret, fetch the payment entity, then
  `fulfil_online_order`.
- `POST /{iid}/fees/online-orders/{id}/reconcile`: lists the order's payments at Razorpay
  and fulfils a captured one. Covers the closed-browser case from the client side.
- Webhook: `webhook_processor._handle_payment_captured` checks
  `TuitionOnlineOrder.gateway_order_id == entity.order_id` before the generic `Payment`
  lookup and calls `fulfil_online_order`. No new webhook route.
- `fulfil_online_order(db, order, entity)`: locks the order; requires `status == captured`,
  matching order id, INR, `amount == amount_paise`, no refund; no-op when already paid with
  the same payment id; ValueError when a different payment id is attached.
  Posts the payment through a shared core `_post_payment(...)` (extracted from
  `record_payment`) with `method="online"`, `reference=gateway payment id`,
  `recorded_by=payer`, `idempotency_key=f"rzp:{payment id}"`, `verification_status="not_required"`.
  If the balance has dropped below the captured amount in the meantime (a counter payment
  landed first), it posts what fits, stores the remainder in `excess_amount`, sets
  `paid_excess`, and the office sees it on the cash desk and on Today for a manual refund.
  The gateway money is never silently lost and the ledger is never overpaid.
- Reminders: when Razorpay is configured, reminder messages append one line
  "Pay online: {portal url}" pointing at the learner fee page.

### Frontend

- Manager Finance
  - Record payment dialog: "Received by" select (active owner/admin/teacher members,
    defaults to me), shown only for cash and cheque.
  - New "Cash desk" panel: date picker, table of the day's cash and cheque payments with
    receiver, amount, status, "Verify" button opening a note dialog, per-receiver totals,
    pending total, "Export CSV". Excess online orders listed with a "Refund manually" note.
  - Each receipt row: "Receipt PDF". Each installment row and the account header:
    "Invoice PDF" (creates then opens).
- Learner Finance (student and parent)
  - Each unpaid installment: "Pay online" and "Invoice PDF". Account header: "Pay balance".
  - Checkout loads `https://checkout.razorpay.com/v1/checkout.js` on demand (same loader
    as `bundle-detail.tsx`), opens Razorpay, on success calls verify and refetches. On
    dismiss it calls reconcile once, so a payment that completed at the gateway still posts.
  - 503 shows a plain notice "Online payment is not set up for this campus yet. Pay at the
    office or ask them to enable it." and the buttons stay visible but disabled.
  - Receipt rows: "Receipt PDF".
- Parent portal fee tile: "Pay now" link to the child's fee page when balance > 0.
- `campus-os.ts` gains the new calls; no new nav entry; no new noSlash prefix.

### Audit

Every write audits through `institution_service.audit`: `tuition.payment.verified`,
`tuition.invoice.issued`, `tuition.online_order.created`, `tuition.online_order.paid`,
`tuition.online_order.excess`.

## Testing

Backend (`tests/test_fee_collection.py`):
1. Cash payment requires receiver, sets pending; card sets not_required.
2. Verify by a different manager succeeds, by the receiver is 409, sole-manager self-verify passes with audit tag, teacher is 403, other campus is 404.
3. Cash desk report groups by receiver and totals; CSV downloads with ASCII filename.
4. Receipt PDF returns `%PDF` bytes for manager, student, approved parent; unrelated parent 404.
5. Invoice create for one installment and whole balance; PDF bytes; 422 when nothing due; listing.
6. Online order 503 when keys unset; with monkeypatched client, create returns checkout; verify with correct HMAC posts a payment with method online and receipt; wrong HMAC 400; replay is a no-op.
7. Webhook path: `_handle_payment_captured` with a tuition order fulfils it.
8. Excess: counter payment lands first, capture posts the remainder and marks paid_excess; Today shows both system cards.
9. Migration 0043 round-trip on scratch SQLite with stub parents.

Frontend (`__tests__/fee-collection.test.tsx`): manager cash desk renders pending rows and
verify calls the API; learner "Pay online" calls create-order and opens checkout (mocked
`window.Razorpay`); 503 renders the notice with disabled buttons; receipt and invoice
buttons call the blob openers.

Browser walk: owner records cash with receiver, second admin verifies, receipt PDF and
invoice PDF open; student sees Pay online with the honest 503 (no keys in preview);
parent portal shows Pay now.

## Out of scope

Refund execution through the gateway (manual for now), GST or address on invoices, a
no-internet counter mode, cheque bounce handling.
