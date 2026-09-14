# Live Classes

Teachmint-style scheduled, interactive live video classes, built on a
self-hosted Jitsi Meet stack. This document is the reference for the
feature: architecture, environment variables, operational runbook, security
posture, and what's deliberately out of scope.

Implementation plan: `docs/superpowers/plans/2026-09-02-live-classes.md`.
Owner spec: `docs/superpowers/specs/2026-09-02-live-classes-brief.md` +
`docs/superpowers/specs/2026-09-02-live-classes-deviations.md` (repo-verified
overrides — binding).

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              Browser / Flutter app            │
                    │  React <JitsiStage> (IFrame API)  |  Flutter  │
                    │        jitsi_meet_flutter_sdk                 │
                    └───────────────┬─────────────────┬─────────────┘
                                    │ HTTPS (app API)   │ HTTPS/WSS (Jitsi)
                                    ▼                   ▼
                    ┌───────────────────────┐  ┌─────────────────────────┐
                    │  Edge nginx            │  │  Edge nginx              │
                    │  10-app.conf            │  │  20-live.conf            │
                    │  /api/v1/live/  (rate-  │  │  live.sashainfinity.com  │
                    │  limited: live_api zone)│  │  -> jitsi-web:8000       │
                    └───────────┬─────────────┘  └────────────┬─────────────┘
                                │                              │ sasha-net
                                ▼                              ▼
                    ┌────────────────────────┐   ┌──────────────────────────────┐
                    │  FastAPI backend         │   │  docker-jitsi-meet stack      │
                    │  /api/v1/live/*          │   │  (deploy/compose.live.yml)    │
                    │  - live_classes.py       │   │                                │
                    │  - live_class_session.py │   │  jitsi-web  ─ prosody (JWT)   │
                    │  - live_class_attendance │   │      │            │            │
                    │  - live_class_polls.py   │   │      │         jicofo          │
                    │  - live_class_recordings │◄──┼──────┘            │            │
                    │  /api/v1/internal/live/  │   │                  jvb (UDP     │
                    │  - live_class_internal.py│   │                  10000, media) │
                    │    (loopback + token)    │   │                   │            │
                    │                           │   │                 jibri         │
                    │  jitsi_token_service.py   │   │            (profile:recording)│
                    │  (mints room-pinned JWTs) │   │                   │            │
                    └────────────┬──────────────┘   │           ./recordings/*.mp4  │
                                 │                   └───────────────────┬────────────┘
                                 │ Postgres (7 tables)                    │ cron, every 2min
                                 ▼                                        ▼
                    ┌────────────────────────┐        ┌──────────────────────────────┐
                    │  live_class_schedules    │        │  finalize_recordings.sh/.py   │
                    │  live_classes             │        │  scans *.mp4, POSTs to        │
                    │  live_class_join_tokens   │        │  /api/v1/internal/live/       │
                    │  live_class_attendance    │        │  recordings (X-Internal-Token │
                    │  live_class_polls         │        │  + loopback)                  │
                    │  live_class_poll_votes    │        └───────────────┬────────────────┘
                    │  live_class_events        │                        │
                    └────────────────────────┘                          ▼
                                                              live_recording_service.py
                                                              -> existing Bunny upload flow
                                                              -> recording_video_id
                                                              -> existing signed playback
```

Key decisions (locked, see spec §3):

- Jitsi is a **single stateful instance** on the data-tier side of the
  infrastructure — it is NOT colour-duplicated and NOT part of the
  blue/green app-tier switch. It lives on the same `sasha-net` docker
  network as everything else.
- Auth: `AUTH_TYPE=jwt`. The backend mints short-lived, room-pinned JWTs
  (`app/services/jitsi_token_service.py`); Prosody verifies them. The room
  claim pins a token to one class's room — a leaked token cannot be replayed
  into a different conference.
- Web embeds Jitsi via the **official IFrame API** (`external_api.js` served
  by the jitsi-web container itself, loaded lazily by `<JitsiStage>`).
  Mobile uses the **official** `jitsi_meet_flutter_sdk`.
- Attendance truth is server-side: join-token redemption + 60s heartbeats
  with a 90s-per-beat cap, not client self-reporting.
- Recordings: Jibri writes to a shared volume; a cron worker
  (`finalize_recordings.sh` → `.py`) hands finished files to an internal,
  loopback+token-guarded endpoint, which uploads them through the
  **existing** Bunny pipeline (no new video infra) and attaches the
  resulting video id to the class.

## Environment reference

Two env files, kept in sync by convention (same `JITSI_JWT_SECRET` and
`INTERNAL_TOKEN` values in both, or token minting and Prosody's JWT
verification disagree):

- `deploy/.env.live` (gitignored; copy from `deploy/.env.live.example`) —
  consumed by `docker compose -f deploy/compose.live.yml` (the Jitsi stack
  containers).
- The backend's own env (`.env` / production env vars, documented in
  `backend/.env.example`) — consumed by `app/core/config.py`.

> **Production wiring lives in `deploy/docker-compose.app.yml` only.** That
> file's backend `environment:` block is an explicit allowlist, and the six
> live-class variables (`JITSI_PUBLIC_URL`, `JITSI_JWT_APP_ID`,
> `JITSI_JWT_SECRET`, `JITSI_RECORDINGS_DIR`, `INTERNAL_TOKEN`,
> `DEFAULT_TIMEZONE`) are passed through there, for both colours — the
> blue/green stacks share one `backend:` service definition parameterised by
> `$COLOR`, so one entry covers both.
>
> The **legacy root compose files are NOT wired for live classes**:
> `docker-compose.yml`, `docker-compose.production.yml`, and
> `nginx/conf.d/default.conf` predate this feature and pass none of the six
> variables. Bringing the backend up from one of them with
> `ENVIRONMENT=production` trips the startup fail-fast on blank
> `JITSI_JWT_SECRET` / `INTERNAL_TOKEN` and the container will not start.
> Either set `ENVIRONMENT=development` for legacy local dev (the fail-fast is
> production-only; live classes are then simply unavailable), or export the
> six variables into that stack's environment. Deliberately left unwired —
> the legacy root stack is out of scope for this feature and must not be
> edited for it.

| Variable | Consumed by | Purpose |
| --- | --- | --- |
| `JITSI_PUBLIC_URL` | backend, jitsi stack (`PUBLIC_URL`) | Public URL browsers/Flutter hit for the Jitsi web app, e.g. `https://live.sashainfinity.com`. TLS terminates at the aaPanel host — this stays `https://` even though the container itself is plain HTTP. |
| `DISABLE_HTTPS` | jitsi stack only | `1` — keeps the `jitsi-web` container itself serving plain HTTP. Required because TLS terminates upstream at the aaPanel host / Cloudflare (same story as `JITSI_PUBLIC_URL` above and `20-live.conf`'s edge vhost) — the container must not also try to speak HTTPS on its own. |
| `ENABLE_LETSENCRYPT` | jitsi stack only | `0` — the jitsi-web image's own Let's Encrypt automation stays off, since certificates are already handled by the TLS-terminating front proxy. Only flip this on if you ever run the Jitsi stack **without** a TLS-terminating front proxy in front of it (see `deploy/.env.live.example:34-37`). |
| `JITSI_JWT_APP_ID` | backend (`jitsi_token_service.py`), jitsi stack (`JWT_APP_ID`) | Shared JWT `iss`/`aud`/`sub` value. Default `sashainfinity`. Must match exactly on both sides. |
| `JITSI_JWT_SECRET` | backend (`jitsi_token_service.py` only), jitsi stack (`JWT_APP_SECRET`) | HS256 signing secret for room-pinned Jitsi JWTs. **Dedicated — never the platform `JWT_SECRET`.** 64+ hex chars (`openssl rand -hex 32`). Backend refuses to start in production if blank. |
| `JITSI_RECORDINGS_DIR` | backend (`live_recording_service.py`, path containment check), `finalize_recordings.py`, jitsi stack (`JIBRI_RECORDING_DIR` inside jibri, and the compose bind-mount source `./recordings`) | Where Jibri writes `*.mp4` files and the finalize worker scans. **The backend and the worker hold DIFFERENT values for the same files** — see the note directly below. |

> **`JITSI_RECORDINGS_DIR` is two different paths for one directory.** The
> host directory `deploy/recordings/` is bind-mounted into two places:
> jibri sees it at `/config/recordings` (`compose.live.yml`) and the backend
> container sees it, read-only, at `/app/recordings_live`
> (`docker-compose.app.yml`). The finalize worker runs on the *host* and sees
> it at `deploy/recordings`.
>
> So the backend's `JITSI_RECORDINGS_DIR` is `/app/recordings_live` while the
> worker's is the host path — and the worker therefore POSTs `file_path`
> **relative** to the recordings dir (`si-a1b2c3d4.mp4`), never an absolute
> path. `validate_recording_path` joins a relative value onto whichever base
> *it* is configured with before resolving, so the containment and room-name
> checks are unaffected. An absolute host path in `file_path` is meaningless
> inside the container and is correctly rejected as outside the recordings
> directory; that mismatch is what silently broke the ingest chain before.
| `INTERNAL_TOKEN` | backend (`live_class_internal.py`), `finalize_recordings.sh`/`.py` | Shared secret for `X-Internal-Token` on the internal recording-ingest endpoint. 48+ hex chars (`openssl rand -hex 24`). Backend returns 503 on this endpoint if blank. |
| `DEFAULT_TIMEZONE` | backend (scheduling/ICS) | Default timezone for new classes when the caller doesn't specify one. `Asia/Kolkata`. |
| `DOCKER_NETWORK` | jitsi stack only | External docker network name shared with the rest of the deployment. Default `sasha-net`. |
| `ENABLE_AUTH` / `AUTH_TYPE` | jitsi stack | `1` / `jwt` — no anonymous conferences. |
| `JWT_ALLOW_EMPTY` | jitsi stack | `0` — reject unsigned tokens. |
| `ENABLE_LOBBY` | jitsi stack | `1` — lobby on by default (per-class override via `settings.lobby_enabled`). |
| `ENABLE_RECORDING` | jitsi stack | `1` — recording feature available (per-class opt-in via the instructor's recording toggle). |
| `TZ` | jitsi stack | Container timezone, `Asia/Kolkata`. |
| `XMPP_DOMAIN` / `XMPP_AUTH_DOMAIN` / `XMPP_MUC_DOMAIN` / `XMPP_INTERNAL_MUC_DOMAIN` / `XMPP_RECORDER_DOMAIN` / `XMPP_GUEST_DOMAIN` / `XMPP_SERVER` | jitsi stack | docker-jitsi-meet stable's standard internal XMPP hostnames — no need to change these. |
| `JICOFO_AUTH_USER` / `JVB_AUTH_USER` / `JIBRI_XMPP_USER` / `JIBRI_RECORDER_USER` | jitsi stack | Fixed internal component usernames. |
| `JVB_ADVERTISE_IPS` | jitsi stack (jvb) | **Commented out by default.** Set to the VPS's public IP if remote participants can join (signalling works) but get no audio/video (media fails) — JVB otherwise advertises its private container IP in ICE candidates. See "Common failures" below. |
| `JICOFO_COMPONENT_SECRET` / `JICOFO_AUTH_PASSWORD` / `JVB_AUTH_PASSWORD` / `JIBRI_XMPP_PASSWORD` / `JIBRI_RECORDER_PASSWORD` | jitsi stack | Internal component secrets — `changeme-*` placeholders in the example file. Generate real ones with `openssl rand -hex 32` before first boot. |
| `TURN_REALM` / `TURN_STATIC_AUTH_SECRET` | jitsi stack, `coturn` profile only | Only needed if WebRTC connectivity testing shows clients failing ICE behind restrictive NATs. |

## Runbook

### Start / stop the Jitsi stack

```bash
cd deploy

# Core stack (web, prosody, jicofo, jvb) — no recording capability yet:
docker compose -f compose.live.yml --env-file .env.live up -d

# With recording (adds jibri):
docker compose -f compose.live.yml --env-file .env.live --profile recording up -d

# With a TURN relay (only if WebRTC connectivity testing requires it):
docker compose -f compose.live.yml --env-file .env.live --profile turn up -d

# Stop everything:
docker compose -f compose.live.yml --env-file .env.live down

# Status / logs:
docker compose -f compose.live.yml --env-file .env.live ps
docker compose -f compose.live.yml --env-file .env.live logs -f jvb
```

Config volumes (`deploy/jitsi/{web,prosody,jicofo,jvb,jibri}`) persist
generated certs and baked-in XMPP passwords across `up`/`down` cycles — do
not delete them casually (see secret rotation below for the one case where
you must).

### Rotate `JITSI_JWT_SECRET`

The secret is baked into both the backend's token-minting config **and**
Prosody's JWT verification config. Rotating it requires changing both in
lockstep, in this order (a mismatched window means existing joins fail with
signature errors):

1. Generate a new secret: `openssl rand -hex 32`.
2. Update `deploy/.env.live`: set `JITSI_JWT_SECRET=<new value>` (and
   `JWT_APP_SECRET=${JITSI_JWT_SECRET}` picks it up automatically since it's
   a variable reference).
3. Update the backend's env (wherever `INTERNAL_TOKEN`/`JITSI_JWT_SECRET`
   live for this deployment — production env file or process manager env) to
   the **same** new value.
4. Recreate the Jitsi stack so Prosody re-reads the new secret from its env
   file (a plain restart is not enough if Prosody has already baked the old
   secret into generated config — recreate to be safe):
   ```bash
   cd deploy
   docker compose -f compose.live.yml --env-file .env.live up -d --force-recreate prosody jicofo
   ```
5. Restart the backend process so `get_settings()` picks up the new
   `JITSI_JWT_SECRET` (it's a `pydantic-settings` singleton read once at
   startup — see `app/core/config.py`).
6. Verify: run `deploy/scripts/smoke_jitsi.sh` (mints a token with the new
   secret and confirms the vhost responds), then do one real two-browser
   join.
7. **Any join tokens minted before step 2–3 land are now invalid** — this is
   expected; any user mid-class at the exact rotation instant would need to
   rejoin. Prefer rotating during a low-traffic window.

Rotating `INTERNAL_TOKEN` is simpler — it's compared by the backend only,
never baked into Jitsi's own config:
1. `openssl rand -hex 24`.
2. Update it in `deploy/.env.live` AND the backend's env to the same value.
3. Restart the backend process. No Jitsi container restart needed.

### Recover stuck recordings

If a class's `recording_status` is stuck at `PROCESSING`/`REQUESTED`, or a
finished `.mp4` on disk was never ingested (finalize worker cron down, a
backend outage during ingest, etc.), re-run the worker manually:

```bash
cd deploy/scripts

# Dry look at what's eligible (no ingest — just see what candidates exist):
ls -la ../recordings/*.mp4

# Which colour is currently answering? (blue = 8010, green = 8011)
curl -fsS http://127.0.0.1:8010/health && echo " <- blue"
curl -fsS http://127.0.0.1:8011/health && echo " <- green"

# Manually re-run the finalize pass against the live backend. Use the port
# the probe above found — 8000 is NOT published by the blue/green app stack:
JITSI_RECORDINGS_DIR=../recordings \
INTERNAL_TOKEN=<value from deploy/.env.live> \
python3 finalize_recordings.py --backend-url http://127.0.0.1:8010 --min-age-seconds 0

# Or via the cron wrapper (reads deploy/.env.live itself, probes 8010 then
# 8011 for whichever colour is live, logs to logs/finalize_recordings.log):
./finalize_recordings.sh
```

**Backend port.** The app tier publishes no public host port; each colour
binds one loopback-only port for exactly this worker —
`127.0.0.1:8010` (blue) / `127.0.0.1:8011` (green), see
`docker-compose.app.yml` ("WORKER LOOPBACK PORT") and
`lib.sh:backend_loopback_port`. `finalize_recordings.sh` probes `/health` on
each in turn and uses the first that answers; set `FINALIZE_BACKEND_URL` to
pin one explicitly. If neither answers (mid-deploy window) the wrapper logs
and exits 0 — nothing is lost, because a file is only marked `.ingested`
after a 200, so the next 2-minute run picks it up.

**The internal endpoint is not reachable through the edge.** nginx returns
404 for `/api/v1/internal/` and never proxies it, and the endpoint itself
rejects any request carrying `X-Forwarded-For`/`X-Forwarded-Host` — which
nginx always sets — *regardless of whether the token is valid*. Only a
process on the host talking to the loopback port directly can ingest. If a
manual `curl` to the ingest endpoint returns 403 with "not reachable through
the edge", you went through the edge vhost instead of `127.0.0.1:<port>`.

Useful flags on `finalize_recordings.py` (see its own docstring for the
full contract):
- `--recordings-dir <path>` — override the directory to scan (default
  `$JITSI_RECORDINGS_DIR`).
- `--backend-url <url>` — override the backend base URL (default
  `http://127.0.0.1:8000`).
- `--internal-token <token>` — override `$INTERNAL_TOKEN` (avoid passing
  secrets as CLI args in practice — prefer the env var; this flag exists
  mainly for one-off local testing against a non-default backend).
- `--min-age-seconds <n>` — skip files newer than this many seconds
  (default 120, to avoid ingesting a file Jibri is still writing). Set to
  `0` to force-process a file you know is finished.
- `--timeout <seconds>` — HTTP request timeout per POST (default 30).

Idempotency: a file already carrying a sidecar `<file>.ingested` marker is
skipped by the worker even on a re-run; the backend has its own idempotency
backstop (a class that already has a `recording_video_id` returns
`skipped=True` rather than re-uploading). If a file is stuck because its
`.ingested` marker was written but the class never actually got a
`recording_video_id` (a partial failure), delete the stale `.ingested`
sidecar file next to the `.mp4` before re-running so the worker POSTs it
again.

**Local fallback copies live in `backend/recordings_fallback/`.** When every
Bunny upload attempt fails, `live_recording_service` copies the `.mp4` to
`backend/recordings_fallback/class-<id>-<name>.mp4` and marks the class
`AVAILABLE` with `settings.recording_fallback = true`. This directory is
deliberately **outside** every `StaticFiles` mount — `app/main.py` mounts
only `uploads/` and `certificates/`, both of which serve their entire
contents publicly with no auth check, so a recording placed under `uploads/`
would have been downloadable by anyone with the filename, bypassing the
enrollment gate the signed Bunny playback exists to enforce. Include this
directory in backups, and do not move it under `uploads/`.

**RAM during ingest.** The Bunny upload reads the whole `.mp4` into memory to
send it as a single request body (the read and the fallback copy both run via
`asyncio.to_thread`, so they no longer block the event loop, but the file is
still buffered). Peak RSS during an ingest is roughly one recording's size —
worth watching if class recordings grow past a couple of GB on a small VPS.

If the room name in the class doesn't match what's in the filename (Jibri
recording-directory naming needs to be verified against real output on
first deploy — see "Alembic and schema notes" caveat list below, item
mirrored here: **finalize worker room-name convention is VPS-only verified**),
check the actual filename/directory under `deploy/recordings/` and compare
it to the class's `room_name` column before assuming the worker is broken.

### Common failures

- **Lobby stuck / participants can't get past the waiting room.** Confirm
  `ENABLE_LOBBY=1` is set and the class's own `settings.lobby_enabled` is
  `true`/`false` as intended (per-class override). The moderator (instructor,
  `context.user.moderator=true` in their JWT) must actually join and admit
  waiting participants from the Jitsi UI — a lobby with no moderator present
  never opens automatically.
- **WebSocket 502 through the edge, Cloudflare orange-cloud.** If DNS for
  `live.sashainfinity.com` is orange-clouded (proxied) before WebRTC has
  been verified end-to-end, Cloudflare's proxy can interfere with the
  long-lived `/xmpp-websocket` and `/colibri-ws/` upgrade connections
  (`20-live.conf` sets `proxy_read_timeout 86400` on the origin side, but
  Cloudflare's own WebSocket timeout/behavior on the free/pro tiers can
  still cut in). Grey-cloud (DNS-only) the record first, confirm joins work
  end-to-end, and only orange-cloud afterward once you've confirmed
  WebSocket traffic survives it in practice.
- **JWT clock skew.** Jitsi JWTs carry `iat`/`nbf`/`exp` as Unix timestamps
  computed from the backend host's clock; Prosody validates them using
  its own container clock. If the VPS's system clock has drifted (NTP not
  running, a VM pause/resume, etc.), valid-looking tokens get rejected as
  "not yet valid" or "expired" even though wall-clock time looks fine from
  a browser. Check `date -u` inside both the backend host and the
  `sasha-jitsi-prosody` container agree, and confirm NTP/`chronyd` is
  running on the VPS.
- **Signalling works, no audio/video (media fails to connect).** This is
  the JVB advertised-IP problem, not a code bug — see the
  `JVB_ADVERTISE_IPS` row in the env table above. Uncomment it in
  `deploy/.env.live`, set it to the VPS's public IP, and recreate the `jvb`
  container.
- **`health_jitsi.sh` reports `jibri` missing.** Expected unless the stack
  was started with `--profile recording` — jibri is optional and
  profile-gated; its absence is not itself a failure.

### Backup

Add the recordings volume to nightly backups alongside the existing
database backup. This repo's backup scheduling lives in
`docker-compose.backup.yml` (a busybox-crond container, no host cron
daemon) — add a companion line for `deploy/recordings` using the **host**
crontab (or a second scheduled line inside that same backup container if
you extend its script to also tar the directory). At minimum, the exact
crontab line to add recordings to a nightly backup job (adjust destination
to match wherever `database/backups/nightly` is retained/rotated):

```cron
# Nightly Live Classes recordings backup — 02:45, after the 02:30 DB dump
45 2 * * * tar -czf /path/to/database/backups/nightly/live-recordings-$(date +\%Y\%m\%d).tar.gz -C /path/to/deploy recordings >> /var/log/sasha/backup.log 2>&1
```

And the finalize worker's own cron entry (every 2 minutes, per the recording
pipeline design — see spec §7):

```cron
*/2 * * * * /path/to/deploy/scripts/finalize_recordings.sh
```

Both lines go in the **host's** crontab (`crontab -e` as the deploy user),
not inside a container — `finalize_recordings.sh` talks to the backend over
`http://127.0.0.1:8000`, which assumes it runs on the host (or an
equivalent network namespace) alongside the backend container's published
port.

### VPS smoke checklist (post-implementation, owner-executed)

This cannot run from the build machine (deviations file item 13). In order:

1. **DNS**: point `live.sashainfinity.com` at the server IP, **grey-cloud**
   (DNS-only, not proxied) initially — see "Common failures" above for why.
2. `cp deploy/.env.live.example deploy/.env.live` and fill in real secrets
   (`openssl rand -hex 32` / `-hex 24` for each `changeme-*` placeholder).
   Set the matching `JITSI_JWT_SECRET`/`INTERNAL_TOKEN` values in the
   backend's own env too.
3. `docker compose -f deploy/compose.live.yml --env-file deploy/.env.live up -d`
   (add `--profile recording` if recording will be tested).
4. `deploy/scripts/health_jitsi.sh` — all core containers healthy, HTTP 200
   from `127.0.0.1:8080`.
5. `deploy/scripts/smoke_jitsi.sh` — mints a throwaway JWT, prints a join
   URL, confirms the vhost + websocket endpoints respond.
6. **Two-browser join test with lobby**: open the printed join URL as the
   moderator in one browser, join as a second (non-moderator) participant
   in another; confirm the lobby holds the second participant until
   admitted, and that audio/video connects after admission (this is also
   where the `JVB_ADVERTISE_IPS` media-path issue would show up — see
   "Common failures").
7. **Reload the edge nginx AFTER the Jitsi stack is up**, not before —
   `20-live.conf`'s `proxy_pass http://jitsi-web:8000` is a literal upstream
   name that nginx resolves via Docker's embedded DNS; reloading edge nginx
   while `jitsi-web` doesn't exist yet on `sasha-net` can leave that
   resolution stale until the next reload. Bring the Jitsi stack up first,
   confirm it's healthy, **then** reload/restart the edge nginx container.
8. Only **orange-cloud** (enable Cloudflare proxying) for
   `live.sashainfinity.com` after step 6 has confirmed real WebRTC media
   connects end-to-end.
9. **Verify the real-Redis SSE path and Prosody's real JWT verification** —
   both are only provable against live infrastructure; the backend test
   suite exercises the `MockRedis` fallback path and a hand-verified claim
   shape, never a real Redis broker or a real Prosody rejection (Task 3's
   explicitly deferred VPS-only item). Two checks:
   - **Poll SSE via real Redis pub/sub**: with `REDIS_URL` pointed at a real
     Redis instance (not the dev/test `MockRedis`), open a class's poll
     stream (`GET /api/v1/live/classes/{id}/polls/{pid}/stream`) in one
     browser tab as the instructor, and cast a vote from a second
     browser/session as a student. Confirm the result bars update in the
     first tab **without a page refresh or manual poll** — that proves
     `poll.voted`/`poll.activated`/`poll.closed` events are actually
     traveling over Redis pub/sub to a live `EventSourceResponse`, not
     falling back to the single-snapshot-then-keepalive behavior
     `live_class_polls.py` uses when Redis is mocked.
   - **Prosody rejects a mis-signed JWT**: mint a token with
     `jitsi_token_service.mint_jitsi_jwt`-shaped claims but a **wrong**
     secret (e.g. reuse `smoke_jitsi.sh`'s hand-rolled HS256 signer with a
     deliberately different `JITSI_JWT_SECRET` value than what's in
     `deploy/.env.live`), and attempt to join the resulting URL. Confirm
     Prosody's `AUTH_TYPE=jwt` verification actually rejects it (the join
     fails at the Jitsi layer, not merely because the room doesn't exist) —
     this is the negative-path proof that the deployed Prosody config is
     really checking the signature and not silently accepting any token
     (`JWT_ALLOW_EMPTY=0` alone doesn't prove signature verification is
     wired correctly; a positive join with a correctly-signed token proves
     the happy path, this negative check proves the guard is real). Then
     confirm a **correctly**-signed token (from `smoke_jitsi.sh` or a real
     backend-minted join token) still joins successfully, so the negative
     result isn't just a broken vhost.

## Alembic and schema notes

This feature introduces the repo's **first** Alembic setup
(`backend/alembic/`), used **only** for the seven new live-class tables.
Everything that existed before this feature is still owned by
`init_db()`'s `Base.metadata.create_all()` (in `app/core/database.py`) plus
the hand-applied SQL files in `backend/migrations/*.sql` — Alembic does not
manage them and never will retroactively.

- **`0001_baseline.py`** is an intentionally empty revision (no-op
  upgrade/downgrade). It exists purely so a database can be stamped
  `alembic stamp head`-equivalent at "nothing before Live Classes" without
  Alembic trying to recreate tables that `create_all`/manual SQL already
  own.
- **`0002_add_live_class_tables.py`** is the one real migration: creates
  (and, on downgrade, drops) all seven `live_class_*` tables.
- **Dual-path is deliberate, not a bug**: `init_db()` also creates the
  live-class tables from the SQLAlchemy models directly (`create_all` is
  additive/idempotent — it no-ops on tables that already exist). This means
  a database can reach the correct final schema either by running
  `init_db()` alone (as every table before this feature always has) or by
  running the Alembic migration. Both paths are safe to run against the
  same database because `create_all` never touches a table Alembic already
  created, and Alembic's `CREATE TABLE` will simply fail loudly (not
  silently corrupt anything) if `create_all` already created the table
  first — see the `has_table` guard note below for how the migration
  protects against exactly that ordering.
- **`has_table` guard rationale**: the migration checks whether each table
  already exists before creating it (via SQLAlchemy's inspector) precisely
  because `init_db()` may have already run first in a given deployment
  sequence (e.g., the backend boots and creates tables via `create_all`
  before anyone thinks to run `alembic upgrade head`). Without the guard,
  running the migration after `init_db()` has already created these tables
  would raise a "relation already exists" error on Postgres. The guard
  makes migration order (init_db-first or alembic-first) a non-issue.
- **When to run `alembic stamp head`**: on any database where the live-class
  tables already exist because `init_db()` created them first (the common
  case for this deployment, since the backend's lifespan always calls
  `init_db()` on startup) — run `alembic stamp head` instead of `alembic
  upgrade head` to tell Alembic "these tables are already correct, just
  record that we're at the latest revision" without re-running the
  (redundant, and on Postgres actually erroring, if the guard weren't in
  place) `CREATE TABLE` statements. Only run a plain `alembic upgrade head`
  on a database you know does NOT yet have the live-class tables (e.g., a
  fresh scratch/test database that never ran `init_db()`).
- **PG-native types verified only on SQLite in this repo's test harness —
  confirm at first real deploy.** The migration declares the enum columns
  as native Postgres `ENUM` types and `LiveClassEvent.id` as `sa.BigInteger`
  with `autoincrement=True` (bigserial-equivalent) specifically for
  Postgres — but this repo's test suite runs the migration only against
  SQLite (`test_live_class_migration.py`), where SQLite's type affinity
  silently accepts and stores these as generic types rather than exercising
  Postgres's actual `CREATE TYPE ... AS ENUM` / `BIGSERIAL` DDL paths. **The
  first real deploy against the production Postgres database is the first
  time these PG-native code paths actually execute** — verify the migration
  runs clean there (watch for enum-creation or bigserial-identity DDL
  errors) before considering this migration proven. If it fails, the fix is
  almost certainly a Postgres-dialect DDL detail (e.g., an enum type name
  collision, or an identity-column syntax quirk) rather than a logic bug —
  compare the generated DDL (`alembic upgrade head --sql`) against what the
  running Postgres version expects.

## Deviations summary

Repo-verified overrides that took precedence over the owner's brief where
they conflicted (full detail: `docs/superpowers/specs/2026-09-02-live-classes-deviations.md`):

1. **Integer PKs/FKs**, not UUID — matches the rest of the schema
   (users/courses/lessons/enrollments). `jti` and `room_name` stay opaque
   strings, not UUID columns.
2. **No response envelope** — plain Pydantic `response_model` per endpoint,
   matching the repo's modern router style (memberships/bundles), not a
   `{success, data}` wrapper.
3. **Roles** guarded with existing `AuthService` dependencies
   (`require_instructor`, `require_admin`, `get_current_active_user`) rather
   than inventing new role-check machinery.
4. **No `env/` directory** — example env at `deploy/.env.live.example`,
   real file `deploy/.env.live` (gitignored); backend reads its own
   variables from the normal `config.py` Field mechanism, with a startup
   fail-fast (not import-time crash) when `ENVIRONMENT=production` and
   `JITSI_JWT_SECRET`/`INTERNAL_TOKEN` are blank.
5. **Reminders use a dedicated asyncio loop** (mirroring
   `app/services/reconciliation.py`'s advisory-lock + per-item
   fault-isolation pattern) — no APScheduler dependency added.
6. **SSE** falls back to short-poll semantics (snapshot + keepalive
   comments) when Redis is a `MockRedis` (tests/dev without a real broker),
   so tests can assert payload shape without a live pub/sub backend.
7. **ICS is hand-rolled** (minimal `VCALENDAR`/`VEVENT`, UTC, escaped text)
   — no new calendar library dependency.
8. **Flutter uses `jitsi_meet_flutter_sdk`** (the maintained package, not
   the discontinued `jitsi_meet`), pinned to `^10.2.0` deliberately
   (conservative — pub's latest at implementation time was 13.1.1; API
   verified against the 10.2.0 docs). No Flutter toolchain exists on the
   build machine and there is no Flutter CI gate — the module is
   compiled/run for the first time by the owner (see "Flutter — owner
   actions" below).
9. **Alembic initialized fresh** under `backend/` for this feature only —
   see "Alembic and schema notes" above for the full dual-path rationale.
10. **CI gates for this feature are pytest + vitest + shellcheck + the new
    gitleaks step** — ESLint/tsc stay advisory repo-wide (391 pre-existing
    type errors), consistent with the rest of this repo's CI posture.
11. **`hls.js` missing from `package.json`** is a pre-existing, unrelated
    latent issue, not fixed here (additive-only constraint) — noted for the
    owner as a separate follow-up.
12. **FCM web push doesn't exist yet**; the backend's `firebase_admin`
    messaging helpers do. Reminder emails ship now; FCM broadcast goes
    through the existing backend helper with a no-op guard when Firebase
    isn't configured. Mobile deep-link handling rides `flutter_app`'s
    existing FCM setup (verified present during the mobile task).
13. **The Phase-1 VPS smoke test cannot run from the build machine** — the
    deliverable here is the configs, `deploy/scripts/smoke_jitsi.sh`, and
    the runbook checklist above; the owner executes it on the server.

## Future phases (out of scope for this build)

Per spec §16 — documented here so requests for these aren't mistaken for
regressions:

- Breakout rooms
- YouTube / Facebook live-streaming integration
- SIP dial-in
- Custom whiteboard (beyond Jitsi's built-in Excalidraw)
- Persistent chat history
- AI-generated class summaries
- Mobile instructor authoring (scheduling a class from the Flutter app)
- Multi-JVB / Octo (horizontal media-routing scale-out)
- High-availability Jitsi (this is a single stateful instance by design)

## Flutter — owner actions required

The Flutter module (`flutter_app/lib/features/live_classes/`) was authored
to convention against two existing feature modules but is **compile-untested**
— there is no Flutter toolchain on the build machine and no Flutter CI gate
(deviations item 8). Before shipping the mobile build:

1. Run `flutter pub get` to fetch `jitsi_meet_flutter_sdk: ^10.2.0` (verify
   this resolves to a version whose `JitsiMeetConferenceOptions` /
   `JitsiMeet().join(...)` API matches what `join_live_class_screen.dart`
   calls — it was written against the 10.2.0 docs, not tested against the
   actual resolved package).
2. Run `flutter pub run build_runner build --delete-conflicting-outputs`
   (or `dart run build_runner build`) — the freezed/Riverpod generated part
   files for the new models/providers are **not** committed (reference
   modules in this codebase commit their generated files; this module's
   generated files are missing and must be produced locally before it will
   compile).
3. `flutter analyze` and a full build (`flutter build apk` /
   `flutter build ios` as applicable) to catch anything the static review
   missed.
4. Confirm the dev-flavor API base URL actually points at a local/staging
   backend (`10.0.2.2:8000` for the Android emulator, or your LAN/staging
   URL) rather than production — this was a real defect found and fixed
   during Task 9 (M-04: dev flavor was silently defaulting to the prod
   URL); worth a manual sanity check after `build_runner` regenerates
   anything.
