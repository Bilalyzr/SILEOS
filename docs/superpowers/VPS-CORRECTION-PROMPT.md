# VPS Correction Prompt — Audit Findings on `feat/company-dashboard-v2`

> Audit was performed locally by comparing `feat/company-dashboard-v2` (your
> branch on origin) against `claude/magical-visvesvaraya-2204b2` (the spec +
> plan + mockup baseline). Paste the block between the markers below into
> the VPS Claude session that has the `feat/company-dashboard-v2` checkout.

## Audit summary (FYI — don't paste this part)

✅ **What was done well**
- All 5 new SQLAlchemy models + 2 migration files + 23 backend endpoints + 10 frontend tab pages + real React Query API client + ImpersonationBanner extended for company + ManagerSetup accept page + view-as-company impersonation backend endpoint + reportlab dependency for PDFs.
- Old mockup `frontend/src/pages/company/dashboard.tsx` correctly deleted.
- `mockInternshipRequests.ts` no longer imported anywhere.

🚨 **Critical issues found**
1. `frontend/dist.before-company-v2-2026-05-05/` was **committed** to git — that was supposed to be a local rollback snapshot, NOT a tracked file. Bloats the repo by ~4 MB of build artifacts.
2. **No tests written for ANY of the 32 plan tasks.** `backend/tests/` only contains Phase 0 smoke (9 lines). The plan explicitly required TDD per task.

⚠️ **Important issues**
3. `frontend/src/utils/mockInternshipRequests.ts` is dead code (no imports) but not deleted. Plan said: delete.
4. `frontend/src/pages/company/Internships.tsx:416` has `// TODO: Implement delete API call` — feature incomplete.

ℹ️ **Minor (verify, may be fine)**
5. Performance review endpoint is `POST /me/reviews` instead of `POST /me/students/{user_id}/review` — REST style differs from spec but functionally OK if the body has `student_user_id`.
6. Schema fields use `start_date` / `end_date` (better — matches existing DB convention; my plan/spec said `start`/`end`).

---

```
=== BEGIN VPS CORRECTION PROMPT ===

You are Claude Code working on the SashaInfinity LMS production VPS. You
previously executed the company-dashboard v2 plan and pushed the
`feat/company-dashboard-v2` branch (last commit `54fd2e3`). A code review
against the spec + plan found several issues. Fix them in this order.

## Context — read these first

- Spec: `docs/superpowers/specs/2026-05-05-company-dashboard-redesign-design.md`
- Plan: `docs/superpowers/plans/2026-05-05-company-dashboard-redesign.md`
- VPS execution prompt (the original instructions you followed):
  `docs/superpowers/VPS-EXECUTION-PROMPT.md`

You're on branch `feat/company-dashboard-v2`. Don't switch branches; commit
fixes here and push.

## Pre-flight (mandatory)

1. `git status` — confirm clean tree.
2. `git log --oneline -5` — last commit should be `54fd2e3`. If you've
   added more commits since then, stop and report what they were.
3. Make sure the live stack is still healthy: `docker compose ps`. If
   anything is down, fix that BEFORE these audit fixes.

## Issue 1 (CRITICAL) — Remove `dist.before-company-v2-2026-05-05/` from git

This folder was supposed to be a local rollback snapshot, not committed to
git. It's ~4 MB of build artifacts polluting the repo.

Steps:

1. **Verify the live frontend bundle is fine first.** This snapshot was
   meant as your rollback; if you delete it from git AND production is
   somehow broken, you lose the rollback path.
   - Confirm `https://sashainfinity.com/` loads.
   - Confirm `/company/dashboard` works for the demo company login.
   - Confirm `/admin/internship-requests` loads as admin.
   - If any of those fail, STOP — keep the snapshot, escalate.

2. Take a fresh local snapshot OUTSIDE git, in case you need to roll back:
   ```
   cp -r frontend/dist.before-company-v2-2026-05-05 \
         /tmp/dist.before-company-v2-2026-05-05
   ```
   And add the path to `.gitignore` so it doesn't accidentally come back:
   ```
   echo 'frontend/dist.before-*' >> .gitignore
   echo 'frontend/dist.snapshot*' >> .gitignore
   ```

3. Remove from git tracking (but keep the local copy you just made in
   /tmp):
   ```
   git rm -r --cached frontend/dist.before-company-v2-2026-05-05
   rm -rf frontend/dist.before-company-v2-2026-05-05
   git add .gitignore
   git commit -m "chore: untrack dist.before-* build snapshots — they're
   local-only rollback copies, not source. Snapshot moved to
   /tmp/dist.before-company-v2-2026-05-05."
   ```

4. **Do NOT rewrite history with `git filter-branch` / `git filter-repo`.**
   The commit that added it (`54fd2e3`) stays in history; we just remove
   the files going forward. Repo bloat is acceptable; the alternative
   (force-pushing rewritten history) breaks anyone else's checkouts.

## Issue 2 (CRITICAL) — Write the missing tests

The plan said TDD per task. `backend/tests/` only has the Phase 0 smoke
test. You need to add tests for the new endpoints. Don't rewrite history;
just add the tests now.

Required test files (one per plan task that has endpoints):

| File to create | Tests for |
|---|---|
| `backend/tests/test_models_existing_extensions.py` | Task 1.2 — `hours_worked` + `reporting_manager_user_id` columns |
| `backend/tests/test_models_company_dashboard.py` | Task 1.3 — 4 new model tables, unique constraints |
| `backend/tests/test_auth_company_deps.py` | Task 1.4 — `require_company_or_manager` accepts both roles |
| `backend/tests/test_managers.py` | Task 1.5 — invite / list / revoke / complete-setup |
| `backend/tests/test_company_scope.py` | Task 2.1 — `assigned_voucher_query` filters by company + manager |
| `backend/tests/test_overview.py` | Task 2.2 — basic counts + activity feed shape |
| `backend/tests/test_students.py` | Task 2.3 — list / detail / patch (+ scope enforcement) |
| `backend/tests/test_company_internships.py` | Task 2.4 — only internships with our students |
| `backend/tests/test_attendance_company.py` | Task 2.5 — grid + upsert + scope enforcement (404 on stranger student) |
| `backend/tests/test_work_logs.py` | Task 2.6 — list + review |
| `backend/tests/test_announcements.py` | Task 2.7 — owner-only post; manager 403 on post |
| `backend/tests/test_perf_review.py` | Task 2.8 — submit once + 409 on duplicate |
| `backend/tests/test_company_report.py` | Task 4.2 — JSON / CSV / PDF responses |
| `backend/tests/test_admin_report.py` | Task 4.3 — admin can filter by company |
| `backend/tests/test_student_workspace.py` | Task 5.1 — student creates + lists own logs; 403 on others |
| `backend/tests/test_internship_requests.py` | Task 5b.1 — submit, withdraw, admin approve creates internship row, admin reject sets reason |
| `backend/tests/test_impersonate_company.py` | Task 5b.3 — admin mints token, token grants access to /companies/me/* as the owner, non-admin gets 403 |

The plan has the **exact test code** for most of these (under each task's
"Step 1: Failing test" block). Copy from the plan, don't reinvent.

After each test file:
1. Run `docker compose exec backend pytest backend/tests/test_<name>.py -v`.
2. If any fails, fix the implementation OR fix the test (whichever is wrong
   per the plan/spec). Don't skip failing tests.
3. Commit each test file separately with `test:` prefix:
   `git commit -m "test(<area>): cover <task name> per plan"`

When all 17 test files pass: `pytest backend/tests/ -q` should report
something like `~70-90 passed`. Push everything.

## Issue 3 — Delete the dead mock store

`frontend/src/utils/mockInternshipRequests.ts` is no longer imported
anywhere (verify with `grep -rn "mockInternshipRequests" frontend/src`)
but the file still exists. Delete it:

```
git rm frontend/src/utils/mockInternshipRequests.ts
git commit -m "chore: delete unused mock store — replaced by real API in commit 120309f"
```

## Issue 4 — Wire up the missing delete-internship-request

Open `frontend/src/pages/company/Internships.tsx` and find the line
`// TODO: Implement delete API call` (around line 416).

The withdraw endpoint already exists on the backend
(`DELETE /api/v1/companies/me/internship-requests/{id}`). Wire it:

1. The hook `useDeleteInternshipRequest` (or similar) should already
   exist in `frontend/src/api/company-dashboard.ts` — if not, add it
   following the pattern of the other DELETE hooks (e.g. `useRevokeManager`).

2. Replace the TODO with a call to the hook + toast on success +
   `queryClient.invalidateQueries(['company', 'internship-requests'])`.

3. Test it by submitting a request, then withdrawing it; the row should
   disappear from `My requests` immediately.

4. Commit:
   `git commit -m "feat(internships): wire withdraw-request to DELETE /me/internship-requests/{id}"`

## Issue 5 — REST style of performance review endpoint

The spec said: `POST /api/v1/companies/me/students/{user_id}/review` (the
review is scoped to a student in the URL). You implemented:
`POST /api/v1/companies/me/reviews` with `student_user_id` in the body.

This is a stylistic difference. **If the frontend currently uses the
`/me/reviews` shape and tests pass, leave it alone.** If you're going to
change anything, do it on the backend AND the frontend AND the tests in
the same commit — don't break running production.

Decision: **leave as-is** unless you encounter an actual bug. Just
document the deviation:

```
echo "
## Spec deviation log

- Performance review endpoint: implemented as
  \`POST /api/v1/companies/me/reviews\` with \`student_user_id\` in the
  body (not \`POST /me/students/{user_id}/review\` per spec). Functionally
  equivalent; chosen for simpler param parsing.
" >> docs/superpowers/specs/2026-05-05-company-dashboard-redesign-design.md
git add docs/superpowers/specs/
git commit -m "docs(spec): note REST-style deviation on perf review endpoint"
```

## Final verification

After all fixes:

```
# Backend tests
docker compose exec backend pytest backend/tests/ -q

# Type-check frontend
docker compose exec frontend npm run type-check

# Confirm migration files apply cleanly to a fresh DB (sandbox, NOT prod)
# This proves the migrations are idempotent.

# Smoke through nginx as you did originally:
# - admin login → /admin/internship-requests → see queue
# - company login → /company/dashboard → all tabs load
# - admin → /admin/companies → "View as company" → banner appears
# - submit a request → admin approves → company sees green callout
# - withdraw a pending request → row disappears
```

## Push

After every fix has its own commit and the smoke tests pass:

```
git push origin feat/company-dashboard-v2
```

Open / update the PR if one exists. If not, mention to the user
(devesh-666) that they can review and merge when ready.

## Report back

Reply with:

- **Status:** ALL_FIXED | PARTIAL | BLOCKED
- For each of the 5 issues: ✅ done / ❌ skipped (with reason)
- Backend test pass count
- Frontend type-check status
- Any new issues you discovered during this audit-fix run
- Final commit SHA on `feat/company-dashboard-v2`

## Hard rules

- Don't rewrite git history (no `git rebase -i` / `git filter-branch` / `git
  push --force` on a shared branch).
- Don't touch production data outside of running the smoke tests.
- Don't skip tests by adding `@pytest.mark.skip` — if a test is hard, ask.
- Don't add new features. This is a correction pass only.

Begin with Issue 1 (the dist snapshot removal) since it has a real safety
sequence. Then 2, 3, 4 (5 is a doc-only update).

=== END VPS CORRECTION PROMPT ===
```

---

## Notes for you (the human)

- The most important fix is **Issue 2 (tests)** — without tests, you have no safety net for future changes. Plan task estimates assumed TDD; skipping it is a real debt.
- **Issue 1 (dist snapshot in git)** is a one-time cleanup. The 4 MB bloat is annoying but not breaking.
- The VPS Claude got the **functional** parts right — endpoints, models, frontend wiring, real-API-backed pages. The mockup → real-API transition appears complete.
- After the corrective prompt finishes, your `feat/company-dashboard-v2` branch should be ready to PR into `main`.
