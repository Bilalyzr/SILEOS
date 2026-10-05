# SashaInfinity: adaptive mathematics pilot

Implemented 27 September 2026. This is a narrow, rule-based pilot, not a
validated learning system or a claim that the whole SaaS is production-certified.

## Experience

- `/discover/volume`: public, orange-themed SVG cube explorer. No headset,
  model download or AI provider required. The component sends no learning events.
- `/math-pilot`: authenticated, enrolled student experience.
- `/instructor/math-pilot`: course-owner/collaborator/admin review and evidence.
- Existing student mastery and instructor navigation link to the new screens.
  Contextual page guides explain the workflow.

The public explorer demonstrates equal layers. The recorded pilot proceeds:
prediction -> two diagnostic items -> recommended explanation + helped cube
construction -> two independent transfer questions -> three-day wait -> two
different retention questions. The transfer and retention forms omit the helper
and explanations. This is not a proctored assessment: external help cannot be
excluded, and the public demonstration is intentionally available.

Each catalog version is hashed from prompts, keys, taxonomy and explanations.
Educators inspect the full material and acknowledge content suitability and
student-data arrangements before enabling it for their own course. A version
change requires another review. Approval records an attestation, not independent
legal, privacy or pedagogical certification. The first shipped wording is English;
Tamil translation and classroom age/grade alignment still require educator review.

## Reuse audit and changes

| Capability | Existing foundation | This release / remaining limitation |
| --- | --- | --- |
| Content and immersive activities | `ConceptLabPlayer`, guided labs, 3D tasks, GeoGebra | Adds a lightweight cube manipulative, not a replacement renderer |
| Prerequisites and learner state | `models/mastery.py`, `services/mastery_service.py` | Approved pilot links prerequisites into existing graph; task-specific hypotheses remain tentative |
| Adaptive practice | `learning_signals_service.py`, `learning_planner_service.py` | Adds pinned volume tasks with deterministic selection; no LLM diagnosis |
| Teacher review | Existing intervention queue and course collaborator rules | Reuses course authorization; adds per-attempt explanation override before transfer |
| Independent outcome checks | Existing planner follow-up checks | Distinct transfer/retention items; server enforces three-day delay |
| Learning evidence | Existing mastery evidence and estimates | Only independent transfer/retention create weighted evidence; clicks/helped construction never award mastery |
| Course/institution access | Existing identity, enrollment and course-editor checks | Pilot is course-scoped; a school must provision private courses/enrollments correctly |
| Brand sharing/referrals | Existing course share banners and cohort referral codes | Adds a public activity customers may share voluntarily; no duplicate rewards ledger |
| Revenue/admin | Existing shared Growth OS | Left intact; this pilot does not create new charges or manipulate prices |
| Efficacy and scale | Prior local release checks | Still unproven: classroom outcome study, PostgreSQL concurrency, sustained staging load and recovery |

## Data and correctness

New tables: `math_pilot_policies`, `math_pilot_sessions`, `math_pilot_events`.
Alembic revision **0052**, after 0051, is frozen and reentrant. Apply the migration
to an existing deployment before serving new code; do not rely on create_all to
upgrade existing databases.

- Session uniqueness: learner + course + catalog version.
- Event uniqueness: session + request UUID and session + monotonic sequence.
- Compare-and-swap sequencing rejects stale tabs; matching retries do not award
  duplicate evidence. Conflicting request-key payloads return 409.
- Answer keys are server-owned and never included in student task responses.
  Only educators authorized for the course can inspect the complete keys.
- Server timestamps, explicit stage, version, answers, rule outcome and teacher
  decisions are retained. No cameras, biometrics, raw keystrokes or emotion inference.
- Internal user IDs are still personal identifiers, not anonymous research data.
  No public learner-results route exists. Private API responses use no-store.
- Self-export returns JSON. Self-deletion removes pilot events, session and its
  mastery contributions, preserving other learning evidence and recomputing state.
- Data expires after 90 days. Authenticated reads hide expired records; the
  supervised maintenance worker's independent `math_pilot_maintenance` schedule
  removes up to 500 expired sessions per cycle. It also creates at most one
  private in-app reminder per due session, respecting learning-intervention
  notification preferences; no email or WhatsApp is sent. Deploy and monitor that
  worker. Backup retention needs its own policy;
  this operation does not erase historical backups or already downloaded exports.
- A 100-step session cap bounds repeated helped attempts. No automatic fail/pass
  label, credential, course completion or high-stakes eligibility decision is made.

Two diagnostic items yield a **possible** layers/equal-groups issue or uncertainty,
not a diagnosis. The inherited mastery confidence is a heuristic, not a calibrated
probability. Scores of 0/2, 1/2 and 2/2 are limited evidence; they do not establish
causal learning improvement, permanent mastery or readiness for certification.

## Customer value and advocacy

The intended value is an understandable activity for learners and inspectable
evidence for teachers. Customers get a public discovery URL worth trying with
someone else, rather than being forced to advertise. Sharing uses the browser's
share sheet or copies a fixed public URL; no learner ID, score, referral identity,
private note or class information is embedded. No contacts are uploaded, messages
automatically sent, rewards promised, or access withheld for declining to share.

Existing cohort referrals and public course banners remain available. Tracked
advocacy attribution, referral payouts and causal customer-growth claims are not
new features in this slice. Measure voluntary recommendation and repeat teacher
use in a pilot; do not present fabricated testimonials or simulated results as
customer outcomes.

## Local demonstration

`scripts/seed_saas_demo.py --seed --serve --port 8027` includes
`seed_math_pilot_demo.py`. That seeder refuses non-demo/non-SQLite databases.
It creates `DEMO: Volume discovery pilot`, with **synthetic local approval only**:

- `campus-student-0@example.org`: fresh attempt.
- `campus-student-1@example.org`: layers support awaiting teacher review.
- `campus-student-2@example.org`: retention ready (explicit synthetic time travel).
- `campus-teacher@example.org`: review/evidence view.

Existing passwords remain in the local-only `.local/saas-demo/campus-role-logins.json`.
They are not included here or in source distributions. Repeated seeding preserves
existing attempts. Demo approvals must never be copied into a real school.

Start the frontend with `VITE_DEV_PORT=3027` and
`VITE_PROXY_TARGET=http://127.0.0.1:8027`. Local preview binds loopback only.

## Launch gates and evaluation

Before a real pilot: educator review/grade selection; school/parent arrangements;
shared-device sign-out and device/browser acceptance; private course provisioning;
PostgreSQL migration and concurrent-submit checks; maintenance, backup/restore and
deletion monitoring; teacher support plan. Offline answer sync is not implemented
for this pilot; uncertain online retries retain their request key until reload.

For outcome evaluation, predefine a comparison with a fixed sequence and suitable
learner/school-level assignment with appropriate oversight. Preserve independent
transfer/retention tasks, count learners rather than events, and split by learner
and eventually school when evaluating future models. No randomized experiment or
trained adaptive model is enabled by this release. A small feasibility pilot cannot
establish broad efficacy or willingness to pay.

Technical checks and remaining validation evidence are recorded in
`ADAPTIVE_MATH_VALIDATION_2026-09-27.md`.
