import React from 'react'
import {
ResponsiveContainer,
PieChart,
Pie,
Cell,
BarChart,
Bar,
XAxis,
YAxis,
CartesianGrid,
Tooltip,
Legend,
AreaChart,
Area,
} from 'recharts'
import { Briefcase,Activity,Ticket,TrendingUp } from 'lucide-react'

const ORANGE = '#f97316'
const BLUE = '#2563eb'
const ORANGE_LIGHT = '#fb923c'
const BLUE_LIGHT = '#60a5fa'
const AMBER = '#f59e0b'

type InternshipStatus = 'in-progress' | 'completed' | 'pending'

interface StudentInternship {
  id: number
  title: string
  start_date: string
  voucher_redeemed: boolean
  status: InternshipStatus
  progress: number
  certificate_issued: boolean
}

interface Props {
  list: StudentInternship[]
}

const Card: React.FC<{ title: string; icon: React.ReactNode; children: React.ReactNode; className?: string }> = ({
  title,
  icon,
  children,
  className = '',
}) => (
  <div className={`rounded-xl border border-slate-200 bg-white p-4 ${className}`}>
    <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
      {icon}
      {title}
    </h3>
    {children}
  </div>
)

export const MyInternshipCharts: React.FC<Props> = ({ list }) => {
  if (!list || list.length === 0) {
    return (
      <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Briefcase className="w-10 h-10 text-orange-400 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800">No internship analytics yet</h3>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          Charts (progress, status, vouchers, timeline) will appear here as soon as you purchase or
          redeem an internship voucher.
        </p>
      </div>
    )
  }

  const progressData = list.map((i) => ({
    name: i.title.length > 18 ? i.title.slice(0, 16) + '…' : i.title,
    progress: i.progress,
  }))

  const statusCounts = list.reduce(
    (acc, i) => {
      acc[i.status] = (acc[i.status] || 0) + 1
      return acc
    },
    {} as Record<InternshipStatus, number>,
  )
  const statusData = [
    { name: 'In progress', value: statusCounts['in-progress'] || 0, color: ORANGE },
    { name: 'Completed', value: statusCounts['completed'] || 0, color: BLUE },
    { name: 'Pending', value: statusCounts['pending'] || 0, color: AMBER },
  ].filter((d) => d.value > 0)

  const voucherData = [
    { name: 'Redeemed', value: list.filter((i) => i.voucher_redeemed).length, color: BLUE },
    { name: 'Pending', value: list.filter((i) => !i.voucher_redeemed).length, color: ORANGE },
  ].filter((d) => d.value > 0)

  const monthMap = new Map<string, number>()
  list.forEach((i) => {
    const d = new Date(i.start_date)
    if (isNaN(d.getTime())) return
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    monthMap.set(key, (monthMap.get(key) || 0) + 1)
  })
  const timelineData = Array.from(monthMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, count]) => ({ month: key, count }))

  const avgProgress = list.length
    ? Math.round(list.reduce((s, i) => s + (i.progress || 0), 0) / list.length)
    : 0

  return (
    <div className="space-y-4 mt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-orange-500" />
            Your internship analytics
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Snapshot of progress, vouchers, and status across all your internships.
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">Avg progress</p>
          <p
            className="text-2xl font-bold"
            style={{
              background: `linear-gradient(90deg, ${ORANGE}, ${BLUE})`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            {avgProgress}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="Progress per internship" icon={<TrendingUp className="w-4 h-4 text-orange-500" />} className="lg:col-span-2">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <BarChart data={progressData} layout="vertical" margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="progBar" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor={ORANGE} />
                    <stop offset="100%" stopColor={BLUE} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} width={120} />
                <Tooltip formatter={(v: number) => [`${v}%`, 'Progress']} contentStyle={{ fontSize: 12 }} />
                <Bar dataKey="progress" fill="url(#progBar)" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Status breakdown" icon={<Activity className="w-4 h-4 text-blue-600" />}>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={42} outerRadius={70} paddingAngle={3}>
                  {statusData.map((s, i) => (
                    <Cell key={i} fill={s.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Vouchers" icon={<Ticket className="w-4 h-4 text-orange-500" />}>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <PieChart>
                <Pie data={voucherData} dataKey="value" nameKey="name" innerRadius={42} outerRadius={70} paddingAngle={3}>
                  {voucherData.map((s, i) => (
                    <Cell key={i} fill={s.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Internships started over time" icon={<Briefcase className="w-4 h-4 text-blue-600" />} className="lg:col-span-2">
          {timelineData.length === 0 ? (
            <p className="text-xs text-slate-500 h-40 flex items-center justify-center">No timeline data.</p>
          ) : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <AreaChart data={timelineData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="myTimeline" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={ORANGE_LIGHT} stopOpacity={0.8} />
                      <stop offset="100%" stopColor={BLUE_LIGHT} stopOpacity={0.15} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip contentStyle={{ fontSize: 12 }} />
                  <Area type="monotone" dataKey="count" name="Started" stroke={ORANGE} strokeWidth={2.5} fill="url(#myTimeline)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

export default MyInternshipCharts
