# Launch Surface & Edge Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the new revenue products discoverable on the public site (header, footer, courses-page promo strip) and add anon-only stale-while-revalidate cache headers to the four hottest public API endpoints.

**Architecture:** One backend helper (`apply_public_cache`) wired into four GET endpoints with an anon-vs-auth split and `Vary: Authorization`; a security-middleware compatibility check; surgical nav/footer/banner edits on the frontend; CDN documentation.

**Tech Stack:** FastAPI (Request/Response header manipulation), React 18 + TS, pytest.

**Spec:** `docs/superpowers/specs/2026-09-02-launch-surface-design.md`

## Global Constraints

- Branch `launch-surface` forked from `company-invoicing`, worktree `.worktrees/launch-surface`. Backend paths relative to `<worktree>/backend/`.
- Tests: `"C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe" -m pytest tests/<files> -v` from `<worktree>/backend/`. Baseline ~45 pre-existing failures / 4 errors; zero NEW. Frontend type-check baseline 391, zero new.
- Personalized data must NEVER get a public cache header: the ONLY discriminator is the presence of the `Authorization` request header, and every cached response carries `Vary: Authorization`.
- Authenticated responses on wired endpoints get `Cache-Control: private, no-store`.
- Never touch payments_proxy.py / test_proxy_webhook_migration.py.
- Commit trailer: blank line then `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Cache-header helper + endpoint wiring + middleware compatibility

**Files:**
- Create: `app/core/cache_headers.py`
- Modify: `app/routers/bundles.py` (both GETs), `app/routers/memberships.py` (GET /plans), `app/routers/courses.py` (the public listing GET only — find the handler that serves `GET /api/v1/courses`), possibly `app/core/security_middleware.py` (only if it clobbers Cache-Control — see Step 3)
- Test: `backend/tests/test_cache_headers.py`

**Interfaces:**
- Produces:
```python
# app/core/cache_headers.py
from fastapi import Request, Response

def apply_public_cache(request: Request, response: Response, *,
                       s_maxage: int, swr: int) -> None:
    """Anon requests → edge-cacheable; authed → private. Callers pass the
    route's Request and Response (FastAPI injects both when declared)."""
    response.headers["Vary"] = "Authorization"
    if request.headers.get("authorization"):
        response.headers["Cache-Control"] = "private, no-store"
    else:
        response.headers["Cache-Control"] = (
            f"public, s-maxage={s_maxage}, stale-while-revalidate={swr}"
        )
```
- Wiring pattern per endpoint (add `request: Request, response: Response` params to the handler signature; FastAPI injects both without affecting the OpenAPI body):
```python
    apply_public_cache(request, response, s_maxage=300, swr=600)
```
  Values: bundles list 300/600; bundle detail 60/600; membership plans 300/600; courses listing 60/600.
- CAUTION for courses.py: the listing handler already has parameters (filters, optional user). Add the two injected params without disturbing existing ones; apply the header at the top (it only touches headers). If the handler already takes `Request`, reuse it.

- [ ] **Step 1: Failing tests**

```python
def _assert_public(r, s_maxage):
    cc = r.headers.get("cache-control", "")
    assert f"s-maxage={s_maxage}" in cc and "stale-while-revalidate=600" in cc
    assert "public" in cc
    assert r.headers.get("vary", "").lower() == "authorization"


def test_bundles_list_cache_headers_anon(client):
    r = client.get("/api/v1/bundles")
    assert r.status_code == 200
    _assert_public(r, 300)


def test_bundle_detail_cache_headers_anon(client, db, course):
    from app.models.bundle import Bundle, BundleCourse
    b = Bundle(name="C", slug="cache-pack", bundle_price=9.0)
    db.add(b)
    db.flush()
    db.add(BundleCourse(bundle_id=b.id, course_id=course.id))
    db.commit()
    r = client.get("/api/v1/bundles/cache-pack")
    assert r.status_code == 200
    _assert_public(r, 60)


def test_membership_plans_cache_headers_anon(client):
    r = client.get("/api/v1/memberships/plans")
    assert r.status_code == 200
    _assert_public(r, 300)


def test_courses_listing_cache_headers_anon(client):
    r = client.get("/api/v1/courses")
    assert r.status_code == 200
    _assert_public(r, 60)


def test_authed_request_gets_private_no_store(client, db, course):
    r = client.get("/api/v1/bundles", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "no-store" in cc and "private" in cc
    assert "s-maxage" not in cc


def test_unwired_endpoint_has_no_public_cache(client):
    r = client.get("/api/v1/memberships/plans")
    assert "s-maxage" in r.headers.get("cache-control", "")  # sanity wired
    r2 = client.get("/health")
    assert "s-maxage" not in r2.headers.get("cache-control", "")
```

NOTE: `test_authed_request_gets_private_no_store` sends a garbage Bearer token to a PUBLIC endpoint — the endpoint must still 200 (it doesn't require auth) while the cache helper sees the header. If the app's middleware rejects garbage tokens on public routes, use the `as_user` override + a real header-less TestClient call instead — adapt and note it.

- [ ] **Step 2: Run** → failures (no headers).

- [ ] **Step 3: Middleware check.** Grep `app/core/security_middleware.py` (and main.py middlewares) for `Cache-Control`/`no-store`/`no-cache`. If any middleware SETS Cache-Control on API responses after the router runs, change it minimally: only set its value when the response doesn't already carry a `Cache-Control` starting with `public, s-maxage` (one `if` — do not otherwise alter middleware behavior). If no middleware touches Cache-Control, note that and move on.

- [ ] **Step 4: Implement + run** → 6 passed; regression `tests/test_bundle_api.py tests/test_membership_api.py` green (endpoint signatures changed — verify no break).

- [ ] **Step 5: Commit** — `feat: anon-only SWR cache headers on public catalog endpoints`

---

### Task 2: Storefront surfacing (header, footer, courses promo strip)

**Files:**
- Modify: `frontend/src/components/layout/header.tsx` (nav array ~line 31), `frontend/src/components/layout/footer.tsx` (courses column ~line 25), the `/courses` listing page (find it: `frontend/src/pages/courses.tsx`)
- Gate: type-check zero new vs 391.

**Steps (binding content):**
- [ ] Header nav array: after `{ name: "Courses", href: "/courses" }` insert `{ name: "Bundles", href: "/bundles" }` and `{ name: "Membership", href: "/membership" }`. Confirm the same array drives the mobile menu (grep its usage); if the array is duplicated for mobile, update both.
- [ ] Footer `courses` column: append `{ name: "Course Bundles", href: "/bundles" }` and `{ name: "Membership", href: "/membership" }`.
- [ ] Courses page promo strip: at the top of the course grid, a slim strip (match the page's card/badge styling — read the page first) with up to two links: "Get every course with a Membership →" (`/membership`) and "Save with Course Bundles →" (`/bundles`). On mount, fetch `fetchMembershipPlans()` (api/membership.ts) and `fetchBundles()` (api/bundle.ts); render each link only when its list is non-empty; render nothing when both empty or on any fetch error (wrap in try/catch, never block the grid). Use Link from react-router-dom.
- [ ] Route sanity: grep App.tsx to confirm `/bundles` and `/membership` routes exist (they do — assert in your report).
- [ ] Type-check gate; commit — `feat: surface membership and bundles across public navigation`

---

### Task 3: CDN + repo docs

**Files:**
- Modify: `CLOUDFLARE_CACHE_SETTINGS.md`, `CLAUDE.md`
- Gate: none (docs).

**Steps:**
- [ ] `CLOUDFLARE_CACHE_SETTINGS.md`: append a dated section "API edge caching (2026-09)" — the four cacheable paths with their s-maxage/swr values; the protection model (headers only emitted for requests WITHOUT Authorization; `Vary: Authorization`; authed responses are `private, no-store`); required Cloudflare config (honor origin cache headers on `/api/v1/bundles*`, `/api/v1/memberships/plans`, `/api/v1/courses` — via Cache Rules "Respect origin TTL"; do NOT blanket-cache `/api/v1/*`).
- [ ] `CLAUDE.md`: under Notes for future work append:
```
- **Edge caching + storefront surfacing** (2026-09): public catalog endpoints
  (bundles list/detail, membership plans, courses listing) emit anon-only
  `Cache-Control: public, s-maxage, stale-while-revalidate` + `Vary:
  Authorization` via app/core/cache_headers.apply_public_cache; authed
  requests get `private, no-store`. Never wire this helper into an endpoint
  returning personalized data without the anon guard. Cloudflare setup in
  CLOUDFLARE_CACHE_SETTINGS.md. Header/footer/courses-page link Membership
  and Bundles; the courses-page promo strip hides itself when no plans/
  bundles exist.
```
- [ ] Commit — `docs: edge caching CDN guidance + surfacing notes`

---

## Post-implementation (owner, manual, optional)
Cloudflare: add Cache Rules honoring origin TTL for the four paths (headers are inert until then — zero risk before).
