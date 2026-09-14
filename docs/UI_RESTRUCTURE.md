# UI restructuring — September 6, 2026

The later [Astra gradient-glass implementation](ASTRA_DESIGN_IMPLEMENTATION.md)
applies the newly supplied `ASTRA-DESIGN.md` principles to these page compositions.
That document describes the current visual system and its validation.

The first lab release applied shared visual tokens while retaining most old page compositions. This follow-up adapts the supplied `Sasha LMS Redesign.dc.html` page patterns into live React layouts. The reference's prototype navigation, example accounts, statistics and publishing instructions are not application data or operational instructions.

## Implemented layouts

| Area | Layout change |
| --- | --- |
| Instructor ebooks | Publishing desk with real resource counts, status/search filters, selectable resource rows, a details/preview panel, file-readiness checklist and publishing/upload controls. Existing create, edit, upload, publish, unpublish and delete API flows remain connected. |
| Workspace navigation | One utility header instead of separate mobile and desktop bars; breadcrumbs and local navigation for the current feature segment. Side rail is 224px. |
| Page composition | 98 page files migrated to explicit page-header and content-region compositions, covering instructor, admin, student, commerce, public and partner screens. Existing forms, validation, dialogs and permission checks remain in the page modules. |
| Teaching dashboard | Compact metrics, primary grading/course areas and a secondary column for review queue, profile and exports. |
| Student dashboard | Course continuation and current learning move ahead of supporting analytics and achievements. |
| Admin and college dashboards | Compact headings/metrics; working actions and internship lists move ahead of supporting reports. Superadmin retains its live refresh controls. |
| Profile | Account identity/details come first; activity, achievements and visibility settings sit in an expandable section. |
| Instructor courses | Compact resource rows with course identity, status, enrollment/rating/price fields, expandable management actions and local thumbnail fallback. |
| Public navigation | Brand, Home, Learn, Internships and Community; keyboard-operable dropdowns, working course search, cart and role-aware account destinations. Responsive mobile navigation uses the same destination lists. |
| Home | Reference-inspired split hero with the supplied mascot, clear course/lab actions and discovery links. Replaces the former global WebGL hero render loops. Existing lower-page sections remain. |
| Course catalog | Compact heading, desktop filter sidebar and controlled search/sort/view toolbar. Mobile uses the existing filter dialog. Format, category, level and price filters remain connected. |
| Course details | Compact metadata/purchase surfaces and horizontally scrollable tabs without page overflow on phones. |
| Lesson workspace | Main learning area before the right-hand 296px curriculum rail, with a course/progress utility bar. Existing media rendering and tracking are preserved. Mobile retains its lesson drawer. |
| Company portal | Clear page heading and separate navigation/content columns, with horizontal section navigation on phones. |
| Public information pages | Shared compact breadcrumb/title composition replaces the large legacy title bands. |

## Component responsibilities

`components/design-system/PageLayout.tsx` owns page composition, headings, metric strips and work panels. It has no API or authorization dependencies. Page modules retain their existing data and business behavior. `WorkspaceNavigation` resolves the most specific navigation destination; `WorkspaceHeader` owns search and breadcrumbs. `PublicHeader` owns public navigation and reuses role routing. `styles/page-redesign.css` supplies responsive layout rules using the established design tokens.

The migration is adaptive: domain-specific editors, live calls, simulators, legal content and forms remain functional components. It does not substitute static prototype screens for application workflows.

## Validation

- TypeScript and zero-warning ESLint checks passed.
- 349 tests passed across 57 files. Added ebook regressions for selection/filter consistency, editing the correct identifier without publishing, and failed-load recovery.
- Production Vite build passed. The pre-existing large-bundle warning remains.
- 17 public screens checked at 1440px and 390px: home, courses, a real course detail, blog, membership, bundles, library, internships, about, contact, terms, privacy, refund policy, login, register, labs and not-found. Final pass had no JavaScript errors or horizontal page overflow. Catalog filtering and reset were exercised.
- Signed-in browser review covered the ebook publishing desk, instructor course management and teaching overview using the existing session. No credentials were entered and no publications or destructive actions were performed for visual QA.
- Not every private route, content state, role and device combination has an individual visual sign-off. The broad migration passed the existing behavioral suite; additional role-specific acceptance review can use the same layout patterns.
- No backend schema changes, production deployment or Git push in this follow-up.

Local verification logs are `frontend/redesign-*.log`; public screenshots are in `.toolchains/lab-qa/redesign-results/`. These QA artifacts are ignored by Git.
