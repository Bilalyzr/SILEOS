/**
 * User-supplied links (profile socials, company websites) render as <a href>.
 * Only http(s) may pass: javascript:/data: hrefs would run on this origin.
 * A bare domain gets https:// so it isn't treated as a relative path.
 */
export function safeHref(url?: string | null): string | undefined {
  if (!url) return undefined;
  const u = url.trim();
  if (/^https?:\/\//i.test(u)) return u;
  if (/^[a-z][a-z0-9+.-]*:/i.test(u.replace(/[\u0000- ]/g, ""))) return undefined;
  return `https://${u.replace(/^\/+/, "")}`;
}
