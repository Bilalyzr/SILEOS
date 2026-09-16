# VPS Execution Prompt — Company Dashboard Redesign

> Paste everything between the `=== BEGIN ===` and `=== END ===` markers
> below into a fresh Claude Code session that's running **on the VPS host
> where your production stack lives**. The session needs full filesystem
> access to the SashaInfinity LMS repo and shell access to the running
> docker stack.
>
> Before pasting:
>
> 1. SSH into your VPS.
> 2. Make sure the repo is at the latest `main` and your `.env` /
>    `.env.production` are present.
> 3. Make sure Docker is running (`docker ps`).
> 4. Take a Postgres backup (the prompt also tells Claude to do this,
>    but a manual one beforehand never hurts).

---

```
=== BEGIN VPS EXECUTION PROMPT ===

You are Claude Code executing on the SashaInfinity LMS production VPS. Your job
is to ship the **Company Dashboard v2** — replacing the mock-data prototype
with the real, end-to-end implementation, and deploy it.

This is production work against live data. Move carefully, verify each step,
and STOP if anything looks wrong.

## Your context — read this first

- **Project:** SashaInfinity LMS — FastAPI + React + Postgres + Redis + nginx,
  all in Docker Compose. Project root contains `docker-compose.yml`,
  `docker-compose.production.yml`, `backend/`, `frontend/`, `nginx/`,
  `streaming-service/`. CLAUDE.md at the root has the full architecture
  brief — read it before doing anything.

- **Design spec (READ THIS FIRST):**
  `docs/superpowers/specs/2026-05-05-company-dashboard-redesign-design.md`

- **Implementation plan (your task list):**
  `docs/superpowers/plans/2026-05-05-company-dashboard-redesign.md`
  All ~32 tasks across 6 phases + Phase 5b. Each task has full code,
  exact file paths, and TDD steps. Do not deviate.

- **Branch state:** Phase 0 (test infra) is already complete on the
  `claude/magical-visvesvaraya-2204b2` branch (commits `75d0252` and
  `828d6b9`). If you don't see those commits, fetch the branch from origin.

- **Mock state in the codebase that MUST go away:**
  - `frontend/src/pages/company/dashboard.tsx` — currently a self-contained
    mockup with hard-coded `MOCK_STUDENTS`, `MOCK_INTERNSHIPS`,
    `MOCK_ATTENDANCE`, `MOCK_WORKLOGS`, `MOCK_ANNOUNCEMENTS`, `MOCK_MANAGERS`
    arrays. Replace per Phase 3 of the plan with real React Query hooks.
  - `frontend/src/utils/mockInternshipRequests.ts` — delete entirely once
    Task 5b.1 endpoints are live.
  - `frontend/src/pages/admin/internship-requests.tsx` — currently reads
    from `mockInternshipRequests`. Rewrite to call the real
    `/api/v1/admin/internship-requests*` endpoints from Task 5b.2.
  - The `sessionStorage.getItem('mock_view_as_company')` shim in
    `frontend/src/pages/company/dashboard.tsx` and the
    `CompanyDashboardGuard` in `frontend/src/App.tsx` — replace with real
    impersonation per Task 5b.3 (mints a JWT, banner reads
    `user._impersonated_by` from token).
  - The hard-coded mock SPOC list in
    `frontend/src/pages/admin/internship-requests.tsx` (`MOCK_SPOCS`) —
    replace with a fetch of `GET /api/v1/users?role=instructor` (and
    `=admin`) when implementing Task 5b.2.

- **Production data is live.** There are real companies, real internships,
  real students, real vouchers, real attendance rows. Do NOT delete or
  reset anything. The schema migration is purely additive (only
  `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS`),
  so it's safe — but verify the migration file before applying.

## Pre-flight (mandatory — do these before touching code)

1. **Confirm you're on the right host.** Run `hostname` and `pwd`. The
   path should match the VPS production checkout, not a dev machine.
2. **Verify the stack is the production one.**
   `docker compose ps` (or `docker-compose ps` depending on version) —
   you should see `sasha_lms-*` or whatever the production project name
   is. If you see `magical-visvesvaraya-2204b2-*`, you're in a worktree —
   move out before doing real work.
3. **Postgres backup.** `pg_dump` the live DB to a timestamped file under
   `database/backups/`. Confirm the dump finished (file size > a few MB).
   If anything goes wrong later, you restore from this.
4. **Snapshot the current frontend bundle.** `cp -r frontend/dist
   frontend/dist.before-company-v2-$(date +%F)` (so you can roll back the
   static bundle without rebuilding).
5. **Check disk space.** `df -h`. Need at least 2 GB free for the rebuild.
6. **Confirm `.env` has all required values** (per CLAUDE.md):
   `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`, `JWT_SECRET`,
   `RAZORPAY_KEY`, `RAZORPAY_SECRET`, `ADMIN_PASSWORD`. If `SECRET_KEY` /
   `JWT_SECRET` are placeholders, FIX THEM NOW (otherwise tokens
   invalidate on restart).

If any of those checks fail, STOP and report back with the specific
failure. Don't try to "make it work" — pause and surface the issue.

## Branching

Create a fresh feature branch from `main`:

```
git fetch origin
git checkout main
git pull origin main
git checkout -b feat/company-dashboard-v2
```

Cherry-pick the test-infra commits from `claude/magical-visvesvaraya-2204b2`
if they aren't on main yet:

```
git log --oneline main..origin/claude/magical-visvesvaraya-2204b2 -- backend/tests backend/pytest.ini
git cherry-pick 75d0252 828d6b9   # exact SHAs may differ; pick the test-infra commits
```

Also bring in the spec + plan + VPS prompt files from that branch:

```
git checkout origin/claude/magical-visvesvaraya-2204b2 -- \
  docs/superpowers/specs/2026-05-05-company-dashboard-redesign-design.md \
  docs/superpowers/plans/2026-05-05-company-dashboard-redesign.md \
  docs/superpowers/VPS-EXECUTION-PROMPT.md
git commit -m "docs: import company dashboard v2 spec + plan + VPS prompt"
```

Do NOT bring over `frontend/src/pages/company/dashboard.tsx` or
`frontend/src/utils/mockInternshipRequests.ts` from that branch — those are
mockup files; you build the real versions from scratch per the plan.

## Execution

Follow `docs/superpowers/plans/2026-05-05-company-dashboard-redesign.md`
**task by task, in order**. Each task is self-contained with file paths,
TDD test code, and implementation code. Do not skip ahead.

Use the `superpowers:subagent-driven-development` skill: dispatch a
fresh general-purpose subagent per task with the full task text +
context, then review with the spec-reviewer + code-quality-reviewer
subagents per task. **Do not batch tasks** — one task, one
implementer, one spec review, one code-quality review.

Order:

1. Phase 1 (Tasks 1.1 – 1.5) — DB migration + models + manager API.
   **CRITICAL**: when you apply the SQL migration in step 1.1, run it
   inside a transaction against the live DB. The migration is
   idempotent (`IF NOT EXISTS`) so re-running is safe.
2. Phase 2 (Tasks 2.1 – 2.8) — backend tab APIs.
3. Phase 3 (Tasks 3.1 – 3.10) — frontend rewrite. **Critical:**
   - Task 3.1 deletes the existing mockup `frontend/src/pages/company/dashboard.tsx`.
   - Replace it with the layout + real-API-backed pages from the plan.
   - Also delete `frontend/src/utils/mockInternshipRequests.ts`.
   - Replace `frontend/src/pages/admin/internship-requests.tsx` with the
     real version from Task 5b.2 (don't keep the localStorage one).
4. Phase 4 (Tasks 4.1 – 4.4) — reports.
5. Phase 5 (Tasks 5.1 – 5.2) — student-side wiring.
6. Phase 5b (Tasks 5b.1 – 5b.3) — internship requests + view-as-company.
   - 5b.1 backend (request schema + endpoints).
   - 5b.2 admin UI (replace the mock-backed page).
   - 5b.3 view-as-company impersonation backend + UI.
7. Phase 6 (Task 6.1) — end-to-end smoke.

Per the plan, ~32 tasks total. Realistic timeline: this will take
several hours of focused execution. Don't rush.

## Deploy-readiness checks (after Phase 6 smoke passes)

These are NOT in the plan — they are production-specific. Do them after
the plan tasks finish and the smoke test passes.

1. **Production secrets audit.** Open `.env` and verify:
   - `SECRET_KEY` and `JWT_SECRET` are NOT the placeholders that
     `app/core/config.py` calls out — they must be real, long, random
     strings unique to this VPS.
   - `ADMIN_PASSWORD` is not the dev default `DevAdmin@2024!`.
   - `RAZORPAY_KEY` / `RAZORPAY_SECRET` are the live (not test-mode)
     keys if this VPS handles real payments.
   - `ENVIRONMENT=production` and `DEBUG=false`.
   - `ALLOWED_HOSTS` includes the public domain (e.g.
     `lms.sashainfinity.com`) and NOT `localhost`.

2. **Compose file verification.** This task ships changes to backend
   models / routers, frontend pages, and the DB schema. Production
   uses `docker-compose.production.yml`. Diff
   `docker-compose.yml` vs `docker-compose.production.yml` and confirm:
   - Both reference the same backend image build context.
   - Production has TLS / nginx config that the dev one doesn't (don't
     break it).
   - The new schema migration runs as part of either backend startup
     OR a one-shot `docker compose -f docker-compose.production.yml run
     --rm backend python -m scripts.apply_migrations`. Pick whichever
     pattern your team already uses.

3. **Frontend production build flags.** Make sure the frontend container
   builds with production env vars (`VITE_API_URL`, `VITE_FRONTEND_URL`,
   `VITE_BACKEND_URL`, `VITE_FIREBASE_*`) — verify from
   `docker-compose.production.yml` env block.

4. **Migration apply order.**
   - Apply schema migration FIRST (zero-downtime: only ADDs, no
     drops/renames).
   - Then deploy backend image (it knows the new tables).
   - Then deploy frontend image.
   - Order matters: if frontend goes out before backend, the new tabs
     hit 404s.

5. **Run smoke against the real domain.**
   - Log in as admin → /admin/internship-requests → see the queue.
   - Log in as a real company → /company/dashboard → all 7 tabs load.
   - Click "View as company" from /admin/companies → land on
     /company/dashboard with banner.
   - Mark attendance → confirm the row appears in `internship_attendance`.
   - Generate an attendance PDF → confirm PDF opens.
   - Submit an internship request → confirm it appears in
     /admin/internship-requests.
   - Approve a request → confirm an `internships` row is created.

6. **Backups.** Add a cron entry for nightly `pg_dump` of the new
   tables. The schema migration adds 5 new tables; make sure they're
   in the backup script's table list (or use `pg_dump` without
   `--table` so all tables are dumped — preferred).

7. **Post-deploy rollback plan.** Document in
   `docs/superpowers/RUNBOOK-company-dashboard-v2.md`:
   - How to roll back the frontend bundle (the snapshot from pre-flight).
   - How to roll back the backend image (`docker compose down && docker
     image tag <previous-tag> sasha_lms-backend:latest && docker compose
     up -d`).
   - How to revert the schema migration (write down-migration SQL —
     dropping the 5 new tables + 2 new columns; only run if data is
     not yet populated in those tables, otherwise restore from backup).

## Reporting back

When done (or if you hit a blocker), report back with:

- **Status:** SHIPPED | PARTIAL | BLOCKED
- **Tasks completed** (list by number from the plan)
- **DB schema migration applied?** Yes / No / Errors
- **Tests:** count passed / failed
- **Smoke test results:** each of the 7 manual checks above
- **Production stack health:**
  `docker compose -f docker-compose.production.yml ps` output
- **What did NOT ship and why** (if anything)
- **Rollback runbook location** (`docs/superpowers/RUNBOOK-...`)

## Hard rules

- DO NOT delete production data.
- DO NOT skip the Postgres backup in pre-flight.
- DO NOT skip reviews. Each task gets a spec-reviewer + code-quality-reviewer.
- DO NOT push to main directly. Open a PR from `feat/company-dashboard-v2`.
- DO NOT leave any `MOCK_` prefixed exports / `localStorage` reads /
  `sessionStorage.getItem('mock_view_as_company')` shims behind. The
  whole point of this work is to remove them.
- DO NOT change `.env` values without explicit confirmation from a human.
- If you uncover a spec ambiguity, STOP and ask a human — don't guess.

Begin with the pre-flight checks. Once those pass, follow the plan.

=== END VPS EXECUTION PROMPT ===
```

---

## Notes for the human (you)

- **Where the spec and plan live now:** they're committed in this
  worktree under `docs/superpowers/specs/` and `docs/superpowers/plans/`.
  Push the worktree branch to your origin so the VPS can fetch them:
  `git push origin claude/magical-visvesvaraya-2204b2`
- **What changes hit prod once Claude finishes:**
  - 1 SQL migration file (idempotent, additive — no destructive ops)
  - ~5 new backend Python files (models, routers, services)
  - ~10 modified backend files (routers, schemas)
  - 1 added Python dep: `reportlab`
  - ~15 new frontend files (typed API client, layout, 7 tab pages,
    admin internship-request page, report components)
  - ~5 modified frontend files (`App.tsx` routes, header role-routing,
    admin layout nav)
  - Old `frontend/src/pages/company/dashboard.tsx` mockup REPLACED
  - Old `frontend/src/utils/mockInternshipRequests.ts` DELETED
- **Rollback if something goes wrong:** Postgres restore from the
  pre-flight backup + git revert the merge commit + re-deploy the
  previous image. The runbook the prompt asks Claude to write spells
  this out concretely.
- **Cost:** the subagent-driven approach dispatches a fresh subagent
  per task (3 per task — implementer + spec reviewer + code reviewer).
  ~32 tasks × 3 = ~100 subagent invocations. Plan accordingly.
