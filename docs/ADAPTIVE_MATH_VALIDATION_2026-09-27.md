# Adaptive mathematics pilot validation — 27 September 2026

## Verified locally

- **68 targeted backend tests passed**: math pilot (13), existing planner,
  learning signals, mastery and production runtime. This is not a full-backend run.
- **499 frontend tests passed across 90 files**, including five new pilot UI tests.
- Frontend TypeScript checking and lint passed.
- Production frontend build passed (3502 modules); lab build validated 59 labs
  and 143 files. Existing oversized-chunk, mixed-import and old browser-data
  warnings remain; these are not claims of load readiness.
- Migration 0052 tested for reentrant creation; runtime test rehearsed upgrade
  from stamped 0049 through head, repeated upgrade, downgrade and upgrade on
  scratch SQLite. PostgreSQL migration/concurrency remains a staging gate.
- Local demo seeded successfully with fresh, needs-support and retention-due
  examples. Backend loopback port 8027 and frontend port 3027 started successfully.
- Public `/discover/volume` opened in the browser. Slider change from 2 to 4
  layers changed the visible/accessible count from 12 to 24 cubes. Screenshot
  inspection caught and corrected heading contrast and cube-face geometry.
- Student and instructor forms were tested with component tests and API tests;
  their complete authenticated browser journeys were not manually verified.

## Test coverage highlights

Educator approval and course authorization; absent/revoked enrollment; private
export/delete; stale tabs; matching retries and conflicting UUID reuse;
server-owned answer keys and integer bounds; helped steps do not award mastery;
independent grading; no early retention attempt; no repeated transfer award;
teacher overrides only before transfer; notification opt-out and deduplication;
data expiration; deletion removes its own evidence/reminder and preserves other
evidence; unrelated mastery remains intact. API timestamps explicitly carry UTC
even when using SQLite.

## Remaining gates

Educator and grade/language suitability; school/parent arrangements; independent
privacy review; accessible/mobile and shared-device acceptance; PostgreSQL and
Redis staging; real worker execution/recovery; backups and deletion retention;
concurrent multi-process submissions; realistic sustained load; controlled
classroom feasibility and outcome evaluation.

This release did not deploy production, alter live payments, publish messages,
send customer referrals, or merge/push Git. The existing release ZIP and release
branch were left untouched; current edits are in the working source tree.

The local demo disables background jobs/providers deliberately. Automated expiry
and reminders are regression-tested, but do not claim a live worker has processed
the synthetic demo. Start the supervised worker only in an appropriately configured
staging environment as described in the production runtime guide.
