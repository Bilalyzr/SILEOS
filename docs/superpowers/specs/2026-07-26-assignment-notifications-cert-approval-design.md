# Assignment Submission Notifications + Certificate Approval Gate — Design

Date: 2026-07-26
Status: Approved (pending spec review)

## Problem

1. When a student submits an assignment, nobody is notified — the instructor
   only finds out by manually opening the grading page.
2. Certificates auto-issue the moment a student reaches 100% course completion.
   Completion only requires assignments to be **submitted**, not **approved**, so
   a student gets a certificate before the instructor has reviewed their work.
3. There is no admin fallback when an instructor is unavailable to review.

## Goals

- Notify the course instructor (in-app **and** email) when a student submits an
  assignment. Admin can see pending items and act as a fallback.
- Gate certificate issuance on instructor/admin **approval** of the assignment
  submission(s), not on mere completion.
- Admin can approve/reject any submission (fallback for an absent instructor).

## Non-goals (YAGNI)

- No auto-escalation timer (admin fallback is manual — admin can act anytime).
- No per-user email preferences.
- No websockets / push; the notification bell polls on load.

## Current state (verified)

- `SubmissionStatus` = `SUBMITTED | GRADED | RETURNED` (`models/assignment.py`).
  Approve == grade (→ `GRADED`); reject == return (→ `RETURNED`).
- Endpoints already exist: `POST /submissions/{id}/grade`, `POST /submissions/{id}/return`
  (both `require_instructor`).
- `submit_assignment` (`routers/assignments.py`) saves the submission and returns —
  no notification.
- Course completion (`services/course_service.py`) requires
  `completed_assignments == total_assignments`, where `completed_assignments` counts
  **submitted** rows (any status) — not approved.
- Certificates auto-issue via `CertificateService.issue_certificate_for_enrollment`,
  gated only on `enrollment.completion_date`.
- No `Notification` model / router / in-app system exists. Email helpers live in
  `app/utils/email.py`; prod SMTP is unreliable, so in-app is the primary channel.

## Design

### A. Notification system (new)

**Model** `Notification` (`models/notification.py`, table `notifications`):
`id`, `user_id` (FK users, recipient, indexed), `type` (string enum),
`title`, `message`, `link` (frontend path, nullable), `related_id` (int, nullable —
e.g. submission id), `is_read` (bool, default false), `created_at`.

Types (string constants): `submission_received`, `cert_issued`, `submission_returned`.

**Helper** `create_notification(db, *, user_id, type, title, message, link=None, related_id=None, email=False, background_tasks=None)`:
inserts the row and, when `email=True`, queues a best-effort email via the existing
`utils/email.py` helper on `background_tasks` (never blocks or raises into the request).

**Router** `routers/notifications.py`, mounted `/api/v1/notifications`:
- `GET /` → current user's notifications (paginated, newest first) + `unread_count`.
- `PATCH /{id}/read` → mark one read (must belong to caller).
- `POST /read-all` → mark all caller's notifications read.

**Frontend**: `api/notifications.ts` wrapper + a bell component (unread badge +
dropdown list, each row links to `notification.link`) in the instructor and admin
dashboard headers. Fetch on mount; light interval poll (e.g. 60s) while mounted.

### B. Certificate approval gate

**Eligibility rule (option A):** a certificate may issue only when
`enrollment.completion_date` is set AND, for every assignment belonging to the
course, the student has a submission with status `GRADED`. If the course has **no**
assignments, completion alone issues (unchanged behavior).

**Changes:**
- Add `all_assignments_approved(db, user_id, course_id) -> bool` helper (in
  `certificate_service.py` or a small assignments helper): true if the course has no
  assignments, or every assignment has a `GRADED` submission by that user.
- `issue_certificate_for_enrollment`: before issuing, call the helper; if not
  approved, do **not** issue (return `(None, False)`; treated as "pending").
- `grade_submission` (approve): after marking `GRADED` and committing, re-check
  eligibility for that student+course; if now fully approved and the course is
  complete, call `issue_certificate_for_enrollment` and notify the student
  (`cert_issued`, in-app + email).
- `return_submission` (reject): notify the student (`submission_returned`,
  in-app + email) so they know to resubmit.

**Admin fallback:** change `grade_submission` and `return_submission` authorization
from instructor-only to **instructor who owns the course OR admin**. (Introduce a
small `require_instructor_or_admin`-style check inside the handlers using the
existing course-ownership check already present in `return_submission`.)

### C. Visibility / approval queue

- **Instructor**: the existing assignment-grading page already lists submissions;
  add an "approving issues the certificate" hint. No new page.
- **Admin**: new page `/admin/approvals` (`pages/admin/approvals.tsx`) listing all
  `SUBMITTED` (pending) submissions across all courses, with student, course,
  assignment, submitted-at, and approve/return actions; flag rows whose approval
  would complete a certificate. Backed by a new
  `GET /api/v1/admin/pending-submissions` endpoint (admin only). Add an "Approvals"
  entry to the admin nav.

### D. Student side

On the course/certificate view: when the enrollment is complete but not all
submissions are approved, show "Certificate pending instructor approval" instead of
the download button. Once approved and issued, show the download. Requires the
course/cert response to expose a `certificate_status` of
`issued | pending_approval | not_eligible` (derived, no new column).

## Data flow

```
student submits assignment
  → create_notification(instructor, submission_received, email)      [A]
instructor OR admin grades (approve)
  → status GRADED
  → if course complete AND all assignments GRADED:
        issue_certificate_for_enrollment  → create_notification(student, cert_issued, email)   [B]
instructor OR admin returns (reject)
  → status RETURNED → create_notification(student, submission_returned, email)
```

## Components & boundaries

- `models/notification.py` — the row.
- `services/notification_service.py` — `create_notification` (+ email fan-out). Single
  place other code calls; hides email/DB details.
- `routers/notifications.py` — read/mark-read API for the current user.
- `certificate_service.py` — gains the approval-eligibility gate.
- `routers/assignments.py` — submit/grade/return call `create_notification` and the
  cert trigger; auth widened to admin.
- `routers/admin.py` (or `export_import`-style) — `GET /admin/pending-submissions`.
- Frontend: `api/notifications.ts`, notification bell component, `admin/approvals.tsx`,
  student cert-status display.

## Testing

- `all_assignments_approved`: no-assignment course → true; one submission still
  `SUBMITTED` → false; all `GRADED` → true.
- `issue_certificate_for_enrollment`: complete + unapproved submission → no cert;
  complete + all approved → cert issued once (idempotent).
- Grade last pending submission → cert issued + student notification created.
- Submit → instructor notification created; return → student notification created.
- Admin can grade/return a submission for a course they don't own; instructor cannot
  grade another instructor's course.
- `GET /notifications` returns only the caller's rows + correct `unread_count`;
  `read`/`read-all` scoped to caller.

## Rollout

Backend (models/services/routers) + frontend. New `notifications` table created by
`init_db()` on startup (same pattern as existing models). No data migration. Deploy =
git pull → rebuild frontend → restart backend. Email is best-effort; the feature works
fully on in-app alone if SMTP is down.
