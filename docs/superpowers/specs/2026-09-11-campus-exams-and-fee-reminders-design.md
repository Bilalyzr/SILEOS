# Campus exams and fee reminders — design (2026-09-11)

Owner decision: build exam management and fee reminders (WhatsApp plus email) for Campus OS. Staff leave, transport, hostel, and the Flutter parent view are deferred. Build order: exams first, then fee reminders. Each module ships backend, migration, tests, frontend, and a browser check before the next starts.

## 1. Exam management

### Purpose
Formal, scheduled examinations for a term: schedule papers per batch and subject, issue hall tickets, enter marks, publish results, and feed the existing term report card. Daily classroom assessments (`campus_assessments`) stay as they are.

### Data (migration `0038_campus_exams`)

- `campus_exams`: `id`, `institution_id` FK, `term_id` FK `campus_terms`, `name` (160), `kind` in `unit|midterm|final|practical|other`, `status` in `draft|scheduled|published`, `published_at` nullable tz, `created_by` FK users, `created_at`, `updated_at`. Unique `(institution_id, term_id, name)`.
- `campus_exam_papers`: `id`, `exam_id` FK, `batch_id` FK `institution_batches`, `subject` (120), `max_marks` float > 0, `pass_marks` float ≥ 0 and ≤ max, `starts_at` tz, `duration_minutes` int 15..600, `room` (80, default ""), `event_id` FK `campus_events` nullable (the timetable row created for the paper), `created_by`. Unique `(exam_id, batch_id, subject)`.
- `campus_exam_marks`: `id`, `paper_id` FK, `member_id` FK `institution_members`, `marks` float nullable, `absent` bool default false, `remarks` (500, default ""), `graded_by` FK users, `updated_at`. Unique `(paper_id, member_id)`. `marks` must be 0..max_marks; absent implies marks null.
- `campus_hall_tickets`: `id`, `exam_id` FK, `member_id` FK, `roll_number` (40), `token` (32, unique), `issued_at`, `issued_by`. Unique `(exam_id, member_id)`.

Results are derived per student from papers and marks. Nothing stores totals.

### Rules
- STAFF (owner, admin, teacher) create and edit exams and papers and enter marks. MANAGERS (owner, admin) publish and unpublish. Both write an `institution_audit` row.
- Status: `draft` → `scheduled` automatically when the first paper exists; `published` only through the publish endpoint. Publishing requires at least one paper. Unpublishing is manager-only and audited.
- Marks entry is blocked (409) while status is `published`.
- Paper create/edit creates or updates a `campus_events` row with `kind="exam"`, `batch_id`, `room`, `starts_at`, `ends_at = starts_at + duration`, `series = "exam:{paper_id}"`, and runs the existing `_conflicts` check for batch and room. Deleting a paper (only when it has no marks) deletes the event.
- Hall tickets: generated lazily for every active student in the paper batches of the exam. Roll number = existing member roll if present, otherwise `{batch_id}-{member_id}` zero-padded. Regeneration is idempotent.
- Visibility: students see their own hall ticket once the exam is `scheduled` or `published`, and their own results only when `published`. Parents access through an approved `parent_link_requests` row with `student_user_id`, using the same pattern as `tuition_service.self_accounts`. Cross-institution and cross-batch access is 404.
- Report card: `campus_pilot.report_card` appends one row per published exam paper the student sat in that term (`subject = "{exam name} · {subject}"`), contributing to total score and grade. Absent rows show `Absent` and count as 0 of max.

### API (`app/routers/campus_exams.py`, prefix `/api/v1/institutions`)
- `GET /{id}/exams?term_id=` list (staff: all; student: scheduled/published only).
- `POST /{id}/exams` create. `PATCH /{id}/exams/{eid}` name/kind. `POST /{id}/exams/{eid}/publish`, `POST /{id}/exams/{eid}/unpublish`.
- `POST /{id}/exams/{eid}/papers`, `PATCH /{id}/exams/{eid}/papers/{pid}`, `DELETE /{id}/exams/{eid}/papers/{pid}`.
- `GET /{id}/exams/{eid}/papers/{pid}/marks` roster with current marks. `PUT .../marks` body `{entries:[{member_id, marks, absent, remarks}]}`.
- `GET /{id}/exams/{eid}/hall-tickets?batch_id=` (staff) list and generate. `GET /{id}/exams/{eid}/hall-tickets/{member_id}/pdf` (staff, the student, or an approved parent via `student_user_id`).
- `GET /{id}/exams/{eid}/results?batch_id=` (staff) consolidated table: per student, per subject marks, total, percentage, pass/fail, rank.
- `GET /{id}/exams/{eid}/results/me?student_user_id=` (student or approved parent).
- `GET /{id}/exams/{eid}/results/{member_id}/marksheet.pdf` (staff, student self, approved parent).

PDFs use ReportLab through `campus_report_pdf` helpers with institution branding, same as the report card.

### Frontend
- `frontend/src/api/campus-exams.ts` client.
- `frontend/src/components/institutions/CampusExams.tsx`: term selector, exam list, create exam dialog, papers table with schedule and conflict errors, marks grid per paper, hall tickets (generate, download), results table with publish/unpublish. Student and parent view: hall ticket download and published results.
- New nav entry `exams` (label "Exams") in `pages/institutions.tsx`, visible to all members.
- Vitest: `components/institutions/__tests__/campus-exams.test.tsx`.

### Tests (`backend/tests/test_campus_exams.py`)
Create exam and paper, timetable conflict rejection, marks validation and bulk entry, marks locked after publish, manager-only publish, student visibility before/after publish, parent access with and without approval, cross-institution 404, hall ticket idempotency and PDF bytes, results ranking and pass/fail, mark sheet PDF, report card includes exam rows, migration 0038 upgrade/downgrade round trip on SQLite.

## 2. Fee reminders

### Purpose
Automatic due-date and overdue reminders, plus receipt notices, from the existing tuition ledger, over WhatsApp and email, without ever claiming a send that did not happen.

### Data (migration `0039_tuition_reminders`)
- `tuition_reminder_policies`: `institution_id` PK/FK, `enabled` bool default false, `days_before` JSON list of ints (default `[7, 1]`, each 0..60, max 5 entries), `overdue_every_days` int 1..30 default 7, `overdue_max` int 0..12 default 3, `send_hour` int 0..23 default 9, `channels` JSON subset of `["whatsapp","email"]` default both, `whatsapp_template` (120, default ""), `whatsapp_language` (20, default "en"), `updated_by`, `updated_at`.
- `tuition_reminders`: `id`, `institution_id`, `assignment_id` FK, `installment_id` FK nullable, `receipt_id` FK nullable, `student_member_id` FK, `recipient_user_id` FK users, `kind` in `upcoming|due|overdue|receipt`, `stage` (32; `before:7`, `due:0`, `overdue:2`, `receipt`), `channel` in `whatsapp|email`, `status` in `queued|sent|failed|skipped`, `skip_reason` (120, default ""), `error` (250, default ""), `attempts` int default 0, `amount` MONEY, `currency` (3), `whatsapp_message_id` FK `campus_whatsapp_messages` nullable, `created_at`, `sent_at` nullable, `updated_at`. Unique `(installment_id, stage, recipient_user_id, channel)` for installment kinds and `(receipt_id, recipient_user_id, channel)` for receipts (enforced in service; DB unique on `(institution_id, dedupe_key)` where `dedupe_key` is the string form).

### Rules
- Recipients for a student: the student's own user, plus every user with an approved `parent_link_requests` row for that student.
- Channel selection per recipient: WhatsApp when the policy allows it, WhatsApp is configured, and the recipient is an active member of the institution with a confirmed `whatsapp_contacts` row; otherwise email when the policy allows it and the recipient has an email. If neither applies the row is `skipped` with `skip_reason` (`no_consent`, `whatsapp_not_configured`, `email_not_configured`, `no_channel`).
- Staging: on each run, for each active assignment with outstanding balance, for each installment with `amount_due` not fully settled (from `_snapshot_for`), compute stages due today in the institution timezone: `before:N` when `due_on - today == N`; `due:0` when `due_on == today`; `overdue:K` when `(today - due_on) // overdue_every_days == K` and `1 ≤ K ≤ overdue_max`. Rows are only created when local hour ≥ `send_hour`. Insert is idempotent through the unique key.
- Delivery: email rows are sent inline through `EmailService._send_smtp_email` with the same locked-row, attempt-counting pattern as `campus_mail.deliver`; failed rows can be retried up to 5 attempts. WhatsApp rows create one `campus_whatsapp_campaigns` row (`request_key = "reminder:{reminder_id}"`, personalised `parameters`: student name, amount, due date, institution name) plus one `campus_whatsapp_messages` row for the member, then rely on the existing `deliver_pending` loop, webhooks, and status updates. The reminder row mirrors the message status when read.
- Receipts: `record_payment` queues a `receipt` reminder for each recipient after commit when the policy is enabled. Email includes receipt number, amount, balance after, and a link to the finance page. WhatsApp uses the same template with the receipt fields.
- Worker: `campus_worker.tick` calls `tuition_reminders.run_all(limit=500)` after WhatsApp delivery. The manual `run-now` endpoint runs the same function for one institution regardless of `send_hour`.
- Nothing sends when `enabled` is false. Manual per-account reminders still work when the policy is disabled, since a manager explicitly asked.

### API (`app/routers/tuition_reminders.py`, prefix `/api/v1/institutions`)
- `GET /{id}/fees/reminders/policy`, `PUT /{id}/fees/reminders/policy` (managers).
- `GET /{id}/fees/reminders?status=&limit=&after_id=` delivery log (managers, keyset).
- `POST /{id}/fees/reminders/run-now` (managers) → `{staged, sent, failed, skipped}`.
- `POST /{id}/fees/reminders/{rid}/retry` (managers; only `failed`).
- `POST /{id}/fees/assignments/{aid}/remind` (managers) → stages `manual:{timestamp-date}` rows for the earliest unpaid installment and delivers immediately.

### Frontend
- `frontend/src/api/tuition-reminders.ts` client.
- `CampusFinance.tsx` gains a "Reminders" tab (managers): policy form, run-now button with result counts, delivery log table with status, channel, reason, retry. Account rows gain a "Send reminder" action.
- Vitest: `components/institutions/__tests__/fee-reminders.test.tsx`.

### Tests (`backend/tests/test_tuition_reminders.py`)
Policy validation and manager-only access, staging for before/due/overdue stages with a frozen date, idempotent re-run, `send_hour` gating, disabled policy sends nothing, recipient resolution including approved and unapproved parents, WhatsApp path creates campaign and message rows when consent exists, email fallback, skipped with reason when nothing configured, receipt notice on payment, manual remind, retry only on failed, worker tick integration, migration 0039 round trip.

## 3. Verification
- Backend: new test files plus `test_campus_pilot.py`, `test_tuition_finance.py`, `test_campus_operations.py` must pass.
- Frontend: `npm run test -- --run` for the new and neighbouring tests, `npm run lint`, `npx tsc --noEmit`, `npm run build`.
- Browser: `scripts/preview_campus.py` plus Vite dev server; walk exam creation → paper → marks → publish → student results → hall ticket PDF, and reminder policy → run now → log.
- Docs: `docs/CAMPUS_OS_RELEASE_2026_09_11.md` gains both modules, routes, and migrations 0038 and 0039.
