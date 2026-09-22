# Security-Fix Plan: Federated-Login Bypass + Minor Audit Items

## Context
Security audit 2026-08-19 (security-audit-artifacts/security-audit-2026-08-19.md) found the
federated-login bypass (critical) plus several quick-win issues. This batch fixes them in one
task, shipped through the standard SDD + CI/CD pipeline.

## Global Constraints
- Worktree /root/sasha-fix3, branch fix/security-audit (from current main).
- Implementers: no pushes, no docker, no real DBs; pytest gate
  (/opt/sasha-ci/venv/bin/python -m pytest -q) fully green (48 passed/3 skipped baseline).
- Preserve API shapes except the specified behavior changes. No new deps. No print().

## Task 1 — Federated-login hardening + minor security fixes
1. FEDERATED GATE (critical): in backend/app/routers/auth.py —
   a. Add a helper (e.g. `_validate_federated_claims(decoded_token) -> None`) that raises
      HTTPException 403 when: `decoded_token.get("email_verified") is not True`, OR
      `decoded_token.get("firebase", {}).get("sign_in_provider")` is not in an allowlist
      (start with just "google.com"). Call it in BOTH google_login (~1171) and
      complete_google_login (~1319) BEFORE any account lookup/token minting.
   b. TOTP gate parity: when the matched user has totp_enabled, do NOT mint full
      access+refresh tokens in the federated path directly. Mirror the password-login flow
      (auth.py ~117-139): issue the same pending-2FA response the password path uses
      (reuse its exact schema/shape) and require the existing /auth/2fa/verify (or
      equivalent) step to complete login. Read the password path carefully and reuse its
      mechanism/fields so the frontend 2FA screen works unchanged for Google logins too.
   c. Tests: unit tests for the claim-validation helper (verified/unverified email,
      provider allowlist, missing claims). Integration-style test that a totp_enabled user
      logging in via the google path receives the pending-2FA shape, not tokens (mock the
      firebase verification boundary as the existing tests do).
2. VIDEO_SECRET: backend/app/routers/player.py — fail fast at import/module load when
   VIDEO_SECRET equals the default ("sasha-video-secret-change-this") in production
   (ENVIRONMENT=production). Keep default allowed for tests/dev. Controller will set the
   real value in .env.
3. LOGIN RATE LIMITER: backend/app/core/security_middleware.py —
   a. Fix the path match: recognize BOTH '/auth/login' and '/api/v1/auth/login' (use
      endswith('/auth/login') or startswith tuple covering the mounted prefix; also cover
      the '/auth/login/' trailing-slash variant seen in traffic).
   b. Client IP: use the LAST entry of X-Forwarded-For (nearest trusted proxy), not the
      first. Apply to _get_client_ip used by rate limiting (keep other uses consistent).
   c. Test: unit test the path matcher + XFF parsing.
4. CERTIFICATE XSS: backend/app/routers/certificates.py (~373-378 and ~712-717) —
   html.escape() every value substituted into certificate HTML templates (student name,
   course title, instructor name, any other replace() values). Test: a display_name with
   `<img src=x onerror=...>` comes back escaped in the rendered HTML.
5. LOGIN ENUMERATION: backend/app/services/auth_service.py + routers/auth.py login —
   return ONE generic message ("Invalid email or password") for both unknown-email and
   wrong-password; keep the unverified-account gate as-is (product behavior). Test asserts
   identical message/shape for both cases.
6. PASSWORD RESET: auth.py reset-password — (a) single-use: store password_reset_at on
   the user (column exists? if not, reuse Redis with the token jti; simplest robust:
   embed jti claim, store jti in Redis with TTL = token life, delete on use, reject if
   missing) — (b) apply the RegisterRequest password-complexity validator to the reset
   schema. Tests: replayed token rejected; weak password 422.
7. SSRF: backend/app/routers/video_streaming.py extract (~206-251) — validate extracted
   id with re.fullmatch(r'[A-Za-z0-9_-]{11}') and pass the REBUILT canonical URL
   (https://www.youtube.com/watch?v=<id>) to extract_info; also validate `quality` against
   a small allowlist before interpolation. Test: non-canonical URLs are rejected/sanitized
   to canonical form.
8. UNAUTH yt-dlp DoS: backend/app/routers/video.py /extract/video — add
   Depends(get_current_user) (any authenticated user) + a simple module-level
   concurrent-extraction semaphore (e.g. 4) with 403/429 when full. Test: endpoint now 401
   without a token.
9. CHUNKED UPLOAD: backend/app/routers/chunked_upload.py — at /complete, validate the
   final extension + content_type against a per-upload_type whitelist (mirror
   uploads.py:127-150 /image pattern); enforce cumulative chunk bytes vs declared
   file_size during /chunk (reject overshoot). Test: .html via upload_type=image → 400.
10. player.py:95 — fix wrong column `lesson.video_url` → `lesson.lesson_video_url`.

## Post-task (controller)
Review → fix loop → push via pipeline → verify → set real VIDEO_SECRET in production .env
(+ redeploy or restart backend) → verify stream-url works for a legit lesson.
