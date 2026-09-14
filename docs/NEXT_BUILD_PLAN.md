# Sasha LMS — Next build plan and UI change instruction set

**Written:** 2026-09-06 by Claude Fable 5.1 for the next build agent (GPT 5.6 Terra)
**Status of the platform:** feature-complete for v2.0 + roadmap R1–R10 + round 2 + learning signals. See `HANDOVER_GPT_5.6_TERRA.md` §2.
**Binding companions:** `CLAUDE.md`, `docs/OWNER_DECISIONS.md`.

This document has three parts:

- **Part A — Flow improvements**: what is clunky today in each journey and the exact change.
- **Part B — UI change instruction set**: the complete, page-by-page recipe to move the whole product onto the glass/orange system.
- **Part C — Sequencing, definition of done, and the check loop.**

Work in the owner's loop: PLAN → BUILD → CHECK → FIX. Verify every button in the browser before reporting it. Failures first.

---

## Part A — Flow improvements

### A1. Learner journey

| # | Today | Change | Where | Done when |
|---|---|---|---|---|
| A1.1 | Student dashboard, My Courses, My Mastery, My Grades, Leaderboard and Live Classes are six separate pages with no single "what do I do next". | Add a **"Continue" rail** at the top of the student dashboard: last lesson with progress, next live class, one adaptive-practice card when the struggle profile has a concept ≥ 60, one due assignment. Everything else stays below the fold. | `pages/dashboard.tsx`, data from `/dashboard/student`, `/signals/me/profile`, `/live/classes`, `/assignments` | Arjun lands on the dashboard and the first card is the lesson he left at 3:52 in course 5. |
| A1.2 | The lesson page (`pages/lesson-redesigned.tsx`, 2,300 lines) mixes player, sidebar, notes, checkpoints, reactions, focus mode, and a dozen dead states (~60 unused symbols in tsc). | **Split** into `LessonShell` (layout + sidebar), `LessonPlayer` (video/3D/lab/game/H5P switch), `LessonNotes`, `LessonTutor`. Delete the dead state (reactions, ambient lighting, speed indicator, comprehension score). Keep the learning-signal hooks (`signalLessonId`, `handleProgress`, quit-early effect) in `LessonPlayer`. | `pages/lesson-redesigned.tsx` → `components/lesson/*` | Same behaviour, file under 600 lines, `tsc` unused-symbol count for the page goes to zero, signals still land (check `learning_signals` rows after a seek). |
| A1.3 | Quiz result screen shows a percentage and "awaiting review"; nothing tells the learner *what to do*. | After submit, show **by-concept results** (reuse `AdaptivePractice`'s result block) and a "Practise the weak ones" button that calls `POST /signals/adaptive/{course_id}/build`. | `pages/quiz-taking.tsx` result branch | A wrong answer on "http status codes" produces a practice set with that concept first. |
| A1.4 | My Mastery lists concepts but a concept does not link back to the lesson that teaches it. | Concept row → "Teaches this: Lesson 2 at 3:00" from `concept_links` (kind `lesson`) and `lesson_concept_markers`. Clicking seeks the player to the marker (`/courses/:id/lessons/lesson-N?t=180`; add `t` handling in the player's mount effect). | `pages/student/my-mastery.tsx`, `routers/mastery.py` (add `teaching_refs` to `/mastery/me`), lesson player | Clicking "http status codes" opens lesson 2 at 3:00. |
| A1.5 | Public preview modal is fine, but the course page still lists locked lessons as plain text. | Locked lessons get a lock chip + "Preview available" chip for preview lessons; clicking a locked lesson opens the enrol CTA (not a 403). | `pages/course-detail.tsx` (curriculum list), `LessonPreviewModal` | Logged-out visitor can open every preview lesson and gets the enrol dialog on locked ones. |

### A2. Instructor journey

| # | Today | Change | Where | Done when |
|---|---|---|---|---|
| A2.1 | The struggle map lives per lecture; an instructor with 40 lectures has no summary. | **Course-level struggle board** tab in Insights: top 10 hot segments across all lessons (query `learning_signals` grouped by lesson+segment, join markers), early-quit leaderboard per lesson, "learners struggling on concept X" count. Add `GET /signals/courses/{id}/hotspots` (editor via `can_edit`). | `routers/learning_signals.py`, `services/learning_signals_service.py::course_hotspots`, `pages/instructor/insights.tsx` | Insights shows lesson 2 3:20–3:30 as #1 with 1 learner (dev DB). |
| A2.2 | Hot segments are silent. | **Retention rule** `hot_segment`: when a segment's score summed over the last 7 days ≥ 3× the lesson median and ≥ 3 learners, write one Notification (`type="hot_segment"`, idempotent via `_sent_since`) to every course editor: "12 learners rewound 3:20–3:30 in Lesson 2 — add a worked example?". | `services/retention_service.py` (follow the existing rule pattern) | `tests/test_retention.py` gets a 5th test; notification appears once, not daily. |
| A2.3 | The AI tutor knows the lesson text but not the learner. | Prepend the learner's struggling concepts + why-strings to the tutor system prompt (`tutor_chat` in `routers/ai_engines.py`, after the graded-item guard — never before it). No key → still 503. | `routers/ai_engines.py`, `services/learning_signals_service.learner_profile` | Test: prompt contains "rewound 3×" for the seeded student; 503 without key unchanged. |
| A2.4 | Course editor Curriculum tab is one long accordion; the Studio face, outcome box, import buttons and lecture list compete. | Two-column editor: left = section/lecture tree (drag), right = the selected lecture's form (content type picker, preview toggle, struggle map, 3D kit). Keep `updateLecture`/`toggleLecture` logic; only re-home the JSX. | `pages/instructor/edit-course.tsx` curriculum branch | Owner can edit lecture 5 without scrolling past lectures 1–4. |
| A2.5 | Review queue, grading queue, gradebook, insights are four sidebar items. | Group under one "Teach" sidebar section with `useNavBadges` counts; the review queue card on the dashboard already exists — link every count to its tab. | `components/dashboard/RoleLayouts.tsx`, `hooks/useNavBadges.ts` | Sidebar shows "Review queue (3)". |

### A3. Admin and commerce

| # | Today | Change | Where | Done when |
|---|---|---|---|---|
| A3.1 | 36 admin pages, each a table with its own filter code. | One `AdminTable` component (search, column sort, page size, CSV export, bulk checkbox) used by every list page. Migrate the five busiest first: courses, students, orders, enrollments, instructors. | `components/admin/AdminTable.tsx` | Five pages share one table; behaviour identical (existing admin tests pass). |
| A3.2 | Payment health, funnel, earnings are three places. | Admin "Revenue" page = funnel report + `admin/payment-health` + refunds list in one screen with the same date picker. | `pages/admin/dashboard.tsx` or new `pages/admin/revenue.tsx` | One date range drives all three panels. |
| A3.3 | Checkout shows UPI/EMI blocks but the Razorpay Offers step depends on the owner. | Nothing to build until the owner creates Offers; keep the honest "coupon not enabled for memberships" message. | — | — |

### A4. Platform hygiene (do alongside, never as a separate sprint)

- Delete dead files listed in `HANDOVER_GPT_5.6_TERRA.md` §8 once the owner agrees (decision to record).
- Frontend tests: `frontend/src/**/__tests__` exist for ~12 pages; every page you migrate in Part B gets a render test that asserts the page's primary heading and primary action button.
- Keep `npm run lint` at 0 errors; do not "fix" the 26 exhaustive-deps warnings blindly (effect loops).

---

## Part B — UI change instruction set (glass + orange system)

### B0. What exists and what the owner asked for

Owner's words: "I like the orange gradient theme and I want a glassmorphic plain output, clear options which is visible, and proper popup functions that make it more professional — the UI that creates the story both in the front and internal system."

Built so far (2026-09-05): tokens and utilities in `frontend/src/styles/globals.css` (`@layer components`, lines ~1200–1262), `GlassDialog` (`components/ui/dialog.tsx`), `useConfirm` / `confirmDialog` / `promptDialog` (`components/ui/confirm.tsx`), `components/ui/card.tsx` glass by default, `.si-page-enter` animation, landing cards, empty state, lesson sidebar, the three signals components. **Adoption: 3 of 154 pages.** The shell (`components/layout/header.tsx`, `footer.tsx`, `main-layout.tsx`, the admin/instructor sidebars) still uses the old flat styling. That is why the product does not yet "tell one story".

### B1. Tokens — use these and nothing else

Tailwind palette (`tailwind.config.js`): `primary` = orange (`primary-500 #f97316` main, `primary-600` hover, `primary-50/100` tints), `secondary` = dark blue (`secondary-900 #0c4a6e`, used only for text on hero surfaces and links), `success` = green. Do not add colours. Amber/emerald/rose from Tailwind's default palette are allowed only for semantic status (warning / ok / danger).

Utility classes (all in `globals.css`):

| Class | Use |
|---|---|
| `si-gradient` | Primary CTA fill, active nav pill, progress fill, hero accents. Never as a page background. |
| `si-gradient-soft` | Section backgrounds behind card grids. |
| `si-hero` | The top band of every landing/marketing page and of every dashboard. |
| `glass-panel` | Every card, panel, table wrapper, form section. Replaces `bg-white rounded-xl border border-gray-200 shadow…`. |
| `glass-panel-dark` | Only inside the lesson player, the live-class stage, and 3D/lab viewers (dark surfaces). |
| `glass-chip` | Tags, status pills, counts. |
| `si-glass-halo` | Optional 1px gradient ring around a featured card (max one per screen). |
| `si-btn-primary` / `si-btn-secondary` / `si-btn-danger` / `si-btn-ghost` | Every button. `components/ui/button.tsx` variants must map to these (see B3). |
| `si-input` | Every text input, select, textarea. |
| `si-page-enter` | On the root element of every routed page. |

Radii: `rounded-xl` for controls, `rounded-2xl` for cards, `rounded-full` for chips. Shadows come from `glass-panel`; do not add `shadow-*` elsewhere. Text: `text-gray-900` headings, `text-gray-700` body, `text-gray-500` meta. Headline font stays the current one (Inter stack) — no new fonts.

Dark mode: the app has a `theme-context`; keep it, but glass surfaces are light-first. Only `glass-panel-dark` surfaces exist in both.

### B2. Layout rules (apply everywhere)

1. **Page skeleton:** `<div className="si-page-enter"> <PageHeader/> <content> </div>`. `PageHeader` = title (text-2xl font-semibold), one-line subtitle (text-gray-500), primary action on the right (`si-btn-primary`), optional chips row. Create `components/ui/page-header.tsx` once and use it on all 154 pages.
2. **Content width:** `max-w-7xl mx-auto px-4 sm:px-6` for lists/dashboards; `max-w-3xl` for forms and readers (quiz taking, assignment submission, settings).
3. **Grid rhythm:** `gap-4` between cards, `p-5` inside cards, `space-y-6` between page sections. No other spacing values for these three roles.
4. **Cards:** `glass-panel rounded-2xl p-5`. Heading inside a card: `text-base font-semibold text-gray-900` + optional right-aligned action (`si-btn-ghost`).
5. **Tables:** wrapper `glass-panel rounded-2xl overflow-hidden`; header row `bg-white/50 text-xs uppercase tracking-wide text-gray-500`; rows `border-t border-white/60 hover:bg-white/40`; wide tables scroll inside `overflow-x-auto`, never the page.
6. **Forms:** label `text-sm font-medium text-gray-700 mb-1`; control `si-input w-full`; help text `text-xs text-gray-500`; error text `text-xs text-rose-600`; sections separated by `glass-panel` cards with a heading. Submit row sticky at the bottom on long forms (`sticky bottom-0 glass-panel p-3 flex justify-end gap-2`).
7. **Dialogs:** only `GlassDialog` (sizes sm/md/lg); confirms only via `useConfirm`. Destructive confirm uses `danger: true` (red button). Dialog title = verb + object ("Delete lesson", "Issue certificate").
8. **Empty states:** `EmptyState` from `components/dashboard/primitives.tsx` (glass, icon, one sentence, one primary action). Never an empty table.
9. **Toasts:** keep `react-hot-toast`; style once in `main.tsx` toaster options: `glass-panel rounded-xl text-sm`. No inline success banners that duplicate a toast.
10. **Status chips:** `glass-chip` + a coloured dot (`bg-primary-500`, `bg-emerald-500`, `bg-amber-500`, `bg-rose-500`). Text never coloured by itself.
11. **Loading:** skeleton blocks `animate-pulse bg-white/60 rounded-xl` in the card's shape; spinners only inside buttons.
12. **Icons:** lucide-react only, `w-4 h-4` inline with text, `w-5 h-5` in headers. No emoji in the internal system (the curriculum type dropdown emoji may stay — owner likes them).
13. **Motion:** `si-page-enter` on page mount, `transition` on hover states, nothing else. Respect `prefers-reduced-motion` (already handled by the class).
14. **Accessibility:** every icon-only button has `aria-label`; every input has a `<label>` or `aria-label`; focus rings are the `si-input` ring — never remove outlines.

### B3. Shared components to change first (one day, unlocks everything)

| Component | Change |
|---|---|
| `components/ui/button.tsx` | Map variants: default→`si-btn-primary`, secondary/outline→`si-btn-secondary`, destructive→`si-btn-danger`, ghost/link→`si-btn-ghost`. Keep the prop API so 150 call sites need no edits. |
| `components/ui/input.tsx` (+ select/textarea if present) | Base class → `si-input`. |
| `components/ui/card.tsx` | Already glass; make `CardHeader` use the card heading style from B2.4. |
| `components/ui/badge.tsx` | Base → `glass-chip`; variants only change the dot colour. |
| `components/ui/page-header.tsx` | NEW (B2.1). |
| `components/dashboard/primitives.tsx` (`EmptyState`) | Already glass; add `compact` prop for use inside cards. |
| `components/layout/header.tsx` | Sticky, `glass-panel` bar (`bg-white/70 backdrop-blur-xl border-b border-white/70`), logo left, nav centre, avatar/cart right; active link = `si-gradient` pill with white text. |
| `components/layout/footer.tsx` | `si-gradient-soft` background, four columns, chips for Membership/Bundles links (already linked). |
| `components/layout/main-layout.tsx` | Body background `si-hero` at the top fading to `#fff` (the hero band is what makes glass read as glass). |
| Admin / superadmin layouts (`components/layout/admin/admin-layout.tsx`, `superadmin-layout.tsx`) and the instructor / student / parent / SPOC / company role layouts (`components/dashboard/RoleLayouts.tsx`, wired in `App.tsx`) | One `Sidebar` component: `glass-panel` column, section labels (`text-[11px] uppercase text-gray-500`), items with icon + label + `useNavBadges` count chip, active item `si-gradient` pill. Collapsible to icons at `lg` and below. |
| `main.tsx` toaster options | B2.9. |

After this step, run the app: most pages already look 60 % migrated because buttons, inputs, cards, chips and the shell changed underneath them.

### B4. Page migration recipe (repeat per page)

1. Open the page; list its ad-hoc style strings: `bg-white rounded…`, `shadow-…`, `bg-gradient-to-…`, `bg-blue-…`, `text-blue-…`, custom modals, `window.confirm`.
2. Wrap the root in `si-page-enter`; replace the hand-written title block with `PageHeader`.
3. Replace each card wrapper string with `glass-panel rounded-2xl p-5`. Replace each table wrapper per B2.5.
4. Replace blue accents with `primary-*`; replace `text-blue-600` links with `text-primary-600 hover:text-primary-700`.
5. Replace every inline button class with the `Button` component (B3) or an `si-btn-*` class; every input with `si-input`.
6. Replace custom modals with `GlassDialog`; confirms with `useConfirm`. Grep for `window.confirm|window.prompt|window.alert` — must be zero.
7. Add an `EmptyState` for every list that can be empty.
8. Run `npx eslint <file>`; open the page in the browser as the right role; click every button; take a screenshot for the report.
9. Add or update the page's render test (`__tests__/<page>.test.tsx`: heading + primary action present).

Patch files with a Python script (assert the anchor count, then write) — the codebase's TSX files are large and hand edits drift. Never use multi-line bash heredocs for TSX.

### B5. Migration order (page groups, with the number of pages)

Work top-down; each group is one PLAN → BUILD → CHECK → FIX cycle with its own report and screenshots.

1. **Shell + shared components** (B3) — 0 pages, everything changes.
2. **Public / marketing (14):** `Home`, `About`, `Contact`, `categories`, the three `category-*` pages, `meiporul-ar`, `courses` listing + `course-detail`, `bundles` + `bundle-detail`, `membership`, `library` + `library-detail`, `blog` + `blog-detail`, `for-companies`, `hall-of-fame`, `verify-certificate`, `privacy/terms/refund-policy/shipping`, `not-found`, `server-down`. Hero band on each; cards in grids; chips for type/price/level.
3. **Auth (6):** login, register, forgot/reset password, verify-email, linkedin-callback. Single centred `glass-panel` on `si-hero`; `AuthLayout` owns the frame.
4. **Student workspace (16):** `dashboard`, `my-courses`, `student/my-mastery`, `student/my-grades`, `leaderboard`, `student/live-classes`, `student/live-class-join`, `student/live-class-recording`, `my-library`, `wishlist`, `cart`, `checkout`, `profile`, `settings`, `dashboard/*` (messages, analytics, internships, vouchers), `parent/dashboard`. The "Continue" rail (A1.1) lands here.
5. **Learning surfaces (5):** `lesson-redesigned` (do the split A1.2 at the same time), `quiz-taking` (+ A1.3), `assignment-submission`, `game-play`, `certificate`. Dark glass for the player stage only.
6. **Instructor studio (31):** dashboard, courses, course-start, edit-course (+ A2.4), quiz-builder, assignment-builder, game-builder, games, h5p-library, three-d-tasks, insights (+ A2.1), review-queue, grading, grading-queue, gradebook, students, analytics, live-classes, live-class-new, live-class-console, live-class-report, past-classes, certificate-designer, blog, blog-editor, ebooks, course-coverage. Studio faces (`components/studio/*`) already exist — keep them, restyle to glass.
7. **Admin (36) + superadmin (5):** build `AdminTable` (A3.1) first, then migrate lists in this order: courses, students, orders, enrollments, instructors, approvals, coupons, memberships, bundles, company-invoices, content-libraries, everything else.
8. **Company / SPOC (9):** `company/dashboard`, `for-companies/signup`, `spoc/*`, `internships`, `internship-detail`.

Total: 154 pages. At roughly 12–15 pages per cycle that is 10–12 cycles.

### B6. Rules that protect what already works

- Never change data fetching or handlers while restyling a page. If a handler must move (A1.2, A2.4), do it in its own cycle with tests.
- Radix components need `mousedown` before `click()` in the embedded browser — the app is fine, only the automation needs it.
- Keep `data-testid`s that existing tests use (`grep -r "getByTestId\|data-testid"` before deleting markup).
- `Button` variant mapping (B3) must keep `asChild` and `size` props working — many pages pass them.
- Do not touch `frontend/public/h5p-player.html` (sandboxed) or the Jitsi stage markup for styling — only their glass wrappers.
- `lesson-redesigned.tsx` carries the learning-signal instrumentation; if you split it, keep `signalLessonId`, `handleProgress`, the quit-early effect and the note signal, and re-verify with a seek that a `video_rewind` row lands.

### B7. Check list per cycle (paste into every report)

- [ ] `npm run lint` — 0 errors, warnings ≤ 26
- [ ] `npx tsc --noEmit` — zero new errors in touched files
- [ ] `npm run test` — page render tests green
- [ ] Browser: every button on every migrated page clicked as the right role; one screenshot per page (light theme, desktop 1280 and mobile 375 via `resize_window`)
- [ ] `grep -rn "window.confirm\|window.alert\|window.prompt\|dangerouslySetInnerHTML" src/pages src/components` — no new hits
- [ ] Backend untouched → no restart needed; if touched, full `pytest` + `smoke.sh`

---

## Part C — Sequencing, definition of done, loop

### C1. Order of work (recommended)

1. **Cycle 1 — Shell + shared components** (B3). Report with before/after screenshots of the dashboard, a list page and a form.
2. **Cycles 2–4 — Public, auth, student workspace** (B5 groups 2–4) + the Continue rail (A1.1) + concept back-links (A1.4).
3. **Cycle 5 — Learning surfaces** (B5 group 5) + lesson split (A1.2) + quiz result by concept (A1.3) + locked-lesson chips (A1.5).
4. **Cycles 6–8 — Instructor studio** (B5 group 6) + course hotspots (A2.1) + hot-segment rule (A2.2) + tutor context (A2.3) + two-column editor (A2.4) + sidebar grouping (A2.5).
5. **Cycles 9–11 — Admin, superadmin, company/SPOC** (B5 groups 7–8) + `AdminTable` (A3.1) + Revenue page (A3.2).
6. **Cycle 12 — Engine A full** (recordings → transcript → segmented lesson). Needs the owner's transcription decision first (Whisper self-hosted vs Bhashini vs GLM audio); the transcript store (`routers/ai_engines.py`) and `process_transcript` (`services/ai_layer_service.py`) already exist.
7. **Cycle 13 — Production readiness**: Postgres rehearsal (`alembic upgrade head` on an empty Postgres, then `seed_*` scripts), `docker-compose.production.yml` up on a VPS, nginx TLS, backups (`database/backups/`), uptime check on `/health` and `/api/v1/admin/payment-health`.

### C2. Definition of done (every cycle)

- Failures first in the report, then what was built, then the check table, then interventions.
- Every new endpoint: test in `backend/tests/`, prefix in `noSlashEndpoints` if it declares `@router.get("")`, migration + parity SQL if it adds a column.
- Every page: clicked in the browser as the right role, screenshot in the report.
- `CLAUDE.md` gets one paragraph per new feature (traps included); `docs/OWNER_DECISIONS.md` gets a numbered line per assumption (next number 32); the ledger gets a section.
- Nothing is reported as done that was not verified. "Honest 503 without the key" is a pass.

### C3. When the owner asks "what's next"

Bring this document's remaining items as a numbered list, one line each, ordered by value to the learner first, instructor second, admin third. He will reply with numbers. Build those, in that order, one cycle at a time.
