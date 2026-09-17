---
name: sasha-mobile-offline
description: Mobile, offline, and sync features
---

Blueprint 3.12 + roadmap P9. Load for offline or sync work.

- Offline is a FIRST-CLASS state, not an error state (UI principle 8).
- Sync queue: ordered replay with idempotent server handlers (the money path already models this — gateway_payment_id dedupe). Conflict policy per data type: last-write-wins for progress state; server-authoritative for grades and attempts.
- Auth expiry mid-queue: the queue survives re-auth; never drop queued items on 401 — park and retry.
- Low-bandwidth mode: data-saver video, downloadable assets, PWA shell.
- .h5p packages and ebooks are self-contained, so they bundle; results and download receipts queue.
- Test: kill the connection mid-action, restore, verify zero lost work.
