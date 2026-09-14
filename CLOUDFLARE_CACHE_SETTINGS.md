# Cloudflare Cache Settings for sashainfinity.com

## Current Configuration (as of 2026-05-10)

### Cache Rules (to be set in Cloudflare Dashboard)

1. **HTML Files - Bypass Cache**
   - URL pattern: `*sashainfinity.com/*.html`
   - Cache Level: Bypass
   - Edge Cache TTL: 0

2. **API Endpoints - Bypass Cache**
   - URL pattern: `*sashainfinity.com/api/v1/*`
   - Cache Level: Bypass
   - Edge Cache TTL: 0

3. **Hashed Assets (JS/CSS) - Standard Cache**
   - URL pattern: `*sashainfinity.com/assets/*-*.{js,css}`
   - Cache Level: Standard
   - Edge Cache TTL: 1 year (31536000s)
   - Browser Cache TTL: 1 year (31536000s)

4. **Static Assets - Standard Cache**
   - URL pattern: `*sashainfinity.com/*.{png,jpg,jpeg,gif,svg,webp,woff,woff2,ttf}`
   - Cache Level: Standard
   - Edge Cache TTL: 30 days
   - Browser Cache TTL: 7 days

5. **Uploads - Standard Cache**
   - URL pattern: `*sashainfinity.com/uploads/*`
   - Cache Level: Standard
   - Edge Cache TTL: 30 days
   - Browser Cache TTL: 7 days

### Page Rules (Alternative method)

1. **Bypass Cache for Dynamic Content**
   - URL: `sashainfinity.com/*.html`
   - Settings: Cache Level: Bypass

2. **Bypass Cache for API**
   - URL: `sashainfinity.com/api/*`
   - Settings: Cache Level: Bypass

3. **Cache Static Assets**
   - URL: `sashainfinity.com/assets/*`
   - Settings: Cache Level: Standard, Edge Cache TTL: 1 year

## How to Purge Cache

### Option 1: Cloudflare Dashboard
1. Log into Cloudflare Dashboard
2. Select sashainfinity.com
3. Go to Caching > Configuration
4. Click "Purge Everything" OR
5. Go to Caching > Cache Tools > Purge Individual Files
6. Enter specific URLs to purge (e.g., `/assets/index-C1DIXjVO.js`)

### Option 2: Cloudflare API
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/YOUR_ZONE_ID/purge_cache" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

### Option 3: During Deployment
Use the deployment script at `scripts/purge-cloudflare-cache.sh` (to be created)

## Nginx Cache Headers

Our nginx config sends these headers (which Cloudflare respects):
- HTML: `Cache-Control: no-cache, no-store, must-revalidate`
- Hashed JS/CSS: `Cache-Control: public, max-age=31536000, immutable`
- Static assets: `Cache-Control: public, max-age=86400`

Cloudflare will respect these headers if "Cache Level" is set to "Respect Existing Headers".

## Host Consolidation Redirects (SEO audit 2026-08-21, Finding 5)

All three hosts — `sashainfinity.com`, `www.sashainfinity.com`, and
`lms.sashainfinity.com` — currently serve the app with HTTP 200 and no
redirect, which fragments SEO signals. They must 301 to the apex.

**These redirects must live in Cloudflare, not nginx.** All three hostnames
resolve to the same Cloudflare proxy and arrive at the nginx origin as a
single host, so nginx never sees the original hostname and cannot
differentiate them.

Set these in the Cloudflare Dashboard under **Rules → Redirect Rules**
(create both, order does not matter):

### Rule 1 — www → apex

- Name: `www-to-apex`
- When incoming requests match: **Custom filter expression**
  `http.host eq "www.sashainfinity.com"`
- Then: **Dynamic redirect**
  - Target URL: `concat("https://sashainfinity.com", http.request.uri.path)`
  - Status code: `301`
  - ✅ Preserve query string

### Rule 2 — lms → apex

- Name: `lms-to-apex`
- When incoming requests match: **Custom filter expression**
  `http.host eq "lms.sashainfinity.com"`
- Then: **Dynamic redirect**
  - Target URL: `concat("https://sashainfinity.com", http.request.uri.path)`
  - Status code: `301`
  - ✅ Preserve query string

### Verification

```bash
curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" https://www.sashainfinity.com/blog
curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" https://lms.sashainfinity.com/blog
# Both must print: 301 -> https://sashainfinity.com/blog
```

Note: after enabling, purge the cache — Cloudflare may have cached the old
200 responses for these hosts.

## API edge caching (2026-09)

Four public catalog endpoints emit cache headers to accelerate anonymous browsing:

### Cacheable paths and TTLs

| Endpoint | Route | s-maxage | stale-while-revalidate |
|----------|-------|----------|------------------------|
| Bundles list | `/api/v1/bundles` | 300s | 600s |
| Bundle detail | `/api/v1/bundles/{slug}` | 60s | 600s |
| Membership plans | `/api/v1/memberships/plans` | 300s | 600s |
| Courses listing | `/api/v1/courses/` | 60s | 600s |

Note the trailing-slash inconsistency is intentional, not a typo: `courses` is
mounted with `@router.get("/")` under prefix `/api/v1/courses` (so the real
path carries a trailing slash), while `bundles` and `memberships` declare
their routes with no trailing slash and the app runs with
`redirect_slashes=False` — a trailing slash on those three 404s instead of
redirecting. Verified against `backend/app/main.py` router mounts, each
router's `@router.get(...)` decorators, and the `noSlashEndpoints` /
`trailingSlashEndpoints` lists in `frontend/src/api/axios.ts`.

### Header and protection model

All four endpoints use the same cache strategy:
- **Anon-only emission**: response headers are sent only when the request has no `Authorization` header
- **Vary header**: `Vary: Authorization` is sent, but this does **not** by
  itself stop Cloudflare from mixing authed and anonymous responses in the
  shared edge cache. Cloudflare's cache key ignores request headers by
  default — `Vary` only affects how *browsers* cache the response locally: it
  is not consulted by Cloudflare's edge cache when deciding whether to serve
  a previously cached response to a different request. An authed response
  never enters the edge cache in the first place because it's served with
  `Cache-Control: private, no-store` (private + no-store are always
  respected), so the real protection is that combination, not `Vary`. Do not
  rely on `Vary: Authorization` for cache-key separation on Cloudflare.
- **Authed requests**: receive `Cache-Control: private, no-store` (no edge caching; safe for personalized data within an authed session)

Implementation: all four routes call `app/core/cache_headers.apply_public_cache()` before returning, which checks for auth, sets the appropriate `Cache-Control` and `Vary` headers, and is safe against accidental wiring into personalized endpoints.

### Cloudflare Cache Rules setup

Set these in the Cloudflare Dashboard under **Rules → Cache Rules**. Every
rule below carries a **mandatory** second condition that bypasses cache
whenever the request has an `Authorization` header, using:

```
http.request.headers["authorization"][0] ne ""
```

This is not optional. Cloudflare's default cache key excludes request
headers, so `Vary: Authorization` on the origin response has no effect on
Cloudflare's edge cache (see "Header and protection model" above) — without
this explicit bypass, a request that happens to carry an `Authorization`
header could be served a stale cached anonymous response, or (in a
misconfiguration) an authed response could be written to the shared edge
cache and served back to anonymous users. `Cache-Control: private, no-store`
on the authed origin response is a second, independent layer of defense, but
the Cache Rule bypass below is required regardless — do not treat it as
redundant.

**Rule 1 — Bundles list**
- When: `http.request.uri.path eq "/api/v1/bundles"`
- Cache: **Respect origin TTL** (Cloudflare honors the `Cache-Control` headers from origin; s-maxage = 300s edge TTL)
- **Mandatory bypass condition**: if `http.request.headers["authorization"][0] ne ""`, set Cache Eligibility to **Bypass cache** (do not serve or write to edge cache for this request)

**Rule 2 — Bundle detail**
- When: `http.request.uri.path starts_with "/api/v1/bundles/"`
- Cache: **Respect origin TTL** (s-maxage = 60s)
- **Mandatory bypass condition**: if `http.request.headers["authorization"][0] ne ""`, set Cache Eligibility to **Bypass cache**

**Rule 3 — Membership plans**
- When: `http.request.uri.path eq "/api/v1/memberships/plans"`
- Cache: **Respect origin TTL** (s-maxage = 300s)
- **Mandatory bypass condition**: if `http.request.headers["authorization"][0] ne ""`, set Cache Eligibility to **Bypass cache**

**Rule 4 — Courses listing**
- When: `http.request.uri.path eq "/api/v1/courses/"`
- Cache: **Respect origin TTL** (s-maxage = 60s)
- **Mandatory bypass condition**: if `http.request.headers["authorization"][0] ne ""`, set Cache Eligibility to **Bypass cache**

In practice this means each entry above is two Cache Rules in the dashboard
(evaluated in order): a bypass rule matching
`<path> and http.request.headers["authorization"][0] ne ""` placed *before*
the cache rule matching `<path>` alone — Cloudflare Cache Rules apply in
list order and stop at the first match, so the bypass rule must be listed
first for each path.

**CRITICAL**: Do NOT blanket-cache `/api/v1/*` — only the four paths above have public data; all other API endpoints are authed or may contain sensitive data. The default Cloudflare rule for `/api/v1/*` must remain **Bypass Cache**.
