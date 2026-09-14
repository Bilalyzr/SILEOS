# Concept & Assessment Studio

## What was built

Instructor route: `/instructor/assessment-studio`. Each intervention has **Fix assessment gap**, linking directly to its course and concept. Owners and course collaborators can use the studio; students have no authoring or answer-key access. Private bank reuse is separately scoped to the instructor's own bank questions.

The studio extends the existing `QuestionBank` / `BankQuestion` storage with `studio_questions` publication metadata. It supports manual authoring, copying reusable questions, additive concept links to existing lessons/quiz questions, explicit review, publication, retirement, and outcome reporting. It requires no AI provider. Existing generated bank drafts can be copied for review if their type is supported; this release does not add a new AI generation provider.

## Coverage and authoring

Coverage concepts come from course outcomes, lesson mappings, usable quiz questions, studio drafts and enrolled learners' interventions. Lesson counts include published lessons only. Existing quiz question coverage requires published quizzes, visible feedback, availability-window eligibility, active questions, supported types, linked concepts and usable answer rows. Studio coverage includes published snapshots only. Exact normalized prompt duplicates count once.

A concept is practice-ready at two distinct practice questions and reserve-ready at two distinct reserved follow-up questions. The UI recommends three of each because planner checks normally select up to three. These thresholds describe content coverage, not instructional completeness or a learner's mastery. The reserve count means separately reserved content; learners may also receive fresh questions from the general practice pool during a delayed check.

Choose a focus concept to create a draft or add mappings. Linking adds a concept without removing prior mappings; cross-course references are rejected. Reusable imports are copies, never edits to the original bank question. Incomplete supported bank questions can be copied as drafts, but missing/invalid answers or explanations must be fixed before review.

Supported types: single choice, multiple correct options, true/false, fill in the blank, and short exact answer. Text answers are case-insensitive after trimming whitespace; no semantic grading is claimed. Multiple-choice options must be distinct and non-empty, and the selected correct indices must be valid. All published questions require explanations.

## Review and publication

`draft → reviewed → published → retired`

- Review requires an explicit note after inspecting the answer, explanation, concept and intended use.
- Editing a draft or reviewed item increments its version and resets review. Stale updates return 409 instead of overwriting a newer decision.
- A content signature binds review to the bank contents and concept/purpose. External bank changes invalidate publication until the draft is edited and reviewed again.
- Publication stores an immutable snapshot. Published content cannot be edited through this workflow; retire it and create a replacement draft. Exact duplicate available prompts are rejected.
- Retirement removes an item from new sets while existing sessions retain their original snapshot for grading and feedback.
- Every save, import and decision records an audit entry. Published/retired studio displays also read the snapshot, not mutable bank contents.
- Existing bank push-to-quiz excludes studio drafts and retired items, so that path cannot bypass studio review. Published bank content remains reusable through the existing explicit quiz-authoring operation.

## Learner integration and fresh checks

Studio publication creates no `Quiz`, `QuizQuestion`, or graded `QuizAttempt`. It supplies practice content directly to the planner's focused adaptive sessions. Positive adaptive question IDs remain legacy quiz question IDs; negative IDs identify immutable studio snapshots (`-StudioQuestion.id`). All public question responses strip keys and explanations before submission. Keys and explanations appear in submitted feedback only.

Focused planner selection now shares the studio's usable-content catalog. Normal practice excludes reserved follow-up items. Delayed checks consider both pools, ranking unseen prompts first, then preferring reserved follow-up content. Exposure includes all recorded adaptive sessions (including started sessions) and stored quiz answers. IDs and exact normalized prompts are checked, preventing simple copies from appearing fresh. Each set contains distinct prompts.

When fresh coverage runs out, the selector can reuse content and records new/reused counts. Learner feedback explicitly warns about answer familiarity. Prompt matching cannot detect all semantic variants, and an unseen prompt is not proof of independent transfer. Existing generic adaptive selection outside the planner retains its original policy.

Studio grading emits mastery evidence as `practice_question` with the existing adaptive weight override of 0.8. It does not affect graded quiz results. The planner's minimum-evidence, pass threshold, instructor-support and three-day delayed-check rules remain in force. Already-started sessions keep their contents; publish additional questions for a subsequent check rather than changing an active session.

## Outcomes

The Outcomes view shows currently enrolled learners' interventions, completed checks, number of graded questions, delayed checks with enough evidence, pass counts and paired practice-to-delayed score changes. A paired change requires sufficient evidence in both checks. Historical check counts include repeated cycles; paired scores use the intervention's current results. Unknown results remain unknown. These observations do not establish that the intervention caused improvement.

## API and persistence

All studio routes are under `/api/v1/assessment-studio` with `require_instructor` and course-editor checks where applicable:

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/courses` | Editable courses |
| GET | `/courses/{id}` | Coverage, drafts, content links and aggregate outcomes |
| GET | `/bank-questions` | Latest 500 own reusable questions |
| POST | `/courses/{id}/questions` | Create draft |
| POST | `/courses/{id}/import` | Copy owned bank content into draft |
| PUT | `/questions/{id}` | Edit with expected version |
| POST | `/questions/{id}/action` | Review, publish or retire with version and note |
| POST | `/courses/{id}/links` | Add a course-content concept mapping |

Alembic **0022**, after 0021, creates `studio_questions` with indexes and a unique bank-question reference. The frozen migration and `backend/migrations/add_assessment_studio.sql` describe equivalent schemas. Use the normal deployment migration workflow after backing up the database. Migration roundtrips were tested on SQLite and PostgreSQL DDL compiled; live PostgreSQL migration and multi-process load testing remain deployment checks.

The local preview database was backed up to `backend/studio_before_0022.sqlite`, then upgraded from 0021 to 0022 without deleting application data. This release was built and verified locally; it was not deployed to production.
