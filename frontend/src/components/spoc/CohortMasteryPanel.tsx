/**
 * CohortMasteryPanel (roadmap R10): class-wise mastery for a cohort — the
 * weakest concepts across the class and every student's average, weakest
 * concept and at-risk flag. Derived from the learner mastery graph.
 */
import { useEffect, useState } from 'react'
import { api } from '@/api/axios'

interface Payload {
  cohort_id: number; cohort_name?: string; members: number; class_average: number | null
  concepts: { concept: string; average: number; learners: number; below_50: number }[]
  students: { user_id: number; name: string; average: number | null; concepts: number; weakest: string | null; weakest_estimate: number | null; risk: { severity: string; reasons: string[] } | null }[]
}

const tone = (v: number | null) => (v == null ? 'text-gray-400' : v < 50 ? 'text-red-700' : v < 75 ? 'text-amber-700' : 'text-emerald-700')

export function CohortMasteryPanel({ cohortId }: { cohortId: number }) {
  const [data, setData] = useState<Payload | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    api.get(`/cohorts/spoc/cohorts/${cohortId}/mastery`).then((r) => setData(r.data)).catch((e) => setError(e?.response?.data?.detail || 'Could not load mastery'))
  }, [cohortId])
  if (error) return <p className="text-sm text-red-600" role="alert">{error}</p>
  if (!data) return <p className="text-sm text-gray-500">Computing class mastery…</p>
  return (
    <div className="space-y-4" data-testid="cohort-mastery">
      <div className="grid sm:grid-cols-3 gap-3">
        <div className="glass-panel rounded-xl p-3"><p className="text-xs text-gray-500">Students</p><p className="text-xl font-semibold text-gray-900">{data.members}</p></div>
        <div className="glass-panel rounded-xl p-3"><p className="text-xs text-gray-500">Class average mastery</p><p className={`text-xl font-semibold ${tone(data.class_average)}`}>{data.class_average == null ? '—' : `${data.class_average}%`}</p></div>
        <div className="glass-panel rounded-xl p-3"><p className="text-xs text-gray-500">At risk</p><p className="text-xl font-semibold text-gray-900">{data.students.filter((s) => s.risk).length}</p></div>
      </div>
      <div className="glass-panel rounded-xl p-4">
        <h3 className="font-semibold text-gray-900 mb-2">Weakest concepts across the class</h3>
        {data.concepts.length === 0 ? <p className="text-sm text-gray-500">No mastery evidence yet — it appears once students take quizzes, labs, games or 3D tasks.</p> : (
          <ul className="space-y-1">
            {data.concepts.slice(0, 10).map((c) => (
              <li key={c.concept} className="flex items-center gap-3 text-sm">
                <span className="w-44 truncate capitalize text-gray-800">{c.concept}</span>
                <span className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden"><span className={`block h-full ${c.average < 50 ? 'bg-red-500' : c.average < 75 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${Math.max(3, c.average)}%` }} /></span>
                <span className={`w-12 text-right font-medium ${tone(c.average)}`}>{c.average}%</span>
                <span className="w-28 text-xs text-gray-500">{c.below_50} of {c.learners} below 50%</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="glass-panel rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-gray-500"><tr><th className="px-3 py-2">Student</th><th className="px-3 py-2">Average</th><th className="px-3 py-2">Concepts</th><th className="px-3 py-2">Weakest</th><th className="px-3 py-2">Risk</th></tr></thead>
          <tbody>
            {data.students.map((s) => (
              <tr key={s.user_id} className="border-t border-white/70">
                <td className="px-3 py-2 font-medium text-gray-900">{s.name}</td>
                <td className={`px-3 py-2 font-semibold ${tone(s.average)}`}>{s.average == null ? '—' : `${s.average}%`}</td>
                <td className="px-3 py-2">{s.concepts}</td>
                <td className="px-3 py-2 capitalize">{s.weakest ? `${s.weakest} (${s.weakest_estimate}%)` : '—'}</td>
                <td className="px-3 py-2">{s.risk ? <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700" title={s.risk.reasons.join('; ')}>{s.risk.severity}</span> : <span className="text-xs text-gray-400">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default CohortMasteryPanel
