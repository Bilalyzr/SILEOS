import { useCallback, useEffect, useState } from 'react'
import { Download, RefreshCw } from 'lucide-react'
import { codingAPI, type ChallengeMetrics, type CourseCodingMetrics } from '@/api/coding'
import { plannerError } from '@/api/planner'
import { formatMemoryKb, formatMinutes, formatMs, formatPercent, formatScore } from './metricsFormat'

const LEADERBOARD_PREVIEW = 10

export default function InstructorReport({ courseId }: { courseId: number }) {
  const [metrics, setMetrics] = useState<CourseCodingMetrics | null>(null)
  const [selectedSlug, setSelectedSlug] = useState('')
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!courseId) return
    setLoading(true)
    setError('')
    try {
      setMetrics(await codingAPI.courseMetrics(courseId))
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    setMetrics(null)
    setSelectedSlug('')
    void load()
  }, [load])

  const download = async () => {
    setDownloading(true)
    setError('')
    try {
      const blob = await codingAPI.courseMetricsCsv(courseId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `coding-metrics-course-${courseId}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (reason) {
      setError(plannerError(reason))
    } finally {
      setDownloading(false)
    }
  }

  if (!courseId) return null

  const challenges = metrics?.challenges ?? []
  const selected: ChallengeMetrics | undefined =
    challenges.find((item) => item.slug === selectedSlug) ?? challenges[0]

  return (
    <section className="glass-panel mt-5 rounded-2xl p-5 sm:p-7" aria-labelledby="coding-report-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="coding-report-heading" className="text-xl font-semibold text-slate-950">Learner performance</h2>
          <p className="mt-1 text-sm text-slate-500">Pass rate, failing tests and the leaderboard for each challenge in this course.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void load()} disabled={loading} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Refresh
          </button>
          <button type="button" onClick={() => void download()} disabled={downloading || !metrics || challenges.length === 0} className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
            <Download className="h-4 w-4" />{downloading ? 'Preparing…' : 'Export CSV'}
          </button>
        </div>
      </div>

      {error && <div role="alert" className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {!metrics && loading && <p className="mt-4 text-sm text-slate-500">Loading report…</p>}
      {metrics && challenges.length === 0 && (
        <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No published or retired challenges yet. Metrics appear after learners submit.</p>
      )}

      {selected && (
        <>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="py-2 pr-4 font-semibold">Challenge</th>
                  <th className="py-2 pr-4 font-semibold">Learners</th>
                  <th className="py-2 pr-4 font-semibold">Passed</th>
                  <th className="py-2 pr-4 font-semibold">Pass rate</th>
                  <th className="py-2 pr-4 font-semibold">Submissions</th>
                  <th className="py-2 pr-4 font-semibold">Median time to pass</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {challenges.map((item) => (
                  <tr key={item.slug} onClick={() => setSelectedSlug(item.slug)} className={`cursor-pointer ${item.slug === selected.slug ? 'bg-violet-50' : 'hover:bg-slate-50'}`}>
                    <td className="py-2 pr-4 font-medium text-slate-900">{item.title}</td>
                    <td className="py-2 pr-4 text-slate-700">{item.learners_attempted}</td>
                    <td className="py-2 pr-4 text-slate-700">{item.learners_passed}</td>
                    <td className="py-2 pr-4 text-slate-700">{formatPercent(item.pass_rate)}</td>
                    <td className="py-2 pr-4 text-slate-700">{item.total_submissions}</td>
                    <td className="py-2 pr-4 text-slate-700">{formatMinutes(item.median_minutes_to_first_pass)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="font-semibold text-slate-950">Failing tests · {selected.title}</h3>
              {selected.failing_cases.length === 0 ? (
                <p className="mt-2 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No failing runs recorded yet.</p>
              ) : (
                <ul className="mt-2 space-y-2">
                  {selected.failing_cases.map((item) => (
                    <li key={item.ordinal} className="rounded-xl border border-slate-200 p-3 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-slate-900">Test {item.ordinal}</span>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${item.visibility === 'hidden' ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}>{item.visibility === 'hidden' ? 'Hidden' : 'Sample'}</span>
                      </div>
                      <p className="mt-1 text-slate-600">{item.failed} of {item.runs} runs failed · {Object.entries(item.failure_breakdown).map(([status, count]) => `${count} ${status.replace(/_/g, ' ')}`).join(', ')}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <h3 className="font-semibold text-slate-950">Leaderboard · top {LEADERBOARD_PREVIEW}</h3>
              {selected.leaderboard.length === 0 ? (
                <p className="mt-2 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No learner has submitted yet.</p>
              ) : (
                <ol className="mt-2 divide-y divide-slate-100 text-sm">
                  {selected.leaderboard.slice(0, LEADERBOARD_PREVIEW).map((row) => (
                    <li key={row.user_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                      <span className="font-medium text-slate-900">{row.rank}. {row.learner_name || `Learner ${row.user_id}`}</span>
                      <span className="text-slate-600">{formatScore(row.best_score)} pts · {formatMs(row.total_ms)} · {formatMemoryKb(row.peak_memory_kb)} · {row.attempts} attempt{row.attempts === 1 ? '' : 's'}{row.passed ? '' : ' · not passed'}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  )
}
