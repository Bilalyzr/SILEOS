# Live Classes — Owner's Brief (verbatim spec)

Owner-supplied build brief, 2026-09-02. This is the authoritative spec for the
Live Classes feature. The Phase-0 recon deviations (repo wins) are recorded in
`2026-09-02-live-classes-deviations.md` alongside this file and OVERRIDE the
corresponding details below.

## Product definition — "Live Classes" (Teachmint-inspired)

An instructor must be able to run a live, interactive online class without
leaving one console screen and with a maximum of two clicks from dashboard to
live. Students join from their course or dashboard in one tap.

### Instructor stories
- Schedule a class for a course/lesson (title, date, time, timezone, duration,
  optional weekly recurrence) in one form.
- Upcoming / Live / Past on one dashboard with a prominent Start class button.
- Device pre-check (mic/cam/speaker) before entering.
- In class: Jitsi video stage, mute all, screen share, built-in whiteboard,
  chat, raise-hand awareness, class timer, live attendance panel, quick polls —
  all in one dock beside the video, never a separate tab.
- Recording toggle with one switch; "This class is being recorded" banner for
  students when on.
- After class: auto attendance summary (who joined, how long, present/absent by
  configurable % threshold), CSV export, recording attached to class & course.
- Copyable join link that is useless alone; access verified server-side.

### Student stories
- Upcoming live classes for enrolled courses with countdown; Join activates 15
  minutes before start; LIVE badge for running classes.
- Quick device check; join muted by default; raise hand, chat, answer polls.
- Recordings appear on the class page and course afterwards (enrollment-gated,
  signed HLS like every other video).

### Admin/SPOC (minimal)
- Admins see all classes, can cancel abusive ones, view attendance reports.

### UX principles (instructor simplicity is the #1 requirement)
- Hide Jitsi complexity: no invite dialog, no personal rooms, no settings
  sprawl. Pre-configure everything.
- One console screen (`/instructor/live-classes/:id/console`) holds video +
  instructor dock. Big obvious buttons; every instructor action ≤2 clicks from
  the dashboard. Attendance automatic; manual adjustment is a fallback.

## Architecture decisions (locked)
1. Media engine: self-hosted docker-jitsi-meet (official stable compose), a
   stateful single instance on the data-tier side (NOT colour-duplicated, NOT
   part of the blue/green switch), on the existing `sasha-net` network.
2. Jitsi auth: `AUTH_TYPE=jwt`. Backend mints short room-scoped JWTs; `room`
   claim pins the token to the exact class room. Instructor tokens carry
   `context.user.moderator=true`. Dedicated `JITSI_JWT_SECRET` — never the
   platform `JWT_SECRET`.
3. Web embed: official Jitsi Meet IFrame API (`external_api.js` from the Jitsi
   web host) inside a React `<JitsiStage>`. No lib-jitsi-meet.
4. Mobile: official Jitsi Flutter SDK with the same server-minted JWT + flags.
5. Whiteboard: Jitsi's built-in Excalidraw (config-enabled). No custom board.
6. Raise-hand / dock signaling: Jitsi raise-hand + endpointTextMessage events
   over the conference data channel. No extra server infra.
7. Polls: server-backed with SSE via Redis pub/sub for live results.
8. Attendance: server-side truth = join-token redemption + 60s heartbeats
   (server-computed deltas, 90s cap per beat). Client events enrich only.
9. Recordings: Jibri → shared volume → finalize worker → existing Bunny
   pipeline (`POST /api/v1/bunny/video`) → `recording_video_id` on the class →
   existing signed-HLS player with enrollment checks. Bunny failure fallback:
   uploads volume via nginx; never lose the file; 3 retries then failed+alert.
10. Instructor dock panels are native React talking to the platform API.

## Data model (adapted: Integer PKs/FKs per repo — see deviations file)
Tables: `live_class_schedules`, `live_classes`, `live_class_join_tokens`,
`live_class_attendance`, `live_class_polls`, `live_class_poll_votes`,
`live_class_events` — fields, enums, uniques, and indexes exactly as the
owner's brief §4 (UUID columns become Integer ids; jti/room stay opaque
strings; timestamps stored UTC; JSON not JSONB; portable for SQLite tests).
`room_name` = `si-<random8>` server-generated, never derived from course id.
Settings JSON default: `{lobby_enabled: true, start_muted: true, allow_chat:
true, allow_share: true, record: false, attendance_threshold_pct: 60}`.
Event names: class.created/updated/started/ended/cancelled,
join.token_issued/redeemed/denied, attendance.exported,
poll.created/activated/closed/voted,
recording.started/stopped/available/failed, moderation.mute_all,
moderation.lobby_toggled.
Alembic is the only schema path for this feature: baseline stamp of current
schema, then one migration `add_live_class_tables` with tested downgrade.

## Backend API contract (mount under /api/v1/live)
Routers ≤~400 lines each: `live_classes.py` (CRUD/scheduling),
`live_class_session.py` (start/join-token/heartbeat/end),
`live_class_attendance.py`, `live_class_polls.py`,
`live_class_recordings.py`, `live_class_internal.py` (X-Internal-Token +
loopback). Full endpoint table, guards, status rules, and Redis keys per the
owner's brief §5, including: join-token rate limit 5/min/user; join-token for
ended/cancelled → 409; non-enrolled student → 403 + join.denied event; start
idempotent via Redis lock; heartbeat 409 after end, ≤90s delta cap; SSE stream
`GET .../polls/{pid}/stream` on channel `live:class:{id}`; `GET /live/live-now`;
`GET .../calendar.ics`; recording start/stop intent endpoints; internal
`POST /internal/live/recordings` triggering the Bunny upload job.

## Jitsi integration
Env (deploy/.env.live, example committed): JITSI_PUBLIC_URL,
JITSI_JWT_APP_ID=sashainfinity, JITSI_JWT_SECRET (64+), JITSI_RECORDINGS_DIR,
INTERNAL_TOKEN (48+), DEFAULT_TIMEZONE=Asia/Kolkata.
Jitsi JWT (pyjwt HS256): iss/aud/sub = app id; room = room_name; jti uuid;
exp = scheduled_end + 30min; context.user {id,name,email,avatar,moderator};
context.features {screen-sharing, recording, livestreaming:false,
transcription:false}. Instructor: moderator+recording true. Student: all false.
IFrame API per brief §6.3 (configOverwrite: prejoin off, students start muted,
disableDeepLinking, whiteboard on, lobby from settings; TOOLBAR_BUTTONS
restricted per role; commands muteEveryone/startRecording/stopRecording/
sendEndpointTextMessage/hangUp/toggleLobby; events per list; participant count
poll 10s; unmount = hangup + final heartbeat). Lobby default ON.

## Recording pipeline
Per brief §7: moderator-triggered file recording; Jibri volume; finalize
worker scans every 2 min → internal endpoint → Bunny upload → available +
notification; fallback to uploads volume; retry 3× then failed + admin alert.

## Web frontend
Routes: /instructor/live-classes (+/new, /:id/console, /:id/report),
/student/live-classes (+/:id/join), recording section on class/course pages
via the EXISTING video player. Components: JitsiStage, DevicePrecheck,
InstructorDock, AttendancePanel, PollPanel, RaiseHandList, ClassCountdown,
RecordingBadge, LiveStatusBadge. Store: liveClassStore. React Query keys
['live-classes', scope]; SSE with 10s-poll fallback; countdown uses server_ts
offset; Join button state machine locked → opens-in-Xm → join → live → ended
→ watch-recording.

## Mobile (Flutter)
Module `flutter_app/lib/features/live_classes/` (data/domain/presentation),
dio + Riverpod + go_router paths /live-classes, /live-classes/:id; join via
the official Jitsi Flutter SDK (serverURL, room, token, flags, muted defaults
per role); FCM class.live deep link; screens LiveClassListScreen,
JoinLiveClassScreen, LiveClassDetailScreen; dev flavor must not target
production (audit M-04).

## Infra
`deploy/compose.live.yml` (web/prosody/jicofo/jvb/jibri + optional coturn
profile; only web on 127.0.0.1:8080 and coturn publish; sasha-net; volumes
./jitsi + recordings; healthchecks; env-file secrets only).
`deploy/nginx/conf.d/live.conf` vhost (websockets /xmpp-websocket,
/colibri-ws/, long read timeout) + `live_api` limit_req zone applied to
/api/v1/live/. CSP gains frame-src/script-src for the live host.
`deploy/scripts/health_jitsi.sh`; IDS scope; reminders (T-15 email/FCM +
class.live broadcast) via the repo's advisory-locked asyncio-loop pattern;
recordings volume added to backups.

## Testing
pytest: token claims/exp/jti; join flow (enrolled/403+event/409/rate limit);
heartbeat math incl. caps and threshold; polls incl. duplicate vote + SSE
payload; start idempotency; cancel; ICS; migration up/down.
vitest (first real suites): JitsiStage with mocked external API; ClassCountdown
offset math; PollPanel optimistic vote; Join button state machine.
Flutter: widget tests list/join; repository mapping unit tests.
CI: suites run on existing gates; gitleaks step added; shellcheck clean.

## Security checklist (all must pass)
Per owner's brief §12 verbatim: env-only secrets + prod fail-fast; room-pinned
JWTs; student tokens cannot record/screen-share; platform JWT + enrollment
guards on all /live endpoints; internal endpoint token+loopback; nginx rate
limits applied; opaque room names; no enumeration; PII-conscious exports with
event logging; consent banner; enrollment-gated recordings; Jitsi internals not
published; legacy root stack untouched; exactly one new compose file.

## Out of scope
Breakout rooms, YouTube/Facebook streaming, SIP, custom whiteboard, persistent
chat history, AI summaries, mobile instructor authoring, multi-JVB/Octo, HA.
Documented as future phases in docs/LIVE_CLASSES.md.
