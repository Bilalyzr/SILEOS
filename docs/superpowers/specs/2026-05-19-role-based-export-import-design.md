# Role-Based Export/Import Design

**Date:** 2026-05-19
**Status:** Approved
**Author:** Claude (via brainstorming skill)

## Overview

Add Export/Import panels to Instructor, SPOC, and Company dashboards. Each role sees only their own data. Reuses existing admin export/import infrastructure with role-based filtering.

## Goals

1. Instructors export/import their courses, students, and assessment results
2. SPOCs export/import student roster, internships, and placement data
3. Companies export/import positions, assigned interns, and performance reviews
4. All exports filtered to current user's data only

## Backend Changes

### New Endpoints

Extend `/backend/app/routers/export_import.py` with role-scoped endpoints:

**Instructor:**
- `GET /instructor/export/{section}` — sections: `courses`, `students`, `quiz_results`, `assignment_results`
- `POST /instructor/import/{section}`

**SPOC:**
- `GET /spoc/export/{section}` — sections: `students`, `internships`, `placements`
- `POST /spoc/import/{section}`

**Company:**
- `GET /company/export/{section}` — sections: `positions`, `interns`, `performance`
- `POST /company/import/{section}`

### Implementation Strategy

1. Add route handlers for each role
2. Reuse existing export/import service functions
3. Add `user_id` and `role` filter parameters to queries
4. All queries scoped to `current_user.id` or derived relationships

## Frontend Changes

### Component Updates

1. **ExportImportPanel** (`/frontend/src/components/admin/ExportImportPanel.tsx`)
   - Add `role: 'admin' | 'instructor' | 'spoc' | 'company'` prop
   - Filter available sections based on role
   - Route to appropriate API endpoints

2. **Dashboard Pages**
   - Add ExportImportPanel to instructor dashboard
   - Add ExportImportPanel to SPOC dashboard
   - Add ExportImportPanel to company dashboard

3. **API Layer** (`/frontend/src/api/admin.ts`)
   - Add role-specific export/import functions
   - Reuse existing types where possible

4. **Navigation**
   - Add "Export/Import" link to each role's sidebar

## Data Mapping

### Instructor Exports

| Section | Fields | Filter |
|---------|--------|--------|
| `courses` | title, category, price, students_count, rating, revenue, created_at | `course.instructor_id = current_user.id` |
| `students` | name, email, enrolled_courses, progress, completion_date | `course.instructor_id = current_user.id` |
| `quiz_results` | student_name, course, quiz, score, completed_at | `quiz.course.instructor_id = current_user.id` |
| `assignment_results` | student_name, course, assignment, status, grade, submitted_at | `assignment.course.instructor_id = current_user.id` |

### SPOC Exports

| Section | Fields | Filter |
|---------|--------|--------|
| `students` | name, email, phone, college, courses_enrolled, status | `student.college_id = spoc.college_id` |
| `internships` | company_name, title, stipend, required_skills, assigned_students, status | `internship.college_id = spoc.college_id` |
| `placements` | student_name, company_name, position, stipend, placed_date | `student.college_id = spoc.college_id` |

### Company Exports

| Section | Fields | Filter |
|---------|--------|--------|
| `positions` | title, stipend, required_skills, applicants_count, status, posted_date | `position.company_id = current_user.company_id` |
| `interns` | name, college, email, join_date, attendance_percentage, status | `assignment.company_id = current_user.company_id` |
| `performance` | intern_name, rating, feedback, review_date, reviewer | `assignment.company_id = current_user.company_id` |

## Security

### Authentication & Authorization

1. Each endpoint verifies `current_user.role` matches requested endpoint
2. JWT middleware validates tokens before processing
3. Role check: only instructors can hit `/instructor/export/*`, etc.

### Data Isolation

1. **WHERE clause filtering**: All queries enforce ownership via WHERE clauses
2. **Defense in depth**: Even if auth bypassed, queries return only user's data
3. **Import validation**: Reject rows with IDs outside user's scope

### Rate Limiting

Apply existing rate limits from admin export/import to new endpoints.

### Audit Logging

Log each export/import action with:
- user_id
- role
- section
- action (export/import)
- timestamp

## Error Handling

1. **403 Forbidden**: Role mismatch (e.g., student hitting instructor endpoint)
2. **404 Not Found**: Invalid section for role
3. **400 Bad Request**: Invalid import data (wrong format, out-of-scope IDs)
4. **413 Payload Too Large**: File size exceeds limits (reuse existing limits)
5. **429 Too Many Requests**: Rate limit exceeded

Import errors return row-level details:
```json
{
  "success_count": 45,
  "error_count": 2,
  "errors": [
    {"row": 3, "message": "Student ID 123 not in your college"},
    {"row": 7, "message": "Invalid email format"}
  ]
}
```

## File Formats

- **Export**: Excel (.xlsx) and PDF (same as admin)
- **Import**: Excel (.xlsx) and CSV (same as admin)

## Testing Checklist

- [ ] Each role can only access their own endpoints
- [ ] Exported data contains only user's records
- [ ] Import rejects rows with IDs outside scope
- [ ] PDF generation works for all sections
- [ ] Rate limiting applies
- [ ] Audit logs capture actions
- [ ] Frontend panels render correctly per role
- [ ] Navigation links work

## Migration Notes

No database schema changes required. Uses existing tables and relationships.
