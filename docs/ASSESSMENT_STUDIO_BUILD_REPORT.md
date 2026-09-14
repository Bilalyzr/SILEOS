# Concept & Assessment Studio build report — 2026-09-06

Completed locally: course concept coverage, reusable question drafts, review and publication, fresh delayed practice and intervention outcome reporting. This is the studio enhancement authorized after the planner release. Recording transcription, broader production hardening and Flutter work remain separate roadmap items.

## Delivered

- **Assessment Studio** instructor page with editable-course selection, concept deep links, Coverage / Questions / Outcomes views, loading/error handling and question review dialogs.
- **Fix assessment gap** from the intervention queue to its exact course and concept.
- Coverage based on published, available, usable questions; hidden feedback, retired questions, invalid answer keys and duplicate prompts do not inflate readiness. Missing lesson links remain visible.
- Five supported authoring types, difficulty, explanations and practice/follow-up purpose. Existing bank content can be copied into drafts, including supported incomplete questions that must be repaired before review.
- Versioned review and explicit publication. Editing resets review; signatures detect source changes. Published snapshots are immutable, retirement preserves existing session grading, and older bank push-to-quiz cannot bypass the review requirement.
- Focused planner checks consume studio practice directly without creating graded curriculum quizzes. Reserved questions stay out of immediate checks. Delayed checks prefer unseen content and disclose repetition.
- Learner explanations after grading; instructor outcomes with check/question counts, evidence-qualified delayed results and paired score changes. No causal improvement claim or automatic mastery guarantee.
- Alembic 0022 and PostgreSQL schema parity SQL, full API/behaviour documentation and architecture handover.

Feature guide: [ASSESSMENT_STUDIO.md](ASSESSMENT_STUDIO.md).

## Validation

| Check | Result |
| --- | --- |
| Full backend regression suite | 1,592 passed, 4 skipped; 721.56 seconds |
| Final focused studio/planner/signals/retention suite | 65 passed; 30.90 seconds |
| Full frontend regression suite | 333 passed across 49 files, including 4 new studio UI tests |
| Scoped frontend ESLint | Passed, zero warnings |
| Frontend production build | Passed; existing bundle-size warnings |
| TypeScript | 393 existing repository errors; no errors in the studio or changed planner pages/API |
| New backend modules/migration/tests pyflakes | Passed, zero findings |
| Live smoke script | 27/27 passed against workspace backend 8012 |
| Live studio permissions | Student 403; course instructor 200 |
| SQLite migration | Idempotent upgrade / downgrade / re-upgrade and model-column parity tests passed |
| PostgreSQL schema | DDL compiled; no live PostgreSQL migration or multi-process load test |
| Patch whitespace | Passed with existing CRLF convention acknowledged |

The full backend run began before the final incomplete-bank import refinement, option normalization, and six added grading/import/publication-boundary cases. The final 65-test focused run verified that final code. No new TypeScript error was left behind: the studio initially used replaceAll, which was changed to a compatible regular-expression replacement. Repository-wide lint retains the previously verified baseline of 26 existing hook warnings; this release's scoped lint passed.

## Live instructor-to-learner walkthrough

1. Opened course 5 with focus `html basics`; the studio correctly showed no usable practice and no follow-up reserve.
2. Created a paragraph-element question in the browser, checked its answer/explanation, approved review and explicitly published it. Draft/reviewed states did not count as available practice.
3. Added two additional practice items and three reserved delayed-check items through the authenticated local studio API, each with explicit review and publication. Coverage became **3 practice / 3 reserved questions**. The lesson gap remained visible because no unrelated lesson was falsely mapped.
4. Requested a fresh HTML check on the local demo intervention. Moved the demo organelles check to tomorrow using the learner UI, making room within the unchanged 30-minute daily budget.
5. The learner received exactly the three published practice items, without pre-submit keys. Submitted correct answers in the browser: **100%**, with answer explanations, an unseen-content message and a retention check scheduled three days later.
6. The instructor Outcomes view then showed **1 completed check / 3 graded questions**, zero completed delayed checks and **Not enough evidence** for paired change. No live calendar fast-forward was used; delayed resolution and reserve selection were tested in isolated databases.

Only local demo content/planner state was changed by this walkthrough. No production data or external messages were involved.

## Preview, migration and review

- Instructor: http://127.0.0.1:3002/instructor/assessment-studio?course_id=5&concept=html%20basics
- Learner: http://localhost:3002/my-plan
- Backend: http://127.0.0.1:8012

The local SQLite database was backed up to `backend/studio_before_0022.sqlite`, upgraded from 0021 to 0022, and the verified workspace backend restarted with the final code. Other previews on 3001/8011 were left running.

Local branch `astra/learning-signals`, based on PR #3 head `25db528fa3f91b5f63173aeef3c2e87f1e94633d`. Previous cycle/planner changes remain intact. No commit, push or production deployment was performed. Preserve the archive's unrelated pre-existing missing WordPress/certificate files; do not stage those as deletions.

Production deployment still needs its normal backup, PostgreSQL migration and concurrency/load validation. Existing repository lint/type debt remains. No AI question-generation provider was added; manual authoring and reusable bank drafts work without a key. Exact prompt exposure matching is not semantic similarity detection, and the outcome aggregates are observational.

Logs: `backend/studio-{full-tests,tests,smoke,migration,pyflakes}.log` and `frontend/studio-{build,lint,types,ui-tests,vitest}.log`. Defaults are recorded under OWNER_DECISIONS 35; architecture ledger section K describes the integration.
