/** Client-side inline validation mirroring the server caps in
 * backend/app/schemas/game_config.py (spec §1). Returns human-readable
 * errors; [] = valid. The SERVER is authoritative — this only powers the
 * builder's inline error hints and Save-button gating. */
import type {
  DragSortConfig,
  GameConfig,
  GameTemplate,
  MatchPairsConfig,
  QuizRushConfig,
  SequenceConfig,
  WordBuilderConfig,
} from '@/api/games'

export const MAX_CONFIG_BYTES = 64 * 1024
export const MAX_ITEM_STRING = 500
export const MAX_OPTION_STRING = 200
export const WORD_BUILDER_ANSWER_RE = /^[A-Za-z0-9 ]{2,24}$/

function checkStr(errors: string[], value: string, label: string, max = MAX_ITEM_STRING) {
  if (!value || !value.trim()) errors.push(`${label} is required`)
  else if (value.length > max) errors.push(`${label} must be at most ${max} characters`)
}

function checkRange(errors: string[], value: number, min: number, max: number, label: string) {
  if (!Number.isInteger(value) || value < min || value > max) {
    errors.push(`${label} must be between ${min} and ${max}`)
  }
}

export function validateConfigDraft(template: GameTemplate, config: GameConfig): string[] {
  const errors: string[] = []
  if (new Blob([JSON.stringify(config)]).size > MAX_CONFIG_BYTES) {
    errors.push('Game is too large (64KB config limit) — remove some items')
  }

  if (template === 'quiz_rush') {
    const c = config as QuizRushConfig
    checkRange(errors, c.items.length, 1, 50, 'Question count')
    c.items.forEach((item, i) => {
      checkStr(errors, item.prompt, `Question ${i + 1} prompt`)
      if (item.options.length < 2 || item.options.length > 6) {
        errors.push(`Question ${i + 1} needs 2 to 6 options`)
      }
      item.options.forEach((o, j) =>
        checkStr(errors, o, `Question ${i + 1} option ${j + 1}`, MAX_OPTION_STRING))
      if (item.answer_index < 0 || item.answer_index >= item.options.length) {
        errors.push(`Question ${i + 1} has no valid correct answer selected`)
      }
    })
    checkRange(errors, c.settings.seconds_per_question, 5, 120, 'Seconds per question')
  } else if (template === 'match_pairs') {
    const c = config as MatchPairsConfig
    checkRange(errors, c.items.length, 3, 12, 'Pair count')
    c.items.forEach((item, i) => {
      checkStr(errors, item.left, `Pair ${i + 1} left side`)
      checkStr(errors, item.right, `Pair ${i + 1} right side`)
    })
    checkRange(errors, c.settings.time_limit_s, 0, 600, 'Time limit')
  } else if (template === 'drag_sort') {
    const c = config as DragSortConfig
    checkRange(errors, c.categories.length, 2, 5, 'Category count')
    c.categories.forEach((cat, i) => checkStr(errors, cat.name, `Category ${i + 1} name`))
    checkRange(errors, c.items.length, 4, 40, 'Item count')
    c.items.forEach((item, i) => {
      checkStr(errors, item.text, `Item ${i + 1} text`)
      if (item.category_index < 0 || item.category_index >= c.categories.length) {
        errors.push(`Item ${i + 1} points at a missing category`)
      }
    })
    checkRange(errors, c.settings.time_limit_s, 0, 600, 'Time limit')
  } else if (template === 'word_builder') {
    const c = config as WordBuilderConfig
    checkRange(errors, c.items.length, 1, 20, 'Word count')
    c.items.forEach((item, i) => {
      checkStr(errors, item.clue, `Word ${i + 1} clue`)
      if (!WORD_BUILDER_ANSWER_RE.test(item.answer)) {
        errors.push(`Word ${i + 1} answer must be 2-24 letters, digits or spaces`)
      }
    })
    checkRange(errors, c.settings.hints_allowed, 0, 3, 'Hints allowed')
  } else if (template === 'sequence') {
    const c = config as SequenceConfig
    checkRange(errors, c.items.length, 3, 10, 'Step count')
    c.items.forEach((item, i) => checkStr(errors, item.text, `Step ${i + 1}`))
    checkRange(errors, c.settings.time_limit_s, 0, 600, 'Time limit')
  }

  return errors
}

/** Case-insensitive, trimmed key for duplicate comparisons below. Empty
 * strings are excluded by the callers (an empty field is already flagged
 * by validateConfigDraft as a blocking error — it shouldn't also produce a
 * confusing "duplicate" warning against other empty fields). */
function normKey(value: string): string {
  return value.trim().toLowerCase()
}

/**
 * NON-BLOCKING content-quality warnings — technically-valid configs that
 * are still probably authoring mistakes (ledger "Task 10: F6 RULED"):
 *   - match_pairs: two pairs with identical left+right (case-insensitive,
 *     trimmed) — an unplayable duplicate pair.
 *   - quiz_rush: duplicate options within the SAME question — no
 *     unambiguous correct answer from the player's point of view.
 *   - drag_sort: duplicate category names — items can't be told apart by
 *     category in the UI.
 * Returns human-readable warnings; [] = none. Callers (game-builder.tsx)
 * MUST NOT gate Save/Publish on this — see validateConfigDraft for the
 * blocking checks.
 */
export function duplicateWarnings(template: GameTemplate, config: GameConfig): string[] {
  const warnings: string[] = []

  if (template === 'quiz_rush') {
    const c = config as QuizRushConfig
    c.items.forEach((item, i) => {
      const seen = new Set<string>()
      item.options.forEach((o) => {
        const key = normKey(o)
        if (!key) return
        if (seen.has(key)) {
          warnings.push(`Question ${i + 1} has duplicate options ("${o.trim()}")`)
        }
        seen.add(key)
      })
    })
  } else if (template === 'match_pairs') {
    const c = config as MatchPairsConfig
    const seen = new Set<string>()
    c.items.forEach((item, i) => {
      const leftKey = normKey(item.left)
      const rightKey = normKey(item.right)
      if (!leftKey || !rightKey) return
      const key = `${leftKey}\u0000${rightKey}`
      if (seen.has(key)) {
        warnings.push(`Pair ${i + 1} duplicates another pair ("${item.left.trim()}" / "${item.right.trim()}")`)
      }
      seen.add(key)
    })
  } else if (template === 'drag_sort') {
    const c = config as DragSortConfig
    const seen = new Set<string>()
    c.categories.forEach((cat, i) => {
      const key = normKey(cat.name)
      if (!key) return
      if (seen.has(key)) {
        warnings.push(`Category ${i + 1} duplicates another category name ("${cat.name.trim()}")`)
      }
      seen.add(key)
    })
  }

  return warnings
}
