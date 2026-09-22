# B2B Company Invoicing & Seat Pools — Design Spec

**Date:** 2026-09-02
**Status:** Approved by owner (standing "proceed as per your recommendation")
**Sub-project:** 4 of 5. Builds on sub-projects 1–3. Implemented on branch
`company-invoicing` (forked from `bundles`) in worktree
`.worktrees/company-invoicing`.

## Product scope (owner-approved recommendation)

- **Admin-negotiated invoices:** admin raises an invoice against an approved
  company (line items: description, optional course OR bundle reference,
  qty, unit price). Companies pay online (Razorpay) or admin marks paid
  (bank transfer, with reference note).
- **GST-correct:** CGST+SGST when buyer state == seller state, IGST
  otherwise; sequential invoice numbers; PDF invoice. If the seller GSTIN
  is NOT configured, invoices issue as plain bills with zero tax lines
  (correct for an unregistered seller); configuring GSTIN enables tax
  automatically for later invoices (already-issued invoices never change).
- **Seat pools:** paid invoice lines that reference a course/bundle create
  seat pools; company managers assign seats to EXISTING platform users by
  email; assignment creates purchase-class enrollments.
- **Out of scope:** partial payments, credit notes/refund automation,
  e-invoicing/IRN, TDS, multi-currency, self-serve seat checkout, invoices
  to non-company entities.

## Data model

### `companies` (extended)
`gstin` varchar(20) default "", `legal_name` varchar(255) default "",
`billing_address` text default "", `state_code` varchar(2) default ""
(Indian GST state code, e.g. "33"). Editable by company owner + admin.

### Seller settings (`app/core/config.py`)
`SELLER_GSTIN` (default ""), `SELLER_LEGAL_NAME` (default ""),
`SELLER_ADDRESS` (default ""), `SELLER_STATE_CODE` (default ""),
`GST_RATE_PERCENT` (default 18.0). Documented in `.env.example`s.

### `company_invoices`
| Column | Notes |
|---|---|
| id | |
| `invoice_number` varchar(30) UNIQUE | `INV-<FY>-<NNNN>` sequential; FY = Indian fiscal year label (e.g. 2026-27 → "2627"); number allocated AT ISSUE time (drafts have none) under a row-lock/serialized counter (see Numbering) |
| company_id FK | |
| status enum | `DRAFT → ISSUED → PAID / CANCELLED` |
| `subtotal`, `cgst`, `sgst`, `igst`, `total` numeric(12,2) | snapshot at issue; never recomputed |
| `tax_note` varchar(200) | e.g. "CGST 9% + SGST 9%", "IGST 18%", or "No GST — seller unregistered" |
| `due_date` date nullable | |
| `issued_at`, `paid_at` timestamptz nullable | |
| `paid_via` varchar(20) default "" | "razorpay" / "bank_transfer" |
| `payment_reference` varchar(255) default "" | bank ref or gateway payment id |
| `pdf_path` varchar(500) default "" | generated at issue |
| `notes` text default "" | admin free text, shown on PDF |
| created_at / updated_at | |

### `company_invoice_items`
invoice_id FK indexed, description varchar(500), `course_id` nullable FK,
`bundle_id` nullable FK (at most one of the two set), `quantity` int > 0,
`unit_price` numeric(10,2), `line_total` numeric(12,2).

### `company_seat_pools`
company_id FK indexed, invoice_id FK, `course_id` nullable FK, `bundle_id`
nullable FK (exactly one set), `total_seats` int, `used_seats` int default
0. Created when the invoice transitions to PAID (one pool per
course/bundle-bearing line; description-only lines create no pool).

### `company_seat_assignments`
pool_id FK indexed, user_id FK, assigned_by FK users, assigned_at.
UNIQUE(pool_id, user_id). Each assignment consumes one seat and grants
enrollments.

### Numbering
`invoice_counters` table (fiscal_year varchar(4) PK, last_number int).
Issue path: `SELECT ... FOR UPDATE` on the counter row (Postgres; plain
read-update in SQLite tests), increment, format. Guarantees gapless-enough
sequential numbers per fiscal year without relying on max(invoice_number).

## Flows

### Draft → Issue
Admin creates a DRAFT (company + items + due date + notes). Editable while
draft. **Issue** validates: company approved, ≥1 item, all item course/
bundle refs exist. Then: compute tax snapshot (see GST), allocate invoice
number, render PDF, status ISSUED. Issued invoices are immutable except
status transitions; CANCELLED only from ISSUED and only while unpaid.

### GST computation (at issue, snapshot)
- Seller GSTIN blank → cgst=sgst=igst=0, tax_note "No GST — seller
  unregistered", total = subtotal.
- Else if company.state_code == SELLER_STATE_CODE and both non-blank →
  CGST = SGST = subtotal × rate/2.
- Else → IGST = subtotal × rate.
- Amounts rounded to 2dp; total = subtotal + taxes. Buyer GSTIN/state
  printed on the PDF when present.

### Payment — online
Company portal "Pay now" on an ISSUED invoice → `create-order` gains a
third target: `invoice_id` (mutually exclusive with course_id/bundle_id;
company-owner/manager auth; amount = invoice.total server-side; notes =
`{invoice_id, user_id}`). `/verify` gains the matching branch (HMAC, notes
match, amount recompute from the invoice row). Webhook `payment.captured`
and the sweeper recognize `invoice_id` notes. All three routes converge on
`settle_invoice(db, invoice, via, reference)` — idempotent (no-op unless
ISSUED), writes Order+Payment (`payment_method="razorpay_invoice"`,
`Order.total = invoice.total`, one OrderItem per invoice line with
course_id when present), sets PAID/paid_at/paid_via/reference, creates
seat pools.

### Payment — offline
Admin "mark paid" with reference → same `settle_invoice` with
via="bank_transfer" (no Razorpay involved; Order+Payment rows written with
gateway ids empty and `payment_method="bank_transfer"` — the unique
gateway_payment_id partial index ignores empty strings by design).

### Seat assignment
Company owner/manager, on a pool with free seats, submits a platform user
email. Validations: user exists (404 with "ask them to sign up first"
detail), not already assigned to this pool (409), pool not exhausted
(409). Effect: assignment row + `used_seats += 1` atomically; enrollment
grant: course pools → the bundle-rescue semantics (existing row of any
source → re-enroll + stamp order_id when NULL; else create with
`enrollment_source="company"`, order_id = the invoice's order); bundle
pools → `fulfill`-style grant across the bundle's CURRENT courses via the
same rescue helper (company seats are assigned post-purchase, so current
contents are correct here — unlike buyer bundles there is no per-buyer
snapshot). Assignments are permanent once made (seat consumed).

### PDF
reportlab (already a dependency; certificate_service shows the pattern).
Layout: seller block (legal name, address, GSTIN), buyer block (company
legal name/name, address, GSTIN, state), invoice number/date/due date,
items table, subtotal/tax/total, tax_note, notes, "computer-generated"
footer. Stored under `certificates/`-style dir: `invoices/` bind-safe path
`backend`-relative `invoices/INV-xxxx.pdf` served via an authenticated
download endpoint (NOT a public static mount — invoices are private).

## API

Admin (`/api/v1/admin/company-invoices`, require_admin):
- `POST /` create draft; `GET /` list (status filter); `GET /{id}` detail;
  `PATCH /{id}` edit draft (items replaceable); `POST /{id}/issue`;
  `POST /{id}/cancel`; `POST /{id}/mark-paid {reference}`;
  `GET /{id}/pdf` download.

Company portal (`/api/v1/companies/billing`, company owner/manager auth —
reuse the existing company-scoped dependency in companies.py):
- `GET /profile` + `PATCH /profile` (gstin/legal_name/billing_address/
  state_code); `GET /invoices`; `GET /invoices/{id}/pdf`;
  `POST /invoices/{id}/pay` → Razorpay order payload;
  `GET /seat-pools`; `POST /seat-pools/{id}/assign {email}`;
  `GET /seat-pools/{id}/assignments`.

## Frontend

- Company portal (company dashboard area): Billing page — billing profile
  form, invoices table (number, date, total, status, PDF, Pay now via the
  existing Razorpay pattern with invoice verify), seat pools with
  assign-by-email + assignment list.
- Admin: Company Invoices page — list + create/edit draft (company select,
  line items editor with optional course/bundle pickers), issue/cancel/
  mark-paid actions, PDF link. Nav beside Bundles.

## Testing

GST math (same-state, inter-state, unregistered); numbering sequence +
fiscal-year rollover; draft immutability after issue; settle_invoice
idempotent (verify+webhook race, double mark-paid no-op); online payment
via all three routes (mirror bundle webhook tests with invoice notes);
offline mark-paid writes Order+Payment without gateway ids; pool creation
per line; assignment validations (missing user, duplicate, exhaustion);
assignment grants incl. rescue of suspended rows; PDF generated and
non-empty; company-scoped auth (a company cannot see another's invoices).

## Ops at launch

Run `backend/migrations/add_company_invoicing_tables.sql`; set the
SELLER_* settings in production `.env` (leave GSTIN blank until you are
GST-registered); no Razorpay dashboard changes.

**Invoice PDF volume (required).** `invoice_pdf.render_invoice_pdf` writes
to a CWD-relative `invoices/` directory. Without a bind mount for it, every
issued invoice PDF is container-ephemeral and disappears on redeploy —
these are legal documents. Create `./invoices` on the host and mount it at
the backend's CWD-relative path, which differs per stack:

- `docker-compose.production.yml` → `./invoices:/app/backend/invoices`
  (supervisord runs the backend with `directory=/app/backend`).
- `deploy/docker-compose.app.yml` and `docker-compose.prod.yml` →
  `./invoices:/app/invoices` (the backend image's `WORKDIR` is `/app`).

Both PDF endpoints (`GET /api/v1/admin/company-invoices/{id}/pdf` and
`GET /api/v1/companies/billing/invoices/{id}/pdf`) go through
`invoice_pdf.ensure_invoice_pdf`, which re-renders an ISSUED/PAID invoice
from its stored snapshot if the file is missing. That is a safety net for a
mount that was forgotten or a volume that was recreated — it is not a
substitute for the mount.
