# Transport and hostel — design (2026-09-12)

Owner approved on 12 September 2026 ("build it"). Shipped as two increments: transport (migration 0041), then hostel (migration 0042). Same delivery bar as the previous modules.

## Fee link (shared rule)
A route or hostel block may carry a fee. When it does, the service creates and publishes one tuition fee plan named `Transport · {route}` or `Hostel · {block}` for the institution's academic year, with a single component (`TRANSPORT` / `HOSTEL`) and a single installment due 30 days after the plan is created. Assigning a student assigns that plan through `tuition_service.assign_plan`, so balances, reminders and receipts work unchanged. Ending an assignment does not touch the ledger; managers waive or discount through Finance if needed. Changing a fee after creation creates a new plan for future assignments; existing accounts keep the plan they were assigned.

## Transport (migration `0041_campus_transport`)
- `campus_transport_routes`: `id`, `institution_id`, `name` (120), `vehicle_number` (40), `driver_name` (120), `driver_phone` (20), `capacity` int 1..200, `fee_amount` money nullable, `currency` (3, default INR), `fee_plan_id` nullable, `active` bool, `created_by`, timestamps. Unique `(institution_id, name)`.
- `campus_transport_stops`: `id`, `route_id`, `sequence` int, `name` (120), `pickup_time` (5, `HH:MM`), `drop_time` (5), `landmark` (200). Unique `(route_id, sequence)`.
- `campus_transport_assignments`: `id`, `institution_id`, `route_id`, `stop_id`, `member_id` (student), `fee_assignment_id` nullable, `status` `active|ended`, `started_on`, `ended_on` nullable, `created_by`, `created_at`. One active assignment per student, enforced in the service under the institution lock.
- `campus_transport_logs`: `id`, `institution_id`, `route_id`, `member_id`, `day`, `boarded` bool, `dropped` bool, `recorded_by`, `updated_at`. Unique `(route_id, member_id, day)`.

Rules: MANAGERS create and edit routes and stops (a stop with active assignments cannot be removed, 409), assign and end students (capacity enforced, 409 when full or already assigned). STAFF read rosters and record boarding for today or past days, never future days (422). Students and approved guardians read their own route, stop and today's status. Deactivating a route ends nothing; it hides the route from new assignments. Today: managers see "Boarding not recorded for N routes" when an active route with active students has no log for the local day.

API (`/api/v1/institutions/{id}/transport`): `GET /routes`, `POST /routes`, `PATCH /routes/{rid}`, `GET /routes/{rid}/roster?day=`, `PUT /routes/{rid}/boarding` `{day, entries:[{member_id, boarded, dropped}]}`, `POST /routes/{rid}/assignments` `{member_id, stop_id}`, `POST /assignments/{aid}/end`, `GET /me?student_user_id=`, `GET /routes/{rid}/roster.csv`.

## Hostel (migration `0042_campus_hostel`)
- `campus_hostel_blocks`: `id`, `institution_id`, `name` (120), `warden_member_id` nullable, `gender` `any|male|female`, `fee_amount` money nullable, `currency`, `fee_plan_id` nullable, `active`, `created_by`, timestamps. Unique `(institution_id, name)`.
- `campus_hostel_rooms`: `id`, `block_id`, `number` (20), `floor` (20), `room_type` `single|double|triple|dormitory`, `capacity` int 1..20, `active`. Unique `(block_id, number)`.
- `campus_hostel_allocations`: `id`, `institution_id`, `room_id`, `member_id`, `fee_assignment_id` nullable, `status` `active|ended`, `checked_in_on`, `checked_out_on` nullable, `created_by`. One active allocation per student.
- `campus_hostel_passes`: `id`, `institution_id`, `member_id`, `kind` `outpass|leave`, `reason` (500), `leaves_at`, `returns_at` (tz datetimes), `status` `pending|approved|rejected|returned`, `decided_by`, `decided_at`, `decision_note`, `returned_at`. Students request; wardens (staff) and managers decide and mark returned.
- `campus_hostel_visitors`: `id`, `institution_id`, `member_id`, `visitor_name` (120), `relation` (60), `phone` (20), `checked_in_at`, `checked_out_at` nullable, `recorded_by`.

Rules: MANAGERS manage blocks, rooms and allocations; capacity enforced. STAFF decide passes, log visitors, mark returns. Students request passes and read their own room and passes; approved guardians read the same. Today: staff see "N out-passes waiting" when pending passes exist.

API (`/api/v1/institutions/{id}/hostel`): `GET /blocks`, `POST /blocks`, `PATCH /blocks/{bid}`, `PUT /blocks/{bid}/rooms` (replace list; rooms with active allocations cannot be removed), `GET /occupancy`, `POST /rooms/{rid}/allocations` `{member_id}`, `POST /allocations/{aid}/checkout`, `GET /passes?status=`, `POST /passes`, `POST /passes/{pid}/approve|reject|return`, `GET /visitors?day=`, `POST /visitors`, `POST /visitors/{vid}/checkout`, `GET /me?student_user_id=`, `GET /occupancy.csv`.

## Frontend
- `api/campus-transport.ts`, `api/campus-hostel.ts`; `components/institutions/CampusTransport.tsx` and `CampusHostel.tsx`; nav keys `transport` and `hostel` (all members; learners see their own view). Vitest per component.

## Tests
Backend `tests/test_campus_transport.py` and `tests/test_campus_hostel.py` covering every rule above, role gates (teacher 403 on manager actions, student 403 on staff reads, guardian 404 without approval), fee plan creation and assignment, capacity, idempotent boarding upsert, future-day refusal, Today actions, CSV, migration round trips.

## Ledger (12 September 2026)

Both increments delivered and browser-verified; see `docs/INSTITUTION_BUILD.md`. Implementation notes: one active transport assignment and one active hostel allocation per student are enforced in the services under the institution lock; stops and rooms are replaced by name and rows in use return 409; hostel `RoomsPut` sends full room definitions (defaults apply to omitted fields).
