-- =============================================================================
-- hide_slugless_certificate_templates_2026_08_02.sql
-- =============================================================================
-- Retire the legacy demo template rows that have no design behind them.
--
-- WHY: a Certificate row only renders its own design when `post_name` names a
-- file in certificates/templates/. The demo rows "Elegant Dark", "Minimal
-- White" and "Nature Green" have an empty slug, so choosing any of them
-- silently produced the default design instead — the picker promised four
-- distinct looks and delivered one. Unpublishing drops them from
-- /certificates/templates/list (it filters on post_status='publish') so
-- instructors only see options that render as advertised.
--
-- Row id=1 is deliberately KEPT: its empty slug is correct, because it IS the
-- default certificates/template.html design.
--
-- Safe: no issued certificate references these rows, and post_type/FKs are
-- untouched, so this is reversible with
--   UPDATE certificates SET post_status='publish' WHERE id IN (...);
-- =============================================================================

BEGIN;

UPDATE certificates
   SET post_status  = 'draft',
       post_modified = now()
 WHERE id <> 1
   AND coalesce(btrim(post_name), '') = ''
   AND post_status = 'publish'
   AND NOT EXISTS (
       SELECT 1 FROM issued_certificates ic WHERE ic.certificate_id = certificates.id
   );

COMMIT;
