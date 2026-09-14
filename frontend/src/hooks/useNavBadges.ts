/**
 * useNavBadges (roadmap R2): live counts on side-rail links. Instructors and
 * admins see the review-queue total (open learner questions + error reports
 * + AI drafts); refreshed every two minutes and on focus. Cheap endpoint —
 * item-statistics flags are deliberately excluded from the badge.
 */
import { useEffect, useMemo, useState } from 'react'
import { api } from '@/api/axios'

interface Badgeable { to?: string; badge?: number | string; kind?: string; children?: Badgeable[] }

export function useNavBadges<T extends Badgeable>(role: string, items: T[]): T[] {
  const [queue, setQueue] = useState<number | null>(null)
  useEffect(() => {
    if (role !== 'instructor' && role !== 'admin' && role !== 'superadmin') return
    let alive = true
    const load = () => api.get('/ai/review-queue/counts').then((r) => { if (alive) setQueue(Number(r.data?.total) || 0) }).catch(() => {})
    load()
    const id = setInterval(load, 120_000)
    const onFocus = () => load()
    window.addEventListener('focus', onFocus)
    return () => { alive = false; clearInterval(id); window.removeEventListener('focus', onFocus) }
  }, [role])
  return useMemo(() => {
    if (!queue) return items
    const decorate = <U extends Badgeable>(it: U): U => ({
      ...it,
      ...(it.to === '/instructor/review-queue' ? { badge: queue } : {}),
      ...(it.children ? { children: it.children.map(decorate) } : {}),
    })
    return items.map(decorate)
  }, [items, queue])
}
