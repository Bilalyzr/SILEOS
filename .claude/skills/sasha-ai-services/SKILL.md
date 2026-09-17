---
name: sasha-ai-services
description: Any AI-generated content feature
---

Blueprint 15 + the live /api/v1/ai integration. Load for AI work.

Four governance rules (implemented in routers/ai.py):
1. AI output is a DRAFT a human approves — drafts land in question banks tagged ai-draft; NEVER auto-publish to live content.
2. No AI grade of record, ever.
3. Learners always know when they are talking to AI.
4. Every call logged: model, input, output, error (the ai_jobs table).

Plus:
- No key configured means an honest 503 with setup guidance; never fake output.
- Model output passes the SAME validation as manual input; invalid items are reported, not stored.
- Provider calls are wrapper functions (monkeypatch in tests; no network in CI).
- Prompt-injection defence: instructor topic strings are data, never concatenated into the system prompt; the system prompt is a constant.
- Cost: meter by logging; route cheap tasks to cheap models when that lands.
