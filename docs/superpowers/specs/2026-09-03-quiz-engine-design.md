# Quiz & Assessment Engine — Authoring, Results, and Grading (spec)

**Date:** 2026-09-03 · **Branch:** `quiz-engine-upgrade` · **Status:** binding for implementation
**Trigger:** owner hit the broken authoring surface in live preview (MCQ-only, no visible
correct-answer control, no explanation field). Investigation found the damage is larger:
one of three authoring surfaces silently discards quizzes, and the explanation feature is
invisible to students on two of three student surfaces.

## 0. Findings this spec fixes (evidence)

| # | Severity | Finding | Evidence |
|---|----------|---------|----------|
| F1 | Critical | Create-Course wizard's inline quiz builder is a dead end: `quizData` lives in local state only; `addLecture` creates lessons, `updateLecture`'s backend-sync list has no quiz mapping, `createOrUpdateCourse` sends metadata only → quizzes authored in the wizard never reach the DB | `frontend/src/pages/instructor/create-course.tsx:340,415-441,1286-1520,470` |
| F2 | Critical | Inline lesson quiz renderer scores client-side against `question.correctAnswer`/`explanation`, which `GET /courses/{id}/quizzes/{qid}` strips for non-owners → students see ✗ on every question and never see correct answers/explanations | `lesson-redesigned.tsx:334-342,492-513` vs `backend/app/routers/quizzes.py:325-380` |
| F3 | Critical | Inline renderer renders inputs only for mcq/true_false/fill_in_blank; a quiz containing short_answer/essay shows no input and Submit stays disabled (`answers.length !== questions.length`) → unsubmittable dead end | `lesson-redesigned.tsx:531` |
| F4 | ~~Critical~~ **PARTLY RETRACTED (audit Part 2)** | A working instructor grading queue EXISTS: `pages/instructor/grading-queue.tsx` (routed App.tsx:692) drives merged `GET /courses/{id}/grading-queue` (gradebook.py:127) + grade + finalize. Real remaining gaps: the queue never sends the accepted `feedback` field (grading-queue.tsx:98 sends marks only), finalize creates no student notification, and the student "awaiting review" screen neither refreshes nor links anywhere. Task 11 re-scoped to wire these. | quizzes.py:1615,1694; gradebook.py:127 |
| F5 | Important | Full-page quiz results (`quiz-taking.tsx`) show only a score summary — no per-question review, correct answers, or explanations, although `GET /quiz-attempts/{id}/results` returns them | `quiz-taking.tsx:385-491` vs `quizzes.py:1534-1569` |
| F6 | Important | Builder's "Show correct answers after submission" toggle is silently dropped by create/update (no column read/written; `quiz_feedback_mode` exists but unused) | `quiz-builder.tsx:804-812`, `quizzes.py:100-111,427-433` |
| F7 | Important | `update_quiz` deletes+recreates all questions (new question_ids) → historical `quiz_attempt_answers` orphaned; delete+recreate is non-transactional with per-loop commits → a mid-loop failure leaves a gutted quiz | `quizzes.py:435-505` |
| F8 | Minor | `question_settings` double-encoded (`json.dumps` into JSON column) → `image_url` silently lost on read via the except path | `quizzes.py:127-129,458-460,350-354` |
| F9 | Minor | No server-side validation of question payloads (MCQ `correctAnswer` index unchecked; empty options accepted); wizard defaults `correctAnswer: 0` (first option always right) | `quizzes.py:117-160,449-504`, `create-course.tsx:1347-1352` |
| F10 | Minor | Two divergent student quiz UIs (`quiz-taking.tsx` all types + no review; inline renderer 3 types + review) — drift by construction | both files |

What is already GOOD and must not be regressed: server-side scoring, server-side timers with
late-submission capture, pause/resume bookkeeping, underscore-key answer stripping, owner-only
answer gating on fetch, `pending_review` state machine, idempotent results endpoint.

## 1. Goals

1. One authoring path: every quiz is created/edited in the full Quiz Builder; the wizard links
   to it instead of embedding a second builder. No quiz data may exist only in client state.
2. Every student surface shows the same post-submit review: per-question your-answer vs
   correct answer, ✓/✗, explanation, and (once graded) instructor feedback — gated by the
   quiz's feedback policy.
3. The manual-grading loop is closed end to end: instructor queue → grade with feedback →
   finalize → student sees final score + feedback; attempt leaves `pending_review`.
4. Server-side validation makes it impossible to save an unscorable question.

## 2. Non-goals (out of scope for this sub-project)

- New question types beyond `multi_select` (see §5); matching/numeric/cloze go to a follow-up.
- Question banks, per-take random-N (column exists, wiring is a follow-up), negative marking UI
  (column `minus_mark` exists; exposing it is a follow-up).
- Rich-text question prompts (needs a sanitizer decision; plain text stays).
- Changes to attempt lifecycle endpoints' contracts beyond what §4 lists.

## 3. Binding rules

- R1: **Single source of authoring.** The only UI that writes quiz questions is the Quiz
  Builder page (`/instructor|admin/courses/:courseId/quiz-builder`). The wizard's quiz
  lecture row becomes a stub that opens the builder. No component may hold quiz question
  state that outlives navigation without an API write.
- R2: **No client-side scoring anywhere.** Correctness display comes only from a server
  results payload (`/quiz-attempts/{id}/results`). A student payload must never need
  `correctAnswer`/`explanation` to render review.
- R3: **Answer secrecy unchanged.** `GET /courses/{id}/quizzes/{qid}` keeps omitting
  `correctAnswer`/`explanation` for non-owners pre-submit. Post-submit review data comes
  exclusively from the attempts results endpoint, which already gates on attempt ownership
  + submission state.
- R4: **Feedback policy is persisted and enforced server-side.** `quiz_feedback_mode`
  ∈ {`reveal_immediate` (default), `reveal_after_due`, `reveal_never`} — mapped onto the
  existing column with a migration-safe default for existing rows. The results endpoint
  filters `correct_answer`/`explanation`/`is_correct` per-question fields according to it.
  The builder toggle writes this column; `create`/`update` read it.
- R5: **Transactions.** Quiz create/update write questions+answers in ONE transaction
  (single commit at the end; rollback on any failure). No `db.commit()` inside loops.
- R6: **Question identity.** `update_quiz` updates rows in place (matching by position and
  patching fields) so `quiz_attempt_answers.question_id` references survive edits; questions
  actually removed are deleted together with their attempt answers ONLY when the quiz has
  zero attempts, otherwise removal of a question with attempts is a 409 with a clear message
  (instructor must delete the quiz or accept keeping the question). Binding numbers: a quiz
  with ≥1 `quiz_attempts` row cannot drop a question via PUT; it can add/modify questions.
- R7: **Server-side payload validation** (422 on violation, exact codes in the plan):
  - `type` ∈ {multiple_choice, true_false, short_answer, essay, fill_in_blank, multi_select}
  - multiple_choice: ≥2 non-empty options, `correctAnswer` an integer index in range
  - multi_select: ≥2 non-empty options, `correctAnswers` an array of ≥1 in-range distinct indices
  - true_false: `correctAnswer` ∈ {"true","false"}
  - fill_in_blank: non-empty `correctAnswer` string (trimmed), ≤200 chars
  - short_answer: optional `correctAnswer` (empty → manual-grade)
  - essay: no answer required; `points` 1..1000 for all types
- R8: **short_answer with empty correctAnswer becomes manual-graded** (joins
  `MANUAL_GRADE_QUESTION_TYPES`). `essay`/`open_ended` stay manual-graded.
- R9: All new endpoints/fields keep the trailing-slash rule: declare routes WITHOUT trailing
  slash; add every new prefix to `noSlashEndpoints` in `frontend/src/api/axios.ts`.
- R10: No `dangerouslySetInnerHTML` for explanations/feedback; render as plain text.

## 4. Endpoint contract changes

- `POST /courses/{course_id}/quizzes`, `PUT /courses/{course_id}/quizzes/{quiz_id}`:
  accept + persist `feedbackMode` (R4); validate per R7; behave per R5/R6.
  Response adds `{"id": ..., "feedback_mode": ...}`.
- `GET /courses/{course_id}/quizzes/{quiz_id}`: adds top-level `feedbackMode`.
- `GET /quiz-attempts/{attempt_id}/results`: per R4, when mode is `reveal_after_due` and the
  quiz has no past due (time-limit quizzes: attempt deadline; otherwise immediate), omit
  per-question `correct_answer`/`explanation` but keep `is_correct`/`achieved_mark` and
  instructor feedback text. `reveal_never` omits all three forever. `reveal_immediate`
  behaves as today. Response adds top-level `"feedback_mode"` so the UI can explain why
  answers aren't shown.
- New: none required for grading (list/grade/finalize exist). Wire, don't re-invent.
- Grading endpoint payload for feedback text stays `{"feedback": str, "achieved_mark": num}`
  as implemented; finalize recomputes totals (existing behavior, add tests).

## 5. Question types after this sub-project

`multiple_choice` (single correct), `multi_select` (NEW — checkbox, ≥1 correct; scoring:
full marks iff exact set match, else 0; no partial credit in v1 — recorded as a deferred
minor), `true_false`, `fill_in_blank`, `short_answer` (auto or manual per R8), `essay`
(manual). Attempt-answer payload shapes:
- multiple_choice: option index (int) — unchanged
- multi_select: array of option indices
- true_false: "true"|"false" — unchanged
- fill_in_blank/short_answer: string — unchanged
- essay: string — unchanged

## 6. Acceptance criteria

1. Creating a quiz entirely from the wizard path (add quiz lecture → builder → save →
   publish) yields questions, correct answers, explanations, and feedback mode in the DB.
2. A student submitting a quiz containing every supported type sees, post-submit, a
   per-question review with their answer, correctness, correct answer, and explanation
   (per feedback policy) on BOTH student surfaces.
3. An essay quiz can be submitted from both surfaces, appears in the instructor pending
   queue, is gradeable with feedback, and finalize produces the final score + student-visible
   feedback.
4. Killing the server mid-`PUT` never leaves a quiz with fewer questions than it had.
5. Editing a quiz that has attempts does not orphan attempt answers (R6 test).
6. Both full suites stay green (backend baseline 944 passed / 4 skipped; tsc 378
   pre-existing errors, zero new).
