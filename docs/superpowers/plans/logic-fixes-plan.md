# Logic-Fix Plan: LMS Evaluation-Integrity & Correctness (25 audit findings)

## Context
A full logic audit found 25 verified issues. This plan fixes all of them in three
code tasks (backend integrity → frontend → backend cleanup), each landing as one
commit on branch `fix/logic-audit`, later pushed to main batch-by-batch through
the existing CI/CD pipeline (pytest + blue-green deploy). A production data
cleanup (resetting submissions fabricated by the old bypass) runs as a
controller-executed step after batch 1 deploys — implementers never touch the
production database.

## Global Constraints
- All changes on branch `fix/logic-audit` (worktree at /root/sasha-fix). NO
  pushes, NO pipeline triggers, NO production DB/docker operations by implementers.
- Test gate: `cd /root/sasha-fix/backend && /opt/sasha-ci/venv/bin/python -m pytest -q`
  must pass (existing 30 tests + new ones) after every task.
- `cd /root/sasha-fix/frontend && npx tsc --noEmit` may report PRE-EXISTING
  errors only — no new ones; `npm run build` must succeed (vite build is the gate).
- Preserve existing public API response shapes except where a task explicitly
  changes them. No new dependencies. Match surrounding code style.
- Tests use the existing `backend/tests/conftest.py` factories (`make_user`,
  `auth_headers`, per-test SQLite). New test files follow `test_courses_mobile.py`.
- Commits: conventional style, one per task, authored in the worktree.

## Task 1 — Backend evaluation integrity (the reported bug class)
1. `backend/app/routers/courses.py` assignment branch of `mark_lesson_complete`
   (~lines 1408-1440): stop fabricating/force-grading submissions. New behavior:
   - no submission → 403 "Submit the assignment first — it is graded by your instructor."
   - submission `status != "graded"` → 403 "Awaiting instructor grading."
   - submission graded → 200 no-op (progress math already counts it).
   Remove the debug prints in this endpoint (~lines 1280-1519).
2. `backend/app/services/course_service.py` (~315-364): `completed_quizzes`
   counts DISTINCT passed quiz ids (set of quiz_id with a passing attempt), not
   attempts; clamp `overall_progress` to `min(100, ...)`.
3. `backend/app/routers/quizzes.py` `submit_quiz` (~460): enforce
   `quiz_max_attempts_allowed` exactly like `start_quiz_attempt` (~730-740):
   count prior `attempt_ended` rows for this user+quiz+course; 0 = unlimited;
   at limit → 403 "Maximum attempts reached".
4. `backend/app/services/certificate_service.py` `issue_certificate_for_enrollment`
   (~567-578): populate `quiz_completion_percentage` and
   `assignment_completion_percentage` (completed/total*100, 0 when total==0);
   replace `enrollment.course_progress_percentage or 100` with an explicit
   `is not None` fallback of 100.
5. `backend/app/schemas/coupon.py` `CouponUpdate` + `backend/app/services/coupon_service.py`:
   `CouponUpdate` gains optional `discount_type` and the same ≤100 percentage
   cross-validator as `CouponCreate`; `validate_and_compute` clamps percentage
   discounts to `min(100, discount_value)` before math. `PUT /coupons/{id}` must
   pass discount_type through when provided.
6. New tests `backend/tests/test_evaluation_gates.py`:
   - assignment gate: 403 no-submission, 403 ungraded-submitted, 200 graded,
     and NO submission row created/modified by the endpoint (count before/after)
   - progress: two passing attempts on one quiz → completed_quizzes == 1,
     course reaches completion, stored percentage ≤ 100
   - submit beyond max_attempts (limit 1) → 403 on second submit
   - CouponUpdate percentage 500 → ValidationError

## Task 2 — Frontend criticals & highs
1. `frontend/src/pages/lesson-redesigned.tsx:1004` — `is_completed: currentLesson.is_completed || false`.
2. Same file `:1607-1630` — Mark-as-Complete disabled for `lesson.type !== 'lesson'`
   (quiz AND assignment); sidebar instance (`:1750`) gated behind `!isInteractive`.
3. `frontend/src/App.tsx:687-721` — wrap `/admin/manage`, `/admin/courses/create`,
   `/admin/courses/:id/edit` in `<ProtectedRoute requiredRole="admin">` copying
   the pattern used at `:702` (`/admin/courses/:courseId/quiz-builder`).
4. `frontend/src/pages/checkout.tsx:84` — cart mode uses `getFinalTotal()` from
   CartContext (`isDirectCheckout ? basePrice - directCouponDiscount : getFinalTotal()`);
   pay-button amount reflects the corrected total.
5. `frontend/src/pages/quiz.tsx:205` — retake gate uses attempts-used, not
   `user_id`. The page can fetch `/courses/{id}/quizzes/{id}/attempts-count`
   (backend `get_quiz_attempts_count` returns `attempts_used`/`max_attempts`/`unlimited`);
   wire it (or an equivalent existing payload field) so failed students with
   attempts remaining see the retake button.
6. `frontend/src/store/quiz.ts` — timer interval routes through `setTimeRemaining`
   (auto-submit at 0 actually fires); `startQuiz` clears stale
   `quizResults`/`currentQuiz` state so quiz B never renders quiz A.
7. `frontend/src/pages/lesson-redesigned.tsx:1132` — strip
   `^(lesson|quiz|assignment)-` prefix before `Number(lessonId)` for
   `recordLessonView`.
8. Standardize progress field on `overall_progress` (the actual backend key):
   `frontend/src/pages/course-detail.tsx:193/196`, `frontend/src/api/course.ts:51`.
9. AssignmentRenderer (`lesson-redesigned.tsx:530-541`) — `submitting` in-flight
   guard; upload selected files the same way as `assignment-submission.tsx:151`
   (uploadDocument) instead of hardcoded `files: []`.
10. `frontend/src/pages/quiz-taking.tsx:108-116` — expiry auto-submit moves out
    of the state updater (call in the interval callback when `timeRemaining === 1`),
    `submittedRef` single-shot guard, no `window.confirm` when submitting due
    to timeout.
11. `frontend/src/api/axios.ts:350` — on 200 with `{success:false}` body, throw
    `new Error(body.message || 'Request failed')`.
Gate: `npm run build` succeeds; `npx tsc --noEmit` adds no NEW errors.

## Task 3 — Backend correctness & hygiene
1. `backend/app/routers/certificates.py` — delete the first duplicate
   `GET /{certificate_id}` handler (~1314-1332, the one with no return); keep
   the complete one (~1378).
2. `backend/app/routers/quizzes.py:533` — cast answer index safely
   (`int(user_answer)` in try/except; non-numeric → scored wrong, not 500).
3. `backend/app/routers/admin.py` (~1443-1500) — after `calculate_course_progress`,
   re-read the enrollment; only send the completion email and report completed
   when the recalc did not revert it; otherwise return the actual final status.
4. `backend/app/routers/coupons.py` `/validate` (~496) — `(coupon.per_user_limit or 1)`
   and delegate math to `CouponService.validate_and_compute` so validate == apply.
5. `backend/app/routers/checkout.py:45` — remove the per-email `is_free_user` branch.
6. `backend/app/routers/courses.py` `GET /{course_id}/progress` (~1964) — no
   writes: call `calculate_course_progress` with `commit=False` (add the kwarg
   to the service; default True preserves other callers). In the service's
   regression branch, when completion is revoked also invalidate any issued
   certificate for that enrollment (`is_valid=False`, `invalidation_reason`).
7. Replace PII/hot-path `print()`s with module `logging` in `backend/app/routers/auth.py`
   (token payloads/emails) and remove remaining debug prints in `quizzes.py`
   submit path. Other prints left as-is.
8. `datetime.utcnow()` → `datetime.now(timezone.utc)` in timestamp WRITES in
   `quizzes.py`, `courses.py` (lesson completion), `assignments.py`.
9. Delete `backend/app/routers/auth.py.bak` and `backend/app/routers/courses.py.bak`.
10. Tests: string-answer submit (no 500, scored as wrong), NULL `per_user_limit`
    validate returns 200, coupon validate/apply parity assertions.

## Post-SDD (controller, not implementers)
- Final whole-branch review, then push batch commits to main sequentially
  (batch 1 → pipeline → verify; batch 2; batch 3), then production data cleanup
  (reset fabricated 'Manually marked as complete' graded submissions with
  `graded_by IS NULL` + `grade == total_points` back to `submitted`; recompute
  affected enrollments) with a fresh safety backup.
