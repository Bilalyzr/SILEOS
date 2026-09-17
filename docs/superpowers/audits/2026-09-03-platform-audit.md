# Platform Audit — findings register (2026-09-03)

**Method:** scripted cross-reference of all 512 backend routes vs all 394 distinct frontend API
calls (both directions), live HTTP probes against the running QA backend to confirm 404s
(401/403/405/422 = route exists, 404 = missing), then three independent deep-dive passes
(authoring surfaces, backend write-path integrity, reachability/trailing-slash), with manual
spot-verification of every Critical claim. Branch: `quiz-engine-upgrade` (audit commit only).

**Scope note:** quiz-engine findings F1–F10 live in
`docs/superpowers/specs/2026-09-03-quiz-engine-design.md` §0 and are NOT repeated here except
where the audit found NEW quiz defects. Severity: Critical = data loss / feature dead-end /
money bug reachable by users; Important = silent wrong behavior; Minor = edge/cosmetic.

---

## A. CRITICAL

### A1. Editing a quiz's duration in the curriculum tab destroys the whole question bank
`frontend/src/pages/instructor/edit-course.tsx:540-545` sends `PUT /courses/{id}/quizzes/{qid}`
with ONLY `{timeLimit}`; backend `update_quiz` (`quizzes.py:435-447`) unconditionally deletes all
questions+answers and rebuilds from the absent `questions` key → `[]`. Instructor tweaks "Duration
(min)" on a quiz row → every question silently deleted, no warning. **Fix vehicle:** quiz-engine
plan Task 3 must add the rule: `questions` key ABSENT in a PUT payload = leave questions
untouched (None vs []), plus a dedicated regression test for the duration-edit path.
Verified: code-verified (both sides read this session). Severity driver: silent data destruction.

### A2. Create-Course wizard's assignment builder is a second dead end (same class as the quiz one)
`create-course.tsx:1457-1571` edits `lecture.assignmentData` (description, maxScore, dueDate,
file rules, attachments) — the file contains ZERO `assignments` API calls; `updateLecture`
(`:396-441`) has no assignmentData mapping. Backend `POST /courses/{id}/assignments`
(`assignments.py:190`) is fully functional and never called from the wizard. Instructor publishes
→ success toast → no assignment exists. **Fix:** same handoff treatment as quiz Task 7.
Verified: grep (0 occurrences) + code read.

### A3. Wizard curriculum sections are never persisted (section titles/grouping lost on publish)
`create-course.tsx` addSection/updateSection are state-only; `createOrUpdateCourse` (`:470-504`)
sends metadata only; `autoSaveDraft` sends `course_structure` (`:580-583`) but
`schemas/course.py:48-74` `CourseUpdate` has no such field (Pydantic drops it) and no
`sections_meta` is ever sent by this page. Lessons exist as rows but land in one orphan bucket;
section titles gone after publish. **Fix:** wizard must persist `sections_meta` exactly like
edit-course.tsx does (it already groups by the same `lectureIds` scheme).
Verified: code read (my own pass) + agent schema check.

### A4. "Apply to become instructor" and admin "create instructor" both 500 on every call
`users.py:316-325` builds `InstructorProfile(bio=…, expertise=…, experience=…, education=…,
certifications=…, social_links=…, status=…)`; `admin.py:2929-2933` builds
`InstructorProfile(bio=…, status="approved", expertise=…, experience=…, education=…)`.
The model (`models/user.py:104-132`) has NONE of those columns (`instructor_bio`, `is_approved`,
…). SQLAlchemy raises TypeError → 500 every time. The admin one is REACHABLE:
mounted page `/admin/manage` (App.tsx:802) calls `POST /admin/instructors/create`
(`pages/admin/manage.tsx:63`). **Fix:** small — map to real columns (or extend the model with a
migration if the data matters). Verified: constructor args vs model columns read this session.

### A5. Sale price is advertised at checkout but never charged on the direct (Razorpay) path
`checkout.tsx:79-87,393-403` shows and promises `sale_price || price`; `payments.py:272` computes
`base_price = float(course.course_price)` — `course_sale_price` is never read anywhere in
payments.py (grep: zero matches). Coupon discounts also compute off list price
(`coupon_service.py:217`). Meanwhile the cart path (`orders.py:86`) DOES honor sale price — two
purchase paths, two different prices for the same course. Student sees "Pay ₹499", modal demands
₹999. **Fix vehicle:** money path → strongest-review pipeline (failing test first: create-order
must use `sale_price when 0 < sale_price < price`; coupon base must match). Verified: code read
this session (both sides).

### A6. Quiz update/create are non-atomic with commits inside loops (already spec'd; confirmed broader)
`quizzes.py:133-134,463-465` (commit per question; quiz row committed before questions
`:113-115`): mid-loop failure leaves a published quiz with 0..k questions and no error.
FK hazard: `quiz_attempt_answers.question_id` → delete-and-recreate in update_quiz 500s on any
quiz that has attempts (IntegrityError on first in-loop commit). Covered by quiz plan Tasks 3
(plus A1's absent-key rule). Cross-reference so the reviewer doesn't miss it:
this is the same partial-write class as the shipped payment bug.

### A7. `add_question_to_quiz` persists unscorable questions and returns 200
`quizzes.py:217-227`: options + correct-answer write wrapped in bare `except: pass` → malformed
`question_options` silently yields a question with zero options. Also takes raw
`question_settings` (second encoder of the same column). **Fix:** covered by quiz plan Task 2
(validation + explicit error handling). Listed here so the register is complete.

## B. IMPORTANT

### B1. Certificate-template picker silently empty on 4 mounted pages
Frontend calls `GET /certificates/templates/list` (create-course.tsx:186, edit-course.tsx:185) —
no such route (verified 404 live). Real route is `GET /certificates/templates`
(certificates.py:1555, trailing slash `/templates/`), AND `noSlashEndpoints` contains
`/certificates/templates` (axios.ts:60), so even calling the right path without the slash 404s.
Silent catch → `[]` → instructors see no certificate templates. **Fix:** call the correct path
with the slash (and reconcile the noSlashEndpoints entry). Verified live 404 + axios entry.

### B2. Blog editor templates silently empty (create mode)
`GET /blog/templates` (api/blog.ts:12) — no route (verified 404). Fires on mount of
`/instructor/blog/create` (blog-editor.tsx:87). Silent catch → empty template picker.
**Fix:** add route or remove feature.

### B3. Spoc blog "Export" button errors
`GET /export-import/export/blogs` (spoc/blog.tsx:70) — no route. Real path is
`GET /spoc/export/{section}` (export_import.py:2548). Visible error toast on click.
Verified live 404.

### B4. Video notes are localStorage-only while the UI says "Note added!"
`lesson-redesigned.tsx:1177-1216` — no notes backend exists (grep: zero notes routes).
Cleared on device/browser change. **Fix (product ruling):** small notes API (table + 2 endpoints)
or relabel the toast; recommend building it — tutoring use-case values notes.

### B5. Notification/privacy preference toggles persist to localStorage only
`settings.tsx:4-7,60-71` — self-documented ("no dedicated preferences API yet"), success toast
anyway. Server never learns the preference. **Fix:** preferences columns + endpoint, or remove
the toggles until real.

### B6. Course tags dropped for admins and on direct publish in the wizard
Tags sent only in the instructor auto-save draft path (create-course.tsx:575-578, which returns
early for admins `:556`); `CourseCreate` schema has no `tags` field at all
(schemas/course.py:42-46); only the update path persists them (courses.py:660).
**Fix:** add tags to create schema + wizard publish payload.

### B7. Company bulk-invite and CSV import commit per row
`companies.py:368` (per-entry commit incl. 48h tokens), `export_import.py:3073` (per-CSV-row
commit). Partial bulk operations reported as "errors: n" with no retry semantics.
**Fix:** single transaction per operation (same pattern as quiz plan Task 3).

### B8. Quiz attempt_info read at :999 bypasses the dual-encoding helper
`quizzes.py:999` does bare `json.loads(attempt.attempt_info)` with no try/except; every writer
double-encodes today (`:816,830,1236,1366,1410,1446,1682` assign `json.dumps(...)` to a JSON
column) but any real-dict writer/migration → results endpoints 500. **Fix:** use
`_attempt_info_dict` (:1039) + stop double-encoding (quiz plan Task 3).

### B9. Assignments double-encode JSON columns inconsistently
`assignments.py:257,261,411,414,704,735` `json.dumps` into JSON columns (`allowed_file_types`,
`attachments`, `files`) while `rubric` in the same table is a real list — mixed encodings on one
table; readers only work by luck of round-tripping. **Fix:** normalize to direct assignment.

### B10. Duplicate DELETE handler on lessons — reorder landmine
`courses.py:1493` and `:1852` both declare `DELETE /{course_id}/lessons/{lesson_id}`; FastAPI
dispatches to the first; the second is dead code. The file's own comment documents this exact
hazard for a removed PATCH twin. **Fix:** delete the dead twin.

### B11. Blog detail 404s on numeric-id URLs
`GET /blog/{id}` (blog-detail.tsx:84) vs backend serving slug-based `GET /blog/{slug}` +
`GET /blog/id/{post_id}` (blog.py:244). All internal links pass slugs so it only breaks legacy/
numeric URLs — conditional reachable. **Fix:** resolve numeric segments via `/blog/id/{id}`.

### B12. swallowed due-date parse
`assignments.py:216-219,395-398` — invalid `dueDate` silently stored as None. **Fix:** 422.

## C. MINOR

- **C-1.** Quiz row rename in curriculum PATCHes the lessons endpoint with a quiz id → 404 +
  full page reload (edit-course.tsx:599,613-614; only duration is special-cased :540).
- **C-2.** Lecture "type" dropdown is client-only in both editors; reverts on reload
  (edit-course.tsx:585-593; create-course.tsx:414-429).
- **C-3.** Video duration "M:SS" parsed with parseInt → 1:30 becomes 1 (edit-course.tsx:1661-1667
  vs :579-583).
- **C-4.** Wizard auto-save sends `short_description`; schema only has `excerpt`
  (create-course.tsx:563 vs schemas/course.py:48-74).
- **C-5.** Admin "Add New Course" page (admin/new-course.tsx:182-186) is a stripped duplicate of
  the wizard with a hardcoded stale category list ("excel", …) diverging from the real taxonomy.
- **C-6.** Drag-reorder survives only if user clicks Save; `sectionsDirty` state is set but never
  read (edit-course.tsx:653-690,156) — no unsaved-changes warning.
- **C-7.** `instructor_reviews.py:147-167` — GET endpoint writes `is_read=True` with per-row
  commits inside a read handler.
- **C-8.** Latent trailing-slash conflicts in `noSlashEndpoints`: `/categories`, `/tags`,
  `/instructors`, `/wishlist`, `/coupons`, `/hall-of-fame` entries point at backend routes declared
  WITH trailing slash; saved today only because current callers hardcode the slash. One refactor
  away from invisible 404s (axios.ts:56-109).

## D. Product gaps — backend exists, no web UI (rulings needed, not bugs)

| Capability | Backend | State |
|---|---|---|
| Student "My Orders" / purchase history | `GET /orders/me` (orders.py:325) | No student page; only admin sees orders |
| Instructor reviews: student rates instructor; instructor inbox + respond | instructor_reviews.py (5 routes) | Zero web UI (flutter declares it); table collecting dust |
| Student work-log submission + announcements | student_workspace.py:49,96,117 | Company-side review UI exists; student submission side absent on web |
| "Become an instructor" application for existing users | `POST /users/apply-instructor` | No UI; handler 500s anyway (A4) |
| Blog contact form / newsletter | blog.py:721,743 | No frontend submit |

## E. Dead code / cleanup (no user impact; delete or wire)

- api/auth.ts `updateProfile` (:106), instructor-profile (:197), roles (:189), social (:145) —
  all call nonexistent routes; zero callers (real flows use /users/profile and /auth/google).
- api/course.ts: getFeaturedCourses(:31), getPopularCourses(:38), searchCourses(:198),
  getCourseCurriculum(:250), getCourseAnnouncements(:257), getCourseCertificate(:268),
  instructor.getCourses(:349), getStudents(:356), getAnalytics(:369),
  uploadCourseMaterial(:383), getCoursesByInstructor(:183) — all 404 routes, zero callers.
- Redundant backend: `POST /quizzes/{id}/questions` (unused by UI), `GET /courses/pending`,
  `PATCH /courses/{id}/approve|reject` (admin uses /admin/courses/{id}/status), duplicate
  `GET /dashboard/admin`, `GET /progress/course/{id}`.

## F. Verified CLEAN (checked, no findings)

- Money: payments.py recomputes amounts from DB and compares to captured (:424-428,:542-544,
  :720-723); orders priced from DB; coupon clamps (coupon_service.py:155-166); memberships use DB
  plan prices; company invoice delete-recreate is single-commit; payments_proxy amounts come from
  token-authenticated partner server.
- Authz: no unauthenticated mutating routes found beyond deliberately-guarded webhooks/internal
  endpoints (HMAC-verified, INTERNAL_TOKEN + XFF-rejected, PAID-state refused).
- Flows verified working end-to-end at the contract level: quiz-taking submission/scoring,
  assignment grading payloads, certificate designer persistence, live-class scheduling/polls,
  game builder + server-clamped scores, blog editor, H5P chunked upload, profile save (real path
  PUT /users/profile), 2FA setup/enable/disable, video progress tracking (progress.py called via
  fetch every 5s — initially misread as orphan).

## Remediation sequencing (recommendation)

1. **Quiz-engine branch (in flight):** absorb A1 (absent-questions rule + duration-edit test),
   A6, A7, B8 into plan Tasks 2/3 — already 90% covered by the existing plan text.
2. **Authoring fix wave (new small branch):** A2 assignment handoff, A3 wizard sections_meta,
   B6 tags, A4 instructor-create 500s (2-line fixes), B1/B2/B3/B11 broken GETs, B10 dead twin,
   C-1..C-4. All are small, test-first, non-money.
3. **Money fix (own branch, strongest review):** A5 sale-price authority + coupon base + tests
   across BOTH purchase paths.
4. **Backlog with owner rulings:** B4 notes API, B5 preferences, D-table product gaps, E cleanup,
   C-8 slash refactor.
