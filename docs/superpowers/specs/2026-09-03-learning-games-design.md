# Learning Games Builder — Design Spec

**Date:** 2026-09-03
**Branch:** `learning-games` (worktree `.worktrees/learning-games`, forked from `revenue-platform` @ 6d937c3)
**Goal:** A native game engine + builder so instructors create concept-based learning games themselves (no external tools), attach them to courses as lessons, and students play them with scores, XP, and progress tracking — end to end inside Sasha.

## Why native (vs H5P only)

H5P already covers *imported* interactive content. This feature gives instructors a **zero-file, in-LMS builder**: pick a template, type in their concept items, preview live, publish. No authoring software, no uploads, mobile-friendly, and fully integrated with Sasha's XP/progress systems.

## 1. Game templates (5 at launch)

One JSON `config` drives everything. `max_score` is always **derived server-side as `10 × item count`** (uniform rule; engines allocate partial credit within it).

| template key | Gameplay | config shape (binding) |
|---|---|---|
| `quiz_rush` | Timed MCQ race; per-question countdown; faster answer = more of the 10 pts (floor 4 on correct, 0 wrong); streak ×1.5 multiplier capped at max_score | `items: [{prompt, options: [2..6 strings], answer_index}]` (1..50 items), `settings: {seconds_per_question: 5..120 (default 20), shuffle: bool}` |
| `match_pairs` | Memory grid; flip two cards to match concept↔definition; 10 pts per pair minus 1 per extra miss on that pair (floor 3) | `items: [{left, right}]` (3..12 pairs), `settings: {time_limit_s: 0(off)..600}` |
| `drag_sort` | Drag items into category buckets; 10 pts per correctly placed item, one attempt each (wrong placement bounces back, −3 retry penalty, floor 2) | `categories: [{name}] (2..5)`, `items: [{text, category_index}]` (4..40), `settings: {time_limit_s: 0..600}` |
| `word_builder` | Unscramble letter tiles to spell the answer for a clue; 10 pts, −2 per hint used | `items: [{clue, answer}]` (1..20; answer = letters/digits/spaces, 2..24 chars), `settings: {hints_allowed: 0..3}` |
| `sequence` | Arrange steps into correct order; 10 pts per item in correct final position, one submit + one retry (−3 on retry) | `items: [{text}]` in correct order (3..10), `settings: {time_limit_s: 0..600, shuffle: true always}` |

**Validation (server, per-template pydantic):** enum template; item/category counts per table above; every string ≤500 chars (prompt/clue/left/right/text/name), options ≤200 chars each; whole `config` JSON ≤64KB serialized; `answer_index`/`category_index` must be in range; `word_builder.answer` matches `^[A-Za-z0-9 ]{2,24}$`. Reject unknown top-level keys. All limits re-validated on every update and at publish.

## 2. Data model (alembic revision `0004_learning_games`, guarded like 0002/0003)

- `games`: `id PK`, `owner_id FK users.id (indexed)`, `title VARCHAR(200) NOT NULL`, `template VARCHAR(32) NOT NULL`, `config JSON NOT NULL`, `status VARCHAR(16) NOT NULL DEFAULT 'draft'` (`draft|published`), `created_at`, `updated_at` (tz-aware pattern per repo).
- `game_results`: `id PK`, `game_id FK games.id (indexed)`, `user_id FK users.id (indexed)`, `score INT NOT NULL`, `max_score INT NOT NULL`, `duration_s INT NOT NULL DEFAULT 0`, `created_at`. Multiple attempts kept; "best score" computed in queries.
- `lessons`: add `game_id FK games.id NULL` via `batch_alter_table` (SQLite FK pattern from 0003); extend `lesson_content_type` allowed set to `('video','h5p','game')`.
- Migration uses `has_table`/`has_column` guards; downgrade drops in reverse.

## 3. Backend API — router `app/routers/games.py`, prefix `/api/v1/games`

⚠ `redirect_slashes=False`: **add `'/games'` to `noSlashEndpoints` in `frontend/src/api/axios.ts`** (the gamification 404 lesson).

Instructor (require_instructor, owner-scoped; admin sees all):
- `POST /games` — create draft `{title, template, config}` → validated, returns game.
- `GET /games/mine` — list own games (id, title, template, status, item_count, updated_at, attached_lesson_count).
- `GET /games/{id}` — full game incl. config (owner/admin only while draft; any instructor CANNOT read others' configs — owner/admin only, always).
- `PUT /games/{id}` — update title/config (owner/admin; re-validates; allowed also when published).
- `POST /games/{id}/publish` / `POST /games/{id}/unpublish` — status flips; publish re-runs full config validation; unpublish blocked with 409 if attached to any lesson (message tells them to detach first).
- `DELETE /games/{id}` — owner/admin; blocked 409 if attached to any lesson.
- `GET /games/{id}/results` — owner/admin: per-student best score, attempts count, last played (join users; display_name only, no emails).

Student (require login):
- `GET /games/{id}/play` — playable payload for a **published** game where the requester is **enrolled in a course containing a lesson attached to this game** (or is the owner/admin — preview). The payload includes answers (grading is client-side for instant feedback) and scores are therefore **advisory only** — game results NEVER enter the gradebook; the assessment engine remains the graded path. This matches the H5P advisory-score decision.
- `POST /games/{id}/results` — body `{score, max_score, duration_s}`; server **recomputes max_score from config** and clamps `score` to `[0, derived_max]`, `duration_s` to `[0, 86400]`; same enrollment/publish gate as `/play`; owner preview does NOT write results (403 with clear message or silently skipped — return `{"preview": true}` skip). On a student's **first** completed result: award XP.

Lesson attach: extend the existing atomic pair helper in `app/routers/courses.py` — `lesson_content_type='game'` requires `game_id`; game must exist, be `published`, and be **owned by the caller** (admin any) — mirrors H5P rules incl. clearing FK on flip back to video and the "pair or 400" contract.

## 4. XP integration (gamification patterns are LAW here)

- `award()` is flush-only; caller owns the transaction; use SAVEPOINT duplicate-key isolation as existing call sites do.
- Event keys: `game:{game_id}:completed:user:{user_id}` (+20 XP, first completion with score>0) and `game:{game_id}:perfect:user:{user_id}` (+10 XP, first `score == max_score`).
- Hooks wrapped best-effort `try/except` per repo pattern; never fail the results POST because XP hiccuped.
- Badge: add `game_on` badge — "Completed your first learning game" (lucide icon `gamepad-2`), awarded on first `game:*:completed` event; follow existing badge-definition pattern.

## 5. Lesson completion

Mirror the H5P lesson flow exactly (read how `lesson-redesigned.tsx` + progress flow mark an H5P lesson complete, and reuse that mechanism for `game` lessons after the student's result POST succeeds). Game lessons therefore count in `calculate_course_progress` with zero new progress infrastructure.

## 6. Frontend

**API client:** `frontend/src/api/games.ts` (typed; mirrors `api/h5p.ts` conventions).

**Shared engine components — `frontend/src/components/games/`:**
- `GameShell.tsx` — frame every template renders inside: title bar, timer ring (SVG), score counter, progress dots, pause, results screen (score, best score, XP toast hook, replay button, confetti — pure CSS/SVG, `prefers-reduced-motion` respected).
- `engines/QuizRush.tsx`, `engines/MatchPairs.tsx`, `engines/DragSort.tsx`, `engines/WordBuilder.tsx`, `engines/SequenceGame.tsx` — pure-props components: `(config, onComplete({score, maxScore, durationS}))`; deterministic scoring functions exported separately for unit tests. Drag interactions use `@dnd-kit` (already a repo dependency) with touch support.
- `GamePlayer.tsx` — fetches `/games/{id}/play`, dispatches to engine, POSTs result on complete, fires lesson-complete when embedded in a lesson (prop), `previewOnly` mode for instructors (no result POST) — mirrors `H5PLesson` semantics.
- `GamePicker.tsx` — curriculum picker: list own **published** games + "Create new game →" link; used in BOTH `edit-course.tsx` and `create-course.tsx` content-type flow (extend the selector to `Video | H5P interactive | Learning game`; the atomic pair sync pattern from commit 6d937c3 applies to `game_id` identically).

**Pages:**
- `pages/instructor/games.tsx` — library: template gallery cards (5 templates, SVG illustrations, description), own games table (status chip, attempts, avg score, edit/publish/delete).
- `pages/instructor/game-builder.tsx` — `/instructor/games/:id/edit` + `/instructor/games/new?template=X`: settings panel + per-template item editor (add/remove/reorder rows; inline validation matching server caps) + **live preview** pane running the real engine with `previewOnly`.
- `pages/game-play.tsx` — student standalone route `/games/:id/play`.
- `lesson-redesigned.tsx` — render `GamePlayer` when `lesson_content_type === 'game'` (alongside the existing h5p branch).
- **Nav:** add "Games" to instructor nav in `nav-configs.ts` (NOT the dead `components/layout/header.tsx`). Routes registered wherever the H5P/gradebook routes were registered.

**Design language:** existing Tailwind design system; template accent colors; game assets are inline SVG/CSS only (no external images); everything responsive + touch-first.

## 7. Security summary

- Config: strict pydantic per-template schemas, size caps, unknown-key rejection — instructor JSON is untrusted input rendered to other users' browsers: **all item strings render as text, never HTML** (React default escaping; no `dangerouslySetInnerHTML` anywhere in games code).
- Ownership: only owner/admin read full config of drafts, update, publish, see results; students only get published+enrolled `/play`.
- Results: server-derived max_score, clamped score/duration; advisory only (never gradebook); rate-irrelevant (idempotent XP).
- No file uploads in this feature (nothing to harden beyond JSON).

## 8. Tests (binding)

- Backend `tests/test_games.py`: template validation matrix (valid+invalid per template incl. oversize config, bad indices, unknown keys), CRUD ownership (instructor A cannot read/update/delete B's), publish/unpublish/delete 409 rules, play-gate (unenrolled 403/404, draft 404, owner preview ok), results clamping + derived max_score, XP idempotency (two completions → one `completed` event), perfect-score bonus, lesson attach pair rules for 'game' (mirror the h5p helper tests), migration columns exist. SQLite in-memory per repo pattern; baseline suite must stay green.
- Frontend vitest: scoring functions per engine (deterministic cases), builder validation helpers, GamePicker (mirrors H5PPicker tests), GamePlayer result POST + previewOnly suppression.

## 9. Docs & seed

- `docs/LEARNING_GAMES.md` — instructor guide + API reference + template config reference.
- `CLAUDE.md` — feature entry (traps: noSlashEndpoints, award() flush-only, atomic pair).
- `backend/seed_games_demo.py` — throwaway demo seed: one published game per template owned by priya@sashademo.com, one attached to course 1 as a lesson (idempotent-ish like other seeds).

## Out of scope (explicitly)

Graded games in the gradebook, multiplayer/real-time games, AI-generated game content, per-question analytics dashboards, game marketplace between instructors, custom templates beyond the 5.
