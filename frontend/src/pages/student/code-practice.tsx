import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Braces, ChevronRight, Clock3, Cpu, Languages } from 'lucide-react'
import { codingAPI, type ChallengeSummary, type LearnerCodingProgress } from '@/api/coding'
import { plannerError } from '@/api/planner'
import { PageHeader, PageLayout } from '@/components/design-system/PageLayout'
import { formatMemoryKb, formatMs, formatScore } from '@/components/coding/metricsFormat'

export default function CodePracticePage() {
  const [rows, setRows] = useState<ChallengeSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    codingAPI.learnerChallenges()
      .then((data) => active && setRows(data))
      .catch((reason) => active && setError(plannerError(reason)))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  return (
    <PageLayout
      className="rd-screen rd-screen-code-practice"
      header={<PageHeader><div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">Utporul · Applied skills</p>
        <h1 className="dash-h1 mt-1">Code practice</h1>
        <p className="mt-2 max-w-2xl text-slate-600">Solve instructor-published challenges in a resource-limited, network-isolated judge.</p>
      </div></PageHeader>}
    >
      {error && <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      <ProgressPanel />
      {loading ? (
        <div className="glass-panel rounded-2xl p-8 text-slate-500">Loading your challenges…</div>
      ) : rows.length === 0 ? (
        <div className="glass-panel rounded-2xl p-10 text-center">
          <Braces className="mx-auto h-10 w-10 text-violet-500" />
          <h2 className="mt-4 text-lg font-semibold text-slate-900">No coding challenges yet</h2>
          <p className="mt-2 text-sm text-slate-600">Published challenges from your enrolled Utporul courses will appear here.</p>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {rows.map((row) => {
            const remaining = Math.max(0, row.max_attempts - row.attempts_used)
            return <Link key={row.id} to={`/coding/${row.slug}`} className="glass-panel group rounded-2xl border border-white/70 p-5 transition hover:-translate-y-0.5 hover:border-violet-200 hover:shadow-lg">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-violet-600">{row.course_title}</p>
                  <h2 className="mt-2 text-lg font-semibold text-slate-950">{row.title}</h2>
                </div>
                <ChevronRight className="mt-1 h-5 w-5 text-slate-400 transition group-hover:translate-x-1 group-hover:text-violet-600" />
              </div>
              <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-600">
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1"><Languages className="h-3.5 w-3.5" />{row.allowed_languages.length} languages</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1"><Clock3 className="h-3.5 w-3.5" />{row.time_limit_ms} ms</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1"><Cpu className="h-3.5 w-3.5" />{row.memory_limit_mb} MB</span>
                <span className={`rounded-full px-2.5 py-1 ${remaining ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>{remaining} attempts left</span>
              </div>
            </Link>
          })}
        </div>
      )}
    </PageLayout>
  )
}

function ProgressPanel() {
  const [progress, setProgress] = useState<LearnerCodingProgress | null>(null)

  useEffect(() => {
    let active = true
    codingAPI.learnerProgress()
      .then((data) => active && setProgress(data))
      .catch(() => active && setProgress(null))
    return () => { active = false }
  }, [])

  if (!progress || progress.summary.challenges_total === 0) return null
  const { summary, challenges, history } = progress

  return (
    <section aria-labelledby="code-progress-heading" className="glass-panel mb-6 rounded-2xl p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="code-progress-heading" className="text-lg font-semibold text-slate-950">Your progress</h2>
        <p className="text-sm text-slate-600">{summary.challenges_passed} of {summary.challenges_total} challenges passed · {summary.challenges_attempted} attempted</p>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {challenges.map((item) => (
          <Link key={item.slug} to={`/coding/${item.slug}`} className="rounded-xl border border-slate-200 bg-white/70 p-4 text-sm transition hover:border-violet-200">
            <div className="flex items-start justify-between gap-2">
              <span className="font-semibold text-slate-900">{item.title}</span>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${item.passed ? 'bg-emerald-50 text-emerald-700' : item.attempts ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>
                {item.passed ? 'Passed' : item.attempts ? 'In progress' : 'Not started'}
              </span>
            </div>
            <p className="mt-2 text-slate-600">Best score {formatScore(item.best_score)} · {item.attempts} of {item.max_attempts} attempts{item.best_total_ms !== null ? ` · ${formatMs(item.best_total_ms)}` : ''}</p>
          </Link>
        ))}
      </div>
      {history.length > 0 && (
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer font-medium text-violet-700">Recent submissions</summary>
          <ul className="mt-3 divide-y divide-slate-100">
            {history.map((item) => (
              <li key={item.submission_id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-slate-700">
                <span>{item.challenge_title} · {item.language}</span>
                <span className="text-slate-500">{item.status.replace(/_/g, ' ')} · {formatScore(item.score)} pts · {formatMs(item.total_ms)} · {formatMemoryKb(item.peak_memory_kb)} · {new Date(item.submitted_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
