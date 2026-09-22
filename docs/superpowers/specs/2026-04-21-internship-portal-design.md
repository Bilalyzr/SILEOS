# Internship Portal — Design Spec

**Date:** 2026-04-21
**Status:** Approved, executing

## Problem

The current `internships.py` module is a minimal job-board (admin posts, any user applies). The user wants a real internship portal where students who complete courses become hireable candidates and startups/companies onboard to browse and hire them. Students arrive via two paths: **organic** (self-serve signup) and **college cohorts** (referral code + SPOC-managed).

## Scope — three independent subsystems

Built in parallel (user accepts coordination risk for speed):

### SS2 — Candidate profile + eligibility
### SS3 — Company portal + marketplace
### SS1 — College / cohort / SPOC + attendance

## Shared foundation

- **New user roles:** `spoc`, `company` (alongside `student`/`instructor`/`admin`).
- **Auth helpers:** `require_spoc`, `require_company`, `require_spoc_or_admin` added to `AuthService`.
- **Email templates (new):** `internship_candidate_interest`, `company_approved`, `cohort_invite`, `session_reminder`, `interest_accepted`.
- **Uploads reuse:** `/uploads/document` for PDF resumes, `/uploads/image` for company logos.

---

## SS2 — Candidate profile + eligibility

### Models — `backend/app/models/candidate.py`

```
CandidateProfile
  id, user_id (FK, unique), is_visible (bool, default False),
  resume_url (str, PDF from /uploads), bio (text),
  skills (JSON list[str]), preferred_roles (JSON list[str]),
  availability_date (date), linkedin_url, github_url, portfolio_url,
  created_at, updated_at

CandidateEligibility
  id, user_id (FK, unique), source (str: 'auto_certificate' | 'spoc_approved'),
  eligible (bool), reason (text), decided_by (user_id, nullable),
  decided_at, cohort_id (FK nullable), created_at, updated_at
```

### Eligibility rules
- **Organic student:** `IssuedCertificate` insert → hook in `certificate_service.py` inserts `CandidateEligibility(source='auto_certificate', eligible=True)`.
- **Cohort student:** SPOC toggles via `/cohorts/spoc/students/{user_id}/internship-eligible`. Writes `source='spoc_approved'`.
- **Browsable in SS3:** `profile.is_visible == True AND eligibility.eligible == True`.

### Endpoints — `backend/app/routers/candidate.py` at `/api/v1/candidates`
- `GET /me` / `PUT /me` — own profile
- `POST /me/visibility` — toggle `is_visible`
- `GET /browse?skills=&roles=&availability_before=&page=&page_size=` — company-only, requires approved Company
- `GET /{user_id}` — full candidate detail (company-only)

### Frontend
- `frontend/src/pages/dashboard/internship-profile.tsx` — editor with completeness indicator.
- Widget on student dashboard: eligibility status + visibility toggle.

---

## SS3 — Company portal + marketplace

### Models — `backend/app/models/company.py`

```
Company
  id, owner_user_id (FK, unique), name, slug, website,
  industry, team_size (str/enum), description, logo_url,
  contact_email, contact_phone,
  is_approved (bool, default False), approval_source (str: 'self_serve'|'admin_invite'),
  approved_by (FK user_id), approved_at, created_at, updated_at

CompanyInterest
  id, company_id (FK), candidate_user_id (FK),
  status (str: 'interested'|'accepted'|'declined'|'withdrawn'),
  company_message (text), responded_at, created_at
  unique(company_id, candidate_user_id)
```

### Signup flows (both supported)
- **Self-serve:** `POST /companies/signup` creates user with role=`company`, Company with `approval_source='self_serve'`, `is_approved=False`. Admin sees queue.
- **Admin-invite:** `POST /companies/admin/invite` — admin creates Company pre-approved, emails the contact a setup link (reuse password-reset token style).

### Express-interest flow
1. Company clicks Interest → `POST /companies/candidates/{id}/interest` with message.
2. Candidate receives email + in-app inbox row.
3. Candidate `POST /companies/interests/{id}/accept` or `/decline`.
4. On accept: candidate email/phone revealed in company's view of the interest row. Company notified.
5. Further contact off-platform.

### Endpoints — `backend/app/routers/companies.py` at `/api/v1/companies`
- `POST /signup`, `POST /admin/invite`, `GET /admin/pending`, `PATCH /admin/{id}/approve`, `PATCH /admin/{id}/reject`
- `GET /me`, `PUT /me`
- `POST /candidates/{candidate_user_id}/interest` (body: `{message}`)
- `GET /me/interests` (company's pipeline)
- `GET /me/candidate-inbox` (student's received-interests list)
- `POST /interests/{id}/accept|decline|withdraw`

### Frontend
- `/for-companies` + `/for-companies/signup` (public)
- `/company/dashboard` (browse, pipeline, profile editor) — `require_company` + approved
- `/dashboard/internship-inbox` (student accept/decline)
- `/admin/companies` (approval queue)

---

## SS1 — College / cohort / SPOC + attendance

### Models — `backend/app/models/cohort.py`

```
College
  id, name, slug, city, state, contact_name, contact_email,
  created_by (admin user_id), created_at, updated_at

Cohort
  id, college_id (FK), course_id (FK), spoc_user_id (FK),
  name, max_students (int), starts_on (date), ends_on (date),
  is_active (bool, default True), created_at, updated_at

ReferralCode
  id, cohort_id (FK, unique), code (str, unique, indexed),
  max_uses (int), used_count (int, default 0),
  expires_at (datetime), created_at

CohortMembership
  id, cohort_id (FK), user_id (FK), joined_at
  unique(cohort_id, user_id)

Session
  id, cohort_id (FK), scheduled_at (datetime), duration_minutes (int),
  topic (str), session_type (str: 'lecture'|'lab'|'evaluation'|'other'),
  created_by (spoc user_id), created_at

SessionAttendance
  id, session_id (FK), user_id (FK),
  status (str: 'present'|'absent'|'late'|'excused'),
  notes, marked_by (user_id), marked_at
  unique(session_id, user_id)
```

### Attendance — two streams
1. **Activity-derived (no storage):** service method `get_activity_roster(cohort_id, date)` joins today's `LessonProgress.updated_at`, `QuizAttempt.attempt_started_at`, and (if exposed) `User.last_login`. Returns per-user booleans.
2. **Session-based (SPOC):** SPOC creates Session → roster view → marks each student → `SessionAttendance` rows.

Dashboard shows both side-by-side: activity dot per student + per-session attendance grid.

### Referral-code signup flow
Extend `POST /auth/register` to accept optional `referral_code`. On submit:
1. Lookup code; reject if missing / inactive / expired / `used_count >= max_uses`.
2. Create user as normal.
3. Insert `CohortMembership(cohort_id, user_id)`.
4. Auto-enroll: `Enrollment(course_id=cohort.course_id, user_id, enrollment_status='enrolled')`.
5. Increment `used_count`.

### Endpoints — `backend/app/routers/cohorts.py` at `/api/v1/cohorts`
Admin:
- `POST|GET|PUT|DELETE /admin/colleges[/id]`
- `POST|GET|PUT|DELETE /admin/cohorts[/id]` — creates ReferralCode on POST

SPOC:
- `GET /spoc/my-cohorts`
- `GET /spoc/cohorts/{id}/roster` — with activity-derived column
- `GET /spoc/cohorts/{id}/task-stats` — lesson/quiz/assignment aggregates per student
- `POST|GET|PUT|DELETE /spoc/cohorts/{id}/sessions[/id]`
- `POST /spoc/sessions/{id}/attendance` — bulk body `[{user_id, status, notes}]`
- `POST /spoc/students/{user_id}/internship-eligible` — body `{eligible: bool, reason?}`; writes `CandidateEligibility(source='spoc_approved', cohort_id=...)` (SS2 handoff)

### Frontend
- `/admin/colleges` (CRUD), `/admin/cohorts` (CRUD + code display)
- `/spoc/dashboard` — list of my cohorts + today summary
- `/spoc/cohort/{id}` — tabs: Roster · Sessions · Task Stats · Internship Eligibility

---

## Cross-subsystem integration points

| Integration | Lives in | Source → Target |
|---|---|---|
| Course completion → auto eligibility | SS2 | `certificate_service.issue_certificate()` appends `CandidateEligibility` |
| SPOC greenlight → eligibility | SS1 → SS2 | `POST /cohorts/spoc/students/{id}/internship-eligible` writes to `CandidateEligibility` |
| Browse filters eligible + visible | SS3 reads SS2 | `companies.py /candidates/browse` joins `CandidateProfile ⋈ CandidateEligibility` |
| Interest notification | SS3 → email | `email_service.send_candidate_interest_email()` |
| Referral code at signup | SS1 → auth | `/auth/register` accepts `referral_code`; cohort join + enrollment on success |
| Admin approval surfaces | SS3 + SS1 → admin | Companies + Colleges appear in `/admin` UI alongside instructor approvals |

## Execution plan — parallel subagents

**Pre-flight (I do before dispatching):**
1. Scaffold new model files with empty class bodies.
2. Scaffold new router files with `router = APIRouter()` + register in `main.py`.
3. Add `require_spoc`, `require_company`, `require_spoc_or_admin` helpers to `AuthService`.
4. Add a `role` enum-ish check to accept `'spoc'` and `'company'` values (the column is already `String`).
5. Commit scaffold so subagents work against a known baseline.

**Dispatch three implementer subagents in parallel:**
- **Agent A → SS2** (candidate module + certificate hook + student UI)
- **Agent B → SS3** (company module + signup + approval + browse + interest + email + admin UI)
- **Agent C → SS1** (college + cohort + referral code + signup hook + SPOC dashboard + attendance)

**Coordination rule:** each agent owns a disjoint set of files. Shared files (`auth_service.py`, `main.py`, `email_service.py`, `certificate_service.py`, `schemas/auth.py` for the referral_code field) are extended only via pre-defined extension points.

After all three return, I review each, fix conflicts/issues, commit each as a separate feature commit, push.

## Out of scope (deferred)
- ATS stages (interview/offer/hired pipeline)
- Company paywall / monetization
- Recruiter messaging threads (beyond single interest message)
- Attendance reports / exports
- College/recruiter analytics dashboards
- Resume parsing / AI matching
- Mobile app
