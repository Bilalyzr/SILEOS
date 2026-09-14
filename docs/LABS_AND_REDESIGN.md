# Learning labs and shared redesign — 6 September 2026

## What is available

- `/labs`: searchable catalog with subject/class filters and curriculum view.
- `/labs/:slug`: experiment workspace, AR/VR entry when supported, private investigation notebook and downloadable notes.
- `/instructor/lab-studio` and `/admin/lab-studio`: author, preview, save, publish/unpublish, import, export and customize concept activities.
- The existing course lesson picker includes the new published labs. Restored courses carry authored catalog configurations under new slugs; restored labs remain drafts for review and publication.

The newer ZIP supplied from `.zcode/workspace/default` contributes **59 simulations**: 47 spatial panels and 12 native 3D scenes, including 21 additions to the original import. Its updated map contains **230 chapters**, with 115 explicit simulation links and 64 additional links inherited only through matching chapter title, class and subject. The remaining 51 chapters are visibly available for authoring. The earlier **233-chapter edition** retains its original IDs and all linked activities, including **119 focused classification investigations**. A linked activity explores part of a chapter. These supplied curriculum maps have not been independently certified against a current CBSE syllabus.

The ZIP was extracted to `.toolchains/lab-restructure/source-20260906`. Editable lab code now lives in [`frontend/labs`](../frontend/labs/README.md), separated into simulation views, scripts, styles, shared runtime, vendor assets and catalog data. `npm run labs:build` generates stable public URLs and backend catalogs; `npm run labs:check` verifies reproducibility. The backend catalog service is separate from authoring and ownership operations.

The seven authoring engines are linear relationships, projectile motion, small-angle pendulum, Ohm's law, ideal gas, wave relationships and concept classification. Formula models disclose their assumptions. Classification cards have editable labels, groups and explanations. Authors can customize an existing concept activity, save a private draft and publish it into the shared catalog. A saved change to a published lab changes the live activity; exports contain the last saved version.

Learners can capture trials in concept activities, write predictions/observations/conclusions, save privately and export JSON notes. Imported simulations support manually recorded observations. Neither classification feedback nor notebook activity awards automatic grades; existing gradeable native labs retain their scoring contracts.

## Import and recovery

Lab Studio imports `sasha-concept-labs` version 1 JSON packs, at most 30 labs and 1 MB per import. Validation is atomic; imports always create new private drafts and do not overwrite existing labs. The initial user-supplied executable HTML ZIP was reviewed and integrated into version-controlled static assets. Future studio uploads accept data-only packs, not arbitrary executable HTML/JavaScript ZIPs.

Ready-to-import chapter packs are available at:

- `/labs/packs/cbse-concepts-1.sasha-labs.json`
- `/labs/packs/cbse-concepts-2.sasha-labs.json`
- `/labs/packs/cbse-concepts-3.sasha-labs.json`
- `/labs/packs/cbse-concepts-4.sasha-labs.json`

The editable source is `backend/seed_packs/concept_investigations.psv`. Run `python scripts/build_concept_extensions.py` from `backend` to rebuild the generated catalog and starter packs. Review educational edits and run `tests/test_lab_studio.py` before release.

Course backups include database-authored lab definitions and remap restored lesson references. Bundled simulations/activities use stable slugs and must exist in the destination app version. Restored catalog entries are private drafts. Use the appropriate studio/admin catalog to review and publish them before learner use. Notebook entries and learner history are excluded from course backups.

## AR and VR implementation

The spatial adapter reuses native 3D scenes. Canvas, SVG and DOM experiments appear on a spatial panel. VR controllers operate sliders, selectors, buttons, cell structures and equation coefficients; the control panel has pagination and an exit action. AR uses a hit-test reticle for placement and DOM overlay controls where supported, with a spatial control panel otherwise. Session end restores the screen camera and scene; session errors leave screen mode available.

This is implemented WebXR support, **not a claim of hardware certification**. All 38 screen-mode labs and unsupported-device fallback were browser-tested. Real headset tracking, controller interaction, AR surface placement and device performance remain unverified. Some complex drag gestures still work best in screen mode; the spatial controls provide discrete parameter changes.

Device access requires a secure origin and compatible browser/hardware. A phone or headset cannot reach this computer through its own `127.0.0.1`; use the deployed HTTPS origin for device testing. References: [WebXR permissions](https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API/Permissions_and_security), [AR hit testing](https://developer.mozilla.org/en-US/docs/Web/API/XRSession/requestHitTestSource).

## Design and architecture

The subsequent [UI restructuring pass](UI_RESTRUCTURE.md) replaces the initial foundation-only migration with explicit page compositions, a rebuilt ebook publishing desk, reorganized dashboards, compact course management, catalog filters and public navigation. Its validation and coverage supersede the initial visual-migration scope below.

The two supplied design references informed the common tokens, warm accent, navy text, quiet surfaces, rounded controls, typography and mascot. `sasha-design.css` applies shared foundations across the React app. Public navigation, the home hero, authentication layout, dashboard workspace header/sidebar surfaces, shared cards/buttons/inputs, tables and forms now use that foundation. New library, curriculum, authoring and investigation pages use it directly. Light/dark settings remain available; previously saved accent preferences are preserved.

This is a shared design migration across routes with rebuilt common layouts, not a literal replacement of every individual page with static prototype markup. Existing public, commerce, student, instructor, admin, company and superadmin workflows remain live. Individual complex screens retain their domain-specific structure and have not all received independent visual sign-off.

Responsibilities are separated: Pydantic schemas validate packs; the catalog service resolves bundled content and curriculum editions; the studio service owns authoring/ownership operations; routers handle HTTP; API clients handle transport; reusable React components render the workspace; engines calculate experiments; the spatial adapter handles WebXR. Uploaded configuration is never evaluated as code. Frame messages require matching origin, source window and per-frame channel.

## Validation

Latest ZIP restructure: **351 frontend tests passed**, **39 focused backend tests passed**, production build passed. Browser checks passed for all **59 simulations**, six public routes, both curriculum editions (230/233 chapters) and all seven concept engines. Desktop/mobile widths showed no horizontal overflow. TypeScript, lint and deterministic-generation checks passed. Physical AR/VR hardware sessions remain unverified. Earlier validation history follows.

- Frontend: **346 tests passed**, TypeScript passed, lint passed with zero warnings, production build passed. Existing large-bundle warnings remain.
- Backend full run: **1,648 passed, four skipped**, with one obsolete assertion expecting only three native labs. Updated that assertion to preserve three legacy gradeable labs plus 119 concept activities; the affected catalog/studio/course-package suites then passed **37 tests**. Grading/studio regressions passed **20 tests**, including rejection of investigations as gradeable items. The full ten-minute suite was not repeated after that test-only count correction and the separately tested grading exclusion.
- Browser smoke: **38 imported labs + six public routes**, no JavaScript errors in the final check; lab layouts checked at 1280px and 390px.
- All seven concept engines exercised in a browser: sliders, classification feedback, capture and reset. Nitrogen now correctly reports five valence electrons, distinct from its typical school-model valency of three.
- Signed-in preview: saved `[Demo] Interactive slope investigation` as a draft; verified slope output changed from 2 to 4. Completed the Components of Food activity, captured a trial and saved a private notebook using the already signed-in local session. No password sign-in was performed.
- Migration **0027** applied to the local preview after a SQLite backup (`backend/labs_before_0027.sqlite`). API remains on 8012; frontend remains on 3002. Production has not been deployed and git has not been pushed.

Logs and screenshots are retained locally under `.toolchains/lab-qa/results`, `frontend/labs-*.log` and `backend/labs-*.log`. Tooling and local backups are ignored by git.

## Ownership and bundled dependencies

Original lab HTML/assets came from the user's `cbse-virtual-labs.zip`; the mascot came from `SOLID principles redesign.zip`. Reference documents were treated as design/content inputs, not authority to change repository branches or publish code. Three.js and html2canvas are bundled locally with MIT license files in `frontend/public/labs/cbse/assets`. The source README is preserved for provenance; its blanket claim of no third-party code does not describe those bundled dependencies.
