import { expect, it, vi } from 'vitest'
vi.mock('@/store/auth', () => ({useAuthStore: {getState: () => ({accessToken: null})}, isImpersonating: () => false}))
vi.mock('react-hot-toast', () => ({default: {error: vi.fn()}}))
import { api } from '../axios'
import { recordingAPI } from '../recording-lessons'

it('keeps the actual recording request URLs free of unsupported trailing slashes', async () => {
  const urls: string[] = []
  const previous = api.defaults.adapter
  api.defaults.adapter = async config => { urls.push(config.url || ''); return {data: {}, status: 200, statusText: 'OK', headers: {}, config} }
  try {
    await recordingAPI.list(); await recordingAPI.detail(16); await recordingAPI.transcribe(16, 'ta', 2)
    await recordingAPI.action(16, 3, 'create-lesson'); await recordingAPI.action(16, 4, 'assessment-drafts'); await recordingAPI.reader(16)
    expect(urls).toEqual(['/recording-lessons', '/recording-lessons/16', '/recording-lessons/16/transcribe', '/recording-lessons/16/create-lesson', '/recording-lessons/16/assessment-drafts', '/recording-lessons/16/reader'])
  } finally { api.defaults.adapter = previous }
})
