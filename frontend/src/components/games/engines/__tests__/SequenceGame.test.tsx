/** SequenceGame state-machine test: retry scoring (10/item on the accepted
 * first-correct submit, 7/item when the accepted submit is the one allowed
 * retry). Drag interactions are dnd-kit driven and not simulated here;
 * instead Math.random is mocked so the initial shuffle is deterministic and
 * the state machine is driven purely through Submit clicks — exercising the
 * exact scoring.ts call sites without needing real pointer drags. */
import { render, screen, cleanup, act, fireEvent } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SequenceConfig } from '@/api/games'
import { SequenceGame } from '../SequenceGame'
import type { GameOutcome } from '../QuizRush'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

const config: SequenceConfig = {
  items: [{ text: 'Step 1' }, { text: 'Step 2' }, { text: 'Step 3' }],
  settings: { time_limit_s: 0, shuffle: true },
}

describe('SequenceGame retry scoring', () => {
  it('submitting the shuffled (wrong) order first offers one retry, and the accepted retry scores 7/item', () => {
    // Force the Fisher-Yates shuffle to fully reverse [0,1,2] -> [2,1,0] on
    // the first pass (guaranteed wrong order for a 3-item list — see the
    // MatchPairs test header for the same Math.random=>0 trace technique),
    // so submit #1 is rejected and triggers the retry path deterministically.
    vi.spyOn(Math, 'random').mockReturnValue(0)

    const onComplete = vi.fn<[GameOutcome], void>()
    render(<SequenceGame config={config} onComplete={onComplete} title="Test" />)

    // First submit: order is reversed (wrong) -> retry offered, no completion yet.
    act(() => { screen.getByRole('button', { name: 'Submit' }).click() })
    expect(onComplete).not.toHaveBeenCalled()
    expect(screen.getByText(/one more try/i)).toBeInTheDocument()

    // Second submit (no reordering performed by the test, so still fully
    // reversed => 0 correct positions) -> final, accepted retry scores
    // scoreSequenceSubmit(0, true) = 0.
    act(() => { screen.getByRole('button', { name: 'Submit' }).click() })
    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete.mock.calls[0][0].score).toBe(0)
  })

  it('accepts a first-try correct order at 10/item (no retry consumed)', () => {
    // A 1-item list is always "in order" regardless of shuffle, so the
    // first submit is accepted without ever exercising the retry path.
    const singleConfig: SequenceConfig = {
      items: [{ text: 'Only step' }],
      settings: { time_limit_s: 0, shuffle: true },
    }
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<SequenceGame config={singleConfig} onComplete={onComplete} title="Test" />)

    act(() => { screen.getByRole('button', { name: 'Submit' }).click() })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete.mock.calls[0][0].score).toBe(10)
  })

  it('is keyboard operable: a focused handle can be lifted and moved with Space + ArrowDown, then dropped with Space', async () => {
    // Deterministic shuffle via the Math.random=>0 mock (traced directly:
    // for this 3-item array it produces [Step 2, Step 3, Step 1]).
    vi.spyOn(Math, 'random').mockReturnValue(0)

    // dnd-kit's built-in sortableKeyboardCoordinates decides the next
    // target by comparing real getBoundingClientRect().top/left values of
    // the sortable rows — jsdom returns an all-zero rect for every element,
    // which makes every row indistinguishable and the keyboard move a
    // no-op. Stubbing getBoundingClientRect with a stable per-row vertical
    // stack (indexed by each row's position among the sortable items) gives
    // the coordinate getter real geometry to compare, so an actual
    // ArrowDown reorder can be driven and observed here instead of only
    // being exercised via Submit-button clicks.
    const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
      const rows = Array.from(document.querySelectorAll('[data-testid^="seq-row-"]'))
      const index = rows.indexOf(this.closest('[data-testid^="seq-row-"]') as Element)
      const top = index >= 0 ? index * 60 : 0
      return {
        top, bottom: top + 56, left: 0, right: 200, width: 200, height: 56,
        x: 0, y: top, toJSON() { return this },
      } as DOMRect
    })

    const onComplete = vi.fn<[GameOutcome], void>()
    render(<SequenceGame config={config} onComplete={onComplete} title="Test" />)

    const rowsBefore = screen.getAllByText(/^Step \d$/).map((el) => el.textContent)
    expect(rowsBefore).toEqual(['Step 2', 'Step 3', 'Step 1'])

    const handles = screen.getAllByRole('button', { name: 'Drag to reorder' })
    const firstHandle = handles[0]

    // dnd-kit's KeyboardSensor activates on Space/Enter keydown (event.code
    // === 'Space'), moves with arrow keys, and ends the drag on a second
    // Space/Enter/Tab keydown. Its keydown listener for the move/end phase
    // is attached inside a setTimeout(0) (see KeyboardSensor.attach in
    // @dnd-kit/core), so a real macrotask must elapse between activation
    // and the follow-up key events, or they fire before the listener
    // exists and are silently dropped.
    firstHandle.focus()
    act(() => { fireEvent.keyDown(firstHandle, { code: 'Space' }) })
    await act(async () => { await new Promise((r) => setTimeout(r, 0)) })
    act(() => { fireEvent.keyDown(firstHandle, { code: 'ArrowDown' }) })
    act(() => { fireEvent.keyDown(firstHandle, { code: 'Space' }) })

    const rowsAfter = screen.getAllByText(/^Step \d$/).map((el) => el.textContent)
    // The first row (Step 2) moved down one slot via arrayMove — a real
    // reorder happened, not just a focus change.
    expect(rowsAfter).not.toEqual(rowsBefore)
    expect(rowsAfter[1]).toBe('Step 2')

    Element.prototype.getBoundingClientRect = originalGetBoundingClientRect
  })
})

describe('SequenceGame timeout reports the current score state, not a stale mount-time value', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  // SequenceGame only ever sets `score` inside finish() itself (there is no
  // partial-credit path that banks points without completing), so unlike
  // MatchPairs/DragSort this engine's stale-closure risk is latent rather
  // than exploitable today. This test still applies the same ref-based fix
  // for symmetry (per the fix-wave spec) and guards the regression: if a
  // future change ever lets `score` accumulate before completion, an
  // expiring timer must report that live value, not whatever `score` was
  // when the countdown effect's closure was created.
  it('reports the same score the running state holds at the moment the timer expires', () => {
    vi.useFakeTimers()
    vi.spyOn(Math, 'random').mockReturnValue(0)

    const timedConfig: SequenceConfig = {
      items: config.items,
      settings: { time_limit_s: 5, shuffle: true },
    }
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<SequenceGame config={timedConfig} onComplete={onComplete} title="Test" />)

    // First submit: wrong order (reversed shuffle) -> retry offered, no
    // completion, score stays 0.
    act(() => { screen.getByRole('button', { name: 'Submit' }).click() })
    expect(onComplete).not.toHaveBeenCalled()

    act(() => { vi.advanceTimersByTime(5000) })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete.mock.calls[0][0].score).toBe(0)
  })
})
