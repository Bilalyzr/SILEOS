# Learning planner build report — 2026-09-06

Completed locally: personal course goals, daily study planning, evidence-based checks, delayed retention follow-up, and instructor interventions. This implements the learning-planner/intervention enhancement requested after Astra cycle 1. It does not claim the entire long-term learning-OS roadmap or original Astra cycles 2–6 are finished.

## Delivered

- Learner **My Learning Plan**: enrolled-course goals, date/time budgets, local time zones, pause/resume, explicit deadline warnings, daily/upcoming/completed tasks, snoozing, lesson links and study tracking.
- Explainable diagnosis from stored course assessment and behavioural evidence; known weak prerequisites can prompt review. Reviews cover duplicate curriculum study time once.
- Persisted focused practice sessions with server-side grading, retry/idempotency controls, minimum-evidence rules and delayed checks. Behaviour and study clicks cannot independently award mastery. Insufficient practice coverage requests instructor support.
- Instructor **Interventions**: course ownership/collaboration controls, priority queue, filters, evidence comparison, learner-visible notes, request-check and close actions, retained decision/reopening history.
- Automatic refresh after canonical quiz submit/finalize and in the six-hour retention loop. Models, Alembic 0021 and PostgreSQL schema SQL included.
- Single-answer adaptive grading hardened against passing by supplying all options.

Full rules, API, deployment instructions and limitations: [LEARNING_PLANNER.md](LEARNING_PLANNER.md).

## Verification

| Check | Result |
| --- | --- |
| Full backend suite | 1,569 passed, 4 skipped, 680.94 seconds |
| Final focused planner/signals/retention suite | 39 passed, 20.14 seconds |
| Existing frontend regression suite | 329 passed across 48 files |
| Existing live smoke script | 27/27 passed on workspace backend 8012 |
| Frontend production build | Passed, 11.00 seconds; existing chunk-size warnings |
| Scoped planner frontend ESLint | Passed, zero warnings |
| New backend modules/migration/tests pyflakes | Passed, no findings |
| Repository ESLint | 0 errors, 26 existing hook warnings; strict zero-warning gate remains failing |
| Repository TypeScript | 393 existing errors; none in planner API/pages/navigation |
| SQLite migration | Upgrade/repeat/rollback/re-upgrade and model-column parity tested; local database now at 0021 |
| PostgreSQL | Schema DDL compiled; no live server migration or concurrent load validation |

The full backend run began before final quiz-refresh/feedback refinements and duplicate-study/queue fixes. The 39-test focused suite passed against the final code, covering those planner behaviours plus existing signal/retention regressions. Frontend tests are the existing regression suite; the new pages were additionally verified in the browser. An initial live smoke run had three request timeouts while other verification was active; the final repeat passed all 27 with unchanged timeout settings.

## Browser verification

Local demo learner Arjun created a 30-minute course goal. Replanning removed the duplicate curriculum/review block. The UI displayed a 100% HTTP practice result with follow-up scheduled for September 9. Missing HTML question coverage produced an actionable error and an instructor-support queue item. Instructor Priya saved a demo closure note; the active queue updated, and a learner reload showed the closed status and note. The learner and instructor pages were visually inspected. Timed retention resolution, repeated submission, paused/revoked access, instructor isolation/collaboration and failed-check retries were validated in isolated database tests.

## Local preview and data

- Learner: http://localhost:3002/my-plan
- Instructor: http://127.0.0.1:3002/instructor/interventions
- Backend: http://127.0.0.1:8012

Different local browser origins preserve separate learner/instructor demo sessions. Existing previews on 3001/8011 were left running. Only local demo planner data was changed during the walkthrough.

Before upgrading, the SQLite database was backed up to `backend/planner_before_0021.sqlite`. Its redundant ancestor version marker 0005 was removed after verifying 0006c already included it; guarded migrations then advanced to 0021. No application data was deleted. Details and precautions for other environments are in the feature guide.

## Review and remaining work

Base: PR #3, head `25db528fa3f91b5f63173aeef3c2e87f1e94633d`. Local branch `astra/learning-signals`. Original line endings are preserved in existing frontend integration files so their changes remain small. Cycle 1 edits remain present. The archive's pre-existing missing WordPress/certificate files are unrelated and must not be staged as deletions.

No Git commit, push or production deployment was performed. Production requires its normal database backup/migration/release checks, including validation against PostgreSQL. The existing repository TypeScript and lint debt remains. This release has no Flutter planner UI, generated question bank, external notification delivery or cross-course budget optimization. Provider-dependent transcription and AI integrations remain separate work.

Local logs: `backend/planner-{full-tests,tests,smoke,pyflakes}.log` and `frontend/planner-{build,lint,full-lint,types,vitest}.log`. Architecture and assumptions recorded in CLAUDE.md, OWNER_DECISIONS.md (33), and architecture ledger section J.
