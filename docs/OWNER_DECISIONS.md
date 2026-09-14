# Owner Decisions

Decisions bind all future builds. Newest last.

## OWNER DECISIONS â€” recorded 2026-09-05 (v2.0 Â§14 answers)

1. **Escape hatch:** CONFIRMED â€” "Add more tools" panel, defaults not walls.
2. **Assessment weights:** owner asked for plain-English explanation before deciding (explanation delivered 2026-09-05; default Â§5.3 weights apply until changed).
3. **Recording retention (SP):** recordings kept on server **1 year**, then deleted.
   Live class deletion: requires **instructor approval**.
4. **Competitive exams:** **JEE and NEET** first.
5. **Mastery graph:** cross-type, learner-scoped from day one â€” CONFIRMED.
6. **Games:** built in-house (game builder) AND an instructor **marketplace**
   with drag-and-drop into courses.

## ASSUMPTIONS made during the v2.0 gap build â€” 2026-09-05 (owner to confirm or change)

Each of these is a default I picked to keep building; every one is a single constant or setting.

7. **Recording retention default** = the ceiling (365 days, decision 3). Soft-deleted recordings stay restorable for **30 days**; expiry warnings go out at **14 and 3 days**. (`RECORDING_RETENTION_MAX_DAYS`, `class_report_service`)
8. **Tier parity rule:** a graded scorable item whose tier floor is better than T4 cannot be published (422). Practice-only items are exempt.
9. **Parent View defaults by type:** SP = attendance + completion only; UP adds scores; MP = attendance + completion. Instructors change it per course in Settings â†’ Guardian visibility.
10. **Streak freezes:** allowance = the most generous `streak_freeze_days_per_month` across the learner's enrolled courses; a missed day is covered automatically; counters reset monthly.
11. **Item auto-flag thresholds (Engine D):** facility < 0.20 or > 0.95 at â‰¥ 10 attempts; discrimination < 0.10 (or negative) at â‰¥ 6 attempts. Flags are advisory, never auto-edit.
12. **Graded-item answer guard (Engine C):** the tutor refuses when a message matches a course quiz question (â‰¥ 80% word overlap or containment) â€” before any AI call, no key needed.
13. **Adaptive lesson mode from mastery:** < 40% recover, < 75% consolidate, else extend (mastery estimates are 0â€“100).
14. **GLB budgets (WP9):** hard reject at 1.5M triangles or 64 MB textures; per-tier soft caps T1 500k/24 MB, T2 150k/8 MB, T3 50k/4 MB (warnings only). Mobile GLB size hint 25 MB in the Tier Preview.
15. **Teach-it-back XP:** +15 for a first explanation per concept, +5 at 3 helpful votes, +10 at 10; explanations count as a weak (0.3) mastery signal at 70%. Owners can hide explanations.
16. **Next-class agenda** is computed from data (report, mastery graph, open questions/reports) and needs no AI; the AI write-up is optional and only when `GLM_API_KEY` is set.
17. **DigiLocker / APAAR:** an adapter only â€” issuer onboarding (NeGD credentials) and APAAR-ID capture are owner-owned; until then the button answers an honest 503.
18. **Dev-only:** `RATE_LIMIT_REQUESTS_PER_MINUTE=600` in the preview launch config; production keeps the 60/min/IP default â€” decide whether that is enough for a classroom on one NAT IP.

Reminders (owner-owned, never done by the builder): `GLM_API_KEY`, Meta WhatsApp Cloud API credentials (`WHATSAPP_*`), GeoGebra licence, DigiLocker issuer credentials, Razorpay webhook secret.

## INTERVENTIONS NEEDED â€” roadmap loop 2026-09-06

19. **GLM key** (rotated) â†’ `backend/.env` `GLM_API_KEY=` and the preview `launch.json`; then ask for the live AI verification pass.
20. **Superseded 2026-09-10:** WhatsApp uses Meta Cloud API with one consent record per SashaInfinity account. Users manage consent in Communication preferences; institution and global Communications Center campaigns reuse it. Guardian digests are not sent automatically. See `docs/WHATSAPP_CLOUD_SETUP.md`.
21. **Razorpay dashboard:** create Offers for membership coupons (link with the "membership offer" action on Admin â†’ Coupons); confirm EMI/pay-later is enabled on the merchant account (checkout now shows those blocks).
22. **Flutter toolchain** on a build machine for mobile parity (R4) and downloads (R9).
23. **gltf-transform / Blender** on a build host for pre-generated 3D tiers; **ffmpeg** for audio-only renditions (R9).
24. **DigiLocker / NeGD issuer credentials** for certificate issuance (R10).
25. **Rate limit in production** stays 60/min/IP â€” classrooms behind one NAT may need 300+.

26. **Retention rule thresholds (round 2):** streak nudge from 2 days, near-certificate at 80%, re-engagement after 7 quiet days every 14 days, weekly digest every 7 days. Change in `services/retention_service.py` constants.
27. **Media tools on the production host:** `ffmpeg` and `@gltf-transform/cli` must be installed (both verified on the dev machine); tier builds are on-demand per model from the editor's 3D kit.
28. **Redis outage behaviour:** rate limits fail OPEN for 30 s at a time when Redis is unreachable â€” availability over strictness. Reverse in `security_middleware.py` if you prefer 503s.
29. **Learning-signal thresholds:** hesitation = 45 s on a question, answer churn = 2+ changes, rewind = seek back >3 s, skip = seek forward >10 s, early quit = leaving between 5% and 60% of a lesson, profile window 60 days. All constants at the top of `services/learning_signals_service.py`.
30. **Adaptive practice is self-service and ungraded for the gradebook.** It feeds the mastery graph (weight 0.8) but never a quiz score; essay/open-ended questions are never included. If you want adaptive sets to count towards grades, that is a separate decision (it would need the manual-review path).
31. **Learners see only their own signals.** Instructors see per-lesson heat-maps for everyone and per-learner profiles only for courses they can edit; no cross-course or cross-instructor view exists by design.


32. **Astra cycle 1 defaults (2026-09-06; assumptions, owner may change):**
Hot-segment alerts use a seven-day window, a positive score >=3 times the
median of observed segments in that lesson, and >=3 distinct learners.
Unobserved segments do not enter the median. Cooldown is seven days per
editor + lesson + segment; recipients are owner and collaborators, not every
platform admin. Course hotspot concept counts derive from lesson behaviour
in the requested window. Adaptive focus doubles weights with a minimum
pre-doubling weight of one for concepts lacking evidence. Weak-concept quiz
feedback obeys reveal_never and excludes unfinished manual grading.
Transcription was pending at cycle 1; see confirmed decision 34 below.


33. **Learning planner defaults (2026-09-06; implementation assumptions):**
One goal per enrolled course; 30 minutes/day default, editable from 5 to 180.
Target date up to two years ahead; local calendar uses the learner-selected IANA
zone. Assessment diagnosis uses the latest five course records within 60 days and
a below-60% threshold. A check uses up to three published linked auto-gradable
questions, requires at least two, and targets 75%. Successful practice schedules
a delayed check three days later. Insufficient/failed checks need instructor
support. Budgets are per course, with their sum displayed. No AI provider required.
These are transparent defaults, not owner-confirmed pedagogical claims. Full
behaviour, validation limits, and deployment notes: `docs/LEARNING_PLANNER.md`.
Transcription was separate from this release; see confirmed decision 34 below.


35. **Assessment Studio defaults (2026-09-06; implementation assumptions):**
Two distinct usable questions establish minimum practice/reserve coverage; the UI
recommends three practice and three reserved delayed-check questions. Authoring
supports five objective/exact-answer types. Manual review requires a note and
binds a content signature; the same authorized instructor may review and publish.
No second-person approval requirement is implied. Publication freezes question
content, and retirement preserves existing session grading. Delayed planner
checks prefer unseen prompts and report reuse when fresh coverage is exhausted.
No AI provider was added; existing bank drafts can be copied and repaired before
review. These defaults may be adjusted; see `docs/ASSESSMENT_STUDIO.md`. Decision
34 below records the subsequently confirmed transcription provider choice.


34. **Self-hosted transcription (owner confirmed, 2026-09-06):** The owner chose
"Self-hosted transcription: process recordings locally, with no external transcription API required."
The implementation uses faster-whisper in an isolated runtime, with a local multilingual model.
Audio is never sent to a transcription or language-model API in this workflow.

37. **Recording lesson defaults (implementation assumptions, 2026-09-06):**
Three-minute initial chapter boundaries, extractive notes and matching existing course concepts;
instructors correct these before conversion. Questions are literal excerpt cloze drafts.
Conversion creates one unpublished lesson per class; normal course publication makes it eligible
for the planner. One-hour ASR timeout, durable jobs, explicit retry on failure, four CPU threads
and int8 inference by default. Production model/hardware quality must be measured with real
English/Tamil recordings. See docs/RECORDING_LESSONS.md.


### Operations and course backup defaults (implementation choices, 2026-09-06)

The owner requested course creation through uploads, automatic backup detection/restoration, and the previously proposed operations work. Imports/restores create new drafts and preserve existing courses; users review content before publishing. Course packages exclude learner/payment records and keep remote media as explicit references. A preview lasts 24 hours. These are implementation defaults, not additional owner approval requirements.

Mobile delivery covers learning goals/tasks, practice/follow-up checks, instructor intervention reviews and recording transcripts. Real recording accuracy and Android/iOS device installation remain verification tasks. See OPERATIONS_BUILD_REPORT.md and COURSE_BACKUPS.md.
