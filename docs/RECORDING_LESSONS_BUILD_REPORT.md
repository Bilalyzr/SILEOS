# Recording Lessons and feature organization — 2026-09-06

## Delivered

- Instructor, student and administrator menus organized into job-based groups; active groups open automatically and compact-group clicks expand the sidebar. Existing links and nested review badges preserved.
- Instructor Recording Lessons workspace, linked from Content Studio and Past classes.
- Self-hosted faster-whisper ASR runtime and multilingual small model installed in this workspace. Real English speech produced four timestamped segments; the persistent worker processed the same local sample successfully.
- Searchable transcript with playback jumps, transcript corrections, editable source notes, chapters and concept links. No remote AI processing in this pipeline.
- Explicit reviewed conversion to an unpublished course lesson, plus source-excerpt questions created as unpublished Assessment Studio drafts.
- Publication/enrollment-gated recording reader and normal published-lesson eligibility in learning plans.
- Durable queue, attempt counts, explicit retry, interrupted-worker recovery and source containment checks. Recording upload commits independently of transcription.

## Validation

- Full backend regression: **1,612 passed, 4 skipped**.
- Final focused backend integration suite: **64 passed**, including two additional checks for planner publication and revoked/cross-course reader access.
- Full frontend regression: **336 passed across 50 files**.
- Final focused frontend suite: **5 passed**, including new real Axios URL-normalization and transcript-search checks.
- Final frontend build passed; lint for changed/new implementation files passed.
- Global frontend baseline remains **26 lint warnings** and **392 TypeScript errors** (one existing unused sidebar binding removed from the prior 393). No new recording/navigation TypeScript errors.
- Local database backed up to `backend/recording_before_0023.sqlite`, migrated to 0023.
- Browser verified nested live review badge, compact-to-expanded group navigation, recording selection, transcript editing, review gating and draft creation.

## Local demonstration and deployment boundary

A clearly labeled **draft** demo course and completed demo class were added using a synthetic English speech sample: course 9, class 16, reviewed draft lesson 26 and one unpublished Assessment Studio question. Its recording workbench is available at `http://127.0.0.1:3002/instructor/recording-lessons?class_id=16`. This demo has local audio only, with no Bunny recording uploaded; it demonstrates transcription/review, not a live CDN stream.

The preview API and separate transcription worker are running locally. No production deploy, git commit, push or live recording upload was performed. Production needs the worker/runtime/model and private recording mount configured as documented. Existing Bunny signing configuration governs media playback. Tamil is supported as a requested transcription language but has not been accuracy-tested on real Tamil classroom recordings. Initial notes are extracts and initial chapters are time-based; instructors supply the reviewed summary and topic titles.

Operational instructions and limitations: `docs/RECORDING_LESSONS.md`. Feature map: `docs/FEATURE_SEGMENTS.md`.
