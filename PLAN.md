# Implementation Plan — Critical Fixes from CODE_REVIEW.md

Goal: ship the Critical and high-impact Important fixes as a series of small, independently verifiable changes. Each task lists the files touched, the exact change, and how to verify.

> No automated tests exist. Every task ends with a manual verification step. Do these in order — later tasks depend on earlier model fixes.

---

## Task 1 — Settle the `Enrollment` schema (I1)

**Why first:** every payment fix below depends on knowing the real column name.

**Files:** `backend/app/models/enrollment.py`, then grep across `backend/app/`.

**Steps:**
1. Open `backend/app/models/enrollment.py`. Record the actual FK column (almost certainly `user_id`).
2. Grep `Enrollment.student_id` and `student_id=` references in routers/services. Replace with the real name.
3. Grep `Enrollment.user_id` to confirm consistency.

**Verify:** start the backend; the broken queries previously raised `InvalidRequestError`. Hit `/api/v1/payments/transactions` while logged in — should return `200 []` (or real data) instead of 500.

---

## Task 2 — Decide which payment flow is canonical (I8)

**Why second:** stops us fixing dead code.

**Steps:**
1. Search frontend `frontend/src/api/` and components for the actual call: `create-payment-intent` vs `create-order`/`verify`.
2. Whichever the frontend uses is the keeper. Delete the other route handlers from `payments.py` and the corresponding schemas.

**Verify:** start frontend + backend, attempt a course purchase (Razorpay test mode), observe network panel — only one `/payments/*` POST should fire on "Pay".

---

## Task 3 — Server-side amount + order verification (C1, C3)

**Files:** `backend/app/routers/payments.py` (the surviving flow only).

**Steps:**
1. In the order-creation handler: ignore any `amount` from the request. Look up `course = db.query(Course).filter(...).first()`. Compute `amount_paise = int(course.course_price * 100)`. Pass that to Razorpay.
2. Add `notes={"course_id": course.id, "user_id": current_user.id}`.
3. In the verify handler: after signature check, call `client.order.fetch(razorpay_order_id)`. Assert `order["notes"]["course_id"] == request.course_id` and `order["notes"]["user_id"] == current_user.id` and `order["amount_paid"] == int(course.course_price * 100)`. 400 on any mismatch.
4. Persist a `Payment` row with `razorpay_order_id`, `razorpay_payment_id`, `amount`, `status="completed"`, `user_id`, `course_id`.

**Verify:**
- In Razorpay test mode, complete a real purchase end-to-end → enrollment row created, `Payment` row created, course visible in dashboard.
- Manually craft a request to `/verify` with a `course_id` different from the one the order was made for → expect 400.
- Manually call `/create-order` with `amount=1` for a paid course → resulting order should have the real price, not 1.

---

## Task 4 — Timing-safe signature compare (I3)

**Files:** `payments.py`.

**Step:** replace `if generated_signature != razorpay_signature` with `if not hmac.compare_digest(generated_signature, razorpay_signature)`.

**Verify:** valid signature still works; tamper one byte → 400.

---

## Task 5 — Fix `Transaction` import or remove the references (C2)

**Files:** `payments.py`, possibly `backend/app/models/payment.py`.

**Steps:**
1. Look in `backend/app/models/payment.py` for a `Transaction` class. If it exists: `from app.models.payment import Transaction` at top of `payments.py`.
2. If it does not exist: delete the `Transaction(...)` blocks from `confirm_payment` and `request_refund`. Leave a TODO if a transaction-log table is on the roadmap.

**Verify:** import the module — `python -c "from app.routers.payments import router"` — must succeed. Hit `/refund` end-to-end with a test payment → no NameError.

---

## Task 6 — Reject refresh tokens at access-token gates (C6)

**Files:** `backend/app/core/security.py`, `backend/app/services/auth_service.py`.

**Steps:**
1. Add `expected_type: str = "access"` to `verify_token`. Decode, then `if payload.get("type") != expected_type: raise JWTError("Wrong token type")`.
2. In `auth_service.get_current_user` and `get_optional_current_user`, the existing call passes "access" implicitly via the default.
3. Wherever refresh tokens are validated (search `verify_token` callers — the refresh endpoint), pass `expected_type="refresh"`.

**Verify:**
- Log in → use access token → 200.
- Use refresh token in `Authorization: Bearer ...` header on a protected route → 401.
- Refresh endpoint with a real refresh token still issues a new access token.

---

## Task 7 — Gate streaming endpoints on enrollment (C4)

**Files:** `backend/app/routers/video_streaming.py`, plus standalone `streaming-service/video_streaming.py`.

**Backend router (`/api/v1/stream/...`):**
1. Add `current_user: User = Depends(AuthService.get_current_active_user)` to `/stream/{video_id}`, `/info/{video_id}`, `/extract`.
2. Add a lookup: `lesson = db.query(Lesson).filter(Lesson.video_id == video_id).first()` (or whatever maps a YouTube ID to a course). Then `enrollment = db.query(Enrollment).filter(user_id=current_user.id, course_id=lesson.course_id, enrollment_status="enrolled").first()`. 403 if missing. Admins/instructors of the course bypass.
3. Remove `/cache/status` from production or restrict to admin (it leaks video URLs).

**Standalone service:**
1. Backend issues a short-lived signed token (HMAC of `video_id|user_id|exp`) when enrollment is verified, included in the redirect URL.
2. Standalone service verifies the token before streaming. Reject anything without a valid token. Tighten `allow_origins` to the frontend domain.

**Verify:**
- Logged-out request to `/api/v1/stream/abc123` → 401.
- Logged-in but un-enrolled student → 403.
- Enrolled student → 200 stream.
- Direct hit on standalone service without token → 401.

---

## Task 8 — Fix upload directory path (C5)

**Files:** `backend/app/routers/uploads.py`, `backend/app/core/config.py`.

**Steps:**
1. Add `UPLOAD_DIR: str = "/app/uploads"` to `Settings`.
2. In `uploads.py`, `from app.core.config import get_settings; UPLOAD_DIR = Path(get_settings().UPLOAD_DIR)`.
3. Delete the hard-coded `/www/wwwroot/...` path.

**Verify:** in container, `docker-compose exec backend ls /app/uploads` shows the mount; upload an image via `/api/v1/uploads/image`; file appears at `./uploads/images/...` on the host and is reachable at `http://localhost:3100/uploads/images/<name>`.

---

## Task 9 — Lock down upload validation and deletes (I4, I5)

**Files:** `uploads.py`, possibly a new `Upload` model.

**Steps:**
1. Install/confirm `python-magic` in `requirements.txt`. Add a helper that reads the first 4KB and asserts MIME from magic bytes matches the claimed `content_type`.
2. Replace `get_file_extension(file.filename)` with a fixed mapping from validated MIME → extension (e.g. `image/png → .png`). Never echo the user extension.
3. For deletes: either restrict to `require_admin`, or add an `Upload(id, url, uploaded_by, created_at)` table and check ownership.

**Verify:**
- Rename `evil.html` to `evil.png`, fake content-type → upload rejected by magic-bytes check.
- Instructor A uploads a file; instructor B attempts delete → 403.

---

## Task 10 — Misc correctness (I2, I7, I9, I10, M1, M2, M4)

Bundle into one PR — small mechanical fixes:

- **I2:** wrap webhook handler body in `try/except`; return 200 with logged warning for unknown events.
- **I7:** `video_streaming.py:208` change to `(now - v[1]) < CACHE_TTL`.
- **I9:** wrap each multi-step write in payment routes with `try/except` → `db.rollback()` → re-raise.
- **I10:** rewrite `get_instructor_earnings` using `func.count` + `func.sum` aggregates.
- **M1:** replace Python increment of `course.total_enrollments` with `db.query(Course).filter(id=...).update({Course.total_enrollments: Course.total_enrollments + 1})`.
- **M2:** widen `except JWTError` → `except (JWTError, ValueError)` in `auth_service.get_current_user`.
- **M4:** in `upload_video`, exit the `with` before `os.remove(file_path)` on size overflow.

**Verify:** smoke each touched endpoint; all should still return 200 on the happy path.

---

## Execution notes

- Do tasks 1, 2 sequentially. Tasks 3-10 can be assigned to parallel subagents *after* 1 and 2 land.
- Recommend committing after each task (this repo isn't under git — initialize first if you want safe rollback).
- After Task 7, retest payments end-to-end since enrollment lookup is now load-bearing for video access.
