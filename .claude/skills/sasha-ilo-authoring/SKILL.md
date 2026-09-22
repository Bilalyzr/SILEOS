---
name: sasha-ilo-authoring
description: ILO manifest and immersive learning objects
---

Blueprint 8.1. Load for ILO or immersive content work.

- An ILO is a versioned, self-describing, assessable 3D learning object. Manifest fields: assets (primary + LODs + fallbacks + usdz), provenance, scene (camera, annotations anchored to mesh+uv, timeline steps, interactions), assessment tasks, xAPI hooks, accessibility equivalents, performance budgets.
- Annotations anchor to mesh+uv, never screen coords.
- ASSESSMENT IS PARAMETER-BASED, NEVER GESTURE-BASED (success is like param planeAngle range 44-46, not "user dragged X"). That is what makes tasks gradeable at every tier.
- Versioning: publishing freezes a manifest version; edits create a new version; attempts reference the version they were graded against.
- Fallbacks are mandatory fields, not extras: turntable video, still sequence, text description.
