# Launch Surface & Edge Caching — Design Spec

**Date:** 2026-09-02
**Status:** Approved by owner (standing recommendation approval; owner explicitly asked that customer-facing frontend be ready for the new features)
**Sub-project:** 5 of 5. Branch `launch-surface` (forked from `company-invoicing`)
in worktree `.worktrees/launch-surface`.

## Problem

Sub-projects 2–4 shipped working pages (`/membership`, `/bundles`, company
Billing tab) but the PUBLIC site never links the first two — header and
footer contain no reference, so paying customers cannot discover the new
revenue products. Separately, the roadmap's final pillar (edge caching with
stale-while-revalidate) is unimplemented: every anonymous catalog request
hits FastAPI/Postgres directly.

## Part A — Storefront surfacing

1. **Header** (`frontend/src/components/layout/header.tsx`): the nav array
   (currently `Courses`, …) gains `Bundles → /bundles` and
   `Membership → /membership` immediately after Courses. The same array
   drives the mobile menu — verify both render.
2. **Footer** (`footer.tsx`): the `courses` link column gains
   `Course Bundles → /bundles` and `Membership → /membership`.
3. **Courses listing** (`/courses` page): one slim, dismiss-less promo strip
   above the course grid with two links — "⭐ Get every course with a
   Membership" → `/membership` and "🎁 Save with Course Bundles" →
   `/bundles`. The strip renders ONLY when the corresponding content
   exists: fetch `/memberships/plans` and `/bundles` on mount; hide a link
   whose list is empty; hide the strip entirely when both are empty. Silent
   on fetch errors (never block the course grid).
4. **No other surfaces**: home page (Tamil-specific layout) and
   course-detail cross-sells are explicitly out of scope (future polish).
5. Gate: type-check zero new; manual code-trace that every new link's
   route exists.

## Part B — Edge caching (stale-while-revalidate)

### Mechanism
`app/core/cache_headers.py` with one function:

```python
apply_public_cache(request, response, *, s_maxage: int, swr: int) -> None
```

- Request has NO `Authorization` header → `Cache-Control: public,
  s-maxage=<s>, stale-while-revalidate=<swr>` and `Vary: Authorization`.
- Request HAS an Authorization header → `Cache-Control: private, no-store`
  and `Vary: Authorization` (personalized fields like `owned_course_ids` /
  `is_enrolled` must never be cached by any shared cache).

### Wired endpoints (initial, conservative set)
| Endpoint | s-maxage | swr |
|---|---|---|
| `GET /api/v1/bundles` | 300 | 600 |
| `GET /api/v1/bundles/{slug}` | 60 | 600 |
| `GET /api/v1/memberships/plans` | 300 | 600 |
| `GET /api/v1/courses` (public listing) | 60 | 600 |

Course DETAIL and everything auth-gated stay uncached (out of scope — the
detail handler mixes personalized logic; revisit later).

### Middleware interplay
`app/core/security_middleware.py` may set global no-cache headers — verify
and, if it overwrites `Cache-Control` on responses that already carry a
`public, s-maxage` value, make it respect the pre-set header (smallest
possible change, behavior for all other responses unchanged).

### Documentation
`CLOUDFLARE_CACHE_SETTINGS.md` gains a section: which API paths are now
edge-cacheable, that `Vary: Authorization` + the anon-only rule protect
personalized data, and the Cloudflare setting needed ("Cache Level:
Standard" honors origin `s-maxage`; no Page Rule bypass for `/api/v1/` on
the four paths above — or equivalently a Cache Rule honoring origin
headers).

## Testing
For each wired endpoint: anonymous GET carries `public, s-maxage=…,
stale-while-revalidate=…` + `Vary: Authorization`; authenticated GET
carries `private, no-store`; a non-wired endpoint (e.g. `/api/v1/payments/
create-order` response or `/memberships/me`) carries NO public cache
header. Frontend: type-check gate; links point at registered routes.

## Non-goals
Redis response caching, HTML/page caching, cache purge webhooks, home-page
redesign, course-detail cross-sells, CDN config automation.

## Ops at launch
None mandatory (headers are inert without a CDN honoring them). When ready:
confirm the Cloudflare zone honors origin cache headers for the four paths.
