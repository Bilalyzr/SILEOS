# SashaInfinity LMS — Production-Readiness & Mock-Data Audit

Date: 2026-07-27
Scope: `backend/app` (FastAPI), `frontend/src` (React/TS), `streaming-service/`, compose + nginx config.
Method: read-only audit across 4 parallel streams (mock-data, security, incomplete-features, config/deploy).

## Bottom line

- **Free of mock data?** ❌ No — fabricated data is shown to real users (About-page mentors, all dashboard charts) and paid enrollments can complete with a mock payment.
- **Ready for public use?** ❌ No — several individually-sufficient critical security holes are live (unauthenticated admin import, live signing secrets + Google session cookies committed to git, payment bypass).

The architecture and most authorization are solid; the blockers are a small number of high-severity issues plus incomplete commerce/admin flows. Fix P0, then P1, before public launch.

---

## P0 — CRITICAL (exploitable now; fix before the site stays public)

1. **Unauthenticated admin data-import** — `backend/app/routers/export_import.py:2312`
   `POST /api/v1/admin/import/{section}` has **no auth dependency**. Creates/overwrites `User`, `Company`, `Course`, `BlogPost`, `Coupon` from an uploaded CSV/Excel. New users get password `temp_password_123` and `is_active`/`is_verified` from the file; `?update_by_id=true` overwrites an existing admin's `user_email`/`is_active` → account takeover/lockout. **Fix:** add `Depends(AuthService.require_admin)`. Same for `GET /admin/export/{section}/count` (`:2749`) and schema/template siblings (`:2646`, `:2674`).

2. **Live signing secrets committed to git** — `.jwt_secret`, `.secret_key` (repo root, git-tracked)
   Real 64-char JWT/app secrets. `deploy_security.sh:27-44` writes them to `.env` and never regenerates (the `if [ ! -f ]` guard). With the JWT secret an attacker forges any user's token, including admin → full auth bypass. **Fix:** regenerate `SECRET_KEY` + `JWT_SECRET`, delete both files, purge from git history (`git filter-repo`), fix `deploy_security.sh` to never commit them. Rotating invalidates all sessions (expected).

3. **Live Google/YouTube session committed** — `backend/youtube_cookies.txt` (git-tracked)
   Real session cookies (`__Secure-3PSID`, `LOGIN_INFO`, …). Account hijack. **Fix:** sign out all sessions on that Google account, regenerate the cookie file out-of-repo, purge from history.

4. **Payment bypass — paid courses enrolled free**
   - `backend/app/routers/courses.py:1870-1956` — `POST /{course_id}/purchase` is an explicit "MOCK PAYMENT: auto-approve", no price/payment check, returns `is_mock: True`. Orphaned by the UI but live on the public API.
   - `backend/app/routers/orders.py:49-225` — cart `POST /orders/` creates `payment_method="mock"`, marks `COMPLETED`, enrolls without collecting money. Reached by the live cart flow (`frontend/src/contexts/CartContext.tsx:174`).
   - `backend/app/routers/courses.py:1688` — `is_free_user = current_user.user_email == "bharathijsw@gmail.com"` free-access backdoor.
   **Fix:** remove/gate `/purchase`; either hide cart for paid courses or wire multi-course Razorpay; delete the email backdoor.

5. **Open streaming service** — `streaming-service/video_streaming.py`
   Every endpoint unauthenticated, `allow_origins=["*"]` (`:29`), host-exposed `:8001`. `/extract` (`:164-225`) validates a URL by substring then passes the **raw** url to `yt_dlp.extract_info` → **SSRF** (e.g. `youtu.be`-containing url pointing at `169.254.169.254`). Also open bandwidth/CPU abuse. **Fix:** require a signed/auth token, restrict CORS, rate-limit, reconstruct the URL from a validated video-id, firewall `:8001` behind nginx.

6. **Client-bundle secret leak + XSS + token storage**
   - `frontend/vite.config.js:79` — `define: { 'process.env': process.env }` inlines the entire build env into public JS; if the prod build sees backend secrets they ship in the bundle. **Fix:** whitelist only `VITE_`-prefixed vars. Also `sourcemap: true` (`:83`) ships source maps — set false for prod.
   - Stored XSS: `dangerouslySetInnerHTML` with no sanitization repo-wide (`frontend/src/pages/blog-detail.tsx:312`, `lesson-redesigned.tsx:2155,621`, `assignment-submission.tsx:389`, `quiz.tsx:302,370`, `course-detail.tsx:41`). **Fix:** DOMPurify (or server-side sanitize) on all sinks.
   - `frontend/src/store/auth.ts:652-662` — access + refresh tokens persisted in `localStorage`; any XSS exfiltrates them. **Fix:** httpOnly/Secure/SameSite cookie for at least the refresh token.

---

## P1 — Blockers (mock data + broken flows)

**Mock/fabricated data shown to users:**
- `frontend/src/components/about/MentorsSection.tsx:29-98` — hardcoded fallback mentors (Deepikasri/Sowmiya/Saran, `@example.com`, invented ratings) rendered on the public `/about` page when the instructor API is empty **or** errors.
- Dashboard charts fed by a self-labeled "mock data generator" (`frontend/src/components/dashboard/charts.tsx:295-329`):
  - `frontend/src/pages/instructor/dashboard.tsx:117-131` — fabricated "Net earnings ~₹4500/week" line chart + hardcoded rating distribution.
  - `frontend/src/pages/dashboard.tsx:56-66` — fabricated student weekly study-time/lessons.
  - `frontend/src/pages/admin/dashboard.tsx:116-126` — fabricated enrollments-vs-completions.
  - Decorative `genTrend` sparklines across all dashboards — headline numbers are real, only the trend shape is invented (cosmetic).
- `frontend/src/pages/Home.tsx:64-197,374-415` — hardcoded marketing stats ("50+ students", "98% satisfaction") + two named testimonials. Marketing copy; verify it doesn't overstate.

**Broken/incomplete flows:**
- `frontend/src/pages/admin/new-course.tsx:24-29` — admin "Add New Course" `handleSubmit` is a no-op (`// TODO: API call`); form silently discards input.
- Cart checkout dead-ends for paid courses (`backend/app/routers/orders.py:157` returns 402) while "Add to Cart" is shown on paid courses (`course-detail.tsx:816`).
- `backend/.env` (prod) `AUTO_VERIFY_EMAIL=true` — email verification bypassed; anyone registers unverified. Set `false` now that SMTP works.

**Migration fragility:**
- No migration-tracking table. `init_db()` (`database.py:80`) `create_all` never adds columns to existing tables; only `courses` self-heals (`ensure_schema()`). Every `backend/migrations/*.sql` must be applied by hand. **Highest risk:** `add_totp_2fa.sql` — an un-applied copy makes every `db.query(User)` 500 (`totp_enabled NOT NULL`) → all auth breaks. Verify it and `edgyy_session_webhook_tracking_*.sql` are applied on the live DB.

---

## P2 — Should-fix (harden before/soon after launch)

- **Default admin passwords in source** — `docker-compose.production.yml:23` (`SashaAdmin@2024`), `seed_admin.py:31` / `seed_admin_simple.py:30` (`SecureAdmin@2024!`). Require `ADMIN_PASSWORD`, fail closed if absent.
- **Weak branded-year secrets** in prod `.env` (`SECRET_KEY`, `JWT_SECRET`, `POSTGRES_PASSWORD=SashaInfinite2024`, `ADMIN_PASSWORD`, SMTP). Rotate to random high-entropy.
- **Verbose error leakage** — many `raise HTTPException(detail=f"...{e}")` / `str(e)` (courses, coupons, cohorts, candidate, certificates, admin, chunked_upload; `main.py:617`). Return generic messages.
- **PII leak** — `backend/app/api/v1/certificate_verification.py:108` returns `student_email` to anyone with a verify code. Gate behind an opt-in (like `users.py:597`).
- **Unauthenticated abuse endpoints** — `payments_proxy.py:626` `/internal/session-failed` (no auth/signature), `video.py:28` `/extract/video` (spawns yt-dlp), `youtube_embed.py:226` `/bulk-validate-videos`.
- **Upload safety** — `uploads.py:93` trusts client `content_type`, stores original extension (stored-XSS via `.html` in `/uploads/`); `:329` `delete_file` builds path from `file_url` with no containment (path traversal, instructor/admin-gated).
- **nginx path bugs** — `nginx/conf.d/default.conf:294` certificate alias points at `/app/certificates` (only exists in backend container; nginx mounts `/var/www/certificates`), and the `:3100` block has no `/certificate-files/` location → cert downloads depend on the out-of-repo host nginx; `:191` streaming proxy targets `backend:8001` but the service is `streaming-service:8001`. Verify both end-to-end.
- **Missing prod config** — `RAZORPAY_WEBHOOK_SECRET` absent (webhook fallback 500s), Edgyy tokens absent (if that integration is live).
- **Broken `.env.example`** — the four example files don't match the real compose contract (`POSTGRES_PASSWORD`/`REDIS_PASSWORD`/`ADMIN_PASSWORD`/Razorpay/Bunny/Edgyy/Firebase/VITE_* undocumented). A fresh deploy from the example won't boot. Collapse to one authoritative file.
- **Compose drift** — prod runs base `docker-compose.yml` with `--reload` + `./backend:/app` bind-mount (dev settings). `docker-compose.production.yml` commits `POSTGRES_PASSWORD=SashaInfinite2024` and password-less Redis with host-exposed DB/cache ports. Reconcile; remove dev flags from prod.
- **Misc** — no per-account login lockout (`MAX_LOGIN_ATTEMPTS` unused; IP-only + 2FA mitigate); Redis "mock fallback" only triggers on ImportError, not connection failure (`core/redis.py:76`); CSP uses `'unsafe-inline'/'unsafe-eval'`; `SecurityHeadersMiddleware` disabled (relies on nginx — direct `:8000` gets no headers); ~94 `print()` in `auth.py`.

**Cosmetic / minor:** instructor bio placeholder "will be available soon" (`course-detail.tsx:1049`), newsletter no-op (`footer.tsx:11`), wishlist local-only (`course-detail.tsx:319`), instructor dashboard hardcoded 0 earnings/reviews (`instructor/courses.tsx:92`), cert `course_level` hardcoded "intermediate" (`certificates.py:934`), `/_thumb` unimplemented (`main.py:562`), analytics tracker disabled (`use-page-view-tracker.tsx:46`), admin blog-templates "coming soon" page, Unsplash thumbnail fallback (`media.ts:74`).

---

## Solid foundation (real credit, do not regress)

JWT HS256 with explicit `algorithms=[…]` (no alg-confusion) + token-type separation; bcrypt hashing; **no SQL injection** in request paths (parameterized/whitelisted, incl. `DATE_TRUNC` whitelist); admin router gates all 82 endpoints with `require_admin`; Razorpay/Edgyy proxy does constant-time compare + HMAC signature verify + re-verifies amount/order against Razorpay; chunked upload well-secured (auth, role, per-session ownership, UUID paths); certificate verification rate-limited + enumeration-resistant; 2FA TOTP available; production SMTP is real and robust; `.env` git-ignored + untracked; `ENVIRONMENT=production`, `DEBUG=false`, `/docs` disabled in prod.

---

## Recommended remediation order

1. **P0-1** add auth to `/admin/import` + `/export/count` (minutes, highest impact).
2. **P0-4** remove/gate the payment-bypass routes + email backdoor.
3. **P0-2, P0-3** rotate + purge committed secrets and Google cookies (history rewrite — coordinate with the team).
4. **P0-5, P0-6** lock down streaming service; fix vite env whitelist + sourcemap; add DOMPurify; move refresh token off localStorage.
5. **P1** remove mock-data fallbacks (About mentors, dashboard charts → real endpoints or hide), fix admin new-course, set `AUTO_VERIFY_EMAIL=false`, verify migrations applied.
6. **P2** work through hardening list.

Confirm `add_totp_2fa.sql` is applied on the live DB immediately (an un-applied copy 500s all auth).
