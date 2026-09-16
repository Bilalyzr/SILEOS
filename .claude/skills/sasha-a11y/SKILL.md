---
name: sasha-a11y
description: UI work and accessibility audits
---

Blueprint 3.13/13.3 + the UI principles. Load for UI work and audits.

- WCAG 2.2 AA minimum; AAA on core learner flows (money paths, quiz taking).
- Every interactive element: real label/for, keyboard operable, visible focus.
- Announce state changes with role=alert or live regions (see the library pages' error patterns).
- Every 3D/visual interaction needs a documented keyboard equivalent AND a non-visual equivalent carrying the same objective — a legal requirement, not a nicety.
- prefers-reduced-motion: disable auto-rotation and camera animation at the token level.
- Contrast: token pairs are pre-verified (AAA body text, AA muted); compute new color pairs, never eyeball them.
- Test with an axe pass on new pages (the axe-core pattern exists in the SILEOS ui package to copy).
