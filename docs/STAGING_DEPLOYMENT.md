# SashaInfinity Local Staging Deployment

The staging stack is an isolated, production-mode rehearsal. It uses PostgreSQL 15, authenticated Redis, a built frontend image, a non-reloading FastAPI image, a separate streaming service, nginx, durable named volumes, migration gating, health checks, and an optional isolated coding worker.

## Start

From the workspace root in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_staging.ps1
```

The command generates unique local secrets beneath `.local/staging/`, validates the Compose model, builds the images, initializes the database, applies every Alembic migration, waits for readiness, and creates the staging administrator.

- Application: `http://127.0.0.1:3200`
- Backend diagnostic port: `http://127.0.0.1:8200`
- Streaming diagnostic port: `http://127.0.0.1:8201`
- PostgreSQL: `127.0.0.1:15433`
- Redis: `127.0.0.1:16380`
- Local credentials: `.local/staging/admin-credentials.txt`

Do not copy the generated local credentials into production.

## Validate configuration without starting containers

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_staging.ps1 -ValidateOnly
```

## Enable coding assessment execution

Deploy Judge0 CE into an isolated private network, set `JUDGE0_URL` and optionally `JUDGE0_AUTH_TOKEN` in `.local/staging/.env.staging.local`, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_staging.ps1 -WithCoding
```

Learner code must never be executed by the LMS API container.

## Rotate all local staging secrets

This changes database and Redis credentials. For an existing volume, either update the corresponding service credentials deliberately or recreate only the `sasha-staging` volumes after confirming that their data is disposable.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_staging.ps1 -RotateSecrets -ValidateOnly
```

## Operations

```powershell
docker compose --env-file .local/staging/.env.staging.local -f docker-compose.staging.yml ps
docker compose --env-file .local/staging/.env.staging.local -f docker-compose.staging.yml logs -f backend
docker compose --env-file .local/staging/.env.staging.local -f docker-compose.staging.yml down
```

`down` preserves named volumes. Do not add `--volumes` unless the staging data is confirmed disposable.

## External integrations

The generated environment intentionally leaves Razorpay, SMTP, Bunny, Firebase, WhatsApp, Jitsi infrastructure, and Judge0 endpoints unconfigured. Add sandbox or staging credentials only. Acceptance cases that depend on an unconfigured provider remain blocked rather than being reported as passed.
