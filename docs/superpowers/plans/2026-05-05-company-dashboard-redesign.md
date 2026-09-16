# Company Dashboard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing 3-tab (Browse / Pipeline / Profile) company dashboard with a 4-tab operational dashboard (Overview · Student management · Internship management · Attendance management), backed by reporting-manager sub-users, daily work-done logs, performance reviews, announcements, hours-worked tracking, and PDF/CSV attendance reports for both company and admin users.

**Architecture:** Backend additions are concentrated in one new router (`backend/app/routers/company_dashboard.py`) plus four new SQLAlchemy models and one SQL migration; existing `companies.py` keeps the auth/manager-invite primitives. Frontend re-uses the existing axios + React-Query layer; old browse/pipeline files are deleted and replaced by a `CompanyDashboardLayout` shell with one page per tab. Reports are server-side-rendered (CSV via stdlib `csv`, PDF via `reportlab`) and exposed both as JSON for the in-app preview and as `Content-Disposition: attachment` for download.

**Tech Stack:** FastAPI · SQLAlchemy · Pydantic · pytest + httpx (test client) · `reportlab` (new dependency) · React 18 + TypeScript · React Query · Tailwind · Vitest + React Testing Library (frontend tests; vitest is currently declared but missing — Phase 0 installs it).

**Companion spec:** `docs/superpowers/specs/2026-05-05-company-dashboard-redesign-design.md`

---

## File map

### New files

**Backend**
- `backend/migrations/company_dashboard_v2_2026_05_05.sql` — schema migration
- `backend/app/models/company_dashboard.py` — new SQLAlchemy models: `CompanyManager`, `DailyWorkLog`, `InternshipAnnouncement`, `InternshipPerformanceReview`
- `backend/app/schemas/company_dashboard.py` — Pydantic request/response schemas
- `backend/app/routers/company_dashboard.py` — new router for `/api/v1/companies/me/*` and `/api/v1/admin/reports/*`
- `backend/app/services/company_scope.py` — pure helpers: `assigned_voucher_ids_for(company_id)`, `is_manager_of(user, student_id)`, `require_company_user(user)`, `require_company_owner(user)`
- `backend/app/services/attendance_report.py` — pure data builder + CSV + PDF renderers
- `backend/tests/conftest.py` — pytest fixtures: in-memory SQLite engine, `client`, `db`, `make_user`, `make_company`, `make_internship`, `make_voucher`, `make_attendance`
- `backend/tests/test_*.py` — one file per task

**Frontend**
- `frontend/vitest.config.ts` — vitest config (currently missing)
- `frontend/src/test-setup.ts` — RTL + jsdom setup
- `frontend/src/api/company-dashboard.ts` — typed React Query hooks for the new endpoints
- `frontend/src/pages/company/Layout.tsx` — sidebar shell + role-aware nav
- `frontend/src/pages/company/Overview.tsx`
- `frontend/src/pages/company/Students.tsx`
- `frontend/src/pages/company/StudentDrawer.tsx`
- `frontend/src/pages/company/Internships.tsx`
- `frontend/src/pages/company/Attendance.tsx` — owns both grid & timeline modes
- `frontend/src/pages/company/Announcements.tsx`
- `frontend/src/pages/company/Managers.tsx`
- `frontend/src/pages/company/Reports.tsx`
- `frontend/src/pages/admin/AttendanceReport.tsx`
- `frontend/src/components/reports/ReportFilters.tsx`
- `frontend/src/components/reports/AttendanceCsvPreview.tsx`
- `frontend/src/components/reports/AttendancePdfPreview.tsx`

### Modified files

- `backend/app/models/__init__.py` — add new models to `__all__`
- `backend/app/models/internship.py` — add `hours_worked` to `InternshipAttendance`; add `reporting_manager_user_id` to `InternshipVoucher`
- `backend/app/main.py` — register `company_dashboard` router
- `backend/app/services/auth_service.py` — add `require_company_or_manager`, `require_company_owner` dependencies
- `backend/requirements.txt` — add `reportlab`
- `frontend/src/App.tsx` — replace single `/company/dashboard` route with nested routes
- `frontend/package.json` — add `vitest`, `@vitest/ui`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` to devDependencies

### Deleted files

- `frontend/src/pages/company/dashboard.tsx` (replaced)
- `frontend/src/components/company/InterestModal.tsx` (no longer used)
- `frontend/src/api/company.ts` (browse / pipeline / interest API — replaced by new module)

---

## Phase 0 — Test infrastructure

### Task 0.1: Add pytest infrastructure to backend

**Files:**
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Create empty `backend/tests/__init__.py`**

```python
```

- [ ] **Step 2: Create `backend/pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

- [ ] **Step 3: Create `backend/tests/conftest.py`**

```python
"""
Pytest fixtures for the LMS backend.

Uses an in-memory SQLite engine per test session so tests are deterministic
and never touch Postgres. The whole `Base.metadata` is created fresh for
each test, then dropped at teardown.
"""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Make `app.*` importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import database as core_db  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402


@pytest.fixture(scope="function")
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Importing models registers them on Base.metadata.
    from app import models  # noqa: F401
    core_db.Base.metadata.create_all(bind=eng)
    yield eng
    core_db.Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def TestingSessionLocal(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db(TestingSessionLocal):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(TestingSessionLocal):
    """FastAPI TestClient with the DB dependency overridden."""
    from app.main import app

    def _get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[core_db.get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ----- factory fixtures -----

@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def _mk(role="student", email=None, password="Test@123", verified=True):
        counter["n"] += 1
        n = counter["n"]
        from app.models.user import User
        u = User(
            user_login=f"user{n}",
            user_pass=get_password_hash(password),
            user_nicename=f"user{n}",
            user_email=email or f"user{n}@example.com",
            display_name=f"User {n}",
            role=role,
            is_active=True,
            is_verified=verified,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    return _mk


@pytest.fixture
def make_company(db, make_user):
    counter = {"n": 0}

    def _mk(name=None, owner=None, approved=True):
        counter["n"] += 1
        n = counter["n"]
        owner = owner or make_user(role="company")
        from app.models.company import Company
        c = Company(
            owner_user_id=owner.id,
            name=name or f"Company {n}",
            slug=f"company-{n}",
            contact_email=owner.user_email,
            is_approved=approved,
            approval_source="admin_invite",
            approved_at=datetime.utcnow() if approved else None,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    return _mk


@pytest.fixture
def auth_headers(client):
    """Login and return Authorization header dict."""

    def _login(email, password="Test@123"):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login
```

- [ ] **Step 4: Smoke-run pytest to verify infra works**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 bash -lc "cd /app && pytest tests/ -q"`
Expected: `0 tests passed` (no test files yet) — exits cleanly.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/__init__.py backend/tests/conftest.py backend/pytest.ini
git commit -m "test(backend): add pytest infrastructure with sqlite test client"
```

---

### Task 0.2: Add vitest to frontend

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test-setup.ts`

- [ ] **Step 1: Add vitest deps to `frontend/package.json` `devDependencies`**

```json
"vitest": "^1.6.0",
"@vitest/ui": "^1.6.0",
"@testing-library/react": "^16.0.0",
"@testing-library/jest-dom": "^6.4.0",
"@testing-library/user-event": "^14.5.0",
"jsdom": "^24.0.0"
```

- [ ] **Step 2: Create `frontend/vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
    css: false,
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
```

- [ ] **Step 3: Create `frontend/src/test-setup.ts`**

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 4: Install and smoke-test**

Run: `docker exec magical-visvesvaraya-2204b2-frontend-1 npm install`
Then: `docker exec magical-visvesvaraya-2204b2-frontend-1 npx vitest run`
Expected: `No test files found` exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/src/test-setup.ts
git commit -m "test(frontend): add vitest + RTL + jsdom"
```

---

## Phase 1 — Backend foundation

### Task 1.1: SQL migration

**Files:**
- Create: `backend/migrations/company_dashboard_v2_2026_05_05.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Company Dashboard v2 — 2026-05-05
-- Adds: company_managers, daily_work_logs, internship_announcements,
--       internship_performance_reviews
-- Modifies: internship_attendance (+hours_worked),
--           internship_vouchers (+reporting_manager_user_id)

BEGIN;

ALTER TABLE internship_attendance
    ADD COLUMN IF NOT EXISTS hours_worked NUMERIC(4,2) NOT NULL DEFAULT 0;

ALTER TABLE internship_vouchers
    ADD COLUMN IF NOT EXISTS reporting_manager_user_id INTEGER
        REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_vouchers_reporting_manager
    ON internship_vouchers (reporting_manager_user_id);

CREATE TABLE IF NOT EXISTS company_managers (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    invited_by INTEGER REFERENCES users(id),
    invited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_company_managers_company
    ON company_managers (company_id);

CREATE TABLE IF NOT EXISTS daily_work_logs (
    id SERIAL PRIMARY KEY,
    student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    internship_id INTEGER NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    attachment_url VARCHAR(500) NOT NULL DEFAULT '',
    review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    reviewed_by INTEGER REFERENCES users(id),
    reviewer_comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_work_log_student_date UNIQUE (student_user_id, log_date)
);
CREATE INDEX IF NOT EXISTS ix_work_logs_internship_date
    ON daily_work_logs (internship_id, log_date);

CREATE TABLE IF NOT EXISTS internship_announcements (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    internship_id INTEGER REFERENCES internships(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_announcements_company
    ON internship_announcements (company_id);

CREATE TABLE IF NOT EXISTS internship_performance_reviews (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    student_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    internship_id INTEGER NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT NOT NULL DEFAULT '',
    hire_recommendation VARCHAR(10) NOT NULL DEFAULT 'maybe',
    submitted_by INTEGER REFERENCES users(id),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_review_company_student_internship
        UNIQUE (company_id, student_user_id, internship_id)
);

COMMIT;
```

- [ ] **Step 2: Apply migration to running Postgres**

Run: `docker exec -i magical-visvesvaraya-2204b2-postgres-1 psql -U tutor -d tutor_lms < backend/migrations/company_dashboard_v2_2026_05_05.sql`
Expected: lines ending in `BEGIN`, `ALTER TABLE`, `CREATE TABLE`, `COMMIT`. No `ERROR`.

- [ ] **Step 3: Verify schema**

Run: `docker exec magical-visvesvaraya-2204b2-postgres-1 psql -U tutor -d tutor_lms -c "\d company_managers"`
Expected: shows the 9 columns of `company_managers`.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/company_dashboard_v2_2026_05_05.sql
git commit -m "feat(db): add company dashboard v2 schema migration"
```

---

### Task 1.2: Update existing models — `hours_worked`, `reporting_manager_user_id`

**Files:**
- Modify: `backend/app/models/internship.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_models_existing_extensions.py`**

```python
from datetime import date

def test_attendance_has_hours_worked_default_zero(db, make_user, make_company):
    from app.models.internship import Internship, InternshipAttendance
    from app.models.cohort import Cohort

    student = make_user(role="student")
    spoc = make_user(role="instructor")
    cohort = Cohort(name="C1", college_id=None, slug="c1")
    db.add(cohort); db.commit(); db.refresh(cohort)
    intern = Internship(
        title="X", slug="x", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id
    )
    db.add(intern); db.commit(); db.refresh(intern)

    att = InternshipAttendance(
        internship_id=intern.id, user_id=student.id,
        attended_at=date(2026, 5, 5), status="present",
    )
    db.add(att); db.commit(); db.refresh(att)
    assert float(att.hours_worked) == 0.0


def test_voucher_has_reporting_manager(db, make_user):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort

    student = make_user(role="student")
    spoc = make_user(role="instructor")
    mgr = make_user(role="company_manager")
    cohort = Cohort(name="C2", slug="c2")
    db.add(cohort); db.commit(); db.refresh(cohort)
    intern = Internship(
        title="Y", slug="y", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id
    )
    db.add(intern); db.commit(); db.refresh(intern)
    v = InternshipVoucher(
        code="VC1", internship_id=intern.id, buyer_user_id=student.id,
        amount_paid=0, reporting_manager_user_id=mgr.id,
    )
    db.add(v); db.commit(); db.refresh(v)
    assert v.reporting_manager_user_id == mgr.id
```

- [ ] **Step 2: Run — expect failure**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 pytest tests/test_models_existing_extensions.py -v`
Expected: AttributeError or "no such column" failures on `hours_worked` and `reporting_manager_user_id`.

- [ ] **Step 3: Add the columns to the models**

In `backend/app/models/internship.py`, inside `class InternshipVoucher` (alongside `hired_by_company_id`), add:

```python
    # Reporting manager assigned by the company. Optional. Set to a user
    # whose role is 'company' or 'company_manager' linked to the same
    # company that hired this voucher's owner.
    reporting_manager_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
```

In `class InternshipAttendance`, add:

```python
    hours_worked = Column(Decimal(4, 2), nullable=False, default=0)
```

- [ ] **Step 4: Run again — expect pass**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 pytest tests/test_models_existing_extensions.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/internship.py backend/tests/test_models_existing_extensions.py
git commit -m "feat(models): add hours_worked + reporting_manager_user_id"
```

---

### Task 1.3: New SQLAlchemy models

**Files:**
- Create: `backend/app/models/company_dashboard.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_models_company_dashboard.py`**

```python
from datetime import date


def test_company_manager_unique_user(db, make_user, make_company):
    from app.models.company_dashboard import CompanyManager
    co = make_company()
    mgr = make_user(role="company_manager")
    db.add(CompanyManager(company_id=co.id, user_id=mgr.id, invited_by=co.owner_user_id))
    db.commit()
    # Same user cannot be linked twice
    db.add(CompanyManager(company_id=co.id, user_id=mgr.id))
    import pytest, sqlalchemy
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.commit()


def test_daily_work_log_unique_per_day(db, make_user):
    from app.models.company_dashboard import DailyWorkLog
    from app.models.internship import Internship
    from app.models.cohort import Cohort
    s = make_user(role="student"); spoc = make_user(role="instructor")
    cohort = Cohort(name="C", slug="cwl"); db.add(cohort); db.commit(); db.refresh(cohort)
    i = Internship(title="i", slug="ix", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id)
    db.add(i); db.commit(); db.refresh(i)
    db.add(DailyWorkLog(student_user_id=s.id, internship_id=i.id, log_date=date(2026,5,5), content="x"))
    db.commit()
    db.add(DailyWorkLog(student_user_id=s.id, internship_id=i.id, log_date=date(2026,5,5), content="y"))
    import pytest, sqlalchemy
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.commit()


def test_review_unique_per_company_student_internship(db, make_user, make_company):
    from app.models.company_dashboard import InternshipPerformanceReview
    from app.models.internship import Internship
    from app.models.cohort import Cohort
    co = make_company(); s = make_user(role="student"); spoc = make_user(role="instructor")
    cohort = Cohort(name="C", slug="cprev"); db.add(cohort); db.commit(); db.refresh(cohort)
    i = Internship(title="i", slug="iprev", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id)
    db.add(i); db.commit(); db.refresh(i)
    db.add(InternshipPerformanceReview(
        company_id=co.id, student_user_id=s.id, internship_id=i.id,
        rating=4, feedback="ok", hire_recommendation="yes",
    ))
    db.commit()
    db.add(InternshipPerformanceReview(
        company_id=co.id, student_user_id=s.id, internship_id=i.id,
        rating=5, feedback="dup", hire_recommendation="yes",
    ))
    import pytest, sqlalchemy
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.commit()


def test_announcement_can_be_internship_scoped_or_global(db, make_company):
    from app.models.company_dashboard import InternshipAnnouncement
    co = make_company()
    db.add(InternshipAnnouncement(company_id=co.id, internship_id=None, title="A", body="b"))
    db.commit()
    rows = db.query(InternshipAnnouncement).filter_by(company_id=co.id).all()
    assert len(rows) == 1 and rows[0].internship_id is None
```

- [ ] **Step 2: Run — expect failure**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 pytest tests/test_models_company_dashboard.py -v`
Expected: ImportError on `app.models.company_dashboard`.

- [ ] **Step 3: Write `backend/app/models/company_dashboard.py`**

```python
"""
Company-dashboard v2 models.

Owns:
  - CompanyManager — sub-users belonging to a Company. role on User is
    'company_manager'. Owner of the Company is the User row referenced by
    Company.owner_user_id (role='company') and is NOT inserted here.
  - DailyWorkLog — student's daily work-done entry for an internship.
  - InternshipAnnouncement — company-posted announcement, optionally
    internship-scoped.
  - InternshipPerformanceReview — end-of-internship review submitted by a
    company about a student.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    UniqueConstraint, Index, Date, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CompanyManager(Base):
    __tablename__ = "company_managers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     unique=True, nullable=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    invited_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", foreign_keys=[company_id])
    user = relationship("User", foreign_keys=[user_id])


class DailyWorkLog(Base):
    __tablename__ = "daily_work_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    internship_id = Column(Integer, ForeignKey("internships.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    log_date = Column(Date, nullable=False)
    content = Column(Text, nullable=False, default="")
    attachment_url = Column(String(500), nullable=False, default="")
    review_status = Column(String(20), nullable=False, default="pending")  # pending|approved|flagged
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_comment = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("student_user_id", "log_date", name="uq_work_log_student_date"),
        Index("ix_work_logs_internship_date", "internship_id", "log_date"),
    )

    student = relationship("User", foreign_keys=[student_user_id])
    internship = relationship("Internship", foreign_keys=[internship_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class InternshipAnnouncement(Base):
    __tablename__ = "internship_announcements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    internship_id = Column(Integer, ForeignKey("internships.id", ondelete="SET NULL"),
                           nullable=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", foreign_keys=[company_id])
    internship = relationship("Internship", foreign_keys=[internship_id])


class InternshipPerformanceReview(Base):
    __tablename__ = "internship_performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    internship_id = Column(Integer, ForeignKey("internships.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=False, default="")
    hire_recommendation = Column(String(10), nullable=False, default="maybe")  # yes|maybe|no
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "student_user_id", "internship_id",
                         name="uq_review_company_student_internship"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
    )

    company = relationship("Company", foreign_keys=[company_id])
    student = relationship("User", foreign_keys=[student_user_id])
    internship = relationship("Internship", foreign_keys=[internship_id])
```

- [ ] **Step 4: Update `backend/app/models/__init__.py`**

Add the import:
```python
from app.models.company_dashboard import (
    CompanyManager, DailyWorkLog, InternshipAnnouncement,
    InternshipPerformanceReview,
)
```
Add to `__all__`:
```python
"CompanyManager",
"DailyWorkLog",
"InternshipAnnouncement",
"InternshipPerformanceReview",
```

- [ ] **Step 5: Run tests — expect pass**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 pytest tests/test_models_company_dashboard.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/company_dashboard.py backend/app/models/__init__.py backend/tests/test_models_company_dashboard.py
git commit -m "feat(models): company managers, work logs, announcements, perf reviews"
```

---

### Task 1.4: Auth dependencies for company / company_manager

**Files:**
- Modify: `backend/app/services/auth_service.py`

- [ ] **Step 1: Failing test `backend/tests/test_auth_company_deps.py`**

```python
def test_require_company_or_manager_accepts_both(client, make_user, make_company, auth_headers):
    owner = make_user(role="company", email="owner@example.com")
    make_company(owner=owner)
    mgr = make_user(role="company_manager", email="mgr@example.com")
    student = make_user(role="student", email="s@example.com")

    # Probe a route we know already requires company auth: /api/v1/companies/me
    h_owner = auth_headers("owner@example.com")
    r = client.get("/api/v1/companies/me", headers=h_owner)
    assert r.status_code == 200

    # Manager — currently fails (only role='company' is accepted). After
    # this task, it must succeed.
    h_mgr = auth_headers("mgr@example.com")
    r = client.get("/api/v1/companies/me", headers=h_mgr)
    # We expect 404 (no company linked yet via CompanyManager) — NOT 403.
    assert r.status_code in (200, 404), r.text

    # Plain student must always be denied.
    h_student = auth_headers("s@example.com")
    r = client.get("/api/v1/companies/me", headers=h_student)
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: Run — expect failure (manager hits 403)**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 pytest tests/test_auth_company_deps.py -v`
Expected: failure on the manager case.

- [ ] **Step 3: Add helpers to `backend/app/services/auth_service.py`**

Append these to the `AuthService` class:

```python
    @staticmethod
    def require_company_or_manager(user: "User" = Depends(get_current_user.__func__)) -> "User":
        """Allow company owners and their managers."""
        if user.role not in ("company", "company_manager"):
            raise HTTPException(status_code=403, detail="Company access required")
        return user

    @staticmethod
    def require_company_owner(user: "User" = Depends(get_current_user.__func__)) -> "User":
        if user.role != "company":
            raise HTTPException(status_code=403, detail="Company owner access required")
        return user
```

(Note: the existing `companies.py` `/me` endpoint reads `User` directly. Update it to call `require_company_or_manager` and to resolve the company via either `Company.owner_user_id == user.id` OR via a `CompanyManager` row.)

In `backend/app/routers/companies.py`, locate `_get_my_company(db, user)` and replace with:

```python
def _get_my_company(db: Session, user: User) -> Company:
    # Owner path
    company = db.query(Company).filter(Company.owner_user_id == user.id).first()
    if company:
        return company
    # Manager path
    from app.models.company_dashboard import CompanyManager
    link = db.query(CompanyManager).filter(CompanyManager.user_id == user.id).first()
    if link:
        company = db.query(Company).filter(Company.id == link.company_id).first()
        if company:
            return company
    raise HTTPException(status_code=404, detail="No company profile for this user")
```

- [ ] **Step 4: Run — expect pass**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 pytest tests/test_auth_company_deps.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/auth_service.py backend/app/routers/companies.py backend/tests/test_auth_company_deps.py
git commit -m "feat(auth): allow company_manager role through company-scoped endpoints"
```

---

### Task 1.5: Manager invite / list / revoke / setup endpoints

**Files:**
- Create: `backend/app/services/company_scope.py`
- Modify: `backend/app/routers/companies.py` (or create `company_dashboard.py` and put manager routes there — we choose `company_dashboard.py` since this is the main file going forward)
- Modify: `backend/app/main.py`
- Create: `backend/app/schemas/company_dashboard.py` (initial — schemas grow as we add endpoints)

- [ ] **Step 1: Failing test `backend/tests/test_managers.py`**

```python
def test_owner_invites_manager(client, db, make_user, make_company, auth_headers):
    owner = make_user(role="company", email="owner@example.com")
    make_company(owner=owner)

    h = auth_headers("owner@example.com")
    r = client.post(
        "/api/v1/companies/me/managers",
        headers=h,
        json={"email": "newmgr@example.com", "name": "New Manager"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "newmgr@example.com"
    assert body["accepted_at"] is None
    assert body["user_id"] > 0


def test_owner_lists_managers(client, make_user, make_company, auth_headers):
    owner = make_user(role="company", email="o@example.com")
    make_company(owner=owner)
    h = auth_headers("o@example.com")
    client.post("/api/v1/companies/me/managers", headers=h,
                json={"email": "a@example.com", "name": "A"})
    client.post("/api/v1/companies/me/managers", headers=h,
                json={"email": "b@example.com", "name": "B"})
    r = client.get("/api/v1/companies/me/managers", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert {m["email"] for m in rows} == {"a@example.com", "b@example.com"}


def test_manager_cannot_invite_other_managers(client, make_user, make_company, auth_headers):
    owner = make_user(role="company", email="o2@example.com")
    co = make_company(owner=owner)
    mgr = make_user(role="company_manager", email="m2@example.com")
    from app.models.company_dashboard import CompanyManager
    # Direct DB link — simulates accepted invite
    from sqlalchemy.orm import sessionmaker
    # We use the same engine via the auth session by piggybacking on /me round-trip
    # Simpler: insert via API-test fixture below using raw SQL.

    # Use the test client-bound session via the running app:
    # (alternative: expose a fixture; we keep it inline for clarity.)
    h = auth_headers("o2@example.com")
    r = client.post("/api/v1/companies/me/managers", headers=h,
                    json={"email": "m2@example.com", "name": "Existing"})
    assert r.status_code in (201, 400)  # may already exist as user; both fine

    h_mgr = auth_headers("m2@example.com")
    r = client.post("/api/v1/companies/me/managers", headers=h_mgr,
                    json={"email": "x@example.com", "name": "X"})
    assert r.status_code == 403


def test_revoke_manager(client, db, make_user, make_company, auth_headers):
    owner = make_user(role="company", email="o3@example.com")
    make_company(owner=owner)
    h = auth_headers("o3@example.com")
    r = client.post("/api/v1/companies/me/managers", headers=h,
                    json={"email": "rm@example.com", "name": "RM"})
    mid = r.json()["id"]
    r = client.delete(f"/api/v1/companies/me/managers/{mid}", headers=h)
    assert r.status_code == 204
    r = client.get("/api/v1/companies/me/managers", headers=h)
    assert all(m["id"] != mid for m in r.json())


def test_complete_manager_setup(client, db, make_user, make_company, auth_headers):
    """Invite returns a setup_token that the manager exchanges for password + login."""
    owner = make_user(role="company", email="o4@example.com")
    make_company(owner=owner)
    h = auth_headers("o4@example.com")
    r = client.post("/api/v1/companies/me/managers", headers=h,
                    json={"email": "newm@example.com", "name": "NM"})
    token = r.json()["setup_token"]

    r = client.post("/api/v1/companies/managers/complete-setup",
                    json={"token": token, "password": "Mgr@1234"})
    assert r.status_code == 200

    # New manager can now log in
    r = client.post("/api/v1/auth/login",
                    json={"email": "newm@example.com", "password": "Mgr@1234"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "company_manager"
```

- [ ] **Step 2: Run — expect failure**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 pytest tests/test_managers.py -v`
Expected: 404 on all routes (router doesn't exist yet).

- [ ] **Step 3: Write `backend/app/schemas/company_dashboard.py`**

```python
"""Pydantic schemas for company dashboard v2."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ---------- Managers ----------

class ManagerInviteRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)


class ManagerResponse(BaseModel):
    id: int
    user_id: int
    email: EmailStr
    name: str
    accepted_at: Optional[datetime] = None
    invited_at: datetime
    setup_token: Optional[str] = None  # only returned on the invite call

    class Config:
        from_attributes = True


class ManagerCompleteSetupRequest(BaseModel):
    token: str
    password: str = Field(min_length=6, max_length=200)
```

- [ ] **Step 4: Write `backend/app/services/company_scope.py`**

```python
"""
Pure helpers shared across the company dashboard router. Stateless — they
take a Session and an authenticated User and return DB rows or raise.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.company import Company
from app.models.company_dashboard import CompanyManager


def get_my_company(db: Session, user: User) -> Company:
    """Return the company the authenticated user belongs to."""
    if user.role == "company":
        c = db.query(Company).filter(Company.owner_user_id == user.id).first()
        if not c:
            raise HTTPException(status_code=404, detail="No company profile")
        return c
    if user.role == "company_manager":
        link = db.query(CompanyManager).filter(CompanyManager.user_id == user.id).first()
        if not link:
            raise HTTPException(status_code=404, detail="Manager not linked to a company")
        c = db.query(Company).filter(Company.id == link.company_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Company not found")
        return c
    raise HTTPException(status_code=403, detail="Company role required")


def is_owner(user: User) -> bool:
    return user.role == "company"


def require_owner(user: User) -> None:
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Company owner only")
```

- [ ] **Step 5: Create `backend/app/routers/company_dashboard.py` with manager endpoints**

```python
"""
Company dashboard v2 — operational dashboard for companies that already have
assigned interns.

Mounted at /api/v1/companies/me (and /api/v1/companies for setup-token flows).

This file only contains the manager-invite endpoints in this task; later tasks
add overview/students/internships/attendance/work-logs/announcements/reviews.
"""
import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    ALGORITHM, create_access_token, get_password_hash,
)
from app.models.user import User
from app.models.company import Company
from app.models.company_dashboard import CompanyManager
from app.schemas.company_dashboard import (
    ManagerInviteRequest, ManagerResponse, ManagerCompleteSetupRequest,
)
from app.services.auth_service import AuthService
from app.services.company_scope import get_my_company, require_owner
from app.services.email_service import EmailService

router = APIRouter()
settings = get_settings()

MANAGER_SETUP_TOKEN_TTL_DAYS = 7


# ---------------- Helpers ----------------

def _mint_manager_setup_token(email: str, manager_link_id: int) -> str:
    payload = {
        "sub": email,
        "manager_link_id": manager_link_id,
        "type": "manager_setup",
        "exp": datetime.now(timezone.utc) + timedelta(days=MANAGER_SETUP_TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _verify_manager_setup_token(token: str) -> tuple[str, int]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if payload.get("type") != "manager_setup":
        raise HTTPException(status_code=400, detail="Wrong token type")
    return payload["sub"], int(payload["manager_link_id"])


# ---------------- Manager endpoints ----------------

@router.post("/me/managers", response_model=ManagerResponse, status_code=201)
def invite_manager(
    body: ManagerInviteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    company = get_my_company(db, user)

    # Find or create the user
    target = db.query(User).filter(User.user_email == body.email).first()
    if target is None:
        login = body.email.split("@")[0][:50] or "manager"
        base_login = login
        n = 2
        while db.query(User).filter(User.user_login == login).first() is not None:
            login = f"{base_login}{n}"[:60]
            n += 1
        target = User(
            user_login=login,
            user_pass=get_password_hash(_secrets.token_urlsafe(32)),
            user_nicename=login,
            user_email=body.email,
            display_name=body.name,
            role="company_manager",
            is_active=True,
            is_verified=False,
        )
        db.add(target)
        db.flush()
    else:
        if target.role not in ("company_manager",):
            # Don't hijack an existing student/instructor/admin/company user.
            raise HTTPException(
                status_code=400,
                detail=f"User already exists with role={target.role}",
            )

    # Don't double-link
    existing = db.query(CompanyManager).filter(CompanyManager.user_id == target.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already a manager")

    link = CompanyManager(
        company_id=company.id,
        user_id=target.id,
        invited_by=user.id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    token = _mint_manager_setup_token(target.user_email, link.id)
    try:
        EmailService.send_manager_setup_link_email(target.user_email, token)
    except Exception:
        pass  # email failures shouldn't roll back the invite

    return ManagerResponse(
        id=link.id,
        user_id=target.id,
        email=target.user_email,
        name=target.display_name,
        accepted_at=link.accepted_at,
        invited_at=link.invited_at,
        setup_token=token,
    )


@router.get("/me/managers", response_model=List[ManagerResponse])
def list_managers(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    company = get_my_company(db, user)
    rows = (
        db.query(CompanyManager, User)
        .join(User, User.id == CompanyManager.user_id)
        .filter(CompanyManager.company_id == company.id)
        .order_by(CompanyManager.invited_at.desc())
        .all()
    )
    return [
        ManagerResponse(
            id=link.id,
            user_id=u.id,
            email=u.user_email,
            name=u.display_name,
            accepted_at=link.accepted_at,
            invited_at=link.invited_at,
        )
        for link, u in rows
    ]


@router.delete("/me/managers/{manager_id}", status_code=204)
def revoke_manager(
    manager_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    company = get_my_company(db, user)
    link = db.query(CompanyManager).filter(
        CompanyManager.id == manager_id,
        CompanyManager.company_id == company.id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Manager not found")
    db.delete(link)
    db.commit()
    return


@router.post("/managers/complete-setup")
def complete_manager_setup(
    body: ManagerCompleteSetupRequest,
    db: Session = Depends(get_db),
):
    email, link_id = _verify_manager_setup_token(body.token)
    link = db.query(CompanyManager).filter(CompanyManager.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Invite not found")
    user = db.query(User).filter(User.id == link.user_id).first()
    if not user or user.user_email != email:
        raise HTTPException(status_code=404, detail="User not found")

    user.user_pass = get_password_hash(body.password)
    user.is_verified = True
    link.accepted_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok"}
```

- [ ] **Step 6: Add `send_manager_setup_link_email` stub to `backend/app/services/email_service.py`**

Search the file for the existing `send_company_setup_link_email`. Right next to it, add:

```python
    @staticmethod
    def send_manager_setup_link_email(to_email: str, token: str) -> None:
        """Send manager-setup email with the given token."""
        link = f"{get_settings().FRONTEND_URL}/company/managers/accept?token={token}"
        subject = "You've been invited as a company manager"
        body = (
            f"You've been invited to manage interns on the SashaInfinity LMS.\n\n"
            f"Open this link to set your password and log in:\n{link}\n"
        )
        EmailService._send(to_email, subject, body)
```

If the file uses a different sending primitive, mirror the existing pattern of `send_company_setup_link_email` exactly — don't invent a new transport.

- [ ] **Step 7: Mount the new router in `backend/app/main.py`**

Find the existing `app.include_router(companies.router, ...)` block and add:
```python
from app.routers import company_dashboard
...
app.include_router(
    company_dashboard.router,
    prefix="/api/v1/companies",
    tags=["company-dashboard"],
)
```

- [ ] **Step 8: Run tests — expect pass**

Run: `docker exec magical-visvesvaraya-2204b2-backend-1 pytest tests/test_managers.py -v`
Expected: 5 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/company_dashboard.py backend/app/services/company_scope.py backend/app/routers/company_dashboard.py backend/app/services/email_service.py backend/app/main.py backend/tests/test_managers.py
git commit -m "feat(api): manager invite/list/revoke/complete-setup"
```

---

## Phase 2 — Tab APIs

All endpoints below live in `backend/app/routers/company_dashboard.py`. Each task: schemas → failing test → endpoint → passing test → commit.

### Task 2.1: Scoped queries — voucher set + manager filter

**Files:**
- Modify: `backend/app/services/company_scope.py`

Add helpers used by all tab endpoints:

```python
from sqlalchemy import or_
from app.models.internship import InternshipVoucher

def assigned_voucher_query(db: Session, user: User):
    """Return a SQLAlchemy query yielding vouchers assigned to the caller's
    company. For managers, further restricts to vouchers whose
    reporting_manager_user_id is the manager."""
    company = get_my_company(db, user)
    q = db.query(InternshipVoucher).filter(
        InternshipVoucher.hired_by_company_id == company.id,
        InternshipVoucher.status == "redeemed",
    )
    if user.role == "company_manager":
        q = q.filter(InternshipVoucher.reporting_manager_user_id == user.id)
    return q
```

- [ ] **Step 1: Failing test `backend/tests/test_company_scope.py`**

```python
def test_owner_sees_all_company_vouchers(db, make_user, make_company):
    from app.services.company_scope import assigned_voucher_query
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort

    owner = make_user(role="company")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    cohort = Cohort(name="C", slug="cs1"); db.add(cohort); db.commit(); db.refresh(cohort)
    intern = Internship(title="i", slug="i1", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id)
    db.add(intern); db.commit(); db.refresh(intern)
    s1 = make_user(role="student"); s2 = make_user(role="student")
    db.add(InternshipVoucher(code="A", internship_id=intern.id, buyer_user_id=s1.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.add(InternshipVoucher(code="B", internship_id=intern.id, buyer_user_id=s2.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.commit()
    rows = assigned_voucher_query(db, owner).all()
    assert {v.code for v in rows} == {"A", "B"}


def test_manager_only_sees_their_reportees(db, make_user, make_company):
    from app.services.company_scope import assigned_voucher_query
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    from app.models.company_dashboard import CompanyManager

    owner = make_user(role="company")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    cohort = Cohort(name="C", slug="cs2"); db.add(cohort); db.commit(); db.refresh(cohort)
    intern = Internship(title="i", slug="i2", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id)
    db.add(intern); db.commit(); db.refresh(intern)
    s1 = make_user(role="student"); s2 = make_user(role="student")
    mgr = make_user(role="company_manager")
    db.add(CompanyManager(company_id=co.id, user_id=mgr.id))
    db.add(InternshipVoucher(code="A", internship_id=intern.id, buyer_user_id=s1.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id,
                             reporting_manager_user_id=mgr.id))
    db.add(InternshipVoucher(code="B", internship_id=intern.id, buyer_user_id=s2.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id,
                             reporting_manager_user_id=None))
    db.commit()
    rows = assigned_voucher_query(db, mgr).all()
    assert {v.code for v in rows} == {"A"}
```

- [ ] **Step 2-4:** Run → fail → implement helper above → pass.
- [ ] **Step 5:** Commit:
```bash
git add backend/app/services/company_scope.py backend/tests/test_company_scope.py
git commit -m "feat(scope): assigned_voucher_query helper for owner+manager scoping"
```

---

### Task 2.2: Overview endpoint

**Files:**
- Modify: `backend/app/routers/company_dashboard.py`
- Modify: `backend/app/schemas/company_dashboard.py`

- [ ] **Step 1: Test `backend/tests/test_overview.py`**

```python
from datetime import date, timedelta


def _make_environment(db, make_user, make_company):
    from app.models.internship import Internship, InternshipVoucher, InternshipAttendance
    from app.models.cohort import Cohort
    owner = make_user(role="company", email="o@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    cohort = Cohort(name="C", slug="ovw"); db.add(cohort); db.commit(); db.refresh(cohort)
    i = Internship(title="i", slug="ovw", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id)
    db.add(i); db.commit(); db.refresh(i)
    s1 = make_user(role="student"); s2 = make_user(role="student")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s1.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.add(InternshipVoucher(code="B", internship_id=i.id, buyer_user_id=s2.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    today = date.today()
    db.add(InternshipAttendance(internship_id=i.id, user_id=s1.id,
                                attended_at=today, status="present"))
    db.commit()
    return owner, co, i, s1, s2


def test_overview_basic_counts(client, db, make_user, make_company, auth_headers):
    _make_environment(db, make_user, make_company)
    h = auth_headers("o@example.com")
    r = client.get("/api/v1/companies/me/overview", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active_interns"] == 2
    assert body["active_internships"] == 1
    assert body["today_present"] == 1
    assert body["today_absent"] == 0
    assert body["today_not_marked"] == 1
    assert "activity" in body
```

- [ ] **Step 2: Run — expect 404 (no route)**.

- [ ] **Step 3: Add schema in `backend/app/schemas/company_dashboard.py`**:

```python
class OverviewResponse(BaseModel):
    active_interns: int
    active_internships: int
    week_attendance_pct: float
    pending_work_log_reviews: int
    today_present: int
    today_absent: int
    today_late: int
    today_excused: int
    today_not_marked: int
    activity: list[dict]
```

- [ ] **Step 4: Add the endpoint** in `backend/app/routers/company_dashboard.py`:

```python
from datetime import date, timedelta
from sqlalchemy import func as sa_func, distinct

from app.models.internship import InternshipAttendance, Internship, InternshipVoucher
from app.models.company_dashboard import DailyWorkLog
from app.schemas.company_dashboard import OverviewResponse


@router.get("/me/overview", response_model=OverviewResponse)
def overview(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    vouchers = assigned_voucher_query(db, user).all()
    student_ids = [v.buyer_user_id for v in vouchers]
    internship_ids = list({v.internship_id for v in vouchers})

    today = date.today()
    week_ago = today - timedelta(days=6)

    today_rows = (
        db.query(InternshipAttendance)
        .filter(
            InternshipAttendance.user_id.in_(student_ids or [-1]),
            InternshipAttendance.internship_id.in_(internship_ids or [-1]),
            InternshipAttendance.attended_at == today,
        )
        .all()
    )
    by_status = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    for r in today_rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    not_marked = len(student_ids) - sum(by_status.values())

    week_rows = (
        db.query(InternshipAttendance.status, sa_func.count())
        .filter(
            InternshipAttendance.user_id.in_(student_ids or [-1]),
            InternshipAttendance.internship_id.in_(internship_ids or [-1]),
            InternshipAttendance.attended_at >= week_ago,
        )
        .group_by(InternshipAttendance.status)
        .all()
    )
    week_total = sum(c for _, c in week_rows)
    week_present = sum(c for s, c in week_rows if s in ("present", "late"))
    week_pct = (week_present / week_total * 100) if week_total else 0.0

    pending_reviews = (
        db.query(sa_func.count(DailyWorkLog.id))
        .filter(
            DailyWorkLog.student_user_id.in_(student_ids or [-1]),
            DailyWorkLog.review_status == "pending",
        )
        .scalar()
        or 0
    )

    activity = []  # placeholder — Task 2.3 fills this in for real

    return OverviewResponse(
        active_interns=len(student_ids),
        active_internships=len(internship_ids),
        week_attendance_pct=round(week_pct, 1),
        pending_work_log_reviews=pending_reviews,
        today_present=by_status.get("present", 0),
        today_absent=by_status.get("absent", 0),
        today_late=by_status.get("late", 0),
        today_excused=by_status.get("excused", 0),
        today_not_marked=max(not_marked, 0),
        activity=activity,
    )
```

- [ ] **Step 5: Run — expect pass.**
- [ ] **Step 6: Commit.**

```bash
git add backend/app/routers/company_dashboard.py backend/app/schemas/company_dashboard.py backend/tests/test_overview.py
git commit -m "feat(api): GET /companies/me/overview"
```

---

### Task 2.3: Students list + detail + patch

**Files:**
- Modify: `backend/app/routers/company_dashboard.py`
- Modify: `backend/app/schemas/company_dashboard.py`

- [ ] **Step 1: Test `backend/tests/test_students.py`**

```python
def test_list_students(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    owner = make_user(role="company", email="o@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    cohort = Cohort(name="C", slug="stl"); db.add(cohort); db.commit(); db.refresh(cohort)
    i = Internship(title="i", slug="stl", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id)
    db.add(i); db.commit(); db.refresh(i)
    s = make_user(role="student", email="alice@example.com")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.commit()
    h = auth_headers("o@example.com")
    r = client.get("/api/v1/companies/me/students", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["email"] == "alice@example.com"
    assert item["internship_title"] == "i"


def test_patch_student_assigns_manager(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    from app.models.company_dashboard import CompanyManager
    owner = make_user(role="company", email="op@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    cohort = Cohort(name="C", slug="ptc"); db.add(cohort); db.commit(); db.refresh(cohort)
    i = Internship(title="i", slug="ptc", price=0, spoc_user_id=spoc.id, cohort_id=cohort.id)
    db.add(i); db.commit(); db.refresh(i)
    s = make_user(role="student", email="b@example.com")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    mgr = make_user(role="company_manager", email="m@example.com")
    db.add(CompanyManager(company_id=co.id, user_id=mgr.id))
    db.commit()

    h = auth_headers("op@example.com")
    r = client.patch(
        f"/api/v1/companies/me/students/{s.id}",
        headers=h,
        json={"reporting_manager_user_id": mgr.id, "notes": "good kid"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["reporting_manager_user_id"] == mgr.id
```

- [ ] **Step 2-4: Add the schemas + endpoints**

Add to schemas:
```python
class StudentListItem(BaseModel):
    user_id: int
    voucher_id: int
    name: str
    email: EmailStr
    internship_id: int
    internship_title: str
    progress_pct: float
    attendance_pct: float
    reporting_manager_user_id: Optional[int] = None
    reporting_manager_name: Optional[str] = None
    cert_status: str
    notes: str = ""

class StudentListResponse(BaseModel):
    items: list[StudentListItem]
    total: int

class StudentPatchRequest(BaseModel):
    reporting_manager_user_id: Optional[int] = None
    notes: Optional[str] = None
    internship_status: Optional[str] = None  # active|completed|hired|let_go
```

Add to router:
```python
@router.get("/me/students", response_model=StudentListResponse)
def list_students(
    internship_id: Optional[int] = None,
    manager_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    q = assigned_voucher_query(db, user)
    if internship_id is not None:
        q = q.filter(InternshipVoucher.internship_id == internship_id)
    if manager_id is not None:
        q = q.filter(InternshipVoucher.reporting_manager_user_id == manager_id)
    vouchers = q.all()

    # Bulk fetch ancillaries
    user_ids = {v.buyer_user_id for v in vouchers}
    intern_ids = {v.internship_id for v in vouchers}
    mgr_ids = {v.reporting_manager_user_id for v in vouchers if v.reporting_manager_user_id}
    students = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids or [-1])).all()}
    interns = {i.id: i for i in db.query(Internship).filter(Internship.id.in_(intern_ids or [-1])).all()}
    mgrs = {u.id: u for u in db.query(User).filter(User.id.in_(mgr_ids or [-1])).all()} if mgr_ids else {}

    items = []
    for v in vouchers:
        s = students.get(v.buyer_user_id)
        i = interns.get(v.internship_id)
        if not s or not i:
            continue
        if search and search.lower() not in (s.display_name + s.user_email).lower():
            continue
        items.append(StudentListItem(
            user_id=s.id,
            voucher_id=v.id,
            name=s.display_name,
            email=s.user_email,
            internship_id=i.id,
            internship_title=i.title,
            progress_pct=0.0,  # filled by Task 2.7 once we wire enrollments
            attendance_pct=0.0,
            reporting_manager_user_id=v.reporting_manager_user_id,
            reporting_manager_name=mgrs[v.reporting_manager_user_id].display_name
                if v.reporting_manager_user_id else None,
            cert_status="none",
            notes="",
        ))
    return StudentListResponse(items=items, total=len(items))


@router.get("/me/students/{user_id}", response_model=StudentListItem)
def get_student(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    v = assigned_voucher_query(db, user).filter(
        InternshipVoucher.buyer_user_id == user_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Student not found")
    s = db.query(User).filter(User.id == user_id).first()
    i = db.query(Internship).filter(Internship.id == v.internship_id).first()
    mgr = (db.query(User).filter(User.id == v.reporting_manager_user_id).first()
           if v.reporting_manager_user_id else None)
    return StudentListItem(
        user_id=s.id, voucher_id=v.id, name=s.display_name, email=s.user_email,
        internship_id=i.id, internship_title=i.title,
        progress_pct=0.0, attendance_pct=0.0,
        reporting_manager_user_id=v.reporting_manager_user_id,
        reporting_manager_name=mgr.display_name if mgr else None,
        cert_status="none", notes="",
    )


@router.patch("/me/students/{user_id}", response_model=StudentListItem)
def patch_student(
    user_id: int,
    body: StudentPatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    v = assigned_voucher_query(db, user).filter(
        InternshipVoucher.buyer_user_id == user_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Student not found")
    if body.reporting_manager_user_id is not None:
        # Validate the manager belongs to this company.
        from app.models.company_dashboard import CompanyManager
        from app.services.company_scope import get_my_company
        company = get_my_company(db, user)
        ok = db.query(CompanyManager).filter(
            CompanyManager.company_id == company.id,
            CompanyManager.user_id == body.reporting_manager_user_id,
        ).first()
        if not ok and body.reporting_manager_user_id != company.owner_user_id:
            raise HTTPException(status_code=400, detail="Manager not in this company")
        v.reporting_manager_user_id = body.reporting_manager_user_id
    db.commit(); db.refresh(v)
    return get_student.__wrapped__(user_id=user_id, db=db, user=user)  # delegate
```

(Note: returning via `get_student.__wrapped__` bypasses the dependency injection; instead, just inline the lookup again or factor a `_serialize_student(...)` helper. Use the helper approach when you implement.)

- [ ] **Step 5: Run — pass. Step 6: Commit.**

```bash
git add backend/app/routers/company_dashboard.py backend/app/schemas/company_dashboard.py backend/tests/test_students.py
git commit -m "feat(api): students list / detail / patch"
```

---

### Task 2.4: Internships list + detail

**Files:** same files.

- [ ] **Step 1: Test `backend/tests/test_company_internships.py`**

```python
def test_list_internships_only_those_with_our_students(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    owner = make_user(role="company", email="o@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    c1 = Cohort(name="C1", slug="c1"); c2 = Cohort(name="C2", slug="c2")
    db.add_all([c1, c2]); db.commit(); db.refresh(c1); db.refresh(c2)
    i1 = Internship(title="i1", slug="i1", price=0, spoc_user_id=spoc.id, cohort_id=c1.id)
    i2 = Internship(title="i2", slug="i2", price=0, spoc_user_id=spoc.id, cohort_id=c2.id)
    db.add_all([i1, i2]); db.commit()
    s = make_user(role="student")
    db.add(InternshipVoucher(code="A", internship_id=i1.id, buyer_user_id=s.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.commit()
    h = auth_headers("o@example.com")
    r = client.get("/api/v1/companies/me/internships", headers=h)
    assert r.status_code == 200
    titles = [it["title"] for it in r.json()["items"]]
    assert titles == ["i1"]
```

- [ ] **Step 2-4: Add schema + endpoint:**

Schema:
```python
class CompanyInternshipItem(BaseModel):
    id: int
    title: str
    slug: str
    cover_image: Optional[str] = ""
    student_count: int
    avg_progress_pct: float
    spoc_name: Optional[str] = None

class CompanyInternshipListResponse(BaseModel):
    items: list[CompanyInternshipItem]
```

Router:
```python
@router.get("/me/internships", response_model=CompanyInternshipListResponse)
def list_company_internships(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    vouchers = assigned_voucher_query(db, user).all()
    by_iid: dict[int, list] = {}
    for v in vouchers:
        by_iid.setdefault(v.internship_id, []).append(v)

    interns = (db.query(Internship)
               .filter(Internship.id.in_(by_iid.keys() or [-1]))
               .all())
    spocs = {u.id: u for u in db.query(User).filter(
        User.id.in_({i.spoc_user_id for i in interns} or [-1])
    ).all()}

    items = []
    for i in interns:
        items.append(CompanyInternshipItem(
            id=i.id, title=i.title, slug=i.slug, cover_image=i.cover_image or "",
            student_count=len(by_iid[i.id]),
            avg_progress_pct=0.0,  # wired later
            spoc_name=spocs.get(i.spoc_user_id).display_name if spocs.get(i.spoc_user_id) else None,
        ))
    return CompanyInternshipListResponse(items=items)


@router.get("/me/internships/{internship_id}", response_model=CompanyInternshipItem)
def get_company_internship(
    internship_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    vouchers = assigned_voucher_query(db, user).filter(
        InternshipVoucher.internship_id == internship_id
    ).all()
    if not vouchers:
        raise HTTPException(status_code=404, detail="Internship not in your scope")
    i = db.query(Internship).filter(Internship.id == internship_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Internship not found")
    spoc = db.query(User).filter(User.id == i.spoc_user_id).first()
    return CompanyInternshipItem(
        id=i.id, title=i.title, slug=i.slug, cover_image=i.cover_image or "",
        student_count=len(vouchers), avg_progress_pct=0.0,
        spoc_name=spoc.display_name if spoc else None,
    )
```

- [ ] **Step 5-6: Pass + commit.**

```bash
git add backend/app/routers/company_dashboard.py backend/app/schemas/company_dashboard.py backend/tests/test_company_internships.py
git commit -m "feat(api): company internships list/detail"
```

---

### Task 2.5: Attendance grid GET + upsert POST

**Files:** same files.

- [ ] **Step 1: Test `backend/tests/test_attendance_company.py`**

```python
from datetime import date


def test_attendance_grid_returns_empty_when_no_data(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    owner = make_user(role="company", email="o@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    c = Cohort(name="C", slug="ag"); db.add(c); db.commit(); db.refresh(c)
    i = Internship(title="i", slug="ag", price=0, spoc_user_id=spoc.id, cohort_id=c.id)
    db.add(i); db.commit(); db.refresh(i)
    s = make_user(role="student")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.commit()
    h = auth_headers("o@example.com")
    today = date.today().isoformat()
    r = client.get(f"/api/v1/companies/me/attendance?from_date={today}&to_date={today}",
                   headers=h)
    assert r.status_code == 200
    body = r.json()
    assert len(body["students"]) == 1
    assert body["students"][0]["entries"] == []


def test_attendance_upsert_marks_and_round_trips(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    owner = make_user(role="company", email="o2@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    c = Cohort(name="C", slug="au"); db.add(c); db.commit(); db.refresh(c)
    i = Internship(title="i", slug="au", price=0, spoc_user_id=spoc.id, cohort_id=c.id)
    db.add(i); db.commit(); db.refresh(i)
    s = make_user(role="student")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.commit()
    h = auth_headers("o2@example.com")
    today = date.today().isoformat()
    r = client.post(
        "/api/v1/companies/me/attendance",
        headers=h,
        json={"entries": [
            {"student_user_id": s.id, "internship_id": i.id, "date": today,
             "status": "present", "hours_worked": 8.0, "notes": ""},
        ]},
    )
    assert r.status_code == 200, r.text

    r = client.get(f"/api/v1/companies/me/attendance?from_date={today}&to_date={today}",
                   headers=h)
    assert r.status_code == 200
    e = r.json()["students"][0]["entries"][0]
    assert e["status"] == "present" and float(e["hours_worked"]) == 8.0


def test_attendance_upsert_rejects_unscoped_student(client, db, make_user, make_company, auth_headers):
    """If the student isn't in this company's scope, return 404."""
    from app.models.internship import Internship
    from app.models.cohort import Cohort
    owner = make_user(role="company", email="o3@example.com")
    make_company(owner=owner)
    spoc = make_user(role="instructor")
    c = Cohort(name="C", slug="ar"); db.add(c); db.commit(); db.refresh(c)
    i = Internship(title="i", slug="ar", price=0, spoc_user_id=spoc.id, cohort_id=c.id)
    db.add(i); db.commit(); db.refresh(i)
    stranger = make_user(role="student")
    db.commit()
    h = auth_headers("o3@example.com")
    r = client.post(
        "/api/v1/companies/me/attendance",
        headers=h,
        json={"entries": [
            {"student_user_id": stranger.id, "internship_id": i.id,
             "date": date.today().isoformat(),
             "status": "present", "hours_worked": 8.0, "notes": ""},
        ]},
    )
    assert r.status_code == 404
```

- [ ] **Step 2-4: Add schema + endpoint:**

Schema:
```python
from datetime import date as DateType

class AttendanceEntry(BaseModel):
    id: Optional[int] = None
    student_user_id: int
    internship_id: int
    date: DateType
    status: str  # present|absent|late|excused
    hours_worked: float = 0
    notes: str = ""

class AttendanceStudentRow(BaseModel):
    user_id: int
    name: str
    entries: list[AttendanceEntry]

class AttendanceGridResponse(BaseModel):
    from_date: DateType
    to_date: DateType
    students: list[AttendanceStudentRow]

class AttendanceUpsertRequest(BaseModel):
    entries: list[AttendanceEntry]

class AttendanceUpsertResponse(BaseModel):
    upserted: int
```

Router:
```python
@router.get("/me/attendance", response_model=AttendanceGridResponse)
def attendance_grid(
    from_date: DateType,
    to_date: DateType,
    internship_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    q = assigned_voucher_query(db, user)
    if internship_id is not None:
        q = q.filter(InternshipVoucher.internship_id == internship_id)
    vouchers = q.all()
    student_ids = [v.buyer_user_id for v in vouchers]
    students = {u.id: u for u in db.query(User).filter(User.id.in_(student_ids or [-1])).all()}

    rows = (
        db.query(InternshipAttendance)
        .filter(
            InternshipAttendance.user_id.in_(student_ids or [-1]),
            InternshipAttendance.attended_at >= from_date,
            InternshipAttendance.attended_at <= to_date,
        )
        .all()
    )
    by_user: dict[int, list[AttendanceEntry]] = {sid: [] for sid in student_ids}
    for r in rows:
        by_user.setdefault(r.user_id, []).append(AttendanceEntry(
            id=r.id, student_user_id=r.user_id, internship_id=r.internship_id,
            date=r.attended_at, status=r.status, hours_worked=float(r.hours_worked or 0),
            notes=r.notes or "",
        ))
    return AttendanceGridResponse(
        from_date=from_date, to_date=to_date,
        students=[
            AttendanceStudentRow(
                user_id=sid,
                name=students[sid].display_name if sid in students else "(unknown)",
                entries=by_user.get(sid, []),
            )
            for sid in student_ids
        ],
    )


@router.post("/me/attendance", response_model=AttendanceUpsertResponse)
def attendance_upsert(
    body: AttendanceUpsertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    allowed_pairs = {
        (v.buyer_user_id, v.internship_id)
        for v in assigned_voucher_query(db, user).all()
    }
    upserted = 0
    for e in body.entries:
        if (e.student_user_id, e.internship_id) not in allowed_pairs:
            raise HTTPException(status_code=404,
                                detail=f"Student {e.student_user_id} not in your scope")
        existing = (
            db.query(InternshipAttendance)
            .filter(
                InternshipAttendance.internship_id == e.internship_id,
                InternshipAttendance.user_id == e.student_user_id,
                InternshipAttendance.attended_at == e.date,
            )
            .first()
        )
        if existing:
            existing.status = e.status
            existing.hours_worked = e.hours_worked
            existing.notes = e.notes
            existing.marked_by = user.id
        else:
            db.add(InternshipAttendance(
                internship_id=e.internship_id, user_id=e.student_user_id,
                attended_at=e.date, status=e.status, hours_worked=e.hours_worked,
                notes=e.notes, marked_by=user.id,
            ))
        upserted += 1
    db.commit()
    return AttendanceUpsertResponse(upserted=upserted)
```

- [ ] **Step 5: Run — pass. Step 6: Commit.**

```bash
git add backend/app/routers/company_dashboard.py backend/app/schemas/company_dashboard.py backend/tests/test_attendance_company.py
git commit -m "feat(api): attendance grid get + upsert"
```

---

### Task 2.6: Work-logs list + review

**Files:** same.

- [ ] **Step 1: Test `backend/tests/test_work_logs.py`**

```python
from datetime import date


def test_list_and_review_work_log(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    from app.models.company_dashboard import DailyWorkLog
    owner = make_user(role="company", email="o@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    c = Cohort(name="C", slug="wl"); db.add(c); db.commit(); db.refresh(c)
    i = Internship(title="i", slug="wl", price=0, spoc_user_id=spoc.id, cohort_id=c.id)
    db.add(i); db.commit(); db.refresh(i)
    s = make_user(role="student")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    log = DailyWorkLog(student_user_id=s.id, internship_id=i.id,
                       log_date=date.today(), content="did stuff")
    db.add(log); db.commit(); db.refresh(log)

    h = auth_headers("o@example.com")
    r = client.get("/api/v1/companies/me/work-logs", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["review_status"] == "pending"

    r = client.post(
        f"/api/v1/companies/me/work-logs/{log.id}/review",
        headers=h,
        json={"review_status": "approved", "comment": "ok"},
    )
    assert r.status_code == 200
    assert r.json()["review_status"] == "approved"
```

- [ ] **Step 2-4: Schemas + endpoint**

Schema:
```python
class WorkLogItem(BaseModel):
    id: int
    student_user_id: int
    student_name: str
    internship_id: int
    internship_title: str
    log_date: DateType
    content: str
    attachment_url: str = ""
    review_status: str
    reviewer_comment: str = ""
    reviewed_by: Optional[int] = None
    created_at: datetime

class WorkLogListResponse(BaseModel):
    items: list[WorkLogItem]
    total: int

class WorkLogReviewRequest(BaseModel):
    review_status: str  # approved|flagged|pending
    comment: str = ""
```

Router:
```python
@router.get("/me/work-logs", response_model=WorkLogListResponse)
def list_work_logs(
    review_status: Optional[str] = None,
    internship_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    student_ids = [v.buyer_user_id for v in assigned_voucher_query(db, user).all()]
    q = db.query(DailyWorkLog).filter(DailyWorkLog.student_user_id.in_(student_ids or [-1]))
    if review_status:
        q = q.filter(DailyWorkLog.review_status == review_status)
    if internship_id is not None:
        q = q.filter(DailyWorkLog.internship_id == internship_id)
    rows = q.order_by(DailyWorkLog.log_date.desc()).all()
    students = {u.id: u for u in db.query(User).filter(User.id.in_(student_ids or [-1])).all()}
    interns = {i.id: i for i in db.query(Internship).filter(
        Internship.id.in_({r.internship_id for r in rows} or [-1])
    ).all()}
    items = [
        WorkLogItem(
            id=r.id, student_user_id=r.student_user_id,
            student_name=students[r.student_user_id].display_name
                if r.student_user_id in students else "(unknown)",
            internship_id=r.internship_id,
            internship_title=interns[r.internship_id].title
                if r.internship_id in interns else "",
            log_date=r.log_date, content=r.content, attachment_url=r.attachment_url,
            review_status=r.review_status, reviewer_comment=r.reviewer_comment,
            reviewed_by=r.reviewed_by, created_at=r.created_at,
        )
        for r in rows
    ]
    return WorkLogListResponse(items=items, total=len(items))


@router.post("/me/work-logs/{log_id}/review", response_model=WorkLogItem)
def review_work_log(
    log_id: int,
    body: WorkLogReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    if body.review_status not in ("approved", "flagged", "pending"):
        raise HTTPException(status_code=400, detail="Bad review_status")
    from app.services.company_scope import assigned_voucher_query
    student_ids = {v.buyer_user_id for v in assigned_voucher_query(db, user).all()}
    log = db.query(DailyWorkLog).filter(DailyWorkLog.id == log_id).first()
    if not log or log.student_user_id not in student_ids:
        raise HTTPException(status_code=404, detail="Log not found")
    log.review_status = body.review_status
    log.reviewer_comment = body.comment
    log.reviewed_by = user.id
    db.commit(); db.refresh(log)
    student = db.query(User).filter(User.id == log.student_user_id).first()
    intern = db.query(Internship).filter(Internship.id == log.internship_id).first()
    return WorkLogItem(
        id=log.id, student_user_id=log.student_user_id,
        student_name=student.display_name if student else "(unknown)",
        internship_id=log.internship_id,
        internship_title=intern.title if intern else "",
        log_date=log.log_date, content=log.content, attachment_url=log.attachment_url,
        review_status=log.review_status, reviewer_comment=log.reviewer_comment,
        reviewed_by=log.reviewed_by, created_at=log.created_at,
    )
```

- [ ] **Step 5-6: Pass + commit.**

```bash
git add backend/app/routers/company_dashboard.py backend/app/schemas/company_dashboard.py backend/tests/test_work_logs.py
git commit -m "feat(api): work-logs list + review"
```

---

### Task 2.7: Announcements (list / post / delete)

**Files:** same.

- [ ] **Step 1: Test `backend/tests/test_announcements.py`**

```python
def test_post_and_list_announcement(client, make_user, make_company, auth_headers):
    owner = make_user(role="company", email="o@example.com")
    make_company(owner=owner)
    h = auth_headers("o@example.com")
    r = client.post("/api/v1/companies/me/announcements", headers=h,
                    json={"title": "Welcome", "body": "Hi!"})
    assert r.status_code == 201, r.text
    aid = r.json()["id"]

    r = client.get("/api/v1/companies/me/announcements", headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["id"] == aid

    r = client.delete(f"/api/v1/companies/me/announcements/{aid}", headers=h)
    assert r.status_code == 204
    r = client.get("/api/v1/companies/me/announcements", headers=h)
    assert r.json()["items"] == []


def test_manager_cannot_post_announcement(client, db, make_user, make_company, auth_headers):
    from app.models.company_dashboard import CompanyManager
    owner = make_user(role="company", email="o2@example.com")
    co = make_company(owner=owner)
    mgr = make_user(role="company_manager", email="m@example.com")
    db.add(CompanyManager(company_id=co.id, user_id=mgr.id)); db.commit()
    h = auth_headers("m@example.com")
    r = client.post("/api/v1/companies/me/announcements", headers=h,
                    json={"title": "x", "body": "y"})
    assert r.status_code == 403
```

- [ ] **Step 2-4: Schemas + endpoints**

Schema:
```python
class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str
    internship_id: Optional[int] = None

class AnnouncementItem(BaseModel):
    id: int
    title: str
    body: str
    internship_id: Optional[int] = None
    created_at: datetime
    created_by: Optional[int] = None

class AnnouncementListResponse(BaseModel):
    items: list[AnnouncementItem]
```

Router:
```python
@router.post("/me/announcements", response_model=AnnouncementItem, status_code=201)
def post_announcement(
    body: AnnouncementCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    from app.services.company_scope import get_my_company
    company = get_my_company(db, user)
    a = InternshipAnnouncement(
        company_id=company.id, internship_id=body.internship_id,
        title=body.title, body=body.body, created_by=user.id,
    )
    db.add(a); db.commit(); db.refresh(a)
    return AnnouncementItem(
        id=a.id, title=a.title, body=a.body, internship_id=a.internship_id,
        created_at=a.created_at, created_by=a.created_by,
    )


@router.get("/me/announcements", response_model=AnnouncementListResponse)
def list_announcements(
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import get_my_company
    company = get_my_company(db, user)
    rows = (db.query(InternshipAnnouncement)
            .filter(InternshipAnnouncement.company_id == company.id,
                    InternshipAnnouncement.deleted_at.is_(None))
            .order_by(InternshipAnnouncement.created_at.desc())
            .all())
    return AnnouncementListResponse(items=[
        AnnouncementItem(
            id=a.id, title=a.title, body=a.body, internship_id=a.internship_id,
            created_at=a.created_at, created_by=a.created_by,
        ) for a in rows
    ])


@router.delete("/me/announcements/{announcement_id}", status_code=204)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    from app.services.company_scope import get_my_company
    company = get_my_company(db, user)
    a = db.query(InternshipAnnouncement).filter(
        InternshipAnnouncement.id == announcement_id,
        InternshipAnnouncement.company_id == company.id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    a.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return
```

(Add `from app.models.company_dashboard import InternshipAnnouncement` near the imports if not already present.)

- [ ] **Step 5-6: Pass + commit.**

```bash
git add backend/app/routers/company_dashboard.py backend/app/schemas/company_dashboard.py backend/tests/test_announcements.py
git commit -m "feat(api): announcements post/list/delete"
```

---

### Task 2.8: Performance review submit

**Files:** same.

- [ ] **Step 1: Test `backend/tests/test_perf_review.py`**

```python
def test_submit_review_once(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    owner = make_user(role="company", email="o@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    c = Cohort(name="C", slug="rv"); db.add(c); db.commit(); db.refresh(c)
    i = Internship(title="i", slug="rv", price=0, spoc_user_id=spoc.id, cohort_id=c.id)
    db.add(i); db.commit(); db.refresh(i)
    s = make_user(role="student")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.commit()
    h = auth_headers("o@example.com")
    r = client.post(
        f"/api/v1/companies/me/students/{s.id}/review",
        headers=h,
        json={"internship_id": i.id, "rating": 5, "feedback": "great",
              "hire_recommendation": "yes"},
    )
    assert r.status_code == 201, r.text
    # Second submit must conflict
    r = client.post(
        f"/api/v1/companies/me/students/{s.id}/review",
        headers=h,
        json={"internship_id": i.id, "rating": 4, "feedback": "x",
              "hire_recommendation": "maybe"},
    )
    assert r.status_code == 409
```

- [ ] **Step 2-4: Schemas + endpoint**

Schema:
```python
class PerformanceReviewRequest(BaseModel):
    internship_id: int
    rating: int = Field(ge=1, le=5)
    feedback: str = ""
    hire_recommendation: str = "maybe"  # yes|maybe|no

class PerformanceReviewResponse(BaseModel):
    id: int
    rating: int
    feedback: str
    hire_recommendation: str
    submitted_at: datetime
```

Router:
```python
from app.models.company_dashboard import InternshipPerformanceReview


@router.post("/me/students/{user_id}/review",
             response_model=PerformanceReviewResponse, status_code=201)
def submit_review(
    user_id: int,
    body: PerformanceReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    require_owner(user)
    from app.services.company_scope import assigned_voucher_query, get_my_company
    company = get_my_company(db, user)
    v = assigned_voucher_query(db, user).filter(
        InternshipVoucher.buyer_user_id == user_id,
        InternshipVoucher.internship_id == body.internship_id,
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Student/internship not in your scope")
    if body.hire_recommendation not in ("yes", "maybe", "no"):
        raise HTTPException(status_code=400, detail="Bad hire_recommendation")
    existing = db.query(InternshipPerformanceReview).filter(
        InternshipPerformanceReview.company_id == company.id,
        InternshipPerformanceReview.student_user_id == user_id,
        InternshipPerformanceReview.internship_id == body.internship_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Review already submitted")
    rev = InternshipPerformanceReview(
        company_id=company.id, student_user_id=user_id,
        internship_id=body.internship_id, rating=body.rating,
        feedback=body.feedback, hire_recommendation=body.hire_recommendation,
        submitted_by=user.id,
    )
    db.add(rev); db.commit(); db.refresh(rev)
    return PerformanceReviewResponse(
        id=rev.id, rating=rev.rating, feedback=rev.feedback,
        hire_recommendation=rev.hire_recommendation, submitted_at=rev.submitted_at,
    )
```

- [ ] **Step 5-6: Pass + commit.**

```bash
git add backend/app/routers/company_dashboard.py backend/app/schemas/company_dashboard.py backend/tests/test_perf_review.py
git commit -m "feat(api): performance review submit"
```

---

## Phase 3 — Frontend

### Task 3.1: Delete old company dashboard files

**Files:**
- Delete: `frontend/src/pages/company/dashboard.tsx`
- Delete: `frontend/src/components/company/InterestModal.tsx`
- Delete: `frontend/src/api/company.ts`
- Modify: `frontend/src/App.tsx` (remove imports + replace `/company/dashboard` route — done in next task)

- [ ] **Step 1: Remove the imports of `CompanyDashboardPage` and `InterestModal`** from any file that references them. Search:
```bash
grep -RIln "CompanyDashboardPage\|InterestModal\|api/company'\|from '@/api/company'" frontend/src
```
For each match, delete the import and any code that depends on it. We'll re-route the dashboard route in Task 3.3 — until then, leave a placeholder.

- [ ] **Step 2: Delete the three files.**
- [ ] **Step 3: Verify build still passes**: `docker exec magical-visvesvaraya-2204b2-frontend-1 npm run type-check`. Fix any remaining import errors.
- [ ] **Step 4: Commit.**

```bash
git add -A
git commit -m "chore(frontend): remove deprecated browse/pipeline dashboard"
```

---

### Task 3.2: New API client

**Files:**
- Create: `frontend/src/api/company-dashboard.ts`

- [ ] **Step 1:** Write the typed client.

```ts
// frontend/src/api/company-dashboard.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './axios'

// ----- Types (mirror backend Pydantic) -----

export type Overview = {
  active_interns: number
  active_internships: number
  week_attendance_pct: number
  pending_work_log_reviews: number
  today_present: number
  today_absent: number
  today_late: number
  today_excused: number
  today_not_marked: number
  activity: any[]
}

export type Manager = {
  id: number
  user_id: number
  email: string
  name: string
  accepted_at: string | null
  invited_at: string
  setup_token?: string
}

export type Student = {
  user_id: number
  voucher_id: number
  name: string
  email: string
  internship_id: number
  internship_title: string
  progress_pct: number
  attendance_pct: number
  reporting_manager_user_id: number | null
  reporting_manager_name: string | null
  cert_status: string
  notes: string
}

export type CompanyInternship = {
  id: number
  title: string
  slug: string
  cover_image: string
  student_count: number
  avg_progress_pct: number
  spoc_name: string | null
}

export type AttendanceEntry = {
  id?: number
  student_user_id: number
  internship_id: number
  date: string
  status: 'present' | 'absent' | 'late' | 'excused'
  hours_worked: number
  notes: string
}

export type AttendanceGrid = {
  from_date: string
  to_date: string
  students: { user_id: number; name: string; entries: AttendanceEntry[] }[]
}

export type WorkLog = {
  id: number
  student_user_id: number
  student_name: string
  internship_id: number
  internship_title: string
  log_date: string
  content: string
  attachment_url: string
  review_status: 'pending' | 'approved' | 'flagged'
  reviewer_comment: string
  reviewed_by: number | null
  created_at: string
}

export type Announcement = {
  id: number
  title: string
  body: string
  internship_id: number | null
  created_at: string
  created_by: number | null
}

// ----- Hooks -----

const base = '/api/v1/companies/me'

export const useOverview = () =>
  useQuery({
    queryKey: ['company', 'overview'],
    queryFn: async () => (await api.get<Overview>(`${base}/overview`)).data,
  })

export const useStudents = (params: { internship_id?: number; manager_id?: number; search?: string } = {}) =>
  useQuery({
    queryKey: ['company', 'students', params],
    queryFn: async () => (await api.get(`${base}/students`, { params })).data as { items: Student[]; total: number },
  })

export const useStudent = (userId: number | null) =>
  useQuery({
    queryKey: ['company', 'student', userId],
    enabled: userId != null,
    queryFn: async () => (await api.get<Student>(`${base}/students/${userId}`)).data,
  })

export const usePatchStudent = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ userId, ...patch }: { userId: number } & Partial<{ reporting_manager_user_id: number; notes: string; internship_status: string }>) =>
      (await api.patch(`${base}/students/${userId}`, patch)).data as Student,
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['company', 'students'] })
      qc.invalidateQueries({ queryKey: ['company', 'student', vars.userId] })
    },
  })
}

export const useCompanyInternships = () =>
  useQuery({
    queryKey: ['company', 'internships'],
    queryFn: async () => (await api.get(`${base}/internships`)).data as { items: CompanyInternship[] },
  })

export const useAttendanceGrid = (from: string, to: string, internshipId?: number) =>
  useQuery({
    queryKey: ['company', 'attendance', from, to, internshipId],
    queryFn: async () => (await api.get<AttendanceGrid>(`${base}/attendance`, {
      params: { from_date: from, to_date: to, internship_id: internshipId },
    })).data,
  })

export const useUpsertAttendance = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (entries: AttendanceEntry[]) =>
      (await api.post(`${base}/attendance`, { entries })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company', 'attendance'] }),
  })
}

export const useWorkLogs = (params: { review_status?: string; internship_id?: number } = {}) =>
  useQuery({
    queryKey: ['company', 'work-logs', params],
    queryFn: async () => (await api.get(`${base}/work-logs`, { params })).data as { items: WorkLog[] },
  })

export const useReviewWorkLog = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, review_status, comment }: { id: number; review_status: string; comment: string }) =>
      (await api.post(`${base}/work-logs/${id}/review`, { review_status, comment })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company', 'work-logs'] }),
  })
}

export const useAnnouncements = () =>
  useQuery({
    queryKey: ['company', 'announcements'],
    queryFn: async () => (await api.get(`${base}/announcements`)).data as { items: Announcement[] },
  })

export const usePostAnnouncement = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { title: string; body: string; internship_id?: number }) =>
      (await api.post(`${base}/announcements`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company', 'announcements'] }),
  })
}

export const useDeleteAnnouncement = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`${base}/announcements/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company', 'announcements'] }),
  })
}

export const useManagers = () =>
  useQuery({
    queryKey: ['company', 'managers'],
    queryFn: async () => (await api.get<Manager[]>(`${base}/managers`)).data,
  })

export const useInviteManager = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (p: { email: string; name: string }) =>
      (await api.post<Manager>(`${base}/managers`, p)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company', 'managers'] }),
  })
}

export const useRevokeManager = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => (await api.delete(`${base}/managers/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company', 'managers'] }),
  })
}

export const useSubmitReview = () =>
  useMutation({
    mutationFn: async ({ userId, ...body }: { userId: number; internship_id: number; rating: number; feedback: string; hire_recommendation: string }) =>
      (await api.post(`${base}/students/${userId}/review`, body)).data,
  })
```

- [ ] **Step 2: Type-check** then commit.

```bash
docker exec magical-visvesvaraya-2204b2-frontend-1 npm run type-check
git add frontend/src/api/company-dashboard.ts
git commit -m "feat(frontend): typed React Query client for company dashboard v2"
```

---

### Task 3.3: Layout + routes

**Files:**
- Create: `frontend/src/pages/company/Layout.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write `frontend/src/pages/company/Layout.tsx`**

```tsx
import { NavLink, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'

const NAV = [
  { to: '/company/dashboard/overview', label: 'Overview' },
  { to: '/company/dashboard/students', label: 'Students' },
  { to: '/company/dashboard/internships', label: 'Internships' },
  { to: '/company/dashboard/attendance', label: 'Attendance' },
  { to: '/company/dashboard/announcements', label: 'Announcements' },
  { to: '/company/dashboard/reports/attendance', label: 'Reports' },
] as const

export default function CompanyLayout() {
  const role = useAuthStore((s) => s.user?.role)
  const isOwner = role === 'company'
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="font-bold text-lg">Company workspace</h1>
        </div>
      </header>
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-12 gap-6 py-6">
        <aside className="col-span-2 space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm ${isActive ? 'bg-indigo-100 text-indigo-700 font-semibold' : 'text-slate-700 hover:bg-slate-100'}`
              }
            >
              {n.label}
            </NavLink>
          ))}
          {isOwner && (
            <NavLink
              to="/company/dashboard/managers"
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm ${isActive ? 'bg-indigo-100 text-indigo-700 font-semibold' : 'text-slate-700 hover:bg-slate-100'}`
              }
            >
              Managers
            </NavLink>
          )}
        </aside>
        <main className="col-span-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Update `frontend/src/App.tsx`** — replace the existing single `/company/dashboard` `<Route>` with:

```tsx
import CompanyLayout from '@/pages/company/Layout'
import Overview from '@/pages/company/Overview'
import Students from '@/pages/company/Students'
import Internships from '@/pages/company/Internships'
import Attendance from '@/pages/company/Attendance'
import Announcements from '@/pages/company/Announcements'
import Managers from '@/pages/company/Managers'
import Reports from '@/pages/company/Reports'

// inside the routes block:
<Route path="/company/dashboard" element={
  <ProtectedRoute requiredRoles={['company', 'company_manager']}>
    <CompanyLayout />
  </ProtectedRoute>
}>
  <Route index element={<Navigate to="/company/dashboard/overview" replace />} />
  <Route path="overview" element={<Overview />} />
  <Route path="students" element={<Students />} />
  <Route path="internships" element={<Internships />} />
  <Route path="attendance" element={<Attendance />} />
  <Route path="announcements" element={<Announcements />} />
  <Route path="managers" element={<Managers />} />
  <Route path="reports/attendance" element={<Reports />} />
</Route>
```

(`ProtectedRoute` currently takes `requiredRole` (singular). Update it to also accept `requiredRoles` (array). Look at its current signature in `frontend/src/components/routing/`. If only `requiredRole` exists, add the `requiredRoles` array support — bool: `roles.includes(user.role)`.)

- [ ] **Step 3: Stub each page so the build passes.** Create each of the seven page files with a placeholder `export default function X() { return <div>X</div> }`. They get filled in in Tasks 3.4–3.10.

- [ ] **Step 4: Type-check + smoke navigate** then commit.

```bash
docker exec magical-visvesvaraya-2204b2-frontend-1 npm run type-check
git add -A
git commit -m "feat(frontend): company dashboard layout + nested routes"
```

---

### Task 3.4: Overview page

**Files:**
- Modify: `frontend/src/pages/company/Overview.tsx`

- [ ] **Step 1: Implement**

```tsx
import { useOverview } from '@/api/company-dashboard'

const StatCard = ({ label, value, hint }: { label: string; value: number | string; hint?: string }) => (
  <div className="bg-white rounded-xl border border-slate-200 p-5">
    <div className="text-xs text-slate-500">{label}</div>
    <div className="text-3xl font-bold text-slate-900 mt-1">{value}</div>
    {hint && <div className="text-xs text-slate-500 mt-1">{hint}</div>}
  </div>
)

export default function Overview() {
  const { data, isLoading, error } = useOverview()
  if (isLoading) return <div>Loading…</div>
  if (error || !data) return <div className="text-red-600">Failed to load</div>
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Active interns" value={data.active_interns} />
        <StatCard label="Active internships" value={data.active_internships} />
        <StatCard label="Week attendance" value={`${data.week_attendance_pct}%`} />
        <StatCard label="Pending work-log reviews" value={data.pending_work_log_reviews} />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold mb-3">Today's attendance</h2>
        <div className="grid grid-cols-5 gap-3 text-center">
          <StatCard label="Present" value={data.today_present} />
          <StatCard label="Absent" value={data.today_absent} />
          <StatCard label="Late" value={data.today_late} />
          <StatCard label="Excused" value={data.today_excused} />
          <StatCard label="Not marked" value={data.today_not_marked} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit.**

```bash
git add frontend/src/pages/company/Overview.tsx
git commit -m "feat(frontend): overview tab"
```

---

### Task 3.5: Students page (table + drawer)

**Files:**
- Modify: `frontend/src/pages/company/Students.tsx`
- Create: `frontend/src/pages/company/StudentDrawer.tsx`

- [ ] Implement the list table; click row → set `selectedId`; render `StudentDrawer` when set. Drawer fetches `useStudent(selectedId)`, `useManagers()`, exposes a `<select>` to assign a reporting manager and a textarea + button to submit a review (calls `useSubmitReview`). Standard React + Tailwind patterns; no novel logic. Keep file under 250 lines.

- [ ] Type-check + commit.

```bash
git add frontend/src/pages/company/Students.tsx frontend/src/pages/company/StudentDrawer.tsx
git commit -m "feat(frontend): students tab with drawer"
```

---

### Task 3.6: Internships page

**Files:**
- Modify: `frontend/src/pages/company/Internships.tsx`

- [ ] Cards grid backed by `useCompanyInternships()`. Click card → route to `/company/dashboard/internships/:id` (add the route). Detail page calls `useStudents({ internship_id })` and renders the same student table component.

- [ ] Commit.

---

### Task 3.7: Attendance grid

**Files:**
- Modify: `frontend/src/pages/company/Attendance.tsx`

- [ ] Build a 14-day grid. Top bar: date-range picker (defaults to last 14 days), internship filter `<select>`, "Mark all present today" button.
- [ ] Each cell: shows status letter + hours; click opens a small popover with status `<select>`, hours `<input type="number">`, notes `<textarea>`, Save → `useUpsertAttendance({ entries: [...] })`.
- [ ] After save, React Query refetches the grid.
- [ ] Commit.

---

### Task 3.8: Announcements

**Files:**
- Modify: `frontend/src/pages/company/Announcements.tsx`

- [ ] List of announcements (`useAnnouncements`). Owner-only "New" form at the top (title + body + optional internship select). Owner-only delete button per row.

---

### Task 3.9: Managers page (owner-only)

**Files:**
- Modify: `frontend/src/pages/company/Managers.tsx`

- [ ] Form to invite (email + name → `useInviteManager`). When the invite returns a `setup_token`, render the link `${origin}/company/managers/accept?token=...` so the owner can copy/paste it (in case email delivery fails — mirrors how admin invites companies). Table of existing managers with revoke button. Add a separate route `/company/managers/accept` that renders an accept-invite page calling `POST /api/v1/companies/managers/complete-setup`.

---

### Task 3.10: Reports page placeholder

**Files:**
- Modify: `frontend/src/pages/company/Reports.tsx`

- [ ] Stub now; full implementation in Phase 4. Just render `<div>Attendance report (Phase 4)</div>` to keep the route alive.

---

## Phase 4 — Reports (PDF + CSV)

### Task 4.1: Add reportlab dependency + service skeleton

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/services/attendance_report.py`

- [ ] **Step 1: Add to `backend/requirements.txt`**: `reportlab==4.2.0`. Rebuild the backend image:
```bash
cd ../../.. && docker-compose build backend && docker-compose up -d backend
```

- [ ] **Step 2: Write `backend/app/services/attendance_report.py`**

```python
"""Pure data builder + CSV/PDF renderers for attendance reports."""
from dataclasses import dataclass
from datetime import date
from io import BytesIO, StringIO
from typing import Iterable, Optional
import csv

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.internship import Internship, InternshipAttendance, InternshipVoucher
from app.models.company import Company


@dataclass
class ReportRow:
    log_date: date
    student_name: str
    student_email: str
    internship_title: str
    reporting_manager: str
    status: str
    hours: float
    note: str
    marked_by_name: str


def build_rows(
    db: Session,
    *,
    voucher_ids: Iterable[int],
    from_date: date,
    to_date: date,
    student_ids: Optional[list[int]] = None,
    internship_ids: Optional[list[int]] = None,
    manager_ids: Optional[list[int]] = None,
) -> list[ReportRow]:
    vouchers = (
        db.query(InternshipVoucher)
        .filter(InternshipVoucher.id.in_(list(voucher_ids) or [-1]))
        .all()
    )
    if internship_ids:
        vouchers = [v for v in vouchers if v.internship_id in set(internship_ids)]
    if manager_ids:
        s = set(manager_ids)
        vouchers = [v for v in vouchers if v.reporting_manager_user_id in s]
    if student_ids:
        s = set(student_ids)
        vouchers = [v for v in vouchers if v.buyer_user_id in s]

    sids = [v.buyer_user_id for v in vouchers]
    iids = list({v.internship_id for v in vouchers})

    students = {u.id: u for u in db.query(User).filter(User.id.in_(sids or [-1])).all()}
    interns = {i.id: i for i in db.query(Internship).filter(Internship.id.in_(iids or [-1])).all()}
    mgrs = {u.id: u for u in db.query(User).filter(
        User.id.in_({v.reporting_manager_user_id for v in vouchers if v.reporting_manager_user_id} or [-1])
    ).all()}

    att = (
        db.query(InternshipAttendance)
        .filter(
            InternshipAttendance.user_id.in_(sids or [-1]),
            InternshipAttendance.attended_at >= from_date,
            InternshipAttendance.attended_at <= to_date,
        )
        .order_by(InternshipAttendance.attended_at.asc())
        .all()
    )
    markers = {u.id: u for u in db.query(User).filter(
        User.id.in_({a.marked_by for a in att if a.marked_by} or [-1])
    ).all()}
    voucher_by_user = {v.buyer_user_id: v for v in vouchers}

    rows: list[ReportRow] = []
    for a in att:
        v = voucher_by_user.get(a.user_id)
        s = students.get(a.user_id)
        i = interns.get(a.internship_id)
        if not (v and s and i):
            continue
        rows.append(ReportRow(
            log_date=a.attended_at,
            student_name=s.display_name,
            student_email=s.user_email,
            internship_title=i.title,
            reporting_manager=(
                mgrs[v.reporting_manager_user_id].display_name
                if v.reporting_manager_user_id and v.reporting_manager_user_id in mgrs
                else ""
            ),
            status=a.status,
            hours=float(a.hours_worked or 0),
            note=a.notes or "",
            marked_by_name=(markers[a.marked_by].display_name
                            if a.marked_by and a.marked_by in markers else ""),
        ))
    return rows


def render_csv(rows: list[ReportRow]) -> bytes:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Student", "Email", "Internship", "Manager",
                "Status", "Hours", "Note", "Marked by"])
    for r in rows:
        w.writerow([r.log_date.isoformat(), r.student_name, r.student_email,
                    r.internship_title, r.reporting_manager, r.status,
                    f"{r.hours:.2f}", r.note, r.marked_by_name])
    # Footer summary
    total_days = len({(r.student_email, r.log_date) for r in rows})
    total_hours = sum(r.hours for r in rows)
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    w.writerow([])
    w.writerow(["Total entries", total_days])
    w.writerow(["Total hours", f"{total_hours:.2f}"])
    for s, c in by_status.items():
        w.writerow([f"Status {s}", c])
    return buf.getvalue().encode("utf-8")


def render_pdf(rows: list[ReportRow], *, title: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    head = ["Date", "Student", "Email", "Internship", "Manager", "Status", "Hours", "Note"]
    body = [[
        r.log_date.isoformat(), r.student_name, r.student_email,
        r.internship_title, r.reporting_manager, r.status, f"{r.hours:.2f}", r.note,
    ] for r in rows]
    table = Table([head, *body], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story.append(table)
    doc.build(story)
    return buf.getvalue()
```

- [ ] **Step 3: Commit.**

```bash
git add backend/requirements.txt backend/app/services/attendance_report.py
git commit -m "feat(reports): attendance report builder + CSV/PDF renderers"
```

---

### Task 4.2: Company report endpoint

**Files:**
- Modify: `backend/app/routers/company_dashboard.py`

- [ ] **Step 1: Test `backend/tests/test_company_report.py`**

```python
from datetime import date


def test_company_report_csv(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher, InternshipAttendance
    from app.models.cohort import Cohort
    owner = make_user(role="company", email="o@example.com")
    co = make_company(owner=owner)
    spoc = make_user(role="instructor")
    c = Cohort(name="C", slug="rp"); db.add(c); db.commit(); db.refresh(c)
    i = Internship(title="i", slug="rp", price=0, spoc_user_id=spoc.id, cohort_id=c.id)
    db.add(i); db.commit(); db.refresh(i)
    s = make_user(role="student", email="alice@example.com")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.add(InternshipAttendance(internship_id=i.id, user_id=s.id,
                                attended_at=date(2026, 5, 5),
                                status="present", hours_worked=8))
    db.commit()
    h = auth_headers("o@example.com")
    r = client.get(
        "/api/v1/companies/me/reports/attendance",
        params={"from_date": "2026-05-01", "to_date": "2026-05-31", "format": "csv"},
        headers=h,
    )
    assert r.status_code == 200
    text = r.content.decode()
    assert "alice@example.com" in text
    assert "Total hours" in text


def test_company_report_pdf(client, db, make_user, make_company, auth_headers):
    owner = make_user(role="company", email="o2@example.com")
    make_company(owner=owner)
    h = auth_headers("o2@example.com")
    r = client.get(
        "/api/v1/companies/me/reports/attendance",
        params={"from_date": "2026-05-01", "to_date": "2026-05-31", "format": "pdf"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_company_report_json(client, make_user, make_company, auth_headers):
    owner = make_user(role="company", email="o3@example.com")
    make_company(owner=owner)
    h = auth_headers("o3@example.com")
    r = client.get(
        "/api/v1/companies/me/reports/attendance",
        params={"from_date": "2026-05-01", "to_date": "2026-05-31"},
        headers=h,
    )
    assert r.status_code == 200
    assert "rows" in r.json()
```

- [ ] **Step 2-4: Endpoint**

```python
from fastapi.responses import Response
from datetime import date as DateType

from app.services.attendance_report import build_rows, render_csv, render_pdf


@router.get("/me/reports/attendance")
def company_attendance_report(
    from_date: DateType,
    to_date: DateType,
    internship_id: Optional[list[int]] = None,
    student_id: Optional[list[int]] = None,
    manager_id: Optional[list[int]] = None,
    format: str = "json",
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_company_or_manager),
):
    from app.services.company_scope import assigned_voucher_query
    voucher_ids = [v.id for v in assigned_voucher_query(db, user).all()]
    rows = build_rows(
        db,
        voucher_ids=voucher_ids,
        from_date=from_date,
        to_date=to_date,
        student_ids=student_id,
        internship_ids=internship_id,
        manager_ids=manager_id,
    )
    if format == "csv":
        return Response(
            content=render_csv(rows),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="attendance-{from_date}-{to_date}.csv"'},
        )
    if format == "pdf":
        return Response(
            content=render_pdf(rows, title=f"Attendance report {from_date} to {to_date}"),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="attendance-{from_date}-{to_date}.pdf"'},
        )
    return {"rows": [r.__dict__ for r in rows]}
```

- [ ] **Step 5-6: Pass + commit.**

```bash
git add backend/app/routers/company_dashboard.py backend/tests/test_company_report.py
git commit -m "feat(api): company attendance report (json/csv/pdf)"
```

---

### Task 4.3: Admin report endpoint

**Files:**
- Modify: `backend/app/routers/company_dashboard.py`

- [ ] **Step 1: Test `backend/tests/test_admin_report.py`**

```python
def test_admin_can_filter_by_company(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher, InternshipAttendance
    from app.models.cohort import Cohort
    from datetime import date
    admin = make_user(role="admin", email="adm@example.com")
    o1 = make_user(role="company", email="c1@example.com"); co1 = make_company(owner=o1)
    o2 = make_user(role="company", email="c2@example.com"); co2 = make_company(owner=o2)
    spoc = make_user(role="instructor")
    c = Cohort(name="C", slug="ar"); db.add(c); db.commit(); db.refresh(c)
    i = Internship(title="i", slug="ar", price=0, spoc_user_id=spoc.id, cohort_id=c.id)
    db.add(i); db.commit(); db.refresh(i)
    s1 = make_user(role="student"); s2 = make_user(role="student")
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=s1.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co1.id))
    db.add(InternshipVoucher(code="B", internship_id=i.id, buyer_user_id=s2.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co2.id))
    db.add(InternshipAttendance(internship_id=i.id, user_id=s1.id,
                                attended_at=date(2026,5,5), status="present", hours_worked=8))
    db.add(InternshipAttendance(internship_id=i.id, user_id=s2.id,
                                attended_at=date(2026,5,5), status="present", hours_worked=8))
    db.commit()

    h = auth_headers("adm@example.com")
    r = client.get(
        "/api/v1/admin/reports/attendance",
        params={"from_date": "2026-05-01", "to_date": "2026-05-31",
                "company_id": [co1.id], "format": "csv"},
        headers=h,
    )
    assert r.status_code == 200
    text = r.content.decode()
    assert s1.user_email in text
    assert s2.user_email not in text
```

- [ ] **Step 2-4: Endpoint**

```python
@router.get("/admin/reports/attendance",
            include_in_schema=True,
            tags=["admin-reports"])
def admin_attendance_report(
    from_date: DateType,
    to_date: DateType,
    company_id: Optional[list[int]] = None,
    internship_id: Optional[list[int]] = None,
    student_id: Optional[list[int]] = None,
    format: str = "json",
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    q = db.query(InternshipVoucher).filter(InternshipVoucher.status == "redeemed")
    if company_id:
        q = q.filter(InternshipVoucher.hired_by_company_id.in_(company_id))
    voucher_ids = [v.id for v in q.all()]
    rows = build_rows(
        db, voucher_ids=voucher_ids,
        from_date=from_date, to_date=to_date,
        student_ids=student_id, internship_ids=internship_id,
    )
    if format == "csv":
        return Response(content=render_csv(rows), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="admin-attendance-{from_date}-{to_date}.csv"'})
    if format == "pdf":
        return Response(content=render_pdf(rows, title=f"Admin attendance report {from_date} to {to_date}"),
                        media_type="application/pdf")
    return {"rows": [r.__dict__ for r in rows]}
```

This endpoint must be reachable at `/api/v1/admin/reports/attendance`. Mount it by either (a) re-using the company_dashboard router with a different prefix include, or (b) creating a parallel `admin_reports.py` router and registering it in `main.py`. Option (b) is cleaner — split this endpoint out to `backend/app/routers/admin_reports.py` and `app.include_router(admin_reports.router, prefix="/api/v1/admin", tags=["admin-reports"])`.

- [ ] **Step 5-6: Pass + commit.**

```bash
git add backend/app/routers/admin_reports.py backend/app/main.py backend/tests/test_admin_report.py
git commit -m "feat(api): admin attendance report"
```

---

### Task 4.4: Frontend report pages

**Files:**
- Modify: `frontend/src/pages/company/Reports.tsx`
- Create: `frontend/src/pages/admin/AttendanceReport.tsx`
- Create: `frontend/src/components/reports/ReportFilters.tsx`
- Create: `frontend/src/components/reports/AttendanceCsvPreview.tsx`
- Create: `frontend/src/components/reports/AttendancePdfPreview.tsx`

- [ ] **Step 1: ReportFilters** — controlled component: from/to date, multi-selects for internship/student/manager, View toggle (PDF / CSV), Download buttons. Calls a `onChange` prop with the current filter object. No data fetching itself.

- [ ] **Step 2: AttendanceCsvPreview** — fetches `/api/v1/companies/me/reports/attendance?...&format=json` (or admin equivalent), renders a virtualised `<table>` (use `react-window` if already installed, otherwise simple windowing). Prop `endpoint` so the same component works for both `/companies/me/reports/attendance` and `/admin/reports/attendance`.

- [ ] **Step 3: AttendancePdfPreview** — fetches the same endpoint with `format=pdf` as a `Blob`, creates an `URL.createObjectURL(blob)`, renders `<embed src={url} type="application/pdf" />`. Revoke on unmount.

- [ ] **Step 4: Reports.tsx** (company) — composes the three above, passes `endpoint="/api/v1/companies/me/reports/attendance"`. Two buttons: "Download CSV" / "Download PDF" — both link to the endpoint with the right `format` query param and `download` attribute.

- [ ] **Step 5: AttendanceReport.tsx** (admin) — same composition, `endpoint="/api/v1/admin/reports/attendance"`, plus a Company multi-select filter only shown for admin.

- [ ] **Step 6: Wire admin route** in `App.tsx` → `<Route path="/admin/reports/attendance" element={<AttendanceReport />} />` inside the admin guard.

- [ ] **Step 7: Type-check + commit.**

```bash
docker exec magical-visvesvaraya-2204b2-frontend-1 npm run type-check
git add -A
git commit -m "feat(frontend): attendance reports — preview + download (company + admin)"
```

---

## Phase 5 — Student-side wiring

### Task 5.1: Student work-log endpoints

**Files:**
- Create: `backend/app/routers/student_workspace.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Test `backend/tests/test_student_workspace.py`**

```python
from datetime import date


def test_student_creates_and_lists_log(client, db, make_user, make_company, auth_headers):
    from app.models.internship import Internship, InternshipVoucher
    from app.models.cohort import Cohort
    student = make_user(role="student", email="s@example.com")
    spoc = make_user(role="instructor")
    co = make_company()
    c = Cohort(name="C", slug="sw"); db.add(c); db.commit(); db.refresh(c)
    i = Internship(title="i", slug="sw", price=0, spoc_user_id=spoc.id, cohort_id=c.id)
    db.add(i); db.commit(); db.refresh(i)
    db.add(InternshipVoucher(code="A", internship_id=i.id, buyer_user_id=student.id,
                             amount_paid=0, status="redeemed", hired_by_company_id=co.id))
    db.commit()

    h = auth_headers("s@example.com")
    r = client.post("/api/v1/student/work-logs", headers=h, json={
        "internship_id": i.id,
        "log_date": date.today().isoformat(),
        "content": "did the thing",
    })
    assert r.status_code == 201, r.text
    r = client.get("/api/v1/student/work-logs", headers=h)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
```

- [ ] **Step 2-4: Implement router**

```python
"""Student-facing endpoints for daily-work-done + announcements."""
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.internship import InternshipVoucher
from app.models.company_dashboard import DailyWorkLog, InternshipAnnouncement
from app.services.auth_service import AuthService

router = APIRouter()


def _require_student(user: User = Depends(AuthService.get_current_user)) -> User:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Students only")
    return user


class WorkLogCreate(BaseModel):
    internship_id: int
    log_date: date
    content: str
    attachment_url: Optional[str] = ""


class WorkLogOut(BaseModel):
    id: int
    internship_id: int
    log_date: date
    content: str
    attachment_url: str
    review_status: str
    reviewer_comment: str


@router.post("/work-logs", response_model=WorkLogOut, status_code=201)
def create_log(
    body: WorkLogCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    # student must have a redeemed voucher on that internship
    v = db.query(InternshipVoucher).filter(
        InternshipVoucher.buyer_user_id == user.id,
        InternshipVoucher.internship_id == body.internship_id,
        InternshipVoucher.status == "redeemed",
    ).first()
    if not v:
        raise HTTPException(status_code=403, detail="Not enrolled in that internship")
    existing = db.query(DailyWorkLog).filter(
        DailyWorkLog.student_user_id == user.id,
        DailyWorkLog.log_date == body.log_date,
    ).first()
    if existing:
        existing.content = body.content
        existing.attachment_url = body.attachment_url or ""
        log = existing
    else:
        log = DailyWorkLog(
            student_user_id=user.id,
            internship_id=body.internship_id,
            log_date=body.log_date,
            content=body.content,
            attachment_url=body.attachment_url or "",
        )
        db.add(log)
    db.commit(); db.refresh(log)
    return WorkLogOut(
        id=log.id, internship_id=log.internship_id, log_date=log.log_date,
        content=log.content, attachment_url=log.attachment_url,
        review_status=log.review_status, reviewer_comment=log.reviewer_comment,
    )


@router.get("/work-logs")
def list_my_logs(
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    rows = db.query(DailyWorkLog).filter(
        DailyWorkLog.student_user_id == user.id
    ).order_by(DailyWorkLog.log_date.desc()).all()
    return {"items": [
        WorkLogOut(
            id=r.id, internship_id=r.internship_id, log_date=r.log_date,
            content=r.content, attachment_url=r.attachment_url,
            review_status=r.review_status, reviewer_comment=r.reviewer_comment,
        ) for r in rows
    ]}


@router.get("/announcements")
def list_my_announcements(
    db: Session = Depends(get_db),
    user: User = Depends(_require_student),
):
    # Announcements where student belongs to that company's cohort.
    company_ids = {
        v.hired_by_company_id for v in db.query(InternshipVoucher).filter(
            InternshipVoucher.buyer_user_id == user.id,
            InternshipVoucher.status == "redeemed",
        ).all() if v.hired_by_company_id
    }
    if not company_ids:
        return {"items": []}
    rows = db.query(InternshipAnnouncement).filter(
        InternshipAnnouncement.company_id.in_(company_ids),
        InternshipAnnouncement.deleted_at.is_(None),
    ).order_by(InternshipAnnouncement.created_at.desc()).all()
    return {"items": [
        {"id": a.id, "title": a.title, "body": a.body,
         "internship_id": a.internship_id, "created_at": a.created_at.isoformat()}
        for a in rows
    ]}
```

Mount in `main.py`:
```python
from app.routers import student_workspace
app.include_router(student_workspace.router, prefix="/api/v1/student", tags=["student-workspace"])
```

- [ ] **Step 5-6: Pass + commit.**

```bash
git add backend/app/routers/student_workspace.py backend/app/main.py backend/tests/test_student_workspace.py
git commit -m "feat(api): student work-logs + announcements feed"
```

---

### Task 5.2: Student dashboard widgets

**Files:**
- Modify: existing student dashboard page (find via `frontend/src/pages/dashboard.tsx` or similar)
- Create: `frontend/src/components/student/DailyWorkLogForm.tsx`
- Create: `frontend/src/components/student/AnnouncementsWidget.tsx`

- [ ] **Step 1: DailyWorkLogForm** — small form (textarea + date defaulting to today + internship `<select>` if more than one) → POST `/api/v1/student/work-logs`. Show today's log if it exists with edit affordance.
- [ ] **Step 2: AnnouncementsWidget** — read-only list of `/api/v1/student/announcements`.
- [ ] **Step 3: Drop both into the existing student dashboard page in a sensible spot.**
- [ ] **Step 4: Type-check + commit.**

```bash
docker exec magical-visvesvaraya-2204b2-frontend-1 npm run type-check
git add -A
git commit -m "feat(frontend): student daily work-log form + announcements widget"
```

---

## Phase 5b — Internship request workflow + admin view-as-company

These tasks were added after the initial mockup review.

### Task 5b.1: Internship request schema + endpoints

**Files:**
- Modify: `backend/migrations/company_dashboard_v2_2026_05_05.sql` (or new migration `internship_requests_2026_05_06.sql`)
- Create: `backend/app/models/internship_request.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/routers/company_dashboard.py`
- Modify: `backend/app/routers/internships.py` (admin side)
- Modify: `backend/app/schemas/company_dashboard.py`
- Create: `backend/tests/test_internship_requests.py`

Schema:
```sql
CREATE TABLE internship_requests (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    requested_by INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    intern_count INTEGER NOT NULL DEFAULT 1,
    description TEXT NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|withdrawn
    rejection_reason TEXT NOT NULL DEFAULT '',
    -- when admin approves: store the resulting internship_id so the company
    -- can see "your request became this live internship"
    approved_internship_id INTEGER REFERENCES internships(id),
    reviewed_by INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_internship_requests_company ON internship_requests (company_id);
CREATE INDEX ix_internship_requests_status ON internship_requests (status);
```

Endpoints (TDD-style — tests first then implementation):

| Method + Path | Purpose | Roles |
|---|---|---|
| `POST /api/v1/companies/me/internship-requests` | Submit a new request (status=pending) | company owner |
| `GET /api/v1/companies/me/internship-requests` | List own requests with status | company, company_manager |
| `DELETE /api/v1/companies/me/internship-requests/{id}` | Withdraw a pending request | company owner |
| `GET /api/v1/admin/internship-requests?status=...` | Admin queue | admin |
| `POST /api/v1/admin/internship-requests/{id}/approve` body `{spoc_user_id, price, slug?}` | Creates an `Internship` row + sets request.status=approved + sets approved_internship_id | admin |
| `POST /api/v1/admin/internship-requests/{id}/reject` body `{reason}` | Sets request.status=rejected + rejection_reason | admin |

Behaviour notes:
- Approval **creates the Internship row** with `created_by=request.requested_by` so audit trail tracks the requester. Admin selects the SPOC user (existing user with role=`instructor` or `admin`) and the price.
- Approval is idempotent: if the request is already `approved`, return 409.
- Withdraw is only legal when status=`pending`. Otherwise 400.
- A rejected request can be reopened by re-submitting (creates a new request row referencing the old via a free-text "previous_request_id" column? — out of scope for v1; just allow new submissions).
- Email notification on approve/reject sent to `company.contact_email` (re-use `EmailService` pattern from manager invite).

Frontend:
- Replace the existing mockup `Request internship` form to call `companyDashboardAPI.requestInternship(...)` and `useInternshipRequests()` hook.
- Live cards come from `useCompanyInternships()` (Task 2.4) — unchanged.
- Pending/rejected cards come from `useInternshipRequests()` — new hook.

Admin UI (separate task, see 5b.2):
- New `/admin/internship-requests` page — list with status filter, accept (modal: SPOC + price), reject (modal: reason textarea).

---

### Task 5b.2: Admin internship-request review UI

**Files:**
- Create: `frontend/src/pages/admin/internship-requests.tsx`
- Modify: `frontend/src/App.tsx` — add route under `AdminLayout`
- Modify: `frontend/src/components/layout/admin/admin-layout.tsx` — add nav item under Internships

Components:
- Table with columns: Company · Title · Dates · Intern count · Submitted · Status · Actions.
- Filter chips: All / Pending / Approved / Rejected.
- Row click → drawer showing full description.
- **Approve** button → modal with SPOC select (load instructors from `/api/v1/users?role=instructor`), price input, slug input (auto-generated from title), submit → POST approve.
- **Reject** button → modal with reason textarea (required min 10 chars), submit → POST reject.
- Toast on success, refresh list.

Tests: add 1-2 vitest component tests verifying the filter behaviour (skip in v1 if frontend tests are still infra-only).

---

### Task 5b.3: Admin "view as company" impersonation

**Background:** the codebase already has admin-as-instructor impersonation (commit `9b08f2f feat(admin): view-as-instructor impersonation with audit log`). We extend the same pattern to companies.

**Files:**
- Modify: `backend/app/routers/admin.py` (or wherever `view-as-instructor` lives) — add a parallel `view-as-company` endpoint
- Modify: `backend/app/services/auth_service.py` — already supports `impersonation_access` token type (verified earlier). No change.
- Modify: `frontend/src/pages/admin/companies.tsx` — make the company name a button that triggers impersonation
- Modify: `frontend/src/components/admin/ImpersonationBanner.tsx` — banner already exists for instructor impersonation; extend the message to handle the company case.

Backend endpoint:

```python
@router.post("/admin/impersonate/company/{company_id}")
def impersonate_company(
    company_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(AuthService.require_admin),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    owner = db.query(User).filter(User.id == company.owner_user_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Company owner not found")

    token = create_access_token(
        data={"sub": str(owner.id), "type": "impersonation_access",
              "impersonated_by": admin.id},
        expires_delta=timedelta(minutes=30),
    )
    # Audit log entry (re-use existing AdminImpersonationLog table)
    log = AdminImpersonationLog(
        admin_id=admin.id, target_user_id=owner.id,
        target_role="company", reason=f"View as company {company.name}",
    )
    db.add(log)
    db.commit()
    return {"access_token": token, "redirect": "/company/dashboard"}
```

Frontend (admin companies page):
- Each row's company-name cell becomes a button → calls `POST /admin/impersonate/company/{id}` → stores returned token in auth store with `impersonatedBy=admin.id` flag → navigates to `/company/dashboard`.

Frontend (impersonation banner):
- Existing `ImpersonationBanner` reads `user._impersonated_by` from the JWT; when set, renders a sticky banner: *"Viewing as Demo Company Pvt Ltd — Exit impersonation"*. The Exit button discards the impersonation token, restores admin's normal token, and navigates back to `/admin/dashboard`.

Tests:
- `backend/tests/test_impersonate_company.py`:
  1. admin POSTs `/admin/impersonate/company/{id}` → 200 with token
  2. token grants access to `/companies/me/students` and returns the right company's students
  3. non-admin gets 403
  4. nonexistent company returns 404
  5. AdminImpersonationLog row written

Out of scope:
- Chained impersonation (admin → company → student) — already blocked by the `_impersonated_by` check in `get_current_user`.
- Write-back protection — the impersonating admin can perform any action the company can. UI should make it obvious via the banner.

---

## Phase 6 — End-to-end smoke test

### Task 6.1: Manual smoke through nginx

- [ ] **Step 1: Run all tests.**
```bash
docker exec magical-visvesvaraya-2204b2-backend-1 pytest -q
```
Expected: all tests in this plan pass.

- [ ] **Step 2: Apply migration to running DB if not already.**
- [ ] **Step 3: Re-seed the demo company** (the `seed_company.py` script).
- [ ] **Step 4: Log in as `company@example.com`.** Click through each tab — Overview / Students / Internships / Attendance / Announcements / Reports. Mark attendance for one student. Download CSV. Open PDF preview.
- [ ] **Step 5: Invite a manager**, complete setup via the returned token, log in as the manager — confirm they see only their reportees.
- [ ] **Step 6: Log in as a seeded student** and submit a daily work-log. Confirm the company sees it under work-logs and can approve it.
- [ ] **Step 7: Log in as admin and run `/admin/reports/attendance`** — confirm filtering by company narrows results.

If any step fails, file a follow-up task to fix and re-verify.

---

## Self-review notes

- All 8 endpoints from the spec's API table have a task (1.5 for managers, 2.2 overview, 2.3 students × 3, 2.4 internships × 2, 2.5 attendance × 2, 2.6 work-logs × 2, 2.7 announcements × 3, 2.8 review, 4.2 company report, 4.3 admin report, 5.1 student endpoints).
- Permission matrix from spec section 12 is enforced by `require_company_or_manager` + `require_owner` calls inside each endpoint.
- `/uploads/work-logs/{user_id}/` storage from spec open-question #2 is **deferred** — Phase 5 returns a string `attachment_url` field but no upload helper. Add a follow-up plan for chunked upload integration if the user wants attachments before launch.
- Email delivery for announcements (spec open-question #3) is **deferred** — announcements are in-app only in this plan. Email fan-out is a one-task follow-up using the existing EmailService.
- Test infrastructure (Phase 0) creates a fresh sqlite DB per test, which means the test client's `get_db` dependency override must use the same session factory — `conftest.py` handles this.
- Frontend Vitest tests are **not** authored in this plan (the plan only sets up the infra). Component tests are a Phase 7 follow-up. Type-check + manual click-through (Phase 6) is the verification gate for the frontend.
