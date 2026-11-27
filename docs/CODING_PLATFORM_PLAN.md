# Live Coding Platform: Implementation Plan

Status: **Phase 0 and Phase 1 done.** **Phase 2 done** (lesson practice blocks, drafts, curriculum editor). **Phase 3 done** (analytics, instructor report, learner progress; certificate setting and per-challenge weights still open). **Phase 4 built on dev** (live class challenges, results board, solution reveal; gradebook link still open). **Phase 5 built on dev** (review comments and queue, pair rooms over WebSocket; production nginx change still needs approval). **Phase 6 built on dev** (pacing, queue backpressure, queue metrics; HTTP load test not run). Owner: to be assigned.
Last reviewed: 2026-11-26.

Goal: let students write, run, test and submit code inside SILEOS, during live classes and while watching recorded lessons, with automatic progress saving and instructor analytics.

---

## 1. What already exists

Build on these rather than replacing them.

| Area | Existing piece | Location |
|---|---|---|
| Challenge model | `CodingChallenge`: slug, statement, allowed languages, starter code, time and memory limits, attempt cap, draft or published status | `backend/app/models/coding_assessment.py` |
| Test cases | `CodingTestCase`: ordinal, visible or hidden, input, expected output, comparison mode, weight | same file |
| Submissions | `CodingSubmission`: language, source hash, idempotency key, status, score, passed and total cases, attempt number, judge version | same file |
| API | Course challenges, learner challenges, submit (returns 202), submission detail | `backend/app/routers/coding_assessments.py` |
| Service | Editor and learner logic, submit, job claim, complete and fail | `backend/app/services/coding_assessment_service.py` |
| Judge | Leases jobs, runs each case in Judge0 with networking off, six languages | `code-judge-worker/worker.py` |
| Internal judge API | Worker callbacks | `backend/app/routers/coding_judge_internal.py` |
| Student UI | Workspace and practice pages | `frontend/src/pages/student/coding-workspace.tsx`, `code-practice.tsx` |
| Instructor UI | Authoring studio | `frontend/src/pages/instructor/coding-studio.tsx` |
| API client | Coding calls | `frontend/src/api/coding.ts` |
| Certificates | Coding referenced in certificate logic | `backend/app/services/certificate_service.py` |
| Tests | Coding assessment tests | `backend/tests/test_coding_assessments.py` |

## 2. Gap analysis

| Requirement | Status | Gap |
|---|---|---|
| Syntax highlighting and autocomplete | Missing | Editor is a plain `<textarea>` |
| Multiple languages | Partial | Six languages, all through Judge0 |
| Code run and test in browser | Partial | Works through the judge, but Judge0 is not running on dev |
| Error handling and debugging | Partial | Raw output only, no line mapping |
| Automated test validation | Present | Hidden and visible cases |
| Performance scoring | Partial | Per-case time and memory not confirmed as stored |
| Submission history and analytics | Partial | History exists; instructor metrics need checking |
| Pause a lesson, practise, resume | Missing | No embedded coding step in lessons |
| Automatic progress saving | Missing | No draft storage |
| Live class exercise sharing | Missing | Live classes have polls only |
| Collaborative coding and live review | Missing | No realtime layer |
| Student certificate and progress view | Partial | Certificate hook exists, no coding criteria |

## 3. Architecture decisions

**Execution stays in the sandbox.** Learner code never runs inside the backend. The judge worker remains the only executor, with networking disabled and CPU and memory limits applied.

**Editor: Monaco.** Use `@monaco-editor/react`, lazy-loaded so it stays out of the main bundle. Monaco gives highlighting, autocomplete and diagnostics. Keep the textarea as a fallback for weak connections.

**Drafts: server-stored.** Drafts live in the database, not only in the browser, so they survive a device change. localStorage is a fast local cache.

**Realtime: deferred.** Live results start with polling. Collaborative editing needs a stateful WebSocket layer and is deferred to Phase 5.

**Lessons: timestamped practice blocks.** A practice block attaches to a lesson at a timestamp. The player pauses there, opens the editor beside the video, and resumes on completion.

## 4. Phases

### Phase 0: Infrastructure (size S, about 1 day)

**Result (2026-11-26, dev):** Judge0 runs on the dev stack and submissions are scored end to end through the backend and the worker. Python, JavaScript, TypeScript, C and C++ pass. Java is blocked (see below).

What was built:
- `docker-compose.judge0.yml` (added to `COMPOSE_FILE`): `judge0-server`, `judge0-workers`, `judge0-db` and `judge0-redis`. Judge0 sits on an internal network and is not published to the host. `code-judge-worker` now starts by default.
- `judge0/judge0.conf` (gitignored, holds secrets): Judge0 runtime settings, loaded with `env_file`.
- `.env`: `CODE_RUNNER_TOKEN`, `JUDGE0_AUTH_TOKEN`, `JUDGE0_URL` and database passwords.
- `code-judge-worker/worker.py`: `MIN_MEMORY_MB` floor of 1024 MB for JavaScript and TypeScript.

Problems found and how they were fixed:
| Symptom | Cause | Fix |
|---|---|---|
| Judge0 connects to `localhost` | Config not applied | Use `env_file` instead of a mounted file |
| Every run: `Internal Error … /box/script.py` | isolate `--cg` needs cgroup v1; host is cgroup v2 | `ENABLE_PER_PROCESS_AND_THREAD_*=true` so Judge0 uses rlimits |
| Node aborts or times out under 512 MB | Node reserves far more virtual memory than it uses | 1 GB floor for JavaScript and TypeScript |
| TypeScript compile limit | Compile uses `MAX_CPU_TIME_LIMIT` (default 5 s) | Raised to 15 s, wall 20 s |
| Java `pthread_create EAGAIN` | JVM thread and address-space needs exceed Judge0 caps (max 120 processes or threads) | Not fixed. See below. |

Verification:
- Direct Judge0 checks: 16 of 17 pass. The failing one is Java.
- End to end (real database, service layer, worker and Judge0): Python, JavaScript, TypeScript, C and C++ each score 100 (2 of 2 cases).
- Sandbox: network is blocked, CPU time limit is enforced, runtime and compile errors are reported, and huge output is capped.

Known limitations:
- **Java is blocked.** The JVM fails to create threads under Judge0's process cap. Tried and failed: smaller heap and code cache, serial GC, one GC thread, and a larger address-space limit. Options: (a) run Java on a host with cgroup v1 or with a newer Judge0 (needs approval, as it changes the host), (b) drop Java from the challenge language list until fixed. Recommended: (b) now, then (a) later.
- **Memory is virtual, not resident.** Judge0 limits address space (RLIMIT_AS) because cgroup accounting is off on this host. Programs can use more real RAM than the challenge limit suggests.
- **Process cap is high.** `MAX_PROCESSES_AND_OR_THREADS=120` is Judge0's maximum. Fork-bomb protection is weaker than with cgroups, but still bounded.
- **Privileged containers.** `judge0-server` and `judge0-workers` run privileged. Keep them on this host and off public networks.
- **Compose profile.** The `coding` profile is overridden in `docker-compose.judge0.yml`, so the worker runs by default on dev.

Still open for Phase 0: the Java decision, and a production review of privileged containers.

### Phase 1: Editor upgrade (size M)

**Result (2026-11-26, dev):** Monaco is in place on the workspace page, with error markers on failing lines. A plain textarea remains as a fallback.

What was built:
- `monaco-editor` 0.57.0, pinned. (0.58.0 was excluded: it was published three days before this work.)
- `frontend/src/components/coding/CodeEditor.tsx`: Monaco wrapper. Loaded lazily by the workspace page, so it downloads only on that page. Only the six judge languages and their workers are registered.
- Autocomplete: keywords per language, plus identifiers from the starter code.
- Error markers: `errorLocations.ts` reads line and column from judge stderr for Python, JavaScript, TypeScript, C, C++ and Java. Markers clear after a run with no errors.
- Fallback: `VITE_CODING_EDITOR=textarea` at build time restores the textarea. An error boundary also falls back if Monaco fails to load.
- `acceptSuggestionOnEnter` is off, so pressing Enter never changes a learner's words.

Verification:
- Unit tests: 11 passing (error parsing, mode flag, identifiers).
- Typecheck: no new errors. The 3 pre-existing `Home.tsx` errors remain.
- Build: `CodeEditor` chunk is 2.8 MB raw and about 730 KB gzipped. It loads only on the workspace page. The TypeScript worker (7 MB) loads only for JavaScript and TypeScript challenges.
- Browser (Playwright, dev stack, 9 checks): the editor renders, typed code is held, a failing run shows an error squiggle on line 1, a passing run scores 2 of 2, and markers clear.

Problems found during testing:
- **Judge worker throttled (fixed in backend and edge).** The general rate limit caps each client at 1000 requests per hour. The worker polls about once a second, so it hit the cap after about 17 minutes and submissions stuck in `queued`. Fix: `/api/v1/internal/coding/` is exempt from the general limit, since every call carries the runner token. The dev edge also returns 404 for these routes, because the worker calls the backend directly.
- **Monaco key handling.** Enter accepted suggestions, which changed typed words. Fixed by turning off `acceptSuggestionOnEnter`.

Still open:
- Mobile layout is not checked.
- Live class and lesson embedding are Phases 2 and 4.
- The Playwright run leaves its test submissions in the dev database.

### Phase 2: Drafts and lesson-embedded practice (size M)

**Result (2026-11-26, dev):** Instructors attach published challenges to a lesson in the curriculum editor. The learner's video pauses at the set time and opens the workspace. Drafts are saved to the account.

What was built:
- **Data:** `lesson_coding_blocks` (lesson, challenge, timestamp in seconds or NULL for after the lesson, instructions) and `coding_drafts` (one row per learner, challenge and language). Both are created at backend start; `backend/migrations/20261126_lesson_coding_blocks.sql` documents them.
- **API:** `GET` and `PUT /api/v1/utporul/coding/courses/{course}/lessons/{lesson}/blocks`, and `GET` and `PUT /api/v1/utporul/coding/challenges/{slug}/draft`.
  - Editors replace the lesson's blocks. Only published challenges from the same course are accepted. A challenge can't appear twice at the same time.
  - Learners read blocks only if enrolled, and see only published challenges.
  - Drafts belong to the learner. One learner can't read another's.
- **Curriculum editor:** a "Coding practice" section in each video lesson. Pick a published challenge, give a time in seconds (or leave it empty for after the lesson), add instructions, and save.
- **Lesson player:** when playback reaches a timed block, the video pauses and a dialog opens with the workspace. "Continue lesson" closes it and resumes. Escape or the close button also closes it. A block opens once per view. Untimed blocks are listed under the video as "Practice in this lesson".
- **Workspace:** the judge workspace is now a component, `CodingWorkspace`, used on the full page and in the lesson dialog. Drafts autosave one second after typing. The copy on this device is written first, so typing survives a dropped connection.

Verification:
- Backend: 16 tests pass. These cover attaching and listing blocks, enrollment rules, draft-only challenges, cross-course attachment, duplicates, negative times, replacing blocks, draft privacy, and draft language and size limits.
- Frontend: 19 unit tests pass, covering trigger order, finished blocks, timestamp formatting and draft keys. Typecheck shows only the 3 existing `Home.tsx` errors.
- Browser (Playwright, dev, 11 checks): the instructor adds a block at 3 seconds. The student sees it, the video pauses at 3 seconds, the draft survives a reload, a correct answer scores 2 of 2, "Continue lesson" resumes the video, and the block does not reopen.

Limits and follow-ups:
- Only video lessons show the practice section. Text lessons do not.
- Each block takes one challenge. Reusing a challenge in several lessons is allowed.
- The dialog does not check whether the learner watched up to the timestamp, so a learner who seeks past it still gets the block.
- Practice is for learning only. Grading and live class exercises are Phase 4.
- The browser test expects a clean lesson. Saving again adds another row and can hit the duplicate check.

### Phase 3: Analytics and performance scoring (size M)

- Store per-case time and memory from Judge0 results on each submission.
- Scoring: pass rate is primary. Time and memory act as tie-breakers, with weights set per challenge.
- Instructor metrics endpoint: pass rate, attempts, common failing cases, and time to first pass per challenge.
- Instructor report view in `coding-studio.tsx`, with CSV export through the existing CSV safety helpers.
- Student progress view: completed and attempted challenges, scores, and history.
- Coding completion criteria for certificates, behind a per-course setting.

**Done when:** an instructor can see pass rates and failing cases for a challenge, and a student can see their scores over time.

**Phase 3 result (built on dev, 2026-11-27):**
- Per-case time and memory were already stored on `CodingCaseResult` by the Phase 0 judge path. No schema change was needed.
- Ranking: score first, then total judge time, then peak memory, then submit time (`ranking_key` in `coding_analytics_service.py`). Per-challenge weights are not built yet; the order is fixed.
- `GET /utporul/coding/courses/{id}/metrics`: pass rate, learners attempted and passed, total submissions, median minutes to first pass, top failing test cases (ordinal, visibility and failure counts only, never inputs or expected outputs), and a leaderboard of the top 50 learners.
- `GET /utporul/coding/courses/{id}/metrics.csv`: one row per learner per challenge, cells sanitised by `csv_safety`. Editors only.
- `GET /utporul/coding/learner/progress`: the learner's own challenges, best scores, attempts, first pass and the last 20 submissions.
- Frontend: `InstructorReport` in Coding Studio; a progress panel on `/coding`; formatting helpers in `metricsFormat.ts`.
- Tests: 5 backend tests in `tests/test_coding_analytics.py`; 4 frontend formatting tests. The full Vitest suite passed (23 tests) and the production build succeeded.
- Not done: the certificate completion criteria (a per-course setting) and per-challenge tie-break weights. Both stay open for a follow-up.
- Not done: browser (Playwright) run of the new screens. Not committed or pushed.

**Phase 4 result (built on dev, 2026-11-27):**
- Data: `live_coding_challenges` (one row per push: status open or closed, graded flag, instructions, model solution, reveal time) and `live_coding_submissions` (link from a live submission to the judge's `coding_submissions` row). Both are new tables, so no ALTER is needed; `create_all` creates them.
- Rules: only the assigned instructor or an admin can push, close or reveal. A push must be a published challenge from the class's own course. Only one challenge can be open per class. Learners must have joined the class (attendance row) to submit. Submissions are rejected once the challenge is closed or the class has ended. Instructors cannot submit.
- Model solution: stored with the push and returned to learners only after the instructor reveals it, which requires the challenge to be closed first.
- Results board: polled every 5 seconds. Instructors see the full board. Learners see only their own row and a summary count. Source code is never shown on the board.
- Grading: a graded session tags each live submission with `counts_for_grade`. It does not write to the gradebook yet, so that open decision remains.
- API under `/api/v1/live/`: `classes/{id}/coding-challenges` (list, push), `coding-challenges/{id}` (learner view), `{id}/submissions`, `{id}/board`, `{id}/close`, `{id}/reveal`.
- Frontend: the instructor dock has a "Coding" tab (`LiveChallengePanel`, staff mode). The learner join page shows the open challenge under the stage, using `CodingWorkspace` with a `submitOverride` so submissions go through the live endpoint.
- Tests: 5 backend tests in `tests/test_coding_live.py` (26 coding tests pass in total). 4 frontend tests in `LiveChallengePanel.test.tsx`.
- Not done: real-time push over SSE (polling is used instead), gradebook integration for graded sessions, and a Playwright run of the live flow with Jitsi.

### Phase 4: Live class exercises (size M to L)

- Instructor pushes a published challenge to a live session, following the pattern in `live_class_polls.py`.
- Students see the challenge in the live view and submit as normal.
- Live results board with polling, refreshing every few seconds.
- Grading is optional per session. Ungraded practice still records submissions.
- Instructor can reveal a model solution after the session.

**Done when:** an instructor can push a challenge mid-class, watch submissions arrive on a results board, and close it.

### Phase 5: Collaboration and live review (size L, deferred)

- Add a WebSocket endpoint in FastAPI, or a small y-websocket service.
- Use Yjs with `y-monaco` for shared editing in a session room.
- Line-anchored review comments stored as rows linked to a submission.
- Instructor review queue.

**Done when:** two students can edit the same file and an instructor can leave a comment on a specific line of a submission.

**Note:** this phase adds a stateful realtime service with its own scaling and failure modes. Start only after Phases 0 to 4 are stable and students ask for it.

**Phase 5 part A result (built on dev, 2026-11-27): review comments and queue.**
- Data: `coding_review_comments` (line-anchored, open or resolved) and `coding_review_requests` (one per submission). New tables, created by `create_all`.
- Rules: the submitter and course editors can read and comment on a submission; others get 404. Line numbers must fall inside the submitted source. Only the submitter can request a review, and only for a finished run. Only course editors can resolve comments or mark a review done.
- API under `/api/v1/utporul/coding/`: `submissions/{id}/comments` (list, add), `comments/{id}/resolve`, `submissions/{id}/review-request`, `submissions/{id}/review-done`, `courses/{id}/review-queue`.
- Frontend: `ReviewThread` (code with line gutters and comments) is in the learner's result panel and the instructor queue. `ReviewQueuePanel` is in Coding Studio.
- Tests: 3 backend tests in `tests/test_coding_review.py` (29 coding tests pass in total). 3 frontend tests in `ReviewThread.test.tsx`.
**Phase 5 part B result (built on dev, 2026-11-27): shared editing over a FastAPI WebSocket with Redis fan-out.**
- Data: `coding_collab_rooms` (challenge, owner, language, invite code) and `coding_collab_members` (cap 4). The snapshot and tickets live in Redis.
- Access: a learner opens a room for a published challenge and shares the invite code. Joining needs the code plus enrolment in the course, so rooms cannot be found by guessing ids. Only members can get a socket ticket. Tickets last 60 seconds and are single use.
- Socket: `/api/v1/utporul/coding/collab-rooms/{id}/ws?ticket=…`. Binary frames only: byte 0 is 0 (update) or 1 (snapshot), then the Yjs bytes. Frames are capped at 512 KB. Malformed frames close with 1003. A forged or reused ticket closes with 4401.
- Fan-out: each uvicorn worker keeps its own sockets. Frames are published to Redis channel `coding:collab:{room}` and relayed to the other workers' sockets, excluding the sender. Without Redis (tests), an in-memory bus is used, which is correct only for one worker.
- Late joiners: the latest snapshot is stored in Redis for 7 days, and a new socket receives it first. Each client also sends a snapshot after changes (debounced 1.5 s), so a rejoining client catches up.
- Frontend: `CollabEditor` (Monaco with `y-monaco`) and `PairPanel`, which is shown under each coding workspace. Only the room owner seeds starter code, and only when no saved text arrives. The room has no submit button; to submit, the learner copies the text into the normal editor.
- Infrastructure: `yjs` 13.6.18, `y-monaco` 0.1.6 and `y-protocols` 1.0.6 are pinned. A Vite alias maps `monaco-editor/esm/vs` so y-monaco and the app share one Monaco. The dev nginx edge has a new location for `/api/v1/utporul/coding/collab-rooms/` with WebSocket headers.
- Tests: 5 backend socket and room tests (`tests/test_coding_collab.py`), 1 cross-worker fan-out test against real Redis (`tests/test_collab_fanout.py`), 4 frame and URL tests. 35 coding backend tests pass. The production frontend build succeeds.
- Production nginx edge (2026-11-27, approved): the live edge is `deploy/nginx/conf.d/10-app.conf` (the blue/green edge that `deploy.sh` validates and reloads). It now has a `/api/v1/utporul/coding/collab-rooms/` location with Upgrade headers, 1-hour timeouts and the general `api` rate-limit zone. It passes `nginx -t` with the production upstream names mapped. An earlier commit also added the same location to `nginx/conf.d/default.conf`, which the blue/green deploy does not use; that is harmless. The host TLS proxy in front of the edge (aaPanel or Cloudflare) must also pass WebSocket upgrades. It runs on the production server and was not checked from here. Two-browser test on dev (2026-11-27), through the dev nginx edge with two separate learner sessions: 8 of 8 checks passed. The checks were: start a room and get a code, connect, partner joins, both listed, edits sync both ways, a reloaded partner rejoins and gets the saved text, and edits keep syncing. Test rooms, Redis snapshots and the extra learner were removed; the learner account could not be deleted because of foreign keys, so it was deactivated. Not done: presence (who is online) is not built. Without Redis persistence, a flushed Redis loses saved snapshots until someone reconnects.

### Phase 6: Hardening (runs alongside all phases)

- Per-user rate limits on runs and submissions.
- Queue backpressure in the judge worker, with a clear message when the queue is full.
- Load test at live-class scale, for example 100 students submitting within one minute.
- Tests:
  - Pytest for each new route and service rule.
  - Vitest for editor and autosave logic.
  - Playwright for the lesson practice flow.
- Monitoring: queue depth, judge latency, failure rate, in the existing observability router.

**Phase 6 result (built on dev, 2026-11-27):**
- Pacing: a learner can make 6 new submissions per minute. The 7th returns 429 with `Retry-After: 60`. Replaying an existing idempotency key still returns the original submission. The check runs under the user row lock.
- Backpressure: when 500 judge jobs are queued or leased, new submissions return 503 with `Retry-After: 60` and a plain message. Both limits are constants in `coding_assessment_service.py`.
- Monitoring: `services/coding_ops.py` adds these gauges to the existing `/metrics` scrape: `sasha_coding_queue_depth` (queued and leased), `sasha_coding_queue_oldest_seconds`, `sasha_coding_completed_last_hour`, `sasha_coding_error_ratio_last_hour`, and `sasha_coding_judge_latency_seconds` (p50 and p95). No learner data is exposed.
- Tests: 4 backend tests in `tests/test_coding_hardening.py`, covering pacing, a full queue, a 100-learner burst (all 100 accepted), and health numbers. 4 new Vitest tests cover autosave: debounce, device-only fallback, and restore order. 39 backend coding tests and 34 frontend coding tests pass.
- HTTP load test on dev (2026-11-27), against the backend port directly, with 25 concurrent clients. A throwaway utporul course held one challenge and 100 labelled learners. **Caveat:** the dev backend was still running the code from 26 Nov (it has no auto-reload), so pacing and backpressure were not active during this run. Each learner submitted once, so pacing would not have triggered, but the run should be repeated now that the backend has been restarted. Results:
  - All 100 submissions returned 202. No 429s or 503s.
  - Submit latency: p50 1.75 s, p95 3.70 s, max 4.92 s.
  - All 100 were judged `passed`. The queue drained in 218 s, about 2.2 s per job. The likely cause is the worker's concurrency (not checked yet). At this rate, 100 students submitting in the same minute would wait about 3.6 minutes for the last result. This is the main bottleneck for live-class scale.
  - Test data was removed afterwards. Dev counts were back to 31 submissions and 9 utporul courses.
- Not done: the `/metrics` endpoint has no test (it needs the observability token). The Playwright lesson test from Phase 2 is not repeated here.
- Rerun on dev (2026-11-27), with the restarted backend so pacing and backpressure were active. Same setup: 100 learners, 25 concurrent clients.
  - All 100 returned 202, with no 429s or 503s.
  - Submit latency: p50 1.42 s, p95 1.99 s, max 2.20 s. The first run's p95 was 3.70 s.
  - All 100 were judged `passed`. The queue drained in 191 s, about 1.9 s per job.
  - Test data was removed; dev counts were back to 31 submissions and 9 utporul courses.
- Cause of the slow drain (confirmed): `code-judge-worker/worker.py` is a single loop that claims one job at a time and runs its test cases one after another. Dev runs one worker container (`docker-compose.prod.yml` sets 2 replicas). At this rate, 100 students submitting together wait about 3 minutes for the last result.
- Next step if live classes need faster judging: run more worker replicas (the lease-based queue already supports several workers), or let one worker run jobs or test cases in parallel.

## 5. Security notes

- Judge0 sandbox: no network, CPU, memory and wall-time limits, output size caps, and no shared filesystem between runs.
- Source size is capped by `max_source_bytes` on each challenge.
- Hidden test case inputs and expected outputs must never reach the learner API. Check this in every new endpoint.
- Live exercise pushes must check that the instructor owns the course.
- Draft endpoints must check ownership on every read and write.

## 6. Open decisions

1. **Judge0 hosting:** self-hosted (more control, privileged containers) or an external service.
2. **Collaboration:** in scope for the first release, or after Phase 4.
3. **Live grading:** should live-class exercises count toward grades?
4. **Languages:** are the six current languages enough for launch?

Recommended order: Phases 0, 1 and 2 first, then 3 and 4. Phase 5 later.

## 7. Testing and rollout

- Dev first: enable per course, starting with one pilot course.
- Feature flag: `CODING_PLATFORM_V2` controls Monaco, drafts and lesson blocks separately, so each can be turned off without a rebuild of the backend.
- Rollout: pilot course, then a small cohort, then all courses.
- Rollback: disable the flags. Existing submissions and drafts are kept.

## 8. Changelog

- **2026-11-26:** Plan written from an audit of the existing coding, judge and live class code.
- **2026-11-26:** Phase 0 built on dev: Judge0 stack, per-language memory floor, cgroup v2 workaround. Five of six languages pass end to end; Java blocked.
- **2026-11-26:** Phase 2 built on dev: lesson practice blocks, learner drafts, curriculum editor section, lesson player dialog.
- **2026-11-26:** Phase 1 built on dev: Monaco editor with markers and fallback. Judge worker exempted from the general rate limit; internal routes blocked at the edge.
- **2026-11-27:** Phase 3 built on dev: instructor metrics and CSV export, learner progress, ranking tie-breaks. Certificate criteria and per-challenge weights still open.
- **2026-11-27:** Phase 4 built on dev: live coding challenges with push, close, results board and model-solution reveal. Gradebook link and Playwright run still open.
- **2026-11-27:** Phase 5 part A built on dev: line-anchored review comments, review requests and the instructor review queue. Realtime shared editing (part B) waits for an infrastructure decision.
- **2026-11-27:** Phase 5 part B built on dev: pair rooms with a FastAPI WebSocket, Redis fan-out, Yjs and y-monaco. Production nginx edge change still needs approval.
- **2026-11-27:** Phase 6 hardening built on dev: per-learner pacing (429), judge queue backpressure (503), queue and latency gauges in `/metrics`, and autosave tests. HTTP load test run on dev: 100 of 100 accepted and judged, 218 s to drain the queue.
