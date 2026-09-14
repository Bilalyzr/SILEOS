import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/store/auth', () => ({
  useAuthStore: { getState: () => ({ accessToken: null }) },
  isImpersonating: () => false,
}))

vi.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: vi.fn() },
}))

import { api } from '../axios'

const originalAdapter = api.defaults.adapter

afterEach(() => {
  api.defaults.adapter = originalAdapter
})

describe('Education OS API route shapes', () => {
  it.each([
    '/platform/tenants',
    '/platform/commercial/offers',
    '/meiporul/operations/sites',
    '/seyappaduporul/tutoring',
    '/utporul/coding/challenges',
  ])('keeps %s free of an unsupported trailing slash', async (url) => {
    let captured: string | undefined
    api.defaults.adapter = async (config) => {
      captured = config.url
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    }

    await api.get(url)

    expect(captured).toBe(url)
  })
})
