/**
 * Slug helpers for human-readable URLs.
 *
 * Mirrors the course URL pattern (`react-js-mastery-(tamil)-12`): the visible
 * path carries a name slug, and the trailing numeric id is what the app
 * actually looks up. Bare-id URLs keep working because the id is extracted
 * from the end of the string.
 */

/** URL-safe slug from a display name. */
export const slugify = (name: string): string =>
  (name || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-') // non-alphanumerics -> hyphen
    .replace(/^-+|-+$/g, '') // trim leading/trailing hyphens

/**
 * Public instructor profile path: `/instructor/<name-slug>`.
 * Falls back to the id when no name is available. The backend resolves either
 * a name-slug or a bare numeric id.
 */
export const instructorPath = (id: number | string, name?: string): string => {
  const slug = slugify(name || '')
  return slug ? `/instructor/${slug}` : `/instructor/${id}`
}
