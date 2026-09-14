# Content Libraries (2026-09-05)

Admin-curated libraries that instructors pull into a course curriculum:
virtual labs (incl. native gradeable labs), a shared 3D asset library, and
prebuilt learning games. Built by Fable 5.1; verified end-to-end on the dev
preview (backend :8011, frontend :3001).

## 1. Virtual labs

**Catalog = built-ins ∪ admin rows.** Built-ins are constants in
`backend/app/routers/virtual_labs.py` (`BUILTIN_LABS`). Admin rows live in
`virtual_lab_catalog` (model `app/models/content_library.py`). A row whose
slug matches a built-in *overrides* it (retitle, unpublish). Unpublished rows
are hidden from `GET /api/v1/virtual-labs` and refused by the lesson
resolver (`courses.py` → `is_valid_lab_slug(db, slug)`).

Providers:

| provider | renders as | notes |
|---|---|---|
| `phet` | iframe | `embed_url` derived from the slug when blank; CC-BY attribution auto-filled |
| `embed` | iframe | any https URL the admin adds |
| `native` | our engine | `native_template` + `config`, validated by `app/schemas/lab_config.py` |

Lessons attach by slug: `lesson_content_type='virtual_lab'` +
`virtual_lab_sim=<slug>` (atomic pair, 422 on unknown/unpublished slug).
`lessons.virtual_lab_sim` is VARCHAR(50), hence the 50-char slug cap.

### Native lab templates (gradeable by parameters, phone-friendly, no WebGL)

* **`reaction_lab`** — balance chemical equations. Config stores each
  reaction's species and the *minimal balanced coefficient set*. The
  validator parses formulas (`Ca(OH)2`, nested parentheses) and PROVES the
  key is element-balanced and in lowest terms, so a wrong answer key cannot
  be published (400 with the element totals). Frontend mirror:
  `frontend/src/components/labs/native/chemistry.ts`. Score = 10 × reactions.
* **`identify_lab`** — "find the named structure" on a diagram. `diagram` is
  a built-in key (`cell`, `skeleton` — SVGs in
  `frontend/src/components/labs/diagrams/`, drawn on a 0-100 viewBox) or an
  https image; hotspots are percent coordinates, ids unique. One attempt per
  prompt; a wrong click reveals the answer. Score = 10 × hotspots.

Shipped native labs: `reaction-lab-basics` (10 reactions, 100 pts),
`cell-biology-identify` (11 organelles, 110 pts), `skeleton-identify`
(14 bones, 140 pts). `max_score` is always DERIVED (`derive_lab_max_score`),
never stored.

Results: `POST /api/v1/virtual-labs/{slug}/results {score, duration_s}` →
`virtual_lab_results` row; XP via `gamification_service.award()` AFTER the
result commit, best-effort (`lab:{slug}:completed:user:{uid}` +20 on first
score>0, `lab:{slug}:perfect:user:{uid}` +10 on first max). Advisory only —
never gradebook truth, identical posture to games/H5P. Instructor/admin
previews pass `previewOnly` and never POST.

### API

* `GET /api/v1/virtual-labs[?subject=]` — public list (no configs).
* `GET /api/v1/virtual-labs/{slug}` — auth; native entries include `config`
  (answer key ships to the client, same as `/games/{id}/play`) + `best_score`.
* `POST /api/v1/virtual-labs/{slug}/results` — auth; 400 if score > max or
  lab is not native.
* Admin (`/api/v1/admin/content-library`, `require_admin`):
  `GET/POST /labs`, `PUT/DELETE /labs/{id}`, `POST /labs/import` (pack
  `{labs:[entry…]}`, upsert by slug, validated all-or-nothing).

## 2. Shared 3D asset library

`three_d_models.is_library` (bool). Admin bulk import
`POST /admin/content-library/three-d/import` (multipart `files[]`, magic-byte
`glTF` + 50MB cap per file, whole batch validated before any write, stored
under `backend/three_d/{admin_id}/`). `GET /api/v1/three-d/models` now
returns `{models: own, library: shared}`; the instructor picker shows a
"Shared library" section. Resolver rule: attach allowed if owner, admin, or
`is_library` (still MP/UP courses only). `PATCH /three-d/{id}` toggles
sharing; `DELETE` is 409 while attached.

## 3. Prebuilt games

`POST /admin/content-library/games/import` takes `{games:[{title, template,
config}]}`; every config goes through the same `validate_game_config` as the
instructor builder (all-or-nothing). Games are created admin-owned,
`published` + `is_listed=True`, so they appear in every instructor's
marketplace section (`GET /games/marketplace`) and attach cross-owner via
the existing listed-game rule. `POST …/games/import-defaults` loads
`backend/seed_packs/prebuilt_games.json` (7 science games) idempotently by
(admin, title, template).

## 4. Frontend

* `src/api/labs.ts` — types + client (labs, results, admin libraries).
* `src/components/labs/VirtualLabPlayer.tsx` — fetches the entry and routes
  iframe vs `NativeLabPlayer`; `VirtualLabEmbed` is a back-compat wrapper.
* `src/components/labs/native/{ReactionLab,IdentifyLab}.tsx` + `chemistry.ts`.
* `src/components/labs/VirtualLabPicker.tsx` — catalog with subject chips,
  search, provider badges, previewOnly preview.
* `src/pages/admin/content-libraries.tsx` — `/admin/content-libraries`
  (nav: "Content Libraries"); tabs Labs / 3D Assets / Prebuilt Games.
* Lesson player branch (`lesson-redesigned.tsx`) passes `onLessonComplete`
  so a native lab with score>0 marks the lesson complete like a game.

Security: all config strings render as React text (no
`dangerouslySetInnerHTML`); iframes only for admin-allowlisted providers;
admin routes behind `require_admin`; 403 for instructors (tested).

## 5. Migration / ops

* Alembic `0007_content_libraries` (down_revision `0006c`, guarded) — run
  `alembic upgrade head`. Postgres parity SQL:
  `backend/migrations/content_libraries_2026_09_05.sql`; `ensure_schema()`
  adds `three_d_models.is_library` as a drift guard.
* Dev SQLite (`backend/visual_qa.db`) already migrated; demo course 5 has
  lessons 20 (cell lab) and 21 (reaction lab) attached; the shipped game pack
  is loaded.
* PhET `photosynthesis` was removed from the built-ins (no such HTML5 sim —
  the URL 404s). No lesson referenced it.

## 6. Tests

`backend/tests/test_content_libraries.py` (7): catalog merge + native
detail, built-in configs pass their own validator, balance/lowest-terms
rejection, admin CRUD/import/attach/unpublish/delete-409 + 403 for
instructors, native results cap + XP, game pack import → marketplace →
cross-owner attach, 3D library import (all-or-nothing) → cross-owner attach
→ unshare 403 → delete rules.

## 7. Pre-existing bugs fixed while verifying (both blocked every non-video content type)

* **Student player** (`pages/lesson-redesigned.tsx`): both lesson-object
  mappings copied H5P/game ids but never `virtual_lab_sim`,
  `three_d_model_id`, `geogebra_applet_id`, so lab / 3D / GeoGebra lessons
  rendered "No Video Available". Now copied at both sites.
* **Course editor** (`pages/instructor/edit-course.tsx`): the loader mapped
  `lesson_content_type` only for h5p/game and never loaded the lab/3D/
  GeoGebra handles, so such lessons opened as plain Text lectures with no
  picker. Now every interactive type loads as a video-container lecture with
  its handle, and the picker shows "Attached: …".
