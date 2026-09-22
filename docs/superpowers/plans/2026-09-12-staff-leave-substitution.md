# Staff leave and substitution — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teacher leave requests with quota-checked manager approval, automatic substitution slots on the timetable, candidate-filtered assignment, Today visibility, and a leave/substitution report.

**Architecture:** One new backend feature group in the campus pattern (models → Alembic 0040 → schemas → service → router under `/api/v1/institutions/{id}/staff/*`), two small hooks into existing code (`campus_pilot.event_dict` gains substitute fields; `campus_action_center.today` includes substituted events for the substitute and a manager system action), one React section, one Vitest file.

**Tech Stack:** as the previous plan. Spec: `docs/superpowers/specs/2026-09-12-staff-leave-substitution-design.md`.

## Global Constraints
Same as `2026-09-11-campus-exams-and-fee-reminders.md`. Local dates use the institution timezone through `zoneinfo`.

### Task 1: Models, migration 0040, round-trip test
- [x] `backend/app/models/campus_staff.py`: `CampusLeaveType`, `CampusLeaveRequest`, `CampusSubstitution` as in the spec; register in `models/__init__.py`.
- [x] `backend/alembic/versions/0040_campus_staff_leave.py` (revises 0039), guarded `has_table`, reverse-order downgrade.
- [x] `tests/test_campus_staff.py::test_campus_staff_migration_round_trip`.

### Task 2: Leave types, requests, decisions, balances
- [x] `schemas/campus_staff.py`: `LeaveTypesPut(academic_year, types:[LeaveTypeIn(code, name, annual_quota)])`, `LeaveCreate(type_id, starts_on, ends_on, note)`, `Decision(override=False, note="")`, `RejectIn(note)`, `AssignIn(substitute_member_id, note="")`.
- [x] `services/campus_staff.py`: `put_types`, `list_types`, `create_leave`, `list_leave`, `approve_leave` (creates substitutions), `reject_leave`, `cancel_leave` (releases), `balances`.
- [x] Router + `main.py` registration. Tests for each rule in the spec.

### Task 3: Substitutions
- [x] `list_substitutions`, `candidates`, `assign`, `unassign` with the exclusion rules; `substitution_dict` with event title, time, batch, absent and substitute names.
- [x] Hook `campus_pilot.event_dict` to add `substitute_member_id` / `substitute_name` (single query per event is acceptable; the events list is capped at 2000).
- [x] Hook `campus_action_center.today`: teacher branch ORs assigned substitutions; manager branch adds `_system_action("substitutions-open", "staff", ...)` when open substitutions exist in the next 7 days.
- [x] Tests for candidates, assign/unassign, event dict, Today.

### Task 4: Report
- [x] `leave_report(db, institution, academic_year)` → `{academic_year, types:[...], rows:[{member_id, name, role, balances:{code:{quota, used, remaining}}, substitution_hours}]}`; CSV writer for `format=csv`.
- [x] Tests for JSON and CSV.

### Task 5: Frontend
- [x] `api/campus-staff.ts`, `components/institutions/CampusStaff.tsx`, nav `staff` in `pages/institutions.tsx` (staff-only), substitute name in `CampusPilot` timetable cards and Today schedule when present.
- [x] `__tests__/campus-staff.test.tsx`: apply leave calls `createLeave`; manager approves; assign calls `assign` with the chosen candidate; teacher does not see Approvals.
- [x] tsc 0, lint 0, vitest, build.

### Task 6: Browser walk and docs
- [x] Preview: teacher applies, owner approves, substitution appears, assign a candidate, Today shows the system action, report CSV downloads. Record in `docs/INSTITUTION_BUILD.md`; add to `docs/CAMPUS_OS_RELEASE_2026_09_11.md`; CLAUDE.md entry; release check head 0040.


## Ledger (12 September 2026)

All six tasks done. Backend `tests/test_campus_staff.py` 10 tests; frontend `campus-staff.test.tsx` 3 tests. Browser walk found one bug: the CSV `Content-Disposition` header carried the en dash from the academic year and returned 400; the filename is now ASCII-sanitised and a regression test covers a non-ASCII year. Today's uncovered-class counter starts from the local day start so early classes still count.
