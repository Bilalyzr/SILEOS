---
name: sasha-geogebra
description: GeoGebra work — embedding, applets, saved state
---

Blueprint 8.3. INTEGRATED in this repo 2026-09-04.

LICENCE (blocking for commercial): the GeoGebra Apps API is free for NON-COMMERCIAL use; commercial deployment needs a written agreement with GeoGebra GmbH. The owner approved preview/development use. Do not ship paid-seat production against it without the licence.

What exists here:
- geogebra_applets table + /api/v1/geogebra/applets CRUD + /embed returning deployggb.js appletParameters (appName one of graphing/geometry/classic/3d/cas; material_id from a Materials URL; optional ggbBase64 saved state capped at 20MB).
- Lesson content type 'geogebra' via the atomic pair with geogebra_applet_id.
- OWNER RULE: attachable to FREE courses ONLY — enforced in the courses.py resolver (422 naming the rule); the wizard mirrors it by hiding the option when price > 0.
- Player: components/geogebra/GeoGebraEmbed.tsx (loads deployggb.js once, injects, emits one xAPI launched statement per mount).
- Delete blocked while attached to lessons (409).

Blueprint extras NOT built: validation rulesets, randomisedProbe (drag free params, check the invariant — distinguishes a real construction from a dragged-to-look-right one), server-side grading via headless browser. Build those only after the licence lands.
