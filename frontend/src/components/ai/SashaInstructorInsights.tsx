import { useEffect, useState } from 'react'
import {
  Activity, AlertTriangle, BrainCircuit, Clock3, MessageCircle,
  RefreshCw, ShieldCheck, Sparkles, UserCheck, Users,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { signalsAPI, type SashaCourseInsights } from '@/api/signals'

const severityStyles = {
  high: 'border-rose-200 bg-rose-50 text-rose-700',
  watch: 'border-orange-200 bg-orange-50 text-orange-700',
  developing: 'border-amber-200 bg-amber-50 text-amber-700',
}

const when = (value: string | null) => {
  if (!value) return 'No timestamp'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Recently' : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
}

export function SashaInstructorInsights({ courseId }: { courseId: number }) {
  const [days, setDays] = useState(30)
  const [data, setData] = useState<SashaCourseInsights | null>(null)
  const [loading, setLoading] = useState(true)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    signalsAPI.sashaInsights(courseId, days)
      .then((result) => { if (active) setData(result) })
      .catch(() => { if (active) toast.error('Could not load Sasha learning insights') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [courseId, days, retry])

  if (loading) return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" role="status" aria-label="Loading Sasha learning insights">
      {[1, 2, 3, 4].map((item) => <div key={item} className="h-32 animate-pulse rounded-3xl bg-orange-100/70" />)}
    </div>
  )

  if (!data) return (
    <div className="rounded-3xl border border-orange-200 bg-orange-50 p-8 text-center">
      <AlertTriangle className="mx-auto h-8 w-8 text-orange-600" />
      <p className="mt-3 font-semibold text-slate-950">Sasha insights are temporarily unavailable.</p>
      <button onClick={() => setRetry((value) => value + 1)} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-orange-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-700"><RefreshCw className="h-4 w-4" /> Try again</button>
    </div>
  )

  const metrics = [
    { label: 'Students using Sasha', value: data.summary.active_students, detail: `${data.summary.questions} course-linked questions`, icon: Users },
    { label: 'Need your attention', value: data.summary.students_needing_attention, detail: 'Repeated or high-concern evidence', icon: UserCheck },
    { label: 'Average concern', value: `${data.summary.average_struggle}%`, detail: 'Explainable learning signal', icon: Activity },
    { label: 'High-concern prompts', value: data.summary.high_concern_questions, detail: 'Prioritise before the next class', icon: AlertTriangle },
  ]

  return (
    <section className="sasha-instructor-monitor space-y-6" aria-label="Sasha learning monitor">
      <div className="relative overflow-hidden rounded-[2rem] border border-orange-200 bg-[linear-gradient(125deg,#fff7ed_0%,#ffedd5_46%,#fef3c7_100%)] p-6 shadow-[0_24px_70px_rgba(234,88,12,.10)] md:p-8">
        <div className="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full bg-gradient-to-br from-orange-400/30 to-amber-300/20 blur-2xl" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-orange-300 bg-white/75 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.16em] text-orange-700"><Sparkles className="h-3.5 w-3.5" /> Sasha learning intelligence</span>
            <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-950 md:text-4xl">Know who is stuck—and why.</h2>
            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-700">Course-linked tutor questions become intervention evidence. Concern scores combine the learner’s language, repeated questions and verified mastery—not an opaque AI guess.</p>
          </div>
          <label className="relative z-10 flex items-center gap-3 rounded-2xl border border-orange-200 bg-white/85 px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm">
            <Clock3 className="h-4 w-4 text-orange-600" /> Window
            <select value={days} onChange={(event) => setDays(Number(event.target.value))} className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-sm font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-orange-400">
              <option value={7}>7 days</option><option value={30}>30 days</option><option value={60}>60 days</option><option value={90}>90 days</option>
            </select>
          </label>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, detail, icon: Icon }) => (
          <article key={label} className="rounded-3xl border border-orange-100 bg-white p-5 shadow-[0_14px_45px_rgba(15,23,42,.055)]">
            <div className="flex items-start justify-between"><p className="text-sm font-semibold text-slate-600">{label}</p><span className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-orange-500 to-amber-400 text-white shadow-lg shadow-orange-200"><Icon className="h-5 w-5" /></span></div>
            <p className="mt-5 text-3xl font-black tracking-tight text-slate-950">{value}</p>
            <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>
          </article>
        ))}
      </div>

      {data.summary.questions === 0 ? (
        <div className="rounded-3xl border border-dashed border-orange-300 bg-orange-50/60 p-10 text-center">
          <BrainCircuit className="mx-auto h-10 w-10 text-orange-500" />
          <h3 className="mt-4 text-xl font-bold text-slate-950">No course-linked Sasha questions yet</h3>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">When enrolled students choose this course in Learn with Sasha, their questions will appear here as privacy-bounded learning signals.</p>
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,.65fr)]">
          <div className="space-y-6">
            <section className="overflow-hidden rounded-3xl border border-orange-100 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-orange-100 px-5 py-4 md:px-6"><div><h3 className="text-lg font-bold text-slate-950">Students to check in with</h3><p className="mt-1 text-sm text-slate-500">Ranked by strongest and average concern evidence.</p></div><Users className="h-5 w-5 text-orange-600" /></div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-orange-50/70 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-6 py-3">Student</th><th className="px-4 py-3">Concern</th><th className="px-4 py-3">Likely gap</th><th className="px-4 py-3">Where they lag</th><th className="px-4 py-3">Evidence</th></tr></thead>
                  <tbody className="divide-y divide-orange-50">
                    {data.students.map((student) => (
                      <tr key={student.user_id} className="align-top transition hover:bg-orange-50/35">
                        <td className="px-6 py-4"><p className="font-bold text-slate-900">{student.name}</p><p className="mt-1 text-xs text-slate-500">{student.email}</p></td>
                        <td className="px-4 py-4"><span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${severityStyles[student.severity]}`}>{student.risk_score}% · {student.severity}</span><p className="mt-2 text-xs text-slate-500">{student.questions} question{student.questions === 1 ? '' : 's'}</p></td>
                        <td className="px-4 py-4 font-semibold text-slate-700">{student.likely_gap}</td>
                        <td className="px-4 py-4"><div className="flex max-w-xs flex-wrap gap-1.5">{student.top_concepts.map((concept) => <span key={concept} className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-800">{concept}</span>)}</div></td>
                        <td className="max-w-xs px-4 py-4"><p className="line-clamp-2 text-slate-600">“{student.evidence[0] || 'Course-linked question'}”</p><p className="mt-2 text-xs text-slate-400">{when(student.last_seen)}</p></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-3xl border border-orange-100 bg-white p-5 shadow-sm md:p-6">
              <div className="flex items-center justify-between"><div><h3 className="text-lg font-bold text-slate-950">Concept pressure map</h3><p className="mt-1 text-sm text-slate-500">Teach the strongest shared gaps first.</p></div><BrainCircuit className="h-5 w-5 text-orange-600" /></div>
              <div className="mt-5 space-y-4">
                {data.concepts.map((concept) => (
                  <div key={concept.concept}>
                    <div className="mb-2 flex items-end justify-between gap-4"><div><p className="font-semibold text-slate-900">{concept.concept}</p><p className="text-xs text-slate-500">{concept.learners} learner{concept.learners === 1 ? '' : 's'} · {concept.questions} questions · {concept.likely_gap}</p></div><span className="text-sm font-black text-orange-700">{concept.score}%</span></div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-orange-100"><div className="h-full rounded-full bg-gradient-to-r from-orange-500 via-orange-400 to-amber-300" style={{ width: `${Math.max(6, concept.score)}%` }} /></div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-3xl border border-orange-100 bg-[#17110d] p-5 text-white shadow-xl shadow-orange-950/10 md:p-6">
              <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-orange-500 to-amber-400 text-white"><MessageCircle className="h-5 w-5" /></span><div><h3 className="font-bold">Live learning evidence</h3><p className="text-xs text-orange-100/65">Latest course-linked questions</p></div></div>
              <div className="mt-5 space-y-3">
                {data.recent.slice(0, 6).map((signal) => (
                  <article key={signal.id} className="rounded-2xl border border-white/10 bg-white/[0.055] p-4">
                    <div className="flex items-center justify-between gap-3"><p className="text-sm font-bold text-orange-100">{signal.student_name}</p><span className="rounded-full bg-orange-400/15 px-2 py-1 text-xs font-bold text-orange-200">{signal.score}%</span></div>
                    <p className="mt-2 text-sm leading-6 text-stone-200">“{signal.excerpt}”</p>
                    <div className="mt-3 flex flex-wrap gap-1.5"><span className="rounded-full bg-white/10 px-2 py-1 text-xs text-stone-300">{signal.concept}</span><span className="rounded-full bg-white/10 px-2 py-1 text-xs text-stone-300">{signal.likely_gap}</span></div>
                    <p className="mt-3 text-xs text-stone-500">{when(signal.created_at)}</p>
                  </article>
                ))}
              </div>
            </section>

            <div className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5">
              <p className="flex items-center gap-2 text-sm font-bold text-emerald-900"><ShieldCheck className="h-5 w-5" /> Privacy boundary</p>
              <p className="mt-2 text-sm leading-6 text-emerald-800">{data.privacy}</p>
            </div>
          </aside>
        </div>
      )}
    </section>
  )
}

export default SashaInstructorInsights
