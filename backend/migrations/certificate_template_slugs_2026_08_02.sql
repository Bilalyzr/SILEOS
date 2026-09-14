-- =============================================================================
-- certificate_template_slugs_2026_08_02.sql
-- =============================================================================
-- Register the four hand-authored certificate designs that ship in
-- certificates/templates/<slug>.html as selectable template rows.
--
-- WHY: resolve_template_path() picks the design file by the Certificate row's
-- `post_name` slug. Production only ever had the four legacy demo rows
-- (Classic Gold / Elegant Dark / Minimal White / Nature Green), all with an
-- EMPTY post_name — so every option in the instructor's picker fell through to
-- the default template.html and every certificate rendered as the same design,
-- whichever one had been selected. The design files and their thumbnails were
-- on disk the whole time; only these rows were missing, because
-- backend/seed_certificate_templates.py was never run against production.
--
-- Idempotent: matched on post_name, so re-running changes nothing. Deletes
-- nothing — the legacy rows and every issued certificate are left untouched.
-- =============================================================================

BEGIN;

INSERT INTO certificates (
    post_author, post_title, post_name, post_excerpt, post_status, post_type,
    certificate_orientation, background_color, title_font_color,
    title_font_family, body_font_family, post_content
)
SELECT
    author.id, t.title, t.slug, t.excerpt, 'publish', 'tutor_certificates',
    'landscape', t.bg_color, t.title_color, t.font, 'Poppins', ''
FROM (
    VALUES
        ('sasha-3d',        'Sasha 3D Celebration', 'Playful mild-orange design featuring the 3D Sasha mascot.',      '#fdfaf5', '#0b2444', 'Playfair Display'),
        ('royal-navy',      'Royal Navy',           'Formal navy-and-gold classic diploma with an ornate frame.',     '#fcf8ef', '#061e43', 'Playfair Display'),
        ('modern-minimal',  'Modern Minimal',       'Clean, contemporary layout with a single orange accent.',        '#ffffff', '#141b26', 'Space Grotesk'),
        ('aurora-gradient', 'Aurora Gradient',      'Vibrant orange-to-navy hero gradient with a modern glass panel.', '#ffffff', '#061e43', 'Sora')
) AS t(slug, title, excerpt, bg_color, title_color, font)
CROSS JOIN LATERAL (
    -- post_author is NOT NULL and FKs to users.id; prefer an admin.
    SELECT id FROM users ORDER BY (role <> 'admin'), id LIMIT 1
) AS author
WHERE NOT EXISTS (
    SELECT 1 FROM certificates c WHERE c.post_name = t.slug
);

COMMIT;
