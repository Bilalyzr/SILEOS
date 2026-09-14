# Site Updates — Integration & Live Deployment Notes (2026-08-13)

This document ties together every mechanism shipped in the `feature/site-updates-issues`
branch (the 9 items in `issues/siteupdates.md`) and how they combine on the
live site. Each section maps an issue to: the backend endpoints, the DB
changes, and the frontend surfaces.

## How to deploy

1. Merge `feature/site-updates-issues` into `main`.
2. Apply the DB changes. The backend's `init_db()` reconciles everything on
   boot (`Base.metadata.create_all` adds the new `watch_sessions` table;
   `ensure_schema()` adds the `courses.video_view_count` column), so a plain
   restart of the backend container is enough for a fresh deploy. To bring an
   existing live DB in line **without** a restart, run:

   ```bash
   bash backend/migrations/apply_2026_08_13_site_updates.sh
   ```

3. Rebuild the frontend (`npm run build`) so the new admin pages and player
   tracking ship.

No environment variables, secrets, or new services are required.

---

## Issue 1 — Video view count per course

- **DB**: `courses.video_view_count` (int, default 0). Migration
  `course_video_view_count_2026_08_13.sql`.
- **Backend**:
  - `POST /api/v1/courses/{course_id}/lessons/{lesson_id}/view` — increments
    the counter when a student opens a lesson video.
  - Counters also surfaced in: `/admin/courses`, `/courses/`, instructor
    `/courses/my-courses`, course detail, `CourseStats`, `CourseManagementResponse`.
- **Frontend**: `courseAPI.recordLessonView` fires on lesson open
  (best-effort); admin Courses table shows a **Video Views** column.

## Issue 2 — Course statistics panel

- **Backend**: `GET /api/v1/analytics/courses/{id}/statistics` — quiz
  attempts / pass-rate / avg-score, struggles (failed attempts + top
  strugglers), revisits (repeat watch sessions + most-revisited lessons),
  averages (progress, sessions/student, time/student).
- **Frontend**: **Statistics** tab on Admin → Courses → Student Activity.

## Issue 3 — Restrict "Mark as Complete" until quiz is passed

- **Backend**: `mark_lesson_complete` (`/courses/{id}/lessons/{lid}/complete`)
  now requires a real, passing `QuizAttempt` for quiz content items; it no
  longer fabricates a passing attempt. Returns 403 with a clear message.
- **Frontend**: Mark-Complete button is disabled for quiz items ("Pass the
  quiz to complete"); video-end no longer auto-completes quiz items.

## Issue 4 — Public certificate URL by Certificate ID

- **Backend**: `GET /api/v1/certificates/public-url/{certificate_id}`
  resolves a certificate by numeric ID and returns `public_url`,
  `share_url`, `certificate_url`, `image_url`. Certificate list/detail now
  include `public_url` + `secure_certificate_id`.
- **Frontend**: `certificatesAPI.getPublicUrl(id)` + a **Copy Link** button
  on the certificate page. Existing `/verify-certificate/:certificateId`
  remains the public verification route.

## Issue 5 — Phone number in admin user details

- **Backend**: `/admin/users` (list) now returns `phone`; per-user detail
  already did. `UserManagementResponse` carries `phone`.
- **Frontend**: admin Students table has a **Phone** column; phone is
  included in the search filter.

## Issue 6 — Voucher connected to course progress

- **Backend**: `/internships/my-vouchers` and `/admin/internship-vouchers`
  attach `course_progress` (progress %, enrollment status, is_completed,
  completion date) for the redeemed course, batch-loaded (no N+1). Admin
  endpoint also returns `redeemed_on_course_id` / `redeemed_course_title`.
- **Frontend**: My Vouchers page has a **Course Progress** column with a
  progress bar and Completed badge.

## Issue 7 — Apply button for vouchers & coupons

- **Backend**: `POST /api/v1/coupons/validate` now resolves `InternshipVoucher`
  codes (INTR-…) **first** — valid/owned/unredeemed → 100% discount; wrong
  owner or already-redeemed → clear error — then falls through to coupons.
- **Frontend**: both the cart and direct-checkout Apply buttons call this
  endpoint, so both now accept vouchers.

## Issue 8 — Student Activity (time / sessions / last active / history)

- **DB**: new `watch_sessions` table. Migration `watch_sessions_2026_08_13.sql`.
- **Backend**:
  - `POST /api/v1/progress/watch-event` — records started/paused/resumed/
    completed events (with duration + position); `started` also bumps the
    course video view count.
  - `mark_lesson_complete` writes `StudentCourseActivity` rows
    (lesson_completed / quiz_passed / assignment_submitted).
  - `GET /api/v1/analytics/courses/{id}/student-activity` — per-student time
    spent, watch sessions, last active, currently-watching flag.
  - `GET /api/v1/analytics/students/{u}/courses/{c}/history` — full viewing
    history timeline + discrete activities.
- **Frontend**: lesson player fires watch events; new
  **Admin → Courses → Student Activity** page (route
  `/admin/courses/:courseId/activity`) with summary cards, per-student table,
  and expandable viewing-history timeline.

## Issue 9 — Combined for live site

- All routers are registered in `backend/app/main.py` (courses, certificates,
  coupons, progress, analytics, internships, admin).
- All schema changes are reconciled on boot (`init_db` → `create_all` +
  `ensure_schema`) and mirrored in idempotent SQL migrations.
- One-shot migration runner: `backend/migrations/apply_2026_08_13_site_updates.sh`.
- No new env vars or services.
