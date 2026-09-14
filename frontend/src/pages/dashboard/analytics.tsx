/**
 * Student Analytics Report.
 *
 * A single, printable view of how a student is actually doing: progress and
 * completion, time invested, quiz/assignment performance, and the certificates
 * they've earned. Every number comes from `/dashboard/student/analytics` —
 * real enrollment, lesson-progress, attempt and certificate rows, not the
 * mock series the main dashboard falls back to.
 *
 * Layout:
 *   - Header: period filter + export actions
 *   - Insights (plain-language takeaways from the backend)
 *   - Headline stats
 *   - Learning activity over time + course status donut
 *   - Monthly completions
 *   - Per-course performance table
 *   - Quiz + assignment performance
 *   - Certificates earned (each shareable to LinkedIn)
 */
import * as React from 'react'
import { Link } from 'react-router-dom'
import {
  Award, BookOpen, Clock, Target, Activity, TrendingUp, GraduationCap,
  Flame, FileText, ClipboardCheck, Printer, Download, BarChart3, Linkedin,
  CheckCircle2, AlertTriangle, Info,
} from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { ExportImportPanel } from '@/components/admin/ExportImportPanel'
import {
  dashboardAPI, StudentAnalyticsData, AnalyticsPeriod, AnalyticsActivityPoint,
} from '@/api/dashboard'
import {
  StatCard, SkeletonStatCard, SkeletonChart, SectionCard, EmptyState, ErrorState,
  Greeting, StaggerGrid, FadeUp,
} from '@/components/dashboard/primitives'
import {
  AreaChartCard, BarChartCard, DonutCard, ChartLegend, CHART_COLORS,
} from '@/components/dashboard/charts'
import { LinkedInShareDialog } from '@/components/certificate/LinkedInShareDialog'
import './analytics-print.css'

const PERIODS: { value: AnalyticsPeriod; label: string }[] = [
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
  { value: '1y', label: '1 year' },
  { value: 'all', label: 'All time' },
]

const TONE_STYLES: Record<string, { wrap: string; icon: React.ElementType; fg: string }> = {
  positive: { wrap: 'border-emerald-100 bg-emerald-50/60', icon: CheckCircle2, fg: 'text-emerald-600' },
  warning:  { wrap: 'border-amber-100 bg-amber-50/60',     icon: AlertTriangle, fg: 'text-amber-600' },
  neutral:  { wrap: 'border-slate-200 bg-slate-50/60',     icon: Info,          fg: 'text-slate-500' },
}

const STATUS_BADGE: Record<string, string> = {
  completed:   'bg-emerald-100 text-emerald-800',
  in_progress: 'bg-amber-100 text-amber-800',
  not_started: 'bg-slate-100 text-slate-700',
}

const STATUS_LABEL: Record<string, string> = {
  completed: 'Completed',
  in_progress: 'In progress',
  not_started: 'Not started',
}

const formatDate = (iso: string | null | undefined): string => {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

/**
 * Collapse a daily series into ~12–16 buckets so a 90-day or 1-year window
 * stays legible. Short windows are left as-is (one point per day).
 */
function bucketTimeline(points: AnalyticsActivityPoint[]): Record<string, any>[] {
  if (points.length === 0) return []
  const targetBuckets = 14
  const size = Math.max(1, Math.ceil(points.length / targetBuckets))
  if (size === 1) {
    return points.map(p => ({ x: p.label, hours: p.hours, lessons: p.lessons }))
  }

  const rows: Record<string, any>[] = []
  for (let i = 0; i < points.length; i += size) {
    const slice = points.slice(i, i + size)
    rows.push({
      x: slice[0].label,
      hours: Math.round(slice.reduce((s, p) => s + p.hours, 0) * 10) / 10,
      lessons: slice.reduce((s, p) => s + p.lessons, 0),
    })
  }
  return rows
}

function toCsv(data: StudentAnalyticsData): string {
  const escape = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const header = [
    'Course', 'Instructor', 'Status', 'Progress %', 'Lessons completed', 'Total lessons',
    'Hours', 'Avg quiz score %', 'Certificate', 'Enrolled on', 'Completed on', 'Last activity',
  ]
  const rows = data.course_breakdown.map(c => [
    c.title, c.instructor, STATUS_LABEL[c.status] || c.status, c.progress,
    c.completed_lessons, c.total_lessons, c.hours,
    c.avg_quiz_score ?? '', c.has_certificate ? 'Yes' : 'No',
    c.enrolled_at?.slice(0, 10) ?? '', c.completed_at?.slice(0, 10) ?? '',
    c.last_activity ?? '',
  ])
  return [header, ...rows].map(r => r.map(escape).join(',')).join('\n')
}

export const StudentAnalyticsPage = () => {
  const { fullName } = useAuth()
  const [period, setPeriod] = React.useState<AnalyticsPeriod>('90d')
  const [data, setData] = React.useState<StudentAnalyticsData | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [shareCert, setShareCert] = React.useState<{ id: string; hash: string; title: string } | null>(null)

  const fetchAnalytics = React.useCallback(async (selected: AnalyticsPeriod) => {
    try {
      setIsLoading(true); setError(null)
      setData(await dashboardAPI.getStudentAnalytics(selected))
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load your analytics report')
    } finally { setIsLoading(false) }
  }, [])

  React.useEffect(() => { fetchAnalytics(period) }, [fetchAnalytics, period])

  const summary = data?.summary
  const timelineRows = React.useMemo(
    () => bucketTimeline(data?.activity_timeline || []),
    [data?.activity_timeline]
  )

  const statusBuckets = React.useMemo(() => ([
    { name: 'Completed',   value: summary?.completed_courses ?? 0,   color: CHART_COLORS.emerald },
    { name: 'In progress', value: summary?.in_progress_courses ?? 0, color: CHART_COLORS.amber },
    { name: 'Not started', value: summary?.not_started_courses ?? 0, color: CHART_COLORS.slate },
  ]), [summary])

  const hasCourses = (summary?.enrolled_courses ?? 0) > 0

  // The print stylesheet keys off this body class, so it can never affect
  // printing any other page that happens to have loaded this chunk.
  const handlePrint = () => {
    document.body.classList.add('printing-report')
    const cleanup = () => {
      document.body.classList.remove('printing-report')
      window.removeEventListener('afterprint', cleanup)
    }
    window.addEventListener('afterprint', cleanup)
    window.print()
    // Safari fires afterprint unreliably — belt and braces.
    setTimeout(cleanup, 1000)
  }

  const handleExportCsv = () => {
    if (!data) return
    const blob = new Blob([toCsv(data)], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `sashainfinity-analytics-${data.period}-${data.generated_at.slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="analytics-report">
      <Greeting
        name={fullName}
        chip="ANALYTICS REPORT"
        subtitle="A complete picture of your learning: progress, time invested, performance and the certificates you've earned."
        className="mb-6"
      />

      {/* Period filter + exports */}
      <FadeUp className="dash-card p-4 mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <BarChart3 className="w-4 h-4 text-orange-500" />
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 mr-1">
            Period
          </span>
          {PERIODS.map(p => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition ${
                period === p.value
                  ? 'bg-orange-500 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 no-print">
          {/* Server-generated learner report — branded PDF / Excel. */}
          <ExportImportPanel section="student_courses" role="student" label="Course report" />
          <ExportImportPanel section="student_certificates" role="student" label="Certificate report" />
          <button onClick={handleExportCsv} disabled={!data} className="dash-cta-ghost text-xs px-3 py-2 disabled:opacity-50">
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
          <button onClick={handlePrint} disabled={!data} className="dash-cta text-xs px-3 py-2 disabled:opacity-50">
            <Printer className="w-3.5 h-3.5" /> Print / Save PDF
          </button>
        </div>
      </FadeUp>

      {error && (
        <FadeUp>
          <ErrorState
            title="Couldn't load your analytics report"
            description={error}
            onRetry={() => fetchAnalytics(period)}
            className="dash-card mb-6"
          />
        </FadeUp>
      )}

      {/* Report meta line — matters most on the printed copy. */}
      {data && (
        <p className="text-xs text-slate-500 mb-6">
          Report for <span className="font-semibold text-slate-700">{data.student.name}</span> ·{' '}
          {data.period_label} · generated {formatDate(data.generated_at)}
        </p>
      )}

      {/* Insights */}
      {data && data.insights.length > 0 && (
        <StaggerGrid className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
          {data.insights.map((insight, i) => {
            const tone = TONE_STYLES[insight.tone] || TONE_STYLES.neutral
            const Icon = tone.icon
            return (
              <FadeUp key={i} className={`rounded-xl border p-4 flex gap-3 ${tone.wrap}`}>
                <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${tone.fg}`} />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-secondary-900">{insight.title}</p>
                  <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">{insight.detail}</p>
                </div>
              </FadeUp>
            )
          })}
        </StaggerGrid>
      )}

      {/* Headline stats */}
      <StaggerGrid className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {isLoading || !summary ? (
          <><SkeletonStatCard /><SkeletonStatCard /><SkeletonStatCard /><SkeletonStatCard /></>
        ) : (
          <>
            <StatCard
              title="Completion rate"
              value={summary.completion_rate}
              format={(n) => `${Math.round(n)}%`}
              icon={Target}
              tone="orange"
              delta={`${summary.completed_courses}/${summary.enrolled_courses} courses`}
              deltaDirection="flat"
            />
            <StatCard
              title="Lessons completed"
              value={summary.completed_lessons}
              icon={BookOpen}
              tone="sky"
              delta={summary.total_lessons > 0 ? `of ${summary.total_lessons}` : undefined}
              deltaDirection="flat"
            />
            <StatCard
              title="Learning hours"
              value={summary.total_hours}
              format={(n) => `${n.toFixed(1)}h`}
              icon={Clock}
              tone="emerald"
              delta={`${summary.period_hours.toFixed(1)}h this period`}
              deltaDirection="up"
            />
            <StatCard
              title="Certificates"
              value={summary.certificates_earned}
              icon={GraduationCap}
              tone="purple"
            />
          </>
        )}
      </StaggerGrid>

      {/* Secondary stats */}
      <StaggerGrid className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {isLoading || !summary ? (
          <><SkeletonStatCard /><SkeletonStatCard /><SkeletonStatCard /><SkeletonStatCard /></>
        ) : (
          <>
            <StatCard
              title="Current streak"
              value={summary.current_streak}
              format={(n) => `${Math.round(n)} d`}
              icon={Flame}
              tone="rose"
              delta={`best ${summary.longest_streak} d`}
              deltaDirection="flat"
            />
            <StatCard
              title="Active days"
              value={summary.active_days}
              icon={Activity}
              tone="navy"
              delta={summary.avg_session_hours > 0 ? `${summary.avg_session_hours.toFixed(1)}h avg` : undefined}
              deltaDirection="flat"
            />
            <StatCard
              title="Avg quiz score"
              value={summary.avg_quiz_score}
              format={(n) => `${n.toFixed(0)}%`}
              icon={ClipboardCheck}
              tone="amber"
              delta={summary.quizzes_attempted > 0 ? `${summary.quizzes_passed}/${summary.quizzes_attempted} passed` : 'no attempts'}
              deltaDirection="flat"
            />
            <StatCard
              title="Avg assignment score"
              value={summary.avg_assignment_score}
              format={(n) => `${n.toFixed(0)}%`}
              icon={FileText}
              tone="slate"
              delta={summary.assignments_submitted > 0 ? `${summary.assignments_graded} graded` : 'none submitted'}
              deltaDirection="flat"
            />
          </>
        )}
      </StaggerGrid>

      {/* Activity + course status */}
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <SectionCard
          title="Learning activity"
          description={data ? `Study hours and lessons completed · ${data.period_label.toLowerCase()}` : undefined}
          icon={Activity}
          className="lg:col-span-2"
          bodyClassName="px-2 pb-3"
        >
          {isLoading ? (
            <SkeletonChart />
          ) : timelineRows.length === 0 ? (
            <EmptyState icon={Activity} title="No activity recorded yet" description="Complete a lesson to start your report." />
          ) : (
            <AreaChartCard
              data={timelineRows}
              series={[
                { key: 'hours', label: 'Hours', color: CHART_COLORS.orange },
                { key: 'lessons', label: 'Lessons completed', color: CHART_COLORS.sky },
              ]}
              xKey="x"
              height={280}
            />
          )}
        </SectionCard>

        <SectionCard title="Course status" description="Across all your enrollments" icon={Target}>
          {isLoading ? (
            <SkeletonChart />
          ) : !hasCourses ? (
            <EmptyState
              icon={BookOpen}
              title="No courses yet"
              description="Enroll in a course to build your report."
              action={{ label: 'Browse courses', to: '/courses' }}
            />
          ) : (
            <>
              <DonutCard
                data={statusBuckets}
                centerLabel="Courses"
                centerValue={summary?.enrolled_courses ?? 0}
                height={200}
              />
              <ChartLegend items={statusBuckets} className="mt-4" />
              <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-sm">
                <span className="text-slate-500">Average progress</span>
                <span className="font-bold text-secondary-900">{summary?.avg_progress ?? 0}%</span>
              </div>
            </>
          )}
        </SectionCard>
      </StaggerGrid>

      {/* Monthly completions */}
      <StaggerGrid className="grid grid-cols-1 mb-6">
        <SectionCard
          title="Courses completed by month"
          description="Last 12 months"
          icon={TrendingUp}
          bodyClassName="px-2 pb-3"
        >
          {isLoading ? (
            <SkeletonChart />
          ) : (
            <BarChartCard
              data={(data?.monthly_completions || []).map(m => ({ x: m.label, completed: m.completed }))}
              series={[{ key: 'completed', label: 'Courses completed', color: CHART_COLORS.emerald }]}
              xKey="x"
              height={220}
            />
          )}
        </SectionCard>
      </StaggerGrid>

      {/* Per-course performance */}
      <StaggerGrid className="grid grid-cols-1 mb-6">
        <SectionCard
          title="Course performance"
          description={hasCourses ? `${data?.course_breakdown.length} enrolled course${data?.course_breakdown.length === 1 ? '' : 's'}` : undefined}
          icon={BookOpen}
          action={{ label: 'My courses', to: '/my-courses' }}
          bodyClassName="p-0"
        >
          {isLoading ? (
            <div className="p-5 space-y-3">
              <div className="h-12 dash-skeleton" /><div className="h-12 dash-skeleton" />
            </div>
          ) : !hasCourses ? (
            <EmptyState
              icon={BookOpen}
              title="No enrollments yet"
              description="Your course-by-course breakdown appears here once you enroll."
              action={{ label: 'Browse courses', to: '/courses' }}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[720px]">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wide text-slate-500 border-b border-slate-100">
                    <th className="px-5 py-3 font-semibold">Course</th>
                    <th className="px-3 py-3 font-semibold">Status</th>
                    <th className="px-3 py-3 font-semibold w-40">Progress</th>
                    <th className="px-3 py-3 font-semibold text-right">Lessons</th>
                    <th className="px-3 py-3 font-semibold text-right">Hours</th>
                    <th className="px-3 py-3 font-semibold text-right">Quiz avg</th>
                    <th className="px-5 py-3 font-semibold text-right">Certificate</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.course_breakdown.map(course => (
                    <tr key={course.course_id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60">
                      <td className="px-5 py-3">
                        <Link
                          to={`/courses/${course.slug || course.course_id}`}
                          className="font-semibold text-secondary-900 hover:text-orange-600"
                        >
                          {course.title}
                        </Link>
                        <p className="text-xs text-slate-500">by {course.instructor}</p>
                      </td>
                      <td className="px-3 py-3">
                        <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${STATUS_BADGE[course.status]}`}>
                          {STATUS_LABEL[course.status]}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-orange-500"
                              style={{ width: `${Math.min(100, Math.max(0, course.progress))}%` }}
                            />
                          </div>
                          <span className="text-xs font-semibold text-slate-600 tabular-nums w-9 text-right">
                            {course.progress}%
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-slate-600">
                        {course.completed_lessons}/{course.total_lessons}
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-slate-600">
                        {course.hours.toFixed(1)}
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-slate-600">
                        {course.avg_quiz_score !== null ? `${course.avg_quiz_score}%` : '—'}
                      </td>
                      <td className="px-5 py-3 text-right">
                        {course.has_certificate ? (
                          <Link to={`/certificates/${course.course_id}`} className="text-xs font-semibold text-orange-600 hover:text-orange-700 inline-flex items-center gap-1">
                            <Award className="w-3.5 h-3.5" /> View
                          </Link>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      </StaggerGrid>

      {/* Assessments */}
      <StaggerGrid className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <SectionCard
          title="Quiz performance"
          description={summary && summary.quizzes_attempted > 0
            ? `${summary.quizzes_attempted} attempt${summary.quizzes_attempted === 1 ? '' : 's'} · ${summary.quiz_pass_rate}% pass rate`
            : undefined}
          icon={ClipboardCheck}
          bodyClassName="space-y-2"
        >
          {isLoading ? (
            <div className="h-24 dash-skeleton" />
          ) : (data?.quiz_history.length ?? 0) === 0 ? (
            <EmptyState icon={ClipboardCheck} title="No quiz attempts in this period" description="Quiz scores appear here once you take a quiz." />
          ) : (
            data?.quiz_history.map(attempt => (
              <div key={attempt.attempt_id} className="flex items-center gap-3 p-3 rounded-xl border border-slate-100">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-secondary-900 truncate">{attempt.quiz_title}</p>
                  <p className="text-xs text-slate-500 truncate">
                    {attempt.course_title} · {formatDate(attempt.attempted_at)}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className={`text-sm font-bold tabular-nums ${attempt.passed ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {attempt.score}%
                  </p>
                  <p className="text-[11px] text-slate-400">pass {attempt.passing_grade}%</p>
                </div>
              </div>
            ))
          )}
        </SectionCard>

        <SectionCard
          title="Assignment performance"
          description={summary && summary.assignments_submitted > 0
            ? `${summary.assignments_submitted} submitted · ${summary.assignments_graded} graded`
            : undefined}
          icon={FileText}
          bodyClassName="space-y-2"
        >
          {isLoading ? (
            <div className="h-24 dash-skeleton" />
          ) : (data?.assignment_history.length ?? 0) === 0 ? (
            <EmptyState icon={FileText} title="No submissions in this period" description="Assignment grades appear here once you submit." />
          ) : (
            data?.assignment_history.map(item => (
              <div key={item.id} className="flex items-center gap-3 p-3 rounded-xl border border-slate-100">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-secondary-900 truncate">{item.title}</p>
                  <p className="text-xs text-slate-500 truncate">
                    {item.course_title} · {formatDate(item.submitted_at)}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  {item.percentage !== null ? (
                    <>
                      <p className="text-sm font-bold tabular-nums text-secondary-900">{item.percentage}%</p>
                      <p className="text-[11px] text-slate-400">{item.grade}/{item.total_points}</p>
                    </>
                  ) : (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium capitalize">
                      {item.status || 'submitted'}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </SectionCard>
      </StaggerGrid>

      {/* Certificates */}
      <StaggerGrid className="grid grid-cols-1">
        <SectionCard
          title="Certificates earned"
          description={(data?.certificates.length ?? 0) > 0
            ? `${data?.certificates.length} verified credential${data?.certificates.length === 1 ? '' : 's'}`
            : undefined}
          icon={Award}
        >
          {isLoading ? (
            <div className="h-24 dash-skeleton" />
          ) : (data?.certificates.length ?? 0) === 0 ? (
            <EmptyState
              icon={Award}
              title="No certificates yet"
              description="Finish a course to earn your first verified certificate."
              action={{ label: 'Browse courses', to: '/courses' }}
            />
          ) : (
            <div className="grid md:grid-cols-2 gap-3">
              {data?.certificates.map(cert => (
                <div key={cert.id} className="p-4 rounded-xl border border-emerald-100 bg-emerald-50/40">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="min-w-0">
                      <p className="font-semibold text-secondary-900 truncate">{cert.course_title}</p>
                      <p className="text-xs text-slate-500">Issued {formatDate(cert.issued_at)}</p>
                      <p className="text-[11px] text-slate-400 font-mono truncate mt-0.5">
                        {cert.secure_certificate_id}
                      </p>
                    </div>
                    <Award className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                  </div>
                  <div className="flex flex-wrap gap-2 no-print">
                    <Link to={`/certificates/${cert.course_id}`} className="dash-cta-ghost text-[11px] px-2.5 py-1.5">
                      <Award className="w-3 h-3" /> View
                    </Link>
                    <button
                      onClick={() => setShareCert({
                        id: cert.secure_certificate_id,
                        hash: cert.certificate_hash,
                        title: cert.course_title,
                      })}
                      className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1.5 rounded-lg bg-[#0A66C2] text-white hover:bg-[#084d92] transition"
                    >
                      <Linkedin className="w-3 h-3" /> Share on LinkedIn
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </StaggerGrid>

      {shareCert && (
        <LinkedInShareDialog
          open
          onClose={() => setShareCert(null)}
          secureCertificateId={shareCert.id}
          certificateHash={shareCert.hash}
          courseTitle={shareCert.title}
        />
      )}
    </div>
  )
}

export default StudentAnalyticsPage
