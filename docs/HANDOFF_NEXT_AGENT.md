# Handoff — SashaInfinity LMS build continuation

**From:** Claude (Fable 5), controller of segments 1–3 · **Date:** 2026-09-03
**To:** the next build agent (Z-GLM) · **Owner:** info.sashainfinity@gmail.com (returns ~Sept 10)

The owner is monetizing this platform to clear personal debt. Every shipped defect costs them real money and trust. That is why the working method below is non-negotiable: it caught a silently-corrupted answer key, a payment-path partial write, a score-zeroing timer bug, and an XSS-adjacent validation bypass before any user ever saw them.

---

## 1. Current state (exact)

- **Remote:** https://github.com/SashaInfinity/Sasha_lms — work lands on branch **`revenue-platform`** (currently the schema/handoff docs commit on top of `00c267c`). **NEVER touch remote `main`.** The owner downloads the platform as one ZIP of `revenue-platform`.
- **Shipped & verified (segments 1–3.1):** payment reliability core, memberships, bundles, company invoicing, launch surface, live classes, learning experience (assessments/H5P/certificate designer/gamification), **learning games** (docs/LEARNING_GAMES.md). All merged into `revenue-platform`, all suites green (backend 944 passed / 4 skipped committed-baseline, frontend 275/275, tsc 378 pre-existing errors — that number is the frozen baseline, zero NEW errors allowed).
- **In progress — Digital Library (sub-project 2 of segment 3):** branch **`digital-library`** (worktree `.worktrees/digital-library`, pushed to origin).
  - Spec: `docs/superpowers/specs/2026-09-03-digital-library-design.md` (binding).
  - Plan: `docs/superpowers/plans/2026-09-03-digital-library.md` (12 TDD tasks, real code in every step, binding).
  - Task 1 DONE + reviewed (commit `c44f942` — models, migration 0005; payment-table relaxation proven safe across 81 targeted payment tests).
  - Task 2 IMPLEMENTED, tests green (19/19 in `tests/test_library.py`), **but its adversarial review NEVER RAN** (commit `9d94336`). **Your first action: review Task 2 before building Task 3** (checklist: magic-byte bypasses, zip-bomb caps, path reassertion, per-owner cap arithmetic, uuid naming, no public exposure).
  - Tasks 3–12: unbuilt. Follow the plan document task by task.
  - Ledger (review verdicts, rulings, deferred minors): `docs/superpowers/handoff/digital-library-ledger.md` (committed copy; the live ledger path `.superpowers/` is gitignored scratch — recreate it there when you resume, seeded from this copy).
- **Queued after the library (segment 3 remainder, in this order):**
  3. **Classes/Sections + Parent Portal** — instructor-defined year/class/section rosters; parent accounts linked to student accounts; parent dashboard showing learning rate (progress velocity, quiz trends, attendance, streaks) for tutoring decisions. New spec needed (write it in the brainstorm→spec→plan style below).
  4. **Live-class whiteboard + attendance-gated replays** — whiteboard (evaluate Excalidraw embed vs Jitsi's whiteboard) in the live console; recordings already exist (Jibri→Bunny) — gate replay visibility to students with attendance rows for that class (`live_class_attendance`).
  5. **3D lessons** — port the Cognitive3D prototype (owner has it as a Claude artifact) into a real lesson type: hardened .glb upload (mirror H5P's zip hardening), Three.js player (real Three.js — the app has no CSP restriction; note `@react-three/drei` is already in package.json but pinned against react18 via `--legacy-peer-deps`), hotspot editor with narration, ZPD hooks into the quiz engine, instructor analytics.
- **Concurrent-session boundary (DO NOT TOUCH):** `backend/app/routers/payments_proxy.py` (modified) and `backend/tests/test_proxy_webhook_migration.py` (untracked) in the MAIN checkout belong to another session. Never commit, revert, or delete them. They also explain test-count drift: the main checkout collects 9 more tests than any worktree.
- **Owner-owned items (remind, don't do):** revoke the leaked PAT in `gitTok.md` (in git history!) at github.com/settings/tokens; two spawned task chips pending (enrollment-status normalization repo-wide; `award()` ledger/stats divergence fix).

## 2. The working method (follow it exactly)

Every feature runs this pipeline. Do not skip gates because something "looks simple" — the worst bugs above came from simple-looking tasks.

1. **Spec** — one markdown doc in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`: binding limits as exact numbers, endpoint contracts, security model, explicit out-of-scope list. Commit it.
2. **Plan** — `docs/superpowers/plans/YYYY-MM-DD-<topic>.md`: 10–12 TDD tasks; every task has Files (exact paths), Interfaces (exact signatures consumed/produced), and bite-sized checkbox steps containing REAL code (models, functions, tests with assertions) — never "add validation" or "similar to Task N". Read the two existing plans as templates. Self-review for spec coverage, placeholders, cross-task signature consistency. Commit it.
3. **Ledger** — a running progress file (one line per event: dispatched/implemented/review verdict/rulings/deferred minors/carried obligations). It is your recovery map after any interruption; trust it and `git log` over memory. Keep a committed copy under `docs/superpowers/handoff/` when pausing.
4. **Implement per task, TDD** — failing test first, watch it fail, implement, watch it pass, run the FULL relevant suite (zero regressions), commit. One task at a time, never parallel implementers on one worktree.
5. **Adversarial review per task** — a fresh reviewer (not the implementer) reads the brief, the implementer's report, and the full diff. It must PROVE findings with payloads/probes, not speculate ("write the exact malicious config that slips through"). Anything touching money, auth, uploads, or untrusted input gets the most capable reviewer available. Verdicts: spec compliance AND code quality, findings ranked Critical/Important/Minor with file:line + concrete failure scenario.
6. **Fix loop** — Critical/Important findings go back to the implementer (failing test first, again); a scoped re-review verifies each finding CLOSED empirically (re-run the exploit). Minors: fix if cheap, else ledger them as deferred with a one-line why. The CONTROLLER rules on judgment calls and records rulings in the ledger so later tasks inherit them.
7. **Final whole-branch review** — after all tasks: one broad review of the entire branch diff for cross-cutting issues per-task reviews can't see (seams between frontend/backend semantics, migration paths on real DBs, spec items with no implementation anywhere, XSS/authz sweeps) + triage of every deferred minor (MUST-FIX vs SHIP-AS-IS). Then ONE fix wave, one re-review.
8. **Merge + verify + push** — merge to `revenue-platform` in the main checkout, run BOTH full suites on the merged result, push to origin.
9. **Live QA** — migrate the local demo DB (`backend/visual_qa.db`: `alembic upgrade head` with `DATABASE_URL=sqlite:///./visual_qa.db`), run the feature's seed script, and walk the feature in a real browser end-to-end (instructor flow AND student flow, including one failure path). Unit tests repeatedly missed integration bugs that live QA caught (trailing-slash 404s, stale-process 404s, timer-expiry storage).

**Report honestly.** If tests fail, say so with output. If you skipped a gate, say so. The ledger records what actually happened, not what should have.

## 3. Environment & traps (each one cost real debugging time)

- **Python venv:** the ONLY working venv is `backend/.venv` in the MAIN checkout (`C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe`). Worktrees have none — run pytest from the worktree's `backend/` with that absolute interpreter. Global python has bcrypt 5.0 which breaks passlib (`AttributeError: __about__`); the venv pins bcrypt 4.0.1.
- **Frontend in worktrees:** run `npm install --legacy-peer-deps` once per worktree (react18 vs `@react-three/drei@10` peer conflict, pre-existing).
- **tsc:** `npx tsc --noEmit` has 378 pre-existing errors. Record the count before your change; zero NEW errors is the bar.
- **Trailing slashes:** backend runs `redirect_slashes=False`. Every new API prefix MUST be added to `noSlashEndpoints` in `frontend/src/api/axios.ts` and every route declared without trailing slash — this exact miss 404'd an entire feature invisibly (unit tests mock axios, so only live QA catches it).
- **`award()` (gamification) is FLUSH-ONLY** — the caller owns the transaction; call it best-effort try/except AFTER your own commit; event keys are UNIQUE (idempotency); copy an existing call site (h5p.py's hook) verbatim.
- **Lesson content types are ATOMIC PAIRS** — `lesson_content_type` + its FK (`h5p_content_id`/`game_id`) must ship in the same request; type-only PATCH is a 400. Frontend mapping lives in ONE shared helper: `frontend/src/lib/lessonContentSync.ts` — extend it, never inline-map in pages.
- **`components/layout/header.tsx` is DEAD CODE** — nav lives in `frontend/src/components/dashboard/nav-configs.ts` and the rendered PublicHeader/PublicFooter components.
- **H5P iframes:** `sandbox="allow-scripts"` ONLY — never add `allow-same-origin`.
- **Uploads:** `uploads/` is PUBLIC (nginx-served). Paid/private files go under `backend/<feature>/` and stream through authenticated endpoints (see `library_storage.py`, invoice PDFs).
- **No `dangerouslySetInnerHTML`** anywhere near instructor/student-authored content.
- **Prices:** rupees in DB, paise only at the Razorpay boundary. `create-order`/`verify` accept EXACTLY ONE of course_id/bundle_id/invoice_id(/ebook_id when Task 5 lands). Fulfillment idempotent on `gateway_payment_id`, converging from /verify + webhook + sweeper.
- **Admin login needs TOTP** (`otp_code` field, raw base32 secrets in `users.totp_secret`). Local demo accounts (dev DB only): admin@sashademo.com (TOTP secret in owner's records), priya@sashademo.com (instructor), arjun@sashademo.com (student) — password Demo@1234.
- **Local preview:** `.claude/launch.json` defines qa-backend (:8000, sqlite visual_qa.db) + qa-frontend (:3000). After merging backend changes, RESTART the backend process (a stale process serves 404s for new routers).
- **Local demo DB is at migration 0005** with 5 demo games + demo assessment content seeded.
- Full conventions and per-feature notes: `CLAUDE.md` (kept current — add your feature's entry when you ship). Full schema: `docs/PLATFORM_SCHEMA.md`.

## 4. Your exact TODO list, in order

1. Recreate the live ledger: copy `docs/superpowers/handoff/digital-library-ledger.md` → `.superpowers/sdd/2026-09-03-digital-library/progress.md` in the worktree.
2. **Review Task 2** (commit `9d94336`) adversarially per §2 step 5. Fix loop if needed.
3. Build Digital Library **Tasks 3–12** from the plan, gate by gate. Tasks 5 & 6 are the Razorpay money path — strongest review scrutiny, and honor the ledger's carried obligation: `admin.py` `course_breakdown` (~line 1751) must skip/label ebook OrderItems (it would render "Course #None"), with a test.
4. Final whole-branch review → fix wave → merge to `revenue-platform` → full suites on merged result → push → live QA per §2 step 9 (seed script: `backend/seed_library_demo.py` per plan Task 12).
5. Sub-project 3 (Parent Portal + sections): write spec → plan → pipeline. Design constraints: parent = new user role linked to student(s) via a join table; parents see ONLY their linked students' progress (no other students, no financials); instructors manage class/section rosters; reuse existing analytics data (lesson_progress, quiz_attempts, xp_events, live_class_attendance).
6. Sub-project 4 (whiteboard + gated replays) — smallest; extends live classes.
7. Sub-project 5 (3D lessons) — mirror the H5P/games integration patterns end to end.
8. After each merge: update `CLAUDE.md`, regenerate `docs/PLATFORM_SCHEMA.md`, keep the handoff ledger copies current.

Ship it clean. The owner trusts the process — keep earning that.
