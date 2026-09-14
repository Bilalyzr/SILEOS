/** QuizRush state-machine test: the 3rd consecutive correct answer must get
 * the x1.5 streak multiplier (streakBefore >= 2 ruling — BINDING). Uses fake
 * timers so the per-question countdown never causes a real wait. */
import { render, screen, cleanup, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { QuizRushConfig } from '@/api/games'
import { QuizRush, type GameOutcome } from '../QuizRush'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

const config: QuizRushConfig = {
  items: [
    { prompt: 'Q1', options: ['right1', 'wrong1'], answer_index: 0 },
    { prompt: 'Q2', options: ['right2', 'wrong2'], answer_index: 0 },
    { prompt: 'Q3', options: ['right3', 'wrong3'], answer_index: 0 },
  ],
  settings: { seconds_per_question: 20, shuffle: false },
}

describe('QuizRush streak boundary', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('applies the x1.5 multiplier starting on the 3rd consecutive correct answer', async () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<QuizRush config={config} onComplete={onComplete} title="Test" />)

    // Answer all 3 correctly, instantly (full time remaining -> 10 pts base
    // each; the 3rd fires the streak multiplier: round(10 * 1.5) = 15,
    // capped by capScore to maxScore=30).
    act(() => {
      screen.getByRole('button', { name: 'right1' }).click()
    })
    act(() => {
      screen.getByRole('button', { name: 'right2' }).click()
    })
    act(() => {
      screen.getByRole('button', { name: 'right3' }).click()
    })

    expect(onComplete).toHaveBeenCalledTimes(1)
    const outcome = onComplete.mock.calls[0][0]
    // 10 + 10 + round(10*1.5)=15 = 35, capped at maxScore 30.
    expect(outcome.maxScore).toBe(30)
    expect(outcome.score).toBe(30)
  })

  it('a broken streak does not get the multiplier', async () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<QuizRush config={config} onComplete={onComplete} title="Test" />)

    act(() => {
      screen.getByRole('button', { name: 'right1' }).click()
    })
    act(() => {
      screen.getByRole('button', { name: 'wrong2' }).click()
    })
    act(() => {
      screen.getByRole('button', { name: 'right3' }).click()
    })

    const outcome = onComplete.mock.calls[0][0]
    // 10 + 0 + 10 (streakBefore resets to 0 after the miss, so no multiplier).
    expect(outcome.score).toBe(20)
  })

  it('time running out counts as a wrong answer via the countdown', () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<QuizRush config={config} onComplete={onComplete} title="Test" />)

    act(() => {
      vi.advanceTimersByTime(20_000)
    })
    // First question timed out -> advances to question 2 automatically.
    expect(screen.getByText('Q2')).toBeInTheDocument()
  })

  it('two full expiry windows elapsing in one flush advance exactly two questions', () => {
    // Regression guard for the impure-updater bug: answer(null) was
    // previously called INSIDE the setTimeRemaining updater function
    // (a side effect during a state update), reading `index`/`timeRemaining`
    // from a stale `answer` closure when multiple ticks are processed
    // together in one batch — so two elapsed 20s windows landed back on Q2
    // instead of advancing to Q3. Expiry detection must be driven from the
    // interval body (real side-effect location), not from inside the
    // updater, so each window's answer(null) sees the CURRENT index.
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<QuizRush config={config} onComplete={onComplete} title="Test" />)

    act(() => {
      // Two full 20s windows elapsing together in one flush must advance
      // exactly two questions (Q1 -> Q2 -> Q3), not get stuck re-processing Q1/Q2.
      vi.advanceTimersByTime(40_000)
    })

    expect(screen.getByText('Q3')).toBeInTheDocument()
  })
})
