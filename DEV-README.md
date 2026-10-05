# Development Environment — SILEOS @ dev.sashainfinity.com

Isolated dev/test stack running the **SILEOS** snapshot
(github.com/Bilalyzr/SILEOS @ `dbaceb5` + dev deployment commit),
alongside production on the same host. Zero shared state with prod.

## URL

**https://dev.sashainfinity.com** (host nginx vhost
`/etc/nginx/sites-enabled/dev.sashainfinity.com` → dev edge `127.0.0.1:4100`,
wildcard cert `*.sashainfinity.com`).

Requires Cloudflare DNS A record: `dev` → `178.236.185.167` (proxied).

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
| Docker project | `sasha-blue`/`sasha-data`/`sasha-edge` | `development` |
| Ports | edge 3200, backend 8010, pg 5432 | edge 4100, backend 8100, streaming 8101, pg 15432 (all loopback) |
| Network | `sasha-net` (172.18.0.0/16) | `development_tutor-network` (172.31.0.0/16) |
| Volumes | `sasha_postgres_data` etc. | `development_postgres_data_sileos` (fresh) — previous dev DB archived in `development_postgres_data` |
| Services | blue/green | backend, runtime-worker, streaming, frontend, nginx, postgres, redis |

## Git layout in this directory

- `development` (current) = SILEOS `main` + dev-only commit
  (ports/subnet/CORS patch) on top
- `main` = original SashaInfinity/Sasha_lms @ `458604c`
- `dev-wip-backup-20260915` = uncommitted WIP from the pre-SILEOS dev tree
- remotes: `origin` (SashaInfinity/Sasha_lms), `sileos` (Bilalyzr/SILEOS)

## Daily commands

```bash
cd /www/wwwroot/sasha_lms/sasha_lms/development
docker compose up -d            # start
docker compose down             # stop (volumes persist)
docker compose logs -f backend
docker compose build && docker compose up -d   # after pulling code changes
git pull sileos main            # fetch upstream SILEOS snapshot
```

Backend runs uvicorn `--reload` — code edits hot-reload via bind mount;
rebuild only for dependency changes. Frontend is baked at build time
(VITE_API_URL=https://dev.sashainfinity.com/api/v1) — rebuild the image
after pulling frontend changes.

## Known dev-only limitations

- **Payments**: Razorpay keys are placeholders — checkout untestable.
- **Email**: no SMTP credentials validated for dev; mail may fail quietly.
- **YouTube cookies / Bunny / Firebase / Edgyy / Jitsi / code-judge**:
  unset or placeholder — those features degrade.
- `code-judge-worker` is opt-in via compose profile `coding`.

## Files changed vs SILEOS upstream (on purpose)

1. `.env` — fresh dev secrets, dev domain, `ENVIRONMENT=development`
2. `docker-compose.yml` — ports 8100/8101/4100/15432 (loopback), subnet
   172.31, volumes renamed to `*_sileos` so the archived pre-SILEOS dev
   DB is never touched
3. `nginx/conf.d/default.conf` — `dev.sashainfinity.com` added to the
   edge CORS origin regex
4. This file.
