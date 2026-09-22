# Live Classes — Phase-0 verified deviations (repo wins)

These override the owner brief where they conflict. Every implementer must
honor them.

1. **Integer PKs/FKs**, not UUID — matches users/courses/lessons/enrollments.
   `jti` (varchar 64) and `room_name` stay opaque strings; no UUID columns.
2. **No response envelope.** Use Pydantic `response_model` per endpoint (the
   repo's modern style, e.g. memberships/bundles routers). Never invent
   `{success,data}` wrappers; the axios `apiRequest<T>` helper tolerates plain
   payloads.
3. **Roles**: guard with the existing AuthService dependencies —
   `require_instructor` (instructor+admin), `require_admin` (admin+superadmin),
   `get_current_active_user`; role strings student/instructor/admin/superadmin/
   spoc/company/company_manager. "Assigned instructor" checks compare
   `live_class.instructor_id == current_user.id` OR admin roles.
4. **No `env/` directory.** Example env committed at `deploy/.env.live.example`;
   real file `deploy/.env.live` (gitignored); compose.live.yml uses
   `env_file: .env.live` relative to deploy/. Backend reads the same variables
   from its normal settings (config.py Fields, env-injected; production
   fail-fast for JITSI_JWT_SECRET and INTERNAL_TOKEN when ENVIRONMENT=production
   via a startup check, NOT import-time crash in dev/tests).
5. **Reminders/scheduler**: no APScheduler. A dedicated asyncio loop in the
   lifespan following app/services/reconciliation.py's pattern (dedicated
   advisory-lock connection on Postgres, per-item fault isolation, idempotency
   via Redis keys `live:reminder:{class_id}` / `live:golive:{class_id}` with
   DB-backed fallback when Redis is mocked).
6. **SSE**: add `sse-starlette` to requirements. Redis pub/sub via
   app/core/redis.py's async client; when MockRedis is active (tests/dev), the
   SSE endpoint falls back to short-poll semantics (yield current snapshot,
   heartbeat comments) so tests can assert payload shape without a broker.
7. **ICS**: hand-rolled minimal VCALENDAR/VEVENT (UTC, escaped text) — no new
   dependency.
8. **Flutter**: package `jitsi_meet_flutter_sdk` (official current), not the
   discontinued `jitsi_meet`. No Flutter toolchain on the build machine and no
   Flutter CI gate — code + tests are authored to convention and must be
   compiled/run by the owner; recorded as a known limitation.
9. **Alembic**: initialize under backend/ (alembic.ini + alembic/), env.py
   wired to app models metadata + DATABASE_URL. Baseline = `stamp head` after
   an initial empty-baseline revision documenting that pre-existing tables are
   created by init_db()/manual SQL. One real migration adds the live tables
   with a working downgrade. init_db() will also create the tables from models
   (create_all is additive/idempotent) — acceptable dual-path during
   transition, documented in docs/LIVE_CLASSES.md.
10. **CI**: eslint has no config repo-wide and tsc is advisory with 391
    pre-existing errors — the binding gates for this feature are pytest,
    vitest (first real suites land here), shellcheck, plus a new gitleaks step.
11. **hls.js missing from package.json** is a pre-existing latent issue —
    NOT fixed here (additive-only rule), noted for the owner.
12. **FCM web push does not exist**; backend firebase_admin.messaging helpers
    exist. Reminder emails ship now; FCM broadcast is wired through the
    existing backend helper with a no-op guard when Firebase is unconfigured,
    and mobile deep-link handling rides flutter_app's existing FCM setup if
    present (verified during the mobile task; degraded gracefully otherwise).
13. **Phase-1 smoke on the VPS cannot run from the build machine** — the
    deliverable is configs + `deploy/scripts/smoke_jitsi.sh` + a runbook
    checklist the owner executes on the server (DNS live.sashainfinity.com
    grey-cloud first, then orange after WebRTC verified).
14. **Jitsi JWT `exp` gained a now-floor**: the spec's `scheduled_end + 30min`
    is kept as the grace window, but the minted expiry is now
    `max(now + 15min, scheduled_end + 30min)`
    (`app/services/jitsi_token_service.token_expiry_for`). The spec formula
    alone mints an ALREADY-EXPIRED token for any class past its scheduled
    slot — Jitsi rejects such a token outright, so a class running overtime
    became unjoinable for late arrivals and for anyone reconnecting after a
    drop, including the instructor still in the room. The floor only ever
    raises the expiry, so a class ending in the future is unaffected
    (`scheduled_end + 30min` is already the later value and wins unchanged);
    it never extends a normal class's window. The join-token endpoint now
    derives its advertised `expires_in` from the same helper instead of a
    hardcoded 900s, which had under-reported the real lifetime and pushed
    clients into needless re-requests against their 5/min rate limit.
