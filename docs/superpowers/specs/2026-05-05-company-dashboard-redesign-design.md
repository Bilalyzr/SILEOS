# Company Dashboard Redesign — Design Spec

**Date:** 2026-05-05
**Owner:** SS3 / Company experience
**Status:** Draft for review

---

## 1. Goal

Replace the existing three-tab company dashboard (Browse candidates / Pipeline / Profile) with a four-tab operational dashboard that companies use to manage interns assigned to them through the platform. The new dashboard is no longer a hiring discovery tool — it is the day-to-day workplace for a company that has live interns.

The redesign also adds:
- Sub-users (reporting managers) so multiple people from the same company can log in.
- Daily attendance + work-done logging by the company (synced to the admin's existing attendance view).
- End-of-internship performance reviews.
- Announcements to assigned interns.
- Hours-worked tracking alongside attendance.
- Attendance reports with PDF + CSV download and in-app preview, available to both company and admin users.

---

## 2. Scoping rule

A company sees only what is theirs:
- **Students:** roster rows where `hired_by_company = me.company_id`.
- **Internships:** internships that have at least one such roster row.
- **Attendance / work-done / announcements / reviews:** scoped to the same set.

A **company manager** (sub-user) sees a further-narrowed slice — only students whose `reporting_manager_user_id = me.user_id`.

The **admin** keeps unrestricted read access plus the ability to run any report across companies.

Anything outside this scope is not visible — no platform-wide student directory, no other companies' data.

---

## 3. New tabs

### 3.1 Overview
A landing page summarising what's happening today.

- **Stat cards:** Active interns · Active internships · This week's attendance % · Pending work-done submissions to review.
- **Today's attendance snapshot:** counts of Present / Absent / Late / Not-yet-marked, with a "Mark now" CTA jumping to the daily grid.
- **Recent activity feed (last 10 events):** new intern assigned, certificate issued, work-done submitted, review pending, manager invited.
- **Pending actions:** end-of-internship reviews owed, late-attendance students this week.

Read-only. All numbers reflect the scoping rule above.

### 3.2 Student management
Roster of all interns assigned to the company.

- Table columns: Name · Email · Internship · Progress % · Attendance % · Reporting Manager · Cert status · Internship status (active / completed / converted-to-hire / let-go).
- Row click → side drawer with full profile: résumé, LinkedIn / GitHub, all daily work-done entries, attendance history, contact (email + phone) once accepted, private company-only notes.
- Actions on a row: assign / change reporting manager · mark internship status · add private note.
- Filters: by internship · by reporting manager · by status.
- Search by name / email.

Edits write to the company-side data only (notes, status, manager assignment). Admin sees the result.

### 3.3 Internship management
Read-only mirror of the internships the company is participating in.

- Card per internship: title · cover image · count of *our* students · average progress · start / end window · SPOC contact.
- Click → curriculum outline + list of *our* students on that internship + per-internship attendance summary.
- No edit (admin owns the internship definition; this tab is for context).

### 3.4 Attendance management
Two views, switchable inside the tab.

**Daily grid view**
- Rows = students; columns = last 14 days (paginate back further).
- Each cell shows status (P/A/L/E) + small badge for hours.
- Click a cell → set status, hours worked, optional note.
- Bulk action: "Mark all present today (8h)".
- A second small grid below shows daily work-done status per student per day (submitted / approved / flagged / missing).

**Per-student timeline view**
- Open one student → calendar of their attendance + their daily work-done entries side-by-side.
- Company can comment on a work-done entry, mark approved or flagged.
- Manager-scoped: a company_manager sub-user only sees their own reportees here.

---

## 4. Sub-users — reporting managers (E1)

Today: one User (role=`company`) per Company.

Add: a Company can invite additional Users with role=`company_manager`, all linked to the same Company.

- Owner-only screen at `/company/dashboard/managers`: list managers, invite by email, revoke.
- Invited user receives email with a setup link → chooses password → role is set to `company_manager` and `company_managers.company_id` is set.
- A company_manager logs in to the same `/company/dashboard` UI but sees only students where `reporting_manager_user_id = self`. They cannot invite other managers, cannot post announcements, cannot submit performance reviews on behalf of the company.
- The owner can re-assign a student's reporting manager from the Student management drawer.

---

## 5. Performance reviews (E2)

When a student's progress hits 100% or their internship status is set to `completed`, the company is prompted to submit a review.

- Form: rating (1–5 stars), written feedback, hire recommendation (yes / maybe / no).
- One review per (company_id, student_user_id, internship_id).
- Review is visible to admin and (in summary form) on the student's certificate flow — full hire-recommendation text stays admin-only by default.
- Only the company owner submits reviews; managers can draft.

---

## 6. Announcements (E3)

A company posts a notice, all of *their* assigned interns (and admin) can read it.

- Owner-only post screen.
- Each announcement: title · body · optional internship filter (all interns vs interns on a specific internship).
- Surfacing: appears in the student's existing dashboard under a new "Announcements" widget; also delivered by email if the recipient has notifications enabled.
- Admin can read all companies' announcements (audit) and soft-delete them if abusive.

---

## 7. Hours worked (E4)

Extend the existing attendance table with an `hours_worked` decimal column. Each Present / Late attendance row carries hours (default 8). Absent / Excused → 0.

- Daily grid lets the company set hours per cell.
- Student management student drawer shows monthly hours roll-up.
- Attendance report (section 8) includes total hours per student.

---

## 8. Attendance reports

Available on **both** admin and company sides. Differences:
- **Company:** filters scoped to their data only.
- **Admin:** filters across all companies, plus "company" as an additional filter dimension.

### 8.1 Filters

All can be combined freely:
- **Date range:** any from-to, plus presets (this week / this month / last month / internship duration).
- **Internship:** one or many.
- **Student:** one or many.
- **Reporting manager:** one or many (company side only).
- **Company:** admin only.

### 8.2 Output formats

Three modes from the same filtered query:

1. **In-app view (PDF preview):** rendered `<embed>` of the PDF inside the page; navigable, printable.
2. **In-app view (CSV preview):** rendered as a virtualised table inside the page so the user can sort / scroll before downloading.
3. **Download:** "Download PDF" / "Download CSV" buttons hit the same endpoint with `?format=pdf` / `?format=csv`.

The user toggles "View" mode (PDF vs CSV) in-app, and "Download" is always available next to it.

### 8.3 Report content

Per row: Date · Student name · Email · Internship · Reporting manager · Status (P/A/L/E) · Hours · Note · Marked-by.

Footer summary: total days · attendance % · total hours · count by status.

PDF carries company logo + report header (date range + filter summary). CSV is plain rows + summary lines at end.

---

## 9. Data model changes

### 9.1 New tables

- `company_managers`
  - `id` PK
  - `company_id` FK → `companies.id`
  - `user_id` FK → `users.id` (unique with `company_id`)
  - `invited_by` FK → `users.id`
  - `invited_at`, `accepted_at`
- `daily_work_logs`
  - `id` PK
  - `student_user_id` FK → `users.id`
  - `internship_id` FK → `internships.id`
  - `log_date` DATE (unique per student per date)
  - `content` TEXT
  - `attachment_url` VARCHAR
  - `review_status` VARCHAR ('pending' / 'approved' / 'flagged') default 'pending'
  - `reviewed_by` FK → `users.id` nullable
  - `reviewer_comment` TEXT
  - `created_at`, `updated_at`
- `internship_announcements`
  - `id`, `company_id`, `internship_id` (nullable = all internships), `title`, `body`, `created_by`, `created_at`, `deleted_at`
- `internship_performance_reviews`
  - `id`, `company_id`, `student_user_id`, `internship_id`, `rating` (1–5), `feedback`, `hire_recommendation` ('yes' / 'maybe' / 'no'), `submitted_by`, `submitted_at`
  - Unique on (company_id, student_user_id, internship_id).

### 9.2 Column additions

- `attendance` (existing): add `hours_worked` NUMERIC(4,2) default 0.
- Roster / interest table (existing) — add or repurpose: `reporting_manager_user_id` FK → `users.id` nullable.
- `users.role` — extend allowed values to include `company_manager`.

### 9.3 Migrations

Per CLAUDE.md, this repo has no Alembic. Add a SQL migration file `backend/migrations/add_company_dashboard_v2.sql` and run it manually. Add the matching SQLAlchemy models so `init_db()` in `app/core/database.py` stays consistent for fresh DBs.

---

## 10. API endpoints

All under `/api/v1/companies/me/...` unless noted.

| Method + Path | Purpose | Roles |
|---|---|---|
| `GET /overview` | stats + activity feed | company, company_manager |
| `GET /students` | list scoped students | company, company_manager |
| `GET /students/{user_id}` | single student detail (drawer) | company, company_manager |
| `PATCH /students/{user_id}` | update reporting manager / status / notes | company (manager: notes only) |
| `GET /internships` | scoped internships | company, company_manager |
| `GET /internships/{id}` | internship detail + our students | company, company_manager |
| `GET /attendance?from&to&internship_id&student_id&manager_id` | grid data | company, company_manager |
| `POST /attendance` | upsert one or many attendance rows (status, hours, note) | company, company_manager |
| `GET /work-logs?...` | list logs with filters | company, company_manager |
| `POST /work-logs/{id}/review` | approve / flag / comment | company, company_manager |
| `GET /managers` | list company managers | company |
| `POST /managers` | invite manager (email) | company |
| `DELETE /managers/{id}` | revoke | company |
| `GET /announcements` | list | company, company_manager |
| `POST /announcements` | post | company |
| `DELETE /announcements/{id}` | soft-delete | company |
| `POST /students/{user_id}/review` | submit performance review | company |
| `GET /reports/attendance?...&format=json|csv|pdf` | attendance report | company, company_manager |

Student-side additions:
| `POST /api/v1/student/work-logs` | submit daily work-done | student |
| `GET /api/v1/student/work-logs` | own logs | student |
| `GET /api/v1/student/announcements` | announcements aimed at me | student |

Admin additions:
| `GET /api/v1/admin/reports/attendance?...&format=json|csv|pdf` | platform-wide report, company filter included | admin |

PDF generation: server-side using `reportlab` (already a Python option) or `weasyprint`. CSV generation: stdlib `csv`. Both stream the response with the right `Content-Disposition`.

---

## 11. Frontend changes

### 11.1 Routes
Replace the single `/company/dashboard` page with nested routes for direct deep-linking:
- `/company/dashboard` → redirects to `/company/dashboard/overview`
- `/company/dashboard/overview`
- `/company/dashboard/students` (+ `?student_id=` to open drawer)
- `/company/dashboard/internships`
- `/company/dashboard/attendance`
- `/company/dashboard/announcements`
- `/company/dashboard/managers` (owner only)
- `/company/dashboard/reports/attendance`

Admin gets `/admin/reports/attendance`.

### 11.2 Component layout
- New `CompanyDashboardLayout` wraps all sub-routes — provides the persistent header (company name, approval badge) + sidebar nav.
- Each tab is its own page module under `frontend/src/pages/company/`.
- The existing `CompanyDashboardPage` is deleted (its three sub-tabs are not part of the new design).
- Shared report-view component used by both `/company/dashboard/reports/attendance` and `/admin/reports/attendance`. PDF preview uses `<embed>`; CSV preview uses a virtualised table.

### 11.3 API layer
New `frontend/src/api/company-dashboard.ts` with React Query hooks per endpoint above. The existing `frontend/src/api/company.ts` (browse / pipeline / interest) is removed along with the old dashboard.

---

## 12. Permissions matrix

| Feature | Company owner | Company manager | Student | Admin |
|---|---|---|---|---|
| Overview | ✓ scoped | ✓ scoped to reportees | — | ✓ all |
| Student mgmt | ✓ | ✓ reportees | — | ✓ |
| Internship mgmt | ✓ | ✓ scoped | — | ✓ |
| Attendance edit | ✓ | ✓ reportees | — | ✓ |
| Work-log review | ✓ | ✓ reportees | — | ✓ |
| Manager admin | ✓ | — | — | ✓ |
| Announcements post | ✓ | — | — | ✓ (audit) |
| Performance review submit | ✓ | draft | — | ✓ (audit) |
| Attendance report | ✓ scoped | ✓ scoped to reportees | — | ✓ all |
| Submit daily work-done | — | — | ✓ self | — |

---

## 13. Out of scope

- Real-time chat between company and student.
- Mobile app.
- Payroll / stipend processing.
- External calendar sync (Google / Outlook).
- Discovery / hiring of *new* candidates (the old Browse + Pipeline tabs are intentionally being removed).
- Multi-company users (one user belongs to exactly one company).

---

## 14. Removal plan

The current company dashboard (Browse / Pipeline / Profile) and its supporting endpoints (`browseCandidates`, `myPipeline`, the interest flow on the company side) are deleted. The candidate-side internship inbox (accept / decline interest) is also no longer reachable for new interest rows; existing rows can stay until cleaned up. Confirm with the user before deleting the candidate-side tables — the design assumes the *feature* is gone but the *data* may be retained.

---

## 15. Open questions

1. Reporting manager column lives on the roster row vs a separate `student_assignments` table — recommended: roster row, simpler.
2. Daily work-done attachment storage — reuse the existing `/uploads` mount? Recommended: yes, under `uploads/work-logs/{user_id}/`.
3. Announcements — email delivery on by default, or opt-in per recipient? Recommended: opt-in via existing notification preferences.
4. Performance review visibility on student certificate — full text or just rating? Recommended: rating + hire recommendation public; written feedback admin-only.
5. PDF library — `reportlab` (lighter, no system deps) vs `weasyprint` (better HTML→PDF). Recommended: `reportlab` for the simple tabular layout.
