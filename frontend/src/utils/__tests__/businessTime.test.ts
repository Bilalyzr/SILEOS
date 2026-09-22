import { describe, expect, it } from 'vitest'
import { businessDate } from '../businessTime'

describe('businessDate', () => {
  it('uses the India business date across the UTC midnight boundary', () => {
    const instant = new Date('2026-09-12T19:00:00.000Z')
    expect(businessDate(0, instant)).toBe('2026-09-13')
    expect(businessDate(-1, instant)).toBe('2026-09-12')
  })
})
