# Production runtime and recovery

This release extends the existing SashaInfinity LMS; it does not replace the three business pillars. The runtime worker coordinates existing maintenance handlers, while the API serves requests. Recording/transcription and sandboxed coding remain separate workers.

## Process topology

| Process | Responsibility | Scale boundary |
| --- | --- | --- |
| API replicas | Authenticated HTTP, authoring, learning, admin reporting | Stateless app instances; shared PostgreSQL, Redis and asset storage |
| `app.workers.runtime` | Payments/memberships every 300 seconds; learner reminders and campus maintenance every 60 seconds; Growth billing/follow-ups every 600 seconds | Multiple standby replicas, one Redis scheduler leader; database claims per job |
| Recording worker | Existing recording-to-lesson pipeline | Optional `recording` staging profile; needs real recording/transcription setup |
| Code judge worker | Existing queued coding assessment runner | Optional `coding` staging profile; isolated execution service required |
| Prometheus | Private runtime/HTTP metrics and alert rules | Optional `observability` staging profile; never expose unauthenticated publicly |

Run the maintenance worker from `backend/` with `python -m app.workers.runtime`. Production requires PostgreSQL, Redis and `BACKGROUND_TASK_MODE=worker`. APIs reject production `inline` or `disabled` modes. `inline` is a development-only compatibility mode; `disabled` is used by the isolated showroom. `--allow-local --once` permits explicit development-only SQLite worker tests, not a production substitute.

## Deployment order

1. Back up PostgreSQL and shared files, and prove restore in a separate environment. Never restore over the live database as a test.
2. Set distinct persistent signing secrets, the AI vault encryption key, provider sandbox credentials, HTTPS origins and allowed hosts. Do not rotate encryption keys casually: existing encrypted provider keys would become unreadable.
3. Build the release images with the included Docker ignore rules. Never put private keys in Vite build arguments or commit local environment files.
4. Apply the historical SQL ledger where appropriate, then run `python -m alembic upgrade head` from the new backend image. Current head is `0051`, adding Growth billing and sales workflows after the runtime migration. For a fresh installation, the staging migration service initializes the legacy schema before upgrading Alembic.
5. Start API, runtime worker and required optional workers. The blue/green deploy script now runs Alembic before starting the target and checks its maintenance worker before switching traffic.
6. Verify `/health/ready`, release identity, admin **Operations → Runtime**, role isolation, provider sandbox flows and backup/restore. A green HTTP health check alone is insufficient.

Use `docker-compose.staging.yml` for an isolated local staging installation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_staging.ps1 -ValidateOnly
powershell -ExecutionPolicy Bypass -File scripts/setup_staging.ps1
```

The setup writes secrets only under `.local/staging/`. It does not configure real providers. Optional coding requires `JUDGE0_URL` and its private token; recording requires source recordings and the transcription runtime/model. Mount provisioned Firebase credentials explicitly; they are excluded from source archives and Docker build contexts.

New administrators must enroll MFA before they can log in. After seeding, run `python admin_mfa_enroll.py --email <configured-admin-email>` inside the backend container from a private interactive terminal. It displays a new authenticator setup key and saves it only after a working code is entered. It cannot reset an already-enrolled account or promote another role. Do not redirect its secret to deployment logs. The staging demo default uses `staging-admin@example.org`; reserved `.local` email addresses are rejected by the login validator.

The root development Compose file also starts a maintenance worker. The monolithic `docker-compose.production.yml` includes a separate worker but is a legacy alternative; do not mix it with the blue/green stack or give two PostgreSQL containers the same volume. Its database migrations must be performed before startup. `docker-compose.prod.yml` and older security overlays are not certified by this release; use the staging or blue/green configuration as the deployment reference.

## Execution and retry guarantees

`runtime_jobs` holds the durable schedule; `runtime_runs` holds execution and operator-retry evidence. A conditional database update grants a 120-second lease. Active runs renew it every 20 seconds. Expired runs can be recovered, and an old lease owner cannot acknowledge a new owner's work. Redis leadership uses a random owner token with conditional renewal/deletion.

Failures retry after 30, 60, 120 and 240 seconds; the fifth failed attempt becomes `dead`. Repeated worker interruptions are also bounded. A global admin can queue a failed/dead job again. The retry is audited and does not mean the provider operation succeeded. Unknown job names and non-admin callers are rejected.

Delivery is **at least once**, not exactly once. Existing handlers retain payment idempotency checks, delivery state and PostgreSQL advisory locks. An SMTP or third-party response lost after acceptance can still be ambiguous; reconcile provider evidence before manual re-sends or financial recovery. The runtime schedule is not a generic arbitrary-code/job endpoint.

Admin Runtime also shows grouped payment-webhook, coding, email, WhatsApp and recording statuses, plus last-tested AI provider metadata. A successful maintenance cycle does not imply every queued delivery succeeded. Those detailed queues remain the source of delivery evidence.

## Observability and privacy

Structured request logs contain request ID, route template, method, status, duration, authenticated role and scoped tenant/vertical when supplied by the relevant authorization service. Unscoped requests say `shared`; this is not comprehensive distributed tracing. Bodies, query strings and credentials are not logged by this middleware. Existing application logs need their own retention/access review.

`RUNTIME_METRICS_ENABLED=true` records bounded per-minute Redis counters with a 20-minute TTL and returns a 15-minute window. Redis failure is reported as unavailable, not zero traffic. Prometheus exposes window gauges, not monotonic counters; do not apply `rate()` to these gauges.

The scrape endpoint is `/api/v1/internal/observability/metrics`. It requires a distinct `OBSERVABILITY_TOKEN` of at least 32 characters. Admin login is not a replacement for this token. The existing edge blocks `/api/v1/internal`; scrape backend service DNS from the private network.

For the optional staging Prometheus profile, place that same token alone in `deploy/secrets/metrics-token`, set `OBSERVABILITY_TOKEN` in the local staging environment and start Compose with `--profile observability`. Prometheus binds only `127.0.0.1:9090`. Included alert rules cover missing workers, dead jobs, unavailable metrics and elevated 5xx rates. **Configure an Alertmanager receiver separately**; rule evaluation alone does not send notifications.

`SENTRY_DSN` enables optional error reporting. It is off by default. Request secrets, user context, local variables, breadcrumbs, extra fields and SQL spans are scrubbed; exception messages are replaced. Enable only after an organizational privacy review. `SENTRY_TRACES_SAMPLE_RATE` defaults to 0.05. No Sentry export is enabled in the demo.

## Operations playbook

| Symptom | Check and action |
| --- | --- |
| Unknown/stale worker | Check container logs and `python -m app.workers.runtime --health`; verify DB/Redis reachability and schema head |
| Dead maintenance job | Inspect redacted error code and provider/queue evidence, correct configuration, then use **Queue safe retry** |
| Provider quota or billing failure | Inspect the selected provider endpoint/model and API-specific balance; a chat/coding subscription need not cover every API endpoint |
| Redis down | Scheduler fails closed; restore Redis, then verify leases and backlog. Do not run a second uncoordinated scheduler |
| Recording/coding backlog | Check those dedicated workers and their external execution/transcription dependencies; maintenance worker does not replace them |
| Rollback | Keep additive schema; roll back application traffic only after compatibility review. Old releases without the worker require an explicitly reviewed older deployment procedure |

Execution history is displayed as the latest 100 events but retained in the database. Set a retention/export policy before prolonged high-volume operation. Back up the AI encryption key separately from the database. Rehearse secret rotation, Redis outages, duplicate webhooks, worker termination, object-store recovery and regional outages before accepting a production SLA.

## Capacity evidence

`scripts/validate_saas_release.py` runs a bounded read-only HTTP exercise and a local SQLite backup/restore check. It refuses non-local targets unless explicitly permitted. It is **not** a PostgreSQL, multi-replica, browser, provider or large-consumer certification. A launch gate still needs sustained authenticated tenant-isolation/load tests on the intended infrastructure with an agreed concurrency target, p95 latency, error budget, RPO and RTO.
