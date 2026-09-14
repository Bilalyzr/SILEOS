/** MatchPairs state-machine test: TOTAL failed match attempts on a pair are
 * passed to scoreMatchPair (no free first miss — BINDING).
 *
 * Cards render "?" until flipped and their grid order is shuffled inside
 * the component, so Math.random is mocked to a constant 0 to make the
 * internal Fisher-Yates shuffle deterministic. For the 4-card deck built
 * from `config` below (pushed as [Cat(pair0,L), Meow(pair0,R),
 * Dog(pair1,L), Woof(pair1,R)]), a shuffle with Math.random()=>0 always
 * produces grid order [Meow, Dog, Woof, Cat] — i.e. grid positions 0 and 3
 * are pair0 (Meow/Cat), and positions 1 and 2 are pair1 (Dog/Woof). This
 * mapping was derived by tracing the Fisher-Yates loop, not guessed. */
import { render, cleanup, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { MatchPairsConfig } from '@/api/games'
import { MatchPairs } from '../MatchPairs'
import type { GameOutcome } from '../QuizRush'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

const config: MatchPairsConfig = {
  items: [
    { left: 'Cat', right: 'Meow' },
    { left: 'Dog', right: 'Woof' },
  ],
  settings: { time_limit_s: 0 },
}

// Deterministic grid positions under the Math.random=>0 mock (see header).
const POS = { meow: 0, dog: 1, woof: 2, cat: 3 }

function allCards(): HTMLElement[] {
  const grid = document.querySelector('.grid') as HTMLElement
  return Array.from(grid.querySelectorAll('button'))
}

function flip(index: number) {
  act(() => { allCards()[index].click() })
}

describe('MatchPairs miss counting', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.spyOn(Math, 'random').mockReturnValue(0)
  })

  it('scores a pair matched with a prior miss as 10 - 1 (both cards touched the miss)', () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<MatchPairs config={config} onComplete={onComplete} title="Test" />)

    // Flip Meow(pair0) then Dog(pair1) -> mismatch -> both pairs' miss
    // counters go to 1.
    flip(POS.meow)
    flip(POS.dog)
    act(() => { vi.advanceTimersByTime(700) })

    // Match pair0: Meow + Cat, with 1 prior miss -> scoreMatchPair(1) = 9.
    flip(POS.meow)
    flip(POS.cat)
    act(() => { vi.advanceTimersByTime(700) })

    // Match pair1: Dog + Woof, with 1 prior miss -> scoreMatchPair(1) = 9.
    flip(POS.dog)
    flip(POS.woof)
    act(() => { vi.advanceTimersByTime(700) })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete.mock.calls[0][0].score).toBe(18) // 9 + 9
  })

  it('scores pairs matched with zero misses as the full 10 each', () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<MatchPairs config={config} onComplete={onComplete} title="Test" />)

    flip(POS.meow)
    flip(POS.cat)
    act(() => { vi.advanceTimersByTime(700) })

    flip(POS.dog)
    flip(POS.woof)
    act(() => { vi.advanceTimersByTime(700) })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete.mock.calls[0][0].score).toBe(20) // 10 + 10
  })
})

describe('MatchPairs timeout reports the banked score, not a stale mount-time value', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.spyOn(Math, 'random').mockReturnValue(0)
  })

  it('banks a match (score 10) then reports that banked score when the timer expires', () => {
    const timedConfig: MatchPairsConfig = {
      items: config.items,
      settings: { time_limit_s: 5 },
    }
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<MatchPairs config={timedConfig} onComplete={onComplete} title="Test" />)

    // Bank pair0 (Meow + Cat) with zero misses -> score becomes 10.
    flip(POS.meow)
    flip(POS.cat)
    act(() => { vi.advanceTimersByTime(700) })

    // Let the 5s countdown run out WITHOUT matching the second pair.
    act(() => { vi.advanceTimersByTime(5000) })

    expect(onComplete).toHaveBeenCalledTimes(1)
    // Must report the banked score (10), not 0 from a stale mount-time closure.
    expect(onComplete.mock.calls[0][0].score).toBe(10)
  })
})
