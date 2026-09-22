# Learning Experience Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.
> Dispatches point implementers at THIS file's task section + the spec
> (docs/superpowers/specs/2026-09-02-learning-experience-design.md) — the spec's lettered
> sections are the requirements; task sections below add file maps and sequencing. Both BINDING.

**Goal:** Assessment hardening + manual grading/gradebook, H5P interactive lessons, unified
instructor certificate designer with 5 new end-to-end templates, and an event-sourced
gamification system — on branch `learning-experience` (worktree .worktrees/learning-experience,
off revenue-platform @ 24d7737).

**Tech stack:** existing (FastAPI/SQLAlchemy/React/Vite/TS/Tailwind). New deps: `h5p-standalone`
(frontend), `qrcode[pil]` (backend). Nothing else without ledger note.

## Global Constraints
- Spec section "Cross-cutting" verbatim: Integer PKs, response_model style, AuthService guards,
  tz-aware datetimes, MockRedis fallback, additive-only, no legacy-stack edits, no secrets.
- Shared venv python: `C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe`, run pytest from the worktree's backend/.
- Task 1 re-baselines the backend suite (bcrypt was fixed to 4.0.1 locally — old 45F baseline
  is stale) and records the new baseline in the ledger; every later task = zero NEW failures.
- Frontend: `npx vitest run` green; `npm run type-check` zero new vs 391. Run `npm install`
  once in the worktree frontend (node_modules absent) — --legacy-peer-deps.
- Alembic: single new revision `0003_learning_experience` grows across Tasks 1/4/9 (each task
  ADDS its tables/columns to the same revision file — it is unreleased until merge; guard every
  create with has_table/has_column/has_index checks like 0002).
- Award-hook calls (Task 9 wires them) must be try/except best-effort in host endpoints.

---

### Task 1: Assessment integrity backend (spec A1 items 1-11 backend side)
**Files:** Modify app/routers/quizzes.py, app/routers/assignments.py, app/routers/uploads.py,
app/models/quiz.py (attempt_status values doc), app/models/assignment.py (+late_policy,
late_penalty_pct, is_late, rubric, rubric_scores columns), backend/alembic/versions/0003 (new),
app/schemas (quiz/assignment schemas). Test: tests/test_assessment_integrity.py (new).
Covers: essay→pending_review flow + instructor grade/finalize endpoints; answer-leak fix;
server timer (+90s grace, pause extension); resume-existing-attempt on start; deadline
enforcement w/ late_policy allow|block|penalty; enrollment check on submit; status lifecycle
(create/update accept status, student list/submit filter published); per-assignment file
validation (`/uploads/assignment-file`); unique (assignment_id,user_id) constraint; pause
blocks answer writes. Rubric fields land here (model+schemas), grading math in Task 2.
TDD; commit `feat(assess): integrity hardening — grading states, timers, deadlines, guards`.

### Task 2: Manual grading, rubrics, gradebook backend (spec A1.12 + A2)
**Files:** Modify quizzes.py/assignments.py (or new app/routers/gradebook.py mounted /api/v1),
app/services/gradebook_service.py (new). Test: tests/test_gradebook.py.
Covers: pending-review queue endpoint (course-scoped: ungraded essay answers + ungraded
submissions, one merged list); rubric-scored grading (per-criterion scores → grade, penalty
application for late `penalty` policy); gradebook matrix endpoint (students × items, scores/
pending/late) + CSV export (csv module, attendance-CSV pattern); guards: course owner/admin.
Commit `feat(assess): manual grading queue, rubrics, gradebook + CSV`.

### Task 3: Assessment frontend
**Files:** Create pages/instructor/gradebook.tsx, pages/instructor/grading-queue.tsx,
components/assess/RubricEditor.tsx + RubricScorer.tsx; Modify assignment-builder.tsx (status,
late policy, rubric editor), assignment-grading.tsx (rubric scoring, late badge), quiz
builder (passing/attempts already exist — expose essay type properly), quiz-taking.tsx
(server-deadline sync: read attempt deadline from start response, pending_review result state),
lesson-redesigned.tsx quiz/assignment renderers if they surface results, App.tsx (routes:
gradebook, grading-queue; REPOINT /courses/:courseId/quizzes/:quizId to the working taking
page and DELETE api/quiz.ts, store/quiz.ts, pages/quiz.tsx after grepping imports), instructor
nav (Gradebook entry). Test: vitest for joinless pure helpers (late-label, rubric sum) +
RubricEditor component test.
Commit `feat(assess): gradebook, grading queue, rubric UI, dead quiz path removed`.

### Task 4: H5P backend (spec B items 4,5,8)
**Files:** Create app/models/h5p.py, app/services/h5p_service.py (zip validation/extraction
per spec B4 — traversal/size/count/extension checks), app/routers/h5p.py (/api/v1/h5p);
Modify app/models/course.py (Lesson +lesson_content_type, +h5p_content_id), chunked_upload.py
(+h5p type 100MB), alembic 0003, courses router lesson create/update schemas to accept the two
new fields, main.py mount. Test: tests/test_h5p.py (malicious zips: traversal, oversize,
disallowed ext, missing h5p.json; happy extraction; result upsert + enrollment guard; delete
blocked while referenced).
Commit `feat(h5p): content model, hardened package pipeline, results API`.

### Task 5: H5P frontend player + instructor UI (spec B items 2,3,6,7)
**Files:** Create frontend/public/h5p-player.html (static player page: boots h5p-standalone
from vendored assets against /uploads/h5p/{id}/, posts xAPI results via postMessage),
components/h5p/H5PLesson.tsx (sandboxed iframe sandbox="allow-scripts" ONLY, origin+source
verified message handler, result POST + lesson-complete call per spec B6), instructor H5P
picker/upload in edit-course lesson editor (content-type select). npm i h5p-standalone; copy
its dist into public/h5p/ (document exact files). Modify lesson-redesigned.tsx branch.
Test: vitest for the message-handler hook (origin rejection, result mapping) + H5PLesson
render; type-check clean.
Commit `feat(h5p): sandboxed player, lesson integration, instructor upload`.

### Task 6: Certificate engine unification (spec C items 1,2,6 backend)
**Files:** Create app/services/certificate_html_renderer.py (elements_config → HTML doc:
curated 12-font Google Fonts links, positioned divs, rotation, shapes, QR via `qrcode` lib
data-URI, sample-vs-real value substitution); Modify certificate_service.py (issuance/
resolve path prefers elements_config rows; Chrome render consumes generated HTML via temp
file or data URL — study how _render_html_pdf_via_chrome loads the verify page and add a
direct-HTML variant; ReportLab preview stays fallback), routers/certificates.py + admin.py
(preview endpoints use new renderer; /templates/list includes ready builder templates with
thumbnails), requirements (+qrcode[pil]). Instructor scoping: template CRUD for instructors
(own rows) — new endpoints /api/v1/certificates/designer/* (list/create/update/delete/preview,
require_instructor, post_author scoping, admin sees all, is_global flag column via 0003).
Test: tests/test_certificate_designer.py (HTML generation snapshot-ish assertions: tokens
substituted, QR present, fonts linked; scoping matrix; legacy slug path untouched).
Commit `feat(certs): unified elements_config renderer, QR, instructor designer API`.

### Task 7: Certificate designer frontend (spec C item 4)
**Files:** Move/extend components/admin/certificate-templates/template-builder.tsx →
components/certificates/designer/ (DesignerCanvas, ElementProperties, LayersPanel,
FontPicker, TemplateGallery); Create pages/instructor/certificate-designer.tsx; Modify
admin certificates page to use the shared designer; edit-course template picker consumes
merged list. Features per spec C4: resize handles, rotate, snap guides, z-order, zoom,
undo/redo (50), curated fonts w/ live load, QR/shape/signature elements, orientation presets,
live server preview, localStorage draft autosave. Instructor nav entry "Certificates".
Test: vitest — undo/redo reducer, snap math, element serialization round-trip.
Commit `feat(certs): full designer UI for instructors + admin`.

### Task 8: Certificate seed templates (spec C item 5)
**Files:** Create backend/seed_designer_templates.py (5 elements_config designs: Ivory
Classic, Midnight Gold, Tamil Heritage, Gradient Modern, Minimal Mono — REAL art direction:
composed layouts, curated font pairs, correct print-safe margins, QR placed deliberately;
idempotent by name), thumbnails via render pipeline when Chrome present else script no-ops
with note; docs snippet. The implementer must render/preview-check each template's generated
HTML for overlap/contrast (assert element bounds don't collide in tests).
Test: tests/test_seed_templates.py (5 rows, valid element schemas, bounds sanity).
Commit `feat(certs): five production seed templates`.

### Task 9: Gamification backend (spec D items 1-5,7)
**Files:** Create app/models/gamification.py (xp_events unique event_key, user_game_stats,
badges, user_badges), app/services/gamification_service.py (award(), touch_streak(), level
math, badge rules, leaderboard queries w/ Redis 300s cache + MockRedis direct fallback),
app/routers/gamification.py (/api/v1/gamification: me, me/unseen+mark-seen, leaderboard,
settings); Modify trigger points with try/except best-effort calls: courses.py lesson-complete,
quizzes.py submit/finalize, assignments.py submit+grade, course_service completion,
live_class_service.finalize_attendance (present only), h5p result endpoint; dashboard.py +
superadmin.py read streaks from user_game_stats (fallback to old calc when row absent);
alembic 0003; seed_badges in service init or seed script. Test: tests/test_gamification.py
(idempotent award, level thresholds, streak advance incl. gap reset, badge rules matrix,
leaderboard visibility toggle, best-effort isolation: award raising never fails host call).
Commit `feat(game): event-sourced XP, badges, streaks, leaderboard`.

### Task 10: Gamification frontend + docs closeout
**Files:** Create components/gamification/{XPLevelCard,StreakCard,BadgeGrid,LeaderboardTable,
AwardToaster}.tsx, pages/leaderboard.tsx, profile badges section; Modify dashboard.tsx
(XP card + real streak card + badges strip — delete the stub components/streak/streak-card.tsx),
dashboard nav (+Leaderboard), profile page (visibility toggle), unseen-awards poll on
dashboard mount wiring into showAchievementNotification/confetti. Docs: docs/
LEARNING_EXPERIENCE.md (architecture, H5P security model + authoring workflow for the owner,
designer guide, gamification rules table, deploy notes: `pip install qrcode[pil]`, npm build,
alembic upgrade) + CLAUDE.md note. Test: vitest — level-ring math, leaderboard render,
unseen-poll hook.
Commit `feat(game): dashboard widgets, leaderboard page + LEARNING_EXPERIENCE docs`.

---
Then: final whole-branch review (most capable model) → one fix wave → scoped re-review →
full suites → merge decision per finishing-a-development-branch.
