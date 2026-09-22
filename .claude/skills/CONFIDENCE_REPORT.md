# Sasha Build Kit — confidence & inference report

Per `Sasha_Build_Kit_Bootstrap.md` Prompt 2: every inference made while
distilling the skills, and contradictions found in the blueprint. **These are
the spots for the owner to check.**

## Confidence: HIGH (distilled straight from blueprint text + live code)
- conventions, wp-protocol, tenancy-rls, assessment-rules, ilo-authoring,
  tier-ladder, webxr, particle-sim (post-critique), h5p, ai-services,
  a11y, perf-budget, security, data-rights.
- geogebra — high on WHAT EXISTS (I built the integration today and
  verified it live); the licence note is the open item.

## Inferences I made (verify these)
1. **component-registry seam list** — the blueprint describes a future
   plugin registry; I distilled the seven seams from the ACTUAL repo
   pattern (h5p→game→geogebra). If SILEOS later lands its registry, this
   skill should merge with it rather than live beside it.
2. **architecture-map** — the blueprint's modular-monolith was mapped onto
   the real Sasha repo (routers/services/models + frontend mirrors). I
   inferred the "async pipeline = none here" point; if a job queue lands,
   update that skill.
3. **tenancy-rls "Sasha is single-tenant"** — inferred from the schema
   (no tenant columns anywhere). If multi-tenant Sasha is planned, this
   skill's Sasha section becomes mandatory reading for every migration.
4. **elearning-standards deferrals** — I wrote SCORM/LTI as
   do-not-start-without-demand. That's the critique's recommendation
   adopted as a rule; the blueprint itself lists them as scope. Owner call.
5. **geogebra free-only rule** — owner instruction 2026-09-04 ("free
   courses only"); encoded in the skill as an OWNER RULE so future agents
   don't "fix" it away.
6. **india-rails** — no blueprint integration detail existed; the skill is
   almost entirely process rules (verify-spec-first, DPDP adjacency) —
   deliberately content-light to avoid stale specifics.

## Contradictions found in the blueprint (worth adjudicating)
1. **GPU determinism** (§8.5.1 vs §5 recovery prompt): the spec demands
   bitwise-identical output across devices; its own recovery prompt admits
   float ordering breaks it. Skills encode the resolution: grading keys on
   quantized state / CPU reference / baked grids — never raw GPU state.
2. **MVP cut vs positioning** (§12.1 vs §4): the MVP excludes particles and
   H5P-editor while the one-sentence pitch implies them. Skills keep the
   MVP cut; marketing copy needs the same honesty.
3. **P0 auth scope** (Phase-0 prompt vs D4 trim): prompt asks for
   SAML/SCIM/passkeys in week 1-4; the trimmed plan deferred them. Skills
   encode the trim — reverse if an anchor school demands otherwise.

## Verification scenarios (Prompt 3 — which skill loads)
1. Chemical-equation question type → `sasha-assessment-rules` (+ component-registry only if it's a lesson content type)
2. 12fps on test Android → `sasha-perf-budget` then `sasha-tier-ladder`
3. Import course from Moodle → `sasha-elearning-standards` (+ `sasha-h5p` for content)
4. Parent requests child data deletion → `sasha-data-rights`
5. Embedded Jupyter component → `sasha-component-registry`
6. AI tutor leaked an answer → `sasha-ai-services`
7. Certificates for 400 students → `sasha-conventions` (no cert skill exists — certificate flows live in CLAUDE.md/quiz spec; acceptable)
8. Quiz submission lost on disconnect → `sasha-mobile-offline` + `sasha-assessment-rules`
9. 1.2M-triangle model → `sasha-3d-pipeline`
10. Tenants seeing each other's catalogue → `sasha-tenancy-rls`
