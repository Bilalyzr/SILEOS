# Learning Experience Platform — Design Spec
2026-09-02 · branch `learning-experience` (off revenue-platform @ 24d7737)

Owner request: "perfect assignment and assessment logics · H5P integration modules · fully
editable certificate designer for instructors with amazing templates · gamification learning
system." Standing instruction: proceed with recommendations.

Phase-0 recon (3 explorers) verified the existing stacks; this spec builds on repo reality.
Recon deltas that BIND every task are inlined per section.

---

## A. Assessment Core — "perfect assignment & assessment logic"

Recon verdict: the models are sound but the logic is full of holes. A is therefore
**hardening + completion of what exists**, not a rewrite. The 12 verified gaps (quiz recon §6)
become requirements:

### A1. Integrity fixes (all BINDING)
1. **Essay grading exists.** `submit_quiz` marks attempts containing essay/short-answer-manual
   questions as `pending_review` (new attempt_status value; auto-scored portion computed
   immediately). New instructor endpoints: list pending attempts per course/quiz, grade one
   answer (`achieved_mark` on QuizAttemptAnswer — the columns already exist unused), finalize
   attempt (recomputes earned_marks, flips to `attempt_ended`, fires progress recalc).
2. **Answer leakage closed**: `GET /courses/{cid}/quizzes/{qid}` returns `correctAnswer`/
   explanations ONLY to the course owner/admin; students get sanitized questions. The
   quiz-taking page already fetches results separately post-submit (results endpoint already
   gates correctly).
3. **Server-side timer**: `submit_quiz` rejects (or caps at zero-credit for unanswered)
   submissions later than `attempt_started_at + quiz_time_limit + 90s grace`. 409 with clear
   detail; client auto-submit stays as UX.
4. **Attempt-limit race**: enforced at start AND submit (already) — add unique-ish guard:
   reject `start` when an un-ended attempt exists (return that attempt instead — resume).
5. **Assignment deadlines enforced**: `submit` compares now vs `due_date` under a per-assignment
   `late_policy` (new fields: `late_policy` enum `allow|block|penalty`, `late_penalty_pct` int).
   `allow`: accept + `is_late=True` flag (new column). `block`: 403 after due. `penalty`:
   accept + flag; grading applies the pct automatically (grade shown as raw + penalized).
6. **Assignment enrollment check**: submit requires enrollment (same helper quizzes use);
   owner/admin bypass for testing.
7. **Assignment status lifecycle usable**: create accepts `status`, update accepts `status`;
   students see/submit ONLY `published` (list filter + submit guard). DRAFT visible to owner.
8. **Per-assignment file validation server-side**: submit validates declared `files` against
   the assignment's `allowed_file_types`/`max_files`; a new upload endpoint variant
   `/uploads/assignment-file?assignment_id=` enforces the assignment's own type/size caps
   (falls back to the global document rules when stricter).
9. **DB constraints**: unique (assignment_id, user_id) on submissions; migration `0003`
   (Alembic now exists — extend it, guarded with has_table/has_index like 0002).
10. **Dead quiz path removed**: route `/courses/:courseId/quizzes/:quizId` repointed to the
    WORKING taking page (quiz-taking.tsx); `api/quiz.ts`+`store/quiz.ts`+`pages/quiz.tsx`
    deleted (dead aspirational code calling nonexistent endpoints). Grep for imports first.
11. **Pause honored**: `save_attempt_answer` refuses writes while `attempt_info._pause.active`;
    pause extends the server-side deadline by paused duration (cap: 24h).
12. **Rubrics (lightweight)**: `Assignment.rubric` JSON (list of {criterion, max_points});
    grading accepts optional per-criterion scores (stored in submission `rubric_scores` JSON;
    grade = sum, still overridable). No new tables.

### A2. Instructor Gradebook
New endpoints + page `/instructor/courses/:id/gradebook`: matrix of students ×
(quizzes, assignments) with scores/pending/late badges, CSV export (blob pattern like
attendance CSV). Pending-review queue page (essay answers + ungraded submissions in one list).

Non-goals (future): question banks, imports, plagiarism detection, peer review, proctoring.

## B. H5P Integration

Locked decisions:
1. **Play, don't author.** Instructors upload `.h5p` packages (authored on lumi.education /
   h5p.org). In-platform authoring is a future phase (needs a Node H5P server — out of scope).
2. **Runtime = `h5p-standalone` (npm, MIT)**, vendored into the frontend build — no CDN.
3. **Security model (BINDING, from recon C8):** H5P JS is instructor-supplied untrusted code.
   It executes ONLY inside `<iframe sandbox="allow-scripts">` — **never `allow-same-origin`** —
   pointing at a dedicated static player page. Extracted package assets are served under
   `/uploads/h5p/{content_id}/` (public static path is acceptable BECAUSE the sandbox denies
   the embedded code cookies/DOM/storage of the app origin; content ids are random hex).
   The shared `sanitizeHtml` is NOT loosened; the player iframe is a React component, not
   rich-text HTML.
4. **Upload path**: new `h5p` chunked-upload type (`.h5p`/`.zip`, cap 100MB) with the
   double-validation pattern chunked_upload already uses. Server-side extraction service:
   validates zip (h5p.json present, no path traversal `..`, no symlinks, file-count and
   per-file + total-size caps, extension allowlist inside the zip: html/js/css/json/svg/png/
   jpg/gif/webp/mp3/mp4/wav/woff/woff2/ttf/otf/vtt/csv/txt — reject others), extracts to
   `uploads/h5p/{hex_id}/`.
5. **Model**: `h5p_contents` (Integer PK, hex public_id String(32) unique, owner FK, title,
   library (from h5p.json mainLibrary), size_bytes, status uploaded|ready|failed,
   created/updated). `Lesson` gains `lesson_content_type` (String(20) default "video") and
   `h5p_content_id` FK nullable — additive columns in migration 0003.
6. **Player flow**: lesson player branches on `content_type === 'h5p'` → `<H5PLesson>` renders
   the sandboxed iframe (`/h5p-player.html?content=<public_id>` served from frontend public/)
   → player boots h5p-standalone against `/uploads/h5p/{id}/`. Completion: the player page
   listens to H5P xAPI events, `postMessage`s `{type:'h5p-result', score, maxScore, completed}`
   to the parent; the React component verifies `event.origin === window.origin` +
   source === iframe, then POSTs `POST /api/v1/h5p/{public_id}/result` (auth'd, enrollment-
   checked, upsert per user) and calls the existing lesson-complete endpoint when
   `completed && score/maxScore >= 0.5` (or no score → completed alone). Server treats client
   scores as advisory engagement data (recorded, feeds gamification), NOT as gradebook truth —
   documented limitation of client-side H5P.
7. **Instructor UI**: in edit-course lesson editor — content-type select (Video | H5P
   interactive), H5P picker (list own uploads + upload new), preview button.
8. Endpoints under `/api/v1/h5p`: POST finalize-from-chunked-upload (or direct small upload
   ≤20MB), GET list (own, instructor), GET meta, DELETE (own, only when no lesson references),
   POST result, GET results (instructor: per-content per-course rollup).

## C. Certificate Designer (instructors) + Templates

Recon verdict: builder exists (admin-only) but **is not what students receive** — issued certs
render hand-authored HTML files via slug lookup; builder templates only reach a ReportLab
preview capped to base-14 fonts. Locked decisions:

1. **Unify on `elements_config` as the single design format.** New server module
   `certificate_html_renderer.py`: `elements_config` → self-contained HTML document
   (absolute-positioned divs, Google Fonts `<link>` from a **curated 12-font list**, background
   image/color, QR container) → fed to the EXISTING Chrome render pipeline
   (`_render_html_pdf_via_chrome`) → same caches. ReportLab preview stays as fast fallback
   when Chrome is unavailable. Issuance path: `resolve_template` prefers a `Certificate` row
   WITH non-empty `elements_config` → dynamic HTML; rows with a `post_name` slug keep the
   legacy file path (the 5 existing designs keep working untouched).
2. **Placeholders become typed tokens**, not sentinel text: element types `student_name`,
   `course_name`, `completion_date`, `certificate_id`, `qr_code` (NEW — renders verify-URL QR
   server-side via the `qrcode` python lib as embedded data-URI), `instructor_name`,
   `signature_image`, `text`, `image`, `rect`, `line`. The HTML generator substitutes real
   values; sample values for preview.
3. **Instructor access**: instructors get template CRUD scoped to OWN templates
   (`post_author`), assignable only to OWN courses; admins see/edit all + can mark a template
   `is_global` (usable by every instructor). The legacy primitive instructor `/templates/`
   CRUD in certificates.py is superseded: routes remain for compat but redirect logic/marked
   deprecated in docstrings (do not delete — frontend course editor uses `/templates/list`
   which now also includes ready builder templates).
4. **Designer frontend upgrade** (the existing template-builder.tsx grows up, moved to shared
   `components/certificates/designer/` and exposed at `/instructor/certificate-designer`
   (+ kept in admin): drag + resize handles + rotate, snap-to-center guides, z-order
   (layers panel), zoom (50–150%), undo/redo (bounded stack 50), font picker (the curated 12
   with live loading), color pickers, QR + shapes + signature elements, orientation/size
   presets (A4 landscape/portrait, square), template gallery with thumbnails, live server
   preview (Chrome path) + instant canvas preview. Autosave draft to localStorage.
5. **5 new seed templates** authored AS `elements_config` rows (renderable end-to-end,
   distinct art directions: Ivory Classic / Midnight Gold / Tamil Heritage (respect the
   platform's Tamil identity — tasteful motif, no clip-art) / Gradient Modern / Minimal Mono),
   seeded idempotently like seed_certificate_templates.py, thumbnails generated via the
   render pipeline at seed time (or a make-thumbnails script when Chrome absent locally).
6. **Safety**: template edits do NOT retroactively change already-rendered certs (render cache
   keyed by issued cert stays; purge endpoint exists). Instructor-uploaded designer images go
   through the existing image upload endpoint (Pillow-verified) — no new raw upload path.
   QR/verify URLs keep using the existing hash mechanism.

## D. Gamification

Recon: streak math exists twice (dashboard + superadmin), heatmap exists, confetti/achievement
toast exists in the player, Hall of Fame is deliberately anti-ranking. Locked decisions:

1. **Event-sourced points.** `xp_events` (Integer PK, user FK, event_key String(120) UNIQUE —
   idempotency, e.g. `lesson:123:completed:user:9`, event_type, points, course_id nullable,
   meta JSON, created_at) + `user_game_stats` (user FK unique, total_xp, level, current/longest
   streak, last_active_date, badges_count) maintained transactionally by ONE service:
   `gamification_service.award(db, user_id, event_type, event_key, course_id, meta)` — no-op
   on duplicate key; called best-effort (never fails the host request) from the existing
   trigger points: lesson complete (+10), quiz passed (+20, +10 bonus ≥90%), assignment
   submitted (+10) / graded ≥ passing (+15), course completed (+100), live-class attended-
   present (+25, hook in finalize_attendance), H5P completed (+10), daily-first-activity
   (+5, also advances streak), streak milestones 7/30/100 days (+50/+200/+500).
2. **Levels**: thresholds `level_n = 100 * n * (n+1) / 2` (L1=100, L2=300, L3=600 …); computed,
   not stored magic.
3. **Badges**: `badges` table seeded with ~15 rule-based badges (first-lesson, course-finisher,
   3 courses, quiz-ace (5 quizzes ≥90%), streak-7/30/100, early-bird (activity before 7am),
   night-owl, live-regular (5 live classes), h5p-explorer, assignment-perfect, xp levels
   5/10) + `user_badges` (unique user+badge). Awarded inside the same service transaction.
4. **Streak unification**: `gamification_service.touch_streak(db, user)` becomes THE
   implementation; `dashboard.py` reads from user_game_stats (its `_compute_streaks` retired
   to fallback for users with no stats row yet); superadmin table reads the same stats.
5. **Leaderboard**: opt-out-able (user_game_stats.leaderboard_visible default True; toggle in
   profile). Endpoints: global top-50 + per-course top-20 + "your rank" (computed, cached in
   Redis 300s w/ MockRedis fallback = direct query). Displays display_name + level + XP only.
   Hall of Fame page untouched — leaderboard is a separate `/leaderboard` page; its copy
   explicitly frames it as friendly weekly motivation.
6. **Frontend**: dashboard gets XP/level card (progress ring to next level) + real streak card
   (replaces stub; flame + weekly dots + heatmap link) + latest badges strip; `/leaderboard`
   page (global/per-course tabs); profile badges grid with earn-dates; award moments reuse
   `showAchievementNotification` + confetti (level-up + badge events returned in API response
   headers or a `GET /api/v1/gamification/me/unseen` poll on dashboard load with mark-seen).
7. **Student API**: `/api/v1/gamification/me` (stats+badges+recent events), `/me/unseen`,
   `/leaderboard?scope=global|course:{id}`, POST `/me/settings` (visibility).

## Cross-cutting (BINDING, from repo conventions + prior plans)
- Integer PKs; NO response envelopes (response_model per endpoint); AuthService guards;
  tz-aware datetimes (SQLite drops tzinfo — reuse `_as_utc` patterns); MockRedis fallbacks;
  additive-only; never touch legacy root stack; no secrets.
- Migrations: Alembic `0003_learning_experience` with has_table/has_index guards (init_db
  create_all dual-path stays); models are source of truth.
- Gates per task: backend zero NEW pytest failures vs baseline family (bcrypt now fixed
  locally — baseline may have shrunk; re-baseline once at Task 1 and record in ledger);
  vitest all green incl. new suites; type-check zero new vs 391; no ESLint config (skip).
- Frontend theme: reuse dashboard primitives (StatCard/SectionCard tone map — new tones must
  be added to the static map), ui primitives, existing animation utils.
- Award/gamification calls in hot request paths are best-effort try/except (never 500 the
  host endpoint) and synchronous (no new loops).

## Out of scope (documented future phases)
In-platform H5P authoring; question banks/import; plagiarism; proctoring; peer review;
seasonal leaderboards/teams; certificate marketplace; Flutter parity for all four features
(mobile gets read-only gamification stats via existing dashboard API only — no new Flutter
work this branch).
