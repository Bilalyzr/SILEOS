import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, cleanup, waitFor, act } from '@testing-library/react'
import {
  H5PLesson,
  isValidH5PResultMessage,
  isValidH5PErrorMessage,
  meetsCompletionThreshold,
  isValidH5PPublicId,
} from '../H5PLesson'
import * as h5pApi from '@/api/h5p'

vi.mock('@/api/h5p', async () => {
  const actual = await vi.importActual<typeof h5pApi>('@/api/h5p')
  return {
    ...actual,
    submitH5PResult: vi.fn().mockResolvedValue({
      content_public_id: 'x',
      user_id: 1,
      score: null,
      max_score: null,
      completed: true,
      updated_at: new Date().toISOString(),
    }),
  }
})

const submitH5PResultMock = h5pApi.submitH5PResult as unknown as ReturnType<typeof vi.fn>

const VALID_CONTENT_ID = 'a'.repeat(32)

afterEach(() => cleanup())
beforeEach(() => {
  submitH5PResultMock.mockClear()
})

/** Dispatches a `message` event as if it came from `source` (an object
 * standing in for a window reference — jsdom lets us pass anything through
 * MessageEvent's `source` init field for equality-check purposes). */
function dispatchMessageFrom(source: unknown, data: unknown) {
  const event = new MessageEvent('message', { data, source: source as Window, origin: 'null' })
  act(() => { window.dispatchEvent(event) })
}

describe('isValidH5PPublicId', () => {
  it('accepts exactly 32 lowercase hex characters', () => {
    expect(isValidH5PPublicId(VALID_CONTENT_ID)).toBe(true)
    expect(isValidH5PPublicId(VALID_CONTENT_ID + 'a')).toBe(false) // 33 chars
    expect(isValidH5PPublicId(VALID_CONTENT_ID.slice(0, 31))).toBe(false) // 31 chars
  })

  it('rejects uppercase hex', () => {
    expect(isValidH5PPublicId('A'.repeat(32))).toBe(false)
  })

  it('rejects non-hex characters', () => {
    expect(isValidH5PPublicId('g'.repeat(32))).toBe(false)
    expect(isValidH5PPublicId('z'.repeat(32))).toBe(false)
  })

  it('rejects path-traversal / injection-shaped input', () => {
    expect(isValidH5PPublicId('../../etc/passwd')).toBe(false)
    expect(isValidH5PPublicId('<script>alert(1)</script>')).toBe(false)
    expect(isValidH5PPublicId('')).toBe(false)
  })
})

describe('public_id validation (isValidH5PResultMessage / meetsCompletionThreshold)', () => {
  it('accepts a well-formed result message', () => {
    expect(isValidH5PResultMessage({ type: 'h5p-result', score: 5, maxScore: 10, completed: true })).toBe(true)
  })

  it('accepts a result message with null score/maxScore (pure interactive content)', () => {
    expect(isValidH5PResultMessage({ type: 'h5p-result', score: null, maxScore: null, completed: true })).toBe(true)
  })

  it('rejects a payload with the wrong type discriminator', () => {
    expect(isValidH5PResultMessage({ type: 'something-else', score: 5, maxScore: 10, completed: true })).toBe(false)
  })

  it('rejects a payload missing completed', () => {
    expect(isValidH5PResultMessage({ type: 'h5p-result', score: 5, maxScore: 10 })).toBe(false)
  })

  it('rejects a payload with a non-numeric score', () => {
    expect(isValidH5PResultMessage({ type: 'h5p-result', score: 'five', maxScore: 10, completed: true })).toBe(false)
  })

  it('rejects null/non-object payloads', () => {
    expect(isValidH5PResultMessage(null)).toBe(false)
    expect(isValidH5PResultMessage('h5p-result')).toBe(false)
    expect(isValidH5PResultMessage(42)).toBe(false)
  })

  it('recognizes a well-formed error message', () => {
    expect(isValidH5PErrorMessage({ type: 'h5p-error', message: 'boot_failed' })).toBe(true)
    expect(isValidH5PErrorMessage({ type: 'h5p-result' })).toBe(false)
  })

  it('meetsCompletionThreshold: no score at all counts as complete', () => {
    expect(meetsCompletionThreshold({ type: 'h5p-result', score: null, maxScore: null, completed: true })).toBe(true)
  })

  it('meetsCompletionThreshold: score/maxScore >= 0.5 passes', () => {
    expect(meetsCompletionThreshold({ type: 'h5p-result', score: 5, maxScore: 10, completed: true })).toBe(true)
    expect(meetsCompletionThreshold({ type: 'h5p-result', score: 6, maxScore: 10, completed: true })).toBe(true)
  })

  it('meetsCompletionThreshold: score/maxScore below 0.5 fails', () => {
    expect(meetsCompletionThreshold({ type: 'h5p-result', score: 4, maxScore: 10, completed: true })).toBe(false)
  })

  it('meetsCompletionThreshold: completed=false always fails regardless of score', () => {
    expect(meetsCompletionThreshold({ type: 'h5p-result', score: 10, maxScore: 10, completed: false })).toBe(false)
  })
})

describe('H5PLesson', () => {
  it('renders the iframe with sandbox="allow-scripts" EXACTLY (no allow-same-origin)', () => {
    render(<H5PLesson contentId={VALID_CONTENT_ID} />)
    const iframe = screen.getByTitle('Interactive content') as HTMLIFrameElement
    expect(iframe.getAttribute('sandbox')).toBe('allow-scripts')
    expect(iframe.getAttribute('sandbox')).not.toContain('allow-same-origin')
  })

  it('points the iframe src at the static player page with the validated content id', () => {
    render(<H5PLesson contentId={VALID_CONTENT_ID} />)
    const iframe = screen.getByTitle('Interactive content') as HTMLIFrameElement
    expect(iframe.getAttribute('src')).toBe(`/h5p-player.html?content=${VALID_CONTENT_ID}`)
  })

  it('rejects an invalid content id without rendering an iframe', () => {
    render(<H5PLesson contentId="not-a-valid-id" />)
    expect(screen.queryByTitle('Interactive content')).not.toBeInTheDocument()
    expect(screen.getByText(/could not be loaded/i)).toBeInTheDocument()
  })

  it('ignores a message whose source is not this iframe\'s contentWindow', async () => {
    render(<H5PLesson contentId={VALID_CONTENT_ID} onCompleted={vi.fn()} />)
    dispatchMessageFrom({ fake: 'window' }, { type: 'h5p-result', score: 10, maxScore: 10, completed: true })
    await new Promise((r) => setTimeout(r, 10))
    expect(submitH5PResultMock).not.toHaveBeenCalled()
  })

  it('valid result message from the real iframe source calls submitH5PResult and triggers onCompleted at threshold', async () => {
    const onCompleted = vi.fn()
    const { container } = render(<H5PLesson contentId={VALID_CONTENT_ID} onCompleted={onCompleted} />)
    const iframeEl = container.querySelector('iframe') as HTMLIFrameElement
    const contentWindow = iframeEl.contentWindow

    dispatchMessageFrom(contentWindow, { type: 'h5p-result', score: 8, maxScore: 10, completed: true })

    await waitFor(() => expect(submitH5PResultMock).toHaveBeenCalledWith(VALID_CONTENT_ID, {
      score: 8,
      max_score: 10,
      completed: true,
    }))
    await waitFor(() => expect(onCompleted).toHaveBeenCalledTimes(1))
  })

  it('valid result below the completion threshold calls the API but NOT onCompleted', async () => {
    const onCompleted = vi.fn()
    const { container } = render(<H5PLesson contentId={VALID_CONTENT_ID} onCompleted={onCompleted} />)
    const iframeEl = container.querySelector('iframe') as HTMLIFrameElement
    const contentWindow = iframeEl.contentWindow

    dispatchMessageFrom(contentWindow, { type: 'h5p-result', score: 2, maxScore: 10, completed: true })

    await waitFor(() => expect(submitH5PResultMock).toHaveBeenCalledWith(VALID_CONTENT_ID, {
      score: 2,
      max_score: 10,
      completed: true,
    }))
    // Give onCompleted a chance to fire erroneously before asserting it never did.
    await new Promise((r) => setTimeout(r, 10))
    expect(onCompleted).not.toHaveBeenCalled()
  })

  it('a malformed payload from the real iframe source is ignored (no API call)', async () => {
    const { container } = render(<H5PLesson contentId={VALID_CONTENT_ID} onCompleted={vi.fn()} />)
    const iframeEl = container.querySelector('iframe') as HTMLIFrameElement
    const contentWindow = iframeEl.contentWindow

    dispatchMessageFrom(contentWindow, { type: 'h5p-result', completed: 'not-a-boolean' })
    await new Promise((r) => setTimeout(r, 10))
    expect(submitH5PResultMock).not.toHaveBeenCalled()
  })

  it('does not call onCompleted twice for two terminal messages', async () => {
    const onCompleted = vi.fn()
    const { container } = render(<H5PLesson contentId={VALID_CONTENT_ID} onCompleted={onCompleted} />)
    const iframeEl = container.querySelector('iframe') as HTMLIFrameElement
    const contentWindow = iframeEl.contentWindow

    dispatchMessageFrom(contentWindow, { type: 'h5p-result', score: 9, maxScore: 10, completed: true })
    await waitFor(() => expect(onCompleted).toHaveBeenCalledTimes(1))

    dispatchMessageFrom(contentWindow, { type: 'h5p-result', score: 10, maxScore: 10, completed: true })
    await new Promise((r) => setTimeout(r, 10))
    expect(onCompleted).toHaveBeenCalledTimes(1)
  })

  it('previewOnly suppresses submitH5PResult and onCompleted entirely', async () => {
    const onCompleted = vi.fn()
    const { container } = render(
      <H5PLesson contentId={VALID_CONTENT_ID} onCompleted={onCompleted} previewOnly />
    )
    const iframeEl = container.querySelector('iframe') as HTMLIFrameElement
    const contentWindow = iframeEl.contentWindow

    dispatchMessageFrom(contentWindow, { type: 'h5p-result', score: 10, maxScore: 10, completed: true })
    await new Promise((r) => setTimeout(r, 10))

    expect(submitH5PResultMock).not.toHaveBeenCalled()
    expect(onCompleted).not.toHaveBeenCalled()
  })

  it('a rapid answered->completed pair (L3 regression): onCompleted fires from the first terminal message and the second message still gets POSTed once the first POST resolves', async () => {
    // Slow the first POST down so the second message arrives while it is
    // still in flight — this is exactly the Question Set
    // answered->completed race the fix targets.
    let resolveFirst!: () => void
    const firstPostGate = new Promise<void>((resolve) => { resolveFirst = resolve })
    submitH5PResultMock.mockImplementationOnce(async () => {
      await firstPostGate
      return {
        content_public_id: VALID_CONTENT_ID,
        user_id: 1,
        score: 9,
        max_score: 10,
        completed: true,
        updated_at: new Date().toISOString(),
      }
    })

    const onCompleted = vi.fn()
    const { container } = render(<H5PLesson contentId={VALID_CONTENT_ID} onCompleted={onCompleted} />)
    const iframeEl = container.querySelector('iframe') as HTMLIFrameElement
    const contentWindow = iframeEl.contentWindow

    // First terminal message ("answered") — its POST will hang on firstPostGate.
    dispatchMessageFrom(contentWindow, { type: 'h5p-result', score: 9, maxScore: 10, completed: true })
    await waitFor(() => expect(submitH5PResultMock).toHaveBeenCalledTimes(1))
    // onCompleted must fire immediately from this message, independent of
    // the POST still being in flight (the L3 bug: it used to be gated
    // behind the POST's await, so a fast second message masked nothing —
    // the real defect was the SECOND message's POST being silently
    // dropped, asserted below).
    expect(onCompleted).toHaveBeenCalledTimes(1)

    // Second terminal message ("completed") arrives WHILE the first POST
    // is still pending — must be queued, not dropped.
    dispatchMessageFrom(contentWindow, { type: 'h5p-result', score: 10, maxScore: 10, completed: true })
    await new Promise((r) => setTimeout(r, 10))
    // Still only one call so far — the second is queued behind the first,
    // not fired concurrently.
    expect(submitH5PResultMock).toHaveBeenCalledTimes(1)
    // onCompleted must not have fired again for the second terminal message.
    expect(onCompleted).toHaveBeenCalledTimes(1)

    // Let the first POST resolve — the queued second message's POST must
    // now fire.
    resolveFirst()
    await waitFor(() => expect(submitH5PResultMock).toHaveBeenCalledTimes(2))
    expect(submitH5PResultMock).toHaveBeenNthCalledWith(2, VALID_CONTENT_ID, {
      score: 10,
      max_score: 10,
      completed: true,
    })
    // onCompleted still only once overall (reportedCompletionRef guard).
    expect(onCompleted).toHaveBeenCalledTimes(1)
  })
})
