# Learning Games

Native, zero-file learning games built entirely inside Sasha: instructors
pick a template, type in their own concept items, preview live, and
publish — no external authoring tool, no file upload, mobile-friendly, and
fully wired into Sasha's existing XP/progress systems.

Implementation plan: `docs/superpowers/plans/2026-09-03-learning-games.md`.
Design spec: `docs/superpowers/specs/2026-09-03-learning-games-design.md`.
Full task-by-task ledger: `.superpowers/sdd/2026-09-03-learning-games/progress.md`.

---

## Why native (vs H5P)

H5P (see `docs/LEARNING_EXPERIENCE.md`) already covers *imported*
interactive content — instructors upload a `.h5p` package authored
externally (lumi.education) and Sasha plays it back in a sandboxed iframe.
Learning Games is the opposite direction: a **zero-file, in-LMS builder**.
An instructor never leaves Sasha, never touches authoring software, and
never uploads anything — they pick one of 5 templates, fill in a form,
watch a live preview render the real game engine against their draft, and
publish. The tradeoff is fixed templates instead of H5P's open-ended
content types; in exchange, instructors get a faster, mobile-friendly
authoring loop for the common case (a quiz, a matching game, a sorting
drill, a word puzzle, a sequencing exercise) without any file-upload attack
surface at all.

---

## Instructor guide

### Creating a game

1. Go to **Games** in the instructor nav (`frontend/src/pages/instructor/games.tsx`,
   route `/instructor/games`). The page shows a 5-card template gallery
   (Quiz Rush, Match Pairs, Drag Sort, Word Builder, Sequence) plus a table
   of your own games (title, template, status, item count, attached-lesson
   count, last updated).
2. Click **Create** on a template card. This opens the builder at
   `/instructor/games/new?template=<template>`
   (`frontend/src/pages/instructor/game-builder.tsx`).
3. Give the game a title (1–200 characters) and fill in the per-template
   item editor:
   - **Quiz Rush** — one or more questions, each with 2–6 answer options and
     a radio button marking the correct one; a settings panel sets seconds
     per question and whether question order shuffles.
   - **Match Pairs** — a list of left/right pairs (concept ↔ definition,
     term ↔ translation, etc.) and an optional time limit.
   - **Drag Sort** — 2–5 categories, then items each assigned to a category
     via a dropdown; reordering/removing a category automatically re-points
     or drops items that referenced it.
   - **Word Builder** — a clue + answer per word (answer restricted to
     letters/digits/spaces) and how many hints a player may use.
   - **Sequence** — steps entered in their *correct* order (this order is
     the answer key — the player sees them shuffled).
   Every editor supports add/remove/reorder (up/down) on its rows, and
   shows a "N left" character-remaining hint once a field gets close to its
   cap.
4. Inline validation (`frontend/src/components/games/builderValidation.ts`,
   a client-side mirror of the server's caps) lists any problems ("Fix
   before saving") and disables **Save draft** / **Publish** until they're
   clear. It also surfaces **non-blocking duplicate warnings** in a
   separate amber panel (see "Duplicate warnings" below) — these never
   block saving or publishing, since a duplicate is a content-quality
   nudge, not a validity error.
5. The **live preview** pane (right side, desktop) runs the actual play
   engine component against your unsaved draft in-memory — no network call,
   no result is recorded. Use **Restart preview** to reset it after edits.
6. **Save draft** stores the game (`POST /games` on first save, `PUT
   /games/{id}` after). A draft is visible only to you; students can never
   see or play it.

### Publishing

Click **Publish** (it saves first, then calls `POST /games/{id}/publish`).
Publishing re-runs the *full* server-side validation — a game with defaults
that happened to pass client-side but not the server's strict schema will
come back as a 400 with the exact validation error. A published game can
still be edited (`PUT` is allowed on published games) and republished;
there is no separate "review" state.

To take a published game offline, **Unpublish** it — this is blocked with
a 409 if any lesson still references it ("detach it from those lessons
first"). **Delete** has the same 409 guard.

### Attaching a game to a lesson

In the course builder (`edit-course.tsx` / `create-course.tsx`), a lesson's
content-type selector now offers three options: **Video**, **H5P
interactive**, and **Learning game**. Choosing "Learning game" opens
`GamePicker.tsx` — a list of your own **published** games (drafts can't be
attached) plus a "Create new game →" link that jumps to the builder. Only
one game can back a lesson at a time; switching a lesson's type away from
`game` clears the attachment (see "Atomic pair contract" below).

### Reading results

Back on the Games library page, click **Results** on any of your games to
open a per-student rollup (`GET /games/{id}/results`): display name (never
email), best score / max score, number of attempts, and when they last
played. There is no per-question analytics breakdown — see "Out of scope"
in the design spec.

---

## Template config reference

`max_score` is **never stored** — it is always derived **server-side as
`10 × item count`** (`len(config["items"])`, uniformly across all 5
templates; `drag_sort` counts *items*, never categories). The client
mirrors this rule only for display (`deriveMaxScore` in
`frontend/src/components/games/engines/scoring.ts`); the server's derived
value is what actually gets stored on a `GameResult` row.

| template key | Gameplay | config shape (binding) |
|---|---|---|
| `quiz_rush` | Timed MCQ race; per-question countdown; faster answer = more of the 10 pts (floor 4 on correct, 0 on wrong); streak ×1.5 multiplier capped at max_score | `items: [{prompt, options: [2..6 strings], answer_index}]` (1..50 items), `settings: {seconds_per_question: 5..120 (default 20), shuffle: bool}` |
| `match_pairs` | Memory grid; flip two cards to match concept↔definition; 10 pts per pair minus 1 per miss on that pair (no free first miss), floor 3 | `items: [{left, right}]` (3..12 pairs), `settings: {time_limit_s: 0(off)..600}` |
| `drag_sort` | Drag items into category buckets; 10 pts per correctly placed item, one attempt each (wrong placement bounces back, −3 retry penalty, floor 2) | `categories: [{name}] (2..5)`, `items: [{text, category_index}]` (4..40), `settings: {time_limit_s: 0..600}` |
| `word_builder` | Unscramble letter tiles to spell the answer for a clue; 10 pts, −2 per hint used | `items: [{clue, answer}]` (1..20; answer = letters/digits/spaces, 2..24 chars, `^[A-Za-z0-9 ]{2,24}$`), `settings: {hints_allowed: 0..3}` |
| `sequence` | Arrange steps into correct order; 10 pts per item in correct final position, one submit + one retry (−3 on retry) | `items: [{text}]` in correct order (3..10), `settings: {time_limit_s: 0..600, shuffle: true always}` |

**Scoring semantics — ruled interpretations (this plan's "Resolved spec
ambiguities," binding):**
- **quiz_rush speed mapping:** points for a correct answer =
  `round(4 + 6 × (time_remaining / seconds_per_question))`, so a correct
  answer is always in `[4, 10]`. A wrong answer scores 0.
- **quiz_rush streak:** the ×1.5 multiplier applies to a question's points
  starting on the **3rd consecutive correct answer** (i.e. once the streak
  of consecutive correct answers *before* the current one reaches 2 — the
  current answer is then the 3rd in a row). The running total is capped at
  `max_score` (`capScore` in `scoring.ts`).
- **match_pairs miss penalty:** every miss on a pair costs 1 point off that
  pair's 10 — there is **no free first miss**; the floor is 3 (so a pair
  that took 7+ misses to solve still nets 3 points, never fewer).
- **drag_sort retry penalty:** each wrong bounce-back before the correct
  placement costs 3 points off that item's 10, floor 2.
- **word_builder hints:** each hint used costs 2 points off that word's 10;
  the spec sets no floor, but `hints_allowed` is capped at 3, so the
  practical minimum on one word is 4.
- **sequence retry:** the −3 penalty is applied **per item**, not once —
  items scored on the accepted retry submit earn 7 points each instead of
  10 (only one retry is allowed; the second submit is final).

**Validation caps (server, strict per-template pydantic,
`backend/app/schemas/game_config.py`):** every string ≤500 characters
(`prompt`/`clue`/`left`/`right`/`text`/`name`), options ≤200 characters
each — these are **character** counts, not byte counts (a 500-character
string of multi-byte UTF-8 can serialize to several KB; only the 64KB
whole-config cap is byte-based). `answer_index` / `category_index` must be
in range for their sibling list. `word_builder.answer` must fullmatch
`^[A-Za-z0-9 ]{2,24}$`. Every string is stripped of leading/trailing
whitespace and rejected if empty after stripping. Unknown keys are
rejected at **every** nesting level (`extra="forbid"` throughout — not
just the top level). All of the above is re-validated on every `PUT`
**and again at publish**.

---

## API reference

Router: `backend/app/routers/games.py`, mounted at `/api/v1/games`.
Response style: plain dicts, no envelopes (matches `h5p.py`/`gradebook.py`).
**Every route is declared without a trailing slash** — see "noSlashEndpoints
trap" below.

### Instructor endpoints (`require_instructor`; owner-scoped, admin sees all)

| Method & path | Auth | Request | Response | Notes |
|---|---|---|---|---|
| `POST /games` | instructor | `{title, template, config}` | full game incl. `config` | Creates a `draft`. Config fully validated; 400 on any violation. |
| `GET /games/mine` | instructor | — | `{games: [...], count}` | Own games (admin: all). Summary rows only — **no `config`** — `id, owner_id, title, template, status, item_count, max_score, attached_lesson_count, created_at, updated_at`. |
| `GET /games/{id}` | owner/admin only | — | full game incl. `config` | 403 for any other instructor, even on a published game — **no other instructor can ever read a game's config.** 404 if the id doesn't exist. |
| `PUT /games/{id}` | owner/admin | `{title?, config?}` | full game | Re-validates `config` if supplied (400 on violation); allowed even while published. |
| `POST /games/{id}/publish` | owner/admin | — | full game | Re-runs full config validation (400 with `Cannot publish: ...` detail on failure); flips `status` to `published`. |
| `POST /games/{id}/unpublish` | owner/admin | — | full game | 409 if any lesson still references the game (`Cannot unpublish: N lesson(s) still use this game. Detach it from those lessons first.`). |
| `DELETE /games/{id}` | owner/admin | — | `{success: true, id}` | 409 with the same "still use this game" message if attached; also deletes the game's `GameResult` rows. |
| `GET /games/{id}/results` | owner/admin | — | `{game_id, results: [...], count}` | Per-student rollup: `user_id, user_name (display_name — never email), best_score, max_score, attempts, last_played`. `max_score` is paired with the **same row** as `best_score` (a config edit can change the derived max between attempts — the rollup never chimera-pairs a score from one attempt with a max_score from another). |

Per-student game data (best score, attempts, last played) lives entirely in
this Results drawer rollup — there is no separate average-score column on
the instructor library, since the per-student rows already give a finer-
grained picture than a single aggregate would. Likewise there is no
dedicated XP "toast" hook wired into game completion — XP earned from a
game rides the same lesson-completion flow/notification path as every
other completion trigger (H5P, quizzes, assignments), rather than a
game-specific popup.

### Student/player endpoints (`get_current_user` — any logged-in user)

| Method & path | Auth | Request | Response | Notes |
|---|---|---|---|---|
| `GET /games/{id}/play` | any logged-in user | — | `{id, title, template, config, max_score, preview}` | **Owner/admin:** always allowed, `preview: true`. **Everyone else:** the game must be `published` (a draft 404s — this hides drafts entirely rather than leaking their existence via 403) **and** the caller must be actively enrolled in a course containing a lesson attached to this game (403 otherwise: "You must be enrolled..."). The payload **includes answers** — grading is client-side for instant feedback, so results are advisory only (see "Advisory scores" below). |
| `POST /games/{id}/results` | any logged-in user | `{score, max_score, duration_s}` (all `StrictInt`) | `{game_id, user_id, score, max_score, duration_s, best_score, created_at}` **or** `{"preview": true}` | Same gate as `/play`. Owner/admin preview writes **nothing** — returns `{"preview": true}` and skips. Otherwise the server **recomputes `max_score` from the stored config** (never trusts the client's number) and **clamps** `score` to `[0, derived_max]` and `duration_s` to `[0, 86400]` before storing. On success, XP is awarded best-effort (see below). |

### Error codes at a glance

- **400** — config validation failure (create/update/publish), or a
  malformed request body.
- **403** — non-owner instructor reading/mutating someone else's game;
  student not enrolled in a course carrying this game's lesson.
- **404** — game id doesn't exist; or (for `/play` and `/results` POST) the
  game exists but is a draft and the caller isn't owner/admin — drafts are
  hidden behind 404, not 403, so their existence isn't leaked to students.
- **409** — unpublish or delete blocked because ≥1 lesson still references
  the game.

### Lesson attach (in `backend/app/routers/courses.py`, not `games.py`)

Attaching a game to a lesson goes through the *existing* atomic-pair helper
(`_resolve_lesson_content_fields`, formerly `_resolve_lesson_h5p_fields`,
renamed and extended for `game`), on the course-builder's create/update
lesson endpoints — there is no separate "attach" endpoint under
`/games`. `lesson_content_type='game'` requires `game_id` in the same
request; the referenced game must exist (404), be `published` (400
otherwise), and be owned by the caller (403 otherwise — admin may attach
any game). Flipping a lesson's type clears the FK(s) that no longer apply:
`video` clears both `h5p_content_id` and `game_id`; `h5p` clears `game_id`;
`game` clears `h5p_content_id`. See "Atomic pair contract" below for why
this must always be a single request.

---

## Security model

- **Untrusted-config posture.** Instructor-authored `config` JSON is
  untrusted input that gets rendered into *other users'* browsers (every
  enrolled student who plays the game). It is validated with strict
  per-template pydantic schemas, `extra="forbid"` at every nesting level
  (not just the top level — rejects unknown keys anywhere in the tree), a
  64KB serialized-size cap, and in-range index checks
  (`answer_index`/`category_index`). All of it is re-validated on every
  update and again at publish — a game can never carry a config that
  passed validation under an old, looser rule.
- **React-text-only rendering.** Every item string (prompt, option, clue,
  answer, left/right, category/item text) renders as plain React text via
  default JSX escaping. **There is zero `dangerouslySetInnerHTML` anywhere
  under `frontend/src/components/games/`, `pages/instructor/games.tsx`,
  `pages/instructor/game-builder.tsx`, or `pages/game-play.tsx`** — this is
  a hard invariant, checked by grep in the plan's final verification sweep
  and re-checked at every task's code review.
- **Ownership matrix.** Only the owner or an admin can ever read a game's
  full `config` (`GET /games/{id}`), update it, publish/unpublish it,
  delete it, or view its results — this holds for **both** draft and
  published games; there is no "any instructor can view a published game's
  config" carve-out. The one deliberate exception: an instructor who is
  *not* the owner but is enrolled as a **student** in a course carrying the
  game's lesson can read the config through `GET /games/{id}/play` — this
  is not a leak, it's the same payload every enrolled player gets by
  design (grading is client-side, so the play payload always includes
  answers). The `/play` surface and the CRUD/authoring surface have
  deliberately different access rules; don't conflate them.
- **Advisory scores, never gradebook.** Because `/play` ships answers to
  the client and grading happens client-side for instant feedback, game
  results are **advisory engagement data only** — they never enter the
  gradebook and the assessment engine (quizzes/assignments) remains the
  one graded path. This is the identical posture to H5P's advisory scores
  (`docs/LEARNING_EXPERIENCE.md`).
- **Server-derived max + clamping.** `max_score` is never trusted from the
  client — the server always recomputes it from the stored `config`
  (`derive_max_score`) before storing a result, and clamps the reported
  `score` into `[0, derived_max]` and `duration_s` into `[0, 86400]`. A
  compromised or buggy client cannot inflate a score or a badge/XP award.
- **No file uploads.** Unlike H5P, this feature has no upload surface at
  all — there is nothing to harden beyond the JSON validation above (no
  zip-bomb, path-traversal, or extension-spoofing class of bug applies
  here).

---

## XP & lesson completion

- **Event keys** (idempotent — `xp_events.event_key` is the dedup key):
  - `game:{game_id}:completed:user:{user_id}` — **+20 XP**, awarded once,
    on the student's first result with `score > 0`.
  - `game:{game_id}:perfect:user:{user_id}` — **+10 XP**, awarded once, on
    the student's first result where `score == max_score` (the *derived*
    max_score, post-clamping).
  - `award()` is **flush-only** — the caller (the results-POST handler)
    owns the transaction and commits. It uses a SAVEPOINT
    (`db.begin_nested()`) for duplicate-key isolation, and every call site
    wraps it in a best-effort `try/except`: an XP/gamification hiccup logs
    a warning and rolls back only the gamification-side work — it can
    **never** fail the `/results` POST itself (the `GameResult` row is
    already committed before XP is attempted).
- **Badge:** `game_on` ("Completed your first learning game", lucide icon
  `gamepad-2`) — awarded on the first `game:*:completed` event, via the
  same badge-definition pattern as every other gamification badge
  (`app/services/gamification_service.py`).
- **Lesson completion.** A `game` lesson reuses the **exact** H5P
  lesson-complete mechanism: after a student's result POST succeeds,
  `lesson-redesigned.tsx`'s `handleGameCompleted` (a byte-for-byte copy of
  `handleH5PCompleted`, same double-fire guard) calls the existing `POST
  /courses/{courseId}/lessons/{lessonId}/complete`. No new progress
  infrastructure was added — `calculate_course_progress` already counts
  any completed lesson regardless of content type.

---

## Ops

- **Migration:** revision `0004_learning_games` (down_revision `0003`)
  adds the `games` and `game_results` tables and `lessons.game_id`
  (`batch_alter_table`, SQLite-safe) plus the extended
  `lesson_content_type` allowed set (`video|h5p|game`). Guarded with
  `has_table`/`has_column` checks throughout, dual-path tolerant with
  `init_db()`'s `create_all` (an existing DB where `create_all` already
  made these tables gets a clean no-op "already exists — skipping"; a bare
  DB gets the tables created by the migration itself). Run:
  ```
  alembic upgrade head
  ```
  from `backend/`, against whatever `DATABASE_URL` you're targeting — this
  is what actually picks up `0004` on an existing database; `init_db()`
  alone only creates *missing* tables and never adds a column to an
  existing table.
- **Demo seed:** `backend/seed_games_demo.py` — throwaway, follows the same
  env-bootstrap pattern as `seed_assessment_demo.py` (defaults
  `DATABASE_URL` to `sqlite:///./visual_qa.db` if unset, sets the other
  required env vars). Creates one **published** game per template (5
  games), owned by `priya@sashademo.com`, each with 4–6 real learning
  items (HTML/CSS quiz, cell-biology matching, frontend-vs-backend
  sorting, web-dev spelling, HTTP-lifecycle sequencing — no lorem ipsum),
  and attaches the `quiz_rush` game to course 1 as a `game` lesson.
  Idempotent-ish: reruns skip creation when a game/lesson with the same
  title already exists. Requires `priya@sashademo.com` to already exist
  (run the base demo-user seed first) and prints a message and exits
  cleanly if it doesn't. Run from `backend/`:
  ```
  python seed_games_demo.py
  ```
  **Do not point this at a shared/live demo database without checking
  first** — it's intended for a scratch or dev database (set
  `DATABASE_URL` to override the sqlite default, or export it before
  running).
- **`'/games'` noSlashEndpoints trap.** The backend runs FastAPI with
  `redirect_slashes=False` repo-wide, and every route in `games.py` is
  declared **without** a trailing slash (`@router.post("")`, not
  `@router.post("/")`). The frontend axios instance
  (`frontend/src/api/axios.ts`) maintains a `noSlashEndpoints` allowlist
  that suppresses its own trailing-slash-normalization logic for matching
  paths — `'/games'` **must** stay in that list, or every `api/games.ts`
  call silently 404s (this is the exact failure mode gamification hit
  before its own endpoints were added to the list — same lesson, same
  fix). If you add a new games route, make sure it's declared without a
  trailing slash and that its prefix is still covered by the existing
  `'/games'` entry (it is, for anything under `/games/...`).
- **Frontend routes:** `/instructor/games`, `/instructor/games/new`,
  `/instructor/games/:id/edit` (all instructor-only, `InstructorLayout`),
  `/games/:id/play` (student, `StudentLayout`) — registered in
  `frontend/src/App.tsx` alongside the equivalent H5P/certificate-designer
  routes.

---

## Frontend architecture map

- **API client:** `frontend/src/api/games.ts` — typed wrapper around every
  endpoint above, mirrors `api/h5p.ts` conventions. `Game` and
  `GamePlayPayload` are tagged unions on the **outer** type (one variant
  per `template`, each pairing the literal template with its own config
  type) rather than tagging the inner `config` field — this is what lets
  `game.template === 'quiz_rush'` narrow `game.config` to `QuizRushConfig`
  with zero casts.
- **Shared engine components** — `frontend/src/components/games/`:
  - `GameShell.tsx` — the frame every template renders inside (title bar,
    SVG timer ring, score counter, progress dots, pause, results screen
    with confetti — pure CSS/SVG, respects `prefers-reduced-motion`).
  - `engines/QuizRush.tsx`, `engines/MatchPairs.tsx`, `engines/DragSort.tsx`,
    `engines/WordBuilder.tsx`, `engines/SequenceGame.tsx` — pure-props
    `(config, onComplete({score, maxScore, durationS}))` components. Drag
    interactions use `@dnd-kit` (already a repo dependency, no new
    packages) with pointer **and** keyboard sensors for accessibility, but
    the keyboard interaction differs by template's drop-target shape:
    `SequenceGame` reorders a single list, so a focused drag handle uses
    dnd-kit's built-in sortable coordinate getter — Space/Enter to lift,
    arrow keys to move, Space/Enter to drop. `DragSort` places items into
    one of several fixed category zones, which dnd-kit's keyboard sensor
    has no built-in coordinate getter for; instead a focused item's
    Enter/Space opens an explicit category-picker menu (arrow keys to
    choose a category, Enter/click to place) — see `DraggableItem`'s header
    comment in `DragSort.tsx`.
  - `engines/scoring.ts` — the deterministic scoring functions described
    above, exported separately from the engines for unit testing.
  - `GamePlayer.tsx` — fetches `/games/{id}/play`, renders the right
    engine, POSTs the result on completion, and (when embedded in a
    lesson) fires the lesson-complete callback. `previewOnly` is a
    **client-side-only** prop: the instructor library/builder's live
    preview passes it explicitly to suppress the POST and the
    lesson-complete callback entirely, on the client, before any request
    is made. It is separate from (and narrower than) the server-side skip:
    when an owner/admin plays their own game through the normal
    non-preview path, `POST /games/{id}/results` still fires but the
    server recognizes the caller as the owner/admin and returns
    `{"preview": true}` **without writing** a result row — see the
    endpoint table below. So owner/admin plays are always
    server-side-skipped regardless of `previewOnly`, while the instructor
    library/builder preview is additionally skipped client-side so the
    request is never sent at all.
  - `GamePicker.tsx` — the curriculum picker used by both course-builder
    pages' lesson content-type selector.
  - `builderValidation.ts` — `validateConfigDraft` (blocking, mirrors every
    server cap) and `duplicateWarnings` (non-blocking content-quality
    nudges — see below).
- **Pages:** `pages/instructor/games.tsx` (library),
  `pages/instructor/game-builder.tsx` (create/edit), `pages/game-play.tsx`
  (student standalone play route), plus the `game` branch added to
  `pages/lesson-redesigned.tsx` alongside the existing `h5p` branch.

### Atomic pair contract (frontend side)

The frontend must **never** `PATCH`/`PUT` a lesson with
`lesson_content_type: 'game'` unless `game_id` is included in the *same*
request — the backend's `_resolve_lesson_content_fields` treats
`lesson_content_type='game'` with no resolvable `game_id` as a 400. Both
course-builder pages set the pair together in one call (the same pattern
established for `h5p_content_id` back in commit `6d937c3`).

### Duplicate warnings (non-blocking)

`builderValidation.ts` exports a second helper,
`duplicateWarnings(template, config): string[]`, separate from the
blocking `validateConfigDraft`. It flags likely authoring mistakes that
are technically valid configs but make for an unplayable or confusing
game:
- **match_pairs:** two pairs with the same `left` **and** the same `right`
  (case-insensitive, trimmed) — an unplayable duplicate pair (either card
  could match either target).
- **quiz_rush:** two options within the *same* question that are identical
  (case-insensitive, trimmed) — a question where two choices read the same
  has no unambiguous correct answer from the player's point of view.
- **drag_sort:** two categories with the same `name` (case-insensitive,
  trimmed) — items can't be told apart by category name in the UI.

These render as an **amber** warning panel in `game-builder.tsx`,
separate from the existing red "Fix before saving" error panel, and do
**not** affect the `Save draft` / `Publish` button's disabled state — a
game with duplicate content is still valid and playable, just probably not
what the instructor meant.
