# SashaInfinity Campus OS release

Release date: 11 September 2026

This release expands SashaInfinity from an LMS into a shared operating workspace for schools and colleges. It keeps the light glass interface and deep orange gradient across the public site, dashboards, banners, dialogs, tables, and empty states.

## What is included

- **Today workspace:** role-aware priorities, schedule, notices, metrics, attendance and grading reminders, fee alerts, admissions signals, and assignable action items.
- **Admissions:** programs, intakes and capacity; applicant stages and history; document tracking; notes and tasks; offers with PDF output; enrollment conversion; learner lifecycle records; pagination, optimistic concurrency, and idempotency.
- **Student finance:** fee plans, components and installments; student assignments; discounts and waivers; append-only ledgers; payments and receipts; balances and aging; parent/student views; tenant and role controls.
- **Campus growth:** a public institutions page with plan comparison and consented lead capture, plus a searchable help center.
- **Trust and integrations:** custom-domain DNS setup, integration configuration with redacted secret references, retention rules, privacy requests, consent receipts, and OneRoster 1.2 ZIP export.
- **WhatsApp communications:** global communications center, account-level preferences, institution workflows, templates, delivery state, retry and rate controls, opt-in records, quiet hours, audit trails, and branded share banners.
- **Platform reliability:** request IDs, protected worker leadership through a PostgreSQL advisory lock, tenant isolation, RBAC, idempotent writes, and sequential Alembic migrations.

## Added 12 September 2026

- **Exam management:** exams per academic term with draft, scheduled and published states; one paper per batch and subject placed on the shared timetable with room and batch conflict checks; marks entry with absent handling, locked once results are published; consolidated batch results with rank and pass/fail; hall tickets with roll numbers and verification codes; branded hall-ticket and mark-sheet PDFs; published exam rows join the term report card. Students and approved guardians see hall tickets once scheduled and results only after a manager publishes. Migration `0038_campus_exams`.
- **Fee reminders:** one policy per institution (days before due, overdue cadence and cap, send hour in campus time, channels, WhatsApp template); an append-only reminder ledger with one row per installment, stage, recipient and channel so re-runs never send twice; recipients are the student plus approved guardians; WhatsApp goes only to consented campus members through the existing campaign pipeline, everyone else falls back to email; rows that cannot be sent are recorded as skipped with a reason, never as sent; receipt notices are queued after every recorded payment; the campus worker runs reminders each tick, and managers can run now, retry failed rows, or send a manual reminder from an account row. Migration `0039_tuition_reminders`.

- **Staff leave and substitution:** leave types with annual quotas per academic year; teachers apply for their own leave (no overlaps, at most 60 days); managers approve against derived balances, with an audited override note when a quota would be exceeded, or reject with a reason; approval turns every timetable slot the absent teacher owns into an open substitution, and cancelling releases them; managers assign only colleagues who are free (no overlapping class, no overlapping substitution, not on leave); timetable cards show "Covered by", the substitute's Today schedule includes the class, and managers get a Today action while classes in the next seven days are uncovered; a leave and substitution-hours report with CSV export. Migration `0040_campus_staff_leave`.

- **Transport:** routes with vehicle, driver, capacity and ordered stops with pickup and drop times; students assigned to one route and stop with capacity enforced; daily boarding and drop log for today or past days; a route roster CSV; students and approved guardians see their route, stop and today's status; managers get a Today action while an active route has no boarding recorded. A route with a fee owns a published tuition plan `Transport · {route}`; assigning a student assigns that plan so reminders and receipts apply. Migration `0041_campus_transport`.
- **Hostel:** blocks with warden and optional fee, rooms with type and bed capacity, allocations with check-in and check-out and capacity enforced; out-passes requested by residents and approved, rejected or marked returned by staff; a visitor register; occupancy report with CSV; residents and approved guardians see room and passes; staff get a Today action while passes are pending. Hostel fees follow the same plan-per-block rule as transport. Migration `0042_campus_hostel`.

- **Fee collection:** cash and cheque recorded at the counter carry the staff member who received them and stay pending until a second owner or admin verifies the count (the receiver cannot verify their own entry; a one-person office may self-verify with an audited tag); a daily cash desk per receiver with CSV export and a Today action while cash is unverified; branded receipt PDFs for every payment showing receiver and verification; numbered demand invoices for one installment or the whole balance, printable by managers, students and approved guardians; online payment through Razorpay from the student and parent fee pages, verified by signature, reconciled on dismiss and fulfilled by the shared webhook, posting through the same ledger path as counter payments; a capture that exceeds the remaining balance is posted up to the balance and the remainder flagged for a manual refund; honest 503 until gateway keys are set; reminders carry a pay link once they are. Migration `0043_fee_collection`.

- **Parent portal:** the `/parent` page now shows every approved child's campus signals in one place: 30-day attendance, fees outstanding and overdue with the next due installment, the latest published exam results with rank, today's transport status, hostel room and out-pass state, recent notices, and derived alerts (overdue fees, low attendance, not boarded, pending out-pass, newly published results). Pure aggregation over the existing guardian-scoped services through `GET /api/v1/parents/campus`; no migration. The online-learning digest stays below. Also fixed: the parents API prefix was missing from the client's no-trailing-slash list, so the pre-existing digest call returned 404.

Routes: `/parent`, `/institutions/:id/exams`, `/institutions/:id/staff`, `/institutions/:id/transport`, `/institutions/:id/hostel`, and the Reminders panel inside `/institutions/:id/finance`. API prefixes: `/api/v1/institutions/{id}/exams/*`, `/api/v1/institutions/{id}/staff/*`, `/api/v1/institutions/{id}/transport/*`, `/api/v1/institutions/{id}/hostel/*`, `/api/v1/institutions/{id}/fees/reminders/*`, `/api/v1/institutions/{id}/fees/assignments/{aid}/remind`.

Prerequisites: SMTP settings for email reminders; Meta WhatsApp Cloud API credentials plus an approved template name saved in the policy for WhatsApp reminders. Without them the delivery log shows `skipped` rows with the missing prerequisite named.

## Main product routes

- `/campus` - public schools and colleges page
- `/help` - searchable product help
- `/institutions/:id/today` - daily action center
- `/institutions/:id/admissions` - admissions workspace
- `/institutions/:id/finance` - fees, receipts, cash desk, invoices and online payment
- `/parent` - parent portal with Pay now and invoice download
- `/institutions/:id/trust` - domains, integrations, privacy, retention, consent, and OneRoster
- `/admin/communications` - SashaInfinity-wide WhatsApp and communications operations

## Database migrations

Apply the migrations in order through Alembic:

- `0035_admissions_student_lifecycle`
- `0036_tuition_finance`
- `0037_campus_growth_control_plane`
- `0038_campus_exams`
- `0039_tuition_reminders`
- `0040_campus_staff_leave`
- `0041_campus_transport`
- `0042_campus_hostel`
- `0043_fee_collection`

```bash
cd backend
alembic upgrade head
```

## Deployment checklist

1. Copy `.env.example` to `.env` and provide production database, Redis, email, payment, storage, and WhatsApp provider values.
2. Apply `alembic upgrade head` from the backend directory.
3. Build the frontend with `npm ci && npm run build` in `frontend`.
4. Start the API and the background worker as separate production processes.
5. Verify the public `/campus` page, each role dashboard, communications delivery, receipt generation, and the institution trust page.
6. Add the DNS record shown in the custom-domain flow and complete provider-side SSO, LTI, DigiLocker, WhatsApp, payment, email, and storage credentials before enabling those services for customers.

The repository never needs plaintext provider secrets in integration records. Store secrets in the deployment secret manager and save only their reference names in SashaInfinity.
