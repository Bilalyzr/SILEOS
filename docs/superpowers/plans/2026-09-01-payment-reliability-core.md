# Payment Reliability Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee that every Razorpay payment captured at the gateway results in enrollment (or an admin alert) without buyer action, via a signature-verified webhook inbox, a shared idempotent fulfillment service, and a reconciliation sweeper.

**Architecture:** A new `webhook_events` Postgres inbox table receives signature-verified Razorpay events with DB-enforced idempotency (UNIQUE event_id). The Order/Payment/Enrollment write block currently inline in `/verify` is extracted into `fulfillment_service.fulfill_course_purchase()`, called by both `/verify` and the webhook processor — whichever runs first wins. An asyncio sweeper in the FastAPI lifespan retries failed inbox events and diffs paid gateway orders against local Payments.

**Tech Stack:** FastAPI 0.104.1, SQLAlchemy 2.0 (sync `Session` via `get_db`), Pydantic 2.4, razorpay 1.4.2, pytest 7.4 + pytest-asyncio (asyncio_mode=auto per `backend/pytest.ini`), SQLite in-memory for tests.

**Spec:** `docs/superpowers/specs/2026-09-01-payment-reliability-core-design.md`

## Global Constraints

- All paths below are relative to `backend/` unless prefixed otherwise. Working dir for commands: `backend/`.
- The payments router is mounted at prefix `/api/v1/payments` (main.py:1128) — route paths in `app/routers/payments.py` are written WITHOUT that prefix.
- No Alembic. Schema changes = SQLAlchemy model (source of truth for `init_db()`) **plus** a manual SQL file in `backend/migrations/`.
- Do NOT touch `app/routers/payments_proxy.py`, any `app/main_*.py` variant, or `app/core/config_broken.py`.
- `RAZORPAY_WEBHOOK_SECRET` already exists in `app/core/config.py` (line ~126) — do not re-add it.
- Existing `/verify` external behavior (request/response shape, defence-in-depth checks) must not change; only its write block moves into the fulfillment service.
- Money amounts: Razorpay speaks paise (int); local Order/Payment rows store rupees (float/Numeric). Convert at the boundary only.
- Admin gating uses `Depends(AuthService.require_admin)` (pattern throughout `app/routers/admin.py`).
- Email alerts go through `EmailService._send_smtp_email(to_email, subject, body)`; recipient is `getattr(settings, "ADMIN_EMAIL", "") or settings.EMAIL_FROM`.
- The repo is not currently a git repository. Task 1 initializes one. If the user has objected to git in the meantime, skip every "Commit" step instead of failing.
- Run tests with: `python -m pytest tests/<file>::<test> -v` from `backend/`.

---

### Task 1: Test harness bootstrap

**Files:**
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_harness.py`

**Interfaces:**
- Produces: pytest fixtures `db` (SQLAlchemy Session on in-memory SQLite with all tables created), `client` (FastAPI TestClient with `get_db` overridden), `student_user` (persisted User), `course` (persisted Course), `as_user(user)` (auth override helper). All later tasks' tests consume these.

- [ ] **Step 1: Initialize git (repo is not one yet)**

Run from the repo root (`Sasha_lms-main/`):
```bash
git init
git add -A
git commit -m "chore: baseline before payment reliability core"
```
`.gitignore` already exists at root. If `git init` is declined/unavailable, skip all commit steps in this plan.

- [ ] **Step 2: Write conftest.py**

```python
"""Shared test fixtures. In-memory SQLite; real app with get_db overridden."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
# Import every model module so Base.metadata knows all tables (mirrors main.py).
from app.models import (  # noqa: F401
    user, course, enrollment, payment, certificate, quiz, assignment,
    blog, coupon, instructor_review, company, company_dashboard,
    internship, internship_request, candidate, cohort, page_view,
)
from app.models.user import User
from app.models.course import Course
from app.main import app
from app.services.auth_service import AuthService


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db):
    def _get_db():
        yield db
    app.dependency_overrides[get_db] = _get_db
    with_client = TestClient(app, raise_server_exceptions=False)
    yield with_client
    app.dependency_overrides.clear()


def _make_user(db, login: str) -> User:
    u = User(
        user_login=login,
        user_pass="x",
        user_nicename=login,
        user_email=f"{login}@example.com",
        display_name=login,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def student_user(db):
    return _make_user(db, "student1")


@pytest.fixture()
def course(db):
    author = _make_user(db, "instructor1")
    c = Course(
        post_author=author.id,
        post_title="Test Course",
        course_price_type="paid",
        course_price=500.0,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def as_user():
    """Override auth to act as the given user. Usage: as_user(student_user)."""
    def _impl(user_obj):
        app.dependency_overrides[AuthService.get_current_active_user] = lambda: user_obj
        app.dependency_overrides[AuthService.require_admin] = lambda: user_obj
        return user_obj
    yield _impl
    app.dependency_overrides.pop(AuthService.get_current_active_user, None)
    app.dependency_overrides.pop(AuthService.require_admin, None)
```

- [ ] **Step 3: Write the sanity test**

```python
"""Harness sanity: tables create, app answers, auth override works."""


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_db_fixture_creates_rows(db, student_user, course):
    assert student_user.id is not None
    assert course.id is not None
```

- [ ] **Step 4: Run, expect PASS (fix model kwargs if NOT NULL errors appear)**

Run: `python -m pytest tests/test_harness.py -v`
Expected: 2 passed. A `NOT NULL constraint failed` error means a fixture is missing a required column — add it and re-run.

- [ ] **Step 5: Commit**

```bash
git add backend/tests
git commit -m "test: bootstrap backend test harness (sqlite + TestClient fixtures)"
```

---

### Task 2: WebhookEvent inbox model + SQL migration

**Files:**
- Create: `app/models/webhook_event.py`
- Modify: `app/models/__init__.py` (add `from app.models import webhook_event` style import, matching how other models are exported there)
- Modify: `backend/tests/conftest.py` (add `webhook_event` to the model-import tuple)
- Create: `backend/migrations/add_webhook_events_table.sql`
- Test: `backend/tests/test_webhook_event_model.py`

**Interfaces:**
- Produces: `WebhookEvent` model and `WebhookEventStatus` enum (`RECEIVED`/`PROCESSED`/`FAILED`/`SKIPPED`), columns exactly as below. Tasks 5–7 consume both.

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime, timezone

from app.models.webhook_event import WebhookEvent, WebhookEventStatus


def test_webhook_event_roundtrip(db):
    ev = WebhookEvent(
        event_id="evt_123",
        event_type="payment.captured",
        payload={"a": 1},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    assert ev.status == WebhookEventStatus.RECEIVED
    assert ev.attempts == 0
    assert ev.received_at is not None


def test_event_id_unique(db):
    db.add(WebhookEvent(event_id="evt_dup", event_type="x", payload={}, signature_valid=True))
    db.commit()
    db.add(WebhookEvent(event_id="evt_dup", event_type="x", payload={}, signature_valid=True))
    import pytest as _pytest
    from sqlalchemy.exc import IntegrityError
    with _pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_webhook_event_model.py -v`
Expected: FAIL — `ModuleNotFoundError: app.models.webhook_event`

- [ ] **Step 3: Write the model**

```python
"""Durable inbox for Razorpay webhook events.

The UNIQUE constraint on event_id IS the idempotency mechanism: duplicate
gateway deliveries insert-conflict into a no-op. Rows are never deleted —
they are the audit trail for the money pipeline.
"""
import enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.types import Enum
from sqlalchemy.sql import func

from app.core.database import Base


class WebhookEventStatus(enum.Enum):
    RECEIVED = "received"    # stored, not yet (successfully) processed
    PROCESSED = "processed"  # handler completed
    FAILED = "failed"        # handler raised; sweeper retries up to 5x
    SKIPPED = "skipped"      # valid signature, event type we don't handle yet


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, default="")
    payload = Column(JSON, nullable=False, default={})
    signature_valid = Column(Boolean, nullable=False, default=False)
    status = Column(
        Enum(WebhookEventStatus), nullable=False, default=WebhookEventStatus.RECEIVED
    )
    attempts = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, event_id={self.event_id}, type={self.event_type}, status={self.status})>"
```

Register it: add the import to `app/models/__init__.py` following the file's existing style, and add `webhook_event` to the conftest model-import tuple.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_webhook_event_model.py -v`
Expected: 2 passed

- [ ] **Step 5: Write the SQL migration for live deployments**

```sql
-- Payment Reliability Core: webhook inbox.
-- init_db() creates this automatically on fresh databases; run this file
-- manually against existing production Postgres:
--   docker-compose exec postgres psql -U tutor -d tutor_lms -f /path/to/this.sql

CREATE TABLE IF NOT EXISTS webhook_events (
    id              SERIAL PRIMARY KEY,
    event_id        VARCHAR(255) NOT NULL UNIQUE,
    event_type      VARCHAR(100) NOT NULL DEFAULT '',
    payload         JSON NOT NULL DEFAULT '{}',
    signature_valid BOOLEAN NOT NULL DEFAULT FALSE,
    status          VARCHAR(20) NOT NULL DEFAULT 'RECEIVED',
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    last_error      TEXT,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_webhook_events_event_id ON webhook_events (event_id);
CREATE INDEX IF NOT EXISTS ix_webhook_events_status ON webhook_events (status);
```

NOTE the `status` column: SQLAlchemy's `Enum(WebhookEventStatus)` stores the **name** (`RECEIVED`), matching the default above. Verify by checking how existing enum columns look in the DB (`orders.order_status` uses the same pattern).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/webhook_event.py backend/app/models/__init__.py backend/migrations/add_webhook_events_table.sql backend/tests
git commit -m "feat: add webhook_events inbox table with unique event_id idempotency"
```

---

### Task 3: Pydantic contracts on /create-order and /verify

**Files:**
- Modify: `app/schemas/payment.py` (append the three models below)
- Modify: `app/routers/payments.py` (replace `request: dict` on both endpoints)
- Test: `backend/tests/test_payment_contracts.py`

**Interfaces:**
- Consumes: Task 1 fixtures.
- Produces: `CreateOrderRequest`, `VerifyPaymentRequest`, `VerifyPaymentResponse` in `app.schemas.payment`. `/verify`'s handler signature becomes `verify_razorpay_payment(request: VerifyPaymentRequest, ...)`; Task 4 modifies that same handler body.

- [ ] **Step 1: Write the failing tests**

```python
def test_create_order_rejects_missing_course_id(client, as_user, student_user):
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"coupon_code": "X"})
    assert r.status_code == 422


def test_create_order_rejects_non_int_course_id(client, as_user, student_user):
    as_user(student_user)
    r = client.post("/api/v1/payments/create-order", json={"course_id": "abc"})
    assert r.status_code == 422


def test_verify_rejects_missing_fields(client, as_user, student_user):
    as_user(student_user)
    r = client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": "order_x", "course_id": 1},
    )
    assert r.status_code == 422


def test_verify_rejects_malformed_gateway_ids(client, as_user, student_user):
    as_user(student_user)
    r = client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_order_id": "not-an-order-id",
            "razorpay_payment_id": "pay_ok123",
            "razorpay_signature": "ab" * 32,
            "course_id": 1,
        },
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_payment_contracts.py -v`
Expected: FAIL — current endpoints accept any dict, so these return 400 (or 404), not 422.

- [ ] **Step 3: Add the schemas**

Append to `app/schemas/payment.py` (match the file's existing import style; it already imports `BaseModel`):

```python
class CreateOrderRequest(BaseModel):
    """Body of POST /api/v1/payments/create-order. Field names mirror the
    frontend payload exactly — do not rename."""
    course_id: int
    coupon_code: str | None = None


class VerifyPaymentRequest(BaseModel):
    """Body of POST /api/v1/payments/verify."""
    razorpay_order_id: str = Field(pattern=r"^order_[A-Za-z0-9]+$", max_length=64)
    razorpay_payment_id: str = Field(pattern=r"^pay_[A-Za-z0-9]+$", max_length=64)
    razorpay_signature: str = Field(min_length=32, max_length=256)
    course_id: int


class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    cohort_id: int | None = None
```

If `Field` is not already imported in the file, add it to the pydantic import line.

- [ ] **Step 4: Swap the endpoint signatures**

In `app/routers/payments.py`:

1. Add to imports: `from app.schemas.payment import CreateOrderRequest, VerifyPaymentRequest, VerifyPaymentResponse`
2. `/create-order`: change `request: dict` → `request: CreateOrderRequest`. Replace `course_id = request.get("course_id")` and the manual `int()` guard (lines ~109–117) with `course_pk = request.course_id`, and `coupon_code = request.get("coupon_code")` (line ~148) with `coupon_code = request.coupon_code`. Delete the now-dead "course_id is required" and "must be an integer" HTTPExceptions.
3. `/verify`: change `request: dict` → `request: VerifyPaymentRequest`, add `response_model=VerifyPaymentResponse` to the decorator. Replace the four `request.get(...)` lines and the `if not all([...])` guard (lines ~268–274) with direct attribute access (`request.razorpay_order_id`, etc.). Everywhere below in the handler that referenced the old locals keeps working because you assign the same local names.

- [ ] **Step 5: Run contract tests + full suite**

Run: `python -m pytest tests/ -v`
Expected: all pass (contract tests now 422; harness tests still green).

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/payment.py backend/app/routers/payments.py backend/tests
git commit -m "feat: Pydantic contracts on create-order and verify endpoints"
```

---

### Task 4: Extract the shared fulfillment service

**Files:**
- Create: `app/services/fulfillment_service.py`
- Modify: `app/routers/payments.py` (`/verify` handler delegates its write block)
- Test: `backend/tests/test_fulfillment_service.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces (Tasks 5–6 call this exact signature):

```python
@dataclass
class FulfillmentResult:
    created_order: bool          # False when payment id already had an Order (no-op replay)
    order_id: int
    is_new_enrollment: bool
    cohort_id: int | None

def fulfill_course_purchase(
    db: Session, *,
    user: User,
    course: Course,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    paid_amount: float,          # rupees actually captured
    base_price: float,           # list price before coupon
    coupon_discount: float = 0.0,
    currency: str = "INR",
    cohort: Cohort | None = None,
    referral_code_id: int | None = None,
    coupon: "Coupon | None" = None,   # when set, records CouponUsage + bumps usage_count
) -> FulfillmentResult
```

The service does **not** commit — the caller owns commit/rollback. It may raise `CouponError` (referral exhausted); callers decide policy.

- [ ] **Step 1: Write the failing tests**

```python
from app.services.fulfillment_service import fulfill_course_purchase
from app.models.payment import Order, Payment
from app.models.enrollment import Enrollment


def _fulfill(db, user, course, pay_id="pay_A1", **kw):
    return fulfill_course_purchase(
        db, user=user, course=course,
        razorpay_order_id="order_A1", razorpay_payment_id=pay_id,
        paid_amount=500.0, base_price=500.0, **kw,
    )


def test_creates_order_payment_enrollment(db, student_user, course):
    res = _fulfill(db, student_user, course)
    db.commit()
    assert res.created_order and res.is_new_enrollment
    assert db.query(Order).count() == 1
    assert db.query(Payment).filter_by(gateway_payment_id="pay_A1").count() == 1
    assert db.query(Enrollment).filter_by(
        user_id=student_user.id, course_id=course.id
    ).count() == 1


def test_replay_same_payment_id_is_noop(db, student_user, course):
    _fulfill(db, student_user, course)
    db.commit()
    res2 = _fulfill(db, student_user, course)
    db.commit()
    assert not res2.created_order
    assert db.query(Order).count() == 1
    assert db.query(Payment).count() == 1
    assert db.query(Enrollment).count() == 1


def test_coupon_discount_recorded_on_order(db, student_user, course):
    res = fulfill_course_purchase(
        db, user=student_user, course=course,
        razorpay_order_id="order_C1", razorpay_payment_id="pay_C1",
        paid_amount=400.0, base_price=500.0, coupon_discount=100.0,
    )
    db.commit()
    row = db.query(Order).get(res.order_id)
    assert float(row.total_amount) == 400.0
    assert float(row.discount_amount) == 100.0
    assert float(row.subtotal_amount) == 500.0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fulfillment_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.fulfillment_service`

- [ ] **Step 3: Create the service by MOVING the /verify write block**

Create `app/services/fulfillment_service.py`. The body is the existing block at `app/routers/payments.py` lines ~362–482 (from the `order_row = db.query(Order)...` lookup through the CouponUsage write), transplanted with these mechanical changes:

- `current_user` → `user`; `cohort_to_assign` → `cohort`; `referral_code_id_note` → `referral_code_id`.
- Coupon recording: the old code checked `resolved is not None and resolved.kind == "coupon"`; the service instead checks `coupon is not None` and uses `coupon.id` / bumps `coupon.usage_count`.
- `order.get("currency")` → the `currency` kwarg; `base_price`/`paid_amount`/`coupon_discount` come from kwargs.
- Remove `db.commit()` / rollback / HTTPException — the service raises nothing except letting `CouponError` from `lock_referral_and_bump` propagate. Keep the "only bump referral / record coupon on NEW enrollment" conditionals exactly as they are.
- Return `FulfillmentResult(created_order=..., order_id=order_row.id, is_new_enrollment=..., cohort_id=cohort.id if cohort else None)` where `created_order` is True iff the initial lookup found no existing Order.

Imports needed: `dataclasses.dataclass`, `uuid`, `datetime/timezone`, `Session`, the models (`Order`, `OrderItem`, `OrderStatus`, `Payment`, `PaymentStatus`, `Enrollment`, `Course`, `Cohort`, `CohortMembership`, `User`, `CouponUsage` from `app.models.coupon`), and `lock_referral_and_bump` from `app.services.coupon_service`.

- [ ] **Step 4: Run service tests**

Run: `python -m pytest tests/test_fulfillment_service.py -v`
Expected: 3 passed

- [ ] **Step 5: Make /verify delegate to it**

In `app/routers/payments.py`, replace the moved block inside the `try:` with:

```python
        result = fulfill_course_purchase(
            db,
            user=current_user,
            course=course,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            paid_amount=paid_amount,
            base_price=base_price,
            coupon_discount=coupon_discount,
            currency=order.get("currency") or "INR",
            cohort=cohort_to_assign,
            referral_code_id=int(referral_code_id_note) if referral_code_id_note else None,
            coupon=resolved.coupon if (resolved is not None and resolved.kind == "coupon") else None,
        )
        db.commit()
```

Wrap the call so `CouponError` maps to the existing 409 ("Referral code exhausted after payment") — keep that except-branch, now catching `CouponError` around the service call instead of inside the block. Keep the existing generic `except Exception` rollback + logged "contact support" 500. Add `from app.services.fulfillment_service import fulfill_course_purchase` and `from app.services.coupon_service import CouponError` (already imported) to the imports. Return `{"success": True, "message": ..., "cohort_id": result.cohort_id}` as before.

- [ ] **Step 6: Full suite**

Run: `python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/fulfillment_service.py backend/app/routers/payments.py backend/tests
git commit -m "refactor: extract idempotent fulfillment service from /verify"
```

---

### Task 5: Webhook endpoint + event processor

**Files:**
- Create: `app/services/webhook_processor.py`
- Modify: `app/routers/payments.py` (add `POST /webhook`)
- Modify: `app/services/email_service.py` (add `send_payment_alert`)
- Test: `backend/tests/test_webhook_endpoint.py`

**Interfaces:**
- Consumes: `WebhookEvent`/`WebhookEventStatus` (Task 2), `fulfill_course_purchase` (Task 4).
- Produces: `process_webhook_event(db, event: WebhookEvent) -> None` (sets event.status/attempts/last_error/last_attempt_at/processed_at; does its own commit), and `EmailService.send_payment_alert(subject: str, body: str) -> bool`. Task 6's sweeper calls `process_webhook_event`; Tasks 5–6 both call `send_payment_alert`.

- [ ] **Step 1: Write the failing tests**

```python
import hashlib
import hmac
import json

from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.models.payment import Order, Payment
from app.models.enrollment import Enrollment
from app.core.config import get_settings

SECRET = "whsec_test"


def _sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def _captured_event(user, course, event_id="evt_1", pay_id="pay_W1", amount_paise=50000):
    return {
        "entity": "event",
        "event": "payment.captured",
        "id": event_id,
        "payload": {"payment": {"entity": {
            "id": pay_id,
            "order_id": "order_W1",
            "amount": amount_paise,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(user.id)},
        }}},
    }


def _post(client, payload, event_id=None, sig=None):
    body = json.dumps(payload).encode()
    headers = {"X-Razorpay-Signature": sig if sig is not None else _sign(body)}
    if event_id:
        headers["X-Razorpay-Event-Id"] = event_id
    return client.post(
        "/api/v1/payments/webhook", content=body,
        headers={**headers, "Content-Type": "application/json"},
    )


def _set_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "RAZORPAY_WEBHOOK_SECRET", SECRET, raising=False)


def test_invalid_signature_stored_unprocessed_400(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    r = _post(client, _captured_event(student_user, course), event_id="evt_bad", sig="0" * 64)
    assert r.status_code == 400
    ev = db.query(WebhookEvent).filter_by(event_id="evt_bad").one()
    assert ev.signature_valid is False
    assert ev.status != WebhookEventStatus.PROCESSED
    assert db.query(Enrollment).count() == 0


def test_captured_event_enrolls_buyer(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    r = _post(client, _captured_event(student_user, course), event_id="evt_ok")
    assert r.status_code == 200
    ev = db.query(WebhookEvent).filter_by(event_id="evt_ok").one()
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Payment).filter_by(gateway_payment_id="pay_W1").count() == 1
    assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 1


def test_duplicate_delivery_is_noop(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    payload = _captured_event(student_user, course, event_id="evt_dup2")
    assert _post(client, payload, event_id="evt_dup2").status_code == 200
    assert _post(client, payload, event_id="evt_dup2").status_code == 200
    assert db.query(WebhookEvent).filter_by(event_id="evt_dup2").count() == 1
    assert db.query(Order).count() == 1
    assert db.query(Enrollment).count() == 1


def test_webhook_after_verify_is_noop(client, db, monkeypatch, student_user, course):
    """The /verify-vs-webhook race: whichever runs first wins, second no-ops.
    Simulates /verify having already fulfilled by calling the same service."""
    _set_secret(monkeypatch)
    from app.services.fulfillment_service import fulfill_course_purchase
    fulfill_course_purchase(
        db, user=student_user, course=course,
        razorpay_order_id="order_W1", razorpay_payment_id="pay_race",
        paid_amount=500.0, base_price=500.0,
    )
    db.commit()
    payload = _captured_event(student_user, course, event_id="evt_race", pay_id="pay_race")
    assert _post(client, payload, event_id="evt_race").status_code == 200
    ev = db.query(WebhookEvent).filter_by(event_id="evt_race").one()
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Order).count() == 1
    assert db.query(Payment).count() == 1
    assert db.query(Enrollment).count() == 1


def test_unknown_event_type_skipped(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    payload = {"entity": "event", "event": "subscription.activated", "id": "evt_sub", "payload": {}}
    assert _post(client, payload, event_id="evt_sub").status_code == 200
    ev = db.query(WebhookEvent).filter_by(event_id="evt_sub").one()
    assert ev.status == WebhookEventStatus.SKIPPED


def test_refund_marks_payment_refunded_keeps_enrollment(client, db, monkeypatch, student_user, course):
    _set_secret(monkeypatch)
    _post(client, _captured_event(student_user, course, event_id="evt_c", pay_id="pay_R1"), event_id="evt_c")
    refund = {
        "entity": "event", "event": "refund.processed", "id": "evt_r",
        "payload": {"refund": {"entity": {"id": "rfnd_1", "payment_id": "pay_R1"}}},
    }
    assert _post(client, refund, event_id="evt_r").status_code == 200
    from app.models.payment import PaymentStatus
    p = db.query(Payment).filter_by(gateway_payment_id="pay_R1").one()
    assert p.payment_status == PaymentStatus.REFUNDED
    assert db.query(Enrollment).count() == 1  # NOT revoked
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_webhook_endpoint.py -v`
Expected: FAIL — 404 on `/api/v1/payments/webhook` (route doesn't exist).

- [ ] **Step 3: Add `EmailService.send_payment_alert`**

Append inside `class EmailService` in `app/services/email_service.py`:

```python
    @staticmethod
    def send_payment_alert(subject: str, body: str) -> bool:
        """Operational alert for the payment pipeline (reconciliation
        failures, unfixable orphaned captures). Falls back to logging when
        SMTP is unconfigured — the alert must never crash the caller."""
        to_email = getattr(settings, "ADMIN_EMAIL", "") or settings.EMAIL_FROM
        try:
            sent = EmailService._send_smtp_email(to_email, f"[LMS payments] {subject}", body)
        except Exception:
            logger.exception("payment alert email raised")
            sent = False
        if not sent:
            logger.error("PAYMENT ALERT (email not sent): %s — %s", subject, body)
        return sent
```

- [ ] **Step 4: Write the processor**

Create `app/services/webhook_processor.py`:

```python
"""Applies a stored WebhookEvent to local state. Idempotent: safe to run on
the same event any number of times (fulfillment is keyed on the gateway
payment id; refund/failed handlers are naturally idempotent updates)."""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.cohort import Cohort
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.fulfillment_service import fulfill_course_purchase
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

HANDLED_EVENTS = {"payment.captured", "payment.failed", "refund.processed"}


class UnrecoverableEvent(Exception):
    """Event can never be applied (bad notes etc.) — alert, don't retry."""


def process_webhook_event(db: Session, event: WebhookEvent) -> None:
    event.attempts = (event.attempts or 0) + 1
    event.last_attempt_at = datetime.now(timezone.utc)
    try:
        if event.event_type not in HANDLED_EVENTS:
            event.status = WebhookEventStatus.SKIPPED
        elif event.event_type == "payment.captured":
            _handle_payment_captured(db, event)
            event.status = WebhookEventStatus.PROCESSED
        elif event.event_type == "payment.failed":
            # No local Order exists before fulfillment, so there is usually
            # nothing to update — recording the event IS the handling.
            event.status = WebhookEventStatus.PROCESSED
        elif event.event_type == "refund.processed":
            _handle_refund_processed(db, event)
            event.status = WebhookEventStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        event.last_error = None
        db.commit()
    except UnrecoverableEvent as exc:
        db.rollback()
        event.status = WebhookEventStatus.FAILED
        event.attempts = 5  # exhaust retries: retrying cannot fix this
        event.last_error = str(exc)
        db.commit()
        EmailService.send_payment_alert(
            f"unrecoverable webhook event {event.event_id}",
            f"type={event.event_type} error={exc}\nManual reconciliation needed.",
        )
    except Exception as exc:
        db.rollback()
        event.status = WebhookEventStatus.FAILED
        event.last_error = f"{type(exc).__name__}: {exc}"
        db.commit()
        logger.exception("webhook event %s processing failed", event.event_id)


def _payment_entity(event: WebhookEvent) -> dict:
    return ((event.payload or {}).get("payload", {})
            .get("payment", {}).get("entity", {}))


def _handle_payment_captured(db: Session, event: WebhookEvent) -> None:
    entity = _payment_entity(event)
    payment_id = entity.get("id")
    if not payment_id:
        raise UnrecoverableEvent("payment.captured without payment id")

    if db.query(Payment).filter(Payment.gateway_payment_id == str(payment_id)).first():
        return  # /verify (or a prior run) already fulfilled — no-op

    notes = entity.get("notes") or {}
    try:
        user_id = int(notes.get("user_id"))
        course_id = int(notes.get("course_id"))
    except (TypeError, ValueError):
        raise UnrecoverableEvent(
            f"unusable notes on payment {payment_id}: {notes!r} "
            f"(amount={entity.get('amount')})"
        )

    user = db.query(User).filter(User.id == user_id).first()
    course = db.query(Course).filter(Course.id == course_id).first()
    if not user or not course:
        raise UnrecoverableEvent(
            f"user {user_id} or course {course_id} not found for payment {payment_id}"
        )

    paid_amount = int(entity.get("amount") or 0) / 100.0
    base_price = float(course.course_price or 0)
    coupon_discount = max(0.0, base_price - paid_amount)

    cohort = None
    if notes.get("cohort_id"):
        cohort = db.query(Cohort).filter(Cohort.id == int(notes["cohort_id"])).first()
        if cohort and not cohort.is_active:
            cohort = None

    referral_id = notes.get("referral_code_id")
    fulfill_course_purchase(
        db, user=user, course=course,
        razorpay_order_id=str(entity.get("order_id") or ""),
        razorpay_payment_id=str(payment_id),
        paid_amount=paid_amount, base_price=base_price,
        coupon_discount=coupon_discount,
        currency=str(entity.get("currency") or "INR"),
        cohort=cohort,
        referral_code_id=int(referral_id) if referral_id else None,
        coupon=None,  # webhook path records the discount amount, not CouponUsage
    )


def _handle_refund_processed(db: Session, event: WebhookEvent) -> None:
    entity = ((event.payload or {}).get("payload", {})
              .get("refund", {}).get("entity", {}))
    payment_id = entity.get("payment_id")
    if not payment_id:
        raise UnrecoverableEvent("refund.processed without payment_id")
    payment = db.query(Payment).filter(
        Payment.gateway_payment_id == str(payment_id)
    ).first()
    if payment:
        payment.payment_status = PaymentStatus.REFUNDED
    # Enrollment is deliberately NOT revoked — /admin/payment-health surfaces
    # refunded payments with live enrollments for a human decision.
```

Note on `CouponError`: `fulfill_course_purchase` can raise it (referral exhausted). It is not `UnrecoverableEvent`, so it lands in the generic handler → `FAILED` + retries; after 5 attempts it appears in payment-health. That is the intended policy.

- [ ] **Step 5: Add the endpoint**

In `app/routers/payments.py` add imports (`Request` from fastapi, `IntegrityError` from sqlalchemy.exc, `WebhookEvent`/`WebhookEventStatus`, `process_webhook_event`) and:

```python
@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Razorpay server-to-server webhook. Unauthenticated by design —
    authenticity comes from the HMAC signature over the RAW body."""
    raw_body = await request.body()

    settings = get_settings()
    secret = _clean_cred(settings.RAZORPAY_WEBHOOK_SECRET)
    if not secret:
        logger.error("webhook received but RAZORPAY_WEBHOOK_SECRET unset")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    provided_sig = request.headers.get("X-Razorpay-Signature", "")
    expected_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    signature_valid = hmac.compare_digest(expected_sig, provided_sig)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Malformed body")

    event_id = request.headers.get("X-Razorpay-Event-Id") or payload.get("id") or ""
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event id")

    event = WebhookEvent(
        event_id=str(event_id),
        event_type=str(payload.get("event") or ""),
        payload=payload,
        signature_valid=signature_valid,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # duplicate delivery — UNIQUE(event_id): ack and stop
        return {"status": "ok"}

    if not signature_valid:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Inline fast path. On failure the row stays FAILED and the sweeper
    # retries — always ack so Razorpay doesn't redeliver what we hold.
    process_webhook_event(db, event)
    return {"status": "ok"}
```

Add `import json` to the module imports.

- [ ] **Step 6: Run webhook tests + full suite**

Run: `python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/webhook_processor.py backend/app/services/email_service.py backend/app/routers/payments.py backend/tests
git commit -m "feat: Razorpay webhook endpoint with durable idempotent inbox"
```

---

### Task 6: Reconciliation sweeper

**Files:**
- Create: `app/services/reconciliation.py`
- Modify: `app/main.py` (lifespan: start/stop the loop task)
- Test: `backend/tests/test_reconciliation.py`

**Interfaces:**
- Consumes: `process_webhook_event` (Task 5), `fulfill_course_purchase` (Task 4), `EmailService.send_payment_alert` (Task 5), `SessionLocal` from `app.core.database`, `_razorpay_client` pattern from `app/routers/payments.py`.
- Produces: `retry_failed_events(db) -> int`, `reconcile_gateway_orders(db, client, lookback_hours=24) -> int`, `reconciliation_loop()` (asyncio task target). Task 7's health endpoint reads the same tables; nothing else consumes these functions.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime, timedelta, timezone

from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.reconciliation import retry_failed_events, reconcile_gateway_orders


def _failed_event(db, user, course, event_id="evt_f1", attempts=1, minutes_ago=60):
    ev = WebhookEvent(
        event_id=event_id,
        event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": f"pay_{event_id}", "order_id": "order_f", "amount": 50000,
            "currency": "INR",
            "notes": {"course_id": str(course.id), "user_id": str(user.id)},
        }}}},
        signature_valid=True,
        status=WebhookEventStatus.FAILED,
        attempts=attempts,
        last_attempt_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    db.add(ev)
    db.commit()
    return ev


def test_retry_reprocesses_eligible_failed_event(db, student_user, course):
    _failed_event(db, student_user, course)
    n = retry_failed_events(db)
    assert n == 1
    ev = db.query(WebhookEvent).filter_by(event_id="evt_f1").one()
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Enrollment).count() == 1


def test_retry_respects_backoff_and_max_attempts(db, student_user, course):
    _failed_event(db, student_user, course, event_id="evt_young", attempts=3, minutes_ago=1)
    _failed_event(db, student_user, course, event_id="evt_dead", attempts=5, minutes_ago=999)
    assert retry_failed_events(db) == 0
    assert db.query(Enrollment).count() == 0


class FakeRzpClient:
    """Mimics razorpay.Client surface used by the sweeper."""
    def __init__(self, orders, payments_by_order):
        self._orders = orders
        self._pbo = payments_by_order
        self.order = self

    def all(self, opts):
        return {"items": self._orders}

    def payments(self, order_id):
        return {"items": self._pbo.get(order_id, [])}


def test_gateway_diff_fulfills_orphan(db, student_user, course):
    client = FakeRzpClient(
        orders=[{"id": "order_G1", "status": "paid", "amount": 50000,
                 "notes": {"course_id": str(course.id), "user_id": str(student_user.id)}}],
        payments_by_order={"order_G1": [
            {"id": "pay_G1", "status": "captured", "amount": 50000, "currency": "INR"},
        ]},
    )
    n = reconcile_gateway_orders(db, client)
    assert n == 1
    assert db.query(Payment).filter_by(gateway_payment_id="pay_G1").count() == 1
    assert db.query(Enrollment).count() == 1
    # Second run: nothing to do.
    assert reconcile_gateway_orders(db, client) == 0


def test_gateway_diff_alerts_on_garbage_notes(db, monkeypatch):
    sent = []
    from app.services import reconciliation as rec
    monkeypatch.setattr(
        rec.EmailService, "send_payment_alert",
        staticmethod(lambda subject, body: sent.append(subject) or True),
    )
    client = FakeRzpClient(
        orders=[{"id": "order_BAD", "status": "paid", "amount": 50000, "notes": {}}],
        payments_by_order={"order_BAD": [
            {"id": "pay_BAD", "status": "captured", "amount": 50000, "currency": "INR"},
        ]},
    )
    assert reconcile_gateway_orders(db, client) == 0
    assert len(sent) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_reconciliation.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.reconciliation`

- [ ] **Step 3: Write the sweeper**

```python
"""Reconciliation: the safety net behind /verify and the webhook.

Cycle cadence (driven by reconciliation_loop):
  - every RETRY_INTERVAL (5 min): re-run FAILED inbox events, backoff 2^attempts minutes, max 5 attempts
  - every GATEWAY_DIFF_EVERY cycles (30 min): diff paid gateway orders vs local payments

Postgres advisory lock makes the loop replica-safe; the two pure functions
below take a Session and are unit-testable without the loop.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.payment import Payment
from app.models.user import User
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.email_service import EmailService
from app.services.fulfillment_service import fulfill_course_purchase
from app.services.webhook_processor import process_webhook_event

logger = logging.getLogger(__name__)

RETRY_INTERVAL_SECONDS = 300
GATEWAY_DIFF_EVERY = 6          # 6 * 5 min = 30 min
MAX_ATTEMPTS = 5
ADVISORY_LOCK_KEY = 931842


def retry_failed_events(db: Session) -> int:
    """Reprocess eligible FAILED events. Returns number reprocessed."""
    now = datetime.now(timezone.utc)
    candidates = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.status == WebhookEventStatus.FAILED,
            WebhookEvent.attempts < MAX_ATTEMPTS,
            WebhookEvent.signature_valid.is_(True),
        )
        .all()
    )
    count = 0
    for ev in candidates:
        backoff = timedelta(minutes=2 ** (ev.attempts or 0))
        last = ev.last_attempt_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last is not None and now - last < backoff:
            continue
        process_webhook_event(db, ev)
        count += 1
    return count


def reconcile_gateway_orders(db: Session, client, lookback_hours: int = 24) -> int:
    """Fulfill paid gateway orders that have no local Payment row.
    Returns number fulfilled. Alerts (never raises) on unusable orders."""
    since = int(time.time()) - lookback_hours * 3600
    try:
        orders = (client.order.all({"from": since, "count": 100}) or {}).get("items", [])
    except Exception:
        logger.exception("gateway order listing failed")
        return 0

    fulfilled = 0
    for order in orders:
        if order.get("status") != "paid":
            continue
        try:
            payments = (client.order.payments(order["id"]) or {}).get("items", [])
        except Exception:
            logger.exception("payments fetch failed for %s", order.get("id"))
            continue
        captured = next((p for p in payments if p.get("status") == "captured"), None)
        if not captured:
            continue
        pay_id = str(captured.get("id"))
        if db.query(Payment).filter(Payment.gateway_payment_id == pay_id).first():
            continue  # already fulfilled

        notes = order.get("notes") or {}
        try:
            user_id = int(notes.get("user_id"))
            course_id = int(notes.get("course_id"))
        except (TypeError, ValueError):
            EmailService.send_payment_alert(
                f"orphaned capture {pay_id} — unusable notes",
                f"gateway order {order.get('id')} amount={order.get('amount')} "
                f"notes={notes!r}. Fulfil manually.",
            )
            continue
        user = db.query(User).filter(User.id == user_id).first()
        course = db.query(Course).filter(Course.id == course_id).first()
        if not user or not course:
            EmailService.send_payment_alert(
                f"orphaned capture {pay_id} — user/course missing",
                f"user_id={user_id} course_id={course_id} "
                f"gateway order {order.get('id')}. Fulfil manually.",
            )
            continue
        try:
            paid_amount = int(captured.get("amount") or 0) / 100.0
            base_price = float(course.course_price or 0)
            fulfill_course_purchase(
                db, user=user, course=course,
                razorpay_order_id=str(order["id"]),
                razorpay_payment_id=pay_id,
                paid_amount=paid_amount, base_price=base_price,
                coupon_discount=max(0.0, base_price - paid_amount),
                currency=str(captured.get("currency") or "INR"),
            )
            db.commit()
            fulfilled += 1
            logger.warning(
                "reconciliation fulfilled orphaned capture %s (user %s, course %s)",
                pay_id, user_id, course_id,
            )
        except Exception as exc:
            db.rollback()
            logger.exception("reconciliation fulfillment failed for %s", pay_id)
            EmailService.send_payment_alert(
                f"reconciliation failed for capture {pay_id}",
                f"error: {exc}. Fulfil manually.",
            )
    return fulfilled


def _run_cycle(cycle_index: int) -> None:
    """One synchronous sweep. Own session; advisory-locked on Postgres."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        locked = True
        if db.bind.dialect.name == "postgresql":
            locked = db.execute(
                text("SELECT pg_try_advisory_lock(:k)"), {"k": ADVISORY_LOCK_KEY}
            ).scalar()
        if not locked:
            return
        try:
            retry_failed_events(db)
            if cycle_index % GATEWAY_DIFF_EVERY == 0:
                client = _gateway_client()
                if client is not None:
                    reconcile_gateway_orders(db, client)
        finally:
            if db.bind.dialect.name == "postgresql":
                db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": ADVISORY_LOCK_KEY})
                db.commit()
    finally:
        db.close()


def _gateway_client():
    from app.routers.payments import _razorpay_creds
    import razorpay
    key_id, key_secret = _razorpay_creds()
    if not key_id or not key_secret:
        return None
    return razorpay.Client(auth=(key_id, key_secret))


async def reconciliation_loop() -> None:
    cycle = 0
    while True:
        try:
            await asyncio.to_thread(_run_cycle, cycle)
        except Exception:
            logger.exception("reconciliation cycle crashed (continuing)")
        cycle += 1
        await asyncio.sleep(RETRY_INTERVAL_SECONDS)
```

- [ ] **Step 4: Run sweeper tests**

Run: `python -m pytest tests/test_reconciliation.py -v`
Expected: 4 passed

- [ ] **Step 5: Wire into lifespan**

In `app/main.py`, inside `lifespan` (starts at line ~59): after the `await init_redis()` line add

```python
    # Payment reconciliation sweeper (see app/services/reconciliation.py).
    from app.services.reconciliation import reconciliation_loop
    reconciliation_task = asyncio.create_task(reconciliation_loop())
```

then locate the function's `yield` and add immediately after it (before any existing shutdown code):

```python
    reconciliation_task.cancel()
    try:
        await reconciliation_task
    except asyncio.CancelledError:
        pass
```

Add `import asyncio` to main.py's imports if absent.

- [ ] **Step 6: Full suite + app boots**

Run: `python -m pytest tests/ -v`
Expected: all pass.
Then verify the app still imports cleanly: `python -c "from app.main import app; print('ok')"`
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/reconciliation.py backend/app/main.py backend/tests
git commit -m "feat: reconciliation sweeper (inbox retries + gateway diff)"
```

---

### Task 7: Admin payment-health endpoint, message copy, env + docs

**Files:**
- Modify: `app/routers/admin.py` (add `GET /payment-health`)
- Modify: `app/routers/payments.py` (soften the `/verify` bookkeeping-failure 500 message)
- Modify: `.env.example` AND `backend/.env.example` (document `RAZORPAY_WEBHOOK_SECRET`)
- Modify: `CLAUDE.md` (payments architecture notes)
- Test: `backend/tests/test_payment_health.py`

**Interfaces:**
- Consumes: `WebhookEvent`/`WebhookEventStatus`, `Payment`/`PaymentStatus`, `Enrollment`, `AuthService.require_admin`.
- Produces: `GET /api/v1/admin/payment-health` (admin-gated) returning the JSON shape asserted below. Nothing downstream consumes it programmatically.

- [ ] **Step 1: Write the failing tests**

```python
from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderStatus, Payment, PaymentStatus
from app.models.webhook_event import WebhookEvent, WebhookEventStatus


def _seed(db, student_user, course):
    db.add(WebhookEvent(event_id="evt_bad1", event_type="payment.captured",
                        payload={}, signature_valid=True,
                        status=WebhookEventStatus.FAILED, attempts=5,
                        last_error="boom"))
    db.add(WebhookEvent(event_id="evt_skip1", event_type="subscription.charged",
                        payload={}, signature_valid=True,
                        status=WebhookEventStatus.SKIPPED))
    order = Order(user_id=student_user.id, order_key="RZP_TEST1",
                  order_status=OrderStatus.COMPLETED, total_amount=500)
    db.add(order)
    db.flush()
    db.add(Payment(user_id=student_user.id, order_id=order.id,
                   payment_method="razorpay", gateway_payment_id="pay_refunded",
                   amount=500, payment_status=PaymentStatus.REFUNDED))
    db.add(Enrollment(user_id=student_user.id, course_id=course.id,
                      enrollment_status="enrolled", order_id=order.id))
    db.commit()


def test_payment_health_reports_pipeline_state(client, db, as_user, student_user, course):
    _seed(db, student_user, course)
    as_user(student_user)  # require_admin overridden by fixture
    r = client.get("/api/v1/admin/payment-health")
    assert r.status_code == 200
    data = r.json()
    assert data["failed_events"]["count"] == 1
    assert data["failed_events"]["items"][0]["event_id"] == "evt_bad1"
    assert data["skipped_events"]["count"] == 1
    assert data["refunded_with_active_enrollment"]["count"] == 1
    assert data["refunded_with_active_enrollment"]["items"][0]["gateway_payment_id"] == "pay_refunded"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_payment_health.py -v`
Expected: FAIL — 404 (route missing).

- [ ] **Step 3: Add the endpoint**

In `app/routers/admin.py` (imports: `WebhookEvent`, `WebhookEventStatus`, `Payment`, `PaymentStatus`, `Enrollment` — follow the file's import section):

```python
@router.get("/payment-health")
async def payment_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    """Payment pipeline observability: what needs a human."""
    def _event_row(ev):
        return {
            "event_id": ev.event_id,
            "event_type": ev.event_type,
            "attempts": ev.attempts,
            "last_error": ev.last_error,
            "received_at": ev.received_at.isoformat() if ev.received_at else None,
        }

    failed = (db.query(WebhookEvent)
              .filter(WebhookEvent.status == WebhookEventStatus.FAILED)
              .order_by(WebhookEvent.received_at.desc()).limit(50).all())
    skipped = (db.query(WebhookEvent)
               .filter(WebhookEvent.status == WebhookEventStatus.SKIPPED)
               .order_by(WebhookEvent.received_at.desc()).limit(50).all())

    refunded = (
        db.query(Payment)
        .join(Enrollment, Enrollment.order_id == Payment.order_id)
        .filter(
            Payment.payment_status == PaymentStatus.REFUNDED,
            Enrollment.enrollment_status == "enrolled",
        )
        .limit(50).all()
    )
    return {
        "failed_events": {"count": len(failed), "items": [_event_row(e) for e in failed]},
        "skipped_events": {"count": len(skipped), "items": [_event_row(e) for e in skipped]},
        "refunded_with_active_enrollment": {
            "count": len(refunded),
            "items": [
                {
                    "gateway_payment_id": p.gateway_payment_id,
                    "order_id": p.order_id,
                    "amount": float(p.amount or 0),
                    "user_id": p.user_id,
                }
                for p in refunded
            ],
        },
    }
```

- [ ] **Step 4: Soften the /verify failure message**

In `app/routers/payments.py`, the generic-exception 500 detail (currently "…contact support quoting payment ID … Do not pay again.") becomes:

```python
                detail=(
                    "Your payment was received. Enrollment will complete "
                    "automatically within a few minutes — do not pay again. "
                    f"If it does not appear, contact support quoting payment ID "
                    f"{razorpay_payment_id}."
                ),
```

- [ ] **Step 5: Env + docs**

1. In root `.env.example` and `backend/.env.example`, next to the existing RAZORPAY lines add:
   ```
   # HMAC secret for the Razorpay webhook (Dashboard → Webhooks → Secret).
   # Without it, POST /api/v1/payments/webhook returns 503 and only the
   # reconciliation sweeper's gateway diff provides the safety net.
   RAZORPAY_WEBHOOK_SECRET=<webhook_secret>
   ```
2. In `CLAUDE.md`, under "Notes for future work", add:
   ```
   - **Payment pipeline** (2026-09): fulfillment is triple-redundant — browser `/verify`,
     `POST /api/v1/payments/webhook` (signature-verified inbox in `webhook_events`, unique
     event_id = idempotency), and the reconciliation sweeper in
     `app/services/reconciliation.py` (5-min inbox retries, 30-min gateway diff, Postgres
     advisory-locked). All three converge on
     `app/services/fulfillment_service.fulfill_course_purchase()` keyed on
     `Payment.gateway_payment_id`. Pipeline state: `GET /api/v1/admin/payment-health`.
     Ops prerequisite: webhook + secret configured in the Razorpay dashboard
     (`RAZORPAY_WEBHOOK_SECRET`). Subscription events are captured as `skipped` until
     sub-project 2 adds handlers. Tests live in `backend/tests/`.
   ```

- [ ] **Step 6: Full suite**

Run: `python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/admin.py backend/app/routers/payments.py .env.example backend/.env.example CLAUDE.md backend/tests
git commit -m "feat: admin payment-health endpoint + webhook env/docs"
```

---

## Post-implementation (owner, manual — not a code task)

1. Razorpay Dashboard → Settings → Webhooks → Add: URL `https://<domain>/api/v1/payments/webhook`, events `payment.captured`, `payment.failed`, `refund.processed`; set a secret.
2. Put that secret in production `.env` as `RAZORPAY_WEBHOOK_SECRET`; restart backend.
3. Run `backend/migrations/add_webhook_events_table.sql` against production Postgres (fresh DBs get the table from `init_db()` automatically).
4. Confirm `GET /api/v1/admin/payment-health` returns zeros, then make a ₹1-level test purchase and watch a `payment.captured` row appear as `processed`.
