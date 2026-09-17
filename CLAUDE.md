# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SashaInfinity LMS** — a learning management system with:
- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS (with Radix UI, Zustand, React Query)
- **Backend**: FastAPI (Python 3) + SQLAlchemy + PostgreSQL 15 + Redis 7
- **Streaming**: Separate FastAPI service (`streaming-service/`) on port 8001 that uses `yt-dlp` to proxy YouTube videos without exposing branding
- **Video CDN**: Bunny.net integration (see `bunny` router) in addition to YouTube streaming
- **Payments**: Razorpay (Indian market)
- **Auth**: JWT access/refresh tokens, role-based (Student / Instructor / Admin / Company / CompanyManager)
- **Company Portal**: Internship management, work logs, attendance, performance reviews, announcements
- **Deployment**: Docker Compose; Nginx reverse proxy

## Common Development Commands

### Docker (primary workflow)
```bash
docker-compose up -d                 # Start all services (backend, frontend, postgres, redis, nginx, streaming-service)
docker-compose down
docker-compose logs -f [service]
docker-compose restart backend
docker-compose exec backend bash
docker-compose exec frontend sh
docker-compose exec postgres psql -U tutor -d tutor_lms

# First-time setup (creates .env from .env.example, builds containers, creates upload/cert/log dirs):
chmod +x scripts/setup.sh && ./scripts/setup.sh

# Production:
./build-production.sh
docker-compose -f docker-compose.production.yml up -d
```

Default exposed ports (from `docker-compose.yml`): backend `8000`, streaming-service `8001`, nginx `3100`. The `frontend` service has **no host port mapping** — reach it through nginx at `http://localhost:3100` (or run the Vite dev server directly on `3000` from outside Docker).

### Frontend (in `frontend/`)
```bash
npm run dev          # Vite dev server on :3000 (inside container proxies /api/v1 → backend:8000)
npm run build
npm run lint         # ESLint on .ts/.tsx with --max-warnings 0
npm run type-check   # tsc --noEmit
npm run test         # Vitest (see vitest.config.ts)
npm run test:ui      # Vitest UI
```
Vite config is `frontend/vite.config.js` (JS, not TS). Path aliases: `@`, `@/components`, `@/pages`, `@/hooks`, `@/utils`, `@/types`, `@/store`, `@/api`, `@/assets`, `@/styles`.

**Frontend tests**: Vitest tests live in `frontend/src/`. Use `npm run test -- --run` for a non-watch release check; 399 tests passed on 2026-09-07.

### Backend (in `backend/`)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Tests live in `backend/tests/` and run with `pytest` (see `backend/tests/conftest.py` for fixtures — `db`, `client`, `student_user`, `course`, `as_user`, etc.). From `backend/`: `./.venv/Scripts/python -m pytest tests/ -v` (or `pytest tests/ -v` with the venv active).

**Migrations**: Existing databases use Alembic in `backend/alembic/` (`alembic upgrade head`, with the target `DATABASE_URL` configured). The current head is `0029`. Back up the target database before migration. `init_db()` creates missing tables for fresh databases; it does not replace migrations for existing schemas. See `docs/PLATFORM_SCHEMA.md` and `docs/releases/2026-09-07.md`.

### Admin user creation
Several scripts at repo root and in `backend/` do roughly the same thing — pick one:
- `./create_admin.sh` (shell wrapper)
- `python backend/seed_admin_simple.py`
- `python backend/seed_admin.py`
- `python backend/create_admin.py`

Admin credentials come from `ADMIN_EMAIL` / `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_FIRST_NAME` / `ADMIN_LAST_NAME` env vars (see `docker-compose.yml` for the defaults).

## Architecture

### Backend (`backend/app/`)
- `main.py` — FastAPI entry point. Registers 24+ routers, sets up CORS / security middleware, mounts `/uploads` and `/certificate-files` static dirs, defines `/health` and `/api/placeholder/{w}/{h}`. `/docs` and `/redoc` are **only enabled when `ENVIRONMENT=development`** (see `docker-compose.yml` which defaults to `production`).
- **Multiple `main_*.py` variants** (`main_simple.py`, `main_test.py`, `main_email_test.py`, `main_frontend_integration.py`, `main_payment_test.py`) exist for experiments / debugging — the real entry point is `main.py`. Don't edit a variant expecting production behavior.
- `core/` — config (`config.py` — pydantic-settings with security defaults), `database.py` (sync) and `database_async.py` + `database_postgres.py` (async), `redis.py`, `security.py`, `security_middleware.py` (rate limit, IP whitelist, request logging, security headers), `cors.py`, `secure_upload.py`, `input_validation.py`. Note `config_broken.py` exists alongside `config.py` — ignore the broken one.
- `models/` — SQLAlchemy models: `user`, `course`, `enrollment`, `payment`, `certificate`, `quiz`, `assignment`, `blog`, `coupon`, `instructor_review`, `company`, `company_dashboard`, `internship`, `internship_request`, `candidate`, `cohort`, `page_view`.
- `schemas/` — Pydantic request/response models matching the models above.
- `routers/` — endpoint modules, mounted under `/api/v1/...` except where noted:
  - Core: `auth`, `users`, `courses`, `dashboard`, `uploads`, `admin`, `analytics`
  - Commerce: `payments`, `orders`, `coupons`, `wishlist`, `checkout`
  - Learning: `quizzes` (mounted at `/api/v1`), `assignments` (mounted at `/api/v1`), `progress`, `certificates`, `instructor_reviews`
  - Company portal: `companies`, `company_dashboard`, `internships`, `student_workspace`, `cohorts`, `candidate`
  - Content: `blog`
  - Video/streaming: `video` (`/api/v1/extract`), `video_streaming` (`/api/v1/stream`), `embed` (`/api/v1/embed`), `youtube_embed` (`/api/v1/youtube`), `player` (`/api/v1/video`), `bunny` (`/api/v1/bunny`)
  - **`chunked_upload`** is mounted at **`/upload/chunked`** (NOT under `/api/v1`) and is imported conditionally — may be disabled if the module fails to import.
- `api/v1/certificate_verification.py` — public certificate verification endpoint (note: lives under `app/api/v1/`, not `app/routers/`).
- `services/` — business logic called by routers: `auth_service`, `user_service`, `course_service`, `payment_service`, `certificate_service`, `email_service`.

### Frontend (`frontend/src/`)
- `App.tsx` — routes; `main.tsx` — entry.
- `pages/` — route-level components. Note the Tamil-language category/content pages (`category-meiporul.tsx`, `category-seyappaduporul.tsx`, `category-utporul.tsx`, `meiporul-ar.tsx`) — the product has Tamil-specific taxonomy, not a generic category layout.
- `components/` — organized by feature: `about/`, `auth/`, `common/`, `contact/`, `course/`, `home/`, `layout/`, `public/`, `routing/`, `streak/`, `ui/`, `upload/`, `video/`.
- `components/ui/` — shadcn-style primitives (avatar, badge, button, card, input, logo, pagination, progress, star-rating). Most Radix components live inline in feature folders.
- `store/` — Zustand stores: `auth`, `cartStore`, `course`, `quiz`.
- `contexts/` — `CartContext`, `theme-context`.
- `api/` — axios + React Query wrappers: `auth`, `course`, `certificates`, `assignment`, `quiz`, `dashboard`, `upload`, `chunked-upload`, `video`, plus the shared `axios.ts` instance.

### Streaming service (`streaming-service/`)
Single-file FastAPI app (`video_streaming.py`) exposing `/health` + streaming endpoints on port 8001. Uses `yt-dlp` with `youtube_cookies.txt` to resolve unlisted YouTube videos and proxies the CDN stream with range-request support. An in-memory URL cache with 10-minute TTL avoids hammering yt-dlp. This service has its own CORS (`allow_origins=["*"]`) and is independent of the backend's auth — the backend must gate access before redirecting clients here.

### Request flow in production
Nginx (`:3100`) → frontend static / backend (`/api/v1/*`, `/uploads`, `/certificate-files`) → backend may redirect/proxy to streaming-service for video playback.

### Static files & uploads
- `./uploads` is bind-mounted into backend (`/app/uploads`) and nginx (`/var/www/uploads`); exposed at `/uploads`.
- `./certificates` is bind-mounted into backend (`/app/certificates`) and nginx (`/var/www/certificates`); exposed at `/certificate-files`.
- `scripts/setup.sh` pre-creates subdirs: `uploads/{courses,profiles,certificates,temp}`, `certificates/{templates,generated}`, `logs/`, `database/backups/`.

## Environment

Copy `.env.example` → `.env`. Required: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`, `JWT_SECRET`, `RAZORPAY_KEY`, `RAZORPAY_SECRET`, `ADMIN_PASSWORD`. If `SECRET_KEY`/`JWT_SECRET` are left at the placeholder values, `config.py` auto-generates random ones at startup — fine for dev, bad for prod (tokens invalidate on restart).

Set `ENVIRONMENT=development` and `DEBUG=true` locally to get `/docs`, `/redoc`, and verbose error responses.

## Compose file layout

Five compose files exist; understand which one is authoritative before editing:
- `docker-compose.yml` — base definition used for local dev.
- `docker-compose.override.yml` — auto-merged by Docker when running the base file locally (dev-only tweaks).
- `docker-compose.prod.yml` / `docker-compose.production.yml` — production stacks; `build-production.sh` uses `docker-compose.production.yml`.
- `docker-compose.security.yml` — hardened overlay (see `deploy_security.sh`).

## Repo noise — files to ignore

This repo has accumulated artifacts at the root and inside `frontend/`/`backend/` that are NOT part of the app. Don't treat them as source of truth:
- Session/transcript dumps at root: `2025-12-*.txt`, `dec_2_changes.txt`, `gitTok.md`.
- Accidental filenames with spaces in `frontend/` (e.g. `match - lesson IDs...`, `ure lectureIds...`, `ts_errors.txt`) — leftover shell-redirect accidents, not code.
- One-off operational scripts in `backend/` (`debug_video.py`, `delete_sasha.py`, `delete_user.py`, `fix_schema.py`, `check_*.py`, `clear_demo_data.py`, `activate_accounts.py`, `set_all_instructors_unapproved.py`) — admin utilities, not part of the request/response flow.
- `backend/app/core/config_broken.py` — ignore; the real config is `config.py`.
- `backend/app/main_*.py` variants — experiments; real entry is `main.py`.

## Notes for future work
- The product is Tamil-language-specific in parts (category taxonomy, some pages) — don't treat Tamil strings or routes as stray/untranslated.
- Video playback has **three** paths: direct YouTube embed (`youtube_embed`/`embed`), server-side yt-dlp proxy (`streaming-service` + `video_streaming` router), and Bunny.net CDN (`bunny` router). Check which path a feature uses before changing video logic.
- There is extensive security middleware with strict CORS/allowed-hosts lists in `docker-compose.yml` and `config.py` — adding a new dev origin usually requires updating both.
- **Company portal** is a major feature area with its own dashboard, internships, work logs, attendance tracking, performance reviews, and announcements. It uses scoped access control — company managers can only see data for their company. See `backend/app/models/company_dashboard.py` for the full data model.
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
- **Memberships** (2026-09): tiered Razorpay Subscriptions. Access = materialized
  Enrollment rows (`enrollment_source="membership"`, suspend on lapse, never touch
  rows with order_id). Models `app/models/membership.py`; grant/suspend logic
  `app/services/membership_access.py`; lifecycle handlers in webhook_processor
  (subscription.* events); lapse-expiry + catalog-sync passes in reconciliation.py;
  member API `/api/v1/memberships/*`; admin CRUD under `/api/v1/admin/memberships`.
  Razorpay plans are immutable — price changes = new tier. Migration:
  backend/migrations/add_memberships_tables.sql.
- **Bundles & seat pricing** (2026-09): bundles = one-time multi-course purchases
  (models app/models/bundle.py; fulfill_bundle_purchase in fulfillment_service.py —
  idempotent on gateway_payment_id, grants enrollment_source="bundle" rows WITH
  order_id so nothing can suspend them; per-course OrderItems keep revenue reports
  meaningful; Orders carry bundle_id). create-order/verify accept exactly one of
  course_id/bundle_id; webhook + sweeper fulfill from the bundle_course_ids notes
  SNAPSHOT (bundle edits never affect paid buyers). Cohorts may carry seat_price —
  referral checkout into such a cohort charges it instead of the course price;
  coupons rejected on bundles and seat-priced cohorts. Public API /api/v1/bundles;
  admin under /api/v1/admin/bundles. Migration: backend/migrations/add_bundles_tables.sql.
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
- **Edge caching + storefront surfacing** (2026-09): public catalog endpoints
  (bundles list/detail, membership plans, courses listing) emit anon-only
  `Cache-Control: public, s-maxage, stale-while-revalidate` + `Vary:
  Authorization` via app/core/cache_headers.apply_public_cache; authed
  requests get `private, no-store`. Never wire this helper into an endpoint
  returning personalized data without the anon guard. Cloudflare setup in
  CLOUDFLARE_CACHE_SETTINGS.md. Header/footer/courses-page link Membership
  and Bundles; the courses-page promo strip hides itself when no plans/
  bundles exist.
- **Live Classes** (2026-09): Teachmint-style scheduled video classes on a
  self-hosted, single-instance docker-jitsi-meet stack (data-tier side, NOT
  part of the blue/green app switch) reached via backend-minted room-pinned
  JWTs (`AUTH_TYPE=jwt`, dedicated `JITSI_JWT_SECRET` ≠ platform `JWT_SECRET`).
  Models `app/models/live_class.py` (7 tables: schedules/classes/join_tokens/
  attendance/polls/poll_votes/events; Integer PKs, first Alembic migration in
  this repo — `backend/alembic/`, baseline-stamp + `0002_add_live_class_tables`,
  init_db() create_all stays a parallel dual path). Token minting
  `app/services/jitsi_token_service.py` (student tokens always carry
  moderator/recording=false); session lifecycle + scheduling + attendance +
  polls (SSE via Redis pub/sub, MockRedis short-poll fallback) + recordings
  routers under `app/routers/live_class_*.py`, all mounted at `/api/v1/live`;
  internal ingest at `/api/v1/internal/live` guarded by `X-Internal-Token` +
  loopback (`live_class_internal.py`). Recordings: Jibri → shared volume →
  `deploy/scripts/finalize_recordings.py` (cron) → internal endpoint →
  existing Bunny upload flow (`live_recording_service.py`, reuses bunny.py's
  logic without modifying it) → `recording_video_id` → existing signed
  playback. Env vars: `JITSI_PUBLIC_URL`, `JITSI_JWT_APP_ID`,
  `JITSI_JWT_SECRET`, `JITSI_RECORDINGS_DIR`, `INTERNAL_TOKEN`,
  `DEFAULT_TIMEZONE` (backend/.env.example); production fails fast at
  startup if `JITSI_JWT_SECRET`/`INTERNAL_TOKEN` are blank. Jitsi stack itself
  (compose, edge vhost, health/smoke scripts, env example) lives under
  `deploy/` — see `docs/LIVE_CLASSES.md` for the architecture diagram, env
  reference, and full runbook (start/stop, secret rotation, stuck-recording
  recovery, VPS smoke checklist). Web: `frontend/src/pages/{instructor,student}/
  live-*`, `frontend/src/components/live/` (JitsiStage wraps the Jitsi IFrame
  API). Mobile: `flutter_app/lib/features/live_classes/` via
  `jitsi_meet_flutter_sdk` (compile-untested — no Flutter toolchain in CI;
  owner must run `flutter pub get` + `build_runner`, see runbook).
- **Learning Experience** (2026-09): four features — assessment hardening +
  manual grading/gradebook, H5P interactive lessons, unified certificate
  designer, event-sourced gamification. Full architecture, security model,
  and deploy runbook: `docs/LEARNING_EXPERIENCE.md`. Assessment: quiz/
  assignment state machines hardened (server-side timer, deadline
  enforcement, answer-leak fix, dead client quiz path removed), rubric-
  scored manual grading + gradebook/CSV export at `/api/v1` (`app/routers/
  quizzes.py`, `assignments.py`, `gradebook.py`). H5P: instructors upload
  `.h5p` packages authored externally (lumi.education) — play, don't author;
  untrusted package JS runs ONLY inside `<iframe sandbox="allow-scripts">`
  (never `allow-same-origin`) via `frontend/public/h5p-player.html` +
  vendored `h5p-standalone`; validated/extracted server-side by
  `app/services/h5p_service.py` (traversal/symlink/zip-bomb/extension
  guards, 2GB per-owner cap) to `uploads/h5p/{public_id}/`; client-reported
  scores are advisory engagement data, never gradebook truth. Certificates:
  `elements_config` JSON is now the single design format for both the
  instructor designer (`/api/v1/certificates/designer/*`,
  `app/routers/certificate_designer.py`) and real issuance
  (`app/services/certificate_html_renderer.py` → existing headless-Chrome/
  Selenium pipeline, ReportLab fallback when Chrome is absent); QR codes via
  `qrcode[pil]`; 5 seed templates in `backend/seed_designer_templates.py`
  (rerun after deploy on a Chrome-capable host to regenerate thumbnails).
  Gamification: event-sourced XP ledger (`xp_events`, idempotent on
  `event_key`) + derived `user_game_stats`, one `award()` entry point in
  `app/services/gamification_service.py` called best-effort from every
  completion trigger across the other three features plus live classes;
  computed levels (`100*n*(n+1)/2`), ~15 seeded badges, server-side
  staleness-corrected streaks, opt-out leaderboard
  (`/api/v1/gamification/*`) that never leaks email. Frontend widgets in
  `frontend/src/components/gamification/`, `/leaderboard` page, dashboard +
  profile integration. All four features' new tables live in one shared
  Alembic revision, `backend/alembic/versions/0003_learning_experience.py`
  (guarded `has_table`/`has_column` checks, grown additively across tasks —
  run `alembic upgrade head`, not `init_db()`, to pick it up on an existing
  database).
- **Learning Games** (2026-09): native, zero-file instructor-built games (5
  templates: quiz_rush/match_pairs/drag_sort/word_builder/sequence) — the
  "build it yourself" counterpart to H5P's "import a package" model. One
  JSON `config` per game, strict per-template pydantic validation
  (`app/schemas/game_config.py` — `extra="forbid"` at every nesting level,
  64KB serialized cap, per-string char caps, in-range index checks);
  `max_score` is NEVER stored, always derived server-side as `10 × item
  count` (`derive_max_score`). Models `app/models/game.py` (`Game`,
  `GameResult`); router `app/routers/games.py` at `/api/v1/games` (plain
  dicts, no envelopes); migration `backend/alembic/versions/
  0004_learning_games.py` (down_revision `0003`, guarded `has_table`/
  `has_column`, `batch_alter_table` for `lessons.game_id` on SQLite — run
  `alembic upgrade head`, not `init_db()`, to pick it up on an existing
  database). Lessons attach via `lesson_content_type='game'` + `game_id` —
  validated as an ATOMIC PAIR by `courses.py`'s
  `_resolve_lesson_content_fields` (renamed from `_resolve_lesson_h5p_
  fields`; never PATCH the type without its id in the same request — game
  must be published + caller-owned or 400/403/404). Scores are advisory
  only (grading is client-side; `/play` ships answers to the client) —
  NEVER gradebook truth, identical posture to H5P. XP via
  `gamification_service.award()` — flush-only, caller commits, SAVEPOINT
  dup isolation, every call site best-effort `try/except` (an XP hiccup
  must never fail the results POST); event keys
  `game:{id}:completed:user:{uid}` (+20, first score>0) /
  `game:{id}:perfect:user:{uid}` (+10, first score==derived max); badge
  `game_on`. Traps: `'/games'` must stay in `axios.ts`'s
  `noSlashEndpoints` (`redirect_slashes=False` backend-wide, every games
  route declared without a trailing slash — the exact gamification-404
  lesson repeated); no `dangerouslySetInnerHTML` anywhere under
  `frontend/src/components/games/` or the games pages (instructor config
  JSON is untrusted input rendered into other users' browsers — all item
  strings render as React text only). Frontend: `api/games.ts` (tagged
  union on the OUTER `Game`/`GamePlayPayload` type, one variant per
  template, so `game.template` narrows `game.config` with zero casts),
  `components/games/` (`GameShell`, `engines/` + `engines/scoring.ts`,
  `GamePlayer`, `GamePicker`, `builderValidation.ts` — blocking
  `validateConfigDraft` + non-blocking `duplicateWarnings`),
  `pages/instructor/games.tsx` + `game-builder.tsx`, `pages/game-play.tsx`;
  full reference (instructor guide, API shapes, per-template scoring
  rules, security model, ops runbook): `docs/LEARNING_GAMES.md`.


## SILEOS feature pack (2026-09-04, docs/SILEOS_FEATURES.md)

Backend-only integration of selected SILEOS blueprint features. Routers:
`question_banks.py` (/api/v1/question-banks: CRUD, import-from-quiz SNAPSHOT-copy,
item analysis with facility + discrimination), `sileos.py` (course prerequisites +
/unlock-status — EXPOSED not ENFORCED yet, learning paths, xAPI statement spine
with ingest/own-stream/admin firehose, per-student mastery 0.6*completion+0.4*quiz-pass-rate,
explainable at-risk rules persisted to student_risk_flags), `ai.py` (Anthropic
question generation — 503 without ANTHROPIC_API_KEY; every call is an AiJob audit row;
drafts land in banks tagged `ai-draft`, never auto-published). Models in
`models/sileos_pack.py`; parity migration `migrations/sileos_pack_2026_09_04.sql`.
xAPI emitters are wired into `progress.py` watch-event and `courses.py`
mark_lesson_complete — best-effort POST-commit, same doctrine as `award()`.
Tests: `tests/test_sileos_pack.py` (11). No UI consumes these yet by design.


## Phase 2/4 — 3D models + Virtual Labs (2026-09-04)

Type-driven tools (owner matrix): MP=3D+GeoGebra+H5P, SP=games+H5P+live+paths+rewards,
UP=everything. Matrix: app/core/course_types.py (TYPE_CAPABILITIES + TOOL_AVAILABILITY),
exposed at GET /api/v1/courses/type-capabilities; wizard mirrors it via config/courseTypes.ts.
- 3D: models/three_d.py, routers/three_d.py (/api/v1/three-d — GLB magic-byte check b"glTF",
  50MB cap, PRIVATE storage backend/three_d/{owner}/, auth-gated stream, delete blocked while
  attached). Lesson type 'three_d' attaches to MP/UP courses ONLY (courses.py resolver, 422 otherwise).
- Virtual labs: routers/virtual_labs.py (curated PhET catalog, GET /api/v1/virtual-labs).
  Lesson type 'virtual_lab' = sim slug column; embeds via PhET iframe (sandbox allow-scripts),
  attribution rendered. Available on ALL course types.
- Resolver contract now 5-tuple (content_type, h5p_id, game_id, geogebra_id, extra) where
  extra = three_d_model_id | virtual_lab_sim based on resolved type.
- Course creation is DRAFT-FIRST (Q2-A): /instructor/courses/create renders a short start form
  (pages/instructor/course-start.tsx) -> creates draft -> redirects to the tabbed
  /instructor/courses/:id/edit editor. The old multi-step wizard is unrouted.
- Quiz scored modules: create AND update quiz accept interactive_modules
  [{kind:'h5p'|'game', id}] (validated, stored on Quiz.interactive_modules, returned by GET);
  quiz without questions is valid if it has modules. Cumulative grade =
  quizzes 40% + assignments 40% + interactive modules 20%
  (GET /api/v1/analytics/courses/{id}/students/{uid}/cumulative-grade).

## Error sweep 2026-09-05 (Fable 5.1) — traps learned

- **Tests must never touch a real Redis.** `tests/conftest.py` has an autouse
  `_isolate_redis` fixture pinning `RedisClient._instance` to a fresh `MockRedis`
  per test. Without it, Docker's Redis on localhost:6379 kept join-token INCR
  counters (60s) and reminder SETNX markers (2h) across runs and the
  live-class suites failed deterministically (the "flakes" in the old handover).
- **`from __future__ import annotations` hides missing imports in signatures.**
  An unimported `Any` in `internships.py` made FastAPI register a JSON body as a
  required QUERY param (422 "payload: Field required") with no import error.
  Run `pyflakes app` after touching routers; `tests/test_static_regressions.py`
  guards this and `AuthService.require_role`.
- `app/core/secure_upload.py` imports python-magic at module level, which hangs
  forever at import on Windows (no libmagic). Nothing in the app imports it —
  never import it from a router without a lazy/guarded import.
- `main.py`'s global `@app.exception_handler(404)` rewrites EVERY 404 detail to
  "Endpoint not found" — handler-raised "X not found" messages never reach the
  client. Assert only on status codes for 404s.
- `npm run lint` now has a config (`frontend/.eslintrc.cjs`, Vite React-TS
  template; unused-vars/any off to match the codebase). Baseline after the
  sweep: 0 errors, 26 `react-hooks/exhaustive-deps` warnings (one per file, left
  for case-by-case review — adding deps blindly can create effect loops).
  Hooks rule: never `id || useId()` and never a hook below an early return.
- Dev ports while the predecessor's ZCode session holds 8010/3000:
  `.claude/launch.json` runs backend :8011 / frontend :3001
  (`VITE_DEV_PORT`, `VITE_PROXY_TARGET`); smoke via
  `SMOKE_BASE=http://127.0.0.1:8011/api/v1 bash scripts/smoke.sh <T> <S>`.

## Content Libraries (2026-09-05, docs/CONTENT_LIBRARIES.md)

Admin-curated libraries instructors pull into a curriculum. **Virtual labs**:
catalog = built-ins (`routers/virtual_labs.py::BUILTIN_LABS`) ∪ admin rows
(`virtual_lab_catalog`, DB row overrides a built-in on slug match); providers
`phet`/`embed` (iframe) and `native` (our engines `reaction_lab` /
`identify_lab`, configs validated by `schemas/lab_config.py` — the reaction
validator PROVES the answer key is element-balanced + lowest terms;
`max_score` derived, never stored). Lesson attach stays the atomic pair
`virtual_lab` + `virtual_lab_sim=<slug>`; resolver calls `is_valid_lab_slug(db,
slug)` (unpublished → 422). Results `POST /virtual-labs/{slug}/results` →
`virtual_lab_results`, XP best-effort AFTER commit (`lab:{slug}:completed|perfect`).
**3D library**: `three_d_models.is_library`; `GET /three-d/models` returns
`{models, library}`; attach allowed for owner/admin/library. **Prebuilt games**:
admin pack import runs `validate_game_config`, creates admin-owned
published+listed games (marketplace); shipped pack `backend/seed_packs/
prebuilt_games.json`. Admin router `routers/content_library_admin.py` at
`/api/v1/admin/content-library` (labs CRUD/import, games import[-defaults],
three-d import/patch/delete; every import all-or-nothing). Migration: Alembic
`0007_content_libraries` + `migrations/content_libraries_2026_09_05.sql`.
Frontend: `api/labs.ts`, `components/labs/{VirtualLabPlayer,NativeLabPlayer,
VirtualLabPicker}.tsx`, `components/labs/native/*`, `components/labs/diagrams/*`
(0-100 viewBox = hotspot percent coords), `pages/admin/content-libraries.tsx`
(`/admin/content-libraries`). Traps: `find` in the browser can't see chip
labels that carry a `title` attr; dev preview sets
`RATE_LIMIT_REQUESTS_PER_MINUTE=600` in launch.json because the default
60/min/IP (Redis-backed) starves an SPA page right after a smoke run.
Tests: `tests/test_content_libraries.py` (7).

## v2.0 gap build — WP1 Scorable items (2026-09-05, plan: docs/superpowers/plans/2026-09-05-v2-architecture-gap-build.md)

`Quiz.interactive_modules` entries now follow the ScorableItem contract
(`app/schemas/scorable.py`): `{kind: h5p|game|lab|three_d_task, id, title,
max_score (DERIVED, never client-set), weight, attempts_allowed,
grading_mode, practice_only, tier_floor}`; legacy `{kind,id,title}` rows
normalise with defaults. `assert_publishable` refuses (422) any graded item
whose `tier_floor` is better than T4 (T0–T3) — practice-only items are exempt.
Registry is DERIVED: `GET /api/v1/scorable-items` (prefix is in axios
`noSlashEndpoints`). Cumulative grade (`routers/sileos.py`): quizzes /
assignments / games_h5p (H5P+games) / three_d_tasks (labs + 3D tasks) /
live_participation (present ratio of ENDED classes), item weights honoured,
practice items skipped, weights from `type_profiles` with in-code §5.3
fallbacks (the raw-SQL table is absent in the test DB). `kind: lab` ids are
catalog slugs (native labs only). `three_d_task` resolves through
`routers/three_d_tasks.py` when WP2 lands (ImportError → 422 until then).

## v2.0 gap build — WP2 3D match-and-verify (2026-09-05)

`three_d_tasks` / `three_d_task_attempts` (Alembic 0008). Seven task types
(match, identify, verify, assemble, measure, manipulate, sequence) — configs
in `schemas/three_d_task_config.py`, strict + 64KB cap; anchors are
NORMALISED bounding-box coordinates (0..1) with auto "Region N" names shown
to learners (labels never leak). Grading is SERVER-SIDE from submitted
answers (`grade_task`) — a client score is ignored; evidence events
(rotate/zoom/reset/param/select/hesitate/mode/place/order, ≤1000) produce the
§6.3 confidence signal (`clean | mixed | trial_and_error`). Owner/admin
attempts are previews and never stored. Router `/api/v1/three-d-tasks` (in
axios `noSlashEndpoints`); published tasks appear in the quiz palette as
`kind: three_d_task` and score into the `three_d_tasks` bucket. Viewer:
`ThreeDViewer` props `anchors`, `onAnchorClick`, `onPickPoint` (surface
raycast → normalised coords), `onEvidence`. Player forces T4 list view when
WebGL is absent; both views earn identical marks. Trap: the browser
automation's synthetic clicks on the WebGL canvas count as drags — real
clicks and dispatched PointerEvents place anchors fine.

## v2.0 gap build — WP3 Learner mastery graph (2026-09-05)

Learner-scoped concept graph (Alembic 0009): `concept_links` (kind+ref →
concepts; kinds quiz|question|game|h5p|lab|three_d_task|lesson|assignment|
course), `mastery_evidence`, `learner_mastery`, `concept_prerequisites`,
`course_outcomes`. `services/mastery_service.record_evidence()` is called via
`safe_record_evidence` from EVERY scoring path AFTER that path's own commit
(quiz submit/finalize, games, labs, H5P, 3D tasks, assignment grading) — it
commits only its own rows, never fails the host request. Estimate =
recency-weighted mean (×0.85 per older row) with source weights quiz 1.0 /
assignment 1.0 / 3D 1.0×path (clean 1, mixed .8, trial_and_error .5) / lab
.7 / H5P .6 / game .5; confidence = 1−1/(1+Σw). Concepts are free text,
normalised. Built-in native labs declare `concepts`; 3D tasks mirror their
`concepts` into links on save. API `/api/v1/mastery` (in axios
`noSlashEndpoints`): me, students/{uid}, weak, evidence per concept, links,
prerequisites (cycle-checked), courses/{id}/coverage (gap report:
no_teaching | no_assessment | target_uncovered), outcome, progress-map.
at-risk adds +20 when ≥3 concepts <50% (confidence ≥0.4); Engine D
`generate-exam-paper` accepts `student_id` to weight weak concepts. Pages:
`/my-mastery`, `/instructor/courses/:id/coverage`.

## v2.0 gap build — WP4 Emergent taxonomy (2026-09-05)

Tags stay free text in `courses.course_tags` (JSON list). `tag_clusters`
(Alembic 0010) is DERIVED by `services/tag_service.py`: normalise → trigram
similarity ≥0.55, distinctive-token equality/prefix ("trig"→"trigonometry",
generic tokens like class/maths never link), co-occurrence ≥2 courses with
weak similarity → union-find; rebuilt lazily (10-min TTL) or via admin
`POST /api/v1/tag-taxonomy/clusters/recluster`; labels survive rebuilds by
member overlap. Course search (`GET /courses/?search=`) ORs title/body/tags
with every cluster member of the term. `GET /tag-taxonomy/suggest` (instructor)
derives suggestions from title/description. Router file is
`routers/tag_taxonomy.py` — `routers/tags.py` is the pre-existing legacy
listing; do not overwrite it. UI: `components/course/TagsEditor.tsx` (editor
Basic Info), catalogue Type dropdown, `components/admin/TagClustersPanel.tsx`.

## v2.0 gap build — WP5 Live class classification + retention (2026-09-05)

`live_classes` gained purpose | mode | audience | recording_policy (validated
against `services/class_report_service.PURPOSES/MODES/AUDIENCES/
RECORDING_POLICIES` via `LiveClassSettings`), `retention_until`,
`recording_deleted_at/_by/_reason` (Alembic 0011 + ensure_schema). Rule:
"media expires, knowledge does not" — `end_class` generates a permanent
`class_reports` row (attendance join/leave/duration, event log, poll
results, engagement, notes; transcript/ai_topics filled by Engine A later)
and sets `retention_until = ended_at + settings.retention_days` capped by
`RECORDING_RETENTION_MAX_DAYS` (default 365, owner decision). `DELETE
/live/classes/{id}/recording` is SOFT (30-day restore via
`/recording/restore`); `/recording/extend` stays under the ceiling; every
action lands in `recording_audit` (`GET /live/recordings/audit`, admin). The
reminders loop calls `retention_pass()`: 14/3-day warnings (most urgent
applicable window first, once each, `recording.expiry_warning_{n}d` events)
and hard purge past retention or 30 days after a soft delete — reports are
never touched. `lifecycle` (scheduled|live|ended|processed|archived|deleted|
cancelled) is derived, not stored. Report endpoints: `/live/classes/{id}/
report[.pdf]`, `/report/notes`, `/report/share-guardians`; learners see only
their own attendance row; guardians only when shared.

## v2.0 gap build — WP6 Studio faces (2026-09-05)

Per-course studio knobs live in `course_studio_settings` (JSON `parent_view`
+ `rewards` + `face_dismissed`; `services/studio_service.py`, router
`/api/v1/studio`, Alembic 0012). Defaults are DERIVED from `course_type`
(`defaults_for_type`) — never seed rows. `gamification_service.award()`
asks `studio_service.points_override()` whenever `course_id` is passed (the
override beats DEFAULT_POINTS *and* a trigger site's explicit `points=`), then
`evaluate_course_badges()` grants custom badges as `course_badge` XpEvents
(idempotent key `course_badge:{course}:{slug}:user:{uid}`). Streak freezes:
`touch_streak` calls `_consume_streak_freeze` (allowance = max
`streak_freeze_days_per_month` across the learner's enrolled courses,
month-scoped counters on `user_game_stats`). `GET /gamification/leaderboard?
scope=course:{id}` returns `{entries: [], opted_out: true}` when the course
switched its leaderboard off. `parents._build_digest` emits ONLY the ticked
parent-view signals — add new guardian data behind a key in
`PARENT_VIEW_KEYS`, never unconditionally. Frontend: `components/studio/*`;
the course editor reads `?tab=` and `?face=1` (the start form redirects with
both); `ThreeDViewer` props `autoRotate/interactive/onStats/captureRef` feed
`TierPreview`. Trap: labs / 3D tasks / games award XP without `course_id`, so
per-course point overrides cannot reach them (documented in the ledger).
Trap: Alembic SQLite `batch_alter_table` on tables with FKs must pass
`reflect_kwargs={"resolve_fks": False}` or downgrades fail on an
Alembic-only DB (`users`/`courses` come from init_db, not migrations).

## v2.0 gap build — WP7 AI layer completion (2026-09-05)

`routers/ai_engines.py` (`/api/v1/ai`, same prefix as `ai_tutor.py`) +
`services/ai_layer_service.py` + `models/ai_layer.py` (Alembic 0013).
Doctrine unchanged: every LLM call goes through `llm_provider.call_glm`,
honest 503 without `GLM_API_KEY`, audited `AiJob`, output is a draft.
Deterministic parts work WITHOUT a key and must stay that way: the
graded-item answer guard in `tutor_chat` (runs before the 503 check — never
reorder it), escalations, error reports, review-queue item flags
(`flag_reasons`, derived from `quiz_attempt_answers`, never stored),
transcript storage (`processing_status=transcribed`; `processed` only after
segmentation). Tests monkeypatch `call_glm` on BOTH `ai_layer_service` and
`ai_engines` (each module imported the name). `/ai` is in axios
`noSlashEndpoints`. Mastery link kinds now include `live_class` (teaching
kind) — `process_transcript` writes them. Trap: `ClassReport` must exist
(class ended) before a transcript can be ingested — 404 (worker) / 409
(owner paste). Trap: the embedded browser pauses `requestAnimationFrame`
when the pane is hidden — WebGL fps meters read "—" there; capture via a
synchronous `renderer.render()` still works.

## v2.0 gap build — WP8 flywheel extras + WP9 quality (2026-09-05)

`routers/flywheel.py` (`/api/v1/flywheel`, in axios `noSlashEndpoints`),
`services/flywheel_service.py`, `models/flywheel.py` (Alembic 0014). The
next-class agenda and the 3D insight cards are DERIVED at read time (report
+ mastery graph + open escalations/error reports; 3D attempt `confidence` ×
`mastery_evidence` quiz rows) — never store them. 3D tasks belong to a
course only through `Quiz.interactive_modules` (`kind: three_d_task`), which
is how `_tasks_for_course` finds them. Teach-back writes a `teach_back`
mastery link kind (SOURCE_WEIGHTS 0.3) — the concept graph now has three
non-assessment kinds (`live_class`, `teach_back` + the teaching kinds).
DigiLocker stays an adapter: 503 without `DIGILOCKER_CLIENT_ID`/`_SECRET`.
`services/glb_budget.py` runs on every GLB upload/import (hard caps → 422,
soft per-tier warnings in the `budget` field) — keep it a pure function of
the bytes. Trap (fixed): every router that declares `@router.get("")` needs
its prefix in axios `noSlashEndpoints` — `/question-banks` was missing and
the Insights item-analysis tab 404'd silently. Trap: `LearnerMastery.
estimate` is 0..100, not 0..1 — WP7's calibrate/choose_mode thresholds are
40/75 on that scale.

## Public lesson preview + glass UI system (2026-09-05 evening)

The course payload is now a REAL lock: `CourseService.format_course_response(
…, full_access=)` strips `LOCKED_LESSON_FIELDS` from non-preview lessons unless
the caller is enrolled / owner / admin (`is_locked` on every lesson; schema
field added to `LessonInfo`/`LessonResponse` — response models drop unknown
keys, so new lesson fields must be declared there). Visitors open preview
lessons through `GET /courses/{id}/lessons/{lid}/preview`; the asset endpoints
(3D file, lab detail, game play) accept an optional user and gate anonymous
access with `services/public_preview.allows_anonymous(db, field, value)` —
extend that helper, never add a second rule. `tests/conftest.as_user`
overrides `get_optional_current_user` too. UI: use `GlassDialog`
(`components/ui/dialog.tsx`) and `useConfirm` (`components/ui/confirm.tsx`)
for every popup — `confirmDialog(msg)` / `promptDialog(msg)` are the drop-in
replacements for window.confirm/prompt (must be `await`ed inside an async
handler; the lint/tsc pass will not catch a missing await, grep for it).
`components/ui/card.tsx` is glass by default. Tokens in `styles/globals.css`
(`si-*`, `glass-*`). Radix
tabs in the embedded browser need a `mousedown` before `click()`. Trap: the
editor's lecture field `isPublished` maps to `is_preview` (public preview),
not to publish state — the labels now say so.

## Roadmap loop R1–R10 (2026-09-06)

New modules: `routers/funnel.py` + `services/funnel_service.py` (events are
append-only; every report is derived; abandoned-checkout reminders run in
the live-reminders loop), `routers/course_ops.py` + `services/
course_ops_service.py` (clone / templates / CSV import / co-instructors),
`services/course_access.can_edit()` — THE edit rule; never write
`course.post_author != user.id` checks again, call `can_edit`. `hooks/
useNavBadges.ts` decorates sidebar items with live counts. Quiz integrity
lives in `attempt_info["integrity"]` and is advisory; retired questions are
filtered by `_not_retired()` in quizzes.py (NULL-safe — legacy rows are
NULL). Coupons on memberships need `coupons.razorpay_offer_id` (owner
creates Offers in the Razorpay dashboard). Alembic head is 0018. Traps:
a 404 raised from a handler is rewritten to "Endpoint not found" by
main.py — use 422 for user-facing validation messages; `CourseCollaborator`
lives in `models/course_ops.py`; the SPOC `cohorts.py` routes are all under
`/api/v1/cohorts/...` (`/spoc/...` and `/admin/...` are sub-paths).

## Round 2 (2026-09-06): retention, earnings, banks, media, visuals

`services/retention_service.py` rules are idempotent via Notification rows —
add a rule by writing one notification `type` and checking `_sent_since`
first; never send email directly from a rule. Earnings live in
`funnel_service.earnings` (orders → OrderItem.course_id; refunds =
Payment.refund_status == "processed"). Per-attempt random subsets use the
reserved `attempt_info["_question_ids"]` key (underscore keys are stripped
from answer payloads — keep it). `services/media_pipeline.py` shells out to
gltf-transform / ffmpeg; `tool_status()` is the truth, endpoints answer 503
when a tool is missing; tier files live next to the source GLB and are
listed in `three_d_models.tier_files`. Rate limiting fails OPEN for 30 s
after a Redis error (`RateLimitMiddleware`) — with Docker's Redis down the
dev preview keeps working; do not "fix" that by making the client block.
Alembic head is 0019.

## Learning-signals engine (2026-09-06)

Behaviour → struggle → adaptive assessment, all in-platform. Client
`frontend/src/api/signals.ts` (`signal()` buffers, flushes every 8 s / on
hide / on pagehide) instrumented in `pages/lesson-redesigned.tsx`
(rewind/replay/skip/pause/rate/note/quit_early — lesson id is the route's
`lesson-<id>` with the prefix stripped) and `pages/quiz-taking.tsx`
(question_time on move + submit, answer_change at submit). Server:
`models/learning_signals.py` (`learning_signals` bucketed into 10-second
segments, `lesson_concept_markers`, `adaptive_sessions`; Alembic 0020),
`services/learning_signals_service.py` (KINDS weights, `learner_profile`
with human `why` strings, `lesson_heatmap`, `build_adaptive` — only
auto-gradable question types, keys never leave the server —,
`grade_adaptive` → `safe_record_evidence` AFTER commit), router
`/api/v1/signals` (in axios `noSlashEndpoints`). UI:
`components/signals/{StruggleProfile,AdaptivePractice,LessonStruggleMap}.tsx`
on My Mastery and in every non-quiz lecture of the course editor. Traps:
learners always get their own heat-map regardless of `user_id`; the map
hides on 404 (unsaved lectures); StrictMode double-invokes the practice
build effect — keep the `builtRef` guard.


## Astra cycle 1 — instructor learning signals (2026-09-06)

Course hotspots at `GET /signals/courses/{id}/hotspots` use `can_edit` and
aggregate by authoritative Lesson.post_parent, rather than trusting the
client's course_id. `course_segments` is shared with retention and retains
all observed segments; only the API trims positive scores to ten. Concepts
use timeline markers, with lesson links as fallback. The Insights Hotspots
tab is the only page mount changed in this cycle; it handles course switching,
loading, empty results, retry, and alert deep links.

`retention_service.hot_segment_alerts` runs inside the existing six-hour
retention pass. Positive seven-day score must reach three times the median
of observed lesson segments with at least three distinct learners. Owner and
collaborators receive in-app notifications; `_sent_since` also matches the
segment-specific link so one segment does not suppress another. No emails.

Tutor chat is actually in `routers/ai_tutor.py`, not `ai_engines.py` as the
handover plan says. Its system prompt gets this learner's course-scoped
concepts at struggle >=60 with the existing why strings. The graded-item
guard and missing-key 503 retain their order. Patch call_glm in ai_tutor too
when testing, since each importing module has its own binding.

Quiz submit, results and finalize return `weak_concepts` from persisted wrong
question answers and question links. Pending manual answers are excluded;
reveal_never suppresses concepts for the learner just as it suppresses
correctness. Adaptive build accepts repeated `focus` query parameters and
normalizes them; each focused concept receives twice its weight, with a
baseline of one when there is no prior evidence. No schema changes.

## Personal learning planner and interventions (2026-09-06)

See `docs/LEARNING_PLANNER.md` for the complete contract. Models in
`models/learning_planner.py`, business rules in `services/learning_planner_service.py`,
API under `/api/v1/planner`. Frontend routes `/my-plan` and
`/instructor/interventions` use existing dashboard layouts. Alembic 0021 creates
three new tables; keep the frozen migration and PostgreSQL parity SQL aligned.

One goal per learner/course; goal mutations lock and verify ownership/enrollment.
Review blocks replace duplicate curriculum time, and cancelled reviews restore
unfinished curriculum work. `Mark studied` never awards course completion.
Published concept-linked practice requires two questions and 75%; immediate success
schedules a three-day delayed check. Behaviour alone is diagnostic. Failed or
underspecified checks go to the course owner's/collaborator's queue. Dismissals
remain closed; fresh failed evidence can reopen a resolved check, retaining history.

Canonical quiz submit/finalize refreshes active goals after grading commits.
The six-hour retention pass also refreshes plans independently per goal. Adaptive
build adds opt-in `focus_only` and deferred-commit support for planner transactions;
its default behaviour remains unchanged. Single-choice grading rejects arrays
containing multiple options. See `docs/PLANNER_BUILD_REPORT.md` for test scope and
known repository baseline failures. No production rollout was performed.

## Concept & Assessment Studio (2026-09-06)

`assessment_studio_service.py` supplies the planner's focused practice catalog,
coverage, immutable studio snapshots and exposure-aware selection. New table
`studio_questions` (Alembic 0022) references existing bank content and stores
publication state/version/history. Instructor route `/instructor/assessment-studio`
accepts course/concept deep links from Interventions. Require course edit access;
bank reuse never implies access to collaborators' private banks.

Adaptive IDs <0 mean StudioQuestion snapshots; IDs >0 retain QuizQuestion meaning.
Never expose snapshot keys in the pre-submit question or session-plan response.
Published/retired content grades against its snapshot even after source edits.
Review signatures prevent stale bank contents from being published; draft edits
reset review. Retired items leave new sets, not existing sessions. Existing bank
push excludes studio-draft and studio-retired tags. Reserved questions appear only
in delayed planner checks. Freshness checks all recorded sessions/quiz answers
and exact prompt identity; outcomes explicitly report repeated content. Full rules,
API and deployment notes: `docs/ASSESSMENT_STUDIO.md`.


## Recording Lessons (2026-09-06)

Role navigation is grouped by workflow (`docs/FEATURE_SEGMENTS.md`). Instructor
Content Studio now includes `/instructor/recording-lessons`. The private workbench
uses `recording_lessons` (migration 0023), `recording_lesson_service.py`,
`transcription_provider.py` and a separate `python -m app.workers.recording_lessons`
process. ASR runs in an optional isolated faster-whisper environment with local
model files; never install its native dependencies into a shared API environment.
Both API and worker need TRANSCRIPTION_* settings and the private recordings mount.

Finalizer ingest commits before best-effort enqueue. Drafts do not populate the
learner-visible ClassReport transcript. Reviewed conversion creates one normal
draft Lesson with source metadata and concept links. Course publication gates
learner access and planner eligibility. `/recordings/:classId` uses the dedicated
publication/enrollment-checked reader and existing signed Bunny playback.
Questions remain Assessment Studio drafts. See `docs/RECORDING_LESSONS.md`.

### Operations and portable course recovery (2026-09-06)

`/api/v1/admin/operations` serves admin queues, consistent lists/CSV, verified learning outcomes, cash/refund/subscription reporting and worker health. `/api/v1/course-packages` provides instructor/admin upload, inspect, export, private previews and restore-as-new-draft. Business logic lives in `operations_service.py` and `course_package_service.py`. Private staged uploads are outside the public uploads directory; course exports exclude learner/payment records. Install requirements (including bleach) and apply migrations 0024–0026. Transfer history uses SET NULL when a restored course is deleted, and owner deletion cascades its private transfer rows. Expired/orphan staging cleanup is bounded and runs through the package upload/history endpoints.

The Flutter learning workspace uses the same planner and recording-reader contracts. Generated live-class models/providers are required. Compatible local validation used Flutter 3.35.7 / Dart 3.9.2; fonts are bundled with licenses. See `docs/COURSE_BACKUPS.md` and `docs/OPERATIONS_BUILD_REPORT.md` for usage, recovery evidence and remaining device/recording checks.

## Campus exams + fee reminders (2026-09-12)

Exams: `models/campus_exams.py` (Alembic 0038), `services/campus_exams.py`,
`routers/campus_exams.py` under `/api/v1/institutions/{id}/exams`. One paper
per batch+subject creates a `campus_events` row (kind `exam`) and reuses
`campus_pilot._conflicts`; results are DERIVED from marks, never stored;
managers publish, staff enter marks (locked while published), learners and
approved guardians read only published results. Hall tickets are issued
lazily and race-safe (`_issue_tickets` re-reads on IntegrityError); learner
downloads use `.../hall-tickets/me/pdf`. Published papers join the term report
card through `campus_exams.report_card_rows`. PDFs: `campus_report_pdf.
build_hall_ticket_pdf` / `build_marksheet_pdf`. UI `components/institutions/
CampusExams.tsx`, nav key `exams`.

Fee reminders: `models/tuition_reminders.py` (Alembic 0039), `services/
tuition_reminders.py`, `routers/tuition_reminders.py` under `/fees/reminders`.
The reminder row is the idempotency unit (`dedupe_key` per installment, stage,
recipient, channel). Recipients = student + approved `parent_link_requests`.
WhatsApp only for consented campus members via a one-recipient
`CampusWhatsAppCampaign`; email otherwise; unusable channels → `skipped` rows
with a reason, never `sent`. `campus_worker.tick` calls `run_all()`;
`tuition_service.record_payment` queues receipt notices post-commit. Tests
monkeypatch `tuition_reminders.whatsapp_ready` / `mail_ready` /
`EmailService._send_smtp_email`. UI `components/institutions/FeeReminders.tsx`
inside Finance. Trap: the preview's single SQLite file can raise `database is
locked` under concurrent requests — production is PostgreSQL.
Toolchain trap: Python 3.13 rejects several requirement pins; build the venv
from the working `Sasha_lms-main (2)` freeze plus PyPDF2/reportlab.

## Staff leave + substitution (2026-09-12)

`models/campus_staff.py` (Alembic 0040), `services/campus_staff.py`, `routers/
campus_staff.py` under `/api/v1/institutions/{id}/staff/*`. Balances are
DERIVED (approved days per type per academic year); approval creates one
`campus_substitutions` row per `campus_events` slot the absent teacher owns in
the local date range; cancel releases them. `candidates()` / `assign()` share
`_busy_member_ids` (overlapping event owner, overlapping assigned substitution,
approved leave that day) — never bypass it. Hooks: `campus_pilot.event_dict`
adds `substitute_member_id/name`; `campus_action_center.today` includes
substituted events for the covering teacher and emits `system-substitutions`
for managers (counted from the local day start). Trap: HTTP header values are
latin-1 — sanitise filenames built from user text (academic years carry en
dashes). UI `components/institutions/CampusStaff.tsx`, nav key `staff` (staff only).

## Transport + hostel (2026-09-12)

`models/campus_transport.py` (Alembic 0041) + `services/campus_transport.py` +
`routers/campus_transport.py` under `/api/v1/institutions/{id}/transport/*`;
`models/campus_hostel.py` (Alembic 0042) + `services/campus_hostel.py` +
`routers/campus_hostel.py` under `/hostel/*`. FEE LINK: a route/block with a
fee owns ONE published tuition plan (`_ensure_fee_plan`: `Transport · {name}` /
`Hostel · {name}`, single component + single installment due in 30 days);
assigning/allocating a student calls `tuition_service.assign_plan` through
`_assign_fee` — never write ledger rows directly. One active assignment /
allocation per student, capacity checks, and future-day boarding refusal live
in the services. Stops/rooms are replaced by name (`_replace_stops` /
`_replace_rooms`); rows in use cannot be removed (409). Today: managers get
`system-transport` (routes with active students but no log today), staff get
`system-hostel-passes` (pending passes). UI `CampusTransport.tsx`,
`CampusHostel.tsx`, nav keys `transport`, `hostel` (learners see own view).

## Parent portal (2026-09-12)

`services/parent_portal.py::overview` aggregates, per approved child
(`parent_link_requests.status == "approved"` ONLY — the legacy
`ParentStudent` table is not consulted) and per active student membership:
attendance (30 local days), fees via `tuition_service.self_accounts`, published
exams via `campus_exams.list_exams` + `my_results`, `campus_transport.me`,
`campus_hostel.me`, notices, and derived alerts. Every block runs inside
`_safe()` so one failure returns `null` for that block only. Router
`routers/parent_portal.py` at `/api/v1/parents/campus` (parent role only).
Trap fixed: `/parents` is now in axios `noSlashEndpoints` — it was missing, so
the old `/parents/digest` call 404'd in the browser. UI `pages/parent/dashboard.tsx`.

## Fee collection (2026-09-12)

`models/tuition_collection.py` (Alembic 0043: `tuition_invoices`,
`tuition_online_orders`, plus `received_by` / `verification_*` columns on
`tuition_payments`), `services/tuition_collection.py`, `routers/
tuition_collection.py` under `/fees/{cash,payments/{id}/verify,receipts/{id}/pdf,
assignments/{id}/invoices,invoices/{id},online/status,assignments/{id}/online-orders,
online-orders/{id}/verify|reconcile}`. `tuition_service.record_payment` was split:
validation + `_receiver()` there, posting in `_post_payment()` (payment row, ledger
allocations, receipt, audit inside one savepoint) — the online path calls the same
core, never a second ledger writer. Rules: cash/cheque REQUIRE `received_by_member_id`
(owner/admin/teacher) and start `pending`; `verify_payment` refuses the receiver
while another manager exists (sole manager self-verifies with an audit tag). Online:
`_creds()` / `_client()` are the monkeypatch seams; `fulfil_online_order` is
idempotent on `gateway_payment_id`, posts `min(amount, balance)` and parks the rest
in `excess_amount` (`paid_excess`, surfaced on the cash desk and Today). The shared
`/api/v1/payments/webhook` routes captures to it via `webhook_processor` before the
exam-paper branch. Invoices are snapshots (`lines_json`), status derived at read.
Frontend: `FeeCashDesk.tsx`, `lib/razorpayCheckout.ts`, Pay online / Invoice /
Receipt PDF in `CampusFinance.tsx`, Pay now on the parent portal tile (portal `fees`
now carries `assignment_id` + `next_due.installment_id`). Trap: the preview SQLite is
built with `create_all`, so column additions need the migration applied by hand
(see INSTITUTION_BUILD.md); tests use 8+ character Idempotency-Keys.
