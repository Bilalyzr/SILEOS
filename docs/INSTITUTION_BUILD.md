# Institution SaaS build — 10 September 2026

Audience: schools and colleges. This release implements the requested light-orange gradient and glass UI, matching display/share banners, and the campus workflows below. See [the release guide](SAAS_CAMPUS_RELEASE.md) for setup, limits, access boundaries and provider references.

## Delivered

1. Shared light-orange gradients, warm glass surfaces, responsive navigation, readable forms, focus/hover/pressed states, reduced-motion and contrast preferences. Semantic success and danger colors retain their meaning.
2. Reusable dashboard and campus banners, persisted campus headline/artwork uploads, share previews, optional local artwork, downloadable 1200 × 630 PNGs and public-course social preview metadata. English and Tamil artwork was visually checked.
3. Institution creation and switching, independent campus roles, verified-account invitations, atomic CSV invitation import, optional durable email delivery, suspension, batches and audit history.
4. Academic terms, batch attendance, assessments, grading and feedback, with student access limited to their own records.
5. Private campus courses, draft/publish workflows, lessons, protected resources, completion and staff progress. Existing connected catalog courses keep their original purchase and visibility rules.
6. Guardian requests that require student approval and support revocation.
7. Usage limits, plan requests, provider-priced subscription checkout, verified-charge entitlements, period-end cancellation, invoices and administrator recovery of uncertain checkout attempts.
8. Migration and authorization coverage, frontend deployment quality gates, and read-only production prerequisite checks. The existing operations dashboard also handles missing storage without crashing or inventing capacity.
9. A Daily campus workspace with an eight-step setup guide, a recurring timetable with room/teacher/batch conflict checks, scoped announcements and read state, a personal attention feed, learner goals, configurable grading, and branded report-card PDFs.
10. A consent-first Meta WhatsApp Cloud API integration shared across SashaInfinity. Every authenticated user has one account-level phone and consent record, confirmed through a one-time inbound JOIN challenge. Institution campaigns resolve members to that global consent and still enforce active membership; campaigns from the global **Communications Center** require an explicit allowed role audience. Signed webhooks, account-wide STOP handling, approved-template allow-lists, durable jobs, idempotent campaign creation, retry leases, delivery/read metrics and optional HTTPS banner headers protect the workflow. Large recipient sets expand in atomic 500-row keyset batches, and each delivery tick fairly interleaves platform and campus queues with at most four local workers. Managers and administrators can inspect eligibility but cannot grant consent for another person.

The institution workspace is available at `/institutions`, linked as Campus in the application. Personal WhatsApp consent belongs to **Communication preferences** at `/communication-preferences` rather than one institution setup. The Daily campus WhatsApp area keeps institution campaign context and links to that shared account setting. Platform administrators use the **Communications Center** at `/admin/communications`. Starter allows 100 active members plus pending invitation reservations, 10 batches and 20 total connected/private courses. A verified account can create up to five institutions. Roles and data access are scoped to active membership.

## Validation

- The full frontend suite passed **439 tests in 71 files**, including account-wide Communication preferences, the global Communications Center, retry-safe campaign drafts, the institution handoff to account consent and the expanded live-preview route contract coverage.
- Frontend lint, TypeScript checks and the production build passed. Existing video/3D chunks still exceeded Vite's 500 kB warning threshold; realistic performance testing and bundle optimization remain follow-up work.
- The selected backend release suite passed **83 tests**, covering the daily campus pilot, campus operations, institutions, subscription webhooks, operations health, company-manager profile access, the SuperAdmin overview on SQLite, account-wide WhatsApp consent, global Communications Center campaigns, concurrent request idempotency, atomic 1,205-recipient expansion and bounded fair delivery scheduling. This was not a claim that the entire backend suite was run.
- Migrations `0031`, `0032` and `0033` passed the recorded SQLite upgrade/downgrade checks; the earlier institution migration `0030` also passed a round trip. Migration `0034` passed its SQLite upgrade/downgrade check through `test_global_whatsapp`, including legacy institution-consent mapping and downgrade synchronization. The release checker requires migration head exactly `0034` and the global WhatsApp tables. Live PostgreSQL migration execution and concurrent locking behavior still require staging verification.
- Browser checks against fictional Greenwood College data verified persisted settings, invitations, batches, assignment, academic term creation, attendance, assessment grading, private course creation/publishing, lesson completion, the Daily campus workspace, and WhatsApp's safe setup-required state. The saved custom banner persisted after reload. Desktop and 390 px mobile layouts were visually inspected; mobile content fits the viewport.
- Server-generated English/Tamil banners were rendered and visually checked. Sharing controls have component coverage; no social post, real invitation email or payment was sent during verification.

The frontend result includes the account-wide WhatsApp surfaces, and the selected backend result includes account-wide consent, global Communications Center campaign coverage, transactional recipient batching, bounded delivery scheduling and migration `0034`'s SQLite round trip. Live PostgreSQL migration and multi-instance concurrency checks remain staging work.

## Local preview

Run `backend/.venv/Scripts/python scripts/preview_campus.py` from the repository root and `npm run dev -- --host 127.0.0.1` from `frontend`. Open `http://127.0.0.1:3000/institutions` for the campus workspace and use the account communication preferences for personal WhatsApp consent.

The helper uses fictional data in ignored `.local/campus-preview.sqlite`, saves the complete role matrix in `.local/campus-role-logins.json` and the owner shortcut in `.local/campus-preview-login.txt`, forces institutional payment, email and WhatsApp provider configuration off, and binds to loopback. It cannot send external WhatsApp messages. It is separate from production and does not run production lifespan jobs.

## Production acceptance still required

Configure real HTTPS origins, SMTP, merchant plans, backend-only Meta WhatsApp credentials and signed webhook verification; apply migrations to a backed-up staging PostgreSQL database; verify global consent/STOP behavior, audience authorization, delivery, gateway test events, cancellation, invoice/accounting procedures, access isolation, backup restoration and realistic load before deployment. The local build does not provision or deploy production infrastructure.

Existing LMS catalog/media records are not automatically converted into private tenants. Confidential material belongs in the new private campus course/resource area. Enterprise SSO/SCIM, verified custom domains, migration of legacy tenant content and production security/performance acceptance remain separate work. Working features and setup-dependent integrations are distinguished in the UI and [release guide](SAAS_CAMPUS_RELEASE.md).

## Exams and fee reminders — 12 September 2026

Delivered: exam management (`campus_exams` service, migration 0038) and tuition fee reminders (`tuition_reminders` service, migration 0039). Design: `docs/superpowers/specs/2026-09-11-campus-exams-and-fee-reminders-design.md`; plan: `docs/superpowers/plans/2026-09-11-campus-exams-and-fee-reminders.md`.

Validation (all commands run locally on 12 September 2026):

- Backend: `tests/test_campus_exams.py` (11 tests) and `tests/test_tuition_reminders.py` (8 tests) pass, and the neighbouring suites `test_tuition_finance.py`, `test_campus_pilot.py`, `test_campus_operations.py` still pass — **52 passed** in one run. Migrations 0038 and 0039 pass SQLite upgrade/downgrade round trips inside those suites. This is not a full-backend-suite claim.
- Frontend: full Vitest run **451 tests in 74 files passed**; `npm run lint` 0 errors and 0 warnings; `tsc --noEmit` 0 errors (baseline was 0); `npm run build` succeeded.
- Browser (synthetic Greenwood College preview, Python 3.13 venv): as owner, created a term, an exam, a Physics paper (timetable event created, status moved to Scheduled), entered marks, saw ranked results, published; hall-ticket list and both PDFs returned `application/pdf` bytes. As a batch student: timetable, published result with rank, hall-ticket and mark-sheet downloads worked; a different student's mark sheet returned 404 and the staff ticket list returned 403. Finance: enabled the reminder policy, ran it now, sent a manual reminder; the delivery log listed `skipped` rows naming the missing SMTP and WhatsApp configuration, because the preview disables both providers.

Found and fixed during the browser walk: concurrent hall-ticket requests could race on the unique constraint and return 409; the service now rolls back and re-reads the winner's rows.

Observed, not fixed: the preview's single SQLite file returned `database is locked` once under concurrent requests (publish returned 500, the retry succeeded). Production runs PostgreSQL; the SQLite engine has no busy-timeout configured, which is pre-existing.

Not done: real SMTP or Meta WhatsApp delivery (no credentials in this environment); PostgreSQL migration execution; Flutter parent view (deferred by owner decision).

## Staff leave and substitution — 12 September 2026

Delivered: `campus_staff` service and router (migration 0040), Staff section in the institution workspace, timetable and Today hooks. Spec `docs/superpowers/specs/2026-09-12-staff-leave-substitution-design.md`, plan `docs/superpowers/plans/2026-09-12-staff-leave-substitution.md`.

Validation (12 September 2026):

- Backend: `tests/test_campus_staff.py` **10 passed**; with `test_campus_action_center.py`, `test_campus_pilot.py`, `test_campus_exams.py`, `test_tuition_reminders.py`, `test_tuition_finance.py`, `test_campus_operations.py` the combined run was **63 passed** before the CSV regression test was added (64 with it). Not a full-backend-suite claim.
- Frontend: full Vitest **454 tests in 75 files passed**; lint 0/0; `tsc --noEmit` 0; production build passed.
- Browser (Greenwood College preview): owner saved a Casual leave type (quota 12) through the Leave types tab; teacher saw only My leave and Substitutions, a 12-of-12 balance, and applied for 14 September through the dialog (201); owner approved through the dialog (200) and the Mathematics slot appeared as an open substitution; the candidate list excluded the absent teacher and offered the two free staff; assignment succeeded and the timetable event API returned the substitute's name.
- Found and fixed during the walk: CSV report download returned 400 because the academic year's en dash cannot be sent in an HTTP header. Fixed, covered by a test, and re-verified in the browser (200, `leave-report-2026-2027.csv`, three staff rows). The Daily campus calendar card for the covered class reads "Covered by Preview Campus Administrator".
- Not verified in the browser: the Today "classes need a substitute" card (covered by the backend test; the preview slot was assigned before Today was opened).

## Transport and hostel — 12 September 2026

Delivered: `campus_transport` (migration 0041) and `campus_hostel` (migration 0042) services and routers, Transport and Hostel sections in the institution workspace, Today hooks, and the fee link through per-route and per-block tuition plans. Spec `docs/superpowers/specs/2026-09-12-transport-hostel-design.md`.

Validation (12 September 2026):

- Backend: `tests/test_campus_transport.py` **5 passed**, `tests/test_campus_hostel.py` **5 passed**; combined run with the other touched suites (`test_campus_staff`, `test_campus_action_center`, `test_campus_pilot`, `test_campus_exams`, `test_tuition_reminders`, `test_tuition_finance`, `test_campus_operations`) **74 passed**. Not a full-backend-suite claim.
- Frontend: full Vitest **458 tests in 76 files passed**; lint 0/0; `tsc --noEmit` 0; production build passed.
- Browser (Greenwood College preview): owner created the North loop route with one stop and a ₹1,500 fee (201, fee plan published); assigned Diya Shah; saved boarding (roster shows boarded); the Transport · North loop plan appeared in her fee accounts. Owner created Block A with room 101 and a ₹24,000 fee (201) and allocated Diya (201). Diya's transport view returned her stop and today's status; she requested an out-pass through the dialog (201). The teacher's Today listed "1 hostel pass waiting for a decision" and the staff hostel view hid manager controls; the teacher approved the pass; both CSV endpoints returned 200.
- Deviation from the two-increment plan: hostel was built before the transport browser walk; both were then walked in one session.
- Not done: real payment of the transport or hostel fee (no gateway in preview); Flutter parent view (deferred by owner).

## Parent portal — 12 September 2026

Delivered: `services/parent_portal.py` + `routers/parent_portal.py` (`GET /api/v1/parents/campus`), the rewritten `pages/parent/dashboard.tsx`, and `api/parent-portal.ts`. No migration. Spec `docs/superpowers/specs/2026-09-12-parent-portal-design.md`.

Validation (12 September 2026):

- Backend: `tests/test_parent_portal.py` **4 passed** (every signal for an approved child, unapproved child hidden, role gate 403, empty state, graceful degradation when one block raises, child without campus membership).
- Frontend: full Vitest **460 tests in 77 files passed**; lint 0/0; `tsc --noEmit` 0; production build passed.
- Browser (Greenwood College preview): logged in as the preview parent linked to two students; the page showed both children with per-institution cards. Diya Shah's card showed the overdue-fee and results-published alerts, ₹28,500 outstanding (tuition + transport + hostel plans) with ₹2,000 overdue, "Boarded" for today on North loop · Anna Nagar, Block A · 101 with the approved out-pass, and Mid-term 2026 82/100 rank 1 of 4. The online-learning digest loaded as well.
- Found and fixed during the walk: `/parents` was missing from `frontend/src/api/axios.ts::noSlashEndpoints`, so both the new portal call and the pre-existing digest call were rewritten with a trailing slash and returned 404 (backend runs `redirect_slashes=False`). Added the prefix.
- Not done: the `/parent` route still renders without the dashboard sidebar, as before this change.

## Fee collection — 12 September 2026

Spec `docs/superpowers/specs/2026-09-12-fee-collection-design.md`, plan
`docs/superpowers/plans/2026-09-12-fee-collection.md`. Migration `0043_fee_collection`.

Verified locally (SQLite preview, Python 3.13 venv):

- Backend `tests/test_fee_collection.py` (10): migration round-trip with backfill,
  receiver rules, verification rules incl. sole-manager self-verify, cash desk + CSV,
  Today cards, receipt PDF access, invoices, online order 503 / create / verify /
  replay, webhook capture with excess. Combined sweep of nine touched suites: 60 passed.
- Frontend `fee-collection.test.tsx` (5) + `parent-dashboard.test.tsx` (3); full
  Vitest 466 passed in 78 files; ESLint 0; tsc 0; production build passed.
- Browser walk: see the ledger in the plan file.

Not verified: a live Razorpay checkout (no keys in the preview; the 503 path is what
the preview shows), PostgreSQL migration on staging, real refund handling.
Legacy tests that recorded cash without a receiver were switched to UPI, because the
receiver is now mandatory for cash and cheque.
