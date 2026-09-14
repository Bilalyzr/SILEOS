# Astra cycle 1 build report — 2026-09-06

## Remaining failures and limits

- Repository lint fails its zero-warning gate: 0 errors, 26 pre-existing hook warnings.
- Repository TypeScript check reports 393 existing errors; neither changed frontend file appears in that output.
- Pyflakes reports 323 existing findings across app; comparison against PR #3 shows zero new findings in changed backend files.
- Automatic transcription is pending the owner's provider choice. Cycles 2–6 have not been implemented in this build.
- No production deployment, Git commit, push, or PR creation was performed.

## Implemented

1. Course-editor-only course hotspots: top ten positive-score segments, timeline concept attribution, early exits per lesson, and distinct struggling learners per concept.
2. Hot-segment notifications through the existing retention loop, with seven-day cooldown per editor/lesson/segment, three-learner minimum and 3x median threshold.
3. Course-scoped learner struggle context in the tutor system prompt. The graded-item guard still precedes the missing-key 503.
4. Quiz submit/results/finalize weak concepts from stored wrong answers; unfinished manual answers and reveal_never learner feedback stay protected. Adaptive build accepts repeated focus parameters and doubles focused weights.
5. Instructor Insights Hotspots tab with course selection, loading, retry, empty-state and notification deep-link handling. This is the only changed page mount.

## Validation

| Check | Result |
|---|---|
| Full backend suite | 1547 passed, 4 skipped, 672.12 s |
| Final focused suite | 23 passed, including three boundary cases added after full-suite collection |
| Live smoke script | 27/27 passed on port 8012 |
| Frontend production build | Passed; existing large-chunk/asset warnings |
| Repository lint | 0 errors / 26 baseline warnings; strict gate fails |
| TypeScript | 393 baseline errors; zero in changed frontend files |
| New pyflakes findings vs PR head | 0 |
| Browser | Verified course 5 lesson 2, 3:20–3:30 first; switch to Python course shows empty state, then switch back restores table |

The full suite ran before the final tutor threshold adjustment (using all profile concepts at struggle >=60) and three added boundary tests. The subsequent focused run passed on the final logic, including tutor guard/503, hotspot isolation/window, manual finalize, and per-segment cooldown tests.

The unchanged demo data has only one learner, so no alert is expected there. Isolated seeded tests verified persisted hot_segment rows for the owner and collaborator, suppression on repeat, separate segment identity, and expiry of both signals and notification cooldowns.

## Base and review

User-supplied PR: https://github.com/SashaInfinity/Sasha_lms/pull/3
Head: 25db528fa3f91b5f63173aeef3c2e87f1e94633d, branch fable-5.1-handover-2026-09-06.
The extracted workspace initially lacked Git metadata. Tracking was restored without checkout or overwriting files, on local branch astra/learning-signals. Source matches that head apart from this build. The extracted archive omits tracked WordPress files, certificate previews and a few .gitkeep files; these pre-existing missing files are outside this patch and must not be staged as deletions.

Preview: http://127.0.0.1:3002/instructor/insights?course_id=5&tab=hotspots
Backend: http://127.0.0.1:8012
Existing previews on 3001/8011 were left running.

Decisions and implementation traps are appended to CLAUDE.md, OWNER_DECISIONS.md (32), and architecture ledger section I. No database migrations were needed. Full logs are local backend/astra-*.log and frontend/astra-*.log.
