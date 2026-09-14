# Code Review — SashaInfinity LMS

Audit date: 2026-04-20. Scope: backend logic correctness and security in payments, auth, video access, uploads. No tests exist; findings come from static reading.

Severity: **Critical** = exploitable / drops revenue or data; **Important** = wrong behavior under normal use; **Minor** = correctness niggle.

---

## CRITICAL

### C1. Client-supplied amount accepted in `/api/v1/payments/create-order`
`backend/app/routers/payments.py:389-426`. The handler reads `amount` from the request body and passes it straight to Razorpay. Course price is never compared. A user can submit `amount=1` for a ₹10,000 course, then call `/verify` with the resulting valid signature and get enrolled.

**Fix:** Ignore client `amount`. Compute `int(course.course_price * 100)` server-side after fetching the course.

### C2. `Transaction` model used but never imported
`payments.py:169` (in `confirm_payment`) and `payments.py:331` (in `request_refund`). Calling either endpoint raises `NameError: Transaction is not defined`. The `/confirm-payment` and `/refund` endpoints are completely broken.

**Fix:** Add `from app.models.payment import Transaction` (or wherever it lives), or remove these references if `Transaction` isn't a real model.

### C3. `/api/v1/payments/verify` doesn't tie payment to course price or order ownership
`payments.py:429-482`. After signature verification, the handler enrolls the user in `course_id` (from request body) without checking:
- That the Razorpay order was created for *that* course/user (the `notes` field exists for this).
- That the captured amount matches `course.course_price`.
- That `payment` is recorded in the DB.

Combined with C1, this is the full bypass: pay ₹1, get any course.

**Fix:** Look up the order via `client.order.fetch(razorpay_order_id)`, verify `notes.course_id == course_id`, `notes.user_id == current_user.id`, and `amount_paid == course.course_price * 100`. Persist a `Payment` row.

### C4. Streaming endpoints have no auth or enrollment check
`backend/app/routers/video_streaming.py`. `/stream/{video_id}`, `/info/{video_id}`, `/extract`, `/cache/status` are all public. Any unauthenticated client can stream paid course content via the proxy. The standalone `streaming-service/` is similarly open (`allow_origins=["*"]`).

**Fix:** Inject `Depends(AuthService.get_current_active_user)` and verify enrollment for the lesson that owns this `video_id`. The standalone `streaming-service` should accept a short-lived signed token issued by the backend after enrollment is confirmed, and reject everything else.

### C5. Hard-coded host path for uploads breaks in Docker
`backend/app/routers/uploads.py:18` sets `UPLOAD_DIR = Path("/www/wwwroot/sasha_lms/...")`. The compose file mounts the host `./uploads` to `/app/uploads`. Uploads through this router either fail (path doesn't exist in container) or write to a path that nginx doesn't serve.

**Fix:** Read from settings/env (e.g. `settings.UPLOAD_DIR` defaulting to `/app/uploads`).

### C6. Refresh tokens accepted as access tokens
`backend/app/core/security.py:57-63` decodes any JWT and returns it; `auth_service.get_current_user` doesn't check `payload["type"] == "access"`. A leaked refresh token (longer-lived, 7 days) can be used directly to call protected endpoints.

**Fix:** In `verify_token`, accept an `expected_type` arg; have `get_current_user` pass `"access"`. Have refresh endpoint pass `"refresh"`.

---

## IMPORTANT

### I1. `Enrollment` model field inconsistency (`user_id` vs `student_id`)
Same file uses both: `Enrollment.user_id` (lines 55, 462, 472) and `Enrollment.student_id` (lines 158, 253, 307). Only one column actually exists on the model. One set of queries will throw at runtime, depending on which is real. Inspect `app/models/enrollment.py` and pick one — most likely `user_id`, which would mean `confirm_payment` and the webhook handler are also broken (pairs with C2).

**Fix:** Audit the model, normalise all queries to the real column name. Add a quick smoke script that queries each path.

### I2. Webhook signature path skipped on JSON parse failure
`payments.py:218-281`. After signature verification, `event_data = json.loads(payload)` and then `event_data["event"]` and nested keys are accessed without `try/except`. A malformed (but signed) Razorpay payload returns 500. Worse, the handler returns `{"status": "success"}` even when the matched event doesn't update anything.

**Fix:** Wrap event handling in `try/except`, log unknown event types, return 200 with `{"status": "ignored"}` for unhandled events.

### I3. Timing-safe compare missing on Razorpay signature check
`payments.py:455`. `if generated_signature != razorpay_signature` is not constant-time. Use `hmac.compare_digest`.

### I4. File-delete endpoint allows any instructor to delete any file
`uploads.py:217-264`. There is no ownership check (no DB lookup for "did you upload this?"). Any logged-in instructor can delete any other instructor's course thumbnails or videos by guessing the URL. The docstring even claims ownership is enforced — it isn't.

**Fix:** Either require admin only, or store an `Upload` row with `uploaded_by` and check that `current_user.id == upload.uploaded_by` (or admin).

### I5. MIME type alone is trusted
`uploads.py` validates `file.content_type` (set by the client). A malicious client can upload `evil.html` claiming `image/png`. Combined with the file extension being preserved from `original_filename` (line 79, 125, 195), an attacker could store `xxx.html` if their MIME header says image. Nginx serves `/uploads/` directly.

**Fix:** Validate file magic bytes (`python-magic` or read first N bytes), and force a safe extension matched to the validated type — never trust the client extension.

### I6. `_url_cache` is reused for two different value shapes
`video_streaming.py`. `get_video_url` writes `_url_cache[video_id] = (url, fetched_at)`; `extract_video_url` writes `_url_cache[f"{video_id}:{quality}"] = (url, fetched_at)`. Both read from the same dict but with different key schemes. Not actively crashing, but adds confusion and risks future cache poisoning.

**Fix:** Two separate dicts, or normalize the key.

### I7. `/cache/status` filter is logically inverted
`video_streaming.py:208`: `active = {k: v for k, v in _url_cache.items() if v[1] > now}`. `v[1]` is `fetched_at` which is always `<= now`, so `active` is always `{}`. Probably meant `(now - v[1]) < CACHE_TTL`.

### I8. `/create-payment-intent` and `/confirm-payment` flow appears to be dead code shadowed by `/create-order` + `/verify`
Two parallel flows with overlapping intent. Confirm with the frontend which is actually used; delete the other to remove an attack surface (the dead flow has the broken `Transaction` import in C2).

### I9. No DB rollback on exceptions in payment paths
None of the payment / enrollment handlers wrap their multi-step DB writes in `try/except` with `db.rollback()`. A mid-flow exception leaves partial state (payment row without enrollment, or vice versa). Combined with C2/I1 this makes recovery painful.

**Fix:** Use a `try/except/finally` or context-manager pattern; explicit `db.rollback()` on failure.

### I10. `get_instructor_earnings` does N×2 queries for sales totals
`payments.py:382-385` re-queries `Payment` per course inside a `sum([...])`. Simple fix: aggregate via SQL `func.count` and `func.sum`.

---

## MINOR

- **M1.** `payments.py:74` — `course.total_enrollments` is incremented in Python without a row lock; concurrent enrollments race. Use SQL `UPDATE ... SET total_enrollments = total_enrollments + 1`.
- **M2.** `auth_service.py:76` — `int(user_id)` raises `ValueError` (not `JWTError`) if `sub` is non-numeric (e.g. an email-verification token); the surrounding `try/except JWTError` won't catch it, returning a 500. Wrap or expand the except clause.
- **M3.** `security.py:20-21` — token lifetimes are module constants; CLAUDE.md notes settings has `JWT_SECRET` separate from `SECRET_KEY`, but security.py only uses `SECRET_KEY`. Decide if you need separate secrets and use them, or remove the unused setting.
- **M4.** `uploads.py:101-157` (`upload_video`) — on size-limit hit, `os.remove(file_path)` runs while the file handle is still open inside the `with` block. On Windows this would fail; on Linux it's fine. Move the cleanup outside the `with`.

---

## What I did NOT review (out of scope or out of time)

- Frontend logic
- `certificates`, `quizzes`, `assignments`, `coupons`, `wishlist` routers
- CORS/security middleware in depth
- The full `streaming-service/` Python file (only behavior inferred from CLAUDE.md + the proxy router)

If you want a deeper pass on any of these, ask and I'll continue.
