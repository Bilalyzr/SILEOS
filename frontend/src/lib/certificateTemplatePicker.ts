/**
 * Certificate template picker sourcing (review finding I2).
 *
 * The course editor's picker used to read ONLY the public
 * `/certificates/templates/list` endpoint. That endpoint is anonymous, so it
 * is deliberately scoped to legacy (slug) rows plus `is_global` rows — an
 * instructor's OWN designer templates are private and never appear there.
 * The result: an instructor could build a template in the designer and then
 * find it unreachable from the course editor, breaking the product loop.
 *
 * Rather than loosen the public endpoint's auth semantics, an
 * instructor/admin ADDITIONALLY fetches `/certificates/designer/` (which
 * returns own + global rows, admin sees all) and the two lists are merged
 * here.
 *
 * ID space: both endpoints emit plain `Certificate.id` primary keys, so a row
 * present in both lists dedupes cleanly. (The `+100000` offset scheme lives
 * only in admin.py's *uploaded-image* template listing, which this picker
 * does not consume — there is no collision.)
 */

export interface PickerTemplate {
  id: number
  name: string
  slug?: string
  thumbnail?: string | null
  template_type?: string
  bg_color?: string | null
  title_color?: string | null
  font?: string | null
  body_font?: string | null
  orientation?: string | null
  /** True when this entry came from the authenticated designer endpoint. */
  is_designer?: boolean
  is_global?: boolean
  is_own?: boolean
}

/** Shape returned by GET /certificates/designer/ (see certificateDesigner.ts). */
export interface DesignerTemplateLike {
  id: number
  name: string
  background_color?: string
  orientation?: string
  thumbnail?: string | null
  is_global?: boolean
  is_own?: boolean
}

export function designerToPickerTemplate(t: DesignerTemplateLike): PickerTemplate {
  return {
    id: t.id,
    name: t.name,
    slug: '',
    thumbnail: t.thumbnail ?? null,
    template_type: 'builder',
    bg_color: t.background_color ?? null,
    // The designer stores per-element colours/fonts inside elements_config
    // rather than on the row, so the picker's CSS swatch falls back to its
    // defaults for these — the real thumbnail (when Chrome rendered one at
    // seed time) is what actually represents the design.
    title_color: null,
    font: null,
    body_font: null,
    orientation: t.orientation ?? null,
    is_designer: true,
    is_global: t.is_global,
    is_own: t.is_own,
  }
}

/**
 * Merge the public list with the instructor's designer templates.
 *
 * The public list wins on conflict: it already carries the richer display
 * metadata (title_color/font/body_font) for any row visible to both, and a
 * global designer template appears in BOTH lists with the same id.
 */
export function mergeTemplateLists(
  publicTemplates: PickerTemplate[],
  designerTemplates: DesignerTemplateLike[],
): PickerTemplate[] {
  const seen = new Set<number>()
  const merged: PickerTemplate[] = []

  for (const t of publicTemplates || []) {
    if (t == null || seen.has(t.id)) continue
    seen.add(t.id)
    merged.push(t)
  }

  for (const d of designerTemplates || []) {
    if (d == null || seen.has(d.id)) continue
    seen.add(d.id)
    merged.push(designerToPickerTemplate(d))
  }

  return merged
}

/** Instructors and admins have access to the designer endpoint. */
export function canUseDesignerTemplates(role?: string | null): boolean {
  return role === 'instructor' || role === 'admin' || role === 'superadmin'
}
