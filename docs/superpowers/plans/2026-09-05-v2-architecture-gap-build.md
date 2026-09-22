# v2.0 Architecture — gap analysis and build plan (2026-09-05)

Source: `Sasha_LMS_Architecture_v2.pdf` (14 pages). Owner instruction: build
everything in it. This file is the ledger: what already exists, what is being
built (in order), and what cannot be built without something only the owner
can supply. Each work package (WP) ships backend + tests + frontend + live
verification before the next starts.

> **Superseded WhatsApp design (10 September 2026):** WhatsApp now uses Meta Cloud API with one account-level consent record. Institution campaigns and platform campaigns from the global Communications Center reuse that consent. See `docs/WHATSAPP_CLOUD_SETUP.md`; the MSG91 guardian-digest references below describe the historical plan only.

## A. Already built before this plan (verify, don't rebuild)

| v2 section | Status |
|---|---|
| §1–2 three types, escape hatch, `type_profiles` as data, capability matrix | built (`core/course_types.py`, `type_profiles`, `enabled_tools`) |
| §3 free-text tags, no taxonomy | built (`course_tags` + relation) — clustering NOT built |
| §4 draft-first studio | built (start form → tabbed editor); type-specific opening states NOT |
| §5 quiz as container (H5P + games as modules), cumulative grade w/ type weights | built; universal item fields, practice flag, tierFloor, 3D/live buckets NOT |
| §6 3D match-and-verify | NOT built (roadmap item 2) |
| §7 live class lifecycle, recordings → library, soft delete, past-class report v1 | built; classification axes, retention mechanics, permanent class_reports NOT |
| §8 virtual labs | catalog + 2 native engines built (2026-09-05); simulation presets/probes + concept propagation NOT |
| §9 Engine A v1 (text), C tutor, D exam generator (drafts = review queue), item statistics | built (503 without `GLM_API_KEY`); Engine B, escalation, learner error reports, personalisation NOT |
| §9.5 mastery | per-course 0.6/0.4 score only; learner-scoped concept graph NOT |
| §10.6 guardian layer, §10.7 marketplace (games), gamification | built (WhatsApp 503 without `MSG91_API_KEY`) |
| §12 data model | `courses.type`, `type_profiles`, `games`, `ai_jobs`, banks built; `tag_clusters`, `scorable_items`, `three_d_tasks`, `simulations`, `learner_mastery_graph`, `class_reports`, live axes NOT |

## B. Work packages, in build order

**WP1 — Scorable item contract (§5, §12 `scorable_items`).** Every quiz
module carries the four universal fields (max_score derived, weight,
attempts_allowed, practice_only) plus grading_mode and tier_floor; kinds grow
to h5p | game | lab | three_d_task | geogebra. Publishing a graded quiz with an
item whose tier_floor > T4 is blocked (422) — the "honest for the market"
rule. Cumulative grade honours per-item weights and skips practice items;
`three_d_tasks` and `live_participation` weight buckets become real
(attendance ratio). Quiz builder: Add item → Question | Game | H5P | Lab | 3D
Task | GeoGebra, each with the universal fields.

**WP2 — 3D match-and-verify assessment (§6).** `three_d_tasks` (model_id,
task_type ∈ match|identify|verify|assemble|measure|manipulate|sequence,
parameter-based config, concepts, tier_floor) + `three_d_task_attempts` with
an evidence trail (views, resets, parameter explorations, hesitation) and a
computed confidence signal ("clean" vs "trial and error"). Player over
`ThreeDViewer` with 3D anchors, plus the T4 interface (static render +
selection/numeric entry) earning identical marks. Instructor builder page;
insertable in quizzes via WP1.

**WP3 — Learner mastery graph + concept propagation (§8.3, §9.5, §10.1).**
Learner-scoped `concepts`, `concept_prerequisites`, `mastery_evidence`,
`learner_mastery`. Every scorable thing declares concepts; evidence weights by
source (supervised > practice, clean 3D path > fumbling). Propagates into the
curriculum coverage view, the learner progress map, at-risk, Engine D
weak-concept weighting and tutor context. UP "Outcome definition" +
assessment-first coverage-gap report (§4.3).

**WP4 — Emergent taxonomy (§3).** `tag_clusters` built from normalisation +
string similarity + co-occurrence (embeddings optional when a key exists);
query expansion in course search; suggested tags on save; aliasing; type as an
implicit catalogue filter; optional admin display label.

**WP5 — Live class classification + retention (§7).** purpose/mode/audience/
recording policy columns; `retention_until` (owner default 1 year, per-course
override ≤ tenant ceiling); 30-day soft-delete grace with restore; deletion
audit log (actor, reason, timestamp); 14/3-day expiry warnings with one-click
extend; "download all first" manifest; permanent `class_reports` generated at
ENDED (attendance join/leave/duration, chat/poll log, engagement, notes,
transcript + AI topics when present), PDF export, guardian share for SP.

**WP6 — Studio faces (§4).** Type-specific opening state after draft creation
(MP → asset library, SP → schedule, UP → outcome); Tier Preview toggle for 3D
lessons; Parent View Configurator; Reward System Designer (per-course points /
badge criteria / streak freeze / leaderboard opt-out consumed by `award()`);
Schedule Builder (term view over live schedules + lessons).

**WP7 — AI layer completion (§9).** Engine B depth-adaptive lesson
(recover/consolidate/extend, scoped to course, mastery-aware); Engine C
escalation-to-instructor with context, mastery-calibrated check questions,
graded-item answer guard; Engine D review-queue UI, learner-reported errors →
instructor inbox, auto-flag by item statistics, weak-concept personalisation;
Engine A transcript ingest hook → segmentation → concepts → artefacts that
survive recording deletion. All 503 honestly without `GLM_API_KEY`.

**WP8 — Flywheel + world-class extras (§10).** Class ENDED → report →
curated lesson → practice bank → mastery → "next class agenda" proposal;
pedagogical insight cards (3D evidence × question outcomes); cross-type
composition by reference; peer "teach it back" v1; DigiLocker/APAAR adapter
(503 without credentials); low-bandwidth toggle in JitsiStage; 3D keyboard
controls + text equivalents.

**WP9 — Quality disciplines (§11).** GLB budget check on import (triangles,
texture bytes per tier → warn/reject); derived-over-stored enforced by WP5;
progressive loading of 3D/labs.

## C. Cannot be built here — owner-owned inputs

| Item | Needs |
|---|---|
| Blender optimisation pipeline (LOD/KTX2/Draco/USDZ), FBX/OBJ/USDZ conversion | Blender + toolchain on a build host |
| XR headset sessions | a headset to test; an "Enter VR" WebXR button ships unverified |
| GPU particle simulations | separate sub-project (sasha-particle-sim skill); native lab presets stand in |
| Transcription (Engine A full) | Whisper/Bhashini decision + key |
| Live AI verification (all engines) | `GLM_API_KEY` |
| WhatsApp guardian digests | `MSG91_API_KEY` |
| DigiLocker / APAAR issuance | government API credentials |
| Offline on-device tutor | mobile model packaging (Flutter) |
| Multi-tenant `tenant_id` | single-tenant repo by design (sasha-tenancy-rls) |

## D. Ledger (filled in as WPs land)

- WP1 (done 2026-09-05): `app/schemas/scorable.py` (contract + normalisation +
  `assert_publishable` tier rule + `best_item_score`), quiz create/update wired,
  `GET /api/v1/scorable-items` derived registry (`routers/scorable_items.py`),
  cumulative grade rewritten (per-item weights, practice excluded, buckets
  games_h5p / three_d_tasks, live participation = present ratio of ENDED
  classes, weights from type_profiles with §5.3 fallbacks; also fixed a latent
  `H5PResult.h5p_content_id` AttributeError). Frontend: `api/scorable.ts`,
  `components/assessment/ScorableItemsEditor.tsx` (quiz builder "Add item"
  palette + universal fields + T4 warning), `ScorableItemsPanel.tsx` (students
  play items inline on the quiz page), My Grades shows the two new buckets.
  Tests `tests/test_scorable_items.py` (7). Verified live: legacy quiz 1
  normalised, lab item added via palette, PUT 200, student panel renders.
- WP2 (done 2026-09-05): `models/three_d_task.py` (ThreeDTask, ThreeDTaskAttempt),
  `schemas/three_d_task_config.py` (seven strict per-type schemas, anchors as
  normalised bbox coords with neutral "Region N" names, server-side
  `grade_task` on state/parameters, `validate_evidence`, `confidence_signal`),
  `routers/three_d_tasks.py` (/api/v1/three-d-tasks: CRUD, publish, play,
  attempts with evidence → confidence, XP best-effort, owner preview never
  stored; palette/quiz hooks for WP1), Alembic `0008_three_d_tasks` + SQL
  parity. Frontend: `ThreeDViewer` gained anchors/markers, surface picking
  (`onPickPoint`), evidence hooks; `components/three-d/tasks/ThreeDTaskPlayer.tsx`
  (all 7 types, T1 3D view ⇄ T4 list view, same marks);
  `pages/instructor/three-d-tasks.tsx` (builder + annotation placer + attempts
  with confidence); nav "3D Tasks"; quiz panel plays `three_d_task` items.
  Tests `tests/test_three_d_tasks.py` (5). Verified live: built "Duck
  anatomy" identify task on model 3 via the placer (2 anchors, 1 prompt),
  published, inserted into quiz 1.
- WP3 (done 2026-09-05): `models/mastery.py` (concept_links, concept_prerequisites,
  mastery_evidence, learner_mastery, course_outcomes — LEARNER-scoped),
  `services/mastery_service.py` (links, evidence → recency-weighted estimate +
  confidence, §9.5 source weights with 3D path multiplier, learner graph with
  recover-first gaps, weak concepts, course coverage/gap report, progress map),
  `routers/mastery.py` (/api/v1/mastery). Hooks (best-effort, post-commit) in
  quiz submit + finalize, games, native labs, H5P, 3D tasks (path-weighted),
  assignment grading; 3D task concepts mirrored into links; built-in labs
  declare concepts; at-risk gained the weak-concepts rule; Engine D accepts
  `student_id` and weights weak concepts into the prompt. Alembic 0009 + SQL
  parity. Frontend: `api/mastery.ts`, `/my-mastery` (student graph, evidence
  drawer, recover-first, progress map), `/instructor/courses/:id/coverage`
  (outcome definition, gap report, per-element concept tagging,
  prerequisites) + "Coverage" button in the editor. Tests `tests/test_mastery.py`
  (6). Verified live: lab result → 3 concepts at 70% on My Mastery; coverage
  page saved outcome + quiz tags and reported 9 concepts / 4 gaps.
- WP4 (done 2026-09-05): `models/tag_cluster.py` + Alembic 0010, `services/tag_service.py`
  (normalisation, trigram similarity, distinctive-token prefix rule, co-occurrence,
  union-find clusters rebuilt lazily every 10 min or on demand; query expansion;
  aliases; suggestions from the course's own text), `routers/tag_taxonomy.py`
  (/api/v1/tag-taxonomy — the legacy /api/v1/tags listing was preserved after an
  accidental overwrite was restored from the sibling checkout). Course search
  expands across clusters (title/body/tags). Frontend: `TagsEditor` (chips +
  suggested-on-save) in the course editor, catalogue "Type" filter
  (course_type param), `TagClustersPanel` on Admin → Tags with labels + rebuild.
  Tests `tests/test_tag_taxonomy.py` (4).
- WP5 (done 2026-09-05): LiveClass gained purpose/mode/audience/recording_policy
  + retention_until + recording_deleted_at/by/reason (Alembic 0011, settings
  schema validates the enums, create endpoint stores them, `lifecycle` in every
  LiveClassOut). `models/live_class_report.py` (ClassReport permanent record,
  RecordingAudit), `services/class_report_service.py` (report generation at
  end_class in the same transaction, retention clock = ended_at + retention_days
  ≤ RECORDING_RETENTION_MAX_DAYS (365), soft delete with 30-day restore, extend
  within the ceiling, expiry warnings 14/3 days (most urgent first, idempotent
  via events, email best-effort), sweeper purge wired into the reminders loop,
  PDF export, course recording manifest). Recordings router: DELETE is now
  soft, + restore / extend / expiring / manifest / audit (admin) / report /
  notes / share-guardians / report.pdf; playback refuses soft-deleted media;
  past-classes rows carry lifecycle, days_left, has_report. Frontend: schedule
  form classification selects + retention days, Past classes "Report" modal
  (`components/live/ClassReportModal.tsx`) with extend/delete/restore, PDF,
  notes, guardian share. Tests `tests/test_live_retention.py` (5).
- WP6 (done 2026-09-05): `models/course_settings.py` (CourseStudioSettings:
  parent_view JSON, rewards JSON, face_dismissed; Alembic 0012 + SQL parity +
  ensure_schema; `user_game_stats` gained streak_freeze_month/streak_freezes_used).
  `services/studio_service.py`: defaults_for_type (opening face MP→asset_library,
  SP→schedule, UP→outcome; SP parent view = attendance + completion only),
  validated put_settings (unknown activity/rule/key → 422), points_override
  (award() honours it whenever course_id is known — wins over trigger-site
  values), evaluate_course_badges (custom badges as idempotent `course_badge`
  XpEvents after every award), streak_freeze_allowance (max across enrolled
  courses; touch_streak spends freezes for missed days, month-scoped),
  leaderboard_opted_out (course scope returns entries=[] + opted_out),
  parent_view (parents digest now emits only the ticked signals: progress,
  attendance summary, recent scores + risk, shared class reports),
  term_schedule + clone_week (same weekday/time, fresh room, SCHEDULED).
  Router `/api/v1/studio` (settings GET/PUT, schedule, schedule/clone-week,
  rewards/me, parent-view). Frontend: `components/studio/{StudioFace,
  TierPreview, ScheduleBuilder, GuardianVisibility, RewardDesigner}.tsx`,
  `api/studio.ts`; editor opens on `?tab=curriculum&face=1` after the start
  form; StudioFace at the top of Curriculum (dismiss persists, chip reopens);
  TierPreview under every attached 3D model (T1 interactive / T3 turntable /
  T4 still + text equivalent, fps/triangle/draw-call meter, GLB budget line —
  ThreeDViewer gained autoRotate/interactive/onStats/captureRef); Settings tab
  gained Guardian visibility + Reward system blocks; live-class form accepts
  `?course_id=`. Tests `tests/test_studio.py` (6). Also fixed: Alembic 0011/
  0012 downgrades reflect without FKs (`reflect_kwargs={"resolve_fks": False}`)
  so `test_live_class_migration` passes on an Alembic-only DB.
- WP7 (done 2026-09-05): `models/ai_layer.py` (TutorEscalation, ContentErrorReport;
  Alembic 0013 + SQL parity), `services/ai_layer_service.py`, router
  `routers/ai_engines.py` at `/api/v1/ai`. Engine C: `graded_item_guard` runs
  in `tutor_chat` BEFORE any LLM call (fuzzy match against the course's quiz
  question titles → refuses, audited as a `guard` AiJob, works without a key);
  `POST /tutor/check-question` mastery-calibrated (easy/medium/hard from the
  learner's estimate); `POST /tutor/escalate` hands the learner to the course
  owner WITH the last 8 turns + weak concepts, in-app notification both ways,
  `GET /tutor/escalations` (learner sees own, instructor sees theirs),
  `/reply`. Engine B: `POST /adaptive-lesson/{course}` recover|consolidate|
  extend (auto from mastery estimate: <0.4 recover, <0.75 consolidate, else
  extend), owner may target a learner, draft only — never a curriculum row.
  Engine D: `GET /review-queue` = ai-draft bank questions (approve → tag
  `reviewed`, reject → delete, 409 for human questions) + auto-flagged quiz
  items DERIVED from live answer stats (`flag_reasons`: facility <0.2 / >0.95
  at ≥10 attempts, discrimination <0.1 / negative at ≥6 — explainable strings)
  + open error reports + open escalations; learner `POST /error-reports`
  (quiz_question|lesson|bank_question|other) → instructor notification →
  `/resolve` (resolved|dismissed + note) → learner notification. Engine A:
  `POST /api/v1/internal/live/transcripts` (X-Internal-Token) and owner
  `POST /live/classes/{id}/report/transcript` both call
  `process_transcript`: transcript stored on the permanent ClassReport
  (`processing_status=transcribed`), and only when GLM is configured
  segmented into `ai_topics` [{topic, summary, concepts, start_hint}]
  (`processed`) with concepts propagated as `live_class` teaching links in the
  mastery graph (new LINK/TEACHING kind). Frontend: `api/aiLayer.ts`,
  `pages/instructor/review-queue.tsx` (`/instructor/review-queue`, nav
  "Review Queue", four lanes), TutorDrawer gained "Ask my instructor" /
  "Check my understanding" / "Report an error", `components/ai/
  AdaptiveLessonPanel.tsx` on My Mastery, ClassReportModal "Paste transcript"
  + processing badge. All LLM paths verified as honest 503 in the browser
  without `GLM_API_KEY`; tests `tests/test_ai_layer.py` (6) cover the LLM
  paths with a fake provider.
- WP8 (done 2026-09-05): `services/flywheel_service.py` + `routers/flywheel.py`
  (`/api/v1/flywheel`) + `models/flywheel.py` (TeachBack, TeachBackRating; Alembic
  0014 + SQL parity). Next-class agenda `GET /courses/{id}/next-agenda` is
  DERIVED with no LLM: last ended class's report (ai_topics or notes → recap),
  class-wide weak concepts aggregated from the learner mastery graph (<50%
  among enrolled learners → re-teach items), absentees from the report's
  attendance (catch-up), open tutor escalations (questions) and open error
  reports (fix); `?polish=true` adds an audited GLM prose draft only when
  configured. Insight cards `GET /courses/{id}/insight-cards`: for every 3D
  task attached to the course's quizzes, share of clean / mixed /
  trial-and-error paths × avg task score × avg quiz/assignment score of the
  same learners on the task's concepts (MasteryEvidence), with explainable
  insights (≥40% trial-and-error, clean solvers ≥15 pts better in quizzes,
  trial-and-error still full marks, ≥70% clean). Teach-it-back v1: `POST/GET
  /teach-back`, `/rate` (one changeable vote per peer, no self-votes), `/hide`
  (owner/admin); writing awards +15 XP (`teach_back_written`, first per
  concept) and records a weak mastery signal (`teach_back` link kind, source
  weight 0.3, score 70); 3 and 10 helpful votes award +5/+10. DigiLocker/APAAR:
  `GET /digilocker/status`, `POST /certificates/{issued_id}/digilocker` —
  honest 503 without `DIGILOCKER_CLIENT_ID`/`_SECRET`; with them it returns the
  prepared issuer document descriptor (the NeGD push itself is owner-verified
  on their sandbox). Cross-type composition by reference: already satisfied by
  the shared 3D library, the games marketplace and the scorable-item registry
  (any published item attaches to any quiz by id) — no new mechanism. Frontend:
  Insights page tab "Next Class & 3D Insights" (`components/flywheel/
  FlywheelPanel.tsx`), `TeachBackPanel` under each expanded concept on My
  Mastery, `DigiLockerButton` on the certificate page, JitsiStage
  "Low-bandwidth mode" toggle (180p receive quality via `setVideoQuality`,
  remembered in localStorage), ThreeDViewer keyboard controls (arrows orbit,
  +/− zoom, R reset; `tabIndex=0`, aria-label states the keys) and a visible
  "Text equivalent" toggle. Tests `tests/test_flywheel.py` (6, shared with WP9).
- WP9 (done 2026-09-05): `services/glb_budget.py` parses the GLB container
  (JSON chunk only, no 3D library): triangles from indexed / non-indexed
  TRIANGLES primitives, texture bytes from image bufferViews, Draco/KTX2
  flags; per-tier soft caps T1 500k/24MB, T2 150k/8MB, T3 50k/4MB → warnings
  + `lowest_full_tier`; hard caps 1.5M triangles / 64MB textures → 422 on
  instructor upload (`POST /three-d/models`) and admin library import
  (all-or-nothing, before any file is stored). Both responses now carry
  `budget`. A GLB whose JSON chunk cannot be parsed is NOT rejected — the
  report says `parse_error` and the file passes (our parser must never block
  what three.js can load). Progressive loading: ThreeDViewer shows GLTFLoader progress
  ("Loading 3D model… 42%"); native lab engines + SVG diagrams are a lazy
  chunk (`React.lazy` in VirtualLabPlayer with a Suspense fallback).
  Derived-over-stored: WP5 lifecycle, WP1 registry, WP4 clusters, WP7 item
  flags, WP8 agenda/cards are all computed at read time — nothing new stored.
  Also fixed while verifying: `/question-banks` was missing from axios
  `noSlashEndpoints` (Insights → Item Analysis 404'd since the SILEOS pack).

## E. Owner requests after the gap build — 2026-09-05 evening

- **Public lesson preview + real lock (done).** Any lesson — video, text, 3D,
  lab, game, H5P — can be switched to "Public preview" per row in the editor
  (`lesson_preview`; the toggle was there but named "Free Preview/Paid" and
  only played videos). `course_service.format_course_response(full_access=)`
  now STRIPS media/content/handles from every non-preview lesson for visitors
  and non-enrolled learners (`is_locked: true`; owner/admin/enrolled keep
  everything) — before this the lock was UI-only and every video URL was in the
  public payload. New `GET /courses/{id}/lessons/{lid}/preview` (optional auth)
  returns the full lesson only for preview lessons / enrolled / owner / admin.
  Asset endpoints (`/three-d/models/{id}/file`, `/virtual-labs/{slug}`,
  `/games/{id}/play`) take an optional user and, when anonymous, consult
  `services/public_preview.allows_anonymous` (a public-preview lesson in a
  published course must embed that asset). Frontend: `components/course/
  LessonPreviewModal.tsx` (dark glass popup, plays the REAL lesson by type, enrol
  CTA), course page curriculum rows (glass "Free preview" chip / "Locked" chip,
  orange hero), editor badge/toggle now reads "Public preview / Locked" with a
  hint under the curriculum header. Tests `tests/test_lesson_preview.py` (5).
  `conftest.as_user` also overrides `get_optional_current_user`.
- **UI system (done, first pass).** `styles/globals.css` tokens: `.si-gradient`,
  `.si-hero`, `.glass-panel`, `.glass-panel-dark`, `.glass-chip`,
  `.si-glass-halo`, `.si-btn-{primary,secondary,danger,ghost}`, `.si-input`.
  One popup primitive `components/ui/dialog.tsx` (GlassDialog on Radix, light/
  dark tone, sizes, action row) and `components/ui/confirm.tsx` (`useConfirm`
  + `confirm.prompt` replacing window.confirm/prompt; `ConfirmProvider` mounted
  in App). Applied to: lesson preview popup, recording delete prompt, dashboard
  sidebar/navbar + public header (frosted glass over the orange hero), course
  preview card, teaching kit / check-yourself panels. Second pass (same evening):
  ALL 63 `window.confirm` / `confirm` / `window.prompt` call sites in 35 files now
  go through `confirmDialog` / `promptDialog` (module-level API registered by
  `ConfirmProvider`; danger wording auto-detected; legacy messages split into
  title + body) — zero browser prompts remain; the shared `Card` primitive is
  frosted glass (so every dashboard/editor/admin card follows), course-catalogue
  cards, auth layout, checkout and catalogue backgrounds use the orange hero,
  toasts are frosted with an orange accent. Verified: glass confirm on 3D tasks
  delete (cancel keeps the task), instructor My Courses, login page.
- **3D teach-and-examine (done).** `components/three-d/ThreeDTeachingKit.tsx`
  under every 3D lesson in the editor (4-step loop with a prefilled builder
  deep-link `?model_id=&title=`), `ThreeDCheckYourself.tsx` under every 3D
  lesson in the player (published tasks on the model, inline play), backend
  `GET /three-d-tasks/for-model/{id}`. Guide: `docs/3D_TEACHING.md`.

## F. World-class roadmap loop — 2026-09-06 (R1–R10)

- **R1 Conversion funnel (done).** `models/funnel.py` (funnel_events: course_view /
  preview_open / checkout_start keyed by browser session + optional user; Alembic
  0015), `services/funnel_service.py` (summary per course with enrolments DERIVED
  from enrollments, four rates, top preview lessons; overview; continue-where-you-
  left-off from LessonProgress; abandoned-checkout pass — one in-app reminder per
  user/course after 24h, idempotent via the notification row — wired into the
  reminders loop), router `/api/v1/funnel`. Frontend: `api/funnel.ts` `track()`
  (fire-and-forget), course page tracks visits + preview opens and shows a "Try
  before you enrol" strip with the free lessons, checkout tracks starts,
  `ContinueLearning` rail on the student dashboard, Insights → "Funnel" tab.
  Tests `tests/test_funnel.py` (3).
- **R2 Review queue as the daily habit (done; live AI verification waits for the
  key).** `GET /ai/review-queue/counts` (cheap) → sidebar badge on "Review Queue"
  (`hooks/useNavBadges.ts`, refreshed every 2 min + on focus) and a "Today's
  review queue" card on the instructor dashboard. Prompts carry the course
  language (tutor: "reply in Tamil…" when `course_language` is not English;
  adaptive lesson + check question: LANGUAGE line). Tests `tests/test_review_counts.py` (2).
- **R3 WhatsApp digests — NEEDS OWNER:** `MSG91_API_KEY`. Code path exists (503 today).
- **R4 Mobile parity — NEEDS OWNER:** Flutter toolchain (`flutter pub get`, build_runner);
  the server side (public preview endpoints, tasks-for-model, low-bandwidth live) is ready.
- **R5 Visual language (partial).** Done: glass Card primitive, orange hero on auth/
  checkout/catalogue/course pages, frosted shell, glass toasts, all popups on
  GlassDialog. Not done: landing page and the lesson player keep their own themes;
  no page-transition/empty-state pass yet.
- **R6 Instructor growth tools (done).** `services/course_ops_service.py`: deep
  `clone_course` (course fields, lessons incl. interactive handles, quizzes +
  questions + answers, assignments, sections_meta id remap, studio settings →
  DRAFT owned by the caller), templates (`courses.is_template`, Alembic 0016,
  `GET /course-ops/templates`, `POST /templates/{id}/use`), CSV quiz import
  (`POST /course-ops/courses/{id}/quizzes/import-csv`, all-or-nothing with row
  errors, `/csv-help`), co-instructors (`course_collaborators`; ONE rule
  `services/course_access.can_edit()` now used by courses/quizzes/assignments/
  gradebook/studio/mastery/live_classes — 24 former owner checks — and
  my-courses lists collaborations). Frontend: Clone button on My Courses,
  "Start from a template" picker on the start form, "Import quiz CSV" in the
  curriculum header, Co-instructors block in Settings. Tests
  `tests/test_course_ops.py` (4). PDF → questions still needs `GLM_API_KEY`.
- **R7 Payments polish (done where verifiable).** Admin orders got the missing
  "Refund" action on the existing idempotent refund endpoint (glass prompt for
  the reason); coupons on memberships via a Razorpay Offer id
  (`coupons.razorpay_offer_id`, Alembic 0017, `PATCH /coupons/{id}/membership-offer`
  admin, `/memberships/subscribe` accepts `coupon_code` and passes `offer_id`;
  refuses honestly otherwise; membership page coupon box); Razorpay checkout shows
  UPI first, then EMI / pay-later, then cards; invoice PDFs carry the orange brand
  band. NEEDS OWNER to verify on a Razorpay test account: Offers must be created
  in the dashboard; EMI availability depends on the merchant account. Tests
  `tests/test_payments_polish.py` (2).
- **R8 Assessment integrity (done).** Timed windows (`quizzes.quiz_available_from/
  until`, Alembic 0018; enforced at `/quizzes/{id}/start` for learners, owner may
  test; builder "Opens at / Closes at"), proctoring-lite (`POST /quiz-attempts/{id}/
  integrity` from the taker's browser: tab_hidden / window_blur / copy / paste /
  fullscreen_exit → `attempt_info.integrity`, advisory only; instructor summary
  `GET /courses/{c}/quizzes/{q}/integrity`; Review Queue "Quiz integrity" lane),
  item retirement (`quiz_questions.is_retired`; `/ai/review-queue/items/{id}/
  retire|unretire` from the Flagged-items lane; retired questions never enter new
  attempts, history untouched). Randomisation from banks already existed
  (`quiz_questions_order=rand`). Tests `tests/test_integrity.py` (3).
- **R9 Offline / low-data (partial).** Done: Data-saver switch (localStorage
  `si.dataSaver`) — 3D lessons show the text equivalent + "Load the 3D model"
  instead of auto-downloading (`components/three-d/DeferredThreeD.tsx`).
  NEEDS OWNER: pre-generated 3D tiers (gltf-transform / Blender on a build host),
  audio-only transcodes (ffmpeg pipeline), Flutter downloads.
- **R10 Institution features (done except DigiLocker).** `GET /cohorts/spoc/cohorts/
  {id}/mastery` (SPOC, course editors, admin): class-wise concept averages, below-50
  counts, per-student average / weakest concept / at-risk flag; `GET /cohorts/admin/
  colleges/{id}/mastery` school roll-up; "Mastery" tab on the SPOC cohort page.
  Teacher accounts under a school: co-instructors (R6) + SPOC roles cover it.
  DigiLocker issuance NEEDS OWNER credentials (adapter from WP8). Tests
  `tests/test_cohort_mastery.py` (2).

## G. Round 2 — items 2, 3, 4, 5, 9 (2026-09-06)

- **Item 3 Retention loop (done).** `services/retention_service.py`: streak nudge
  (streak ≥ 2, last active yesterday, once per day), near-certificate prompt
  (progress ≥ 80%, once per course, "N lessons to go"), 7-day re-engagement
  (enrolled ≥ 7 days, no lesson touched for 7 days, once per 14 days per course),
  weekly digest (lessons / XP / streak, once per 7 days, silent when nothing
  happened). All idempotent through notification rows; runs in the reminders
  loop at most every 6 hours. Tests `tests/test_retention.py` (4).
- **Item 4 Instructor analytics (done).** `GET /funnel/instructor/earnings` (paid
  orders, gross from course line items, processed refunds, net, refund rate,
  enrolments + funnel per course; admin sees all) and `GET /funnel/instructor/
  report.pdf` (ReportLab, orange brand band). Insights → "Earnings" tab with the
  PDF button. Tests in `tests/test_round2.py`.
- **Item 5 Banks at scale (done).** `POST /question-banks/{bank}/push-to-quiz/
  {quiz}` (random draw of reviewed questions — AI drafts excluded — with an
  optional easy/medium/hard mix, SNAPSHOT copies incl. answers), `GET
  /question-banks/{id}/export.csv` (same columns the importer accepts, so banks
  round-trip), per-attempt subsets: `quiz_max_questions_for_take` now draws N
  random non-retired questions at `/start` (`attempt_info._question_ids`,
  returned as `question_ids`, resumed attempts keep theirs, grading counts only
  the subset). Builder: "Add from bank" dialog in the header, "Questions per
  attempt" in Settings; the taker filters to the drawn subset.
- **Item 9 Low-data media (done on this host; owner decides for prod).**
  `services/media_pipeline.py`: `build_glb_tiers` (gltf-transform simplify +
  webp; T2 45% / T3 15% of triangles) recorded on `three_d_models.tier_files`
  (Alembic 0019), streamed by `GET /three-d/models/{id}/file?tier=T2|T3` (falls
  back to the original, `X-Tier` header), `POST /three-d/models/{id}/build-tiers`
  (503 with the install hint when the tool is missing), `GET /three-d/tools`.
  Viewer picks T3 on data saver, T2 on ≤4 GB devices / narrow screens. Video
  uploads queue an ffmpeg AAC-64k `.m4a` sibling in a background task
  (`audio_url` + `audio_status` in the upload response); the lesson player
  shows an "Audio only" toggle when the rendition exists (auto-on with data
  saver). Both tools are present on this machine (ffmpeg global, gltf-transform
  installed via npm); verified live: duck model 120 KB → 87 KB tiers. NEEDS OWNER
  on the production host: `npm i -g @gltf-transform/cli` and ffmpeg on PATH.
- **Item 2 Visual language (done).** Page-enter transition on every workspace
  and public main (`.si-page-enter`, reduced-motion safe), glass empty states,
  landing category cards on frosted glass, lesson player sidebar as dark glass.
- **Hardening found on the way:** with Docker's Redis down every request waited
  on connect timeouts (health 7.5 s, authenticated calls > 15 s). The rate-limit
  middleware now uses 300/500 ms socket timeouts and a 30 s fail-open circuit
  breaker (`RateLimitMiddleware._redis_available`); requests are back to ~10 ms
  without Redis. Production still needs Redis for real limits.

## H. Learning-signals engine — "detect where the exact deformation happens" (2026-09-06)

Owner ask: the platform should notice *how* a learner learns (rewinding
twice or thrice, fast-forwarding, not taking notes, giving up early,
hesitating on questions) and customise the assessment to that pattern —
all inside the ecosystem, no external analytics.

**Signal capture (client → `POST /api/v1/signals/events`, batches ≤200).**
`frontend/src/api/signals.ts` buffers events and flushes every 8 s, when
the tab hides, and on `pagehide`; nothing ever blocks the UI.
- Lesson player (`pages/lesson-redesigned.tsx`): `video_rewind` (seek back
  >3 s, value = seconds jumped), `video_replay` (playing through a
  10-second segment already watched, once per rewind pass), `video_skip`
  (seek forward >10 s), `video_pause` (≥2 s of play before the pause),
  `rate_change` (speed ≠ 1), `note_written` (timestamped note),
  `quit_early` (leaving the lesson between 5% and 60% progress — route
  change or tab close).
- Quiz taking (`pages/quiz-taking.tsx`): `question_time` per question
  when the learner moves on + at submit; `answer_change` counts per
  question, sent at submit. Adaptive practice reports the same two.

**Server (`app/services/learning_signals_service.py`, router
`app/routers/learning_signals.py`, models `app/models/learning_signals.py`,
Alembic 0020 + `migrations/learning_signals_2026_09_06.sql`).**
- `LearningSignal` rows are bucketed into 10-second `segment`s; instructors
  place `LessonConceptMarker`s ("from 3:00 this lesson is about the
  limiting reagent") so a segment maps to a concept — without markers the
  lesson's own concept links apply. Adding a marker also adds the concept
  as a lesson teaching link (mastery graph coverage stays consistent).
- `lesson_heatmap()` → per-segment rewinds/replays/pauses/skips/learners/
  score + top-5 `struggle_segments` + `early_quits` (instructor: everyone;
  learner: own signals only, whatever `user_id` they pass).
- `learner_profile()` → per-concept `struggle` (0–100 normalised), `raw`,
  and a human `why` list ("rewound 3×", "re-watched N segments", "left
  early N×", "hesitated on N questions", "changed answers N×", "took N
  notes" — notes count *against* struggle), joined with mastery.
  Hesitation = ≥45 s on a question; answer churn = ≥2 changes. 60-day window.
- `build_adaptive()` → weights = struggle raw + (60 − mastery)/20; picks
  non-retired, auto-gradable questions of the course (essay / open-ended /
  file-upload / image-answering never enter a set) whose concepts match,
  difficulty pitched from mastery (easy <40, medium <75, hard), variety
  cap per type, recent-session penalty. No answer keys leave the server.
- `grade_adaptive()` grades server-side, records one mastery evidence row
  per question (`safe_record_evidence`, weight 0.8) AFTER commit, emits an
  `adaptive_result` signal, returns `by_concept`. 409 on double submit.

**UI.** Student: My Mastery → "Where you struggle" (`components/signals/
StruggleProfile.tsx`) with the why-strings and "Practice built for you"
(`AdaptivePractice.tsx`, StrictMode-guarded single build). Instructor:
course editor → every non-quiz lecture shows a Struggle map
(`LessonStruggleMap.tsx`: heat bars per 10-second segment, top segments
with concept, early-quit count, marker editor add/remove). Instructor can
also read one learner's profile via `GET /signals/students/{uid}/profile`.

**Checks.** `tests/test_learning_signals.py` (3) — ingest+heat-map+markers
(learner scoping, marker attribution), profile "why" strings + sign,
adaptive build targets the struggling concept at the right difficulty,
grades, feeds evidence, refuses double submit. Browser: student profile
on course 5 showed "rewound 3× · re-watched 1 segment · left early 1× ·
hesitated on 1 question · changed answers 1×", practice set of 6
auto-gradable items scored 5/6 by concept; instructor map showed 4 hot
segments, marker add/remove round-tripped; a real quiz attempt in the
browser produced `question_time` rows for every visited question and one
`answer_change` for the answer that was switched.

**Traps.** Lesson ids on the lesson page are `lesson-<id>` strings —
strip the prefix before sending (`signalLessonId`). The editor's lecture
ids may be `lesson-N` or bare `N`; new unsaved lectures never match and
the map hides itself on a 404. `question_time` for the *last* question is
only sent at submit. Video signals only fire when the player reports
progress — text/3D/lab lessons contribute notes, quits and quiz behaviour.


## I — Astra cycle 1: close the learning-signals loop (2026-09-06)

Implemented course hotspots with can_edit access, ten ranked segments,
early exits and per-concept learner counts; seven-day hot-segment alerts
for owners/collaborators through the existing retention loop; tutor struggle
context after the graded-item guard and missing-key check; quiz weak concepts
and normalized repeated focus parameters for adaptive practice. Only page
mount: instructor/insights.tsx (plain Hotspots table); api/signals.ts extended.
No migration required. Base verified against PR #3 head 25db528; local branch
astra/learning-signals. Final check results are recorded in
`docs/ASTRA_CYCLE_1_BUILD_REPORT.md`.

Plan corrections: tutor_chat lives in ai_tutor.py. Demo signals involve one
learner, so expecting an alert on unchanged demo data would violate the
specified three-learner threshold; alert persistence and cooldown are instead
verified in isolated seeded test databases. Transcription remains pending the
owner's provider selection. Later roadmap cycles are not claimed complete.


## J — Personal planner and intervention engine (2026-09-06)

Implemented learner goals and daily budgets, course evidence diagnosis, review and
practice tasks, three-day retention checks, and a course-scoped instructor queue
with notes/decisions/history. Includes schema revision 0021, PostgreSQL parity SQL,
quiz-submit/finalize hooks, retention-pass refresh, and local browser verification.
See `docs/LEARNING_PLANNER.md` and `docs/PLANNER_BUILD_REPORT.md` for exact rules,
checks, local migration repair, and deployment limitations. This is a separately
requested learning-OS enhancement; it does not mark the original transcription
and other Astra roadmap cycles complete.


## K — Concept & Assessment Studio (2026-09-06)

Added course coverage, bank-backed drafts, signature-bound review, immutable
publication/retirement, intervention deep links, reserved fresh follow-up items,
and evidence-qualified outcome aggregates. Planner focus sets share the exact
coverage catalog; no graded curriculum quizzes are created by studio publication.
Alembic 0022 / PostgreSQL parity SQL included. Details and verification scope:
`docs/ASSESSMENT_STUDIO.md` and `docs/ASSESSMENT_STUDIO_BUILD_REPORT.md`.
This enhancement does not complete pending transcription, mobile or production
roadmap work.
