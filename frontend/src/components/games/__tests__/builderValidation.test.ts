import { describe, expect, it } from 'vitest'
import { validateConfigDraft, duplicateWarnings } from '../builderValidation'

describe('validateConfigDraft', () => {
  it('accepts a valid quiz_rush config', () => {
    expect(validateConfigDraft('quiz_rush', {
      items: [{ prompt: 'Q?', options: ['a', 'b'], answer_index: 0 }],
      settings: { seconds_per_question: 20, shuffle: false },
    })).toEqual([])
  })

  it('flags item-count, option-count, index, and length violations', () => {
    const errors = validateConfigDraft('quiz_rush', {
      items: [{ prompt: 'p'.repeat(501), options: ['only'], answer_index: 5 }],
      settings: { seconds_per_question: 200, shuffle: false },
    })
    expect(errors.length).toBeGreaterThanOrEqual(4)
  })

  it('enforces word_builder answer regex', () => {
    const errors = validateConfigDraft('word_builder', {
      items: [{ clue: 'c', answer: 'bad!char' }],
      settings: { hints_allowed: 0 },
    })
    expect(errors.some((e) => e.includes('letters'))).toBe(true)
  })

  it('enforces per-template item ranges', () => {
    expect(validateConfigDraft('match_pairs', {
      items: [{ left: 'l', right: 'r' }],
      settings: { time_limit_s: 0 },
    }).length).toBeGreaterThan(0)
    expect(validateConfigDraft('sequence', {
      items: [{ text: 'a' }, { text: 'b' }],
      settings: { time_limit_s: 0, shuffle: true },
    }).length).toBeGreaterThan(0)
  })
})

describe('duplicateWarnings', () => {
  it('is empty for a config with no duplicates', () => {
    expect(duplicateWarnings('quiz_rush', {
      items: [{ prompt: 'Q?', options: ['a', 'b', 'c'], answer_index: 0 }],
      settings: { seconds_per_question: 20, shuffle: false },
    })).toEqual([])
    expect(duplicateWarnings('match_pairs', {
      items: [{ left: 'A', right: '1' }, { left: 'B', right: '2' }, { left: 'C', right: '3' }],
      settings: { time_limit_s: 0 },
    })).toEqual([])
    expect(duplicateWarnings('drag_sort', {
      categories: [{ name: 'Frontend' }, { name: 'Backend' }],
      items: [{ text: 'React', category_index: 0 }, { text: 'FastAPI', category_index: 1 },
        { text: 'Vite', category_index: 0 }, { text: 'SQLAlchemy', category_index: 1 }],
      settings: { time_limit_s: 0 },
    })).toEqual([])
  })

  it('flags duplicate options within the same quiz_rush question (case-insensitive, trimmed) but not across questions', () => {
    const warnings = duplicateWarnings('quiz_rush', {
      items: [
        { prompt: 'Q1', options: ['Blue', '  blue  ', 'Green'], answer_index: 0 },
        { prompt: 'Q2', options: ['Blue', 'Red'], answer_index: 0 },
      ],
      settings: { seconds_per_question: 20, shuffle: false },
    })
    expect(warnings.length).toBe(1)
    expect(warnings[0]).toMatch(/Question 1/)
  })

  it('flags identical match_pairs pairs (same left+right, case-insensitive, trimmed)', () => {
    const warnings = duplicateWarnings('match_pairs', {
      items: [
        { left: 'Nucleus', right: 'Stores DNA' },
        { left: '  nucleus ', right: ' stores dna ' },
        { left: 'Ribosome', right: 'Makes proteins' },
      ],
      settings: { time_limit_s: 0 },
    })
    expect(warnings.length).toBe(1)
    expect(warnings[0]).toMatch(/Pair 2/)
  })

  it('does NOT flag pairs that share only one side (left matches but right differs)', () => {
    const warnings = duplicateWarnings('match_pairs', {
      items: [
        { left: 'Nucleus', right: 'Stores DNA' },
        { left: 'Nucleus', right: 'A different definition' },
        { left: 'Ribosome', right: 'Makes proteins' },
      ],
      settings: { time_limit_s: 0 },
    })
    expect(warnings).toEqual([])
  })

  it('does NOT false-positive when a space-joined left+right straddles the left/right boundary differently across two pairs', () => {
    // "cat" + "dog x" and "cat dog" + "x" both joined with a plain space
    // collide as the same "cat dog x" key, even though neither pair is
    // actually a duplicate of the other (their left/right split differs).
    const warnings = duplicateWarnings('match_pairs', {
      items: [
        { left: 'cat', right: 'dog x' },
        { left: 'cat dog', right: 'x' },
      ],
      settings: { time_limit_s: 0 },
    })
    expect(warnings).toEqual([])
  })

  it('flags duplicate drag_sort category names (case-insensitive, trimmed)', () => {
    const warnings = duplicateWarnings('drag_sort', {
      categories: [{ name: 'Frontend' }, { name: ' frontend ' }],
      items: [{ text: 'React', category_index: 0 }, { text: 'Vue', category_index: 1 },
        { text: 'FastAPI', category_index: 0 }, { text: 'Django', category_index: 1 }],
      settings: { time_limit_s: 0 },
    })
    expect(warnings.length).toBe(1)
    expect(warnings[0]).toMatch(/Category 2/)
  })

  it('is empty for word_builder and sequence (no duplicate rule defined for those templates)', () => {
    expect(duplicateWarnings('word_builder', {
      items: [{ clue: 'c1', answer: 'same' }, { clue: 'c2', answer: 'same' }],
      settings: { hints_allowed: 0 },
    })).toEqual([])
    expect(duplicateWarnings('sequence', {
      items: [{ text: 'Step' }, { text: 'Step' }, { text: 'Other' }],
      settings: { time_limit_s: 0, shuffle: true },
    })).toEqual([])
  })

  it('ignores empty/blank fields rather than flagging them as duplicates of each other', () => {
    expect(duplicateWarnings('match_pairs', {
      items: [{ left: '', right: '' }, { left: '  ', right: '  ' }, { left: 'A', right: 'B' }],
      settings: { time_limit_s: 0 },
    })).toEqual([])
  })
})
