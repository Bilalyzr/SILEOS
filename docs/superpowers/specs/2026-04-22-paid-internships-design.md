# Paid Internship Programs — Design Spec

**Date:** 2026-04-22
**Status:** Approved, executing via subagent-driven-development

## Problem

Two product threads were half-built and diverging:
1. A legacy "apply to internship" module (`Internship` + `InternshipApplication`, `/internships/{id}/apply`) — never carried real users, flagged broken by the recent audit.
2. College-cohort onboarding via `ReferralCode` + SPOC attendance.

The user wants a new primary flow that merges internship + cohort:
- Admin creates a **Paid Internship Program** (title, description, price, SPOC).
- Public `/internships` lists programs with Razorpay "Enroll" button.
- Student pays → receives a one-time voucher code.
- Voucher redeems for **any one** course on the platform (buyer's choice) at no further cost.
- Payment for the voucher IS the revenue; the single course enrollment it unlocks is the benefit.
- SPOC role is **read-only oversight** — tracks who completed their course, who got certificates, who got hired. No sessions, no manual attendance.

Paid courses are otherwise never bypassed — the voucher represents prepaid course access, not a free pass.

## Scope

Four tasks, implemented sequentially via subagent-driven-development:

- **T1** — Models + migration.
- **T2** — Backend routers + unified-code-resolver extension.
- **T3** — Frontend (public, admin, SPOC, buyer).
- **T4** — Course-completion + certification audit & fixes.

## 1. Data model

### Repurpose `Internship`
```
id (PK)
title, slug (unique), description, cover_image
price (Decimal, NOT NULL)
is_published (bool, default False)
spoc_user_id (FK users.id, NOT NULL)   -- MANDATORY
cohort_id (FK cohorts.id, NOT NULL, unique)  -- auto-created 1:1
created_by (FK users.id)
created_at, updated_at
```

### New `InternshipVoucher`
```
id (PK)
code (str unique indexed) -- e.g. INTR-AB12CD34
internship_id (FK internships.id)
buyer_user_id (FK users.id)
amount_paid (Decimal)
razorpay_order_id, razorpay_payment_id (str)
status ('issued' | 'redeemed', default 'issued')
redeemed_on_course_id (FK courses.id, nullable)
redeemed_at (timestamptz, nullable)
created_at (timestamptz)
```

### `Cohort` model change
- `course_id` → nullable (was NOT NULL). Internship cohorts have NULL here.
- `college_id` → nullable. Internship cohorts have NULL here.
- Alembic-free migration SQL under `backend/migrations/`.

### Drop
- `InternshipApplication` model + table.
- All application-related endpoints in `backend/app/routers/internships.py`.

## 2. Endpoints

### Admin (`/api/v1/admin/internships`)
- `POST` — body: `title, description, price, spoc_user_id, cover_image?, is_published?`. Auto-creates `Cohort` named after the title with that SPOC; `Cohort.course_id=NULL, college_id=NULL`. Stores cohort FK on the new Internship row. Single transaction.
- `GET` — list all (including unpublished) with counts: `{vouchers_issued, vouchers_redeemed}`.
- `GET /{id}` — detail.
- `PUT /{id}` — update mutable fields. Price edits do NOT retroactively affect already-issued vouchers.
- `DELETE /{id}` — blocks if `vouchers_redeemed > 0`; otherwise cascades voucher-delete + cohort-cleanup (reuses Batch 2 logic: nulls Enrollment.cohort_id, revokes spoc-source CandidateEligibility, detaches Coupon.cohort_id).
- `GET /{id}/vouchers` — paginated list: code, buyer_name, buyer_email, status, redeemed_on_course (title + id), purchased_at, redeemed_at.
- `GET /{id}/roster` — per-buyer unified view: voucher status, redeemed course info, course_progress_percentage, completion_date, certificates_earned_count, hired_by_company (from `CompanyInterest` with status='accepted' joined on buyer_user_id; nullable).

### Public
- `GET /api/v1/internships` — list published: `{id, slug, title, description, cover_image, price, spoc_name}`.
- `GET /api/v1/internships/{slug}` — same + full description.

### Student
- `POST /api/v1/internships/{id}/purchase` — auth required. Creates Razorpay order with `notes: {internship_id, buyer_user_id}`. Returns `{order_id, amount, currency, key_id}`.
- `POST /api/v1/internships/purchase/verify` — body: `razorpay_order_id, razorpay_payment_id, razorpay_signature, internship_id`. Verifies HMAC signature (constant-time), fetches order from Razorpay, matches notes, verifies `amount == internship.price * 100`. On success, in one transaction:
  1. Generate unique 12-char voucher code `INTR-` + 8 hex chars (retry on collision).
  2. Insert `InternshipVoucher(status='issued')`.
  3. Insert `CohortMembership(cohort_id=internship.cohort_id, user_id=buyer)` if not present.
  4. Commit.
  5. Email voucher code to buyer via `EmailService`.
  6. Return `{code, voucher_id}`.
- `GET /api/v1/internships/my-vouchers` — user's vouchers with status + redeemed-course info.

### SPOC
- Existing `/api/v1/cohorts/spoc/my-cohorts` — returns all cohorts they manage (college-type AND internship-type, mixed).
- `GET /api/v1/cohorts/spoc/cohorts/{id}/roster` — rewritten to show per-student: voucher code + status (if internship-cohort), redeemed course title, progress %, completion_date, certs, hired-by.
- `GET /api/v1/cohorts/spoc/cohorts/{id}/task-stats` — unchanged.
- Session endpoints retained but hidden from primary UI.

### Voucher redemption flow (wired into unified resolver)

Extend `coupon_service.resolve_checkout_code`:
- Lookup order: **InternshipVoucher → ReferralCode → Coupon**.
- If InternshipVoucher matches:
  - Validate: `status='issued'`, `buyer_user_id == current_user.id`, and not already redeemed on a different course.
  - If not the buyer → `403 "Voucher bound to another account"`.
  - Mark kind='voucher' in `ResolvedCode`, cohort = internship.cohort, `final_amount = 0`.
- `/courses/{id}/enroll` (free path already exists) and `/payments/create-order` (paid path) call resolver.
  - For PAID courses + voucher: waive payment, enroll free, atomically mark voucher `redeemed` + `redeemed_on_course_id` + `redeemed_at` using `SELECT ... FOR UPDATE`. Enrollment.cohort_id = voucher.internship.cohort_id.
  - If voucher status changed between create-order and verify (shouldn't happen in practice since we go direct-enroll, but defensive check): 409.

## 3. Frontend

### Public
- `frontend/src/pages/internships.tsx` — rewrite from "apply" cards to "Enroll for ₹X" cards. Each card → `/internships/:slug`.
- `frontend/src/pages/internship-detail.tsx` — rewrite. Hero with price + big "Enroll Now" button. On click: require login → `/internships/{id}/purchase` → open Razorpay modal → on verify: success page showing voucher code + "Browse courses" CTA.

### Student
- `frontend/src/pages/dashboard/my-vouchers.tsx` (new) — list of vouchers (issued and redeemed) with copyable codes.
- `frontend/src/components/candidate/InternshipEligibilityWidget.tsx` — keep, but add a "My Vouchers" link.
- Checkout page `checkout.tsx` — combined-code field already exists; no frontend change needed, backend resolver handles the new branch.

### Admin
- `frontend/src/pages/admin/internships.tsx` — rewrite. Table: title, price, SPOC, vouchers_issued / vouchers_redeemed, is_published. Create/edit modal with required SPOC dropdown from `/admin/spocs`. "View Vouchers" button opens modal. "View Roster" button opens roster modal.
- Navbar entry already exists (admin sidebar "Internships" submenu).

### SPOC
- `frontend/src/pages/spoc/cohort.tsx` — Roster tab becomes the **primary** view with the enhanced fields. Sessions tab moved behind an "Advanced" toggle (still functional, just de-emphasized).

## 4. Course-completion + certification audit (T4)

Read and verify:
- `backend/app/services/course_service.py` `calculate_course_progress()` — does it correctly compute progress from LessonProgress + QuizAttempt + AssignmentSubmission? Does it set `completion_date` exactly once when progress hits 100%? Handles lesson-only courses (no quizzes/assignments)?
- `backend/app/services/certificate_service.py` — `issue_certificate` + `grant_internship_eligibility_on_certificate` hook. Is `IssuedCertificate` created exactly once? Does PDF generation succeed? Is the hook called from every completion trigger (mark-lesson-complete, grade-assignment, submit-quiz, progress-save)?
- `backend/app/routers/progress.py` — after the Batch 1 refactor to `LessonProgress`, does the certificate path fire from video-watch-driven completion?

Fix any bugs found. If no bugs, confirm in the final report.

## 5. Integration with Batch 1-3 work

- **Unified resolver (Batch 1)** — extended in T2 to recognize InternshipVoucher.
- **Cohort cascade cleanup (Batch 2)** — inherited by admin internship delete.
- **Admin cohort Members modal (Batch 3)** — still works for internship-cohorts; admin can manually add students to an internship cohort (edge case but OK).
- **SPOC greenlight preservation (Batch 1)** — unaffected.
- **Razorpay payment flow (Batch 1, 4)** — reused for internship purchase.

## 6. Out of scope

- Voucher expiry. Codes never expire.
- Tiered internship pricing. Admin sets a fixed price per program.
- "Hired by company" manual override — auto-derived from `CompanyInterest.status='accepted'` only.
- Legacy `/internships/{id}/apply` flow — deleted.
- SPOC write access to student progress (read-only).
- Course-completion UI changes beyond whatever T4 audit surfaces.

## 7. Migration notes for production

- New SQL file at `backend/migrations/paid_internships_2026_04_22.sql` — dropped `internship_applications` table, added `internship_vouchers` table, altered `internships` columns, altered `cohorts` columns to nullable.
- Old internship rows without a `price` or `spoc_user_id` will need a one-time backfill or deletion. Safer: delete (there are none per prior audit).
- Email templates for voucher delivery added to `email_service.py`.
- Docker: after pull, `docker compose up -d --build backend frontend`.
