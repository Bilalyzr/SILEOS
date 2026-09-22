---
name: sasha-conventions
description: Definition of done for every unit of work
---

Distilled from the SILEOS build brief + blueprint. Load every session.

## Code
- TypeScript strict; no `any` without a written justification comment. Sasha backend (Python): type hints on public functions.
- Validate inputs at the boundary (Zod frontend / Pydantic or explicit checks backend). Never trust client payloads.
- Errors handled explicitly — no swallowed exceptions. Backend errors follow the existing HTTPException(detail=...) pattern.
- No secrets in code or committed config. `.env` is gitignored; `.env.example` documents keys.
- Match the surrounding file's idiom. Comments only for constraints the code cannot show.

## Data
- Every migration reversible (write the down path). Run forward+backward on a scratch DB before claiming done.
- Indexes for every new query path. Check N+1 before merging list endpoints.

## API
- New routes: auth dependency declared (require_instructor / require_admin / get_current_active_user) plus a negative-case authz test.
- No trailing slashes on new prefixes (redirect_slashes=False); add the prefix to noSlashEndpoints in frontend/src/api/axios.ts.
- Idempotent POSTs where the client can retry (see create-order/fulfillment for the pattern).

## Frontend
- Loading, empty and error states implemented. Works at 320px. Keyboard operable. prefers-reduced-motion respected.

## Tests — the rule
- NEVER claim something is tested that you did not run. Paste real output in the report.
- Sasha backend regression: run the touched suite + the SILEOS pack; known-flaky areas (live_session timing, 429 state leakage) are documented, not "fixed" by rerolls.

## Reporting
- Lead with what is broken or skipped, then what works. Numbers over adjectives.
