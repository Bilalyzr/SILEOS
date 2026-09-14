-- add_lesson_h5p_columns.sql — 2026-09-03
--
-- The learning-experience wave's Lesson model declares H5P support columns
-- (lesson_content_type, h5p_content_id) that init_db/create_all could not
-- add to the EXISTING lessons table — create_all only creates missing
-- TABLES, never missing COLUMNS. Every course-listing query selects the new
-- columns, so listings 500'd with UndefinedColumn until this runs.
-- Re-run-safe guards included.

ALTER TABLE lessons ADD COLUMN IF NOT EXISTS lesson_content_type VARCHAR(20) NOT NULL DEFAULT 'video';
ALTER TABLE lessons ADD COLUMN IF NOT EXISTS h5p_content_id INTEGER REFERENCES h5p_contents(id);
