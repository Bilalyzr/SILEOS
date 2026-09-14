# Sasha Infinity business-vertical architecture

## Decision

Sasha Infinity is one platform and control plane with three independently
operated business pillars. The pillars are product surfaces, not three copies
of the LMS and not course categories with different labels.

| Pillar | Public host | Owns | Primary revenue families |
|---|---|---|---|
| MA1 Meiporul | `meiporul.sashainfinity.com` | 3D/GLB library, AR/VR experiences, GeoGebra, immersive and virtual labs, experiential evidence | immersive programs, asset licensing, subscriptions, lab deployment, AMC/support |
| MA2 Seyappaduporul | `seyappaduporul.sashainfinity.com` | tutoring and institution operations: live classes, attendance, fees, schedules, notes, ebooks, papers, parent/center workflows | tuition, institution SaaS/managed operations, digital resources, paper generation, franchise services |
| MA3 Utporul | `utporul.sashainfinity.com` | shared course-authoring engine, skills catalog, quizzes, assignments, assessment, credentials, creator commerce, careers | courses/cohorts, memberships, assessment services, premium credentials, creator revenue share, career services |

`Upporul` is accepted as a legacy MA3 alias in data and imports. New UI, URLs,
and writes use the product name `Utporul`.

## Runtime shape

The three hosts serve the existing React application. Host detection selects
the correct pillar home, while shared routes, authentication, authoring, and
learner records continue to use the same FastAPI/PostgreSQL platform.
Public course catalogs inherit the pillar from the current host. A shared,
HttpOnly refresh cookie scoped to `.sashainfinity.com` restores a user's
bearer-token session on a sibling pillar without exposing tokens to JavaScript
across origins; localhost continues to use a host-only cookie.

```text
Meiporul ---------\
Seyappaduporul ----> shared identity + course engine + payments + evidence
Utporul ----------/                         |
                                              v
                                  Sasha Admin Control Center
```

This preserves one learner identity and avoids synchronizing three databases.
Route-level workspaces provide separation now; independently deployable
frontends can be introduced later without changing the data contract.

## Ownership and integration rules

1. Utporul owns the reusable academic authoring engine. A Meiporul course is an
   Utporul-authored course whose learning experience uses Meiporul objects,
   interactives, or labs. A Seyappaduporul timetable can deliver that same
   course in a school or tutoring center.
2. Meiporul owns immersive assets and simulation behavior. It does not create a
   second course, user, payment, or certificate system.
3. Seyappaduporul owns operational records such as institutions, classes,
   attendance, tuition plans/payments, staff, and parents. Campus management is
   therefore a Seyappaduporul workspace, not the root product.
4. Shared concerns remain shared: identity/RBAC, notifications, audit,
   payment gateway integration, learner evidence, certificates, search, and
   the admin control plane.
5. Every new revenue writer must declare a canonical pillar and revenue-stream
   key. If it cannot be classified, it must appear in the Control Center's
   `unallocated` queue; it must never be silently assigned.

## Reporting contract

The Control Center is a consolidated read model, not a second financial ledger.
Current adapters read the existing sources of truth:

- generic commerce `Payment` + `Order` + `OrderItem` records for courses,
  ebooks, bundles, and generated papers;
- the audited `TuitionPayment` ledger for school/tutoring fees;
- `InternshipVoucher.amount_paid` for the established career purchase flow.

Each pillar response contains operational inventory, totals by currency, and
all expected revenue streams. Empty streams are labelled `Planned` until a real
writer exists. Unknown commerce and unknown course classifications remain
visible instead of disappearing. Every admin revenue headline and chart uses
the same Asia/Kolkata business-day definition: captures use payment date and
refunds use processing date. The concentration view reports the largest
pillar's positive collections share and the collections remaining if that
leader pauses. A share above 60% is flagged as concentrated; it is not a P&L,
cash-runway forecast, or guarantee of business resilience.

The Control Center is the default admin landing page and provides filterable,
exportable inventory for courses, lectures, ebooks, 3D objects, virtual labs,
GeoGebra applets, live classes, quizzes, certificates, generated papers,
students, instructors, orders, and enrollments. The specialist admin screens
remain the write authority for content and settings. Existing
audited impersonation provides "view as instructor/student/company" support;
pillar dashboards link back to the specialist control workspaces rather than
reimplementing those controls.

## Current capability truth

### Reorganized and connected

- public pillar homes, host-aware catalog routing, and shared subdomain session restoration;
- canonical pillar vocabulary in frontend and backend;
- centralized portfolio/revenue read model, daily pillar cash series, and concentration signal;
- pillar links in public and admin navigation;
- Meiporul 3D/AR, authored labs, virtual labs, GeoGebra, and course blocks;
- Seyappaduporul institution/campus operations, fees, live classes, library,
  and practice-paper generation;
- Utporul courses, quizzes, assignments, Assessment Studio, certificates,
  commerce, internships, and career connections;
- GeoGebra public-preview access and production content-security policy.

### Planned, not represented as implemented

- sandboxed live coding tests with visible/hidden cases;
- Meiporul device fleet, room safety, installation, quotations, EMI, and AMC
  execution workflows;
- revenue writers for asset licensing, lab deployment, institution SaaS,
  premium credentials, and other newly introduced business models.

These planned streams already have stable reporting keys, so implementing a
writer later does not require redesigning the Control Center.

## Deployment requirements

Application and reverse-proxy configuration now recognizes the three hosts.
Production launch still requires external infrastructure work:

1. create DNS records for the three subdomains pointing at the current edge;
2. install a certificate covering all three names (a wildcard certificate is
   the simplest option) before reloading the HTTPS server;
3. confirm environment-provided `CORS_ORIGINS` and `ALLOWED_HOSTS` do not
   override the checked-in defaults with an older list;
4. smoke-test root routing, login persistence, checkout return URLs, GeoGebra,
   and admin reporting from each host.

## Extension checklist

When a future business model is added:

1. choose the owning pillar and use an existing stream key or add one to both
   canonical configs;
2. keep the operational source authoritative and add a read adapter to
   `business_portfolio_service.py`;
3. test currency, capture/refund timing, access control, and unknown-source
   behavior;
4. expose the specialist workspace through that pillar and the central admin;
5. label partially built flows as planned until the writer and fulfillment path
   are both production-ready.
