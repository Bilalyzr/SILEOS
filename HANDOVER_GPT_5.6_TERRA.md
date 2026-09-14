# HANDOVER — Sasha LMS to GPT 5.6 Terra

**From:** Claude Fable 5.1, controller of the 2026-09-05 → 2026-09-06 build loop
**Date:** 2026-09-06
**Owner:** SashaInfinity ("bro") — English only, direct, verify every button, never claim untested work
**Read with this file:** `CLAUDE.md` (binding conventions and traps, one section per feature), `docs/OWNER_DECISIONS.md` (binding decisions 1–31), `docs/NEXT_BUILD_PLAN.md` (what to build next + the complete UI change instruction set), the ledger `docs/superpowers/plans/2026-09-05-v2-architecture-gap-build.md` sections D–H.

---

## 0. TL;DR

Sasha LMS is a FastAPI + React learning platform for the Indian market (Tamil-specific taxonomy: Meiporul / Seyappaduporul / Utporul course types). Over the last three sprints it grew from a course-and-payments LMS into a full learning platform: live classes, H5P, native games, 3D models with match-and-verify tasks, virtual labs, a learner mastery graph, gamification, memberships, bundles, company invoicing, question banks, an AI layer (GLM, honest 503 without a key), a parent portal, a sales funnel, retention automation, media tiers, and — last — a learning-signals engine that watches *how* a learner learns and builds adaptive practice from it.

State at handover: backend suite **1540 passed / 4 skipped**, API smoke **27/27**, frontend lint **0 errors / 26 baseline warnings**, Alembic head **0020**. Every feature was verified in the embedded browser before it was reported. Nothing is half-built. The biggest open item is not a feature: **the glass/orange UI system exists but only 3 of 154 pages use it.** The plan document tells you exactly how to roll it out.

## 1. Environment and how to run

**Repo:** this zip (`Sasha_LMS_handover_Fable5.1_2026-09-05/`). Not a git repository. A second, older checkout exists at `C:\Users\Admin\Downloads\Sasha_lms-main (2)` — another agent's tree, NEVER commit, revert or delete anything there. This zip is the newest line.

**Python:** the venv that works is `C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe` (bcrypt 4.0.1 pinned; the global Python breaks passlib). If it is gone, create one from `backend/requirements.txt` and pin `bcrypt==4.0.1`.

**Dev servers (preferred):** `.claude/launch.json` defines `qa-backend` (uvicorn on **:8011**, SQLite `backend/visual_qa.db`, `RATE_LIMIT_REQUESTS_PER_MINUTE=600`) and `qa-frontend` (Vite on **:3001**, proxies to 8011). Ports 8010/3000 are held by the predecessor's session on this machine — do not fight for them. The backend runs without `--reload`: **stop and start it after every backend change.**

Manual equivalent:
```bash
cd backend && DATABASE_URL="sqlite:///./visual_qa.db" REDIS_URL="redis://localhost:6379/0" SECRET_KEY=<64 chars> JWT_SECRET=<64 chars> VIDEO_SECRET=<32 chars> ENVIRONMENT=development RATE_LIMIT_REQUESTS_PER_MINUTE=600 <venv-python> -m uvicorn app.main:app --host 127.0.0.1 --port 8011
```
```bash
cd frontend && VITE_PROXY_TARGET=http://localhost:8011 VITE_DEV_PORT=3001 npm run dev
```

**Docker is down on this machine**, so Redis is unreachable. Rate limiting fails OPEN for 30 s after a Redis error (circuit breaker in `app/core/security_middleware.py`) — this is deliberate. Tests never touch a real Redis (autouse `_isolate_redis` fixture pins a `MockRedis`).

**Demo DB (ships in the zip):** `backend/visual_qa.db`, migrated to head 0020, seeded. Accounts (password `Demo@1234`):

| Account | Role | User id |
|---|---|---|
| `priya@sashademo.com` | instructor | 1 |
| `admin@sashademo.com` | admin (TOTP secret `Y2Z3VE7HVT35QBQ4BOQLAOKF54FWDRQK`) | 2 |
| `arjun@sashademo.com` | student | 3 |
| `parent@demo.com` / `Parent@1234` | parent, linked to arjun | 4 |

Demo course 5 = "Explore 3D & Labs" (Utporul, published): video lesson 2 (has concept markers + seeded learning signals), 3D lesson 8, labs 16/20/21, quiz 1 (8 questions + scored modules). Course 2 = "Python for Data Analysis". Arjun is enrolled in both.

**Tokens (8-hour JWTs):** never log in repeatedly (429s). Mint with:
```bash
cd backend && <venv-python> -c "from app.core.security import create_access_token as c; print(c({'sub':'3'}))"
```
Browser auth injection: fetch `/api/v1/auth/me` and `/api/v1/users/profile` with the token, then `localStorage.setItem('auth-storage', JSON.stringify({state:{user,profile,instructorProfile:null,accessToken,refreshToken:null,isAuthenticated:true},version:0}))` and reload.

**Checks (run all four before reporting anything done):**
```bash
cd backend && <venv-python> -m pytest tests/ -q          # ~8 min, expect 1540 passed / 4 skipped
```
```bash
SMOKE_BASE=http://127.0.0.1:8011/api/v1 bash scripts/smoke.sh <student_token> <instructor_token>   # 27/27
```
```bash
cd frontend && npm run lint                                # 0 errors, 26 exhaustive-deps warnings is the baseline
```
```bash
cd frontend && npx tsc --noEmit | grep -c "error TS"      # ~393 pre-existing; zero NEW errors in files you touch
```
`tsc` has never been a gate on this codebase — check only the files you changed. `pyflakes app` after touching routers (a missing `Any` import once turned a JSON body into a required query param with no error).

## 2. What exists (map)

Each line names the doc or code that is the source of truth. `CLAUDE.md` has a paragraph per feature with the traps.

**Core LMS (pre-existing):** courses/lessons/sections, enrollments, Razorpay payments with triple-redundant fulfilment (verify + webhook + reconciliation sweeper), certificates (designer + headless-Chrome renderer), quizzes/assignments with hardened state machines, gradebook, blog, coupons, wishlist, company portal (internships, work logs, attendance), streaming service (yt-dlp proxy) + Bunny CDN, Flutter app (compile-untested).

**Type-driven v2.0 (ZCode sprint, 2026-09-04/05):** course types MP/SP/UP with `type_profiles` weights, tool matrix (`app/core/course_types.py`), draft-first course creation → tabbed editor, GeoGebra (free courses only, licence unresolved), 3D GLB models (`/api/v1/three-d`, private storage), PhET virtual labs, H5P + games as lesson types, quiz-as-container (`Quiz.interactive_modules`), cumulative grading, question banks + item analysis, xAPI spine, at-risk rules, ebook library, live-class past-classes report, GLM AI layer (tutor, JEE/NEET paper generator, lesson curation), parent layer, games marketplace.

**Fable 5.1 session (2026-09-05 → 06), in order:**
1. **Error sweep** — Redis isolation in tests, pyflakes guard, ESLint config, launch.json ports.
2. **Content libraries** (`docs/CONTENT_LIBRARIES.md`) — admin-curated virtual labs (PhET/embed/native `reaction_lab` + `identify_lab` engines), 3D library, prebuilt game packs, `/admin/content-libraries`.
3. **v2.0 gap build WP1–WP9** (ledger section D): scorable-item contract, 3D match-and-verify tasks (7 types, server-graded, evidence confidence), learner mastery graph (`/api/v1/mastery`, `/my-mastery`, coverage report), emergent tag taxonomy, live-class classification + retention ("media expires, knowledge does not"), studio faces per course type, AI layer completion, flywheel extras (agenda, insight cards, teach-back), quality pass.
4. **Public lesson preview + glass UI system** (ledger E) — any lesson type can be a public preview behind a real server-side lock (`is_locked`); `GlassDialog` + `useConfirm` replaced all 63 browser prompts; tokens in `styles/globals.css`.
5. **3D teach-and-examine kit** (`docs/3D_TEACHING.md`) — `ThreeDTeachingKit`, `ThreeDCheckYourself`.
6. **Roadmap R1–R10** (ledger F) — sales funnel (`/api/v1/funnel`), review-queue habit, course ops (clone/templates/CSV import/co-instructors, `services/course_access.can_edit()` is THE edit rule), payments polish (UPI/EMI blocks, refunds, membership coupons via Razorpay Offers), quiz integrity (advisory), data saver, cohort mastery.
7. **Round 2** (ledger G) — visual pass, retention automation (`services/retention_service.py`, idempotent via Notification rows), instructor earnings + PDF, banks at scale (push-to-quiz, CSV export, per-attempt random subsets), media tiers (gltf-transform T2/T3, ffmpeg audio-only renditions).
8. **Learning-signals engine** (ledger H) — `frontend/src/api/signals.ts` buffered tracker; lesson player + quiz taking instrumented; `learning_signals` bucketed into 10-second segments; instructor concept markers per lesson; explainable struggle profile ("rewound 3× · left early 1× · hesitated on 1 question"); adaptive practice built from the profile, graded server-side, feeding the mastery graph. UI: My Mastery "Where you struggle" + "Practice built for you"; course editor "Struggle map" on every non-quiz lecture.

## 3. Verification state (last full run, 2026-09-06)

| Check | Result |
|---|---|
| Backend `pytest tests/` | 1540 passed, 4 skipped |
| `scripts/smoke.sh` | 27 / 27 |
| `npm run lint` | 0 errors, 26 warnings (baseline) |
| Browser | every feature in §2 items 2–8 exercised live as student, instructor and admin |

Known non-issues: the four skipped tests need Chrome/Selenium; `tsc` baseline ~393 errors is pre-existing and frozen (zero new allowed).

## 4. Owner profile and working rules (binding)

- Address him as "bro". English only. Plain language; when he asks what something means, explain with a worked example.
- Loop: **PLAN → BUILD → CHECK → FIX → repeat.** Never skip CHECK. Failures first in every report. "Honest 503 without the key" counts as a pass for AI/WhatsApp features.
- Build step by step without asking permission mid-build. When he asks "what's next", bring an ordered list with one line each; he picks numbers ("proceed with 2,3,4,5,9").
- He tests every button in the browser himself. If it is not clickable and verified, it is not done.
- Leave things that need him (keys, licences, dashboard configuration) as **interventions**, listed at the end of each report and appended to `docs/OWNER_DECISIONS.md` — never guess a secret, never write a key he pasted in chat into a file (tell him to rotate it and put it in `backend/.env` himself).
- Decisions and assumptions go in `docs/OWNER_DECISIONS.md` with a running number (next is 32).

## 5. Non-negotiables (details in CLAUDE.md)

1. Lesson content types are ATOMIC PAIRS through `courses.py::_resolve_lesson_content_fields` (type + id in the same request). 3D lessons attach to MP/UP courses only; GeoGebra to free courses only.
2. `redirect_slashes=False` — every new API prefix goes in `frontend/src/api/axios.ts::noSlashEndpoints`, or the page 404s silently.
3. `main.py`'s global 404 handler rewrites every 404 detail to "Endpoint not found" — use 422 for user-facing validation messages.
4. `award()`, `emit_statement`, `safe_record_evidence`, `signal ingestion`: flush-only / best-effort, called AFTER the host request's commit, never allowed to fail the host.
5. AI only through `app/services/llm_provider.call_glm`; no key → honest 503; output is always a human-reviewed draft.
6. FormData: never set `Content-Type` (the axios interceptor strips it).
7. UI popups: `GlassDialog` + `useConfirm` (`confirmDialog` / `promptDialog`, must be `await`ed) — no `window.confirm/prompt/alert` anywhere.
8. No `dangerouslySetInnerHTML` for instructor-authored content (games, labs, 3D, signals) — render as React text.
9. Patch TSX files with a Python script (assert-count on the anchor, `ast.parse` for `.py`), never multi-line bash heredocs for code.
10. Every new table = Alembic revision (guarded `has_table`/`has_column`, `reflect_kwargs={"resolve_fks": False}` for SQLite batch ops) + parity SQL in `backend/migrations/` + `ensure_schema()` where the dev DB needs a column.

## 6. Interventions still owned by the owner

1. `GLM_API_KEY` in `backend/.env` and `.claude/launch.json` env (he pasted a Zhipu key in chat on 2026-09-05 — it must be rotated; it was never written to disk).
2. `MSG91_API_KEY` for WhatsApp parent digests.
3. GeoGebra commercial licence before any paid GeoGebra exposure.
4. Razorpay dashboard: webhook + `RAZORPAY_WEBHOOK_SECRET`, Offers for membership coupons, EMI enablement.
5. Flutter toolchain (`flutter pub get` + `build_runner`) — mobile code is compile-untested.
6. Production host: `ffmpeg` and `@gltf-transform/cli` installed; Chrome for certificate thumbnails.
7. DigiLocker credentials (`DIGILOCKER_CLIENT_ID/_SECRET`) — adapter is a 503 until then.
8. Production rate limit stays 60/min/IP unless he decides otherwise (classrooms behind one NAT may need 300+).
9. Production deploy pass has never been exercised (Postgres, `docker-compose.production.yml`, Bunny/Jitsi env).

## 7. What to build next

The ordered plan with acceptance criteria is `docs/NEXT_BUILD_PLAN.md`. Short version:

1. **UI system rollout** — migrate the 151 pages that still use ad-hoc white cards onto the glass/orange system, page group by page group, with the shell (header, sidebar, layouts) first. This is the owner's most-repeated request ("UI that creates the story both in the front and internal system").
2. **Close the signals loop for instructors** — hot-segment alerts across learners, struggle profile inside the AI tutor prompt, cohort-level struggle map.
3. **Learner flow polish** — one "Continue learning" entry point, lesson player chrome, quiz result page, mastery → practice → lesson links.
4. **Engine A full** — recordings → transcript → segmented lesson (needs a transcription decision from the owner).
5. **Production readiness** — Postgres migration rehearsal, compose stack, monitoring, backups.

## 8. Repo noise (ignore)

Root: `2025-12-*.txt`, `dec_2_changes.txt`, `gitTok.md`, `lesson1.json`, `certificate.....png`, `lms-ss*.png`, `sasha_db_20260416.sql`, `wp-content/`, the many `deploy*.sh`/`*.bat`. `frontend/`: `ts_errors.txt`, `_plan.md`, the two filenames with spaces. `backend/`: `_patch_*.py`, `check_*.py`, `debug_*.py`, `delete_*.py`, `token.tmp`, `arjun-token2.txt`, `app/main_*.py` variants, `app/core/config_broken.py`. `docs/HANDOFF_NEXT_AGENT.md` and `HANDOVER_FABLE_5.1.md` are the two previous handovers — history, not instructions.

Build it clean, Terra. The owner trusts the loop — keep earning that.
