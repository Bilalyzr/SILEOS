/**
 * Bounded undo/redo history for the certificate designer's elements_config
 * array (plan Task 7 binding: "Undo/redo: bounded stack (50) of
 * elements_config snapshots — plain reducer, tested").
 *
 * Plain, framework-free reducer over a simple {past, present, future} shape
 * (classic linear undo/redo). Kept deliberately dumb: DesignerCanvas owns a
 * useReducer(designerHistoryReducer, ...) and dispatches PUSH on every
 * committed edit (drag end, resize end, property change, add/delete), UNDO/
 * REDO on toolbar buttons or Ctrl+Z/Ctrl+Shift+Z.
 */
import type { DesignerElement } from './certificateDesignerTypes'

export const MAX_HISTORY = 50

export interface DesignerHistoryState {
  past: DesignerElement[][]
  present: DesignerElement[]
  future: DesignerElement[][]
}

export type DesignerHistoryAction =
  | { type: 'PUSH'; elements: DesignerElement[] }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'RESET'; elements: DesignerElement[] }

export function createHistory(initial: DesignerElement[] = []): DesignerHistoryState {
  return { past: [], present: initial, future: [] }
}

/**
 * PUSH truncates any redo branch (standard undo/redo semantics — making a
 * new edit after undoing abandons the redone-away future) and caps `past`
 * at MAX_HISTORY entries, dropping the oldest snapshot once the cap is
 * exceeded so the stack never grows unbounded across a long editing session.
 */
export function designerHistoryReducer(
  state: DesignerHistoryState,
  action: DesignerHistoryAction
): DesignerHistoryState {
  switch (action.type) {
    case 'PUSH': {
      const nextPast = [...state.past, state.present]
      const trimmedPast = nextPast.length > MAX_HISTORY ? nextPast.slice(nextPast.length - MAX_HISTORY) : nextPast
      return { past: trimmedPast, present: action.elements, future: [] }
    }
    case 'UNDO': {
      if (state.past.length === 0) return state
      const previous = state.past[state.past.length - 1]
      const remainingPast = state.past.slice(0, -1)
      return { past: remainingPast, present: previous, future: [state.present, ...state.future] }
    }
    case 'REDO': {
      if (state.future.length === 0) return state
      const next = state.future[0]
      const remainingFuture = state.future.slice(1)
      const nextPast = [...state.past, state.present]
      const trimmedPast = nextPast.length > MAX_HISTORY ? nextPast.slice(nextPast.length - MAX_HISTORY) : nextPast
      return { past: trimmedPast, present: next, future: remainingFuture }
    }
    case 'RESET':
      return { past: [], present: action.elements, future: [] }
    default:
      return state
  }
}

export function canUndo(state: DesignerHistoryState): boolean {
  return state.past.length > 0
}

export function canRedo(state: DesignerHistoryState): boolean {
  return state.future.length > 0
}
