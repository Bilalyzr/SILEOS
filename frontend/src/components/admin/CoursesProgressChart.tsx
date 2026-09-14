import React, { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { TrendingUp, BookOpen, Users, Award, Search, ArrowUpDown } from 'lucide-react'
import { api } from '@/api/axios'

const ORANGE = '#f97316'
const BLUE = '#2563eb'

interface CourseRow {
  course_id: number
  course_title: string
  avg_progress: number
  avg_completion: number
  total_enrollments: number
  completed_enrollments: number
}

type SortKey = 'enrollments' | 'progress' | 'completion'

const progressColor = (pct: number): string => {
  if (pct >= 75) return '#10b981'  // emerald
  if (pct >= 50) return ORANGE
  if (pct >= 25) return '#f59e0b'  // amber
  return '#ef4444'                  // red
}

export const CoursesProgressChart: React.FC = () => {
  const [rows, setRows] = useState<CourseRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('enrollments')

  useEffect(() => {
    let cancelled = false
    const fetch = async () => {
      try {
        setLoading(true)
        setError(null)
        const r = await api.get('/admin/analytics/courses-progress')
        if (cancelled) return
        setRows(r.data?.courses ?? [])
      } catch (e: any) {
        if (cancelled) return
        setError(e?.response?.data?.detail || e?.message || 'Failed to load course progress')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetch()
    return () => {
      cancelled = true
    }
  }, [])

  const effectiveRows = rows

  const visible = useMemo(() => {
    let v = effectiveRows.filter((r) => r.total_enrollments > 0)
    if (search.trim()) {
      const q = search.toLowerCase()
      v = v.filter((r) => r.course_title.toLowerCase().includes(q))
    }
    v = [...v].sort((a, b) => {
      if (sortKey === 'progress') return b.avg_progress - a.avg_progress
      if (sortKey === 'completion') return b.avg_completion - a.avg_completion
      return b.total_enrollments - a.total_enrollments
    })
    return v
  }, [effectiveRows, search, sortKey])

  const overallAvg =
    visible.length > 0
      ? Math.round(visible.reduce((s, r) => s + r.avg_progress, 0) / visible.length)
      : 0
  const totalEnrollments = effectiveRows.reduce((s, r) => s + r.total_enrollments, 0)
  const totalCompleted = effectiveRows.reduce((s, r) => s + r.completed_enrollments, 0)
  const completionRate = totalEnrollments > 0 ? Math.round((totalCompleted / totalEnrollments) * 100) : 0

  // Top 5 by enrollment for the side chart
  const topByEnrollment = [...effectiveRows]
    .filter((r) => r.total_enrollments > 0)
    .sort((a, b) => b.total_enrollments - a.total_enrollments)
    .slice(0, 5)
    .map((r) => ({
      name: r.course_title.length > 20 ? r.course_title.slice(0, 18) + '…' : r.course_title,
      full: r.course_title,
      enrollments: r.total_enrollments,
      completed: r.completed_enrollments,
    }))

  return (
    <div className="space-y-4">
      {/* Header + KPIs */}
      <div className="bg-gradient-to-r from-orange-50 via-white to-blue-50 rounded-xl border border-gray-200 p-6">
        <div className="flex items-start justify-between mb-5">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-orange-500" />
              Course Learning Progress
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Per-course average progress and enrollment health.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KPI icon={<BookOpen className="w-5 h-5" />} label="Courses with data" value={visible.length.toString()} accent="orange" />
          <KPI icon={<Users className="w-5 h-5" />} label="Total enrollments" value={totalEnrollments.toLocaleString()} accent="blue" />
          <KPI icon={<Award className="w-5 h-5" />} label="Completed" value={totalCompleted.toLocaleString()} hint={`${completionRate}% rate`} accent="emerald" />
          <KPI
            icon={<TrendingUp className="w-5 h-5" />}
            label="Overall avg"
            value={`${overallAvg}%`}
            accent="gradient"
          />
        </div>
      </div>

      {/* Body: course list + top chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Course progress list */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
            <h3 className="text-base font-semibold text-gray-900">All courses</h3>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Filter courses…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-orange-400 focus:border-transparent w-44"
                />
              </div>
              <div className="flex items-center gap-1">
                <ArrowUpDown className="w-3.5 h-3.5 text-gray-400" />
                <select
                  value={sortKey}
                  onChange={(e) => setSortKey(e.target.value as SortKey)}
                  className="text-xs border border-gray-300 rounded-md px-2 py-1.5 bg-white focus:ring-2 focus:ring-orange-400 focus:border-transparent"
                >
                  <option value="enrollments">Enrollments</option>
                  <option value="progress">Progress %</option>
                  <option value="completion">Completion %</option>
                </select>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="h-48 flex items-center justify-center">
              <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-orange-500" />
            </div>
          ) : error ? (
            <div className="text-sm text-red-600 py-6">{error}</div>
          ) : visible.length === 0 ? (
            <div className="text-sm text-gray-500 py-12 text-center">
              No courses with enrollments yet.
            </div>
          ) : (
            <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
              {visible.map((c) => (
                <CourseRow key={c.course_id} c={c} />
              ))}
            </div>
          )}
        </div>

        {/* Top 5 enrollments chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-base font-semibold text-gray-900 mb-1">Top by enrollment</h3>
          <p className="text-xs text-gray-500 mb-4">5 most-enrolled courses, completed vs total.</p>

          {topByEnrollment.length === 0 ? (
            <div className="h-60 flex items-center justify-center text-sm text-gray-500">
              No data
            </div>
          ) : (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <BarChart data={topByEnrollment} margin={{ top: 8, right: 12, left: 0, bottom: 60 }}>
                  <defs>
                    <linearGradient id="topEnrollGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={ORANGE} />
                      <stop offset="100%" stopColor="#fb923c" />
                    </linearGradient>
                    <linearGradient id="topComplGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={BLUE} />
                      <stop offset="100%" stopColor="#60a5fa" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: '#374151' }}
                    interval={0}
                    angle={-30}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
                  <Tooltip
                    labelFormatter={(_l, payload) => {
                      const item: any = payload?.[0]?.payload
                      return item?.full || _l
                    }}
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  />
                  <Bar dataKey="enrollments" name="Total" fill="url(#topEnrollGrad)" radius={[6, 6, 0, 0]} barSize={18} />
                  <Bar dataKey="completed" name="Completed" fill="url(#topComplGrad)" radius={[6, 6, 0, 0]} barSize={18} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------
// Subcomponents
// ------------------------------------------------------------------

const KPI: React.FC<{
  icon: React.ReactNode
  label: string
  value: string
  hint?: string
  accent: 'orange' | 'blue' | 'emerald' | 'gradient'
}> = ({ icon, label, value, hint, accent }) => {
  const accentMap = {
    orange: 'bg-orange-100 text-orange-600',
    blue: 'bg-blue-100 text-blue-600',
    emerald: 'bg-emerald-100 text-emerald-600',
    gradient: 'bg-gradient-to-br from-orange-100 to-blue-100 text-orange-600',
  }
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${accentMap[accent]}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wide text-gray-500 font-medium">{label}</p>
        {accent === 'gradient' ? (
          <p
            className="text-xl font-bold"
            style={{
              background: `linear-gradient(90deg, ${ORANGE}, ${BLUE})`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            {value}
          </p>
        ) : (
          <p className="text-xl font-bold text-gray-900">{value}</p>
        )}
        {hint && <p className="text-[10px] text-gray-500">{hint}</p>}
      </div>
    </div>
  )
}

const CourseRow: React.FC<{ c: CourseRow }> = ({ c }) => {
  const color = progressColor(c.avg_progress)
  const completionPct = c.total_enrollments > 0 ? Math.round((c.completed_enrollments / c.total_enrollments) * 100) : 0

  return (
    <div className="border border-gray-100 rounded-lg p-3 hover:border-orange-200 hover:bg-orange-50/30 transition-colors">
      <div className="flex items-center justify-between gap-3 mb-2">
        <h4 className="font-medium text-sm text-gray-900 truncate">{c.course_title}</h4>
        <span className="text-sm font-bold whitespace-nowrap" style={{ color }}>
          {Math.round(c.avg_progress)}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 rounded-full bg-gray-100 overflow-hidden mb-2">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${Math.min(100, Math.max(0, c.avg_progress))}%`,
            background: `linear-gradient(90deg, ${ORANGE}, ${BLUE})`,
          }}
        />
      </div>

      <div className="flex items-center justify-between text-[11px] text-gray-500 gap-3 flex-wrap">
        <span className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          <strong className="text-gray-700">{c.total_enrollments}</strong> enrolled
        </span>
        <span className="flex items-center gap-1">
          <Award className="w-3 h-3" />
          <strong className="text-gray-700">{c.completed_enrollments}</strong> completed
          <span className="text-gray-400">({completionPct}%)</span>
        </span>
        <span className="flex items-center gap-1">
          <BookOpen className="w-3 h-3" />
          Lessons <strong className="text-gray-700">{Math.round(c.avg_completion)}%</strong>
        </span>
      </div>
    </div>
  )
}

export default CoursesProgressChart
