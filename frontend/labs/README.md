# Lab source workspace

This is the editable source for the 59 user-authored simulations imported from
the ZIP supplied on 6 September 2026. Archive identity is recorded in
`catalog/provenance.json`. The complete original archive was extracted to
`.toolchains/lab-restructure/source-20260906` at repository root.

## Responsibilities

- `simulations/<subject>/<lab>/view.html`: accessible page structure and controls.
- `simulations/<subject>/<lab>/simulation.js`: experiment state, calculations and rendering.
- `simulations/<subject>/<lab>/styles.css`: lab-specific styles, where needed.
- `runtime/`: shared screen scaffolding, 3D scaffolding, concept engines and WebXR adapter.
- `vendor/`: bundled libraries, accompanying licenses and supplied font.
- `catalog/`: simulation metadata, versioned curriculum and import provenance.
- `../scripts/build-labs.mjs`: deterministic publisher and local-reference/syntax validator.

The original browser scripts retain their execution order and isolated iframe
globals. They are separate source files, not ES modules: converting their global
contracts would require a separate behavioral migration. The LMS handles
authentication, course attachment and notebook persistence outside these frames.

## Edit and build

From `frontend`:

```sh
npm run labs:build
npm run labs:check
npm run dev
```

`dev` and `build` regenerate lab assets automatically. Edit this directory;
`public/labs/cbse/labs`, its shared assets, and the two generated backend catalog
JSON files are build outputs. Outputs remain checked in for backend-only and
static deployments. The builder does not delete unrelated files or execute lab
code. It checks JavaScript syntax and local HTML asset references. `labs:check`
fails when generated files differ from source.

To add a reviewed simulation, create its folder and metadata in `catalog/labs.json`,
then rebuild. Keep `file` and `slug` stable once a course uses them. New curriculum
editions must have distinct IDs; never rename an existing chapter ID to mean a
different chapter. Instructor uploads continue to use validated data-only packs.

## Compatibility

All original 38 URLs and slugs are retained. Their reviewed nitrogen correction,
canvas redraw and XR scene integration remain in the source. The newer ZIP adds
21 simulations. Original standalone index/journey/SCORM files remain in the
extraction for reference; the LMS owns navigation and completion reporting.

The updated supplied curriculum contains 230 chapters. Its explicit lab links
are supplemented only by exact title, class and subject matches to the earlier
edition, in `backend/app/services/lab_catalog_service.py`. The earlier 233 chapter
IDs and 119 concept activities remain available for saved courses and notebooks.

Screen mode has been browser-tested for all 59 simulations at desktop and mobile
widths. Native scenes and spatial panels retain AR/VR entry and device detection;
physical headset/phone sessions still need device validation.

## Active library policy (integrated release)

The 59 supplied simulations are the active built-in library. Generic generated
chapter activities and PhET entries are no longer offered in catalogs or course
pickers. Unmapped chapters remain unlinked. Historical source files and private
drafts are retained without inventing replacement curriculum alignment.

Sasha Virtual Lab Pack imports/exports are in Lab Studio. The complete reviewed
source is `backend/seed_packs/cbse-supplied.zip`; restored metadata is validated
against that exact asset set. See `backend/app/services/supplied_lab_pack.py`.
Global lab-frame accent and gradients use #ff751f with accessible dark text.
