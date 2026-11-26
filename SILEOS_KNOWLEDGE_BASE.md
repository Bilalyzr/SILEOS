# SILEOS Knowledge Base

Living document for developers working on SILEOS (the SashaInfinity learning platform). Read this first, then the module sections you touch.

**Maintenance rule:** whenever a feature, bug fix, config change or architecture change lands, update the relevant section here in the same commit. Record the date of the change in the changelog at the bottom.

---

## 1. Project overview

SILEOS is a learning management system with several product areas on one codebase:

- **Learning:** courses, lessons, quizzes, assignments, progress, certificates, labs (browser labs, virtual labs, 3D models), coding challenges, live classes and recordings.
- **Commerce:** cart, checkout, coupons, bundles, memberships, Razorpay payments, invoices.
- **Company and career:** company dashboards, internships, candidate profiles.
- **Campus OS:** admissions, tuition and fee collection, exams, transport, hostel, staff, parent portal, WhatsApp and mail messaging.
- **Content:** Tamil-language category pages (Meiporul, Seyappaduporul, Utporul), blog, content libraries, Hall of Fame.
- **Admin and superadmin tools:** course studio, certificate designer, analytics, AI layer, gradebook.

Roles: Student, Instructor, Admin, Company, CompanyManager, plus superadmin.

### Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 5, TypeScript, React Router 6, Zustand, TanStack Query, Axios, framer-motion, three.js 0.183 |
| Backend | Python, FastAPI 0.104, SQLAlchemy 2, Pydantic, uvicorn (4 workers in dev), Redis, Sentry |
| Database | PostgreSQL. Schema is created by `create_all` at backend startup; SQL files live in `backend/migrations/` |
| Queues and background work | `recording-worker` (runs background loops), `code-judge-worker` (Judge0 sandbox, opt-in profile `coding`) |
| Video | `streaming-service` (yt-dlp proxy on port 8001), Bunny CDN, Jitsi for live classes |
| Edge | Nginx reverse proxy, Cloudflare in front, Let's Encrypt certificates on the host |
| Deployment | Docker Compose; GitHub Actions self-hosted runner on the VPS |

---

## 2. Architecture

### 2.1 Runtime topology

```mermaid
flowchart LR
  U[Browser] --> CF[Cloudflare]
  CF --> HN[Host nginx<br/>TLS vhost]
  HN --> EN[Edge nginx container<br/>127.0.0.1:4100]
  EN -->|/| FE[frontend container<br/>static Vite build]
  EN -->|/api/v1/*, /health, /uploads| BE[backend container<br/>FastAPI + uvicorn x4]
  EN -->|/api/v1/stream/*| SS[streaming-service :8001]
  BE --> PG[(PostgreSQL)]
  BE --> RD[(Redis)]
  RW[recording-worker] --> PG
  RW --> RD
  CJ[code-judge-worker] --> PG
  CJ --> J0[Judge0 sandbox]
  BE --> EXT[Razorpay, Bunny, SMTP,<br/>Google/LinkedIn OAuth, Jitsi]
```

Production nginx (`nginx/conf.d/default.production.conf`) routes `/api/v1/stream/` straight to the streaming service on port 8001. The dev edge (`nginx/conf.d/default.conf`, `nginx/conf.d.local/default.conf`) sends `/` to the frontend container on port 3000 and `/api/v1/` to the backend.

### 2.2 Request lifecycle

1. The browser loads the SPA from nginx. Hashed `/assets/*` files are cached long-term; `*.html` is not cached.
2. The SPA calls `/api/v1/...` through the Axios instance in `frontend/src/api/axios.ts`. It attaches the access token and refreshes it on 401.
3. nginx proxies to the backend. `main.py` runs security middleware (rate limits, security headers, request logging, optional IP allow-list), then CORS, then the router.
4. The router validates input with Pydantic schemas, authenticates through `core/security.py` and `routers/auth.py`, and calls a service in `services/`.
5. Services use SQLAlchemy sessions from `core/database.py` and Redis via `core/redis.py`.
6. Media: uploads go to `./uploads` (served at `/uploads`), certificates to `./certificates` (served at `/certificate-files`). Video goes through the streaming service or Bunny signed URLs.

### 2.3 Repository layout

```
sileos-dev/                     project root (this folder)
├── backend/
│   ├── app/
│   │   ├── main.py             REAL entry point; registers ~116 routers
│   │   ├── core/               config, database, redis, security, TOTP, uploads, middleware
│   │   ├── routers/            HTTP endpoints, one module per feature (~140 files)
│   │   ├── services/           business logic called by routers (~100 files)
│   │   ├── models/             SQLAlchemy models (~79 files)
│   │   ├── schemas/            Pydantic request and response models
│   │   ├── workers/            runtime.py (scheduler), recording_lessons.py
│   │   ├── api/v1/             certificate verification (public)
│   │   ├── migration/          legacy data migration helpers
│   │   └── seed_data*.py       demo data
│   ├── migrations/             hand-written SQL migrations
│   ├── alembic/                upstream reference only (not used at runtime)
│   ├── tests/                  pytest suite (~140 test files)
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx             route table
│   │   ├── pages/              route-level components (admin/, instructor/, student/, company/, superadmin/, parent/, spoc/ …)
│   │   ├── components/         feature folders: auth/gateway, sympho, labs, campus, ui, layout …
│   │   ├── api/                one module per backend area, plus axios.ts
│   │   ├── store/              Zustand stores (auth, cart, course, quiz)
│   │   ├── hooks/ utils/ lib/ types/ config/ styles/
│   │   └── offline/            offline support
│   ├── public/                 static assets, models/ar/*.glb (3D models), vendor/
│   └── vite.config.js          Vite config is JavaScript, not TypeScript
├── streaming-service/          video_streaming.py: yt-dlp proxy with range requests
├── code-judge-worker/          worker.py: runs learner code through Judge0
├── nginx/                      nginx.conf, conf.d/, conf.d.local/ (dev edge)
├── deploy/                     CI/CD scripts, production compose, runner bootstrap
├── .github/workflows/deploy.yml
├── docker-compose.yml          base dev stack
├── docker-compose.override.yml auto-merged locally
├── docker-compose.server.yml   THIS VPS only: port fixes, worker count, frontend volume fix
├── docker-compose.{prod,production,security,staging,ids,backup}.yml
└── .env                        secrets (gitignored). Never commit.
```

---

## 3. Modules and responsibilities

### 3.1 Backend core (`backend/app/core/`)

| File | Responsibility |
|---|---|
| `config.py` | pydantic-settings configuration with security defaults. `config_broken.py` is dead code; ignore it. |
| `database.py`, `database_async.py`, `database_postgres.py` | Sync and async SQLAlchemy engines and sessions. |
| `redis.py`, `redis_full.py` | Redis client. Redis stores sessions, revocations and rate-limit counters. |
| `security.py`, `auth_security.py` | Password hashing, JWT creation and validation, lockout rules. |
| `security_middleware.py` | Rate limiting, IP allow-list, request logging, security headers. |
| `totp.py` | RFC 6238 TOTP helpers (`pyotp`). Enforcement lives in `routers/auth.py`. |
| `cors.py`, `cache_headers.py` | CORS policy and cache-control headers. |
| `secure_upload.py`, `csv_safety.py`, `input_validation.py` | Upload checks, CSV formula-injection protection, input sanitising. |
| `runtime_telemetry.py`, `error_reporting.py` | Telemetry and Sentry. |
| `course_types.py`, `business_verticals.py`, `course_links.py` | Course-type rules and vertical (Meiporul / Seyappaduporul / Utporul) helpers. |

### 3.2 Backend routers (`backend/app/routers/`)

Each module is one feature area and is mounted in `main.py`, normally under `/api/v1/<name>`. Frequently touched groups:

| Group | Modules |
|---|---|
| Identity | `auth`, `users`, `admin`, `superadmin`, `platform_tenants` |
| Learning | `courses`, `lessons`, `quizzes`, `assignments`, `progress`, `certificates`, `certificate_designer`, `gradebook`, `mastery`, `learning_planner`, `learning_signals`, `scorable_items`, `question_banks`, `exam_papers` |
| Video and live | `video`, `video_streaming`, `player`, `bunny`, `youtube_embed`, `embed`, `live_classes`, `live_class_*`, `recording_lessons`, `jitsi` services |
| Labs and 3D | `labs`, `lab_studio`, `virtual_labs`, `three_d`, `three_d_tasks`, `geogebra`, `h5p`, `coding_assessments`, `coding_judge_internal` |
| Commerce | `checkout`, `cart`-related in `orders`, `payments`, `payments_proxy`, `coupons`, `bundles`, `memberships`, `commercial`, `payouts`, `company_billing` |
| Company | `companies`, `company_dashboard`, `internships`, `candidate`, `cohorts` |
| Campus OS | `admissions`, `tuition`, `tuition_collection`, `tuition_reminders`, `campus_*` (exams, staff, transport, hostel, growth, pilot, operations, control plane), `parent_portal`, `parents`, `whatsapp` |
| Growth and engagement | `growth`, `funnel`, `flywheel`, `gamification`, `games`, `notifications`, `wishlist`, `hall_of_fame`, `blog` |
| Content | `library`, `content_library_admin`, `studio`, `curriculum_workspace`, `assessment_studio`, `uploads`, `chunked_upload` (mounted at `/upload/chunked`) |
| Ops | `observability` (private metrics), `operations`, `course_ops`, `export_import` |

Two mounts to remember: `chunked_upload` is not under `/api/v1`, and the WhatsApp webhook has its own nginx location.

### 3.3 Services (`backend/app/services/`)

Services hold business rules. Routers stay thin. Examples:

- `auth_service`: account rules, login flow support.
- `course_service`, `course_access`, `course_ops_service`, `course_package_service`: enrolment and access checks.
- `cart_checkout`, `coupon_service`, `fulfillment_service`, `invoice_service`, `invoice_pdf`: order-to-enrolment flow.
- `certificate_service`, `certificate_html_renderer`: certificate generation.
- `email_service`, `campus_mail`, `campus_whatsapp`: messaging.
- `lab_*_service`, `glb_budget`: 3D lab catalogue and model budget checks.
- `campus_*`, `growth_*`, `attendance_report`, `class_report_service`: Campus OS reporting and operations.
- `jitsi_token_service`: signed Jitsi tokens.
- `ai_layer_service`, `ai_provider_vault`: AI provider selection and key storage.

### 3.4 Models and schemas

- `models/` holds about 79 SQLAlchemy models. Key ones: `user`, `course`, `enrollment`, `payment`, `certificate`, `quiz`, `assignment`, `company`, `internship`, `candidate`, `cohort`, `page_view`.
- `schemas/` holds Pydantic request and response types. Keep them in step with the models.

### 3.5 Background workers

- **`recording-worker`** runs `python -m app.workers.recording_lessons` and the background loops (`BACKGROUND_TASK_MODE=worker`). Keeping loops out of the API workers stops them running once per uvicorn process.
- **`app/workers/runtime.py`** is a supervised maintenance scheduler. Redis picks the scheduler. Durable database claims and Postgres advisory locks are the safety boundary, so duplicate delivery is avoided at the database layer.
- **Judge0 sandbox** (`docker-compose.judge0.yml`, `judge0/judge0.conf`, gitignored): `judge0-server`, `judge0-workers`, `judge0-db`, `judge0-redis`. Internal network only, privileged. Runs on dev and is wired to `code-judge-worker`. Java is currently blocked; see `docs/CODING_PLATFORM_PLAN.md`, Phase 0.
- **`code-judge-worker`** leases Utporul coding submissions and runs each test case in a Judge0 sandbox with networking disabled. It never executes learner code itself. Enable with compose profile `coding`.

### 3.6 Streaming service (`streaming-service/video_streaming.py`)

- Standalone FastAPI app on port 8001.
- Resolves unlisted YouTube videos with `yt-dlp` and proxies the stream with HTTP range support.
- In-memory URL cache with a 10-minute TTL.
- Its own CORS is open (`*`) and it has no auth. **The backend must authorise the learner before a client is sent here.**
- Code is baked into its image; only the yt-dlp cache is mounted.

### 3.7 Frontend (`frontend/src/`)

- **Routing** (`App.tsx`): public pages (`/`, `/courses`, `/labs`, `/hall-of-fame`, `/bundles`, `/membership`), auth pages (`/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password`), and role-based areas (`/dashboard`, `/admin/*`, `/instructor/*`, `/company/*`, `/parent/*`, `/superadmin/*`, `/spoc/*`).
- **API layer** (`api/`): one module per backend area, all using the shared `axios.ts`. Keep URL paths in these modules, not in components.
- **State** (`store/`): Zustand for auth, cart, course and quiz state. TanStack Query handles server data.
- **Auth gateway** (`components/auth/gateway/`): the sign-in and sign-up experience ("Infinity Gateway"). `auth-layout.tsx` wraps `/login` and `/register`, and `GatewayCanvas.tsx` draws the animated network behind them.
- **3D** (`components/sympho/`, `pages/meiporul-ar.tsx`): three.js scenes for the hero and the AR gallery. Models are GLB files in `frontend/public/models/ar/` and are meshopt-compressed for the gallery (decoder at `public/vendor/meshopt_decoder.js`).
- **Page guides** (`page-guides.ts`): contextual help. Auth pages are excluded on purpose.
- **Frontend is baked at build time.** `VITE_*` variables are read during `npm run build`, so changing them needs a rebuild.

---

## 4. Key business logic and concepts

### 4.1 Authentication and sessions

- **Access and refresh tokens:** JWTs. Access tokens are short-lived. The refresh flow is `POST /api/v1/auth/refresh`.
- **Shared session cookie:** `sf_ss` is set by `_set_shared_session` in `routers/auth.py` so the LMS and SILEOS can recognise the same user.
- **Revocation:** sessions are tracked in Redis. `revoke_all_user_sessions` runs on logout.
- **Logout** (`POST /api/v1/auth/logout`) does not require a valid access token. It always clears the shared cookie and revokes sessions. It identifies the user from the bearer token or from the refresh token in the body or cookie. Impersonation tokens do not revoke all sessions. Before this rule, a refresh could bring back a logged-out session.
- **Admin 2FA:** mandatory for admins. The secret is stored on `User.totp_secret`, with `User.totp_enabled` as the flag. `_federated_totp_gate` applies the check to Google and LinkedIn sign-ins too.
- **Lockout and rate limits:** governed by `MAX_LOGIN_ATTEMPTS`, `LOCKOUT_DURATION_MINUTES` and `RATE_LIMIT_*` in `.env`.
- **OAuth:** Google (`/api/v1/auth/google/...`) and LinkedIn (`/api/v1/auth/linkedin/...`). The LinkedIn redirect is hard-coded to the LMS host, so check it before using LinkedIn on SILEOS.

### 4.2 Enrolment and access

- Purchases, bundles and memberships create enrolments through `fulfillment_service` and `course_access`.
- Course access is checked on the server for every lesson and video request. Frontend checks are for display only.
- Certificates are issued when progress and assessment rules are met. Public verification is at `api/v1/certificate_verification.py`, and the verification endpoint requires a certificate hash.

### 4.3 Payments

- Razorpay handles checkout. Webhooks are verified with `RAZORPAY_WEBHOOK_SECRET`.
- Dev keys are placeholders, so checkout cannot be tested on the dev server.
- Invoices are generated as PDFs (`invoice_pdf.py`).

### 4.4 Video and content protection

- Bunny CDN serves signed URLs (`BUNNY_SIGNED_URL_TTL`).
- YouTube lessons go through the streaming service. The backend checks access before handing out the stream.
- Uploads are scanned and checked by `secure_upload.py` (`SCAN_UPLOADED_FILES`, `QUARANTINE_INFECTED_FILES`).

### 4.5 3D models and performance

- Each GLB must stay within the budget in `glb_budget.py`. Large models should be compressed with meshopt (gltf-transform).
- The hero scene caps device pixel ratio at 2 (1.25 in low-quality mode), and it starts only after the opening loader has been removed.
- Models in `public/models/ar/` are gitignored by `.gitignore`. Force-add them when committing.

### 4.6 Campus OS

- Admissions, tuition and fee collection, exams, transport, hostel, staff leave and substitution, parent portal and messaging. Each has a `campus_*` router and service.
- Reminders are run by `tuition_reminders`. WhatsApp uses `whatsapp` and `campus_whatsapp`.

---

## 5. Setup

### 5.1 Local development (Docker, recommended)

```bash
cp .env.example .env          # then fill in real values
docker compose up -d
docker compose logs -f backend
```

Local ports: frontend `http://localhost:4000`, edge `http://localhost:4100`, backend `http://localhost:8100`, streaming `http://localhost:8101`, Postgres `127.0.0.1:15432`.

### 5.2 Frontend without Docker

```bash
cd frontend
npm ci
npm run dev        # Vite dev server
npm run build      # production bundle to dist/
npx --no-install vitest run
```

### 5.3 Backend without Docker

```bash
cd backend
pip install -r requirements.txt
pytest
```

### 5.4 Creating an admin

- `backend/create_admin.py` and `seed_admin.py` create admin users. `create_admin.sh` wraps them.
- The admin account needs 2FA enrolment on first login.
- **Never put admin passwords in documentation or commit them.** Keep credentials in `.env` or a password manager.

---

## 6. Deployment and maintenance

### 6.1 CI/CD

`.github/workflows/deploy.yml` runs on push to `main`:

```
quality (lint, pytest, shellcheck) → build (images, local) → deploy (blue-safe recreate) → verify (public URL)
```

- Runs on the self-hosted runner on the VPS. Pull requests run quality and build only.
- `workflow_dispatch` allows a manual deploy or rollback.

### 6.2 Git workflow

- Work on `development`. Push to GitHub with `git push origin development:main`.
- Commit identity: use the deploy author configured for this repo.
- Do not commit `docker-compose.server.yml`, `frontend/dist*` or `.env`.
- Git history and conventions for AI-assisted commits are in `CLAUDE.md` and `AGENTS.md`.

### 6.3 Deploying changes

| Change type | Command |
|---|---|
| Backend code | `docker compose restart backend` (code is bind-mounted) |
| Backend dependencies | `docker compose build backend && docker compose up -d backend` |
| Frontend | `docker compose build frontend && docker compose up -d --no-deps frontend && docker compose restart nginx` |
| Streaming service | rebuild its image, then `up -d` |
| Database schema | applied at backend startup via `create_all`; run SQL in `backend/migrations/` by hand when a change is not additive |

Restarting nginx after a frontend rebuild is needed because nginx caches container IP addresses.

### 6.4 Server-specific rules (this VPS)

- Production LMS containers share this host. `docker-compose.server.yml` strips ports 3100 and 8000 so the dev stack does not collide with them.
- `UVICORN_WORKERS` in `.env` sets the backend worker count (default 4).
- The old `frontend/dist.stale-sep26/` folder is quarantined. Do not restore it, because it once masked every frontend rebuild.
- Never run `build-production.sh` casually: it runs `docker system prune -f` on the whole host.

### 6.5 Backups

- Database dumps go to `database/backups/`.
- Restore guidance is in `RESTORE_GUIDE.md`.

### 6.6 Monitoring

- `/health` and `/health/ready` on the backend, `/health/version` for the deployed version.
- Sentry through `sentry-sdk` if configured.
- Private metrics at `/api/v1/internal/observability`.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Site shows old UI after a deploy | Frontend image not rebuilt, or stale `dist` folder mounted | Rebuild frontend, `up -d`, restart nginx. Confirm `frontend/dist` is not mounted. |
| API calls return 502 or 404 | Backend not up, or nginx holding an old container IP | `docker compose ps`, then `docker compose restart nginx`. |
| Backend code change has no effect | Container not restarted | `docker compose restart backend`. |
| Logout does not end session | Refresh token still valid, or sessions not revoked | Confirm `/auth/logout` returns 200 and Redis revocation keys exist. |
| Admin 2FA code rejected | Phone clock drift, or secret replaced | Enable automatic time on the phone and retry. If the secret is lost, an admin with DB access re-enrols the user. Never share codes. |
| Tokens invalid after restart | `SECRET_KEY` / `JWT_SECRET` left as placeholder (regenerated each boot) | Set real values in `.env`. |
| Video will not play | Streaming service down, or yt-dlp cache stale, or cookies expired | Check `streaming-service` health on 8101 and refresh `youtube_cookies.txt`. |
| 3D model missing in AR gallery | GLB not in `public/models/ar`, or meshopt decoder not loaded | Confirm the file exists and that `MESHOPT_DECODER_SRC` is set in `meiporul-ar.tsx`. |
| Payments fail on dev | Razorpay keys are placeholders | Expected on dev. Use test keys on a staging stack. |
| Email not sent | SMTP not configured or invalid | Check `SMTP_*` in `.env` and run `backend/check_smtp.py`. |
| Coding challenge never graded | `code-judge-worker` not running, or Judge0 down | `docker compose ps judge0-server code-judge-worker`. The worker runs by default on dev. |
| Judge0 runs fail with `Internal Error … /box/script.py` | isolate cannot use cgroup v2 | Judge0 must use per-process limits (`ENABLE_PER_PROCESS_AND_THREAD_*=true` in `judge0/judge0.conf`). |
| Node or TypeScript run times out or aborts | Memory cap too low for Node's address space | The worker applies a 1 GB floor (`MIN_MEMORY_MB` in `code-judge-worker/worker.py`). |
| Java submissions fail with `pthread_create EAGAIN` | JVM exceeds Judge0 thread and address-space caps | Known blocker. Do not enable Java in challenges yet. |
| Tests fail on stale expectations | Tests out of date with UI or API changes | Update the test to the current behaviour, after checking the change is intended. |

Useful commands:

```bash
docker compose ps
docker compose logs --tail=200 backend
docker compose exec postgres psql -U "$DB_USER" "$DB_NAME"   # DB_USER / DB_NAME from .env
cd backend && pytest -q                                       # run tests on the host (pytest is not in the backend image)
```

---

## 8. Onboarding guide for new developers

1. **Read in this order:** this file, `CLAUDE.md` (conventions and traps), `AGENTS.md` (boundaries and gotchas), `DEV-README.md` (this server), `BUILD.md`.
2. **Get the stack running** using section 5.1. Confirm the homepage loads at the local edge.
3. **Learn the entry points:** `backend/app/main.py`, `frontend/src/App.tsx`, and the API modules in `frontend/src/api/`.
4. **Pick a small first task** such as a copy change or a test fix. Follow the path: router, service, model, schema, then API client, then page.
5. **Know the traps:**
   - Only `main.py` is the real backend entry. Ignore `main_*.py` variants and `config_broken.py`.
   - The frontend is baked at build time. Rebuild after `VITE_*` or UI changes.
   - Five compose files exist. Check which one applies before editing.
   - Do not commit secrets or `.env`.
6. **Test before pushing:** `pytest` for backend, `vitest` and `tsc --noEmit` for frontend.
7. **Update this file** if your change alters behaviour, setup or deployment.

---

## 9. Known gaps and open items

- The LinkedIn OAuth redirect is hard-coded to the LMS host.
- `apple-vision-pro.glb` is no longer used by the hero; the Meta Quest 3S model replaced it. Confirm before deleting.
- The Meta Quest 3S model has no licence recorded. Confirm usage rights before public launch.
- Razorpay, Bunny, Firebase, Edgyy and Jitsi credentials are placeholders on dev.
- Some older docs (`README.md`, `CLAUDE.md` router counts, the frontend port 3000 in the architecture diagram) describe earlier states. Trust the code and compose files first.
- Several `.md` files at the root are historical release notes. Keep new documentation in this file, or in `docs/`.

---

## 10. Changelog

- **2026-11-26:** Live coding platform plan added at `docs/CODING_PLATFORM_PLAN.md` (proposed, not started).
- **2026-11-26:** Judge0 sandbox added on dev for the coding worker (Phase 0): 5 of 6 languages pass end to end; Java blocked. Worker gained a Node memory floor.
- **2026-11-26:** First version of this knowledge base, written from the repository layout, compose files, routers, services, nginx configs and CI workflow.
- **2026-10-30:** Infinity Gateway sign-in and sign-up redesign; logout now fully revokes sessions; hero swapped to Meta Quest 3S; gallery models compressed (meshopt); opening loader smoothed; page-header blueprints redesigned.
- **2026-10-29:** Backend moved to 4 uvicorn workers without reload (performance fix); frontend stale-build volume fixed.
- **2026-10-19:** Dev stack moved out of the LMS tree; `docker-compose.server.yml` added.
