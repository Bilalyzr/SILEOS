import { describe, expect, it } from 'vitest'
import { formatMemoryKb, formatMinutes, formatMs, formatPercent, formatScore } from '../metricsFormat'

describe('coding analytics formatting', () => {
  it('formats pass rates from 0 to 1 as percentages', () => {
    expect(formatPercent(0.667)).toBe('66.7%')
    expect(formatPercent(1)).toBe('100%')
    expect(formatPercent(0)).toBe('0%')
    expect(formatPercent(Number.NaN)).toBe('0%')
  })

  it('formats durations and missing values', () => {
    expect(formatMinutes(null)).toBe('—')
    expect(formatMinutes(0.4)).toBe('<1 min')
    expect(formatMinutes(12.6)).toBe('13 min')
    expect(formatMinutes(125)).toBe('2 h 5 min')
    expect(formatMinutes(120)).toBe('2 h')
  })

  it('formats judge time and memory', () => {
    expect(formatMs(20)).toBe('20 ms')
    expect(formatMs(1500)).toBe('1.50 s')
    expect(formatMs(null)).toBe('—')
    expect(formatMemoryKb(9216)).toBe('9.0 MB')
    expect(formatMemoryKb(512)).toBe('512 KB')
    expect(formatMemoryKb(0)).toBe('—')
  })

  it('rounds scores to one decimal', () => {
    expect(formatScore(100)).toBe('100')
    expect(formatScore(66.666)).toBe('66.7')
    expect(formatScore(Number.NaN)).toBe('—')
  })
})
