import { describe, it, expect } from 'vitest'
import {
  designerHistoryReducer,
  createHistory,
  canUndo,
  canRedo,
  MAX_HISTORY,
} from '../designerHistory'
import type { DesignerElement } from '../certificateDesignerTypes'

function el(id: string, x = 0): DesignerElement {
  return { id, type: 'text', x, y: 0, width: 10, height: 10, z_index: 0 }
}

describe('designerHistoryReducer', () => {
  it('starts with no undo/redo available', () => {
    const state = createHistory([el('a')])
    expect(canUndo(state)).toBe(false)
    expect(canRedo(state)).toBe(false)
    expect(state.present).toEqual([el('a')])
  })

  it('push adds a past entry and sets present', () => {
    let state = createHistory([el('a')])
    state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', 5)] })
    expect(state.present).toEqual([el('a', 5)])
    expect(state.past).toEqual([[el('a')]])
    expect(canUndo(state)).toBe(true)
    expect(canRedo(state)).toBe(false)
  })

  it('undo restores the previous snapshot and populates future', () => {
    let state = createHistory([el('a', 0)])
    state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', 1)] })
    state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', 2)] })

    state = designerHistoryReducer(state, { type: 'UNDO' })
    expect(state.present).toEqual([el('a', 1)])
    expect(state.past).toEqual([[el('a', 0)]])
    expect(state.future).toEqual([[el('a', 2)]])
  })

  it('undo is a no-op at the start of history', () => {
    const state = createHistory([el('a')])
    const next = designerHistoryReducer(state, { type: 'UNDO' })
    expect(next).toBe(state)
  })

  it('redo re-applies an undone snapshot', () => {
    let state = createHistory([el('a', 0)])
    state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', 1)] })
    state = designerHistoryReducer(state, { type: 'UNDO' })
    state = designerHistoryReducer(state, { type: 'REDO' })
    expect(state.present).toEqual([el('a', 1)])
    expect(canRedo(state)).toBe(false)
  })

  it('redo is a no-op with no future', () => {
    const state = createHistory([el('a')])
    const next = designerHistoryReducer(state, { type: 'REDO' })
    expect(next).toBe(state)
  })

  it('a fresh push after undo truncates the redo branch', () => {
    let state = createHistory([el('a', 0)])
    state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', 1)] })
    state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', 2)] })
    state = designerHistoryReducer(state, { type: 'UNDO' }) // present = 1, future = [2]
    expect(canRedo(state)).toBe(true)

    state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', 99)] })
    expect(state.present).toEqual([el('a', 99)])
    expect(state.future).toEqual([])
    expect(canRedo(state)).toBe(false)
  })

  it('caps past at MAX_HISTORY entries, dropping the oldest', () => {
    let state = createHistory([el('a', 0)])
    for (let i = 1; i <= MAX_HISTORY + 10; i += 1) {
      state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', i)] })
    }
    expect(state.past.length).toBe(MAX_HISTORY)
    // Oldest surviving past entry should be x=10 (0..9 dropped), since we
    // pushed MAX_HISTORY+10 times starting from x=0.
    expect(state.past[0]).toEqual([el('a', 10)])
    expect(state.present).toEqual([el('a', MAX_HISTORY + 10)])
  })

  it('caps past growth through redo pushes too', () => {
    let state = createHistory([el('a', 0)])
    for (let i = 1; i <= MAX_HISTORY + 5; i += 1) {
      state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', i)] })
    }
    state = designerHistoryReducer(state, { type: 'UNDO' })
    state = designerHistoryReducer(state, { type: 'REDO' })
    expect(state.past.length).toBeLessThanOrEqual(MAX_HISTORY)
  })

  it('RESET clears past/future and sets a new present', () => {
    let state = createHistory([el('a', 0)])
    state = designerHistoryReducer(state, { type: 'PUSH', elements: [el('a', 1)] })
    state = designerHistoryReducer(state, { type: 'RESET', elements: [el('b', 0)] })
    expect(state.present).toEqual([el('b', 0)])
    expect(state.past).toEqual([])
    expect(state.future).toEqual([])
  })
})
