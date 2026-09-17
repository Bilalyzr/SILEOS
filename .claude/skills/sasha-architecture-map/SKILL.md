---
name: sasha-architecture-map
description: Where new code goes — layers and boundaries
---

One-page map (blueprint section 6 adapted to the real Sasha repo).

## Sasha LMS (this repo)
- FastAPI backend: app/routers/* per domain (courses, quizzes, payments, library, geogebra, sileos pack). Routers stay thin; app/services holds logic; app/models holds tables.
- React 18 + Vite frontend: pages mirror backend domains; shared clients in src/api/*; ONE shared mapping for lesson content types in src/lib/lessonContentSync.ts.
- Async: no job queue in this repo; the xAPI spine is post-commit best-effort.
- Money: rupees in DB; paise only at the Razorpay boundary (max(int(round(x*100)),100)).

## Placement rules
- New domain endpoint: new router file, register in app/main.py, add prefix to axios noSlashEndpoints.
- Cross-cutting learner analytics: xapi_statements via app/services/xapi_service.emit_statement (post-commit only).
- New lesson content type: extend the ATOMIC PAIR in the courses.py resolver + lessonContentSync.ts + player branch. Zero other engine files.
- Every new table: SQLAlchemy model + ensure_schema entry + idempotent SQL in backend/migrations/.

## SILEOS (greenfield sibling at C:/Users/Admin/SILEOS/sileos)
NestJS+Next monorepo, Postgres RLS multi-tenant, pnpm. Never mix conventions between the two repos.
