---
name: sasha-elearning-standards
description: xAPI / SCORM / LTI / QTI / Caliper work
---

Blueprint 3.5/9.6. Load for standards or event-tracking work.

## xAPI in this repo (the spine is LIVE)
- Emit via app/services/xapi_service.emit_statement — best-effort POST-COMMIT (same doctrine as the gamification award() hook).
- Verbs: ADL short forms. Object whitelist lives in routers/sileos.py VALID_OBJECTS — add new object types THERE when introducing content types (geogebra was added with its integration).
- Actor is always the authenticated user on ingest; no client may forge another user's stream.
- Statements feed the analytics: at-risk and mastery read them.

## Not built here
SCORM/cmi5/LTI/QTI/Caliper/OneRoster — do not start without a named customer demand; SCORM is buy-not-build (Rustici class) per blueprint 13.1.

## Traps
- Statement bursts on every player tick — one statement per meaningful action.
- Forgetting context.course_id — analytics key on it.
