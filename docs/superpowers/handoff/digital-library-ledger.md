# SDD ledger — plan: docs/superpowers/plans/2026-09-03-digital-library.md

Branch: digital-library (worktree .worktrees/digital-library), forked from revenue-platform @ 00c267c. Plan commit 6c71bc3. 12 tasks.
Key cross-task facts:
- Prices in RUPEES (Numeric/Integer), paise only at Razorpay boundary via max(int(round(price*100)), 100).
- Migration 0005 relaxes order_items.course_id to nullable + adds order_items.ebook_id; ebook lines order_item_type="ebook_item".
- '/library' must be added to axios noSlashEndpoints (Task 8).
- Tasks 5 & 6 (money path) get OPUS reviews.
- Test env: pytest via main checkout "backend/.venv/Scripts/python.exe", cwd worktree backend/; FOREGROUND runs only (no bg wait-loops). Baseline 949P/4S. Frontend vitest baseline 275/275; tsc baseline 378 pre-existing errors.
- Worktree needs npm install --legacy-peer-deps for frontend tasks (react18 vs @react-three/drei peer conflict).

BASELINE CLARIFICATION (controller-verified): main-checkout "949P/4S" includes 9 tests from the concurrent session's UNCOMMITTED tests/test_proxy_webhook_migration.py (untracked → absent from all worktrees). True committed baseline = 944P/4S. Worktree Task-1 result 945P... wait: 944 + 5 new = 949 collected, 945P+4S = 949. Correct and clean.
Task 1: complete pending review — commit c44f942 (ebook models, orders/order_items ebook cols, migration 0005). Implementer CAUGHT+FIXED a real brief bug: downgrade needed batch_op.drop_index before drop_column on SQLite recreate path; added a full-schema preseeded-at-0004 CLI upgrade/downgrade test that exercises it. Suite 945P/4S (= zero regressions vs true 944 baseline).
Task 1: review dispatched.
Task 1: complete — commit c44f942. Review: spec ✅; deviation (drop_index-before-drop_column in downgrade) independently reproduced + confirmed correct+minimal; payment-surface grep clean, 81/81 targeted payment tests green.
Task 1: RULING — Ebook.price_inr Integer (whole rupees) vs courses' Numeric(10,2): ACCEPTED consciously (unit matches; sub-rupee ebook prices not a real need; Integer is strict-safer).
Task 1: carried to Tasks 5/6 (BINDING): admin.py:1751-1790 course_breakdown would label ebook OrderItems as "Course #None" — whoever creates ebook order items must make that loop skip/label ebook lines properly (+ test).
Task 2: dispatched (private storage + upload hardening).

Task 2: implemented + module tests green (19/19), commit 9d94336 � REVIEW NOT RUN (pipeline paused 2026-09-03 for owner weekly-limit break). Successor: review before Task 3.
PAUSED: see docs/HANDOFF_NEXT_AGENT.md on revenue-platform.
