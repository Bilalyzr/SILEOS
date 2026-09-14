import React from 'react'
import {
  ResponsiveContainer,
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
import { Briefcase, Users, TrendingUp, Activity } from 'lucide-react'
import type { CompanyInternship } from '@/api/company-dashboard'

const ORANGE = '#f97316'
const BLUE = '#2563eb'
const ORANGE_LIGHT = '#fb923c'
const BLUE_LIGHT = '#60a5fa'
const EMERALD = '#10b981'
const AMBER = '#f59e0b'

interface Props {
  internships: CompanyInternship[]
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

export const CompanyInternshipCharts: React.FC<Props> = ({ internships }) => {
  if (!internships || internships.length === 0) {
    return (
      <div className="mb-6 rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <Briefcase className="w-10 h-10 text-orange-400 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800">No internship analytics yet</h3>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          Charts (progress, students, distribution) will appear once admin publishes an internship
          tied to your company.
        </p>
      </div>
    )
  }

  const progressData = internships.map((i) => ({
    name: i.title.length > 18 ? i.title.slice(0, 16) + '…' : i.title,
    progress: i.avg_progress_pct || 0,
  }))

  const studentData = internships.map((i) => ({
    name: i.title.length > 18 ? i.title.slice(0, 16) + '…' : i.title,
    students: i.student_count || 0,
  }))

  const bins = { '0-25%': 0, '26-50%': 0, '51-75%': 0, '76-100%': 0 }
  internships.forEach((i) => {
    const p = i.avg_progress_pct || 0
    if (p <= 25) bins['0-25%']++
    else if (p <= 50) bins['26-50%']++
    else if (p <= 75) bins['51-75%']++
    else bins['76-100%']++
  })
  const distData = [
    { name: '0-25%', value: bins['0-25%'], color: AMBER },
    { name: '26-50%', value: bins['26-50%'], color: ORANGE },
    { name: '51-75%', value: bins['51-75%'], color: BLUE },
    { name: '76-100%', value: bins['76-100%'], color: EMERALD },
  ].filter((d) => d.value > 0)

  const totalStudents = internships.reduce((s, i) => s + (i.student_count || 0), 0)
  const overallAvg =
    internships.length > 0
      ? Math.round(internships.reduce((s, i) => s + (i.avg_progress_pct || 0), 0) / internships.length)
      : 0

  return (
    <div className="space-y-4 mb-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-orange-500" />
            Internship analytics
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Progress and roster across {internships.length} internship{internships.length === 1 ? '' : 's'}.
          </p>
        </div>
        <div className="flex gap-6 text-right">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-500">Students</p>
            <p className="text-2xl font-bold text-slate-900">{totalStudents}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-500">Avg progress</p>
            <p
              className="text-2xl font-bold"
              style={{
                background: `linear-gradient(90deg, ${ORANGE}, ${BLUE})`,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              {overallAvg}%
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="Avg progress per internship" icon={<TrendingUp className="w-4 h-4 text-orange-500" />} className="lg:col-span-2">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <BarChart data={progressData} layout="vertical" margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="cpyProg" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor={ORANGE} />
                    <stop offset="100%" stopColor={BLUE} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} width={120} />
                <Tooltip formatter={(v: number) => [`${v}%`, 'Avg progress']} contentStyle={{ fontSize: 12 }} />
                <Bar dataKey="progress" fill="url(#cpyProg)" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Progress distribution" icon={<Activity className="w-4 h-4 text-blue-600" />}>
          {distData.length === 0 ? (
            <p className="text-xs text-slate-500 h-40 flex items-center justify-center">No progress data.</p>
          ) : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <PieChart>
                  <Pie data={distData} dataKey="value" nameKey="name" innerRadius={42} outerRadius={70} paddingAngle={3}>
                    {distData.map((s, i) => (
                      <Cell key={i} fill={s.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card title="Students per internship" icon={<Users className="w-4 h-4 text-orange-500" />} className="lg:col-span-3">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <BarChart data={studentData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="cpyStudents" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={ORANGE_LIGHT} stopOpacity={0.95} />
                    <stop offset="100%" stopColor={BLUE_LIGHT} stopOpacity={0.7} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} interval={0} angle={-15} textAnchor="end" height={60} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Bar dataKey="students" name="Students" fill="url(#cpyStudents)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default CompanyInternshipCharts
