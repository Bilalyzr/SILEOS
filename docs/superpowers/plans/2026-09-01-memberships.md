# Memberships (Subscriptions) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tiered Razorpay-subscription memberships that grant course access via materialized Enrollment rows, driven entirely by the sub-project-1 webhook inbox and reconciliation sweeper.

**Architecture:** New `membership_plans` / `membership_plan_courses` / `memberships` tables plus two columns on `enrollments`. A `membership_access` service owns grant/suspend/reactivate of membership-sourced enrollments. Subscription lifecycle events flow through the existing `webhook_events` inbox into new handlers in `webhook_processor.py`; the existing reconciliation loop gains lapse-expiry and catalog-sync passes. Member/admin APIs in a new `memberships` router; minimal React UI (pricing page, dashboard card, admin CRUD).

**Tech Stack:** FastAPI 0.104 + SQLAlchemy 2.0 sync + Pydantic 2, razorpay SDK, pytest (backend/.venv), React 18 + TS + React Query + axios (`import { api } from './axios'`).

**Spec:** `docs/superpowers/specs/2026-09-01-memberships-design.md`

## Global Constraints

- Work happens in an isolated worktree on branch `memberships` forked from `payment-reliability-core`. Never touch `backend/app/routers/payments_proxy.py` or `backend/tests/test_proxy_webhook_migration.py` (concurrent session owns them; they may not exist in this worktree — fine).
- Backend paths relative to `backend/`; tests from `backend/`: `./.venv/Scripts/python -m pytest tests/<file> -v`. If the worktree lacks `.venv`, reuse the main checkout's venv via absolute path: `"C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe" -m pytest ...` run from the worktree's `backend/` (the venv has no project-path coupling).
- Full-suite baseline: ~45 pre-existing failures / 4 errors in old test files. Gate per task: new tests pass + zero NEW failures.
- No Alembic: SQLAlchemy models are init_db()'s source of truth AND each schema change gets a SQL file in `backend/migrations/`.
- Money/state rules: subscription state changes come ONLY from webhook handlers and sweeper passes — never from frontend callbacks. Razorpay amounts are paise (int); local rows store rupees. All Razorpay client construction goes through a factory that applies `functools.partial(client.session.request, timeout=30)`.
- Membership enrollment ownership: grant never overwrites an existing (user, course) row; suspend touches only rows with `enrollment_source == "membership"` AND `order_id IS NULL`.
- One membership per user in states pending/active/grace (409 otherwise).
- `total_count=100` on Razorpay subscriptions; cancel always `cancel_at_cycle_end=1`.
- Commit messages end with a blank line then `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Frontend gate: `npm run type-check` and `npm run lint` from `frontend/` must pass for files you touched (pre-existing lint state: run each before editing to record baseline; zero new errors).

---

### Task 1: Models + migration

**Files:**
- Create: `app/models/membership.py`
- Modify: `app/models/enrollment.py` (add 2 columns to Enrollment)
- Modify: `app/models/__init__.py` (register module, match existing style)
- Create: `backend/migrations/add_memberships_tables.sql`
- Test: `backend/tests/test_membership_models.py`

**Interfaces:**
- Produces: `MembershipPlan(id, name, description, all_access, period, interval, price, grace_days, razorpay_plan_id, is_active, created_at, updated_at)`, `MembershipPlanCourse(plan_id, course_id)`, `Membership(id, user_id, plan_id, razorpay_subscription_id UNIQUE, status: MembershipStatus, current_period_end, grace_until, cancel_at_period_end, created_at, updated_at)`, `MembershipStatus` enum `PENDING/ACTIVE/GRACE/SUSPENDED/CANCELLED/COMPLETED`, and `Enrollment.enrollment_source` (String(20) nullable) + `Enrollment.membership_id` (FK memberships.id nullable). All later tasks import from `app.models.membership`.

- [ ] **Step 1: Write the failing test**

```python
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.membership import (
    Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
)
from app.models.enrollment import Enrollment


def test_plan_membership_roundtrip(db, student_user):
    plan = MembershipPlan(
        name="Pro", all_access=True, period="monthly", interval=1,
        price=999.0, razorpay_plan_id="plan_X1",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    assert plan.grace_days == 7 and plan.is_active is True

    m = Membership(
        user_id=student_user.id, plan_id=plan.id,
        razorpay_subscription_id="sub_X1",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    assert m.status == MembershipStatus.PENDING


def test_subscription_id_unique(db, student_user):
    plan = MembershipPlan(name="P", all_access=True, period="monthly",
                          interval=1, price=1.0, razorpay_plan_id="plan_U")
    db.add(plan)
    db.commit()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_dup"))
    db.commit()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_dup"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_enrollment_source_columns(db, student_user, course):
    e = Enrollment(course_id=course.id, user_id=student_user.id,
                   enrollment_source="membership")
    db.add(e)
    db.commit()
    db.refresh(e)
    assert e.enrollment_source == "membership"
    assert e.membership_id is None
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_membership_models.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Write the models**

`app/models/membership.py`:

```python
"""Membership tiers and subscriptions (Razorpay Subscriptions).

State changes come exclusively from webhook handlers and the reconciliation
sweeper — see app/services/webhook_processor.py and reconciliation.py.
"""
import enum

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
)
from sqlalchemy.types import Enum, Numeric
from sqlalchemy.sql import func

from app.core.database import Base


class MembershipStatus(enum.Enum):
    PENDING = "pending"        # subscription created, first charge not confirmed
    ACTIVE = "active"
    GRACE = "grace"            # renewal failed; access kept until grace_until
    SUSPENDED = "suspended"    # grace expired; membership enrollments suspended
    CANCELLED = "cancelled"    # user cancelled; access until current_period_end
    COMPLETED = "completed"    # total_count exhausted at gateway


class MembershipPlan(Base):
    __tablename__ = "membership_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, default="")
    all_access = Column(Boolean, nullable=False, default=False)
    period = Column(String(20), nullable=False)   # daily/weekly/monthly/yearly
    interval = Column(Integer, nullable=False, default=1)
    price = Column(Numeric(10, 2), nullable=False)  # INR per cycle
    grace_days = Column(Integer, nullable=False, default=7)
    razorpay_plan_id = Column(String(64), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())

    def __repr__(self):
        return f"<MembershipPlan(id={self.id}, name={self.name})>"


class MembershipPlanCourse(Base):
    """Curated tier coverage. Empty for all_access plans."""
    __tablename__ = "membership_plan_courses"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)


class Membership(Base):
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("membership_plans.id"), nullable=False)
    razorpay_subscription_id = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(Enum(MembershipStatus), nullable=False,
                    default=MembershipStatus.PENDING)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    grace_until = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())

    def __repr__(self):
        return f"<Membership(id={self.id}, user={self.user_id}, status={self.status})>"
```

`app/models/enrollment.py` — add to the Enrollment class after `cohort_id`:

```python
    # Membership-materialized enrollment tracking (memberships sub-project).
    # "membership" marks rows the membership system owns; NULL = purchase/legacy.
    enrollment_source = Column(String(20), nullable=True)
    membership_id = Column(Integer, ForeignKey("memberships.id"), nullable=True)
```

Register `membership` in `app/models/__init__.py` following the file's existing import/`__all__` style.

- [ ] **Step 4: Run tests** — expect 3 passed.

- [ ] **Step 5: SQL migration** `backend/migrations/add_memberships_tables.sql`:

```sql
-- Memberships sub-project. Fresh DBs get these from init_db(); run manually
-- against existing Postgres:
--   docker-compose exec postgres psql -U tutor -d tutor_lms -f /path/to/this.sql

CREATE TABLE IF NOT EXISTS membership_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT DEFAULT '',
    all_access BOOLEAN NOT NULL DEFAULT FALSE,
    period VARCHAR(20) NOT NULL,
    interval INTEGER NOT NULL DEFAULT 1,
    price NUMERIC(10,2) NOT NULL,
    grace_days INTEGER NOT NULL DEFAULT 7,
    razorpay_plan_id VARCHAR(64) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS membership_plan_courses (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES membership_plans(id),
    course_id INTEGER NOT NULL REFERENCES courses(id)
);
CREATE INDEX IF NOT EXISTS ix_membership_plan_courses_plan_id
    ON membership_plan_courses (plan_id);

CREATE TABLE IF NOT EXISTS memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_id INTEGER NOT NULL REFERENCES membership_plans(id),
    razorpay_subscription_id VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    current_period_end TIMESTAMPTZ,
    grace_until TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_memberships_user_id ON memberships (user_id);
CREATE INDEX IF NOT EXISTS ix_memberships_subscription
    ON memberships (razorpay_subscription_id);

ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS enrollment_source VARCHAR(20);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS membership_id INTEGER REFERENCES memberships(id);
```

(Enum stored by NAME — 'PENDING' — matching the webhook_events precedent.)

- [ ] **Step 6: Commit** — `git add backend/app/models backend/migrations/add_memberships_tables.sql backend/tests/test_membership_models.py` → `feat: membership plan/subscription models + enrollment source columns`

---

### Task 2: Membership access service

**Files:**
- Create: `app/services/membership_access.py`
- Test: `backend/tests/test_membership_access.py`

**Interfaces:**
- Consumes: Task 1 models; `Enrollment`, `Course`.
- Produces (Tasks 3–4 call these exact signatures; none commit — caller commits):
```python
covered_course_ids(db, plan: MembershipPlan) -> set[int]
grant_membership_enrollments(db, membership: Membership) -> int   # rows created/reactivated
suspend_membership_enrollments(db, membership: Membership) -> int # rows suspended
```

- [ ] **Step 1: Write the failing tests**

```python
from app.models.enrollment import Enrollment
from app.models.membership import (
    Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
)
from app.services.membership_access import (
    covered_course_ids, grant_membership_enrollments,
    suspend_membership_enrollments,
)


def _plan(db, all_access=True, course_ids=()):
    plan = MembershipPlan(name="T", all_access=all_access, period="monthly",
                          interval=1, price=999.0,
                          razorpay_plan_id=f"plan_{all_access}_{len(course_ids)}")
    db.add(plan)
    db.flush()
    for cid in course_ids:
        db.add(MembershipPlanCourse(plan_id=plan.id, course_id=cid))
    db.commit()
    db.refresh(plan)
    return plan


def _membership(db, user, plan):
    m = Membership(user_id=user.id, plan_id=plan.id,
                   razorpay_subscription_id=f"sub_{plan.id}_{user.id}")
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_all_access_covers_paid_courses_only(db, course, free_course):
    plan = _plan(db, all_access=True)
    ids = covered_course_ids(db, plan)
    assert course.id in ids
    assert free_course.id not in ids


def test_curated_covers_exact_set(db, course):
    plan = _plan(db, all_access=False, course_ids=[course.id])
    assert covered_course_ids(db, plan) == {course.id}


def test_grant_creates_membership_rows(db, student_user, course):
    plan = _plan(db, all_access=False, course_ids=[course.id])
    m = _membership(db, student_user, plan)
    n = grant_membership_enrollments(db, m)
    db.commit()
    assert n == 1
    row = db.query(Enrollment).filter_by(user_id=student_user.id,
                                         course_id=course.id).one()
    assert row.enrollment_source == "membership"
    assert row.membership_id == m.id
    assert row.enrollment_status == "enrolled"
    # idempotent
    assert grant_membership_enrollments(db, m) == 0


def test_grant_never_touches_existing_purchase_row(db, student_user, course):
    db.add(Enrollment(course_id=course.id, user_id=student_user.id,
                      enrollment_status="enrolled"))
    db.commit()
    plan = _plan(db, all_access=False, course_ids=[course.id])
    m = _membership(db, student_user, plan)
    assert grant_membership_enrollments(db, m) == 0
    row = db.query(Enrollment).filter_by(user_id=student_user.id,
                                         course_id=course.id).one()
    assert row.enrollment_source is None


def test_suspend_only_membership_rows_without_order(db, student_user, course, order_row):
    plan = _plan(db, all_access=False, course_ids=[course.id])
    m = _membership(db, student_user, plan)
    grant_membership_enrollments(db, m)
    db.commit()
    # Simulate the member later BUYING the course: purchase flow stamps order_id.
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    row.order_id = order_row.id
    db.commit()
    assert suspend_membership_enrollments(db, m) == 0  # exempt: has order
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    assert row.enrollment_status == "enrolled"


def test_suspend_and_regrant_cycle(db, student_user, course):
    plan = _plan(db, all_access=False, course_ids=[course.id])
    m = _membership(db, student_user, plan)
    grant_membership_enrollments(db, m)
    db.commit()
    assert suspend_membership_enrollments(db, m) == 1
    db.commit()
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    assert row.enrollment_status == "suspended"
    # progress-preserving reactivation on re-grant
    assert grant_membership_enrollments(db, m) == 1
    db.commit()
    db.refresh(row)
    assert row.enrollment_status == "enrolled"
```

Add two fixtures to `backend/tests/conftest.py` (after the existing `course` fixture, same style):

```python
@pytest.fixture()
def free_course(db):
    author = _make_user(db, "instructor_free")
    c = Course(post_author=author.id, post_title="Free Course",
               course_price_type="free", course_price=0)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def order_row(db, student_user):
    from app.models.payment import Order, OrderStatus
    o = Order(user_id=student_user.id, order_key="RZP_FIXTURE",
              order_status=OrderStatus.COMPLETED, total_amount=500)
    db.add(o)
    db.commit()
    db.refresh(o)
    return o
```

- [ ] **Step 2: Run to verify failure** — ModuleNotFoundError.

- [ ] **Step 3: Implement**

```python
"""Grant / suspend the Enrollment rows a membership materializes.

Ownership rules (spec):
- grant never overwrites an existing (user, course) row of ANY source;
- suspend touches only rows with enrollment_source == "membership" AND
  order_id IS NULL (a later purchase stamps order_id and permanently
  exempts the row);
- suspension preserves all progress; re-grant flips status back to enrolled.
Callers own commit/rollback.
"""
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.membership import Membership, MembershipPlan, MembershipPlanCourse


def covered_course_ids(db: Session, plan: MembershipPlan) -> set[int]:
    if plan.all_access:
        rows = (db.query(Course.id)
                .filter(Course.course_price_type == "paid").all())
    else:
        rows = (db.query(MembershipPlanCourse.course_id)
                .filter(MembershipPlanCourse.plan_id == plan.id).all())
    return {r[0] for r in rows}


def grant_membership_enrollments(db: Session, membership: Membership) -> int:
    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == membership.plan_id).one()
    covered = covered_course_ids(db, plan)
    if not covered:
        return 0
    existing = {
        e.course_id: e
        for e in db.query(Enrollment).filter(
            Enrollment.user_id == membership.user_id,
            Enrollment.course_id.in_(covered),
        ).all()
    }
    changed = 0
    for course_id in covered:
        row = existing.get(course_id)
        if row is None:
            db.add(Enrollment(
                course_id=course_id,
                user_id=membership.user_id,
                enrollment_status="enrolled",
                enrollment_source="membership",
                membership_id=membership.id,
            ))
            changed += 1
        elif (row.enrollment_source == "membership"
              and row.enrollment_status == "suspended"):
            row.enrollment_status = "enrolled"
            row.membership_id = membership.id
            changed += 1
        # any other existing row (purchase, cohort, completed...) is not ours
    return changed


def suspend_membership_enrollments(db: Session, membership: Membership) -> int:
    rows = db.query(Enrollment).filter(
        Enrollment.membership_id == membership.id,
        Enrollment.enrollment_source == "membership",
        Enrollment.order_id.is_(None),
        Enrollment.enrollment_status == "enrolled",
    ).all()
    for row in rows:
        row.enrollment_status = "suspended"
    return len(rows)
```

- [ ] **Step 4: Run tests** — 7 passed.

- [ ] **Step 5: Commit** — `feat: membership access service (grant/suspend materialized enrollments)`

---

### Task 3: Subscription webhook handlers

**Files:**
- Modify: `app/services/webhook_processor.py`
- Test: `backend/tests/test_subscription_webhooks.py`

**Interfaces:**
- Consumes: Task 1 models, Task 2 service, existing `process_webhook_event` / `HANDLED_EVENTS` / `UnrecoverableEvent`, `fulfill`-style Order/Payment models.
- Produces: `HANDLED_EVENTS` additionally contains `subscription.activated`, `subscription.charged`, `subscription.halted`, `subscription.cancelled`, `subscription.completed`, `subscription.pending`; internal `_handle_subscription_event(db, event)`; `payment.captured` entities carrying a non-empty `subscription_id` are routed to `_handle_subscription_charge_payment(db, entity)` (records Order+Payment rows, `payment_method="razorpay_subscription"`) instead of the course-notes path. Task 4's sweeper relies only on model state, not these functions.

- [ ] **Step 1: Write the failing tests** (uses the Task 2 test helpers — import `_plan`, `_membership` equivalents locally; write them fresh here, tests must be self-contained):

```python
from datetime import datetime, timedelta, timezone

from app.models.enrollment import Enrollment
from app.models.membership import (
    Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
)
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.services.webhook_processor import process_webhook_event


def _plan(db, course_ids):
    plan = MembershipPlan(name="T", all_access=False, period="monthly",
                          interval=1, price=999.0, razorpay_plan_id="plan_W")
    db.add(plan)
    db.flush()
    for cid in course_ids:
        db.add(MembershipPlanCourse(plan_id=plan.id, course_id=cid))
    db.commit()
    return plan


def _membership(db, user, plan, **kw):
    m = Membership(user_id=user.id, plan_id=plan.id,
                   razorpay_subscription_id="sub_W1", **kw)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _sub_event(db, event_type, sub_id="sub_W1", event_id=None, current_end=None,
               payment=None):
    entity = {"id": sub_id, "status": event_type.split(".")[1]}
    if current_end is not None:
        entity["current_end"] = current_end
    payload = {"entity": "event", "event": event_type,
               "payload": {"subscription": {"entity": entity}}}
    if payment:
        payload["payload"]["payment"] = {"entity": payment}
    ev = WebhookEvent(event_id=event_id or f"evt_{event_type}_{sub_id}",
                      event_type=event_type, payload=payload,
                      signature_valid=True)
    db.add(ev)
    db.commit()
    return ev


def test_activated_grants_and_sets_period(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan)
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    ev = _sub_event(db, "subscription.activated", current_end=end)
    process_webhook_event(db, ev)
    db.refresh(m)
    assert ev.status == WebhookEventStatus.PROCESSED
    assert m.status == MembershipStatus.ACTIVE
    assert m.current_period_end is not None
    assert db.query(Enrollment).filter_by(user_id=student_user.id,
                                          course_id=course.id).count() == 1


def test_charged_recovers_from_grace(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan, status=MembershipStatus.GRACE,
                    grace_until=datetime.now(timezone.utc))
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    ev = _sub_event(db, "subscription.charged", current_end=end,
                    payment={"id": "pay_SUB1", "amount": 99900,
                             "currency": "INR", "subscription_id": "sub_W1"})
    process_webhook_event(db, ev)
    db.refresh(m)
    assert m.status == MembershipStatus.ACTIVE
    assert m.grace_until is None


def test_charged_records_payment_row_idempotently(db, student_user, course):
    plan = _plan(db, [course.id])
    _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    pay = {"id": "pay_SUB2", "amount": 99900, "currency": "INR",
           "subscription_id": "sub_W1"}
    process_webhook_event(db, _sub_event(db, "subscription.charged",
                                         event_id="evt_c1", current_end=end,
                                         payment=pay))
    process_webhook_event(db, _sub_event(db, "subscription.charged",
                                         event_id="evt_c2", current_end=end,
                                         payment=pay))
    assert db.query(Payment).filter_by(gateway_payment_id="pay_SUB2").count() == 1


def test_halted_starts_grace_keeps_access(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    from app.services.membership_access import grant_membership_enrollments
    grant_membership_enrollments(db, m)
    db.commit()
    process_webhook_event(db, _sub_event(db, "subscription.halted"))
    db.refresh(m)
    assert m.status == MembershipStatus.GRACE
    assert m.grace_until is not None
    row = db.query(Enrollment).filter_by(user_id=student_user.id).one()
    assert row.enrollment_status == "enrolled"  # access kept during grace


def test_cancelled_marks_cancelled_keeps_access(db, student_user, course):
    plan = _plan(db, [course.id])
    m = _membership(db, student_user, plan, status=MembershipStatus.ACTIVE,
                    current_period_end=datetime.now(timezone.utc) + timedelta(days=10))
    process_webhook_event(db, _sub_event(db, "subscription.cancelled"))
    db.refresh(m)
    assert m.status == MembershipStatus.CANCELLED


def test_unknown_subscription_id_is_unrecoverable(db):
    ev = _sub_event(db, "subscription.activated", sub_id="sub_GHOST",
                    event_id="evt_ghost")
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.FAILED
    assert ev.attempts == 5  # unrecoverable exhausts retries


def test_captured_with_subscription_id_not_unrecoverable(db, student_user, course):
    plan = _plan(db, [course.id])
    _membership(db, student_user, plan, status=MembershipStatus.ACTIVE)
    ev = WebhookEvent(
        event_id="evt_subcap", event_type="payment.captured",
        payload={"payload": {"payment": {"entity": {
            "id": "pay_SUB3", "amount": 99900, "currency": "INR",
            "subscription_id": "sub_W1", "notes": {},
        }}}},
        signature_valid=True)
    db.add(ev)
    db.commit()
    process_webhook_event(db, ev)
    assert ev.status == WebhookEventStatus.PROCESSED
    assert db.query(Payment).filter_by(gateway_payment_id="pay_SUB3").count() == 1
```

- [ ] **Step 2: Run to verify failure** — subscription events currently SKIPPED; assertions fail.

- [ ] **Step 3: Implement in `webhook_processor.py`**

Read the file first; integrate without disturbing existing handlers or the Edgyy dispatch. Additions:

```python
SUBSCRIPTION_EVENTS = {
    "subscription.activated", "subscription.charged", "subscription.halted",
    "subscription.cancelled", "subscription.completed", "subscription.pending",
}
HANDLED_EVENTS = HANDLED_EVENTS | SUBSCRIPTION_EVENTS  # adapt to file's literal set
```

Dispatch inside `process_webhook_event`: `elif event.event_type in SUBSCRIPTION_EVENTS: _handle_subscription_event(db, event); event.status = PROCESSED` (same shape as existing branches).

```python
def _subscription_entity(event):
    return ((event.payload or {}).get("payload", {})
            .get("subscription", {}).get("entity", {}))


def _handle_subscription_event(db: Session, event: WebhookEvent) -> None:
    from datetime import datetime, timedelta, timezone
    from app.models.membership import Membership, MembershipPlan, MembershipStatus
    from app.services.membership_access import grant_membership_enrollments

    entity = _subscription_entity(event)
    sub_id = entity.get("id")
    if not sub_id:
        raise UnrecoverableEvent("subscription event without subscription id")
    membership = db.query(Membership).filter(
        Membership.razorpay_subscription_id == str(sub_id)).first()
    if membership is None:
        raise UnrecoverableEvent(f"no membership for subscription {sub_id}")

    etype = event.event_type
    current_end = entity.get("current_end")
    if current_end:
        membership.current_period_end = datetime.fromtimestamp(
            int(current_end), tz=timezone.utc)

    if etype == "subscription.activated":
        membership.status = MembershipStatus.ACTIVE
        membership.grace_until = None
        grant_membership_enrollments(db, membership)
    elif etype == "subscription.charged":
        membership.status = MembershipStatus.ACTIVE
        membership.grace_until = None
        grant_membership_enrollments(db, membership)
        pay_entity = ((event.payload or {}).get("payload", {})
                      .get("payment", {}).get("entity", {}))
        if pay_entity.get("id"):
            _record_subscription_charge(db, membership, pay_entity)
    elif etype == "subscription.halted":
        plan = db.query(MembershipPlan).filter(
            MembershipPlan.id == membership.plan_id).one()
        membership.status = MembershipStatus.GRACE
        membership.grace_until = (datetime.now(timezone.utc)
                                  + timedelta(days=plan.grace_days or 7))
    elif etype == "subscription.cancelled":
        membership.status = MembershipStatus.CANCELLED
    elif etype == "subscription.completed":
        membership.status = MembershipStatus.COMPLETED
    # subscription.pending: recorded only — Razorpay is still retrying.


def _record_subscription_charge(db, membership, pay_entity) -> None:
    """Order+Payment rows for a renewal charge — same idempotency key as
    course purchases (gateway_payment_id)."""
    import uuid
    from datetime import datetime, timezone
    from app.models.payment import (Order, OrderItem, OrderStatus, Payment,
                                    PaymentStatus)
    from app.models.membership import MembershipPlan

    pay_id = str(pay_entity.get("id"))
    if db.query(Payment).filter(Payment.gateway_payment_id == pay_id).first():
        return
    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == membership.plan_id).one()
    amount = int(pay_entity.get("amount") or 0) / 100.0
    currency = str(pay_entity.get("currency") or "INR")
    order = Order(
        user_id=membership.user_id,
        order_key=f"SUB_{uuid.uuid4().hex[:12].upper()}",
        order_status=OrderStatus.COMPLETED,
        currency=currency,
        subtotal_amount=amount, total_amount=amount,
        payment_method="razorpay_subscription",
        payment_method_title=f"Membership: {plan.name}",
        transaction_id=pay_id,
        date_paid=datetime.now(timezone.utc),
        date_completed=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    db.add(OrderItem(order_id=order.id, course_id=None,
                     order_item_name=f"Membership renewal — {plan.name}",
                     order_item_type="membership", quantity=1,
                     subtotal=amount, total=amount))
    db.add(Payment(user_id=membership.user_id, order_id=order.id,
                   payment_method="razorpay_subscription",
                   gateway_transaction_id=pay_id, gateway_payment_id=pay_id,
                   gateway_order_id=str(pay_entity.get("order_id") or ""),
                   amount=amount, currency=currency,
                   payment_status=PaymentStatus.COMPLETED,
                   processed_date=datetime.now(timezone.utc)))
```

NOTE: check `OrderItem.course_id` nullability in `app/models/payment.py` first — if it is `nullable=False`, omit the OrderItem row entirely (Order+Payment suffice for revenue) and note that in your report.

In `_handle_payment_captured`, BEFORE the notes extraction (and after the Edgyy dispatch), add:

```python
    if entity.get("subscription_id"):
        from app.models.membership import Membership
        membership = db.query(Membership).filter(
            Membership.razorpay_subscription_id == str(entity["subscription_id"])
        ).first()
        if membership is not None:
            _record_subscription_charge(db, membership, entity)
            return
        raise UnrecoverableEvent(
            f"captured payment for unknown subscription {entity['subscription_id']}")
```

- [ ] **Step 4: Run tests** — 7 passed; also run `tests/test_webhook_endpoint.py tests/test_reconciliation.py` to confirm no regression.

- [ ] **Step 5: Commit** — `feat: subscription lifecycle webhook handlers`

---

### Task 4: Sweeper passes — lapse expiry + catalog sync

**Files:**
- Modify: `app/services/reconciliation.py`
- Test: `backend/tests/test_membership_sweeper.py`

**Interfaces:**
- Consumes: Task 1 models, Task 2 service.
- Produces: `expire_lapsed_memberships(db) -> int` and `sync_membership_catalog(db) -> int`, both called from `_run_cycle` — expiry every cycle, catalog sync on the same cadence as the gateway diff (`cycle_index % GATEWAY_DIFF_EVERY == 0`). Neither raises; both commit their own work (mirroring `retry_failed_events`' pattern of committing via `process_webhook_event` — here call `db.commit()` after each membership's changes).

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime, timedelta, timezone

from app.models.enrollment import Enrollment
from app.models.membership import (
    Membership, MembershipPlan, MembershipPlanCourse, MembershipStatus,
)
from app.services.membership_access import grant_membership_enrollments
from app.services.reconciliation import (
    expire_lapsed_memberships, sync_membership_catalog,
)


def _setup(db, user, course, status, **kw):
    plan = MembershipPlan(name="T", all_access=False, period="monthly",
                          interval=1, price=9.0, razorpay_plan_id="plan_S")
    db.add(plan)
    db.flush()
    db.add(MembershipPlanCourse(plan_id=plan.id, course_id=course.id))
    m = Membership(user_id=user.id, plan_id=plan.id,
                   razorpay_subscription_id="sub_S1", status=status, **kw)
    db.add(m)
    db.commit()
    db.refresh(m)
    grant_membership_enrollments(db, m)
    db.commit()
    return plan, m


def test_grace_expiry_suspends(db, student_user, course):
    _, m = _setup(db, student_user, course, MembershipStatus.GRACE,
                  grace_until=datetime.now(timezone.utc) - timedelta(days=1))
    assert expire_lapsed_memberships(db) == 1
    db.refresh(m)
    assert m.status == MembershipStatus.SUSPENDED
    assert db.query(Enrollment).filter_by(
        user_id=student_user.id).one().enrollment_status == "suspended"
    assert expire_lapsed_memberships(db) == 0  # idempotent


def test_grace_not_yet_expired_untouched(db, student_user, course):
    _, m = _setup(db, student_user, course, MembershipStatus.GRACE,
                  grace_until=datetime.now(timezone.utc) + timedelta(days=3))
    assert expire_lapsed_memberships(db) == 0
    db.refresh(m)
    assert m.status == MembershipStatus.GRACE


def test_cancelled_past_period_end_suspends_access(db, student_user, course):
    _, m = _setup(db, student_user, course, MembershipStatus.CANCELLED,
                  current_period_end=datetime.now(timezone.utc) - timedelta(days=1))
    assert expire_lapsed_memberships(db) == 1
    assert db.query(Enrollment).filter_by(
        user_id=student_user.id).one().enrollment_status == "suspended"


def test_catalog_sync_grants_new_course(db, student_user, course):
    plan = MembershipPlan(name="All", all_access=True, period="monthly",
                          interval=1, price=9.0, razorpay_plan_id="plan_AA")
    db.add(plan)
    db.flush()
    m = Membership(user_id=student_user.id, plan_id=plan.id,
                   razorpay_subscription_id="sub_AA",
                   status=MembershipStatus.ACTIVE)
    db.add(m)
    db.commit()
    assert sync_membership_catalog(db) >= 1  # grants the existing paid course
    assert db.query(Enrollment).filter_by(user_id=student_user.id,
                                          course_id=course.id).count() == 1
    assert sync_membership_catalog(db) == 0  # then converges
```

- [ ] **Step 2: Run to verify failure** — ImportError.

- [ ] **Step 3: Implement in `reconciliation.py`**

```python
def expire_lapsed_memberships(db: Session) -> int:
    """Suspend memberships whose grace or paid period has run out."""
    from app.models.membership import Membership, MembershipStatus
    from app.services.membership_access import suspend_membership_enrollments

    now = datetime.now(timezone.utc)
    count = 0
    graced = db.query(Membership).filter(
        Membership.status == MembershipStatus.GRACE,
        Membership.grace_until.isnot(None),
    ).all()
    ended = db.query(Membership).filter(
        Membership.status.in_([MembershipStatus.CANCELLED,
                               MembershipStatus.COMPLETED]),
        Membership.current_period_end.isnot(None),
    ).all()
    for m in graced + ended:
        deadline = m.grace_until if m.status == MembershipStatus.GRACE else m.current_period_end
        if deadline is not None and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline is None or deadline > now:
            continue
        suspended = suspend_membership_enrollments(db, m)
        if m.status == MembershipStatus.GRACE:
            m.status = MembershipStatus.SUSPENDED
        elif suspended == 0:
            continue  # cancelled/completed with nothing left to suspend
        db.commit()
        count += 1
        logger.info("membership %s lapsed; %s enrollments suspended", m.id, suspended)
    return count


def sync_membership_catalog(db: Session) -> int:
    """Grant enrollments for courses added since a membership activated."""
    from app.models.membership import Membership, MembershipStatus
    from app.services.membership_access import grant_membership_enrollments

    granted = 0
    active = db.query(Membership).filter(
        Membership.status == MembershipStatus.ACTIVE).all()
    for m in active:
        n = grant_membership_enrollments(db, m)
        if n:
            db.commit()
            granted += n
    return granted
```

Wire into `_run_cycle` after `retry_failed_events(db)`:

```python
        expire_lapsed_memberships(db)
        if cycle_index % GATEWAY_DIFF_EVERY == 0:
            sync_membership_catalog(db)
```

CAREFUL: `test_cancelled_past_period_end_suspends_access` relies on the cancelled branch counting only when suspensions happened; re-running yields 0 because rows are already suspended — matches the idempotency assertions.

- [ ] **Step 4: Run tests** — 4 passed + rerun `tests/test_reconciliation.py` (5 passed, no regression).

- [ ] **Step 5: Commit** — `feat: membership lapse-expiry and catalog-sync sweeper passes`

---

### Task 5: Member API + schemas

**Files:**
- Create: `app/routers/memberships.py`
- Create: `app/schemas/membership.py`
- Modify: `app/main.py` (import + `app.include_router(memberships.router, prefix="/api/v1/memberships", tags=["Memberships"])` next to the payments router)
- Test: `backend/tests/test_membership_api.py`

**Interfaces:**
- Consumes: Tasks 1–2; `AuthService.get_current_active_user`; `_razorpay_creds` pattern.
- Produces: routes `GET /api/v1/memberships/plans`, `POST /api/v1/memberships/subscribe`, `GET /api/v1/memberships/me`, `POST /api/v1/memberships/cancel`; schemas `PlanOut`, `SubscribeRequest {plan_id: int}`, `SubscribeResponse {subscription_id, razorpay_key}`, `MembershipOut`. Frontend (Task 7) consumes these exact JSON shapes. Module-level `_rzp_client()` factory (monkeypatchable in tests).

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime, timedelta, timezone

from app.models.membership import (
    Membership, MembershipPlan, MembershipStatus,
)


def _plan(db, active=True):
    p = MembershipPlan(name="Pro", all_access=True, period="monthly",
                       interval=1, price=999.0, razorpay_plan_id="plan_API",
                       is_active=active)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


class FakeRzp:
    class subscription:
        @staticmethod
        def create(payload):
            assert payload["plan_id"] == "plan_API"
            assert payload["total_count"] == 100
            return {"id": "sub_API1", "status": "created"}

        @staticmethod
        def cancel(sub_id, payload=None):
            FakeRzp.cancelled = (sub_id, payload)
            return {"id": sub_id, "status": "cancelled"}


def _patch_client(monkeypatch):
    import app.routers.memberships as mod
    monkeypatch.setattr(mod, "_rzp_client", lambda: FakeRzp)
    monkeypatch.setattr(mod, "_rzp_key_id", lambda: "rzp_test_key")


def test_plans_lists_only_active(client, db):
    _plan(db)
    _plan_inactive = MembershipPlan(name="Old", all_access=True,
                                    period="monthly", interval=1, price=1.0,
                                    razorpay_plan_id="plan_OLD", is_active=False)
    db.add(_plan_inactive)
    db.commit()
    r = client.get("/api/v1/memberships/plans")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Pro" in names and "Old" not in names


def test_subscribe_creates_pending_membership(client, db, as_user, student_user, monkeypatch):
    plan = _plan(db)
    _patch_client(monkeypatch)
    as_user(student_user)
    r = client.post("/api/v1/memberships/subscribe", json={"plan_id": plan.id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["subscription_id"] == "sub_API1"
    m = db.query(Membership).filter_by(user_id=student_user.id).one()
    assert m.status == MembershipStatus.PENDING


def test_subscribe_conflict_when_already_member(client, db, as_user, student_user, monkeypatch):
    plan = _plan(db)
    _patch_client(monkeypatch)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_EXIST",
                      status=MembershipStatus.ACTIVE))
    db.commit()
    as_user(student_user)
    r = client.post("/api/v1/memberships/subscribe", json={"plan_id": plan.id})
    assert r.status_code == 409


def test_me_and_cancel(client, db, as_user, student_user, monkeypatch):
    plan = _plan(db)
    _patch_client(monkeypatch)
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_ME",
                      status=MembershipStatus.ACTIVE,
                      current_period_end=datetime.now(timezone.utc) + timedelta(days=9)))
    db.commit()
    as_user(student_user)
    r = client.get("/api/v1/memberships/me")
    assert r.status_code == 200 and r.json()["status"] == "active"
    r = client.post("/api/v1/memberships/cancel")
    assert r.status_code == 200
    assert FakeRzp.cancelled[0] == "sub_ME"
    assert FakeRzp.cancelled[1] == {"cancel_at_cycle_end": 1}
    m = db.query(Membership).filter_by(razorpay_subscription_id="sub_ME").one()
    assert m.cancel_at_period_end is True


def test_me_without_membership_404(client, as_user, student_user):
    as_user(student_user)
    assert client.get("/api/v1/memberships/me").status_code == 404
```

- [ ] **Step 2: Run to verify failure** — 404s (router not mounted).

- [ ] **Step 3: Implement**

`app/schemas/membership.py`:

```python
from datetime import datetime

from pydantic import BaseModel


class PlanOut(BaseModel):
    id: int
    name: str
    description: str
    all_access: bool
    period: str
    interval: int
    price: float
    covered_courses: int


class SubscribeRequest(BaseModel):
    plan_id: int


class SubscribeResponse(BaseModel):
    subscription_id: str
    razorpay_key: str


class MembershipOut(BaseModel):
    plan_id: int
    plan_name: str
    status: str
    current_period_end: datetime | None
    grace_until: datetime | None
    cancel_at_period_end: bool
```

`app/routers/memberships.py`:

```python
"""Member-facing membership endpoints. State transitions are webhook/sweeper
owned — these endpoints only create/cancel gateway subscriptions and read."""
import functools
import logging

import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.membership import Membership, MembershipPlan, MembershipStatus
from app.models.user import User
from app.routers.payments import _razorpay_creds
from app.schemas.membership import (
    MembershipOut, PlanOut, SubscribeRequest, SubscribeResponse,
)
from app.services.auth_service import AuthService
from app.services.membership_access import covered_course_ids

logger = logging.getLogger(__name__)
router = APIRouter()

BLOCKING_STATUSES = [MembershipStatus.PENDING, MembershipStatus.ACTIVE,
                     MembershipStatus.GRACE]


def _rzp_key_id() -> str:
    key_id, _ = _razorpay_creds()
    return key_id


def _rzp_client():
    key_id, key_secret = _razorpay_creds()
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")
    client = razorpay.Client(auth=(key_id, key_secret))
    client.session.request = functools.partial(client.session.request, timeout=30)
    return client


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(db: Session = Depends(get_db)):
    plans = (db.query(MembershipPlan)
             .filter(MembershipPlan.is_active.is_(True))
             .order_by(MembershipPlan.price).all())
    return [PlanOut(
        id=p.id, name=p.name, description=p.description or "",
        all_access=p.all_access, period=p.period, interval=p.interval,
        price=float(p.price), covered_courses=len(covered_course_ids(db, p)),
    ) for p in plans]


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    request: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    plan = db.query(MembershipPlan).filter(
        MembershipPlan.id == request.plan_id,
        MembershipPlan.is_active.is_(True)).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    existing = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.status.in_(BLOCKING_STATUSES)).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already have a membership")

    client = _rzp_client()
    try:
        sub = client.subscription.create({
            "plan_id": plan.razorpay_plan_id,
            "total_count": 100,
            "customer_notify": 1,
            "notes": {"user_id": str(current_user.id), "plan_id": str(plan.id)},
        })
    except HTTPException:
        raise
    except Exception:
        logger.exception("subscription create failed (user=%s plan=%s)",
                         current_user.id, plan.id)
        raise HTTPException(status_code=502, detail="Could not start subscription")

    db.add(Membership(user_id=current_user.id, plan_id=plan.id,
                      razorpay_subscription_id=str(sub["id"])))
    db.commit()
    return SubscribeResponse(subscription_id=str(sub["id"]),
                             razorpay_key=_rzp_key_id())


@router.get("/me", response_model=MembershipOut)
async def my_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    m = (db.query(Membership)
         .filter(Membership.user_id == current_user.id)
         .order_by(Membership.created_at.desc()).first())
    if not m:
        raise HTTPException(status_code=404, detail="No membership")
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == m.plan_id).one()
    return MembershipOut(
        plan_id=plan.id, plan_name=plan.name, status=m.status.value,
        current_period_end=m.current_period_end, grace_until=m.grace_until,
        cancel_at_period_end=m.cancel_at_period_end)


@router.post("/cancel")
async def cancel_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    m = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.status.in_(BLOCKING_STATUSES)).first()
    if not m:
        raise HTTPException(status_code=404, detail="No active membership")
    client = _rzp_client()
    try:
        client.subscription.cancel(m.razorpay_subscription_id,
                                   {"cancel_at_cycle_end": 1})
    except Exception:
        logger.exception("subscription cancel failed (membership=%s)", m.id)
        raise HTTPException(status_code=502, detail="Could not cancel; try again")
    m.cancel_at_period_end = True
    db.commit()
    return {"success": True,
            "message": "Membership will end at the current period's close"}
```

Verify the razorpay SDK exposes `client.subscription.cancel(sub_id, data)` in the venv (`python -c "import razorpay, inspect; print(inspect.signature(razorpay.Client(auth=('x','y')).subscription.cancel))"`); adapt the call shape if it differs, keeping `cancel_at_cycle_end: 1` semantics, and note it in the report.

- [ ] **Step 4: Run tests** — 5 passed; app imports (`python -c "from app.main import app"` with the six env vars).

- [ ] **Step 5: Commit** — `feat: member-facing membership API (plans/subscribe/me/cancel)`

---

### Task 6: Admin API — plan CRUD, member list, health section

**Files:**
- Modify: `app/routers/admin.py`
- Modify: `app/schemas/membership.py` (admin schemas)
- Test: `backend/tests/test_membership_admin_api.py`

**Interfaces:**
- Consumes: Tasks 1–2, 5. IMPORTANT: admin.py must access the client factory as a module attribute — `from app.routers import memberships` then `memberships._rzp_client()` — NOT `from app.routers.memberships import _rzp_client`. A by-name import binds at import time and the tests' monkeypatch of `app.routers.memberships._rzp_client` would never reach it.
- Produces: `POST/GET/PATCH /api/v1/admin/memberships/plans[...]`, `GET /api/v1/admin/memberships`, and a `memberships` section in the existing `/api/v1/admin/payment-health` response: `{"memberships": {"by_status": {...}, "in_grace": N}}`. Frontend Task 8 consumes these shapes. Admin schemas: `PlanCreate {name, description="", all_access=False, course_ids=[], period, interval=1, price, grace_days=7}`, `PlanUpdate {description?, is_active?, course_ids?}`, `AdminPlanOut = PlanOut + {grace_days, razorpay_plan_id, is_active}`, `AdminMembershipOut {id, user_id, user_email, plan_name, status, current_period_end}`.

- [ ] **Step 1: Write the failing tests**

```python
from app.models.membership import Membership, MembershipPlan, MembershipStatus


class FakeRzpAdmin:
    class plan:
        @staticmethod
        def create(payload):
            assert payload["period"] == "monthly"
            assert payload["item"]["amount"] == 99900  # paise
            return {"id": "plan_NEW1"}


def _patch(monkeypatch):
    import app.routers.memberships as mod
    monkeypatch.setattr(mod, "_rzp_client", lambda: FakeRzpAdmin)


def test_admin_creates_plan_with_razorpay(client, db, as_user, student_user, monkeypatch, course):
    _patch(monkeypatch)
    as_user(student_user)  # require_admin overridden by fixture
    r = client.post("/api/v1/admin/memberships/plans", json={
        "name": "Pro", "period": "monthly", "price": 999.0,
        "all_access": False, "course_ids": [course.id],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["razorpay_plan_id"] == "plan_NEW1"
    assert body["covered_courses"] == 1


def test_admin_plan_validation(client, as_user, student_user):
    as_user(student_user)
    r = client.post("/api/v1/admin/memberships/plans", json={
        "name": "Bad", "period": "hourly", "price": 10.0})
    assert r.status_code == 422


def test_admin_lists_members_and_health(client, db, as_user, student_user):
    plan = MembershipPlan(name="P", all_access=True, period="monthly",
                          interval=1, price=1.0, razorpay_plan_id="plan_H")
    db.add(plan)
    db.flush()
    db.add(Membership(user_id=student_user.id, plan_id=plan.id,
                      razorpay_subscription_id="sub_H",
                      status=MembershipStatus.GRACE))
    db.commit()
    as_user(student_user)
    r = client.get("/api/v1/admin/memberships")
    assert r.status_code == 200 and r.json()[0]["status"] == "grace"
    r = client.get("/api/v1/admin/payment-health")
    assert r.status_code == 200
    assert r.json()["memberships"]["in_grace"] == 1
```

- [ ] **Step 2: Run to verify failure** — 404 / KeyError.

- [ ] **Step 3: Implement**

Schemas appended to `app/schemas/membership.py`:

```python
from pydantic import Field


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    all_access: bool = False
    course_ids: list[int] = []
    period: str = Field(pattern=r"^(daily|weekly|monthly|yearly)$")
    interval: int = Field(default=1, ge=1, le=12)
    price: float = Field(gt=0)
    grace_days: int = Field(default=7, ge=0, le=90)


class PlanUpdate(BaseModel):
    description: str | None = None
    is_active: bool | None = None
    course_ids: list[int] | None = None


class AdminPlanOut(PlanOut):
    grace_days: int
    razorpay_plan_id: str
    is_active: bool


class AdminMembershipOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    plan_name: str
    status: str
    current_period_end: datetime | None
```

In `app/routers/admin.py` (imports per the file's conventions; `from app.routers import memberships` and call `memberships._rzp_client()` — see Interfaces note):

```python
@router.post("/memberships/plans", response_model=AdminPlanOut)
async def create_membership_plan(
    request: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    client = memberships._rzp_client()
    rzp_plan = client.plan.create({
        "period": request.period,
        "interval": request.interval,
        "item": {
            "name": request.name,
            "amount": int(round(request.price * 100)),
            "currency": "INR",
        },
    })
    plan = MembershipPlan(
        name=request.name, description=request.description,
        all_access=request.all_access, period=request.period,
        interval=request.interval, price=request.price,
        grace_days=request.grace_days,
        razorpay_plan_id=str(rzp_plan["id"]),
    )
    db.add(plan)
    db.flush()
    if not request.all_access:
        for cid in request.course_ids:
            db.add(MembershipPlanCourse(plan_id=plan.id, course_id=cid))
    db.commit()
    db.refresh(plan)
    return _admin_plan_out(db, plan)


@router.get("/memberships/plans", response_model=list[AdminPlanOut])
async def list_membership_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    return [_admin_plan_out(db, p) for p in db.query(MembershipPlan)
            .order_by(MembershipPlan.created_at.desc()).all()]


@router.patch("/memberships/plans/{plan_id}", response_model=AdminPlanOut)
async def update_membership_plan(
    plan_id: int,
    request: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if request.description is not None:
        plan.description = request.description
    if request.is_active is not None:
        plan.is_active = request.is_active
    if request.course_ids is not None and not plan.all_access:
        db.query(MembershipPlanCourse).filter(
            MembershipPlanCourse.plan_id == plan.id).delete()
        for cid in request.course_ids:
            db.add(MembershipPlanCourse(plan_id=plan.id, course_id=cid))
    db.commit()
    db.refresh(plan)
    return _admin_plan_out(db, plan)


@router.get("/memberships", response_model=list[AdminMembershipOut])
async def list_memberships(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_admin),
):
    rows = (db.query(Membership, MembershipPlan, User)
            .join(MembershipPlan, MembershipPlan.id == Membership.plan_id)
            .join(User, User.id == Membership.user_id)
            .order_by(Membership.created_at.desc()).limit(200).all())
    return [AdminMembershipOut(
        id=m.id, user_id=u.id, user_email=u.user_email or "",
        plan_name=p.name, status=m.status.value,
        current_period_end=m.current_period_end,
    ) for m, p, u in rows]


def _admin_plan_out(db, plan) -> AdminPlanOut:
    from app.services.membership_access import covered_course_ids
    return AdminPlanOut(
        id=plan.id, name=plan.name, description=plan.description or "",
        all_access=plan.all_access, period=plan.period, interval=plan.interval,
        price=float(plan.price), covered_courses=len(covered_course_ids(db, plan)),
        grace_days=plan.grace_days, razorpay_plan_id=plan.razorpay_plan_id,
        is_active=plan.is_active)
```

Note on price/period changes: plan price and period are intentionally NOT in
`PlanUpdate` — Razorpay plans are immutable, so pricing changes mean creating
a NEW tier (POST) and deactivating the old one (PATCH `is_active=false`).
Put that sentence in a comment above `PlanUpdate`.

Payment-health addition inside the existing `payment_health` endpoint:

```python
    from app.models.membership import Membership, MembershipStatus
    by_status = {}
    for st in MembershipStatus:
        by_status[st.value] = db.query(Membership).filter(
            Membership.status == st).count()
    memberships_section = {
        "by_status": by_status,
        "in_grace": by_status.get("grace", 0),
    }
```
and add `"memberships": memberships_section` to the returned dict.

- [ ] **Step 4: Run tests** — 3 passed + rerun `tests/test_payment_health.py`.

- [ ] **Step 5: Commit** — `feat: admin membership plan CRUD, member list, health section`

---

### Task 7: Frontend — pricing page + my-membership card

**Files:**
- Create: `frontend/src/api/membership.ts`
- Create: `frontend/src/pages/membership.tsx`
- Modify: `frontend/src/App.tsx` (add `/membership` route beside `/checkout`; public route)
- Modify: the student dashboard page (locate via `frontend/src/pages/dashboard.tsx` / `pages/dashboard/` — put the card where other summary cards render)
- Gate: `npm run type-check` and `npm run lint`

**Interfaces:**
- Consumes: Task 5 endpoints/shapes verbatim.
- Produces: nothing downstream.

- [ ] **Step 1: API wrapper** `frontend/src/api/membership.ts` (mirror `api/certificates.ts` style):

```typescript
import { api } from './axios'

export interface MembershipPlan {
  id: number
  name: string
  description: string
  all_access: boolean
  period: string
  interval: number
  price: number
  covered_courses: number
}

export interface MyMembership {
  plan_id: number
  plan_name: string
  status: string
  current_period_end: string | null
  grace_until: string | null
  cancel_at_period_end: boolean
}

export const fetchMembershipPlans = async (): Promise<MembershipPlan[]> => {
  const { data } = await api.get('/memberships/plans')
  return data
}

export const subscribeToPlan = async (planId: number): Promise<{ subscription_id: string; razorpay_key: string }> => {
  const { data } = await api.post('/memberships/subscribe', { plan_id: planId })
  return data
}

export const fetchMyMembership = async (): Promise<MyMembership | null> => {
  try {
    const { data } = await api.get('/memberships/me')
    return data
  } catch {
    return null
  }
}

export const cancelMembership = async (): Promise<void> => {
  await api.post('/memberships/cancel')
}
```

(Confirm the axios instance's baseURL already includes `/api/v1` — checkout code calls e.g. `/payments/create-order`; mirror whatever prefix convention the existing api modules use and note it.)

- [ ] **Step 2: Pricing page** `frontend/src/pages/membership.tsx` — before writing, read `frontend/src/pages/checkout.tsx` for: `ensureRazorpayLoaded` (extract-or-copy its script-loader), the Razorpay open-checkout options shape, auth-store usage, and toast/error patterns; read one existing public page for layout wrappers. Structure (adapt classes/components to the codebase's Tailwind/ui conventions — this is a skeleton whose LOGIC is binding, whose styling should match the site):

```tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchMembershipPlans, fetchMyMembership, subscribeToPlan, MembershipPlan } from '@/api/membership'
import { useAuthStore } from '@/store/auth'   // verify actual store path/name in codebase

export default function MembershipPage() {
  const [plans, setPlans] = useState<MembershipPlan[]>([])
  const [hasMembership, setHasMembership] = useState(false)
  const [busyPlan, setBusyPlan] = useState<number | null>(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  useEffect(() => {
    fetchMembershipPlans().then(setPlans).catch(() => setError('Could not load plans'))
    if (isAuthenticated) fetchMyMembership().then(m => setHasMembership(!!m && ['pending', 'active', 'grace'].includes(m.status)))
  }, [isAuthenticated])

  const handleSubscribe = async (plan: MembershipPlan) => {
    if (!isAuthenticated) { navigate('/login?redirect=/membership'); return }
    setBusyPlan(plan.id); setError('')
    try {
      const { subscription_id, razorpay_key } = await subscribeToPlan(plan.id)
      await ensureRazorpayLoaded()               // same loader as checkout.tsx
      const rzp = new (window as any).Razorpay({
        key: razorpay_key,
        subscription_id,
        name: 'SashaInfinity',
        description: `${plan.name} membership`,
        handler: () => navigate('/dashboard?membership=activating'),
        modal: { ondismiss: () => setBusyPlan(null) },
      })
      rzp.open()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Could not start subscription')
      setBusyPlan(null)
    }
  }
  // render: plan cards (name, price/period, covered_courses or "All courses",
  // Subscribe button disabled when hasMembership || busyPlan) + error line.
}
```

The rendered copy: price as `₹{price} / {interval > 1 ? interval + ' ' : ''}{period}`; all_access plans say "Every paid course"; curated say `${covered_courses} courses included`. If the user already has a membership, the button reads "You're a member" and is disabled. IMPORTANT: after checkout success we navigate to the dashboard with a note that activation is confirmed by the server — copy: "Payment received — your membership activates within a minute." Never grant anything client-side.

- [ ] **Step 3: Route** in `App.tsx`, following the existing public-route pattern: `<Route path="/membership" element={<MembershipPage />} />` (match however `/courses` is declared — public, inside the shared layout).

- [ ] **Step 4: Dashboard card** — in the student dashboard component, add a "My membership" card using `fetchMyMembership`: plan name, status chip (active = normal, grace = warning copy "Payment issue — access ends {grace_until date} unless payment succeeds", cancelled = "Ends {current_period_end}"), renewal date, and a Cancel button (confirm dialog, calls `cancelMembership`, then refetch). No membership → a small "Explore memberships" link to `/membership`. Match the dashboard's existing card components.

- [ ] **Step 5: Gate** — from `frontend/`: `npm run type-check` and `npm run lint` → zero NEW errors (record baseline first).

- [ ] **Step 6: Commit** — `feat: membership pricing page + dashboard membership card`

---

### Task 8: Frontend admin — plan management + docs

**Files:**
- Create: `frontend/src/pages/admin/memberships.tsx`
- Modify: `frontend/src/App.tsx` (admin route beside `/admin/coupons`-style routes)
- Modify: admin navigation (locate the admin sidebar/menu component by grepping for an existing entry like "Coupons" and add "Memberships" beside it)
- Modify: `CLAUDE.md`
- Gate: type-check + lint

**Interfaces:**
- Consumes: Task 6 admin endpoints/shapes.

- [ ] **Step 1: Admin page** `frontend/src/pages/admin/memberships.tsx` — read `frontend/src/pages/admin/coupons.tsx` first and mirror its table/form/dialog patterns exactly. Functional requirements (binding): table of plans (name, price+period, coverage, active toggle via PATCH, razorpay_plan_id shown truncated); "New tier" form (name, description, period select daily/weekly/monthly/yearly, interval number, price, grace days, all-access checkbox, and when unchecked a course multi-select fed from the existing admin courses API used elsewhere in `pages/admin/`); a members table below (email, plan, status chip, period end) from `GET /api/v1/admin/memberships`. A visible note near the price field: "Pricing is fixed once created — to change price, create a new tier and deactivate this one."

- [ ] **Step 2: Route + nav** — add the admin route following the existing `/admin/*` pattern and a "Memberships" nav item beside the existing commerce entries.

- [ ] **Step 3: CLAUDE.md** — under the payment-pipeline note from sub-project 1, append:

```
- **Memberships** (2026-09): tiered Razorpay Subscriptions. Access = materialized
  Enrollment rows (`enrollment_source="membership"`, suspend on lapse, never touch
  rows with order_id). Models `app/models/membership.py`; grant/suspend logic
  `app/services/membership_access.py`; lifecycle handlers in webhook_processor
  (subscription.* events); lapse-expiry + catalog-sync passes in reconciliation.py;
  member API `/api/v1/memberships/*`; admin CRUD under `/api/v1/admin/memberships`.
  Razorpay plans are immutable — price changes = new tier. Migration:
  backend/migrations/add_memberships_tables.sql.
```

- [ ] **Step 4: Gate** — type-check + lint, zero new errors.

- [ ] **Step 5: Commit** — `feat: admin membership management UI + docs`

---

## Post-implementation (owner, manual)

1. Add subscription events to the Razorpay webhook: `subscription.activated`, `subscription.charged`, `subscription.halted`, `subscription.cancelled`, `subscription.completed`, `subscription.pending`.
2. Run `backend/migrations/add_memberships_tables.sql` on production Postgres.
3. Create the first tiers in Admin → Memberships.
