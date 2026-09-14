# AGENTS.md

Workspace guidance for ZCode agents working in this repo.
**Read this first**, then consult the in-repo deep-dives when you touch those areas:
`CLAUDE.md` (architecture & gotchas), `BUILD.md` (build/deploy manual),
`STREAMING_SETUP.md` (video), `VIDEO_PLAYER_IMPLEMENTATION.md`, `ADMIN_SETUP.md`.

## What this is

**SashaInfinity LMS** — a learning management system with a React 18 + Vite +
Tailwind frontend, a FastAPI backend, PostgreSQL 15, Redis 7, a standalone
yt-dlp streaming service, and a Flutter mobile app. Live production domain:
`sashainfinity.com`. Indian-market (Razorpay payments; Tamil-language content
in parts).

## Major directories (workspace root)

| Dir | What |
|---|---|
| `backend/` | FastAPI app — entry point is `backend/app/main.py` |
| `frontend/` | React + TS + Vite web app |
| `streaming-service/` | Separate FastAPI app (`video_streaming.py`) on :8001 |
| `flutter_app/` | Flutter mobile app (`sashalms`) |
| `nginx/` | Reverse-proxy config |
| `uploads/`, `certificates/` | Bind-mounted static file dirs |
| `database/`, `models/`, `docs/`, `scripts/` | SQL dumps, seed models, docs, ops scripts |

## Commands

**Primary workflow is Docker Compose** (workspace root):
```bash
docker-compose up -d            # backend :8000, streaming :8001, nginx :3100
docker-compose logs -f backend
docker-compose exec backend bash
docker-compose exec postgres psql -U tutor -d tutor_lms
```
First-time setup: `chmod +x scripts/setup.sh && ./scripts/setup.sh`.
Frontend has **no host port** — reach it via nginx at `http://localhost:3100`.

**Frontend** (`cd frontend`):
```bash
npm install --legacy-peer-deps   # peer conflicts are expected; flag is required
npm run dev          # Vite :3000, proxies /api/v1 -> backend:8000
npm run build
npm run lint         # ESLint --max-warnings 0 — any warning fails the gate
npm run type-check   # tsc --noEmit — run before committing
npm run test         # Vitest (config exists; no tests written yet)
```

**Backend** (host, outside Docker):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Run `lint` + `type-check` before any frontend commit.** There is **no backend
test suite** — `backend/tests/` is empty; don't assume `pytest` returns results.

## Architecture boundaries

- **Backend routers** mount under `/api/v1/...` EXCEPT `chunked_upload`
  (`/upload/chunked`, imported conditionally) and `quizzes`/`assignments`
  (`/api/v1`). `main.py` currently registers ~37 routers. `/docs` + `/redoc` are
  only enabled when `ENVIRONMENT=development` (compose defaults to production).
- **Source of truth for schema = SQLAlchemy models** in `backend/app/models/`.
  There is **no Alembic** — `init_db()` in `app/core/database.py` (run from
  `main.py` lifespan) creates tables on boot. Changing a model means extending
  init logic or hand-applying a SQL file under `backend/migrations/`.
- **Services layer** (`backend/app/services/`) holds business logic; routers
  should stay thin. Follow that split when adding endpoints.
- **Video has THREE paths** — don't change video logic without checking which one
  a feature uses: (1) direct YouTube embed (`youtube_embed`/`embed`),
  (2) server-side yt-dlp proxy (`streaming-service/` + `video_streaming` router),
  (3) Bunny.net CDN (`bunny` router).
- **Streaming service has its own CORS (`*`) and NO auth** — the backend must
  gate access before redirecting a client to :8001.
- **Company portal** is a major feature area (dashboard, internships, work logs,
  attendance, reviews) with company-scoped access control — managers only see
  their own company. See `backend/app/models/company_dashboard.py`.
- **Frontend**: `App.tsx` defines routes, `store/` = Zustand stores
  (`auth`, `cartStore`, `course`, `quiz`), `api/` = axios + React Query wrappers,
  `components/ui/` = shadcn-style primitives. Some pages are Tamil-specific
  (`category-meiporul.tsx` etc.) — that taxonomy is intentional, not stray.

## Conventions

- **Path aliases** (frontend): `@`, `@/components`, `@/pages`, `@/hooks`,
  `@/utils`, `@/types`, `@/store`, `@/api`, `@/assets`, `@/styles`.
- **Vite config is JS** (`frontend/vite.config.js`), not TS.
- **Auth**: JWT access/refresh; roles Student / Instructor / Admin / Company /
  CompanyManager.
- **Adding a new dev origin**: update CORS/allowed-hosts in **two** places —
  `docker-compose.yml` (or the relevant compose file) AND `backend/app/core/config.py`.
- **Secrets**: `SECRET_KEY`/`JWT_SECRET` left at placeholder → `config.py`
  regenerates random ones each boot, invalidating all tokens on restart. Fine for
  dev; set real values for prod.

## Gotchas

- **Real entry point is `backend/app/main.py`.** The `main_simple.py`,
  `main_test.py`, `main_email_test.py`, `main_frontend_integration.py`,
  `main_payment_test.py` variants are experiments — editing them changes nothing.
  Likewise ignore `backend/app/core/config_broken.py` (real config is `config.py`)
  and `.bak` files.
- **Five compose files exist** — confirm which is authoritative for the target
  env before editing: `docker-compose.yml` (dev base), `.override.yml`
  (auto-merged locally), `.prod.yml`, `.production.yml` (used by
  `build-production.sh`), `.security.yml` (hardened overlay).
- **`build-production.sh` runs `docker system prune -f`** — it removes ALL unused
  images/build cache on the host, not just this project's.
- **`deploy-production.sh` has a hardcoded path** (`/www/wwwroot/sasha_lms/sasha_lms/sasha_lms`)
  and uses the `devesh` remote — fails on a machine without both.
- **Repo noise to ignore** (not source of truth): root transcript dumps
  (`2025-12-*.txt`, `dec_2_changes.txt`, `gitTok.md`), one-off admin scripts in
  `backend/` (`debug_video.py`, `delete_*.py`, `fix_schema.py`, `check_*.py`,
  `clear_demo_data.py`, `activate_accounts.py`), and accidental space-named files
  in `frontend/`.
- **Nested `sasha_lms/` directory** at workspace root contains a near-duplicate
  copy of backend/frontend/docs — verify you are editing the correct tree
  (this AGENTS.md lives at the outer workspace root).
- **Bind mounts**: `uploads/` and `certificates/` must exist before `up` or they
  get created root-owned and the backend can't write. `chown`/`chmod 755` on host.
