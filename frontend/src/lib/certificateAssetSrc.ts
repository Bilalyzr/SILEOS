/**
 * Client-side mirror of backend/app/services/certificate_html_renderer.py
 * ::is_safe_asset_src — gives instructors instant feedback in the image/
 * signature src field before they ever hit the server. The server remains
 * the authority (this is a UX convenience, not a security boundary); every
 * case here matches a case the backend allowlist accepts or rejects.
 *
 * Allowed: same-origin static paths (/uploads/..., /certificate-files/...)
 * or an inline data:image/(png|jpeg|jpg|gif|webp);base64,... URI. Rejected:
 * file://, blob:, any external http(s) URL, path traversal attempts
 * (including percent-encoded / double-encoded traversal), backslashes.
 */

const SAFE_PATH_PREFIXES = ['/uploads/', '/certificate-files/']
const DATA_URI_RE = /^data:image\/(?:png|jpeg|jpg|gif|webp);base64,/
const MAX_UNQUOTE_ROUNDS = 10

/** Percent-decode repeatedly until stable (defeats double/triple encoding
 * like %252e), mirroring the backend's _fully_unquote. Returns null if it
 * never stabilizes within MAX_UNQUOTE_ROUNDS rounds, or if a decode step
 * throws (malformed percent-escape) — both treated as unsafe. */
function fullyUnquote(value: string): string | null {
  let current = value
  for (let i = 0; i < MAX_UNQUOTE_ROUNDS; i += 1) {
    let decoded: string
    try {
      decoded = decodeURIComponent(current)
    } catch {
      return null
    }
    if (decoded === current) return current
    current = decoded
  }
  return null
}

/** Collapse "." and ".." segments the way posixpath.normpath does, for a
 * string already known to start with "/". Pure string/array logic — no
 * filesystem or URL API involved (matches the backend's posixpath.normpath
 * re-check on the decoded path). */
function normalizePosixPath(path: string): string {
  const segments = path.split('/')
  const out: string[] = []
  for (const seg of segments) {
    if (seg === '' || seg === '.') continue
    if (seg === '..') {
      if (out.length > 0) out.pop()
      // else: leading ".." on an absolute path — dropped (can't go above root)
      continue
    }
    out.push(seg)
  }
  return '/' + out.join('/')
}

export function isSafeAssetSrc(src: string | null | undefined): boolean {
  if (!src || typeof src !== 'string') return false
  const s = src.trim()

  if (DATA_URI_RE.test(s)) return true

  if (!SAFE_PATH_PREFIXES.some((p) => s.startsWith(p))) return false

  if (s.includes('\\')) return false

  const decoded = fullyUnquote(s)
  if (decoded === null || decoded.includes('%')) return false

  if (decoded.split('/').includes('..')) return false

  const normalized = normalizePosixPath(decoded)
  if (!SAFE_PATH_PREFIXES.some((p) => normalized.startsWith(p))) return false

  return true
}

export function assetSrcErrorMessage(): string {
  return 'Must be an uploaded asset path (/uploads/... or /certificate-files/...) or a data:image/... URI'
}
