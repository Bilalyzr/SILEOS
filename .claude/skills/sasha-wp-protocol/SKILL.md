---
name: sasha-wp-protocol
description: Executing a work package or feature build end-to-end
---

How to execute any scoped build. Load at the start of every feature.

1. Read dependencies and VERIFY them: run their tests, do not assume.
2. Produce a plan (files, decisions, acceptance criteria) for non-trivial work.
3. Build in increments; after each, run tests and report honestly — failures first.
4. Gates are binary: a gate that "mostly passes" has FAILED. Say which part failed.
5. Commit logically: one feature concern per commit; message says what and why.
6. Keep a ledger of what actually happened (docs/superpowers style: spec, plan, task-by-task record). Trust the ledger and git log over memory.
7. If another agent session owns files in this repo (check HANDOFF docs), never modify their in-flight files; coordinate or exclude.
8. After merge: update CLAUDE.md with the feature entry — conventions live there.

## Failure modes
- Jumping ahead before the previous increment's tests pass.
- "I'll add tests later." No later exists.
- Rerolling a flaky test until green and calling it fixed — instead document the flakiness mechanism.
