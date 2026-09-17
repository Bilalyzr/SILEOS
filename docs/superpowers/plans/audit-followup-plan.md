# Follow-up Plan: Post-Audit Backlog + Deferred Minors

## Context
Continuation of the logic-fix branch (shipped as e920119..49507e8 on main). This
batch closes the 3 backlog tickets and the worthwhile deferred minors in one
task. Same SDD pipeline: one implementer, one task review, one pipeline deploy.

## Global Constraints
- Worktree /root/sasha-fix2, branch fix/audit-followup (from current main).
- No pushes by implementer; pytest gate: /opt/sasha-ci/venv/bin/python -m pytest -q
  fully green (43 passed/3 skipped baseline); no new tsc errors; npm run build passes.
- Preserve API shapes except where specified; no new deps; no print().

## Task 1 — Backlog + minors (single batched dispatch)
1. CERT REVIVAL GATING (backlog): admin-revoked certificates must be terminal.
   The regression branch in course_service.calculate_course_progress writes
   invalidation_reason — make it a recognizable marker (e.g.
   "course_completion_regressed") instead of free text. In
   certificate_service.issue_certificate_for_enrollment's revival branch, only
   revive when existing.invalidated_reason == that marker; admin-revoked certs
   (any other reason) keep returning (existing, False).
2. BULK ADMIN FORCE-COMPLETE (backlog): admin.py bulk update_enrollment_status
   (~1550+) force-sets completed without recalc. Make it consistent with the
   single endpoint: after setting completed, call calculate_course_progress
   (commit=True), refresh, and only report/send completion for enrollments the
   recalc confirmed (mirror the single endpoint's post-recalc semantics).
3. CONSOLIDATE DISTINCT-QUIZ LOGIC (backlog): course_service.calculate_course_progress
   and certificate_service.course_completion_percentages both reimplement
   passed-distinct-quiz counting. Extract one read-only shared helper (e.g. in
   course_service or a small shared module) used by both; behavior unchanged.
4. CouponUpdate enum validator (minor): add CouponCreate's discount_type enum
   validation to CouponUpdate.
5. Stored-type cross-check on coupon update (minor): in PUT /coupons/{id}, when
   discount_value is provided without discount_type, validate the value against
   the STORED coupon.discount_type (percentage ≤100) and 422 on violation.
6. auth.py naive last_login writes (minor): convert the 3 utcnow writes
   (auth.py ~159, ~1253, ~1499) to datetime.now(timezone.utc).
7. Float answer truncation (minor): quizzes.py answer cast — reject non-integer
   numerics ("1.9") as wrong instead of truncating (e.g. try int(); on
   ValueError from float-string, treat as wrong).
Tests: extend backend/tests/ — (a) admin-revoked cert NOT revived via
issue_certificate_for_enrollment, regression-invalidated cert IS revived;
(b) bulk force-complete respects recalc (below-100% student ends enrolled, no
completion email); (c) PUT coupon 500 on stored percentage type → 422;
(d) "1.9" answer scores wrong.

## Post-task (controller)
Task review → fix loop if needed → single push to main → pipeline → verify.
