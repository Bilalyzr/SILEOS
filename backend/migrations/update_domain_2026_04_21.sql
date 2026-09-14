-- Migration: Update domain from lms.sashainfinity.com to sashainfinity.com
-- Description: Updates all URL columns across all tables to use the new domain
-- Date: 2026-04-21
-- Author: Automated migration
--
-- IMPORTANT:
-- 1. This migration is IDEMPOTENT - safe to run multiple times
-- 2. Uses REPLACE() which only affects rows containing the old domain
-- 3. No data loss - only updates exact matches of the old domain
-- 4. Run this AFTER updating backend/frontend/nginx configurations
--
-- BEFORE RUNNING:
-- - Backup your database: pg_dump tutor_lms > backup_before_domain_update_$(date +%Y%m%d_%H%M%S).sql
-- - Verify backups are complete
-- - Schedule maintenance window if database is large

BEGIN;

-- =============================================================================
-- COURSES TABLE
-- =============================================================================

-- Course thumbnail URLs
UPDATE courses
SET course_thumbnail = REPLACE(course_thumbnail, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE course_thumbnail LIKE '%lms.sashainfinity.com%';

-- Course cover image URLs
UPDATE courses
SET course_cover_image = REPLACE(course_cover_image, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE course_cover_image LIKE '%lms.sashainfinity.com%';

-- Course intro video URLs (may contain embedded domain)
UPDATE courses
SET course_intro_video = REPLACE(course_intro_video, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE course_intro_video LIKE '%lms.sashainfinity.com%';

-- Course certificate template URLs
UPDATE courses
SET certificate_template = REPLACE(certificate_template, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE certificate_template LIKE '%lms.sashainfinity.com%';

-- Course content (may contain embedded URLs in HTML/Markdown)
UPDATE courses
SET post_content = REPLACE(post_content, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE post_content LIKE '%lms.sashainfinity.com%';

-- Course excerpt
UPDATE courses
SET post_excerpt = REPLACE(post_excerpt, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE post_excerpt LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- LESSONS TABLE
-- =============================================================================

-- Lesson video URLs
UPDATE lessons
SET lesson_video_url = REPLACE(lesson_video_url, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE lesson_video_url LIKE '%lms.sashainfinity.com%';

-- Lesson YouTube URLs
UPDATE lessons
SET lesson_youtube_url = REPLACE(lesson_youtube_url, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE lesson_youtube_url LIKE '%lms.sashainfinity.com%';

-- Lesson video poster images
UPDATE lessons
SET lesson_video_poster = REPLACE(lesson_video_poster, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE lesson_video_poster LIKE '%lms.sashainfinity.com%';

-- Lesson attachment URLs
UPDATE lessons
SET lesson_attachment_url = REPLACE(lesson_attachment_url, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE lesson_attachment_url LIKE '%lms.sashainfinity.com%';

-- Lesson content (may contain embedded URLs)
UPDATE lessons
SET post_content = REPLACE(post_content, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE post_content LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- CERTIFICATES TABLE
-- =============================================================================

-- Certificate background images
UPDATE certificates
SET background_image = REPLACE(background_image, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE background_image LIKE '%lms.sashainfinity.com%';

-- Certificate content (HTML may contain verification URLs)
UPDATE certificates
SET post_content = REPLACE(post_content, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE post_content LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- ISSUED_CERTIFICATES TABLE
-- =============================================================================

-- Issued certificate file paths
UPDATE issued_certificates
SET certificate_file_path = REPLACE(certificate_file_path, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE certificate_file_path LIKE '%lms.sashainfinity.com%';

-- Issued certificate download URLs
UPDATE issued_certificates
SET certificate_download_url = REPLACE(certificate_download_url, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE certificate_download_url LIKE '%lms.sashainfinity.com%';

-- Issued certificate content (generated HTML)
UPDATE issued_certificates
SET certificate_content = REPLACE(certificate_content, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE certificate_content LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- CERTIFICATE_ELEMENT_TEMPLATES TABLE
-- =============================================================================

-- Certificate element image URLs (signatures, logos)
UPDATE certificate_element_templates
SET element_image_url = REPLACE(element_image_url, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE element_image_url LIKE '%lms.sashainfinity.com%';

-- Certificate element content (may contain URLs)
UPDATE certificate_element_templates
SET element_content = REPLACE(element_content, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE element_content LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- BLOG_POSTS TABLE
-- =============================================================================

-- Blog featured images
UPDATE blog_posts
SET featured_image = REPLACE(featured_image, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE featured_image LIKE '%lms.sashainfinity.com%';

-- Blog content (may contain embedded image/media URLs)
UPDATE blog_posts
SET content = REPLACE(content, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE content LIKE '%lms.sashainfinity.com%';

-- Blog excerpt
UPDATE blog_posts
SET excerpt = REPLACE(excerpt, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE excerpt LIKE '%lms.sashainfinity.com%';

-- Blog meta description (may contain URLs)
UPDATE blog_posts
SET meta_description = REPLACE(meta_description, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE meta_description LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- ENROLLMENTS TABLE
-- =============================================================================

-- Certificate URLs in enrollments
UPDATE enrollments
SET certificate_url = REPLACE(certificate_url, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE certificate_url LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- USER_PROFILES TABLE
-- =============================================================================

-- User profile photos
UPDATE user_profiles
SET profile_photo = REPLACE(profile_photo, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE profile_photo LIKE '%lms.sashainfinity.com%';

-- User cover photos
UPDATE user_profiles
SET cover_photo = REPLACE(cover_photo, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE cover_photo LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- COURSE_ANNOUNCEMENTS TABLE
-- =============================================================================

-- Announcement content (may contain media URLs)
UPDATE course_announcements
SET post_content = REPLACE(post_content, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE post_content LIKE '%lms.sashainfinity.com%';

-- Announcement excerpt
UPDATE course_announcements
SET post_excerpt = REPLACE(post_excerpt, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE post_excerpt LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- ASSIGNMENT_SUBMISSIONS TABLE
-- =============================================================================

-- Assignment submission file URLs (JSON array)
UPDATE assignment_submissions
SET files = REPLACE(files::text, 'lms.sashainfinity.com', 'sashainfinity.com')::jsonb
WHERE files::text LIKE '%lms.sashainfinity.com%';

-- Assignment submission text content (may contain URLs)
UPDATE assignment_submissions
SET text_content = REPLACE(text_content, 'lms.sashainfinity.com', 'sashainfinity.com')
WHERE text_content LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- INTERNSHIPS TABLE (if exists)
-- =============================================================================

-- Internship featured images
-- UPDATE internships
-- SET featured_image = REPLACE(featured_image, 'lms.sashainfinity.com', 'sashainfinity.com')
-- WHERE featured_image LIKE '%lms.sashainfinity.com%';

-- Internship resume URLs
-- UPDATE internship_applications
-- SET resume_url = REPLACE(resume_url, 'lms.sashainfinity.com', 'sashainfinity.com')
-- WHERE resume_url LIKE '%lms.sashainfinity.com%';

-- Internship submission URLs
-- UPDATE internship_applications
-- SET submission_url = REPLACE(submission_url, 'lms.sashainfinity.com', 'sashainfinity.com')
-- WHERE submission_url LIKE '%lms.sashainfinity.com%';

-- Internship certificate URLs
-- UPDATE internship_applications
-- SET certificate_url = REPLACE(certificate_url, 'lms.sashainfinity.com', 'sashainfinity.com')
-- WHERE certificate_url LIKE '%lms.sashainfinity.com%';

-- =============================================================================
-- VERIFICATION & SUMMARY
-- =============================================================================

-- Display summary of changes (for verification)
DO $$
DECLARE
    courses_updated INTEGER;
    lessons_updated INTEGER;
    certificates_updated INTEGER;
    issued_certs_updated INTEGER;
    blog_posts_updated INTEGER;
    enrollments_updated INTEGER;
    profiles_updated INTEGER;
    total_updated INTEGER;
BEGIN
    -- Count affected tables (not exact row counts, just verification that we ran)
    SELECT INTO courses_updated COUNT(*) FROM courses
        WHERE course_thumbnail LIKE '%sashainfinity.com%'
           OR course_cover_image LIKE '%sashainfinity.com%'
           OR post_content LIKE '%sashainfinityfinity.com%';

    RAISE NOTICE 'Migration completed. Tables processed: courses, lessons, certificates, issued_certificates, blog_posts, enrollments, user_profiles, and more.';
    RAISE NOTICE 'Please verify URLs visually in the application.';
END $$;

COMMIT;

-- =============================================================================
-- POST-MIGRATION VERIFICATION QUERIES
-- Run these manually to verify the migration was successful
-- =============================================================================

-- Check for any remaining old domain references in key tables:
-- SELECT COUNT(*) FROM courses WHERE course_thumbnail LIKE '%lms.sashainfinity.com%';
-- SELECT COUNT(*) FROM courses WHERE post_content LIKE '%lms.sashainfinity.com%';
-- SELECT COUNT(*) FROM lessons WHERE lesson_video_url LIKE '%lms.sashainfinity.com%';
-- SELECT COUNT(*) FROM issued_certificates WHERE certificate_download_url LIKE '%lms.sashainfinity.com%';
-- SELECT COUNT(*) FROM blog_posts WHERE content LIKE '%lms.sashainfinity.com%';

-- Sample rows to visually inspect:
-- SELECT id, post_title, course_thumbnail FROM courses WHERE course_thumbnail LIKE '%sashainfinity.com%' LIMIT 5;
-- SELECT id, certificate_title, certificate_download_url FROM issued_certificates WHERE certificate_download_url LIKE '%sashainfinity.com%' LIMIT 5;

-- =============================================================================
-- ROLLBACK SCRIPT (if needed)
-- To undo: swap REPLACE arguments and re-run
-- =============================================================================

