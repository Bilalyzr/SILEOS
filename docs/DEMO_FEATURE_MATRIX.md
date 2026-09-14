# Isolated SaaS demo and acceptance matrix

Run from the repository root using a Python environment with the backend requirements:

```powershell
python scripts/seed_saas_demo.py --seed --serve --port 8014
```

The showroom owns only `.local/saas-demo/`. It refuses production mode and a foreign database URL; external payment, mail, WhatsApp, AI and recording credentials are disabled. Existing preview and production databases are not modified. Repeat seeding preserves the initial dataset and fills missing supported fixtures.

The local `campus-role-logins.json` contains generated credentials for admin, instructor/campus owner, teacher, students, parent, SPOC, company and company manager. Admin MFA details are local-only. Do not commit this file or reuse these identities in production. Credentials and databases are intentionally excluded from the release ZIP.

For a separate frontend, set `VITE_PROXY_TARGET=http://127.0.0.1:8014`, leave `VITE_API_URL` empty and run the existing Vite dev server. The configured default frontend origin is port 3000. Do not accidentally point the showroom at a real backend. Visit `/login`, then use the role's dashboard and **How it works**/tour controls.

## What is provided

| Area | Seeded scenario | Acceptance still needed |
| --- | --- | --- |
| Shared identity and tours | Synthetic role accounts, memberships and role-specific onboarding | Real email verification, Google OAuth, invitation delivery, recovery and device/browser review |
| Shared catalog and Utporul | Three published pillar courses, lessons, paid enrollments, quizzes, assignments awaiting grading, a bundle, inactive membership plan | Real purchases, refunds, subscription renewals, tax/accounting review |
| Learning experience | Supplied 3D model library, 59 bundled virtual labs, published game and curriculum references | Physical AR/VR, remote GeoGebra embeds, authored H5P import, low-end/mobile device performance |
| Meiporul operations | Demo site, headset fleet, planned safety/service tasks | Device pairing, actual deployments, inventory reconciliation and offline recovery |
| Coding assessment | Published example challenge and test cases | Isolated judge service, malicious-code sandbox testing, concurrency and resource limits |
| Seyappaduporul | Campus, batch memberships, tuition installments, payment verification, transport/hostel assignments, leave configuration, attendance and published exam marks | Real receipt delivery, parent communications and institution-specific operational sign-off |
| Student/instructor insights | Existing synthetic learning signals and lesson concept links | Real learning activity validation and educational review; AI output is not manufactured |
| eBooks, notes and certification | Downloadable private demo guide, a student lab notebook, shared orange certificate template and completion criteria | Complete the real course criteria to test issuance; a template is not an earned certificate |
| Live learning | Upcoming live-class schedule | Jitsi permissions, recording ingest, transcription, signed playback and provider failure recovery |
| Revenue/admin | Explicitly synthetic completed orders/payments and a pending cash verification | Razorpay sandbox capture/webhooks/refunds; reconcile before live use |
| Runtime monitor | Intentionally failed/dead maintenance sample with execution evidence | Start a real worker to prove recovery; demo does not manufacture a healthy heartbeat |

`feature-coverage.json` lists the actual row count of every table so empty areas remain visible. Seeded rows are not evidence that every feature or provider was tested. Existing backend/frontend suites exercise many additional empty/error/authorization paths; use both the fixtures and tests.

## Hands-on walkthrough

1. Sign in as student: open enrolled courses, launch the 3D/lab/game lessons, take a quiz and inspect recommendations. An unavailable AI provider must remain an explicit setup/failure state.
2. Sign in as instructor: inspect students, review a submitted assignment, use course authoring and the published coding challenge. Confirm unrelated instructors cannot access these records.
3. Sign in as campus owner/teacher: inspect the batch, attendance and published exams; review tuition and operational allocations. Use the parent account to check only linked learners.
4. Sign in as global admin: visit `/admin/operations?view=runtime`, inspect the synthetic failed maintenance job and queue a retry. In demo mode it stays queued until an actual worker is intentionally started.
5. Visit the communication preferences and tour controls for each role. Tour dismissal/progress follows the existing role-aware implementation.

Run `python scripts/validate_saas_release.py --url http://127.0.0.1:8014` for read-only local HTTP and restore checks. It writes `.local/saas-release-validation.json` and never captures a real payment or sends a real notification. `python scripts/verify_saas_demo.py` separately verifies all ten generated logins, admin MFA, own-profile access and the runtime admin boundary.

Provider acceptance should use dedicated sandbox accounts and synthetic learners. No live API keys, Firebase service accounts, SMTP passwords, copied user uploads or production data belong in the release archive.
