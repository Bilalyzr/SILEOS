# SashaInfinity Education OS — production handoff

Validated: 2026-09-13

## Product topology

SashaInfinity is one platform kernel with three independently marketable business
pillars. A pillar owns its product experience and revenue streams; identity,
tenancy, entitlements, audit, payments, reporting, and administration remain
shared. A customer may buy one, two, or all three pillars without receiving a
separate account or a duplicated course/content database.

| Pillar | Public host | Product responsibility | Revenue families |
|---|---|---|---|
| Meiporul | `meiporul.sashainfinity.com` | 3D/AR/VR curriculum, immersive objects, virtual and experiential labs, lab deployments | course sales, asset licensing, subscriptions, deployment milestones, AMC/support |
| Seyappaduporul | `seyappaduporul.sashainfinity.com` | tutoring and institution operations: live classes, attendance, fees, notes, ebooks, exams and school services | tuition/tutoring fees, institution subscriptions, books/notes, papers, franchise services |
| Utporul | `utporul.sashainfinity.com` | skill course creation, quizzes, assignments, coding assessments, credentials and career pathways | course sales, assessment services, premium credentials, creator commerce, career services |

The main LMS remains the shared discovery, authentication, checkout, learner,
instructor, and admin surface. Hostname-aware public pages filter the catalog to
the relevant pillar. Course authoring can compose shared primitives while each
course keeps one canonical business-vertical classification for reporting.

## Shared platform kernel

The tenant boundary consists of `PlatformTenant`, memberships, verified domains,
vertical entitlements, audit events, and transactional outbox events. Institution
provisioning synchronizes with that boundary rather than becoming a separate LMS.
Admin controls are exposed under `/api/v1/platform/tenants` and in the Sasha
Control Center at `/admin/operations?view=tenants`.

The commercial boundary consists of offers, contracts, invoices, fiscal invoice
numbering, and immutable revenue-ledger events. It supports one-time,
subscription, usage, royalty, and milestone billing models. Every ledger event
has a pillar, revenue stream, tenant, source key, gross amount, and net amount.
Admin controls are exposed under `/api/v1/platform/commercial` and at
`/admin/operations?view=commercial`.

The consolidated portfolio report is a read model. Commerce payments, tuition
ledger entries, internship vouchers, and commercial ledger events remain the
authoritative sources; the portfolio aggregates them without rewriting source
transactions.

## Meiporul

Implemented product surfaces include the public immersive catalog, curriculum
authoring, reusable 3D/GLB assets, AR display, virtual lab catalog, native and
guided experiential labs, GeoGebra content, lab investigation evidence, and Lab
Studio publication controls.

The field-operations module is separate from course authoring. It manages tenant
deployment sites, device fleets, safety inspections, rollout milestones, go-live
readiness, service tickets, and SLA state. State-changing actions write audit and
outbox events. API: `/api/v1/meiporul/operations`. Admin UI:
`/admin/operations?view=meiporul`.

## Seyappaduporul

Implemented product surfaces include institution workspaces and roles, admissions
and student lifecycle, classes/batches, timetables, attendance, guardian access
and consent, tuition plans/installments/receipts, cash verification, online fee
orders, reminder policies, exams/papers/marks/results/hall tickets, staff leave
and substitution, transport, hostel, notices, goals, report cards, live Jitsi
classes and recordings, ebooks/notes, and priced question-paper generation.

Institution data is tenant scoped. Company and institution managers cannot query
another customer's workspace. Platform administrators retain a cross-tenant
control plane for support, reporting, and audited intervention.

## Utporul

Implemented product surfaces include course creation and publication, lessons,
quizzes, assignments, rubric grading, Assessment Studio, question banks, games,
mastery and adaptive planning, certificates, internships/career workflows, and
live coding assessments.

Coding submissions are queued and leased to a private worker. Hidden tests and
runner credentials are not returned to learners. The worker talks to an isolated
Judge0 CE deployment with network and resource limits, records retries, and uses
an internal service token. Public/admin API: `/api/v1/utporul/coding`; internal
worker API: `/api/v1/internal/coding`.

## Payments, fulfillment, and payouts

Razorpay order amounts are calculated from server-side prices. Paid multi-course
carts store a compact immutable signed snapshot, verify the exact captured order,
course set, user and amount, and converge through verify, webhook, or
reconciliation without duplicate fulfillment. A captured payment still fulfills
from that immutable snapshot if a coupon is later deleted.

Course revenue is allocated to order items. Instructor available balance is
derived from completed, non-mock order items owned by that instructor and reduced
by pending, approved, or paid withdrawals. Withdrawal state is one-way:
`pending -> approved|rejected`, then `approved -> paid`. Request and transition
events enter the central audit/outbox trail. Admin UI: `/admin/payouts`;
instructor UI: `/instructor/payouts`. The default minimum is INR 500 and can be
set with `MIN_WITHDRAWAL_INR`.

## Admin operating model

`/admin/operations` is the shared control center. It provides portfolio,
tenant/entitlement, commercial, per-pillar, daily-operations, inventory, outcomes,
revenue, health, and launch-readiness views. Existing admin workspaces retain
content, people, enrollment, course, ebook, assessment, certificate, internship,
order, invoice, coupon, membership, bundle, refund, and payout controls. View-as
sessions allow an admin to reproduce instructor or learner problems while
preserving the original admin session and audit boundary.

## Production rollout

1. Provision PostgreSQL, Redis, durable `uploads/`, `certificates/`, `invoices/`,
   `ebooks/`, logs, and backup storage. Take a verified database backup before an
   upgrade.
2. Supply unique persistent values for `SECRET_KEY`, `JWT_SECRET`,
   `VIDEO_SECRET`, `JITSI_JWT_SECRET`, `INTERNAL_TOKEN`, `CODE_RUNNER_TOKEN`,
   database/admin credentials, Razorpay credentials and webhook secret, and SMTP
   credentials. Configure Bunny, Firebase, WhatsApp, and Sentry only for enabled
   capabilities.
3. Deploy the private Judge0 service and set `JUDGE0_URL`; never expose Judge0 or
   the streaming service directly to the public internet.
4. Run `python -m alembic upgrade head`, then confirm `python -m alembic current`
   reports `0047` before serving traffic.
5. Build the frontend and start `docker-compose.production.yml`. Route public
   traffic only through nginx. Issue TLS certificates and DNS records for the
   LMS, backend, three pillar subdomains, and live-class host.
6. Configure Razorpay webhooks, sender-domain authentication, Jitsi/Jibri,
   storage/CDN policy, monitoring/alerts, log retention, and scheduled backups.
7. Perform a staging payment/refund/payout reconciliation, live-class recording,
   coding-runner isolation check, tenant-isolation check, restore drill, and
   capacity/load test before opening production traffic.

## Verified release gates

- Backend: 1,879 passed; 4 environment-dependent tests skipped.
- Frontend: 85 files and 483 tests passed.
- ESLint: zero warnings under `--max-warnings 0`.
- TypeScript: `tsc --noEmit` passed.
- Database: clean scratch upgrade and upgraded seeded preview both reached Alembic
  `0047 (head)`.
- Frontend: 59 labs/143 files checked; production Vite build completed across
  3,483 modules.
- Deployment: `docker compose -f docker-compose.production.yml config --quiet`
  passed with the required deployment variables supplied.
- Browser: platform login, portfolio, tenant/entitlement, commercial ledger,
  Meiporul operations, and admin payout screens loaded against the current API.

Build warnings about stale browser-compatibility metadata, mixed static/dynamic
auth imports, and two large lazy chunks are optimization work, not functional
release failures. Production go-live still requires real infrastructure,
provider credentials, DNS/TLS, backup restoration, and capacity evidence; those
cannot be completed safely from a local preview.
