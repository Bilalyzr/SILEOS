# Fee Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cash desk with receiver verification, printable receipts and demand invoices, and Razorpay online payment for tuition installments, all posting through the existing tuition ledger.

**Architecture:** `tuition_service.record_payment` is split into validation plus a shared `_post_payment` core. A new `tuition_collection` service and router hold verification, cash desk, invoices, PDFs and online orders. The webhook processor and Today action centre get small hooks. Frontend adds a Cash desk panel, PDF buttons, a Razorpay checkout helper and Pay now on the parent portal.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic (0043), Pydantic v2, reportlab, razorpay SDK, React 18, TanStack Query, Vitest.

Spec: `docs/superpowers/specs/2026-09-12-fee-collection-design.md`.

## Global Constraints

- No trailing slashes on new routes; all new routes live under the existing `/{institution_id}/fees/...` prefix, so no `noSlashEndpoints` change.
- Every write audits via `institution_service.audit`; commits via `institution_service.save`.
- Honest 503 when Razorpay keys are missing. No secrets in code.
- Header values ASCII only (CSV and PDF filenames sanitised with `re.sub(r"[^A-Za-z0-9._-]+", "-", ...)`).
- Migration 0043 reversible; round-trip tested on SQLite with stub parent tables.
- Pydantic Command schemas are `extra="forbid"`.
- Tests: backend suite `backend/tests/test_fee_collection.py`; frontend `frontend/src/components/institutions/__tests__/fee-collection.test.tsx`.

---

### Task 1: Data model and migration 0043

**Files:**
- Modify: `backend/app/models/tuition.py` (TuitionPayment)
- Create: `backend/app/models/tuition_collection.py`
- Modify: `backend/app/models/__init__.py` (register models, same way `campus_hostel` is registered)
- Create: `backend/alembic/versions/0043_fee_collection.py`
- Test: `backend/tests/test_fee_collection.py::test_migration_0043_round_trip`

**Produces:** `TuitionPayment.received_by/verification_status/verified_by/verified_at/verification_note`, `TuitionInvoice`, `TuitionOnlineOrder`.

- [x] **Step 1: Write the failing migration test** (module scaffold with ROOT and imports mirrors `test_tuition_finance.py`)

```python
def test_migration_0043_round_trip(tmp_path):
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0043_fee_collection.py"
    spec = importlib.util.spec_from_file_location("m0043", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert (migration.revision, migration.down_revision) == ("0043", "0042")
    engine = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
    metadata = sa.MetaData()
    sa.Table("institutions", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("users", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("tuition_fee_assignments", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("tuition_installments", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("tuition_payments", metadata,
             sa.Column("id", sa.Integer(), primary_key=True),
             sa.Column("institution_id", sa.Integer()), sa.Column("method", sa.String(30)),
             sa.Column("recorded_by", sa.Integer()), sa.Column("paid_at", sa.DateTime()))
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO tuition_payments (id, institution_id, method, recorded_by) VALUES (1, 1, 'cash', 7), (2, 1, 'upi', 7)"))
        migration.op = Operations(MigrationContext.configure(conn))
        migration.upgrade()
        cols = {c["name"] for c in inspect(conn).get_columns("tuition_payments")}
        assert {"received_by", "verification_status", "verified_by", "verified_at", "verification_note"} <= cols
        rows = dict(conn.execute(sa.text("SELECT id, verification_status FROM tuition_payments")).all())
        assert rows == {1: "verified", 2: "not_required"}
        assert {"tuition_invoices", "tuition_online_orders"} <= set(inspect(conn).get_table_names())
        migration.downgrade()
        assert "tuition_invoices" not in inspect(conn).get_table_names()
        cols = {c["name"] for c in inspect(conn).get_columns("tuition_payments")}
        assert "verification_status" not in cols
```

- [x] **Step 2: Run it, expect failure** — `pytest tests/test_fee_collection.py::test_migration_0043_round_trip -q` → file not found.

- [x] **Step 3: Model columns** on `TuitionPayment` after `recorded_by`:

```python
    received_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    verification_status = Column(String(20), nullable=False, default="not_required", server_default="not_required")
    verified_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_note = Column(String(300), nullable=False, default="", server_default="")
```
Add to `__table_args__`: `CheckConstraint("verification_status IN ('not_required','pending','verified')", name="ck_tuition_payment_verification")` and `Index("ix_tuition_payment_verification", "institution_id", "verification_status", "paid_at")`.

- [x] **Step 4: New models file** `models/tuition_collection.py`:

```python
class TuitionInvoice(Base):
    __tablename__ = "tuition_invoices"
    id, institution_id (FK institutions, index), assignment_id (FK tuition_fee_assignments, index),
    installment_id (FK tuition_installments, nullable), invoice_number String(50) unique,
    amount MONEY, currency String(3), due_on Date, lines_json JSON default list,
    issued_by FK users, issued_at DateTime(tz) server_default now
    CheckConstraint("amount > 0", name="ck_tuition_invoice_amount_positive")

class TuitionOnlineOrder(Base):
    __tablename__ = "tuition_online_orders"
    id, institution_id (FK, index), assignment_id (FK, index), installment_id (FK nullable),
    payer_user_id FK users, gateway_order_id String(64) unique, gateway_payment_id String(64) nullable unique,
    payment_id FK tuition_payments nullable, amount MONEY, amount_paise Integer, currency String(3),
    status String(20) default "created", excess_amount MONEY default 0,
    created_at server_default now, paid_at nullable
    CheckConstraint("status IN ('created','paid','paid_excess','failed')", name="ck_tuition_online_order_status")
```
`MONEY = Numeric(13, 2)` as in `models/tuition.py`.

- [x] **Step 5: Migration 0043** using `op.batch_alter_table("tuition_payments")` to add the five columns, then `op.execute` the two backfill UPDATEs (`received_by = recorded_by` where null; `verification_status = 'verified'` where method in ('cash','cheque')), create the index, create both tables guarded by `inspector.has_table`. Downgrade drops both tables, the index, then batch-drops the columns.

- [x] **Step 6: Run test, expect pass.** Also run `pytest tests/test_tuition_finance.py -q` (still 5 passed).

---

### Task 2: Receiver on record_payment and the shared post core

**Files:**
- Modify: `backend/app/schemas/tuition.py` (`TuitionPaymentCreate.received_by_member_id`, `TuitionPaymentOut` new fields)
- Modify: `backend/app/services/tuition_service.py`
- Test: `test_fee_collection.py::test_cash_requires_receiver_and_sets_pending`

**Produces:** `tuition_service.CASH_METHODS`, `_post_payment(db, institution, assignment, actor, *, amount, paid_at, method, reference, note, idempotency_key, fingerprint, received_by) -> (payment, receipt, balance_after)`, `_payment_dict` with `received_by` and `verification`.

- [x] **Step 1: Failing test**

```python
def test_cash_requires_receiver_and_sets_pending(client, db, as_user, tuition_campus):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    root = f"{ROOT}/{campus.institution_id}/fees/assignments/{assignment['id']}/payments"
    missing = client.post(root, json={"amount": "100", "method": "cash"}, headers={"Idempotency-Key": "cash-no-receiver"})
    assert missing.status_code == 422
    teacher_receiver = client.post(root, json={"amount": "100", "method": "cash", "received_by_member_id": campus.teacher_member.id}, headers={"Idempotency-Key": "cash-teacher"})
    assert teacher_receiver.status_code == 201, teacher_receiver.text
    payment = teacher_receiver.json()["payment"]
    assert payment["verification"]["status"] == "pending"
    assert payment["received_by"]["name"] == campus.teacher.display_name
    student_receiver = client.post(root, json={"amount": "50", "method": "cash", "received_by_member_id": campus.student_member.id}, headers={"Idempotency-Key": "cash-student"})
    assert student_receiver.status_code == 404
    card = client.post(root, json={"amount": "100", "method": "card"}, headers={"Idempotency-Key": "card-1"})
    assert card.status_code == 201
    assert card.json()["payment"]["verification"]["status"] == "not_required"
    assert card.json()["payment"]["received_by"] is None
```

- [x] **Step 2: Run, expect 422 mismatch (extra field forbidden)**.

- [x] **Step 3: Schema.** `TuitionPaymentCreate` gains `received_by_member_id: int | None = Field(default=None, gt=0)`. New `TuitionPersonOut(Out): id: int; name: str`, `TuitionVerificationOut(Out): status: str; verified_by: TuitionPersonOut | None; verified_at: datetime | None; note: str`. `TuitionPaymentOut` gains `received_by: TuitionPersonOut | None` and `verification: TuitionVerificationOut`.

- [x] **Step 4: Service.** Add `CASH_METHODS = ("cash", "cheque")` and `RECEIVER_ROLES = ("owner", "admin", "teacher")`.

```python
def _receiver(db, institution_id, data):
    if data.method not in CASH_METHODS:
        return None
    if not data.received_by_member_id:
        raise HTTPException(422, "Choose who received the cash or cheque.")
    member = db.query(InstitutionMember).filter_by(id=data.received_by_member_id, institution_id=institution_id, status="active").first()
    if not member or member.role not in RECEIVER_ROLES:
        raise HTTPException(404, "Receiver must be an active owner, admin or teacher of this institution.")
    return member.user_id


def _person(db, user_id):
    if not user_id:
        return None
    row = db.get(User, user_id)
    return {"id": user_id, "name": (row.display_name if row else None) or "Staff"}
```
`_payment_dict` adds `"received_by": _person(db, payment.received_by)` and `"verification": {"status": payment.verification_status, "verified_by": _person(db, payment.verified_by), "verified_at": payment.verified_at, "note": payment.verification_note}`.

Extract `_post_payment`: everything from the `paid_at` normalisation through the receipt creation and audit inside `begin_nested`, parameterised; it sets `received_by=received_by`, `verification_status="pending" if method in CASH_METHODS else "not_required"`, audit detail `f"Account #{assignment.id} · {currency} {amount} · {method}" + (f" · received by {name}" if received_by)`. `record_payment` becomes: scope, assignment, fingerprint (now includes `received_by_member_id`), replay check, cancelled check, balance check, `receiver = _receiver(...)`, then `try: payment, receipt, balance_after = _post_payment(...) except IntegrityError: replay-or-409`, then `save`, `queue_receipt`, return dict. Behaviour for existing callers unchanged.

- [x] **Step 5: Run test → pass; run `test_tuition_finance.py`, `test_tuition_reminders.py`, `test_campus_transport.py`, `test_campus_hostel.py` → all green (they record payments).**

---

### Task 3: Cash verification, cash desk and Today cards

**Files:**
- Create: `backend/app/services/tuition_collection.py`
- Create: `backend/app/routers/tuition_collection.py`; register in `backend/app/main.py` after tuition_reminders.
- Modify: `backend/app/schemas/tuition.py` (`PaymentVerify(Command): note: str = Field(default="", max_length=300)`, `CashDeskOut`)
- Modify: `backend/app/services/campus_action_center.py` (manager branch)
- Test: `test_verify_rules_and_cash_desk`, `test_today_shows_cash_cards`

**Produces:** `verify_payment(db, iid, payment_id, user, note)`, `cash_desk(db, iid, user, day)`, `cash_desk_csv(db, iid, user, day) -> (filename, text)`, `pending_cash(db, iid) -> (count, total)`, `excess_order_count(db, iid)`.

- [x] **Step 1: Failing tests**

```python
def test_verify_rules_and_cash_desk(client, db, as_user, make_user, tuition_campus):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    admin = make_user(role="instructor", email="fee-admin@example.org")
    db.add(InstitutionMember(institution_id=campus.institution_id, user_id=admin.id, role="admin", status="active", department="")); db.commit()
    owner_member = db.query(InstitutionMember).filter_by(institution_id=campus.institution_id, user_id=campus.owner.id).one()
    paid = client.post(f"{fees}/assignments/{assignment['id']}/payments", json={"amount": "300", "method": "cash", "received_by_member_id": owner_member.id}, headers={"Idempotency-Key": "cash-a"}).json()["payment"]
    # receiver cannot verify own entry while another manager exists
    assert client.post(f"{fees}/payments/{paid['id']}/verify", json={"note": "counted"}).status_code == 409
    as_user(campus.teacher)
    assert client.post(f"{fees}/payments/{paid['id']}/verify", json={}).status_code == 403
    as_user(admin)
    ok = client.post(f"{fees}/payments/{paid['id']}/verify", json={"note": "counted 300"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["verification"]["status"] == "verified"
    assert ok.json()["verification"]["verified_by"]["id"] == admin.id
    assert client.post(f"{fees}/payments/{paid['id']}/verify", json={}).status_code == 409
    desk = client.get(f"{fees}/cash", params={"day": date.today().isoformat()})
    assert desk.status_code == 200, desk.text
    body = desk.json()
    assert body["verified_total"] == 300 and body["pending_total"] == 0
    assert body["receivers"][0]["name"] == campus.owner.display_name
    csv = client.get(f"{fees}/cash/csv", params={"day": date.today().isoformat()})
    assert csv.status_code == 200 and "attachment" in csv.headers["content-disposition"]
    assert campus.owner.display_name.split()[0] in csv.text


def test_sole_manager_can_self_verify(client, db, as_user, tuition_campus):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    owner_member = db.query(InstitutionMember).filter_by(institution_id=campus.institution_id, user_id=campus.owner.id).one()
    paid = client.post(f"{fees}/assignments/{assignment['id']}/payments", json={"amount": "100", "method": "cheque", "received_by_member_id": owner_member.id, "reference": "CHQ 1"}, headers={"Idempotency-Key": "chq-a"}).json()["payment"]
    ok = client.post(f"{fees}/payments/{paid['id']}/verify", json={"note": "sole"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["verification"]["status"] == "verified"
    from app.models.institution import InstitutionAudit
    assert db.query(InstitutionAudit).filter(InstitutionAudit.detail.contains("self_verified_sole_manager")).count() == 1


def test_today_shows_cash_cards(client, db, as_user, tuition_campus):
    campus = tuition_campus
    plan_id = create_published_plan(client, campus)
    assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    owner_member = db.query(InstitutionMember).filter_by(institution_id=campus.institution_id, user_id=campus.owner.id).one()
    client.post(f"{fees}/assignments/{assignment['id']}/payments", json={"amount": "250", "method": "cash", "received_by_member_id": owner_member.id}, headers={"Idempotency-Key": "cash-t"})
    today = client.get(f"{ROOT}/{campus.institution_id}/today").json()
    card = next(a for a in today["actions"] if a["id"] == "system-cash-verification")
    assert "1 cash" in card["title"] and "250" in card["detail"]
```

- [x] **Step 2: Run → 404s.**

- [x] **Step 3: Service `tuition_collection.py`**

```python
def _managers(db, institution_id):
    return db.query(InstitutionMember).filter(InstitutionMember.institution_id == institution_id, InstitutionMember.status == "active", InstitutionMember.role.in_(institution_svc.MANAGERS)).all()

def verify_payment(db, institution_id, payment_id, user, note):
    institution, actor = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    payment = db.query(TuitionPayment).filter_by(id=payment_id, institution_id=institution_id).with_for_update().first()
    if not payment: raise HTTPException(404, "Tuition payment not found.")
    if payment.status != "posted": raise HTTPException(409, "A reversed payment cannot be verified.")
    if payment.verification_status != "pending": raise HTTPException(409, "This payment does not need verification or is already verified.")
    tag = ""
    if payment.received_by == user.id:
        others = [m for m in _managers(db, institution_id) if m.user_id != user.id]
        if others: raise HTTPException(409, "The person who received the cash cannot verify it. Ask another owner or admin.")
        tag = " · self_verified_sole_manager"
    payment.verification_status = "verified"; payment.verified_by = user.id
    payment.verified_at = datetime.now(timezone.utc); payment.verification_note = note
    institution_svc.audit(db, institution_id, user, "tuition.payment.verified", f"Payment #{payment.id} · {payment.currency} {payment.amount}{tag}")
    institution_svc.save(db)
    return tuition_service._payment_dict(db, payment)
```
`cash_desk`: managers only; day → local window via `ZoneInfo(institution.timezone)`; query `TuitionPayment` where method in CASH_METHODS and paid_at within window, join assignment→member→user for student name and plan; rows `{payment_id, receipt_id, receipt_number, student_name, plan_name, amount, currency, method, reference, paid_at, received_by, verification}`; `receivers` grouped `{id, name, count, total, pending}`; `pending_total`, `verified_total`, `pending_count`; `excess_orders` list from `TuitionOnlineOrder` status `paid_excess` (any day) `{id, student_name, excess_amount, currency, gateway_payment_id, paid_at}`. CSV: header `Receipt,Student,Plan,Method,Reference,Amount,Currency,Paid at,Received by,Status,Verified by`; filename `cash-desk-{slug}-{day}.csv` sanitised.

`pending_cash(db, iid)` → `(count, total)` for status pending. `excess_order_count`.

- [x] **Step 4: Router** (`router = APIRouter()`, `CurrentUser` as tuition router): the three endpoints. CSV response: `Response(content=text, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})`. Register in `main.py`:

```python
from app.routers import tuition_collection
app.include_router(tuition_collection.router, prefix="/api/v1/institutions", tags=["Tuition collection"])
```
In the test module, include the router if `/fees/cash` is not mounted (same guard pattern as `test_tuition_finance.py`).

- [x] **Step 5: Today.** In the manager block next to `system-transport`:

```python
            from app.services.tuition_collection import pending_cash, excess_order_count
            cash_count, cash_total = pending_cash(db, institution_id)
            if cash_count:
                actions.append(_system_action("system-cash-verification", "finance",
                    f"{cash_count} cash payment{'s' if cash_count != 1 else ''} waiting for verification",
                    f"{cash_total:,.2f} received at the counter has not been counted by a second person yet.",
                    "high", base + "?section=finance&panel=cash", "Open cash desk"))
            excess = excess_order_count(db, institution_id)
            if excess:
                actions.append(_system_action("system-online-excess", "finance",
                    f"{excess} online payment{'s' if excess != 1 else ''} need a refund",
                    "A gateway payment arrived after the balance was already settled at the counter.",
                    "high", base + "?section=finance&panel=cash", "Review"))
```

- [x] **Step 6: Run the three tests → pass. Run `test_campus_action_center.py` → green.**

---

### Task 4: Receipt PDF and demand invoices

**Files:**
- Modify: `backend/app/services/campus_report_pdf.py` (+ `build_fee_receipt_pdf`, `build_fee_invoice_pdf`)
- Modify: `backend/app/services/tuition_collection.py` (+ `receipt_document`, `create_invoice`, `list_invoices`, `invoice_detail`, `invoice_document`)
- Modify: `backend/app/routers/tuition_collection.py`
- Modify: `backend/app/schemas/tuition.py` (`InvoiceCreate(Command): installment_id: int | None = Field(default=None, gt=0)`, `TuitionInvoiceOut`)
- Test: `test_receipt_pdf_access`, `test_invoices`

- [x] **Step 1: Failing tests**

```python
def _link_parent(db, campus):
    db.add(ParentLinkRequest(parent_user_id=campus.parent.id, student_user_id=campus.student.id, status="approved")); db.commit()

def test_receipt_pdf_access(client, db, as_user, tuition_campus):
    campus = tuition_campus; _link_parent(db, campus)
    plan_id = create_published_plan(client, campus); assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    owner_member = db.query(InstitutionMember).filter_by(institution_id=campus.institution_id, user_id=campus.owner.id).one()
    paid = client.post(f"{fees}/assignments/{assignment['id']}/payments", json={"amount": "300", "method": "cash", "received_by_member_id": owner_member.id}, headers={"Idempotency-Key": "pdf-a"}).json()["payment"]
    url = f"{fees}/receipts/{paid['receipt']['id']}/pdf"
    for person in (campus.owner, campus.student, campus.parent):
        as_user(person); r = client.get(url)
        assert r.status_code == 200 and r.content.startswith(b"%PDF"), (person.user_email, r.status_code)
    as_user(campus.stranger_parent); assert client.get(url).status_code == 404

def test_invoices(client, db, as_user, tuition_campus):
    campus = tuition_campus; _link_parent(db, campus)
    plan_id = create_published_plan(client, campus); assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    first = assignment["installments"][0]["id"]
    one = client.post(f"{fees}/assignments/{assignment['id']}/invoices", json={"installment_id": first})
    assert one.status_code == 201, one.text
    assert one.json()["amount"] == 1000 and one.json()["invoice_number"].startswith("TI-")
    as_user(campus.parent)
    whole = client.post(f"{fees}/assignments/{assignment['id']}/invoices", json={})
    assert whole.status_code == 201 and whole.json()["amount"] == 3000 and len(whole.json()["lines"]) == 3
    pdf = client.get(f"{fees}/invoices/{whole.json()['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    listed = client.get(f"{fees}/assignments/{assignment['id']}/invoices").json()
    assert [row["id"] for row in listed["items"]] == [whole.json()["id"], one.json()["id"]]
    as_user(campus.owner)
    client.post(f"{fees}/assignments/{assignment['id']}/payments", json={"amount": "1000", "method": "upi"}, headers={"Idempotency-Key": "inv-pay"})
    assert client.post(f"{fees}/assignments/{assignment['id']}/invoices", json={"installment_id": first}).status_code == 422
    assert client.get(f"{fees}/invoices/{one.json()['id']}").json()["status"] == "settled"
    as_user(campus.stranger_parent)
    assert client.get(f"{fees}/invoices/{one.json()['id']}").status_code == 404
```

- [x] **Step 2: Run → 404s.**

- [x] **Step 3: Service.**

`_viewable_assignment(db, iid, aid, user)`: load assignment by id+institution; `tuition_service._can_view_assignment` else 404.

`create_invoice(db, iid, aid, user, installment_id)`: assignment (lock), snapshot via `tuition_service._snapshot_for`; rows = installments filtered by id if given (404 if missing); rows with balance > 0; if none → 422 "Nothing is due on this account." (or "...this installment"); amount = sum balances; due_on = min due_on of rows; `invoice_number = f"TI-{iid}-{year}-{seq:06d}"` where seq = count of invoices for institution + 1, retried once on IntegrityError; lines `[{"installment_id","name","due_on":iso,"amount_due","credited","balance"}]`; audit `tuition.invoice.issued`; save; return `invoice_dict`.

`invoice_dict(db, invoice)`: fields plus `status` = "settled" if current balance of the covered installments is 0 else "open", `student`, `plan`, `institution_name`, `timezone`, `issued_by` person.

`receipt_document(db, iid, receipt_id, user)`: `tuition_service.receipt_detail(...)` plus `received_by`, `verification`, `timezone`, `allocations` from `TuitionLedgerEntry` where payment_id → `[{"installment": name, "amount": -entry.amount}]`, `academic_year`.

- [x] **Step 4: PDFs** in `campus_report_pdf.py`, mirroring `build_hall_ticket_pdf`: title = branding title or institution name; lead "Fee receipt {number}" / "Fee invoice {number}"; `_key_value_table` for student, plan, academic year, paid at (local), method, reference, received by, verification (`Verified by X on date` / `Awaiting verification` / `Not required`); `_grid` for allocations (Installment, Amount) or invoice lines (Installment, Due, Amount due, Credited, Balance); total line; footer paragraph "Registered details: -" and "This is a computer-generated document."

- [x] **Step 5: Router** endpoints: `GET /{iid}/fees/receipts/{rid}/pdf`, `POST /{iid}/fees/assignments/{aid}/invoices` (201), `GET /{iid}/fees/assignments/{aid}/invoices` → `{"items": [...]}`, `GET /{iid}/fees/invoices/{id}`, `GET /{iid}/fees/invoices/{id}/pdf`. Reuse `_pdf` helper (copy from `campus_exams.py`), branding via `db.get(CampusBranding, iid)`.

- [x] **Step 6: Run tests → pass.**

---

### Task 5: Online payment through Razorpay

**Files:**
- Modify: `backend/app/services/tuition_collection.py` (+ `online_ready`, `online_status`, `create_online_order`, `fulfil_online_order`, `verify_online_order`, `reconcile_online_order`)
- Modify: `backend/app/routers/tuition_collection.py`
- Modify: `backend/app/schemas/tuition.py` (`OnlineOrderCreate(Command): installment_id: int | None; amount: MoneyInput | None`, `OnlineVerify(Command): razorpay_order_id: str; razorpay_payment_id: str; razorpay_signature: str`)
- Modify: `backend/app/services/webhook_processor.py` (`_handle_payment_captured`)
- Modify: `backend/app/services/tuition_reminders.py` (`message_text` pay line)
- Test: `test_online_order_503_when_unconfigured`, `test_online_order_create_verify_replay`, `test_webhook_capture_and_excess`

**Produces:** `fulfil_online_order(db, order, entity)` used by verify, reconcile and the webhook.

- [x] **Step 1: Failing tests** (monkeypatch `tuition_collection._creds` to return `("rzp_test_key", "secret")` and `tuition_collection._client` to a `FakeClient` with `order.create`, `payment.fetch`, `order.payments`).

```python
class FakeClient:
    def __init__(self): self.created = []; self.payments = {}
    class _Order:
        def __init__(s, outer): s.outer = outer
        def create(s, payload): s.outer.created.append(payload); return {"id": f"order_{len(s.outer.created)}", "amount": payload["amount"], "currency": "INR"}
        def payments(s, order_id): return {"items": [p for p in s.outer.payments.values() if p["order_id"] == order_id]}
    class _Payment:
        def __init__(s, outer): s.outer = outer
        def fetch(s, pid): return s.outer.payments[pid]
    @property
    def order(self): return FakeClient._Order(self)
    @property
    def payment(self): return FakeClient._Payment(self)

def _sign(order_id, payment_id, secret="secret"):
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()

def test_online_order_503_when_unconfigured(client, db, as_user, tuition_campus, monkeypatch):
    from app.services import tuition_collection as tc
    monkeypatch.setattr(tc, "_creds", lambda: ("", ""))
    campus = tuition_campus; plan_id = create_published_plan(client, campus); assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    assert client.get(f"{fees}/online/status").json() == {"ready": False}
    as_user(campus.student)
    r = client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={})
    assert r.status_code == 503 and "not set up" in r.json()["detail"]

def test_online_order_create_verify_replay(client, db, as_user, tuition_campus, monkeypatch):
    from app.services import tuition_collection as tc
    fake = FakeClient(); monkeypatch.setattr(tc, "_creds", lambda: ("rzp_test", "secret")); monkeypatch.setattr(tc, "_client", lambda: fake)
    campus = tuition_campus; plan_id = create_published_plan(client, campus); assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"; first = assignment["installments"][0]
    as_user(campus.student)
    too_much = client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={"installment_id": first["id"], "amount": "1500"})
    assert too_much.status_code == 422
    created = client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={"installment_id": first["id"]})
    assert created.status_code == 201, created.text
    checkout = created.json()["checkout"]; order = created.json()["order"]
    assert checkout["amount_paise"] == 100000 and checkout["key"] == "rzp_test" and checkout["order_id"] == "order_1"
    fake.payments["pay_1"] = {"id": "pay_1", "order_id": "order_1", "status": "captured", "amount": 100000, "currency": "INR", "amount_refunded": 0}
    bad = client.post(f"{fees}/online-orders/{order['id']}/verify", json={"razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1", "razorpay_signature": "nope"})
    assert bad.status_code == 400
    ok = client.post(f"{fees}/online-orders/{order['id']}/verify", json={"razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1", "razorpay_signature": _sign("order_1", "pay_1")})
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "paid" and ok.json()["payment"]["method"] == "online" and ok.json()["payment"]["reference"] == "pay_1"
    again = client.post(f"{fees}/online-orders/{order['id']}/verify", json={"razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1", "razorpay_signature": _sign("order_1", "pay_1")})
    assert again.status_code == 200 and again.json()["payment"]["id"] == ok.json()["payment"]["id"]
    assert db.query(TuitionPayment).filter_by(method="online").count() == 1
    me = client.get(f"{fees}/me").json()
    assert me["assignments"][0]["installments"][0]["status"] == "paid"
    as_user(campus.stranger_parent)
    assert client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={}).status_code == 404

def test_webhook_capture_and_excess(client, db, as_user, tuition_campus, monkeypatch):
    from app.services import tuition_collection as tc
    from app.services.webhook_processor import process_webhook_event
    from app.models.webhook_event import WebhookEvent
    fake = FakeClient(); monkeypatch.setattr(tc, "_creds", lambda: ("rzp_test", "secret")); monkeypatch.setattr(tc, "_client", lambda: fake)
    campus = tuition_campus; plan_id = create_published_plan(client, campus); assignment = create_assignment(client, campus, plan_id)
    fees = f"{ROOT}/{campus.institution_id}/fees"
    as_user(campus.student)
    order = client.post(f"{fees}/assignments/{assignment['id']}/online-orders", json={}).json()["order"]  # 3000
    as_user(campus.owner)
    client.post(f"{fees}/assignments/{assignment['id']}/payments", json={"amount": "2500", "method": "upi"}, headers={"Idempotency-Key": "counter-first"})
    entity = {"id": "pay_w", "order_id": "order_1", "status": "captured", "amount": 300000, "currency": "INR", "amount_refunded": 0, "notes": {}}
    event = WebhookEvent(event_id="evt_1", event_type="payment.captured", payload={"payload": {"payment": {"entity": entity}}}, signature_valid=True)
    db.add(event); db.commit()
    process_webhook_event(db, event); db.commit()
    assert event.status.value == "processed" if hasattr(event.status, "value") else event.status == "processed"
    row = db.get(TuitionOnlineOrder, order["id"]); db.refresh(row)
    assert row.status == "paid_excess" and float(row.excess_amount) == 2500 and row.gateway_payment_id == "pay_w"
    assert client.get(f"{fees}/me", params={}).status_code in (200, 404)
    today = client.get(f"{ROOT}/{campus.institution_id}/today").json()
    assert any(a["id"] == "system-online-excess" for a in today["actions"])
    desk = client.get(f"{fees}/cash", params={"day": date.today().isoformat()}).json()
    assert desk["excess_orders"][0]["excess_amount"] == 2500
```

- [x] **Step 2: Run → fail.**

- [x] **Step 3: Service.**

```python
def _creds():
    from app.routers.payments import _razorpay_creds
    return _razorpay_creds()

def online_ready(): key, secret = _creds(); return bool(key and secret)

def _client():
    import razorpay
    key, secret = _creds()
    return razorpay.Client(auth=(key, secret))

def create_online_order(db, iid, aid, user, installment_id, amount):
    if not online_ready(): raise HTTPException(503, "Online payment is not set up for this campus yet. Pay at the office or ask them to enable it.")
    institution = db.get(Institution, iid); assignment = _viewable_assignment(db, iid, aid, user)   # 404 covers stranger
    if assignment.status == "cancelled": raise HTTPException(409, ...)
    if assignment.currency != "INR": raise HTTPException(422, "Online payment supports INR accounts only.")
    snapshot = tuition_service._snapshot_for(db, assignment)
    if installment_id: row = next((r for r in snapshot["installments"] if r["id"] == installment_id), None) or 404; limit = money(row["balance"])
    else: limit = money(snapshot["balance"])
    amount = money(amount) if amount is not None else limit
    if amount <= 0 or amount > limit: raise HTTPException(422, "The amount must be between 0.01 and the outstanding balance.")
    paise = int(round(amount * 100))
    order = TuitionOnlineOrder(... status="created", gateway_order_id=f"pending-{uuid4().hex}")  # flush to get id
    db.add(order); db.flush()
    try:
        gw = _client().order.create({"amount": paise, "currency": "INR", "receipt": f"tf-{order.id}", "notes": {"tuition_order_id": str(order.id), "institution_id": str(iid)}})
    except Exception:
        db.rollback(); log.exception(...); raise HTTPException(503, "Checkout could not start. Nothing was charged.")
    order.gateway_order_id = gw["id"]
    audit "tuition.online_order.created"; save
    student = db.get(User, member.user_id)
    return {"order": order_dict(db, order), "checkout": {"key": key, "order_id": gw["id"], "amount_paise": paise, "currency": "INR", "name": institution.name, "description": f"{plan.name} · {installment name or 'Fee balance'}", "prefill": {"name": user.display_name or "", "email": user.user_email or ""}}}
```

`fulfil_online_order(db, order, entity)`: `order = db.query(TuitionOnlineOrder).filter_by(id=order.id).with_for_update().one()`; payment_id = entity id; check `entity.status == "captured"`, `entity.order_id == order.gateway_order_id`, `currency == INR`, `int(amount) == order.amount_paise`, no refund → else `ValueError`. If `order.gateway_payment_id`: equal → return order (no-op); different → ValueError. If another order already has this payment id → ValueError. Load institution, assignment (lock), snapshot; `limit = money(snapshot["balance"])`; `post = min(order.amount, limit)`; if `post > 0`: `payment, receipt, balance_after = tuition_service._post_payment(db, institution, assignment, payer_user, amount=post, paid_at=now, method="online", reference=payment_id, note=f"Razorpay order {order.gateway_order_id}", idempotency_key=f"rzp:{payment_id}"[:64], fingerprint=..., received_by=None)`; `order.payment_id = payment.id`; queue receipt after commit (caller commits; call `tuition_reminders.queue_receipt` after `db.flush()` — it never raises and inserts rows in the same session). `order.excess_amount = order.amount - post`; `order.status = "paid_excess" if excess > 0 else "paid"`; `order.gateway_payment_id = payment_id`; `order.paid_at = now`; audit `tuition.online_order.paid` (+ `.excess`). Return order. The caller commits.

`verify_online_order(db, iid, order_id, user, body)`: order by id+institution (404); `_viewable_assignment` guard; `body.razorpay_order_id == order.gateway_order_id` else 400; HMAC with secret over `f"{order_id}|{payment_id}"`, compare else 400 "Invalid payment signature."; `entity = _client().payment.fetch(payment_id)`; try `fulfil_online_order`; commit; `ValueError` → rollback + 409; `IntegrityError` → rollback + 409 "Payment is being verified. Refresh; do not pay again."; other Exception → rollback + 503. Return `order_dict` incl. `payment` (`_payment_dict`) or None.

`reconcile_online_order`: if status != created → return dict; `items = _client().order.payments(gateway_order_id)["items"]`; fulfil first captured; commit; errors → 503.

`order_dict(db, order)`: id, assignment_id, installment_id, status, amount, amount_paise, currency, excess_amount, gateway_order_id, gateway_payment_id, created_at, paid_at, payment (dict or None).

- [x] **Step 4: Webhook hook** in `_handle_payment_captured`, before the exam paper block:

```python
    from app.models.tuition_collection import TuitionOnlineOrder
    from app.services.tuition_collection import fulfil_online_order
    tuition_order = db.query(TuitionOnlineOrder).filter(TuitionOnlineOrder.gateway_order_id == entity.get("order_id")).first() if entity.get("order_id") else None
    if tuition_order is not None:
        fulfil_online_order(db, tuition_order, entity)
        return
```
(`ValueError` propagates to the existing handler which marks the event failed with the message; that is the desired honest outcome for a mismatched amount.)

- [x] **Step 5: Reminder pay line.** In `tuition_reminders.message_text`, for kinds `upcoming`, `due`, `overdue`, append `f" Pay online: {ctx['pay_url']}"` when `ctx.get("pay_url")`. In `_context`, set `pay_url` when `tuition_collection.online_ready()`: `f"{settings.FRONTEND_URL}/parent"` if recipient role is parent else `f"{settings.FRONTEND_URL}/institutions/{institution.id}?section=finance"`.

- [x] **Step 6: Router.** `GET /{iid}/fees/online/status` (any active member or approved parent → `{"ready": bool}`; use `institution_svc.scope` for members, parents allowed if any approved link into this institution — simplest: any authenticated user, it leaks nothing but a boolean), `POST /{iid}/fees/assignments/{aid}/online-orders` (201), `POST /{iid}/fees/online-orders/{id}/verify`, `POST /{iid}/fees/online-orders/{id}/reconcile`.

- [x] **Step 7: Run all fee_collection tests → pass. Run `test_tuition_reminders.py` → green.**

---

### Task 6: Frontend API and Razorpay helper

**Files:**
- Modify: `frontend/src/api/campus-os.ts` (types + api + hooks)
- Create: `frontend/src/lib/razorpayCheckout.ts`

- [x] **Step 1: Types.** `TuitionPerson {id; name}`, `TuitionVerification {status: "not_required"|"pending"|"verified"; verified_by: TuitionPerson|null; verified_at: string|null; note: string}`; `TuitionPayment` gains `received_by: TuitionPerson|null; verification: TuitionVerification`; `RecordFeePayment` gains `received_by_member_id?: number|null`; `CashDeskRow`, `CashDesk {day; currency; rows; receivers; pending_total; verified_total; pending_count; excess_orders}`; `TuitionInvoice {id; invoice_number; amount; currency; due_on; status; lines; issued_at; installment_id}`; `OnlineCheckout {key; order_id; amount_paise; currency; name; description; prefill}`; `OnlineOrder {id; status; amount; excess_amount; payment: TuitionPayment|null}`.

- [x] **Step 2: API.** `cashDesk(iid, day)`, `cashDeskCsv(iid, day)` (blob), `verifyPayment(iid, paymentId, note)`, `receiptPdf(iid, receiptId)` (blob), `createInvoice(iid, aid, installmentId|null)`, `invoicePdf(iid, invoiceId)` (blob), `onlineStatus(iid)`, `createOnlineOrder(iid, aid, {installment_id, amount})`, `verifyOnlineOrder(iid, orderId, body)`, `reconcileOnlineOrder(iid, orderId)`. Keys: `cashDesk(iid, day)`, `onlineStatus(iid)`. Hooks `useCashDesk`, `useOnlineStatus`. Export `openBlob` re-used from `@/api/campus-exams`.

- [x] **Step 3: Helper** `razorpayCheckout.ts`: `ensureRazorpayLoaded()` (copied from `bundle-detail.tsx`) and

```ts
export async function openRazorpay(checkout: OnlineCheckout, handlers: { onSuccess: (r: RazorpayResponse) => void; onDismiss: () => void }) {
  await ensureRazorpayLoaded();
  const rz = new (window as any).Razorpay({ key: checkout.key, amount: checkout.amount_paise, currency: checkout.currency, name: checkout.name, description: checkout.description, order_id: checkout.order_id, prefill: checkout.prefill, handler: handlers.onSuccess, modal: { ondismiss: handlers.onDismiss }, theme: { color: "#a9360c" } });
  rz.open();
}
```

- [x] **Step 4: `npx tsc --noEmit -p frontend` clean.**

---

### Task 7: Manager UI — received by, cash desk, PDFs

**Files:**
- Create: `frontend/src/components/institutions/FeeCashDesk.tsx`
- Modify: `frontend/src/components/institutions/CampusFinance.tsx`
- Test: `frontend/src/components/institutions/__tests__/fee-collection.test.tsx` (manager cases)

- [x] **Step 1: Failing test** — render `CampusFinance` as owner with mocked `campusOsApi.cashDesk` returning one pending row for "Asha Rao" received by "Owner One"; expect "Cash desk" heading, "Asha Rao", a "Verify" button; clicking Verify opens dialog, submit calls `verifyPayment` with the payment id and note.

- [x] **Step 2: `FeeCashDesk.tsx`** — props `{institutionId, currency}`; day state (default local today); `useCashDesk`; metrics (Pending, Verified, Receivers); table (student, plan, method, amount, received by, status badge, actions: "Receipt PDF", "Verify" when pending); excess orders list; "Export CSV" via `openBlob`; verify dialog (`GlassDialog`, note textarea). Invalidate `campusOsKeys.cashDesk(iid, day)` and `campusOsKeys.fees(iid)` after verify. Section id `cash-desk` and `panel=cash` URL param scrolls to it (read `new URLSearchParams(location.search).get("panel")` on mount).

- [x] **Step 3: Record payment dialog** — `method` becomes controlled state (`const [method, setMethod] = useState("upi")`); when method is cash or cheque render `<label>Received by<select name="received_by_member_id" required defaultValue={myMemberId}>` listing active owner/admin/teacher members from `data.members`. Mutation passes `received_by_member_id` when present. Aging row gets an "Invoice" ghost button that calls `createInvoice(iid, assignment_id, null)` then `openBlob(invoicePdf(...))`.

- [x] **Step 4: Mount `<FeeCashDesk>` in ManagerFinance after the columns, before `FeeReminders`.**

- [x] **Step 5: Run vitest file → pass; ESLint + tsc clean.**

---

### Task 8: Learner UI and parent portal — pay online, invoices, receipts

**Files:**
- Modify: `frontend/src/components/institutions/CampusFinance.tsx` (LearnerFinance)
- Modify: `backend/app/services/parent_portal.py` (`_fees` adds `assignment_id`, `next_due.installment_id`)
- Modify: `frontend/src/api/parent-portal.ts`, `frontend/src/pages/parent/dashboard.tsx`
- Test: `fee-collection.test.tsx` (learner cases), `pages/__tests__/parent-dashboard.test.tsx` (Pay now)

- [x] **Step 1: Failing tests** — learner: mocked `onlineStatus` `{ready: true}`, `createOnlineOrder` returns checkout, `window.Razorpay` mocked class capturing options and exposing `open`; clicking "Pay online" on the first installment calls `createOnlineOrder(iid, aid, {installment_id: 1, amount: null})`, then invoking the captured `handler` calls `verifyOnlineOrder`. Second case: `onlineStatus` `{ready: false}` → notice text "Online payment is not set up for this campus yet" and buttons disabled. Parent: fees tile shows "Pay now" and "Invoice" when outstanding > 0.

- [x] **Step 2: LearnerFinance** — `useOnlineStatus`; `payOnline` mutation: create order → `openRazorpay(checkout, {onSuccess: verify → toast + refetch, onDismiss: reconcile once → refetch})`; errors via `errorMessage`. Per installment with balance > 0: "Pay online" (disabled when not ready) and "Invoice" (create + open). Header: "Pay balance". Receipt rows: "Receipt PDF" button. Notice when not ready.

- [x] **Step 3: Parent portal** — backend `_fees` returns `assignment_id` of the account holding `next_due` and `next_due.installment_id`; frontend tile footer gains "Pay now" (same flow, using `createOnlineOrder(institution.id, assignment_id, {installment_id})`) and "Invoice" (create for that assignment, whole balance, open PDF). Buttons only when `fees.outstanding > 0`.

- [x] **Step 4: Run backend `test_parent_portal.py`, frontend tests → pass; full vitest; ESLint; tsc; `npm run build`.**

---

### Task 9: Docs, release check, browser walk

- [x] Update `docs/CAMPUS_OS_RELEASE_2026_09_11.md` (fee collection entry, migration 0043, routes), `docs/INSTITUTION_BUILD.md` (verification section dated 12 Sep 2026), `CLAUDE.md` (feature entry), `scripts/campus_release_check.py` head → `{"0043"}`.
- [x] Run full backend gate: `pytest tests/test_fee_collection.py tests/test_tuition_finance.py tests/test_tuition_reminders.py tests/test_parent_portal.py tests/test_campus_action_center.py tests/test_campus_transport.py tests/test_campus_hostel.py -q`.
- [x] Browser walk with both preview servers: owner records cash with receiver → pending; second admin verifies; receipt PDF opens; invoice PDF opens; student sees Pay online disabled with the notice (no keys) and Invoice works; parent portal shows Pay now and Invoice.
- [x] Append ledger to this plan.

---

## Ledger (what actually happened, 12 September 2026)

- Tasks 1–5 backend: built as planned. `tests/test_fee_collection.py` 10 passed.
  Nine-suite regression sweep 60 passed. pyflakes clean on new modules.
- Deviation: three legacy tests recorded cash without a receiver
  (`test_tuition_finance.py:269`, `test_tuition_reminders.py:242,253`); switched
  to `upi` because the receiver is now mandatory for cash/cheque. Intentional.
- Deviation: test idempotency keys must be 8+ chars (endpoint rule); first run
  failed on that alone.
- Fix during browser walk: Today card hrefs and the reminder pay link used
  `?section=finance`; the app routes sections as a path segment, so both now use
  `/institutions/{id}/finance` (`?panel=cash` scrolls the cash desk into view).
- Fix during browser walk: the app QueryClient sets `mutations.retry: 1`, so a
  failed Pay now / verify fired twice. `retry: 0` set on the six money mutations
  (verify, manager invoice, learner pay/invoice, parent pay/invoice). Confirmed one
  click → one request afterwards.
- Preview SQLite is built by `create_all`; migration 0043 was applied by hand to
  `.local/campus-preview.sqlite` (columns + backfill + two tables) before the walk.
- Tasks 6–8 frontend: `fee-collection.test.tsx` 5 passed, `parent-dashboard.test.tsx`
  3 passed; full Vitest 466 passed in 78 files; ESLint 0; tsc 0; `npm run build` ok.
- Browser walk (owner → admin → student-1 → parent):
  owner recorded ₹500 cash with "Received by" defaulting to self → cash desk shows
  Pending; owner's own verify refused with the exact 409 message; receipt PDF and
  invoice PDF both `%PDF-1.4` (2.8 KB / 2.9 KB) over the API; admin verified with a
  note → single 200, row reads Verified, toast "Cash verified"; student-1 (Diya) sees
  the honest notice, all eight pay buttons disabled (no keys), invoice per
  installment issued and opened, receipt PDF opened, "received by Ananya Rao" on the
  receipt row; parent sees Pay now + Invoice on the fee tile, Pay now → 503 toast,
  Invoice → 201 + PDF 200. student-0 has no plan and correctly shows no buttons.
- Not verified: a real Razorpay checkout and webhook (no keys), PostgreSQL migration.
