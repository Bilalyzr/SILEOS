# Digital Library & Suggestive Buying — Design Spec

**Date:** 2026-09-03
**Branch:** `digital-library` (worktree `.worktrees/digital-library`, forked from `revenue-platform` @ 00c267c)
**Goal:** A separate "Library" store where students buy ebooks/guides/lecture notes (one-time Razorpay purchases through the hardened payment stack), with concept-linked "suggested reading" surfaced inside lessons and after weak quiz results — a new revenue engine that rides existing, battle-tested payment rails.

## 1. Product model

- `ebooks` table (migration `0005_digital_library`, guarded like 0003/0004): `id`, `owner_id FK users` (instructor or admin), `title` ≤200, `slug` unique (generated like course slugs), `description` TEXT ≤5000, `category VARCHAR(16)` ∈ {`book`,`guide`,`lecture_notes`} (the user's "book, guide, lecture notes" naming — displayed as Books / Guides / Lecture Notes tabs), `price_inr INT` (paise NOT rupees? NO — follow whatever unit the existing courses/bundles use; MATCH EXACTLY), `discount_price_inr` nullable (must be < price when set), `cover_image` (existing public uploads flow, images are fine public), `file_path` (PRIVATE — see §3), `file_size_bytes`, `page_count` nullable, `sample_path` nullable (optional free-preview PDF, also served through the authenticated endpoint but grant-free), `concept_tags JSON` (list of ≤10 strings ≤50 chars), `course_id FK nullable` (links "reading for this course"), `status` ∈ {`draft`,`published`}, timestamps.
- `ebook_grants`: `id`, `ebook_id FK indexed`, `user_id FK indexed`, `order_id FK nullable` (paid) — UNIQUE(ebook_id, user_id); `granted_at`; `source VARCHAR(16)` ∈ {`purchase`,`admin`,`owner`}. Owner/admin implicitly readable without grants; grants are for students.

## 2. Payments — EXTEND the hardened stack, do not fork it

- `create-order`/`verify` currently accept exactly one of `course_id`/`bundle_id`/`invoice_id` → extend to include `ebook_id` (still exactly-one; coupons REJECTED on ebooks at launch, mirroring bundles).
- `fulfillment_service.fulfill_ebook_purchase(...)`: idempotent on `Payment.gateway_payment_id`, creates the `ebook_grants` row (get-or-create), never touches enrollments. Wired into ALL THREE convergent paths exactly like bundles: browser `/verify`, webhook inbox processor, reconciliation sweeper (order notes carry `ebook_id` snapshot).
- Order rows: `orders.ebook_id FK nullable` + per-item OrderItem naming consistent with how bundles record revenue lines (one OrderItem for the ebook, so revenue reports stay meaningful).
- Price at order-creation time is snapshotted into the order (discount honored); publish-state re-checked at order creation (draft ebooks cannot be ordered — 400).
- Free ebooks (price 0): "Get" flow bypasses Razorpay entirely — a direct authenticated `POST /api/v1/library/{id}/claim` creating a grant (source `purchase`, order_id NULL). No payment objects created.

## 3. File security (the crux — paid content must not leak)

- Ebook files live under `backend/ebooks/{owner_id}/{uuid}.{ext}` — NOT under `uploads/` (which nginx serves publicly). Mirror the company-invoicing private-PDF pattern (authenticated streaming endpoint).
- Upload (instructor): extension allowlist {pdf, epub} + magic-byte sniff (PDF `%PDF-`, EPUB = zip magic + mimetype entry check), size cap 200MB, per-owner total cap 5GB, filename never trusted (uuid names), path normalize-and-reassert inside the ebooks root. Reuse `core/secure_upload.py` conventions where applicable.
- Download: `GET /api/v1/library/{id}/download` — requires grant (or owner/admin); streams with `Content-Disposition: attachment`, correct content-type, support Range requests if the existing invoice/video streaming helpers make that cheap, else full-file streaming is acceptable at launch. NEVER a redirect to a static path. `GET /api/v1/library/{id}/sample` — published ebooks only, no grant needed.
- Cover images are public (normal uploads flow). Samples are semi-public by design.

## 4. Backend API — `app/routers/library.py` at `/api/v1/library` (⚠ add `'/library'` to axios noSlashEndpoints)

Public/student:
- `GET /library` — published ebooks; filters: `category`, `q` (title search), `course_id`, `tag`; anon-cacheable via `cache_headers.apply_public_cache` WITH the anon guard (edge-caching pattern — never cache authed responses).
- `GET /library/{slug}` — published detail (public, cacheable same way). Includes `owned: bool` ONLY for authed users (and then the response must be private/no-store — the helper's existing semantics).
- `GET /library/me` — authed: my grants with download availability.
- `POST /library/{id}/claim` — free ebooks only (price 0), creates grant; 400 for priced ones.
- `GET /library/{id}/download`, `GET /library/{id}/sample` — per §3.
- `GET /library/suggestions?course_id=X&limit=3` — published ebooks matching the course (course_id match first, then concept_tags ∩ course title/category words), excluding already-owned; authed.

Instructor/admin (owner-scoped, admin-any — mirror games/h5p ownership exactly):
- `POST /library` (create draft, metadata only), `POST /library/{id}/file` (upload/replace the ebook file; multipart), `POST /library/{id}/sample`, `PUT /library/{id}`, `POST /library/{id}/publish` (requires file present) / `unpublish` (allowed anytime — already-granted students KEEP download access; unpublish only hides from the store), `DELETE /library/{id}` (409 if any grants exist — sold content is never deleted), `GET /library/mine`, `GET /library/{id}/sales` (owner: count, gross from OrderItems, last sale; NO buyer emails — display_name only).

## 5. Suggestive buying surfaces (frontend)

1. **Lesson page** (`lesson-redesigned.tsx`): a compact "Suggested reading" card in the sidebar/below content fed by `/library/suggestions?course_id=` — cover, title, price (₹, struck-through original when discounted), one-click to detail page. Renders nothing when empty (zero layout cost). Cache per course view (React Query).
2. **Quiz results**: on a submitted attempt scoring < passing grade, the results view shows "Brush up with these" using the same suggestions endpoint (course of the quiz). Advisory placement only — no dark patterns, one dismissible card.
3. **Library store page** `/library`: public route, category tabs (Books / Guides / Lecture Notes), search box, course filter chips, cards with cover/price/sample badge. Nav: "Library" link in the PUBLIC header nav config AND student sidebar (`nav-configs.ts` — NOT dead header.tsx; also the RENDERED PublicHeader per the launch-surface lesson).
4. **Detail page** `/library/:slug`: cover, description, page count, sample-download button, Buy (→ existing checkout flow exactly as courses/bundles use it) or "Get free" (claim), "Go to my library" when owned.
5. **My Library** `/my-library` (student): owned items grid with download buttons.
6. **Instructor manager** `/instructor/library`: list + editor (metadata, uploads with progress, publish gate showing "file required"), sales panel.

## 6. Gamification & polish

- XP: `ebook:{id}:claimed:user:{uid}` → NO XP at launch (purchases are money, not learning). No badge. (Explicit decision: keep XP for learning actions only.)
- Instructor revenue analytics beyond the sales panel: out of scope (existing admin revenue reports pick up OrderItems automatically).

## 7. Tests (binding)

Backend `tests/test_library.py`: upload validation matrix (bad ext, fake magic bytes, oversize, per-owner cap), ownership matrix on every instructor endpoint, publish-requires-file, delete-409-with-grants, unpublish-keeps-access, download gate (no grant 403, granted 200 streams bytes, draft 404 to non-owner, sample public-when-published), claim free-only, order create/verify with ebook_id (mock gateway like existing payment tests), fulfillment idempotency (duplicate gateway_payment_id → one grant), webhook + sweeper paths reuse existing test harness patterns from bundle tests, suggestions relevance + owned-exclusion + never-draft, cache-headers anon-only on list/detail, coupons rejected. Full suite stays green (baseline 949P/4S).
Frontend vitest: store page filters, detail buy/claim/owned states, suggestions card renders/empty, instructor editor validation, my-library.

## 8. Docs & seed

- `docs/DIGITAL_LIBRARY.md` (architecture, security model, payment convergence, API ref, deploy notes: create backend/ebooks dir + nginx nothing-to-do since files are app-streamed; alembic upgrade head).
- CLAUDE.md entry.
- `backend/seed_library_demo.py`: 3 demo ebooks (one per category; one free, one priced, one discounted) owned by priya, PDFs generated tiny via reportlab (already a dependency), one linked to course 1.

## Out of scope (explicit)

DRM/watermarking, EPUB in-browser reader, subscriptions/rentals, marketplace revenue splits, coupons on ebooks, ratings/reviews, bulk/company ebook seats.
