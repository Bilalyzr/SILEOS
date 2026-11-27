import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { act, renderHook, cleanup } from '@testing-library/react'
import { codingAPI } from '@/api/coding'
import { draftKey, useCodingDraft } from '../useCodingDraft'

vi.mock('@/api/coding', async () => {
  const actual = await vi.importActual<typeof import('@/api/coding')>('@/api/coding')
  return {
    ...actual,
    codingAPI: { ...actual.codingAPI, draft: vi.fn(), saveDraft: vi.fn() },
  }
})

const draftMock = codingAPI.draft as unknown as ReturnType<typeof vi.fn>
const saveMock = codingAPI.saveDraft as unknown as ReturnType<typeof vi.fn>

describe('useCodingDraft autosave', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    window.localStorage.clear()
    draftMock.mockReset()
    saveMock.mockReset()
    saveMock.mockResolvedValue({ language: 'python', source_code: '', updated_at: '' })
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('keys drafts by challenge and language', () => {
    expect(draftKey('two-sum', 'python')).toBe('sileos-coding-draft:two-sum:python')
    expect(draftKey('two-sum', 'cpp')).not.toBe(draftKey('two-sum', 'python'))
  })

  it('writes this device copy at once and saves the server copy once after typing stops', async () => {
    const { result } = renderHook(() => useCodingDraft('two-sum', 'python', 1000))
    act(() => {
      result.current.save('a')
      result.current.save('ab')
      result.current.save('abc')
    })
    expect(window.localStorage.getItem(draftKey('two-sum', 'python'))).toBe('abc')
    expect(result.current.status).toBe('saving')
    expect(saveMock).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(1000)
    })
    expect(saveMock).toHaveBeenCalledTimes(1)
    expect(saveMock).toHaveBeenCalledWith('two-sum', 'python', 'abc')
    expect(result.current.status).toBe('saved')
  })

  it('reports device-only when the server copy cannot be saved', async () => {
    saveMock.mockRejectedValue(new Error('offline'))
    const { result } = renderHook(() => useCodingDraft('two-sum', 'python', 1000))
    act(() => result.current.save('print(1)'))
    await act(async () => {
      vi.advanceTimersByTime(1000)
    })
    expect(result.current.status).toBe('device-only')
    expect(window.localStorage.getItem(draftKey('two-sum', 'python'))).toBe('print(1)')
  })

  it('restores the server copy first and falls back to this device', async () => {
    const { result } = renderHook(() => useCodingDraft('two-sum', 'python'))

    draftMock.mockResolvedValue({ language: 'python', source_code: 'server', updated_at: '' })
    expect(await result.current.restore()).toBe('server')

    draftMock.mockResolvedValue(null)
    window.localStorage.setItem(draftKey('two-sum', 'python'), 'local')
    expect(await result.current.restore()).toBe('local')

    draftMock.mockRejectedValue(new Error('network'))
    expect(await result.current.restore()).toBe('local')
  })
})
