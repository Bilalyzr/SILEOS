/**
 * S-H1 fallout: GET/POST /wishlist declare a trailing slash on the backend
 * (wishlist.py:19,45) and redirect_slashes=False means a slash-less call
 * 404s — verified live against the FastAPI test client. '/wishlist' was
 * previously ONLY in axios.ts's noSlashEndpoints list, which stripped the
 * trailing slash and made the collection endpoint unreachable. This
 * exercises the actual request interceptor (not a mock of it) via a custom
 * axios adapter that captures the final resolved URL without hitting the
 * network.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/store/auth', () => ({
  useAuthStore: { getState: () => ({ accessToken: null }) },
  isImpersonating: () => false,
}))

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: vi.fn() },
}))

import { api } from '../axios'

function captureUrl(): { getUrl: () => string | undefined } {
  let captured: string | undefined
  api.defaults.adapter = async (config: any) => {
    captured = config.url
    return {
      data: {}, status: 200, statusText: 'OK', headers: {}, config,
    }
  }
  return { getUrl: () => captured }
}

describe('axios interceptor — /wishlist trailing slash (S-H1)', () => {
  beforeEach(() => {
    // restore default adapter behavior isn't needed; each test sets its own
  })

  it('POST /wishlist gets a trailing slash appended', async () => {
    const { getUrl } = captureUrl()
    await api.post('/wishlist', { course_id: 1 })
    expect(getUrl()).toBe('/wishlist/')
  })

  it('GET /wishlist gets a trailing slash appended', async () => {
    const { getUrl } = captureUrl()
    await api.get('/wishlist')
    expect(getUrl()).toBe('/wishlist/')
  })

  it('DELETE /wishlist/{course_id} keeps no trailing slash', async () => {
    const { getUrl } = captureUrl()
    await api.delete('/wishlist/42')
    expect(getUrl()).toBe('/wishlist/42')
  })
})
