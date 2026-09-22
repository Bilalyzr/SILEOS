---
name: sasha-perf-budget
description: Performance work and budgets
---

Blueprint 8.4/13.1. Load when anything renders or loads.

- Reference device: an 8000-rupee-class Android, 2GB RAM, throttled 3G. A budget miss is a bug in the code, NOT a limitation of the device.
- Measure, never estimate: report draw calls, triangle counts, texture MB, p95 timings, Lighthouse scores. Numbers or it did not happen.
- 3 seconds to interactive on 3G for every page; skeleton then fallback then upgrade for heavy content.
- Backend: check N+1 on every new list endpoint; paginate unbounded sets (see library /mine).
- Frontend: route-split heavy players; debounce search inputs; size images.
