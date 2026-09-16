# Staff leave and substitution — design (2026-09-12)

Owner approved on 12 September 2026 ("build it"). Same delivery bar as exams and fee reminders: backend, migration, tests, frontend, browser walk, docs.

## Purpose
Let teachers apply for leave, let managers approve against per-type quotas, and turn every timetable slot the absent teacher owns into a substitution that a free colleague can cover. Students see who is teaching; the Today workspace surfaces uncovered classes.

## Data (migration `0040_campus_staff_leave`)
- `campus_leave_types`: `id`, `institution_id`, `academic_year` (32), `code` (20, upper-cased), `name` (80), `annual_quota` int 0..366, `created_by`. Unique `(institution_id, academic_year, code)`. Managers maintain the list; the first read seeds nothing (an institution without types cannot approve leave, and the UI says so).
- `campus_leave_requests`: `id`, `institution_id`, `member_id` (staff member), `type_id`, `starts_on`, `ends_on` (dates, inclusive), `days` int (calendar days inclusive), `note` (500), `status` in `pending|approved|rejected|cancelled`, `decided_by`, `decided_at`, `decision_note` (500), `override` bool, `created_at`, `updated_at`. Indexes on `(institution_id, status)` and `member_id`.
- `campus_substitutions`: `id`, `institution_id`, `leave_id`, `event_id` (`campus_events`), `absent_member_id`, `substitute_member_id` nullable, `status` in `open|assigned|released`, `assigned_by`, `assigned_at`, `note` (500). Unique `(leave_id, event_id)`.

Balances are derived: used = sum of `days` of approved requests for the member, type and academic year; remaining = quota − used.

## Rules
- STAFF (owner, admin, teacher) apply for their own leave. A request needs `ends_on >= starts_on`, at most 60 days, and must not overlap the member's own pending or approved requests (409).
- MANAGERS approve or reject. Approval exceeding the remaining balance is refused (422) unless `override=true` with a non-empty note. Rejection requires a note.
- On approval, every `campus_events` row with `teacher_id = member.id` whose local start date falls inside the range becomes an `open` substitution. Cancelling approved leave (by the teacher before it starts, or by a manager any time) sets its substitutions to `released`.
- Candidates for a substitution are active STAFF members other than the absent teacher who have no overlapping event as owner, no overlapping assigned substitution, and no approved leave covering that date. Assigning a non-candidate is refused (422). Unassign returns the row to `open`.
- Timetable event dicts carry `substitute_member_id` and `substitute_name` when a substitution is assigned. Today: a teacher's schedule includes events they are substituting; managers get a system action "N classes need a substitute" for open substitutions in the next seven days, linking to the Staff section.
- Every decision and assignment writes an `institution_audit` row.
- Report: per staff member and per type, quota, used, remaining for an academic year, plus hours covered as substitute. Available as JSON and CSV. Managers only.

## API (`app/routers/campus_staff.py`, prefix `/api/v1/institutions`)
- `GET /{id}/staff/leave/types?academic_year=`, `PUT /{id}/staff/leave/types` (managers; body `{academic_year, types:[{code,name,annual_quota}]}` upserts and deletes missing codes that have no requests).
- `GET /{id}/staff/leave?status=&member_id=` (staff own; managers any), `POST /{id}/staff/leave`, `POST /{id}/staff/leave/{lid}/approve` `{override, note}`, `POST .../reject` `{note}`, `POST .../cancel`.
- `GET /{id}/staff/leave/balances?member_id=&academic_year=`.
- `GET /{id}/staff/substitutions?status=&from=&to=` (managers all; staff where they are absent or substitute), `GET /{id}/staff/substitutions/{sid}/candidates`, `POST /{id}/staff/substitutions/{sid}/assign` `{substitute_member_id, note}`, `POST .../unassign`.
- `GET /{id}/staff/leave/report?academic_year=&format=json|csv` (managers).

## Frontend
- `frontend/src/api/campus-staff.ts`; `components/institutions/CampusStaff.tsx` mounted under nav key `staff` (label "Staff", staff-only) with: My leave (apply, list, cancel, balances), Approvals (managers), Substitutions (managers assign from candidates; teachers see their own), Leave types (managers), Report (managers, CSV download).
- Timetable and Today show the substitute name where assigned.
- Vitest: `components/institutions/__tests__/campus-staff.test.tsx`.

## Tests (`backend/tests/test_campus_staff.py`)
Types upsert and manager gate; apply with overlap 409 and student 403; own-only visibility; approve creates substitutions only for events in range; quota refusal and override; reject with note; cancel releases substitutions; candidate exclusions (owner of overlapping event, already substituting, on leave, the absent teacher); assign and unassign; event dict shows substitute; substitute's Today includes the event; manager Today has the system action; report JSON and CSV; migration 0040 round trip.
