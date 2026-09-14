import React, { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { TrendingUp } from 'lucide-react'
import { api } from '@/api/axios'

interface ProgressPoint {
  date: string
  avg_progress: number
  avg_completion: number
  enrolled_count: number
}

interface Props {
  period: string
}

const ORANGE = '#f97316'
const BLUE = '#2563eb'

export const LearningProgressChart: React.FC<Props> = ({ period }) => {
  const [data, setData] = useState<ProgressPoint[]>([])
  const [bucket, setBucket] = useState<string>('day')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchSeries = async () => {
      try {
        setLoading(true)
        setError(null)
        const r = await api.get(`/admin/analytics/learning-progress?period=${period}`)
        if (cancelled) return
        setData(r.data?.series ?? [])
        setBucket(r.data?.bucket ?? 'day')
      } catch (e: any) {
        if (cancelled) return
        setError(e?.message || 'Failed to load progress data')
        setData([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchSeries()
    return () => {
      cancelled = true
    }
  }, [period])

  const avgOverall =
    data.length > 0
      ? Math.round(data.reduce((s, d) => s + d.avg_progress, 0) / data.length)
      : 0

  const formatDate = (d: string) => {
    if (!d) return ''
    const dt = new Date(d)
    if (bucket === 'month') {
      return dt.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
    }
    return dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center">
            <TrendingUp className="w-5 h-5 mr-2 text-orange-500" />
            Average Learning Progress
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Mean enrollment progress across all students, bucketed by {bucket}.
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Overall avg</p>
          <p
            className="text-3xl font-bold"
            style={{
              background: `linear-gradient(90deg, ${ORANGE}, ${BLUE})`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            {avgOverall}%
          </p>
        </div>
      </div>

      {loading ? (
        <div className="h-72 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500" />
        </div>
      ) : error ? (
        <div className="h-72 flex items-center justify-center text-sm text-red-600">{error}</div>
      ) : data.length === 0 ? (
        <div className="h-72 flex items-center justify-center text-sm text-gray-500">
          No enrollment data for this period.
        </div>
      ) : (
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
            <AreaChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="progressGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={ORANGE} stopOpacity={0.8} />
                  <stop offset="100%" stopColor={BLUE} stopOpacity={0.2} />
                </linearGradient>
                <linearGradient id="completionGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={BLUE} stopOpacity={0.6} />
                  <stop offset="100%" stopColor={BLUE} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontSize: 12, fill: '#6b7280' }}
                stroke="#9ca3af"
              />
              <YAxis
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
                tick={{ fontSize: 12, fill: '#6b7280' }}
                stroke="#9ca3af"
              />
              <Tooltip
                formatter={(value: number, name: string) => [`${value.toFixed(1)}%`, name]}
                labelFormatter={(l) => formatDate(l as string)}
                contentStyle={{
                  background: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area
                type="monotone"
                dataKey="avg_progress"
                name="Avg Progress"
                stroke={ORANGE}
                strokeWidth={2.5}
                fill="url(#progressGradient)"
              />
              <Area
                type="monotone"
                dataKey="avg_completion"
                name="Avg Lesson Completion"
                stroke={BLUE}
                strokeWidth={2}
                fill="url(#completionGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default LearningProgressChart
