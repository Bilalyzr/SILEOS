# SILEOS Feature Pack — integrated into Sasha LMS (2026-09-04)

Selected capabilities from `SILEOS_Master_Blueprint.md`, integrated
**backend-only** into the existing Sasha LMS. No existing UI was changed;
every feature is API-first so UI can be wired later without schema changes.

Source mapping: each endpoint below cites the blueprint section it
implements. Design/quality rules follow `docs/superpowers/specs/` house
style: real code, no silent stubs, audit trails, idempotent writes.

---

## 1. Question Banks + Item Analysis (blueprint §3.4)

Router: `backend/app/routers/question_banks.py` → prefix `/api/v1/question-banks`

| Endpoint | Purpose |
|---|---|
| `POST /question-banks` | Create a bank (instructor; 201) |
| `GET /question-banks` | Own banks with question counts |
| `GET /question-banks/{id}` | Bank detail with questions |
| `DELETE /question-banks/{id}` | 409 while the bank still has questions (content is never silently destroyed) |
| `POST /question-banks/{id}/questions` | Add a question — server-side validation (type whitelist `multiple_choice/true_false/fill_in_blanks/short_answer`, in-range correct index, ≥2 non-empty options, difficulty enum) |
| `POST /question-banks/{id}/import-from-quiz/{quiz_id}` | **Snapshot-copy** a live quiz's questions into the bank; the live quiz keeps working untouched. Provenance kept in `source_quiz_question_id` |
| `GET /question-banks/{id}/analysis` | Per-question **item analysis**: attempts, facility (p-value = share correct), **discrimination** (top-27% minus bottom-27% correct rate over attempt totals), and a flag: `too_easy` (>0.95) / `too_hard` (<0.25) / `weak_discrimination` (<0.10) / `ok` / `no_data` |

Data: `question_banks`, `bank_questions` (options/answer JSON per type, tags,
difficulty). Ownership: instructor owns banks; admins see all; students have
no bank surface (answers leak).

## 2. Prerequisites, Unlock-Status, Learning Paths (blueprint §3.2)

Router: `backend/app/routers/sileos.py`

| Endpoint | Purpose |
|---|---|
| `PUT /courses/{id}/prerequisites` | Replace the prerequisite set `{items:[{requires_course_id, min_progress_percentage}]}`. Rejects self-reference, duplicates, unknown courses, out-of-range percentages. Owner/admin only |
| `GET /courses/{id}/prerequisites` | The rule set |
| `GET /courses/{id}/unlock-status` | For the CURRENT student: per-rule `{enrolled, progress_percentage, met}` + `unlocked` + `unmet_count` — numbers so a UI can *explain* a lock, never just block |
| `POST /learning-paths` · `GET /learning-paths` | Ordered course sequences owned by the author |
| `GET /learning-paths/{id}/progress` | The current student's step-by-step progress along a path |

**Rollout note:** prerequisites are *exposed* but not yet *enforced* on
enrollment/mark-complete. Enforcement should flip once the UI renders
unlock states (one guard call to `unlock-status`), so we don't lock
existing students out of live courses before the UI can explain it.

## 3. xAPI Event Spine (blueprint §3.5, xAPI-lite)

- Emitter service: `backend/app/services/xapi_service.py` —
  `emit_statement(...)` is **best-effort, post-commit** (same doctrine as
  the gamification `award()` hook: analytics must never break the learner
  action). Failures log, never raise.
- **Wired into existing flows** (the only touches to existing code):
  - `POST /progress/watch-event` (progress.py) → emits `watched/paused/resumed/completed`
  - `mark_lesson_complete` (courses.py) → emits `completed` with the new progress %
- Ingest API:
  - `POST /xapi/statements` — actor is ALWAYS the authenticated user (no forging)
  - `GET /xapi/me/statements` — own stream
  - `GET /xapi/statements` — admin firehose (limit ≤ 500)
- Verb whitelist mirrors the ADL registry short forms; object whitelist:
  `lesson|course|quiz|h5p|game|ebook|live_class`.
- Storage: `xapi_statements` (Postgres/SQLite) with `(actor, stored_at)`
  index. The blueprint's ClickHouse mirror is deliberately deferred.

## 4. Mastery (blueprint §15 mastery learning graph, lite)

`GET /analytics/students/{user_id}/mastery` — per enrolled course:
`completion_percentage`, distinct quizzes attempted, pass rate (≥80%),
**mastery = 0.6·completion + 0.4·quiz-pass-rate** (a course with no quizzes
is mastery = completion), level ∈ `novice <40 | developing <70 |
proficient <90 | mastered`. Students see only their own; instructors/admins
see all.

## 5. At-Risk Analytics — explainable by construction (blueprint §3.6/§15)

`GET /analytics/courses/{id}/at-risk?persist=true` (course owner/admin)

Three transparent rules, each threshold echoed in the response:

| Rule | Trigger | Points |
|---|---|---|
| Stalled / never started | No xAPI activity for ≥7 days (or enrolled ≥7 days with zero activity), not completed | +45 |
| Low velocity | <5%/week at <100% complete | +25 |
| Quiz struggle | ≥2 failing attempts (<80%) on the same quiz | +30 |

Severity: `high ≥60`, `medium ≥30`, else `low`. Every flag carries its
human-readable reasons ("stalled: no recorded activity for 12 days
(threshold 7)"). Results are **persisted idempotently** to
`student_risk_flags` (UNIQUE course+student) so dashboards can sort/filter
and history stays auditable. This is rule-based, not a black box — by
design (blueprint: "explainability").

## 6. AI Question Generation (blueprint §3.6 + §15 guardrails)

Router: `backend/app/routers/ai.py`

| Endpoint | Purpose |
|---|---|
| `POST /ai/generate-questions` | `{topic, count ≤20, bank_id?, difficulty_mix?, question_types?}` → calls the **real Anthropic Messages API** (`ANTHROPIC_API_KEY`, optional `ANTHROPIC_MODEL`, default `claude-sonnet-4-5-20250929`) |
| `GET /ai/jobs/{id}` | The audit trail: model, input, output, error |

Guardrails implemented:
- **503 with setup guidance when `ANTHROPIC_API_KEY` is absent** — never a
  silent fake.
- Every call is logged as an `AiJob` (pending → done/failed with error).
- Model output is *validated with the same server rules as manual
  questions*; invalid items are **reported, not stored**.
- Accepted drafts land in the bank (auto-created "AI Generated — {topic}"
  when no `bank_id`) tagged **`ai-draft`** — they are never auto-published
  to a live quiz (blueprint §15: no AI output ships without human approval).

## 7. Schema & migration

Models: `backend/app/models/sileos_pack.py` (registered in
`models/__init__.py`) — `question_banks`, `bank_questions`,
`course_prerequisites`, `learning_paths`, `xapi_statements`,
`ai_jobs`, `student_risk_flags`.

Dev DBs: created automatically by `init_db()` → `create_all` on boot.
Live DB parity (no restart): `psql $DATABASE_URL -f backend/migrations/sileos_pack_2026_09_04.sql` (idempotent).

### Alembic graph fix (bonus, same day)

The repo had TWO parallel alembic branches (`0005` digital-library +
`0005m` money-ops) that were never merge-revised, so every
`alembic upgrade head` (and several migration test fixtures) failed with
`MultipleHeads`. Added `alembic/versions/0006_merge_digital_library_and_money_ops.py`
(revision `0006m`, down-revision `("0005","0005m")`) and re-chained the
course-types revision `0006c` on top of it — the graph now has a single
head. `0006c` also skips its UPDATEs when `courses` does not exist (the
chain is partial; create_all builds the full schema on fresh DBs).

## 8. Tests

`backend/tests/test_sileos_pack.py` — 11 tests, all green:
bank CRUD + validation + guarded delete; import-from-quiz snapshot
integrity (live quiz untouched); item analysis math (facility 0.5,
discrimination 1.0 on a constructed cohort); prerequisites incl. self-reference
422 and unlock transitions (20% locked → 60% unlocked); learning-path
progress; xAPI ingest + verb whitelist + privacy + admin firehose (with
TOTP admin login); watch-event → statement emitter hook; mastery
weighting (0.6·50 + 0.4·100 = 70.0 → "proficient") + privacy 403;
at-risk rule + explainability + idempotent persistence; AI 503 without
key; AI happy path with the provider monkeypatched (job audit, validation
rejection reporting, `ai-draft` tagging all real).

## 9. What was NOT built (deliberate, with reasons)

- **GeoGebra / HIP particles / 3D viewer** — UI-facing; blocked on the
  GeoGebra commercial licence and the 3D-lessons design doc. Next in line
  after instructor UI for this pack.
- **ClickHouse mirror, GraphQL, SAML/SCIM/passkeys** — SILEOS-scale
  plumbing that Postgres/existing auth already covers at this traffic level.
- **Enforcement of prerequisites on enroll/mark-complete** — flip after UI
  shows unlock states (see §2 Rollout note).
