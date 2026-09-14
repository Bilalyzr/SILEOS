import React, { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { Briefcase, Ticket, TrendingUp, IndianRupee } from 'lucide-react'
import { api } from '@/api/axios'

const ORANGE = '#f97316'
const BLUE = '#2563eb'
const ORANGE_LIGHT = '#fb923c'
const BLUE_LIGHT = '#60a5fa'

interface TimePoint {
  date: string
  issued: number
  redeemed: number
}
interface RevenuePoint {
  date: string
  revenue: number
}
interface StatusSlice {
  status: string
  count: number
}
interface TopInternship {
  name: string
  issued: number
  redeemed: number
}
interface Payload {
  period: string
  bucket: string
  timeseries: TimePoint[]
  status_breakdown: StatusSlice[]
  top_internships: TopInternship[]
  revenue_timeseries: RevenuePoint[]
}

interface Props {
  period: string
}

const Card: React.FC<{ title: string; icon: React.ReactNode; children: React.ReactNode; className?: string }> = ({
  title,
  icon,
  children,
  className = '',
}) => (
  <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
    <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center">
      <span className="mr-2">{icon}</span>
      {title}
    </h3>
    {children}
  </div>
)

export const InternshipAnalyticsCharts: React.FC<Props> = ({ period }) => {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)
        const r = await api.get(`/admin/analytics/internships?period=${period}`)
        if (cancelled) return
        setData(r.data)
      } catch (e: any) {
        if (cancelled) return
        setError(e?.response?.data?.detail || e?.message || 'Failed to load internship analytics')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchData()
    return () => {
      cancelled = true
    }
  }, [period])

  const formatDate = (d: string) => {
    if (!d) return ''
    const dt = new Date(d)
    if (data?.bucket === 'month') {
      return dt.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
    }
    return dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 h-72 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-red-200 p-6 text-sm text-red-600">
        {error}
      </div>
    )
  }

  if (!data) return null

  const totalIssued = data.status_breakdown.reduce((s, r) => s + r.count, 0)
  const totalRedeemed = data.status_breakdown.find((r) => r.status === 'redeemed')?.count || 0
  const totalRevenue = data.revenue_timeseries.reduce((s, r) => s + r.revenue, 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center">
            <Briefcase className="w-5 h-5 mr-2 text-orange-500" />
            Internship Analytics
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Voucher activity and revenue across all internships, bucketed by {data.bucket}.
          </p>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Vouchers Issued</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{totalIssued}</p>
          </div>
          <Ticket className="w-8 h-8 text-orange-500" />
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Vouchers Redeemed</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{totalRedeemed}</p>
            <p className="text-xs text-gray-500 mt-1">
              {totalIssued > 0 ? Math.round((totalRedeemed / totalIssued) * 100) : 0}% redemption
            </p>
          </div>
          <TrendingUp className="w-8 h-8 text-blue-600" />
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Revenue ({data.period})</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">₹{totalRevenue.toLocaleString()}</p>
          </div>
          <IndianRupee className="w-8 h-8 text-emerald-600" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Issued vs Redeemed timeseries */}
        <Card title="Vouchers Issued vs Redeemed" icon={<Ticket className="w-4 h-4 text-orange-500" />} className="lg:col-span-2">
          {data.timeseries.length === 0 ? (
            <p className="text-sm text-gray-500 h-60 flex items-center justify-center">No voucher activity in this period.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <AreaChart data={data.timeseries} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="issuedGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={ORANGE} stopOpacity={0.8} />
                      <stop offset="100%" stopColor={ORANGE} stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="redeemedGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={BLUE} stopOpacity={0.7} />
                      <stop offset="100%" stopColor={BLUE} stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12, fill: '#6b7280' }} />
                  <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} />
                  <Tooltip labelFormatter={(l) => formatDate(l as string)} contentStyle={{ fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area type="monotone" dataKey="issued" name="Issued" stroke={ORANGE} strokeWidth={2.5} fill="url(#issuedGrad)" />
                  <Area type="monotone" dataKey="redeemed" name="Redeemed" stroke={BLUE} strokeWidth={2} fill="url(#redeemedGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Status donut */}
        <Card title="Status Breakdown" icon={<TrendingUp className="w-4 h-4 text-blue-600" />}>
          {data.status_breakdown.length === 0 ? (
            <p className="text-sm text-gray-500 h-60 flex items-center justify-center">No vouchers yet.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <PieChart>
                  <Pie
                    data={data.status_breakdown}
                    dataKey="count"
                    nameKey="status"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                  >
                    {data.status_breakdown.map((s, i) => (
                      <Cell
                        key={i}
                        fill={s.status === 'redeemed' ? BLUE : ORANGE}
                      />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Top internships bars */}
        <Card title="Top Internships (by vouchers)" icon={<Briefcase className="w-4 h-4 text-orange-500" />} className="lg:col-span-2">
          {data.top_internships.length === 0 ? (
            <p className="text-sm text-gray-500 h-60 flex items-center justify-center">No internships yet.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <BarChart data={data.top_internships} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6b7280' }} interval={0} angle={-15} textAnchor="end" height={60} />
                  <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} />
                  <Tooltip contentStyle={{ fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="issued" name="Issued" fill={ORANGE} radius={[6, 6, 0, 0]} />
                  <Bar dataKey="redeemed" name="Redeemed" fill={BLUE} radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        {/* Revenue area */}
        <Card title="Voucher Revenue" icon={<IndianRupee className="w-4 h-4 text-emerald-600" />}>
          {data.revenue_timeseries.length === 0 ? (
            <p className="text-sm text-gray-500 h-60 flex items-center justify-center">No revenue in this period.</p>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <AreaChart data={data.revenue_timeseries} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={ORANGE_LIGHT} stopOpacity={0.8} />
                      <stop offset="100%" stopColor={BLUE_LIGHT} stopOpacity={0.2} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12, fill: '#6b7280' }} />
                  <YAxis tickFormatter={(v) => `₹${v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}`} tick={{ fontSize: 12, fill: '#6b7280' }} />
                  <Tooltip
                    formatter={(value: number) => [`₹${value.toLocaleString()}`, 'Revenue']}
                    labelFormatter={(l) => formatDate(l as string)}
                    contentStyle={{ fontSize: 12 }}
                  />
                  <Area type="monotone" dataKey="revenue" stroke={ORANGE} strokeWidth={2.5} fill="url(#revenueGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

export default InternshipAnalyticsCharts
