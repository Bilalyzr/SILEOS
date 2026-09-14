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
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts'

const ORANGE = '#f97316'
const BLUE = '#2563eb'

interface MyInternship {
  id: number | string
  title: string
  status: string
  attendance_days?: number
  voucher_code?: string
  redeemed_course_title?: string | null
  hired_company?: string | null
}

interface Props {
  internships: MyInternship[]
}

export const StudentInternshipSummary: React.FC<Props> = ({ internships }) => {
  if (!internships || internships.length === 0) return null

  const redeemed = internships.filter((i) => i.status === 'redeemed').length
  const issued = internships.length - redeemed
  const statusData = [
    { name: 'Issued', value: issued },
    { name: 'Redeemed', value: redeemed },
  ].filter((d) => d.value > 0)

  const attendanceData = internships.map((i) => ({
    name: i.title.length > 14 ? i.title.slice(0, 12) + '…' : i.title,
    days: i.attendance_days || 0,
  }))

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-2">
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="text-sm font-semibold text-slate-800 mb-2">Voucher status</h4>
        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
            <PieChart>
              <Pie
                data={statusData}
                dataKey="value"
                nameKey="name"
                innerRadius={40}
                outerRadius={65}
                paddingAngle={3}
              >
                {statusData.map((s, i) => (
                  <Cell key={i} fill={s.name === 'Redeemed' ? BLUE : ORANGE} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="text-sm font-semibold text-slate-800 mb-2">Attendance by internship</h4>
        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
            <BarChart data={attendanceData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="days" name="Days attended" fill={ORANGE} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export default StudentInternshipSummary
