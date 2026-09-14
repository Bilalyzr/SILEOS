# RESTRUCTURE PLAN — type-driven course creation (v2)

Owner feedback 2026-09-04, four fixes + phased roadmap. This file is the
plan of record for the changes made in this pass.

## Fix 1 — Categories & tags are FREE INPUT (no predefined dropdowns)
- create-course.tsx: Category `<select>` (12 hardcoded options) → plain
  text input. Instructor types any category ("Tamil Grammar", "NEET Bio"…).
- Tags already free-form (type + Enter) — unchanged.
- edit-course.tsx: same select→input fix for consistency.
- Backend: accepts any string already — no backend change.
- ACCEPTANCE: no dropdown options exist anywhere for category; any typed
  value saves and renders.

## Fix 2 — Quiz = questions OR scored modules (not "at least 1 question")
- QuizSetupModal: "Add at least one question" guard removed. New rule:
  save requires ≥1 question OR ≥1 interactive module (H5P/game).
- Backend create_quiz already accepts empty questions — module-only quizzes
  persist as-is; their scores flow from h5p_results/game_results into the
  cumulative grade (20% weight, already built).
- ACCEPTANCE: create a quiz with zero questions + one game → 200 + stored
  module visible on the quiz; cumulative-grade reads it.

## Fix 3 — Video lectures: multiple streaming options
The video lecture editor gets an explicit source selector with three
options (all already supported by the backend lesson fields):
  1. Upload file (VideoUpload component → stored/streamed via existing
     video pipeline)
  2. YouTube URL (existing youtube_url field + no-brand player)
  3. Direct URL — Bunny CDN / any MP4/HLS link (existing video_url field)
Radio-style source switch; only the chosen input shows. ACCEPTANCE: all
three paths fill their field and persist through the lesson PATCH.

## Fix 4 — Make the type-driven restructure VISIBLE
- Lecture-type dropdown: instead of HIDING unsupported options, render ALL
  FOUR with unsupported ones DISABLED + an inline reason
  ("games are on SP/UP courses") — the gating becomes impossible to miss.
- Step-1 type cards keep the "Enabled tools · coming soon" strip.
- NOTE: changes are in Create Course (instructor) — students/landing page
  show nothing, by design. Hard refresh (Ctrl+F5) if React cached.

## Phased roadmap (confirmed direction, built in order after this pass)
- Phase 2 — 3D GLB import for MP/UP: upload → hardening (mirror ebook/H5P
  pattern) → Three.js viewer lesson type → "coming soon" flag goes live.
- Phase 3 — AI teaching: transcribe recorded lectures → curated deeper-
  learning lessons; custom test-paper generator personalised per student
  learning pattern (uses ai_jobs audit + ai-draft governance).
- Phase 4 — Virtual sims/labs in instructor toolkit + curriculum + learner
  path; 3D-object match/verify assessments (parameter-based success rules).
- Live classes: past-classes report API is LIVE (12 classes verified);
  instructor report page + download-then-delete UI is a small page build.
