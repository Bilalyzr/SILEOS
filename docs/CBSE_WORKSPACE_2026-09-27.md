# Connected CBSE workspace — implementation and launch boundaries

## Available now

Open `/school` after signing in, or use **Classes 6–12** in the shared dashboard header.
The existing SaaS is preserved: Meiporul links to labs, Seyappaduporul to institution workspaces, and Utporul to courses. These links do not change enrolment, billing or tenant permissions.

- Seven class filters, subject and edition filters, chapter search and resource coverage indicators.
- The supplied NCERT 2024–25 map contains 230 chapter references across mathematics/science and senior-secondary mathematics, physics, chemistry and biology. It is not certification against the current syllabus and does not include all languages, humanities or commerce subjects.
- Existing published labs are linked using the catalogue mappings. These mappings still need educator alignment review.
- Instructors can attach courses they own or collaborate on after publishing the course and at least one lesson. A meaningful mapping review note is required. Administrators can manage all mappings.
- A stored content fingerprint invalidates the student-visible course mapping when lesson fields or course title/content/section metadata change. Underlying assets and assessment banks can change independently: this is a mapping review guard, not exhaustive content certification.
- Students cannot write mappings or shared chapter definitions. Mapping a course does not give free access to its lessons.
- Administrators can add chapter references, including missing subjects/electives, with an HTTPS CBSE Academic or NCERT source URL and review note. URL validation checks the domain, not the accuracy of the source or review.
- Removing a mapping does not delete the course. Existing mappings can be re-reviewed through the same form.

## Deployment

Apply `python -m alembic upgrade head` with the deployment's configured database. Head `0053` adds the chapter and mapping tables after `0052`. Rebuild the frontend and restart the API. Use the existing staging/runtime runbooks; do not deploy the local synthetic-data server or its accounts publicly.

## Validation performed

- 22 targeted backend tests passed (new curriculum routes and production runtime/migration tests), with existing deprecation warnings.
- Two new UI tests passed: seven-class filtering and truthful content gaps; instructor mapping submission.
- Full frontend regression suite: 501 tests across 91 files passed. Type-check, lint and production build passed. Build warnings include large pre-existing chunks and outdated browser compatibility data.
- Student and instructor credentials authenticated through the local Vite proxy. Student browser sign-in reached the dashboard and the new workspace.
- Local Docker API was unavailable, so PostgreSQL/Redis/container deployment acceptance was not performed.

## Remaining launch gates — not completed by this change

1. Confirm launch subjects, languages, academic year and XI–XII streams. Have qualified educators review the current official syllabus and each chapter mapping.
2. Author/license, review and publish the complete lessons, assessments and accessible interactive activities. Catalogue entries are not lesson content.
3. Validate tenant isolation and all role journeys against staging PostgreSQL, not only SQLite fixtures.
4. Exercise real payment sandbox capture/refund/webhook replay, email, AI quota/fallback, video and code execution providers with configured staging accounts.
5. Run workload-specific load tests, worker failure/recovery and backup restoration. Set a measured concurrent-user target before claiming capacity.
6. Review student-data handling, guardian/school access, consent and retention with the deployment owner; provide legal/policy review where needed.
7. Complete mobile, assistive-technology and actual classroom acceptance before opening paid enrolment.

The current workspace is an integrated implementation increment, not a claim that a complete all-subject production SaaS has been delivered.
