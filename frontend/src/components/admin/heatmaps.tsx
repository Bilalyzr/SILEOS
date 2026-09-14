import React from 'react'
import { BookOpen, IndianRupee, TrendingUp, Clock } from 'lucide-react'
import { api } from '@/api/axios'

interface EnrollmentDay { day: string; count: number }
interface UserRegistration { dow: number; hour: number; count: number }
interface CourseEngagement { course_id: number; course_name: string; dow: number; count: number }
interface RevenueDay { day: string; revenue: number }

interface HeatmapData {
  enrollment_activity: EnrollmentDay[]
  user_registration: UserRegistration[]
  course_engagement: CourseEngagement[]
  revenue_activity: RevenueDay[]
  period_days: number
}

const DAYS_FULL = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
const DAYS_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr)
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`
}

// 1. ENROLLMENT ACTIVITY — Clear daily bars with numbers
export const EnrollmentHeatmap: React.FC<{ data: EnrollmentDay[]; days: number }> = ({ data, days }) => {
  const dataMap = new Map(data.map(d => [d.day, d.count]))

  const cells: { date: string; count: number; dayName: string }[] = []
  const today = new Date()
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().split('T')[0]
    cells.push({
      date: dateStr,
      count: dataMap.get(dateStr) || 0,
      dayName: DAYS_SHORT[d.getDay()]
    })
  }

  const total = data.reduce((sum, d) => sum + d.count, 0)
  const maxCount = Math.max(...cells.map(c => c.count), 1)
  const activeDays = cells.filter(c => c.count > 0).length
  const avgPerDay = (total / days).toFixed(1)

  const showAllLabels = days <= 30

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-green-100 rounded-lg">
            <TrendingUp className="w-6 h-6 text-green-600" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">Enrollment Activity</h3>
            <p className="text-sm text-gray-600">Daily new enrollments</p>
          </div>
        </div>
        <div className="flex gap-4 text-right">
          <div>
            <div className="text-2xl font-bold text-green-600">{total}</div>
            <div className="text-xs text-gray-500">Total</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-600">{activeDays}</div>
            <div className="text-xs text-gray-500">Active days</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-600">{avgPerDay}</div>
            <div className="text-xs text-gray-500">Avg/day</div>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <div className="flex items-end gap-1 min-w-max pb-2" style={{ minHeight: '180px' }}>
          {cells.map((cell, i) => {
            const heightPct = cell.count > 0 ? (cell.count / maxCount) * 100 : 3
            return (
              <div key={i} className="flex flex-col items-center gap-1" style={{ minWidth: showAllLabels ? '32px' : '12px' }}>
                {cell.count > 0 && (
                  <div className="text-xs font-bold text-green-700">{cell.count}</div>
                )}
                <div
                  className={`w-full ${cell.count > 0 ? 'bg-gradient-to-t from-green-600 to-green-400' : 'bg-gray-100'} rounded-t cursor-pointer hover:from-green-700 hover:to-green-500 transition-all`}
                  style={{ height: `${heightPct}%`, minHeight: cell.count > 0 ? '8px' : '4px' }}
                  title={`${formatDate(cell.date)} (${cell.dayName}): ${cell.count} enrollment${cell.count !== 1 ? 's' : ''}`}
                />
                {showAllLabels && (
                  <div className="text-[9px] text-gray-500 rotate-45 origin-top-left whitespace-nowrap mt-1 h-8">
                    {new Date(cell.date).getDate()} {cell.dayName}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-gray-100 text-xs text-gray-500 text-center">
        Hover over any bar to see the exact date and enrollment count
      </div>
    </div>
  )
}

// 2. USER REGISTRATION PATTERN — Large clear grid with numbers
export const RegistrationHeatmap: React.FC<{ data: UserRegistration[] }> = ({ data }) => {
  const grid: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0))
  data.forEach(d => { grid[d.dow][d.hour] = d.count })
  const max = Math.max(...data.map(d => d.count), 1)
  const total = data.reduce((sum, d) => sum + d.count, 0)

  let peakDay = 0, peakHour = 0, peakCount = 0
  grid.forEach((row, dow) => {
    row.forEach((cnt, hr) => {
      if (cnt > peakCount) { peakCount = cnt; peakDay = dow; peakHour = hr }
    })
  })

  const getColor = (val: number) => {
    if (val === 0) return '#f9fafb'
    const ratio = val / max
    if (ratio < 0.25) return '#dbeafe'
    if (ratio < 0.5) return '#93c5fd'
    if (ratio < 0.75) return '#3b82f6'
    return '#1e40af'
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-100 rounded-lg">
            <Clock className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">Peak Registration Times</h3>
            <p className="text-sm text-gray-600">When users sign up — hour × day (UTC)</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-blue-600">{total}</div>
          <div className="text-xs text-gray-500">Registrations</div>
        </div>
      </div>

      {peakCount > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
          <div className="text-sm text-blue-900">
            <strong>Peak Time:</strong> {DAYS_FULL[peakDay]} at {peakHour}:00 UTC — <strong>{peakCount}</strong> registrations
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <div className="min-w-max">
          <div className="flex gap-1 mb-2 pl-16">
            {Array.from({ length: 24 }).map((_, h) => (
              <div key={h} className="w-7 text-[10px] text-center text-gray-600 font-medium">
                {h}
              </div>
            ))}
          </div>
          {DAYS_SHORT.map((day, di) => (
            <div key={di} className="flex items-center gap-1 mb-1">
              <div className="w-14 text-sm font-medium text-gray-700 pr-2">{day}</div>
              {grid[di].map((count, hi) => (
                <div
                  key={hi}
                  className="w-7 h-7 rounded cursor-pointer flex items-center justify-center text-[10px] font-semibold transition-all hover:scale-125 hover:ring-2 hover:ring-blue-500 hover:z-10 relative"
                  style={{
                    backgroundColor: getColor(count),
                    color: count > max * 0.5 ? 'white' : '#374151'
                  }}
                  title={`${DAYS_FULL[di]} ${hi}:00 UTC — ${count} registration${count !== 1 ? 's' : ''}`}
                >
                  {count || ''}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-gray-600">
        <div className="flex items-center gap-2">
          <span>Less</span>
          <div className="flex gap-1">
            <div className="w-5 h-5 rounded" style={{ backgroundColor: '#f9fafb' }} />
            <div className="w-5 h-5 rounded" style={{ backgroundColor: '#dbeafe' }} />
            <div className="w-5 h-5 rounded" style={{ backgroundColor: '#93c5fd' }} />
            <div className="w-5 h-5 rounded" style={{ backgroundColor: '#3b82f6' }} />
            <div className="w-5 h-5 rounded" style={{ backgroundColor: '#1e40af' }} />
          </div>
          <span>More</span>
        </div>
        <div>Numbers in the grid show registration count</div>
      </div>
    </div>
  )
}

// 3. COURSE ENGAGEMENT — Big clear table
export const CourseEngagementHeatmap: React.FC<{ data: CourseEngagement[] }> = ({ data }) => {
  const courseMap = new Map<number, { name: string; days: number[] }>()
  data.forEach(d => {
    if (!courseMap.has(d.course_id)) {
      courseMap.set(d.course_id, { name: d.course_name, days: Array(7).fill(0) })
    }
    courseMap.get(d.course_id)!.days[d.dow] = d.count
  })
  const max = Math.max(...data.map(d => d.count), 1)
  const courses = Array.from(courseMap.entries()).sort((a, b) => {
    const totalA = a[1].days.reduce((s, n) => s + n, 0)
    const totalB = b[1].days.reduce((s, n) => s + n, 0)
    return totalB - totalA
  })
  const grandTotal = data.reduce((sum, d) => sum + d.count, 0)

  const getColor = (val: number) => {
    if (val === 0) return '#f9fafb'
    const ratio = val / max
    if (ratio < 0.25) return '#fed7aa'
    if (ratio < 0.5) return '#fb923c'
    if (ratio < 0.75) return '#ea580c'
    return '#9a3412'
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-orange-100 rounded-lg">
            <BookOpen className="w-6 h-6 text-orange-600" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">Course Popularity by Day</h3>
            <p className="text-sm text-gray-600">Which courses get enrollments on which days</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-orange-600">{grandTotal}</div>
          <div className="text-xs text-gray-500">Total enrollments</div>
        </div>
      </div>

      {courses.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <BookOpen className="w-12 h-12 mx-auto mb-2 text-gray-300" />
          <p>No course engagement data yet</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="text-left text-sm font-semibold text-gray-700 pb-3 pr-4">Course Name</th>
                {DAYS_SHORT.map(day => (
                  <th key={day} className="text-center text-sm font-semibold text-gray-700 px-2 pb-3 w-20">{day}</th>
                ))}
                <th className="text-center text-sm font-semibold text-gray-700 pl-4 pb-3">Total</th>
              </tr>
            </thead>
            <tbody>
              {courses.map(([id, { name, days }]) => {
                const total = days.reduce((s, n) => s + n, 0)
                const bestDay = days.indexOf(Math.max(...days))
                return (
                  <tr key={id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 pr-4">
                      <div className="text-sm font-medium text-gray-900 truncate max-w-xs" title={name}>{name}</div>
                      <div className="text-xs text-gray-500">Best day: {DAYS_FULL[bestDay]}</div>
                    </td>
                    {days.map((count, di) => (
                      <td key={di} className="px-2 py-3">
                        <div
                          className="w-14 h-14 mx-auto rounded-lg flex items-center justify-center text-base font-bold cursor-pointer transition-all hover:scale-110 hover:shadow-md"
                          style={{
                            backgroundColor: getColor(count),
                            color: count > max * 0.5 ? 'white' : (count > 0 ? '#9a3412' : '#9ca3af')
                          }}
                          title={`${DAYS_FULL[di]}: ${count} enrollment${count !== 1 ? 's' : ''}`}
                        >
                          {count || '—'}
                        </div>
                      </td>
                    ))}
                    <td className="pl-4 py-3 text-center">
                      <span className="inline-flex items-center justify-center w-12 h-12 bg-orange-600 text-white rounded-lg font-bold text-lg">
                        {total}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// 4. REVENUE ACTIVITY — Bar chart with numbers
export const RevenueHeatmap: React.FC<{ data: RevenueDay[]; days: number }> = ({ data, days }) => {
  const dataMap = new Map(data.map(d => [d.day, d.revenue]))
  const total = data.reduce((sum, d) => sum + d.revenue, 0)

  const cells: { date: string; revenue: number; dayName: string }[] = []
  const today = new Date()
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().split('T')[0]
    cells.push({
      date: dateStr,
      revenue: dataMap.get(dateStr) || 0,
      dayName: DAYS_SHORT[d.getDay()]
    })
  }
  const max = Math.max(...cells.map(c => c.revenue), 1)
  const revenueDays = cells.filter(c => c.revenue > 0).length
  const showAllLabels = days <= 30

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-100 rounded-lg">
            <IndianRupee className="w-6 h-6 text-emerald-600" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">Revenue Activity</h3>
            <p className="text-sm text-gray-600">Daily revenue tracking</p>
          </div>
        </div>
        <div className="flex gap-4 text-right">
          <div>
            <div className="text-2xl font-bold text-emerald-600">{total.toLocaleString()}</div>
            <div className="text-xs text-gray-500">INR Total</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-600">{revenueDays}</div>
            <div className="text-xs text-gray-500">Paying days</div>
          </div>
        </div>
      </div>

      {total === 0 ? (
        <div className="text-center py-12">
          <IndianRupee className="w-16 h-16 mx-auto mb-3 text-gray-300" />
          <p className="text-gray-600 font-medium">No revenue recorded yet</p>
          <p className="text-sm text-gray-500 mt-1">All recent enrollments were free (coupon-based)</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="flex items-end gap-1 min-w-max pb-2" style={{ minHeight: '180px' }}>
            {cells.map((cell, i) => {
              const heightPct = cell.revenue > 0 ? (cell.revenue / max) * 100 : 3
              return (
                <div key={i} className="flex flex-col items-center gap-1" style={{ minWidth: showAllLabels ? '32px' : '12px' }}>
                  {cell.revenue > 0 && (
                    <div className="text-xs font-bold text-emerald-700">{cell.revenue}</div>
                  )}
                  <div
                    className={`w-full ${cell.revenue > 0 ? 'bg-gradient-to-t from-emerald-600 to-emerald-400' : 'bg-gray-100'} rounded-t cursor-pointer hover:from-emerald-700 transition-all`}
                    style={{ height: `${heightPct}%`, minHeight: cell.revenue > 0 ? '8px' : '4px' }}
                    title={`${formatDate(cell.date)}: INR ${cell.revenue.toLocaleString()}`}
                  />
                  {showAllLabels && (
                    <div className="text-[9px] text-gray-500 rotate-45 origin-top-left whitespace-nowrap mt-1 h-8">
                      {new Date(cell.date).getDate()} {cell.dayName}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// Main component with period tabs
export const AnalyticsHeatmaps: React.FC = () => {
  const [data, setData] = React.useState<HeatmapData | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [days, setDays] = React.useState(30)

  const periods = [
    { label: 'Last 7 days', value: 7 },
    { label: 'Last 30 days', value: 30 },
    { label: 'Last 90 days', value: 90 },
    { label: 'Last 180 days', value: 180 }
  ]

  React.useEffect(() => {
    setLoading(true)
    api.get(`/admin/analytics/heatmaps?days=${days}`)
      .then(r => { setData(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [days])

  return (
    <div className="space-y-6 mt-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Activity Heatmaps</h2>
          <p className="text-sm text-gray-600 mt-1">Visual breakdown of enrollments, registrations, and revenue</p>
        </div>
        <div className="flex items-center gap-2 bg-gray-100 rounded-xl p-1">
          {periods.map(p => (
            <button
              key={p.value}
              onClick={() => setDays(p.value)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                days === p.value
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500 mx-auto"></div>
          <p className="text-gray-600 mt-4">Loading heatmaps...</p>
        </div>
      ) : data ? (
        <>
          <EnrollmentHeatmap data={data.enrollment_activity} days={data.period_days} />
          <RevenueHeatmap data={data.revenue_activity} days={data.period_days} />
          <RegistrationHeatmap data={data.user_registration} />
          <CourseEngagementHeatmap data={data.course_engagement} />
        </>
      ) : null}
    </div>
  )
}
