# Platform Audit Part 2 — CRUD / management completeness (2026-09-03)

**Trigger:** owner review of Part 1 ("memberships and bundles have no edit/delete — you missed
it"). Owner is right: Part 1 checked whether existing pipes WORK; this part checks whether the
management surfaces are COMPLETE. Method: three parallel deep-dives building CRUD matrices for
every admin page (28 pages), every instructor/SPOC/company surface, and the student/public
lifecycle, each verified against the backend routers with file:line evidence. Spot-verified
independently: memberships + bundles (owner's example), and the grading-queue correction below.

**Correction to Part 1 (integrity):** Part 1 F4 ("manual grading has no UI, essays stuck
forever") was WRONG. A functional instructor grading queue exists:
`frontend/src/pages/instructor/grading-queue.tsx` (routed App.tsx:692, linked from courses/
gradebook pages) driving the merged `GET /courses/{id}/grading-queue` (gradebook.py:127) +
`POST /quiz-attempts/{id}/answers/{aid}/grade` (quizzes.py:1615) + `/finalize` (quizzes.py:1694).
What ACTUALLY remains: the page never sends the `feedback` field the grade endpoint accepts
(grading-queue.tsx:98 sends `{achieved_mark}` only — students get marks, never written
feedback), finalize creates no student notification, and the student's "awaiting review" screen
neither refreshes nor links anywhere. Quiz-engine plan Task 11 re-scoped accordingly (wire, not
build). Part 1 table F4 row corrected in place.

---

## 0. Owner's examples, verified

- **Memberships** (`/admin/memberships`): list/create/edit-plan/deactivate-plan exist
  (admin.py:130,163,172,196). MISSING: plan DELETE (no route either side), and **no admin
  action to cancel/suspend a member's subscription** (memberships.py `/cancel`:167 is
  self-service only) — support cannot intervene on refunds/chargebacks.
- **Bundles** (`/admin/bundles`): list/create/edit (admin.py:254,292,301). MISSING: DELETE —
  no route, no button, no archive concept beyond the edit modal.

## 1. Highest-impact gaps (High — operator or student blocked)

### Admin
| # | Gap | Evidence |
|---|-----|----------|
| A-H1 | **Orders page is read-only and there is NO refund anywhere**: no admin order status change, no refund route in the entire backend (`OrderStatus.REFUNDED` defined, nothing sets it), no resend receipt. Refund/correction workflow = raw DB edits. | admin.py:2725 (GET only); orders.py (POST /, GET /me); payments.py:224,603,794 |
| A-H2 | **Blog comment moderation missing everywhere** — no admin view/approve/delete of comments (spam vector on a public site). | blog.py:542,568 (GET/POST only); admin.py:4841-5030 (no comment routes) |
| A-H3 | **Admin cannot set/reset any user's password** (students, instructors, SPOCs at creation only). Workaround: impersonation. | admin.py (no set-password route); auth.py:847,877 self-service only; admin.py:1239-1241 SPOC PUT fields |
| A-H4 | **Admin cannot grant a course enrollment** (no create-enrollment route); workaround: impersonate → self-enroll. | admin.py:1859,1905,2019 list/status/bulk only |
| A-H5 | **Certificates page cannot revoke/reissue** — backend routes exist (`/admin/{id}/revoke`, `/admin/enrollments/{id}/issue`) but the only buttons live in the Internships roster. | certificates.tsx:307-328 (verify/download only); internships.tsx:316,336 |

### Instructor
| # | Gap | Evidence |
|---|-----|----------|
| I-H1 | **Cannot edit or cancel/delete a scheduled live class** — backend PATCH + DELETE exist and are fully implemented; the UI has zero buttons for either. | live_classes.py:238,294; api/liveClasses.ts:165,168 unused; live-classes.tsx:155-186 |
| I-H2 | **Instructor payouts/withdrawals missing everywhere** — `Withdrawal` model exists (models/payment.py:219-236), zero request endpoint, zero UI, zero nav. Instructors can see earnings totals but can never be paid out through the product. | models/payment.py:219-236; nav-configs.tsx:31-47 |
| I-H3 | **Cannot remove a student from a course** (no DELETE-enrollment route anywhere; admin can only set status). | courses.py:1905 (POST enroll only) |
| I-H4 | **H5P content cannot be deleted or replaced from the UI** — ref-safe DELETE endpoint exists, unused; no H5P management page at all (upload-or-nothing). | h5p.py:372 (409-guarded); api/h5p.ts:97 unused |
| I-H5 | **Cannot unpublish own course** — backend allows the owner (courses.py:934), `unpublishCourse` client fn never called. | api/course.ts:324; courses.tsx |
| I-H6 | **Gradebook is read-only** — no cell override/edit route or UI (instructors cannot correct an auto-graded score short of DB). | gradebook.py:127,147,158 |

### Student
| # | Gap | Evidence |
|---|-----|----------|
| S-H1 | **The wishlist heart is a stub** — `// TODO: Implement wishlist logic` (local toggle only); `POST /wishlist/` has zero UI callers. The entire wishlist feature is unreachable from the UI that shows it. | course-detail.tsx:319-321; wishlist.py:45 |
| S-H2 | **The cart can never be populated** — the only `addToCart` caller is wishlist's "move to cart"; no Add-to-cart button exists anywhere; cart is localStorage-only. | wishlist.tsx:36 (only caller); CartContext.tsx:51-70 |
| S-H3 | **Paid multi-course cart checkout is a broken promise** — UI offers "Complete Order"; backend hard-402s "Cart checkout cannot process paid orders yet". | checkout.tsx:217-225; orders.py:157-164 |
| S-H4 | **No student change-password UI** — endpoint + client wrapper exist; only the ADMIN settings page calls them. | auth.py:939; api/auth.ts:111; admin/settings.tsx:144 |
| S-H5 | **"Watch recording" dead-ends** — the button renders on ended classes but links to the JOIN page, which has no recording handling; the playback endpoint is never fetched by any UI. | live-classes.tsx:80-88; live_class_recordings.py:101 |
| S-H6 | **Account deletion is stubbed client-side** (`toast: "disabled in this preview"`) with no self-serve backend route. | settings.tsx:156-159 |

### Company
| # | Gap | Evidence |
|---|-----|----------|
| C-H1 | **Company "Save notes" on a student is a no-op** — UI sends `{notes}`; backend handler branch is a literal `pass` placeholder. Silent data loss. | company dashboard.tsx:663; company_dashboard.py:421-423 |
| C-H2 | **Company cannot close or edit an internship** — status field advertised in the schema, never read by the handler; no UI. | schemas/company_dashboard.py:77-81 vs company_dashboard.py:414-423 |
| C-H3 | **Seat-pool revoke missing everywhere** — seats can be assigned, never unassigned. | company_billing.py (assign only) |

## 2. Medium gaps (workaround exists, or dormant backend capability)

- **M-1.** Companies cannot be suspended/deactivated after approval (one-way approval;
  companies.py:137-257).
- **M-2.** Admin enrollments page: bulk-update route exists (admin.py:2019), zero UI callers.
- **M-3.** Certificate revoke/issue not on the certificates page (see A-H5); templates tab in
  /admin/manage is a read-only duplicate of the designer.
- **M-4.** `/admin/blogs/categories` fetch has no backend route — category filter dropdown
  silently fails (api/blog.ts:80, blogs.tsx:46).
- **M-5.** SPOC: session edit has no UI (PUT exists, cohorts.py:770, client fn unused);
  session-attendance export missing everywhere.
- **M-6.** Company profile edit missing (PUT /companies/me exists, companies.py:705, unused).
- **M-7.** Company candidate browse / express-interest has no mounted page (companies.py:726,838;
  InterestModal.tsx unmounted); candidate inbox absent from company nav.
- **M-8.** Student: no invoice/receipt download for individual purchases (email only;
  company invoice flows are separate); no cancel-abandoned-order; membership payment-method
  update / dunning self-service missing (grace banner is a dead end).
- **M-9.** Student: voluntary course leave/withdraw missing everywhere (admin-only status
  change); free re-enroll on a cancelled enrollment returns "already enrolled" without
  reactivating (courses.py:1952-1966).
- **M-10.** Student: change email missing everywhere (schema has no email field);
  blog comment edit/delete (own comment) missing everywhere.
- **M-11.** Live-class "Add to calendar" (.ics) endpoint + client fn exist, no button
  (live_classes.py:326; api/liveClasses.ts:179).
- **M-12.** Newsletter subscribe: backend route live (blog.py:721), Home footer onSubmit is
  `e.preventDefault()` and layout footer is a TODO.
- **M-13.** Recording visibility gating (the sub-project-4 "attendance-gated replays" idea):
  currently no endpoint and no UI at all.
- **M-14.** Categories page is a hardcoded array; backend category APIs unused by it
  (categories.tsx:17 vs courses.py:2340,2356).
- **M-15.** Instructor-profile public page falls back to an admin-only endpoint for some
  lookups (instructor-profile.tsx:95 → 403 public).
- **M-16.** Certificates: student "regenerate" exists in backend + client, no UI entry
  (certificates.py:313).

## 3. Low / cleanup

- Naive (unguarded) deletes on: categories (admin.py:2393), tags (:2491), blog posts (:4972 —
  comments orphaned), lessons (:3694), cohorts/colleges (cohorts.py:184,314 — college delete
  returns raw FK 400), coupons (coupons.py:383). Guarded (good): users, SPOCs, internships,
  quizzes, courses(force), designer templates, invoices.
- Coupon usage-count cannot be reset (limit-raise only). Blog-templates admin page is a
  "Coming soon" stub on a real route. Individual notification mark-read unused; no
  notifications center page. Dead client fns now totaling ~20: unpublishCourse,
  updateLiveClass, deleteLiveClass, deleteH5PContent, updateCompany, browseCandidates,
  updateSession, bulk-update, fetchCalendarIcs, regenerateCertificate, deleteWishlistItem,
  getBlogTemplates(404)… (full E-lists in Part 1 §E + matrices above).
- Assignment delete lacks a submissions guard (hard delete, assignments.py:485-489) — the 409
  pattern from games/h5p should be copied.

## 4. Verified complete (full CRUD round trips exist and are wired)

Games (instructor), blog posts (author), assignments (instructor, incl. grade/return),
live-class attendance reports (CSV + recompute), company managers/announcements/requests/
attendance/work-logs/invoices, SPOC cohorts-roster/eligibility/blog, certificates
download/share/public-verify, membership subscribe/cancel/status (cancel lives on the
dashboard card), single-course paid + free/voucher checkout + coupons, admin
companies/messages/settings/course-reviews/hall-of-fame/internships/cohorts/spocs tables,
export-import panel surfaces.

## 5. Sequencing update (supersedes Part 1 §5 item ordering where they overlap)

1. **Quiz-engine branch** (in flight) — absorb: grading-queue feedback field + finalize
   notification + results auto-refresh (replaces old Task 11 body), A1 duration rule.
2. **"Wire-the-backend" fix wave** (small, mostly frontend buttons for existing routes):
   live-class edit/cancel (I-H1), unpublish course (I-H5), H5P delete/management (I-H4),
   certificate revoke/issue buttons on /admin/certificates (A-H5), wishlist heart (S-H1),
   change-password in student settings (S-H4), newsletter + ICS wiring (M-11/M-12),
   company notes handler (C-H1 — 1-line backend fix), internship close (C-H2),
   blog categories route (M-4).
3. **Money-adjacent branch (strongest review):** refunds + order status marking (A-H1),
   instructor withdrawal requests (I-H2), seat-pool revoke (C-H3), sale-price fix (Part 1 A5).
4. **Rulings needed from owner:** delete vs archive for memberships/bundles (recommend:
   archive/is_active + block-delete-when-active-subscribers, add admin subscription-cancel);
   paid cart checkout (build server-priced cart vs hide the CTA — recommend hide + "buy
   courses individually" until server cart exists); account deletion (GDPR scope);
   comment moderation build vs third-party; admin password-reset policy (temp-password +
   force-change vs email link).
