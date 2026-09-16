# Campus exams and fee reminders — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add scheduled exams with hall tickets, marks, published results and mark sheets, then automatic tuition fee reminders and receipt notices over WhatsApp and email, to Campus OS.

**Architecture:** Two new backend feature groups following the existing campus pattern (SQLAlchemy model → Alembic migration → Pydantic schema → service → router registered under `/api/v1/institutions` → pytest on SQLite), each with one React component mounted in the institution page and a Vitest test. Exams link into the existing timetable (`campus_events`) and report card; reminders link into the existing tuition ledger, WhatsApp campaign pipeline, SMTP mail pattern and the campus worker tick.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, ReportLab, pytest (SQLite), React 18 + TanStack Query + Vitest, axios client in `frontend/src/api`.

## Global Constraints

- Backend python: `backend/.venv/Scripts/python.exe` (Python 3.13; pins relaxed for Pillow, pandas, pydantic, asyncpg, aiohttp, psycopg2-binary). Tests: `cd backend && .venv/Scripts/python.exe -m pytest tests/<file> -q`.
- Frontend: `cd frontend && npm run test -- --run <pattern>`, `npm run lint`, `npx tsc --noEmit`, `npm run build`.
- Repo is not a git repository. "Commit" steps are replaced by a checkpoint note in this file; no git commands.
- New API prefixes must be added to `frontend/src/api/axios.ts::noSlashEndpoints` if they are new top-level prefixes (they are not: everything lives under the existing `/institutions` prefix).
- Role constants: `institution_service.MANAGERS = ("owner","admin")`, `STAFF = ("owner","admin","teacher")`. Use `institution_service.scope(db, institution_id, user, roles=...)` which returns `(institution, member)` and raises 404 outside membership; `institution_service.audit(db, institution_id, user, action, detail)` for audit rows.
- Parent access follows `tuition_service.self_accounts`: role `parent` must pass `student_user_id` and have an approved `parent_link_requests` row.
- Money type is `tuition.MONEY`; amounts through `tuition_service.money()`.
- Never claim delivery that did not happen: unconfigured providers produce `skipped`/`failed` rows with a reason.
- Keep the glass UI: reuse `campus-panel`, `campus-table`, `campus-muted`, `CampusOsPrimitives` components.

---

## Module 1 — Exams

### Task 1: Models and migration 0038

**Files:**
- Create: `backend/app/models/campus_exams.py`
- Modify: `backend/app/models/__init__.py` (import the four models)
- Create: `backend/alembic/versions/0038_campus_exams.py` (revises `0037`)
- Test: `backend/tests/test_campus_exams.py::test_migration_0038_round_trip`

**Produces:** `CampusExam(id, institution_id, term_id, name, kind, status, published_at, created_by, created_at, updated_at)`, `CampusExamPaper(id, exam_id, batch_id, subject, max_marks, pass_marks, starts_at, duration_minutes, room, event_id, created_by)`, `CampusExamMark(id, paper_id, member_id, marks, absent, remarks, graded_by, updated_at)`, `CampusHallTicket(id, exam_id, member_id, roll_number, token, issued_at, issued_by)`. Unique constraints: `uq_campus_exam (institution_id, term_id, name)`, `uq_campus_exam_paper (exam_id, batch_id, subject)`, `uq_campus_exam_mark (paper_id, member_id)`, `uq_campus_hall_ticket (exam_id, member_id)`; `campus_hall_tickets.token` unique.

- [x] Write the migration round-trip test using the same `MigrationContext`/`Operations` pattern as `test_campus_pilot.py` (upgrade 0037→0038 creates the four tables; downgrade drops them).
- [x] Run it, expect ImportError/failed.
- [x] Write models and migration (inspector `has_table` guards on upgrade, `drop_table` in reverse order on downgrade).
- [x] Run test, expect pass. Checkpoint.

### Task 2: Exam and paper CRUD with timetable linkage

**Files:**
- Create: `backend/app/schemas/campus_exams.py` — `ExamCreate(term_id:int, name:str[1..160], kind:Literal[...]="other")`, `ExamUpdate(name?, kind?)`, `PaperCreate(batch_id:int, subject:str[1..120], max_marks:float>0, pass_marks:float>=0, starts_at:datetime, duration_minutes:int[15..600], room:str="")`, `PaperUpdate` (all optional), `MarksPut(entries: list[MarkEntry(member_id:int, marks:float|None, absent:bool=False, remarks:str="")])`.
- Create: `backend/app/services/campus_exams.py`
- Create: `backend/app/routers/campus_exams.py`
- Modify: `backend/app/main.py` — `app.include_router(campus_exams.router, prefix="/api/v1/institutions", tags=["Campus exams"])` next to the campus_pilot include.
- Test: `backend/tests/test_campus_exams.py`

**Produces (service):**
- `list_exams(db, institution, member, term_id=None) -> list[dict]`
- `create_exam(db, institution, user, data) -> dict`, `update_exam(...)`, `publish_exam(db, institution, user, exam_id) -> dict`, `unpublish_exam(...)`
- `create_paper(db, institution, user, exam_id, data) -> dict`, `update_paper`, `delete_paper`
- `exam_dict(db, exam) -> {id, term_id, name, kind, status, published_at, papers:[paper_dict]}`; `paper_dict -> {id, exam_id, batch_id, batch_name, subject, max_marks, pass_marks, starts_at, ends_at, duration_minutes, room, event_id, marks_entered:int, students:int}`
- Paper creation calls `campus_pilot._conflicts(db, institution_id, starts_at, ends_at, batch_id, None, room)`; when the result is non-empty raise 409 with the same message shape as `create_events`. Creates `CampusEvent(kind="exam", series=f"exam:{paper.id}", title=f"{exam.name} · {subject}")` and stores `event_id`. Update re-checks conflicts excluding its own event.
- Status: create → `draft`; first paper → `scheduled`; deleting last paper → `draft`; publish requires ≥1 paper (422 otherwise), sets `published_at`; unpublish clears it. Both audited.

Tests (fixture `exam_campus` mirrors `pilot_campus`: owner, teacher, two students in batch, one other-institution owner):
- teacher creates exam → 201, status draft; second same name in term → 409.
- create paper → status scheduled, event exists with kind exam; overlapping paper same room → 409.
- student cannot create (404 scope), other institution 404.
- delete paper with marks → 409.
- publish without papers → 422; teacher publish → 403/404 (manager only); owner publish → published; unpublish → scheduled and audit row exists.

### Task 3: Marks entry and results

**Files:** same service/router/test.

**Produces:**
- `roster(db, institution, paper) -> [{member_id, name, roll_number, marks, absent, remarks}]` (active students of the paper batch).
- `put_marks(db, institution, user, exam_id, paper_id, entries)`; 409 when exam published; 422 when marks outside 0..max or member not in batch; absent forces marks None.
- `results(db, institution, exam_id, batch_id) -> {papers:[{id, subject, max_marks, pass_marks}], rows:[{member_id, name, roll_number, marks:{paper_id: {marks, absent}}, total, max_total, percent, passed:bool, rank:int}]}`; rank by total desc, ties share rank; `passed` = every paper has marks ≥ pass_marks and not absent.
- `my_results(db, institution, user, exam_id, student_user_id=None)` → 404 unless published; parent rules as in `self_accounts`.

Tests: bulk marks upsert twice (second replaces), invalid marks 422, locked after publish 409, results ranking (student A 80+70 rank 1, student B 50+absent rank 2 failed), student sees own results only after publish, parent approved sees, parent unapproved 404.

### Task 4: Hall tickets and PDFs

**Files:**
- Modify: `backend/app/services/campus_report_pdf.py` — add `build_hall_ticket_pdf(ticket: dict, branding=None) -> bytes` and `build_marksheet_pdf(sheet: dict, branding=None) -> bytes` reusing the existing page/header helpers.
- Service: `ensure_hall_tickets(db, institution, user, exam_id, batch_id=None) -> list[dict]` (idempotent; roll_number = `f"{batch_id:02d}-{member_id:04d}"`; token = `secrets.token_hex(16)`), `hall_ticket_pdf(...)`, `marksheet_pdf(...)`.
- Router: `GET /{id}/exams/{eid}/hall-tickets`, `GET /{id}/exams/{eid}/hall-tickets/{member_id}/pdf?student_user_id=`, `GET /{id}/exams/{eid}/results?batch_id=`, `GET /{id}/exams/{eid}/results/me?student_user_id=`, `GET /{id}/exams/{eid}/results/{member_id}/marksheet.pdf?student_user_id=`. PDFs return `application/pdf` with `Cache-Control: private, no-store`.

Tests: tickets generated once for two students, second call returns same tokens; student downloads own ticket (PDF magic `%PDF`) and not another's (404); mark sheet 404 before publish for student, 200 for staff; PDF text via PyPDF2 contains subject name.

### Task 5: Report card integration

**Files:** Modify `backend/app/services/campus_pilot.py::report_card` — after assessment rows, query published exams in the term whose papers include the student's batches; append rows `{"subject": f"{exam.name} · {paper.subject}", "score", "max_score", "grade" | "Absent" | "Pending", "comment": remarks}` and add to totals (absent → 0 of max).

Test: published exam paper with marks appears in `GET .../pilot/report-card` rows and totals; unpublished does not.

### Task 6: Frontend exams section

**Files:**
- Create: `frontend/src/api/campus-exams.ts` — `examsApi = { list(id, termId?), create(id, data), update(id, eid, data), publish(id, eid), unpublish(id, eid), createPaper(id, eid, data), updatePaper(id, eid, pid, data), deletePaper(id, eid, pid), roster(id, eid, pid), putMarks(id, eid, pid, entries), hallTickets(id, eid, batchId?), hallTicketPdf(id, eid, memberId, studentUserId?) -> Blob, results(id, eid, batchId), myResults(id, eid, studentUserId?), marksheetPdf(id, eid, memberId, studentUserId?) -> Blob }` and TypeScript types matching the dicts above.
- Create: `frontend/src/components/institutions/CampusExams.tsx` with props `{ data: InstitutionOverview; studentUserId?: number }`. Staff: term select (from `campusApi.academics` terms), exam list, "New exam" form, selected exam → papers table + "Add paper" form (batch, subject, max, pass, datetime-local, duration, room), per-paper "Enter marks" grid (inputs per student with absent checkbox, Save), "Hall tickets" (Generate, per-row Download), "Results" (batch select, table, Publish/Unpublish for managers). Student/parent: list of scheduled/published exams, Download hall ticket, published results table, Download mark sheet.
- Modify: `frontend/src/pages/institutions.tsx` — nav entry `{ key: "exams", label: "Exams", icon: ClipboardList }` after `academics`; render `<CampusExams key={inst.id} data={data} studentUserId={user?.id} />`.
- Test: `frontend/src/components/institutions/__tests__/campus-exams.test.tsx` — mocks `@/api/campus-exams` and `@/api/campus`; staff creates exam (calls `create`), enters marks (calls `putMarks` with entries), publishes (calls `publish`); student view shows results only when `myResults` resolves.

Run: vitest for the file, then `npm run lint`, `npx tsc --noEmit` (compare error count with baseline before changes; must not grow), `npm run build`.

### Task 7: Browser verification (exams)

Run `backend/.venv/Scripts/python.exe scripts/preview_campus.py` and `npm run dev -- --host 127.0.0.1` in `frontend`; log in with the owner shortcut from `.local/campus-preview-login.txt`; walk: create term (if missing) → Exams → new exam → paper → marks → results → publish → student login → results + hall ticket PDF. Record findings in `docs/INSTITUTION_BUILD.md` (new dated section).

---

## Module 2 — Fee reminders

### Task 8: Models and migration 0039

**Files:**
- Create: `backend/app/models/tuition_reminders.py` — `TuitionReminderPolicy` (PK `institution_id`), `TuitionReminder` with `dedupe_key String(120)` and `UniqueConstraint("institution_id","dedupe_key", name="uq_tuition_reminder_dedupe")`, index on `(status, created_at)`.
- Modify: `backend/app/models/__init__.py`.
- Create: `backend/alembic/versions/0039_tuition_reminders.py` (revises `0038`).
- Test: `backend/tests/test_tuition_reminders.py::test_migration_0039_round_trip`.

### Task 9: Policy endpoints

**Files:**
- Create: `backend/app/schemas/tuition_reminders.py` — `PolicyOut`, `PolicyPut(enabled:bool, days_before:list[int] (0..60, ≤5, unique), overdue_every_days:int 1..30, overdue_max:int 0..12, send_hour:int 0..23, channels:list[Literal["whatsapp","email"]] non-empty unique, whatsapp_template:str≤120, whatsapp_language:str≤20)`, `ReminderOut`, `ReminderListOut(items, next_after_id)`, `RunResult(staged, sent, failed, skipped)`.
- Create: `backend/app/services/tuition_reminders.py` — `get_policy(db, institution) -> dict` (defaults when missing), `save_policy(db, institution, user, data) -> dict`.
- Create: `backend/app/routers/tuition_reminders.py`; register in `main.py` under `/api/v1/institutions`.

Tests: default policy for manager; teacher/student 404; PUT validates duplicates/out-of-range 422; saved values round-trip.

### Task 10: Staging and recipient resolution

**Service functions:**
- `recipients_for(db, institution, student_member) -> list[{user, member: InstitutionMember|None, contact: WhatsAppContact|None}]` — student user + approved parents; `member` set when that user is an active member of this institution.
- `choose_channels(policy, recipient, whatsapp_ready: bool, mail_ready: bool) -> list[(channel, skip_reason|None)]`.
- `stage_installments(db, institution, policy, today: date, now_local_hour: int, force=False) -> int` — computes stages as in spec; inserts `TuitionReminder` rows with `dedupe_key = f"{installment_id}:{stage}:{recipient_user_id}:{channel}"`; ignores IntegrityError per row (idempotent). Returns staged count. Skips when `not policy.enabled and not force`, or local hour < send_hour unless `force`.
- Uses `tuition_service._snapshot_for(db, assignment)` to get per-installment outstanding; only installments with outstanding > 0.

Tests with fixed `today`: installment due in 7 days → `before:7` rows for student and approved parent; due today → `due:0`; 14 days overdue with every 7 → `overdue:2`; re-run stages 0; hour gating; disabled policy stages 0 unless force; unapproved parent excluded.

### Task 11: Delivery (email inline, WhatsApp via campaign pipeline) and worker

**Service functions:**
- `deliver_email(db, reminder) -> None` — locks row, builds subject/body per kind (upcoming/due/overdue/receipt), calls `EmailService._send_smtp_email` only if `campus_mail.mail_configured()`; sets sent/failed with error, increments attempts.
- `deliver_whatsapp(db, reminder) -> None` — requires `campus_whatsapp.configuration_status()["ready"]` (read the actual key from that function) and `policy.whatsapp_template` in `approved_templates()`; creates `CampusWhatsAppCampaign(request_key=f"reminder:{reminder.id}", template, language, parameters=[student_name, amount, due_on, institution.name], batch_id=None, created_by=reminder.created_by or owner)` and one `CampusWhatsAppMessage(member_id, phone, callback_key=secrets.token_hex(16))`; stores `whatsapp_message_id`; status `queued` → mirrored from the message on read (`sent`/`delivered`/`read` → sent; `failed` → failed).
- `deliver_pending(db, institution_id=None, limit=200) -> (sent, failed)`.
- `run_all(limit=500)` — for every institution with an enabled policy: `stage_installments` + `deliver_pending`; called from `campus_worker.tick()` after WhatsApp delivery.
- `run_now(db, institution, user) -> RunResult` (force=True).
- `retry(db, institution, user, reminder_id)` — only `failed`, attempts < 5.
- `remind_assignment(db, institution, user, assignment_id)` — earliest outstanding installment, stage `manual:{today}`, deliver immediately.
- Modify `tuition_service.record_payment` — after commit, call `tuition_reminders.queue_receipt(db, institution, payment, receipt)` guarded by policy enabled; failures logged, never raise.
- Modify `backend/app/services/campus_worker.py::tick` to call `run_all()`.

Tests: email path with `EmailService._send_smtp_email` monkeypatched → sent; unconfigured SMTP → failed with message; WhatsApp path with confirmed contact + configured settings (monkeypatch `configuration_status`/`approved_templates`) creates campaign+message rows and reminder queued; no consent → email fallback; nothing configured → skipped `no_channel`; receipt row after `record_payment`; retry only failed; `run_now` returns counts; `campus_worker.tick()` runs without error on SQLite.

### Task 12: Frontend reminders tab

**Files:**
- Create: `frontend/src/api/tuition-reminders.ts` — `remindersApi = { policy(id), savePolicy(id, data), list(id, params), runNow(id), retry(id, rid), remind(id, assignmentId) }`.
- Modify: `frontend/src/components/institutions/CampusFinance.tsx` — add a "Reminders" tab for managers rendering new `FeeReminders` component; add "Send reminder" action on account rows calling `remindersApi.remind`.
- Create: `frontend/src/components/institutions/FeeReminders.tsx` — policy form (enabled switch, days-before chips input, overdue every/max, send hour, channels checkboxes, template, language), Run now button showing `staged/sent/failed/skipped`, log table (kind, stage, recipient, channel, status, reason, attempts, Retry when failed).
- Test: `frontend/src/components/institutions/__tests__/fee-reminders.test.tsx` — saving policy calls `savePolicy` with parsed days; run now displays counts; retry button visible only for failed rows.

Run vitest, lint, tsc, build.

### Task 13: Browser verification (reminders) and docs

Preview walk: Finance → Reminders → enable, save → Run now (expect skipped rows with `no_channel` since preview disables providers) → log shows rows. Record in `docs/INSTITUTION_BUILD.md`. Update `docs/CAMPUS_OS_RELEASE_2026_09_11.md` with both modules, routes, migrations 0038/0039, and the provider prerequisites. Run the full campus-related backend suites (`test_campus_pilot.py test_campus_operations.py test_tuition_finance.py test_campus_exams.py test_tuition_reminders.py`) and report exact counts.


## Ledger (12 September 2026)

- Tasks 1-7 (exams) done: models, migration 0038, schemas, service, router, PDFs, report-card hook, `CampusExams.tsx`, nav entry, Vitest, browser walk. Extra: `GET .../hall-tickets/me/pdf` so learners and guardians fetch their own ticket without knowing a member id; hall-ticket issue made race-safe after the browser walk surfaced a 409.
- Tasks 8-13 (reminders) done: models, migration 0039, schemas, service, router, worker hook, receipt hook in `record_payment`, `FeeReminders.tsx`, Finance wiring with per-account Send reminder, Vitest, browser walk, docs. Deviation from spec: when no channel is usable the ledger records one skipped row per configured channel (not one row total) so the log names every missing prerequisite.
- Counts: backend 52 passed across five suites; frontend 451 passed, lint 0/0, tsc 0, build ok.
