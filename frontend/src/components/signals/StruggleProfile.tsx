import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, Sparkles } from 'lucide-react'
import { signalsAPI, StruggleProfile as Profile, StruggleConcept } from '@/api/signals'
import AdaptivePractice from './AdaptivePractice'

interface Props { courseId?: number; userId?: number }

/** Explainable struggle profile: what the learner did (rewinds, quits,
 *  hesitation…) per concept, and a one-click practice set built from it. */
export default function StruggleProfile({ courseId, userId }: Props) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [practice, setPractice] = useState(false)
  const own = !userId

  useEffect(() => {
    let alive = true
    setLoading(true)
    const p = own ? signalsAPI.myProfile(courseId) : signalsAPI.studentProfile(userId as number, courseId as number)
    p.then((d) => { if (alive) setProfile(d) }).catch(() => { if (alive) setProfile(null) }).finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [courseId, userId, own])

  if (loading) return <div className="glass-panel p-5 text-sm text-gray-500">Reading learning signals…</div>
  if (!profile) return null

  const Row = ({ c }: { c: StruggleConcept }) => (
    <li className="flex items-start gap-3 py-2 border-b border-white/10 last:border-0" data-testid="struggle-row">
      <div className="w-24 shrink-0">
        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-orange-600" style={{ width: `${Math.max(4, c.struggle)}%` }} />
        </div>
        <div className="text-[11px] text-gray-500 mt-1">struggle {Math.round(c.struggle)}</div>
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-medium text-gray-900 capitalize">{c.concept}</div>
        <div className="text-xs text-gray-500">
          {c.why.join(' · ') || 'no strong signals'}
          {c.mastery != null && <span className="ml-2 text-primary-600">mastery {Math.round(c.mastery)}%</span>}
        </div>
      </div>
    </li>
  )

  return (
    <div className="glass-panel p-5 space-y-4" data-testid="struggle-profile">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary-600" />
          <h3 className="font-semibold text-gray-900">{own ? 'Where you struggle' : 'Where this learner struggles'}</h3>
          <span className="text-xs text-gray-500">{profile.signals} signals · last {profile.days} days</span>
        </div>
        {own && courseId && profile.signals > 0 && !practice && (
          <button type="button" className="si-btn-primary text-sm" onClick={() => setPractice(true)} data-testid="build-practice">
            <Sparkles className="w-4 h-4" /> Practice built for you
          </button>
        )}
      </div>

      {profile.signals === 0 ? (
        <p className="text-sm text-gray-500">No learning signals yet. Watch lessons, take notes and attempt quizzes — the platform learns where you slow down and builds practice around it.</p>
      ) : (
        <>
          {profile.struggling.length > 0 && (
            <div>
              <div className="flex items-center gap-1 text-sm font-medium text-amber-600 mb-1"><AlertTriangle className="w-4 h-4" /> Needs attention</div>
              <ul>{profile.struggling.map((c) => <Row key={c.concept} c={c} />)}</ul>
            </div>
          )}
          {profile.confident.length > 0 && (
            <div>
              <div className="flex items-center gap-1 text-sm font-medium text-emerald-600 mb-1"><CheckCircle2 className="w-4 h-4" /> Flowing well</div>
              <ul>{profile.confident.map((c) => <Row key={c.concept} c={c} />)}</ul>
            </div>
          )}
          {profile.struggling.length === 0 && profile.confident.length === 0 && (
            <ul>{profile.concepts.slice(0, 6).map((c) => <Row key={c.concept} c={c} />)}</ul>
          )}
        </>
      )}

      {practice && courseId && (
        <AdaptivePractice courseId={courseId} onClose={() => setPractice(false)} />
      )}
    </div>
  )
}
