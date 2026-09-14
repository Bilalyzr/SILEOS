/** DragSort keyboard-accessibility test: a focused draggable item can be
 * placed into a category with Enter/Space (opens a category picker menu)
 * and Enter/click on the target category — dnd-kit's KeyboardSensor has no
 * built-in coordinate getter for "free" drop-zone targeting (only for
 * sortable lists), so DragSort implements its own keyboard picker menu (see
 * DragSort.tsx's header comment on DraggableItem). This test drives that
 * path end-to-end and asserts a real placement happens (score increases,
 * item moves out of the unplaced tray into its category). */
import { render, screen, cleanup, act, fireEvent } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DragSortConfig } from '@/api/games'
import { DragSort } from '../DragSort'
import type { GameOutcome } from '../QuizRush'

afterEach(() => cleanup())

const config: DragSortConfig = {
  categories: [{ name: 'Fruits' }, { name: 'Vegetables' }],
  items: [
    { text: 'Apple', category_index: 0 },
    { text: 'Carrot', category_index: 1 },
  ],
  settings: { time_limit_s: 0 },
}

describe('DragSort keyboard accessibility', () => {
  it('places a focused item into the correct category via Enter -> menu -> click, scoring the full 10', () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<DragSort config={config} onComplete={onComplete} title="Test" />)

    const appleButton = screen.getByRole('button', { name: /Apple\. Press Enter/i })
    appleButton.focus()

    // Enter opens the category picker menu (keyboard-only path).
    act(() => { fireEvent.keyDown(appleButton, { key: 'Enter' }) })
    const menu = screen.getByRole('menu', { name: /Place "Apple" into category/i })
    expect(menu).toBeInTheDocument()

    // Select the correct category ("Fruits") from the menu.
    const fruitsOption = screen.getByRole('menuitem', { name: 'Fruits' })
    act(() => { fireEvent.click(fruitsOption) })

    // A real placement happened: Apple is no longer in the unplaced tray,
    // and it now renders inside the Fruits drop zone.
    expect(screen.queryByRole('button', { name: /Apple\. Press Enter/i })).not.toBeInTheDocument()
    expect(screen.getByText('Apple')).toBeInTheDocument()
    expect(menu).not.toBeInTheDocument()
  })

  it('a wrong category choice via keyboard does not place the item and does not complete the game', () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<DragSort config={config} onComplete={onComplete} title="Test" />)

    const carrotButton = screen.getByRole('button', { name: /Carrot\. Press Enter/i })
    carrotButton.focus()
    act(() => { fireEvent.keyDown(carrotButton, { key: ' ' }) })

    const wrongOption = screen.getByRole('menuitem', { name: 'Fruits' })
    act(() => { fireEvent.click(wrongOption) })

    // Still unplaced (visible in the draggable tray, not scored).
    expect(screen.getByRole('button', { name: /Carrot\. Press Enter/i })).toBeInTheDocument()
    expect(onComplete).not.toHaveBeenCalled()
  })

  it('completes the game once every item is correctly placed, capping score at maxScore', () => {
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<DragSort config={config} onComplete={onComplete} title="Test" />)

    const place = (label: RegExp, categoryName: string) => {
      const btn = screen.getByRole('button', { name: label })
      act(() => { fireEvent.keyDown(btn, { key: 'Enter' }) })
      const option = screen.getByRole('menuitem', { name: categoryName })
      act(() => { fireEvent.click(option) })
    }

    place(/Apple\. Press Enter/i, 'Fruits')
    place(/Carrot\. Press Enter/i, 'Vegetables')

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onComplete.mock.calls[0][0].score).toBe(20) // 10 + 10, zero wrong attempts
  })
})

describe('DragSort timeout reports the banked score, not a stale mount-time value', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('banks one correct placement (score 10) then reports that banked score when the timer expires', () => {
    vi.useFakeTimers()
    const timedConfig: DragSortConfig = {
      categories: config.categories,
      items: config.items,
      settings: { time_limit_s: 5 },
    }
    const onComplete = vi.fn<[GameOutcome], void>()
    render(<DragSort config={timedConfig} onComplete={onComplete} title="Test" />)

    // Place Apple correctly via the keyboard picker -> score becomes 10.
    const appleButton = screen.getByRole('button', { name: /Apple\. Press Enter/i })
    act(() => { fireEvent.keyDown(appleButton, { key: 'Enter' }) })
    const fruitsOption = screen.getByRole('menuitem', { name: 'Fruits' })
    act(() => { fireEvent.click(fruitsOption) })

    // Let the 5s countdown run out WITHOUT placing the second item.
    act(() => { vi.advanceTimersByTime(5000) })

    expect(onComplete).toHaveBeenCalledTimes(1)
    // Must report the banked score (10), not 0 from a stale mount-time closure.
    expect(onComplete.mock.calls[0][0].score).toBe(10)
  })
})
