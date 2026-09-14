# Zero-Downtime Deployment

Blue-green deployment for SashaInfinity LMS. Users keep being served throughout a
release; if anything fails, the previous version keeps running and the deploy
rolls itself back.

---

## 1. How it works

Three independent Docker Compose stacks:

```
                        internet
                            │
              host nginx / Cloudflare  (terminates TLS)
                            │
                            ▼
   ┌────────────────────────────────────────────────────┐
   │  EDGE          sasha-edge   (nginx, port 3200)     │  never recreated
   │                                                    │
   │   reads  nginx/active/active.conf ────┐            │
   └───────────────────────────────────────┼────────────┘
                                           │
              ┌────────────────────────────┴─────────────┐
              ▼                                          ▼
   ┌───────────────────────┐                 ┌───────────────────────┐
   │  APP: blue            │                 │  APP: green           │
   │   backend-blue:8000   │                 │   backend-green:8000  │
   │   frontend-blue:3000  │   ← one is      │   frontend-green:3000 │
   │   streaming-blue:8001 │     live, the   │   streaming-green:8001│
   └───────────┬───────────┘     other idle  └───────────┬───────────┘
               └───────────────────┬──────────────────────┘
                                   ▼
   ┌────────────────────────────────────────────────────┐
   │  DATA    sasha-postgres · sasha-redis              │  never recreated
   └────────────────────────────────────────────────────┘

         all four on the shared docker network "sasha-net"
```

**Only the app tier is blue-green.** Postgres and Redis hold the state and are
started once and left alone — cycling them on every release would cause a
connection drop on every release, which is the downtime we are removing. The edge
proxy is likewise never recreated, because recreating the proxy would drop every
in-flight connection.

### The switch

`deploy/nginx/active/active.conf` is the only thing that decides which colour is
live:

```nginx
set $active_color "blue";
set $up_backend   "backend-blue:8000";
```

`switch.sh` rewrites that file and sends nginx a reload. On reload nginx starts a
new generation of workers using the new config and tells the old generation to
finish what it is already doing. Old workers stop accepting new connections but
complete in-flight requests — long video range requests, slow uploads. The
listening socket is never closed, so nothing is refused. **No connection is
dropped, and the switch itself is instant.**

Two details make this work, and both are deliberate:

- **Upstreams are referenced through variables** (`proxy_pass http://$up_backend`)
  with `resolver 127.0.0.11` (docker's DNS). With a conventional `upstream {}`
  block, nginx resolves hostnames once at startup and treats an unresolvable
  host as a fatal config error — so the edge would refuse to boot whenever the
  idle colour did not exist. Variables are re-resolved per request instead.
- **`nginx/active` is mounted as a directory, not a file.** `switch.sh` writes a
  temp file and renames it, which is atomic, so nginx can never read a
  half-written config. A file-level bind mount is bound to an inode and would
  keep showing the old contents forever after a rename.

### A release, step by step

| # | Step | User impact if it fails |
|---|------|------------------------|
| 1 | Preflight — validate config, env, files | none, nothing started |
| 2 | Ensure network / data / edge exist | none |
| 3 | Build or pull images | none, live colour still serving |
| 4 | Run database migrations | none, aborts before any traffic change |
| 5 | Start the **idle** colour | none, it receives no traffic |
| 6 | **Health gate** on the idle colour | none — deploy aborts, slot torn down |
| 7 | **Switch** — nginx reload | this is the only user-visible moment |
| 8 | Verify end-to-end through the edge | auto-rollback to the previous colour |
| 9 | Drain, then stop the old colour | none |
| 10 | Prune images past the retention window | none |

Everything up to step 6 is invisible. From step 7 on, a failure switches traffic
back to the colour that was serving moments earlier — which is still running, so
recovery is one nginx reload, not a rebuild.

---

## 2. First-time setup

### Prerequisites

- Docker with the Compose v2 plugin (the legacy `docker-compose` binary also works)
- The deploy user in the `docker` group
- The repo checked out on the server
- A populated repo-root `.env`

### Step 1 — configure

```bash
cd /path/to/Sasha_lms
cp deploy/.env.deploy.example deploy/.env.deploy
$EDITOR deploy/.env.deploy
```

**Check the volume names before anything else.** The data stack pins volume names
so it *adopts* the volumes the original root `docker-compose.yml` created, rather
than starting with an empty database:

```bash
docker volume ls | grep -E 'postgres|redis'
```

Set `POSTGRES_VOLUME` / `REDIS_VOLUME` in `deploy/.env.deploy` to match what you
see. Getting this wrong gives you a new, empty Postgres.

If you use Firebase Google sign-in, drop the service-account JSON in:

```bash
cp /secure/path/firebase-service-account.json deploy/secrets/
```

### Step 2 — baseline the migration ledger

This repo has no Alembic; migrations are hand-written SQL files that were applied
manually. `migrate.sh` adds the missing ledger, but it has to be told that the
existing files are already applied:

```bash
docker compose -f deploy/docker-compose.data.yml up -d      # if not already running
deploy/scripts/migrate.sh --baseline
```

**Run this exactly once, on a database that is already up to date.** Skipping it
means the first pipeline deploy re-runs every historical migration against your
live database.

Verify:

```bash
deploy/scripts/migrate.sh --status     # everything should read "applied"
```

### Step 3 — first deploy, alongside the existing stack

The edge defaults to port **3200**, not the 3100 the current stack uses, so you
can bring the whole thing up and test it without touching production:

```bash
deploy/scripts/deploy.sh --dry-run     # review the plan
deploy/scripts/deploy.sh               # build and deploy to the idle colour
deploy/scripts/status.sh
```

Test it directly:

```bash
curl http://127.0.0.1:3200/health
curl http://127.0.0.1:3200/health/ready
curl http://127.0.0.1:3200/__edge/active
```

### Step 4 — cut over

Once you are satisfied, point the host's nginx (aaPanel) or the Cloudflare origin
at port 3200 and stop the old stack:

```bash
docker compose down          # the OLD root-level stack
```

Alternatively, take 3100 over directly — stop the old stack first, then set
`EDGE_HTTP_PORT=3100` in `deploy/.env.deploy` and run
`docker compose -f deploy/docker-compose.edge.yml up -d`.

> The old root `docker-compose.yml`, `deploy-production.sh` and
> `build-production.sh` are left untouched so you have a fallback during the
> transition. Delete them once you have deployed this way a few times —
> `deploy-production.sh` runs `docker-compose down` before building, which is
> exactly the downtime this replaces.

---

## 3. Everyday use

```bash
# Deploy the current commit (builds on the server)
deploy/scripts/deploy.sh

# Deploy an image CI already built and pushed
deploy/scripts/deploy.sh --tag v1.4.2 --pull

# See what would happen, change nothing
deploy/scripts/deploy.sh --dry-run

# Where are we?
deploy/scripts/status.sh
deploy/scripts/status.sh --history 30

# Undo the last release
deploy/scripts/rollback.sh

# Go back to a specific release
deploy/scripts/rollback.sh --tag v1.4.1

# Move traffic by hand (both colours must already be running)
deploy/scripts/switch.sh green

# Check a colour without deploying
deploy/scripts/health-check.sh --color green

# Maintenance page
deploy/scripts/maintenance-on.sh --reason "coupon table migration"
deploy/scripts/maintenance-off.sh

# Migrations
deploy/scripts/migrate.sh --status
deploy/scripts/migrate.sh --dry-run
deploy/scripts/migrate.sh

# Reclaim disk (keeps the rollback path intact)
deploy/scripts/cleanup.sh --dry-run
deploy/scripts/cleanup.sh
```

All scripts are idempotent, log to `logs/deploy/`, and exit `0` on success, `1` on
failure, `2` on bad arguments.

---

## 4. Health checks

Three endpoints, with distinct jobs:

| Endpoint | Checks | Used by |
|----------|--------|---------|
| `GET /health` | Process is answering HTTP | Docker HEALTHCHECK, monitoring |
| `GET /health/ready` | **Postgres reachable**; Redis reported | the deploy gate |
| `GET /health/version` | Which release and colour is serving | post-switch verification |

```json
// GET /health
{ "status": "healthy", "service": "sashainfinity-lms-backend",
  "version": "1.0.0", "release": "a1b2c3d", "environment": "production" }

// GET /health/ready  → 200 when servable, 503 when not
{ "status": "healthy", "ready": true, "release": "a1b2c3d",
  "checks": { "database": "ok", "redis": "ok" } }
```

**The gate uses `/health/ready`, not `/health`.** A container can serve `/health`
perfectly while being unable to reach the database — it would sail through a
shallow gate and take the site down the moment traffic switched.

Postgres is required; Redis is *degradable*. `RedisClient` falls back to an
in-process mock and the app keeps working with weaker rate limiting and caching,
so a Redis outage reports `"degraded": ["redis"]` and logs a warning rather than
blocking a release.

The gate also requires **`HEALTH_RETRIES` consecutive passes** (default 3), not
one. A single success can come from a worker that is about to die — a boot that
succeeded before lazily opening its DB pool, an OOM about to land. A failure
resets the streak. Container restart counts are re-checked on every attempt so a
crash loop fails fast instead of burning the whole timeout.

Tuning lives in `deploy/.env.deploy`: `HEALTH_TIMEOUT`, `HEALTH_INTERVAL`,
`HEALTH_RETRIES`, `EDGE_VERIFY_TIMEOUT`.

---

## 5. Rollback

Automatic, on any of:

- container startup failure
- health gate failure
- deploy timeout
- migration failure
- any docker error, or an unexpected non-zero exit anywhere in `deploy.sh`

A single `EXIT` trap covers every path — `die`, `set -e`, and Ctrl-C — so there is
no failure mode that leaves the deploy half-finished with nothing watching.

**Before the switch** (the common case): traffic never moved. The failed slot is
torn down and the live colour never notices.

**After the switch:** traffic goes back to the colour that was serving moments
ago. Because `deploy.sh` *stops* the old colour instead of removing it
(`KEEP_PREVIOUS=true`), those containers are still there, so this takes seconds —
no pull, no build.

The failed colour is then **stopped but kept**, because its containers and logs
are the evidence for why it failed. `docker logs` works on a stopped container and
would not on a removed one:

```bash
docker logs --tail 200 sasha-backend-green
cat logs/deploy/deploy-<timestamp>.log
```

Rolling back also health-gates the destination — a rollback to something equally
broken just extends the outage. If that gate fails, traffic is left where it is
and you get a clear message. `--force` overrides it, for when a degraded previous
release is genuinely better than the current one.

### If automatic rollback fails

```bash
deploy/scripts/status.sh                          # establish the facts
deploy/scripts/rollback.sh --to blue --force      # force traffic to a colour
deploy/scripts/switch.sh blue --force             # or just move traffic
deploy/scripts/maintenance-on.sh --reason "incident"   # buy time
```

---

## 6. Maintenance mode

**Normal deploys never show a maintenance page** — that is the entire point of
blue-green. This is for the cases blue-green genuinely cannot cover: a
*destructive* migration where old and new code cannot both run against the same
schema (dropping or renaming a column, splitting a table).

```bash
deploy/scripts/maintenance-on.sh --reason "splitting the enrollments table"
deploy/scripts/deploy.sh
deploy/scripts/maintenance-off.sh
```

Implementation: the script creates `deploy/nginx/maintenance/ON`. The edge tests
for that file's existence on **every request**:

```nginx
if (-f /etc/nginx/maintenance/ON) { set $maintenance 1; }
```

So toggling is instant — no reload, no config rewrite, nothing to get wrong under
pressure. Both scripts verify the result rather than assuming it, and both are
idempotent (safe to call from a cleanup trap; the worst failure mode here is
forgetting to turn it off).

Users get **HTTP 503 with `Retry-After: 600`**, which is the correct signal for
crawlers and CDNs — they come back rather than caching the page or de-indexing
the site. A private status code (461) is used internally so that a genuine 503
from the backend is *not* rewritten into a maintenance page.

`/health` and `/__edge/*` stay reachable during maintenance so monitoring does not
go dark and the deploy scripts keep working.

The page lives at `deploy/nginx/maintenance/__maintenance.html`, is entirely
self-contained (no external fonts or scripts — during maintenance no other origin
is guaranteed reachable), and self-refreshes every 60s.

---

## 7. Migrations

`migrate.sh` runs `backend/migrations/*.sql` in lexicographic order, once each,
tracked in a `_deploy_migrations` table (filename, checksum, timestamp, release).

- Safe to re-run: applied files are skipped.
- A file whose contents changed after being applied is a **hard error**, not a
  silent re-run or a silent skip. Editing an applied migration means environments
  have diverged; add a new file instead.
- On failure the ledger is not updated, so re-running retries that file — and
  `deploy.sh` turns the non-zero exit into an abort with traffic never switched.

Most existing files open their own `BEGIN`/`COMMIT`, so psql is **not** invoked
with `--single-transaction` (that would nest transactions and let the file's own
`COMMIT` end the outer one early). Per-file atomicity is the SQL file's
responsibility — wrap new migrations in `BEGIN`/`COMMIT`, as the existing ones do.

### The ordering constraint worth understanding

Migrations run **before** the new colour starts, and before any traffic switch.
For a window during the deploy, the **old code runs against the new schema**.

- **Additive migrations are safe**: new tables, new nullable columns, new indexes.
- **Destructive migrations are not**: dropping or renaming a column the old code
  still selects will make the *live* colour throw errors before the switch even
  happens. Those need maintenance mode (section 6).

This is inherent to blue-green, not a limitation of these scripts. The
alternative — expand/contract, where every schema change ships as an additive
migration in one release and the cleanup in a later one — is the standard way to
avoid maintenance windows entirely, and is worth adopting for destructive changes.

---

## 8. CI/CD pipeline (self-hosted, fully free)

`.github/workflows/deploy.yml`:

```
push to main ──> quality ──> build (3 images) ──> deploy ──> verify
                  (VPS runner)  (VPS runner)      (VPS runner)  (GitHub-hosted)
```

The **quality/build/deploy jobs run on a self-hosted runner installed on this
VPS** (`deploy/ci/bootstrap-runner.sh`, systemd service `sasha-ci-runner`).
That is what makes the pipeline free: the repo is private, so GitHub-hosted
minutes are quota-limited (2,000/month) and GHCR private storage (500 MB)
cannot hold these images — the local runner needs neither. The **verify** job
stays GitHub-hosted so the public URL is probed from outside the server
(~1 min of quota per deploy).

- **quality** — ESLint, `tsc --noEmit`, Vitest, **backend pytest** (real suite
  in `backend/tests/`, SQLite-based, runs in `/opt/sasha-ci/venv`), streaming
  syntax check, flake8 (errors only), shellcheck on all operational scripts
- **build** — one job per service, built locally on the VPS with the same image
  names the deploy uses; validates images on every PR and warms the docker
  layer cache so deploys are fast
- **deploy** — `deploy/ci/ci-deploy.sh` against the **live compose stack**:
  safety backup (`pg_dump`), ledger migrations (additive-only, against the
  running postgres container — never starts a second one), tags current images
  as `:ci-prev` (rollback point), rebuilds and recreates **only**
  backend/frontend/streaming-service (nginx/postgres/redis untouched),
  health-gates `:3100/health`, auto-restores `:ci-prev` on failure
- **verify** — probe the **public** URL from GitHub's infrastructure, covering
  DNS, Cloudflare, TLS and the host proxy, which a server-local probe cannot
  see

A failing job stops the ones after it, so a bad commit never reaches the
server. A deploy that starts and then fails its health gate is rolled back to
the previous images automatically.

The deploy log is always uploaded as an artifact, including on failure — that
is exactly when you want it.

### No secrets required

The runner is already on the production host; `ci-deploy.sh` reads the
server's own `.env` files. There are no SSH keys, registry tokens or hosts to
configure. (Historic SSH/GHCR secrets from the previous SSH-based pipeline can
be deleted from repository settings.)

### Runner setup (once)

```bash
# registration token (valid 1h):
gh api repos/SashaInfinity/Sasha_lms/actions/runners/registration-token --jq .token
sudo bash deploy/ci/bootstrap-runner.sh <TOKEN>
```

Maintenance: `systemctl status|restart sasha-ci-runner`; decommission with
`/opt/sasha-ci/actions-runner/config.sh --remove`.

The runner executes as root on this single-admin box (it must run docker, read
`.env` and write the deploy checkout). The repo is private — only collaborators
can trigger workflows. Revisit if outside contributors ever get write access.

### Why not `deploy/scripts/deploy.sh` (blue-green) in the pipeline?

The three-tier blue-green system expects its own data tier (`sasha-postgres`),
which is currently **dead** — starting it would place a second postgres on the
live data volume, the exact failure class that destroyed production on
2026-08-15. `ci-deploy.sh` refuses to run if that container is ever up. When
the blue-green tier is repaired, the pipeline can switch back to `deploy.sh`
and regain zero-downtime switches; today it ships short per-service recreate
windows (seconds) behind the health gate.

### Manual runs

`workflow_dispatch` accepts:

- `release_tag` — deploy a specific tag
- `rollback` — restore the last `:ci-prev` images without shell access. This is
  a **separate job** with no dependency on quality or build: during an
  incident, recovery must not be blocked behind a lint job.
- `skip_migrations`

### One thing to know about the quality gate

**ESLint and type-check are advisory by default, and that is a deliberate call
about this repository, not an oversight.**

`npm run type-check` currently reports pre-existing errors — unused imports in
`store/course.ts`, missing `QuizState` members in `store/quiz.ts`, a missing
`dompurify` type declaration — and `npm run lint` runs with `--max-warnings 0`.
Making these blocking today would mean no commit could ever deploy, and the
predictable result is that someone switches the pipeline off entirely.

They still run on every commit and their status appears in the job summary, so
the debt stays visible. Once it is paid down, set the repository variable
`QUALITY_GATE=strict` and they become hard gates. Nothing else changes.

Backend tests, the streaming syntax check and shellcheck (at error severity)
**are** blocking. The Vitest suite is currently empty and runs with
`--passWithNoTests`, so it reports honestly rather than either failing the
build or pretending tests passed — and it starts protecting the pipeline the
moment the first test lands.

---

## 9. Configuration

Two files, layered, both read by `docker compose`:

| File | Contents | Sourced by bash? |
|------|----------|------------------|
| `<repo>/.env` | Application secrets and runtime config | **No** |
| `deploy/.env.deploy` | Deployment knobs (registry, ports, timeouts) | Yes |

The repo `.env` is never sourced by the shell: it legitimately contains values
like `CORS_ORIGINS=["a", "b"]` that are valid for compose's parser but a syntax
error for bash. It is handed to compose via `--env-file`.

`deploy/.env.deploy` **is** sourced, so keep it plain `KEY=value` — no spaces
around `=`, no brackets, no command substitution.

Real environment variables outrank both, which is what lets CI set `RELEASE_TAG`
without editing anything on the server.

Every setting is documented in `deploy/.env.deploy.example`. The ones that matter
most:

| Variable | Default | Notes |
|----------|---------|-------|
| `EDGE_HTTP_PORT` | `3200` | Deliberately not 3100, so this can run alongside the old stack |
| `EDGE_BIND_ADDR` | `127.0.0.1` | Keep loopback if a host nginx terminates TLS |
| `POSTGRES_VOLUME` | `sasha_lms_postgres_data` | **Verify against `docker volume ls`** |
| `HEALTH_TIMEOUT` | `180` | Budget for a colour to become ready |
| `HEALTH_RETRIES` | `3` | Consecutive passes required |
| `DRAIN_SECONDS` | `15` | Grace before stopping the old colour |
| `KEEP_PREVIOUS` | `true` | Keeps rollback near-instant |
| `IMAGE_RETENTION` | `3` | Must be ≥ 2 or you lose rollback |
| `UVICORN_WORKERS` | `2` | Both colours run briefly, so peak RAM is ~2× |

---

## 10. Logging

| What | Where |
|------|-------|
| Per-run deploy log | `logs/deploy/deploy-<timestamp>-<pid>.log` |
| Deploy/switch/rollback history | `deploy/state/history.log` (TSV) |
| Edge access + error logs | `logs/edge-nginx/` |
| Container logs | `docker logs sasha-<service>-<colour>` |

Every script logs deployment start, image version, build status, each health
check attempt, the traffic switch, any rollback, total duration and all errors.
On a failed health gate, the last 60 log lines from every container are captured
into the deploy log while the containers still exist.

The edge access log includes the serving colour and upstream, so you can prove
from the log which release answered a given request:

```
1.2.3.4 - - [30/Jul/2026:11:04:09 +0000] "GET /api/v1/courses HTTP/1.1" 200 4213
  "-" "Mozilla/5.0" "-" color=green upstream=172.19.0.7:8000 rt=0.043 urt=0.041
```

Responses also carry `X-Deploy-Color`. Retention: deploy logs are trimmed after
`LOG_RETENTION_DAYS` (30); container and nginx logs rotate at 20 MB × 5 files.

---

## 11. Troubleshooting

**`deploy.sh` says another deploy is in progress**

```bash
deploy/scripts/status.sh          # shows the lock holder's PID
rm -rf deploy/state/.lock         # only if you are certain it is stale
```

Stale locks from dead processes are detected and cleared automatically.

**nginx and state disagree about the live colour**

`status.sh` flags this. `deploy.sh` repairs it automatically on the next run,
trusting nginx — it is what actually serves traffic.

**Health gate keeps failing**

```bash
docker logs --tail 100 sasha-backend-green
docker exec sasha-backend-green curl -s http://localhost:8000/health/ready
```

Usually the readiness payload names the cause (`"database": "error: ..."`). Note
that `HEALTH_TIMEOUT` needs to cover `init_db()` running at startup on a large
schema.

**Rollback says the images are neither local nor pullable**

`cleanup.sh` protects the live and previous releases, so this normally means
`IMAGE_RETENTION` was set to 1, or something else pruned them. Rebuild instead:

```bash
deploy/scripts/deploy.sh --tag <old-tag> --color blue
```

**Both colours are down**

The edge stays up and its own endpoints keep answering, which is how you tell the
proxy apart from the app tier:

```bash
curl http://127.0.0.1:3200/__edge/health     # edge itself
curl http://127.0.0.1:3200/__edge/active     # which colour it points at
deploy/scripts/deploy.sh --color blue        # redeploy into a specific slot
```

**Uploads or certificates vanished after a deploy**

They shouldn't — both colours bind-mount the same `uploads/` and `certificates/`
host directories, and the edge serves them straight off disk. Check the mounts:

```bash
docker inspect -f '{{json .Mounts}}' sasha-backend-blue | python -m json.tool
```

---

## 12. Files

```
deploy/
├── README.md                       this document
├── .env.deploy.example             every setting, documented
├── docker-compose.data.yml         postgres + redis      (never recycled)
├── docker-compose.edge.yml         nginx edge            (never recycled)
├── docker-compose.app.yml          one colour's app tier (COLOR-parameterised)
├── nginx/
│   ├── nginx.conf                  http-level config, docker resolver
│   ├── conf.d/
│   │   ├── 00-maps.conf            crawler + CORS origin maps
│   │   └── 10-app.conf             routing, maintenance gate
│   ├── snippets/
│   │   └── security-headers.conf   shared so nested locations don't drop CSP
│   ├── active/
│   │   └── active.conf             GENERATED — the live colour
│   └── maintenance/
│       └── __maintenance.html      served by nginx, no upstream needed
├── secrets/                        mounted at /run/secrets (gitignored)
├── state/                          machine-local, gitignored
└── scripts/
    ├── lib.sh                      shared plumbing
    ├── deploy.sh                   the orchestrator
    ├── rollback.sh                 revert to the previous release
    ├── switch.sh                   move traffic between colours
    ├── health-check.sh             the gate
    ├── migrate.sh                  SQL migrations with a ledger
    ├── maintenance-on.sh           show the maintenance page
    ├── maintenance-off.sh          resume normal service
    ├── status.sh                   what is deployed right now
    └── cleanup.sh                  prune without breaking rollback

.github/workflows/deploy.yml        CI/CD pipeline
```

### Deliberate differences from the old root `docker-compose.yml`

The app tier fixes three things that are incompatible with immutable releases:

1. **No `./backend:/app` bind mount.** A release must be exactly the image CI
   built and tested; mounting host source over `/app` makes the deployed code
   depend on whatever happens to be checked out on the server.
2. **No `--reload`.** The uvicorn reloader watches the filesystem, costs memory
   and restarts workers under load. It has no place in production.
3. **No host port publishing for app containers.** Only the edge is reachable
   from outside; the app tier is reachable solely over the docker network.
