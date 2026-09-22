---
name: sasha-h5p
description: H5P content work
---

Blueprint 8.5.2 + this repo's live integration. Load for H5P changes.

- H5P is ADOPTED, not rebuilt: never rebuild a content type H5P already ships (the build-vs-adopt line).
- This repo: h5p router with hardened upload (zip checks, library allowlist), content status lifecycle (attach requires status=ready), results and user-data endpoints, xAPI bridging.
- Iframes: sandbox="allow-scripts" ONLY — never allow-same-origin.
- Licence register: content-type libraries carry their own licences; audit anything newly shipped.
- .h5p packages are self-contained, so they offline-bundle cleanly; results queue and sync.
- Migration weapon: bulk import from Moodle/Brightspace is a feature — keep import paths healthy.
