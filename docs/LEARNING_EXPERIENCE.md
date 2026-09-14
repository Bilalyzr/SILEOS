# Learning Experience Platform

Four features shipped together on branch `learning-experience`: assessment
integrity + manual grading/gradebook, H5P interactive lessons, a unified
instructor certificate designer with 5 production templates, and an
event-sourced gamification system (XP/levels/badges/streaks/leaderboard).
This document is the reference for all four: architecture, security model,
operator/deploy notes, and what was deliberately deferred.

Implementation plan: `docs/superpowers/plans/2026-09-02-learning-experience.md`.
Design spec: `docs/superpowers/specs/2026-09-02-learning-experience-design.md`
(sections A–D — binding requirements for each feature).
Full task-by-task ledger (every review round, every fix, every deferred
item): `.superpowers/sdd/2026-09-02-learning-experience/progress.md`.

---

## A. Assessment hardening + manual grading

**What changed.** The quiz/assignment models were sound but the request-flow
logic had real holes (leaking answers to students, no server-side timer, no
deadline enforcement, no enrollment check on submit, a dead client-side quiz
route calling endpoints that don't exist). Task 1 closed those; Task 2 added
rubric-scored grading + a gradebook; Task 3 built the instructor UI.

**Grading state machine** (`QuizAttempt.attempt_status`, see
`backend/app/models/quiz.py`):
- `attempt_started` — in progress, answers may still be saved (blocked while
  the attempt is paused).
- `pending_review` — submitted, contains ≥1 manually-graded question (essay /
  open-ended); the auto-scored portion is already computed, `earned_marks`
  reflects only auto-graded questions until an instructor finalizes.
- `attempt_ended` — fully graded, final score stands.

**Grading endpoints** (`backend/app/routers/quizzes.py` /
`assignments.py` / `gradebook.py`, all under `/api/v1`):
- `GET /courses/{course_id}/quizzes/pending-reviews` — essay answers awaiting
  a grade, scoped to the course.
- `POST /quiz-attempts/{attempt_id}/answers/{answer_id}/grade` — sets
  `achieved_mark` on one `QuizAttemptAnswer`.
- `POST /quiz-attempts/{attempt_id}/finalize` — recomputes `earned_marks`,
  flips the attempt to `attempt_ended`, fires progress recalculation.
- `POST /submissions/{submission_id}/grade` — assignment grading; accepts
  either an explicit `grade` or per-criterion `rubricScores` (validated
  against `Assignment.rubric`, summed into the candidate grade — an explicit
  `grade` field still wins if both are given). Late-penalty math (see below)
  applies after either source.
- `GET /courses/{course_id}/grading-queue` — merged, oldest-first list of
  pending essay answers + submitted assignments for one course
  (`gradebook.py`, new in Task 2).
- `GET /courses/{course_id}/gradebook` / `gradebook.csv` — student × item
  matrix (`app/services/gradebook_service.py`'s `build_matrix`: cell status
  is `graded` / `pending` / `missing` / `late`, keyed `"{type}:{id}"` per
  row, e.g. `"quiz:3"`, `"assignment:7"` — not array-index aligned). CSV uses
  the stdlib `csv` module + `app/core/csv_safety.sanitize_csv_cell` (OWASP
  formula-injection defense: a leading `=+-@`/tab/CR gets a single-quote
  prefix) — the same helper also now guards the pre-existing live-class
  attendance CSV export.

**Late-submission policy** (`Assignment.late_policy` — `allow` / `block` /
`penalty`, `Assignment.late_penalty_pct`): `allow` accepts the submission and
flags `is_late=True`; `block` rejects with 403 once `due_date` has passed;
`penalty` accepts + flags, and grading applies the percentage automatically
(grade shown as raw + penalized). `late` on the gradebook matrix reads
`AssignmentSubmission.is_late` (set once at submit time) — the gradebook does
not independently recompute lateness from `due_date`.

**Integrity fixes worth knowing about operationally:**
- Server-side timer: `submit_quiz` rejects (or caps at zero-credit for
  unanswered questions) submissions later than
  `attempt_started_at + quiz_time_limit + 90s grace`; a paused attempt's
  deadline extends by the paused duration (capped at 24h).
  Deadline-exceeded submits now END the attempt server-side (`200` +
  `late_submission: true`, scoring only pre-deadline-saved answers) rather
  than leaving it wedged in `attempt_started` forever.
- Starting an attempt when one is already open (`attempt_started` or
  `pending_review`) returns the EXISTING attempt (resume), and both statuses
  count toward `max_attempts` at start and submit.
- `GET /courses/{cid}/quizzes/{qid}` returns `correctAnswer`/explanations
  only to the course owner/admin — students get sanitized questions; results
  are fetched separately post-submit through an endpoint that already gated
  correctly.
- Per-assignment file upload (`/uploads/assignment-file?assignment_id=`)
  enforces the assignment's own `allowed_file_types`/`max_files`, intersected
  with a hardcoded safe-extension ceiling + content-type cross-check (an
  instructor's config can only narrow the allowlist, never widen it past
  what's safe) — and requires the caller to be enrolled or the course
  owner/admin. `max_files` is counted from files actually on disk for that
  user, with orphaned (returned-then-replaced or abandoned) uploads reclaimed
  before counting so a legitimate retry never permanently exhausts the quota.
- The dead client-side quiz path was removed: `/courses/:courseId/quizzes/:quizId`
  now routes to the working `quiz-taking.tsx`; `api/quiz.ts`, `store/quiz.ts`,
  and `pages/quiz.tsx` (calling nonexistent endpoints) were deleted.

**Rubrics** are lightweight: `Assignment.rubric` is a JSON list of
`{criterion, max_points}` (≤20 criteria, validated on create/update); a grade
submission's `rubric_scores` JSON stores the per-criterion scores, summed
into the grade (still overridable by an explicit grade). No separate rubric
tables.

**Frontend:** `pages/instructor/gradebook.tsx`, `grading-queue.tsx`,
`components/assess/RubricEditor.tsx` + `RubricScorer.tsx`; instructor nav
entry is a course-picker page (`pages/instructor/grading.tsx`) since
gradebook/grading-queue are per-course routes with no single global
destination.

---

## B. H5P interactive lessons

**Locked decision: play, don't author.** Instructors author `.h5p` packages
externally (lumi.education or h5p.org — both free, no account required for
lumi's basic export) and upload the finished package to a lesson. In-platform
authoring would need a Node H5P server and is out of scope for this build.

**Owner authoring workflow:**
1. Build the interactive content at **lumi.education** (or any H5P.org-
   compatible authoring tool) — quizzes, interactive video, branching
   scenarios, etc.
2. Export as a `.h5p` file (this is just a zip with a specific structure —
   `h5p.json` manifest + `content/` + library folders).
3. In the course editor's lesson panel, switch the lesson's content type to
   **H5P interactive**, then upload the `.h5p` file (or pick a previously
   uploaded one — uploads are reusable across lessons).
4. Preview inside the editor before publishing.

**Security model (binding — spec B3).** An uploaded `.h5p` package is
instructor-supplied, and its bundled JavaScript is UNTRUSTED CODE — it runs
inside a `<iframe sandbox="allow-scripts">`, **never** `allow-same-origin`,
pointing at a dedicated static player page (`frontend/public/h5p-player.html`,
which boots the vendored `h5p-standalone` runtime from
`frontend/public/h5p/{frame.bundle.js, main.bundle.js, styles/, fonts/,
images/}` — copied in at build time, no CDN). Without `allow-same-origin`,
the browser treats the player document as a unique **opaque origin** on
every load: `window.location.origin` reads `"null"`, and any storage access
(`localStorage`/`sessionStorage`/IndexedDB/cookies) throws a `SecurityError`
instead of silently no-opping — so the embedded, untrusted JS can never read
the app's cookies, DOM, or storage, even though its asset files are served
from the same origin as everything else. Extracted package assets under
`/uploads/h5p/{public_id}/` being publicly reachable is acceptable ONLY
because of this sandbox boundary; `public_id` is random hex (32 chars), and
the shared `sanitizeHtml` utility is never loosened for this feature — the
player iframe is a React component (`components/h5p/H5PLesson.tsx`), not
rich-text HTML.

Completion flow: the player page listens for H5P xAPI events and
`postMessage`s `{type: 'h5p-result', score, maxScore, completed}` to the
parent; `H5PLesson.tsx` verifies the message's `source` is that iframe's
`contentWindow` (origin-based verification doesn't work here since the
sandboxed frame's origin reports `"null"` — spec B6's origin-check wording
technically deviates for this reason, documented in code), then
`POST /api/v1/h5p/{public_id}/result` (auth'd, enrollment-checked, upserts
per user) and calls the lesson-complete endpoint when
`completed && score/maxScore >= 0.5` (or no score at all → completed alone).
**The server treats client-reported H5P scores as advisory engagement data —
recorded and fed into gamification — never as gradebook truth**; this is a
documented limitation of client-side H5P content, not a bug.

**Upload/extraction pipeline** (`backend/app/services/h5p_service.py`,
`backend/app/routers/h5p.py`, mounted `/api/v1/h5p`):
- Zip validation, before a single byte is written to disk: no path
  traversal, absolute paths, or Windows drive/UNC paths, no symlinked
  entries (detected via the Unix mode bits in `ZipInfo.external_attr`), no
  duplicate entry names, no nested `.h5p`/`.zip` archives (rejected outright
  rather than recursed into — deliberate: H5P subcontent can legitimately
  embed other H5P packages, but validating a nested archive's contents would
  mean re-running every one of these checks against unvalidated content one
  level down; an author who needs nested content re-exports as one package),
  no more than `MAX_FILE_COUNT = 2000` entries,
  `MAX_MEMBER_UNCOMPRESSED_BYTES = 50MB` per file,
  `MAX_TOTAL_UNCOMPRESSED_BYTES = 300MB` total (zip-bomb guard: validated
  twice — once against the zip's attacker-controlled declared-size header
  before extraction, then re-enforced against *actual* bytes streamed out
  during extraction), and an extension allowlist (html/js/css/json/svg/png/
  jpg/jpeg/gif/webp/mp3/mp4/wav/ogg/woff/woff2/ttf/otf/eot/vtt/csv/txt/md).
  Extensionless entries (license files, dotfiles) are silently skipped, not
  rejected — real lumi.education packages ship these. `h5p.json` must be
  present at the package root; any validation failure removes the entire
  partial extraction directory (`shutil.rmtree`) — no partial content ever
  survives on disk.
- Successful extraction lands at `uploads/h5p/{public_id}/` (served by the
  existing static `/uploads` mount).
- Endpoints: `POST /finalize` (small packages ≤20MB, direct multipart, or
  large packages via the chunked-upload flow — see below), `GET /` (list own
  uploads), `GET /{public_id}` (meta), `DELETE /{public_id}` (blocked while
  any lesson still references it), `POST /{public_id}/result`,
  `GET /{public_id}/results` (instructor rollup).
- Upload path for large packages (up to 100MB, the chunked-upload `h5p`
  type): `/upload/chunked/{init,chunk,complete}` writes the assembled blob
  OUTSIDE the static `/uploads` root, to `h5p_temp/{user_id}/{filename}`
  (per-user namespaced; moved outside `/uploads` in a review-round fix so no
  static mount ever serves an unextracted, unvalidated raw upload) — `POST
  /finalize` then resolves `chunked_session_id` as that filename inside
  `H5P_TEMP_DIR/{current_user.id}/` and runs it through the same validation/
  extraction pipeline as a direct upload.
- **2GB cap per owner**, summed across that instructor's `h5p_contents` rows
  (including `uploaded`-status rows, which is intentional — space is
  reserved from upload, not just after successful extraction).
- `Lesson.lesson_content_type` (`"video"` default | `"h5p"`) and
  `Lesson.h5p_content_id` (nullable FK) are additive columns gating the
  player branch in `pages/lesson-redesigned.tsx`.

**Asset serving — CORS is load-bearing (review finding C1).** The player
document runs in `<iframe sandbox="allow-scripts">` WITHOUT
`allow-same-origin`, so the browser gives it a unique **opaque origin**.
Requests then split in two:

| Request kind | Origin-checked? | Consequence |
| --- | --- | --- |
| Parser GETs (`<script src>`, `<link>`, `<img>`) | No | `/h5p/*` runtime loads fine |
| `fetch()` / XHR | **Yes** (`Origin: null`) | Rejected without an explicit ACAO |

h5p-standalone loads packages via `fetch()` (`h5p.json`,
`content/content.json`, library descriptors), so **`/uploads/h5p/*` must
answer with `Access-Control-Allow-Origin: *` or the player never boots at
all.** This is why the feature can be perfectly correct server-side and
still be dead on arrival in the browser.

The header is applied in two independent places, and BOTH must stay in sync:

- `backend/app/main.py` — a `StaticFiles` sub-app for the `/uploads/h5p`
  subtree wrapped in `H5PAssetHeadersMiddleware`, mounted BEFORE the general
  `/uploads` mount (Starlette matches mounts in registration order). It also
  registers explicit `mimetypes` entries for `.woff`/`.woff2`, which Windows
  hosts do not resolve natively.
- nginx — `location /uploads/h5p/` blocks in `nginx/conf.d/default.conf`,
  `nginx/conf.d/default.production.conf` and `deploy/nginx/conf.d/10-app.conf`
  (the blue/green edge, which is what actually serves `/uploads` in
  production — the backend is never consulted for these paths there).

Alongside ACAO both layers send `X-Content-Type-Options: nosniff` and
`Content-Security-Policy: sandbox`, so an HTML file inside an uploaded
package can never execute as a same-origin top-level document. `*` grants no
new read access: these files already sit behind an unguessable 32-hex
`public_id`. Regression coverage: `backend/tests/test_h5p_cors_headers.py`
(asserts the headers on the h5p subtree AND that the rest of `/uploads` does
NOT get a wildcard ACAO). See also deploy smoke step 7.

**Known deferred items:** the `public_id` regex (`^[0-9a-f]{32}$`) is
duplicated between `H5PLesson.tsx` and `h5p-player.html` — kept in sync by
comment, not by a shared constant (both files live in different build
contexts — one is bundled TS, the other a static public HTML file with no
build step).

---

## C. Certificate designer (instructors) + 5 seed templates

**What changed.** Previously, issued certificates rendered from hand-authored
HTML files looked up by slug, and the drag-and-drop builder's saved designs
only ever reached a ReportLab preview capped to 14 base fonts — the builder
was disconnected from what students actually received. Task 6 unified both
paths onto `elements_config`.

**Rendering architecture:**
`app/services/certificate_html_renderer.py` turns an `elements_config` JSON
document (element types: `student_name`, `course_name`, `completion_date`,
`certificate_id`, `qr_code`, `instructor_name`, `signature_image`, `text`,
`image`, `rect`, `line` — typed tokens, not sentinel text substitution) into
a self-contained HTML document: absolute-positioned divs, a curated 12-font
Google Fonts `<link>` list, background image/color, rotation, and a
server-generated QR code (the `qrcode[pil]` Python library, embedded as a
data-URI pointing at the certificate's verify URL — no new upload path, no
external QR service). `CertificateService.resolve_template` prefers a
`Certificate` row with non-empty `elements_config` (renders through this
module); rows with a `post_name` slug keep the legacy static-file path
untouched (the original 5 hand-authored designs still work).

**Chrome dependency.** The production render path is headless Chrome via
Selenium (`CertificateService._build_chrome_driver`; the legacy slug path
uses `_render_html_pdf_via_chrome` which navigates to the live public verify
URL, the elements_config path uses the newer
`_render_local_html_pdf_via_chrome` which navigates to a local `file://`
temp HTML file and calls Selenium's `driver.print_page()`): the backend
Docker image installs `google-chrome-stable` + a matching `chromedriver`
pinned at `/usr/local/bin/chromedriver` (see `backend/Dockerfile`) so
renders never need outbound network access to resolve a driver at request
time. Concurrent Chrome renders are capped at 2 via a semaphore
(`_render_semaphore`) to bound memory/process use during a burst of
downloads. **ReportLab stays as the fast fallback** when Chrome is
unavailable (e.g. local dev without the Docker image) — capped to base-14
fonts, used only for quick previews, never for final issuance when Chrome is
reachable.

**Instructor access & scoping:** instructors get template CRUD scoped to
their OWN rows (`post_author`), assignable only to their own courses,
mounted at `/api/v1/certificates/designer/*`
(`app/routers/certificate_designer.py`: `GET/POST /`, `PUT/DELETE
/{id}`, `POST /{id}/duplicate`, `POST /{id}/preview`). Admins see/edit all
rows and can mark a template `is_global` (usable by every instructor). The
legacy primitive `/templates/` CRUD in `certificates.py` is superseded but
NOT deleted — docstrings mark it `DEPRECATED (Task 6)`, and the course
editor's `/templates/list` endpoint merges in the new designer templates so
existing integrations keep working.

**Designer frontend** (`components/certificates/designer/`:
`DesignerCanvas`, `ElementProperties`, `LayersPanel`, `FontPicker`,
`TemplateGallery`; page `pages/instructor/certificate-designer.tsx`, also
reused by the admin certificates page): resize handles, rotate, snap-to-
center guides, z-order/layers panel, zoom 50–150%, undo/redo (bounded stack
of 50), the curated 12-font picker with live loading, QR/shape/signature
elements, orientation/size presets (A4 landscape/portrait, square), a
template gallery with thumbnails, live server preview (the real Chrome
path) plus an instant client-side canvas preview, and draft autosave to
`localStorage`. Instructor nav entry: **Certificates**
(`INSTRUCTOR_NAV` in `components/dashboard/nav-configs.ts` — this file is
the RENDERED nav config, consumed by `RoleLayouts.tsx`'s `InstructorLayout`;
a duplicate-looking nav lives in a dead `header.tsx` that is NOT rendered
anywhere — a repo trap two separate tasks in this branch hit).

**Safety:** editing a template does NOT retroactively change
already-rendered certificates (the render cache is keyed by issued
certificate, with a purge endpoint available). Instructor-uploaded designer
images (signatures, backgrounds) go through the existing Pillow-verified
image upload endpoint — no new raw upload path was added.

**5 seed templates** (`backend/seed_designer_templates.py` — idempotent by
name, run at deploy): **Ivory Classic** (warm ivory ground, thin double-rule
border), **Midnight Gold** (deep navy ground, gold accents), **Tamil
Heritage** (maroon + turmeric gold + ivory palette — a real, tasteful motif
respecting the platform's Tamil identity, not clip-art), **Gradient Modern**
(light ground, a 24-band stepped-hue color spine), **Minimal Mono**
(near-white ground, Space Grotesk only, one hairline rule). Each went
through a design-review pass fixing real layout bugs (QR-through-border
overlap, dead-half compositions, ornament paint-over) — see the ledger's
Task 8 entries for the full history. **Thumbnails only render when Chrome is
present** — locally this script no-ops with a note; on a VPS with Chrome
installed (the standard Docker image), rerunning the seeder regenerates
them. This is the one operational step that needs a deploy-time rerun after
initial seeding if the first run happened without Chrome.

---

## D. Gamification (XP, levels, badges, streaks, leaderboard)

**Architecture: event-sourced.** `xp_events` is an append-only ledger — one
row per award, idempotent on `event_key` (a caller-constructed string like
`"lesson:123:completed:user:9"`; a duplicate key is caught as an
`IntegrityError` and treated as a no-op, so a retried request never double-
awards). `user_game_stats` is the derived, transactionally-maintained
summary row per user (total XP, streak, `leaderboard_visible`,
`badges_count` — level is always computed from XP, never stored).
`badges` is a seeded rule catalog (~15 rows); `user_badges` is the award
join row, unique per `(user_id, badge_id)`. Models:
`backend/app/models/gamification.py`. All four tables live in the shared
`0003_learning_experience` Alembic revision (guarded `has_table` checks,
appended by Tasks 1/4/9 — one migration file, grown across the branch).

**Single entry point:** `app/services/gamification_service.award(db,
user_id, event_type, event_key, course_id=None, meta=None)`. Every call site
wraps it in try/except — an award failure must never fail the host request
(spec D1, "best-effort"). `award()` itself only `flush()`es, never commits —
the calling request owns its own transaction boundary; this was a real bug
fixed in review (an earlier version's internal `commit()` was committing the
CALLER's unrelated pending writes mid-flight). Trigger points (all
try/except-wrapped): lesson complete (+10), quiz passed (+20, +10 bonus at
≥90%) — **first pass only**, assignment submitted (+10) / graded at-or-above
passing (+15), course completed (+100), live-class attended-present (+25),
H5P completed (+10), daily-first-activity (+5, also advances the streak),
streak milestones 7/30/100 days (+50/+200/+500).

**Award keys are per-achievement, never per-attempt.** The quiz-pass and
quiz-bonus keys are `quiz:{quiz_id}:passed:user:{user_id}` and
`quiz:{quiz_id}:bonus:user:{user_id}` — keyed on the QUIZ, so passing a quiz
is worth XP **once ever**, matching lesson/course-completion semantics. An
earlier per-attempt key (`quiz:{id}:attempt:{attempt_id}:passed:...`) let a
student farm unbounded XP by simply re-taking a quiz they had already
passed, since each fresh `attempt_id` minted a new un-awarded key (review
finding M4). Both award sites — the direct pass in `_submit_quiz_impl` and
the deferred pass in `finalize_quiz_attempt` — must use the identical key so
the two paths converge on a single award rather than stacking.

Likewise, lesson completion uses one key,
`lesson:{lesson_id}:completed:user:{user_id}`, shared by BOTH completion
paths: the explicit "mark complete" button (`courses.py`) and crossing the
90% video-watch threshold (`progress.py` `/save`, review finding I3 — this
path previously awarded nothing, so a student who finished a course purely
by watching videos earned no lesson XP at all). Whichever fires first wins;
the other converges to an idempotent no-op.

**Level math** — computed, never stored: `xp_for_level(n) = 100 * n * (n+1)
/ 2` (L1 = 100 XP, L2 = 300, L3 = 600, L4 = 1000, …). `GET
/api/v1/gamification/me`'s `stats` includes the full progress-ring shape:
`level`, `total_xp`, `current_level_floor_xp`, `next_level_xp`,
`xp_into_level`, `xp_to_next_level`, `progress_fraction` (0–1, `1.0` when
the level span is 0 — i.e. already at the ceiling).

**Badge catalog** (`gamification_service.BADGE_CATALOG`, seeded lazily by
`ensure_badges`; mirrored on the frontend in
`components/gamification/BadgeGrid.tsx` since there is no "list all badges"
endpoint — only earned ones come back from `/me`, so unearned/grayed tiles
need the catalog client-side too):

| slug | name | rule | icon |
|---|---|---|---|
| first-lesson | First Steps | complete 1 lesson | footprints |
| five-lessons | Getting Momentum | complete 5 lessons | footprints |
| course-finisher | Course Finisher | complete 1 course | graduation-cap |
| three-courses | Triple Threat | complete 3 courses | trophy |
| quiz-ace | Quiz Ace | score ≥90% on 5 quizzes | target |
| streak-7 | Week Warrior | 7-day streak | flame |
| streak-30 | Month Master | 30-day streak | flame |
| streak-100 | Century Streak | 100-day streak | flame |
| early-bird | Early Bird | activity before 7am UTC | sunrise |
| night-owl | Night Owl | activity after 10pm UTC | moon |
| live-regular | Live Regular | attend 5 live classes | video |
| h5p-explorer | H5P Explorer | complete 1 H5P activity | puzzle |
| assignment-perfect | Perfectionist | a perfect assignment grade | star |
| xp-level-5 | Rising Star | reach level 5 | sparkles |
| xp-level-10 | XP Legend | reach level 10 | crown |

All 12 distinct icon names above were verified against `lucide-react`'s
actual exports for this task (kebab-case → PascalCase, e.g. `graduation-cap`
→ `GraduationCap`) — every one resolves; no backend fix was needed.
`early_bird`/`night_owl` hour comparisons are computed in UTC explicitly
(`_utc_hour_expr`, dialect-branched: Postgres needs an explicit
`timezone('UTC', …)` wrap since a plain `EXTRACT(HOUR FROM …)` over a
`timestamptz` implicitly uses the session timezone; SQLite stores naive-UTC
already by this codebase's convention).

**Streak rules** (`touch_streak`, THE implementation — `dashboard.py`'s
old `_compute_streaks` and `superadmin.py`'s table now read from
`user_game_stats` first, falling back to their own computation only for a
user with no stats row yet): same calendar day as `last_active_date` is a
no-op (already counted today); exactly one day after is `+1`; a gap of more
than one day resets to `1`. `longest_streak` is a high-water mark, never
decreases. **`current_streak` is staleness-corrected server-side on read** —
a user inactive for more than a day reads `current_streak = 0` even though
the stored value hasn't been touched (both the `/me` stats and
`superadmin.py`'s bulk query apply this); the frontend never needs to
re-derive staleness itself.

**Leaderboard privacy** (spec D5): `user_game_stats.leaderboard_visible`
defaults `True`, toggled via `POST /api/v1/gamification/me/settings`. Only
visible users appear in `GET /api/v1/gamification/leaderboard?scope=global`
(top 50) or `?scope=course:{id}` (top 20) — **a caller can always see their
own rank regardless of their own visibility toggle**, returned as `my_rank`
in the same response, derived from the exact same cached `entries` list when
the caller is in it (keeps one response internally consistent even though
`entries` is Redis-cached for 300s with a `MockRedis` direct-query fallback
in dev/test). Entries expose `display_name` + `level` + `total_xp` only —
**never email**. Ties break deterministically on `user_id ASC` (both in the
cached list and the live `my_rank` fallback query, so they never disagree).
This is a SEPARATE page from the pre-existing `/admin/hall-of-fame` Wall of
Fame (which is deliberately anti-ranking) — `/leaderboard` is framed as
friendly weekly motivation, not competitive ranking.

**Frontend** (`components/gamification/`): `XPLevelCard.tsx` (SVG progress
ring, `stroke-dasharray`/`stroke-dashoffset` driven by `progress_fraction`),
`StreakCard.tsx` (flame icon, current/longest counts, last-7-UTC-days
activity dots derived from `recent_events` — replaces the dead
`components/streak/streak-card.tsx` stub, deleted this task after confirming
zero imports), `BadgeGrid.tsx` (earned badges with lucide icons + earn
dates, unearned tiles grayed with a rule-hint tooltip/caption),
`LeaderboardTable.tsx` (rank/name/level/XP rows, self-row highlighted, a
`my_rank` footer row when the caller is outside the listed top-N),
`AwardToaster.tsx` (on mount: `GET /me/unseen` → for each badge/streak-
milestone event, fires `celebrationAnimation()` from `utils/animations.ts` +
a timed toast banner reimplementing the same visual pattern
`pages/lesson-redesigned.tsx`'s local `showAchievementNotification` uses —
that function is component-local state, not exported, so it isn't imported
directly → `POST /me/unseen/mark-seen` once for every consumed event id).
Mounted on the student dashboard (`pages/dashboard.tsx`: XP card + streak
card in the stats row, a badges strip section, `<AwardToaster />` at the top
of the tree) and surfaced in the student nav as **Leaderboard**
(`STUDENT_NAV` in `nav-configs.ts` — the same rendered-nav file
`INSTRUCTOR_NAV` lives in, see the certificate designer section above for
why that distinction matters in this repo). The profile page
(`pages/profile.tsx`) gained a badges section + the leaderboard-visibility
toggle for students.

**Known deferred items** (accepted tradeoffs, not bugs): XP can be
permanently lost if a crash lands between a completion commit and its
`award()` call (best-effort by design); `ensure_badges` does a `COUNT` query
per award call (cheap — short-circuits once all 15 exist, but not zero-cost);
`award()` returns `None` ambiguously (success-with-nothing-new vs.
degraded-failure look the same to the caller); leaderboard cache staleness
(up to 300s) is handled via same-list derivation for `my_rank` but a
different user's rank several seconds later could still reflect a slightly
stale ordering.

---

## Deploy

Run in this order for a fresh deploy or an upgrade of an existing
environment:

1. **Database migration** — `alembic upgrade head` from `backend/` (revision
   `0003_learning_experience` adds all Task 1/4/9 tables/columns; every
   `CREATE` is guarded with `has_table`/`has_column`/`has_index` checks, safe
   to run against an existing database).
2. **Backend dependency** — `pip install qrcode[pil]` (`==8.2`, already
   pinned in `backend/requirements.txt` — a normal `pip install -r
   requirements.txt` picks it up; called out here because it's new in this
   branch and QR codes on certificates silently fail without it).
3. **Frontend** — `npm install` (picks up `h5p-standalone@^3.8.2`) then
   `npm run build`. The vendored H5P player runtime
   (`frontend/public/h5p/{frame.bundle.js, main.bundle.js, styles/, fonts/,
   images/}`) ships as static files checked into the repo — no separate copy
   step needed at deploy time, only at initial setup if those files are ever
   regenerated from a newer `h5p-standalone` version.
4. **Seeders to run** (idempotent — safe to rerun):
   - `python backend/seed_designer_templates.py` — the 5 certificate
     templates. **On a VPS with Chrome available (the standard Docker
     image), always rerun this after first deploy** even if it ran once
     already: a run without Chrome creates the template rows but skips
     thumbnails (documented no-op, not a failure) — rerunning with Chrome
     present regenerates the thumbnails for the existing rows.
   - Badge catalog seeding is automatic and lazy (`ensure_badges` runs
     inside the first `award()` call after deploy) — no separate script.
5. **Chrome / certificate rendering** — the backend Docker image already
   installs `google-chrome-stable` + a pinned `chromedriver`
   (`/usr/local/bin/chromedriver`, see `backend/Dockerfile`); no additional
   ops step is needed on a standard container deploy. If certificates are
   ever rendered from a non-Docker host, install Chrome + a matching
   chromedriver there or accept the ReportLab fallback (base-14 fonts only).
6. **Per-owner H5P storage cap** — each instructor is capped at 2GB of H5P
   uploads (`uploaded`-status rows count toward the cap by design). If an
   instructor needs more, there is no self-service increase — an operator
   would need to raise `MAX_OWNER_AGGREGATE_BYTES` in
   `backend/app/routers/h5p.py` (no admin UI for this; not built this
   branch, see Out of scope below).

### Deploy-day smoke checklist (MANDATORY — run in this order)

Every item below covers a failure mode that the automated suite provably
cannot catch, because each depends on a real browser, a real Chrome host, or
real edge (nginx) config that no unit test exercises. Do not sign off a
deploy until all three pass.

7. **Real-browser H5P boot test.** Open a lesson whose
   `lesson_content_type = "h5p"` in an ACTUAL browser (not a headless smoke
   script, not curl) and confirm the interactive content renders and is
   clickable.

   *Why this cannot be skipped:* the player runs in
   `<iframe sandbox="allow-scripts">`, which gives the document an OPAQUE
   origin, and h5p-standalone loads the package via `fetch()`. A `fetch()`
   from an opaque origin is treated as cross-origin (`Origin: null`), so it
   is rejected unless `/uploads/h5p/*` answers with
   `Access-Control-Allow-Origin: *`. That header comes from TWO independent
   places — the dedicated `/uploads/h5p` mount in `backend/app/main.py` and
   the `location /uploads/h5p/` blocks in the nginx configs
   (`nginx/conf.d/default.conf`, `nginx/conf.d/default.production.conf`,
   `deploy/nginx/conf.d/10-app.conf`). In production nginx serves
   `/uploads` off disk and the backend is never consulted, so a correct
   backend with a stale nginx config yields a player that is dead on
   arrival with only a CORS error in the browser console. Curl will NOT
   reveal this: a plain GET succeeds either way; only a real browser
   enforces CORS.

   Quick triage if the content does not appear: open devtools → Network,
   request `/uploads/h5p/<public_id>/h5p.json`, and confirm the response
   carries `access-control-allow-origin: *`. If it is missing, the edge
   nginx config was not reloaded.

8. **Chrome-host certificate render.** Issue (or re-render) one real
   certificate on the deployed host and confirm the PDF/PNG comes back from
   the headless-Chrome path, not the ReportLab fallback. The fallback is
   base-14-fonts only, so a designer template will render with wrong
   typography and mis-positioned elements while still returning HTTP 200 —
   a silent visual regression rather than an error. Verify Chrome and
   `chromedriver` are both present and version-matched on the host actually
   doing the rendering.

9. **Thumbnails seeder.** Re-run `python backend/seed_designer_templates.py`
   on the Chrome-capable host and then confirm the certificate template
   picker in the course editor shows real preview images rather than the CSS
   swatch placeholder. A seeder run without Chrome creates the rows but
   silently skips thumbnails (a documented no-op, not an error), so a first
   deploy that seeded before Chrome was available leaves every template
   thumbnail-less until this rerun.

### Deferred-minor items (from the task ledger — not blocking, no known
customer-facing impact; listed here so they aren't silently lost)

- **Assessment:** parallel-attempt-start TOCTOU race (would need a partial
  unique index or `IntegrityError` catch to fully close); the M3 report-
  framing item from the Task 1 review round; the GRADED-status reclaim
  branch is untested (identical code path as SUBMITTED, so behavior is
  covered indirectly); the upload-budget reclaim pass is synchronous per
  upload (fine at `max_files<=10`); instructor-entered grade has no
  lower-bound validation (a negative grade renders oddly but harmlessly in
  the gradebook/CSV); a `RETURNED` assignment submission currently reads as
  pending/missing in the gradebook matrix rather than a distinct badge (the
  backend matrix doesn't carry that status yet); the lesson player's
  assignment renderer has no late/grade badge (pre-existing, unrelated to
  this branch).
- **H5P:** the `public_id` regex is duplicated (not shared) between
  `H5PLesson.tsx` and `h5p-player.html`; extensionless zip entries are
  skipped rather than extracted (intentional).
- **Certificates:** the CSS color-keyword allowlist admits harmless CSS-wide
  keywords like `unset`; `nanpx`-style letter-spacing is a cosmetic issue,
  not fixed; the designer's cache-clear on template `PUT` is synchronous per
  request (bounded cost, documented); a few self-cancelling `%2e%2e`-style
  paths are conservatively over-rejected by the traversal guard (intentional,
  safe direction to err).
- **Gamification:** XP can be lost on a crash between a completion commit
  and its award call (accepted best-effort tradeoff); `ensure_badges` runs a
  `COUNT` query on every award rather than caching catalog-complete state;
  `award()`'s `None` return is ambiguous between "nothing new" and
  "degraded"; leaderboard cache staleness (≤300s) can very rarely show a
  slightly different ordering to a second user moments apart.

None of the above blocked merge — each was triaged during its task's review
round and explicitly deferred rather than missed.

## Out of scope (documented future phases)

In-platform H5P authoring (needs a Node H5P server); quiz question
banks/import; plagiarism detection; proctoring; peer review; seasonal
leaderboards/teams; a certificate marketplace; self-service H5P storage-cap
increases; Flutter parity for any of these four features (mobile gets
read-only gamification stats via the existing dashboard API only — no new
Flutter work this branch).
