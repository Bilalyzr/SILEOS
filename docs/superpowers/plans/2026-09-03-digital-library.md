# Digital Library & Suggestive Buying Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.
> Dispatches point implementers at THIS file's task section + the spec
> (docs/superpowers/specs/2026-09-03-digital-library-design.md) — the spec's numbered
> sections are the requirements; task sections below add file maps, exact code, and
> sequencing. Both BINDING.

**Goal:** A separate "Library" store where students buy ebooks/guides/lecture notes as
one-time Razorpay purchases riding the hardened triple-redundant payment stack (browser
`/verify` + webhook inbox + reconciliation sweeper — extended exactly the way bundles were),
with paid files streamed only through authenticated endpoints (never nginx-static), and
concept-linked "suggested reading" surfaced inside lessons and after failed quiz attempts.
Branch `digital-library` (worktree `.worktrees/digital-library`, forked from
`revenue-platform` @ 00c267c).

**Architecture:** Two new tables (`ebooks`, `ebook_grants` — migration `0005_digital_library`,
guarded like 0003/0004) plus `orders.ebook_id` and `order_items.ebook_id` (with
`order_items.course_id` relaxed to nullable — it is `NOT NULL` today and an ebook line has no
course). One new router `app/routers/library.py` at `/api/v1/library` carries the public store
(anon-edge-cacheable via `cache_headers.apply_public_cache`), the grant-gated
download/sample streaming endpoints (files under `backend/ebooks/{owner_id}/{uuid}.{ext}`,
mirroring the company-invoicing private-PDF pattern), the owner-scoped instructor CRUD
(games.py ownership conventions), the free-claim flow, and the suggestions endpoint.
`create-order`/`verify` grow an `ebook_id` branch (exactly-one-of contract extended);
`fulfillment_service.fulfill_ebook_purchase` (idempotent on `Payment.gateway_payment_id`,
template: `fulfill_bundle_purchase`) is converged on by all three payment paths via an
`ebook_id` order-notes snapshot. Frontend: public store + detail pages, My Library, an
instructor manager, and two advisory suggestion surfaces (lesson page, failed quiz results).

**Tech Stack:** existing only — FastAPI + SQLAlchemy + Alembic (backend), React 18 + TS +
Vite + Tailwind + React Query (suggestions caching), Vitest, pytest, reportlab (seed PDFs —
already in `backend/requirements.txt` as `reportlab==4.0.7`). **No new dependencies.**

## Global Constraints

All BINDING; every task re-checks the ones it touches.

1. **Price units (verified finding):** courses store rupees
   (`Course.course_price = Numeric(10,2)`, e.g. `500.00` = ₹500) and bundles store rupees
   (`Bundle.bundle_price = Numeric(10,2)`); paise exist ONLY at the Razorpay boundary via
   `max(int(round(price * 100)), 100)` (payments.py, every branch). Ebooks therefore store
   **whole rupees**: `price_inr = Column(Integer)` (spec's INT), `discount_price_inr`
   nullable Integer, converted to paise only inside `_create_ebook_order` /
   `_verify_ebook_payment` with the same `max(int(round(p * 100)), 100)` clamp.
   `Order.total_amount` / `OrderItem.total` / `Payment.amount` are written in rupees
   (`amount_paise / 100.0`), exactly like courses/bundles.
2. **File caps (spec §3, verbatim):** extension allowlist `{pdf, epub}`; magic-byte sniff —
   PDF starts `%PDF-`, EPUB = zip magic `PK\x03\x04` + a `mimetype` zip entry equal to
   `application/epub+zip`; per-file size cap **200MB**; per-owner total cap **5GB**
   (computed from on-disk usage of `backend/ebooks/{owner_id}/`); filename NEVER trusted
   (uuid names); normalize-and-reassert every resolved path inside the ebooks root. Files
   live under `backend/ebooks/` — **NOT** `uploads/` (nginx serves that publicly). Samples
   are PDF only.
3. **Category enum (spec §1, verbatim):** `category VARCHAR(16)` ∈
   {`book`, `guide`, `lecture_notes`} — enforced at the API layer (no DB CHECK, matching
   `Game.template`'s precedent). `concept_tags` = JSON list of ≤10 strings, each ≤50 chars.
   `discount_price_inr` must be `< price_inr` when set. `description` ≤5000, `title` ≤200.
4. **Payment contract extension:** `CreateOrderRequest`/`VerifyPaymentRequest` accept
   exactly ONE of `course_id`/`bundle_id`/`invoice_id`/`ebook_id` (the existing
   `_exactly_one_target` model_validator grows one element — 422 otherwise). **Coupons are
   REJECTED on ebooks** (400, mirroring bundles/invoices). Draft ebooks cannot be ordered
   (400 at create-order). Price is snapshotted into the order notes
   (`ebook_price_inr`, rupees) at creation; verify checks the captured amount against the
   SNAPSHOT, not the live price.
5. **Grants:** `ebook_grants` has `UNIQUE(ebook_id, user_id)`
   (`uq_ebook_grants_ebook_user`) — the DB-level backstop for the idempotent get-or-create
   in `grant_ebook`. `source` ∈ {`purchase`, `admin`, `owner`}; free claims are
   `source="purchase"` with `order_id NULL` (spec §2 verbatim). Owner/admin read their own
   ebooks WITHOUT grants. Fulfillment never touches enrollments.
6. **Delete/unpublish rules:** `DELETE /library/{id}` → **409 while any grant exists**
   (sold content is never deleted). Unpublish is allowed anytime and only hides the ebook
   from the store — **already-granted students keep download access** (the download gate
   checks the grant, not the status).
7. **Anon-only edge caching:** `GET /library` and `GET /library/{slug}` call
   `cache_headers.apply_public_cache` (WITH its anon guard — authed responses get
   `private, no-store`; `Vary: Authorization` always). The detail's `owned` flag appears
   only for authed users, whose responses the helper already makes uncacheable. NEVER wire
   the helper into `/me`, `/mine`, `/suggestions`, `/download`, `/sample`, or `/sales`.
8. **noSlashEndpoints:** backend runs `redirect_slashes=False`; `'/library'` MUST be added
   to `noSlashEndpoints` in `frontend/src/api/axios.ts` (the gamification-404 lesson).
   Every library route is declared WITHOUT a trailing slash (create is `@router.post("")`),
   and fixed-path routes (`/mine`, `/me`, `/suggestions`) are declared BEFORE `/{slug}`.
9. **Private streaming:** download/sample are `FileResponse` streams from the app (mirroring
   `company_billing.get_invoice_pdf`) with `Content-Disposition: attachment` (FileResponse's
   `filename=`) and the correct media type — NEVER a redirect to a static path, never a
   response containing `file_path`/`sample_path`.
10. **XP:** none. No `award()` calls anywhere in this feature (spec §6: purchases are money,
    not learning). No badge.
11. **Baseline stays green:** backend `./.venv/Scripts/python -m pytest tests/ -v` (from the
    worktree's `backend/`, shared venv
    `C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe`)
    — zero NEW failures vs the 949 passed / 4 skipped baseline. Frontend: `npx vitest run`
    green; `npm run type-check` zero new errors.

**Test commands used throughout:**
- Backend (from `backend/`): `./.venv/Scripts/python -m pytest tests/test_library.py -v`
  (full suite: `./.venv/Scripts/python -m pytest tests/ -v`)
- Frontend (from `frontend/`): `npx vitest run <path>`

**Resolved spec ambiguities (documented here, encoded in the tasks):**
- *Price unit/type*: rupees confirmed (Global Constraint 1). `price_inr` is a whole-rupee
  `Integer` per the spec's "INT"; courses use `Numeric(10,2)` but the UNIT (rupees) is what
  "MATCH EXACTLY" binds — whole rupees is a lawful subset and every gateway conversion is
  identical.
- *`OrderItem.course_id` is `NOT NULL` today*: an ebook OrderItem has no course, so
  migration 0005 relaxes `order_items.course_id` to nullable and adds
  `order_items.ebook_id` (nullable FK). Ebook lines: `order_item_type="ebook_item"`,
  `course_id=NULL`, `ebook_id` set. (The alternative — skipping OrderItem like membership
  renewals do — violates spec §2's "one OrderItem for the ebook".)
- *Sample auth*: spec §3 says samples are served "through the authenticated endpoint but
  grant-free" while §7's test matrix says "sample public-when-published". Resolved: the
  sample endpoint is app-streamed (never static) with OPTIONAL auth — published samples
  need no login (anon 200), drafts 404 to everyone but owner/admin. "Authenticated
  endpoint" is read as "app-served endpoint", which §3's own sentence ("semi-public by
  design") supports.
- *"Free" means effective price 0*: the claim gate and the create-order free-rejection both
  use `effective_price_inr` (= `discount_price_inr` if set else `price_inr`), so a
  discount-to-zero ebook is claimable and never Razorpay-ordered.
- *Verify amount check*: against the `ebook_price_inr` order-notes snapshot (spec §2 says
  price is snapshotted at order creation); falls back to the live effective price only when
  the note is missing/corrupt (hand-built order).
- *Range requests*: spec allows full-file streaming at launch; we use Starlette
  `FileResponse` (same as invoice PDFs) and defer explicit Range handling.
- *Claim idempotency*: re-claiming an already-granted free ebook returns 200 with
  `created: false` (get-or-create), not an error — mirrors fulfillment's replay posture.
- *Slug*: generated like course slugs — `<title-slug>-<id>` via
  `course_service._slugify_title` after flush, falling back to `ebook-<id>` for pure-Tamil
  titles (NEVER empty, always unique because the id is embedded).
- *Suggestions tag matching*: "concept_tags ∩ course title/category words" is computed on
  TOKENIZED words (regex `[a-z0-9]+`, lowercased) so the multiword tag "data structures"
  matches a course titled "Data Structures in Python". Course-linked ebooks always rank
  before tag matches.
- *Ebook deleted before fulfillment*: delete is 409-blocked once any grant exists, but a
  capture can race a pre-first-sale delete. Mirroring the bundle no-resolvable-courses
  path: Order + Payment are still written (the capture stays reconcilable), an alert email
  fires, and no grant is created.
- *Authenticated downloads in the browser*: the JWT lives in axios headers, so `/download`
  cannot be a bare `<a href>` — the frontend fetches a blob and hands the browser an object
  URL. Samples (anon-public) remain plain links.
- *Sales panel money*: `gross` = `SUM(OrderItem.total)` over the ebook's `ebook_item` rows
  (free claims contribute 0 because they have no order); `count` = grant count;
  `last_sale_at` = newest `granted_at`; buyers listed by `display_name` ONLY (spec §4: no
  emails — same rule as the games results endpoint).

---

## Task 1: Models + migration 0005 (+ model tests)

**Files:**
- Create: `backend/app/models/ebook.py`
- Create: `backend/alembic/versions/0005_digital_library.py`
- Modify: `backend/app/models/payment.py` (Order: add `ebook_id`; OrderItem: add `ebook_id`,
  relax `course_id` to `nullable=True`)
- Modify: `backend/app/models/__init__.py` (import the new module so `Base.metadata` sees it)
- Test: `backend/tests/test_library.py` (new — this file grows across Tasks 1–7)

**Interfaces:**
- Produces: `app.models.ebook.Ebook`, `app.models.ebook.EbookGrant`,
  `app.models.ebook.EBOOK_CATEGORIES`, `app.models.ebook.effective_price_inr(ebook) -> int`,
  `Order.ebook_id`, `OrderItem.ebook_id`, nullable `OrderItem.course_id`
- Consumes: `app.core.database.Base`, existing `users`/`courses`/`orders` tables

**Steps:**

- [ ] Write failing model tests at the top of `backend/tests/test_library.py`:

```python
"""Digital Library backend (docs/superpowers/specs/2026-09-03-digital-library-design.md).

Grows across plan Tasks 1-7: models/migration, upload hardening, instructor
CRUD + ownership, public store + download gates, payment extension,
webhook/sweeper convergence + free claim, suggestions.
SQLite in-memory per repo pattern (see conftest.py).
"""
import io
import zipfile

import pytest

from app.models.course import Course
from app.models.ebook import EBOOK_CATEGORIES, Ebook, EbookGrant, effective_price_inr
from app.models.payment import Order, OrderItem, Payment
from app.models.user import User


# ----- factories --------------------------------------------------------------

def _make_approved_instructor(db, make_user, email):
    from app.models.user import InstructorProfile
    instructor = make_user(role="instructor", email=email)
    profile = db.query(InstructorProfile).filter_by(user_id=instructor.id).first()
    if profile:
        profile.is_approved = True
    else:
        db.add(InstructorProfile(user_id=instructor.id, is_approved=True))
    db.commit()
    return instructor


def _make_ebook(db, owner, *, title="Demo Ebook", category="book", price=199,
                discount=None, status="draft", file_path=None, sample_path=None,
                tags=None, course_id=None):
    ebook = Ebook(
        owner_id=owner.id, title=title, slug="pending", category=category,
        price_inr=price, discount_price_inr=discount, status=status,
        file_path=file_path, sample_path=sample_path,
        file_size_bytes=1024 if file_path else 0,
        concept_tags=tags or [], course_id=course_id,
    )
    db.add(ebook)
    db.flush()
    ebook.slug = f"{title.lower().replace(' ', '-')}-{ebook.id}"
    db.commit()
    db.refresh(ebook)
    return ebook


def _grant(db, ebook, user, *, order_id=None, source="purchase"):
    g = EbookGrant(ebook_id=ebook.id, user_id=user.id, order_id=order_id, source=source)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


# Tiny REAL file payloads for upload tests (magic bytes must be genuine).
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF\n"


def _epub_bytes(mimetype=b"application/epub+zip"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", mimetype)
        zf.writestr("META-INF/container.xml", "<container/>")
    return buf.getvalue()


# ============================================================================
# Task 1: models + migration columns
# ============================================================================


class TestEbookModels:
    def test_ebook_defaults_and_effective_price(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "lib-owner@example.com")
        ebook = _make_ebook(db, owner, price=499)
        assert ebook.status == "draft"
        assert ebook.category in EBOOK_CATEGORIES
        assert ebook.concept_tags == []
        assert effective_price_inr(ebook) == 499
        ebook.discount_price_inr = 299
        assert effective_price_inr(ebook) == 299

    def test_grant_unique_per_user(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "lib-owner2@example.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        _grant(db, ebook, student)
        from sqlalchemy.exc import IntegrityError
        db.add(EbookGrant(ebook_id=ebook.id, user_id=student.id, source="admin"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_order_and_order_item_ebook_columns(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "lib-owner3@example.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        from app.models.payment import OrderStatus
        order = Order(user_id=student.id, ebook_id=ebook.id, order_key="EBK_TEST1",
                      order_status=OrderStatus.COMPLETED, total_amount=199)
        db.add(order)
        db.flush()
        # course_id is now nullable: an ebook line has no course.
        db.add(OrderItem(order_id=order.id, course_id=None, ebook_id=ebook.id,
                         order_item_name=ebook.title, order_item_type="ebook_item",
                         quantity=1, subtotal=199, total=199))
        db.commit()
        item = db.query(OrderItem).filter(OrderItem.ebook_id == ebook.id).one()
        assert item.course_id is None
        assert item.order_item_type == "ebook_item"


class TestMigration0005:
    def test_upgrade_creates_tables_and_columns(self, tmp_path):
        """Run 0005's upgrade() against a bare SQLite file DB that already has
        the FK-target tables (mirrors test_games.py's TestMigration0004)."""
        import sqlalchemy as sa
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        import importlib.util
        from pathlib import Path

        engine = sa.create_engine(f"sqlite:///{tmp_path / 'mig.db'}")
        with engine.begin() as conn:
            conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text("CREATE TABLE courses (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text("CREATE TABLE orders (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text(
                "CREATE TABLE order_items (id INTEGER PRIMARY KEY, "
                "order_id INTEGER NOT NULL, course_id INTEGER NOT NULL)"))
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0005_digital_library.py"
        spec = importlib.util.spec_from_file_location("mig_0005", path)
        mig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig)

        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                mig.upgrade()
            conn.commit()

        insp = sa.inspect(engine)
        assert insp.has_table("ebooks")
        assert insp.has_table("ebook_grants")
        ebook_cols = {c["name"] for c in insp.get_columns("ebooks")}
        assert {"id", "owner_id", "title", "slug", "description", "category",
                "price_inr", "discount_price_inr", "cover_image", "file_path",
                "file_size_bytes", "page_count", "sample_path", "concept_tags",
                "course_id", "status", "created_at", "updated_at"} <= ebook_cols
        grant_cols = {c["name"] for c in insp.get_columns("ebook_grants")}
        assert {"id", "ebook_id", "user_id", "order_id", "source", "granted_at"} <= grant_cols
        order_cols = {c["name"] for c in insp.get_columns("orders")}
        assert "ebook_id" in order_cols
        item_cols = {c["name"]: c for c in insp.get_columns("order_items")}
        assert "ebook_id" in item_cols
        assert item_cols["course_id"]["nullable"] is True  # relaxed by 0005
        uniques = {u["name"] for u in insp.get_unique_constraints("ebook_grants")}
        assert "uq_ebook_grants_ebook_user" in uniques
```

- [ ] Run to see fail: `./.venv/Scripts/python -m pytest tests/test_library.py -v`
      (ImportError: `app.models.ebook` does not exist).
- [ ] Implement `backend/app/models/ebook.py`:

```python
"""Digital Library models (spec 2026-09-03-digital-library §1).

`Ebook` is one sellable digital product (PDF/EPUB). Store metadata is public
once published; `file_path` is PRIVATE — a path relative to backend/ebooks/
(NOT uploads/, which nginx serves publicly) that only the authenticated
download endpoint may resolve, and it must NEVER appear in an API response.
Prices are whole RUPEES (`price_inr`), matching the unit courses/bundles use
— paise exist only at the Razorpay boundary (max(int(round(p * 100)), 100)).

`EbookGrant` is one user's access to one ebook. UNIQUE(ebook_id, user_id)
backs the idempotent get-or-create in fulfillment_service.grant_ebook: a
purchase, a free claim, and an admin/owner grant all converge on one row.
Grants are for students — owner/admin read their own ebooks without grants.
Unpublishing hides an ebook from the store but NEVER touches grants
(spec §4: already-granted students keep download access), and deletion is
blocked with 409 while any grant exists (sold content is never deleted).
"""
from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.sql import func

from app.core.database import Base

# Enforced at the API layer (VARCHAR(16), no DB CHECK) — same precedent as
# Game.template / lesson_content_type. Displayed as Books / Guides /
# Lecture Notes tabs in the store.
EBOOK_CATEGORIES = ("book", "guide", "lecture_notes")


def effective_price_inr(ebook: "Ebook") -> int:
    """The rupee amount a buyer actually pays: the discount price when set
    (validated < price at the API layer), else the list price. Lives here so
    payments/fulfillment can import it without touching the library router
    (no import cycles). effective 0 == free == claimable, never orderable."""
    if ebook.discount_price_inr is not None:
        return int(ebook.discount_price_inr)
    return int(ebook.price_inr or 0)


class Ebook(Base):
    __tablename__ = "ebooks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    category = Column(String(16), nullable=False)  # book | guide | lecture_notes

    price_inr = Column(Integer, nullable=False, default=0)  # whole rupees
    discount_price_inr = Column(Integer, nullable=True)     # < price_inr when set

    cover_image = Column(String(500), default="")    # public uploads flow — images are fine public
    file_path = Column(String(500), nullable=True)   # PRIVATE; relative to backend/ebooks/
    file_size_bytes = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=True)
    sample_path = Column(String(500), nullable=True)  # grant-free preview PDF (semi-public)

    concept_tags = Column(JSON, nullable=False, default=list)  # <=10 strings, each <=50 chars
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)

    status = Column(String(16), nullable=False, default="draft")  # draft | published

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Ebook(id={self.id}, slug={self.slug}, status={self.status})>"


class EbookGrant(Base):
    """One user's access to one ebook. order_id NULL = free claim or
    admin/owner hand-grant; set = paid purchase (the money trail)."""
    __tablename__ = "ebook_grants"
    __table_args__ = (
        UniqueConstraint("ebook_id", "user_id", name="uq_ebook_grants_ebook_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ebook_id = Column(Integer, ForeignKey("ebooks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    source = Column(String(16), nullable=False, default="purchase")  # purchase | admin | owner
    granted_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EbookGrant(ebook_id={self.ebook_id}, user_id={self.user_id}, source={self.source})>"
```

- [ ] Modify `backend/app/models/payment.py` — on `Order`, directly under the existing
      `bundle_id` column:

```python
    # Set by ebook fulfillment; NULL for course/bundle/subscription orders.
    ebook_id = Column(Integer, ForeignKey("ebooks.id"), nullable=True, index=True)
```

  and on `OrderItem`, replace the `course_id` line and add `ebook_id` under it:

```python
    # course_id was NOT NULL until migration 0005: an ebook line item has no
    # course, so exactly one of course_id / ebook_id is set per row (enforced
    # by the writers in fulfillment_service, not a DB constraint).
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    ebook_id = Column(Integer, ForeignKey("ebooks.id"), nullable=True, index=True)
```

- [ ] Register the module in `backend/app/models/__init__.py` following its existing import
      style (read the file first; add `from app.models.ebook import Ebook, EbookGrant  # noqa`
      exactly how `bundle`/`game` are imported there).
- [ ] Implement `backend/alembic/versions/0005_digital_library.py`:

```python
"""digital library — ebooks, ebook_grants, orders.ebook_id,
order_items.ebook_id, order_items.course_id -> nullable

Guarded like 0002/0003/0004: init_db()'s create_all may already have created
these tables/columns via the SQLAlchemy models before Alembic runs, so every
operation checks has_table/_has_column first. FK column adds on SQLite use
batch_alter_table (ADD COLUMN can't attach an FK there — the FK must be
NAMED in the batch path), and the course_id nullability relax also needs
batch mode on SQLite (ALTER COLUMN is unsupported).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table_name: str, column_name: str) -> bool:
    if not insp.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in insp.get_columns(table_name))


def _course_id_nullable(insp) -> bool:
    for col in insp.get_columns("order_items"):
        if col["name"] == "course_id":
            return bool(col["nullable"])
    return True


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ---- ebooks (new table) ----
    if not insp.has_table("ebooks"):
        op.create_table(
            "ebooks",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(255), nullable=False, unique=True),
            sa.Column("description", sa.Text(), server_default=""),
            sa.Column("category", sa.String(16), nullable=False),
            sa.Column("price_inr", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("discount_price_inr", sa.Integer(), nullable=True),
            sa.Column("cover_image", sa.String(500), server_default=""),
            sa.Column("file_path", sa.String(500), nullable=True),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("page_count", sa.Integer(), nullable=True),
            sa.Column("sample_path", sa.String(500), nullable=True),
            sa.Column("concept_tags", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_ebooks_owner_id", "ebooks", ["owner_id"])
        op.create_index("ix_ebooks_slug", "ebooks", ["slug"])
        op.create_index("ix_ebooks_course_id", "ebooks", ["course_id"])
    else:
        print("[0005_digital_library] ebooks already exists — skipping create.")

    # ---- ebook_grants (new table) ----
    insp = sa.inspect(bind)
    if not insp.has_table("ebook_grants") and insp.has_table("ebooks"):
        op.create_table(
            "ebook_grants",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("ebook_id", sa.Integer(), sa.ForeignKey("ebooks.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
            sa.Column("source", sa.String(16), nullable=False, server_default="purchase"),
            sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("ebook_id", "user_id", name="uq_ebook_grants_ebook_user"),
        )
        op.create_index("ix_ebook_grants_ebook_id", "ebook_grants", ["ebook_id"])
        op.create_index("ix_ebook_grants_user_id", "ebook_grants", ["user_id"])
    elif insp.has_table("ebook_grants"):
        print("[0005_digital_library] ebook_grants already exists — skipping create.")
    else:
        print("[0005_digital_library] ebooks missing — skipping ebook_grants create (FK dependency).")

    # ---- orders.ebook_id ----
    insp = sa.inspect(bind)
    if insp.has_table("orders") and insp.has_table("ebooks") \
            and not _has_column(insp, "orders", "ebook_id"):
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("orders") as batch_op:
                batch_op.add_column(sa.Column("ebook_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key("fk_orders_ebook_id", "ebooks", ["ebook_id"], ["id"])
        else:
            op.add_column("orders", sa.Column("ebook_id", sa.Integer(),
                                              sa.ForeignKey("ebooks.id"), nullable=True))
        op.create_index("ix_orders_ebook_id", "orders", ["ebook_id"])

    # ---- order_items.ebook_id + course_id nullability relax ----
    insp = sa.inspect(bind)
    if insp.has_table("order_items"):
        add_ebook_id = insp.has_table("ebooks") and not _has_column(insp, "order_items", "ebook_id")
        relax_course_id = not _course_id_nullable(insp)
        if bind.dialect.name == "sqlite":
            if add_ebook_id or relax_course_id:
                with op.batch_alter_table("order_items") as batch_op:
                    if add_ebook_id:
                        batch_op.add_column(sa.Column("ebook_id", sa.Integer(), nullable=True))
                        batch_op.create_foreign_key(
                            "fk_order_items_ebook_id", "ebooks", ["ebook_id"], ["id"])
                    if relax_course_id:
                        batch_op.alter_column("course_id", existing_type=sa.Integer(),
                                              nullable=True)
        else:
            if add_ebook_id:
                op.add_column("order_items", sa.Column("ebook_id", sa.Integer(),
                                                       sa.ForeignKey("ebooks.id"), nullable=True))
            if relax_course_id:
                op.alter_column("order_items", "course_id",
                                existing_type=sa.Integer(), nullable=True)
        if add_ebook_id:
            op.create_index("ix_order_items_ebook_id", "order_items", ["ebook_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Reverse order: drop FK columns first, then the tables they reference.
    # course_id is deliberately NOT restored to NOT NULL — ebook order rows
    # with course_id NULL may exist and a data-destroying downgrade is worse
    # than a laxer column.
    if insp.has_table("order_items") and _has_column(insp, "order_items", "ebook_id"):
        with op.batch_alter_table("order_items") as batch_op:
            batch_op.drop_column("ebook_id")
    insp = sa.inspect(bind)
    if insp.has_table("orders") and _has_column(insp, "orders", "ebook_id"):
        with op.batch_alter_table("orders") as batch_op:
            batch_op.drop_column("ebook_id")
    insp = sa.inspect(bind)
    if insp.has_table("ebook_grants"):
        op.drop_table("ebook_grants")
    if insp.has_table("ebooks"):
        op.drop_table("ebooks")
```

- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_library.py -v`
- [ ] Run full backend suite; zero new failures (the relaxed `course_id` must not break any
      existing order test): `./.venv/Scripts/python -m pytest tests/ -v`
- [ ] Commit: `feat(library): Ebook/EbookGrant models, orders+order_items ebook columns, migration 0005`

---

## Task 2: Private storage service + upload hardening tests

**Files:**
- Create: `backend/app/services/library_storage.py`
- Test: `backend/tests/test_library.py` (append `TestUploadHardening` + the `ebooks_root`
  fixture)

**Interfaces:**
- Produces:
  - `EBOOKS_ROOT: Path` (= `Path("ebooks")`, resolved against the backend working dir —
    same convention as `backend/invoices/`)
  - `ALLOWED_EXTENSIONS = {"pdf", "epub"}`, `MAX_FILE_BYTES = 200MB`,
    `MAX_OWNER_TOTAL_BYTES = 5GB`, `MEDIA_TYPES: dict[str, str]`
  - `save_ebook_file(owner_id, upload, allowed=None) -> tuple[str, int]` (relative path, size)
  - `resolve_ebook_path(rel_path) -> Path` (normalize-and-reassert, 404 outside root)
  - `delete_stored_file(rel_path) -> None` (best-effort)
- Consumes: `fastapi.UploadFile`, stdlib `zipfile`/`uuid`/`pathlib`

**Steps:**

- [ ] Add the fixture + failing tests to `backend/tests/test_library.py`:

```python
# ============================================================================
# Task 2: upload hardening
# ============================================================================

from fastapi import HTTPException, UploadFile  # noqa: E402


@pytest.fixture
def ebooks_root(tmp_path, monkeypatch):
    """Point the storage service (and everything importing it as a MODULE)
    at a throwaway root. Routers must use `from app.services import
    library_storage` + attribute access so this monkeypatch reaches them."""
    from app.services import library_storage
    root = tmp_path / "ebooks"
    monkeypatch.setattr(library_storage, "EBOOKS_ROOT", root)
    return root


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data))


class TestUploadHardening:
    def test_valid_pdf_saved_with_uuid_name(self, ebooks_root):
        from app.services import library_storage
        rel, size = library_storage.save_ebook_file(7, _upload("My Notes.pdf", PDF_BYTES))
        assert size == len(PDF_BYTES)
        assert rel.startswith("7/")
        assert "My Notes" not in rel and "my notes" not in rel  # filename never trusted
        assert rel.endswith(".pdf")
        assert (ebooks_root / rel).is_file()

    def test_valid_epub_saved(self, ebooks_root):
        from app.services import library_storage
        rel, _ = library_storage.save_ebook_file(7, _upload("book.epub", _epub_bytes()))
        assert rel.endswith(".epub")

    @pytest.mark.parametrize("name,data", [
        ("notes.txt", PDF_BYTES),                        # bad extension
        ("noext", PDF_BYTES),                            # no extension
        ("evil.pdf.exe", PDF_BYTES),                     # ext taken from LAST segment
        ("fake.pdf", b"MZ\x90\x00 not a pdf at all"),   # wrong magic bytes
        ("fake.epub", PDF_BYTES),                        # pdf bytes in .epub clothing
        ("nomime.epub", b"PK\x03\x04broken"),            # zip magic, not a real zip
        ("empty.pdf", b""),                              # empty
    ])
    def test_rejected_uploads(self, ebooks_root, name, data):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload(name, data))
        assert exc.value.status_code in (400, 413)
        # nothing durable left behind (no .part or final files)
        leftovers = list(ebooks_root.rglob("*")) if ebooks_root.exists() else []
        assert not [p for p in leftovers if p.is_file()]

    def test_epub_wrong_mimetype_entry_rejected(self, ebooks_root):
        from app.services import library_storage
        bad = _epub_bytes(mimetype=b"application/zip")
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("book.epub", bad))
        assert exc.value.status_code == 400

    def test_oversize_rejected(self, ebooks_root, monkeypatch):
        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_FILE_BYTES", 16)
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("big.pdf", PDF_BYTES))
        assert exc.value.status_code == 413

    def test_per_owner_total_cap(self, ebooks_root, monkeypatch):
        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_OWNER_TOTAL_BYTES",
                            len(PDF_BYTES) + 10)
        library_storage.save_ebook_file(7, _upload("a.pdf", PDF_BYTES))  # fits
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("b.pdf", PDF_BYTES))  # cap
        assert exc.value.status_code == 413
        # another owner's dir is unaffected by 7's usage
        library_storage.save_ebook_file(8, _upload("c.pdf", PDF_BYTES))

    def test_sample_allowlist_pdf_only(self, ebooks_root):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("s.epub", _epub_bytes()),
                                            allowed={"pdf"})
        assert exc.value.status_code == 400

    def test_resolve_reasserts_root(self, ebooks_root):
        from app.services import library_storage
        rel, _ = library_storage.save_ebook_file(7, _upload("ok.pdf", PDF_BYTES))
        assert library_storage.resolve_ebook_path(rel).is_file()
        for evil in ("../../etc/passwd", "..\\..\\secrets.pdf", "/etc/passwd"):
            with pytest.raises(HTTPException) as exc:
                library_storage.resolve_ebook_path(evil)
            assert exc.value.status_code == 404
```

- [ ] Run to see fail (ImportError), then implement
      `backend/app/services/library_storage.py`:

```python
"""Private ebook file storage (spec §3 — the crux: paid content must not leak).

Files live under backend/ebooks/{owner_id}/{uuid}.{ext} — NOT under
uploads/, which nginx serves publicly. Serving happens exclusively through
the authenticated /download and the app-streamed /sample endpoints in
app/routers/library.py (mirrors the company-invoicing private-PDF pattern:
FileResponse, never a static redirect).

Hardening (reuses core/secure_upload.py's posture where applicable):
  - extension allowlist {pdf, epub}; the CLIENT filename contributes ONLY
    its extension — the stored name is always uuid4().{ext}
  - magic-byte sniff after the bytes are on disk: PDF must start "%PDF-";
    EPUB must be a real zip (PK\x03\x04) whose `mimetype` entry equals
    application/epub+zip
  - 200MB per-file cap enforced WHILE streaming (a liar Content-Length
    can't help); 5GB per-owner cap measured from actual on-disk usage of
    the owner's directory (covers files + samples + replacements)
  - normalize-and-reassert: every path is resolved and asserted inside
    EBOOKS_ROOT both before writing and before serving
  - failed validation leaves no bytes behind (.part temp is unlinked)

Callers import the MODULE (`from app.services import library_storage`) and
use attribute access so tests can monkeypatch EBOOKS_ROOT and the caps.
"""
import logging
import uuid
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

EBOOKS_ROOT = Path("ebooks")  # backend/ebooks — created on demand; see deploy notes
ALLOWED_EXTENSIONS = {"pdf", "epub"}
MAX_FILE_BYTES = 200 * 1024 * 1024              # 200MB per file (spec §3)
MAX_OWNER_TOTAL_BYTES = 5 * 1024 * 1024 * 1024  # 5GB per owner (spec §3)
_CHUNK = 1024 * 1024

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "epub": "application/epub+zip",
}


def _owner_dir(owner_id: int) -> Path:
    return EBOOKS_ROOT / str(int(owner_id))


def owner_total_bytes(owner_id: int) -> int:
    """Actual on-disk usage of one owner's directory (files + samples)."""
    root = _owner_dir(owner_id)
    if not root.exists():
        return 0
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def _sniff_magic(path: Path, ext: str) -> None:
    """Reject files whose bytes don't match their claimed type (spec §3)."""
    if ext == "pdf":
        with open(path, "rb") as f:
            if f.read(5) != b"%PDF-":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="File is not a valid PDF")
        return
    # epub: zip magic + the OCF-required `mimetype` entry
    with open(path, "rb") as f:
        if f.read(4) != b"PK\x03\x04":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="File is not a valid EPUB")
    try:
        with ZipFile(path) as zf:
            if "mimetype" not in zf.namelist():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="EPUB is missing its mimetype entry")
            if zf.read("mimetype").strip() != b"application/epub+zip":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="EPUB mimetype entry is wrong")
    except BadZipFile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="File is not a valid EPUB")


def save_ebook_file(owner_id: int, upload: UploadFile,
                    allowed: "set[str] | None" = None) -> "tuple[str, int]":
    """Validate + store one uploaded ebook/sample. Returns
    (path relative to EBOOKS_ROOT as a posix string, size in bytes).
    Raises HTTPException 400/413 on any violation, leaving nothing on disk."""
    allowed = allowed or ALLOWED_EXTENSIONS
    name = upload.filename or ""
    if "." not in name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="File must have a .pdf or .epub extension")
    ext = name.rsplit(".", 1)[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type .{ext} is not allowed (allowed: {sorted(allowed)})")

    dest_dir = _owner_dir(owner_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / f"{uuid.uuid4().hex}.{ext}"

    # Normalize-and-reassert BEFORE writing. uuid names make traversal
    # impossible by construction; re-assert anyway (h5p_service posture).
    root = EBOOKS_ROOT.resolve()
    resolved = final.resolve()
    if root not in resolved.parents:
        raise HTTPException(status_code=500,
                            detail="Storage path escaped the ebooks root")

    tmp = final.with_suffix(final.suffix + ".part")
    size = 0
    try:
        with open(tmp, "wb") as out:
            while True:
                chunk = upload.file.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {MAX_FILE_BYTES} byte cap")
                out.write(chunk)
        if size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Uploaded file is empty")
        # Per-owner aggregate cap AGAINST ACTUAL BYTES (the .part just
        # written is included by the walk).
        if owner_total_bytes(owner_id) > MAX_OWNER_TOTAL_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"This upload would exceed your {MAX_OWNER_TOTAL_BYTES} "
                       "byte library storage cap. Delete unused files first.")
        _sniff_magic(tmp, ext)
        tmp.rename(final)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return final.relative_to(EBOOKS_ROOT).as_posix(), size


def resolve_ebook_path(rel_path: str) -> Path:
    """Resolve a stored relative path for serving; 404 on anything that
    normalizes outside EBOOKS_ROOT or doesn't exist. NEVER serve a path
    that didn't come through here."""
    root = EBOOKS_ROOT.resolve()
    candidate = (EBOOKS_ROOT / rel_path).resolve()
    if candidate == root or root not in candidate.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File not found")
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File not found")
    return candidate


def delete_stored_file(rel_path: "str | None") -> None:
    """Best-effort removal of a replaced/deleted blob. Never raises — a
    stale file on disk is an ops nuisance, not a request failure."""
    if not rel_path:
        return
    try:
        root = EBOOKS_ROOT.resolve()
        target = (EBOOKS_ROOT / rel_path).resolve()
        if target != root and root in target.parents:
            target.unlink(missing_ok=True)
    except OSError:
        logger.warning("could not delete stored ebook file %s", rel_path)
```

- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_library.py -v`
- [ ] Commit: `feat(library): private ebook storage service (magic bytes, 200MB/5GB caps, uuid names)`

---

## Task 3: Instructor CRUD router + ownership tests

**Files:**
- Create: `backend/app/routers/library.py`
- Modify: `backend/app/main.py` (import + `app.include_router(library.router,
  prefix="/api/v1/library", tags=["Library"])` next to the bundles line ~1304)
- Test: `backend/tests/test_library.py` (append `TestInstructorCrud`)

**Interfaces:**
- Produces (all under `/api/v1/library`, NO trailing slashes anywhere; fixed-path routes
  declared BEFORE `/{slug}` because of declaration-order matching):
  - `POST ""` — create draft (metadata only) `{title, description, category, price_inr,
    discount_price_inr?, cover_image?, page_count?, concept_tags?, course_id?}` → ebook dict
  - `GET /mine` — `{"ebooks": [...], "count": n}` (own; admin sees all)
  - `PUT /{ebook_id}` — update metadata (owner/admin; re-validates everything)
  - `POST /{ebook_id}/file` — multipart upload/replace the ebook file (owner/admin)
  - `POST /{ebook_id}/sample` — multipart upload/replace the sample PDF (owner/admin)
  - `POST /{ebook_id}/publish` — 400 without a file / `POST /{ebook_id}/unpublish` —
    always allowed, grants keep working
  - `DELETE /{ebook_id}` — 409 while any grant exists; deletes stored files best-effort
  - `GET /{ebook_id}/sales` — owner/admin: `{count, gross_inr, last_sale_at, buyers:
    [{display_name, source, granted_at}]}` — display_name ONLY, never emails
- Consumes: `AuthService.require_instructor`, `library_storage` (module import),
  `course_service._slugify_title`, `Ebook`/`EbookGrant`/`OrderItem`

**Steps:**

- [ ] Append failing tests:

```python
# ============================================================================
# Task 3: instructor CRUD + ownership
# ============================================================================


def _create_payload(**over):
    payload = {
        "title": "Tamil Grammar Guide",
        "description": "A concise guide.",
        "category": "guide",
        "price_inr": 299,
        "concept_tags": ["grammar", "tamil"],
    }
    payload.update(over)
    return payload


class TestInstructorCrud:
    def test_create_draft_generates_slug(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-a@lib.com")
        r = client.post("/api/v1/library", json=_create_payload(),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "draft"
        assert body["slug"].startswith("tamil-grammar-guide-")
        assert body["effective_price_inr"] == 299
        assert "file_path" not in body and "sample_path" not in body  # NEVER leaked

    def test_student_cannot_create(self, client, db, make_user, auth_headers):
        student = make_user(role="student")
        r = client.post("/api/v1/library", json=_create_payload(),
                        headers=auth_headers(student.user_email))
        assert r.status_code == 403

    @pytest.mark.parametrize("mutate", [
        {"category": "magazine"},                        # not in enum
        {"discount_price_inr": 299},                     # not < price
        {"discount_price_inr": 400},                     # > price
        {"concept_tags": [f"t{i}" for i in range(11)]},  # >10 tags
        {"concept_tags": ["x" * 51]},                    # tag >50 chars
        {"title": ""},                                   # empty title
        {"price_inr": -5},                               # negative price
        {"description": "d" * 5001},                     # >5000
    ])
    def test_metadata_validation(self, client, db, make_user, auth_headers, mutate):
        owner = _make_approved_instructor(db, make_user, "crud-b@lib.com")
        r = client.post("/api/v1/library", json=_create_payload(**mutate),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 422, r.text

    def test_cross_owner_blocked_everywhere(self, client, db, make_user,
                                            auth_headers, ebooks_root):
        a = _make_approved_instructor(db, make_user, "crud-c@lib.com")
        b = _make_approved_instructor(db, make_user, "crud-d@lib.com")
        ebook = _make_ebook(db, a)
        hb = auth_headers(b.user_email)
        assert client.put(f"/api/v1/library/{ebook.id}", json={"title": "hijack"},
                          headers=hb).status_code == 403
        assert client.post(f"/api/v1/library/{ebook.id}/file",
                           files={"file": ("x.pdf", PDF_BYTES, "application/pdf")},
                           headers=hb).status_code == 403
        assert client.post(f"/api/v1/library/{ebook.id}/publish",
                           headers=hb).status_code == 403
        assert client.post(f"/api/v1/library/{ebook.id}/unpublish",
                           headers=hb).status_code == 403
        assert client.delete(f"/api/v1/library/{ebook.id}",
                             headers=hb).status_code == 403
        assert client.get(f"/api/v1/library/{ebook.id}/sales",
                          headers=hb).status_code == 403

    def test_mine_lists_only_own(self, client, db, make_user, auth_headers):
        a = _make_approved_instructor(db, make_user, "crud-e@lib.com")
        b = _make_approved_instructor(db, make_user, "crud-f@lib.com")
        _make_ebook(db, a, title="A Book")
        _make_ebook(db, b, title="B Book")
        r = client.get("/api/v1/library/mine", headers=auth_headers(a.user_email))
        assert r.status_code == 200
        assert [e["title"] for e in r.json()["ebooks"]] == ["A Book"]

    def test_upload_then_publish_flow(self, client, db, make_user, auth_headers,
                                      ebooks_root):
        owner = _make_approved_instructor(db, make_user, "crud-g@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        # publish before file → 400
        r = client.post(f"/api/v1/library/{ebook_id}/publish", headers=h)
        assert r.status_code == 400
        assert "file" in r.json()["detail"].lower()
        # upload, then publish works
        r = client.post(f"/api/v1/library/{ebook_id}/file",
                        files={"file": ("g.pdf", PDF_BYTES, "application/pdf")},
                        headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["has_file"] is True
        assert client.post(f"/api/v1/library/{ebook_id}/publish",
                           headers=h).json()["status"] == "published"
        # sample rejects epub
        r = client.post(f"/api/v1/library/{ebook_id}/sample",
                        files={"file": ("s.epub", _epub_bytes(),
                                        "application/epub+zip")}, headers=h)
        assert r.status_code == 400
        # unpublish always allowed
        assert client.post(f"/api/v1/library/{ebook_id}/unpublish",
                           headers=h).json()["status"] == "draft"

    def test_delete_409_with_grants(self, client, db, make_user, auth_headers,
                                    ebooks_root):
        owner = _make_approved_instructor(db, make_user, "crud-h@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        _grant(db, ebook, student)
        r = client.delete(f"/api/v1/library/{ebook.id}",
                          headers=auth_headers(owner.user_email))
        assert r.status_code == 409
        assert db.query(Ebook).filter(Ebook.id == ebook.id).first() is not None

    def test_delete_without_grants_removes_row(self, client, db, make_user,
                                               auth_headers, ebooks_root):
        owner = _make_approved_instructor(db, make_user, "crud-i@lib.com")
        ebook = _make_ebook(db, owner)
        r = client.delete(f"/api/v1/library/{ebook.id}",
                          headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        assert db.query(Ebook).filter(Ebook.id == ebook.id).first() is None

    def test_sales_panel_shape_no_emails(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-j@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        _grant(db, ebook, student)
        r = client.get(f"/api/v1/library/{ebook.id}/sales",
                       headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["gross_inr"] == 0.0  # free/hand grant: no OrderItem money
        assert body["buyers"][0]["display_name"] == student.display_name
        import json as _json
        assert "user_email" not in _json.dumps(body)  # spec §4: no buyer emails
```

- [ ] Run to see fail (404s — router missing), then implement
      `backend/app/routers/library.py` (instructor half; public/student endpoints, claim and
      suggestions are Tasks 4/6/7 — the file grows like h5p.py did):

```python
"""Digital Library API (spec §4) — mounted at /api/v1/library.

redirect_slashes=False: every path here is declared WITHOUT a trailing
slash (create is @router.post("")), and '/library' is in axios.ts's
noSlashEndpoints — the gamification-404 lesson.

ROUTE ORDER MATTERS: fixed-path GETs (/mine, /me, /suggestions) are
declared BEFORE GET /{slug} so they never match as a slug.

Ownership (spec §4): instructor endpoints are owner-scoped, admin-any —
mirrors games.py exactly. Students touch only the public store, /me,
claim, download and sample.

Money: prices are whole rupees (price_inr); the payments router owns the
single paise boundary. file_path/sample_path NEVER appear in any response
body (spec §3) — _ebook_dict exposes has_file/has_sample booleans only.

Response style: plain dicts, no envelopes (matches games.py/h5p.py).
"""
import logging
import re
from typing import List, Optional

from fastapi import (APIRouter, Depends, File, HTTPException, Request,
                     Response, UploadFile, status)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache_headers import apply_public_cache
from app.core.database import get_db
from app.models.course import Course
from app.models.ebook import (EBOOK_CATEGORIES, Ebook, EbookGrant,
                              effective_price_inr)
from app.models.payment import OrderItem
from app.models.user import User
from app.services import library_storage
from app.services.auth_service import AuthService
from app.services.course_service import _slugify_title

router = APIRouter()
logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-z0-9]+")


# ---- request schemas ---------------------------------------------------------

class EbookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=5000)
    category: str
    price_inr: int = Field(..., ge=0, le=1_000_000)   # whole rupees
    discount_price_inr: Optional[int] = Field(None, ge=0)
    cover_image: str = Field("", max_length=500)      # existing public uploads flow
    page_count: Optional[int] = Field(None, ge=1, le=100_000)
    concept_tags: List[str] = Field(default_factory=list, max_items=10)
    course_id: Optional[int] = None

    @validator("category")
    def _category_in_enum(cls, v):
        if v not in EBOOK_CATEGORIES:
            raise ValueError(f"category must be one of {list(EBOOK_CATEGORIES)}")
        return v

    @validator("concept_tags", each_item=True)
    def _tag_caps(cls, v):
        v = str(v).strip()
        if not (1 <= len(v) <= 50):
            raise ValueError("each concept tag must be 1..50 chars")
        return v

    @validator("discount_price_inr")
    def _discount_below_price(cls, v, values):
        price = values.get("price_inr")
        if v is not None and price is not None and v >= price:
            raise ValueError("discount_price_inr must be less than price_inr")
        return v


class EbookUpdate(EbookCreate):
    """PUT body — same fields/caps, everything optional. The cross-field
    discount<price rule is re-checked against the MERGED row in the handler
    (a kept discount must still undercut a newly-lowered price)."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = None
    price_inr: Optional[int] = Field(None, ge=0, le=1_000_000)

    @validator("category")
    def _category_in_enum(cls, v):
        if v is not None and v not in EBOOK_CATEGORIES:
            raise ValueError(f"category must be one of {list(EBOOK_CATEGORIES)}")
        return v


# ---- helpers -----------------------------------------------------------------

def _get_ebook_or_404(db: Session, ebook_id: int) -> Ebook:
    ebook = db.query(Ebook).filter(Ebook.id == ebook_id).first()
    if not ebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ebook not found")
    return ebook


def _require_owner_or_admin(ebook: Ebook, current_user: User) -> None:
    if ebook.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized for this ebook")


def _is_privileged(ebook: Ebook, user: "User | None") -> bool:
    return user is not None and (user.id == ebook.owner_id or user.role == "admin")


def _build_ebook_slug(ebook: Ebook) -> str:
    """`<title-slug>-<id>` like course slugs (course_service.build_default_slug);
    `ebook-<id>` for pure-Tamil titles. The embedded id guarantees uniqueness."""
    base = _slugify_title(ebook.title or "")
    if not base:
        return f"ebook-{ebook.id}"
    return f"{base}-{ebook.id}"


def _ebook_dict(ebook: Ebook, *, owned: "bool | None" = None,
                course_title: "str | None" = None) -> dict:
    """Public/instructor shape. file_path/sample_path are PRIVATE and never
    leave the server — only has_file/has_sample booleans do."""
    d = {
        "id": ebook.id,
        "owner_id": ebook.owner_id,
        "slug": ebook.slug,
        "title": ebook.title,
        "description": ebook.description or "",
        "category": ebook.category,
        "price_inr": int(ebook.price_inr or 0),
        "discount_price_inr": ebook.discount_price_inr,
        "effective_price_inr": effective_price_inr(ebook),
        "cover_image": ebook.cover_image or "",
        "page_count": ebook.page_count,
        "concept_tags": list(ebook.concept_tags or []),
        "course_id": ebook.course_id,
        "course_title": course_title,
        "status": ebook.status,
        "has_file": bool(ebook.file_path),
        "has_sample": bool(ebook.sample_path),
        "file_size_bytes": int(ebook.file_size_bytes or 0),
        "created_at": ebook.created_at,
        "updated_at": ebook.updated_at,
    }
    if owned is not None:
        d["owned"] = owned
    return d


def _course_titles(db: Session, ebooks: "list[Ebook]") -> dict:
    ids = {e.course_id for e in ebooks if e.course_id}
    if not ids:
        return {}
    return {c.id: c.post_title for c in
            db.query(Course).filter(Course.id.in_(ids)).all()}


# ---- instructor/admin endpoints (owner-scoped, admin-any) ---------------------

@router.post("")
async def create_ebook(
    payload: EbookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Create a draft (metadata only — files arrive via /file and /sample)."""
    ebook = Ebook(
        owner_id=current_user.id,
        title=payload.title.strip(),
        slug="pending",
        description=payload.description,
        category=payload.category,
        price_inr=payload.price_inr,
        discount_price_inr=payload.discount_price_inr,
        cover_image=payload.cover_image,
        page_count=payload.page_count,
        concept_tags=payload.concept_tags,
        course_id=payload.course_id,
        status="draft",
    )
    db.add(ebook)
    db.flush()                      # assign id, then derive the slug from it
    ebook.slug = _build_ebook_slug(ebook)
    db.commit()
    db.refresh(ebook)
    return _ebook_dict(ebook)


@router.get("/mine")
async def list_my_ebooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    query = db.query(Ebook)
    if current_user.role != "admin":
        query = query.filter(Ebook.owner_id == current_user.id)
    ebooks = query.order_by(Ebook.updated_at.desc()).all()
    titles = _course_titles(db, ebooks)
    return {"ebooks": [_ebook_dict(e, course_title=titles.get(e.course_id))
                       for e in ebooks],
            "count": len(ebooks)}


@router.put("/{ebook_id}")
async def update_ebook(
    ebook_id: int,
    payload: EbookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)

    data = payload.dict(exclude_unset=True)
    for field in ("title", "description", "category", "price_inr",
                  "discount_price_inr", "cover_image", "page_count",
                  "concept_tags", "course_id"):
        if field in data:
            setattr(ebook, field,
                    data[field].strip() if field == "title" else data[field])
    # Cross-field rule re-checked against the MERGED row.
    if ebook.discount_price_inr is not None and \
            ebook.discount_price_inr >= int(ebook.price_inr or 0):
        raise HTTPException(status_code=422,
                            detail="discount_price_inr must be less than price_inr")
    if "title" in data:
        ebook.slug = _build_ebook_slug(ebook)
    db.commit()
    db.refresh(ebook)
    return _ebook_dict(ebook)


@router.post("/{ebook_id}/file")
async def upload_ebook_file(
    ebook_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Upload/replace the sellable file. Stored under the EBOOK OWNER's dir
    (admin uploads land in the owner's 5GB quota, not the admin's)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    rel_path, size = library_storage.save_ebook_file(ebook.owner_id, file)
    old = ebook.file_path
    ebook.file_path = rel_path
    ebook.file_size_bytes = size
    db.commit()
    db.refresh(ebook)
    if old:
        library_storage.delete_stored_file(old)  # after commit: never orphan the live row
    return _ebook_dict(ebook)


@router.post("/{ebook_id}/sample")
async def upload_ebook_sample(
    ebook_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Upload/replace the free-preview sample. PDF only (spec §1)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    rel_path, _size = library_storage.save_ebook_file(ebook.owner_id, file,
                                                      allowed={"pdf"})
    old = ebook.sample_path
    ebook.sample_path = rel_path
    db.commit()
    db.refresh(ebook)
    if old:
        library_storage.delete_stored_file(old)
    return _ebook_dict(ebook)


@router.post("/{ebook_id}/publish")
async def publish_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Publish requires the sellable file to be present (spec §4)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    if not ebook.file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot publish: upload the ebook file first")
    ebook.status = "published"
    db.commit()
    db.refresh(ebook)
    return _ebook_dict(ebook)


@router.post("/{ebook_id}/unpublish")
async def unpublish_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Allowed anytime. Only hides the ebook from the store — grants keep
    working (the download gate checks grants, not status; spec §4)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    ebook.status = "draft"
    db.commit()
    db.refresh(ebook)
    return _ebook_dict(ebook)


@router.delete("/{ebook_id}")
async def delete_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """409 while ANY grant exists — sold content is never deleted (spec §4).
    Unpublish is the way to retire a sold ebook."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    grant_count = db.query(func.count(EbookGrant.id)).filter(
        EbookGrant.ebook_id == ebook.id).scalar() or 0
    if grant_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: {grant_count} student(s) own this ebook. "
                   "Unpublish it instead — sold content is never deleted.")
    file_path, sample_path = ebook.file_path, ebook.sample_path
    db.delete(ebook)
    db.commit()
    library_storage.delete_stored_file(file_path)
    library_storage.delete_stored_file(sample_path)
    return {"success": True, "id": ebook_id}


@router.get("/{ebook_id}/sales")
async def ebook_sales(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Owner sales panel: count, gross from OrderItems, last sale, buyers by
    display_name ONLY — never emails (spec §4)."""
    ebook = _get_ebook_or_404(db, ebook_id)
    _require_owner_or_admin(ebook, current_user)
    grants = (db.query(EbookGrant)
              .filter(EbookGrant.ebook_id == ebook.id)
              .order_by(EbookGrant.granted_at.desc())
              .all())
    gross = db.query(func.coalesce(func.sum(OrderItem.total), 0)).filter(
        OrderItem.ebook_id == ebook.id).scalar()
    users_by_id = {u.id: u for u in db.query(User).filter(
        User.id.in_([g.user_id for g in grants])).all()} if grants else {}
    return {
        "ebook_id": ebook.id,
        "count": len(grants),
        "gross_inr": float(gross or 0),
        "last_sale_at": grants[0].granted_at if grants else None,
        "buyers": [{
            "display_name": users_by_id[g.user_id].display_name
            if g.user_id in users_by_id else "Unknown",
            "source": g.source,
            "granted_at": g.granted_at,
        } for g in grants],
    }
```

  (Task 4 INSERTS the public GETs `""`, `/me` and `/{slug}` plus download/sample into this
  file — `/me` and Task 7's `/suggestions` must sit ABOVE `GET /{slug}` in declaration
  order, and `/{slug}` itself must be the LAST GET declared.)

- [ ] Register in `backend/app/main.py`: add `from app.routers import library` next to the
      bundles import, and
      `app.include_router(library.router, prefix="/api/v1/library", tags=["Library"])`
      next to the bundles include (~line 1304).
- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_library.py -v`
- [ ] Full suite green: `./.venv/Scripts/python -m pytest tests/ -v`
- [ ] Commit: `feat(library): instructor CRUD router (ownership, publish gate, delete-409, sales panel)`

---

## Task 4: Public store endpoints + edge caching + download/sample gates

**Files:**
- Modify: `backend/app/routers/library.py` (insert public/student endpoints — `GET ""`,
  `GET /me`, `GET /{slug}` and the two streaming routes; keep `/{slug}` the LAST GET)
- Test: `backend/tests/test_library.py` (append `TestPublicStore`, `TestCacheHeaders`,
  `TestDownloadGates`)

**Interfaces:**
- Produces:
  - `GET ""` — published ebooks; query filters `category`, `q` (title ilike), `course_id`,
    `tag`; anon-edge-cacheable (300/600) → `{"ebooks": [...], "count": n}`
  - `GET /me` — authed: `{"items": [{...ebook, granted_at, downloadable}], "count": n}`
  - `GET /{slug}` — published detail, cacheable (60/600); `owned` present ONLY for authed
    users (helper makes those responses `private, no-store`)
  - `GET /{ebook_id}/download` — authed; grant or owner/admin; streams with
    `Content-Disposition: attachment`; draft → 404 to non-owner; unpublished-but-granted
    still 200; NEVER a redirect
  - `GET /{ebook_id}/sample` — optional auth; published + sample present → 200 PDF stream
- Consumes: `apply_public_cache`, `AuthService.get_optional_current_user`,
  `AuthService.get_current_active_user`, `library_storage.resolve_ebook_path`

**Steps:**

- [ ] Append failing tests:

```python
# ============================================================================
# Task 4: public store + caching + download/sample gates
# ============================================================================


class TestPublicStore:
    def test_list_filters(self, client, db, make_user, course):
        owner = _make_approved_instructor(db, make_user, "store-a@lib.com")
        _make_ebook(db, owner, title="Algebra Book", category="book",
                    status="published", tags=["algebra"])
        _make_ebook(db, owner, title="Algebra Notes", category="lecture_notes",
                    status="published", course_id=course.id)
        _make_ebook(db, owner, title="Hidden Draft", status="draft")

        assert client.get("/api/v1/library").json()["count"] == 2  # drafts never listed
        r = client.get("/api/v1/library", params={"category": "book"})
        assert [e["title"] for e in r.json()["ebooks"]] == ["Algebra Book"]
        r = client.get("/api/v1/library", params={"q": "notes"})
        assert [e["title"] for e in r.json()["ebooks"]] == ["Algebra Notes"]
        r = client.get("/api/v1/library", params={"course_id": course.id})
        assert r.json()["count"] == 1
        r = client.get("/api/v1/library", params={"tag": "Algebra"})  # case-insensitive
        assert [e["title"] for e in r.json()["ebooks"]] == ["Algebra Book"]

    def test_detail_owned_flag_only_when_authed(self, client, db, make_user,
                                                auth_headers):
        owner = _make_approved_instructor(db, make_user, "store-b@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        _grant(db, ebook, student)

        anon = client.get(f"/api/v1/library/{ebook.slug}")
        assert anon.status_code == 200
        assert "owned" not in anon.json()          # anon body is user-independent

        authed = client.get(f"/api/v1/library/{ebook.slug}",
                            headers=auth_headers(student.user_email))
        assert authed.json()["owned"] is True

        other = make_user(role="student", email="store-nobody@lib.com")
        r = client.get(f"/api/v1/library/{ebook.slug}",
                       headers=auth_headers(other.user_email))
        assert r.json()["owned"] is False

    def test_detail_404_for_draft(self, client, db, make_user):
        owner = _make_approved_instructor(db, make_user, "store-c@lib.com")
        ebook = _make_ebook(db, owner, status="draft")
        assert client.get(f"/api/v1/library/{ebook.slug}").status_code == 404

    def test_me_lists_grants(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "store-d@lib.com")
        student = make_user(role="student")
        with_file = _make_ebook(db, owner, title="Has File", status="published",
                                file_path="1/abc.pdf")
        _grant(db, with_file, student)
        r = client.get("/api/v1/library/me", headers=auth_headers(student.user_email))
        assert r.status_code == 200
        item = r.json()["items"][0]
        assert item["title"] == "Has File"
        assert item["downloadable"] is True
        assert "granted_at" in item
        assert client.get("/api/v1/library/me").status_code in (401, 403)  # authed only


class TestCacheHeaders:
    def test_list_anon_cacheable_authed_private(self, client, db, make_user,
                                                auth_headers):
        student = make_user(role="student")
        anon = client.get("/api/v1/library")
        assert anon.headers["Cache-Control"] == \
            "public, s-maxage=300, stale-while-revalidate=600"
        assert anon.headers["Vary"] == "Authorization"
        authed = client.get("/api/v1/library",
                            headers=auth_headers(student.user_email))
        assert authed.headers["Cache-Control"] == "private, no-store"

    def test_detail_anon_cacheable_authed_private(self, client, db, make_user,
                                                  auth_headers):
        owner = _make_approved_instructor(db, make_user, "cache-a@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        anon = client.get(f"/api/v1/library/{ebook.slug}")
        assert anon.headers["Cache-Control"] == \
            "public, s-maxage=60, stale-while-revalidate=600"
        authed = client.get(f"/api/v1/library/{ebook.slug}",
                            headers=auth_headers(student.user_email))
        assert authed.headers["Cache-Control"] == "private, no-store"

    def test_me_never_edge_cached(self, client, db, make_user, auth_headers):
        student = make_user(role="student")
        r = client.get("/api/v1/library/me", headers=auth_headers(student.user_email))
        assert "s-maxage" not in r.headers.get("Cache-Control", "")


class TestDownloadGates:
    def _published_with_file(self, client, db, make_user, auth_headers, email,
                             sample=False):
        owner = _make_approved_instructor(db, make_user, email)
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        client.post(f"/api/v1/library/{ebook_id}/file",
                    files={"file": ("f.pdf", PDF_BYTES, "application/pdf")}, headers=h)
        if sample:
            client.post(f"/api/v1/library/{ebook_id}/sample",
                        files={"file": ("s.pdf", PDF_BYTES, "application/pdf")},
                        headers=h)
        client.post(f"/api/v1/library/{ebook_id}/publish", headers=h)
        db.expire_all()
        return db.query(Ebook).filter(Ebook.id == ebook_id).one(), h

    def test_no_grant_403_granted_200_streams_bytes(self, client, db, make_user,
                                                    auth_headers, ebooks_root):
        ebook, _ = self._published_with_file(client, db, make_user, auth_headers,
                                             "dl-a@lib.com")
        student = make_user(role="student")
        hs = auth_headers(student.user_email)
        assert client.get(f"/api/v1/library/{ebook.id}/download",
                          headers=hs).status_code == 403
        _grant(db, ebook, student)
        r = client.get(f"/api/v1/library/{ebook.id}/download", headers=hs)
        assert r.status_code == 200
        assert r.content == PDF_BYTES                     # actual bytes, not a redirect
        assert r.headers["content-type"].startswith("application/pdf")
        assert "attachment" in r.headers["content-disposition"]
        assert client.get(f"/api/v1/library/{ebook.id}/download").status_code \
            in (401, 403)                                  # anon never downloads

    def test_owner_and_admin_download_without_grant(self, client, db, make_user,
                                                    auth_headers, ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-b@lib.com")
        assert client.get(f"/api/v1/library/{ebook.id}/download",
                          headers=owner_h).status_code == 200

    def test_draft_download_404_to_non_owner(self, client, db, make_user,
                                             auth_headers, ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-c@lib.com")
        client.post(f"/api/v1/library/{ebook.id}/unpublish", headers=owner_h)
        stranger = make_user(role="student", email="dl-stranger@lib.com")
        r = client.get(f"/api/v1/library/{ebook.id}/download",
                       headers=auth_headers(stranger.user_email))
        assert r.status_code == 404  # drafts don't leak existence to non-owners

    def test_unpublish_keeps_access(self, client, db, make_user, auth_headers,
                                    ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-d@lib.com")
        student = make_user(role="student", email="dl-keeper@lib.com")
        _grant(db, ebook, student)
        client.post(f"/api/v1/library/{ebook.id}/unpublish", headers=owner_h)
        r = client.get(f"/api/v1/library/{ebook.id}/download",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 200                        # spec §4, BINDING
        assert r.content == PDF_BYTES

    def test_sample_public_when_published(self, client, db, make_user,
                                          auth_headers, ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-e@lib.com",
                                                   sample=True)
        r = client.get(f"/api/v1/library/{ebook.id}/sample")   # NO auth header
        assert r.status_code == 200
        assert r.content == PDF_BYTES
        client.post(f"/api/v1/library/{ebook.id}/unpublish", headers=owner_h)
        assert client.get(f"/api/v1/library/{ebook.id}/sample").status_code == 404
        # owner still reaches the sample of the draft
        assert client.get(f"/api/v1/library/{ebook.id}/sample",
                          headers=owner_h).status_code == 200

    def test_sample_missing_404(self, client, db, make_user, auth_headers,
                                ebooks_root):
        ebook, _ = self._published_with_file(client, db, make_user, auth_headers,
                                             "dl-f@lib.com", sample=False)
        assert client.get(f"/api/v1/library/{ebook.id}/sample").status_code == 404
```

- [ ] Run to see fail, then insert into `backend/app/routers/library.py` — public/store
      section ABOVE the instructor block's `/{ebook_id}` routes, with `GET /{slug}` declared
      after `/mine` and `/me` (and, later, `/suggestions`):

```python
# ---- public store (anon-edge-cacheable; spec §4) -------------------------------

@router.get("")
async def list_published_ebooks(
    request: Request,
    response: Response,
    category: Optional[str] = None,
    q: Optional[str] = None,
    course_id: Optional[int] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Published ebooks with store filters. Anon requests are edge-cacheable;
    the helper stamps authed ones `private, no-store` (body is identical for
    every anon caller — no per-user data here)."""
    apply_public_cache(request, response, s_maxage=300, swr=600)
    query = db.query(Ebook).filter(Ebook.status == "published")
    if category:
        query = query.filter(Ebook.category == category)
    if q:
        query = query.filter(Ebook.title.ilike(f"%{q.strip()}%"))
    if course_id:
        query = query.filter(Ebook.course_id == course_id)
    ebooks = query.order_by(Ebook.created_at.desc()).all()
    if tag:
        # JSON containment isn't portable across SQLite/Postgres — filter in
        # Python; the published set is small (a store, not a firehose).
        wanted = tag.strip().lower()
        ebooks = [e for e in ebooks
                  if wanted in [str(t).lower() for t in (e.concept_tags or [])]]
    titles = _course_titles(db, ebooks)
    return {"ebooks": [_ebook_dict(e, course_title=titles.get(e.course_id))
                       for e in ebooks],
            "count": len(ebooks)}


@router.get("/me")
async def my_library(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """My grants with download availability. Per-user — NEVER edge-cached
    (no apply_public_cache here, Global Constraint 7)."""
    grants = (db.query(EbookGrant)
              .filter(EbookGrant.user_id == current_user.id)
              .order_by(EbookGrant.granted_at.desc())
              .all())
    ebooks_by_id = {e.id: e for e in db.query(Ebook).filter(
        Ebook.id.in_([g.ebook_id for g in grants])).all()} if grants else {}
    items = []
    for g in grants:
        ebook = ebooks_by_id.get(g.ebook_id)
        if ebook is None:
            continue
        d = _ebook_dict(ebook)
        d["granted_at"] = g.granted_at
        d["downloadable"] = bool(ebook.file_path)
        items.append(d)
    return {"items": items, "count": len(items)}
```

  and the detail + streaming routes at the BOTTOM of the file (after every fixed-path and
  `/{ebook_id}`-typed route so `/{slug}` matches last):

```python
# ---- streaming gates (spec §3: never a redirect to a static path) --------------

@router.get("/{ebook_id}/download")
async def download_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Grant-gated download. Owner/admin need no grant. A granted student
    keeps access after unpublish (the gate checks the grant, not status).
    Drafts 404 to everyone else so unpublished inventory can't be probed."""
    ebook = _get_ebook_or_404(db, ebook_id)
    if not _is_privileged(ebook, current_user):
        grant = db.query(EbookGrant).filter(
            EbookGrant.ebook_id == ebook.id,
            EbookGrant.user_id == current_user.id).first()
        if grant is None:
            if ebook.status != "published":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Ebook not found")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You do not own this ebook")
    if not ebook.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No file uploaded for this ebook")
    path = library_storage.resolve_ebook_path(ebook.file_path)
    ext = path.suffix.lstrip(".").lower()
    return FileResponse(
        path,
        media_type=library_storage.MEDIA_TYPES.get(ext, "application/octet-stream"),
        filename=f"{ebook.slug}.{ext}",   # → Content-Disposition: attachment
    )


@router.get("/{ebook_id}/sample")
async def download_sample(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user),
):
    """Grant-free preview (semi-public by design, spec §3): published samples
    stream to anyone; drafts only to owner/admin. Still app-streamed —
    never nginx-static."""
    ebook = _get_ebook_or_404(db, ebook_id)
    if ebook.status != "published" and not _is_privileged(ebook, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ebook not found")
    if not ebook.sample_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No sample available for this ebook")
    path = library_storage.resolve_ebook_path(ebook.sample_path)
    return FileResponse(path, media_type="application/pdf",
                        filename=f"{ebook.slug}-sample.pdf")


# ---- public detail — LAST GET in the file: /{slug} is the catch-all ------------

@router.get("/{slug}")
async def get_ebook_detail(
    slug: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(AuthService.get_optional_current_user),
):
    """Published detail. `owned` appears ONLY for authed users — whose
    responses apply_public_cache already stamps `private, no-store`, so the
    per-user flag can never leak through a shared edge (spec §4)."""
    apply_public_cache(request, response, s_maxage=60, swr=600)
    ebook = db.query(Ebook).filter(Ebook.slug == slug,
                                   Ebook.status == "published").first()
    if not ebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ebook not found")
    titles = _course_titles(db, [ebook])
    owned = None
    if current_user is not None:
        owned = _is_privileged(ebook, current_user) or db.query(EbookGrant).filter(
            EbookGrant.ebook_id == ebook.id,
            EbookGrant.user_id == current_user.id).first() is not None
    return _ebook_dict(ebook, owned=owned,
                       course_title=titles.get(ebook.course_id))
```

- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_library.py -v`
- [ ] Full suite green: `./.venv/Scripts/python -m pytest tests/ -v`
- [ ] Commit: `feat(library): public store + anon edge caching + grant-gated download/sample streaming`

---

## Task 5: Payment extension — create-order/verify ebook_id + fulfillment + grants (review: opus)

**Files:**
- Modify: `backend/app/schemas/payment.py` (`ebook_id` joins the exactly-one-of contract in
  BOTH request models)
- Modify: `backend/app/routers/payments.py` (`_create_ebook_order`, `_verify_ebook_payment`,
  branch lines in `create_razorpay_order` and `verify_razorpay_payment`)
- Modify: `backend/app/services/fulfillment_service.py` (add `grant_ebook`,
  `fulfill_ebook_purchase`)
- Test: `backend/tests/test_library.py` (append `TestEbookCheckout`,
  `TestEbookFulfillment`)

**Interfaces:**
- Produces:
  - `CreateOrderRequest.ebook_id` / `VerifyPaymentRequest.ebook_id` (exactly-one-of grows to
    4 targets; 422 otherwise)
  - `POST /api/v1/payments/create-order {ebook_id}` → `{order_id, amount, currency, key_id}`
    — server-priced (rupee snapshot in notes), coupons 400, draft 400, owned 400, free 400
  - `POST /api/v1/payments/verify {razorpay_*, ebook_id}` → grant + Order/OrderItem/Payment
  - `fulfillment_service.grant_ebook(db, *, ebook_id, user_id, order_id, source) -> bool`
  - `fulfillment_service.fulfill_ebook_purchase(db, *, user, ebook_id, razorpay_order_id,
    razorpay_payment_id, paid_amount, currency) -> FulfillmentResult` — idempotent on
    `Payment.gateway_payment_id`, never touches enrollments, does NOT commit
- Consumes: `effective_price_inr`, `_razorpay_client`/`_razorpay_creds`, `EmailService`

**Steps:**

- [ ] Append failing tests (gateway mocked exactly like `tests/test_bundle_checkout.py`):

```python
# ============================================================================
# Task 5: payment extension (create-order / verify / fulfillment)
# ============================================================================

import hashlib  # noqa: E402
import hmac  # noqa: E402


class FakeOrders:
    """Copy of test_bundle_checkout.FakeOrders — records the created payload
    and echoes it back on fetch, so verify sees exactly what create built."""
    last_payload = None

    class order:
        @staticmethod
        def create(payload):
            FakeOrders.last_payload = payload
            return {"id": "order_TEST1", "amount": payload["amount"],
                    "currency": "INR", "notes": payload["notes"]}

        @staticmethod
        def fetch(order_id):
            return {"id": order_id,
                    "amount": FakeOrders.last_payload["amount"],
                    "amount_paid": FakeOrders.last_payload["amount"],
                    "currency": "INR",
                    "notes": FakeOrders.last_payload["notes"]}


def _patch_gateway(monkeypatch):
    import app.routers.payments as pay
    monkeypatch.setattr(pay, "_razorpay_client", lambda: FakeOrders)
    monkeypatch.setattr(pay, "_razorpay_creds", lambda: ("rzp_key", "secret"))


def _signed_verify_body(ebook_id, payment_id="pay_TEST1", order_id="order_TEST1"):
    sig = hmac.new(b"secret", f"{order_id}|{payment_id}".encode(),
                   hashlib.sha256).hexdigest()
    return {"razorpay_order_id": order_id, "razorpay_payment_id": payment_id,
            "razorpay_signature": sig, "ebook_id": ebook_id}


class TestEbookCheckout:
    def test_exactly_one_of_rejects_pairs(self, client, as_user, student_user):
        as_user(student_user)
        r = client.post("/api/v1/payments/create-order",
                        json={"course_id": 1, "ebook_id": 1})
        assert r.status_code == 422
        r = client.post("/api/v1/payments/create-order",
                        json={"bundle_id": 1, "ebook_id": 1})
        assert r.status_code == 422

    def test_order_uses_server_price_and_snapshot(self, client, db, make_user,
                                                  as_user, student_user,
                                                  monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-a@lib.com")
        ebook = _make_ebook(db, owner, price=500, discount=350,
                            status="published", file_path="1/x.pdf")
        as_user(student_user)
        r = client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        assert r.status_code == 200, r.text
        assert FakeOrders.last_payload["amount"] == 35000  # discount honored, paise
        notes = FakeOrders.last_payload["notes"]
        assert notes["ebook_id"] == str(ebook.id)
        assert notes["user_id"] == str(student_user.id)
        assert notes["ebook_price_inr"] == "350"           # rupee snapshot

    def test_order_rejections(self, client, db, make_user, as_user, student_user,
                              monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-b@lib.com")
        published = _make_ebook(db, owner, price=500, status="published",
                                file_path="1/x.pdf")
        draft = _make_ebook(db, owner, title="Draft One", price=500)
        free = _make_ebook(db, owner, title="Free One", price=0,
                           status="published", file_path="1/y.pdf")
        as_user(student_user)
        # coupons rejected on ebooks (mirrors bundles)
        r = client.post("/api/v1/payments/create-order",
                        json={"ebook_id": published.id, "coupon_code": "X"})
        assert r.status_code == 400
        assert "coupon" in r.json()["detail"].lower()
        # draft cannot be ordered (spec §2: publish-state re-checked → 400)
        assert client.post("/api/v1/payments/create-order",
                           json={"ebook_id": draft.id}).status_code == 400
        # free ebooks bypass Razorpay entirely
        r = client.post("/api/v1/payments/create-order", json={"ebook_id": free.id})
        assert r.status_code == 400
        assert "claim" in r.json()["detail"].lower()
        # already owned
        _grant(db, published, student_user)
        assert client.post("/api/v1/payments/create-order",
                           json={"ebook_id": published.id}).status_code == 400

    def test_verify_grants_and_writes_money_trail(self, client, db, make_user,
                                                  as_user, student_user,
                                                  monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-c@lib.com")
        ebook = _make_ebook(db, owner, price=500, discount=350,
                            status="published", file_path="1/x.pdf")
        as_user(student_user)
        assert client.post("/api/v1/payments/create-order",
                           json={"ebook_id": ebook.id}).status_code == 200
        r = client.post("/api/v1/payments/verify", json=_signed_verify_body(ebook.id))
        assert r.status_code == 200, r.text

        grant = db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                               user_id=student_user.id).one()
        assert grant.source == "purchase"
        assert grant.order_id is not None
        order = db.query(Order).filter(Order.id == grant.order_id).one()
        assert order.ebook_id == ebook.id
        assert float(order.total_amount) == 350.0          # rupees, discount price
        assert float(order.subtotal_amount) == 500.0       # list price
        assert float(order.discount_amount) == 150.0
        item = db.query(OrderItem).filter(OrderItem.order_id == order.id).one()
        assert item.ebook_id == ebook.id and item.course_id is None
        assert item.order_item_type == "ebook_item"
        payment = db.query(Payment).filter(
            Payment.gateway_payment_id == "pay_TEST1").one()
        assert payment.order_id == order.id
        # no enrollment side effects — ebooks never touch enrollments
        from app.models.enrollment import Enrollment
        assert db.query(Enrollment).filter_by(user_id=student_user.id).count() == 0

    def test_verify_replay_is_idempotent(self, client, db, make_user, as_user,
                                         student_user, monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-d@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        body = _signed_verify_body(ebook.id)
        assert client.post("/api/v1/payments/verify", json=body).status_code == 200
        assert client.post("/api/v1/payments/verify", json=body).status_code == 200
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1
        assert db.query(Order).filter(Order.ebook_id == ebook.id).count() == 1

    def test_verify_amount_checked_against_snapshot(self, client, db, make_user,
                                                    as_user, student_user,
                                                    monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-e@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        # price raised AFTER checkout: the 500-rupee capture must still verify
        # (the snapshot, not the live price, is authoritative)
        ebook.price_inr = 900
        db.commit()
        assert client.post("/api/v1/payments/verify",
                           json=_signed_verify_body(ebook.id)).status_code == 200

    def test_verify_wrong_user_403_wrong_ebook_400(self, client, db, make_user,
                                                   as_user, student_user,
                                                   auth_headers, monkeypatch):
        _patch_gateway(monkeypatch)
        owner = _make_approved_instructor(db, make_user, "pay-f@lib.com")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        other = _make_ebook(db, owner, title="Other Book", price=500,
                            status="published", file_path="1/y.pdf")
        as_user(student_user)
        client.post("/api/v1/payments/create-order", json={"ebook_id": ebook.id})
        # notes say ebook.id → verifying against `other` must 400
        assert client.post("/api/v1/payments/verify",
                           json=_signed_verify_body(other.id)).status_code == 400
        # another user redeeming the signed order must 403
        thief = make_user(role="student", email="pay-thief@lib.com")
        r = client.post("/api/v1/payments/verify", json=_signed_verify_body(ebook.id),
                        headers=auth_headers(thief.user_email))
        assert r.status_code == 403


class TestEbookFulfillment:
    def test_fulfill_is_idempotent_on_gateway_payment_id(self, db, make_user):
        from app.services.fulfillment_service import fulfill_ebook_purchase
        owner = _make_approved_instructor(db, make_user, "ff-a@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        for _ in range(2):  # duplicate gateway_payment_id → one grant, one order
            result = fulfill_ebook_purchase(
                db, user=student, ebook_id=ebook.id,
                razorpay_order_id="order_FF1", razorpay_payment_id="pay_FF1",
                paid_amount=500.0)
            db.commit()
        assert result.created_order is False               # second call was a replay
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1
        assert db.query(Payment).filter_by(gateway_payment_id="pay_FF1").count() == 1

    def test_fulfill_missing_ebook_writes_money_and_alerts(self, db, make_user,
                                                           monkeypatch):
        from app.services import fulfillment_service
        from app.services.email_service import EmailService
        alerts = []
        monkeypatch.setattr(EmailService, "send_payment_alert",
                            staticmethod(lambda subj, body: alerts.append(subj)))
        student = make_user(role="student")
        result = fulfillment_service.fulfill_ebook_purchase(
            db, user=student, ebook_id=999999,
            razorpay_order_id="order_FF2", razorpay_payment_id="pay_FF2",
            paid_amount=350.0)
        db.commit()
        assert result.created_order is True                 # capture stays reconcilable
        assert db.query(Payment).filter_by(gateway_payment_id="pay_FF2").count() == 1
        assert db.query(EbookGrant).count() == 0            # nothing grantable
        assert alerts                                        # human paged

    def test_fulfill_stamps_order_id_on_prior_free_claim(self, db, make_user):
        """A free-claim row later purchased keeps ONE row, now tied to the
        money trail (grant_ebook stamps NULL order_id)."""
        from app.services.fulfillment_service import fulfill_ebook_purchase
        owner = _make_approved_instructor(db, make_user, "ff-b@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=500, status="published",
                            file_path="1/x.pdf")
        _grant(db, ebook, student, order_id=None, source="purchase")
        fulfill_ebook_purchase(db, user=student, ebook_id=ebook.id,
                               razorpay_order_id="order_FF3",
                               razorpay_payment_id="pay_FF3", paid_amount=500.0)
        db.commit()
        grant = db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                               user_id=student.id).one()
        assert grant.order_id is not None
```

- [ ] Extend `backend/app/schemas/payment.py` — both `CreateOrderRequest` and
      `VerifyPaymentRequest` gain the field and the validator grows one element (update the
      docstrings to name all four):

```python
    course_id: int | None = None
    bundle_id: int | None = None
    invoice_id: int | None = None
    ebook_id: int | None = None
    # (CreateOrderRequest keeps coupon_code below these)

    @model_validator(mode="after")
    def _exactly_one_target(self):
        targets = [self.course_id, self.bundle_id, self.invoice_id, self.ebook_id]
        if sum(bool(t) for t in targets) != 1:
            raise ValueError(
                "Provide exactly one of course_id, bundle_id, invoice_id, or ebook_id")
        return self
```

- [ ] Add to `backend/app/routers/payments.py` — the order-creation branch function (placed
      next to `_create_invoice_order`):

```python
async def _create_ebook_order(request, db, current_user):
    """Create a Razorpay order for an ebook purchase (spec §2). Server-computed
    price from the Ebook row (discount honored) — coupons are REJECTED on
    ebooks at launch, mirroring bundles. Notes carry an ebook_id + rupee-price
    snapshot so /verify (and the webhook/sweeper) fulfill the exact deal that
    was priced at checkout even if the ebook's price changes later."""
    from app.models.ebook import Ebook, EbookGrant, effective_price_inr

    if request.coupon_code:
        raise HTTPException(status_code=400,
                            detail="Coupons cannot be applied to ebooks")
    ebook = db.query(Ebook).filter(Ebook.id == request.ebook_id).first()
    if not ebook:
        raise HTTPException(status_code=404, detail="Ebook not found")
    if ebook.status != "published":
        # Publish-state re-checked at order creation (spec §2: drafts 400).
        raise HTTPException(status_code=400,
                            detail="Ebook is not available for purchase")
    already = db.query(EbookGrant).filter(
        EbookGrant.ebook_id == ebook.id,
        EbookGrant.user_id == current_user.id).first()
    if already:
        raise HTTPException(status_code=400, detail="You already own this ebook")

    price_inr = effective_price_inr(ebook)
    if price_inr <= 0:
        raise HTTPException(
            status_code=400,
            detail=(f"Free ebooks do not require a payment order — use "
                    f"POST /library/{ebook.id}/claim instead."))

    amount_paise = max(int(round(float(price_inr) * 100)), 100)
    notes = {
        "ebook_id": str(ebook.id),
        "user_id": str(current_user.id),
        "ebook_price_inr": str(price_inr),   # checkout-time snapshot (rupees)
    }
    client = _razorpay_client()
    try:
        order = client.order.create({
            "amount": amount_paise, "currency": "INR",
            "receipt": f"ebook_{ebook.id}_user_{current_user.id}",
            "notes": notes,
        })
    except Exception:
        logger.exception("Razorpay ebook order failed (user=%s ebook=%s)",
                         current_user.id, ebook.id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Could not reach the payment gateway.")
    key_id, _ = _razorpay_creds()
    return {"order_id": order["id"], "amount": order["amount"],
            "currency": order["currency"], "key_id": key_id}
```

  branch it in `create_razorpay_order`, directly under the invoice branch:

```python
    if request.ebook_id is not None:
        return await _create_ebook_order(request, db, current_user)
```

  the verify branch function (placed next to `_verify_invoice_payment`):

```python
async def _verify_ebook_payment(request, db, current_user):
    """Verify a Razorpay payment for an ebook and grant it. Mirrors the
    bundle /verify flow: HMAC signature check, order/user/target match
    against notes, amount check against the checkout-time PRICE SNAPSHOT
    (a price edit between checkout and verify must not orphan the capture),
    then the idempotent fulfillment write."""
    from app.models.ebook import Ebook, effective_price_inr
    from app.services.fulfillment_service import fulfill_ebook_purchase

    razorpay_order_id = request.razorpay_order_id
    razorpay_payment_id = request.razorpay_payment_id
    razorpay_signature = request.razorpay_signature

    _, key_secret = _razorpay_creds()
    if not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway not configured — payment captured but not verified. Contact support.",
        )
    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected_sig = hmac.new(key_secret.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # No published filter: an ebook unpublished between checkout and verify
    # must still fulfill — the buyer already paid (same posture as bundles).
    ebook = db.query(Ebook).filter(Ebook.id == request.ebook_id).first()
    if not ebook:
        raise HTTPException(status_code=404, detail="Ebook not found")

    client = _razorpay_client()
    try:
        order = client.order.fetch(razorpay_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Order not found at gateway")

    notes = order.get("notes") or {}
    if str(notes.get("ebook_id")) != str(ebook.id):
        raise HTTPException(status_code=400, detail="Order does not match ebook")
    if str(notes.get("user_id")) != str(current_user.id):
        raise HTTPException(status_code=403,
                            detail="Order does not belong to this user")

    try:
        snapshot_inr = int(notes.get("ebook_price_inr"))
    except (TypeError, ValueError):
        snapshot_inr = effective_price_inr(ebook)  # hand-built order fallback
    expected_amount = max(int(round(float(snapshot_inr) * 100)), 100)
    if int(order.get("amount", 0)) != expected_amount \
            or int(order.get("amount_paid", 0)) < expected_amount:
        raise HTTPException(status_code=400,
                            detail="Order amount does not match ebook price")

    paid_amount = expected_amount / 100.0
    try:
        fulfill_ebook_purchase(
            db,
            user=current_user,
            ebook_id=ebook.id,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            paid_amount=paid_amount,
            currency=order.get("currency") or "INR",
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Payment verified at gateway but ebook grant write failed "
            "(user_id=%s ebook_id=%s razorpay_payment_id=%s razorpay_order_id=%s)",
            current_user.id, ebook.id, razorpay_payment_id, razorpay_order_id,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Your payment was received. Library access will complete "
                "automatically within a few minutes — do not pay again. "
                f"If it does not appear, contact support quoting payment ID "
                f"{razorpay_payment_id}."
            ),
        )

    return {
        "success": True,
        "message": "Payment verified — ebook added to your library",
        "cohort_id": None,
    }
```

  branch it in `verify_razorpay_payment`, directly under the invoice branch:

```python
    if request.ebook_id is not None:
        return await _verify_ebook_payment(request, db, current_user)
```

- [ ] Add to `backend/app/services/fulfillment_service.py` (below
      `fulfill_bundle_purchase`; template noted in its docstring):

```python
def grant_ebook(
    db: Session, *, ebook_id: int, user_id: int,
    order_id: "int | None", source: str,
) -> bool:
    """Get-or-create one EbookGrant. UNIQUE(ebook_id, user_id) backs the
    race: the loser's transaction fails at commit exactly like the
    gateway_payment_id partial unique index does for payments.

    An existing grant is a no-op EXCEPT that a NULL order_id is stamped with
    this order — a free-claim row later purchased keeps one row, now tied to
    the money trail. `source` is NEVER rewritten on an existing row.

    Returns True only when a new grant was created."""
    from app.models.ebook import EbookGrant

    row = db.query(EbookGrant).filter(
        EbookGrant.ebook_id == ebook_id,
        EbookGrant.user_id == user_id,
    ).first()
    if row is not None:
        if order_id and not row.order_id:
            row.order_id = order_id
        return False
    db.add(EbookGrant(ebook_id=ebook_id, user_id=user_id,
                      order_id=order_id, source=source))
    return True


def fulfill_ebook_purchase(
    db: Session, *,
    user: User,
    ebook_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    paid_amount: float,          # rupees actually captured
    currency: str = "INR",
) -> FulfillmentResult:
    """Write the idempotent Order/OrderItem/Payment/EbookGrant trail for a
    successful ebook purchase. Template: fulfill_bundle_purchase — keyed on
    Payment.gateway_payment_id, converged on by /verify, the webhook
    processor, and the reconciliation sweeper. NEVER touches enrollments
    (spec §2). Does not commit — caller owns commit/rollback."""
    from app.models.ebook import Ebook

    order_row = db.query(Order).join(Payment, Payment.order_id == Order.id).filter(
        Payment.gateway_payment_id == str(razorpay_payment_id)
    ).first()
    created_order = order_row is None

    ebook = db.query(Ebook).filter(Ebook.id == ebook_id).first()
    if ebook is None:
        # Money moved but the product row is gone (delete is 409-blocked once
        # any grant exists, so this is the narrow pre-first-sale window).
        # The Order + Payment are still written below — the capture is real
        # and must stay reconcilable; the alert is the trigger for a human
        # refund or hand-grant. Mirrors the bundle no-resolvable-courses path.
        from app.services.email_service import EmailService
        logger.error(
            "ebook %s fulfillment: ebook missing (user=%s payment=%s)",
            ebook_id, user.id, razorpay_payment_id,
        )
        EmailService.send_payment_alert(
            "ebook payment with no resolvable ebook",
            f"ebook_id={ebook_id} user_id={user.id}\n"
            f"razorpay_payment_id={razorpay_payment_id}\n"
            f"razorpay_order_id={razorpay_order_id}\n"
            f"paid_amount={paid_amount} {currency}\n"
            "Order + Payment were written; NO grant created. "
            "Refund or grant access manually.",
        )

    if created_order:
        list_price = float(ebook.price_inr or 0) if ebook is not None else paid_amount
        order_row = Order(
            user_id=user.id,
            ebook_id=ebook.id if ebook is not None else None,
            order_key=f"EBK_{uuid.uuid4().hex[:12].upper()}",
            order_status=OrderStatus.COMPLETED,
            currency=currency,
            subtotal_amount=list_price,                       # list price (rupees)
            discount_amount=max(0.0, list_price - paid_amount),
            total_amount=paid_amount,                          # what changed hands
            payment_method="razorpay_ebook",
            payment_method_title="Razorpay (ebook)",
            transaction_id=str(razorpay_payment_id),
            billing_email=user.user_email or "",
            date_paid=datetime.now(timezone.utc),
            date_completed=datetime.now(timezone.utc),
        )
        db.add(order_row)
        db.flush()
        if ebook is not None:
            # One OrderItem for the ebook so revenue reports stay meaningful
            # (spec §2). course_id NULL / ebook_id set — 0005 relaxed the FK.
            db.add(OrderItem(
                order_id=order_row.id,
                course_id=None,
                ebook_id=ebook.id,
                order_item_name=ebook.title or f"Ebook {ebook.id}",
                order_item_type="ebook_item",
                quantity=1,
                subtotal=list_price,
                total=paid_amount,
            ))
        db.add(Payment(
            user_id=user.id,
            order_id=order_row.id,
            payment_method="razorpay_ebook",
            gateway_transaction_id=str(razorpay_payment_id),
            gateway_payment_id=str(razorpay_payment_id),
            gateway_order_id=str(razorpay_order_id),
            amount=paid_amount,
            currency=currency,
            payment_status=PaymentStatus.COMPLETED,
            processed_date=datetime.now(timezone.utc),
        ))

    any_new = False
    if ebook is not None:
        # Deliberately NOT gated on created_order — a replay against an
        # existing order self-heals a missing grant (bundle posture).
        any_new = grant_ebook(db, ebook_id=ebook.id, user_id=user.id,
                              order_id=order_row.id, source="purchase")

    return FulfillmentResult(
        created_order=created_order,
        order_id=order_row.id,
        is_new_enrollment=any_new,
        cohort_id=None,
    )
```

- [ ] Update the `payments.py` module docstring's target list and the `create-order`
      docstring to name `ebook_id` among the exactly-one-of targets.
- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_library.py -v`
- [ ] Payment regression sweep: `./.venv/Scripts/python -m pytest tests/test_payment_contracts.py
      tests/test_bundle_checkout.py tests/test_invoice_payments.py tests/test_fulfillment_service.py -v`
      then the full suite — zero new failures.
- [ ] Commit: `feat(library): ebook_id joins create-order/verify contract + idempotent fulfill_ebook_purchase`

---

## Task 6: Webhook + sweeper convergence + free-claim flow (review: opus)

**Files:**
- Modify: `backend/app/services/webhook_processor.py` (`_fulfill_ebook_from_notes` + branch
  in `_handle_payment_captured` + widened order-notes fallback condition)
- Modify: `backend/app/services/reconciliation.py` (ebook branch in
  `reconcile_gateway_orders`; import `fulfill_ebook_purchase`)
- Modify: `backend/app/routers/library.py` (`POST /{ebook_id}/claim`)
- Test: `backend/tests/test_library.py` (append `TestWebhookEbookPath`,
  `TestSweeperEbookPath`, `TestFreeClaim`)

**Interfaces:**
- Produces:
  - webhook `payment.captured` with `notes.ebook_id` → `fulfill_ebook_purchase` (idempotent;
    no-op when `/verify` already fulfilled)
  - sweeper: paid gateway orders with `notes.ebook_id` and no local Payment →
    `fulfill_ebook_purchase` (per-order fault isolation + alert emails, like bundles)
  - `POST /api/v1/library/{ebook_id}/claim` — authed; effective price 0 only; grant
    `source="purchase"`, `order_id NULL`; NO payment objects; idempotent 200
- Consumes: `fulfill_ebook_purchase`, `grant_ebook`, `UnrecoverableEvent`, `EmailService`

**Steps:**

- [ ] Append failing tests:

```python
# ============================================================================
# Task 6: webhook + sweeper convergence, free claim
# ============================================================================


def _captured_event(db, *, ebook, user, payment_id, amount_paise,
                    event_id="evt_lib_1"):
    """A stored payment.captured WebhookEvent whose entity notes carry the
    ebook snapshot (mirrors test_bundle_webhooks' payload builder)."""
    from app.models.webhook_event import WebhookEvent
    event = WebhookEvent(
        event_id=event_id,
        event_type="payment.captured",
        signature_valid=True,
        payload={"event": "payment.captured", "payload": {"payment": {"entity": {
            "id": payment_id,
            "order_id": "order_WH1",
            "amount": amount_paise,
            "currency": "INR",
            "notes": {"ebook_id": str(ebook.id), "user_id": str(user.id),
                      "ebook_price_inr": str(amount_paise // 100)},
        }}}},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


class TestWebhookEbookPath:
    def test_captured_event_grants_ebook(self, db, make_user):
        from app.models.webhook_event import WebhookEventStatus
        from app.services.webhook_processor import process_webhook_event
        owner = _make_approved_instructor(db, make_user, "wh-a@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=350, status="published",
                            file_path="1/x.pdf")
        event = _captured_event(db, ebook=ebook, user=student,
                                payment_id="pay_WH1", amount_paise=35000)
        process_webhook_event(db, event)
        assert event.status == WebhookEventStatus.PROCESSED
        grant = db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                               user_id=student.id).one()
        assert grant.order_id is not None
        assert db.query(Payment).filter_by(gateway_payment_id="pay_WH1").count() == 1

    def test_replay_after_verify_is_noop(self, db, make_user):
        from app.services.fulfillment_service import fulfill_ebook_purchase
        from app.services.webhook_processor import process_webhook_event
        owner = _make_approved_instructor(db, make_user, "wh-b@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=350, status="published",
                            file_path="1/x.pdf")
        # browser /verify path already fulfilled this capture…
        fulfill_ebook_purchase(db, user=student, ebook_id=ebook.id,
                               razorpay_order_id="order_WH2",
                               razorpay_payment_id="pay_WH2", paid_amount=350.0)
        db.commit()
        # …so the webhook replay must not double anything
        event = _captured_event(db, ebook=ebook, user=student,
                                payment_id="pay_WH2", amount_paise=35000,
                                event_id="evt_lib_2")
        process_webhook_event(db, event)
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id).count() == 1
        assert db.query(Order).filter(Order.ebook_id == ebook.id).count() == 1

    def test_unusable_ebook_notes_unrecoverable(self, db, make_user, monkeypatch):
        from app.models.webhook_event import WebhookEvent, WebhookEventStatus
        from app.services.webhook_processor import process_webhook_event
        from app.services.email_service import EmailService
        monkeypatch.setattr(EmailService, "send_payment_alert",
                            staticmethod(lambda *a, **k: None))
        event = WebhookEvent(
            event_id="evt_lib_3", event_type="payment.captured",
            signature_valid=True,
            payload={"event": "payment.captured", "payload": {"payment": {"entity": {
                "id": "pay_WH3", "order_id": "", "amount": 35000,
                "currency": "INR",
                "notes": {"ebook_id": "not-a-number", "user_id": "9"},
            }}}})
        db.add(event)
        db.commit()
        process_webhook_event(db, event)
        assert event.status == WebhookEventStatus.FAILED
        assert event.attempts >= 5  # retries exhausted: retrying can't fix notes


class TestSweeperEbookPath:
    def test_sweeper_fulfills_orphaned_ebook_capture(self, db, make_user):
        from app.services.reconciliation import reconcile_gateway_orders
        owner = _make_approved_instructor(db, make_user, "sw-a@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, price=350, status="published",
                            file_path="1/x.pdf")

        class FakeGatewayClient:
            class order:
                @staticmethod
                def all(params):
                    return {"items": [{
                        "id": "order_SW1", "status": "paid", "amount": 35000,
                        "notes": {"ebook_id": str(ebook.id),
                                  "user_id": str(student.id),
                                  "ebook_price_inr": "350"},
                    }]}

                @staticmethod
                def payments(order_id):
                    return {"items": [{"id": "pay_SW1", "status": "captured",
                                       "amount": 35000, "currency": "INR"}]}

        fulfilled = reconcile_gateway_orders(db, FakeGatewayClient)
        assert fulfilled == 1
        assert db.query(EbookGrant).filter_by(ebook_id=ebook.id,
                                              user_id=student.id).count() == 1
        # second sweep: local Payment now exists → no-op
        assert reconcile_gateway_orders(db, FakeGatewayClient) == 0


class TestFreeClaim:
    def test_claim_free_creates_grant_without_payment_objects(
            self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "cl-a@lib.com")
        student = make_user(role="student")
        free = _make_ebook(db, owner, title="Free Guide", price=0,
                           status="published", file_path="1/x.pdf")
        r = client.post(f"/api/v1/library/{free.id}/claim",
                        headers=auth_headers(student.user_email))
        assert r.status_code == 200, r.text
        assert r.json()["created"] is True
        grant = db.query(EbookGrant).filter_by(ebook_id=free.id,
                                               user_id=student.id).one()
        assert grant.source == "purchase" and grant.order_id is None  # spec §2 verbatim
        assert db.query(Order).count() == 0                # NO payment objects
        assert db.query(Payment).count() == 0

    def test_claim_discount_to_zero_is_free(self, client, db, make_user,
                                            auth_headers):
        owner = _make_approved_instructor(db, make_user, "cl-b@lib.com")
        student = make_user(role="student")
        promo = _make_ebook(db, owner, title="Promo Book", price=500, discount=0,
                            status="published", file_path="1/x.pdf")
        r = client.post(f"/api/v1/library/{promo.id}/claim",
                        headers=auth_headers(student.user_email))
        assert r.status_code == 200  # effective price 0 → claimable

    def test_claim_priced_400_draft_404_reclaim_idempotent(
            self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "cl-c@lib.com")
        student = make_user(role="student")
        h = auth_headers(student.user_email)
        priced = _make_ebook(db, owner, title="Priced", price=500,
                             status="published", file_path="1/x.pdf")
        draft = _make_ebook(db, owner, title="Draft Free", price=0)
        free = _make_ebook(db, owner, title="Free Again", price=0,
                           status="published", file_path="1/y.pdf")
        assert client.post(f"/api/v1/library/{priced.id}/claim",
                           headers=h).status_code == 400
        assert client.post(f"/api/v1/library/{draft.id}/claim",
                           headers=h).status_code == 404
        assert client.post(f"/api/v1/library/{free.id}/claim", headers=h).json()["created"] is True
        r = client.post(f"/api/v1/library/{free.id}/claim", headers=h)
        assert r.status_code == 200 and r.json()["created"] is False
        assert db.query(EbookGrant).filter_by(ebook_id=free.id).count() == 1
        # anon cannot claim
        assert client.post(f"/api/v1/library/{free.id}/claim").status_code in (401, 403)
```

- [ ] Modify `backend/app/services/webhook_processor.py`:
  - add the branch function (next to `_fulfill_bundle_from_notes`):

```python
def _fulfill_ebook_from_notes(db: Session, entity: dict, notes: dict) -> None:
    from app.services.fulfillment_service import fulfill_ebook_purchase

    payment_id = str(entity.get("id"))
    if db.query(Payment).filter(Payment.gateway_payment_id == payment_id).first():
        return  # /verify (or a prior run) already fulfilled — no-op
    try:
        user_id = int(notes.get("user_id"))
        ebook_id = int(notes.get("ebook_id"))
    except (TypeError, ValueError):
        raise UnrecoverableEvent(
            f"unusable ebook notes on payment {payment_id}: {notes!r}")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnrecoverableEvent(
            f"user {user_id} not found for ebook payment {payment_id}")
    fulfill_ebook_purchase(
        db, user=user, ebook_id=ebook_id,
        razorpay_order_id=str(entity.get("order_id") or ""),
        razorpay_payment_id=payment_id,
        paid_amount=int(entity.get("amount") or 0) / 100.0,
        currency=str(entity.get("currency") or "INR"))
```

  - in `_handle_payment_captured`, widen the order-notes fallback condition and add the
    dispatch branch AFTER the invoice branch (order of the whole chain: edgyy →
    subscription → payment-exists → bundle → invoice → ebook → course):

```python
    if ids is None and not notes.get("bundle_id") and not notes.get("invoice_id") \
            and not notes.get("ebook_id"):
        order_notes = _fetch_order_notes(entity.get("order_id"))
        ids = _extract_ids(order_notes)
        if ids is not None or order_notes.get("bundle_id") \
                or order_notes.get("invoice_id") or order_notes.get("ebook_id"):
            notes = order_notes

    if notes.get("bundle_id"):
        _fulfill_bundle_from_notes(db, entity, notes)
        return

    if notes.get("invoice_id"):
        _settle_invoice_from_notes(db, entity, notes)
        return

    if notes.get("ebook_id"):
        _fulfill_ebook_from_notes(db, entity, notes)
        return
```

- [ ] Modify `backend/app/services/reconciliation.py`: import `fulfill_ebook_purchase`
      alongside the other fulfillment imports, and add the ebook branch to
      `reconcile_gateway_orders` directly after the `invoice_id` branch's `continue`
      (before the course fallback):

```python
        if notes.get("ebook_id"):
            try:
                user_id = int(notes.get("user_id"))
                ebook_id = int(notes.get("ebook_id"))
            except (TypeError, ValueError):
                EmailService.send_payment_alert(
                    f"orphaned ebook capture {pay_id} — unusable notes",
                    f"gateway order {order.get('id')} amount={order.get('amount')} "
                    f"notes={notes!r}. Fulfil manually.",
                )
                continue
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                EmailService.send_payment_alert(
                    f"orphaned ebook capture {pay_id} — user missing",
                    f"user_id={user_id} ebook_id={ebook_id} "
                    f"gateway order {order.get('id')}. Fulfil manually.",
                )
                continue
            try:
                fulfill_ebook_purchase(
                    db, user=user, ebook_id=ebook_id,
                    razorpay_order_id=str(order["id"]),
                    razorpay_payment_id=pay_id,
                    paid_amount=int(captured.get("amount") or 0) / 100.0,
                    currency=str(captured.get("currency") or "INR"),
                )
                db.commit()
                fulfilled += 1
                logger.warning(
                    "reconciliation fulfilled orphaned ebook capture %s "
                    "(user %s, ebook %s)", pay_id, user_id, ebook_id,
                )
            except Exception as exc:
                db.rollback()
                logger.exception("reconciliation ebook fulfillment failed for %s", pay_id)
                EmailService.send_payment_alert(
                    f"reconciliation failed for ebook capture {pay_id}",
                    f"error: {exc}. Fulfil manually.",
                )
            continue
```

- [ ] Add the claim endpoint to `backend/app/routers/library.py` (with the other
      `/{ebook_id}`-typed routes, above `GET /{slug}`):

```python
@router.post("/{ebook_id}/claim")
async def claim_free_ebook(
    ebook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Free ebooks only (effective price 0): a direct grant that bypasses
    Razorpay entirely — NO payment objects created (spec §2). Grant is
    source="purchase" with order_id NULL, verbatim per spec. Idempotent:
    re-claiming returns 200 with created=false."""
    from app.services.fulfillment_service import grant_ebook

    ebook = _get_ebook_or_404(db, ebook_id)
    if ebook.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ebook not found")
    if effective_price_inr(ebook) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This ebook is not free — buy it through checkout")
    created = grant_ebook(db, ebook_id=ebook.id, user_id=current_user.id,
                          order_id=None, source="purchase")
    db.commit()
    return {"success": True, "created": created, "ebook_id": ebook.id}
```

- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_library.py -v`
- [ ] Convergence regression sweep: `./.venv/Scripts/python -m pytest tests/test_webhook_endpoint.py
      tests/test_bundle_webhooks.py tests/test_reconciliation.py tests/test_subscription_webhooks.py -v`
      then the full suite — zero new failures.
- [ ] Commit: `feat(library): webhook + sweeper ebook convergence, free-claim flow (no payment objects)`

---

## Task 7: Suggestions endpoint + tests

**Files:**
- Modify: `backend/app/routers/library.py` (`GET /suggestions` — MUST be declared above
  `GET /{slug}`)
- Test: `backend/tests/test_library.py` (append `TestSuggestions`)

**Interfaces:**
- Produces: `GET /api/v1/library/suggestions?course_id=X&limit=3` (authed) →
  `{"suggestions": [ebook dicts], "count": n}` — published only, owned excluded,
  course-linked first, then concept-tag ∩ course title/category WORDS; limit clamped 1..10
- Consumes: `Course`, `Ebook`, `EbookGrant`, `_ebook_dict`

**Steps:**

- [ ] Append failing tests:

```python
# ============================================================================
# Task 7: suggestions
# ============================================================================


class TestSuggestions:
    def _setup(self, db, make_user, course):
        owner = _make_approved_instructor(db, make_user, "sug-a@lib.com")
        # conftest `course` fixture title is used for word matching — link one
        # ebook directly, tag-match another via a title word, leave one
        # irrelevant, one draft, one owned.
        linked = _make_ebook(db, owner, title="Linked Reader", status="published",
                             course_id=course.id, file_path="1/a.pdf")
        title_word = course.post_title.split()[0].lower()
        tagged = _make_ebook(db, owner, title="Tagged Reader", status="published",
                             tags=[title_word], file_path="1/b.pdf")
        _make_ebook(db, owner, title="Unrelated", status="published",
                    tags=["knitting"], file_path="1/c.pdf")
        _make_ebook(db, owner, title="Draft Match", status="draft",
                    course_id=course.id)
        owned = _make_ebook(db, owner, title="Owned Match", status="published",
                            course_id=course.id, file_path="1/d.pdf")
        return linked, tagged, owned

    def test_relevance_owned_exclusion_never_draft(self, client, db, make_user,
                                                   auth_headers, course):
        linked, tagged, owned = self._setup(db, make_user, course)
        student = make_user(role="student")
        _grant(db, owned, student)
        r = client.get("/api/v1/library/suggestions",
                       params={"course_id": course.id, "limit": 3},
                       headers=auth_headers(student.user_email))
        assert r.status_code == 200, r.text
        titles = [e["title"] for e in r.json()["suggestions"]]
        assert titles[0] == "Linked Reader"       # course_id match ranks first
        assert "Tagged Reader" in titles          # tokenized tag ∩ title words
        assert "Owned Match" not in titles        # owned excluded
        assert "Draft Match" not in titles        # never drafts
        assert "Unrelated" not in titles

    def test_limit_clamped_and_auth_required(self, client, db, make_user,
                                             auth_headers, course):
        self._setup(db, make_user, course)
        student = make_user(role="student", email="sug-s2@lib.com")
        r = client.get("/api/v1/library/suggestions",
                       params={"course_id": course.id, "limit": 999},
                       headers=auth_headers(student.user_email))
        assert r.status_code == 200
        assert r.json()["count"] <= 10
        assert client.get("/api/v1/library/suggestions",
                          params={"course_id": course.id}).status_code in (401, 403)

    def test_unknown_course_404_and_never_cached(self, client, db, make_user,
                                                 auth_headers, course):
        student = make_user(role="student", email="sug-s3@lib.com")
        h = auth_headers(student.user_email)
        assert client.get("/api/v1/library/suggestions",
                          params={"course_id": 999999}, headers=h).status_code == 404
        self._setup(db, make_user, course)
        r = client.get("/api/v1/library/suggestions",
                       params={"course_id": course.id}, headers=h)
        assert "s-maxage" not in r.headers.get("Cache-Control", "")  # per-user body
```

- [ ] Implement in `backend/app/routers/library.py`, inserted between `GET /me` and the
      instructor block (i.e. ABOVE `GET /{slug}`):

```python
@router.get("/suggestions")
async def suggest_ebooks(
    course_id: int,
    limit: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
):
    """Suggested reading for a course (spec §4): published ebooks, the ones
    LINKED to the course first, then concept-tag matches — the ∩ is computed
    on tokenized lowercase words of the course title + category, so a
    multiword tag like "data structures" matches a course named "Data
    Structures in Python". Excludes ebooks the caller already owns. Authed
    and per-user — NEVER edge-cached (Global Constraint 7)."""
    limit = max(1, min(int(limit), 10))
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Course not found")

    owned_ids = {g.ebook_id for g in db.query(EbookGrant.ebook_id).filter(
        EbookGrant.user_id == current_user.id).all()}
    published = (db.query(Ebook)
                 .filter(Ebook.status == "published")
                 .order_by(Ebook.created_at.desc())
                 .all())

    course_words = set(_WORD_RE.findall(
        f"{course.post_title or ''} {course.course_category or ''}".lower()))

    linked, tagged = [], []
    for ebook in published:
        if ebook.id in owned_ids:
            continue
        if ebook.course_id == course.id:
            linked.append(ebook)
            continue
        tag_words = set()
        for t in ebook.concept_tags or []:
            tag_words |= set(_WORD_RE.findall(str(t).lower()))
        if tag_words & course_words:
            tagged.append(ebook)

    rows = (linked + tagged)[:limit]
    titles = _course_titles(db, rows)
    return {"suggestions": [_ebook_dict(e, course_title=titles.get(e.course_id))
                            for e in rows],
            "count": len(rows)}
```

  NOTE: `db.query(EbookGrant.ebook_id)` returns Row tuples — use
  `{row[0] for row in ...}` or keep the model query; the implementer picks one and the test
  suite catches the wrong choice.
- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_library.py -v`
- [ ] Full suite green: `./.venv/Scripts/python -m pytest tests/ -v`
- [ ] Commit: `feat(library): course-aware suggestions endpoint (linked-first, tag-word match, owned-excluded)`

---

## Task 8: Frontend api/library.ts + store page + public nav + routes

**Files:**
- Modify: `frontend/src/api/axios.ts` (add `'/library'` to `noSlashEndpoints`, ~line 33 block)
- Create: `frontend/src/api/library.ts`
- Create: `frontend/src/pages/library.tsx` (store page)
- Modify: `frontend/src/components/public/PublicHeader.tsx` (Library link in BOTH the desktop
  nav ~line 99 and the mobile nav ~line 236 — the RENDERED header per the launch-surface
  lesson; `components/layout/header.tsx` is dead, do NOT touch it)
- Modify: `frontend/src/App.tsx` (routes `/library`, `/library/:slug` — MainLayout, public,
  next to the `/bundles` routes ~line 304)
- Test: `frontend/src/pages/__tests__/library.test.tsx`

**Interfaces:**
- Produces: typed API client (`Ebook`, `EbookDetail`, `MyLibraryItem`, fetch/claim/order/
  verify/download helpers, instructor CRUD helpers), `/library` store route with category
  tabs + search + course chips + sample badges
- Consumes: `api` axios instance, `MainLayout`, backend endpoints from Tasks 3–7

**Steps:**

- [ ] `frontend/src/api/axios.ts`: in the `noSlashEndpoints` array add a section:

```ts
        // Library endpoints (redirect_slashes=False backend-wide — the
        // gamification-404 lesson; covers /library and every subpath)
        '/library',
```

- [ ] Create `frontend/src/api/library.ts`:

```ts
import { api } from './axios'

export type EbookCategory = 'book' | 'guide' | 'lecture_notes'

export const CATEGORY_LABELS: Record<EbookCategory, string> = {
  book: 'Books',
  guide: 'Guides',
  lecture_notes: 'Lecture Notes',
}

export interface Ebook {
  id: number
  owner_id: number
  slug: string
  title: string
  description: string
  category: EbookCategory
  price_inr: number
  discount_price_inr: number | null
  effective_price_inr: number
  cover_image: string
  page_count: number | null
  concept_tags: string[]
  course_id: number | null
  course_title: string | null
  status: 'draft' | 'published'
  has_file: boolean
  has_sample: boolean
  file_size_bytes: number
  created_at: string
  updated_at: string
}

export interface EbookDetail extends Ebook {
  owned?: boolean // present ONLY when authenticated
}

export interface MyLibraryItem extends Ebook {
  granted_at: string
  downloadable: boolean
}

export interface EbookSales {
  ebook_id: number
  count: number
  gross_inr: number
  last_sale_at: string | null
  buyers: { display_name: string; source: string; granted_at: string }[]
}

export interface LibraryFilters {
  category?: EbookCategory
  q?: string
  course_id?: number
  tag?: string
}

export interface EbookPayload {
  title: string
  description: string
  category: EbookCategory
  price_inr: number
  discount_price_inr?: number | null
  cover_image?: string
  page_count?: number | null
  concept_tags?: string[]
  course_id?: number | null
}

// ---- public / student -------------------------------------------------------

export const fetchLibrary = async (filters: LibraryFilters = {}): Promise<Ebook[]> => {
  const { data } = await api.get('/library', { params: filters })
  return data.ebooks
}

export const fetchEbook = async (slug: string): Promise<EbookDetail> => {
  const { data } = await api.get(`/library/${slug}`)
  return data
}

export const fetchMyLibrary = async (): Promise<MyLibraryItem[]> => {
  const { data } = await api.get('/library/me')
  return data.items
}

export const claimEbook = async (
  id: number
): Promise<{ success: boolean; created: boolean; ebook_id: number }> => {
  const { data } = await api.post(`/library/${id}/claim`)
  return data
}

export const fetchSuggestions = async (courseId: number, limit = 3): Promise<Ebook[]> => {
  const { data } = await api.get('/library/suggestions', {
    params: { course_id: courseId, limit },
  })
  return data.suggestions
}

export const createEbookOrder = async (
  ebookId: number
): Promise<{ order_id: string; amount: number; currency: string; key_id: string }> => {
  const { data } = await api.post('/payments/create-order', { ebook_id: ebookId })
  return data
}

export const verifyEbookPayment = async (p: {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
  ebook_id: number
}): Promise<{ success: boolean; message: string }> => {
  const { data } = await api.post('/payments/verify', p)
  return data
}

// The JWT rides the axios Authorization header, so /download can't be a bare
// <a href> — fetch the bytes and hand the browser an object URL. Samples are
// anon-public and stay plain links (see sampleUrl).
export const downloadEbook = async (ebook: Pick<Ebook, 'id' | 'slug'>): Promise<void> => {
  const res = await api.get(`/library/${ebook.id}/download`, { responseType: 'blob' })
  const contentType = String(res.headers['content-type'] ?? '')
  const ext = contentType.includes('epub') ? 'epub' : 'pdf'
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `${ebook.slug}.${ext}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const sampleUrl = (id: number): string => `/api/v1/library/${id}/sample`

// ---- instructor / admin -----------------------------------------------------

export const fetchMyEbooks = async (): Promise<Ebook[]> => {
  const { data } = await api.get('/library/mine')
  return data.ebooks
}

export const createEbook = async (payload: EbookPayload): Promise<Ebook> => {
  const { data } = await api.post('/library', payload)
  return data
}

export const updateEbook = async (
  id: number,
  payload: Partial<EbookPayload>
): Promise<Ebook> => {
  const { data } = await api.put(`/library/${id}`, payload)
  return data
}

export const uploadEbookFile = async (
  id: number,
  file: File,
  kind: 'file' | 'sample',
  onProgress?: (percent: number) => void
): Promise<Ebook> => {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post(`/library/${id}/${kind}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

export const publishEbook = async (id: number): Promise<Ebook> => {
  const { data } = await api.post(`/library/${id}/publish`)
  return data
}

export const unpublishEbook = async (id: number): Promise<Ebook> => {
  const { data } = await api.post(`/library/${id}/unpublish`)
  return data
}

export const deleteEbook = async (id: number): Promise<{ success: boolean }> => {
  const { data } = await api.delete(`/library/${id}`)
  return data
}

export const fetchEbookSales = async (id: number): Promise<EbookSales> => {
  const { data } = await api.get(`/library/${id}/sales`)
  return data
}

// ---- shared display helpers -------------------------------------------------

export const formatPrice = (e: Pick<Ebook, 'effective_price_inr'>): string =>
  e.effective_price_inr === 0 ? 'Free' : `₹${e.effective_price_inr}`

export const isDiscounted = (
  e: Pick<Ebook, 'discount_price_inr' | 'price_inr'>
): boolean => e.discount_price_inr !== null && e.discount_price_inr < e.price_inr
```

- [ ] Create `frontend/src/pages/library.tsx` (store: tabs / search / course chips / cards —
      plain useState+useEffect like bundles.tsx, no new deps):

```tsx
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, FileText, Loader2, Search } from 'lucide-react'
import {
  CATEGORY_LABELS,
  Ebook,
  EbookCategory,
  fetchLibrary,
  formatPrice,
  isDiscounted,
} from '@/api/library'

const TABS: { key: EbookCategory | 'all'; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'book', label: CATEGORY_LABELS.book },
  { key: 'guide', label: CATEGORY_LABELS.guide },
  { key: 'lecture_notes', label: CATEGORY_LABELS.lecture_notes },
]

export function EbookPriceTag({ ebook }: { ebook: Ebook }) {
  return (
    <span className="flex items-baseline gap-2">
      <span className="font-semibold text-gray-900">{formatPrice(ebook)}</span>
      {isDiscounted(ebook) && (
        <span className="text-sm text-gray-400 line-through">₹{ebook.price_inr}</span>
      )}
    </span>
  )
}

export default function LibraryStorePage() {
  const [ebooks, setEbooks] = useState<Ebook[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<EbookCategory | 'all'>('all')
  const [q, setQ] = useState('')
  const [courseFilter, setCourseFilter] = useState<number | null>(null)

  useEffect(() => {
    setLoading(true)
    setError('')
    fetchLibrary()
      .then(setEbooks)
      .catch(() => setError('Could not load the library'))
      .finally(() => setLoading(false))
  }, [])

  // Course filter chips: derived from what the loaded catalog actually links.
  const courseChips = useMemo(() => {
    const seen = new Map<number, string>()
    for (const e of ebooks) {
      if (e.course_id && e.course_title && !seen.has(e.course_id)) {
        seen.set(e.course_id, e.course_title)
      }
    }
    return Array.from(seen, ([id, title]) => ({ id, title }))
  }, [ebooks])

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return ebooks.filter((e) => {
      if (tab !== 'all' && e.category !== tab) return false
      if (courseFilter !== null && e.course_id !== courseFilter) return false
      if (needle && !e.title.toLowerCase().includes(needle)) return false
      return true
    })
  }, [ebooks, tab, q, courseFilter])

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Library</h1>
        <p className="text-gray-600 mb-6">
          Ebooks, guides and lecture notes from our instructors.
        </p>

        <div className="flex flex-wrap items-center gap-2 mb-4" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 rounded-full text-sm font-medium ${
                tab === t.key
                  ? 'bg-orange-500 text-white'
                  : 'bg-white text-gray-700 border border-gray-200 hover:bg-orange-50'
              }`}
            >
              {t.label}
            </button>
          ))}
          <div className="relative ml-auto">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search titles…"
              aria-label="Search titles"
              className="pl-9 pr-3 py-2 rounded-lg border border-gray-200 text-sm w-56"
            />
          </div>
        </div>

        {courseChips.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {courseChips.map((c) => (
              <button
                key={c.id}
                onClick={() => setCourseFilter(courseFilter === c.id ? null : c.id)}
                className={`px-3 py-1 rounded-full text-xs border ${
                  courseFilter === c.id
                    ? 'bg-orange-100 border-orange-400 text-orange-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-100'
                }`}
              >
                {c.title}
              </button>
            ))}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
          </div>
        ) : error ? (
          <p className="text-red-600 py-12 text-center">{error}</p>
        ) : visible.length === 0 ? (
          <p className="text-gray-500 py-12 text-center">
            No titles match — try another category or search.
          </p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {visible.map((ebook) => (
              <Link
                key={ebook.id}
                to={`/library/${ebook.slug}`}
                className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                <div className="aspect-[3/4] bg-orange-50 flex items-center justify-center">
                  {ebook.cover_image ? (
                    <img
                      src={ebook.cover_image}
                      alt={ebook.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <BookOpen className="h-12 w-12 text-orange-300" />
                  )}
                </div>
                <div className="p-3">
                  <p className="text-xs uppercase tracking-wide text-gray-400">
                    {CATEGORY_LABELS[ebook.category]}
                  </p>
                  <h3 className="font-medium text-gray-900 line-clamp-2">{ebook.title}</h3>
                  <div className="mt-2 flex items-center justify-between">
                    <EbookPriceTag ebook={ebook} />
                    {ebook.has_sample && (
                      <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                        <FileText className="h-3 w-3" /> Sample
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] `frontend/src/components/public/PublicHeader.tsx`: add a "Library" link pointing to
      `/library` in BOTH nav blocks, cloning the existing Bundles `<Link>` verbatim
      (desktop ~line 99, mobile ~line 236) — same classNames, placed between Bundles and
      Membership.
- [ ] `frontend/src/App.tsx`: `import LibraryStorePage from '@/pages/library'` next to the
      BundlesPage import, and add next to the `/bundles` routes:

```tsx
              <Route path="/library" element={
                <MainLayout>
                  <LibraryStorePage />
                </MainLayout>
              } />
```

  (`/library/:slug` is added in Task 9 with the detail page.)
- [ ] Write `frontend/src/pages/__tests__/library.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LibraryStorePage from '@/pages/library'
import type { Ebook } from '@/api/library'

const ebook = (over: Partial<Ebook>): Ebook => ({
  id: 1, owner_id: 1, slug: 'x-1', title: 'X', description: '',
  category: 'book', price_inr: 100, discount_price_inr: null,
  effective_price_inr: 100, cover_image: '', page_count: null,
  concept_tags: [], course_id: null, course_title: null, status: 'published',
  has_file: true, has_sample: false, file_size_bytes: 10,
  created_at: '', updated_at: '', ...over,
})

vi.mock('@/api/library', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@/api/library')>()
  return { ...mod, fetchLibrary: vi.fn() }
})
import { fetchLibrary } from '@/api/library'

const CATALOG = [
  ebook({ id: 1, slug: 'algebra-1', title: 'Algebra Book', category: 'book' }),
  ebook({ id: 2, slug: 'notes-2', title: 'Algebra Notes', category: 'lecture_notes',
          course_id: 5, course_title: 'Algebra 101', has_sample: true,
          price_inr: 500, discount_price_inr: 350, effective_price_inr: 350 }),
  ebook({ id: 3, slug: 'free-3', title: 'Free Guide', category: 'guide',
          price_inr: 0, effective_price_inr: 0 }),
]

describe('LibraryStorePage', () => {
  beforeEach(() => {
    vi.mocked(fetchLibrary).mockResolvedValue(CATALOG)
  })

  const renderPage = () =>
    render(<MemoryRouter><LibraryStorePage /></MemoryRouter>)

  it('renders all published titles with prices and badges', async () => {
    renderPage()
    expect(await screen.findByText('Algebra Book')).toBeInTheDocument()
    expect(screen.getByText('Free')).toBeInTheDocument()          // price 0
    expect(screen.getByText('₹350')).toBeInTheDocument()          // discounted
    expect(screen.getByText('₹500')).toBeInTheDocument()          // struck-through list
    expect(screen.getByText('Sample')).toBeInTheDocument()
  })

  it('category tab filters the grid', async () => {
    renderPage()
    await screen.findByText('Algebra Book')
    fireEvent.click(screen.getByRole('tab', { name: 'Guides' }))
    expect(screen.queryByText('Algebra Book')).not.toBeInTheDocument()
    expect(screen.getByText('Free Guide')).toBeInTheDocument()
  })

  it('search narrows by title', async () => {
    renderPage()
    await screen.findByText('Algebra Book')
    fireEvent.change(screen.getByLabelText('Search titles'),
                     { target: { value: 'notes' } })
    expect(screen.queryByText('Algebra Book')).not.toBeInTheDocument()
    expect(screen.getByText('Algebra Notes')).toBeInTheDocument()
  })

  it('course chip toggles a course filter', async () => {
    renderPage()
    await screen.findByText('Algebra Book')
    fireEvent.click(screen.getByRole('button', { name: 'Algebra 101' }))
    await waitFor(() =>
      expect(screen.queryByText('Free Guide')).not.toBeInTheDocument())
    expect(screen.getByText('Algebra Notes')).toBeInTheDocument()
  })
})
```

- [ ] Verify: `npx vitest run src/pages/__tests__/library.test.tsx`; `npm run type-check`;
      `npm run lint`.
- [ ] Commit: `feat(library-web): api client, store page with tabs/search/chips, public nav + route`

---

## Task 9: Detail page (buy / claim / owned) + My Library page

**Files:**
- Create: `frontend/src/pages/library-detail.tsx`
- Create: `frontend/src/pages/my-library.tsx`
- Modify: `frontend/src/App.tsx` (routes `/library/:slug` public + `/my-library` protected)
- Modify: `frontend/src/components/dashboard/nav-configs.ts` (STUDENT_NAV: "Library" +
  "My Library")
- Test: `frontend/src/pages/__tests__/library-detail.test.tsx`,
  `frontend/src/pages/__tests__/my-library.test.tsx`

**Interfaces:**
- Produces: detail page with sample download, Buy (existing Razorpay checkout flow, mirroring
  `bundle-detail.tsx` exactly), "Get free" claim, "Go to my library" when owned; `/my-library`
  owned grid with blob downloads
- Consumes: `api/library.ts`, `useAuthStore`, `react-hot-toast`

**Steps:**

- [ ] Create `frontend/src/pages/library-detail.tsx`. The Razorpay loader + handler are
      copied from `pages/bundle-detail.tsx` (the canonical checkout entry) with the
      bundle order/verify calls swapped for the ebook ones:

```tsx
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ArrowLeft, BookOpen, Download, Loader2 } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import {
  CATEGORY_LABELS,
  claimEbook,
  createEbookOrder,
  EbookDetail,
  fetchEbook,
  formatPrice,
  isDiscounted,
  sampleUrl,
  verifyEbookPayment,
} from '@/api/library'

const ensureRazorpayLoaded = async (): Promise<void> => {
  if ((window as any).Razorpay) return
  await new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]'
    )
    if (existing) {
      if ((window as any).Razorpay) return resolve()
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () =>
        reject(new Error('Failed to load Razorpay SDK')))
      return
    }
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Razorpay SDK'))
    document.body.appendChild(script)
  })
  if (!(window as any).Razorpay) {
    throw new Error(
      'Razorpay SDK did not initialize. Please disable ad-blockers and retry.')
  }
}

export default function LibraryDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const [ebook, setEbook] = useState<EbookDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    if (!slug) return
    setLoading(true)
    setNotFound(false)
    fetchEbook(slug)
      .then(setEbook)
      .catch((err: any) => {
        if (err?.response?.status === 404) setNotFound(true)
        else setError('Could not load this ebook')
      })
      .finally(() => setLoading(false))
  }, [slug])

  useEffect(load, [load])

  const requireLogin = (): boolean => {
    if (isAuthenticated) return false
    navigate(`/login?redirect=${encodeURIComponent(`/library/${slug}`)}`)
    return true
  }

  const handleClaim = async () => {
    if (!ebook || requireLogin()) return
    setBusy(true)
    try {
      await claimEbook(ebook.id)
      toast.success('Added to your library.')
      navigate('/my-library')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not claim this ebook')
    } finally {
      setBusy(false)
    }
  }

  const handleBuy = async () => {
    if (!ebook || requireLogin()) return
    setBusy(true)
    setError('')
    try {
      const order = await createEbookOrder(ebook.id)
      await ensureRazorpayLoaded()
      const rzp = new (window as any).Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency || 'INR',
        name: 'SashaInfinity',
        description: ebook.title,
        order_id: order.order_id,
        prefill: {
          name: user ? `${user.first_name ?? ''} ${user.last_name ?? ''}`.trim() : '',
          email: user?.user_email ?? '',
        },
        theme: { color: '#f97316' },
        // Never grant anything client-side — the handler only verifies with
        // the server and then navigates. Access is confirmed server-side.
        handler: async (response: any) => {
          try {
            await verifyEbookPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              ebook_id: ebook.id,
            })
            toast.success('Payment confirmed — the ebook is in your library.')
            navigate('/my-library')
          } catch (verifyErr: any) {
            const message =
              verifyErr?.response?.data?.detail ??
              'Payment verification failed. Please contact support before paying again.'
            setError(message)
            toast.error(message)
          } finally {
            setBusy(false)
          }
        },
        modal: {
          ondismiss: () => {
            toast.error('Payment cancelled')
            setBusy(false)
          },
        },
      })
      rzp.on('payment.failed', (resp: any) => {
        toast.error(resp?.error?.description || 'Payment failed')
        setBusy(false)
      })
      rzp.open()
    } catch (e: any) {
      const message = e?.response?.data?.detail ?? 'Could not start payment'
      setError(message)
      toast.error(message)
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    )
  }

  if (notFound || !ebook) {
    return (
      <div className="min-h-screen bg-gray-50 py-12">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <p className="text-gray-600 mb-4">This ebook could not be found.</p>
          <Link to="/library" className="text-orange-600 hover:underline inline-flex items-center gap-1">
            <ArrowLeft className="h-4 w-4" /> Back to the library
          </Link>
        </div>
      </div>
    )
  }

  const isFree = ebook.effective_price_inr === 0

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 grid md:grid-cols-[280px_1fr] gap-8">
        <div className="aspect-[3/4] bg-orange-50 rounded-xl overflow-hidden flex items-center justify-center">
          {ebook.cover_image ? (
            <img src={ebook.cover_image} alt={ebook.title} className="w-full h-full object-cover" />
          ) : (
            <BookOpen className="h-16 w-16 text-orange-300" />
          )}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-400">
            {CATEGORY_LABELS[ebook.category]}
          </p>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{ebook.title}</h1>
          {ebook.page_count && (
            <p className="text-sm text-gray-500 mt-1">{ebook.page_count} pages</p>
          )}
          <div className="mt-3 flex items-baseline gap-3">
            <span className="text-2xl font-semibold text-gray-900">{formatPrice(ebook)}</span>
            {isDiscounted(ebook) && (
              <span className="text-lg text-gray-400 line-through">₹{ebook.price_inr}</span>
            )}
          </div>
          <p className="text-gray-700 mt-4 whitespace-pre-line">{ebook.description}</p>

          {error && <p className="text-red-600 mt-4">{error}</p>}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            {ebook.owned ? (
              <Link
                to="/my-library"
                className="px-6 py-3 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700"
              >
                Go to my library
              </Link>
            ) : isFree ? (
              <button
                onClick={handleClaim}
                disabled={busy}
                className="px-6 py-3 rounded-lg bg-orange-500 text-white font-medium hover:bg-orange-600 disabled:opacity-50"
              >
                {busy ? 'Adding…' : 'Get free'}
              </button>
            ) : (
              <button
                onClick={handleBuy}
                disabled={busy}
                className="px-6 py-3 rounded-lg bg-orange-500 text-white font-medium hover:bg-orange-600 disabled:opacity-50"
              >
                {busy ? 'Starting payment…' : `Buy for ${formatPrice(ebook)}`}
              </button>
            )}
            {ebook.has_sample && (
              <a
                href={sampleUrl(ebook.id)}
                target="_blank"
                rel="noreferrer"
                className="px-6 py-3 rounded-lg border border-gray-300 text-gray-700 font-medium hover:bg-gray-100 inline-flex items-center gap-2"
              >
                <Download className="h-4 w-4" /> Download sample
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] Create `frontend/src/pages/my-library.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { BookOpen, Download, Loader2 } from 'lucide-react'
import { downloadEbook, fetchMyLibrary, MyLibraryItem } from '@/api/library'

export default function MyLibraryPage() {
  const [items, setItems] = useState<MyLibraryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState<number | null>(null)

  useEffect(() => {
    fetchMyLibrary()
      .then(setItems)
      .catch(() => setError('Could not load your library'))
      .finally(() => setLoading(false))
  }, [])

  const handleDownload = async (item: MyLibraryItem) => {
    setDownloading(item.id)
    try {
      await downloadEbook(item)
    } catch {
      toast.error('Download failed — please try again')
    } finally {
      setDownloading(null)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">My Library</h1>
      {error ? (
        <p className="text-red-600">{error}</p>
      ) : items.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 mb-4">You don't own any ebooks yet.</p>
          <Link to="/library" className="text-orange-600 hover:underline">
            Browse the library
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {items.map((item) => (
            <div key={item.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <Link to={`/library/${item.slug}`} className="block aspect-[3/4] bg-orange-50 flex items-center justify-center">
                {item.cover_image ? (
                  <img src={item.cover_image} alt={item.title} className="w-full h-full object-cover" />
                ) : (
                  <BookOpen className="h-12 w-12 text-orange-300" />
                )}
              </Link>
              <div className="p-3">
                <h3 className="font-medium text-gray-900 line-clamp-2">{item.title}</h3>
                <button
                  onClick={() => handleDownload(item)}
                  disabled={!item.downloadable || downloading === item.id}
                  className="mt-2 w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600 disabled:opacity-50"
                >
                  <Download className="h-4 w-4" />
                  {downloading === item.id ? 'Downloading…' : 'Download'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] `frontend/src/App.tsx`: import both pages and add, next to the Task 8 route:

```tsx
              <Route path="/library/:slug" element={
                <MainLayout>
                  <LibraryDetailPage />
                </MainLayout>
              } />
```

  and with the student routes (mirroring `/my-courses`):

```tsx
              <Route path="/my-library" element={
                <ProtectedRoute>
                  <StudentLayout><MyLibraryPage /></StudentLayout>
                </ProtectedRoute>
              } />
```

- [ ] `frontend/src/components/dashboard/nav-configs.ts`: import `Library` from
      `lucide-react` in the existing icon import, and add to `STUDENT_NAV` after the
      "Browse" entry:

```ts
  { kind: 'link', to: '/library',    label: 'Library',    icon: Library, matchPrefix: '/library' },
  { kind: 'link', to: '/my-library', label: 'My Library', icon: BookOpen, matchPrefix: '/my-library' },
```

- [ ] Write `frontend/src/pages/__tests__/library-detail.test.tsx` — mock `@/api/library`
      (as in Task 8) plus `@/store/auth` (authenticated user) and assert the four states:
  - `owned: true` → "Go to my library" link rendered, no Buy button;
  - `effective_price_inr: 0` → "Get free" button; clicking calls `claimEbook(id)` once and
    navigates (`useNavigate` mocked via `MemoryRouter` + spy);
  - priced + `owned: false` → "Buy for ₹350" button; clicking calls `createEbookOrder(id)`
    (Razorpay `window.Razorpay` stubbed with `vi.fn(() => ({ on: vi.fn(), open: vi.fn() }))`);
  - `has_sample: true` → sample link with `href` = `/api/v1/library/{id}/sample`.
- [ ] Write `frontend/src/pages/__tests__/my-library.test.tsx` — mock `fetchMyLibrary` with
      two items (one `downloadable: false`); assert grid renders both, the download button
      of the non-downloadable one is disabled, and clicking the enabled one calls
      `downloadEbook` once.
- [ ] Verify: `npx vitest run src/pages/__tests__`; `npm run type-check`; `npm run lint`.
- [ ] Commit: `feat(library-web): detail page with buy/claim via existing checkout, My Library page + nav`

---

## Task 10: Instructor manager pages + routes + nav

**Files:**
- Create: `frontend/src/pages/instructor/library.tsx` (list + editor + sales panel in one
  page module, matching how `pages/instructor/games.tsx` bundles list + management)
- Modify: `frontend/src/App.tsx` (routes `/instructor/library`, mirroring
  `/instructor/games`'s `ProtectedRoute` + `InstructorLayout` wrappers ~line 702)
- Modify: `frontend/src/components/dashboard/nav-configs.ts` (INSTRUCTOR_NAV entry)
- Test: `frontend/src/pages/__tests__/instructor-library.test.tsx`

**Interfaces:**
- Produces: instructor manager at `/instructor/library` — my-ebooks table (status, price,
  file/sample presence, sales count), metadata editor (create + edit), upload buttons with
  progress bars, publish gate messaging ("file required"), sales panel per ebook
- Consumes: `api/library.ts` instructor helpers (Task 8)

**Steps:**

- [ ] Create `frontend/src/pages/instructor/library.tsx`. Structure (one file, three
      sections — mirror games.tsx's list-page conventions; all strings render as React
      text, no `dangerouslySetInnerHTML`):

```tsx
import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { BookOpen, Loader2, Trash2, Upload } from 'lucide-react'
import {
  CATEGORY_LABELS,
  createEbook,
  deleteEbook,
  Ebook,
  EbookCategory,
  EbookPayload,
  EbookSales,
  fetchEbookSales,
  fetchMyEbooks,
  formatPrice,
  publishEbook,
  unpublishEbook,
  updateEbook,
  uploadEbookFile,
} from '@/api/library'

const EMPTY_FORM: EbookPayload = {
  title: '',
  description: '',
  category: 'book',
  price_inr: 0,
  discount_price_inr: null,
  cover_image: '',
  page_count: null,
  concept_tags: [],
  course_id: null,
}

// Client-side mirror of the server rules — blocking, same style as
// games' builderValidation.validateConfigDraft. The server re-validates.
export function validateEbookDraft(form: EbookPayload): string[] {
  const errors: string[] = []
  if (!form.title.trim()) errors.push('Title is required.')
  if (form.title.length > 200) errors.push('Title must be at most 200 characters.')
  if (form.description.length > 5000) errors.push('Description must be at most 5000 characters.')
  if (form.price_inr < 0 || !Number.isInteger(form.price_inr))
    errors.push('Price must be a whole number of rupees (0 or more).')
  if (form.discount_price_inr !== null && form.discount_price_inr !== undefined) {
    if (form.discount_price_inr < 0 || !Number.isInteger(form.discount_price_inr))
      errors.push('Discount price must be a whole number of rupees.')
    else if (form.discount_price_inr >= form.price_inr)
      errors.push('Discount price must be less than the price.')
  }
  const tags = form.concept_tags ?? []
  if (tags.length > 10) errors.push('At most 10 concept tags.')
  if (tags.some((t) => t.trim().length === 0 || t.length > 50))
    errors.push('Each concept tag must be 1–50 characters.')
  return errors
}

function UploadButton({ ebook, kind, onDone }: {
  ebook: Ebook
  kind: 'file' | 'sample'
  onDone: () => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [progress, setProgress] = useState<number | null>(null)
  const accept = kind === 'sample' ? '.pdf' : '.pdf,.epub'
  const present = kind === 'sample' ? ebook.has_sample : ebook.has_file

  const onPick = async (file: File | undefined) => {
    if (!file) return
    setProgress(0)
    try {
      await uploadEbookFile(ebook.id, file, kind, setProgress)
      toast.success(kind === 'sample' ? 'Sample uploaded.' : 'Ebook file uploaded.')
      onDone()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Upload failed')
    } finally {
      setProgress(null)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        aria-label={kind === 'sample' ? 'Upload sample' : 'Upload ebook file'}
        onChange={(e) => onPick(e.target.files?.[0])}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={progress !== null}
        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-300 text-sm hover:bg-gray-100 disabled:opacity-50"
      >
        <Upload className="h-3.5 w-3.5" />
        {progress !== null
          ? `${progress}%`
          : present
            ? (kind === 'sample' ? 'Replace sample' : 'Replace file')
            : (kind === 'sample' ? 'Add sample' : 'Add file')}
      </button>
      {progress !== null && (
        <span className="w-24 h-1.5 bg-gray-200 rounded" role="progressbar"
              aria-valuenow={progress}>
          <span className="block h-1.5 bg-orange-500 rounded"
                style={{ width: `${progress}%` }} />
        </span>
      )}
    </span>
  )
}

export default function InstructorLibraryPage() {
  const [ebooks, setEbooks] = useState<Ebook[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<Ebook | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<EbookPayload>(EMPTY_FORM)
  const [formErrors, setFormErrors] = useState<string[]>([])
  const [tagsInput, setTagsInput] = useState('')
  const [sales, setSales] = useState<EbookSales | null>(null)

  const reload = useCallback(() => {
    fetchMyEbooks()
      .then(setEbooks)
      .catch(() => toast.error('Could not load your library'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(reload, [reload])

  const openEditor = (ebook: Ebook | null) => {
    setSales(null)
    setFormErrors([])
    if (ebook) {
      setEditing(ebook)
      setCreating(false)
      setForm({
        title: ebook.title,
        description: ebook.description,
        category: ebook.category,
        price_inr: ebook.price_inr,
        discount_price_inr: ebook.discount_price_inr,
        cover_image: ebook.cover_image,
        page_count: ebook.page_count,
        concept_tags: ebook.concept_tags,
        course_id: ebook.course_id,
      })
      setTagsInput(ebook.concept_tags.join(', '))
    } else {
      setEditing(null)
      setCreating(true)
      setForm(EMPTY_FORM)
      setTagsInput('')
    }
  }

  const submitForm = async () => {
    const payload: EbookPayload = {
      ...form,
      concept_tags: tagsInput.split(',').map((t) => t.trim()).filter(Boolean),
    }
    const errors = validateEbookDraft(payload)
    setFormErrors(errors)
    if (errors.length) return
    try {
      if (editing) {
        await updateEbook(editing.id, payload)
        toast.success('Saved.')
      } else {
        await createEbook(payload)
        toast.success('Draft created — now upload the ebook file.')
      }
      setCreating(false)
      setEditing(null)
      reload()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Save failed')
    }
  }

  const togglePublish = async (ebook: Ebook) => {
    try {
      if (ebook.status === 'published') {
        await unpublishEbook(ebook.id)
        toast.success('Unpublished — existing buyers keep access.')
      } else {
        await publishEbook(ebook.id)
        toast.success('Published.')
      }
      reload()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not change status')
    }
  }

  const remove = async (ebook: Ebook) => {
    if (!window.confirm(`Delete "${ebook.title}"? This cannot be undone.`)) return
    try {
      await deleteEbook(ebook.id)
      toast.success('Deleted.')
      reload()
    } catch (e: any) {
      // 409: grants exist — surface the server's explanation verbatim
      toast.error(e?.response?.data?.detail ?? 'Could not delete')
    }
  }

  const showSales = async (ebook: Ebook) => {
    try {
      setSales(await fetchEbookSales(ebook.id))
    } catch {
      toast.error('Could not load sales')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Library manager</h1>
        <button
          onClick={() => openEditor(null)}
          className="px-4 py-2 rounded-lg bg-orange-500 text-white font-medium hover:bg-orange-600"
        >
          New ebook
        </button>
      </div>

      {(creating || editing) && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8">
          <h2 className="font-semibold text-gray-900 mb-4">
            {editing ? `Edit: ${editing.title}` : 'New ebook'}
          </h2>
          {formErrors.length > 0 && (
            <ul className="mb-4 text-sm text-red-600 list-disc list-inside" role="alert">
              {formErrors.map((e) => <li key={e}>{e}</li>)}
            </ul>
          )}
          <div className="grid md:grid-cols-2 gap-4">
            <label className="block text-sm">
              Title
              <input value={form.title}
                     onChange={(e) => setForm({ ...form, title: e.target.value })}
                     className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" />
            </label>
            <label className="block text-sm">
              Category
              <select value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value as EbookCategory })}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2">
                {(Object.keys(CATEGORY_LABELS) as EbookCategory[]).map((c) => (
                  <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Price (₹, whole rupees; 0 = free)
              <input type="number" min={0} value={form.price_inr}
                     onChange={(e) => setForm({ ...form, price_inr: Number(e.target.value) })}
                     className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" />
            </label>
            <label className="block text-sm">
              Discount price (₹, optional — must be below the price)
              <input type="number" min={0}
                     value={form.discount_price_inr ?? ''}
                     onChange={(e) => setForm({
                       ...form,
                       discount_price_inr: e.target.value === '' ? null : Number(e.target.value),
                     })}
                     className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" />
            </label>
            <label className="block text-sm md:col-span-2">
              Description
              <textarea value={form.description} rows={4}
                        onChange={(e) => setForm({ ...form, description: e.target.value })}
                        className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" />
            </label>
            <label className="block text-sm md:col-span-2">
              Concept tags (comma-separated, up to 10 — drives lesson/quiz suggestions)
              <input value={tagsInput}
                     onChange={(e) => setTagsInput(e.target.value)}
                     className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2" />
            </label>
          </div>
          <div className="mt-4 flex gap-3">
            <button onClick={submitForm}
                    className="px-4 py-2 rounded-lg bg-orange-500 text-white font-medium hover:bg-orange-600">
              {editing ? 'Save' : 'Create draft'}
            </button>
            <button onClick={() => { setCreating(false); setEditing(null) }}
                    className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-100">
              Cancel
            </button>
          </div>
        </div>
      )}

      {ebooks.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No ebooks yet — create your first draft.</p>
        </div>
      ) : (
        <table className="w-full bg-white border border-gray-200 rounded-xl overflow-hidden text-sm">
          <thead className="bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Price</th>
              <th className="px-4 py-3">Files</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {ebooks.map((ebook) => (
              <tr key={ebook.id} className="border-t border-gray-100">
                <td className="px-4 py-3">
                  <button onClick={() => openEditor(ebook)}
                          className="font-medium text-gray-900 hover:text-orange-600">
                    {ebook.title}
                  </button>
                  <p className="text-xs text-gray-400">{CATEGORY_LABELS[ebook.category]}</p>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${
                    ebook.status === 'published'
                      ? 'bg-green-50 text-green-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {ebook.status}
                  </span>
                  {ebook.status === 'draft' && !ebook.has_file && (
                    <p className="text-xs text-amber-600 mt-1">file required to publish</p>
                  )}
                </td>
                <td className="px-4 py-3">{formatPrice(ebook)}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-1">
                    <UploadButton ebook={ebook} kind="file" onDone={reload} />
                    <UploadButton ebook={ebook} kind="sample" onDone={reload} />
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button onClick={() => togglePublish(ebook)}
                            disabled={ebook.status === 'draft' && !ebook.has_file}
                            title={ebook.status === 'draft' && !ebook.has_file
                              ? 'Upload the ebook file first' : undefined}
                            className="px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50">
                      {ebook.status === 'published' ? 'Unpublish' : 'Publish'}
                    </button>
                    <button onClick={() => showSales(ebook)}
                            className="px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-100">
                      Sales
                    </button>
                    <button onClick={() => remove(ebook)} aria-label={`Delete ${ebook.title}`}
                            className="p-1.5 rounded-lg text-red-600 hover:bg-red-50">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {sales && (
        <div className="mt-8 bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 mb-2">Sales</h2>
          <p className="text-sm text-gray-600">
            {sales.count} owner(s) · gross ₹{sales.gross_inr}
            {sales.last_sale_at && ` · last sale ${new Date(sales.last_sale_at).toLocaleDateString()}`}
          </p>
          <ul className="mt-3 text-sm text-gray-700 space-y-1">
            {sales.buyers.map((b, i) => (
              <li key={i}>
                {b.display_name} · {b.source} ·{' '}
                {new Date(b.granted_at).toLocaleDateString()}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
```

- [ ] `frontend/src/App.tsx`: `import InstructorLibraryPage from '@/pages/instructor/library'`
      next to the InstructorGamesPage import, and add next to the `/instructor/games` routes:

```tsx
              <Route path="/instructor/library" element={
                <ProtectedRoute allowedRoles={['instructor', 'admin']}>
                  <InstructorLayout><InstructorLibraryPage /></InstructorLayout>
                </ProtectedRoute>
              } />
```

  (Match the EXACT wrapper props the `/instructor/games` route uses at ~line 702 — copy
  that block and swap the component; if it passes no `allowedRoles`, drop it here too.)
- [ ] `frontend/src/components/dashboard/nav-configs.ts`: add to `INSTRUCTOR_NAV` after the
      Games entry (reuses the `Library` icon imported in Task 9):

```ts
  { kind: 'link', to: '/instructor/library',     label: 'Library',       icon: Library, matchPrefix: '/instructor/library' },
```

- [ ] Write `frontend/src/pages/__tests__/instructor-library.test.tsx` — mock
      `@/api/library`; assert:
  - `validateEbookDraft` (imported directly): empty title, discount ≥ price, 11 tags, and
    a 51-char tag each produce an error; a valid form produces `[]`;
  - list renders "file required to publish" for a draft with `has_file: false` and its
    Publish button is disabled;
  - submitting the editor with a discount ≥ price shows the error list (role `alert`) and
    does NOT call `createEbook`;
  - a valid create calls `createEbook` with `concept_tags` parsed from the comma input.
- [ ] Verify: `npx vitest run src/pages/__tests__/instructor-library.test.tsx`;
      `npm run type-check`; `npm run lint`.
- [ ] Commit: `feat(library-web): instructor manager (editor, uploads with progress, publish gate, sales panel)`

---

## Task 11: Suggestion surfaces (lesson card + quiz-results card)

**Files:**
- Create: `frontend/src/components/library/SuggestedReading.tsx`
- Modify: `frontend/src/pages/lesson-redesigned.tsx` (card below the lesson content)
- Modify: `frontend/src/pages/quiz-taking.tsx` (dismissible card in the failed-results view)
- Test: `frontend/src/components/library/__tests__/SuggestedReading.test.tsx`

**Interfaces:**
- Produces: `<SuggestedReading courseId={n} title?: string dismissible?: boolean />` —
  React Query cached per course, renders NOTHING when empty/unauthed/error (zero layout
  cost), advisory placement only (no dark patterns: one card, plain links, dismiss is
  final for the session)
- Consumes: `fetchSuggestions`, `@tanstack/react-query` (already app-wide), auth store

**Steps:**

- [ ] Create `frontend/src/components/library/SuggestedReading.tsx`:

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, X } from 'lucide-react'
import { useAuthStore } from '@/store/auth'
import { fetchSuggestions, formatPrice, isDiscounted } from '@/api/library'

interface SuggestedReadingProps {
  courseId: number
  title?: string
  dismissible?: boolean
}

/**
 * Compact "suggested reading" card (spec §5). Renders NOTHING when there are
 * no suggestions, the viewer is anonymous, or the request fails — zero
 * layout cost. Advisory only: plain links to detail pages, no auto-opening
 * checkout, dismiss (where enabled) hides it for the rest of the session.
 * Cached per course via React Query.
 */
export function SuggestedReading({
  courseId,
  title = 'Suggested reading',
  dismissible = false,
}: SuggestedReadingProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const [dismissed, setDismissed] = useState(false)

  const { data: suggestions } = useQuery({
    queryKey: ['library-suggestions', courseId],
    queryFn: () => fetchSuggestions(courseId, 3),
    enabled: isAuthenticated && courseId > 0 && !dismissed,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  if (dismissed || !suggestions || suggestions.length === 0) return null

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4"
         data-testid="suggested-reading">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-orange-500" /> {title}
        </h3>
        {dismissible && (
          <button onClick={() => setDismissed(true)} aria-label="Dismiss suggestions"
                  className="p-1 rounded hover:bg-gray-100 text-gray-400">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      <ul className="space-y-3">
        {suggestions.map((ebook) => (
          <li key={ebook.id}>
            <Link to={`/library/${ebook.slug}`}
                  className="flex items-center gap-3 group">
              <span className="w-10 h-14 rounded bg-orange-50 flex items-center justify-center overflow-hidden shrink-0">
                {ebook.cover_image ? (
                  <img src={ebook.cover_image} alt=""
                       className="w-full h-full object-cover" />
                ) : (
                  <BookOpen className="h-5 w-5 text-orange-300" />
                )}
              </span>
              <span className="min-w-0">
                <span className="block text-sm text-gray-900 group-hover:text-orange-600 truncate">
                  {ebook.title}
                </span>
                <span className="text-sm font-medium text-gray-900">
                  {formatPrice(ebook)}
                  {isDiscounted(ebook) && (
                    <span className="ml-2 text-xs text-gray-400 line-through">
                      ₹{ebook.price_inr}
                    </span>
                  )}
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] `frontend/src/pages/lesson-redesigned.tsx` — two edits:
  1. Import next to the other component imports:
     `import { SuggestedReading } from '@/components/library/SuggestedReading'`
  2. Render the card directly BELOW the lesson content column (after the content-type
     render branches, inside the main content container — find the closing of the player/
     content block around the render branches at ~line 1918 and append as a sibling):

```tsx
              {(numericCourseId || currentCourseId) ? (
                <div className="mt-6">
                  <SuggestedReading courseId={Number(numericCourseId || currentCourseId)} />
                </div>
              ) : null}
```

  (The component itself renders null when there is nothing to show, so this adds zero
  layout when the course has no linked/tagged ebooks.)
- [ ] `frontend/src/pages/quiz-taking.tsx` — two edits:
  1. Same import.
  2. In the results view (the block starting
     `const { percentage, passed, pendingReview, lateSubmission } = result;` ~line 390),
     render after the score summary, ONLY on a submitted attempt that failed
     (`!passed && !pendingReview`), using the quiz's course id already held in state
     (`quiz.courseId`):

```tsx
            {!passed && !pendingReview && quiz && quiz.courseId > 0 && (
              <div className="mt-6 max-w-md mx-auto text-left">
                <SuggestedReading
                  courseId={quiz.courseId}
                  title="Brush up with these"
                  dismissible
                />
              </div>
            )}
```

- [ ] Write `frontend/src/components/library/__tests__/SuggestedReading.test.tsx` — wrap in
      `QueryClientProvider` + `MemoryRouter`; mock `@/api/library` and `@/store/auth`:
  - suggestions present → card renders titles, prices, struck-through original when
    discounted, links to `/library/{slug}`;
  - empty array → `queryByTestId('suggested-reading')` is null (renders nothing);
  - unauthenticated → `fetchSuggestions` is never called and nothing renders;
  - `dismissible` → clicking the dismiss button removes the card.
- [ ] Verify: `npx vitest run src/components/library/__tests__ && npx vitest run`;
      `npm run type-check`; `npm run lint`.
- [ ] Commit: `feat(library-web): suggested-reading card on lesson page + failed quiz results`

---

## Task 12: Seed + docs/DIGITAL_LIBRARY.md + CLAUDE.md entry

**Files:**
- Create: `backend/seed_library_demo.py`
- Create: `docs/DIGITAL_LIBRARY.md`
- Modify: `CLAUDE.md` (worktree root — "Notes for future work" list)

**Steps:**

- [ ] Implement `backend/seed_library_demo.py` (env bootstrap mirrors
      `seed_games_demo.py`; tiny PDFs generated with reportlab — already a dependency):

```python
"""Demo library content for the walkthrough. Throwaway.

Creates 3 PUBLISHED ebooks owned by priya@sashademo.com — one per category;
one free, one priced, one discounted; the lecture notes linked to course 1 —
with tiny real PDFs (reportlab) stored through library_storage so magic-byte
checks and download streaming genuinely work. Idempotent-ish: skips creation
when an ebook with the same title exists.
"""
import io
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./visual_qa.db")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0?socket_connect_timeout=0.05")
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("JWT_SECRET", "y" * 64)
os.environ.setdefault("VIDEO_SECRET", "visual-qa-secret-0123456789abcdef")
os.environ.setdefault("ENVIRONMENT", "development")

from reportlab.lib.pagesizes import A4          # noqa: E402
from reportlab.pdfgen import canvas             # noqa: E402
from starlette.datastructures import UploadFile  # noqa: E402

from app.core.database import SessionLocal      # noqa: E402
from app.models.ebook import Ebook              # noqa: E402
from app.models.user import User                # noqa: E402
from app.services import library_storage        # noqa: E402
from app.services.course_service import _slugify_title  # noqa: E402

COURSE_ID = 1

DEMO_EBOOKS = [
    {"title": "Meiporul Study Companion", "category": "book",
     "price_inr": 499, "discount_price_inr": 349, "page_count": 120,
     "concept_tags": ["meiporul", "tamil"], "course_id": None,
     "description": "A companion volume for Meiporul learners."},
    {"title": "Quick Revision Guide", "category": "guide",
     "price_inr": 0, "discount_price_inr": None, "page_count": 24,
     "concept_tags": ["revision", "basics"], "course_id": None,
     "description": "Free quick-revision guide."},
    {"title": "Course 1 Lecture Notes", "category": "lecture_notes",
     "price_inr": 199, "discount_price_inr": None, "page_count": 60,
     "concept_tags": ["lecture", "notes"], "course_id": COURSE_ID,
     "description": "Full lecture notes for course 1."},
]


def _tiny_pdf(title: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(100, 750, title)
    c.drawString(100, 730, "SashaInfinity demo ebook")
    c.showPage()
    c.save()
    return buf.getvalue()


def main():
    db = SessionLocal()
    instructor = db.query(User).filter(
        User.user_email == "priya@sashademo.com").first()
    if not instructor:
        print("priya@sashademo.com not found — run the demo user seed first.")
        return

    for spec in DEMO_EBOOKS:
        existing = db.query(Ebook).filter(Ebook.title == spec["title"]).first()
        if existing:
            print(f"ebook exists: {spec['title']} -> {existing.id}")
            continue
        pdf = _tiny_pdf(spec["title"])
        upload = UploadFile(filename="demo.pdf", file=io.BytesIO(pdf))
        rel_path, size = library_storage.save_ebook_file(instructor.id, upload)
        ebook = Ebook(
            owner_id=instructor.id,
            slug="pending",
            status="published",
            file_path=rel_path,
            file_size_bytes=size,
            **spec,
        )
        db.add(ebook)
        db.flush()
        base = _slugify_title(ebook.title or "")
        ebook.slug = f"{base}-{ebook.id}" if base else f"ebook-{ebook.id}"
        db.commit()
        print(f"ebook created: {spec['category']} -> {ebook.id} ({ebook.slug})")


if __name__ == "__main__":
    main()
```

- [ ] Write `docs/DIGITAL_LIBRARY.md` with these sections (each fully written out, sourced
      from the spec + the code as built):
  1. **Overview & architecture** — the store, grants, and how the feature EXTENDS (never
     forks) the payment stack; a request-flow sketch of the three convergent fulfillment
     paths ending in `fulfill_ebook_purchase`.
  2. **Security model** — private files under `backend/ebooks/` (never `uploads/`), the
     upload hardening matrix (allowlist, magic bytes, 200MB/5GB, uuid names,
     normalize-and-reassert), grant-gated streaming, drafts-404, unpublish-keeps-access,
     no `file_path` in responses, sample semi-public rationale.
  3. **Payment convergence** — the exactly-one-of contract (now 4 targets), the
     `ebook_price_inr` notes snapshot, coupons-rejected, free-claim flow (no payment
     objects), idempotency keys (`gateway_payment_id`, `UNIQUE(ebook_id, user_id)`), the
     missing-ebook alert path, and PRICE UNITS (whole rupees; paise only at the gateway).
  4. **API reference** — every `/api/v1/library` endpoint plus the payments extension, with
     method, auth, request/response shape, and the 400/403/404/409/413/422 rules.
  5. **Suggestions** — ranking (linked-first, tokenized tag ∩ title/category words),
     owned-exclusion, the two surfaces, advisory-placement policy.
  6. **Frontend map** — `api/library.ts`, pages, nav touchpoints, the axios
     `noSlashEndpoints` requirement, blob-download rationale.
  7. **Ops/deploy** — `alembic upgrade head` (revision 0005, includes the
     `order_items.course_id` relax), create `backend/ebooks/` (or let the app mkdir on
     first upload) and ensure it is bind-mounted in docker-compose alongside
     uploads/invoices; nginx needs NO change (files are app-streamed);
     `seed_library_demo.py` usage; storage-cap tuning constants.
- [ ] Append to `CLAUDE.md`'s "Notes for future work" list:

```markdown
- **Digital Library** (2026-09): ebook/guide/lecture-notes store riding the
  hardened payment stack the way bundles did. Models app/models/ebook.py
  (Ebook + EbookGrant, UNIQUE(ebook_id, user_id)); prices are WHOLE RUPEES
  (price_inr Integer — same unit as courses/bundles, paise only at the
  gateway boundary). Router app/routers/library.py at /api/v1/library
  (fixed-path routes /mine //me //suggestions declared BEFORE /{slug});
  migration backend/alembic/versions/0005_digital_library.py (guarded; also
  adds orders.ebook_id + order_items.ebook_id and relaxes
  order_items.course_id to nullable — ebook OrderItems are
  order_item_type="ebook_item" with course_id NULL). Files are PRIVATE under
  backend/ebooks/{owner_id}/{uuid}.{ext} (NOT uploads/ — nginx-public);
  upload hardening in app/services/library_storage.py (pdf/epub allowlist,
  magic bytes, 200MB file / 5GB per-owner caps, normalize-and-reassert);
  download/sample are authenticated FileResponse streams, never redirects.
  create-order/verify accept exactly one of course_id/bundle_id/invoice_id/
  ebook_id; coupons REJECTED on ebooks; order notes carry an ebook_price_inr
  snapshot; fulfill_ebook_purchase in fulfillment_service.py (idempotent on
  gateway_payment_id, never touches enrollments) converges browser /verify +
  webhook (_fulfill_ebook_from_notes) + reconciliation sweeper. Free ebooks
  (effective price 0): POST /library/{id}/claim — grant source="purchase",
  order_id NULL, NO payment objects. Delete 409s while grants exist;
  unpublish keeps granted access. Store list/detail use
  cache_headers.apply_public_cache (anon-only; detail's owned flag appears
  only on authed = private/no-store responses). NO XP (purchases are money,
  not learning). Traps: '/library' must stay in axios.ts noSlashEndpoints;
  file_path/sample_path must never appear in API responses. Frontend:
  api/library.ts, pages/library.tsx + library-detail.tsx + my-library.tsx +
  instructor/library.tsx, components/library/SuggestedReading.tsx (lesson
  page + failed quiz results, advisory only); public nav lives in the
  RENDERED components/public/PublicHeader.tsx (NOT dead layout/header.tsx);
  docs/DIGITAL_LIBRARY.md.
```

- [ ] Smoke the seed import: `./.venv/Scripts/python -c "import seed_library_demo"` must
      import cleanly with the env defaults (running it needs a seeded dev DB — optional).
- [ ] Final verification sweep:
  - `./.venv/Scripts/python -m pytest tests/ -v` — zero new failures vs the 949P/4S baseline.
  - `npx vitest run` — green.
  - `npm run type-check` && `npm run lint` — zero new issues.
  - `grep -rn "dangerouslySetInnerHTML" frontend/src/pages/library.tsx
    frontend/src/pages/library-detail.tsx frontend/src/pages/my-library.tsx
    frontend/src/pages/instructor/library.tsx frontend/src/components/library` — zero matches.
  - `grep -rn "file_path\|sample_path" backend/app/routers/library.py` — appears only in
    gate checks / storage calls, never in a returned dict.
- [ ] Commit: `docs(library): demo seed, DIGITAL_LIBRARY.md, CLAUDE.md entry`

---

## Spec coverage map (self-review)

| Spec section | Covered by |
|---|---|
| §1 product model (ebooks + ebook_grants, caps, category enum, price unit) | Task 1 (models/migration), Task 3 (API-layer validation), Global Constraints 1–3, 5 |
| §2 payments extension (exactly-one-of + ebook_id, coupons rejected, snapshot, three convergent paths, free claim, OrderItem revenue line) | Tasks 5, 6 (both "review: opus"), Global Constraint 4 |
| §3 file security (private dir, upload hardening, streaming gates, samples) | Tasks 2, 4, Global Constraints 2, 9 |
| §4 backend API (store filters + caching, detail owned flag, /me, claim, download/sample, instructor endpoints, sales panel, noSlash) | Tasks 3, 4, 6, 7, Global Constraints 6–8 |
| §5 suggestive-buying surfaces (lesson card, quiz-results card, store page, detail page, My Library, instructor manager, nav in RENDERED PublicHeader + nav-configs) | Tasks 8, 9, 10, 11 |
| §6 gamification (NO XP, no badge; admin revenue picks up OrderItems automatically) | Global Constraint 10; OrderItem lines in Task 5 |
| §7 tests (binding backend matrix + frontend vitest) | backend: Tasks 1–7 test classes map 1:1 to the §7 list; frontend: Tasks 8–11 |
| §8 docs & seed (DIGITAL_LIBRARY.md, CLAUDE.md entry, seed_library_demo.py) | Task 12 |
| Out of scope | untouched (no DRM/watermarking, no EPUB reader, no rentals, no revenue splits, no coupons on ebooks, no ratings, no company ebook seats) |
