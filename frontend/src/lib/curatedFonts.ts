/**
 * Curated 12-font list — mirrors backend/app/services/certificate_html_
 * renderer.py CURATED_FONTS exactly (name, category, Google Fonts weight
 * list). The designer's font picker loads these live via a Google Fonts
 * <link> tag added on demand (see loadGoogleFont below); the backend
 * silently falls back to Inter for anything outside this list, so the
 * client only ever offers these 12 to keep instructor expectations aligned
 * with what will actually render.
 */

export type FontCategory = 'serif' | 'sans-serif' | 'script'

export interface CuratedFont {
  name: string
  category: FontCategory
  weights: string
}

export const CURATED_FONTS: CuratedFont[] = [
  { name: 'Playfair Display', category: 'serif', weights: '400;500;600;700;800;900' },
  { name: 'Cormorant Garamond', category: 'serif', weights: '400;500;600;700' },
  { name: 'Great Vibes', category: 'script', weights: '400' },
  { name: 'Space Grotesk', category: 'sans-serif', weights: '400;500;600;700' },
  { name: 'Sora', category: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Poppins', category: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Inter', category: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Lora', category: 'serif', weights: '400;500;600;700' },
  { name: 'Montserrat', category: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'DM Serif Display', category: 'serif', weights: '400' },
  { name: 'Crimson Pro', category: 'serif', weights: '400;500;600;700' },
  { name: 'Outfit', category: 'sans-serif', weights: '400;500;600;700;800' },
]

export const CURATED_FONT_NAMES: string[] = CURATED_FONTS.map((f) => f.name)

export function isCuratedFont(name: string | null | undefined): boolean {
  return !!name && CURATED_FONT_NAMES.includes(name)
}

export function fontFallbackStack(name: string | null | undefined): string {
  const font = CURATED_FONTS.find((f) => f.name === name)
  const category = font?.category ?? 'sans-serif'
  if (category === 'serif') return "Georgia, 'Times New Roman', serif"
  if (category === 'script') return 'cursive'
  return 'Helvetica, Arial, sans-serif'
}

/** CSS font-family value for an element — quoted curated name + matching
 * fallback stack, or the app-wide fallback stack when the name isn't
 * curated (mirrors the backend's _font_family_css/_FALLBACK_FONT_STACK). */
export function fontFamilyCss(name: string | null | undefined): string {
  if (isCuratedFont(name)) {
    return `'${name}', ${fontFallbackStack(name)}`
  }
  return "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
}

const _loadedFonts = new Set<string>()

/**
 * Add a Google Fonts <link> for one curated font on demand (idempotent —
 * a font is only linked once per page load). No-op for a non-curated name
 * or outside a browser environment (SSR/test safety).
 */
export function loadGoogleFont(name: string): void {
  if (typeof document === 'undefined') return
  const font = CURATED_FONTS.find((f) => f.name === name)
  if (!font || _loadedFonts.has(name)) return
  _loadedFonts.add(name)
  const family = name.replace(/ /g, '+')
  const href = `https://fonts.googleapis.com/css2?family=${family}:wght@${font.weights}&display=swap`
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = href
  link.setAttribute('data-designer-font', name)
  document.head.appendChild(link)
}

export function loadAllCuratedFonts(): void {
  CURATED_FONTS.forEach((f) => loadGoogleFont(f.name))
}
