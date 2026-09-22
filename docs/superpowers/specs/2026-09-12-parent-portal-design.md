# Parent web portal — design (2026-09-12)

Owner approved on 12 September 2026 ("Build it"). One parent home page that shows every approved child's campus signals in one place, built purely by aggregating existing services. No new tables, no migration.

## Purpose
Parents already have fees, exam results, transport and hostel views, but each lives on a separate institution page a parent cannot open (institution pages require membership). The portal replaces that with a single page at `/parent` that reads everything through the same guardian rules (approved `parent_link_requests` only).

## Backend
`services/parent_portal.py::overview(db, parent_user)` returns:

```
{
  "children": [
    {
      "student": {"id", "name", "email"},
      "institutions": [
        {
          "institution": {"id", "name", "academic_year", "timezone"},
          "member_id", "batches": ["Grade 9", ...],
          "attendance": {"present", "total", "percent"} | null   # last 30 local days
          "fees": {"currency", "outstanding", "overdue", "next_due": {"name","due_on","balance"} | null, "accounts": n},
          "exams": [{"id","name","status","total","max_total","percent","passed","rank","students"}],  # published, latest 3
          "transport": <campus_transport.me>,
          "hostel": {"resident", "room", "block", "pending_pass": {...} | null, "approved_pass": {...} | null},
          "notices": [{"id","title","created_at"}],  # latest 3 for the child's batches or campus-wide
          "alerts": [{"kind","message"}]
        }
      ]
    }
  ],
  "pending_requests": n
}
```

Alerts (derived): `fees_overdue` when overdue > 0; `attendance_low` when 30-day percent < 75 with at least 5 recorded days; `transport_not_boarded` when assigned and today's log exists with boarded false; `hostel_pass_pending` when a pass is pending; `results_published` when an exam was published in the last 7 days.

Every per-institution block is computed only for institutions where the child is an active student member. Each sub-block is wrapped so one failing service degrades to `null` rather than failing the page; failures are logged.

Router: `GET /api/v1/parents/campus` (new file `routers/parent_portal.py`, registered under the existing `/api/v1/parents` prefix). Role `parent` only; 403 otherwise.

## Frontend
`pages/parent/dashboard.tsx` becomes the portal: keep the link-by-email form; for each child, one card per institution with metric tiles (attendance, outstanding, overdue, next due), an alerts strip, latest results, transport today, hostel status, and recent notices. The existing course digest stays below as "Online learning". `api/parent-portal.ts` client. Vitest `pages/__tests__/parent-dashboard.test.tsx`.

## Tests
`backend/tests/test_parent_portal.py`: approved child appears with attendance, overdue fee, published exam, transport status, pending hostel pass and notices; unapproved child is absent; alerts computed; a student or instructor gets 403; a parent with no children gets an empty list and the pending count.
