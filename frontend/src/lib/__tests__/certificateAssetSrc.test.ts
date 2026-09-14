/**
 * Mirrors backend/tests/test_certificate_designer.py's is_safe_asset_src
 * matrix (same test names/cases where practical) so the client-side
 * allowlist in lib/certificateAssetSrc.ts never silently drifts from the
 * server's authority (backend/app/services/certificate_html_renderer.py).
 */
import { describe, it, expect } from 'vitest'
import { isSafeAssetSrc } from '../certificateAssetSrc'

describe('isSafeAssetSrc', () => {
  it('accepts uploads/certificate-files paths and data: image URIs', () => {
    expect(isSafeAssetSrc('/uploads/certs/sig.png')).toBe(true)
    expect(isSafeAssetSrc('/certificate-files/thumbnails/x.png')).toBe(true)
    expect(isSafeAssetSrc('data:image/png;base64,AAAA')).toBe(true)
    expect(isSafeAssetSrc('data:image/jpeg;base64,AAAA')).toBe(true)
    expect(isSafeAssetSrc('data:image/webp;base64,AAAA')).toBe(true)
  })

  it('rejects file://, blob:, and external http(s)', () => {
    expect(isSafeAssetSrc('file:///etc/passwd')).toBe(false)
    expect(isSafeAssetSrc('file://C:/Windows/System32/config/SAM')).toBe(false)
    expect(isSafeAssetSrc('blob:https://example.com/uuid')).toBe(false)
    expect(isSafeAssetSrc('https://attacker.example/beacon.png')).toBe(false)
    expect(isSafeAssetSrc('http://internal-metadata.local/latest')).toBe(false)
    expect(isSafeAssetSrc('')).toBe(false)
    expect(isSafeAssetSrc(null)).toBe(false)
    expect(isSafeAssetSrc(undefined)).toBe(false)
  })

  it('rejects raw ".." traversal', () => {
    expect(isSafeAssetSrc('/uploads/../../../../etc/passwd')).toBe(false)
    expect(isSafeAssetSrc('/uploads/../etc/passwd')).toBe(false)
    expect(isSafeAssetSrc('/certificate-files/../../etc/passwd')).toBe(false)
  })

  it('rejects percent-encoded traversal (single and double encoding)', () => {
    expect(isSafeAssetSrc('/uploads/%2e%2e/%2e%2e/etc/passwd')).toBe(false)
    expect(isSafeAssetSrc('/uploads/%2E%2E/%2E%2E/etc/passwd')).toBe(false) // uppercase hex
    expect(isSafeAssetSrc('/uploads/..%2fetc%2fpasswd')).toBe(false)
    expect(isSafeAssetSrc('/uploads/%2e%2e%2fetc%2fpasswd')).toBe(false)
    expect(isSafeAssetSrc('/uploads/%252e%252e/%252e%252e/etc/passwd')).toBe(false)
    expect(isSafeAssetSrc('/uploads/%252e%252e%252fetc%252fpasswd')).toBe(false)
  })

  it('rejects mixed-encoding traversal', () => {
    expect(isSafeAssetSrc('/uploads/..%2f../etc/passwd')).toBe(false)
    expect(isSafeAssetSrc('/uploads/%2e./%2e./etc/passwd')).toBe(false)
  })

  it('rejects backslash traversal outright', () => {
    expect(isSafeAssetSrc('/uploads/..\\..\\etc\\passwd')).toBe(false)
    expect(isSafeAssetSrc('/uploads/certs\\..\\..\\secrets.txt')).toBe(false)
  })

  it('rejects an unparseable percent-escape rather than guessing', () => {
    expect(isSafeAssetSrc('/uploads/100%sure/x.png')).toBe(false)
  })

  it('accepts legitimate nested-but-safe paths', () => {
    expect(isSafeAssetSrc('/uploads/certificates/sig123.png')).toBe(true)
    expect(isSafeAssetSrc('/uploads/certs/2026/09/thumb.png')).toBe(true)
    expect(isSafeAssetSrc('/certificate-files/thumbnails/ivory-classic.png')).toBe(true)
    expect(isSafeAssetSrc('data:image/png;base64,QUJDRA==')).toBe(true)
  })

  it('rejects a path not under an allowed prefix', () => {
    expect(isSafeAssetSrc('/etc/passwd')).toBe(false)
    expect(isSafeAssetSrc('/static/logo.png')).toBe(false)
  })

  it('rejects a data URI with a disallowed image subtype', () => {
    expect(isSafeAssetSrc('data:image/svg+xml;base64,AAAA')).toBe(false)
    expect(isSafeAssetSrc('data:text/html;base64,AAAA')).toBe(false)
  })

  it('trims surrounding whitespace before checking', () => {
    expect(isSafeAssetSrc('  /uploads/certs/sig.png  ')).toBe(true)
  })
})
