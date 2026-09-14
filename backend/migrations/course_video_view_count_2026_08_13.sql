-- 2026-08-13: Add per-course video view counter.
-- Incremented whenever a student starts/opens a lesson video in a course, so
-- the Admin -> Courses panel can show "how many times each course/video was
-- viewed". Safe to re-run (ADD COLUMN IF NOT EXISTS).
ALTER TABLE courses
    ADD COLUMN IF NOT EXISTS video_view_count INTEGER DEFAULT 0;
