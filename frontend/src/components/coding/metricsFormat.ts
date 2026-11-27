/** Display helpers for coding analytics. Pure functions, no React. */

export function formatPercent(rate: number): string {
  if (!Number.isFinite(rate) || rate <= 0) return '0%'
  return `${Math.round(rate * 1000) / 10}%`
}

export function formatMinutes(minutes: number | null): string {
  if (minutes === null || !Number.isFinite(minutes)) return '—'
  if (minutes < 1) return '<1 min'
  if (minutes < 60) return `${Math.round(minutes)} min`
  const hours = Math.floor(minutes / 60)
  const rest = Math.round(minutes - hours * 60)
  return rest ? `${hours} h ${rest} min` : `${hours} h`
}

export function formatMs(ms: number | null): string {
  if (ms === null || !Number.isFinite(ms)) return '—'
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`
}

export function formatMemoryKb(kb: number | null): string {
  if (kb === null || !Number.isFinite(kb) || kb <= 0) return '—'
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.round(kb)} KB`
}

export function formatScore(score: number): string {
  return Number.isFinite(score) ? `${Math.round(score * 10) / 10}` : '—'
}
