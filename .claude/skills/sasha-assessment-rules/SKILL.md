---
name: sasha-assessment-rules
description: Quizzes, grading, and gradebook work
---

Blueprint 3.4 + the 2026-09-03 quiz-engine spec. Load for any quiz or grade change.

- Server-side scoring is the authority; the client never grades (the F2 lesson: students saw wrong marks because the client scored against stripped answers).
- _validate_questions runs BEFORE any write — nothing persists if any question is invalid; quiz create is one transaction.
- Question identity is preserved on update (in-place patch; never delete+recreate — historical attempt answers reference question_id).
- MANUAL_GRADE types (essay/open_ended/short_answer-blank) flow through pending_review; everything else auto-scores.
- Owner-only answer gating on fetch: correct answers stripped for non-owners.
- Server-side timers, late-submission capture and pause/resume already exist — extend, do not rebuild.
- Grading queue endpoints already merge pending submissions; extend, do not fork.
- Question banks (SILEOS pack): pulling a bank question into a quiz SNAPSHOTS it; editing a bank question never rewrites live quizzes.
- Test grades against hand-calculated fixtures, to the decimal (mastery test: 0.6*50 + 0.4*100 == 70.0).
