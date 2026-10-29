# Development Environment — SILEOS @ dev.sashainfinity.com

Isolated dev/test stack running the **SILEOS** snapshot
(github.com/Bilalyzr/SILEOS), alongside production on the same host.
Zero shared state with prod.

Site root: `/www/wwwroot/sileos-dev` — moved 2026-10-19 out of the LMS tree
(was `/www/wwwroot/sasha_lms/sasha_lms/development`) so this checkout no longer
lives inside any production deployment path.

Server-local compose wiring lives in the gitignored `.env`
(`COMPOSE_PROJECT_NAME=development` pins the stack to its volumes/network
regardless of directory; `COMPOSE_FILE` appends `docker-compose.server.yml`
last, which strips upstream's extra loopback ports 3100/8000 — on this VPS
those belong to the PRODUCTION LMS containers and would collide). Plain
`docker compose` commands from this directory are safe.

## URL

**https://sileos.sashainfinity.com** and **https://dev.sashainfinity.com**
(host nginx vhost `/etc/nginx/sites-enabled/sashainfinity-sileos.conf`
→ dev edge `127.0.0.1:4100`, cert `/etc/letsencrypt/live/sashainfinity.com/`).
DNS is live on the current VPS (209.182.233.86, Cloudflare-proxied).

Local-only fallbacks: frontend `http://localhost:4000`, edge `http://localhost:4100`,
backend `http://localhost:8100`, streaming `http://localhost:8101`,
postgres `127.0.0.1:15432`.

## Admin login

- Email: `admin@dev.sashainfinity.com`
- Password: `DevAdmin#2026` (from `.env` — dev only, never prod)
- 2FA is mandatory for admins. The fresh-DB admin is NOT TOTP-enrolled
  yet — enroll on first login.

## Isolation from production

| Resource | Production | This dev stack |
|---|---|---|
| Docker project | `sasha_lms` | `development` |
| Ports | edge 3100, backend 8000, streaming 8001, pg 5432 | edge 4100, backend 8100, streaming 8101, pg 15432 (all loopback) |
| Network | `sasha_lms_tutor-network` | `development_tutor-network` (172.31.0.0/16) |
| Volumes | `sasha_lms_postgres_data` etc. | `development_postgres_data_sileos` (fresh) — previous dev DB archived in `development_postgres_data` |
| Services | backend, frontend, nginx, postgres, redis, streaming | backend, recording-worker, streaming, frontend, nginx, postgres, redis |

Schema changes apply via backend startup (`create_all`) — this deployment
keeps no `alembic_version` table; upstream alembic files are reference only.

## Git layout in this directory

- `development` (current) = SILEOS `development` merged with `origin/main`
  (fast-forwarded 2026-10-19 to f95217d "Sileos Sunrise" design system)
- `main` = original SashaInfinity/Sasha_lms @ `458604c` (local history ref)
- `dev-wip-backup-20260915` = uncommitted WIP from the pre-SILEOS dev tree
- remote: `origin` = **github.com/Bilalyzr/SILEOS** — the ONE repo all
  pulls and pushes go through (renamed from `sileos` 2026-10-19; no other
  remotes). Upstream also carries `fix/student-admin-issues`.
- push credentials: repo-local helper `!gh auth git-credential` (gh account
  ShailogTech). NOTE: ShailogTech currently has pull-only access to
  Bilalyzr/SILEOS — pushing from this server requires adding it as a
  collaborator (or providing a Bilalyzr token); until then push from your
  own machine.

## Daily commands

```bash
cd /www/wwwroot/sileos-dev
docker compose up -d            # start
docker compose down             # stop (volumes persist)
docker compose logs -f backend
docker compose build && docker compose up -d   # after pulling code changes
git pull origin main            # absorb upstream SILEOS main into development
```

Backend runs uvicorn with 4 workers and NO `--reload` (set in
`docker-compose.server.yml`, 2026-10-29 perf fix — a single reload process
serialised every page's parallel API calls). Code is still bind-mounted, so
after editing backend code run `docker compose restart backend`; rebuild only
for dependency changes. Worker count: `UVICORN_WORKERS` in `.env` (default 4). Frontend is baked at build time
(VITE_API_URL=https://dev.sashainfinity.com/api/v1) — rebuild the image
after pulling frontend changes. Same for `streaming-service` (code baked
into the image; only the yt-dlp cache is mounted).

**Frontend deploy trap (fixed 2026-10-19):** upstream's compose bind-mounts
the host's `frontend/dist` over the image's dist. A stale Sep-26 build in
that folder silently masked every image rebuild — the site kept serving
September code no matter what was deployed. `docker-compose.server.yml`
now overrides the frontend volumes to none (image is the source of truth);
the stale folder is quarantined as `frontend/dist.stale-sep26`. Deploying
UI changes = `docker compose build frontend && docker compose up -d
frontend && docker compose restart nginx` (the edge caches container IPs).

## Known dev-only limitations

- **Payments**: Razorpay keys are placeholders — checkout untestable.
- **Email**: no SMTP credentials validated for dev; mail may fail quietly.
- **YouTube cookies / Bunny / Firebase / Edgyy / Jitsi / code-judge**:
  unset or placeholder — those features degrade.
- `code-judge-worker` is opt-in via compose profile `coding`.

## Files changed vs SILEOS upstream (on purpose, all server-local)

1. `.env` — fresh dev secrets, dev domain, `ENVIRONMENT=development`,
   `COMPOSE_PROJECT_NAME`/`COMPOSE_FILE` wiring
2. `docker-compose.server.yml` (untracked) — strips the upstream loopback
   ports 3100/8000 that collide with the prod LMS on this VPS
3. This file — server-specific deployment doc (upstream copy is stale;
   local modification kept deliberately)
