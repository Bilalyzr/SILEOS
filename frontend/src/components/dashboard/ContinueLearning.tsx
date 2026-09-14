/**
 * ContinueLearning (roadmap R1): "pick up where you left off" rail on the
 * student dashboard — the last touched lesson per course with a one-click
 * resume. Hidden when the learner has never opened a lesson.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PlayCircle } from 'lucide-react'
import { funnelAPI, type ContinueItem } from '@/api/funnel'

const TYPE: Record<string, string> = { video: 'Video', text: 'Reading', three_d: '3D model', virtual_lab: 'Lab', game: 'Game', h5p: 'Interactive', geogebra: 'GeoGebra' }

export function ContinueLearning() {
  const [items, setItems] = useState<ContinueItem[] | null>(null)
  useEffect(() => { funnelAPI.continueLearning().then(setItems).catch(() => setItems([])) }, [])
  if (!items || items.length === 0) return null
  return (
    <div className="glass-panel rounded-2xl p-4 mb-6" data-testid="continue-learning">
      <div className="flex items-center gap-2 mb-3">
        <PlayCircle className="w-5 h-5 text-orange-600" />
        <h2 className="font-semibold text-gray-900">Continue where you left off</h2>
      </div>
      <div className="grid sm:grid-cols-3 gap-3">
        {items.map((it) => (
          <Link key={it.course_id} to={`/courses/${it.course_id}/lessons/${it.lesson_id}`} className="rounded-xl bg-white/80 border border-white/80 p-3 hover:shadow-md hover:-translate-y-0.5 transition block">
            <p className="text-[11px] uppercase tracking-wide text-orange-700 font-semibold">{TYPE[it.lesson_type] || it.lesson_type} · {it.lesson_status === 'completed' ? 'next up' : 'resume'}</p>
            <p className="text-sm font-semibold text-gray-900 line-clamp-1">{it.lesson_title}</p>
            <p className="text-xs text-gray-500 line-clamp-1">{it.course_title}</p>
            <div className="mt-2 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden"><div className="h-full si-gradient" style={{ width: `${Math.max(4, it.course_pct)}%` }} /></div>
            <p className="text-[11px] text-gray-500 mt-1">{it.course_pct}% of the course{it.video_pct > 0 && it.lesson_status !== 'completed' ? ` · video at ${it.video_pct}%` : ''}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default ContinueLearning
