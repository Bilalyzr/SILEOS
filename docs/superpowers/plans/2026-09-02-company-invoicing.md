# B2B Company Invoicing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admin-negotiated GST invoices for companies, payable online through the hardened Razorpay pipeline or marked paid offline, with paid invoices becoming seat pools that company managers assign to platform users.

**Architecture:** New tables (`company_invoices`, `company_invoice_items`, `company_seat_pools`, `company_seat_assignments`, `invoice_counters`) + billing columns on `companies` + SELLER_* settings. An `invoice_service` owns GST math, sequential numbering, and the idempotent `settle_invoice` (Order+Payment + pools); a shared `grant_purchased_course` helper in `fulfillment_service` (extracted from the bundle rescue loop) powers seat-assignment enrollments. `create-order`/`/verify`/webhook/sweeper gain an `invoice_id` target. reportlab renders the PDF; downloads are authenticated endpoints, never public mounts.

**Tech Stack:** FastAPI + SQLAlchemy sync + Pydantic 2, razorpay SDK, reportlab, pytest (shared venv), React 18 + TS.

**Spec:** `docs/superpowers/specs/2026-09-02-company-invoicing-design.md`

## Global Constraints

- Branch `company-invoicing` forked from `bundles`, worktree `.worktrees/company-invoicing`. Backend paths relative to `<worktree>/backend/`.
- Tests: from `<worktree>/backend/`, `"C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe" -m pytest tests/<files> -v`. Baseline ~45 pre-existing failures / 4 errors; gate = zero NEW failures. Frontend type-check baseline 391 errors, zero new.
- No Alembic: models + SQL file `backend/migrations/add_company_invoicing_tables.sql`.
- Money authority server-side: invoice totals snapshot at issue, never recomputed; online payment amount = invoice.total from the DB row.
- Idempotency: `settle_invoice` no-ops unless status ISSUED; gateway payments keyed on the unique `gateway_payment_id` partial index (empty string = exempt, used by bank transfers).
- Issued invoices immutable (except status transitions ISSUED→PAID / ISSUED→CANCELLED while unpaid).
- Enrollment grants use `grant_purchased_course` rescue semantics: existing row of any source → re-enroll + stamp order_id when NULL, source preserved; else create with the given source + order_id. Purchase-class rows are never suspendable (order_id set).
- Invoice PDFs are PRIVATE: authenticated download endpoints only; files under `<backend>/invoices/` (create dir at write time, os.makedirs exist_ok).
- Company access control: every company-portal endpoint resolves the caller's company via the existing pattern (`AuthService.require_company` / `require_company_or_manager` + the CompanyManager link used in company_dashboard.py — read it) and must never expose another company's data.
- Never touch payments_proxy.py / test_proxy_webhook_migration.py.
- Commit trailer: blank line then `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Models, settings, migration

**Files:**
- Create: `app/models/company_invoice.py`
- Modify: `app/models/company.py` (4 billing columns), `app/models/__init__.py`, `app/core/config.py` (SELLER_* + GST_RATE_PERCENT), `.env.example` + `backend/.env.example` (document settings)
- Create: `backend/migrations/add_company_invoicing_tables.sql`
- Test: `backend/tests/test_invoice_models.py`

**Interfaces:**
- Produces from `app.models.company_invoice`: `CompanyInvoice(id, invoice_number UNIQUE nullable, company_id, status: InvoiceStatus, subtotal, cgst, sgst, igst, total Numeric(12,2), tax_note, due_date, issued_at, paid_at, paid_via, payment_reference, pdf_path, notes, created_at, updated_at)`, `InvoiceStatus` enum `DRAFT/ISSUED/PAID/CANCELLED`, `CompanyInvoiceItem(invoice_id indexed, description, course_id nullable FK, bundle_id nullable FK, quantity, unit_price Numeric(10,2), line_total Numeric(12,2))`, `CompanySeatPool(company_id indexed, invoice_id, order_id nullable FK orders.id, course_id nullable, bundle_id nullable, total_seats, used_seats default 0)` — order_id is stamped by settle_invoice and used by seat assignment to give enrollments purchase-class order backing, `CompanySeatAssignment(pool_id indexed, user_id, assigned_by, assigned_at; UNIQUE(pool_id, user_id))`, `InvoiceCounter(fiscal_year varchar(4) PK, last_number int)`.
- Company gains: `gstin` varchar(20) "", `legal_name` varchar(255) "", `billing_address` Text "", `state_code` varchar(2) "".
- Settings: `SELLER_GSTIN`, `SELLER_LEGAL_NAME`, `SELLER_ADDRESS`, `SELLER_STATE_CODE` (str, default ""), `GST_RATE_PERCENT` (float, default 18.0) — Field(default=..., env=...) style matching ADMIN_EMAIL at config.py:140.

- [ ] **Step 1: Failing test**

```python
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatAssignment,
    CompanySeatPool, InvoiceCounter, InvoiceStatus,
)


def _company(db, owner):
    from app.models.company import Company
    c = Company(owner_user_id=owner.id, name="Acme", slug="acme",
                contact_email="a@acme.test", is_approved=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_invoice_roundtrip_defaults(db, student_user):
    co = _company(db, student_user)
    inv = CompanyInvoice(company_id=co.id, subtotal=1000, total=1000)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(invoice_id=inv.id, description="Seats",
                              quantity=10, unit_price=100, line_total=1000))
    db.commit()
    db.refresh(inv)
    assert inv.status == InvoiceStatus.DRAFT
    assert inv.invoice_number is None
    assert co.gstin == "" and co.state_code == ""


def test_assignment_unique_per_pool(db, student_user):
    co = _company(db, student_user)
    inv = CompanyInvoice(company_id=co.id, subtotal=0, total=0)
    db.add(inv)
    db.flush()
    pool = CompanySeatPool(company_id=co.id, invoice_id=inv.id,
                           course_id=None, bundle_id=None, total_seats=5)
    db.add(pool)
    db.flush()
    db.add(CompanySeatAssignment(pool_id=pool.id, user_id=student_user.id,
                                 assigned_by=student_user.id))
    db.commit()
    db.add(CompanySeatAssignment(pool_id=pool.id, user_id=student_user.id,
                                 assigned_by=student_user.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_counter_and_settings(db):
    db.add(InvoiceCounter(fiscal_year="2627", last_number=0))
    db.commit()
    from app.core.config import get_settings
    s = get_settings()
    assert s.GST_RATE_PERCENT == 18.0
    assert s.SELLER_GSTIN == ""
```

- [ ] **Step 2: Run** `... -m pytest tests/test_invoice_models.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement.** Model file mirrors the interface block above exactly (SQLAlchemy style per app/models/membership.py: `Enum(InvoiceStatus)` default DRAFT, `Numeric` from sqlalchemy.types, timestamps via func.now(), `UniqueConstraint("pool_id", "user_id", name="uq_seat_assignment_pool_user")` in `__table_args__`). Company columns appended after `contact_phone`. Settings after ADMIN_EMAIL. Register module in `__init__.py`.

- [ ] **Step 4: Run** → 3 passed; regression `tests/test_bundle_models.py tests/test_membership_models.py` green.

- [ ] **Step 5: Migration** `backend/migrations/add_company_invoicing_tables.sql` — CREATE TABLE IF NOT EXISTS for the five tables (status VARCHAR(20) DEFAULT 'DRAFT' storing enum NAMES, invoice_number VARCHAR(30) UNIQUE, all Numeric→NUMERIC, UNIQUE(pool_id, user_id)), ALTER TABLE companies ADD COLUMN IF NOT EXISTS × 4, indexes on company_invoice_items.invoice_id, company_seat_pools.company_id, company_seat_assignments.pool_id.

- [ ] **Step 6: Commit** — `feat: company invoicing models, billing columns, seller settings`

---

### Task 2: Shared purchase-grant helper + invoice service (GST, numbering, settle)

**Files:**
- Modify: `app/services/fulfillment_service.py` (extract `grant_purchased_course`; refactor bundle loop to use it)
- Create: `app/services/invoice_service.py`
- Test: `backend/tests/test_invoice_service.py`

**Interfaces:**
- Produces in fulfillment_service:
```python
grant_purchased_course(db, *, user_id: int, course_id: int, order_id: int,
                       source: str) -> bool  # True when newly enrolled or re-enrolled from non-enrolled
```
  Semantics = the bundle rescue loop verbatim: existing (user, course) row → status "enrolled" if not already + stamp order_id when NULL + NEVER rewrite enrollment_source, return True only if it wasn't enrolled; no row → create (status enrolled, given source, order_id) + bump Course.total_enrollments, return True. The bundle loop in `fulfill_bundle_purchase` is refactored to call it (source="bundle") with behavior byte-equivalent — its tests must pass unchanged.
- Produces in invoice_service:
```python
compute_gst(company, settings) -> tuple[Decimal cgst, Decimal sgst, Decimal igst, str tax_note]  # on a subtotal passed in: signature compute_gst(subtotal: float, company, settings)
allocate_invoice_number(db, now: datetime) -> str      # INV-<FY4>-<NNNN>, InvoiceCounter row-locked on postgres
issue_invoice(db, invoice) -> None                     # validate, snapshot tax, number, render PDF (Task 3 renderer injected via callable param pdf_renderer=None default), status ISSUED; raises ValueError on bad state
settle_invoice(db, invoice, *, via: str, reference: str, gateway_payment_id: str = "", gateway_order_id: str = "") -> bool
```
  `settle_invoice`: returns False (no-op) unless ISSUED; writes Order (payment_method = "razorpay_invoice" if via=="razorpay" else "bank_transfer", total = invoice.total, billing company name) + one OrderItem per invoice line (course_id when set, order_item_type="invoice_item", subtotal=line_total, total=line_total) + Payment (gateway ids as given — empty for bank transfer; amount=total, COMPLETED); creates one CompanySeatPool per line with course_id or bundle_id set (total_seats=quantity); sets PAID/paid_at/paid_via/payment_reference; does NOT commit. When gateway_payment_id is non-empty, first check `Payment.gateway_payment_id` exists → return False (idempotent replay).
- Fiscal year: `fy = year if month >= 4 else year - 1; label = f"{fy % 100:02d}{(fy + 1) % 100:02d}"`.

- [ ] **Step 1: Failing tests**

```python
from datetime import datetime, timezone
from decimal import Decimal

from app.core.config import get_settings
from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatPool, InvoiceStatus,
)
from app.models.enrollment import Enrollment
from app.models.payment import Order, Payment
from app.services.fulfillment_service import grant_purchased_course
from app.services.invoice_service import (
    allocate_invoice_number, compute_gst, issue_invoice, settle_invoice,
)
from tests.test_invoice_models import _company


def _invoice(db, co, course=None, qty=5, unit=200.0):
    inv = CompanyInvoice(company_id=co.id, subtotal=qty * unit, total=qty * unit)
    db.add(inv)
    db.flush()
    db.add(CompanyInvoiceItem(
        invoice_id=inv.id, description="Seats",
        course_id=course.id if course else None,
        quantity=qty, unit_price=unit, line_total=qty * unit))
    db.commit()
    db.refresh(inv)
    return inv


def test_gst_matrix(db, student_user, monkeypatch):
    co = _company(db, student_user)
    s = get_settings()
    # unregistered seller
    monkeypatch.setattr(s, "SELLER_GSTIN", "", raising=False)
    cgst, sgst, igst, note = compute_gst(1000.0, co, s)
    assert (cgst, sgst, igst) == (Decimal("0.00"),) * 3 or (float(cgst), float(sgst), float(igst)) == (0, 0, 0)
    assert "unregistered" in note.lower()
    # same state
    monkeypatch.setattr(s, "SELLER_GSTIN", "33AAAAA0000A1Z5", raising=False)
    monkeypatch.setattr(s, "SELLER_STATE_CODE", "33", raising=False)
    co.state_code = "33"
    cgst, sgst, igst, note = compute_gst(1000.0, co, s)
    assert float(cgst) == 90.0 and float(sgst) == 90.0 and float(igst) == 0
    # inter-state
    co.state_code = "29"
    cgst, sgst, igst, note = compute_gst(1000.0, co, s)
    assert float(igst) == 180.0 and float(cgst) == 0


def test_numbering_sequence_and_fy(db):
    n1 = allocate_invoice_number(db, datetime(2026, 9, 1, tzinfo=timezone.utc))
    n2 = allocate_invoice_number(db, datetime(2026, 9, 2, tzinfo=timezone.utc))
    n3 = allocate_invoice_number(db, datetime(2027, 4, 1, tzinfo=timezone.utc))
    assert n1 == "INV-2627-0001" and n2 == "INV-2627-0002"
    assert n3 == "INV-2728-0001"


def test_issue_then_settle_creates_pools_and_money(db, student_user, course):
    co = _company(db, student_user)
    inv = _invoice(db, co, course=course)
    issue_invoice(db, inv, pdf_renderer=lambda i: "invoices/test.pdf")
    db.commit()
    assert inv.status == InvoiceStatus.ISSUED and inv.invoice_number
    assert settle_invoice(db, inv, via="bank_transfer", reference="NEFT-1") is True
    db.commit()
    assert inv.status == InvoiceStatus.PAID
    pool = db.query(CompanySeatPool).one()
    assert pool.course_id == course.id and pool.total_seats == 5
    assert db.query(Order).count() == 1 and db.query(Payment).count() == 1
    # idempotent: already PAID
    assert settle_invoice(db, inv, via="bank_transfer", reference="NEFT-1") is False
    assert db.query(Order).count() == 1


def test_settle_replay_by_gateway_id_noop(db, student_user, course):
    co = _company(db, student_user)
    inv = _invoice(db, co, course=course)
    issue_invoice(db, inv, pdf_renderer=lambda i: "x.pdf")
    db.commit()
    assert settle_invoice(db, inv, via="razorpay", reference="pay_I1",
                          gateway_payment_id="pay_I1") is True
    db.commit()
    inv.status = InvoiceStatus.ISSUED  # simulate replayed webhook racing state
    db.commit()
    assert settle_invoice(db, inv, via="razorpay", reference="pay_I1",
                          gateway_payment_id="pay_I1") is False


def test_grant_purchased_course_rescues(db, student_user, course, order_row):
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="suspended",
                      enrollment_source="membership"))
    db.commit()
    assert grant_purchased_course(db, user_id=student_user.id,
                                  course_id=course.id,
                                  order_id=order_row.id, source="company") is True
    db.commit()
    row = db.query(Enrollment).one()
    assert row.enrollment_status == "enrolled"
    assert row.enrollment_source == "membership"  # source preserved
    assert row.order_id == order_row.id
```

- [ ] **Step 2: Run** → ImportError.

- [ ] **Step 3: Implement.** `grant_purchased_course` is extracted from the bundle loop in `fulfill_bundle_purchase` (READ it; keep the loop's semantics identical by delegating; keep the loop's `existing` prefetch optimization by allowing the helper to accept a preloaded row via optional `_row=...` param OR simply query per course inside the helper — correctness over micro-optimization; bundle tests must stay green). `invoice_service.py`:

```python
"""Invoice lifecycle: GST snapshot, sequential numbering, settlement.

settle_invoice is the single convergence point for ALL payment routes
(online verify/webhook/sweeper and offline mark-paid) — idempotent via
status gate + gateway_payment_id check. Callers commit.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_invoice import (
    CompanyInvoice, CompanyInvoiceItem, CompanySeatPool, InvoiceCounter,
    InvoiceStatus,
)
from app.models.payment import Order, OrderItem, OrderStatus, Payment, PaymentStatus

logger = logging.getLogger(__name__)

_TWO = Decimal("0.01")


def _d(x) -> Decimal:
    return Decimal(str(x)).quantize(_TWO, rounding=ROUND_HALF_UP)


def compute_gst(subtotal: float, company: Company, settings):
    sub = _d(subtotal)
    rate = Decimal(str(settings.GST_RATE_PERCENT)) / Decimal("100")
    zero = _d(0)
    if not (settings.SELLER_GSTIN or "").strip():
        return zero, zero, zero, "No GST — seller unregistered"
    seller_state = (settings.SELLER_STATE_CODE or "").strip()
    buyer_state = (company.state_code or "").strip()
    if seller_state and buyer_state and seller_state == buyer_state:
        half = _d(sub * rate / 2)
        pct = settings.GST_RATE_PERCENT / 2
        return half, half, zero, f"CGST {pct:g}% + SGST {pct:g}%"
    return zero, zero, _d(sub * rate), f"IGST {settings.GST_RATE_PERCENT:g}%"


def fiscal_year_label(now: datetime) -> str:
    fy = now.year if now.month >= 4 else now.year - 1
    return f"{fy % 100:02d}{(fy + 1) % 100:02d}"


def allocate_invoice_number(db: Session, now: datetime) -> str:
    fy = fiscal_year_label(now)
    q = db.query(InvoiceCounter).filter(InvoiceCounter.fiscal_year == fy)
    if db.bind.dialect.name == "postgresql":
        q = q.with_for_update()
    counter = q.first()
    if counter is None:
        counter = InvoiceCounter(fiscal_year=fy, last_number=0)
        db.add(counter)
        db.flush()
    counter.last_number += 1
    return f"INV-{fy}-{counter.last_number:04d}"


def issue_invoice(db: Session, invoice: CompanyInvoice, *, pdf_renderer=None) -> None:
    if invoice.status != InvoiceStatus.DRAFT:
        raise ValueError("Only draft invoices can be issued")
    items = db.query(CompanyInvoiceItem).filter(
        CompanyInvoiceItem.invoice_id == invoice.id).all()
    if not items:
        raise ValueError("Invoice has no items")
    company = db.query(Company).filter(Company.id == invoice.company_id).one()
    from app.core.config import get_settings
    settings = get_settings()
    subtotal = _d(sum(float(i.line_total) for i in items))
    cgst, sgst, igst, note = compute_gst(float(subtotal), company, settings)
    invoice.subtotal = subtotal
    invoice.cgst, invoice.sgst, invoice.igst = cgst, sgst, igst
    invoice.total = _d(subtotal + cgst + sgst + igst)
    invoice.tax_note = note
    now = datetime.now(timezone.utc)
    invoice.invoice_number = allocate_invoice_number(db, now)
    invoice.issued_at = now
    invoice.status = InvoiceStatus.ISSUED
    if pdf_renderer is not None:
        invoice.pdf_path = pdf_renderer(invoice) or ""


def settle_invoice(db: Session, invoice: CompanyInvoice, *, via: str,
                   reference: str, gateway_payment_id: str = "",
                   gateway_order_id: str = "") -> bool:
    if gateway_payment_id and db.query(Payment).filter(
            Payment.gateway_payment_id == gateway_payment_id).first():
        return False
    if invoice.status != InvoiceStatus.ISSUED:
        return False
    company = db.query(Company).filter(Company.id == invoice.company_id).one()
    items = db.query(CompanyInvoiceItem).filter(
        CompanyInvoiceItem.invoice_id == invoice.id).all()
    now = datetime.now(timezone.utc)
    method = "razorpay_invoice" if via == "razorpay" else "bank_transfer"
    order = Order(
        user_id=company.owner_user_id,
        order_key=f"INV_{invoice.invoice_number or invoice.id}",
        order_status=OrderStatus.COMPLETED,
        currency="INR",
        subtotal_amount=invoice.subtotal, total_amount=invoice.total,
        payment_method=method,
        payment_method_title=f"Invoice {invoice.invoice_number or ''}".strip(),
        transaction_id=gateway_payment_id or reference,
        billing_company=company.legal_name or company.name,
        billing_email=company.contact_email or "",
        date_paid=now, date_completed=now,
    )
    db.add(order)
    db.flush()
    for it in items:
        db.add(OrderItem(order_id=order.id, course_id=it.course_id,
                         order_item_name=it.description,
                         order_item_type="invoice_item",
                         quantity=it.quantity,
                         subtotal=it.line_total, total=it.line_total))
        if it.course_id or it.bundle_id:
            db.add(CompanySeatPool(
                company_id=company.id, invoice_id=invoice.id,
                order_id=order.id,
                course_id=it.course_id, bundle_id=it.bundle_id,
                total_seats=it.quantity))
    db.add(Payment(user_id=company.owner_user_id, order_id=order.id,
                   payment_method=method,
                   gateway_transaction_id=gateway_payment_id,
                   gateway_payment_id=gateway_payment_id,
                   gateway_order_id=gateway_order_id,
                   amount=invoice.total, currency="INR",
                   payment_status=PaymentStatus.COMPLETED,
                   processed_date=now))
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = now
    invoice.paid_via = via
    invoice.payment_reference = reference
    return True
```

CHECK: `OrderItem.course_id` is `nullable=False` (verified in sub-project 2) — description-only lines have `course_id=None`, which would violate it. Adaptation REQUIRED: for items with `course_id is None`, SKIP the OrderItem row (Order+Payment carry the money; note it in a comment, same precedent as subscription orders). Bundle-ref items also have course_id None → also skipped as OrderItems (pool still created). Adjust the plan test if it asserts OrderItem counts (it doesn't).

Also verify `Order.billing_company` exists on the Order model (it does — WooCommerce columns); if the exact name differs, use the actual column.

- [ ] **Step 4: Run** → 5 passed + `tests/test_bundle_fulfillment.py` unchanged green (refactor gate).

- [ ] **Step 5: Commit** — `feat: invoice service (GST, numbering, settle) + shared purchase-grant helper`

---

### Task 3: PDF renderer + admin invoice API

**Files:**
- Create: `app/services/invoice_pdf.py`, `app/schemas/company_invoice.py`
- Modify: `app/routers/admin.py` (invoice endpoints), `app/main.py` (nothing new to mount — admin router already mounted)
- Test: `backend/tests/test_invoice_admin_api.py`

**Interfaces:**
- `render_invoice_pdf(db, invoice) -> str` (relative path `invoices/INV-....pdf`; reportlab canvas/platypus per certificate_service patterns; seller block from settings, buyer block from company, items table, totals + tax_note, notes, footer). Writes under `<backend cwd>/invoices/` with os.makedirs(exist_ok=True).
- Admin endpoints (require_admin) under `/api/v1/admin/company-invoices`:
  - `POST /` `InvoiceCreate {company_id, due_date?, notes?, items: [InvoiceItemIn {description, course_id?, bundle_id?, quantity>=1, unit_price>0}] min 1}` → draft (line_total computed server-side; at most one of course_id/bundle_id per item, 422 via validator; company must exist + be approved → 400).
  - `GET /` (status filter), `GET /{id}` (with items), `PATCH /{id}` (draft only: due_date/notes/items replace → 409 if not draft), `POST /{id}/issue` (calls issue_invoice with render_invoice_pdf; 409 non-draft; surfaces ValueError as 400), `POST /{id}/cancel` (ISSUED+unpaid only → 409 otherwise), `POST /{id}/mark-paid {reference}` (ISSUED only; settle_invoice via="bank_transfer" + commit; 409 otherwise), `GET /{id}/pdf` (FileResponse, 404 if no pdf).
- Schemas: `InvoiceItemIn`, `InvoiceItemOut (+id, line_total)`, `InvoiceCreate`, `InvoiceUpdate {due_date?, notes?, items?}`, `InvoiceOut {id, invoice_number, company_id, company_name, status, subtotal, cgst, sgst, igst, total, tax_note, due_date, issued_at, paid_at, paid_via, payment_reference, notes, items}`, `MarkPaidRequest {reference: str min 1}`.

- [ ] **Step 1: Failing tests**

```python
from app.models.company_invoice import CompanyInvoice, InvoiceStatus
from tests.test_invoice_models import _company


def _create(client, co, course=None, qty=3, unit=500.0):
    item = {"description": "Course seats", "quantity": qty, "unit_price": unit}
    if course is not None:
        item["course_id"] = course.id
    return client.post("/api/v1/admin/company-invoices", json={
        "company_id": co.id, "items": [item]})


def test_draft_create_and_issue_flow(client, db, as_user, student_user, course):
    co = _company(db, student_user)
    as_user(student_user)
    r = _create(client, co, course=course)
    assert r.status_code == 200, r.text
    inv_id = r.json()["id"]
    assert r.json()["status"] == "draft"
    assert float(r.json()["items"][0]["line_total"]) == 1500.0
    r = client.post(f"/api/v1/admin/company-invoices/{inv_id}/issue")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "issued" and body["invoice_number"].startswith("INV-")
    # issued → PATCH forbidden
    assert client.patch(f"/api/v1/admin/company-invoices/{inv_id}",
                        json={"notes": "x"}).status_code == 409
    # pdf exists
    r = client.get(f"/api/v1/admin/company-invoices/{inv_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")


def test_item_validation(client, db, as_user, student_user, course):
    co = _company(db, student_user)
    as_user(student_user)
    r = client.post("/api/v1/admin/company-invoices", json={
        "company_id": co.id,
        "items": [{"description": "bad", "course_id": course.id,
                   "bundle_id": 1, "quantity": 1, "unit_price": 10}]})
    assert r.status_code == 422
    r = client.post("/api/v1/admin/company-invoices", json={
        "company_id": co.id, "items": []})
    assert r.status_code == 422


def test_mark_paid_creates_pool(client, db, as_user, student_user, course):
    from app.models.company_invoice import CompanySeatPool
    co = _company(db, student_user)
    as_user(student_user)
    inv_id = _create(client, co, course=course).json()["id"]
    client.post(f"/api/v1/admin/company-invoices/{inv_id}/issue")
    r = client.post(f"/api/v1/admin/company-invoices/{inv_id}/mark-paid",
                    json={"reference": "NEFT-77"})
    assert r.status_code == 200, r.text
    assert db.query(CompanySeatPool).filter_by(invoice_id=inv_id).one().total_seats == 3
    # double mark-paid → 409
    assert client.post(f"/api/v1/admin/company-invoices/{inv_id}/mark-paid",
                       json={"reference": "NEFT-77"}).status_code == 409


def test_cancel_only_issued_unpaid(client, db, as_user, student_user, course):
    co = _company(db, student_user)
    as_user(student_user)
    inv_id = _create(client, co, course=course).json()["id"]
    assert client.post(f"/api/v1/admin/company-invoices/{inv_id}/cancel").status_code == 409  # draft
    client.post(f"/api/v1/admin/company-invoices/{inv_id}/issue")
    assert client.post(f"/api/v1/admin/company-invoices/{inv_id}/cancel").status_code == 200
```

- [ ] **Step 2: Run** → 404s.
- [ ] **Step 3: Implement** per Interfaces (read certificate_service.py's reportlab usage for the canvas pattern; keep the PDF simple and deterministic: A4, seller block top-left, buyer top-right, table via platypus Table, totals right-aligned; skip logos). PATCH replaces items wholesale (delete + reinsert) only in DRAFT.
- [ ] **Step 4: Run** → 4 passed.
- [ ] **Step 5: Commit** — `feat: invoice PDF renderer + admin invoice lifecycle API`

---

### Task 4: Payments integration — invoice_id target in create-order/verify + webhook + sweeper

**Files:**
- Modify: `app/schemas/payment.py` (add invoice_id to both requests; exactly-one-of-three validator), `app/routers/payments.py` (_create_invoice_order, _verify_invoice_payment), `app/services/webhook_processor.py` (+invoice notes branch, after bundle, before course), `app/services/reconciliation.py` (same in gateway diff)
- Test: `backend/tests/test_invoice_payments.py`

**Interfaces:**
- Consumes settle_invoice (Task 2).
- Produces notes contract `{"invoice_id": str, "user_id": str}`. Auth: `/pay` path is exposed via the company billing API in Task 5 — but create-order accepts invoice_id directly from an authenticated user who must be the company owner OR a linked CompanyManager of the invoice's company (403 otherwise; resolve via the CompanyManager pattern from company_dashboard.py). Amount = invoice.total (ISSUED only; 409 otherwise).
- `_verify_invoice_payment`: HMAC; notes user/invoice match; amount == invoice.total recomputed from row; settle_invoice(via="razorpay", reference=payment_id, gateway ids) + commit; response message "Invoice paid — seats activated".
- Webhook/sweeper: notes `invoice_id` → load invoice; missing → UnrecoverableEvent/alert; else settle + commit (webhook processor's own commit flow; sweeper commits like its bundle branch). Both routes tolerate already-PAID (settle returns False → still PROCESSED / not counted).
- ALSO exports `create_invoice_order_payload(db, invoice, user) -> dict` (the {order_id, amount, currency, key_id} payload builder incl. the owner/manager 403 check and ISSUED 409 check) — Task 5's `/invoices/{id}/pay` calls it instead of duplicating order creation.

- [ ] **Step 1: Failing tests** — mirror tests/test_bundle_webhooks.py + test_bundle_checkout.py structure exactly, with:
  - create-order invoice happy path (FakeOrders; amount == int(total*100); notes contract),
  - create-order 403 for a non-company user; 409 for a DRAFT invoice,
  - verify path settles + pool created,
  - webhook payment.captured with invoice notes settles idempotently (two events, one Order),
  - webhook already-PAID invoice → PROCESSED, no second Order,
  - sweeper orphan invoice order → settles once then 0.
  (Write the tests fully in the implementer's file following those two reference files; each asserts db state exactly as the bundle analogues do.)
- [ ] **Step 2-4:** implement, run — new file green + `tests/test_bundle_checkout.py tests/test_bundle_webhooks.py tests/test_webhook_endpoint.py tests/test_reconciliation.py tests/test_subscription_webhooks.py tests/test_payment_contracts.py` all green.
- [ ] **Step 5: Commit** — `feat: invoice payments through create-order/verify/webhook/sweeper`

---

### Task 5: Company billing API

**Files:**
- Create: `app/routers/company_billing.py`, `app/schemas/company_billing.py`
- Modify: `app/main.py` (mount at `/api/v1/companies/billing`)
- Test: `backend/tests/test_company_billing_api.py`

**Interfaces:**
- Auth helper `_resolve_company(db, user) -> Company` (owner via Company.owner_user_id OR manager via CompanyManager link; 403 none) — copy the resolution pattern from company_dashboard.py (read it; reuse its helper if importable).
- Endpoints: `GET /profile`, `PATCH /profile {gstin?, legal_name?, billing_address?, state_code?}` (state_code pattern `^[0-9]{2}$` or ""), `GET /invoices` (own company only, ISSUED/PAID/CANCELLED — drafts hidden), `GET /invoices/{id}/pdf` (404 unless own + has pdf), `POST /invoices/{id}/pay` → calls the payments create-order invoice branch logic via an internal call OR duplicates the order-creation (DECISION: return the same payload by calling a shared helper `create_invoice_order_payload(db, invoice, user)` extracted in Task 4's payments.py — Task 4 must export it; 409 non-ISSUED), `GET /seat-pools` (with used/total + course/bundle names), `POST /seat-pools/{pool_id}/assign {email}` (validations per spec: 404 unknown user w/ helpful detail, 409 duplicate, 409 exhausted; grants via grant_purchased_course — course pool: that course; bundle pool: every CURRENT published paid course of the bundle; order_id = the pool invoice's Order — locate via Order.order_key == f"INV_{invoice.invoice_number}" or better: store nothing new, query Payment/Order by payment_reference? DECISION: settle_invoice (Task 2) is extended NOW to stamp `CompanySeatPool.order_id` — add nullable order_id FK column to CompanySeatPool in Task 1's model+migration so this task can use it directly), `GET /seat-pools/{pool_id}/assignments`.
- NOTE FOR TASK 1: include `order_id` nullable FK on CompanySeatPool (model + SQL). NOTE FOR TASK 2: settle_invoice sets pool.order_id = order.id.
- Cross-company isolation is the top test concern: every endpoint 404s (not 403-leaks) on other companies' resources.

- [ ] **Steps:** failing tests (profile roundtrip; invoices list hides drafts + other companies; pay returns order payload; assign happy path grants enrollment source="company" + used_seats increments atomically; duplicate 409; exhausted 409; unknown email 404; other company's pool 404; bundle-pool assignment grants the bundle's published paid courses) → implement → run (+ regression list from Task 4) → commit `feat: company billing portal API`.

---

### Task 6: Frontend — company billing page

**Files:**
- Create: `frontend/src/api/companyBilling.ts`, `frontend/src/pages/company/billing.tsx`
- Modify: company dashboard routing/nav (read frontend/src/pages/company/dashboard.tsx and App.tsx company routes; add a Billing tab/section/route consistent with how the company area navigates), axios noSlashEndpoints if needed.
- Gate: type-check zero new vs 391.

Content: billing profile form (GSTIN, legal name, address, state code); invoices table (number, date, total incl. tax note, status chip, PDF download via authenticated GET → open blob, Pay now button on ISSUED using the existing Razorpay pattern with the invoice verify call `{razorpay_*, invoice_id}` — check what Task 4 exposed for verify: it reuses /payments/verify with invoice_id); seat pools cards (course/bundle name, used/total, assign-by-email input with the three error cases surfaced verbatim from API details, assignment list). Mirror membership/bundle page patterns.

- [ ] Commit `feat: company billing portal UI`.

---

### Task 7: Frontend admin — invoices page + docs

**Files:**
- Create: `frontend/src/pages/admin/company-invoices.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/dashboard/nav-configs.ts` (entry "Invoices" beside Bundles), `CLAUDE.md`
- Gate: type-check zero new vs 391.

Content: mirror admin/bundles.tsx patterns — invoices table (number, company, total, status, date, actions), create/edit-draft modal (company select from the admin companies source, line-items editor rows {description, optional course picker OR bundle picker, qty, unit price} with client-side line totals + running subtotal display and a note that tax is computed at issue), Issue / Cancel / Mark-paid (reference prompt) actions, PDF link.

CLAUDE.md addition under the Bundles bullet:

```
- **Company invoicing** (2026-09): admin-negotiated GST invoices (models
  app/models/company_invoice.py; GST/numbering/settlement in
  app/services/invoice_service.py — settle_invoice is the idempotent
  convergence point for online verify/webhook/sweeper AND offline mark-paid;
  PDFs private via authenticated endpoints, files under backend/invoices/).
  create-order/verify accept exactly one of course_id/bundle_id/invoice_id.
  Paid invoices create company_seat_pools; managers assign seats to existing
  users (grants via fulfillment_service.grant_purchased_course rescue
  semantics, enrollment_source="company"). Seller GST config = SELLER_* env
  settings; blank SELLER_GSTIN → invoices issue without tax lines. Migration:
  backend/migrations/add_company_invoicing_tables.sql.
```

- [ ] Commit `feat: admin company invoices UI + docs`.

---

## Post-implementation (owner, manual)

Run `backend/migrations/add_company_invoicing_tables.sql`; set SELLER_LEGAL_NAME/SELLER_ADDRESS/SELLER_STATE_CODE (+ SELLER_GSTIN when registered) in production `.env`; no Razorpay dashboard changes.
