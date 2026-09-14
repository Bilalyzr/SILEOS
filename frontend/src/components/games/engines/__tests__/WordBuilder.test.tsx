/** WordBuilder state-machine test: hint costs (-2/hint, floor 0). */
import { render, screen, cleanup, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { WordBuilderConfig } from '@/api/games'
import { WordBuilder } from '../WordBuilder'
import type { GameOutcome } from '../QuizRush'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

const config: WordBuilderConfig = {
  items: [{ clue: 'Feline pet', answer: 'CAT' }],
  settings: { hints_allowed: 3 },
}

describe('WordBuilder hint costs', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('solving with zero hints scores the full 10', () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<WordBuilder config={config} onComplete={onComplete} title="Test" />)

    // Use the Hint button 0 times; place letters via available tiles by
    // reading their text content (C, A, T in some shuffled order) and
    // clicking each in the correct sequence using their accessible name.
    for (const letter of ['C', 'A', 'T']) {
      const btn = screen.getAllByRole('button', { name: letter }).find((b) => !b.hasAttribute('disabled'))
      expect(btn).toBeTruthy()
      act(() => { btn!.click() })
    }
    act(() => { vi.advanceTimersByTime(600) })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete.mock.calls[0][0].score).toBe(10)
  })

  it('using 2 hints scores 10 - 2*2 = 6', () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<WordBuilder config={config} onComplete={onComplete} title="Test" />)

    act(() => { screen.getByRole('button', { name: /hint/i }).click() })
    act(() => { screen.getByRole('button', { name: /hint/i }).click() })
    // Last letter placed manually.
    const remaining = screen.getAllByRole('button', { name: /^[A-Z]$/ })
      .filter((b) => !b.hasAttribute('disabled'))
    expect(remaining.length).toBeGreaterThan(0)
    act(() => { remaining[0].click() })
    act(() => { vi.advanceTimersByTime(600) })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete.mock.calls[0][0].score).toBe(6)
  })
})
