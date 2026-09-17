# Live Classes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teachmint-style live classes on self-hosted Jitsi: schedule → one-console instructor experience (video + dock: attendance, polls, timer, raise-hand, recording) → server-truth attendance → Jibri recordings auto-published through the existing Bunny pipeline — web + Flutter, fully tested.

**Architecture:** Jitsi (docker-jitsi-meet, JWT auth, single data-tier instance on `sasha-net`) is embedded via the IFrame API / Flutter SDK using backend-minted room-pinned JWTs. Platform truth lives in seven new tables behind `/api/v1/live/*` routers (Pydantic response models, existing role guards). Polls stream over SSE + Redis pub/sub. A reconciliation-style asyncio loop sends reminders. A finalize worker moves Jibri output into Bunny.

**Tech Stack:** FastAPI + SQLAlchemy 2 + Alembic (new) + PyJWT + sse-starlette (new), React 18 + Vite + vitest, Flutter (`jitsi_meet_flutter_sdk`), docker-jitsi-meet stable, nginx edge.

**Spec:** `docs/superpowers/specs/2026-09-02-live-classes-brief.md` (owner brief) + `2026-09-02-live-classes-deviations.md` (repo-verified overrides — BINDING). Both are in this worktree; every implementer reads BOTH before coding.

## Global Constraints

- Worktree `.worktrees/live-classes`, branch `live-classes` (off revenue-platform). Backend paths relative to `<worktree>/backend/`.
- Backend tests: `"C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe" -m pytest tests/<files> -v` from `<worktree>/backend/`. Baseline ~45 pre-existing failures / 4 errors in old files; gate = zero NEW failures. Install backend deps into the shared venv when the plan says so (pip install is allowed for the named packages only).
- Frontend gates: `npm run type-check` zero NEW vs the 391-error baseline; `npx vitest run` green (this feature ships the first suites). No ESLint config exists — skip lint.
- **Additive only.** Never touch: root `docker-compose.yml`, `nginx/conf.d/default.conf`, `main_*.py` variants, `wp-content/`, `frontend-build/`, `payments_proxy.py`, `test_proxy_webhook_migration.py`. New code in new files; registrations (router mounts, nginx include, requirements lines, App.tsx routes, nav arrays) may be appended.
- **No secrets anywhere.** Committed env files are `*.example` only, placeholder values. `JITSI_JWT_SECRET` ≠ platform `JWT_SECRET` by design; backend refuses to start when `ENVIRONMENT=production` and JITSI_JWT_SECRET or INTERNAL_TOKEN is blank (startup check in lifespan, not import time).
- Response style: Pydantic `response_model` per endpoint. Guards: existing AuthService dependencies. Integer PKs/FKs. UTC timestamps. Routers ≤ ~400 lines each.
- Room names: `si-` + 8 chars from `secrets.token_urlsafe`/hex — never derived from course/class ids.
- Commit trailer: blank line then `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Infrastructure — Jitsi stack, edge vhost, env example, health & smoke scripts

**Files:**
- Create: `deploy/compose.live.yml`, `deploy/.env.live.example`, `deploy/nginx/conf.d/20-live.conf`, `deploy/scripts/health_jitsi.sh`, `deploy/scripts/smoke_jitsi.sh`
- Modify: `deploy/nginx/nginx.conf` (add `limit_req_zone $binary_remote_addr zone=live_api:10m rate=10r/s;` beside the existing zones; fix nothing else), `deploy/nginx/conf.d/10-app.conf` (INSERT a `location /api/v1/live/ { limit_req zone=live_api burst=20 nodelay; ... }` block ABOVE the general `/api/v1/` location, proxying identically to it — copy its proxy directives verbatim), `deploy/nginx/snippets/security-headers.conf` (append `https://live.sashainfinity.com` to frame-src AND script-src of the CSP line — modify only those two directives), `.gitignore` (add `deploy/.env.live`), `docker-compose.backup.yml`-adjacent backup docs NOT touched — instead note recordings-volume backup in the runbook (Task 10).

**Interfaces:** compose file name + service names consumed by Task 10 runbook and health script. Recordings volume named `live_recordings` mounted at `/config/recordings` in jibri and referenced by Task 7's worker as host path `deploy/recordings/` (bind mount `./recordings:/config/recordings`).

**Content requirements (binding):**
- `deploy/compose.live.yml`: services `jitsi-web` (image `jitsi/web:stable`, ports `127.0.0.1:8080:80`), `prosody` (`jitsi/prosody:stable`), `jicofo` (`jitsi/jicofo:stable`), `jvb` (`jitsi/jvb:stable`, UDP 10000 published), `jibri` (`jitsi/jibri:stable`, profile `recording`, bind `./recordings:/config/recordings`, shm_size 2gb, cap_add SYS_ADMIN), optional `coturn` under profile `turn`. All on external network `sasha-net` (`name: ${DOCKER_NETWORK:-sasha-net}`, external: true — mirror deploy/docker-compose.app.yml:263-266 style). `env_file: .env.live` on every service. `restart: unless-stopped`. Healthchecks: web = `wget -q --spider http://localhost:80` style; prosody/jvb = process/port checks per docker-jitsi-meet conventions. Config volumes `./jitsi/{web,prosody,jicofo,jvb,jibri}:/config`.
- Jitsi env in `.env.live.example` (placeholders only): the §6.1 variables PLUS the docker-jitsi-meet JWT knobs: `ENABLE_AUTH=1`, `AUTH_TYPE=jwt`, `JWT_APP_ID=${JITSI_JWT_APP_ID}`, `JWT_APP_SECRET=${JITSI_JWT_SECRET}`, `JWT_ALLOW_EMPTY=0`, `ENABLE_LOBBY=1`, `ENABLE_RECORDING=1`, `JIBRI_RECORDING_DIR=/config/recordings`, `PUBLIC_URL=${JITSI_PUBLIC_URL}`, `TZ=Asia/Kolkata`, XMPP internal hostnames per the official compose (copy from docker-jitsi-meet stable defaults), and strong-random placeholders `changeme-*` for JICOFO/JVB/JIBRI component secrets with a comment to generate real ones.
- `20-live.conf`: vhost `live.sashainfinity.com` on the edge (port 80 inside the container — TLS terminates at aaPanel host like every other vhost; mirror 10-app.conf's header patterns), `location /` + `/xmpp-websocket` + `/colibri-ws/` all proxy to `http://jitsi-web:80` **via the docker network name** (the edge container and jitsi share sasha-net — NOT 127.0.0.1, which would be the edge container's own loopback; this corrects the owner brief's sketch) with Upgrade/Connection headers and `proxy_read_timeout 86400`.
- `health_jitsi.sh`: bash, shellcheck-clean, checks: `docker inspect` health/running state of the five containers, HTTP 200 from `http://127.0.0.1:8080` (host-published web port), and prints a one-line OK/FAIL summary with exit code. Style-match `deploy/scripts/health-check.sh` (read it first).
- `smoke_jitsi.sh`: run ON THE VPS by the owner: generates a throwaway HS256 JWT with python3 + the env's JITSI_JWT_SECRET for a test room, prints a join URL `${JITSI_PUBLIC_URL}/<room>?jwt=<token>`, and curls the vhost + websocket endpoints for 101/200s. Never reads secrets from args; sources `deploy/.env.live`. Shellcheck-clean.

- [ ] Steps: write files → `bash -n` + `shellcheck` both scripts (`shellcheck deploy/scripts/health_jitsi.sh deploy/scripts/smoke_jitsi.sh`) → `docker compose -f deploy/compose.live.yml config -q` parses (docker CLI available; daemon not needed for config) → nginx changes reviewed by diff (no nginx binary locally; syntax kept trivially valid by copying existing directive style) → commit `feat(live): jitsi stack, edge vhost, health + smoke scripts`.

---

### Task 2: Backend foundation — settings, Alembic, models, schemas

**Files:**
- Modify: `app/core/config.py` (add `JITSI_PUBLIC_URL`, `JITSI_JWT_APP_ID` default "sashainfinity", `JITSI_JWT_SECRET` default "", `JITSI_RECORDINGS_DIR` default "recordings_live", `INTERNAL_TOKEN` default "", `DEFAULT_TIMEZONE` default "Asia/Kolkata" — Field(env=...) style matching ADMIN_EMAIL), `app/main.py` lifespan (fail-fast: if `settings.ENVIRONMENT == "production"` and (not JITSI_JWT_SECRET or not INTERNAL_TOKEN) → `logger.critical` + `raise RuntimeError` BEFORE init_db — mirror the VIDEO_SECRET validation pattern in routers/player.py), `backend/requirements.txt` (append `sse-starlette==2.1.3`), `.env.example` + `backend/.env.example` (document the six vars)
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_baseline.py` (empty upgrade/downgrade with docstring: pre-existing schema is owned by init_db + backend/migrations/*.sql; this revision marks the baseline), `backend/alembic/versions/0002_add_live_class_tables.py` (real create/drop of all seven tables), `app/models/live_class.py`, `app/schemas/live_class.py`
- Test: `backend/tests/test_live_class_models.py`, `backend/tests/test_live_class_migration.py`

**Interfaces (produced — Tasks 3-6 import these exact names):**
```python
# app/models/live_class.py
class LiveClassStatus(enum.Enum): SCHEDULED/LIVE/ENDED/CANCELLED
class RecordingStatus(enum.Enum): NONE/REQUESTED/PROCESSING/AVAILABLE/FAILED
class PollStatus(enum.Enum): DRAFT/ACTIVE/CLOSED
class AttendanceSource(enum.Enum): WEB/MOBILE
LiveClassSchedule, LiveClass, LiveClassJoinToken, LiveClassAttendance,
LiveClassPoll, LiveClassPollVote, LiveClassEvent
```
Columns exactly per spec §4 with the deviations file's Integer ids: e.g. `LiveClass(id Integer pk, schedule_id FK nullable, course_id FK courses.id nullable=False, lesson_id FK lessons.id nullable, instructor_id FK users.id, title String(200), description Text nullable, scheduled_start/scheduled_end DateTime(timezone=True), timezone String(64) default "Asia/Kolkata", room_name String(120) unique index, status Enum default SCHEDULED, started_at/ended_at nullable, live_participants Integer default 0, recording_video_id String(64) nullable  # Bunny video GUIDs are strings — verify against bunny.py and use its id type, recording_status Enum default NONE, settings JSON default dict, created_at/updated_at/deleted_at)`. Indexes: (course_id, scheduled_start), (instructor_id, scheduled_start), (status). `LiveClassEvent.id` = Integer autoincrement (bigserial only in the Alembic migration for Postgres via sa.BigInteger with autoincrement). All enums stored by NAME (repo convention).
Schemas: `LiveClassCreate {course_id, lesson_id?, title, description?, scheduled_start (aware datetime), duration_minutes int 15..480, timezone?, recurrence_weekly: list[str]? (MO..SU), weeks: int? 1..12, settings?: LiveClassSettings}`, `LiveClassSettings` (the five settings + attendance_threshold_pct 0..100 default 60), `LiveClassOut` (all display fields + `server_ts: datetime` + `my_attendance?` + `can_start: bool` + `join_opens_at`), `JoinTokenOut {class_summary: LiveClassOut, room_name, jitsi_url, jwt, expires_in: int}`, `HeartbeatIn {client_ts: datetime}`, `PollCreate/PollOut/PollVoteIn`, `AttendanceRowOut`, `LiveNowOut`.

**Alembic env.py contract:** reads `DATABASE_URL` env (fallback settings), `target_metadata = Base.metadata` via `from app import models`. `alembic upgrade head` and `downgrade -1` must work against a scratch SQLite file DB.

- [ ] Steps (TDD): failing model tests (roundtrip each table, room_name unique, unique(class_id,user_id) attendance, unique(poll_id,user_id) votes) + migration test (`command.upgrade(cfg,'head')` then `downgrade(cfg,'base')` on `sqlite:///<tmp>` asserting tables exist/gone via inspector) → implement → `pip install sse-starlette==2.1.3 alembic==1.12.1` into the shared venv (alembic already pinned in requirements; install if missing) → all green + regression `tests/test_membership_models.py` → commit `feat(live): settings, alembic baseline, live-class models + migration`.

---

### Task 3: Jitsi token service + session router (start/end/join-token/heartbeat) + service + events

**Files:**
- Create: `app/services/jitsi_token_service.py`, `app/services/live_class_service.py`, `app/routers/live_class_session.py`
- Modify: `app/main.py` (mount `app.include_router(live_class_session.router, prefix="/api/v1/live", tags=["Live Classes"])` — ONE `/api/v1/live` prefix shared by all live routers)
- Test: `backend/tests/test_live_tokens.py`, `backend/tests/test_live_session.py`

**Interfaces (produced):**
```python
# jitsi_token_service.py
mint_jitsi_jwt(*, user, live_class, moderator: bool) -> tuple[str, str]  # (jwt, jti)
  # claims exactly per spec §6.2: iss/aud/sub = settings.JITSI_JWT_APP_ID,
  # room = live_class.room_name, jti = uuid4 hex, iat/nbf now,
  # exp = live_class.scheduled_end + 30min (as unix ts),
  # context.user{id: str(user.id), name, email, avatar: "", moderator: "true"/"false"},
  # context.features{screen-sharing/recording: "true" iff moderator, livestreaming/transcription: "false"}
  # HS256 via PyJWT with settings.JITSI_JWT_SECRET; raises RuntimeError if secret blank.

# live_class_service.py
generate_room_name() -> str                      # "si-" + secrets.token_hex(4)
log_event(db, class_id, user_id, event, payload=None)  # LiveClassEvent row, no commit
user_can_access_class(db, live_class, user) -> bool    # instructor_id match, admin/superadmin,
                                                       # or enrolled (Enrollment enrolled status) in course_id
finalize_attendance(db, live_class) -> int             # sets present = accumulated_seconds >=
                                                       # threshold_pct% of (scheduled duration), returns rows updated
apply_heartbeat(db, attendance, now) -> int            # delta = min((now - last_heartbeat_at).seconds, 90)
                                                       # if last is None: delta 0, set first fields; returns delta
```
Router endpoints (response_model'd, per spec §5): `POST /classes/{id}/start` (assigned instructor or require_admin roles; idempotent — if already LIVE return current state 200 without new event; Redis lock key `live:class:{id}:startlock` via app.core.redis with Mock fallback tolerated), `POST /classes/{id}/end` (409 if not LIVE; finalize attendance; recording_status REQUESTED→PROCESSING if recording), `POST /classes/{id}/join-token` (rate limit 5/min/user via Redis INCR+EXPIRE key `rl:join-token:{user_id}` — on MockRedis fall back to a DB count of tokens issued in the last 60s; 403 + join.denied event for non-permitted; 409 for ENDED/CANCELLED; SCHEDULED joins allowed from T-15min for students, anytime for the instructor; mints JWT, inserts LiveClassJoinToken, upserts attendance stub, event join.token_issued, returns JoinTokenOut with `jitsi_url=settings.JITSI_PUBLIC_URL` and expires_in 900), `POST /classes/{id}/heartbeat` (participant with attendance row; 409 after end; applies delta; marks redeemed_at on first beat + join.redeemed event).

- [ ] Steps (TDD, tests written FIRST — cover): token claim matrix incl. exp = end+30m ±5s and moderator/features flip; jti uniqueness across two mints; join-token happy path for enrolled student (assert DB rows + payload shape) / 403 non-enrolled + join.denied logged / 409 ended / instructor allowed pre-window / student 409 before T-15 (assert detail mentions opens time) / rate limit trips on 6th call in a minute (freeze time or DB-fallback path); heartbeat math: two beats 60s apart accumulate 60±1, a 10-min gap accumulates only 90, first beat accumulates 0 and stamps first_joined_at; start idempotency (two starts → one class.started event); end finalizes present threshold (attendee at 61% of a 100-min class with threshold 60 → present True; 59% → False) → implement → green + regression webhook/membership suites → commit `feat(live): jitsi tokens + session lifecycle endpoints`.

---

### Task 4: Scheduling CRUD router + live-now + ICS

**Files:**
- Create: `app/routers/live_classes.py`
- Modify: `app/main.py` (mount with same `/api/v1/live` prefix)
- Test: `backend/tests/test_live_scheduling.py`

**Endpoints:** `POST /classes` (require_instructor; instructor must own the course — `course.post_author == user.id` unless admin; generates occurrences: one row, or `weeks × len(recurrence_weekly)` rows at the same local time via zoneinfo, all sharing a new LiveClassSchedule parent; each gets its own room_name; event per class), `GET /classes?scope=upcoming|past|live|course:{id}&page&page_size` (role-aware visibility: instructor → own; student → classes of courses they're enrolled in; admin/superadmin → all; ordered by scheduled_start), `GET /classes/{id}` (permitted per user_can_access_class; includes `server_ts=now`, my_attendance, recording availability, join_opens_at), `PATCH /classes/{id}` (assigned instructor/admin; 409 unless SCHEDULED; editable: title/description/times/settings), `DELETE /classes/{id}` (soft-cancel: status CANCELLED + deleted_at + event; 409 if ENDED), `GET /live-now` (LIVE classes visible to me), `GET /classes/{id}/calendar.ics` (permitted; `text/calendar` response, hand-rolled VCALENDAR with UID `liveclass-{id}@sashainfinity.com`, DTSTART/DTEND in UTC `...Z` format, SUMMARY escaped).

- [ ] Steps (TDD first): create one-off + weekly recurrence (2 weekdays × 3 weeks → 6 rows, distinct room names, same schedule_id, correct local-time→UTC conversion for Asia/Kolkata); non-owner instructor 403; student list scoping (enrolled sees, stranger doesn't); patch after start 409; cancel notifies-event; ICS bytes contain DTSTART in UTC and escaped summary; live-now filters status LIVE + visibility → implement (router ≤400 lines; helpers in live_class_service) → green → commit `feat(live): scheduling CRUD, live-now, ICS`.

---

### Task 5: Attendance + polls routers, SSE, reminders loop

**Files:**
- Create: `app/routers/live_class_attendance.py`, `app/routers/live_class_polls.py`, `app/services/live_reminders.py`
- Modify: `app/main.py` (mount both; start/cancel `live_reminders_loop()` task in lifespan beside the reconciliation task)
- Test: `backend/tests/test_live_attendance.py`, `backend/tests/test_live_polls.py`, `backend/tests/test_live_reminders.py`

**Attendance:** `GET /classes/{id}/attendance` (assigned instructor/admin; rows with user name/email, first_joined_at, accumulated minutes, present tri-state, live_participants summary), `GET /classes/{id}/attendance/export.csv` (StreamingResponse text/csv; columns name,email,first_join,total_minutes,present; logs attendance.exported event), `POST /classes/{id}/attendance/recompute {threshold_pct}` (updates settings + recomputes present on an ENDED class — powers the report page's threshold editor).

**Polls:** per spec §5 — create (draft), activate/close (single ACTIVE poll per class at a time: activating auto-closes any other ACTIVE), vote (participant with attendance row; 409 duplicate via unique constraint + IntegrityError net; 409 unless ACTIVE), list (role-aware: instructor all + tallies; student active + own vote + results iff show_results), `GET /classes/{id}/polls/{pid}/stream` — SSE via sse-starlette EventSourceResponse: subscribes Redis pub/sub channel `live:class:{id}`; on MockRedis falls back to yielding a snapshot event then keepalive comments every 15s (documented; tests assert the snapshot event shape `{type:"poll", poll: PollOut-dict}`). Publishers: activate/close/vote publish compact JSON to the channel (fire-and-forget, tolerate MockRedis no-op).

**Reminders (`live_reminders.py`):** async loop, 60s cadence, advisory-locked cycle (postgres key 931850, dedicated connection — copy reconciliation.py's `_run_cycle` lock pattern), per-class fault isolation: (a) classes with scheduled_start within [now, now+15min] and no `live:reminder:{id}` marker (Redis SETNX with TTL 2h; MockRedis fallback = LiveClassEvent existence check for event `reminder.sent`) → email enrolled students via EmailService (subject "Live class starting soon: {title}") + FCM broadcast through `app.core.firebase_admin` messaging helper guarded by try/except no-op + log event `reminder.sent`; (b) classes LIVE and no `golive` marker → event `class.live_broadcast` + FCM. NEVER raises out of the loop.

- [ ] Steps (TDD): CSV shape + export event; recompute flips present rows; poll lifecycle draft→active→closed; second activation closes first; duplicate vote 409; student list hides tallies when show_results false; SSE endpoint returns event-stream content-type and first snapshot frame parses to expected shape; reminders: seeded class 10-min out → one email-send recorded (monkeypatch EmailService) and second cycle sends nothing (idempotent) → implement → green + `tests/test_reconciliation.py` unregressed → commit `feat(live): attendance, polls + SSE, reminder loop`.

---

### Task 6: Recordings — intent endpoints, internal ingest, Bunny wiring, finalize worker

**Files:**
- Create: `app/routers/live_class_recordings.py`, `app/routers/live_class_internal.py`, `app/services/live_recording_service.py`, `deploy/scripts/finalize_recordings.sh`, `deploy/scripts/finalize_recordings.py`
- Modify: `app/main.py` (mount recordings under `/api/v1/live`; internal under `/api/v1/internal/live`), `.gitignore` (`deploy/recordings/`)
- Test: `backend/tests/test_live_recordings.py`

**Endpoints:** `POST /classes/{id}/recording/start|stop` (assigned instructor; records intent: recording_status REQUESTED / event recording.started|stopped; actual Jibri control is client-side per spec). Internal `POST /api/v1/internal/live/recordings` — guard: header `X-Internal-Token` constant-time-compared to settings.INTERNAL_TOKEN (503 if unconfigured, 403 mismatch) AND client host in (127.0.0.1, ::1, testclient) (403 otherwise); body `{class_id, file_path, size_bytes, duration_seconds}`; idempotent per class+file (skip if recording_video_id already set); calls `live_recording_service.ingest_recording`.

**`ingest_recording(db, live_class, file_path)`:** reads the file, uploads via the EXISTING bunny flow — read app/routers/bunny.py and REUSE its create+upload logic through a shared helper (extract the minimal upload function into live_recording_service by calling Bunny endpoints the same way; do NOT modify bunny.py) → on success set recording_video_id + AVAILABLE + event recording.available (+ EmailService notification to instructor "Class recording ready"); on failure after 3 attempts (tenacity-free simple loop with backoff) copy file into `uploads/live-recordings/` (create dir) → mark AVAILABLE with `settings["recording_fallback"]=true` and event; only if both paths fail → FAILED + send_payment_alert-style admin email (reuse EmailService.send_payment_alert as the generic ops alert — acceptable; note in report).

**Worker:** `finalize_recordings.py` (stdlib-only python3): scan `$JITSI_RECORDINGS_DIR` for `*.mp4` older than 120s and not yet marked (sidecar `.ingested` files), POST to `http://127.0.0.1:8000/api/v1/internal/live/recordings` with X-Internal-Token from env, on 200 write sidecar. `finalize_recordings.sh`: shellcheck-clean cron wrapper sourcing `deploy/.env.live`, calling the python file, logging to `logs/finalize_recordings.log`. Playback for users: recordings surface through class detail's existing fields — the web player consumes `recording_video_id` via the EXISTING authenticated bunny playback endpoint (`GET /api/v1/bunny/video/{id}/playback`) — verify that endpoint's access check covers course enrollment for this video id path and note findings; if it gates on course linkage that live classes lack, add a thin `GET /classes/{id}/recording-playback` endpoint in live_class_recordings.py that enforces user_can_access_class then delegates to bunny signing helpers.

- [ ] Steps (TDD): internal endpoint auth matrix (no token 503/403, wrong 403, non-loopback 403, happy 200); ingest success path with monkeypatched bunny HTTP → AVAILABLE + video id; bunny failure ×3 → fallback copy → AVAILABLE + flag; both fail → FAILED + alert; recording start intent requires assigned instructor; playback endpoint enforces enrollment (student of another course 403) → implement → shellcheck both scripts → green → commit `feat(live): recording intents, internal ingest, bunny wiring, finalize worker`.

---

### Task 7: Web core — API module, store, JitsiStage, DevicePrecheck, student pages + first vitest suites

**Files:**
- Create: `frontend/src/api/liveClasses.ts`, `frontend/src/store/liveClassStore.ts`, `frontend/src/components/live/JitsiStage.tsx`, `frontend/src/components/live/DevicePrecheck.tsx`, `frontend/src/components/live/ClassCountdown.tsx`, `frontend/src/components/live/LiveStatusBadge.tsx`, `frontend/src/components/live/RecordingBadge.tsx`, `frontend/src/pages/student/live-classes.tsx`, `frontend/src/pages/student/live-class-join.tsx`, `frontend/src/components/live/__tests__/JitsiStage.test.tsx`, `frontend/src/components/live/__tests__/ClassCountdown.test.tsx`
- Modify: `frontend/src/App.tsx` (routes `/student/live-classes`, `/student/live-classes/:id/join` — protected student routes per existing patterns; also `/live-classes` alias if a student dashboard nav exists), student dashboard nav (`nav-configs.ts` STUDENT nav + any dashboard entry — follow how My Courses appears), `frontend/src/api/axios.ts` noSlash list if needed (mirror /memberships handling for /live paths).

**Binding behavior:**
- `liveClasses.ts`: typed functions for every endpoint (list w/ scope, detail, joinToken, heartbeat, polls list/vote, liveNow, icsUrl builder). Types mirror backend response models exactly.
- `JitsiStage`: props `{jitsiUrl, roomName, jwt, isModerator, displayName, onApiReady?, onLeft, classId}`. Lazily injects `<script src="${jitsiUrl}/external_api.js">` once (cached promise); constructs `JitsiMeetExternalAPI` with configOverwrite/interfaceConfigOverwrite per spec §6.3 (students: prejoin off, start muted, restricted toolbar; moderator adds desktop/whiteboard/recording/mute-everyone); wires events (`videoConferenceJoined/participantJoined/participantLeft/endpointTextMessageReceived/recordingStatusChanged/readyToClose/errorOccurred`) into the store; starts a 60s heartbeat interval calling the API module; on unmount/leave: clear interval, final heartbeat, `dispose()`. Error event → styled fallback panel with retry.
- `DevicePrecheck`: getUserMedia mic level meter (AnalyserNode), cam `<video>` preview, speaker test tone button, Continue disabled until mic+cam permission resolved (allow continue-without-cam). All within existing card/button primitives.
- `ClassCountdown`: pure function `computeRemaining(serverTs, fetchedAtLocal, target, nowLocal)` exported for tests — offset = serverTs - fetchedAtLocal applied to nowLocal.
- Student list page: Upcoming (cards: title, course, countdown, Join button with the state machine locked→opens-in-Xm→Join→LIVE→ended→Watch recording), LIVE-now strip from live-now endpoint, Past with recording links. Join page: precheck → joinToken call → JitsiStage (student flags) → onLeft returns to list.
- CREATE the pure helper here (Task 8 reuses it): `frontend/src/components/live/joinButtonState.ts` exporting `joinButtonState(cls: {status, scheduled_start, recording_status?}, now: Date) -> {label, disabled, action: 'none'|'join'|'recording'}` covering locked / opens-in-Xm / join / live / ended-no-recording / watch-recording.
- vitest: set up `src/test-setup.ts` compatibility (exists); JitsiStage test with `window.JitsiMeetExternalAPI` mocked as vi.fn class — asserts constructor got jwt+roomName, unmount calls dispose + one final heartbeat (mock api module); ClassCountdown offset math cases (server ahead/behind, target passed).

- [ ] Steps: write vitest specs first where pure (countdown), component-after for stage → implement → `npx vitest run` green, type-check zero new → commit `feat(live): web core — api, store, JitsiStage, student experience + first vitest suites`.

---

### Task 8: Web instructor — dashboard, schedule form, console with dock, report

**Files:**
- Create: `frontend/src/pages/instructor/live-classes.tsx`, `frontend/src/pages/instructor/live-class-new.tsx`, `frontend/src/pages/instructor/live-class-console.tsx`, `frontend/src/pages/instructor/live-class-report.tsx`, `frontend/src/components/live/InstructorDock.tsx`, `frontend/src/components/live/AttendancePanel.tsx`, `frontend/src/components/live/PollPanel.tsx`, `frontend/src/components/live/RaiseHandList.tsx`, `frontend/src/components/live/__tests__/PollPanel.test.tsx`, `frontend/src/components/live/__tests__/joinButtonState.test.ts`
- Modify: `frontend/src/App.tsx` (four instructor routes, wrapped per existing instructor-protected pattern), `frontend/src/components/dashboard/nav-configs.ts` (INSTRUCTOR_NAV gains "Live classes" after My courses).

**Binding behavior:** dashboard tabs Upcoming/Live/Past with big Start button (→ console) and LIVE badges; New-class form per spec §8 (instructor's own courses from the existing instructor courses API — grep pages/instructor/courses.tsx for its source; datetime-local + timezone select defaulting Asia/Kolkata; weekly recurrence day-chips + weeks count; settings toggles); console = DevicePrecheck gate → grid `[JitsiStage | InstructorDock]`; dock tabs People (live count via getNumberOfParticipants 10s poll + AttendancePanel rows refreshed 15s + RaiseHandList from store + Mute all + Lobby toggle buttons calling stage commands), Polls (create form, activate/close, live result bars fed by SSE EventSource with 10s-poll fallback), Timer (elapsed since started_at + optional countdown to scheduled_end), Recording (switch → intent endpoint + `executeCommand('startRecording',{mode:'file'})`, status from recordingStatusChanged, students see RecordingBadge banner). End class = confirm dialog → end endpoint → navigate to report. Report page: attendance table, threshold editor calling recompute, CSV download (authenticated blob like invoice PDFs), recording status/player (existing video-player component with the playback endpoint URL).
Reuse the `joinButtonState` helper created in Task 7 (components/live/joinButtonState.ts).
vitest: PollPanel renders options, optimistic vote marks selection before response resolves (vi.mock on the api module); joinButtonState full six-state matrix (test file lives in this task).

- [ ] Steps: implement → vitest green, type-check zero new → commit `feat(live): instructor dashboard, schedule form, console dock, report`.

---

### Task 9: Flutter module

**Files (all under `flutter_app/`):**
- Modify: `pubspec.yaml` (add `jitsi_meet_flutter_sdk: ^10.2.0` — verify latest compatible major in pub cache docs; note exact chosen version), routing registration file (locate go_router config; add `/live-classes`, `/live-classes/:id`), DI/providers registration per module convention, `lib/core/config/app_config.dart` or equivalent (M-04: ensure dev flavor targets `http://10.0.2.2:8000`/localhost-style staging var, NEVER the prod URL silently — read the file, apply the minimal correct wiring, report what was wrong).
- Create: `lib/features/live_classes/data/live_class_api.dart` (dio), `data/live_class_repository.dart` + models (fromJson mirroring backend), `domain/` entities per convention, `presentation/live_class_list_screen.dart`, `presentation/join_live_class_screen.dart` (minimal precheck → repository.joinToken → JitsiMeet().join(JitsiMeetConferenceOptions(serverURL, room, token, configOverrides per role, featureFlags))), `presentation/live_class_detail_screen.dart` (recording via existing video player widget — locate it), `presentation/providers.dart` (Riverpod).
- Create tests: `test/features/live_classes/live_class_repository_test.dart` (json mapping incl. status enums + join payload), `test/features/live_classes/live_class_list_screen_test.dart` (renders upcoming card + countdown text from a fake repo).
- FCM deep link: read the existing FCM/notification handling in flutter_app (grep firebase_messaging); if present, register `class.live` payload → go_router push to join screen; if absent, add a documented TODO hook + note (do not build FCM infra from scratch).

**CAVEAT (binding):** no Flutter toolchain on this machine — code must be written strictly to the existing module conventions (READ two existing feature modules end-to-end first and mirror their file/naming/DI patterns exactly). Report compiles-untested status honestly.

- [ ] Steps: recon two modules → implement → self-review against conventions → commit `feat(live): flutter live-classes module (compile-untested locally)`.

---

### Task 10: CI, security hardening pass, docs

**Files:**
- Modify: `.github/workflows/deploy.yml` (quality job gains a `gitleaks` step: `uses: gitleaks/gitleaks-action@v2` with `GITHUB_TOKEN`, or dockerized `zricethezav/gitleaks:latest detect --no-git -s .` on self-hosted — pick what runs offline on the self-hosted runner; ADVISORY first run via continue-on-error with a comment saying flip to blocking after triage, because the tree is not yet proven leak-free), `CLAUDE.md` (Live Classes note under Notes for future work: architecture one-liner, file map, env vars, jitsi stack pointer)
- Create: `docs/LIVE_CLASSES.md` — architecture diagram (ASCII), env reference table, runbook (start/stop jitsi stack, rotate JITSI_JWT_SECRET step-by-step incl. restart order, recover stuck recordings via finalize script flags, common failures: lobby stuck / websocket 502 via Cloudflare orange-cloud / JWT clock skew), backup note (add `deploy/recordings` to the nightly backup routine — exact crontab line), future phases (spec §16 list), deviations summary, VPS smoke checklist (DNS grey-cloud → compose up → health_jitsi → smoke_jitsi → orange-cloud after WebRTC verified).

**Security checklist execution:** walk spec §12 item by item against the final tree; every item gets evidence (file:line) in the task report; failures become fixes in this task. Verify with greps: no `changeme` outside *.example; `JITSI_JWT_SECRET` never read outside config/token service; internal router loopback guard; nginx limit_req applied.

- [ ] Steps: implement → shellcheck all new scripts once more, full backend suite + vitest run → commit `feat(live): CI gitleaks step, security pass, LIVE_CLASSES docs`.

---

## Post-implementation (owner, manual — the VPS half)
1. DNS `live.sashainfinity.com` → server IP, **grey-cloud** initially.
2. `cp deploy/.env.live.example deploy/.env.live` + fill real secrets (openssl rand -hex 32 / 48).
3. `docker compose -f deploy/compose.live.yml --env-file deploy/.env.live up -d` on the VPS; run `deploy/scripts/health_jitsi.sh` then `smoke_jitsi.sh`; verify a two-browser join with lobby.
4. Reload edge nginx with the new conf; verify wss endpoints; then orange-cloud if desired.
5. Cron: finalize_recordings.sh every 2 min; add recordings dir to backups.
6. Merge branch when accepted; deploy via the normal CI path.
