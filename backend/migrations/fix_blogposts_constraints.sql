-- fix_blogposts_constraints.sql — 2026-08-25
--
-- Same defect class as the coupons table: blog_posts had NO primary key, so a
-- double-run seed inserted exact duplicates of 4 published posts (15 rows /
-- 11 ids). Deduped and constrained live on production 2026-08-25.
-- Re-run-safe guards included for pre-fix dev/test clones.

BEGIN;

DELETE FROM blog_posts a
 USING blog_posts b
 WHERE a.ctid > b.ctid AND a.id = b.id;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'blog_posts_pkey') THEN
    ALTER TABLE blog_posts ADD CONSTRAINT blog_posts_pkey PRIMARY KEY (id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'blog_posts_slug_unique') THEN
    ALTER TABLE blog_posts ADD CONSTRAINT blog_posts_slug_unique UNIQUE (slug);
  END IF;
END $$;

COMMIT;
