# Growth OS validation evidence — 2026-09-20

## Completed local checks

- Growth/commercial/runtime backend suite: **38 passed**, including frozen migration roundtrip and the timeout/no-duplicate-order case.
- Related campus, tenancy, webhook and 3D suites: **56 passed**.
- Learning-planner/communication-preference regressions: **22 passed**. A subsequently added lead-to-workspace/version-check test also passed in the final **17-test Growth suite** (117 distinct selected backend tests total).
- Complete frontend suite: **494 passed across 89 files**, including the Growth execution/runtime UI tests.
- Frontend type-check, lint and production build passed. Existing bundle-size, browser-data and mixed static/dynamic import warnings remain; no bundle warning was hidden.
- Synthetic demo seeding completed. The API responded on loopback port 8016 and the Vite preview started on 3016.
- No live payment, bank payout or external promotional message was executed.

## Read-load rehearsal

120 authenticated requests with 8 concurrent clients, including the admin snapshot:

| Run | HTTP failures | p50 | p95 | 1,500 ms target |
| --- | --- | --- | --- | --- |
| Initial/cold local run | 0 | 67.52 ms | 2,275.06 ms | Failed |
| Warmed local run | 0 | 52.85 ms | 109.19 ms | Passed |

Both outcomes are retained under `.local/`. The warm result does not erase the cold failure, prove a consumer-scale capacity target, or validate PostgreSQL, providers, browser journeys or multi-replica writes.

## Blockers and unverified areas

- Docker engine pipe unavailable on this host: PostgreSQL restore and Redis/worker failover were not executed.
- The in-app browser webview failed to attach after a retry. Visual/browser acceptance is unverified; the source build and HTTP/API tests are separate evidence.
- No user-designated staging URL/concurrency target or real sandbox provider acceptance was supplied during this run.
- Tax classification/compliance and physical service delivery require responsible human acceptance.
- Full unified consumer/business identity attribution and trained churn prediction are not claimed by the commercial analytics implementation.

Status: **release candidate for staging, not production-certified**.
