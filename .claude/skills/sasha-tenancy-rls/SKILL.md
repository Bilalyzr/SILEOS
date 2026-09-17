---
name: sasha-tenancy-rls
description: Any migration, query, or multi-tenant concern
---

Blueprint 7.4/13.2. Load for any data-access or migration work.

## Rules (SILEOS repo — the RLS reference implementation)
- Every table carries tenant_id; RLS policies at the DATABASE level (USING tenant_id = current_setting('app.tenant_id', true)), never only in app code.
- App connects as a NON-OWNER role so RLS actually applies; login-only lookups go through SECURITY DEFINER functions.
- SET LOCAL app.tenant_id per transaction (withTenantDb). No context = zero rows by construction.
- Test the breach vectors: wrong-context read, no-context read, explicit other-tenant WHERE, cross-tenant INSERT (WITH CHECK), API layer returning 404 not 403 (no existence leak).

## Sasha LMS (this repo)
Single-tenant today — the seam: features that could be sold to another institution must keep tenant scoping OUT of business logic (scope in middleware/query helpers) so RLS can be added without rewrites. New tables here need no tenant_id, but avoid global mutable singletons that would block it.

## Failure modes
- Bypassing RLS "just for this report query" — that is the breach.
- Testing isolation only through the API; always also test at the SQL layer.
