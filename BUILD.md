# BUILD MANUAL — SashaInfinity LMS

For the September 2026 runtime release, start with [the production runtime runbook](docs/PRODUCTION_RUNTIME.md) and [release status](docs/SAAS_RELEASE_2026-09-14.md). It adds Alembic head `0050`, a separate maintenance worker, admin MFA enrollment and explicit staging acceptance gates. Older commands below are not a production sign-off.

Stack: React 18 + Vite frontend, FastAPI backend, PostgreSQL 15, Redis 7, yt-dlp streaming service, Nginx.

---

## 0. Prerequisites

| Tool | Min version | Check |
|---|---|---|
| Docker | 20.10 | `docker --version` |
| Docker Compose | 1.29 / v2 | `docker-compose --version` |
| Node.js | 18 | `node -v` (only for host-side frontend build) |
| Python | 3.11 | `python3 -V` (only for running backend outside Docker) |
| git | any | `git --version` |

Disk: ~8 GB free for images + node_modules.

---

## 1. Environment file

Repo has **both** `.env.example` and `env.example`. The scripts copy `.env.example`. Use that one.

```bash
cp .env.example .env
```

Required keys — build starts without them, runtime breaks:

```
POSTGRES_PASSWORD=
REDIS_PASSWORD=
SECRET_KEY=
JWT_SECRET=
RAZORPAY_KEY=
RAZORPAY_SECRET=
ADMIN_PASSWORD=
```

Generate secrets:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

If `SECRET_KEY`/`JWT_SECRET` left at placeholder, `backend/app/core/config.py` auto-generates random ones each boot — every restart invalidates all tokens. Fine for dev, never for prod.

Dev extras (enables `/docs`, `/redoc`, verbose errors):

```
ENVIRONMENT=development
DEBUG=true
```

---

## 2. Local dev build (one command)

```bash
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

Script does: copy `.env`, create `uploads/{courses,profiles,certificates,temp}`, `certificates/{templates,generated}`, `logs/`, `database/backups/`, `docker-compose build`, `docker-compose up -d`, health-check.

Manual equivalent:

```bash
mkdir -p uploads/{courses,profiles,certificates,temp} certificates/{templates,generated} logs database/backups
chmod 755 uploads certificates logs database/backups
docker-compose build
docker-compose up -d
```

`docker-compose.override.yml` auto-merges with base file — dev-only tweaks land automatically. No flag needed.

### Ports after `up`

| Service | Host port |
|---|---|
| nginx (use this) | 3100 |
| backend | 8000 |
| streaming-service | 8001 |
| frontend | **no host mapping** — reach via nginx |
| postgres | internal |
| redis | internal |

App: http://localhost:3100
Health: http://localhost:8000/health
API docs: http://localhost:8000/docs (only if `ENVIRONMENT=development`)

### Production-mode local staging

Use the isolated staging stack for a PostgreSQL migration and container-release
rehearsal without colliding with the development preview:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_staging.ps1
```

This generates unique local secrets beneath `.local/staging/`, validates the
Compose model, builds immutable source images, initializes and migrates the
database, waits for `/health/ready`, and creates a staging administrator. The
application is served on `http://127.0.0.1:3200`. See
`docs/STAGING_DEPLOYMENT.md` for validation-only, coding-worker, operations,
and teardown commands.

---

## 3. Frontend build (host, outside Docker)

```bash
cd frontend
npm install --legacy-peer-deps     # peer conflicts exist; flag is required
npm run build                      # Vite build to dist/
```

Other targets:

```bash
npm run dev          # Vite dev server :3000, proxies /api/v1 -> backend:8000
npm run lint         # ESLint, --max-warnings 0 (any warning fails)
npm run type-check   # tsc --noEmit
npm run test         # Vitest — config + setup exist, no tests written yet
```

Vite config is `frontend/vite.config.js` (JS, not TS). Aliases: `@`, `@/components`, `@/pages`, `@/hooks`, `@/utils`, `@/types`, `@/store`, `@/api`, `@/assets`, `@/styles`.

Run `lint` and `type-check` before committing — CI-equivalent gate.

---

## 4. Backend build/run (host, outside Docker)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Needs Postgres + Redis reachable per `.env`. Start just those:

```bash
docker-compose up -d postgres redis
```

Real entry point is `app/main.py`. The `main_simple.py` / `main_test.py` / `main_email_test.py` / `main_frontend_integration.py` / `main_payment_test.py` variants are experiments — editing them changes nothing in production.

Run the backend regression suite from the workspace root with the project virtual
environment (or from the backend container):

```bash
python -m pytest backend/tests
# Docker equivalent
docker-compose exec backend python -m pytest tests
```

The suite includes API, authorization, accounting, migration, vertical, and
security regressions. Treat any failure as a release blocker.

---

## 5. Database

SQLAlchemy models in `backend/app/models/` remain the schema source of truth.
Alembic migrations in `backend/migrations/versions/` upgrade existing databases;
`init_db()` in `app/core/database.py` still creates tables for a completely fresh
development database. Before deploying an existing environment, apply and verify
the migration head:

```bash
docker-compose exec backend python -m alembic upgrade head
docker-compose exec backend python -m alembic current
```

Do not rely on `create_all()` to alter an existing table. Every model change that
affects persisted schema needs a new, idempotent Alembic revision. Legacy one-off
SQL migrations remain under `backend/migrations/` for historical installs only;
apply them manually only when their accompanying migration notes explicitly say
the target deployment needs one:

```bash
docker-compose exec -T postgres psql -U tutor -d tutor_lms < backend/migrations/add_coupons_tables.sql
```

Shell in:

```bash
docker-compose exec postgres psql -U tutor -d tutor_lms
```

---

## 6. Admin user

Four equivalent scripts — pick one, after containers are up:

```bash
./create_admin.sh
# or
docker-compose exec backend python seed_admin_simple.py
docker-compose exec backend python seed_admin.py
docker-compose exec backend python create_admin.py
```

Credentials read from `ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_FIRST_NAME`, `ADMIN_LAST_NAME`. Defaults live in `docker-compose.yml`.

---

## 7. Production build

Two paths. Pick by which compose file you deploy.

### 7a. Single-container production image

```bash
./build-production.sh
docker-compose -f docker-compose.production.yml up -d
docker-compose -f docker-compose.production.yml logs -f
```

`build-production.sh` does, in order:
1. verify docker + docker-compose present
2. `docker-compose -f docker-compose.production.yml down --remove-orphans`
3. `docker system prune -f` and `docker image prune -f` — **removes all unused images and build cache on the host, not just this project's.** Check nothing else on the box depends on dangling images before running.
4. `cd frontend && npm install --legacy-peer-deps && npm run build`
5. writes a default `.env.production` if missing (with placeholder secrets — edit it)
6. `docker-compose -f docker-compose.production.yml build --no-cache`

It builds only. Bring up separately with the `up -d` above.

### 7b. Server-side redeploy of the multi-container stack

```bash
./deploy-production.sh
```

Does: `cd /www/wwwroot/sasha_lms/sasha_lms/sasha_lms`, `git pull devesh main`, ensure `.env`, `docker-compose down`, `docker-compose up -d --build`, sleep 30, `ps`, health checks on :8000, :3000, :3100.

Hardcoded path and `devesh` remote — will fail on a machine without both.

### Compose file map

| File | Role |
|---|---|
| `docker-compose.yml` | base, local dev |
| `docker-compose.override.yml` | auto-merged into base locally |
| `docker-compose.prod.yml` | production stack variant |
| `docker-compose.production.yml` | production stack used by `build-production.sh` |
| `docker-compose.security.yml` | hardened overlay, applied by `deploy_security.sh` |

Confirm which file is authoritative for the target environment before editing any of them.

---

## 8. Streaming service

Separate FastAPI app, `streaming-service/video_streaming.py`, port 8001. Built by the same `docker-compose build`. Standalone deploy:

```bash
./deploy_streaming.sh
```

Needs `youtube_cookies.txt` next to the app to resolve unlisted YouTube videos. Its CORS is `allow_origins=["*"]` and it has **no auth of its own** — backend must gate access before handing a client to :8001.

---

## 9. Static mounts

| Host dir | Backend path | Nginx path | Public URL |
|---|---|---|---|
| `./uploads` | `/app/uploads` | `/var/www/uploads` | `/uploads` |
| `./certificates` | `/app/certificates` | `/var/www/certificates` | `/certificate-files` |

Bind-mounted, so both containers need the dirs to exist before `up` or the mount creates them root-owned and the backend can't write.

---

## 10. Daily commands

```bash
docker-compose up -d
docker-compose down
docker-compose logs -f backend
docker-compose restart backend
docker-compose exec backend bash
docker-compose exec frontend sh
docker-compose ps
```

---

## 11. Build failures — first checks

| Symptom | Cause | Fix |
|---|---|---|
| `npm install` peer dep error | React 18 + Radix peer ranges | add `--legacy-peer-deps` |
| `npm run lint` fails on warnings | `--max-warnings 0` | fix warning, or it stays red |
| Backend 500 on boot | missing `.env` key | diff `.env` against `.env.example` |
| Login breaks after restart | placeholder `SECRET_KEY`/`JWT_SECRET` regenerating | set real values |
| Frontend not on :3000 | no host port mapping in compose | use nginx :3100 |
| `/docs` 404 | `ENVIRONMENT=production` | set `ENVIRONMENT=development` |
| CORS blocked from new origin | strict allowlist in **two** places | update `CORS_ORIGINS`/`ALLOWED_HOSTS` in both `docker-compose.yml` and `config.py` |
| Upload write permission denied | root-owned bind mount | `chown`/`chmod 755 uploads certificates` on host |
| Chunked upload 404 | mounted at `/upload/chunked`, not `/api/v1`, and imported conditionally | check backend startup logs for the import failure |
