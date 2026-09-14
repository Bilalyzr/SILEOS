# Personal learning planner and interventions

Implemented locally on 2026-09-06. The planner uses persisted course evidence and transparent rules; it needs no AI provider or API key.

## Learner workflow

Open **My Learning Plan** (`/my-plan`). Choose an enrolled course, describe a goal, set a target date, daily minutes, and time zone. There is one editable goal per learner per course. Budgets are per course; the page displays their combined total when there are multiple goals.

The plan schedules published lessons, reviews, focused understanding checks and delayed retention checks. A review covers the corresponding curriculum study block once. Completed study blocks consume that day's budget; snoozing moves a task no earlier than tomorrow. A long lesson receives a dedicated block with an explicit warning. An infeasible deadline is reported rather than hiding workload. Paused goals preserve history and disable task actions.

**Mark studied** records a planning action only. It does not award lesson completion, grades or mastery. Actual course lesson completion synchronizes into the plan on refresh.

## Evidence and intervention rules

- Use course-specific assessments from the last 60 days, averaging the latest five records per concept. Stored quiz question answers take precedence over an aggregate quiz score for that concept. Pending manual answers and quizzes with `reveal_never` feedback are excluded from diagnosis.
- An assessment average below 60% suggests a check. Behavioural struggle also suggests a diagnostic check; it never establishes a misconception by itself. Reasons and baseline uncertainty are visible.
- Review a linked published lesson, including a known weak prerequisite where available, then practise with up to three published, auto-gradable, concept-linked questions. Hidden-feedback quizzes are excluded from practice selection.
- At least two linked questions and 75% correct are required to meet the check target. A successful immediate check schedules a follow-up no earlier than three local calendar days later. A successful delayed check closes the intervention as evidence of retention, without claiming permanent mastery.
- Failed checks or insufficient question coverage require instructor support. No questions produces an actionable error and preserves the task so it can be retried after content is added.
- Practice uses the existing adaptive evidence path (including its mastery weighting); it never changes a graded quiz result. Single-choice questions cannot be passed by submitting every option.
- Start requests resume the same persisted session. Repeated submissions reuse saved grading outcomes and do not create duplicate follow-ups. PostgreSQL row locks and uniqueness constraints protect updates; conflicts return a refresh-and-retry response.
- Fresh below-threshold assessment evidence can reopen a resolved intervention. Instructor dismissals remain closed. Review and reopening history is retained.

The plan refreshes when saved or manually replanned, after canonical quiz submit/manual finalize, and during the existing six-hour retention pass. Other evidence enters on the next refresh. The goal title is a learner description; concept targeting comes from course evidence, not automatic interpretation of that text.

## Instructor workflow

Open **Interventions** (`/instructor/interventions`). Owners and collaborators see only their editable courses; administrators can see all courses. Revoked enrollments are excluded. The queue prioritizes support-needed cases before limiting to 300 rows, and labels counts as belonging to that queue.

Review baseline, practice and delayed-check evidence. Add a note to request another understanding check or close the intervention. Closing does not override mastery. Paused goals cannot be reviewed until resumed. Notes are visible to the learner; history is stored in intervention evidence.

## API

All routes use `/api/v1/planner` and require authentication.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/me` | Own enrolled courses and goals |
| POST | `/goals` | Create/update one goal for a course |
| POST | `/goals/{id}/refresh` | Rebuild the schedule from current evidence |
| POST | `/tasks/{id}/action` | Mark studied or snooze |
| POST | `/tasks/{id}/start` | Start/resume a focused check |
| POST | `/tasks/{id}/submit` | Grade and update intervention state |
| GET | `/instructor/interventions` | Course-scoped support queue |
| POST | `/instructor/interventions/{id}/review` | Instructor note and decision |

## Data and deployment

`learning_goals`, `learning_interventions`, and `learning_plan_tasks` are registered SQLAlchemy models. Alembic revision **0021**, after 0020, creates the tables and indexes. The migration freezes its schema independently of future model edits and is safe when development startup has already created the tables. Back up the database, then run `alembic upgrade head` from `backend` using the deployment's normal environment. `backend/migrations/add_learning_planner.sql` is the PostgreSQL schema equivalent for installations using manually managed migrations; do not apply both workflows independently without reconciling Alembic history.

The local SQLite preview was backed up to `backend/planner_before_0021.sqlite`. Its version table contained both 0006c and its ancestor 0005. After confirming that relationship, only the redundant 0005 version marker was removed, allowing guarded migrations through 0021. No application rows were deleted. Do not repeat this repair blindly on another environment.

## Validation limits

SQLite lifecycle, migration roundtrip, access controls, local calendar boundaries, budget handling, hidden feedback, quiz-triggered replanning, missing questions, repeated submissions, delayed follow-up and instructor decisions are covered by regression tests. PostgreSQL DDL compiles; a live PostgreSQL migration and multi-process concurrency/load test were not run. Daily minute estimates use lesson metadata, with fallback estimates. The delayed check can reuse questions from a small concept bank, so it is not proof of independent transfer or permanent mastery. Mobile planner UI, external notifications, cross-course optimization, question generation and production deployment are outside this release.
